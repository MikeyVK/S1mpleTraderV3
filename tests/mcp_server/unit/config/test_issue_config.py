"""Unit tests for IssueConfig loader-based access (Issue #149, Cycle 1).

@layer: tests
@dependencies: mcp_server.config.loader
@responsibilities: Verify IssueConfig loads issues.yaml, get_workflow, get_label (incl. hotfix
                   -> type:bug mapping), and optional_label_inputs.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import IssueConfig
from mcp_server.core.exceptions import ConfigError

_MINIMAL_ISSUES_YAML = {
    "version": "1.0",
    "issue_types": [
        {"name": "feature", "workflow": "feature", "label": "type:feature"},
        {"name": "bug", "workflow": "bug", "label": "type:bug"},
        {"name": "hotfix", "workflow": "hotfix", "label": "type:bug"},
        {"name": "chore", "workflow": "feature", "label": "type:chore"},
        {"name": "epic", "workflow": "epic", "label": "type:epic"},
    ],
    "required_label_categories": ["type", "priority", "scope"],
    "optional_label_inputs": {
        "is_epic": {"type": "bool", "label": "type:epic", "behavior": "Overrides type:*"},
        "parent_issue": {"type": "int", "label_pattern": "parent:{value}"},
    },
}


def _load_issue_config(config_path: Path) -> IssueConfig:
    return ConfigLoader(config_path.parent).load_issue_config(config_path=config_path)


@pytest.fixture(name="issues_yaml_path")
def _issues_yaml_path() -> Path:
    """Write a temporary issues.yaml and return its Path."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fh:
        yaml.dump(_MINIMAL_ISSUES_YAML, fh, allow_unicode=True)
        return Path(fh.name)


@pytest.fixture(name="issue_config")
def _issue_config(issues_yaml_path: Path) -> IssueConfig:
    """Return a fresh IssueConfig loaded from temporary yaml."""
    return _load_issue_config(issues_yaml_path)


class TestIssueConfigFromFile:
    """Loading behaviour through ConfigLoader."""

    def test_from_file_loads_issue_types(self, issue_config: IssueConfig) -> None:
        names = [entry.name for entry in issue_config.issue_types]
        assert "feature" in names
        assert "hotfix" in names
        assert "chore" in names

    def test_from_file_raises_on_missing_file(self) -> None:
        with pytest.raises(ConfigError, match="Config file not found"):
            _load_issue_config(Path(".st3/nonexistent_issues.yaml"))

    def test_repeated_loads_are_equivalent(self, issues_yaml_path: Path) -> None:
        cfg1 = _load_issue_config(issues_yaml_path)
        cfg2 = _load_issue_config(issues_yaml_path)
        assert cfg1 == cfg2

    def test_loads_optional_label_inputs(self, issue_config: IssueConfig) -> None:
        assert "is_epic" in issue_config.optional_label_inputs
        assert "parent_issue" in issue_config.optional_label_inputs


class TestIssueConfigGetWorkflow:
    """get_workflow() correctness."""

    def test_get_workflow_feature(self, issue_config: IssueConfig) -> None:
        assert issue_config.get_workflow("feature") == "feature"

    def test_get_workflow_hotfix(self, issue_config: IssueConfig) -> None:
        assert issue_config.get_workflow("hotfix") == "hotfix"

    def test_get_workflow_chore_maps_to_feature_workflow(self, issue_config: IssueConfig) -> None:
        assert issue_config.get_workflow("chore") == "feature"

    def test_get_workflow_raises_on_unknown_type(self, issue_config: IssueConfig) -> None:
        with pytest.raises(ValueError, match="Unknown issue type"):
            issue_config.get_workflow("unknown_type")


class TestIssueConfigGetLabel:
    """get_label() correctness, including hotfix -> type:bug non-obvious mapping."""

    def test_get_label_feature(self, issue_config: IssueConfig) -> None:
        assert issue_config.get_label("feature") == "type:feature"

    def test_get_label_bug(self, issue_config: IssueConfig) -> None:
        assert issue_config.get_label("bug") == "type:bug"

    def test_get_label_hotfix_returns_type_bug(self, issue_config: IssueConfig) -> None:
        """hotfix must map to type:bug, not type:hotfix."""
        assert issue_config.get_label("hotfix") == "type:bug"

    def test_get_label_chore(self, issue_config: IssueConfig) -> None:
        assert issue_config.get_label("chore") == "type:chore"

    def test_get_label_epic(self, issue_config: IssueConfig) -> None:
        assert issue_config.get_label("epic") == "type:epic"

    def test_get_label_raises_on_unknown_type(self, issue_config: IssueConfig) -> None:
        with pytest.raises(ValueError, match="Unknown issue type"):
            issue_config.get_label("nonexistent")
