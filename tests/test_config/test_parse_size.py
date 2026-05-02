"""Tests for human-readable size string parsing."""

import unittest
from engine.config import parse_size


class TestParseSize(unittest.TestCase):

    def test_bytes(self):
        self.assertEqual(parse_size("100B"), 100)

    def test_kilobytes(self):
        self.assertEqual(parse_size("1KB"), 1024)

    def test_megabytes(self):
        self.assertEqual(parse_size("10MB"), 10 * 1024 ** 2)

    def test_gigabytes(self):
        self.assertEqual(parse_size("2GB"), 2 * 1024 ** 3)

    def test_terabytes(self):
        self.assertEqual(parse_size("1TB"), 1024 ** 4)

    def test_fractional(self):
        self.assertEqual(parse_size("1.5MB"), int(1.5 * 1024 ** 2))

    def test_case_insensitive(self):
        self.assertEqual(parse_size("10mb"), 10 * 1024 ** 2)
        self.assertEqual(parse_size("10Mb"), 10 * 1024 ** 2)

    def test_whitespace_tolerance(self):
        self.assertEqual(parse_size("  10 MB  "), 10 * 1024 ** 2)

    def test_none_returns_none(self):
        self.assertIsNone(parse_size(None))

    def test_invalid_string_raises(self):
        with self.assertRaises(ValueError):
            parse_size("ten megabytes")

    def test_missing_unit_raises(self):
        with self.assertRaises(ValueError):
            parse_size("1024")

    def test_unknown_unit_raises(self):
        with self.assertRaises(ValueError):
            parse_size("10PB")


if __name__ == "__main__":
    unittest.main()
