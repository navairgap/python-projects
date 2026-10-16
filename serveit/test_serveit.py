import functools
import http.server
import threading
import unittest
import urllib.request

import serveit


def serve_dir(path, port):
    handler = functools.partial(serveit.Handler, directory=path)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


class TestServe(unittest.TestCase):
    def test_directory_listing_disabled_by_default(self):
        self.assertFalse(serveit.Handler.allow_listing)

    def test_get_file(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            with open(f"{d}/hi.txt", "w") as f:
                f.write("hello")
            srv = serve_dir(d, 0)
            port = srv.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/hi.txt") as r:
                self.assertEqual(r.read().decode(), "hello")
                self.assertEqual(r.status, 200)
            srv.shutdown()

    def test_missing_file_404(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            srv = serve_dir(d, 0)
            port = srv.server_address[1]
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/nope")
            self.assertEqual(ctx.exception.code, 404)
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()

class TestNoListing(unittest.TestCase):
    def test_directory_listing_disabled(self):
        import tempfile
        serveit.Handler.allow_listing = False
        try:
            with tempfile.TemporaryDirectory() as d:
                srv = serve_dir(d, 0)
                port = srv.server_address[1]
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/")
                self.assertEqual(ctx.exception.code, 404)
                srv.shutdown()
        finally:
            serveit.Handler.allow_listing = False


if __name__ == "__main__":
    unittest.main()
