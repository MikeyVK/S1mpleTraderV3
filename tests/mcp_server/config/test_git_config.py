"""Tests for GitConfig (Issue #55)."""
import pytest

from mcp_server.config.git_config import GitConfig


class TestGitConfig:
    """Test GitConfig loading and validation."""

    def teardown_method(self):
        """Reset singleton after each test."""
        GitConfig.reset_instance()

    def test_load_git_yaml_success(self):
        """Test loading existing git.yaml file."""
        # GREEN: Now that GitConfig exists, test successful loading
        config = GitConfig.from_file(".st3/git.yaml")

        # Verify all conventions loaded correctly
        assert config.branch_types == ["feature", "fix", "refactor", "docs", "epic"]
        assert config.tdd_phases == ["red", "green", "refactor", "docs"]
        assert config.commit_prefix_map == {
            "red": "test",
            "green": "feat",
            "refactor": "refactor",
            "docs": "docs"
        }
        assert config.protected_branches == ["main", "master", "develop"]
        assert config.branch_name_pattern == r"^[a-z0-9-]+$"
        assert config.default_base_branch == "main"

    def test_git_yaml_not_found(self):
        """Test FileNotFoundError when git.yaml doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Git config not found"):
            GitConfig.from_file(".st3/nonexistent.yaml")

    def test_singleton_pattern(self):
        """Test singleton behavior - same instance returned."""
        config1 = GitConfig.from_file(".st3/git.yaml")
        config2 = GitConfig.from_file(".st3/git.yaml")

        assert config1 is config2  # Same object instance
