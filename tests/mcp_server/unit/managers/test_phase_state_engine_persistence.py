"""Tests for PhaseStateEngine state.json persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from tests.mcp_server.test_support import make_phase_state_engine, make_project_manager


class TestPhaseStateEnginePersistence:
    """Test persistence through explicit write operations, not query-side effects."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        return tmp_path

    @pytest.fixture
    def project_manager(self, workspace_root: Path) -> ProjectManager:
        manager = make_project_manager(workspace_root)
        manager.initialize_project(
            issue_number=1,
            issue_title="First feature",
            workflow_name="feature",
        )
        manager.initialize_project(
            issue_number=2,
            issue_title="Second feature",
            workflow_name="feature",
        )
        return manager

    @pytest.fixture
    def state_engine(
        self,
        workspace_root: Path,
        project_manager: ProjectManager,
    ) -> PhaseStateEngine:
        return make_phase_state_engine(
            workspace_root,
            project_manager=project_manager,
        )

    def test_initialize_branch_writes_single_branch_state(
        self,
        state_engine: PhaseStateEngine,
        workspace_root: Path,
    ) -> None:
        state_engine.initialize_branch("feature/1-first-feature", 1, "research")

        state_file = workspace_root / ".st3" / "state.json"
        assert state_file.exists()

        disk_state = json.loads(state_file.read_text(encoding="utf-8"))
        assert disk_state["branch"] == "feature/1-first-feature"
        assert disk_state["issue_number"] == 1
        assert "feature/1-first-feature" not in disk_state

    def test_initializing_second_branch_overwrites_state_json_completely(
        self,
        state_engine: PhaseStateEngine,
        workspace_root: Path,
    ) -> None:
        state_engine.initialize_branch("feature/1-first-feature", 1, "research")
        state_engine.initialize_branch("feature/2-second-feature", 2, "research")

        state_file = workspace_root / ".st3" / "state.json"
        disk_state = json.loads(state_file.read_text(encoding="utf-8"))
        assert disk_state["branch"] == "feature/2-second-feature"
        assert disk_state["issue_number"] == 2
        assert "feature/1-first-feature" not in json.dumps(disk_state)

    def test_transition_persists_updated_state_immediately(
        self,
        state_engine: PhaseStateEngine,
        workspace_root: Path,
    ) -> None:
        branch = "feature/1-first-feature"
        state_engine.initialize_branch(branch, 1, "research")

        result = state_engine.transition(branch=branch, to_phase="planning")
        state_file = workspace_root / ".st3" / "state.json"
        disk_state = json.loads(state_file.read_text(encoding="utf-8"))

        assert result == {
            "success": True,
            "from_phase": "research",
            "to_phase": "planning",
        }
        assert disk_state["current_phase"] == "planning"
        assert disk_state["branch"] == branch
