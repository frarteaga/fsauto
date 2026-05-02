"""Tests for template variable expansion in action destinations and patterns."""

import unittest
from datetime import datetime

from tests.helpers import TempTree
from engine.actions import expand_template, _counters


class TestExpandTemplate(unittest.TestCase):

    def setUp(self):
        # Reset the global counter between tests for predictability
        _counters.clear()

    def test_name_and_ext(self):
        with TempTree() as t:
            f = t.create_file("input/report.pdf", "x")
            result = expand_template("{name}_{ext}", str(f))
            self.assertEqual(result, "report_.pdf")

    def test_ext_name_without_dot(self):
        with TempTree() as t:
            f = t.create_file("input/report.pdf", "x")
            result = expand_template("{ext_name}", str(f))
            self.assertEqual(result, "pdf")

    def test_date_format(self):
        with TempTree() as t:
            f = t.create_file("input/file.txt", "x")
            result = expand_template("{date}", str(f))
            self.assertEqual(result, datetime.now().strftime("%Y-%m-%d"))

    def test_time_format(self):
        with TempTree() as t:
            f = t.create_file("input/file.txt", "x")
            result = expand_template("{time}", str(f))
            # Just verify it's 6 digits (HHMMSS)
            self.assertRegex(result, r"^\d{6}$")

    def test_year_month_day(self):
        with TempTree() as t:
            f = t.create_file("input/file.txt", "x")
            now = datetime.now()
            self.assertEqual(expand_template("{year}", str(f)), now.strftime("%Y"))
            self.assertEqual(expand_template("{month}", str(f)), now.strftime("%m"))
            self.assertEqual(expand_template("{day}", str(f)), now.strftime("%d"))

    def test_counter_increments(self):
        with TempTree() as t:
            f = t.create_file("input/a.txt", "x")
            r1 = expand_template("{counter}", str(f))
            r2 = expand_template("{counter}", str(f))
            self.assertEqual(r1, "1")
            self.assertEqual(r2, "2")

    def test_size_mb(self):
        with TempTree() as t:
            # 1 MB file
            f = t.create_file("input/big.bin", size_bytes=1024 * 1024)
            result = expand_template("{size_mb}", str(f))
            self.assertEqual(result, "1.0")

    def test_size_mb_small_file(self):
        with TempTree() as t:
            f = t.create_file("input/tiny.txt", "hi")
            result = expand_template("{size_mb}", str(f))
            self.assertEqual(result, "0.0")

    def test_multiple_variables_combined(self):
        with TempTree() as t:
            f = t.create_file("input/photo.jpg", "img")
            now = datetime.now()
            result = expand_template(
                "{name}_{date}_{counter}.{ext_name}", str(f)
            )
            expected = f"photo_{now.strftime('%Y-%m-%d')}_1.jpg"
            self.assertEqual(result, expected)

    def test_no_variables_passthrough(self):
        with TempTree() as t:
            f = t.create_file("input/file.txt", "x")
            result = expand_template("static_name.txt", str(f))
            self.assertEqual(result, "static_name.txt")


if __name__ == "__main__":
    unittest.main()
