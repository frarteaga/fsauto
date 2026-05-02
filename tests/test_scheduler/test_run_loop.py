"""Tests for run_loop — full integration from config dict through file changes."""

import json
import unittest

from tests.helpers import TempTree
from engine.config import load_config
from engine.scheduler import run_loop


class TestRunLoopSinglePass(unittest.TestCase):
    """Use once=True to run a single pass and verify results."""

    def test_move_rule_via_loop(self):
        with TempTree() as t:
            inp = t.mkdir("input")
            out = t.mkdir("output")
            t.create_file("input/doc.pdf", "content")
            cfg = t.write_config([{
                "name": "move pdfs",
                "watch": [str(inp)],
                "schedule": "every 1s",
                "match": {"extensions": [".pdf"]},
                "action": {"type": "move", "destination": str(out)},
            }])
            config = load_config(cfg)
            run_loop(config, once=True)
            self.assertTrue(t.exists("output/doc.pdf"))
            self.assertFalse(t.exists("input/doc.pdf"))

    def test_delete_rule_via_loop(self):
        with TempTree() as t:
            inp = t.mkdir("input")
            t.create_file("input/junk.tmp", "x")
            cfg = t.write_config([{
                "name": "delete tmp",
                "watch": [str(inp)],
                "schedule": "every 1s",
                "match": {"extensions": [".tmp"]},
                "action": {"type": "delete"},
            }])
            config = load_config(cfg)
            run_loop(config, once=True)
            self.assertFalse(t.exists("input/junk.tmp"))

    def test_disabled_rule_skipped(self):
        with TempTree() as t:
            inp = t.mkdir("input")
            t.create_file("input/keep.tmp", "x")
            cfg = t.write_config([{
                "name": "disabled",
                "enabled": False,
                "watch": [str(inp)],
                "schedule": "every 1s",
                "match": {"extensions": [".tmp"]},
                "action": {"type": "delete"},
            }])
            config = load_config(cfg)
            run_loop(config, once=True)
            # File should still exist because the rule is disabled
            self.assertTrue(t.exists("input/keep.tmp"))

    def test_dry_run_via_settings(self):
        with TempTree() as t:
            inp = t.mkdir("input")
            t.create_file("input/safe.tmp", "x")
            cfg = t.write_config(
                [{
                    "name": "dry delete",
                    "watch": [str(inp)],
                    "schedule": "every 1s",
                    "match": {"extensions": [".tmp"]},
                    "action": {"type": "delete"},
                }],
                settings={"dry_run": True},
            )
            config = load_config(cfg)
            run_loop(config, once=True)
            self.assertTrue(t.exists("input/safe.tmp"))


class TestRunLoopMultiRule(unittest.TestCase):
    """Multiple rules operating on the same watched folder in one pass."""

    def test_two_rules_different_extensions(self):
        with TempTree() as t:
            inp = t.mkdir("input")
            pdf_out = t.mkdir("pdfs")
            img_out = t.mkdir("images")
            t.create_file("input/report.pdf", "pdf")
            t.create_file("input/photo.png", "img")
            t.create_file("input/readme.txt", "keep")  # unmatched
            cfg = t.write_config([
                {
                    "name": "move pdfs",
                    "watch": [str(inp)],
                    "schedule": "every 1s",
                    "match": {"extensions": [".pdf"]},
                    "action": {"type": "move", "destination": str(pdf_out)},
                },
                {
                    "name": "move images",
                    "watch": [str(inp)],
                    "schedule": "every 1s",
                    "match": {"extensions": [".png"]},
                    "action": {"type": "move", "destination": str(img_out)},
                },
            ])
            config = load_config(cfg)
            run_loop(config, once=True)
            self.assertTrue(t.exists("pdfs/report.pdf"))
            self.assertTrue(t.exists("images/photo.png"))
            self.assertTrue(t.exists("input/readme.txt"))  # untouched

    def test_no_enabled_rules_exits_gracefully(self):
        with TempTree() as t:
            inp = t.mkdir("input")
            cfg = t.write_config([{
                "name": "off",
                "enabled": False,
                "watch": [str(inp)],
                "action": {"type": "delete"},
            }])
            config = load_config(cfg)
            # Should return without error
            run_loop(config, once=True)


class TestRunLoopVariables(unittest.TestCase):
    """Variable substitution flows through to the loop correctly."""

    def test_variables_in_watch_and_destination(self):
        with TempTree() as t:
            inp = t.mkdir("source")
            t.create_file("source/file.pdf", "data")
            cfg_path = t.root / "cfg.json"
            cfg_path.write_text(json.dumps({
                "settings": {
                    "log_file": str(t.root / "t.log"),
                    "dry_run": False,
                    "default_poll_seconds": 1,
                },
                "variables": {
                    "src": str(inp),
                    "dst": str(t.root / "dest"),
                },
                "rules": [{
                    "name": "var test",
                    "watch": ["${src}"],
                    "schedule": "every 1s",
                    "match": {"extensions": [".pdf"]},
                    "action": {"type": "move", "destination": "${dst}"},
                }],
            }))
            config = load_config(cfg_path)
            run_loop(config, once=True)
            self.assertTrue(t.exists("dest/file.pdf"))


class TestRunLoopErrorIsolation(unittest.TestCase):
    """An error in one rule must not prevent other rules from running."""

    def test_bad_rule_does_not_block_good_rule(self):
        with TempTree() as t:
            inp = t.mkdir("input")
            out = t.mkdir("output")
            t.create_file("input/good.pdf", "content")
            t.create_file("input/bad.log", "data")
            cfg = t.write_config([
                {
                    "name": "broken rule",
                    "watch": [str(inp)],
                    "schedule": "every 1s",
                    "match": {"extensions": [".log"]},
                    "action": {
                        "type": "compress",
                        "destination": str(out),
                        "format": "zip",
                    },
                },
                {
                    "name": "good rule",
                    "watch": [str(inp)],
                    "schedule": "every 1s",
                    "match": {"extensions": [".pdf"]},
                    "action": {"type": "move", "destination": str(out)},
                },
            ])
            config = load_config(cfg)
            # Even if compress has issues, the move rule should still work
            run_loop(config, once=True)
            self.assertTrue(t.exists("output/good.pdf"))


if __name__ == "__main__":
    unittest.main()
