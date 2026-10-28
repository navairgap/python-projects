import socket
import unittest
from unittest.mock import patch

import netcheck


class FakeConn:
    def __enter__(self): return self
    def __exit__(self, *a): return False


class TestPort(unittest.TestCase):
    def test_rejects_invalid_port(self):
        for port in (0, -1, 65536, True, "80"):
            with self.subTest(port=port), self.assertRaises(ValueError):
                netcheck.check_port("example.com", port)

    def test_rejects_invalid_timeout(self):
        for timeout in (0, -1, float("inf"), float("nan")):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                netcheck.check_port("example.com", 443, timeout=timeout)

    def test_rejects_boolean_timeout(self):
        with self.assertRaises(ValueError):
            netcheck.check_port("example.com", 443, timeout=True)

    def test_open_port(self):
        with patch.object(socket, "create_connection", return_value=FakeConn()):
            ok, ms = netcheck.check_port("example.com", 443)
        self.assertTrue(ok)
        self.assertIsNotNone(ms)

    def test_closed_port(self):
        with patch.object(socket, "create_connection", side_effect=OSError("refused")):
            ok, ms = netcheck.check_port("example.com", 1)
        self.assertFalse(ok)
        self.assertIsNone(ms)


class TestDns(unittest.TestCase):
    def test_resolves(self):
        self.assertIsNotNone(netcheck.dns_time("localhost"))

    def test_nxdomain(self):
        with patch.object(socket, "getaddrinfo", side_effect=socket.gaierror):
            self.assertIsNone(netcheck.dns_time("nope.invalid"))


class TestHttp(unittest.TestCase):
    def test_404_is_a_valid_answer(self):
        from urllib.error import HTTPError
        with patch.object(netcheck.urllib.request, "urlopen",
                          side_effect=HTTPError("u", 404, "nf", {}, None)):
            self.assertEqual(netcheck.http_status("http://x/"), 404)

    def test_rejects_non_http_schemes_before_open(self):
        with patch.object(netcheck.urllib.request, "urlopen") as open_url:
            self.assertIsNone(netcheck.http_status("file:///etc/passwd"))
        open_url.assert_not_called()

    def test_malformed_url_returns_none(self):
        self.assertIsNone(netcheck.http_status("http://["))

    def test_timeout_is_forwarded(self):
        with patch.object(netcheck.urllib.request, "urlopen") as open_url:
            open_url.return_value.__enter__.return_value.status = 204
            self.assertEqual(netcheck.http_status("https://example.com", timeout=0.5), 204)
        self.assertEqual(open_url.call_args.kwargs["timeout"], 0.5)

    def test_nonpositive_timeout_rejected(self):
        with self.assertRaises(ValueError):
            netcheck.http_status("https://example.com", timeout=0)

    def test_nonfinite_or_non_numeric_timeout_rejected(self):
        for timeout in (float("inf"), float("nan"), True, "1"):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                netcheck.http_status("https://example.com", timeout=timeout)


if __name__ == "__main__":
    unittest.main()

class FakeConn:
    def __enter__(self): return self
    def __exit__(self, *a): return False


class TestCliValidation(unittest.TestCase):
    def test_invalid_port_exits_before_network_access(self):
        import os
        import subprocess
        import sys
        script = os.path.join(os.path.dirname(__file__), "netcheck.py")
        result = subprocess.run(
            [sys.executable, script, "port", "example.com", "65536"],
            capture_output=True, text=True, timeout=3,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("port must be between 1 and 65535", result.stderr)


class TestTimeout(unittest.TestCase):
    def test_cli_timeout_parser_rejects_nonpositive_and_nonfinite(self):
        for value in ("0", "-1", "inf", "nan"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                import argparse
                parser = argparse.ArgumentParser()
                parser.add_argument("--timeout", type=netcheck.positive_timeout)
                parser.parse_args(["--timeout", value])

    def test_cli_port_parser_rejects_out_of_range(self):
        for value in ("0", "65536", "abc"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                import argparse
                parser = argparse.ArgumentParser()
                parser.add_argument("port", type=netcheck.tcp_port)
                parser.parse_args([value])

    def test_timeout_forwarded(self):
        seen = {}
        def fake(addr, timeout=3):
            seen["timeout"] = timeout
            return FakeConn()
        with patch.object(socket, "create_connection", side_effect=fake):
            ok, _ = netcheck.check_port("h", 80, timeout=0.5)
        self.assertTrue(ok)
        self.assertEqual(seen["timeout"], 0.5)


class TestHttpUrlTypes(unittest.TestCase):
    def test_non_string_and_blank_urls_return_none_without_opening(self):
        for url in (None, "", "  ", 42, [], {}):
            with self.subTest(url=url):
                with patch.object(netcheck.urllib.request, "urlopen") as open_url:
                    self.assertIsNone(netcheck.http_status(url))
                    open_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()
