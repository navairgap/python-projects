import functools
import http.server
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import serveit


def serve_dir(path):
    """Start a threaded server on an ephemeral port; stop it via the cleanup."""
    handler = functools.partial(serveit.Handler, directory=path)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()

    def stop():
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=3)

    return srv, stop


class ServeItTestCase(unittest.TestCase):
    def serve(self, path):
        srv, stop = serve_dir(path)
        self.addCleanup(stop)
        return srv


class TestHandlerDefaults(unittest.TestCase):
    def test_directory_listing_disabled_by_default(self):
        self.assertFalse(serveit.Handler.allow_listing)


class TestServing(ServeItTestCase):
    def test_get_file(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "hi.txt"), "w", encoding="utf-8") as f:
                f.write("hello")
            srv = self.serve(d)
            url = f"http://127.0.0.1:{srv.server_address[1]}/hi.txt"
            with urllib.request.urlopen(url, timeout=3) as r:
                self.assertEqual(r.read().decode(), "hello")
                self.assertEqual(r.status, 200)

    def test_missing_file_404(self):
        with tempfile.TemporaryDirectory() as d:
            srv = self.serve(d)
            url = f"http://127.0.0.1:{srv.server_address[1]}/nope"
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(url, timeout=3)
            self.assertEqual(ctx.exception.code, 404)


class TestListing(ServeItTestCase):
    def test_directory_listing_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            srv = self.serve(d)
            url = f"http://127.0.0.1:{srv.server_address[1]}/"
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(url, timeout=3)
            self.assertEqual(ctx.exception.code, 404)

    def test_directory_listing_requires_explicit_opt_in(self):
        old = serveit.Handler.allow_listing
        serveit.Handler.allow_listing = True
        self.addCleanup(setattr, serveit.Handler, "allow_listing", old)
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "visible.txt"), "w", encoding="utf-8") as f:
                f.write("hello")
            srv = self.serve(d)
            url = f"http://127.0.0.1:{srv.server_address[1]}/"
            with urllib.request.urlopen(url, timeout=3) as response:
                html = response.read().decode()
                self.assertEqual(response.status, 200)
                self.assertIn("visible.txt", html)


class TestSymlinkBoundary(ServeItTestCase):
    def test_symlink_cannot_serve_a_file_outside_the_root(self):
        with tempfile.TemporaryDirectory() as served, tempfile.TemporaryDirectory() as outside:
            secret = os.path.join(outside, "private.txt")
            with open(secret, "w", encoding="utf-8") as stream:
                stream.write("not for serving")

            link = os.path.join(served, "escape.txt")
            try:
                os.symlink(secret, link)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")

            srv = self.serve(served)
            url = f"http://127.0.0.1:{srv.server_address[1]}/escape.txt"
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(url, timeout=3)
            self.assertEqual(ctx.exception.code, 404)

    def test_outside_symlink_cannot_fall_through_to_denial_sentinel(self):
        # Regression: denial used to clamp escaping requests onto a fixed
        # sentinel path, which a real file of the same name could shadow.
        with tempfile.TemporaryDirectory() as served, tempfile.TemporaryDirectory() as outside:
            with open(os.path.join(served, ".serveit-denied"), "w", encoding="utf-8") as stream:
                stream.write("this file must never be returned")
            secret = os.path.join(outside, "private.txt")
            with open(secret, "w", encoding="utf-8") as stream:
                stream.write("outside data")
            try:
                os.symlink(secret, os.path.join(served, "escape.txt"))
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")

            srv = self.serve(served)
            url = f"http://127.0.0.1:{srv.server_address[1]}/escape.txt"
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(url, timeout=3)
            self.assertEqual(caught.exception.code, 404)


class TestCli(unittest.TestCase):
    def test_cli_rejects_out_of_range_port_without_traceback(self):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "serveit.py")
        for port in ("-1", "65536", "not-a-port"):
            with self.subTest(port=port):
                result = subprocess_run([script, "--port", port])
                self.assertEqual(result.returncode, 2)
                self.assertIn("port must", result.stderr)
                self.assertNotIn("Traceback", result.stderr)


def subprocess_run(arguments):
    import subprocess
    import sys

    command = [sys.executable]
    command.extend(arguments)
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)


if __name__ == "__main__":
    unittest.main()
