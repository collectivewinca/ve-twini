import os
import tempfile
from datetime import datetime
from db import BookmarkDB


def test_archive_and_fetch():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = BookmarkDB(os.path.join(tmpdir, "test.db"))

        tweet = {
            "id": "123",
            "text": "Hello world",
            "author_username": "testuser",
            "author_name": "Test User",
            "created_at": "2025-01-01T00:00:00Z",
        }

        db.archive_tweet(tweet)
        results = db.get_all()

        assert len(results) == 1
        assert results[0]["tweet_id"] == "123"
        assert results[0]["text"] == "Hello world"
        assert results[0]["author_username"] == "testuser"


def test_incremental_sync():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = BookmarkDB(os.path.join(tmpdir, "test.db"))

        old_tweet = {
            "id": "100",
            "text": "Old tweet",
            "author_username": "user1",
            "author_name": "User One",
            "created_at": "2025-01-01T00:00:00Z",
        }
        db.archive_tweet(old_tweet)

        new_tweets = [
            {
                "id": "100",
                "text": "Old tweet (updated)",
                "author_username": "user1",
                "author_name": "User One",
                "created_at": "2025-01-01T00:00:00Z",
            },
            {
                "id": "200",
                "text": "New tweet",
                "author_username": "user2",
                "author_name": "User Two",
                "created_at": "2025-01-02T00:00:00Z",
            },
        ]

        filtered = db.filter_new_tweets(new_tweets)
        assert len(filtered) == 1
        assert filtered[0]["id"] == "200"

        db.mark_sync_time()
        last_sync = db.get_last_sync()
        assert last_sync is not None

        last_sync_time = datetime.fromisoformat(last_sync)
        assert (datetime.utcnow() - last_sync_time).total_seconds() < 5