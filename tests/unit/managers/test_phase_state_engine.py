"""Tests for PhaseStateEngine entry/exit hooks.

Issue #146 Cycle 4: TDD phase lifecycle hooks.
Issue #229 Cycle 6: Research phase exit gate — file_glob support (GAP-10).
Issue #229 Cycle 7: Per-phase deliverable gate on design exit (GAP-11/D7.2).
"""

import json
from pathlib import Path

import pytest
import yaml

from mcp_server.managers.deliverable_checker import DeliverableCheckError
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager


class TestTDDPhaseHooks:
    """Tests for TDD phase entry/exit hooks.

    Issue #146 Cycle 4: on_enter_tdd_phase and on_exit_tdd_phase.
    """

    @pytest.fixture()
    def setup_project(self, tmp_path: Path) -> tuple[Path, int]:
        """Create project with planning deliverables."""
        workspace_root = tmp_path
        issue_number = 146

        project_manager = ProjectManager(workspace_root=workspace_root)

        # Initialize project
        project_manager.initialize_project(
            issue_number=issue_number,
            issue_title="TDD Cycle Tracking",
            workflow_name="feature",
        )

        # Save planning deliverables (4 cycles)
        planning_deliverables = {
            "tdd_cycles": {
                "total": 4,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": "Schema & Storage",
                        "deliverables": ["Schema"],
                        "exit_criteria": "Tests pass",
                    },
                    {
                        "cycle_number": 2,
                        "name": "Validation Logic",
                        "deliverables": ["Validators"],
                        "exit_criteria": "All scenarios covered",
                    },
                    {
                        "cycle_number": 3,
                        "name": "Discovery Tools",
                        "deliverables": ["get_work_context"],
                        "exit_criteria": "Tools return cycle info",
                    },
                    {
                        "cycle_number": 4,
                        "name": "Transition Tools",
                        "deliverables": ["transition_cycle", "force_cycle_transition"],
                        "exit_criteria": "All transitions working",
                    },
                ],
            }
        }
        project_manager.save_planning_deliverables(
            issue_number=issue_number, planning_deliverables=planning_deliverables
        )

        return workspace_root, issue_number

    def test_on_enter_tdd_phase_initializes_cycle_1(self, setup_project: tuple[Path, int]) -> None:
        """Test that entering TDD phase auto-initializes cycle 1."""
        # Arrange
        workspace_root, issue_number = setup_project
        branch = "feature/146-tdd-cycle-tracking"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize branch in design phase
        state_engine.initialize_branch(
            branch=branch, issue_number=issue_number, initial_phase="design"
        )

        # Verify no TDD cycle yet
        state = state_engine.get_state(branch)
        assert state.get("current_tdd_cycle") is None

        # Act
        state_engine.on_enter_tdd_phase(branch, issue_number)

        # Assert
        state = state_engine.get_state(branch)
        assert state.get("current_tdd_cycle") == 1
        assert state.get("last_tdd_cycle") == 0

    def test_on_enter_tdd_phase_does_not_block_without_planning_deliverables(
        self, tmp_path: Path
    ) -> None:
        """Test that entering TDD phase does NOT block on missing planning deliverables.

        GAP-02 fix (Issue #229 C2): the planning-deliverables check was moved to
        on_exit_planning_phase. TDD entry must no longer enforce this contract.
        """
        # Arrange
        workspace_root = tmp_path
        issue_number = 146
        branch = "feature/146-tdd-cycle-tracking"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize project WITHOUT planning deliverables
        project_manager.initialize_project(
            issue_number=issue_number,
            issue_title="TDD Cycle Tracking",
            workflow_name="feature",
        )

        state_engine.initialize_branch(
            branch=branch, issue_number=issue_number, initial_phase="design"
        )

        # Act & Assert — must NOT raise; gate lives at planning exit now
        state_engine.on_enter_tdd_phase(branch, issue_number)
        state = state_engine.get_state(branch)
        assert state.get("current_tdd_cycle") == 1

    def test_on_exit_tdd_phase_preserves_last_cycle(self, setup_project: tuple[Path, int]) -> None:
        """Test that exiting TDD phase preserves last_tdd_cycle."""
        # Arrange
        workspace_root, issue_number = setup_project
        branch = "feature/146-tdd-cycle-tracking"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize in TDD phase at cycle 3
        state_engine.initialize_branch(
            branch=branch, issue_number=issue_number, initial_phase="tdd"
        )
        state = state_engine.get_state(branch)
        state["current_tdd_cycle"] = 3
        state_engine._save_state(branch, state)

        # Act
        state_engine.on_exit_tdd_phase(branch)

        # Assert
        state = state_engine.get_state(branch)
        assert state.get("last_tdd_cycle") == 3
        assert state.get("current_tdd_cycle") is None

    def test_on_exit_tdd_phase_validates_completion(self, setup_project: tuple[Path, int]) -> None:
        """Test that exiting TDD phase validates all cycles completed."""
        # Arrange
        workspace_root, issue_number = setup_project
        branch = "feature/146-tdd-cycle-tracking"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize in TDD phase at cycle 2 (not completed)
        state_engine.initialize_branch(
            branch=branch, issue_number=issue_number, initial_phase="tdd"
        )
        state = state_engine.get_state(branch)
        state["current_tdd_cycle"] = 2
        state_engine._save_state(branch, state)

        # Act
        # Design decision: Allow exit with warning (logs but doesn't block)
        state_engine.on_exit_tdd_phase(branch)

        # Assert
        state = state_engine.get_state(branch)
        assert state.get("last_tdd_cycle") == 2
        assert state.get("current_tdd_cycle") is None


