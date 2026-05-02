"""
actions.py — Execute file-management actions (move, rename, delete, compress).

Each public action function follows the signature:

    action_*(file_path, action_block, dry_run) -> str

It returns a short human-readable description of what was done (for logging).

Template variables available in 'destination' and 'pattern' strings:
  {name}      — filename without extension
  {ext}       — extension including the dot (.pdf)
  {ext_name}  — extension without the dot  (pdf)
  {date}      — current date  YYYY-MM-DD
  {time}      — current time  HHMMSS
  {year}      — current 4-digit year
  {month}     — current 2-digit month
  {day}       — current 2-digit day
  {counter}   — auto-incrementing integer (unique per destination dir)
  {size_mb}   — file size in megabytes, rounded to 1 decimal
"""

import gzip
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("automation.actions")

# ── Template expansion ──────────────────────────────────────────────────────

# Module-level counter per directory to avoid collisions within a single run.
_counters = {}


def _next_counter(directory):
    """Return the next integer counter for *directory*."""
    directory = str(directory)
    _counters[directory] = _counters.get(directory, 0) + 1
    return _counters[directory]


def expand_template(template, file_path):
    """Replace {name}, {ext}, {date}, … placeholders in *template*."""
    path = Path(file_path)
    now = datetime.now()
    try:
        size_mb = round(os.path.getsize(file_path) / (1024 ** 2), 1)
    except OSError:
        size_mb = 0

    values = {
        "name": path.stem,
        "ext": path.suffix,            # .pdf
        "ext_name": path.suffix.lstrip("."),  # pdf
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H%M%S"),
        "year": now.strftime("%Y"),
        "month": now.strftime("%m"),
        "day": now.strftime("%d"),
        "counter": _next_counter(path.parent),
        "size_mb": size_mb,
    }
    result = template
    for key, val in values.items():
        result = result.replace(f"{{{key}}}", str(val))
    return result


# ── Conflict resolution ────────────────────────────────────────────────────

def _resolve_conflict(dest_path, mode):
    """Handle the case where *dest_path* already exists.

    mode:
      "skip"      — return None (caller should skip this file)
      "overwrite" — return dest_path unchanged
      "rename"    — append _1, _2, … until a free name is found
    """
    if not dest_path.exists():
        return dest_path

    if mode == "skip":
        logger.info("SKIP (conflict): %s already exists", dest_path)
        return None

    if mode == "overwrite":
        return dest_path

    # mode == "rename" (default)
    stem = dest_path.stem
    suffix = dest_path.suffix
    parent = dest_path.parent
    n = 1
    while True:
        candidate = parent / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


# ── Action implementations ─────────────────────────────────────────────────

def action_move(file_path, action, dry_run):
    """Move *file_path* to the destination folder."""
    dest_dir = Path(expand_template(action["destination"], file_path))
    on_conflict = action.get("on_conflict", "rename")

    dest_file = dest_dir / Path(file_path).name

    if dry_run:
        return f"[DRY-RUN] MOVE {file_path} -> {dest_file}"

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = _resolve_conflict(dest_file, on_conflict)
    if dest_file is None:
        return f"SKIP {file_path} (conflict)"

    shutil.move(str(file_path), str(dest_file))
    return f"MOVE {file_path} -> {dest_file}"


def action_rename(file_path, action, dry_run):
    """Rename *file_path* in place using the template pattern."""
    new_name = expand_template(action["pattern"], file_path)
    new_path = Path(file_path).parent / new_name

    if dry_run:
        return f"[DRY-RUN] RENAME {file_path} -> {new_path}"

    new_path = _resolve_conflict(new_path, "rename")
    if new_path is None:
        return f"SKIP {file_path} (conflict)"

    Path(file_path).rename(new_path)
    return f"RENAME {file_path} -> {new_path}"


def action_delete(file_path, action, dry_run):
    """Delete *file_path*."""
    if dry_run:
        return f"[DRY-RUN] DELETE {file_path}"

    os.remove(file_path)
    return f"DELETE {file_path}"


def action_compress(file_path, action, dry_run):
    """Compress *file_path* into a zip or gzip archive, then remove the original."""
    fmt = action.get("format", "zip").lower()
    dest_dir = Path(expand_template(action["destination"], file_path))
    src = Path(file_path)

    if fmt == "zip":
        archive_name = dest_dir / f"{src.stem}.zip"
    elif fmt == "gzip":
        archive_name = dest_dir / f"{src.name}.gz"
    else:
        raise ValueError(f"Unsupported compression format: {fmt}")

    if dry_run:
        return f"[DRY-RUN] COMPRESS ({fmt}) {file_path} -> {archive_name}"

    dest_dir.mkdir(parents=True, exist_ok=True)
    on_conflict = action.get("on_conflict", "rename")
    archive_name = _resolve_conflict(archive_name, on_conflict)
    if archive_name is None:
        return f"SKIP {file_path} (conflict)"

    if fmt == "zip":
        with zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(file_path, src.name)
    else:  # gzip
        with open(file_path, "rb") as f_in, gzip.open(archive_name, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    os.remove(file_path)
    return f"COMPRESS ({fmt}) {file_path} -> {archive_name}"


# ── Dispatcher ──────────────────────────────────────────────────────────────

_ACTION_MAP = {
    "move": action_move,
    "rename": action_rename,
    "delete": action_delete,
    "compress": action_compress,
}


def execute_action(file_path, action, dry_run=False):
    """Dispatch to the correct action handler and return a log message."""
    atype = action["type"]
    handler = _ACTION_MAP.get(atype)
    if handler is None:
        raise ValueError(f"Unknown action type: {atype}")
    return handler(file_path, action, dry_run)
