# File Automation Engine

A hands-free file management system driven by a JSON DSL. Watches folders, matches files by rules you define, and executes actions (move, rename, delete, compress) automatically.

**Zero external dependencies** — uses only the Python 3 standard library.

## Quick Start

```bash
# 1. Edit config.json with your folders and rules (dry_run is ON by default)
# 2. Run a single test pass
python run.py --once

# 3. Check automation.log — satisfied? Turn off dry_run and run continuously
python run.py
```

## CLI Options

| Flag | Description |
|---|---|
| `--config PATH` / `-c` | Config file (default: `config.json`) |
| `--dry-run` / `-n` | Log actions without touching files (overrides config) |
| `--once` | Run one pass over all rules, then exit |

## Config DSL Reference

The config file has three top-level sections:

### `settings`

| Key | Type | Default | Description |
|---|---|---|---|
| `log_file` | string | `"automation.log"` | Log file path |
| `log_level` | string | `"INFO"` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `dry_run` | bool | `false` | When true, log actions without executing |
| `default_poll_seconds` | int | `2` | Sleep interval between scan cycles |

### `variables`

Key-value pairs referenced as `${name}` anywhere inside `rules`:

```json
"variables": {
  "downloads": "C:/Users/frank/Downloads",
  "archive": "C:/Users/frank/Archive"
}
```

### `rules`

An ordered list of rule objects. Each rule has:

```json
{
  "name": "Human-readable label",
  "enabled": true,
  "schedule": "every 2s",
  "watch": ["${downloads}", "/other/folder"],
  "match": { ... },
  "action": { ... }
}
```

#### Schedule Expressions

| Expression | Meaning |
|---|---|
| `"every 2s"` | Every 2 seconds |
| `"every 5m"` | Every 5 minutes |
| `"every 1h"` | Every 1 hour |
| `"daily 09:00"` | Once daily at 09:00 |
| `"weekly monday 09:00"` | Weekly on Monday at 09:00 |

#### Match Conditions (AND logic — all must pass)

| Field | Type | Example | Description |
|---|---|---|---|
| `extensions` | list | `[".pdf", ".log"]` | Allowed file extensions |
| `glob` | string | `"Report_*"` | fnmatch pattern against filename |
| `regex` | string | `"^data_\\d+\\.csv$"` | Regex against filename |
| `older_than_days` | number | `30` | File mtime older than N days |
| `newer_than_days` | number | `1` | File mtime newer than N days |
| `larger_than` | string | `"10MB"` | Minimum file size (B, KB, MB, GB, TB) |
| `smaller_than` | string | `"1GB"` | Maximum file size |

All fields are optional. Omitted fields are not checked.

#### Action Types

**move** — Move file to a destination folder.

```json
{ "type": "move", "destination": "${archive}/{year}/{month}", "on_conflict": "rename" }
```

**rename** — Rename file in place using a template.

```json
{ "type": "rename", "pattern": "screenshot_{date}_{time}_{counter}{ext}" }
```

**delete** — Delete the file.

```json
{ "type": "delete" }
```

**compress** — Zip/gzip the file, then delete the original.

```json
{ "type": "compress", "destination": "${archive}", "format": "zip" }
```

`on_conflict` options: `"rename"` (default — appends `_1`, `_2`, ...), `"skip"`, `"overwrite"`.

#### Template Variables

Available in `destination` and `pattern` strings:

| Variable | Example | Description |
|---|---|---|
| `{name}` | `report` | Filename without extension |
| `{ext}` | `.pdf` | Extension with dot |
| `{ext_name}` | `pdf` | Extension without dot |
| `{date}` | `2026-05-01` | Current date |
| `{time}` | `143052` | Current time HHMMSS |
| `{year}` | `2026` | 4-digit year |
| `{month}` | `05` | 2-digit month |
| `{day}` | `01` | 2-digit day |
| `{counter}` | `3` | Auto-incrementing integer |
| `{size_mb}` | `12.4` | File size in MB |

## Running as a Background Service

### Windows Task Scheduler

1. Open Task Scheduler and create a new task
2. Trigger: **At startup** (or a custom schedule)
3. Action: `python C:\Users\frank\python-file-automation\run.py`
4. Check "Run whether user is logged on or not"

### Linux (systemd / cron)

```bash
# crontab -e
@reboot python3 /home/user/python-file-automation/run.py >> /var/log/file-auto.log 2>&1
```

## Project Structure

```
python-file-automation/
  run.py           — CLI entry point
  config.json      — Your rules (edit this)
  automation.log   — Action log (created at runtime)
  engine/
    __init__.py
    config.py      — Config loading, validation, variable resolution
    matcher.py     — File matching (extension, glob, regex, age, size)
    actions.py     — Action execution (move, rename, delete, compress)
    scheduler.py   — Schedule parsing and main polling loop
```
