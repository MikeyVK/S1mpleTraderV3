# tests/mcp_server/unit/managers/test_quality_state_repository.py
"""C5 (C_QA_STATE_SPLIT): IQualityStateRepository protocol and FileQualityStateRepository.

Tests verify:
- IQualityStateRepository protocol exists in mcp_server.core.interfaces
- Protocol has load() -> QualityState and apply(mutate) -> None
- FileQualityStateRepository.load() returns QualityState() when backing file absent
- FileQualityStateRepository.load() returns persisted state when file present
- FileQualityStateRepository.apply() persists mutation via mutate callback
- FileQualityStateRepository satisfies IQualityStateRepository protocol

@layer: Tests (Unit)
@dependencies: pathlib, mcp_server.core.interfaces, mcp_server.managers.quality_state_repository
"""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import inspect
import json
from pathlib import Path

import mcp_server.managers.quality_state_repository as _qsr_module

# RED: will fail with ImportError until C5 GREEN adds IQualityStateRepository
from mcp_server.core.interfaces import IQualityStateRepository

# RED: will fail with ModuleNotFoundError until C5 GREEN creates quality_state_repository.py
from mcp_server.managers.quality_state_repository import FileQualityStateRepository

# RED: will fail with ModuleNotFoundError until C5 GREEN creates quality_state.py
from mcp_server.state.quality_state import QualityState
from tests.mcp_server.test_support import get_default_server_root


class TestIQualityStateRepositoryProtocol:
    """IQualityStateRepository protocol is defined in mcp_server.core.interfaces."""

    def test_protocol_importable(self) -> None:
        """IQualityStateRepository is importable from mcp_server.core.interfaces."""
        assert IQualityStateRepository is not None

    def test_protocol_has_load_method(self) -> None:
        """IQualityStateRepository protocol declares load()."""
        assert hasattr(IQualityStateRepository, "load")

    def test_protocol_has_apply_method(self) -> None:
        """IQualityStateRepository protocol declares apply()."""
        assert hasattr(IQualityStateRepository, "apply")

    def test_concrete_class_satisfies_protocol(self, tmp_path: Path) -> None:
        """FileQualityStateRepository satisfies IQualityStateRepository runtime check."""
        repo = FileQualityStateRepository(
            backing_file=tmp_path / get_default_server_root() / "quality_state.json"
        )
        assert isinstance(repo, IQualityStateRepository)


class TestQualityState:
    """Tests for QualityState model."""

    def test_quality_state_includes_schema_version(self) -> None:
        """Verify that QualityState defaults schema_version to '1.0.0'."""
        state = QualityState(baseline_sha="abc", failed_files=[])
        assert state.schema_version == "1.0.0"


class TestFileQualityStateRepositoryLoad:
    """FileQualityStateRepository.load() returns correct state."""

    def test_load_returns_empty_state_when_file_absent(self, tmp_path: Path) -> None:
        """load() returns QualityState() (all defaults) when backing file does not exist."""
        repo = FileQualityStateRepository(
            backing_file=tmp_path / get_default_server_root() / "quality_state.json"
        )
        state = repo.load()
        assert state == QualityState()

    def test_load_returns_persisted_baseline_sha(self, tmp_path: Path) -> None:
        """load() returns baseline_sha from persisted file."""
        backing = tmp_path / get_default_server_root() / "quality_state.json"
        backing.parent.mkdir(parents=True, exist_ok=True)
        backing.write_text(
            '{"schema_version": "1.0.0", "baseline_sha": "abc123", "failed_files": []}',
            encoding="utf-8",
        )
        repo = FileQualityStateRepository(backing_file=backing)
        state = repo.load()
        assert state.baseline_sha == "abc123"

    def test_load_returns_persisted_failed_files(self, tmp_path: Path) -> None:
        """load() returns failed_files from persisted file."""
        backing = tmp_path / get_default_server_root() / "quality_state.json"
        backing.parent.mkdir(parents=True, exist_ok=True)
        backing.write_text(
            '{"schema_version": "1.0.0", "baseline_sha": null, "failed_files": ["x.py", "y.py"]}',
            encoding="utf-8",
        )
        repo = FileQualityStateRepository(backing_file=backing)
        state = repo.load()
        assert state.failed_files == ["x.py", "y.py"]

    def test_load_returns_default_when_file_malformed(self, tmp_path: Path) -> None:
        """load() returns QualityState() when backing file is malformed JSON."""
        backing = tmp_path / get_default_server_root() / "quality_state.json"
        backing.parent.mkdir(parents=True, exist_ok=True)
        backing.write_text("not valid json", encoding="utf-8")
        repo = FileQualityStateRepository(backing_file=backing)
        state = repo.load()
        assert state == QualityState()


