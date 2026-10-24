#!/usr/bin/env python3
"""disk-audit - find what's eating your disk. stdlib only."""

import argparse
import csv
import json
import math
import os
import sys
from dataclasses import dataclass, field

EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".cache"}

@dataclass
class DirStat:
    path: str
    size: int = 0
    files: int = 0

def format_size(n):
    for unit in ["B", "K", "M", "G", "T"]:
        if n < 1024 or unit == "T":
            return f"{n}B" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024

def parse_size(s):
    """Parse a non-negative byte count or a value with B/K/M/G/T suffix."""
    mult = {"B": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}
    if not isinstance(s, str) or not s.strip():
        raise ValueError("size must be a non-negative number with optional B/K/M/G/T suffix")
    s = s.upper().strip()
    try:
        if s[-1:] in mult:
            amount = float(s[:-1])
            if not math.isfinite(amount) or amount < 0:
                raise ValueError
            return int(amount * mult[s[-1]])
        amount = int(s)
        if amount < 0:
            raise ValueError
        return amount
    except (ValueError, OverflowError):
        raise ValueError("size must be a non-negative number with optional B/K/M/G/T suffix") from None

def audit(root, exclude=(), min_size=0, _depth=0):
    """walk root; return (per-dir stats, total bytes, total files)."""
    stats = []
    total = 0
    count = 0
    try:
        entries = list(os.scandir(root))
    except (PermissionError, OSError):
        return stats, 0, 0
    for e in entries:
        try:
            if e.is_symlink():
                continue
            if e.is_dir(follow_symlinks=False):
                if e.name in EXCLUDE_DIRS or e.name in exclude:
                    continue
                sub, s, c = audit(e.path, exclude, min_size, _depth + 1)
                stats.extend(sub)
                total += s
                count += c
            else:
                total += e.stat().st_size
                count += 1
        except OSError:
            continue
    if _depth > 0 and total >= min_size:
        stats.append(DirStat(root, total, count))
    return stats, total, count

def render_bars(rows, width=40):
    if not rows:
        return []
    mx = max(r.size for r in rows)
    return [
        f"{format_size(r.size):>8}  {'█' * max(1, int(r.size / mx * width))}  {r.path}"
        for r in rows
    ]

def main():
    ap = argparse.ArgumentParser(prog="disk-audit", description="find what's eating your disk")
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("-n", "--top", type=int, default=15, help="show top N directories")
    ap.add_argument("--exclude", action="append", default=[], help="dir names to skip (repeatable)")
    ap.add_argument("--min-size", default="0", help="e.g. 100M, 2G")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--csv", metavar="FILE", help="write results to a csv file")
    ap.add_argument("--totals-only", action="store_true", help="skip the per-directory chart")
    a = ap.parse_args()
    if a.top < 1:
        ap.error("--top must be at least 1")

    try:
        min_bytes = parse_size(a.min_size)
    except ValueError as exc:
        ap.error(str(exc))
    stats, total, count = audit(a.path, set(a.exclude), min_bytes)
    stats.sort(key=lambda s: s.size, reverse=True)
    rows = stats[: a.top]

    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "size_bytes", "files"])
            for s in rows:
                w.writerow([s.path, s.size, s.files])
        print(f"wrote {a.csv}")

    if a.json:
        print(json.dumps({
            "total": total,
            "files": count,
            "dirs": [{"path": s.path, "size": s.size, "files": s.files} for s in rows],
        }, indent=2))
        return

    print(f"scanned {count} files · total {format_size(total)}")
    if a.totals_only:
        return
    print()
    for line in render_bars(rows):
        print(line)


if __name__ == "__main__":
    main()
