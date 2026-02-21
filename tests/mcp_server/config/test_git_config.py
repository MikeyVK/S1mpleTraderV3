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
            "docs": "docs",
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

    # REFACTOR: Test helper methods for GitManager integration
    def test_has_branch_type(self):
        """Test has_branch_type() helper (Convention #1)."""
        config = GitConfig.from_file(".st3/git.yaml")

        # Valid types
        assert config.has_branch_type("feature") is True
        assert config.has_branch_type("fix") is True
        assert config.has_branch_type("epic") is True

        # Invalid types
        assert config.has_branch_type("hotfix") is False
        assert config.has_branch_type("FEATURE") is False  # Case-sensitive

    def test_validate_branch_name(self):
        """Test validate_branch_name() helper (Convention #5)."""
        config = GitConfig.from_file(".st3/git.yaml")

        # Valid names (kebab-case)
        assert config.validate_branch_name("feature-123-name") is True
        assert config.validate_branch_name("fix-bug") is True
        assert config.validate_branch_name("epic-76-tooling") is True

        # Invalid names
        assert config.validate_branch_name("Feature-123") is False  # Uppercase
        assert config.validate_branch_name("feature_123") is False  # Underscore
        assert config.validate_branch_name("feature/123") is False  # Slash

    def test_has_phase(self):
        """Test has_phase() helper (Convention #2)."""
        config = GitConfig.from_file(".st3/git.yaml")

        # Valid phases
        assert config.has_phase("red") is True
        assert config.has_phase("green") is True
        assert config.has_phase("docs") is True

        # Invalid phases
        assert config.has_phase("test") is False
        assert config.has_phase("RED") is False  # Case-sensitive

    def test_get_prefix(self):
        """Test get_prefix() helper (Convention #3)."""
        config = GitConfig.from_file(".st3/git.yaml")

        # Valid mappings
        assert config.get_prefix("red") == "test"
        assert config.get_prefix("green") == "feat"
        assert config.get_prefix("refactor") == "refactor"
        assert config.get_prefix("docs") == "docs"

        # Invalid phase should raise KeyError
        with pytest.raises(KeyError):
            config.get_prefix("invalid")

    def test_is_protected(self):
        """Test is_protected() helper (Convention #4)."""
        config = GitConfig.from_file(".st3/git.yaml")

        # Protected branches
        assert config.is_protected("main") is True
        assert config.is_protected("master") is True
        assert config.is_protected("develop") is True

        # Unprotected branches
        assert config.is_protected("feature-123") is False
        assert config.is_protected("Main") is False  # Case-sensitive
