import socket
import unittest
from unittest.mock import patch

import netcheck


class FakeConn:
    def __enter__(self): return self
    def __exit__(self, *a): return False


class TestPort(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

class FakeConn:
    def __enter__(self): return self
    def __exit__(self, *a): return False


class TestTimeout(unittest.TestCase):
    def test_timeout_forwarded(self):
        seen = {}
        def fake(addr, timeout=3):
            seen["timeout"] = timeout
            return FakeConn()
        with patch.object(socket, "create_connection", side_effect=fake):
            ok, _ = netcheck.check_port("h", 80, timeout=0.5)
        self.assertTrue(ok)
        self.assertEqual(seen["timeout"], 0.5)


if __name__ == "__main__":
    unittest.main()
