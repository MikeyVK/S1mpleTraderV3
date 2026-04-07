"""Tests for workflow configuration (WorkflowConfig, WorkflowTemplate).

Test Coverage:
- Config loading via ConfigLoader
- Workflow lookup (exists, unknown workflow)
- Transition validation (next phase, skip phase, backward, invalid phases)

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


def _load_workflow_config(config_path: Path | None = None) -> WorkflowConfig:
    if config_path is None:
        return ConfigLoader(Path(".st3/config")).load_workflow_config()
    return ConfigLoader(config_path.parent).load_workflow_config(config_path=config_path)


@pytest.fixture
def valid_workflows_yaml(tmp_path: Path) -> Path:
    """Create valid workflows.yaml fixture."""
    config_data = {
        "version": "1.0",
        "workflows": {
            "feature": {
                "name": "feature",
                "description": "Full development workflow",
                "default_execution_mode": "interactive",
                "phases": [
                    "research",
                    "planning",
                    "design",
                    "tdd",
                    "validation",
                    "documentation",
                ],
            },
            "hotfix": {
                "name": "hotfix",
                "description": "Emergency fix workflow",
                "default_execution_mode": "autonomous",
                "phases": ["tdd", "validation", "documentation"],
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


@pytest.fixture
def invalid_schema_yaml(tmp_path: Path) -> Path:
    """Create YAML with invalid schema (missing required fields)."""
    config_data = {
        "version": "1.0",
        "workflows": {
            "broken": {
                "name": "broken",
                "default_execution_mode": "interactive",
            },
        },
    }

    yaml_path = tmp_path / "invalid_schema.yaml"
    with yaml_path.open("w", encoding="utf-8") as file_handle:
        yaml.dump(config_data, file_handle)

    return yaml_path


class TestWorkflowConfigLoading:
    """Test ConfigLoader-based workflow loading."""

    def test_load_valid_yaml(self, valid_workflows_yaml: Path) -> None:
        """Test loading valid workflows.yaml file."""
        config = _load_workflow_config(valid_workflows_yaml)

        assert isinstance(config, WorkflowConfig)
        assert config.version == "1.0"
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

    def test_load_default_path_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading with default path when file doesn't exist."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigError) as exc_info:
            _load_workflow_config()

        error_msg = str(exc_info.value)
        assert ".st3/config/workflows.yaml" in error_msg or "workflows.yaml" in error_msg

    def test_load_invalid_yaml(self, invalid_yaml: Path) -> None:
        """Test loading malformed YAML file."""
        with pytest.raises(ConfigError) as exc_info:
            _load_workflow_config(invalid_yaml)

        assert "Invalid YAML" in str(exc_info.value)

    def test_load_invalid_schema(self, invalid_schema_yaml: Path) -> None:
        """Test loading YAML with invalid schema (missing required fields)."""
        with pytest.raises(ConfigError) as exc_info:
            _load_workflow_config(invalid_schema_yaml)

        error_msg = str(exc_info.value)
        assert "phases" in error_msg or "required" in error_msg.lower()


class TestWorkflowTemplateValidation:
    """Test WorkflowTemplate Pydantic validation."""

    def test_duplicate_phases_rejected(self) -> None:
        """Test that duplicate phases in workflow are rejected."""
        with pytest.raises(ValueError) as exc_info:
            WorkflowTemplate(
                name="test",
                phases=["research", "planning", "research"],
                default_execution_mode="interactive",
            )

        error_msg = str(exc_info.value)
        assert "duplicate" in error_msg.lower()
        assert "research" in error_msg

    def test_empty_phase_names_rejected(self) -> None:
        """Test that empty or whitespace phase names are rejected."""
        with pytest.raises(ValueError) as exc_info:
            WorkflowTemplate(
                name="test",
                phases=["research", "  ", "planning"],
                default_execution_mode="interactive",
            )

        error_msg = str(exc_info.value)
        assert "empty" in error_msg.lower()

    def test_invalid_execution_mode_rejected(self) -> None:
        """Test that invalid execution_mode values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowTemplate(
                name="test",
                phases=["research"],
                default_execution_mode="manual",  # type: ignore[arg-type]
            )

        error_msg = str(exc_info.value)
        assert "execution_mode" in error_msg.lower() or "literal" in error_msg.lower()


