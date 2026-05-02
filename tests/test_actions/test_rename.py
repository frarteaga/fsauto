"""Tests for the rename action — template patterns and conflict handling."""

import unittest
from datetime import datetime

from tests.helpers import TempTree
from engine.actions import execute_action


class TestRenameBasic(unittest.TestCase):

    def test_rename_with_date_template(self):
        with TempTree() as t:
            f = t.create_file("input/screenshot.png", "img")
            today = datetime.now().strftime("%Y-%m-%d")
            execute_action(str(f), {
                "type": "rename",
                "pattern": "capture_{date}{ext}",
            })
            self.assertFalse(f.exists())
            self.assertTrue(t.exists(f"input/capture_{today}.png"))

    def test_rename_preserves_content(self):
        with TempTree() as t:
            f = t.create_file("input/notes.txt", "important data")
            execute_action(str(f), {
                "type": "rename",
                "pattern": "renamed_{name}{ext}",
            })
            self.assertEqual(t.read("input/renamed_notes.txt"), "important data")

    def test_rename_with_ext_name(self):
        with TempTree() as t:
            f = t.create_file("input/data.csv", "1,2,3")
            execute_action(str(f), {
                "type": "rename",
                "pattern": "{name}_backup.{ext_name}",
            })
            self.assertTrue(t.exists("input/data_backup.csv"))

    def test_rename_with_year_month_day(self):
        with TempTree() as t:
            f = t.create_file("input/log.txt", "entries")
            now = datetime.now()
            execute_action(str(f), {
                "type": "rename",
                "pattern": "{year}_{month}_{day}_{name}{ext}",
            })
            expected = f"input/{now.strftime('%Y_%m_%d')}_log.txt"
            self.assertTrue(t.exists(expected))


class TestRenameConflict(unittest.TestCase):

    def test_rename_auto_increments_on_conflict(self):
        with TempTree() as t:
            t.create_file("input/fixed_name.txt", "first")
            f = t.create_file("input/original.txt", "second")
            execute_action(str(f), {
                "type": "rename",
                "pattern": "fixed_name.txt",
            })
            self.assertTrue(t.exists("input/fixed_name.txt"))
            self.assertTrue(t.exists("input/fixed_name_1.txt"))
            self.assertEqual(t.read("input/fixed_name_1.txt"), "second")


if __name__ == "__main__":
    unittest.main()
