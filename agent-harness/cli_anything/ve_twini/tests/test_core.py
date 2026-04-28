"""Unit tests for cli-anything-ve-twini — no bird/opencli needed."""

import json
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from cli_anything.ve_twini.__main__ import cli


@pytest.fixture
def runner():
    return CliRunner()


# ── bookmarks ─────────────────────────────────────────────────────────

class TestBookmarks:
    @patch("cli_anything.ve_twini.__main__._run_bird")
    def test_bookmarks_json_success(self, mock_run_bird, runner):
        mock_run_bird.return_value = (0, '[{"id": "123", "text": "hello"}]', "")
        result = runner.invoke(cli, ["bookmarks", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["id"] == "123"

    @patch("cli_anything.ve_twini.__main__._run_bird")
    @patch("cli_anything.ve_twini.__main__._run_opencli")
    def test_bookmarks_bird_falls_back_to_opencli(self, mock_run_opencli, mock_run_bird, runner):
        mock_run_bird.return_value = (1, "", "auth failed")
        mock_run_opencli.return_value = (0, "bookmarks via opencli", "")
        result = runner.invoke(cli, ["bookmarks"])
        assert result.exit_code == 0

    @patch("cli_anything.ve_twini.__main__._run_bird")
    def test_bookmarks_both_fail(self, mock_run_bird, runner):
        mock_run_bird.return_value = (1, "", "auth failed")
        with patch("cli_anything.ve_twini.__main__._run_opencli") as m:
            m.return_value = (1, "", "opencli also failed")
            result = runner.invoke(cli, ["bookmarks"])
        assert result.exit_code == 1


# ── post ─────────────────────────────────────────────────────────────

class TestPost:
    @patch("cli_anything.ve_twini.__main__._run_opencli")
    def test_post_success(self, mock_run_opencli, runner):
        mock_run_opencli.return_value = (0, "posted!", "")
        result = runner.invoke(cli, ["post", "Hello world"])
        assert result.exit_code == 0

    @patch("cli_anything.ve_twini.__main__._run_opencli")
    def test_post_failure(self, mock_run_opencli, runner):
        mock_run_opencli.return_value = (1, "", "browser error")
        result = runner.invoke(cli, ["post", "Hello world"])
        assert result.exit_code == 1


# ── search ───────────────────────────────────────────────────────────

class TestSearch:
    @patch("cli_anything.ve_twini.__main__._run_bird")
    def test_search_success(self, mock_run_bird, runner):
        mock_run_bird.return_value = (0, '[{"id": "456", "text": "AI agents"}]', "")
        result = runner.invoke(cli, ["search", "AI agents"])
        assert result.exit_code == 0
        assert "456" in result.output

    @patch("cli_anything.ve_twini.__main__._run_bird")
    def test_search_json_flag(self, mock_run_bird, runner):
        mock_run_bird.return_value = (0, '[{"id": "789"}]', "")
        result = runner.invoke(cli, ["search", "AI agents", "--json"])
        assert result.exit_code == 0

    @patch("cli_anything.ve_twini.__main__._run_bird")
    def test_search_bird_error(self, mock_run_bird, runner):
        mock_run_bird.return_value = (1, "", "network error")
        result = runner.invoke(cli, ["search", "AI agents"])
        assert result.exit_code == 1


# ── auth-check ────────────────────────────────────────────────────────

class TestAuthCheck:
    @patch("cli_anything.ve_twini.__main__._run_bird")
    @patch("cli_anything.ve_twini.__main__._run_opencli")
    def test_auth_check_all_ok(self, mock_opencli, mock_bird, runner):
        mock_bird.return_value = (0, "user123", "")
        mock_opencli.return_value = (0, "Extension: connected", "")
        result = runner.invoke(cli, ["auth-check"])
        assert result.exit_code == 0
        assert "Auth OK" in result.output
        assert "Chrome Bridge connected" in result.output

    @patch("cli_anything.ve_twini.__main__._run_bird")
    @patch("cli_anything.ve_twini.__main__._run_opencli")
    def test_auth_check_bird_fail(self, mock_opencli, mock_bird, runner):
        mock_bird.return_value = (1, "", "not logged in")
        mock_opencli.return_value = (0, "Extension: connected", "")
        result = runner.invoke(cli, ["auth-check"])
        assert result.exit_code == 0
        assert "Not authenticated" in result.output


# ── archive ──────────────────────────────────────────────────────────

class TestArchive:
    @patch("cli_anything.ve_twini.__main__._run_bird")
    def test_archive_new_tweets(self, mock_run_bird, runner, tmp_path):
        import os
        db_path = str(tmp_path / "test.db")
        with patch.dict("os.environ", {"VE_TWINI_DB": db_path}):
            mock_run_bird.return_value = (
                0,
                json.dumps([{"id": "1", "text": "hello", "author_username": "u", "author_name": "n"}]),
                "",
            )
            with patch("cli_anything.ve_twini.__main__._filter_new_tweets") as m_filter:
                m_filter.return_value = [{"id": "1", "text": "hello", "author_username": "u", "author_name": "n"}]
                result = runner.invoke(cli, ["archive"])
            assert result.exit_code == 0
            assert "Archived" in result.output

    @patch("cli_anything.ve_twini.__main__._run_bird")
    def test_archive_no_new_tweets(self, mock_run_bird, runner, tmp_path):
        db_path = str(tmp_path / "test.db")
        with patch.dict("os.environ", {"VE_TWINI_DB": db_path}):
            mock_run_bird.return_value = (0, json.dumps([]), "")
            with patch("cli_anything.ve_twini.__main__._filter_new_tweets") as m_filter:
                m_filter.return_value = []
                result = runner.invoke(cli, ["archive"])
            assert result.exit_code == 0
            assert "No new bookmarks" in result.output

    @patch("cli_anything.ve_twini.__main__._run_bird")
    def test_archive_bird_error(self, mock_run_bird, runner):
        mock_run_bird.return_value = (1, "", "bird error")
        result = runner.invoke(cli, ["archive"])
        assert result.exit_code == 1
