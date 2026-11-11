import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from audit import DirStat, audit, format_size, parse_size, render_bars

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit.py")


def run_cli(arguments):
    command = [sys.executable, SCRIPT]
    command.extend(arguments)
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        os.makedirs(f"{self.root}/sub/deep")
        self._w(f"{self.root}/a.txt", 100)
        self._w(f"{self.root}/sub/b.bin", 200)
        self._w(f"{self.root}/sub/deep/c.bin", 400)

    def _w(self, p, n):
        with open(p, "wb") as f:
            f.write(b"x" * n)

    def test_sizes_aggregate_up(self):
        stats, total, count = audit(self.root)
        self.assertEqual(count, 3)
        self.assertEqual(total, 700)
        sizes = {s.path.split(os.sep)[-1]: s.size for s in stats}
        self.assertEqual(sizes["deep"], 400)
        self.assertEqual(sizes["sub"], 600)

    def test_min_size_filter(self):
        stats, _, _ = audit(self.root, min_size=500)
        self.assertEqual([s.path for s in stats], [f"{self.root}/sub"])

    def test_exclude(self):
        _, total, count = audit(self.root, exclude={"sub"})
        self.assertEqual((total, count), (100, 1))

    def test_default_cache_and_dependency_dirs_are_skipped(self):
        os.makedirs(os.path.join(self.root, ".cache"))
        os.makedirs(os.path.join(self.root, "node_modules"))
        self._w(os.path.join(self.root, ".cache", "ignored.bin"), 900)
        self._w(os.path.join(self.root, "node_modules", "ignored.bin"), 800)
        _, total, count = audit(self.root)
        self.assertEqual((total, count), (700, 3))

    def test_symlink_skipped(self):
        try:
            os.symlink(f"{self.root}/sub", f"{self.root}/link")
        except OSError:
            self.skipTest("no symlink support")
        _, _, count = audit(self.root)
        self.assertEqual(count, 3)

    def test_deeper_than_default_recursion_limit(self):
        # Regression: the walk used to recurse per directory level, so any
        # tree deeper than the interpreter's recursion limit crashed the scan.
        # (setUp adds 700 bytes across sub/deep; the deep branch adds 10.)
        depth = 1900
        path = self.root
        for _ in range(depth):
            path = os.path.join(path, "d")
            os.mkdir(path)
        self._w(os.path.join(path, "leaf.bin"), 10)
        stats, total, count = audit(self.root)
        self.assertEqual((total, count), (710, 4))
        self.assertEqual(sum(1 for s in stats if s.size == 10), depth)


class BrokenEntry:
    name = "restricted.bin"
    path = "/restricted/restricted.bin"

    def is_symlink(self):
        return False

    def is_dir(self, *, follow_symlinks=False):
        return False

    def stat(self, *, follow_symlinks=False):
        raise PermissionError("access denied")


class TestAuditIoErrors(unittest.TestCase):
    def test_unreadable_root_returns_empty_result(self):
        with patch("audit.os.scandir", side_effect=PermissionError("access denied")):
            stats, total, count = audit("/restricted")

        self.assertEqual(stats, [])
        self.assertEqual((total, count), (0, 0))

    def test_unreadable_file_is_skipped_without_losing_other_entries(self):
        class ReadableEntry(BrokenEntry):
            name = "readable.bin"
            path = "/scan/readable.bin"

            def stat(self, *, follow_symlinks=False):
                return type("Stat", (), {"st_size": 25})()

        with patch("audit.os.scandir", return_value=[BrokenEntry(), ReadableEntry()]):
            stats, total, count = audit("/scan")

        self.assertEqual(stats, [])
        self.assertEqual((total, count), (25, 1))


class TestFormat(unittest.TestCase):
    def test_format_size(self):
        self.assertEqual(format_size(512), "512B")
        self.assertEqual(format_size(2048), "2.0K")
        self.assertEqual(format_size(5 * 1024 ** 3), "5.0G")

    def test_parse_size(self):
        self.assertEqual(parse_size("100M"), 100 * 1024 ** 2)
        self.assertEqual(parse_size("2g"), 2 * 1024 ** 3)
        self.assertEqual(parse_size("512"), 512)
        self.assertEqual(parse_size("1.5K"), 1536)

    def test_parse_size_rejects_empty_negative_and_nonfinite_values(self):
        for value in ("", "  ", "-1", "-1M", "infG", "nanM", "1e999T"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_size(value)

    def test_render_bars(self):
        rows = [DirStat("/a", 100, 1), DirStat("/b", 50, 1)]
        lines = render_bars(rows, width=10)
        self.assertEqual(len(lines), 2)
        self.assertIn("/a", lines[0])

    def test_all_zero_size_directories_render_without_division_error(self):
        rows = [DirStat("/empty", 0, 0), DirStat("/nested-empty", 0, 0)]
        lines = render_bars(rows)
        self.assertEqual(len(lines), 2)
        self.assertTrue(all("0B" in line for line in lines))
        self.assertIn("/empty", lines[0])
        self.assertIn("/nested-empty", lines[1])


class TestCli(unittest.TestCase):
    def test_missing_root_returns_argparse_error(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = os.path.join(directory, "does-not-exist")
            result = run_cli([missing])
        self.assertEqual(result.returncode, 2)
        self.assertIn("scan path is not a directory", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_file_cannot_be_used_as_scan_root(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = os.path.join(directory, "input.txt")
            with open(file_path, "w", encoding="utf-8") as stream:
                stream.write("data")
            result = run_cli([file_path])
        self.assertEqual(result.returncode, 2)
        self.assertIn("scan path is not a directory", result.stderr)

    def test_totals_only_skips_the_chart(self):
        with tempfile.TemporaryDirectory() as d:
            with open(f"{d}/f.bin", "wb") as f:
                f.write(b"x" * 10)
            out = run_cli([d, "--totals-only", "-n", "5"])
            self.assertEqual(out.returncode, 0)
            self.assertIn("scanned 1 files", out.stdout)
            self.assertNotIn("\u2588", out.stdout)

    def test_nonpositive_top_rejected(self):
        result = run_cli(["--top", "0"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("--top must be at least 1", result.stderr)

    def test_invalid_min_size_has_argparse_error_not_traceback(self):
        result = run_cli(["--min-size=-1M"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("size must be a non-negative number", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_unwritable_csv_path_reports_clean_error(self):
        with tempfile.TemporaryDirectory() as d:
            result = run_cli([d, "--csv", os.path.join(d, "missing-dir", "out.csv")])
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot write csv", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
