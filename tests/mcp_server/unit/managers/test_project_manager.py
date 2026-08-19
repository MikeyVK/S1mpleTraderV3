"""Tests for ProjectManager with workflow-based initialization.

Issue #50: Tests migrated from PHASE_TEMPLATES to workflows.yaml.
- Workflow selection from workflows.yaml
- Execution mode handling (interactive/autonomous)
- Custom phases with skip_reason
- Project plan storage in .pgmcp/deliverables.json

@layer: Tests (Unit)
@dependencies: pytest, tests.mcp_server.test_support, mcp_server.managers.project_manager
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.core.exceptions import PlanningVersionMismatchError
from mcp_server.managers.project_manager import ProjectInitOptions, ProjectManager
from mcp_server.managers.state_repository import StateBranchMismatchError, StateNotFoundError
from mcp_server.state.workflow_status import WorkflowStatusDTO
from tests.mcp_server.test_support import (
    get_default_server_root,
    load_contracts_config,
    load_workflow_config,
    make_project_manager,
)


class TestProjectManagerWorkflows:
    """Test ProjectManager with workflows.yaml integration."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace.

        Args:
            tmp_path: Pytest tmp_path fixture

        Returns:
            Path to temporary workspace root
        """
        return tmp_path

    @pytest.fixture
    def manager(self, workspace_root: Path) -> ProjectManager:
        """Create ProjectManager instance."""
        return make_project_manager(workspace_root)

    def test_workflows_loaded_from_yaml(self) -> None:
        """Test that workflows are loaded from workflows.yaml."""
        workflow_config = load_workflow_config()
        assert "feature" in workflow_config.workflows
        assert "bug" in workflow_config.workflows
        assert "hotfix" in workflow_config.workflows
        assert "refactor" in workflow_config.workflows
        assert "docs" in workflow_config.workflows

    def test_feature_workflow_has_6_phases(self) -> None:
        """Test feature workflow phase count from contracts.yaml (C6+: SSOT).

        Feature workflow has 7 phases including 'ready' terminal phase.
        """
        phases = load_contracts_config().get_phases("feature")
        assert len(phases) == 7
        expected = [
            "research",
            "design",
            "planning",
            "implementation",
            "validation",
            "documentation",
            "ready",
        ]
        assert phases == expected
        wf = load_workflow_config().get_workflow("feature")
        assert wf.default_execution_mode == "interactive"

    def test_hotfix_workflow_has_3_phases_autonomous(self) -> None:
        """Test hotfix workflow from contracts.yaml (C6+: SSOT).

        Hotfix workflow has 4 phases including 'ready' terminal phase.
        """
        phases = load_contracts_config().get_phases("hotfix")
        assert len(phases) == 4
        assert phases == ["implementation", "validation", "documentation", "ready"]
        assert load_workflow_config().get_workflow("hotfix").default_execution_mode == "autonomous"

    def test_initialize_project_with_feature_workflow(
        self, manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test initialize_project with feature workflow."""
        result = manager.initialize_project(
            issue_number=42, issue_title="Add user authentication", workflow_name="feature"
        )

        assert result["success"] is True
        assert result["workflow_name"] == "feature"
        assert result["execution_mode"] == "interactive"
        assert len(result["required_phases"]) == 7

        plan = manager.get_project_plan(42)
        assert plan is not None
        assert plan["workflow_name"] == "feature"
        assert plan["execution_mode"] == "interactive"
        assert len(plan["required_phases"]) == 7

    def test_initialize_project_with_hotfix_workflow(
        self, manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test initialize_project with hotfix workflow.

        contracts.yaml SSOT — execution_mode defaults to interactive.
        """
        result = manager.initialize_project(
            issue_number=99, issue_title="Critical security fix", workflow_name="hotfix"
        )

        assert result["success"] is True
        assert result["workflow_name"] == "hotfix"
        assert result["execution_mode"] == "interactive"
        assert len(result["required_phases"]) == 4

        plan = manager.get_project_plan(99)
        assert plan is not None
        assert plan["execution_mode"] == "interactive"

    def test_initialize_project_with_execution_mode_override(
        self, manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test execution_mode override (feature normally interactive)."""
        result = manager.initialize_project(
            issue_number=77,
            issue_title="Test",
            workflow_name="feature",
            options=ProjectInitOptions(execution_mode="autonomous"),
        )

        assert result["execution_mode"] == "autonomous"

        plan = manager.get_project_plan(77)
        assert plan is not None
        assert plan["execution_mode"] == "autonomous"

    def test_initialize_project_with_custom_phases(
        self, manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test initialize_project with custom phases."""
        custom_phases = (
            "research",
            "planning",
            "design",
            "implementation",
            "validation",
            "documentation",
        )

        result = manager.initialize_project(
            issue_number=50,
            issue_title="Complex refactor",
            workflow_name="refactor",
            options=ProjectInitOptions(
                custom_phases=custom_phases, skip_reason="Adding design phase for complex refactor"
            ),
        )

        assert result["success"] is True
        assert result["workflow_name"] == "refactor"
        assert result["required_phases"] == custom_phases
        assert result["skip_reason"] == "Adding design phase for complex refactor"

        plan = manager.get_project_plan(50)
        assert plan is not None
        assert tuple(plan["required_phases"]) == custom_phases
        assert plan["skip_reason"] == "Adding design phase for complex refactor"

    def test_initialize_project_invalid_workflow(self, manager: ProjectManager) -> None:
        """Test initialize_project rejects unknown workflow."""
        with pytest.raises(ValueError) as exc_info:
            manager.initialize_project(
                issue_number=999, issue_title="Test", workflow_name="invalid_workflow"
            )

        error_msg = str(exc_info.value)
        assert "Unknown workflow: 'invalid_workflow'" in error_msg
        assert "Available:" in error_msg

    def test_initialize_project_invalid_execution_mode(self, manager: ProjectManager) -> None:
        """Test initialize_project rejects invalid execution_mode."""
        with pytest.raises(ValueError) as exc_info:
            manager.initialize_project(
                issue_number=888,
                issue_title="Test",
                workflow_name="feature",
                options=ProjectInitOptions(execution_mode="manual"),
            )

        error_msg = str(exc_info.value)
        assert "Invalid execution_mode: 'manual'" in error_msg
        assert "Valid values: 'interactive', 'autonomous'" in error_msg

    def test_initialize_project_custom_phases_without_skip_reason(
        self, manager: ProjectManager
    ) -> None:
        """Test initialize_project requires skip_reason with custom_phases."""
        with pytest.raises(ValueError) as exc_info:
            manager.initialize_project(
                issue_number=777,
                issue_title="Test",
                workflow_name="feature",
                options=ProjectInitOptions(custom_phases=("research", "implementation")),
            )

        error_msg = str(exc_info.value)
        assert "skip_reason required when custom_phases provided" in error_msg

    def test_get_project_plan_returns_stored_plan(self, manager: ProjectManager) -> None:
        """Test get_project_plan retrieves stored project plan."""
        # Initialize project
        manager.initialize_project(issue_number=42, issue_title="Test", workflow_name="feature")

        # Retrieve plan
        plan = manager.get_project_plan(issue_number=42)
        assert plan is not None
        assert plan["workflow_name"] == "feature"
        assert plan["execution_mode"] == "interactive"
        assert len(plan["required_phases"]) == 7

    def test_get_project_plan_nonexistent_returns_none(self, manager: ProjectManager) -> None:
        """Test get_project_plan returns None for nonexistent project."""
        plan = manager.get_project_plan(issue_number=999)
        assert plan is None

    def test_initialize_project_with_parent_branch(self, manager: ProjectManager) -> None:
        """Test initializing project with explicit parent_branch.

        Issue #79: parent_branch tracking for merge targets.
        """
        result = manager.initialize_project(
            issue_number=79,
            issue_title="Add parent branch tracking",
            workflow_name="feature",
            options=ProjectInitOptions(parent_branch="epic/76-quality-gates-tooling"),
        )

        # Verify parent_branch in returned result
        assert result["parent_branch"] == "epic/76-quality-gates-tooling"

        # Verify persisted to deliverables.json
        plan = manager.get_project_plan(issue_number=79)
        assert plan is not None
        assert plan["parent_branch"] == "epic/76-quality-gates-tooling"

    def test_initialize_project_without_parent_branch(self, manager: ProjectManager) -> None:
        """Test initializing project without parent_branch (backward compat).

        Issue #79: parent_branch is optional for existing workflows.
        """
        result = manager.initialize_project(
            issue_number=80, issue_title="Old style project", workflow_name="bug"
        )

        # Verify parent_branch is None
        assert result["parent_branch"] is None

        # Verify persisted as None
        plan = manager.get_project_plan(issue_number=80)
        assert plan is not None
        assert plan["parent_branch"] is None


class TestProjectManagerPhaseDetection:
    """Test ProjectManager phase detection (Issue #139).

    Cycle 3.2: get_project_plan should return current_phase via ScopeDecoder.
    """

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace with .pgmcp directory."""
        phase_gate_dir = tmp_path / get_default_server_root()
        phase_gate_dir.mkdir()

        # Create workphases.yaml
        workphases_path = phase_gate_dir / "workphases.yaml"
        workphases_path.write_text(
            """
version: "1.0.0"
phases:
  research:
    display_name: "Research"
    commit_type_hint: "docs"
    subphases: []
  implementation:
    display_name: "Implementation"
    commit_type_hint: null
    subphases: ["red", "green", "refactor"]
  documentation:
    display_name: "Documentation"
    commit_type_hint: "docs"
    subphases: ["reference", "guides"]
"""
        )

        return tmp_path

    @pytest.fixture
    def manager(self, workspace_root: Path) -> ProjectManager:
        """Create ProjectManager instance."""
        return make_project_manager(workspace_root)

    def test_get_project_plan_includes_current_phase_from_state_json(self, tmp_path: Path) -> None:
        """After #298: current_phase comes from state.json via resolver when state present.

        Issue #139: Phase detection is now state.json-authoritative (not commit-scope).
        """
        resolver = MagicMock()
        resolver.resolve_current.return_value = WorkflowStatusDTO(
            current_phase="implementation",
            sub_phase=None,
            current_cycle=None,
            phase_source="state.json",
            phase_confidence="high",
            phase_detection_error=None,
        )
        manager = make_project_manager(tmp_path, workflow_status_resolver=resolver)
        manager.initialize_project(
            issue_number=139,
            issue_title="Add current_phase to get_project_plan",
            workflow_name="feature",
        )

        plan = manager.get_project_plan(issue_number=139)

        assert plan is not None
        assert "current_phase" in plan
        assert plan["phase_source"] == "state.json"
        assert "phase_detection_error" in plan

    def test_get_project_plan_has_no_phase_fields_when_state_absent(self, tmp_path: Path) -> None:
        """After #298: when resolver raises StateNotFoundError, plan has no phase fields.

        Issue #140: No state.json → plan returned without phase metadata.
        """
        resolver = MagicMock()
        resolver.resolve_current.side_effect = StateNotFoundError("no-state-branch")
        manager = make_project_manager(tmp_path, workflow_status_resolver=resolver)

        manager.initialize_project(
            issue_number=140,
            issue_title="Test unknown phase",
            workflow_name="bug",
        )

        plan = manager.get_project_plan(issue_number=140)

        assert plan is not None
        assert "current_phase" not in plan
        assert "phase_source" not in plan


class TestPlanningDeliverablesSchema:
    """Test planning_deliverables schema storage (Issue #146 Cycle 1)."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace."""
        return tmp_path

    @pytest.fixture
    def manager(self, workspace_root: Path) -> ProjectManager:
        """Create ProjectManager instance."""
        return make_project_manager(workspace_root)

    def test_planning_deliverables_stored_in_projects_json(self, manager: ProjectManager) -> None:
        """Test that planning_deliverables are persisted to deliverables.json."""
        # Arrange: Create planning deliverables according to design.md schema
        planning_deliverables = {
            "cycles": {
                "total": 4,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "deliverables": [
                            {"id": "D1.1", "description": "planning_deliverables schema"}
                        ],
                        "exit_criteria": "Schema validated, tests pass",
                    },
                    {
                        "cycle_number": 2,
                        "deliverables": [{"id": "D2.1", "description": "cycle_number validation"}],
                        "exit_criteria": "Validation tests pass",
                    },
                    {
                        "cycle_number": 3,
                        "deliverables": [
                            {"id": "D3.1", "description": "get_work_context enhancement"}
                        ],
                        "exit_criteria": "Discovery tools tested",
                    },
                    {
                        "cycle_number": 4,
                        "deliverables": [{"id": "D4.1", "description": "transition_cycle"}],
                        "exit_criteria": "All tools implemented",
                    },
                ],
            }
        }

        # Act: Initialize project and save planning deliverables
        manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Save planning deliverables
        manager.save_planning_deliverables(146, planning_deliverables)

        # Assert: Retrieve and verify planning deliverables persisted
        plan = manager.get_project_plan(146)
        assert plan is not None
        assert "planning_deliverables" in plan
        assert plan["planning_deliverables"]["cycles"]["total"] == 4
        assert len(plan["planning_deliverables"]["cycles"]["cycles"]) == 4

    def test_save_planning_deliverables_rejects_duplicate(self, manager: ProjectManager) -> None:
        """Test that save_planning_deliverables rejects duplicate saves."""
        # Arrange
        manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )
        planning_deliverables = {
            "cycles": {
                "total": 1,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "deliverables": [{"id": "D1.1", "description": "test deliverable"}],
                        "exit_criteria": "test criteria",
                    }
                ],
            }
        }
        manager.save_planning_deliverables(146, planning_deliverables)

        # Act & Assert: Second save should fail
        with pytest.raises(ValueError, match="already exist"):
            manager.save_planning_deliverables(146, planning_deliverables)

    def test_save_planning_deliverables_rejects_missing_cycles(
        self, manager: ProjectManager
    ) -> None:
        """Test schema validation: cycles required."""
        manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Missing cycles key
        with pytest.raises(ValueError, match="must contain 'cycles' key"):
            manager.save_planning_deliverables(146, {"validation": {"deliverables": []}})

    def test_save_planning_deliverables_rejects_malformed_cycles(
        self, manager: ProjectManager
    ) -> None:
        """Test schema validation: cycles structure."""
        manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # cycles not a dict/model
        with pytest.raises(ValueError, match="Input should be a valid dictionary"):
            manager.save_planning_deliverables(146, {"cycles": "invalid"})

        # Missing total key
        with pytest.raises(ValueError, match="total[\\s\\S]*Field required"):
            manager.save_planning_deliverables(146, {"cycles": {"cycles": []}})

        # Invalid total (not int)
        with pytest.raises(ValueError, match="Input should be a valid integer"):
            manager.save_planning_deliverables(146, {"cycles": {"total": "4", "cycles": []}})

        # Invalid total (zero / negative)
        with pytest.raises(ValueError, match="Input should be greater than 0"):
            manager.save_planning_deliverables(146, {"cycles": {"total": 0, "cycles": []}})

        # Missing cycles list key
        with pytest.raises(ValueError, match="cycles[\\s\\S]*Field required"):
            manager.save_planning_deliverables(146, {"cycles": {"total": 4}})

        # Invalid cycles (not list)
        with pytest.raises(ValueError, match="Input should be a valid list"):
            manager.save_planning_deliverables(146, {"cycles": {"total": 4, "cycles": "invalid"}})

    def test_save_planning_deliverables_rejects_total_mismatch(
        self, manager: ProjectManager
    ) -> None:
        """Test validation: total must equal len(cycles)."""
        manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # total=4 but only 2 cycles provided
        with pytest.raises(ValueError, match="total \\(4\\) must equal len\\(cycles\\) \\(2\\)"):
            manager.save_planning_deliverables(
                146,
                {
                    "cycles": {
                        "total": 4,
                        "cycles": [
                            {
                                "cycle_number": 1,
                                "deliverables": [{"id": "D1.1", "description": "Schema"}],
                                "exit_criteria": "Tests pass",
                            },
                            {
                                "cycle_number": 2,
                                "deliverables": [{"id": "D2.1", "description": "Validation"}],
                                "exit_criteria": "Tests pass",
                            },
                        ],
                    }
                },
            )

    def test_save_planning_deliverables_rejects_non_sequential_cycles(
        self, manager: ProjectManager
    ) -> None:
        """Test validation: cycle_number must be sequential 1-based."""
        manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Missing cycle_number
        with pytest.raises(ValueError, match="cycle_number[\\s\\S]*Field required"):
            manager.save_planning_deliverables(
                146,
                {
                    "cycles": {
                        "total": 1,
                        "cycles": [
                            {
                                "deliverables": [{"id": "D1.1", "description": "Schema"}],
                                "exit_criteria": "Tests pass",
                            }
                        ],
                    }
                },
            )

        # Non-sequential cycle_number (starts at 0)
        with pytest.raises(ValueError, match="must be sequential 1-based"):
            manager.save_planning_deliverables(
                146,
                {
                    "cycles": {
                        "total": 1,
                        "cycles": [
                            {
                                "cycle_number": 0,
                                "deliverables": [{"id": "D1.1", "description": "Schema"}],
                                "exit_criteria": "Tests pass",
                            }
                        ],
                    }
                },
            )

        # Skip cycle_number (1, 3 instead of 1, 2)
        with pytest.raises(ValueError, match="must be sequential 1-based"):
            manager.save_planning_deliverables(
                146,
                {
                    "cycles": {
                        "total": 2,
                        "cycles": [
                            {
                                "cycle_number": 1,
                                "deliverables": [{"id": "D1.1", "description": "Schema"}],
                                "exit_criteria": "Tests pass",
                            },
                            {
                                "cycle_number": 3,
                                "deliverables": [{"id": "D2.1", "description": "Validation"}],
                                "exit_criteria": "Tests pass",
                            },
                        ],
                    }
                },
            )

    def test_save_planning_deliverables_rejects_empty_deliverables(
        self, manager: ProjectManager
    ) -> None:
        """Test validation: deliverables array must not be empty."""
        manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Missing deliverables key
        with pytest.raises(ValueError, match="deliverables[\\s\\S]*Field required"):
            manager.save_planning_deliverables(
                146,
                {
                    "cycles": {
                        "total": 1,
                        "cycles": [{"cycle_number": 1, "exit_criteria": "Tests pass"}],
                    }
                },
            )

        # Empty deliverables array
        with pytest.raises(ValueError, match="List should have at least 1 item"):
            manager.save_planning_deliverables(
                146,
                {
                    "cycles": {
                        "total": 1,
                        "cycles": [
                            {"cycle_number": 1, "deliverables": [], "exit_criteria": "Tests pass"}
                        ],
                    }
                },
            )

        # deliverables not a list
        with pytest.raises(ValueError, match="Input should be a valid list"):
            manager.save_planning_deliverables(
                146,
                {
                    "cycles": {
                        "total": 1,
                        "cycles": [
                            {
                                "cycle_number": 1,
                                "deliverables": "Schema",
                                "exit_criteria": "Tests pass",
                            }
                        ],
                    }
                },
            )

    def test_save_planning_deliverables_rejects_empty_exit_criteria(
        self, manager: ProjectManager
    ) -> None:
        """Test validation: exit_criteria must be non-empty string."""
        manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Missing exit_criteria key
        with pytest.raises(ValueError, match="exit_criteria[\\s\\S]*Field required"):
            manager.save_planning_deliverables(
                146,
                {
                    "cycles": {
                        "total": 1,
                        "cycles": [
                            {
                                "cycle_number": 1,
                                "deliverables": [{"id": "D1.1", "description": "Schema"}],
                            }
                        ],
                    }
                },
            )

        # Empty exit_criteria string
        with pytest.raises(ValueError, match="exit_criteria must be a non-empty string"):
            manager.save_planning_deliverables(
                146,
                {
                    "cycles": {
                        "total": 1,
                        "cycles": [
                            {
                                "cycle_number": 1,
                                "deliverables": [{"id": "D1.1", "description": "Schema"}],
                                "exit_criteria": "",
                            }
                        ],
                    }
                },
            )

        # Whitespace-only exit_criteria
        with pytest.raises(ValueError, match="exit_criteria must be a non-empty string"):
            manager.save_planning_deliverables(
                146,
                {
                    "cycles": {
                        "total": 1,
                        "cycles": [
                            {
                                "cycle_number": 1,
                                "deliverables": [{"id": "D1.1", "description": "Schema"}],
                                "exit_criteria": "   ",
                            }
                        ],
                    }
                },
            )

        # exit_criteria not a string
        with pytest.raises(ValueError, match="Input should be a valid string"):
            manager.save_planning_deliverables(
                146,
                {
                    "cycles": {
                        "total": 1,
                        "cycles": [
                            {
                                "cycle_number": 1,
                                "deliverables": [{"id": "D1.1", "description": "Schema"}],
                                "exit_criteria": 123,
                            }
                        ],
                    }
                },
            )