class TestFileQualityStateRepositoryApply:
    """FileQualityStateRepository.apply() mutates and persists state."""

    def test_apply_persists_mutation(self, tmp_path: Path) -> None:
        """apply() persists the mutated QualityState to backing file."""
        backing = tmp_path / get_default_server_root() / "quality_state.json"
        repo = FileQualityStateRepository(backing_file=backing)

        repo.apply(lambda _s: QualityState(baseline_sha="new_sha", failed_files=[]))

        state = repo.load()
        assert state.baseline_sha == "new_sha"
        assert state.failed_files == []

    def test_apply_receives_current_state(self, tmp_path: Path) -> None:
        """apply() passes current state to the mutate function."""
        backing = tmp_path / get_default_server_root() / "quality_state.json"
        backing.parent.mkdir(parents=True, exist_ok=True)
        backing.write_text(
            '{"schema_version": "1.0.0", "baseline_sha": "initial_sha", "failed_files": []}',
            encoding="utf-8",
        )
        repo = FileQualityStateRepository(backing_file=backing)

        seen: list[QualityState] = []

        def capture(s: QualityState) -> QualityState:
            seen.append(s)
            return s

        repo.apply(capture)
        assert len(seen) == 1
        assert seen[0].baseline_sha == "initial_sha"

    def test_apply_union_failed_files(self, tmp_path: Path) -> None:
        """apply() can accumulate failed_files via union in the mutate function."""
        backing = tmp_path / get_default_server_root() / "quality_state.json"
        backing.parent.mkdir(parents=True, exist_ok=True)
        backing.write_text(
            '{"schema_version": "1.0.0", "baseline_sha": "sha1", "failed_files": ["old.py"]}',
            encoding="utf-8",
        )
        repo = FileQualityStateRepository(backing_file=backing)

        def add_new(s: QualityState) -> QualityState:
            merged = sorted(set(s.failed_files) | {"new.py"})
            return QualityState(baseline_sha=s.baseline_sha, failed_files=merged)

        repo.apply(add_new)
        state = repo.load()
        assert "old.py" in state.failed_files
        assert "new.py" in state.failed_files

    def test_apply_serializes_schema_version(self, tmp_path: Path) -> None:
        """Verify that apply() serializes schema_version to backing file."""
        backing = tmp_path / get_default_server_root() / "quality_state.json"
        repo = FileQualityStateRepository(backing_file=backing)

        repo.apply(lambda _s: QualityState(baseline_sha="new_sha", failed_files=[]))

        content = backing.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data.get("schema_version") == "1.0.0"

    def test_quality_repository_resets_on_error_after_backup(self, tmp_path: Path) -> None:
        """Back up corrupt or mismatched quality state and return reset state."""
        backing = tmp_path / get_default_server_root() / "quality_state.json"
        backing.parent.mkdir(parents=True, exist_ok=True)
        backing.write_text("{corrupt json", encoding="utf-8")

        repo = FileQualityStateRepository(backing_file=backing)
        state = repo.load()

        backup_file = backing.with_suffix(backing.suffix + ".bak")
        assert not backing.exists()
        assert backup_file.exists()
        assert state.baseline_sha is None
        assert state.failed_files == []

    def test_apply_creates_parent_dirs(self, tmp_path: Path) -> None:
        """apply() creates parent directories if they don't exist."""
        backing = tmp_path / "deep" / "nested" / "quality_state.json"
        repo = FileQualityStateRepository(backing_file=backing)
        repo.apply(lambda _s: QualityState(baseline_sha="sha1"))
        assert backing.exists()

    def test_apply_is_atomic_via_atomic_json_writer(self) -> None:
        """FileQualityStateRepository uses AtomicJsonWriter for writes (source check)."""
        source = inspect.getsource(_qsr_module)
        assert "AtomicJsonWriter" in source, (
            "FileQualityStateRepository must use AtomicJsonWriter for atomic writes"
        )


