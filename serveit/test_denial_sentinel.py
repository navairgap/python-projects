import functools
import http.server
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import serveit


class DenialSentinelRegressionTests(unittest.TestCase):
    def test_outside_symlink_cannot_fall_through_to_denial_sentinel(self):
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

            handler = functools.partial(serveit.Handler, directory=served)
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/escape.txt"
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(url, timeout=3)
                self.assertEqual(caught.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
