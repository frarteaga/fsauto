#!/usr/bin/env python3
"""
run.py — Entry point for the file-automation engine.

Usage:
    python run.py                        # use default config.json
    python run.py --config my_rules.json # custom config path
    python run.py --dry-run              # log actions without touching files
    python run.py --once                 # single pass, then exit (no loop)
"""

import argparse
import logging
import sys
from pathlib import Path

from engine.config import load_config
from engine.scheduler import run_loop


def _setup_logging(log_file, log_level):
    """Configure logging to both console and file."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — append mode so history is preserved across runs
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(fh)
    root.addHandler(ch)


def main():
    parser = argparse.ArgumentParser(
        description="File-automation engine — watches folders and applies rules."
    )
    parser.add_argument(
        "--config", "-c",
        default="config.json",
        help="Path to the JSON config file (default: config.json)",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Log what would happen without making changes",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one pass over all rules, then exit",
    )
    args = parser.parse_args()

    # Load and validate config
    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # CLI --dry-run overrides the config setting
    if args.dry_run:
        config["settings"]["dry_run"] = True

    settings = config["settings"]
    _setup_logging(settings["log_file"], settings["log_level"])

    logger = logging.getLogger("automation")
    logger.info("Loaded config from %s", Path(args.config).resolve())

    run_loop(config, once=args.once)


if __name__ == "__main__":
    main()