class TestWorkflowLookup:
    """Test WorkflowConfig.get_workflow() method."""

    def test_get_workflow_exists(self, valid_workflows_yaml: Path) -> None:
        """Test getting an existing workflow by name."""
        config = _load_workflow_config(valid_workflows_yaml)

        workflow = config.get_workflow("feature")

        assert isinstance(workflow, WorkflowTemplate)
        assert workflow.name == "feature"
        assert workflow.phases == [
            "research",
            "planning",
            "design",
            "tdd",
            "validation",
            "documentation",
        ]
        assert workflow.default_execution_mode == "interactive"

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


class TestTransitionValidation:
    """Test WorkflowConfig.validate_transition() method."""

    def test_validate_transition_next_phase(self, valid_workflows_yaml: Path) -> None:
        """Test validating transition to next phase."""
        config = _load_workflow_config(valid_workflows_yaml)

        assert config.validate_transition("feature", "research", "planning") is True
        assert config.validate_transition("feature", "planning", "design") is True
        assert config.validate_transition("hotfix", "tdd", "validation") is True

    def test_validate_transition_skip_phase(self, valid_workflows_yaml: Path) -> None:
        """Test validating transition that skips a phase."""
        config = _load_workflow_config(valid_workflows_yaml)

        with pytest.raises(ValueError) as exc_info:
            config.validate_transition("feature", "research", "design")

        error_msg = str(exc_info.value)
        assert "Invalid transition:" in error_msg
        assert "research" in error_msg
        assert "design" in error_msg
        assert "Expected next phase: planning" in error_msg
        assert "force_phase_transition" in error_msg

    def test_validate_transition_backward(self, valid_workflows_yaml: Path) -> None:
        """Test validating backward transition."""
        config = _load_workflow_config(valid_workflows_yaml)

        with pytest.raises(ValueError) as exc_info:
            config.validate_transition("feature", "design", "planning")

        error_msg = str(exc_info.value)
        assert "Invalid transition:" in error_msg
        assert "design" in error_msg
        assert "planning" in error_msg

    def test_validate_transition_invalid_current_phase(self, valid_workflows_yaml: Path) -> None:
        """Test validation with invalid current phase."""
        config = _load_workflow_config(valid_workflows_yaml)

        with pytest.raises(ValueError) as exc_info:
            config.validate_transition("feature", "invalid", "planning")

        error_msg = str(exc_info.value)
        assert "Current phase 'invalid' not in workflow 'feature'" in error_msg
        assert "Valid phases:" in error_msg

    def test_validate_transition_invalid_target_phase(self, valid_workflows_yaml: Path) -> None:
        """Test validation with invalid target phase."""
        config = _load_workflow_config(valid_workflows_yaml)

        with pytest.raises(ValueError) as exc_info:
            config.validate_transition("feature", "research", "invalid")

        error_msg = str(exc_info.value)
        assert "Target phase 'invalid' not in workflow 'feature'" in error_msg


class TestWorkflowHelpers:
    """Tests for helper methods added to workflows.py during config consolidation."""

    def test_get_first_phase_returns_first_phase(self, valid_workflows_yaml: Path) -> None:
        """WorkflowConfig exposes get_first_phase() on workflows.py."""
        config = _load_workflow_config(valid_workflows_yaml)

        assert config.get_first_phase("feature") == "research"
        assert config.get_first_phase("hotfix") == "tdd"

    def test_has_workflow_returns_true_only_for_defined_workflows(
        self, valid_workflows_yaml: Path
    ) -> None:
        """WorkflowConfig exposes has_workflow() on workflows.py."""
        config = _load_workflow_config(valid_workflows_yaml)

        assert config.has_workflow("feature") is True
        assert config.has_workflow("hotfix") is True
        assert config.has_workflow("unknown") is False


class TestRepositoryWorkflowPhases:
    """Tests for the live repository workflows.yaml contract for issue #257."""

    def test_repo_workflows_use_implementation_instead_of_tdd(self) -> None:
        """Feature and hotfix workflows must use implementation after cycle 1 rename."""
        config = _load_workflow_config()

        feature_phases = config.get_workflow("feature").phases
        hotfix_phases = config.get_workflow("hotfix").phases

        assert "implementation" in feature_phases
        assert "implementation" in hotfix_phases
        assert "tdd" not in feature_phases
        assert "tdd" not in hotfix_phases
