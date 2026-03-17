"""Unit tests for MilestoneConfig loader-based access (Issue #149, Cycle 1)."""

import tempfile
from pathlib import Path

import pytest
import yaml

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import MilestoneConfig
from mcp_server.core.exceptions import ConfigError

_EMPTY_MILESTONES_YAML = {"version": "1.0", "milestones": []}

_POPULATED_MILESTONES_YAML = {
    "version": "1.0",
    "milestones": [
        {"number": 1, "title": "v1.0", "state": "open"},
        {"number": 2, "title": "v2.0", "state": "closed"},
    ],
}


def _load_milestone_config(config_path: Path) -> MilestoneConfig:
    return ConfigLoader(config_path.parent).load_milestone_config(config_path=config_path)


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
def _empty_milestone_config(empty_milestones_path: Path) -> MilestoneConfig:
    return _load_milestone_config(empty_milestones_path)


@pytest.fixture(name="populated_milestone_config")
def _populated_milestone_config(populated_milestones_path: Path) -> MilestoneConfig:
    return _load_milestone_config(populated_milestones_path)


class TestMilestoneConfigFromFile:
    """Loading behaviour through ConfigLoader."""

    def test_from_file_loads_empty_list(self, empty_milestone_config: MilestoneConfig) -> None:
        assert empty_milestone_config.milestones == []

    def test_from_file_loads_populated_list(
        self, populated_milestone_config: MilestoneConfig
    ) -> None:
        titles = [m.title for m in populated_milestone_config.milestones]
        assert "v1.0" in titles
        assert "v2.0" in titles

    def test_from_file_raises_on_missing_file(self) -> None:
        with pytest.raises(ConfigError, match="Config file not found"):
            _load_milestone_config(Path(".st3/nonexistent_milestones.yaml"))

    def test_repeated_loads_are_equivalent(self, empty_milestones_path: Path) -> None:
        cfg1 = _load_milestone_config(empty_milestones_path)
        cfg2 = _load_milestone_config(empty_milestones_path)
        assert cfg1 == cfg2


class TestMilestoneConfigValidateMilestone:
    """validate_milestone() permissive when list empty, strict when populated."""

    def test_validate_milestone_always_true_when_list_empty(
        self, empty_milestone_config: MilestoneConfig
    ) -> None:
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
