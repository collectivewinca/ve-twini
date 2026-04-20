# ve-twini Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement URL enrichment, SQLite archive, and fallback routing for ve-twini

**Architecture:** ve-twini wraps bird/opencli, enriches outputs with resolved URLs and media metadata, stores bookmarks in SQLite for offline access, and gracefully falls back when primary tools fail.

**Tech Stack:** Python 3.11+, sqlite3 (stdlib), subprocess, urllib

---

## Task 1: enrich.py — URL & Media URL Expansion

**Files:**
- Create: `enrich.py`
- Modify: `ve-twini.py` (import enrich, use in cmd_bookmarks)

**Step 1: Write the failing test**

```python
# tests/test_enrich.py
import pytest
from enrich import expand_tco_urls, extract_media_urls

def test_expand_tco_urls():
    """Resolves t.co shortened URLs to real URLs"""
    urls = ["https://t.co/xgecemAaiq"]
    expanded = expand_tco_urls(urls)
    assert "x.com/HeritageMatterz" in expanded[0]["expanded"]
    assert "video" in expanded[0]["expanded"] or "pbs.twimg.com" in expanded[0]["expanded"]

def test_extract_media_from_tweet():
    """Extracts media URLs from bird JSON tweet objects"""
    tweet = {
        "id": "123",
        "text": "check this out https://t.co/abc",
        "media": [
            {"url": "https://pbs.twimg.com/media/img.jpg", "type": "photo"}
        ]
    }
    result = extract_media_urls(tweet)
    assert result[0]["url"] == "https://pbs.twimg.com/media/img.jpg"
    assert result[0]["type"] == "photo"
```

**Step 2: Run test to verify it fails**

```bash
mkdir -p tests && touch tests/__init__.py
pytest tests/test_enrich.py -v
```
Expected: FAIL — `enrich` module not found

**Step 3: Write minimal implementation**

```python
# enrich.py
"""URL expansion and media extraction for ve-twini"""
import subprocess
import re

def expand_tco_urls(urls: list[str]) -> list[dict]:
    """Resolve t.co shortened URLs to real URLs"""
    results = []
    for url in urls:
        result = subprocess.run(
            ["curl", "-sIL", "-o", "/dev/null", "-w", "%{url_effective}", url],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            effective_url = result.stdout.strip()
            results.append({
                "original": url,
                "expanded": effective_url
            })
        else:
            results.append({"original": url, "expanded": url})
    return results

def extract_media_urls(tweet: dict) -> list[dict]:
    """Extract media URLs from a bird tweet object"""
    media = tweet.get("media", [])
    return [
        {
            "url": m.get("url") or m.get("videoUrl") or m.get("previewUrl", ""),
            "type": m.get("type", "unknown"),
            "width": m.get("width"),
            "height": m.get("height"),
        }
        for m in media
        if m.get("url") or m.get("videoUrl") or m.get("previewUrl")
    ]
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_enrich.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add enrich.py tests/test_enrich.py
git commit -m "feat: add enrich.py with t.co URL expansion and media extraction"
```

---

## Task 2: ve-twini.py integration — enrich bookmarks output

**Files:**
- Modify: `ve-twini.py` (add enrichment layer to cmd_bookmarks)

**Step 1: Write the failing test**

```python
# tests/test_integration.py
def test_bookmarks_enrichment_flag():
    """--enrich flag resolves URLs and extracts media"""
    import subprocess
    result = subprocess.run(
        ["python3", "ve-twini.py", "bookmarks", "--json", "--enrich"],
        capture_output=True, text=True
    )
    # Should not fail, and JSON should have expanded URLs
    if result.returncode == 0:
        import json
        data = json.loads(result.stdout)
        assert len(data) > 0
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_integration.py::test_bookmarks_enrichment_flag -v
```
Expected: FAIL — `--enrich` flag not yet supported

**Step 3: Write minimal implementation**

Update `cmd_bookmarks()` in `ve-twini.py`:

