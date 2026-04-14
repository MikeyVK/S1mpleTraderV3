# tests/mcp_server/unit/managers/test_git_manager_no_file_open.py
# template=unit_test version=manual created=2026-05-01T00:00Z updated=
"""
Unit test proving GitManager.commit_with_scope executes without file I/O.

C5 gate proof: after WorkphasesConfig injection, commit_with_scope must NOT open
any files — it must read phase metadata directly from the injected WorkphasesConfig
object.

@layer: Tests (Unit)
@dependencies: [pytest, unittest.mock, mcp_server.managers.git_manager,
    mcp_server.config.schemas.workphases]
@responsibilities:
    - Verify commit_with_scope performs no open() calls when workphases_config injected
    - Verify correct commit message is generated from WorkphasesConfig without file I/O
"""

# Standard library
from unittest.mock import MagicMock, patch

# Third-party
import pytest

# Project modules
from mcp_server.config.schemas.workphases import PhaseDefinition, WorkphasesConfig
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.git_manager import GitManager
from mcp_server.schemas import GitConfig

_TEST_WORKPHASES = WorkphasesConfig(
    phases={
        "research": PhaseDefinition(commit_type_hint="docs"),
        "implementation": PhaseDefinition(
            commit_type_hint=None,
            subphases=["red", "green", "refactor"],
        ),
        "documentation": PhaseDefinition(commit_type_hint="docs", terminal=True),
    }
)


def _make_manager(mock_adapter: MagicMock) -> GitManager:
    """Build GitManager with injected WorkphasesConfig — no file I/O required."""
    git_config = MagicMock(spec=GitConfig)
    return GitManager(
        git_config=git_config,
        adapter=mock_adapter,
        workphases_config=_TEST_WORKPHASES,
    )


class TestGitManagerNoFileOpen:
    """Proof that commit_with_scope performs no open() calls when config injected."""

    def test_commit_with_scope_no_file_open_phase_only(self) -> None:
        """commit_with_scope for phase-only scope opens no files."""
        mock_adapter = MagicMock()
        mock_adapter.commit.return_value = "abc123"
        manager = _make_manager(mock_adapter)

        with patch("builtins.open") as mock_open:
            manager.commit_with_scope(
                workflow_phase="research",
                message="complete analysis",
                note_context=NoteContext(),
            )
            mock_open.assert_not_called()

        mock_adapter.commit.assert_called_once_with(
            "docs(P_RESEARCH): complete analysis",
            files=None,
            skip_paths=frozenset(),
        )

    def test_commit_with_scope_no_file_open_with_subphase(self) -> None:
        """commit_with_scope for phase + subphase opens no files."""
        mock_adapter = MagicMock()
        mock_adapter.commit.return_value = "def456"
        manager = _make_manager(mock_adapter)

        with patch("builtins.open") as mock_open:
            manager.commit_with_scope(
                workflow_phase="implementation",
                message="add failing test",
                sub_phase="red",
                cycle_number=1,
                note_context=NoteContext(),
            )
            mock_open.assert_not_called()

        mock_adapter.commit.assert_called_once_with(
            "chore(P_IMPLEMENTATION_SP_C1_RED): add failing test",
            files=None,
            skip_paths=frozenset(),
        )

    def test_commit_with_scope_no_file_open_with_commit_type_override(self) -> None:
        """commit_with_scope with explicit commit_type override opens no files."""
        mock_adapter = MagicMock()
        mock_adapter.commit.return_value = "ghi789"
        manager = _make_manager(mock_adapter)

        with patch("builtins.open") as mock_open:
            manager.commit_with_scope(
                workflow_phase="research",
                message="update notes",
                commit_type="chore",
                note_context=NoteContext(),
            )
            mock_open.assert_not_called()

        mock_adapter.commit.assert_called_once_with(
            "chore(P_RESEARCH): update notes",
            files=None,
            skip_paths=frozenset(),
        )

    def test_commit_with_scope_uses_null_commit_type_hint_as_chore(self) -> None:
        """Phase with null commit_type_hint falls back to 'chore' without reading files."""
        mock_adapter = MagicMock()
        mock_adapter.commit.return_value = "jkl012"
        # documentation has commit_type_hint="docs", implementation has null
        manager = _make_manager(mock_adapter)

        with patch("builtins.open") as mock_open:
            manager.commit_with_scope(
                workflow_phase="implementation",
                message="implement feature",
                sub_phase="green",
                cycle_number=2,
                note_context=NoteContext(),
            )
            mock_open.assert_not_called()

        # implementation has commit_type_hint=None → falls back to "chore"
        mock_adapter.commit.assert_called_once_with(
            "chore(P_IMPLEMENTATION_SP_C2_GREEN): implement feature",
            files=None,
            skip_paths=frozenset(),
        )
