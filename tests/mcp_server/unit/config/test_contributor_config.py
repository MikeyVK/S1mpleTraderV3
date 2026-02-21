"""Unit tests for ContributorConfig singleton (Issue #149, Cycle 1).

@layer: tests
@dependencies: mcp_server.config.contributor_config
@responsibilities: Verify ContributorConfig loads contributors.yaml (including empty list),
                   validate_assignee() permissive when list empty, singleton behaviour.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
import yaml

from mcp_server.config.contributor_config import ContributorConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_EMPTY_CONTRIBUTORS_YAML = {"version": "1.0", "contributors": []}

_POPULATED_CONTRIBUTORS_YAML = {
    "version": "1.0",
    "contributors": [
        {"login": "alice", "name": "Alice Doe"},
        {"login": "bob"},
    ],
}


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
def _empty_contributor_config(
    empty_contributors_path: Path,
) -> Generator[ContributorConfig, None, None]:
    ContributorConfig.reset_instance()
    cfg = ContributorConfig.from_file(str(empty_contributors_path))
    yield cfg
    ContributorConfig.reset_instance()


@pytest.fixture(name="populated_contributor_config")
def _populated_contributor_config(
    populated_contributors_path: Path,
) -> Generator[ContributorConfig, None, None]:
    ContributorConfig.reset_instance()
    cfg = ContributorConfig.from_file(str(populated_contributors_path))
    yield cfg
    ContributorConfig.reset_instance()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestContributorConfigFromFile:
    """Loading and singleton behaviour."""

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
        """name field is optional — bob has no name."""
        bob = next(c for c in populated_contributor_config.contributors if c.login == "bob")
        assert bob.name is None

    def test_from_file_raises_on_missing_file(self) -> None:
        ContributorConfig.reset_instance()
        with pytest.raises(FileNotFoundError, match="Contributor config not found"):
            ContributorConfig.from_file(".st3/nonexistent_contributors.yaml")

    def test_singleton_returns_same_instance(self, empty_contributors_path: Path) -> None:
        ContributorConfig.reset_instance()
        cfg1 = ContributorConfig.from_file(str(empty_contributors_path))
        cfg2 = ContributorConfig.from_file(str(empty_contributors_path))
        assert cfg1 is cfg2


class TestContributorConfigValidateAssignee:
    """validate_assignee() permissive when list empty, strict when populated."""

    def test_validate_assignee_always_true_when_list_empty(
        self, empty_contributor_config: ContributorConfig
    ) -> None:
        """Permissive: any login passes when contributors list is empty."""
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
