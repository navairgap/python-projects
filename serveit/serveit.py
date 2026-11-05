#!/usr/bin/env python3
"""serveit - dead-simple static file server. stdlib only."""

import argparse
import functools
import http.server
import os
import sys

QUIET = False


def valid_port(value):
    """Argparse validator for TCP ports; zero requests an ephemeral port."""
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("port must be an integer from 0 to 65535")
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 0 and 65535")
    return port


class Handler(http.server.SimpleHTTPRequestHandler):
    allow_listing = False

    def _resolve_path(self, path):
        """Resolve a path and mark requests that escape through symlinks."""
        root = os.path.realpath(self.directory)
        candidate = os.path.realpath(super().translate_path(path))
        try:
            inside_root = os.path.commonpath((root, candidate)) == root
        except ValueError:
            inside_root = False
        if not inside_root:
            self._serveit_path_denied = True
            return root
        return candidate

    def translate_path(self, path):
        """Return the prevalidated path during the base handler's lookup."""
        cached = getattr(self, "_serveit_cached_path", None)
        if cached is not None:
            return cached
        return self._resolve_path(path)

    def send_head(self):
        # A fake filename under the document root can collide with a real file.
        # Decide on the path before the base class sends any success headers.
        self._serveit_path_denied = False
        resolved = self._resolve_path(self.path)
        if self._serveit_path_denied:
            self.send_error(404, "not found")
            return None
        self._serveit_cached_path = resolved
        try:
            return super().send_head()
        finally:
            self._serveit_cached_path = None

    def log_message(self, fmt, *args):
        if not QUIET:
            super().log_message(fmt, *args)

    def list_directory(self, path):
        if not self.allow_listing:
            self.send_error(404, "listing disabled")
            return None
        return super().list_directory(path)

def main():
    global QUIET
    ap = argparse.ArgumentParser(prog="serveit", description="serve a directory over http")
    ap.add_argument("directory", nargs="?", default=".")
    ap.add_argument("-p", "--port", type=valid_port, default=8000)
    ap.add_argument("-b", "--bind", default="127.0.0.1")
    ap.add_argument("-q", "--quiet", action="store_true")
    ap.add_argument("--list", dest="listing", action="store_true", help="enable directory listings (disabled by default)")
    ap.add_argument("--no-listing", action="store_true", help="disable directory listings (default)")
    a = ap.parse_args()
    QUIET = a.quiet
    Handler.allow_listing = a.listing and not a.no_listing

    handler = functools.partial(Handler, directory=os.path.abspath(a.directory))
    with http.server.ThreadingHTTPServer((a.bind, a.port), handler) as srv:
        print(f"serving {a.directory} at http://{a.bind}:{a.port} (ctrl+c to stop)", file=sys.stderr)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
