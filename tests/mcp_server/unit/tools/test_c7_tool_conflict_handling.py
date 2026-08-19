# tests/mcp_server/unit/tools/test_c7_tool_conflict_handling.py
# template=manual version=1 created=2026-03-19 updated=
"""C7 RED tests — StateMutationConflictError surface in transition tools.

Issue #231/#292 — C7: Tools must handle StateMutationConflictError
explicitly: return ToolResult.error(diagnostic) and emit RecoveryNote
through the NoteContext.

Affected tools:
  - TransitionPhaseTool
  - ForcePhaseTransitionTool
  - TransitionCycleTool
  - ForceCycleTransitionTool

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.tools.phase_tools, mcp_server.tools.cycle_tools,
                mcp_server.managers.workflow_state_mutator,
                mcp_server.core.operation_notes]
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.workflow_state_mutator import StateMutationConflictError
from mcp_server.tools.cycle_tools import ForceCycleTransitionTool, TransitionCycleTool
from mcp_server.tools.phase_tools import (
    ForcePhaseTransitionInput,
    ForcePhaseTransitionTool,
    TransitionPhaseInput,
    TransitionPhaseTool,
)
from tests.mcp_server.test_support import (
    get_default_server_root,
    make_phase_state_engine,
    make_project_manager,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_conflict_engine(
    workspace_root: Path,
    *,
    diagnostic: str = "Lock timeout on branch 'feature/42'.",
    recovery: str = "Retry after the current operation completes.",
) -> PhaseStateEngine:
    """Return a PhaseStateEngine whose FIRST state-mutating call raises a conflict."""
    engine = make_phase_state_engine(workspace_root)
    conflict = StateMutationConflictError(diagnostic, recovery)
    engine.transition = MagicMock(side_effect=conflict)  # type: ignore[method-assign]
    engine.force_transition = MagicMock(side_effect=conflict)  # type: ignore[method-assign]
    engine.transition_cycle = MagicMock(side_effect=conflict)  # type: ignore[method-assign]
    engine.force_cycle_transition = MagicMock(side_effect=conflict)  # type: ignore[method-assign]
    return engine


# ---------------------------------------------------------------------------
# TestTransitionPhaseToolConflict
# ---------------------------------------------------------------------------


class TestTransitionPhaseToolConflict:
    """C7: TransitionPhaseTool surfaces StateMutationConflictError."""

    @pytest.fixture
    def conflict_tool(self, tmp_path: Path) -> TransitionPhaseTool:
        """TransitionPhaseTool with an engine that raises StateMutationConflictError."""
        pm = make_project_manager(tmp_path)
        engine = _make_conflict_engine(
            tmp_path,
            diagnostic="Lock timeout on branch 'feature/42'.",
            recovery="Retry after the current operation completes.",
        )
        return TransitionPhaseTool(
            workspace_root=tmp_path,
            project_manager=pm,
            state_engine=engine,
            server_root=tmp_path,
            workphases_config=None,
        )

    @pytest.mark.asyncio
    async def test_transition_phase_returns_error_on_conflict(
        self, conflict_tool: TransitionPhaseTool
    ) -> None:
        """TransitionPhaseTool returns ToolResult.error with diagnostic on conflict."""
        context = NoteContext()
        params = TransitionPhaseInput(branch="feature/42-x", to_phase="design")

        result = await conflict_tool.execute(params, context)

        assert not result.success
        assert result.error_message is not None
        assert "Lock timeout on branch 'feature/42'" in result.error_message

    @pytest.mark.asyncio
    async def test_transition_phase_emits_recovery_note_on_conflict(
        self, conflict_tool: TransitionPhaseTool
    ) -> None:
        """TransitionPhaseTool emits RecoveryNote through NoteContext on conflict."""
        context = NoteContext()
        params = TransitionPhaseInput(branch="feature/42-x", to_phase="design")

        await conflict_tool.execute(params, context)

        notes = [n for n in context.of_type(Note) if n.key == "transition_conflict_recovery"]
        assert len(notes) == 1
        assert "Retry after the current operation" in notes[0].params.get("recovery_steps", "")


# ---------------------------------------------------------------------------
# TestForcePhaseTransitionToolConflict
# ---------------------------------------------------------------------------


class TestForcePhaseTransitionToolConflict:
    """C7: ForcePhaseTransitionTool surfaces StateMutationConflictError."""

    @pytest.fixture
    def conflict_tool(self, tmp_path: Path) -> ForcePhaseTransitionTool:
        """ForcePhaseTransitionTool with engine that raises StateMutationConflictError."""
        pm = make_project_manager(tmp_path)
        engine = _make_conflict_engine(
            tmp_path,
            diagnostic="Mutation conflict on 'feature/42': branch mismatch.",
            recovery="Ensure the mutation callback preserves branch identity.",
        )
        return ForcePhaseTransitionTool(
            workspace_root=tmp_path,
            project_manager=pm,
            state_engine=engine,
            server_root=tmp_path,
            workphases_config=None,
        )

    @pytest.mark.asyncio
    async def test_force_transition_returns_error_on_conflict(
        self, conflict_tool: ForcePhaseTransitionTool
    ) -> None:
        """ForcePhaseTransitionTool returns ToolResult.error with diagnostic on conflict."""
        context = NoteContext()
        params = ForcePhaseTransitionInput(
            branch="feature/42-x",
            to_phase="validation",
            skip_reason="test",
            human_approval_message="Agent approved",
        )

        result = await conflict_tool.execute(params, context)

        assert not result.success
        assert result.error_message is not None
        assert "Mutation conflict on 'feature/42'" in result.error_message

    @pytest.mark.asyncio
    async def test_force_transition_emits_recovery_note_on_conflict(
        self, conflict_tool: ForcePhaseTransitionTool
    ) -> None:
        """ForcePhaseTransitionTool emits RecoveryNote through NoteContext on conflict."""
        context = NoteContext()
        params = ForcePhaseTransitionInput(
            branch="feature/42-x",
            to_phase="validation",
            skip_reason="test",
            human_approval_message="Agent approved",
        )

        await conflict_tool.execute(params, context)

        notes = [n for n in context.of_type(Note) if n.key == "transition_conflict_recovery"]
        assert len(notes) == 1
        assert "mutation callback" in notes[0].params.get("recovery_steps", "")


# ---------------------------------------------------------------------------
# TestTransitionCycleToolConflict
# ---------------------------------------------------------------------------


class TestTransitionCycleToolConflict:
    """C7: TransitionCycleTool surfaces StateMutationConflictError."""

    @pytest.fixture
    def conflict_tool(self, tmp_path: Path) -> TransitionCycleTool:
        """TransitionCycleTool with engine that raises StateMutationConflictError."""
        pm = make_project_manager(tmp_path)
        engine = _make_conflict_engine(
            tmp_path,
            diagnostic="Lock timeout acquiring mutation lock for branch 'feature/42'.",
            recovery="Another operation holds the lock. Retry after it completes.",
        )
        git_manager = MagicMock()
        git_manager.get_current_branch.return_value = "feature/42-test"
        git_config = MagicMock()
        git_config.extract_issue_number = MagicMock(return_value=42)
        git_manager.git_config = git_config

        # Write a minimal state.json so branch detection does not fall through
        state_dir = tmp_path / get_default_server_root()
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "state.json").write_text('{"branch": "feature/42-test"}', encoding="utf-8")

        return TransitionCycleTool(
            workspace_root=tmp_path,
            project_manager=pm,
            state_engine=engine,
            git_manager=git_manager,
            server_root=tmp_path,
        )

    @pytest.mark.asyncio
    async def test_transition_cycle_returns_error_on_conflict(
        self, conflict_tool: TransitionCycleTool
    ) -> None:
        """TransitionCycleTool returns ToolResult.error with diagnostic on conflict."""
        from mcp_server.tools.cycle_tools import TransitionCycleInput  # noqa: PLC0415

        context = NoteContext()
        params = TransitionCycleInput(to_cycle=2)

        result = await conflict_tool.execute(params, context)

        assert not result.success
        assert result.error_message is not None
        assert "Lock timeout" in result.error_message

    @pytest.mark.asyncio
    async def test_transition_cycle_emits_recovery_note_on_conflict(
        self, conflict_tool: TransitionCycleTool
    ) -> None:
        """TransitionCycleTool emits RecoveryNote through NoteContext on conflict."""
        from mcp_server.tools.cycle_tools import TransitionCycleInput  # noqa: PLC0415

        context = NoteContext()
        params = TransitionCycleInput(to_cycle=2)

        await conflict_tool.execute(params, context)

        notes = [n for n in context.of_type(Note) if n.key == "transition_conflict_recovery"]
        assert len(notes) == 1
        assert "lock" in notes[0].params.get("recovery_steps", "").lower()


# ---------------------------------------------------------------------------
# TestForceCycleTransitionToolConflict
# ---------------------------------------------------------------------------


class TestForceCycleTransitionToolConflict:
    """C7: ForceCycleTransitionTool surfaces StateMutationConflictError."""

    @pytest.fixture
    def conflict_tool(self, tmp_path: Path) -> ForceCycleTransitionTool:
        """ForceCycleTransitionTool with engine that raises StateMutationConflictError."""
        pm = make_project_manager(tmp_path)
        engine = _make_conflict_engine(
            tmp_path,
            diagnostic="Lock timeout acquiring mutation lock for branch 'feature/42'.",
            recovery="Retry after the current operation completes.",
        )
        git_manager = MagicMock()
        git_manager.get_current_branch.return_value = "feature/42-test"
        git_config = MagicMock()
        git_config.extract_issue_number = MagicMock(return_value=42)
        git_manager.git_config = git_config

        state_dir = tmp_path / get_default_server_root()
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "state.json").write_text('{"branch": "feature/42-test"}', encoding="utf-8")

        return ForceCycleTransitionTool(
            workspace_root=tmp_path,
            project_manager=pm,
            state_engine=engine,
            git_manager=git_manager,
            server_root=tmp_path,
        )

    @pytest.mark.asyncio
    async def test_force_cycle_transition_returns_error_on_conflict(
        self, conflict_tool: ForceCycleTransitionTool
    ) -> None:
        """ForceCycleTransitionTool returns ToolResult.error with diagnostic on conflict."""
        from mcp_server.tools.cycle_tools import ForceCycleTransitionInput  # noqa: PLC0415

        context = NoteContext()
        params = ForceCycleTransitionInput(
            to_cycle=1,
            skip_reason="test rollback",
            human_approval_message="Agent approved",
        )

        result = await conflict_tool.execute(params, context)

        assert not result.success
        assert result.error_message is not None
        assert "Lock timeout" in result.error_message

    @pytest.mark.asyncio
    async def test_force_cycle_transition_emits_recovery_note_on_conflict(
        self, conflict_tool: ForceCycleTransitionTool
    ) -> None:
        """ForceCycleTransitionTool emits RecoveryNote through NoteContext on conflict."""
        from mcp_server.tools.cycle_tools import ForceCycleTransitionInput  # noqa: PLC0415

        context = NoteContext()
        params = ForceCycleTransitionInput(
            to_cycle=1,
            skip_reason="test rollback",
            human_approval_message="Agent approved",
        )

        await conflict_tool.execute(params, context)

        notes = [n for n in context.of_type(Note) if n.key == "transition_conflict_recovery"]
        assert len(notes) == 1
        assert "Retry" in notes[0].params.get("recovery_steps", "")
