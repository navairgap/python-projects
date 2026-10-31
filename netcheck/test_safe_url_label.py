"""Tests for netcheck's sanitized HTTP URL display labels."""

import unittest

from netcheck import safe_url_label


class TestSafeUrlLabel(unittest.TestCase):
    def test_removes_credentials_path_query_and_fragment(self):
        url = "https://alice:secret@example.com/private?token=hidden#section"
        self.assertEqual(safe_url_label(url), "https://example.com")

    def test_keeps_brackets_for_ipv6_and_explicit_port(self):
        self.assertEqual(
            safe_url_label("https://[2001:db8::1]:8443/status?token=x"),
            "https://[2001:db8::1]:8443",
        )

    def test_rejects_non_http_schemes_and_missing_hosts(self):
        for value in ("ftp://example.com/file", "file:///etc/passwd", "/relative/path"):
            with self.subTest(value=value):
                self.assertEqual(safe_url_label(value), "<invalid URL>")

    def test_malformed_port_does_not_raise(self):
        self.assertEqual(safe_url_label("https://example.com:70000"), "<invalid URL>")


if __name__ == "__main__":
    unittest.main()