class TestTransitionHooksWiring:
    """Tests that transition() automatically calls entry/exit hooks (Issue #146 Cycle 5 D3)."""

    @pytest.fixture()
    def setup_project(self, tmp_path: Path) -> tuple[Path, int]:
        """Create project with planning deliverables."""
        workspace_root = tmp_path
        issue_number = 999

        project_manager = ProjectManager(workspace_root=workspace_root)
        project_manager.initialize_project(
            issue_number=issue_number,
            issue_title="Hook Wiring Test",
            workflow_name="feature",
        )
        project_manager.save_planning_deliverables(
            issue_number=issue_number,
            planning_deliverables={
                "tdd_cycles": {
                    "total": 1,
                    "cycles": [
                        {
                            "cycle_number": 1,
                            "name": "Basic",
                            "deliverables": ["A"],
                            "exit_criteria": "pass",
                        }
                    ],
                }
            },
        )
        return workspace_root, issue_number

    def test_transition_to_tdd_calls_enter_hook(self, setup_project: tuple[Path, int]) -> None:
        """Test that transition() to 'tdd' auto-calls on_enter_tdd_phase (Issue #146)."""
        workspace_root, issue_number = setup_project
        branch = "feature/999-hook-wiring"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize branch in design phase
        state_engine.initialize_branch(
            branch=branch, issue_number=issue_number, initial_phase="design"
        )

        # Verify no TDD cycle before transition
        state = state_engine.get_state(branch)
        assert state.get("current_tdd_cycle") is None

        # Transition to TDD - should auto-call on_enter_tdd_phase
        state_engine.transition(branch=branch, to_phase="tdd")

        # Assert: hook was triggered and cycle 1 was initialized
        state = state_engine.get_state(branch)
        assert state.get("current_tdd_cycle") == 1, (
            "on_enter_tdd_phase was not called by transition() - "
            "current_tdd_cycle should be 1 after entering TDD phase"
        )

    def test_transition_from_tdd_calls_exit_hook(self, setup_project: tuple[Path, int]) -> None:
        """Test that transition() from 'tdd' auto-calls on_exit_tdd_phase (Issue #146)."""
        workspace_root, issue_number = setup_project
        branch = "feature/999-hook-wiring"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize branch in TDD phase at cycle 2
        state_engine.initialize_branch(
            branch=branch, issue_number=issue_number, initial_phase="tdd"
        )
        state = state_engine.get_state(branch)
        state["current_tdd_cycle"] = 2
        state_engine._save_state(branch, state)

        # Transition away from TDD - should auto-call on_exit_tdd_phase
        state_engine.transition(branch=branch, to_phase="validation")

        # Assert: hook was triggered and last_tdd_cycle was preserved
        state = state_engine.get_state(branch)
        assert state.get("last_tdd_cycle") == 2, (
            "on_exit_tdd_phase was not called by transition() - "
            "last_tdd_cycle should be 2 after exiting TDD phase"
        )
        assert state.get("current_tdd_cycle") is None, (
            "current_tdd_cycle should be None after exiting TDD phase"
        )


