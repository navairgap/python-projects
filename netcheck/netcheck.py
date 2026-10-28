#!/usr/bin/env python3
"""netcheck - small network diagnostics. stdlib only."""

import argparse
import math
import socket
import sys
import time
import urllib.request

DEFAULT_TIMEOUT = 3

def positive_timeout(value):
    """argparse type: require a finite, positive timeout in seconds."""
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("timeout must be a number greater than zero")
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be a finite number greater than zero")
    return timeout

def tcp_port(value):
    """argparse type: accept only valid TCP port numbers."""
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("port must be an integer from 1 to 65535")
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port

def check_port(host, port, timeout=DEFAULT_TIMEOUT):
    """return (ok, latency_ms) for a TCP connect."""
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("port must be an integer from 1 to 65535")
    if (not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError("timeout must be a finite number greater than zero")
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, round((time.perf_counter() - start) * 1000, 1)
    except OSError:
        return False, None

def dns_time(host):
    """Resolve a non-empty host; return elapsed milliseconds or None."""
    if not isinstance(host, str) or not host.strip():
        return None
    start = time.perf_counter()
    try:
        socket.getaddrinfo(host, None)
        return round((time.perf_counter() - start) * 1000, 1)
    except OSError:
        return None

def http_status(url, timeout=DEFAULT_TIMEOUT):
    """HEAD an HTTP(S) URL, return status code or None for failures."""
    if (not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError("timeout must be a finite number greater than zero")
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            return None
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (OSError, ValueError):
        return None

def local_ip():
    """best-effort local IP without sending any packets."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()

def main():
    ap = argparse.ArgumentParser(prog="netcheck", description="small network diagnostics")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("port"); p.add_argument("host"); p.add_argument("port", type=tcp_port, nargs="+")
    p = sub.add_parser("dns"); p.add_argument("host")
    p = sub.add_parser("http"); p.add_argument("url")
    sub.add_parser("ip")
    ap.add_argument("-t", "--timeout", type=positive_timeout, default=DEFAULT_TIMEOUT)
    a = ap.parse_args()

    if a.cmd == "port":
        all_ok = True
        for port in a.port:
            ok, ms = check_port(a.host, port, timeout=a.timeout)
            if ok:
                print(f"{a.host}:{port} open ({ms}ms)")
            else:
                print(f"{a.host}:{port} closed or filtered")
                all_ok = False
        if not all_ok:
            sys.exit(1)
    elif a.cmd == "dns":
        ms = dns_time(a.host)
        print(f"{a.host} resolves in {ms}ms" if ms is not None else f"{a.host} does not resolve")
        sys.exit(0 if ms is not None else 1)
    elif a.cmd == "http":
        code = http_status(a.url, timeout=a.timeout)
        print(f"{a.url} -> {code}" if code else f"{a.url} unreachable")
        sys.exit(0 if code else 1)
    elif a.cmd == "ip":
        print(local_ip())


if __name__ == "__main__":
    main()