class TestIssue257Cycle7Contracts:
    """Contract tests for Issue #257 Cycle 7 deliverables."""

    def test_project_manager_source_uses_atomic_json_writer(self) -> None:
        """D7.3: project_manager.py should use AtomicJsonWriter for deliverables writes."""
        source = Path("mcp_server/managers/project_manager.py").read_text(encoding="utf-8")

        assert "AtomicJsonWriter" in source

    def test_gitignore_does_not_ignore_state_json(self) -> None:
        """D7.4: .pgmcp/state.json must not remain ignored."""
        gitignore = Path(".gitignore").read_text(encoding="utf-8")

        assert f"{get_default_server_root()}/state.json" not in gitignore


class TestProjectManagerResolverAdoption:
    """C4: WorkflowStatusResolver adoption in ProjectManager.get_project_plan().

    Issue #231: These tests FAIL (RED) until WorkflowStatusResolver is injected
    into ProjectManager and used in get_project_plan().
    """

    def test_get_project_plan_uses_resolver_phase(self, tmp_path: Path) -> None:
        """get_project_plan uses WorkflowStatusResolver.resolve_current() when injected."""
        resolver = MagicMock()
        resolver.resolve_current.return_value = WorkflowStatusDTO(
            current_phase="research",
            sub_phase=None,
            current_cycle=None,
            phase_source="state.json",
            phase_confidence="high",
            phase_detection_error=None,
        )
        manager = make_project_manager(tmp_path, workflow_status_resolver=resolver)
        manager.initialize_project(99, "Test resolver adoption", "feature")

        plan = manager.get_project_plan(99)

        assert plan is not None
        assert plan["current_phase"] == "research"
        assert plan["phase_source"] == "state.json"
        resolver.resolve_current.assert_called_once()

    def test_get_project_plan_formats_phase_colon_sub_phase(self, tmp_path: Path) -> None:
        """get_project_plan formats 'phase:sub_phase' when resolver returns sub_phase."""
        resolver = MagicMock()
        resolver.resolve_current.return_value = WorkflowStatusDTO(
            current_phase="implementation",
            sub_phase="red",
            current_cycle=1,
            phase_source="state.json",
            phase_confidence="high",
            phase_detection_error=None,
        )
        manager = make_project_manager(tmp_path, workflow_status_resolver=resolver)
        manager.initialize_project(100, "Test sub-phase format", "feature")

        plan = manager.get_project_plan(100)

        assert plan is not None
        assert plan["current_phase"] == "implementation:red"

    def test_get_project_plan_passes_resolver_error_to_plan(self, tmp_path: Path) -> None:
        """get_project_plan propagates phase_detection_error from resolver."""
        resolver = MagicMock()
        resolver.resolve_current.return_value = WorkflowStatusDTO(
            current_phase="implementation",
            sub_phase=None,
            current_cycle=None,
            phase_source="state.json",
            phase_confidence="high",
            phase_detection_error="Phase detection failed: no state file",
        )
        manager = make_project_manager(tmp_path, workflow_status_resolver=resolver)
        manager.initialize_project(101, "Test error propagation", "feature")

        plan = manager.get_project_plan(101)

        assert plan is not None
        assert plan["phase_detection_error"] == "Phase detection failed: no state file"