class TestResearchExitGate:
    """Tests for research phase exit gate (Issue #229 C6, GAP-10).

    on_exit_research_phase() reads exit_requires from workphases.yaml for 'research'.
    Supports type: file_glob with {issue_number} interpolation.
    - D6.1: file_glob dispatch in PhaseStateEngine
    - D6.2: research.exit_requires in workphases.yaml
    """

    def _workphases_yaml(self, tmp_path: Path, research_exit_requires: list | None = None) -> Path:
        """Write a minimal workphases.yaml to tmp_path / .st3 / workphases.yaml."""
        content: dict = {"version": "1.0", "phases": {"research": {}}}
        if research_exit_requires is not None:
            content["phases"]["research"]["exit_requires"] = research_exit_requires
        path = tmp_path / ".st3" / "workphases.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump(content))
        return path

    def _setup_project(self, tmp_path: Path, issue_number: int, phase: str = "research") -> None:
        """Initialize a project in the given phase."""
        manager = ProjectManager(workspace_root=tmp_path)
        manager.initialize_project(
            issue_number=issue_number,
            issue_title="Research exit gate test",
            workflow_name="feature",
        )
        engine = PhaseStateEngine(workspace_root=tmp_path, project_manager=manager)
        engine.initialize_branch(
            branch=f"feature/{issue_number}-test",
            issue_number=issue_number,
            initial_phase=phase,
        )

    def test_on_exit_research_phase_silent_when_no_exit_requires(self, tmp_path: Path) -> None:
        """No exit_requires configured → passes without raising. (D6.1)"""
        self._workphases_yaml(tmp_path, research_exit_requires=None)
        self._setup_project(tmp_path, issue_number=300)
        manager = ProjectManager(workspace_root=tmp_path)
        engine = PhaseStateEngine(workspace_root=tmp_path, project_manager=manager)

        # Must not raise
        engine.on_exit_research_phase(branch="feature/300-test", issue_number=300)

    def test_on_exit_research_phase_passes_when_file_glob_matches(self, tmp_path: Path) -> None:
        """file_glob exit gate passes when at least one file matches. (D6.1)"""
        self._workphases_yaml(
            tmp_path,
            research_exit_requires=[
                {
                    "type": "file_glob",
                    "file": "docs/development/issue{issue_number}/*research*.md",
                    "description": "Research document aanwezig",
                }
            ],
        )
        self._setup_project(tmp_path, issue_number=301)

        # Create matching file
        doc_dir = tmp_path / "docs" / "development" / "issue301"
        doc_dir.mkdir(parents=True)
        (doc_dir / "my-research-notes.md").write_text("# Research")

        manager = ProjectManager(workspace_root=tmp_path)
        engine = PhaseStateEngine(workspace_root=tmp_path, project_manager=manager)

        # Must not raise
        engine.on_exit_research_phase(branch="feature/301-test", issue_number=301)

    def test_on_exit_research_phase_raises_when_file_glob_not_found(self, tmp_path: Path) -> None:
        """file_glob exit gate raises when no file matches the pattern. (D6.1)"""
        self._workphases_yaml(
            tmp_path,
            research_exit_requires=[
                {
                    "type": "file_glob",
                    "file": "docs/development/issue{issue_number}/*research*.md",
                    "description": "Research document aanwezig",
                }
            ],
        )
        self._setup_project(tmp_path, issue_number=302)

        # No matching file created
        manager = ProjectManager(workspace_root=tmp_path)
        engine = PhaseStateEngine(workspace_root=tmp_path, project_manager=manager)

        with pytest.raises(DeliverableCheckError):
            engine.on_exit_research_phase(branch="feature/302-test", issue_number=302)

    def test_on_exit_research_phase_interpolates_issue_number(self, tmp_path: Path) -> None:
        """Pattern {issue_number} is substituted before globbing. (D6.1)"""
        issue_number = 303
        self._workphases_yaml(
            tmp_path,
            research_exit_requires=[
                {
                    "type": "file_glob",
                    "file": "docs/development/issue{issue_number}/*research*.md",
                    "description": "Research document",
                }
            ],
        )
        self._setup_project(tmp_path, issue_number=issue_number)

        # Create file for the WRONG issue number — must still fail
        wrong_dir = tmp_path / "docs" / "development" / "issue999"
        wrong_dir.mkdir(parents=True)
        (wrong_dir / "my-research.md").write_text("# Research")

        manager = ProjectManager(workspace_root=tmp_path)
        engine = PhaseStateEngine(workspace_root=tmp_path, project_manager=manager)

        with pytest.raises(DeliverableCheckError):
            engine.on_exit_research_phase(branch="feature/303-test", issue_number=issue_number)

    def test_transition_from_research_triggers_exit_hook(self, tmp_path: Path) -> None:
        """transition(research→planning) calls on_exit_research_phase. (D6.1 wiring)"""
        issue_number = 304
        self._workphases_yaml(
            tmp_path,
            research_exit_requires=[
                {
                    "type": "file_glob",
                    "file": "docs/development/issue{issue_number}/*research*.md",
                    "description": "Research document aanwezig",
                }
            ],
        )
        manager = ProjectManager(workspace_root=tmp_path)
        manager.initialize_project(
            issue_number=issue_number,
            issue_title="Transition wiring test",
            workflow_name="feature",
        )
        engine = PhaseStateEngine(workspace_root=tmp_path, project_manager=manager)
        engine.initialize_branch(
            branch="feature/304-test",
            issue_number=issue_number,
            initial_phase="research",
        )

        # No matching file → transition must raise DeliverableCheckError
        with pytest.raises(DeliverableCheckError):
            engine.transition(branch="feature/304-test", to_phase="planning")


