"""
config.py — Load, validate, and resolve the JSON DSL configuration.

Handles:
  - Reading the JSON config file
  - Replacing ${variable} references with values from the "variables" block
  - Parsing human-readable sizes ("10MB") into bytes
  - Validating required keys and action types
"""

import json
import re
import logging
from pathlib import Path

logger = logging.getLogger("automation.config")

# ── Size parsing ────────────────────────────────────────────────────────────

_SIZE_UNITS = {
    "B": 1,
    "KB": 1024,
    "MB": 1024 ** 2,
    "GB": 1024 ** 3,
    "TB": 1024 ** 4,
}

_SIZE_RE = re.compile(r"^\s*([\d.]+)\s*(B|KB|MB|GB|TB)\s*$", re.IGNORECASE)


def parse_size(value):
    """Convert a human-readable size string like '10MB' to an integer byte count.
    Returns None if *value* is None or empty."""
    if value is None:
        return None
    m = _SIZE_RE.match(str(value))
    if not m:
        raise ValueError(f"Invalid size string: {value!r}  (expected e.g. '10MB')")
    number, unit = float(m.group(1)), m.group(2).upper()
    return int(number * _SIZE_UNITS[unit])


# ── Variable resolution ────────────────────────────────────────────────────

_VAR_RE = re.compile(r"\$\{(\w+)\}")


def _resolve_string(text, variables):
    """Replace every ${name} token in *text* with the matching variable value."""
    def _replacer(m):
        key = m.group(1)
        if key not in variables:
            raise KeyError(f"Undefined variable ${{{key}}} in config")
        return variables[key]
    return _VAR_RE.sub(_replacer, text)


def resolve_variables(obj, variables):
    """Recursively walk *obj* (dict / list / str) and expand ${var} tokens."""
    if isinstance(obj, str):
        return _resolve_string(obj, variables)
    if isinstance(obj, list):
        return [resolve_variables(item, variables) for item in obj]
    if isinstance(obj, dict):
        return {k: resolve_variables(v, variables) for k, v in obj.items()}
    return obj  # int, float, bool, None — pass through


# ── Validation ──────────────────────────────────────────────────────────────

_VALID_ACTIONS = {"move", "rename", "delete", "compress"}
_VALID_CONFLICT = {"rename", "skip", "overwrite"}


def _validate_rule(rule, index):
    """Raise ValueError if a rule is structurally invalid."""
    name = rule.get("name", f"rule #{index}")

    if "watch" not in rule or not rule["watch"]:
        raise ValueError(f"Rule '{name}': 'watch' list is required")
    if "action" not in rule:
        raise ValueError(f"Rule '{name}': 'action' block is required")

    action = rule["action"]
    atype = action.get("type")
    if atype not in _VALID_ACTIONS:
        raise ValueError(
            f"Rule '{name}': unknown action type '{atype}' "
            f"(expected one of {_VALID_ACTIONS})"
        )

    if atype in ("move", "compress") and not action.get("destination"):
        raise ValueError(f"Rule '{name}': '{atype}' action requires 'destination'")
    if atype == "rename" and not action.get("pattern"):
        raise ValueError(f"Rule '{name}': 'rename' action requires 'pattern'")

    conflict = action.get("on_conflict", "rename")
    if conflict not in _VALID_CONFLICT:
        raise ValueError(
            f"Rule '{name}': invalid on_conflict '{conflict}' "
            f"(expected one of {_VALID_CONFLICT})"
        )

    # Warn about watch dirs that don't exist yet (non-fatal)
    for folder in rule.get("watch", []):
        if not Path(folder).is_dir():
            logger.warning("Rule '%s': watch directory does not exist: %s", name, folder)


# ── Public API ──────────────────────────────────────────────────────────────

_DEFAULTS = {
    "log_file": "automation.log",
    "log_level": "INFO",
    "dry_run": False,
    "default_poll_seconds": 2,
}


def load_config(path):
    """Read the JSON config file, resolve variables, validate, and return the
    fully-expanded config dict.

    Returned dict shape::

        {
            "settings": { ... },
            "variables": { ... },
            "rules": [ ... ],
        }
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    # Merge default settings
    settings = {**_DEFAULTS, **(raw.get("settings") or {})}
    variables = raw.get("variables") or {}
    rules = raw.get("rules") or []

    if not rules:
        logger.warning("Config contains no rules — nothing to do")

    # Resolve ${var} tokens inside rules (settings and variables stay literal)
    resolved_rules = resolve_variables(rules, variables)

    # Validate each rule
    for i, rule in enumerate(resolved_rules):
        _validate_rule(rule, i)

    return {
        "settings": settings,
        "variables": variables,
        "rules": resolved_rules,
    }
