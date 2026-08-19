"""Tests for state repository abstractions and atomic state persistence.

Issue #257 Cycle 2 RED:
- BranchState frozen Pydantic model
- FileStateRepository and InMemoryStateRepository
- AtomicJsonWriter shared utility
- IStateReader / IStateRepository protocol split

@layer: Tests (Unit)
@dependencies: pytest, pydantic, json, pathlib, mcp_server.managers.state_repository
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from mcp_server.core.exceptions import StateCorruptedError, StateNotFoundError
from mcp_server.core.interfaces import IStateReader, IStateRepository
from mcp_server.managers.state_repository import (
    BranchState,
    BranchValidatedStateReader,
    FileStateRepository,
    InMemoryStateRepository,
    StateBranchMismatchError,
)
from mcp_server.utils.atomic_json_writer import AtomicJsonWriter
from tests.mcp_server.test_support import (
    get_default_server_root,
    make_phase_state_engine,
    make_project_manager,
)


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

    def test_branch_state_includes_schema_version(self) -> None:
        """Verify that BranchState defaults schema_version to '1.0.0'."""
        state = BranchState(
            branch="feature/257-reorder-workflow-phases",
            workflow_name="feature",
            current_phase="implementation",
            current_cycle=2,
            last_cycle=1,
            cycle_history=[],
            transitions=[],
        )
        assert state.schema_version == "1.0.0"


class TestFileStateRepository:
    """Tests for filesystem-backed state repository."""

    def test_load_returns_branch_state(self, tmp_path: Path) -> None:
        """Loading from state.json should return a validated BranchState instance."""
        state_file = tmp_path / get_default_server_root() / "state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "branch": "feature/257-reorder-workflow-phases",
                    "issue_number": 257,
                    "workflow_name": "feature",
                    "current_phase": "implementation",
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

    def test_file_state_repository_load_orchestrates_cqs_backup_on_error(
        self, tmp_path: Path
    ) -> None:
        """Loading a corrupt or version mismatched state file backs up file and raises exception."""
        state_file = tmp_path / get_default_server_root() / "state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        # Write corrupted JSON
        state_file.write_text("{corrupt json", encoding="utf-8")

        repository = FileStateRepository(state_file=state_file)
        with pytest.raises(StateCorruptedError):
            repository.load("feature/test")

        backup_file = state_file.with_suffix(state_file.suffix + ".bak")
        assert not state_file.exists()
        assert backup_file.exists()

    def test_save_persists_branch_state(self, tmp_path: Path) -> None:
        """Saving BranchState should write state.json through the shared atomic writer."""
        state_file = tmp_path / get_default_server_root() / "state.json"
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
        assert not (tmp_path / get_default_server_root() / "state.json").exists()


class TestAtomicJsonWriter:
    """Tests for shared atomic JSON writer."""

    def test_write_json_preserves_original_file_when_rename_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rename failure must not corrupt the original file contents."""
        target = tmp_path / get_default_server_root() / "state.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps({"current_phase": "design"}), encoding="utf-8")

        writer = AtomicJsonWriter()

        def failing_replace(src: Path, _dst: Path) -> None:
            if Path(src).name.startswith(".state.tmp"):
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
        repository = FileStateRepository(
            state_file=tmp_path / get_default_server_root() / "state.json"
        )

        reader = cast(IStateReader, repository)
        writable = cast(IStateRepository, repository)

        assert hasattr(reader, "load")
        assert hasattr(writable, "load")
        assert hasattr(writable, "save")


# ---------------------------------------------------------------------------
# C1 RED — StateBranchMismatchError + BranchValidatedStateReader (issue #231)
# ---------------------------------------------------------------------------


class TestStateBranchMismatchError:
    """StateBranchMismatchError is the single branch-mismatch contract for reads."""

    def test_is_exception(self) -> None:
        exc = StateBranchMismatchError("branch mismatch")
        assert isinstance(exc, Exception)

    def test_carries_message(self) -> None:
        exc = StateBranchMismatchError("loaded='main', requested='feature/1'")
        assert "main" in str(exc)
        assert "feature/1" in str(exc)

    def test_is_not_file_not_found_error(self) -> None:
        exc = StateBranchMismatchError("mismatch")
        assert not isinstance(exc, FileNotFoundError)