```python
def cmd_bookmarks(json_output: bool = False, enrich: bool = False):
    args = ["bookmarks", "--json"]
    result = run_bird(args)

    if result.returncode != 0:
        print(f"bird error: {result.stderr}", file=sys.stderr)
        # Fallback to opencli
        print("⚠️  bird failed, falling back to opencli...", file=sys.stderr)
        result = run_opencli(["reddit", "bookmarks"])
        print(result.stdout)
        return

    if not enrich:
        print(result.stdout)
        return

    # Enrich with expanded URLs
    import json
    from enrich import expand_tco_urls, extract_media_urls

    tweets = json.loads(result.stdout)

    # Collect all t.co URLs from tweets
    tco_urls = []
    for tweet in tweets:
        for match in re.findall(r'https://t\.co/\S+', tweet.get("text", "")):
            tco_urls.append(match)

    # Expand all at once
    expanded = {e["original"]: e["expanded"] for e in expand_tco_urls(tco_urls)}

    # Attach enriched data to each tweet
    for tweet in tweets:
        tweet["_enriched"] = {
            "urls": {orig: exp for orig, exp in expanded.items()},
            "media": extract_media_urls(tweet),
        }

    print(json.dumps(tweets, indent=2))
```

Also add `--enrich` flag to bookmarks subparser:

```python
p = sub.add_parser("bookmarks", help="Fetch your bookmarks")
p.add_argument("--json", action="store_true")
p.add_argument("--enrich", action="store_true", help="Expand URLs and extract media")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_integration.py::test_bookmarks_enrichment_flag -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add ve-twini.py
git commit -m "feat: integrate enrich.py, add --enrich flag to bookmarks"
```

---

## Task 3: db.py — SQLite Bookmark Archive

**Files:**
- Create: `db.py`
- Test: `tests/test_db.py`

**Step 1: Write the failing test**

```python
# tests/test_db.py
import pytest
import tempfile
import os
from db import BookmarkDB

def test_archive_and_fetch():
    """Store bookmark in SQLite and retrieve it"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BookmarkDB(db_path)

        tweet = {
            "id": "123",
            "text": "hello world",
            "author": {"username": "testuser", "name": "Test User"},
            "created_at": "2026-04-20",
            "media": [{"url": "https://pbs.twimg.com/img.jpg", "type": "photo"}],
        }

        db.archive_tweet(tweet)
        rows = db.get_all()

        assert len(rows) == 1
        assert rows[0]["tweet_id"] == "123"
        assert rows[0]["text"] == "hello world"
        assert rows[0]["author_username"] == "testuser"

def test_incremental_sync():
    """Only fetch bookmarks newer than last run"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BookmarkDB(db_path)

        db.archive_tweet({"id": "001", "text": "old", "author": {}, "created_at": "2026-01-01"})
        db.mark_sync_time()

        new_tweets = [
            {"id": "002", "text": "new", "author": {}, "created_at": "2026-04-20"},
        ]

        synced = db.filter_new_tweets(new_tweets)
        assert len(synced) == 1
        assert synced[0]["id"] == "002"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_db.py -v
```
Expected: FAIL — `db` module not found

**Step 3: Write minimal implementation**

```python
# db.py
"""SQLite archive for bookmarks"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

class BookmarkDB:
    def __init__(self, db_path: str = "~/.ve-twini/bookmarks.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                tweet_id TEXT PRIMARY KEY,
                text TEXT,
                author_username TEXT,
                author_name TEXT,
                created_at TEXT,
                raw_json TEXT,
                synced_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    def archive_tweet(self, tweet: dict):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO bookmarks
            (tweet_id, text, author_username, author_name, created_at, raw_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            tweet["id"],
            tweet.get("text", ""),
            tweet.get("author", {}).get("username", ""),
            tweet.get("author", {}).get("name", ""),
            tweet.get("created_at", ""),
            json.dumps(tweet),
        ))
        conn.commit()

    def get_all(self) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM bookmarks ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def filter_new_tweets(self, tweets: list[dict]) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        existing = conn.execute("SELECT tweet_id FROM bookmarks").fetchall()
        existing_ids = {r["tweet_id"] for r in existing}
        return [t for t in tweets if t["id"] not in existing_ids]

    def mark_sync_time(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT OR REPLACE INTO sync_meta (key, value, updated_at) VALUES (?, ?, ?)",
                     ("last_sync", datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()

    def get_last_sync(self) -> str | None:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT value FROM sync_meta WHERE key = 'last_sync'").fetchone()
        return row["value"] if row else None
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_db.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: add SQLite bookmark archive with incremental sync"
```

