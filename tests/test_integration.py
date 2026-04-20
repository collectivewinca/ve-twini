import io
import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

import importlib.util
spec = importlib.util.spec_from_file_location("ve_twini", str(__file__).rsplit("/", 2)[0] + "/ve-twini.py")
ve_twini = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ve_twini)

cmd_bookmarks = ve_twini.cmd_bookmarks
cmd_archive = ve_twini.cmd_archive
BookmarkDB = ve_twini.BookmarkDB


class TestEnrichIntegration:

    def test_enrich_adds_enriched_key(self):
        mock_result = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {"id": "1", "text": "Check this https://t.co/abc123 video", "media": []}
            ])
        )

        with patch.object(ve_twini, 'run_bird', return_value=mock_result), \
             patch.object(ve_twini, 'expand_tco_urls') as mock_expand, \
             patch.object(ve_twini, 'extract_media_urls') as mock_extract:

            mock_expand.return_value = [{"original": "https://t.co/abc123", "expanded": "https://example.com/video"}]
            mock_extract.return_value = [{"url": "https://pbs.twimg.com/media/img.jpg", "type": "photo", "width": 1200, "height": 675}]

            captured = io.StringIO()
            with patch.object(sys, 'stdout', captured):
                cmd_bookmarks(json_output=False, enrich=True)
                output = captured.getvalue()

        result = json.loads(output)
        assert "_enriched" in result[0]
        assert result[0]["_enriched"]["urls"][0]["expanded"] == "https://example.com/video"
        assert result[0]["_enriched"]["media"][0]["type"] == "photo"

    def test_enrich_parses_tco_urls(self):
        mock_result = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {"id": "2", "text": "Link https://t.co/xyz789 and https://t.co/aaa111", "media": []}
            ])
        )

        with patch.object(ve_twini, 'run_bird', return_value=mock_result), \
             patch.object(ve_twini, 'expand_tco_urls') as mock_expand, \
             patch.object(ve_twini, 'extract_media_urls') as mock_extract:

            mock_expand.return_value = [
                {"original": "https://t.co/xyz789", "expanded": "https://first.com"},
                {"original": "https://t.co/aaa111", "expanded": "https://second.com"}
            ]
            mock_extract.return_value = []

            captured = io.StringIO()
            with patch.object(sys, 'stdout', captured):
                cmd_bookmarks(json_output=False, enrich=True)
                output = captured.getvalue()

        result = json.loads(output)
        assert len(result[0]["_enriched"]["urls"]) == 2

    def test_enrich_extracts_media(self):
        mock_result = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {"id": "3", "text": "Photo post", "media": [
                    {"url": "https://pbs.twimg.com/media/1.jpg", "type": "photo", "width": 800, "height": 600},
                    {"url": "https://pbs.twimg.com/media/2.jpg", "type": "photo", "width": 1200, "height": 900}
                ]}
            ])
        )

        with patch.object(ve_twini, 'run_bird', return_value=mock_result), \
             patch.object(ve_twini, 'expand_tco_urls') as mock_expand, \
             patch.object(ve_twini, 'extract_media_urls') as mock_extract:

            mock_expand.return_value = []
            mock_extract.return_value = [
                {"url": "https://pbs.twimg.com/media/1.jpg", "type": "photo", "width": 800, "height": 600},
                {"url": "https://pbs.twimg.com/media/2.jpg", "type": "photo", "width": 1200, "height": 900}
            ]

            captured = io.StringIO()
            with patch.object(sys, 'stdout', captured):
                cmd_bookmarks(json_output=False, enrich=True)
                output = captured.getvalue()

        result = json.loads(output)
        assert len(result[0]["_enriched"]["media"]) == 2

    def test_enrich_false_prints_raw_json(self):
        raw = '[{"id": "5", "text": "raw"}]'
        mock_result = MagicMock(returncode=0, stdout=raw)

        with patch.object(ve_twini, 'run_bird', return_value=mock_result):
            captured = io.StringIO()
            with patch.object(sys, 'stdout', captured):
                cmd_bookmarks(json_output=False, enrich=False)
                output = captured.getvalue()

        assert output.strip() == raw

    def test_both_bird_and_opencli_fail(self):
        bird_fail = MagicMock(returncode=1, stderr="bird auth error")
        opencli_fail = MagicMock(returncode=1, stderr="opencli error")

        with patch.object(ve_twini, 'run_bird', return_value=bird_fail), \
             patch.object(ve_twini, 'run_opencli', return_value=opencli_fail):
            with pytest.raises(SystemExit) as exc:
                cmd_bookmarks(json_output=False, enrich=False)
            assert exc.value.code == 1

    def test_bird_fallback_to_opencli_succeeds(self):
        bird_fail = MagicMock(returncode=1, stderr="auth required")
        opencli_success = MagicMock(returncode=0, stdout='[{"id": "7", "text": "from opencli"}]')

        with patch.object(ve_twini, 'run_bird', return_value=bird_fail), \
             patch.object(ve_twini, 'run_opencli', return_value=opencli_success):
            captured = io.StringIO()
            with patch.object(sys, 'stdout', captured):
                cmd_bookmarks(json_output=False, enrich=False)
            output = captured.getvalue()

        assert '{"id": "7", "text": "from opencli"}' in output

    def test_bird_fallback_to_opencli_enrich_flag_ignored(self):
        bird_fail = MagicMock(returncode=1, stderr="auth required")
        opencli_success = MagicMock(returncode=0, stdout='[{"id": "8", "text": "https://t.co/abc opencli"}]')

        with patch.object(ve_twini, 'run_bird', return_value=bird_fail), \
             patch.object(ve_twini, 'run_opencli', return_value=opencli_success):
            captured = io.StringIO()
            with patch.object(sys, 'stdout', captured):
                cmd_bookmarks(json_output=False, enrich=True)
            output = captured.getvalue()

        result = json.loads(output)
        assert result[0]["id"] == "8"
        assert "_enriched" not in result[0]


