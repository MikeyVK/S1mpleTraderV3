"""Tests for state repository abstractions and atomic state persistence.

Issue #257 Cycle 2 RED:
- BranchState frozen Pydantic model
- FileStateRepository and InMemoryStateRepository
- AtomicJsonWriter shared utility
- IStateReader / IStateRepository protocol split
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from mcp_server.core.interfaces import IStateReader, IStateRepository
from tests.mcp_server.test_support import make_phase_state_engine, make_project_manager
from mcp_server.managers.state_repository import (
    BranchState,
    FileStateRepository,
    InMemoryStateRepository,
)
from mcp_server.utils.atomic_json_writer import AtomicJsonWriter


class TestBranchState:
    """Tests for immutable BranchState."""

    def test_branch_state_is_frozen(self) -> None:
        """Mutating BranchState after construction must fail."""
        state = BranchState(
            branch="feature/257-reorder-workflow-phases",
            workflow_name="feature",
            current_phase="implementation",
            current_cycle=2,
            last_cycle=1,
            cycle_history=[],
            transitions=[],
        )

        with pytest.raises(ValidationError):
            state.current_phase = "validation"


class TestFileStateRepository:
    """Tests for filesystem-backed state repository."""

    def test_load_returns_branch_state(self, tmp_path: Path) -> None:
        """Loading from state.json should return a validated BranchState instance."""
        state_file = tmp_path / ".st3" / "state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text(
            json.dumps(
                {
                    "branch": "feature/257-reorder-workflow-phases",
                    "issue_number": 257,
                    "workflow_name": "feature",
                    "current_phase": "implementation",
                    "parent_branch": "main",
                    "transitions": [],
                    "created_at": "2026-03-12T00:00:00+00:00",
                    "current_cycle": 2,
                    "last_cycle": 1,
                    "cycle_history": [],
                }
            ),
            encoding="utf-8",
        )

        repository = FileStateRepository(state_file=state_file)
        state = repository.load("feature/257-reorder-workflow-phases")

        assert isinstance(state, BranchState)
        assert state.current_phase == "implementation"
        assert state.current_cycle == 2

    def test_save_persists_branch_state(self, tmp_path: Path) -> None:
        """Saving BranchState should write state.json through the shared atomic writer."""
        state_file = tmp_path / ".st3" / "state.json"
        repository = FileStateRepository(state_file=state_file)
        state = BranchState(
            branch="feature/257-reorder-workflow-phases",
            issue_number=257,
            workflow_name="feature",
            current_phase="implementation",
            parent_branch="main",
            transitions=[],
            created_at="2026-03-12T00:00:00+00:00",
            current_cycle=2,
            last_cycle=1,
            cycle_history=[],
        )

        repository.save(state)

        persisted = json.loads(state_file.read_text(encoding="utf-8"))
        assert persisted["current_phase"] == "implementation"
        assert persisted["current_cycle"] == 2


class TestInMemoryStateRepository:
    """Tests for in-memory state repository used by unit tests."""

    def test_save_and_load_round_trip(self) -> None:
        """In-memory repository should support save/load without touching the filesystem."""
        repository = InMemoryStateRepository()
        state = BranchState(
            branch="feature/257-reorder-workflow-phases",
            issue_number=257,
            workflow_name="feature",
            current_phase="implementation",
            parent_branch="main",
            transitions=[],
            created_at="2026-03-12T00:00:00+00:00",
            current_cycle=2,
            last_cycle=1,
            cycle_history=[],
        )

        repository.save(state)
        loaded = repository.load("feature/257-reorder-workflow-phases")

        assert loaded == state

    def test_phase_state_engine_uses_injected_repository(self, tmp_path: Path) -> None:
        """PSE should persist through the injected repository instead of direct file writes."""
        project_manager = make_project_manager(tmp_path)
        project_manager.initialize_project(
            issue_number=257,
            issue_title="Repository injection",
            workflow_name="feature",
        )
        repository = InMemoryStateRepository()
        engine = make_phase_state_engine(
            tmp_path,
            project_manager=project_manager,
            state_repository=repository,
        )

        engine.initialize_branch(
            branch="feature/257-reorder-workflow-phases",
            issue_number=257,
            initial_phase="implementation",
            parent_branch="main",
        )

        loaded = repository.load("feature/257-reorder-workflow-phases")
        assert loaded.current_phase == "implementation"
        assert not (tmp_path / ".st3" / "state.json").exists()


class TestAtomicJsonWriter:
    """Tests for shared atomic JSON writer."""

    def test_write_json_preserves_original_file_when_rename_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rename failure must not corrupt the original file contents."""
        target = tmp_path / ".st3" / "state.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps({"current_phase": "design"}), encoding="utf-8")

        writer = AtomicJsonWriter()

        def failing_replace(src: Path, _dst: Path) -> None:
            if Path(src).name == ".state.tmp":
                raise OSError("simulated rename failure")
            raise AssertionError("Unexpected replace target")

        monkeypatch.setattr("mcp_server.utils.atomic_json_writer.os.replace", failing_replace)

        with pytest.raises(OSError, match="simulated rename failure"):
            writer.write_json(target, {"current_phase": "implementation"}, temp_name=".state.tmp")

        persisted = json.loads(target.read_text(encoding="utf-8"))
        assert persisted["current_phase"] == "design"


class TestStateRepositoryProtocols:
    """Tests for protocol boundaries used for dependency injection."""

    def test_file_state_repository_satisfies_reader_and_repository_protocols(
        self, tmp_path: Path
    ) -> None:
        """FileStateRepository should satisfy both read-only and read-write protocols."""
        repository = FileStateRepository(state_file=tmp_path / ".st3" / "state.json")

        reader = cast(IStateReader, repository)
        writable = cast(IStateRepository, repository)

        assert hasattr(reader, "load")
        assert hasattr(writable, "load")
        assert hasattr(writable, "save")
