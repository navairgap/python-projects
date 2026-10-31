"""Regression tests for disk-audit filesystem permission failures."""

import unittest
from unittest.mock import patch

from audit import audit


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


if __name__ == "__main__":
    unittest.main()
