# cli-anything-ve-twini

Unified Twitter/X CLI harness — bridges [bird](https://github.com/steipete/bird) (GraphQL API) and [opencli](https://github.com/jackwener/opencli) (browser automation) for complete Twitter workflows.

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
cli-anything-ve-twini bookmarks [--json] [--enrich]
cli-anything-ve-twini post "Hello world"
cli-anything-ve-twini search "AI agents" [--json]
cli-anything-ve-twini auth-check
cli-anything-ve-twini archive
```

## Architecture

```
cli-anything-ve-twini (CLI router)
├── bird subprocess      → bookmarks --json, search, whoami
├── opencli subprocess  → post, browser-gated actions
└── enrich layer       → t.co URL expansion, media URL extraction, SQLite archive
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `VE_TWINI_DB` | `~/.ve-twini/bookmarks.db` | SQLite archive path for `archive` command |

## CLI-Hub

This harness is registered on [CLI-Hub](https://clianything.cc/).
