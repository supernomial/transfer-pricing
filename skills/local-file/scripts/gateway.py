#!/usr/bin/env python3
"""
Cache-first content gateway for the Supernomial Cowork plugin.

Resolution order:
  1. Local cache (~/.supernomial/cache/)
  2. Content API (cowork.supernomial.co/api/content/)
  3. Plugin zip fallback (read-only plugin folder)

Usage:
  python gateway.py fetch <path> [--plugin-root <dir>]
  python gateway.py clear-cache
  python gateway.py cache-status

The API key is read from:
  [working-dir]/.supernomial/config.json  →  { "api_key": "sk_..." }
  or environment variable SUPERNOMIAL_API_KEY
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error

CONTENT_API_BASE = "https://cowork.supernomial.co/api/content"
VALIDATE_URL = "https://cowork.supernomial.co/api/validate"
CACHE_DIR = os.path.expanduser("~/.supernomial/cache")
CACHE_TTL_SECONDS = 3600  # 1 hour

def get_api_key(working_dir=None):
    key = os.environ.get("SUPERNOMIAL_API_KEY")
    if key:
        return key

    if working_dir:
        config_path = os.path.join(working_dir, ".supernomial", "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                return config.get("api_key")

    return None


def cache_path_for(content_path):
    safe_name = content_path.replace("/", "__")
    return os.path.join(CACHE_DIR, safe_name)


def cache_meta_path_for(content_path):
    return cache_path_for(content_path) + ".meta"


def read_from_cache(content_path):
    cp = cache_path_for(content_path)
    mp = cache_meta_path_for(content_path)

    if not os.path.exists(cp) or not os.path.exists(mp):
        return None

    with open(mp, "r") as f:
        meta = json.load(f)

    if time.time() - meta.get("fetched_at", 0) > CACHE_TTL_SECONDS:
        return None

    with open(cp, "r") as f:
        return f.read()


def write_to_cache(content_path, content):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cp = cache_path_for(content_path)
    mp = cache_meta_path_for(content_path)

    with open(cp, "w") as f:
        f.write(content)

    with open(mp, "w") as f:
        json.dump({"fetched_at": time.time(), "path": content_path}, f)


def fetch_from_api(content_path, api_key):
    if not api_key:
        return None

    url = f"{CONTENT_API_BASE}/{content_path}"
    req = urllib.request.Request(url, headers={"x-api-key": api_key})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            write_to_cache(content_path, content)
            return content
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        print(f"API error {e.code}: {e.reason}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        return None


def read_from_plugin(content_path, plugin_root):
    if not plugin_root:
        return None

    full_path = os.path.join(plugin_root, content_path)
    if os.path.exists(full_path):
        with open(full_path, "r") as f:
            return f.read()
    return None


def fetch(content_path, plugin_root=None, working_dir=None):
    """Resolve content via cache → API → plugin fallback."""
    cached = read_from_cache(content_path)
    if cached is not None:
        return {"content": cached, "source": "cache"}

    api_key = get_api_key(working_dir)
    from_api = fetch_from_api(content_path, api_key)
    if from_api is not None:
        return {"content": from_api, "source": "api"}

    from_plugin = read_from_plugin(content_path, plugin_root)
    if from_plugin is not None:
        return {"content": from_plugin, "source": "plugin"}

    return None


def validate(working_dir=None):
    """Check that the API key is valid and the subscription is active.
    Returns True if valid, False otherwise. Prints a user-facing message."""
    api_key = get_api_key(working_dir)
    if not api_key:
        print(
            "No Supernomial API key found.\n"
            "Save your key to .supernomial/config.json in your working folder:\n"
            '  { "api_key": "sk_..." }\n'
            "Or set the SUPERNOMIAL_API_KEY environment variable.\n"
            "Get your key at cowork.supernomial.co/settings.",
            file=sys.stderr,
        )
        return False

    req = urllib.request.Request(
        VALIDATE_URL,
        headers={"x-api-key": api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(
                "Your Supernomial API key is invalid or your subscription is inactive.\n"
                "Visit cowork.supernomial.co to check your account.",
                file=sys.stderr,
            )
        else:
            print(f"Validation error {e.code}: {e.reason}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"Could not reach cowork.supernomial.co: {e.reason}", file=sys.stderr)

    return False


def clear_cache():
    if not os.path.exists(CACHE_DIR):
        print("Cache directory does not exist.")
        return

    count = 0
    for f in os.listdir(CACHE_DIR):
        os.remove(os.path.join(CACHE_DIR, f))
        count += 1
    print(f"Cleared {count} cached files.")


def cache_status():
    if not os.path.exists(CACHE_DIR):
        print("Cache directory does not exist.")
        return

    files = [f for f in os.listdir(CACHE_DIR) if not f.endswith(".meta")]
    if not files:
        print("Cache is empty.")
        return

    total_size = 0
    print(f"{'Path':<60} {'Age':>8} {'Size':>10}")
    print("-" * 80)

    for f in sorted(files):
        fp = os.path.join(CACHE_DIR, f)
        mp = fp + ".meta"
        size = os.path.getsize(fp)
        total_size += size

        age_str = "unknown"
        if os.path.exists(mp):
            with open(mp, "r") as mf:
                meta = json.load(mf)
                age_seconds = time.time() - meta.get("fetched_at", 0)
                if age_seconds < 60:
                    age_str = f"{int(age_seconds)}s"
                elif age_seconds < 3600:
                    age_str = f"{int(age_seconds / 60)}m"
                else:
                    age_str = f"{age_seconds / 3600:.1f}h"

        original_path = f.replace("__", "/")
        print(f"{original_path:<60} {age_str:>8} {size:>8} B")

    print("-" * 80)
    print(f"Total: {len(files)} files, {total_size:,} bytes")


def main():
    parser = argparse.ArgumentParser(description="Supernomial content gateway")
    sub = parser.add_subparsers(dest="command")

    validate_cmd = sub.add_parser("validate", help="Check API key and subscription status")
    validate_cmd.add_argument("--working-dir", help="Working directory (for API key config)")

    fetch_cmd = sub.add_parser("fetch", help="Fetch content by path")
    fetch_cmd.add_argument("path", help="Content path (e.g. skills/local-file/SKILL.md)")
    fetch_cmd.add_argument("--plugin-root", help="Plugin root directory for fallback")
    fetch_cmd.add_argument("--working-dir", help="Working directory (for API key config)")

    sub.add_parser("clear-cache", help="Clear all cached content")
    sub.add_parser("cache-status", help="Show cache status")

    args = parser.parse_args()

    if args.command == "validate":
        ok = validate(args.working_dir)
        sys.exit(0 if ok else 1)

    elif args.command == "fetch":
        result = fetch(args.path, args.plugin_root, args.working_dir)
        if result:
            print(result["content"])
            print(f"\n[source: {result['source']}]", file=sys.stderr)
        else:
            print(f"Not found: {args.path}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "clear-cache":
        clear_cache()

    elif args.command == "cache-status":
        cache_status()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
