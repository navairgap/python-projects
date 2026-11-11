import argparse
import contextlib
import io
import os
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

import netcheck
from netcheck import safe_url_label

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "netcheck.py")


class FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


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

    def test_blank_and_non_string_hosts_are_rejected_before_resolution(self):
        for host in ("", "  ", None, 42, [], {}):
            with self.subTest(host=host):
                with patch.object(socket, "getaddrinfo") as resolve:
                    self.assertIsNone(netcheck.dns_time(host))
                    resolve.assert_not_called()


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

    def test_truncated_http_response_returns_none(self):
        # http.client errors (e.g. IncompleteRead) are not OSError subclasses.
        import http.client

        with patch.object(netcheck.urllib.request, "urlopen",
                          side_effect=http.client.IncompleteRead(b"partial")):
            self.assertIsNone(netcheck.http_status("https://example.com"))

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

    def test_non_string_and_blank_urls_return_none_without_opening(self):
        for url in (None, "", "  ", 42, [], {}):
            with self.subTest(url=url):
                with patch.object(netcheck.urllib.request, "urlopen") as open_url:
                    self.assertIsNone(netcheck.http_status(url))
                    open_url.assert_not_called()


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


class TestTimeoutForwarding(unittest.TestCase):
    def test_timeout_forwarded(self):
        seen = {}

        def fake(addr, timeout=3):
            seen["timeout"] = timeout
            return FakeConn()

        with patch.object(socket, "create_connection", side_effect=fake):
            ok, _ = netcheck.check_port("h", 80, timeout=0.5)
        self.assertTrue(ok)
        self.assertEqual(seen["timeout"], 0.5)


class TestArgparseTypes(unittest.TestCase):
    def test_cli_timeout_parser_rejects_nonpositive_and_nonfinite(self):
        for value in ("0", "-1", "inf", "nan"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                parser = argparse.ArgumentParser()
                parser.add_argument("--timeout", type=netcheck.positive_timeout)
                parser.parse_args(["--timeout", value])

    def test_cli_port_parser_rejects_out_of_range(self):
        for value in ("0", "65536", "abc"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                parser = argparse.ArgumentParser()
                parser.add_argument("port", type=netcheck.tcp_port)
                parser.parse_args([value])


class TestCli(unittest.TestCase):
    def test_invalid_port_exits_before_network_access(self):
        result = subprocess.run(
            [sys.executable, SCRIPT, "port", "example.com", "65536"],
            capture_output=True, text=True, check=False, timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("port must be between 1 and 65535", result.stderr)

    def test_http_output_does_not_echo_credentials_or_query_tokens(self):
        supplied = "https://alice:secret@example.com/private?token=secret#fragment"
        output = io.StringIO()
        with patch.object(sys, "argv", ["netcheck.py", "http", supplied]):
            with patch.object(netcheck, "http_status", return_value=200):
                with contextlib.redirect_stdout(output):
                    with self.assertRaises(SystemExit) as result:
                        netcheck.main()
        self.assertEqual(result.exception.code, 0)
        displayed = output.getvalue().strip()
        self.assertEqual(displayed, "https://example.com -> 200")
        self.assertNotIn("secret", displayed)
        self.assertNotIn("/private", displayed)


if __name__ == "__main__":
    unittest.main()