class TestBranchValidatedStateReader:
    """BranchValidatedStateReader rejects mismatched branch loads."""

    def _make_state(self, branch: str) -> BranchState:
        return BranchState(
            branch=branch,
            workflow_name="feature",
            current_phase="implementation",
            transitions=[],
        )

    class _FixedReader:
        """Stub reader that always returns the same state object."""

        def __init__(self, state: BranchState) -> None:
            self._state = state

        def load(self, _branch: str) -> BranchState:
            return self._state

    def test_accepts_matching_branch(self) -> None:
        state = self._make_state("feature/231-test")
        reader = BranchValidatedStateReader(self._FixedReader(state))
        loaded = reader.load("feature/231-test")
        assert loaded.branch == "feature/231-test"

    def test_raises_on_mismatched_branch(self) -> None:
        state = self._make_state("main")
        reader = BranchValidatedStateReader(self._FixedReader(state))
        with pytest.raises(StateBranchMismatchError):
            reader.load("feature/231-test")

    def test_raises_not_file_not_found_error(self) -> None:
        state = self._make_state("wrong-branch")
        reader = BranchValidatedStateReader(self._FixedReader(state))
        with pytest.raises(StateBranchMismatchError):
            reader.load("feature/231-test")

    def test_reader_protocol_satisfied(self) -> None:
        inner = InMemoryStateRepository()
        reader = BranchValidatedStateReader(inner)
        assert hasattr(reader, "load")


# ---------------------------------------------------------------------------
# C1 RED — BranchState.current_sub_phase + StateNotFoundError (issue #298)
# ---------------------------------------------------------------------------


class TestBranchStateCurrentSubPhase:
    """BranchState.current_sub_phase is a new optional field persisted in state.json."""

    def test_branch_state_current_sub_phase_defaults_to_none(self) -> None:
        """BranchState constructed without current_sub_phase must deserialise to None."""
        state = BranchState(
            branch="feature/298-test",
            workflow_name="feature",
            current_phase="implementation",
            transitions=[],
        )
        assert state.current_sub_phase is None

    def test_branch_state_current_sub_phase_persists(self, tmp_path: Path) -> None:
        """FileStateRepository save+load must round-trip current_sub_phase='red'."""
        state_file = tmp_path / get_default_server_root() / "state.json"
        repository = FileStateRepository(state_file=state_file)
        state = BranchState(
            branch="feature/298-test",
            workflow_name="feature",
            current_phase="implementation",
            transitions=[],
            current_sub_phase="red",
        )

        repository.save(state)
        loaded = repository.load("feature/298-test")

        assert loaded.current_sub_phase == "red"

    def test_branch_state_current_sub_phase_none_round_trips(self, tmp_path: Path) -> None:
        """FileStateRepository save+load must round-trip current_sub_phase=None."""
        state_file = tmp_path / get_default_server_root() / "state.json"
        repository = FileStateRepository(state_file=state_file)
        state = BranchState(
            branch="feature/298-test",
            workflow_name="feature",
            current_phase="implementation",
            transitions=[],
            current_sub_phase=None,
        )

        repository.save(state)
        loaded = repository.load("feature/298-test")

        assert loaded.current_sub_phase is None

    def test_branch_state_existing_json_without_sub_phase_deserialises(
        self, tmp_path: Path
    ) -> None:
        """Existing state.json files without current_sub_phase must not raise ValidationError."""
        state_file = tmp_path / get_default_server_root() / "state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "branch": "feature/298-test",
                    "workflow_name": "feature",
                    "current_phase": "implementation",
                    "transitions": [],
                }
            ),
            encoding="utf-8",
        )

        repository = FileStateRepository(state_file=state_file)
        loaded = repository.load("feature/298-test")

        assert loaded.current_sub_phase is None


class TestStateNotFoundError:
    """StateNotFoundError is a domain error distinct from FileNotFoundError."""

    def test_state_not_found_error_is_exception(self) -> None:
        """StateNotFoundError must be an Exception subclass."""
        exc = StateNotFoundError("feature/298-test")
        assert isinstance(exc, Exception)

    def test_state_not_found_error_carries_branch(self) -> None:
        """StateNotFoundError message must contain the branch name."""
        exc = StateNotFoundError("feature/298-test")
        assert "feature/298-test" in str(exc)

    def test_state_not_found_error_is_not_file_not_found_error(self) -> None:
        """StateNotFoundError must not be a FileNotFoundError (domain vs I/O error)."""
        exc = StateNotFoundError("feature/298-test")
        assert not isinstance(exc, FileNotFoundError)
