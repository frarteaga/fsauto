"""Tests for schedule expression parsing and is_due logic."""

import time
import unittest
from unittest.mock import patch
from datetime import datetime

from engine.scheduler import parse_schedule, Schedule


class TestParseScheduleInterval(unittest.TestCase):

    def test_every_seconds(self):
        s = parse_schedule("every 2s")
        self.assertEqual(s.kind, "interval")
        self.assertEqual(s.interval_sec, 2)

    def test_every_minutes(self):
        s = parse_schedule("every 5m")
        self.assertEqual(s.kind, "interval")
        self.assertEqual(s.interval_sec, 300)

    def test_every_hours(self):
        s = parse_schedule("every 1h")
        self.assertEqual(s.kind, "interval")
        self.assertEqual(s.interval_sec, 3600)

    def test_case_insensitive(self):
        s = parse_schedule("Every 10S")
        self.assertEqual(s.interval_sec, 10)

    def test_none_defaults_to_zero_interval(self):
        s = parse_schedule(None)
        self.assertEqual(s.kind, "interval")
        self.assertEqual(s.interval_sec, 0)


class TestParseScheduleDaily(unittest.TestCase):

    def test_daily(self):
        s = parse_schedule("daily 09:00")
        self.assertEqual(s.kind, "daily")
        self.assertEqual(s.hour, 9)
        self.assertEqual(s.minute, 0)

    def test_daily_afternoon(self):
        s = parse_schedule("daily 14:30")
        self.assertEqual(s.hour, 14)
        self.assertEqual(s.minute, 30)


class TestParseScheduleWeekly(unittest.TestCase):

    def test_weekly_monday(self):
        s = parse_schedule("weekly monday 08:00")
        self.assertEqual(s.kind, "weekly")
        self.assertEqual(s.weekday, 0)
        self.assertEqual(s.hour, 8)

    def test_weekly_sunday(self):
        s = parse_schedule("weekly sunday 23:59")
        self.assertEqual(s.weekday, 6)
        self.assertEqual(s.hour, 23)
        self.assertEqual(s.minute, 59)

    def test_weekly_case_insensitive(self):
        s = parse_schedule("Weekly FRIDAY 12:00")
        self.assertEqual(s.weekday, 4)


class TestParseScheduleInvalid(unittest.TestCase):

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            parse_schedule("whenever I feel like it")

    def test_missing_unit_raises(self):
        with self.assertRaises(ValueError):
            parse_schedule("every 10")

    def test_bad_day_raises(self):
        with self.assertRaises(ValueError):
            parse_schedule("weekly funday 09:00")


class TestIsDueInterval(unittest.TestCase):

    def test_first_run_always_due(self):
        s = parse_schedule("every 10s")
        self.assertTrue(s.is_due(None))

    def test_due_after_interval(self):
        s = parse_schedule("every 2s")
        past = time.time() - 3
        self.assertTrue(s.is_due(past))

    def test_not_due_before_interval(self):
        s = parse_schedule("every 10s")
        recent = time.time() - 1
        self.assertFalse(s.is_due(recent))

    def test_zero_interval_always_due(self):
        s = parse_schedule(None)  # interval_sec=0
        self.assertTrue(s.is_due(time.time()))


class TestIsDueDaily(unittest.TestCase):

    def test_daily_fires_at_matching_time(self):
        now = datetime.now()
        s = parse_schedule(f"daily {now.hour}:{now.minute:02d}")
        self.assertTrue(s.is_due(None))

    def test_daily_does_not_fire_twice(self):
        now = datetime.now()
        s = parse_schedule(f"daily {now.hour}:{now.minute:02d}")
        self.assertTrue(s.is_due(None))  # fires once
        self.assertFalse(s.is_due(None))  # blocked — already fired today

    def test_daily_does_not_fire_at_wrong_time(self):
        # Use a time that definitely isn't now
        fake_hour = (datetime.now().hour + 6) % 24
        s = parse_schedule(f"daily {fake_hour}:00")
        self.assertFalse(s.is_due(None))


class TestIsDueWeekly(unittest.TestCase):

    def test_weekly_fires_on_matching_day_and_time(self):
        now = datetime.now()
        day_names = ["monday", "tuesday", "wednesday", "thursday",
                     "friday", "saturday", "sunday"]
        today_name = day_names[now.weekday()]
        s = parse_schedule(f"weekly {today_name} {now.hour}:{now.minute:02d}")
        self.assertTrue(s.is_due(None))

    def test_weekly_does_not_fire_on_wrong_day(self):
        now = datetime.now()
        day_names = ["monday", "tuesday", "wednesday", "thursday",
                     "friday", "saturday", "sunday"]
        # Pick a day that isn't today
        other_day = day_names[(now.weekday() + 3) % 7]
        s = parse_schedule(f"weekly {other_day} {now.hour}:{now.minute:02d}")
        self.assertFalse(s.is_due(None))


if __name__ == "__main__":
    unittest.main()
