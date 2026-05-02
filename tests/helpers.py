"""
helpers.py — Shared utilities for all integration tests.

Provides temp directory management, file creation, and config builders
so each test module stays focused on assertions.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path


class TempTree:
    """Context manager that creates an isolated temp directory tree and cleans
    it up on exit.  Provides helpers to create files, write configs, and
    inspect results."""

    def __init__(self):
        self.root = None

    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="fileauto_test_"))
        return self

    def __exit__(self, *exc):
        if self.root and self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)

    # ── Directory helpers ───────────────────────────────────────────────

    def mkdir(self, *parts):
        """Create a subdirectory under root and return its Path."""
        d = self.root.joinpath(*parts)
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── File helpers ────────────────────────────────────────────────────

    def create_file(self, relpath, content="", size_bytes=None):
        """Create a file at *relpath* (relative to root).  If *size_bytes*
        is given, write exactly that many null bytes instead of *content*."""
        p = self.root / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        if size_bytes is not None:
            with open(p, "wb") as f:
                f.write(b"\x00" * size_bytes)
        else:
            p.write_text(content, encoding="utf-8")
        return p

    def create_old_file(self, relpath, age_days, content="old"):
        """Create a file and backdate its mtime by *age_days*."""
        p = self.create_file(relpath, content)
        old_time = os.path.getmtime(p) - (age_days * 86400)
        os.utime(p, (old_time, old_time))
        return p

    def exists(self, relpath):
        return (self.root / relpath).exists()

    def read(self, relpath):
        return (self.root / relpath).read_text(encoding="utf-8")

    def listdir(self, relpath=""):
        d = self.root / relpath
        if not d.is_dir():
            return []
        return sorted(os.listdir(d))

    # ── Config builder ──────────────────────────────────────────────────

    def write_config(self, rules, settings=None, variables=None):
        """Write a JSON config file and return its path."""
        cfg = {
            "settings": {
                "log_file": str(self.root / "test.log"),
                "log_level": "DEBUG",
                "dry_run": False,
                "default_poll_seconds": 1,
                **(settings or {}),
            },
            "variables": variables or {},
            "rules": rules,
        }
        p = self.root / "test_config.json"
        p.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        return p
