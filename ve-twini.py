#!/usr/bin/env python3
"""
ve-twini — Unified Twitter/X CLI
Bridges bird (GraphQL API) and opencli (browser automation)
"""

import argparse
import json
import subprocess
import sys

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


def cmd_bookmarks(json_output: bool = False):
    """Fetch bookmarks via bird, enrich with media URLs."""
    args = ["bookmarks"]
    if json_output:
        args.append("--json")

    result = run_bird(args)

    if result.returncode != 0:
        print(f"bird error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

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


def main():
    parser = argparse.ArgumentParser(
        description="ve-twini — Unified Twitter/X CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # bookmarks
    p = sub.add_parser("bookmarks", help="Fetch your bookmarks")
    p.add_argument("--json", action="store_true", help="Output raw JSON")

    # post
    p = sub.add_parser("post", help="Post a tweet")
    p.add_argument("text", help="Tweet text")

    # search
    p = sub.add_parser("search", help="Search tweets")
    p.add_argument("query", help="Search query")
    p.add_argument("--json", action="store_true", help="Output raw JSON")

    # auth-check
    sub.add_parser("auth-check", help="Check auth status")

    opts = parser.parse_args()

    if opts.command == "bookmarks":
        cmd_bookmarks(opts.json)
    elif opts.command == "post":
        cmd_post(opts.text)
    elif opts.command == "search":
        cmd_search(opts.query, opts.json)
    elif opts.command == "auth-check":
        cmd_auth_check()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
