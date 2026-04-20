import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class BookmarkDB:
    def __init__(self, db_path: str = "~/.ve-twini/bookmarks.db"):
        self.db_path = os.path.expanduser(db_path)
        self._init()

    def _init(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def archive_tweet(self, tweet: dict) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO bookmarks (
                tweet_id, text, author_username, author_name,
                created_at, raw_json, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tweet.get("id"),
            tweet.get("text"),
            tweet.get("author_username"),
            tweet.get("author_name"),
            tweet.get("created_at"),
            json.dumps(tweet),
            datetime.utcnow().isoformat(),
        ))
        conn.commit()
        conn.close()

    def get_all(self) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM bookmarks ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def filter_new_tweets(self, tweets: list[dict]) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT tweet_id FROM bookmarks")
        existing_ids = {row[0] for row in cursor.fetchall()}
        conn.close()
        return [t for t in tweets if t.get("id") not in existing_ids]

    def mark_sync_time(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO sync_meta (key, value, updated_at)
            VALUES ('last_sync', ?, ?)
        """, (now, now))
        conn.commit()
        conn.close()

    def get_last_sync(self) -> str | None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT value FROM sync_meta WHERE key = 'last_sync'
        """)
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None