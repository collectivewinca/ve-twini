#!/usr/bin/env python3
"""
ve-twini — Unified Twitter/X CLI
Bridges bird (GraphQL API) and opencli (browser automation)
"""

import argparse
import json
import os
import re
import subprocess
import sys

from db import BookmarkDB
from enrich import expand_tco_urls, extract_media_urls

BIRD_CMD = "bird"
OPENCLI_CMD = "opencli"


def run_bird(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BIRD_CMD] + args,
        capture_output=True,
        text=True,
    )


def run_opencli(args: list[str]) -> subprocess.CompletedProcess:
    cmd = OPENCLI_CMD.split() + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )


def cmd_bookmarks(json_output: bool = False, enrich: bool = False):
    """Fetch bookmarks via bird, enrich with media URLs."""
    args = ["bookmarks", "--json"]
    result = run_bird(args)

    if result.returncode != 0:
        print(f"bird error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    if enrich:
        tweets = json.loads(result.stdout)
        for tweet in tweets:
            tco_urls = re.findall(r'https://t\.co/\S+', tweet.get("text", ""))
            tweet["_enriched"] = {
                "urls": expand_tco_urls(tco_urls),
                "media": extract_media_urls(tweet),
            }
        print(json.dumps(tweets, indent=2))
    else:
        print(result.stdout)


def cmd_post(text: str):
    """Post a tweet via opencli browser."""
    result = run_opencli(["twitter", "post", text])
    if result.returncode != 0:
        print(f"opencli error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)


def cmd_search(query: str, json_output: bool = False):
    """Search tweets via bird."""
    args = ["search", query]
    if json_output:
        args.append("--json")

    result = run_bird(args)
    if result.returncode != 0:
        print(f"bird error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)


def cmd_auth_check():
    """Check auth status for both bird and opencli."""
    print("=== ve-twini auth check ===\n")

    print("[bird]")
    result = run_bird(["whoami"])
    if result.returncode == 0:
        print("  ✅ Auth OK")
        print(result.stdout)
    else:
        print("  ❌ Not authenticated")
        print(f"  {result.stderr}")

    print("\n[opencli browser]")
    result = run_opencli(["browser", "state"])
    if "about:blank" in result.stdout:
        print("  ⚠️  Browser open but not connected to extension")
    elif result.returncode == 0:
        print("  ✅ Chrome Bridge connected")
        print(result.stdout)
    else:
        print("  ❌ Browser error")


def cmd_archive():
    """Fetch bookmarks via bird and archive new ones in SQLite."""
    db_path = os.environ.get("VE_TWINI_DB", "~/.ve-twini/bookmarks.db")
    db = BookmarkDB(db_path)

    result = run_bird(["bookmarks", "--json"])
    if result.returncode != 0:
        print(f"bird error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    tweets = json.loads(result.stdout)
    new_tweets = db.filter_new_tweets(tweets)

    if not new_tweets:
        print("No new bookmarks to archive")
        db.mark_sync_time()
        return

    for tweet in new_tweets:
        db.archive_tweet(tweet)

    db.mark_sync_time()
    print(f"Archived {len(new_tweets)} new bookmarks")


def main():
    parser = argparse.ArgumentParser(
        description="ve-twini — Unified Twitter/X CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # bookmarks
    p = sub.add_parser("bookmarks", help="Fetch your bookmarks")
    p.add_argument("--json", action="store_true", help="Output raw JSON")
    p.add_argument("--enrich", action="store_true", help="Expand t.co URLs and attach media URLs")

    # post
    p = sub.add_parser("post", help="Post a tweet")
    p.add_argument("text", help="Tweet text")

    # search
    p = sub.add_parser("search", help="Search tweets")
    p.add_argument("query", help="Search query")
    p.add_argument("--json", action="store_true", help="Output raw JSON")

    # auth-check
    sub.add_parser("auth-check", help="Check auth status")

    # archive
    p = sub.add_parser("archive", help="Fetch bookmarks and archive new ones to SQLite")

    opts = parser.parse_args()

    if opts.command == "bookmarks":
        cmd_bookmarks(opts.json, opts.enrich)
    elif opts.command == "post":
        cmd_post(opts.text)
    elif opts.command == "search":
        cmd_search(opts.query, opts.json)
    elif opts.command == "auth-check":
        cmd_auth_check()
    elif opts.command == "archive":
        cmd_archive()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
