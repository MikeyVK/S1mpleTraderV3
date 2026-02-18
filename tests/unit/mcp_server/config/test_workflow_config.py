"""Tests for workflow configuration (WorkflowConfig, WorkflowTemplate).

Test Coverage:
- Config loading (valid YAML, missing file, invalid YAML, invalid schema)
- Workflow lookup (exists, unknown workflow)
- Transition validation (next phase, skip phase, backward, invalid phases)

Quality Requirements:
- Pylint: 10/10 (no exceptions)
- Mypy: strict mode passing
- Coverage: 100% for mcp_server/config/workflows.py
"""

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

# Module under test
from mcp_server.config.workflows import WorkflowConfig, WorkflowTemplate


@pytest.fixture
def valid_workflows_yaml(tmp_path: Path) -> Path:
    """Create valid workflows.yaml fixture.

    Args:
        tmp_path: Pytest tmp_path fixture

    Returns:
        Path to temporary workflows.yaml file
    """
    config_data = {
        "version": "1.0",
        "workflows": {
            "feature": {
                "name": "feature",
                "description": "Full development workflow",
                "default_execution_mode": "interactive",
                "phases": ["research", "planning", "design", "tdd", "validation", "documentation"]
            },
            "hotfix": {
                "name": "hotfix",
                "description": "Emergency fix workflow",
                "default_execution_mode": "autonomous",
                "phases": ["tdd", "validation", "documentation"]
            }
        }
    }

    yaml_path = tmp_path / "workflows.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)

    return yaml_path


@pytest.fixture
def invalid_yaml(tmp_path: Path) -> Path:
    """Create malformed YAML file.

    Args:
        tmp_path: Pytest tmp_path fixture

    Returns:
        Path to malformed YAML file
    """
    yaml_path = tmp_path / "invalid.yaml"
    yaml_path.write_text("invalid: yaml: content: [unclosed", encoding="utf-8")
    return yaml_path


@pytest.fixture
def invalid_schema_yaml(tmp_path: Path) -> Path:
    """Create YAML with invalid schema (missing required fields).

    Args:
        tmp_path: Pytest tmp_path fixture

    Returns:
        Path to invalid schema YAML file
    """
    config_data = {
        "version": "1.0",
        "workflows": {
            "broken": {
                "name": "broken",
                # Missing required 'phases' field
                "default_execution_mode": "interactive"
            }
        }
    }

    yaml_path = tmp_path / "invalid_schema.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)

    return yaml_path


# =============================================================================
# Phase 1: Config Loading Tests (GREEN)
# =============================================================================

class TestWorkflowConfigLoading:
    """Test WorkflowConfig.load() method."""

    def test_load_valid_yaml(self, valid_workflows_yaml: Path) -> None:
        """Test loading valid workflows.yaml file.

        Expected behavior:
        - Loads YAML successfully
        - Returns WorkflowConfig instance
        - Contains expected workflows (feature, hotfix)
        - Version is "1.0"

        Args:
            valid_workflows_yaml: Path to valid test YAML file
        """
        config = WorkflowConfig.load(valid_workflows_yaml)

        assert isinstance(config, WorkflowConfig)
        assert config.version == "1.0"
        assert "feature" in config.workflows
        assert "hotfix" in config.workflows
        assert len(config.workflows) == 2

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Test loading non-existent workflows.yaml file.

        Expected behavior:
        - Raises FileNotFoundError
        - Error message includes expected path
        - Error message includes helpful hint

        Args:
            tmp_path: Pytest tmp_path fixture
        """
        missing_path = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError) as exc_info:
            WorkflowConfig.load(missing_path)

        error_msg = str(exc_info.value)
        assert "Workflow config not found" in error_msg
        assert str(missing_path) in error_msg
        assert "Hint:" in error_msg

    def test_load_default_path_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading with default path when file doesn't exist.

        Expected behavior:
        - Uses default path .st3/workflows.yaml
        - Raises FileNotFoundError
        - Error message mentions .st3/workflows.yaml

        Args:
            tmp_path: Pytest tmp_path fixture
            monkeypatch: Pytest monkeypatch fixture for changing working directory
        """
        # Change to tmp_path so .st3/workflows.yaml doesn't exist
        monkeypatch.chdir(tmp_path)

        with pytest.raises(FileNotFoundError) as exc_info:
            WorkflowConfig.load()  # No path argument = default

        error_msg = str(exc_info.value)
        assert ".st3/workflows.yaml" in error_msg

    def test_load_invalid_yaml(self, invalid_yaml: Path) -> None:
        """Test loading malformed YAML file.

        Expected behavior:
        - Raises yaml.YAMLError or ValidationError
        - Error message indicates YAML parsing failure

        Args:
            invalid_yaml: Path to malformed YAML file
        """
        with pytest.raises((yaml.YAMLError, ValidationError)):
            WorkflowConfig.load(invalid_yaml)

    def test_load_invalid_schema(self, invalid_schema_yaml: Path) -> None:
        """Test loading YAML with invalid schema (missing required fields).

        Expected behavior:
        - Raises ValidationError (Pydantic validation)
        - Error message indicates missing field

        Args:
            invalid_schema_yaml: Path to invalid schema YAML file
        """
        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig.load(invalid_schema_yaml)

        error_msg = str(exc_info.value)
        assert "phases" in error_msg or "required" in error_msg.lower()


