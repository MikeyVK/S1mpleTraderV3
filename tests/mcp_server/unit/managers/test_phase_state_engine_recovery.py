"""Tests for StateReconstructor after C_STATE_RECOVERY extraction."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.managers.project_manager import ProjectManager
from tests.mcp_server.test_support import make_project_manager, make_state_reconstructor


class TestStateReconstructor:
    """Direct tests for the extracted recovery component."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        return tmp_path

    @pytest.fixture
    def project_manager(self, workspace_root: Path) -> ProjectManager:
        manager = make_project_manager(workspace_root)
        manager.initialize_project(
            issue_number=39,
            issue_title="Test state reconstruction",
            workflow_name="bug",
        )
        return manager

    def test_reconstruct_infers_phase_from_git_scopes(
        self,
        workspace_root: Path,
        project_manager: ProjectManager,
    ) -> None:
        reconstructor = make_state_reconstructor(
            workspace_root,
            project_manager=project_manager,
        )

        with patch.object(
            reconstructor,
            "_get_git_commits",
            return_value=[
                "docs(P_DESIGN): Complete technical specifications",
                "docs(P_PLANNING): Define implementation goals",
            ],
        ):
            state = reconstructor.reconstruct("fix/39-test")

        assert state.branch == "fix/39-test"
        assert state.issue_number == 39
        assert state.workflow_name == "bug"
        assert state.current_phase == "design"
        assert state.transitions == []
        assert state.reconstructed is True

    def test_reconstruct_maps_implementation_subphases_to_workflow_phase(
        self,
        workspace_root: Path,
        project_manager: ProjectManager,
    ) -> None:
        reconstructor = make_state_reconstructor(
            workspace_root,
            project_manager=project_manager,
        )

        with patch.object(
            reconstructor,
            "_get_git_commits",
            return_value=[
                "feat(P_IMPLEMENTATION_SP_GREEN): Implement feature",
                "docs(P_DESIGN): Complete specs",
            ],
        ):
            state = reconstructor.reconstruct("fix/39-test")

        assert state.current_phase == "implementation"

    def test_reconstruct_falls_back_to_first_workflow_phase_when_no_scope_found(
        self,
        workspace_root: Path,
        project_manager: ProjectManager,
    ) -> None:
        reconstructor = make_state_reconstructor(
            workspace_root,
            project_manager=project_manager,
        )

        with patch.object(
            reconstructor,
            "_get_git_commits",
            return_value=[
                "Initial commit",
                "Add README",
            ],
        ):
            state = reconstructor.reconstruct("fix/39-test")

        assert state.current_phase == "research"
        assert state.reconstructed is True

    def test_reconstruct_raises_when_project_plan_missing(
        self,
        workspace_root: Path,
        project_manager: ProjectManager,
    ) -> None:
        reconstructor = make_state_reconstructor(
            workspace_root,
            project_manager=project_manager,
        )
        deliverables_file = workspace_root / ".st3" / "deliverables.json"
        if deliverables_file.exists():
            deliverables_file.unlink()

        with pytest.raises(ValueError, match="Project plan not found"):
            reconstructor.reconstruct("fix/39-test")

    def test_reconstruct_raises_for_invalid_branch_name(
        self,
        workspace_root: Path,
        project_manager: ProjectManager,
    ) -> None:
        reconstructor = make_state_reconstructor(
            workspace_root,
            project_manager=project_manager,
        )

        with pytest.raises(ValueError, match="Cannot extract issue number"):
            reconstructor.reconstruct("invalid-branch-name")

    def test_reconstruct_handles_git_errors_with_workflow_fallback(
        self,
        workspace_root: Path,
        project_manager: ProjectManager,
    ) -> None:
        reconstructor = make_state_reconstructor(
            workspace_root,
            project_manager=project_manager,
        )

        with patch.object(
            reconstructor,
            "_get_git_commits",
            side_effect=RuntimeError("Git failed"),
        ):
            state = reconstructor.reconstruct("fix/39-test")

        assert state.current_phase == "research"
        assert state.reconstructed is True