# ---------------------------------------------------------------------------
# C6 RED — project_manager get_project_plan graceful degradation (issue #298)
# ---------------------------------------------------------------------------


class TestGetProjectPlanGracefulDegradation:
    """C6 (issue #298): get_project_plan() skips phase-enrichment on resolver errors."""

    def _make_manager_with_resolver(
        self, tmp_path: Path, resolver_side_effect: Exception
    ) -> ProjectManager:
        """Return a ProjectManager whose resolver raises the given exception."""
        mock_resolver = MagicMock()
        mock_resolver.resolve_current.side_effect = resolver_side_effect

        manager = make_project_manager(tmp_path)
        manager._workflow_status_resolver = mock_resolver  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001 — inject test double: no public setter

        # Seed the project plan
        manager.initialize_project(
            issue_number=298,
            issue_title="Graceful degradation test",
            workflow_name="feature",
        )
        return manager

    def test_get_project_plan_returns_plan_without_phase_fields_when_state_absent(
        self, tmp_path: Path
    ) -> None:
        """StateNotFoundError from resolver must not propagate; plan returned without phase keys."""
        manager = self._make_manager_with_resolver(
            tmp_path,
            resolver_side_effect=StateNotFoundError("feature/298-test"),
        )
        plan = manager.get_project_plan(298)

        assert plan is not None
        assert "current_phase" not in plan
        assert "phase_source" not in plan

    def test_get_project_plan_returns_plan_without_phase_fields_on_mismatch(
        self, tmp_path: Path
    ) -> None:
        """StateBranchMismatchError from resolver must not propagate; plan without phase keys."""
        manager = self._make_manager_with_resolver(
            tmp_path,
            resolver_side_effect=StateBranchMismatchError("branch mismatch"),
        )
        plan = manager.get_project_plan(298)

        assert plan is not None
        assert plan is not None
        assert "current_phase" not in plan
        assert "parent_branch" not in plan or "parent" not in plan  # type: ignore[operator]


