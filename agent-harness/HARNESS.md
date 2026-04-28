# ve-twini Harness

## Overview

`cli-anything-ve-twini` is a Click-based CLI harness that wraps the `ve-twini` Python CLI (which itself wraps `bird` and `opencli` as subprocesses). This harness exposes the same commands as `ve-twini` but conforms to the CLI-Anything convention with a `click`-based entry point.

## Architecture

```
cli-anything-ve-twini (Click CLI)
└── subprocess calls to:
    ├── bird         → bookmarks, search, expand, whoami
    └── opencli     → post, browser-gated actions
        └── SQLite  → archive deduplication
```

## Commands

| Command | Backend | Description |
|---------|---------|-------------|
| `bookmarks [--json] [--enrich]` | bird → opencli fallback | Fetch Twitter bookmarks |
| `post <text>` | opencli | Post tweet via browser automation |
| `search <query> [--json]` | bird | Search tweets via GraphQL |
| `auth-check` | bird + opencli | Verify auth for both tools |
| `archive` | bird → SQLite | Incremental bookmark archiver |

## Design Decisions

1. **Thin wrapper** — harness delegates to existing `ve-twini.py` logic via replicated function calls. No changes to upstream `ve-twini` are required.
2. **Inline enrichment** — t.co URL expansion and media extraction are inlined in `__main__.py` rather than importing from the local `enrich.py` (which is outside the package).
3. **SQLite bundled** — archive logic is self-contained to avoid cross-package imports from the parent repo.
4. **No extra dependencies** — only `click>=8.0.0` is required beyond the standard library.

## Maintenance

When `ve-twini` adds new commands, add corresponding Click subcommands in `__main__.py` following the existing patterns above.