class TestArchiveIntegration:

    def test_archive_archives_new_tweets(self, tmp_path):
        tweets = [
            {"id": "1", "text": "Hello", "author_username": "user1", "author_name": "User One", "created_at": "2024-01-01T00:00:00Z"},
            {"id": "2", "text": "World", "author_username": "user2", "author_name": "User Two", "created_at": "2024-01-02T00:00:00Z"},
        ]
        mock_result = MagicMock(returncode=0, stdout=json.dumps(tweets))

        with patch.object(ve_twini, 'run_bird', return_value=mock_result), \
             patch.dict(os.environ, {"VE_TWINI_DB": str(tmp_path / "test.db")}):
            captured = io.StringIO()
            with patch.object(sys, 'stdout', captured):
                cmd_archive()
            output = captured.getvalue()

        assert "Archived 2 new bookmarks" in output

    def test_archive_no_new_tweets(self, tmp_path):
        existing_tweets = [
            {"id": "1", "text": "Existing", "author_username": "user1", "author_name": "User One", "created_at": "2024-01-01T00:00:00Z"},
        ]
        db = BookmarkDB(str(tmp_path / "test.db"))
        for t in existing_tweets:
            db.archive_tweet(t)

        all_tweets = [
            {"id": "1", "text": "Existing", "author_username": "user1", "author_name": "User One", "created_at": "2024-01-01T00:00:00Z"},
            {"id": "2", "text": "New", "author_username": "user2", "author_name": "User Two", "created_at": "2024-01-02T00:00:00Z"},
        ]
        mock_result = MagicMock(returncode=0, stdout=json.dumps(all_tweets))

        with patch.object(ve_twini, 'run_bird', return_value=mock_result), \
             patch.dict(os.environ, {"VE_TWINI_DB": str(tmp_path / "test.db")}):
            captured = io.StringIO()
            with patch.object(sys, 'stdout', captured):
                cmd_archive()
            output = captured.getvalue()

        assert "Archived 1 new bookmarks" in output

    def test_archive_all_already_archived(self, tmp_path):
        existing_tweet = {"id": "1", "text": "Already saved", "author_username": "user1", "author_name": "User One", "created_at": "2024-01-01T00:00:00Z"}
        db = BookmarkDB(str(tmp_path / "test.db"))
        db.archive_tweet(existing_tweet)

        mock_result = MagicMock(returncode=0, stdout=json.dumps([existing_tweet]))

        with patch.object(ve_twini, 'run_bird', return_value=mock_result), \
             patch.dict(os.environ, {"VE_TWINI_DB": str(tmp_path / "test.db")}):
            captured = io.StringIO()
            with patch.object(sys, 'stdout', captured):
                cmd_archive()
            output = captured.getvalue()

        assert "No new bookmarks to archive" in output

    def test_archive_bird_error_exits(self):
        mock_result = MagicMock(returncode=1, stderr="auth required")

        with patch.object(ve_twini, 'run_bird', return_value=mock_result):
            with pytest.raises(SystemExit) as exc:
                cmd_archive()
            assert exc.value.code == 1