class TestPerPhaseDeliverableGate:
    """Tests for per-phase deliverable gate on design exit (Issue #229 C7, GAP-11).

    on_exit_design_phase() reads planning_deliverables.design.deliverables and
    runs DeliverableChecker.check() for each entry that has a validates spec.
    - D7.1: save_planning_deliverables accepts optional phase keys
    - D7.2: gate check in PhaseStateEngine.on_exit_design_phase()
    """

    def _make_engine(
        self, tmp_path: Path, issue_number: int = 229, deliverables_state: dict | None = None
    ) -> PhaseStateEngine:
        """Build a PhaseStateEngine in design phase with optional planning_deliverables injected."""
        manager = ProjectManager(workspace_root=tmp_path)
        manager.initialize_project(
            issue_number=issue_number,
            issue_title="Per-phase deliverable gate test",
            workflow_name="feature",
        )
        engine = PhaseStateEngine(workspace_root=tmp_path, project_manager=manager)
        engine.initialize_branch(
            branch=f"feature/{issue_number}-test",
            issue_number=issue_number,
            initial_phase="design",
        )
        # Inject planning_deliverables into projects.json (gate reads from project plan)
        if deliverables_state is not None:
            projects_path = tmp_path / ".st3" / "projects.json"
            projects_data: dict = json.loads(projects_path.read_text())
            projects_data[str(issue_number)]["planning_deliverables"] = deliverables_state
            projects_path.write_text(json.dumps(projects_data, indent=2))
        return engine

    def test_on_exit_design_gate_silent_when_phase_key_absent(self, tmp_path: Path) -> None:
        """Gate is optional: no planning_deliverables.design → silent pass."""
        engine = self._make_engine(tmp_path, deliverables_state={"tdd_cycles": {}})
        # Should not raise even though no design key present
        engine.on_exit_design_phase(branch="feature/229-test", issue_number=229)

    def test_on_exit_design_gate_passes_when_validates_spec_satisfied(self, tmp_path: Path) -> None:
        """Gate passes when DeliverableChecker.check() succeeds for all deliverables."""
        # Create matching file in tmp_path (which is the workspace root used by _make_engine)
        docs_dir = tmp_path / "docs" / "development" / "issue229"
        docs_dir.mkdir(parents=True)
        (docs_dir / "design.md").write_text("# Design")

        deliverables_state = {
            "design": {
                "deliverables": [
                    {
                        "id": "D7.1",
                        "description": "Design document",
                        "validates": {
                            "type": "file_glob",
                            "dir": "docs/development/issue229",
                            "pattern": "design*.md",
                        },
                    }
                ]
            }
        }
        engine = self._make_engine(tmp_path, deliverables_state=deliverables_state)
        # Should not raise
        engine.on_exit_design_phase(branch="feature/229-test", issue_number=229)

    def test_on_exit_design_gate_raises_when_validates_spec_fails(self, tmp_path: Path) -> None:
        """Gate raises DeliverableCheckError when required file is missing."""
        deliverables_state = {
            "design": {
                "deliverables": [
                    {
                        "id": "D7.1",
                        "description": "Design document",
                        "validates": {
                            "type": "file_glob",
                            "dir": "docs/development/issue229",
                            "pattern": "design*.md",
                        },
                    }
                ]
            }
        }
        engine = self._make_engine(tmp_path, deliverables_state=deliverables_state)
        with pytest.raises(DeliverableCheckError):
            engine.on_exit_design_phase(branch="feature/229-test", issue_number=229)
