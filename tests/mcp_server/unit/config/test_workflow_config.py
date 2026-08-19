"""Tests for workflow configuration (WorkflowConfig, WorkflowTemplate).

Test Coverage:
- Config loading via ConfigLoader
- Workflow lookup (exists, unknown workflow)
- WorkflowTemplate metadata (no phases — catalog role only)
- has_workflow helper

Quality Requirements:
- Pylint: 10/10 (no exceptions)
- Mypy: strict mode passing
- Coverage: 100% for workflow schema behavior

@layer: Tests (Unit)
@dependencies: pytest, yaml, pydantic, mcp_server.config.schemas
"""

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import WorkflowConfig, WorkflowTemplate
from mcp_server.core.exceptions import ConfigError
from tests.mcp_server.test_support import get_default_server_root

_PGMCP_CONFIG = Path(__file__).resolve().parents[4] / get_default_server_root() / "config"


def _load_workflow_config(config_path: Path | None = None) -> WorkflowConfig:
    if config_path is None:
        return ConfigLoader(_PGMCP_CONFIG).load_workflow_config()
    return ConfigLoader(_PGMCP_CONFIG).load_workflow_config(config_path=config_path)


@pytest.fixture
def valid_workflows_yaml(tmp_path: Path) -> Path:
    """Create valid workflows.yaml fixture (C6+: no phases lists)."""
    config_data = {
        "version": "1.0.0",
        "workflows": {
            "feature": {
                "name": "feature",
                "description": "Full development workflow",
                "default_execution_mode": "interactive",
            },
            "hotfix": {
                "name": "hotfix",
                "description": "Emergency fix workflow",
                "default_execution_mode": "autonomous",
            },
        },
    }

    yaml_path = tmp_path / "workflows.yaml"
    with yaml_path.open("w", encoding="utf-8") as file_handle:
        yaml.dump(config_data, file_handle)

    return yaml_path


@pytest.fixture
def invalid_yaml(tmp_path: Path) -> Path:
    """Create malformed YAML file."""
    yaml_path = tmp_path / "invalid.yaml"
    yaml_path.write_text("invalid: yaml: content: [unclosed", encoding="utf-8")
    return yaml_path


class TestWorkflowConfigLoading:
    """Test ConfigLoader-based workflow loading."""

    def test_load_valid_yaml(self, valid_workflows_yaml: Path) -> None:
        """Test loading valid workflows.yaml file."""
        config = _load_workflow_config(valid_workflows_yaml)

        assert isinstance(config, WorkflowConfig)
        assert config.version == "1.0.0"
        assert "feature" in config.workflows
        assert "hotfix" in config.workflows
        assert len(config.workflows) == 2

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Test loading non-existent workflows.yaml file."""
        missing_path = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigError) as exc_info:
            _load_workflow_config(missing_path)

        error_msg = str(exc_info.value)
        assert "Config file not found" in error_msg
        assert "nonexistent.yaml" in error_msg

    def test_load_default_path_missing(self, tmp_path: Path) -> None:
        """Test loading with default path when file doesn't exist."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        with pytest.raises(ConfigError) as exc_info:
            ConfigLoader(config_dir).load_workflow_config()

        error_msg = str(exc_info.value)
        assert (
            f"{get_default_server_root()}/config/workflows.yaml" in error_msg
            or "workflows.yaml" in error_msg
        )

    def test_load_invalid_yaml(self, invalid_yaml: Path) -> None:
        """Test loading malformed YAML file."""
        with pytest.raises(ConfigError) as exc_info:
            _load_workflow_config(invalid_yaml)

        assert "Invalid YAML" in str(exc_info.value)


class TestWorkflowTemplateValidation:
    """Test WorkflowTemplate Pydantic validation."""

    def test_invalid_execution_mode_rejected(self) -> None:
        """Test that invalid execution_mode values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowTemplate(
                name="test",
                default_execution_mode="manual",  # type: ignore[arg-type]
            )

        error_msg = str(exc_info.value)
        assert "execution_mode" in error_msg.lower() or "literal" in error_msg.lower()

    def test_extra_field_rejected(self) -> None:
        """WorkflowTemplate rejects unknown extra fields (extra='forbid')."""
        with pytest.raises(ValidationError):
            WorkflowTemplate(  # type: ignore[call-arg]
                name="test",
                default_execution_mode="interactive",
                unknown_field="should_fail",
            )


class TestWorkflowLookup:
    """Test WorkflowConfig.get_workflow() method."""

    def test_get_workflow_exists(self, valid_workflows_yaml: Path) -> None:
        """Test getting an existing workflow by name."""
        config = _load_workflow_config(valid_workflows_yaml)

        workflow = config.get_workflow("feature")

        assert isinstance(workflow, WorkflowTemplate)
        assert workflow.name == "feature"
        assert workflow.default_execution_mode == "interactive"
        assert workflow.description == "Full development workflow"

    def test_get_workflow_unknown(self, valid_workflows_yaml: Path) -> None:
        """Test getting a non-existent workflow by name."""
        config = _load_workflow_config(valid_workflows_yaml)

        with pytest.raises(ValueError) as exc_info:
            config.get_workflow("nonexistent")

        error_msg = str(exc_info.value)
        assert "Unknown workflow: 'nonexistent'" in error_msg
        assert "Available workflows:" in error_msg
        assert "feature" in error_msg
        assert "hotfix" in error_msg
        assert "Hint:" in error_msg


class TestWorkflowHelpers:
    """Tests for WorkflowConfig catalog helper methods."""

    def test_has_workflow_returns_true_only_for_defined_workflows(
        self, valid_workflows_yaml: Path
    ) -> None:
        """WorkflowConfig.has_workflow() returns True iff workflow is defined."""
        config = _load_workflow_config(valid_workflows_yaml)

        assert config.has_workflow("feature") is True
        assert config.has_workflow("hotfix") is True
        assert config.has_workflow("unknown") is False