# C3 RED — FileQualityStateRepository lock + QualityStateMutationConflictError (issue #292)


class TestFileQualityStateLockC3:
    """C3 (#292): FileQualityStateRepository.apply() must serialize concurrent access.

    Tests verify:
    - apply() raises QualityStateMutationConflictError when lock cannot be acquired within 5s
    - Two concurrent apply() calls both persist their mutations (no lost update under lock)
    """

    def test_apply_raises_conflict_error_on_timeout(self, tmp_path: Path) -> None:
        """apply() raises QualityStateMutationConflictError on lock timeout (C3-D1, C3-D2)."""
        from unittest.mock import MagicMock  # noqa: PLC0415

        import pytest  # noqa: PLC0415

        from mcp_server.managers.quality_state_repository import (  # noqa: PLC0415
            QualityStateMutationConflictError,
        )

        backing = tmp_path / get_default_server_root() / "quality_state.json"
        repo = FileQualityStateRepository(backing_file=backing)

        # Replace lock with a mock that simulates timeout (acquire returns False immediately).
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = False
        repo._lock = mock_lock  # pyright: ignore[reportPrivateUsage]  # Test lock injection.

        with pytest.raises(QualityStateMutationConflictError) as exc_info:
            repo.apply(lambda _s: _s)

        assert exc_info.value.diagnostic, "QualityStateMutationConflictError must have diagnostic"
        assert exc_info.value.recovery, "QualityStateMutationConflictError must have recovery"

    def test_concurrent_applies_both_land(self, tmp_path: Path) -> None:
        """Two concurrent apply() calls must both persist mutations (C3-D1, no lost update)."""
        import threading  # noqa: PLC0415
        import time  # noqa: PLC0415

        from mcp_server.managers.quality_state_repository import (  # noqa: PLC0415
            QualityStateMutationConflictError,
        )

        backing = tmp_path / get_default_server_root() / "quality_state.json"
        backing.parent.mkdir(parents=True, exist_ok=True)
        backing.write_text('{"baseline_sha": null, "failed_files": []}', encoding="utf-8")
        repo = FileQualityStateRepository(backing_file=backing)

        barrier = threading.Barrier(2)
        errors: list[Exception] = []

        def add_file(name: str) -> None:
            try:
                barrier.wait()

                def slow_mutate(s: QualityState) -> QualityState:
                    time.sleep(0.05)  # Force overlap to expose lost-update without lock.
                    return QualityState(
                        baseline_sha=s.baseline_sha,
                        failed_files=sorted(set(s.failed_files) | {name}),
                    )

                repo.apply(slow_mutate)
            except QualityStateMutationConflictError as e:
                errors.append(e)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        t1 = threading.Thread(target=add_file, args=("a.py",), daemon=True)
        t2 = threading.Thread(target=add_file, args=("b.py",), daemon=True)
        t1.start()
        t2.start()
        t1.join(timeout=10.0)
        t2.join(timeout=10.0)

        assert not errors, f"Unexpected errors in concurrent apply(): {errors}"
        final_state = repo.load()
        assert "a.py" in final_state.failed_files, "a.py must survive concurrent apply()"
        assert "b.py" in final_state.failed_files, "b.py must survive concurrent apply()"