class TestProjectManagerVersioning:
    """Tests for deliverables.json envelope versioning and validation."""

    def test_project_manager_read_projects_validates_envelope(self, tmp_path: Path) -> None:
        """Verify that _read_projects validates the envelope and backs up on mismatch."""

        manager = make_project_manager(tmp_path)

        # Write valid projects but version mismatch (expected: 1.0.0, actual: 0.9.0)
        deliverables_file = tmp_path / get_default_server_root() / "deliverables.json"
        deliverables_file.parent.mkdir(parents=True, exist_ok=True)
        deliverables_file.write_text(
            json.dumps({"schema_version": "0.9.0", "projects": {}}),
            encoding="utf-8",
        )

        # Calling get_project_plan should raise PlanningVersionMismatchError
        # because validation mismatch bubbles
        with pytest.raises(PlanningVersionMismatchError):
            manager.get_project_plan(42)

        # The mismatched file must have been backed up to deliverables.json.bak
        backup_file = deliverables_file.with_suffix(deliverables_file.suffix + ".bak")
        assert not deliverables_file.exists()
        assert backup_file.exists()

    def test_project_manager_write_deliverables_saves_envelope(self, tmp_path: Path) -> None:
        """Verify that ProjectManager saves deliverables nested in a version envelope."""
        manager = make_project_manager(tmp_path)

        manager.initialize_project(
            issue_number=42,
            issue_title="Versioning test",
            workflow_name="feature",
        )

        deliverables_file = tmp_path / get_default_server_root() / "deliverables.json"
        assert deliverables_file.exists()

        content = deliverables_file.read_text(encoding="utf-8")
        data = json.loads(content)

        assert data.get("schema_version") == "1.0.0"
        assert "projects" in data
        assert "42" in data["projects"]

    def test_project_manager_write_paths_delegate_to_write_deliverables(
        self, tmp_path: Path
    ) -> None:
        """Verify that write paths delegate to private _write_deliverables."""

        manager = make_project_manager(tmp_path)

        # pyright: ignore[reportPrivateUsage]  # inject test double on private method
        with patch.object(
            manager,
            "_write_deliverables",
            wraps=manager._write_deliverables,  # pyright: ignore[reportPrivateUsage]
        ) as mock_write:
            # 1. initialize_project
            manager.initialize_project(42, "Issue 42", "feature")
            assert mock_write.call_count == 1

            # 2. save_planning_deliverables
            mock_write.reset_mock()
            dummy_planning = {
                "cycles": {
                    "total": 1,
                    "cycles": [
                        {
                            "cycle_number": 1,
                            "deliverables": [{"id": "D1.1", "description": "dummy"}],
                            "exit_criteria": "dummy",
                        }
                    ],
                }
            }
            manager.save_planning_deliverables(42, dummy_planning)
            assert mock_write.call_count == 1

            # 3. update_planning_deliverables
            mock_write.reset_mock()
            manager.update_planning_deliverables(
                42,
                {
                    "cycles": {
                        "cycles": [
                            {
                                "cycle_number": 1,
                                "deliverables": [{"id": "D1.1", "description": "dummy"}],
                            }
                        ]
                    }
                },
            )
            assert mock_write.call_count == 1
