"""
matcher.py — Decide whether a file matches a rule's conditions.

All conditions in the "match" block are combined with AND logic:
a file must satisfy every specified condition to match.  Omitted
(None) conditions are skipped.

Supported conditions:
  - extensions   — list of allowed extensions (e.g. [".pdf", ".log"])
  - glob         — fnmatch pattern against the filename
  - regex        — regex pattern against the filename
  - older_than_days / newer_than_days — file age via mtime
  - larger_than  / smaller_than       — file size (human-readable)
"""

import fnmatch
import logging
import os
import re
import time
from pathlib import Path

from engine.config import parse_size

logger = logging.getLogger("automation.matcher")


def matches(file_path, match_block):
    """Return True if *file_path* satisfies every condition in *match_block*.

    Parameters
    ----------
    file_path : str or Path
        Absolute path to the candidate file.
    match_block : dict or None
        The "match" section of a rule.  If None or empty, every file matches.
    """
    if not match_block:
        return True

    path = Path(file_path)
    name = path.name

    # ── Extension filter ────────────────────────────────────────────────
    extensions = match_block.get("extensions")
    if extensions:
        # Normalise to lowercase with leading dot
        exts = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions}
        if path.suffix.lower() not in exts:
            return False

    # ── Glob pattern ────────────────────────────────────────────────────
    glob_pat = match_block.get("glob")
    if glob_pat and not fnmatch.fnmatch(name, glob_pat):
        return False

    # ── Regex pattern ───────────────────────────────────────────────────
    regex_pat = match_block.get("regex")
    if regex_pat and not re.search(regex_pat, name):
        return False

    # ── File stat (age + size) ──────────────────────────────────────────
    try:
        stat = os.stat(file_path)
    except OSError as exc:
        logger.debug("Cannot stat %s: %s", file_path, exc)
        return False

    now = time.time()
    age_days = (now - stat.st_mtime) / 86400

    older = match_block.get("older_than_days")
    if older is not None and age_days < older:
        return False

    newer = match_block.get("newer_than_days")
    if newer is not None and age_days > newer:
        return False

    larger = parse_size(match_block.get("larger_than"))
    if larger is not None and stat.st_size < larger:
        return False

    smaller = parse_size(match_block.get("smaller_than"))
    if smaller is not None and stat.st_size > smaller:
        return False

    return True
