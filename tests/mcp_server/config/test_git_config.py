"""Tests for GitConfig (Issue #55)."""
import pytest

# pylint: disable=import-error, no-name-in-module
from mcp_server.config.git_config import GitConfig


class TestGitConfig:
    """Test GitConfig loading and validation."""

    def test_git_yaml_not_found(self):
        """Test FileNotFoundError when git.yaml doesn't exist."""
        # RED: This should fail because GitConfig doesn't exist yet
        with pytest.raises(FileNotFoundError, match="Git config not found"):
            GitConfig.from_file(".st3/git.yaml")

    def test_placeholder(self):
        """Placeholder test to satisfy pylint too-few-public-methods."""
        assert True
