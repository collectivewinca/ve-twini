---
name: >-
  cli-anything-ve-twini
description: >-
  Unified Twitter/X CLI harness bridging bird (GraphQL API) and opencli (browser automation) for complete Twitter workflows. Use when you need to fetch bookmarks, post tweets, search, check auth, or archive bookmarks to SQLite.
---

# cli-anything-ve-twini

Unified Twitter/X CLI bridging bird (GraphQL API) and opencli (browser automation) for complete Twitter workflows.

## Installation

```bash
pip install cli-anything-ve-twini
```

**Prerequisites:**
- Python 3.10+
- `bird` CLI (`pip install bird`) with valid Twitter cookies
- `opencli` CLI (`npm install -g @jackwener/opencli`) with Chrome Bridge connected

## Usage

```bash
# Show help
cli-anything-ve-twini --help

# Fetch bookmarks (JSON from bird)
cli-anything-ve-twini bookmarks --json

# Enriched bookmarks — resolve t.co URLs + extract media
cli-anything-ve-twini bookmarks --enrich

# Post a tweet via browser automation
cli-anything-ve-twini post "Hello from ve-twini"

# Search tweets via bird
cli-anything-ve-twini search "AI agents"

# Check auth status for both bird and opencli
cli-anything-ve-twini auth-check

# Archive bookmarks to local SQLite (incremental sync)
cli-anything-ve-twini archive
```

## Command Reference

| Command | Description |
|---------|-------------|
| `bookmarks [--json] [--enrich]` | Fetch Twitter bookmarks via bird, optionally enrich with media URLs |
| `post <text>` | Post a tweet via opencli browser automation |
| `search <query> [--json]` | Search tweets via bird GraphQL API |
| `auth-check` | Verify auth status for both bird and opencli |
| `archive` | Incremental bookmark archiver — deduplicates against local SQLite |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `VE_TWINI_DB` | `~/.ve-twini/bookmarks.db` | SQLite archive path for `archive` command |

## Architecture

```
cli-anything-ve-twini (CLI router)
├── bird subprocess      → bookmarks --json, search, whoami
├── opencli subprocess → post, browser-gated actions
└── enrich layer       → t.co URL expansion, media URL extraction, SQLite archive
```

## For AI Agents

1. Always use `--json` flag on `bookmarks` and `search` for parseable output
2. Check return codes — 0 for success, non-zero for errors
3. `bird` provides full tweet objects with media URLs; `opencli` provides browser-gated actions
4. `archive` is idempotent — safe to re-run; only new bookmarks are inserted
5. Run `auth-check` first to verify both tools are authenticated before other commands

## Version

1.0.0
