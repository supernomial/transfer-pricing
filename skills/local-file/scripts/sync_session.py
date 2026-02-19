#!/usr/bin/env python3
"""
Sync session metadata to the Supernomial Cowork cloud dashboard.

Reads the latest session-log entry and posts it to the Sync API.
This runs at the end of a Cowork session (called by commands).

Usage:
  python sync_session.py --working-dir <dir> --group <name> [--quiet]

The API key is read from:
  [working-dir]/.supernomial/config.json  →  { "api_key": "sk_..." }
  or environment variable SUPERNOMIAL_API_KEY
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

SYNC_API_URL = "https://cowork.supernomial.co/api/sync"


def get_api_key(working_dir):
    key = os.environ.get("SUPERNOMIAL_API_KEY")
    if key:
        return key

    config_path = os.path.join(working_dir, ".supernomial", "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
            return config.get("api_key")

    return None


def load_latest_session(working_dir, group_name):
    """Read the most recent entry from the group's session-log.json."""
    log_path = os.path.join(working_dir, group_name, "Records", "session-log.json")
    if not os.path.exists(log_path):
        return None

    with open(log_path, "r") as f:
        log = json.load(f)

    if not log or not isinstance(log, list):
        return None

    return log[-1]


def sync(working_dir, group_name, quiet=False):
    api_key = get_api_key(working_dir)
    if not api_key:
        if not quiet:
            print("No API key found. Skipping sync.", file=sys.stderr)
            print("Set up: [working-dir]/.supernomial/config.json or SUPERNOMIAL_API_KEY env var", file=sys.stderr)
        return False

    session = load_latest_session(working_dir, group_name)
    if not session:
        if not quiet:
            print(f"No session log found for group '{group_name}'.", file=sys.stderr)
        return False

    payload = {
        "group": group_name,
        "command": session.get("command", "unknown"),
        "entity": session.get("entity"),
        "summary": session.get("summary", "Session completed"),
        "decisions": session.get("decisions", []),
        "pending": session.get("pending"),
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SYNC_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if not quiet:
                print(f"Synced session → {result.get('session_id', 'ok')}")
            return True
    except urllib.error.HTTPError as e:
        if not quiet:
            body = e.read().decode("utf-8", errors="replace")
            print(f"Sync failed ({e.code}): {body}", file=sys.stderr)
        return False
    except urllib.error.URLError as e:
        if not quiet:
            print(f"Sync failed (network): {e.reason}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Sync session to Supernomial cloud")
    parser.add_argument("--working-dir", required=True, help="User's working directory")
    parser.add_argument("--group", required=True, help="Group name")
    parser.add_argument("--quiet", action="store_true", help="Suppress output (fail silently)")
    args = parser.parse_args()

    success = sync(args.working_dir, args.group, args.quiet)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
