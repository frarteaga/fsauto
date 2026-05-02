"""
scheduler.py — Parse schedule expressions and run the main polling loop.

Schedule format (simple, no external dependencies):

  "every 2s"              — run every 2 seconds
  "every 5m"              — run every 5 minutes
  "every 1h"              — run every 1 hour
  "daily 09:00"           — run once a day at 09:00
  "weekly monday 09:00"   — run once a week on Monday at 09:00

The main loop sleeps in 1-second ticks so that interval-based rules can fire
as frequently as every 1 s.
"""

import logging
import os
import time
from datetime import datetime
from pathlib import Path
import re as _re

from engine.matcher import matches
from engine.actions import execute_action

logger = logging.getLogger("automation.scheduler")

# ── Schedule parsing ────────────────────────────────────────────────────────

_INTERVAL_RE = _re.compile(r"^every\s+(\d+)\s*([smh])$", _re.IGNORECASE)
_DAILY_RE = _re.compile(r"^daily\s+(\d{1,2}):(\d{2})$", _re.IGNORECASE)
_WEEKLY_RE = _re.compile(
    r"^weekly\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"\s+(\d{1,2}):(\d{2})$",
    _re.IGNORECASE,
)

_DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600}


class Schedule:
    """Represents a parsed schedule expression."""

    def __init__(self, kind, interval_sec=None, hour=None, minute=None, weekday=None):
        self.kind = kind              # "interval" | "daily" | "weekly"
        self.interval_sec = interval_sec
        self.hour = hour
        self.minute = minute
        self.weekday = weekday        # 0=Mon … 6=Sun
        # Track whether a daily/weekly rule already fired in this window
        self._last_fire_date = None

    def is_due(self, last_run_ts):
        """Return True if this schedule should fire now.

        Parameters
        ----------
        last_run_ts : float or None
            Timestamp (time.time()) of the last execution, or None if never.
        """
        now = time.time()

        if self.kind == "interval":
            if last_run_ts is None:
                return True
            return (now - last_run_ts) >= self.interval_sec

        dt = datetime.now()

        if self.kind == "daily":
            today = dt.date()
            if self._last_fire_date == today:
                return False  # already fired today
            if dt.hour == self.hour and dt.minute == self.minute:
                self._last_fire_date = today
                return True
            return False

        if self.kind == "weekly":
            today = dt.date()
            if self._last_fire_date == today:
                return False
            if (dt.weekday() == self.weekday
                    and dt.hour == self.hour
                    and dt.minute == self.minute):
                self._last_fire_date = today
                return True
            return False

        return False


def parse_schedule(expr):
    """Parse a schedule expression string into a Schedule object."""
    if expr is None:
        # Default: run every poll cycle
        return Schedule("interval", interval_sec=0)

    expr = expr.strip()

    m = _INTERVAL_RE.match(expr)
    if m:
        amount, unit = int(m.group(1)), m.group(2).lower()
        return Schedule("interval", interval_sec=amount * _UNIT_SECONDS[unit])

    m = _DAILY_RE.match(expr)
    if m:
        return Schedule("daily", hour=int(m.group(1)), minute=int(m.group(2)))

    m = _WEEKLY_RE.match(expr)
    if m:
        day = _DAY_MAP[m.group(1).lower()]
        return Schedule("weekly", hour=int(m.group(2)), minute=int(m.group(3)),
                        weekday=day)

    raise ValueError(
        f"Invalid schedule expression: {expr!r}\n"
        "Expected: 'every <N>s|m|h', 'daily HH:MM', or 'weekly <day> HH:MM'"
    )


# ── Folder scanning ────────────────────────────────────────────────────────

def _scan_files(folders):
    """Yield absolute Path objects for every file in *folders* (non-recursive)."""
    for folder in folders:
        folder = Path(folder)
        if not folder.is_dir():
            continue
        try:
            for entry in os.scandir(folder):
                if entry.is_file(follow_symlinks=False):
                    yield Path(entry.path)
        except OSError as exc:
            logger.error("Cannot scan %s: %s", folder, exc)


# ── Processed-file tracking ────────────────────────────────────────────────

class _ProcessedTracker:
    """Remember which (path, mtime) pairs a rule has already handled so we
    don't re-process files every tick."""

    def __init__(self):
        self._seen = set()

    def already_processed(self, file_path):
        """Return True if we already acted on this file (same path + mtime)."""
        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            return True  # can't stat → treat as already handled
        key = (str(file_path), mtime)
        if key in self._seen:
            return True
        self._seen.add(key)
        return False

    def purge_missing(self):
        """Drop entries whose files no longer exist (keeps the set small)."""
        self._seen = {
            (p, mt) for p, mt in self._seen if os.path.exists(p)
        }


# ── Main loop ──────────────────────────────────────────────────────────────

def run_loop(config, once=False):
    """Run the automation engine.

    Parameters
    ----------
    config : dict
        Fully resolved config from :func:`engine.config.load_config`.
    once : bool
        If True, execute one pass over all rules and return (no loop).
    """
    settings = config["settings"]
    dry_run = settings.get("dry_run", False)
    poll = max(settings.get("default_poll_seconds", 2), 1)

    # Build per-rule state
    rule_states = []
    for rule in config["rules"]:
        if not rule.get("enabled", True):
            logger.info("Rule '%s' is disabled — skipping", rule.get("name"))
            continue
        schedule = parse_schedule(rule.get("schedule"))
        rule_states.append({
            "rule": rule,
            "schedule": schedule,
            "last_run": None,
            "tracker": _ProcessedTracker(),
        })

    if not rule_states:
        logger.warning("No enabled rules — exiting")
        return

    logger.info(
        "Engine started — %d rule(s) active, poll=%ds, dry_run=%s",
        len(rule_states), poll, dry_run,
    )

    try:
        while True:
            for state in rule_states:
                sched = state["schedule"]
                if not sched.is_due(state["last_run"]):
                    continue

                rule = state["rule"]
                tracker = state["tracker"]
                rule_name = rule.get("name", "(unnamed)")

                for fpath in _scan_files(rule["watch"]):
                    if tracker.already_processed(fpath):
                        continue

                    if not matches(fpath, rule.get("match")):
                        continue

                    # Execute the action — errors are isolated per file
                    try:
                        msg = execute_action(str(fpath), rule["action"], dry_run)
                        logger.info("[%s] %s", rule_name, msg)
                    except Exception:
                        logger.exception(
                            "[%s] Error processing %s", rule_name, fpath
                        )

                state["last_run"] = time.time()

                # Periodic cleanup of the tracker set
                tracker.purge_missing()

            if once:
                break

            time.sleep(poll)

    except KeyboardInterrupt:
        logger.info("Shutting down (Ctrl+C received)")