class TestWorkflowTemplateValidation:
    """Test WorkflowTemplate Pydantic validation."""

    def test_duplicate_phases_rejected(self) -> None:
        """Test that duplicate phases in workflow are rejected.

        Expected behavior:
        - Pydantic @model_validator catches duplicates
        - Raises ValueError
        - Error message lists duplicate phases
        """
        with pytest.raises(ValueError) as exc_info:
            WorkflowTemplate(
                name="test",
                phases=["research", "planning", "research"],  # Duplicate
                default_execution_mode="interactive"
            )

        error_msg = str(exc_info.value)
        assert "duplicate" in error_msg.lower()
        assert "research" in error_msg

    def test_empty_phase_names_rejected(self) -> None:
        """Test that empty/whitespace phase names are rejected.

        Expected behavior:
        - Pydantic @model_validator catches empty strings
        - Raises ValueError
        - Error message indicates empty phase names
        """
        with pytest.raises(ValueError) as exc_info:
            WorkflowTemplate(
                name="test",
                phases=["research", "  ", "planning"],  # Empty phase
                default_execution_mode="interactive"
            )

        error_msg = str(exc_info.value)
        assert "empty" in error_msg.lower()

    def test_invalid_execution_mode_rejected(self) -> None:
        """Test that invalid execution_mode values are rejected.

        Expected behavior:
        - Pydantic Literal validation rejects invalid values
        - Raises ValidationError
        - Valid values: "interactive", "autonomous"
        """
        with pytest.raises(ValidationError) as exc_info:
            WorkflowTemplate(
                name="test",
                phases=["research"],
                default_execution_mode="manual"  # type: ignore[arg-type]
            )

        error_msg = str(exc_info.value)
        assert "execution_mode" in error_msg.lower() or "literal" in error_msg.lower()


# =============================================================================
# Phase 2: Workflow Lookup Tests (RED)
# =============================================================================

class TestWorkflowLookup:
    """Test WorkflowConfig.get_workflow() method."""

    def test_get_workflow_exists(self, valid_workflows_yaml: Path) -> None:
        """Test getting an existing workflow by name.

        Expected behavior:
        - Returns WorkflowTemplate instance
        - Template has correct name and phases
        - Workflow matches expected configuration

        Args:
            valid_workflows_yaml: Path to valid test YAML file
        """
        config = WorkflowConfig.load(valid_workflows_yaml)

        workflow = config.get_workflow("feature")

        assert isinstance(workflow, WorkflowTemplate)
        assert workflow.name == "feature"
        assert workflow.phases == [
            "research", "planning", "design", "tdd", "validation", "documentation"
        ]
        assert workflow.default_execution_mode == "interactive"

    def test_get_workflow_unknown(self, valid_workflows_yaml: Path) -> None:
        """Test getting a non-existent workflow by name.

        Expected behavior:
        - Raises ValueError
        - Error message includes unknown workflow name
        - Error message lists available workflows
        - Error message includes helpful hint

        Args:
            valid_workflows_yaml: Path to valid test YAML file
        """
        config = WorkflowConfig.load(valid_workflows_yaml)

        with pytest.raises(ValueError) as exc_info:
            config.get_workflow("nonexistent")

        error_msg = str(exc_info.value)
        assert "Unknown workflow: 'nonexistent'" in error_msg
        assert "Available workflows:" in error_msg
        assert "feature" in error_msg
        assert "hotfix" in error_msg
        assert "Hint:" in error_msg


