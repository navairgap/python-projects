"""CLI argument validation tests for disk-audit."""

import os
import subprocess
import sys
import tempfile
import unittest


SCRIPT = os.path.join(os.path.dirname(__file__), "audit.py")


class AuditCliPathTests(unittest.TestCase):
    def test_missing_root_returns_argparse_error(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = os.path.join(directory, "does-not-exist")
            result = subprocess.run(
                [sys.executable, SCRIPT, missing],
                capture_output=True,
                text=True,
                timeout=5,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("scan path is not a directory", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_file_cannot_be_used_as_scan_root(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = os.path.join(directory, "input.txt")
            with open(file_path, "w", encoding="utf-8") as stream:
                stream.write("data")
            result = subprocess.run(
                [sys.executable, SCRIPT, file_path],
                capture_output=True,
                text=True,
                timeout=5,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("scan path is not a directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
