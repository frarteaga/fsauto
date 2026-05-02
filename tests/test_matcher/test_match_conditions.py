"""Tests for file matching — extensions, glob, regex, age, and size filters."""

import os
import unittest

from tests.helpers import TempTree
from engine.matcher import matches


class TestExtensionMatch(unittest.TestCase):

    def test_matching_extension(self):
        with TempTree() as t:
            f = t.create_file("doc.pdf", "hello")
            self.assertTrue(matches(f, {"extensions": [".pdf"]}))

    def test_non_matching_extension(self):
        with TempTree() as t:
            f = t.create_file("doc.txt", "hello")
            self.assertFalse(matches(f, {"extensions": [".pdf"]}))

    def test_case_insensitive_extension(self):
        with TempTree() as t:
            f = t.create_file("photo.JPG", "img")
            self.assertTrue(matches(f, {"extensions": [".jpg"]}))

    def test_extension_without_leading_dot(self):
        with TempTree() as t:
            f = t.create_file("doc.pdf", "hello")
            self.assertTrue(matches(f, {"extensions": ["pdf"]}))

    def test_multiple_extensions(self):
        with TempTree() as t:
            f1 = t.create_file("a.pdf", "x")
            f2 = t.create_file("b.doc", "x")
            f3 = t.create_file("c.txt", "x")
            block = {"extensions": [".pdf", ".doc"]}
            self.assertTrue(matches(f1, block))
            self.assertTrue(matches(f2, block))
            self.assertFalse(matches(f3, block))


class TestGlobMatch(unittest.TestCase):

    def test_glob_star(self):
        with TempTree() as t:
            f = t.create_file("report_2026.pdf", "x")
            self.assertTrue(matches(f, {"glob": "report_*"}))

    def test_glob_no_match(self):
        with TempTree() as t:
            f = t.create_file("photo.png", "x")
            self.assertFalse(matches(f, {"glob": "report_*"}))

    def test_glob_question_mark(self):
        with TempTree() as t:
            f = t.create_file("log1.txt", "x")
            self.assertTrue(matches(f, {"glob": "log?.txt"}))

    def test_glob_combined_with_extension(self):
        """Both glob AND extension must match (AND logic)."""
        with TempTree() as t:
            f = t.create_file("report_jan.pdf", "x")
            self.assertTrue(matches(f, {
                "extensions": [".pdf"],
                "glob": "report_*",
            }))
            # Extension matches but glob doesn't
            f2 = t.create_file("invoice.pdf", "x")
            self.assertFalse(matches(f2, {
                "extensions": [".pdf"],
                "glob": "report_*",
            }))


class TestRegexMatch(unittest.TestCase):

    def test_regex_digits(self):
        with TempTree() as t:
            f = t.create_file("data_001.csv", "x")
            self.assertTrue(matches(f, {"regex": r"^data_\d+\.csv$"}))

    def test_regex_no_match(self):
        with TempTree() as t:
            f = t.create_file("notes.csv", "x")
            self.assertFalse(matches(f, {"regex": r"^data_\d+\.csv$"}))

    def test_regex_partial_match(self):
        """re.search, not re.match — matches anywhere in the name."""
        with TempTree() as t:
            f = t.create_file("my_data_001.csv", "x")
            self.assertTrue(matches(f, {"regex": r"data_\d+"}))


class TestAgeMatch(unittest.TestCase):

    def test_older_than_passes(self):
        with TempTree() as t:
            f = t.create_old_file("old.log", age_days=10)
            self.assertTrue(matches(f, {"older_than_days": 5}))

    def test_older_than_fails(self):
        with TempTree() as t:
            f = t.create_file("new.log", "x")
            self.assertFalse(matches(f, {"older_than_days": 5}))

    def test_newer_than_passes(self):
        with TempTree() as t:
            f = t.create_file("fresh.log", "x")
            self.assertTrue(matches(f, {"newer_than_days": 1}))

    def test_newer_than_fails(self):
        with TempTree() as t:
            f = t.create_old_file("stale.log", age_days=10)
            self.assertFalse(matches(f, {"newer_than_days": 5}))

    def test_age_window(self):
        """File between 3 and 10 days old should pass both bounds."""
        with TempTree() as t:
            f = t.create_old_file("mid.log", age_days=5)
            self.assertTrue(matches(f, {
                "older_than_days": 3,
                "newer_than_days": 10,
            }))


class TestSizeMatch(unittest.TestCase):

    def test_larger_than_passes(self):
        with TempTree() as t:
            f = t.create_file("big.bin", size_bytes=2048)
            self.assertTrue(matches(f, {"larger_than": "1KB"}))

    def test_larger_than_fails(self):
        with TempTree() as t:
            f = t.create_file("small.bin", size_bytes=100)
            self.assertFalse(matches(f, {"larger_than": "1KB"}))

    def test_smaller_than_passes(self):
        with TempTree() as t:
            f = t.create_file("tiny.bin", size_bytes=100)
            self.assertTrue(matches(f, {"smaller_than": "1KB"}))

    def test_smaller_than_fails(self):
        with TempTree() as t:
            f = t.create_file("big.bin", size_bytes=2048)
            self.assertFalse(matches(f, {"smaller_than": "1KB"}))

    def test_size_range(self):
        """File between 1KB and 1MB should match both bounds."""
        with TempTree() as t:
            f = t.create_file("mid.bin", size_bytes=50_000)
            self.assertTrue(matches(f, {
                "larger_than": "1KB",
                "smaller_than": "1MB",
            }))


class TestEmptyMatch(unittest.TestCase):

    def test_none_match_block_matches_everything(self):
        with TempTree() as t:
            f = t.create_file("anything.xyz", "x")
            self.assertTrue(matches(f, None))

    def test_empty_dict_matches_everything(self):
        with TempTree() as t:
            f = t.create_file("anything.xyz", "x")
            self.assertTrue(matches(f, {}))


class TestAndLogic(unittest.TestCase):
    """All conditions must pass simultaneously."""

    def test_all_conditions_pass(self):
        with TempTree() as t:
            f = t.create_old_file("report_99.pdf", age_days=10)
            # Make it a known size
            with open(f, "wb") as fh:
                fh.write(b"x" * 5000)
            # Backdate again after rewrite
            old_time = os.path.getmtime(f) - (10 * 86400)
            os.utime(f, (old_time, old_time))

            self.assertTrue(matches(f, {
                "extensions": [".pdf"],
                "glob": "report_*",
                "regex": r"\d+",
                "older_than_days": 5,
                "larger_than": "1KB",
                "smaller_than": "1MB",
            }))

    def test_one_condition_fails_rejects(self):
        with TempTree() as t:
            f = t.create_file("report_99.pdf", "tiny")
            # Extension, glob, regex all pass — but larger_than will fail
            self.assertFalse(matches(f, {
                "extensions": [".pdf"],
                "glob": "report_*",
                "regex": r"\d+",
                "larger_than": "1MB",
            }))


if __name__ == "__main__":
    unittest.main()
