# ve-twini

> Unified Twitter/X CLI — bridges bird (GraphQL API) and opencli (browser automation) for complete Twitter workflow

## Overview

ve-twini is a thin Python CLI wrapper that unifies two best-of-breed Twitter tools:

- **[bird](https://github.com/steipete/bird)** (`@steipete/bird`) — Twitter GraphQL API CLI with full cookie auth, returns complete tweet objects including media URLs, quoted tweets, author IDs
- **[opencli](https://github.com/jackwener/opencli)** (`@jackwener/opencli`) — Browser automation CLI with Chrome Bridge, for authenticated actions requiring a live browser session

ve-twini routes commands to the appropriate backend, enriches data where possible, and provides a consistent interface.

## Problem

Neither tool alone covers the full Twitter workflow:

| Capability | bird | opencli |
|------------|------|---------|
| Bookmark fetch (full metadata) | ✅ | ❌ |
| Media URLs in response | ✅ | ❌ |
| Quoted tweets | ✅ | ❌ |
| Tweet posting | via API | via browser |
| Browser-gated actions | ❌ | ✅ |
| Twitter login verification | ❌ | ✅ |

## Solution

ve-twini provides a unified interface:

```bash
# Full-featured bookmark fetch (bird data + opencli media enrichment)
ve-twini bookmarks

# Enriched bookmarks — resolve t.co URLs + extract media
ve-twini bookmarks --enrich

# Tweet via browser automation
ve-twini post "Hello from ve-twini"

# Search with dedup
ve-twini search "AI agents"

# Verify auth status across both tools
ve-twini auth-check

# Archive bookmarks to local SQLite (incremental sync)
ve-twini archive

# Set custom archive path
VE_TWINI_DB=/path/to/bookmarks.db ve-twini archive
```

## Source Repos

| Tool | Repo | Purpose |
|------|------|---------|
| **bird** | https://github.com/steipete/bird | GraphQL API access, cookie auth, full tweet objects |
| **opencli** | https://github.com/jackwener/opencli | Browser automation, Chrome Bridge |
| **ve-twini** | https://github.com/collectivewinca/ve-twini | This repo — unified wrapper |

## Installation

```bash
# Requires bird and opencli
npm install -g @jackwener/opencli
pip install bird

# Clone and run
git clone https://github.com/collectivewinca/ve-twini
cd ve-twini
python ve-twini.py --help
```

## Architecture

```
ve-twini (CLI router)
├── bird subprocess      → bookmarks, search, likes, whoami
├── opencli subprocess  → post, browser actions
└── enrich layer        → media URL expansion, dedup, formatting
```

## Status

✅ **Implemented** — All core features complete.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `VE_TWINI_DB` | `~/.ve-twini/bookmarks.db` | SQLite archive path |

See [docs/](docs/) for design documents and implementation plan.
