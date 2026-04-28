#!/usr/bin/env python3
"""ve-twini CLI — Unified Twitter/X CLI harness for CLI-Anything.

Bridges bird (GraphQL API) and opencli (browser automation) for a complete
Twitter workflow.

Usage:
    cli-anything-ve-twini bookmarks
    cli-anything-ve-twini bookmarks --enrich
    cli-anything-ve-twini post "Hello world"
    cli-anything-ve-twini search "AI agents"
    cli-anything-ve-twini auth-check
    cli-anything-ve-twini archive
"""

import os
import sys

import click

BIRD_CMD = "bird"
OPENCLI_CMD = "opencli"


def _run_bird(args: list[str]) -> tuple[int, str, str]:
    import subprocess

    result = subprocess.run(
        [BIRD_CMD] + args,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def _run_opencli(args: list[str]) -> tuple[int, str, str]:
    import subprocess

    cmd = OPENCLI_CMD.split() + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Unified Twitter/X CLI — bridges bird and opencli."""
    pass


@cli.command("bookmarks")
@click.option("--json", is_flag=True, help="Output raw JSON from bird")
@click.option("--enrich", is_flag=True, help="Expand t.co URLs and attach media URLs")
def bookmarks(json: bool, enrich: bool):
    """Fetch your Twitter bookmarks via bird."""
    args = ["bookmarks"]
    if json:
        args.append("--json")

    code, stdout, stderr = _run_bird(args)

    if code != 0:
        click.echo("⚠️  bird auth failed or unavailable, trying opencli...", err=True)
        code, stdout, stderr = _run_opencli(["twitter", "bookmarks"])
        if code != 0:
            click.echo(f"opencli also failed: {stderr}", err=True)
            raise SystemExit(1)
        click.echo(stdout)
        return

    if enrich:
        import json as _json
        import re

        tweets = _json.loads(stdout)

        # Enrich helper — inline to avoid importing from the local package
        tco_urls = re.findall(r"https://t\.co/\S+", " ".join(t.get("text", "") for t in tweets))
        expanded = _expand_tco_urls(tco_urls)
        for tweet in tweets:
            tweet_tcos = re.findall(r"https://t\.co/\S+", tweet.get("text", ""))
            tweet["_enriched"] = {
                "urls": [{"original": u, "resolved": expanded.get(u, u)} for u in tweet_tcos],
                "media": _extract_media_urls(tweet),
            }
        click.echo(_json.dumps(tweets, indent=2))
    else:
        click.echo(stdout)


def _expand_tco_urls(urls: list[str]) -> dict[str, str]:
    import subprocess

    result = subprocess.run(
        ["bird", "expand"] + urls,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        import json as _json

        try:
            return _json.loads(result.stdout)
        except _json.JSONDecodeError:
            pass
    return {u: u for u in urls}


def _extract_media_urls(tweet: dict) -> list[dict]:
    media = []
    for item in tweet.get("edit_history_tweet_ids", []):
        pass
    photos = tweet.get("photos", [])
    for p in photos:
        media.append({"type": "photo", "url": p.get("url", "")})
    cards = tweet.get("card", {}).get("preview", {}).get("image", {})
    if cards:
        media.append({"type": "card", "url": cards})
    return media


@cli.command()
@click.argument("text")
def post(text: str):
    """Post a tweet via opencli browser automation."""
    code, stdout, stderr = _run_opencli(["twitter", "post", text])
    if code != 0:
        click.echo(f"opencli error: {stderr}", err=True)
        raise SystemExit(1)
    click.echo(stdout)


@cli.command()
@click.argument("query")
@click.option("--json", is_flag=True, help="Output raw JSON")
def search(query: str, json: bool):
    """Search tweets via bird."""
    args = ["search", query]
    if json:
        args.append("--json")

    code, stdout, stderr = _run_bird(args)
    if code != 0:
        click.echo(f"bird error: {stderr}", err=True)
        raise SystemExit(1)
    click.echo(stdout)


@cli.command("auth-check")
def auth_check():
    """Check authentication status for both bird and opencli."""
    click.echo("=== ve-twini auth check ===\n")

    click.echo("[bird]")
    code, stdout, stderr = _run_bird(["whoami"])
    if code == 0:
        click.echo("  ✅ Auth OK")
        click.echo(f"  {stdout.strip()}")
    else:
        click.echo("  ❌ Not authenticated")
        click.echo(f"  {stderr.strip()}")

    click.echo("\n[opencli browser]")
    code, stdout, stderr = _run_opencli(["doctor"])
    if "Extension: connected" in stdout:
        click.echo("  ✅ Chrome Bridge connected")
    elif "about:blank" in stdout:
        click.echo("  ⚠️  Browser open but not on a real page (extension may still be connected)")
    else:
        click.echo("  ❌ Extension not connected")


@cli.command()
def archive():
    """Fetch bookmarks via bird and archive new ones to local SQLite (incremental sync)."""
    import json as _json
    import sqlite3
    from datetime import datetime
    from pathlib import Path

    db_path = os.environ.get("VE_TWINI_DB", "~/.ve-twini/bookmarks.db")
    db_path = os.path.expanduser(db_path)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _init_db(db_path)

    code, stdout, stderr = _run_bird(["bookmarks", "--json"])
    if code != 0:
        click.echo(f"bird error: {stderr}", err=True)
        raise SystemExit(1)

    tweets = _json.loads(stdout)
    new_tweets = _filter_new_tweets(tweets, db_path)

    if not new_tweets:
        click.echo("No new bookmarks to archive")
        _mark_sync_time(db_path)
        return

    for tweet in new_tweets:
        _archive_tweet(tweet, db_path)

    _mark_sync_time(db_path)
    click.echo(f"Archived {len(new_tweets)} new bookmarks")


def _init_db(db_path: str) -> None:
    import sqlite3

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS bookmarks (
            tweet_id TEXT PRIMARY KEY,
            text TEXT,
            author_username TEXT,
            author_name TEXT,
            created_at TEXT,
            raw_json TEXT,
            synced_at TEXT DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS sync_meta (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.commit()
    conn.close()


def _archive_tweet(tweet: dict, db_path: str) -> None:
    import sqlite3
    import json as _json
    from datetime import datetime

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO bookmarks
           (tweet_id, text, author_username, author_name, created_at, raw_json, synced_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            tweet.get("id"),
            tweet.get("text"),
            tweet.get("author_username"),
            tweet.get("author_name"),
            tweet.get("created_at"),
            _json.dumps(tweet),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def _filter_new_tweets(tweets: list[dict], db_path: str) -> list[dict]:
    import sqlite3

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT tweet_id FROM bookmarks")
    existing_ids = {row[0] for row in cur.fetchall()}
    conn.close()
    return [t for t in tweets if t.get("id") not in existing_ids]


def _mark_sync_time(db_path: str) -> None:
    import sqlite3
    from datetime import datetime

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT OR REPLACE INTO sync_meta (key, value, updated_at) VALUES ('last_sync', ?, ?)",
        (now, now),
    )
    conn.commit()
    conn.close()


def main():
    cli()
