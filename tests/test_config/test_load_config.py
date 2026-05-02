"""Tests for config loading, default merging, and validation errors."""

import json
import unittest
from pathlib import Path

from tests.helpers import TempTree
from engine.config import load_config


class TestLoadConfigDefaults(unittest.TestCase):
    """Settings block should merge with built-in defaults."""

    def test_defaults_applied_when_settings_missing(self):
        with TempTree() as t:
            watch = t.mkdir("watch")
            cfg_path = t.root / "c.json"
            cfg_path.write_text(json.dumps({
                "rules": [{
                    "name": "r1", "watch": [str(watch)],
                    "action": {"type": "delete"},
                }]
            }))
            cfg = load_config(cfg_path)
            self.assertEqual(cfg["settings"]["log_level"], "INFO")
            self.assertEqual(cfg["settings"]["default_poll_seconds"], 2)
            self.assertFalse(cfg["settings"]["dry_run"])

    def test_user_settings_override_defaults(self):
        with TempTree() as t:
            watch = t.mkdir("watch")
            cfg_path = t.root / "c.json"
            cfg_path.write_text(json.dumps({
                "settings": {"log_level": "DEBUG", "dry_run": True},
                "rules": [{
                    "name": "r1", "watch": [str(watch)],
                    "action": {"type": "delete"},
                }]
            }))
            cfg = load_config(cfg_path)
            self.assertEqual(cfg["settings"]["log_level"], "DEBUG")
            self.assertTrue(cfg["settings"]["dry_run"])


class TestVariableResolution(unittest.TestCase):

    def test_variables_expanded_in_watch_and_destination(self):
        with TempTree() as t:
            inp = t.mkdir("input")
            cfg_path = t.root / "c.json"
            cfg_path.write_text(json.dumps({
                "variables": {"src": str(inp), "dst": str(t.root / "out")},
                "rules": [{
                    "name": "r1",
                    "watch": ["${src}"],
                    "action": {"type": "move", "destination": "${dst}"},
                }]
            }))
            cfg = load_config(cfg_path)
            self.assertEqual(cfg["rules"][0]["watch"][0], str(inp))
            self.assertEqual(cfg["rules"][0]["action"]["destination"],
                             str(t.root / "out"))

    def test_undefined_variable_raises(self):
        with TempTree() as t:
            watch = t.mkdir("watch")
            cfg_path = t.root / "c.json"
            cfg_path.write_text(json.dumps({
                "rules": [{
                    "name": "r1",
                    "watch": ["${nowhere}"],
                    "action": {"type": "delete"},
                }]
            }))
            with self.assertRaises(KeyError):
                load_config(cfg_path)


class TestValidationErrors(unittest.TestCase):

    def _write_and_load(self, t, rule):
        cfg_path = t.root / "c.json"
        cfg_path.write_text(json.dumps({"rules": [rule]}))
        return load_config(cfg_path)

    def test_missing_watch_raises(self):
        with TempTree() as t:
            with self.assertRaises(ValueError):
                self._write_and_load(t, {
                    "name": "bad", "action": {"type": "delete"}
                })

    def test_empty_watch_raises(self):
        with TempTree() as t:
            with self.assertRaises(ValueError):
                self._write_and_load(t, {
                    "name": "bad", "watch": [],
                    "action": {"type": "delete"}
                })

    def test_missing_action_raises(self):
        with TempTree() as t:
            watch = t.mkdir("w")
            with self.assertRaises(ValueError):
                self._write_and_load(t, {
                    "name": "bad", "watch": [str(watch)]
                })

    def test_unknown_action_type_raises(self):
        with TempTree() as t:
            watch = t.mkdir("w")
            with self.assertRaises(ValueError):
                self._write_and_load(t, {
                    "name": "bad", "watch": [str(watch)],
                    "action": {"type": "explode"}
                })

    def test_move_without_destination_raises(self):
        with TempTree() as t:
            watch = t.mkdir("w")
            with self.assertRaises(ValueError):
                self._write_and_load(t, {
                    "name": "bad", "watch": [str(watch)],
                    "action": {"type": "move"}
                })

    def test_rename_without_pattern_raises(self):
        with TempTree() as t:
            watch = t.mkdir("w")
            with self.assertRaises(ValueError):
                self._write_and_load(t, {
                    "name": "bad", "watch": [str(watch)],
                    "action": {"type": "rename"}
                })

    def test_compress_without_destination_raises(self):
        with TempTree() as t:
            watch = t.mkdir("w")
            with self.assertRaises(ValueError):
                self._write_and_load(t, {
                    "name": "bad", "watch": [str(watch)],
                    "action": {"type": "compress"}
                })

    def test_invalid_on_conflict_raises(self):
        with TempTree() as t:
            watch = t.mkdir("w")
            with self.assertRaises(ValueError):
                self._write_and_load(t, {
                    "name": "bad", "watch": [str(watch)],
                    "action": {"type": "move", "destination": str(t.root),
                               "on_conflict": "panic"}
                })

    def test_config_file_not_found_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_config("/nonexistent/path/config.json")

    def test_delete_action_passes_validation(self):
        """delete needs no extra fields — should pass."""
        with TempTree() as t:
            watch = t.mkdir("w")
            cfg = self._write_and_load(t, {
                "name": "ok", "watch": [str(watch)],
                "action": {"type": "delete"}
            })
            self.assertEqual(len(cfg["rules"]), 1)


if __name__ == "__main__":
    unittest.main()
