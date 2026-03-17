"""Tests for GitConfig (Issue #55)."""

from pathlib import Path

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import GitConfig
from mcp_server.core.exceptions import ConfigError


def _load_git_config(config_path: Path | None = None) -> GitConfig:
    if config_path is None:
        return ConfigLoader(Path(".st3/config")).load_git_config()
    return ConfigLoader(config_path.parent).load_git_config(config_path=config_path)


class TestGitConfig:
    """Test GitConfig loading and validation."""

    def test_load_git_yaml_success(self) -> None:
        """Test loading existing git.yaml file."""
        config = _load_git_config()

        assert config.branch_types == [
            "feature",
            "bug",
            "fix",
            "refactor",
            "docs",
            "hotfix",
            "epic",
        ]
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

    def test_git_yaml_not_found(self) -> None:
        """Test ConfigError when git.yaml doesn't exist."""
        with pytest.raises(ConfigError, match="Config file not found"):
            _load_git_config(Path(".st3/nonexistent.yaml"))

    def test_repeated_loads_are_equivalent(self) -> None:
        """Repeated loads of the same file should be value-equivalent."""
        config1 = _load_git_config()
        config2 = _load_git_config()

        assert config1 == config2

    def test_has_branch_type(self) -> None:
        """Test has_branch_type() helper (Convention #1)."""
        config = _load_git_config()

        assert config.has_branch_type("feature") is True
        assert config.has_branch_type("bug") is True
        assert config.has_branch_type("fix") is True
        assert config.has_branch_type("hotfix") is True
        assert config.has_branch_type("epic") is True
        assert config.has_branch_type("FEATURE") is False

    def test_validate_branch_name(self) -> None:
        """Test validate_branch_name() helper (Convention #5)."""
        config = _load_git_config()

        assert config.validate_branch_name("feature-123-name") is True
        assert config.validate_branch_name("fix-bug") is True
        assert config.validate_branch_name("epic-76-tooling") is True
        assert config.validate_branch_name("Feature-123") is False
        assert config.validate_branch_name("feature_123") is False
        assert config.validate_branch_name("feature/123") is False

    def test_has_phase(self) -> None:
        """Test has_phase() helper (Convention #2)."""
        config = _load_git_config()

        assert config.has_phase("red") is True
        assert config.has_phase("green") is True
        assert config.has_phase("docs") is True
        assert config.has_phase("test") is False
        assert config.has_phase("RED") is False

    def test_get_prefix(self) -> None:
        """Test get_prefix() helper (Convention #3)."""
        config = _load_git_config()

        assert config.get_prefix("red") == "test"
        assert config.get_prefix("green") == "feat"
        assert config.get_prefix("refactor") == "refactor"
        assert config.get_prefix("docs") == "docs"

        with pytest.raises(KeyError):
            config.get_prefix("invalid")

    def test_extract_issue_number_returns_int_for_supported_branch_names(self) -> None:
        """extract_issue_number() should parse the numeric issue id from branch names."""
        config = _load_git_config()

        assert config.extract_issue_number("feature/42-test-branch") == 42
        assert config.extract_issue_number("fix/7-hot-patch") == 7
        assert config.extract_issue_number("docs/120-refresh-readme") == 120

    def test_extract_issue_number_returns_none_for_invalid_branch_names(self) -> None:
        """extract_issue_number() should degrade gracefully when no issue id is present."""
        config = _load_git_config()

        assert config.extract_issue_number("main") is None
        assert config.extract_issue_number("feature/no-number") is None
        assert config.extract_issue_number("unknown/42-test") is None

    def test_is_protected(self) -> None:
        """Test is_protected() helper (Convention #4)."""
        config = _load_git_config()

        assert config.is_protected("main") is True
        assert config.is_protected("master") is True
        assert config.is_protected("develop") is True
        assert config.is_protected("feature-123") is False
        assert config.is_protected("Main") is False
