import os
import tempfile
import unittest

from audit import DirStat, audit, format_size, parse_size, render_bars


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


if __name__ == "__main__":
    unittest.main()

class TestFormat(unittest.TestCase):
    def test_format_size(self):
        self.assertEqual(format_size(512), "512B")
        self.assertEqual(format_size(2048), "2.0K")
        self.assertEqual(format_size(5 * 1024 ** 3), "5.0G")

    def test_parse_size(self):
        self.assertEqual(parse_size("100M"), 100 * 1024 ** 2)
        self.assertEqual(parse_size("2g"), 2 * 1024 ** 3)
        self.assertEqual(parse_size("512"), 512)

    def test_parse_size_rejects_empty_negative_and_nonfinite_values(self):
        for value in ("", "  ", "-1", "-1M", "infG", "nanM", "1e999T"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_size(value)

    def test_parse_size_accepts_fractional_suffix(self):
        self.assertEqual(parse_size("1.5K"), 1536)

    def test_render_bars(self):
        rows = [DirStat("/a", 100, 1), DirStat("/b", 50, 1)]
        lines = render_bars(rows, width=10)
        self.assertEqual(len(lines), 2)
        self.assertIn("/a", lines[0])


class TestCsv(unittest.TestCase):
    def test_csv_export(self):
        import csv, io
        from audit import DirStat
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["path", "size_bytes", "files"])
        w.writerow(["/x", 10, 1])
        buf.seek(0)
        rows = list(csv.reader(buf))
        self.assertEqual(rows[1], ["/x", "10", "1"])


if __name__ == "__main__":
    unittest.main()

class TestTotalsOnly(unittest.TestCase):
    def test_no_chart_when_totals_only(self):
        import subprocess
        import sys
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as d:
            with open(f"{d}/f.bin", "wb") as f:
                f.write(b"x" * 10)
            out = subprocess.run(
                [sys.executable, os.path.join(os.path.dirname(__file__), "audit.py"),
                 d, "--totals-only", "-n", "5"],
                capture_output=True, text=True)
            self.assertEqual(out.returncode, 0)
            self.assertIn("scanned 1 files", out.stdout)
            self.assertNotIn("\u2588", out.stdout)


if __name__ == "__main__":
    unittest.main()


class TestTopValidation(unittest.TestCase):
    def test_nonpositive_top_rejected(self):
        import subprocess
        import sys
        script = os.path.join(os.path.dirname(__file__), "audit.py")
        result = subprocess.run(
            [sys.executable, script, "--top", "0"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--top must be at least 1", result.stderr)
