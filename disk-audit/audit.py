#!/usr/bin/env python3
"""disk-audit - find what's eating your disk. stdlib only."""

import argparse
import csv
import json
import math
import os
from dataclasses import dataclass

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


def audit(root, exclude=(), min_size=0):
    """Walk root; return (per-dir stats, total bytes, total files).

    Traverses iteratively with an explicit stack, so directory nesting deeper
    than the interpreter's recursion limit cannot crash the scan. Every
    directory aggregates the files directly inside it plus everything beneath
    it, skipping symlinks, EXCLUDE_DIRS, and the caller's exclude names.
    Unreadable subtrees contribute nothing and produce no entry.
    """
    # nodes[i] = [path, depth, subtree_size, subtree_files, parent_index]
    nodes = []
    stack = [(root, 0, -1)]
    while stack:
        path, depth, parent = stack.pop()
        index = len(nodes)
        nodes.append([path, depth, 0, 0, parent])
        try:
            entries = list(os.scandir(path))
        except OSError:
            continue  # unreadable subtree: contributes nothing, gets no entry
        for entry in entries:
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in EXCLUDE_DIRS or entry.name in exclude:
                        continue
                    stack.append((entry.path, depth + 1, index))
                else:
                    nodes[index][2] += entry.stat().st_size
                    nodes[index][3] += 1
            except OSError:
                continue
    # Children always appear after their parents in `nodes`, so one reverse
    # pass folds every subtree total into its parent directory.
    stats = []
    total = 0
    count = 0
    for i in reversed(range(len(nodes))):
        path, depth, size, files, parent = nodes[i]
        if parent >= 0:
            nodes[parent][2] += size
            nodes[parent][3] += files
        else:  # the root
            total, count = size, files
        if depth > 0 and size >= min_size:
            stats.append(DirStat(path, size, files))
    return stats, total, count


def render_bars(rows, width=40):
    if not rows:
        return []
    mx = max(r.size for r in rows) or 1
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
    if not os.path.isdir(a.path):
        ap.error(f"scan path is not a directory: {a.path}")
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
        try:
            with open(a.csv, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["path", "size_bytes", "files"])
                for s in rows:
                    w.writerow([s.path, s.size, s.files])
        except OSError as exc:
            ap.error(f"cannot write csv: {exc}")
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