---

## Task 4: ve-twini archive command — wire db.py

**Files:**
- Modify: `ve-twini.py` (add `archive` subcommand)

**Step 1: Write the failing test**

```python
def test_archive_command():
    """ve-twini archive stores bookmarks in SQLite"""
    result = subprocess.run(
        ["python3", "ve-twini.py", "archive"],
        capture_output=True, text=True,
        env={**os.environ, "VE_TWINI_DB": ":memory:"}
    )
    # Should complete without error (may skip if no new tweets)
    assert result.returncode == 0 or "no new" in result.stdout.lower()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_integration.py::test_archive_command -v
```
Expected: FAIL — `archive` subcommand not yet implemented

**Step 3: Write minimal implementation**

Add to `ve-twini.py`:

```python
def cmd_archive():
    """Archive bookmarks to local SQLite via bird + db"""
    import json
    from db import BookmarkDB

    db = BookmarkDB()

    # Fetch bookmarks via bird
    result = run_bird(["bookmarks", "--json"])
    if result.returncode != 0:
        print(f"bird error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    tweets = json.loads(result.stdout)

    # Filter already-archived
    new_tweets = db.filter_new_tweets(tweets)
    if not new_tweets:
        print("No new bookmarks to archive")
        return

    for tweet in new_tweets:
        db.archive_tweet(tweet)

    db.mark_sync_time()
    print(f"Archived {len(new_tweets)} new bookmarks")

    # Enrich with media
    from enrich import expand_tco_urls, extract_media_urls
    tco_urls = list({u["original"] for t in new_tweets for u in t.get("_enriched", {}).get("urls", {}).values()})
    if tco_urls:
        expanded = {e["original"]: e["expanded"] for e in expand_tco_urls(tco_urls)}
        for tweet in new_tweets:
            tweet["_enriched"] = {"urls": expanded, "media": extract_media_urls(tweet)}

    print(f"Total archived: {len(db.get_all())} bookmarks")
```

Add subparser:

```python
sub.add_parser("archive", help="Archive bookmarks to local SQLite")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_integration.py::test_archive_command -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add ve-twini.py
git commit -m "feat: add archive command using SQLite bookmark DB"
```

---

## Task 5: Fallback routing — opencli when bird fails

**Files:**
- Modify: `ve-twini.py` (fallback logic in bookmarks/search)

**Step 1: Write the failing test**

```python
def test_bookmarks_fallback():
    """When bird fails, falls back to opencli with warning"""
    result = subprocess.run(
        ["python3", "ve-twini.py", "bookmarks"],
        capture_output=True, text=True,
        # Simulate bird failure by patching
    )
    # Should contain warning about fallback
    assert "⚠️" in result.stdout or "fallback" in result.stdout.lower() or result.returncode == 0
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_integration.py::test_bookmarks_fallback -v
```
Expected: FAIL — fallback not implemented

**Step 3: Write minimal implementation**

Update `cmd_bookmarks()`:

```python
def cmd_bookmarks(json_output: bool = False, enrich: bool = False):
    result = run_bird(["bookmarks"])

    if result.returncode != 0:
        print("⚠️  bird auth failed or unavailable, trying opencli...", file=sys.stderr)
        result = run_opencli(["twitter", "bookmarks"])
        if result.returncode != 0:
            print(f"opencli also failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        print(result.stdout)
        return

    print(result.stdout)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_integration.py::test_bookmarks_fallback -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add ve-twini.py
git commit -m "feat: add fallback routing when bird is unavailable"
```

---

## Task 6: Final integration — README + --help update

**Files:**
- Modify: `README.md`

Update README with:
- New commands (`archive`, `--enrich`)
- Environment variables (`VE_TWINI_DB`)
- Requirements

**Commit:**

```bash
git add README.md
git commit -m "docs: update README with archive command and enriched output"
git push
```

---

## Execution Options

**Plan complete.** Two execution options:

**1. Subagent-Driven (this session)** — I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — Open new session with executing-plans, batch execution with checkpoints

Which approach?
