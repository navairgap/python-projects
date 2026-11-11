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
    if not STORE.exists():
        return []

    try:
        items = json.loads(STORE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("todo store is not readable valid JSON") from exc
    if not isinstance(items, list):
        raise ValueError("todo store must contain a JSON array")

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"todo item #{index} must be an object")
        if not isinstance(item.get("task"), str) or not item["task"].strip():
            raise ValueError(f"todo item #{index} must have non-empty task text")
        if not isinstance(item.get("done"), bool):
            raise ValueError(f"todo item #{index} must have a boolean done field")
        item.setdefault("created", "")
        if not isinstance(item["created"], str):
            raise ValueError(f"todo item #{index} must have a string created field")
        item.setdefault("priority", "normal")
        if item["priority"] not in ("high", "normal", "low"):
            raise ValueError(f"todo item #{index} has an invalid priority")
    return items


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
    if not isinstance(text, str) or not text.strip():
        raise ValueError("task text must be a non-empty string")
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
        line = f"[{mark}] {n:>2}  {it['task']}"
        if it["created"]:
            line += f"  ({it['created']})"
        if it["priority"] != "normal":
            line += f"  [{it['priority']}]"
        print(line)
    if not rows:
        print("nothing here. enjoy it or add something.")


def _item(items, n):
    """Return a 1-based item or reject invalid indexes."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1 or n > len(items):
        raise IndexError(f"no item #{n}")
    return items[n - 1]


def done(n, value=True):
    if not isinstance(value, bool):
        raise ValueError("done state must be a boolean")
    items = load()
    _item(items, n)["done"] = value
    save(items)


def pri(n, value):
    if value not in ("high", "normal", "low"):
        raise ValueError("priority must be high, normal, or low")
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
        except (OSError, ValueError) as e:
            ap.error(str(e))
    elif a.cmd == "ls":
        try:
            ls(a.all)
        except (OSError, ValueError) as e:
            ap.error(str(e))
    elif a.cmd in ("done", "undone"):
        try:
            done(a.n, a.cmd == "done")
        except IndexError as e:
            sys.exit(str(e))
        except (OSError, ValueError) as e:
            ap.error(str(e))
    elif a.cmd == "pri":
        try:
            pri(a.n, a.priority)
        except IndexError as e:
            sys.exit(str(e))
        except (OSError, ValueError) as e:
            ap.error(str(e))
    elif a.cmd == "stats":
        try:
            total, done_count = stats()
        except (OSError, ValueError) as e:
            ap.error(str(e))
        print(f"{done_count}/{total} done")
    elif a.cmd == "rm":
        try:
            print(f"removed: {rm(a.n)}")
        except IndexError as e:
            sys.exit(str(e))
        except (OSError, ValueError) as e:
            ap.error(str(e))


if __name__ == "__main__":
    main()