# =============================================================================
# Phase 3: Transition Validation Tests (RED)
# =============================================================================

class TestTransitionValidation:
    """Test WorkflowConfig.validate_transition() method."""

    def test_validate_transition_next_phase(self, valid_workflows_yaml: Path) -> None:
        """Test validating transition to next phase (valid).

        Expected behavior:
        - Returns True for valid next-phase transition
        - Follows strict sequential order

        Args:
            valid_workflows_yaml: Path to valid test YAML file
        """
        config = WorkflowConfig.load(valid_workflows_yaml)

        # Valid transitions: research ÔåÆ planning, planning ÔåÆ design, etc.
        assert config.validate_transition("feature", "research", "planning") is True
        assert config.validate_transition("feature", "planning", "design") is True
        assert config.validate_transition("hotfix", "tdd", "validation") is True

    def test_validate_transition_skip_phase(self, valid_workflows_yaml: Path) -> None:
        """Test validating transition that skips a phase (invalid).

        Expected behavior:
        - Raises ValueError
        - Error message indicates invalid transition
        - Error message shows expected next phase
        - Error message includes hint about force_phase_transition

        Args:
            valid_workflows_yaml: Path to valid test YAML file
        """
        config = WorkflowConfig.load(valid_workflows_yaml)

        with pytest.raises(ValueError) as exc_info:
            config.validate_transition("feature", "research", "design")  # Skips planning

        error_msg = str(exc_info.value)
        assert "Invalid transition:" in error_msg
        assert "research" in error_msg
        assert "design" in error_msg
        assert "Expected next phase: planning" in error_msg
        assert "force_phase_transition" in error_msg

    def test_validate_transition_backward(self, valid_workflows_yaml: Path) -> None:
        """Test validating backward transition (invalid).

        Expected behavior:
        - Raises ValueError
        - Error message indicates invalid transition
        - Backward transitions not allowed

        Args:
            valid_workflows_yaml: Path to valid test YAML file
        """
        config = WorkflowConfig.load(valid_workflows_yaml)

        with pytest.raises(ValueError) as exc_info:
            config.validate_transition("feature", "design", "planning")  # Backward

        error_msg = str(exc_info.value)
        assert "Invalid transition:" in error_msg
        assert "design" in error_msg
        assert "planning" in error_msg

    def test_validate_transition_invalid_current_phase(
        self, valid_workflows_yaml: Path
    ) -> None:
        """Test validation with invalid current phase.

        Expected behavior:
        - Raises ValueError
        - Error message indicates current phase not in workflow
        - Error message lists valid phases

        Args:
            valid_workflows_yaml: Path to valid test YAML file
        """
        config = WorkflowConfig.load(valid_workflows_yaml)

        with pytest.raises(ValueError) as exc_info:
            config.validate_transition("feature", "invalid", "planning")

        error_msg = str(exc_info.value)
        assert "Current phase 'invalid' not in workflow 'feature'" in error_msg
        assert "Valid phases:" in error_msg

    def test_validate_transition_invalid_target_phase(
        self, valid_workflows_yaml: Path
    ) -> None:
        """Test validation with invalid target phase.

        Expected behavior:
        - Raises ValueError
        - Error message indicates target phase not in workflow
        - Error message lists valid phases

        Args:
            valid_workflows_yaml: Path to valid test YAML file
        """
        config = WorkflowConfig.load(valid_workflows_yaml)

        with pytest.raises(ValueError) as exc_info:
            config.validate_transition("feature", "research", "invalid")

        error_msg = str(exc_info.value)
        assert "Target phase 'invalid' not in workflow 'feature'" in error_msg
        assert "Valid phases:" in error_msg
