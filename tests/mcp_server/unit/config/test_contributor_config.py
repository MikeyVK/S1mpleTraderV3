"""Unit tests for ContributorConfig loader-based access (Issue #149, Cycle 1).

@layer: tests
@dependencies: mcp_server.config.loader
@responsibilities: Verify ContributorConfig loads contributors.yaml (including empty list),
                   validate_assignee() permissive when list empty, strict when populated.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import ContributorConfig
from mcp_server.core.exceptions import ConfigError

_EMPTY_CONTRIBUTORS_YAML = {"version": "1.0", "contributors": []}

_POPULATED_CONTRIBUTORS_YAML = {
    "version": "1.0",
    "contributors": [
        {"login": "alice", "name": "Alice Doe"},
        {"login": "bob"},
    ],
}


def _load_contributor_config(config_path: Path) -> ContributorConfig:
    return ConfigLoader(config_path.parent).load_contributor_config(config_path=config_path)


@pytest.fixture(name="empty_contributors_path")
def _empty_contributors_path() -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fh:
        yaml.dump(_EMPTY_CONTRIBUTORS_YAML, fh, allow_unicode=True)
        return Path(fh.name)


@pytest.fixture(name="populated_contributors_path")
def _populated_contributors_path() -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fh:
        yaml.dump(_POPULATED_CONTRIBUTORS_YAML, fh, allow_unicode=True)
        return Path(fh.name)


@pytest.fixture(name="empty_contributor_config")
def _empty_contributor_config(empty_contributors_path: Path) -> ContributorConfig:
    return _load_contributor_config(empty_contributors_path)


@pytest.fixture(name="populated_contributor_config")
def _populated_contributor_config(populated_contributors_path: Path) -> ContributorConfig:
    return _load_contributor_config(populated_contributors_path)


class TestContributorConfigFromFile:
    """Loading behaviour through ConfigLoader."""

    def test_from_file_loads_empty_list(self, empty_contributor_config: ContributorConfig) -> None:
        assert empty_contributor_config.contributors == []

    def test_from_file_loads_populated_list(
        self, populated_contributor_config: ContributorConfig
    ) -> None:
        logins = [c.login for c in populated_contributor_config.contributors]
        assert "alice" in logins
        assert "bob" in logins

    def test_from_file_contributor_name_is_optional(
        self, populated_contributor_config: ContributorConfig
    ) -> None:
        """name field is optional; bob has no name."""
        bob = next(c for c in populated_contributor_config.contributors if c.login == "bob")
        assert bob.name is None

    def test_from_file_raises_on_missing_file(self) -> None:
        with pytest.raises(ConfigError, match="Config file not found"):
            _load_contributor_config(Path(".st3/nonexistent_contributors.yaml"))

    def test_repeated_loads_are_equivalent(self, empty_contributors_path: Path) -> None:
        cfg1 = _load_contributor_config(empty_contributors_path)
        cfg2 = _load_contributor_config(empty_contributors_path)
        assert cfg1 == cfg2


class TestContributorConfigValidateAssignee:
    """validate_assignee() permissive when list empty, strict when populated."""

    def test_validate_assignee_always_true_when_list_empty(
        self, empty_contributor_config: ContributorConfig
    ) -> None:
        assert empty_contributor_config.validate_assignee("anyone") is True
        assert empty_contributor_config.validate_assignee("unknown-user") is True

    def test_validate_assignee_true_for_known_login(
        self, populated_contributor_config: ContributorConfig
    ) -> None:
        assert populated_contributor_config.validate_assignee("alice") is True

    def test_validate_assignee_false_for_unknown_login(
        self, populated_contributor_config: ContributorConfig
    ) -> None:
        assert populated_contributor_config.validate_assignee("charlie") is False

    def test_validate_assignee_is_case_sensitive(
        self, populated_contributor_config: ContributorConfig
    ) -> None:
        assert populated_contributor_config.validate_assignee("Alice") is False
