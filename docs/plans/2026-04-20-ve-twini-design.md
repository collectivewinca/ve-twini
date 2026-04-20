# ve-twini Design

**Date:** 2026-04-20
**Status:** Approved for implementation

## Concept & Vision

A thin Python CLI that routes Twitter/X operations to the best backend (bird for data, opencli for browser actions) while providing a unified, enriched output format. The goal is to never lose tweet metadata like media URLs or quoted tweets, while enabling full Twitter workflows including authenticated posting.

## Design Principles

1. **Delegate to strengths** — bird owns data queries, opencli owns browser actions
2. **Enrich, don't replace** — ve-twini wraps outputs, adds value (URL expansion, dedup, formatting)
3. **Fail gracefully** — if one backend is missing, fall back to the other with a warning
4. **Zero config for common cases** — auto-detect bird/opencli paths, use environment

## Architecture

```
User
  │
  ▼
ve-twini.py (main CLI)
  │
  ├─► bird subprocess ───► bookmark/search/likes/whoami
  │                       (returns complete JSON)
  │
  ├─► opencli subprocess ──► post/browser actions
  │                        (uses Chrome Bridge)
  │
  └─► enrich layer
        │   (expand t.co URLs, merge media, dedup)
        ▼
    unified JSON output
```

## Commands

### `ve-twini bookmarks [--json]`
- Routes to `bird bookmarks --json`
- Parses JSON output from bird
- Enriches with: expanded URLs (resolves t.co), media objects with full URLs
- Returns unified format

### `ve-twini post <text>`
- Routes to opencli for browser-based posting
- Or routes to `bird tweet <text>` if cookie auth is available
- Falls back to browser if API fails

### `ve-twini search <query>`
- Routes to `bird search <query> --json`
- Deduplicates by tweet ID
- Enriches with expanded URLs

### `ve-twini auth-check`
- Checks: `bird whoami` and `opencli browser state`
- Reports auth status for both tools

### `ve-twini archive`
- Fetches all bookmarks via bird
- Stores to local SQLite: tweet_id, text, author, created_at, media_urls, raw_json
- Supports incremental sync (only new bookmarks since last run)

## Data Model

```python
Tweet = {
    "id": str,
    "text": str,
    "created_at": str,
    "author": {"username": str, "name": str},
    "author_id": str,
    "media": [{"url": str, "type": str, "width": int, "height": int}],
    "quoted_tweet": Tweet | None,
    "urls": [{"expanded": str, "display": str}],
}
```

## Fallback Strategy

| Command | Primary | Fallback |
|---------|---------|----------|
| bookmarks | bird | opencli (incomplete) + warning |
| post | opencli (browser) | bird (API) |
| search | bird | opencli (incomplete) |
| auth-check | bird + opencli | report which is available |

## File Structure

```
ve-twini/
├── ve-twini.py           # Main CLI entry point
├── enrich.py             # URL expansion, media merge
├── db.py                 # SQLite archive (optional)
├── bird_wrapper.py       # bird subprocess wrapper
├── opencli_wrapper.py    # opencli subprocess wrapper
├── README.md
└── docs/
    └── 2026-04-20-ve-twini-design.md
```

## Tech Stack

- **Python 3.11+** (no external deps beyond stdlib + bird + opencli)
- **SQLite** via `sqlite3` (stdlib)
- **Subprocess** for wrapping bird/opencli

## Out of Scope (v1)

- Posting with media (just text)
- Thread creation
- Auto-scheduling
- Cross-posting to other platforms
