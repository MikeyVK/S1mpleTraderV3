"""Unit tests for MilestoneConfig singleton (Issue #149, Cycle 1).

@layer: tests
@dependencies: mcp_server.config.milestone_config
@responsibilities: Verify MilestoneConfig loads milestones.yaml (including empty list),
                   validate_milestone() permissive when list empty, singleton behaviour.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
import yaml

from mcp_server.config.milestone_config import MilestoneConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_EMPTY_MILESTONES_YAML = {"version": "1.0", "milestones": []}

_POPULATED_MILESTONES_YAML = {
    "version": "1.0",
    "milestones": [
        {"number": 1, "title": "v1.0", "state": "open"},
        {"number": 2, "title": "v2.0", "state": "closed"},
    ],
}


@pytest.fixture(name="empty_milestones_path")
def _empty_milestones_path() -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fh:
        yaml.dump(_EMPTY_MILESTONES_YAML, fh, allow_unicode=True)
        return Path(fh.name)


@pytest.fixture(name="populated_milestones_path")
def _populated_milestones_path() -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fh:
        yaml.dump(_POPULATED_MILESTONES_YAML, fh, allow_unicode=True)
        return Path(fh.name)


@pytest.fixture(name="empty_milestone_config")
def _empty_milestone_config(empty_milestones_path: Path) -> Generator[MilestoneConfig, None, None]:
    MilestoneConfig.reset_instance()
    cfg = MilestoneConfig.from_file(str(empty_milestones_path))
    yield cfg
    MilestoneConfig.reset_instance()


@pytest.fixture(name="populated_milestone_config")
def _populated_milestone_config(
    populated_milestones_path: Path,
) -> Generator[MilestoneConfig, None, None]:
    MilestoneConfig.reset_instance()
    cfg = MilestoneConfig.from_file(str(populated_milestones_path))
    yield cfg
    MilestoneConfig.reset_instance()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMilestoneConfigFromFile:
    """Loading and singleton behaviour."""

    def test_from_file_loads_empty_list(self, empty_milestone_config: MilestoneConfig) -> None:
        assert empty_milestone_config.milestones == []

    def test_from_file_loads_populated_list(
        self, populated_milestone_config: MilestoneConfig
    ) -> None:
        titles = [m.title for m in populated_milestone_config.milestones]
        assert "v1.0" in titles
        assert "v2.0" in titles

    def test_from_file_raises_on_missing_file(self) -> None:
        MilestoneConfig.reset_instance()
        with pytest.raises(FileNotFoundError, match="Milestone config not found"):
            MilestoneConfig.from_file(".st3/nonexistent_milestones.yaml")

    def test_singleton_returns_same_instance(self, empty_milestones_path: Path) -> None:
        MilestoneConfig.reset_instance()
        cfg1 = MilestoneConfig.from_file(str(empty_milestones_path))
        cfg2 = MilestoneConfig.from_file(str(empty_milestones_path))
        assert cfg1 is cfg2


class TestMilestoneConfigValidateMilestone:
    """validate_milestone() permissive when list empty, strict when populated."""

    def test_validate_milestone_always_true_when_list_empty(
        self, empty_milestone_config: MilestoneConfig
    ) -> None:
        """Permissive: any title passes when milestones list is empty."""
        assert empty_milestone_config.validate_milestone("v99.0") is True
        assert empty_milestone_config.validate_milestone("anything") is True

    def test_validate_milestone_true_for_known_title(
        self, populated_milestone_config: MilestoneConfig
    ) -> None:
        assert populated_milestone_config.validate_milestone("v1.0") is True

    def test_validate_milestone_false_for_unknown_title(
        self, populated_milestone_config: MilestoneConfig
    ) -> None:
        assert populated_milestone_config.validate_milestone("v99.0") is False
