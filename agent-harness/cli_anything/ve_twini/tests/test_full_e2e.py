"""E2E tests for cli-anything-ve-twini — requires bird and opencli installed."""

import pytest
from click.testing import CliRunner
from cli_anything.ve_twini.__main__ import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.mark.e2e
class TestE2E:
    def test_bookmarks_command_runs(self, runner):
        result = runner.invoke(cli, ["bookmarks", "--help"])
        assert result.exit_code == 0

    def test_post_command_runs(self, runner):
        result = runner.invoke(cli, ["post", "--help"])
        assert result.exit_code == 0

    def test_search_command_runs(self, runner):
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0

    def test_auth_check_command_runs(self, runner):
        result = runner.invoke(cli, ["auth-check", "--help"])
        assert result.exit_code == 0

    def test_archive_command_runs(self, runner):
        result = runner.invoke(cli, ["archive", "--help"])
        assert result.exit_code == 0
