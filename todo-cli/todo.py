#!/usr/bin/env python3
"""todo-cli - a json-backed todo list. stdlib only."""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STORE = Path(__file__).with_name("todo.json")


def load():
    if STORE.exists():
        items = json.loads(STORE.read_text(encoding="utf-8"))
        for it in items:
            it.setdefault("priority", "normal")
        return items
    return []


def save(items):
    """Persist tasks atomically so an interrupted write cannot truncate the store."""
    payload = json.dumps(items, indent=2) + "\n"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{STORE.name}.",
            suffix=".tmp",
            dir=STORE.parent,
            delete=False,
        ) as temp:
            temp_path = temp.name
            temp.write(payload)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp_path, STORE)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass


def add(text):
    if not text or not text.strip():
        raise ValueError("task text cannot be empty")
    items = load()
    items.append({"task": text, "done": False,
                  "created": datetime.now(timezone.utc).isoformat()[:16]})
    save(items)
    return len(items)


def ls(show_all=False):
    items = load()
    rows = [(i + 1, it) for i, it in enumerate(items) if show_all or not it["done"]]
    for n, it in rows:
        mark = "x" if it["done"] else " "
        print(f"[{mark}] {n:>2}  {it['task']}  ({it['created']})")
    if not rows:
        print("nothing here. enjoy it or add something.")


def _item(items, n):
    """Return a 1-based item or reject invalid CLI indexes."""
    if n < 1 or n > len(items):
        raise IndexError(f"no item #{n}")
    return items[n - 1]


def done(n, value=True):
    items = load()
    _item(items, n)["done"] = value
    save(items)


def pri(n, value):
    items = load()
    _item(items, n)["priority"] = value
    save(items)


def stats():
    items = load()
    done = sum(1 for it in items if it["done"])
    return len(items), done


def rm(n):
    items = load()
    removed = _item(items, n)
    items.pop(n - 1)
    save(items)
    return removed["task"]


def main():
    ap = argparse.ArgumentParser(prog="todo")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add")
    p_add.add_argument("text")
    p_ls = sub.add_parser("ls")
    p_ls.add_argument("-a", "--all", action="store_true")
    for name in ("done", "undone", "rm"):
        sub.add_parser(name).add_argument("n", type=int)
    sub.add_parser("stats")
    p_pri = sub.add_parser("pri")
    p_pri.add_argument("n", type=int)
    p_pri.add_argument("priority", choices=["high", "normal", "low"])
    a = ap.parse_args()

    if a.cmd == "add":
        try:
            print(f"added #{add(a.text)}")
        except ValueError as e:
            ap.error(str(e))
    elif a.cmd == "ls":
        ls(a.all)
    elif a.cmd in ("done", "undone"):
        try:
            done(a.n, a.cmd == "done")
        except IndexError:
            sys.exit(f"no item #{a.n}")
    elif a.cmd == "pri":
        try:
            pri(a.n, a.priority)
        except IndexError:
            sys.exit(f"no item #{a.n}")
    elif a.cmd == "stats":
        total, done = stats()
        print(f"{done}/{total} done")
    elif a.cmd == "rm":
        try:
            print(f"removed: {rm(a.n)}")
        except IndexError:
            sys.exit(f"no item #{a.n}")


if __name__ == "__main__":
    main()
