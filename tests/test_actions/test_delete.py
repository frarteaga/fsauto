"""Tests for the delete action."""

import unittest

from tests.helpers import TempTree
from engine.actions import execute_action


class TestDeleteBasic(unittest.TestCase):

    def test_delete_removes_file(self):
        with TempTree() as t:
            f = t.create_file("input/trash.tmp", "garbage")
            self.assertTrue(f.exists())
            result = execute_action(str(f), {"type": "delete"})
            self.assertFalse(f.exists())
            self.assertIn("DELETE", result)

    def test_delete_nonexistent_raises(self):
        with TempTree() as t:
            fake = t.root / "nope.txt"
            with self.assertRaises(OSError):
                execute_action(str(fake), {"type": "delete"})

    def test_delete_multiple_files(self):
        with TempTree() as t:
            files = []
            for i in range(5):
                files.append(t.create_file(f"input/tmp_{i}.bak", f"data{i}"))
            for f in files:
                execute_action(str(f), {"type": "delete"})
            for f in files:
                self.assertFalse(f.exists())


if __name__ == "__main__":
    unittest.main()
