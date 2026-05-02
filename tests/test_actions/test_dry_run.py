"""Tests for dry-run mode — every action type should log but not touch files."""

import unittest

from tests.helpers import TempTree
from engine.actions import execute_action


class TestDryRunMove(unittest.TestCase):

    def test_dry_run_move_does_not_move(self):
        with TempTree() as t:
            f = t.create_file("input/doc.pdf", "original")
            dest = t.mkdir("output")
            result = execute_action(str(f), {
                "type": "move", "destination": str(dest),
            }, dry_run=True)
            self.assertIn("[DRY-RUN]", result)
            self.assertIn("MOVE", result)
            self.assertTrue(f.exists())
            self.assertFalse((dest / "doc.pdf").exists())


class TestDryRunRename(unittest.TestCase):

    def test_dry_run_rename_does_not_rename(self):
        with TempTree() as t:
            f = t.create_file("input/old.txt", "data")
            result = execute_action(str(f), {
                "type": "rename", "pattern": "new.txt",
            }, dry_run=True)
            self.assertIn("[DRY-RUN]", result)
            self.assertIn("RENAME", result)
            self.assertTrue(f.exists())
            self.assertFalse(t.exists("input/new.txt"))


class TestDryRunDelete(unittest.TestCase):

    def test_dry_run_delete_does_not_delete(self):
        with TempTree() as t:
            f = t.create_file("input/keep.tmp", "safe")
            result = execute_action(str(f), {
                "type": "delete",
            }, dry_run=True)
            self.assertIn("[DRY-RUN]", result)
            self.assertIn("DELETE", result)
            self.assertTrue(f.exists())


class TestDryRunCompress(unittest.TestCase):

    def test_dry_run_compress_zip_does_not_compress(self):
        with TempTree() as t:
            f = t.create_file("input/data.log", "entries")
            dest = t.mkdir("archive")
            result = execute_action(str(f), {
                "type": "compress", "destination": str(dest), "format": "zip",
            }, dry_run=True)
            self.assertIn("[DRY-RUN]", result)
            self.assertIn("COMPRESS", result)
            self.assertTrue(f.exists())
            self.assertFalse((dest / "data.zip").exists())

    def test_dry_run_compress_gzip_does_not_compress(self):
        with TempTree() as t:
            f = t.create_file("input/data.log", "entries")
            dest = t.mkdir("archive")
            result = execute_action(str(f), {
                "type": "compress", "destination": str(dest), "format": "gzip",
            }, dry_run=True)
            self.assertIn("[DRY-RUN]", result)
            self.assertTrue(f.exists())


if __name__ == "__main__":
    unittest.main()
