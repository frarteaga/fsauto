"""Tests for the move action — basic move, templated dest, and all conflict modes."""

import unittest

from tests.helpers import TempTree
from engine.actions import execute_action


class TestMoveBasic(unittest.TestCase):

    def test_move_to_new_directory(self):
        with TempTree() as t:
            f = t.create_file("input/doc.pdf", "hello")
            dest = t.mkdir("output")
            execute_action(str(f), {
                "type": "move", "destination": str(dest),
            })
            self.assertFalse(f.exists())
            self.assertTrue((dest / "doc.pdf").exists())
            self.assertEqual((dest / "doc.pdf").read_text(), "hello")

    def test_move_creates_destination_directory(self):
        with TempTree() as t:
            f = t.create_file("input/doc.pdf", "data")
            dest = t.root / "nonexistent" / "deep" / "path"
            execute_action(str(f), {
                "type": "move", "destination": str(dest),
            })
            self.assertTrue((dest / "doc.pdf").exists())

    def test_move_with_template_destination(self):
        with TempTree() as t:
            f = t.create_file("input/report.pdf", "content")
            dest = str(t.root / "sorted" / "{ext_name}")
            execute_action(str(f), {
                "type": "move", "destination": dest,
            })
            self.assertTrue(t.exists("sorted/pdf/report.pdf"))


class TestMoveConflictRename(unittest.TestCase):

    def test_rename_appends_suffix(self):
        with TempTree() as t:
            t.create_file("output/doc.pdf", "original")
            f = t.create_file("input/doc.pdf", "new copy")
            execute_action(str(f), {
                "type": "move",
                "destination": str(t.root / "output"),
                "on_conflict": "rename",
            })
            self.assertTrue(t.exists("output/doc.pdf"))
            self.assertTrue(t.exists("output/doc_1.pdf"))
            self.assertEqual(t.read("output/doc.pdf"), "original")
            self.assertEqual(t.read("output/doc_1.pdf"), "new copy")

    def test_rename_increments_past_existing(self):
        with TempTree() as t:
            t.create_file("output/doc.pdf", "v0")
            t.create_file("output/doc_1.pdf", "v1")
            f = t.create_file("input/doc.pdf", "v2")
            execute_action(str(f), {
                "type": "move",
                "destination": str(t.root / "output"),
                "on_conflict": "rename",
            })
            self.assertTrue(t.exists("output/doc_2.pdf"))


class TestMoveConflictSkip(unittest.TestCase):

    def test_skip_leaves_original_and_source(self):
        with TempTree() as t:
            t.create_file("output/doc.pdf", "original")
            f = t.create_file("input/doc.pdf", "should stay")
            result = execute_action(str(f), {
                "type": "move",
                "destination": str(t.root / "output"),
                "on_conflict": "skip",
            })
            self.assertIn("SKIP", result)
            # Source file remains because it was skipped
            self.assertTrue(f.exists())
            self.assertEqual(t.read("output/doc.pdf"), "original")


class TestMoveConflictOverwrite(unittest.TestCase):

    def test_overwrite_replaces_existing(self):
        with TempTree() as t:
            t.create_file("output/doc.pdf", "old")
            f = t.create_file("input/doc.pdf", "new")
            execute_action(str(f), {
                "type": "move",
                "destination": str(t.root / "output"),
                "on_conflict": "overwrite",
            })
            self.assertEqual(t.read("output/doc.pdf"), "new")
            self.assertFalse(f.exists())


if __name__ == "__main__":
    unittest.main()
