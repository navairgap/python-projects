import json
import tempfile
import unittest
from pathlib import Path

import todo


class TestTodo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Path(self.tmp.name) / "todo.json"
        self.old = todo.STORE
        todo.STORE = self.store
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(setattr, todo, "STORE", self.old)

    def test_add_and_list(self):
        todo.add("write tests")
        todo.add("ship it")
        self.assertEqual(len(todo.load()), 2)
        self.assertFalse(todo.load()[0]["done"])

    def test_list_hides_completed_items_unless_all_requested(self):
        from unittest.mock import patch

        todo.add("completed task")
        todo.add("open task")
        todo.done(1)

        with patch("builtins.print") as printer:
            todo.ls()
        open_output = "\\n".join(str(call.args[0]) for call in printer.call_args_list)
        self.assertIn("open task", open_output)
        self.assertNotIn("completed task", open_output)

        with patch("builtins.print") as printer:
            todo.ls(show_all=True)
        all_output = "\\n".join(str(call.args[0]) for call in printer.call_args_list)
        self.assertIn("open task", all_output)
        self.assertIn("completed task", all_output)

    def test_blank_task_rejected(self):
        for value in ("", "   ", "\t"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    todo.add(value)

    def test_done_and_undone(self):
        todo.add("a")
        todo.done(1)
        self.assertTrue(todo.load()[0]["done"])
        todo.done(1, False)
        self.assertFalse(todo.load()[0]["done"])

    def test_rm(self):
        todo.add("keep")
        todo.add("drop")
        self.assertEqual(todo.rm(2), "drop")
        self.assertEqual(len(todo.load()), 1)

    def test_persistence_format(self):
        todo.add("persist me")
        data = json.loads(self.store.read_text())
        self.assertEqual(data[0]["task"], "persist me")
        self.assertIn("created", data[0])

    def test_unicode_task_round_trips(self):
        task = "नमस्ते 👋 café"
        todo.add(task)
        self.assertEqual(todo.load()[0]["task"], task)

    def test_failed_atomic_replace_preserves_existing_store(self):
        from unittest.mock import patch

        todo.add("existing task")
        original = self.store.read_text()

        with patch("todo.os.replace", side_effect=OSError("replace failed")):
            with self.assertRaises(OSError):
                todo.add("new task")

        self.assertEqual(self.store.read_text(), original)
        self.assertEqual([p.name for p in self.store.parent.iterdir()], ["todo.json"])

    def test_stats(self):
        todo.add("a")
        todo.add("b")
        todo.done(1)
        total, done = todo.stats()
        self.assertEqual((total, done), (2, 1))

    def test_rm_out_of_range(self):
        with self.assertRaises(IndexError):
            todo.rm(7)

    def test_invalid_item_numbers(self):
        todo.add("sample")
        for number in (0, -1, 2):
            for operation in (
                lambda n=number: todo.done(n),
                lambda n=number: todo.pri(n, "high"),
                lambda n=number: todo.rm(n),
            ):
                with self.subTest(number=number, operation=operation):
                    with self.assertRaises(IndexError):
                        operation()


if __name__ == "__main__":
    unittest.main()


class TestPriorityField(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Path(self.tmp.name) / "todo.json"
        self.old = todo.STORE
        todo.STORE = self.store
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(setattr, todo, "STORE", self.old)

    def test_legacy_items_backfilled(self):
        import json as _json
        self.store.write_text(_json.dumps([{"task": "old", "done": False}]))
        self.assertEqual(todo.load()[0]["priority"], "normal")

    def test_new_items_have_priority(self):
        todo.add("check field")
        self.assertEqual(todo.load()[0].get("priority"), "normal")

    def test_priority_updates_persist_across_reload(self):
        todo.add("prioritize")
        todo.pri(1, "high")
        self.assertEqual(todo.load()[0]["priority"], "high")
        todo.pri(1, "low")
        self.assertEqual(todo.load()[0]["priority"], "low")


if __name__ == "__main__":
    unittest.main()
