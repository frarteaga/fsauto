"""Tests for the compress action — zip and gzip formats, conflict modes."""

import gzip
import unittest
import zipfile

from tests.helpers import TempTree
from engine.actions import execute_action


class TestCompressZip(unittest.TestCase):

    def test_zip_creates_archive_and_removes_original(self):
        with TempTree() as t:
            f = t.create_file("input/data.log", "log content here")
            dest = t.mkdir("archive")
            execute_action(str(f), {
                "type": "compress",
                "destination": str(dest),
                "format": "zip",
            })
            self.assertFalse(f.exists())
            zip_path = dest / "data.zip"
            self.assertTrue(zip_path.exists())
            with zipfile.ZipFile(zip_path) as zf:
                self.assertIn("data.log", zf.namelist())
                self.assertEqual(zf.read("data.log").decode(), "log content here")

    def test_zip_default_format(self):
        """If format is omitted, default to zip."""
        with TempTree() as t:
            f = t.create_file("input/info.log", "content")
            dest = t.mkdir("archive")
            execute_action(str(f), {
                "type": "compress",
                "destination": str(dest),
            })
            self.assertTrue((dest / "info.zip").exists())

    def test_zip_creates_destination_dirs(self):
        with TempTree() as t:
            f = t.create_file("input/deep.log", "x")
            dest = str(t.root / "a" / "b" / "c")
            execute_action(str(f), {
                "type": "compress", "destination": dest, "format": "zip",
            })
            self.assertTrue(t.exists("a/b/c/deep.zip"))

    def test_zip_with_template_destination(self):
        with TempTree() as t:
            f = t.create_file("input/app.log", "entries")
            dest = str(t.root / "archive" / "{year}" / "{month}")
            execute_action(str(f), {
                "type": "compress", "destination": dest, "format": "zip",
            })
            # We just check that some year/month directory was created
            from datetime import datetime
            now = datetime.now()
            expected = f"archive/{now.strftime('%Y')}/{now.strftime('%m')}/app.zip"
            self.assertTrue(t.exists(expected))


class TestCompressGzip(unittest.TestCase):

    def test_gzip_creates_gz_and_removes_original(self):
        with TempTree() as t:
            f = t.create_file("input/data.log", "gzip me")
            dest = t.mkdir("archive")
            execute_action(str(f), {
                "type": "compress",
                "destination": str(dest),
                "format": "gzip",
            })
            self.assertFalse(f.exists())
            gz_path = dest / "data.log.gz"
            self.assertTrue(gz_path.exists())
            with gzip.open(gz_path, "rt") as gz:
                self.assertEqual(gz.read(), "gzip me")


class TestCompressConflict(unittest.TestCase):

    def test_zip_rename_on_conflict(self):
        with TempTree() as t:
            dest = t.mkdir("archive")
            t.create_file("archive/data.zip", "existing")
            f = t.create_file("input/data.log", "new content")
            execute_action(str(f), {
                "type": "compress",
                "destination": str(dest),
                "format": "zip",
                "on_conflict": "rename",
            })
            self.assertTrue(t.exists("archive/data.zip"))
            self.assertTrue(t.exists("archive/data_1.zip"))

    def test_zip_skip_on_conflict(self):
        with TempTree() as t:
            dest = t.mkdir("archive")
            t.create_file("archive/data.zip", "existing")
            f = t.create_file("input/data.log", "skippable")
            result = execute_action(str(f), {
                "type": "compress",
                "destination": str(dest),
                "format": "zip",
                "on_conflict": "skip",
            })
            self.assertIn("SKIP", result)
            # Original should still exist because skip means no action
            self.assertTrue(f.exists())


class TestCompressUnsupported(unittest.TestCase):

    def test_unsupported_format_raises(self):
        with TempTree() as t:
            f = t.create_file("input/data.log", "x")
            dest = t.mkdir("archive")
            with self.assertRaises(ValueError):
                execute_action(str(f), {
                    "type": "compress",
                    "destination": str(dest),
                    "format": "rar",
                })


if __name__ == "__main__":
    unittest.main()
