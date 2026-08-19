"""Tests for WorkflowStatusResolver (C3: C_RESOLVER_CORE RED phase)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from mcp_server.config.schemas.workphases import PhaseDefinition, WorkphasesConfig
from mcp_server.core.commit_phase_detector import CommitPhaseDetector
from mcp_server.core.interfaces import IGitContextReader
from mcp_server.managers.state_repository import (
    BranchState,
    BranchValidatedStateReader,
    InMemoryStateRepository,
    StateBranchMismatchError,
    StateNotFoundError,
)
from mcp_server.managers.workflow_status_resolver import WorkflowStatusResolver
from mcp_server.state.workflow_status import WorkflowStatusDTO
from tests.mcp_server.test_support import get_default_server_root

_TEST_WORKPHASES = WorkphasesConfig(
    phases={
        "research": PhaseDefinition(commit_type_hint="docs"),
        "planning": PhaseDefinition(commit_type_hint="docs"),
        "design": PhaseDefinition(commit_type_hint="docs"),
        "implementation": PhaseDefinition(
            commit_type_hint=None, subphases=["red", "green", "refactor"]
        ),
        "validation": PhaseDefinition(commit_type_hint="test"),
        "documentation": PhaseDefinition(commit_type_hint="docs"),
        "ready": PhaseDefinition(commit_type_hint="chore", terminal=True),
    }
)


class TestWorkflowStatusDTO:
    """WorkflowStatusDTO shape and immutability."""

    def test_dto_has_required_fields(self) -> None:
        dto = WorkflowStatusDTO(
            current_phase="implementation",
            phase_source="state.json",
            phase_confidence="high",
        )
        assert dto.current_phase == "implementation"
        assert dto.sub_phase is None
        assert dto.current_cycle is None
        assert dto.phase_source == "state.json"
        assert dto.phase_confidence == "high"
        assert dto.phase_detection_error is None

    def test_dto_is_frozen(self) -> None:
        dto = WorkflowStatusDTO(
            current_phase="research",
            phase_source="state.json",
            phase_confidence="high",
        )
        with pytest.raises(ValidationError):
            dto.current_phase = "other"  # type: ignore[misc]

    def test_dto_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowStatusDTO(  # type: ignore[call-arg]
                current_phase="research",
                phase_source="state.json",
                phase_confidence="high",
                unexpected_field="boom",
            )

    def test_dto_with_all_optional_fields(self) -> None:
        dto = WorkflowStatusDTO(
            current_phase="implementation",
            sub_phase="red",
            current_cycle=2,
            phase_source="state.json",
            phase_confidence="high",
            phase_detection_error=None,
        )
        assert dto.sub_phase == "red"
        assert dto.current_cycle == 2


class TestIGitContextReader:
    """IGitContextReader protocol surface exists."""

    def test_protocol_has_get_current_branch(self) -> None:
        assert hasattr(IGitContextReader, "get_current_branch")

    def test_protocol_has_get_recent_commits(self) -> None:
        assert hasattr(IGitContextReader, "get_recent_commits")

    def test_concrete_class_satisfies_protocol(self) -> None:
        class _Stub:
            def get_current_branch(self) -> str:
                return "feature/99-test"

            def get_recent_commits(self, limit: int = 5) -> list[str]:  # noqa: ARG002
                return []

            def get_status(self) -> dict[str, Any]:
                return {}

        assert isinstance(_Stub(), IGitContextReader)


class TestCommitPhaseDetector:
    """CommitPhaseDetector wraps ScopeDecoder (commit-scope-only, no state.json fallback)."""

    def test_detector_exists_and_detects_from_commit(self) -> None:
        detector = CommitPhaseDetector(workphases_config=_TEST_WORKPHASES)
        result = detector.detect_from_commit("feat(P_IMPLEMENTATION_SP_C3_GREEN): add dto")
        assert result["workflow_phase"] == "implementation"
        assert result["source"] == "commit-scope"

    def test_detector_never_reads_state_json(self, tmp_path: Path) -> None:
        state_dir = tmp_path / get_default_server_root()
        state_dir.mkdir()
        (state_dir / "state.json").write_text(
            '{"branch": "main", "current_phase": "research", "workflow_name": "feature"}'
        )
        detector = CommitPhaseDetector(workphases_config=_TEST_WORKPHASES)
        result = detector.detect_from_commit("feat(P_IMPLEMENTATION_SP_C3_RED): add tests")
        # Must read commit-scope, NOT state.json
        assert result["source"] == "commit-scope"
        assert result["workflow_phase"] == "implementation"

    def test_detector_returns_unknown_for_missing_scope(self) -> None:
        detector = CommitPhaseDetector(workphases_config=_TEST_WORKPHASES)
        result = detector.detect_from_commit("chore: bump version")
        assert result["workflow_phase"] == "unknown"
        assert result["source"] == "unknown"

    def test_detector_returns_unknown_for_none_commit(self) -> None:
        detector = CommitPhaseDetector(workphases_config=_TEST_WORKPHASES)
        result = detector.detect_from_commit(None)
        assert result["workflow_phase"] == "unknown"


class TestWorkflowStatusResolver:
    """WorkflowStatusResolver resolves current branch status."""

    def _make_resolver(
        self,
        branch: str = "feature/50-test",
        commits: list[str] | None = None,
        state_phase: str = "implementation",
        state_cycle: int | None = 3,
        state_sub_phase: str | None = None,
    ) -> WorkflowStatusResolver:
        git_reader = MagicMock()
        git_reader.get_current_branch.return_value = branch
        git_reader.get_recent_commits.return_value = commits or []

        state_repo = InMemoryStateRepository()
        state_repo.save(
            BranchState(
                branch=branch,
                current_phase=state_phase,
                current_cycle=state_cycle,
                current_sub_phase=state_sub_phase,
                workflow_name="feature",
                issue_number=50,
                parent_branch="main",
            )
        )

        detector = CommitPhaseDetector(workphases_config=_TEST_WORKPHASES)
        return WorkflowStatusResolver(
            git_context_reader=git_reader,
            state_reader=state_repo,
            commit_phase_detector=detector,
        )

    def test_resolve_current_returns_dto(self) -> None:
        resolver = self._make_resolver(
            commits=["feat(P_IMPLEMENTATION_SP_C3_GREEN): add resolver"],
        )
        result = resolver.resolve_current()
        assert isinstance(result, WorkflowStatusDTO)

    def test_resolve_uses_state_json_when_state_present(self) -> None:
        """After #298: resolver always uses state.json as source (phase_source='state.json')."""
        resolver = self._make_resolver(
            commits=["feat(P_IMPLEMENTATION_SP_C3_GREEN): add resolver"],
        )
        result = resolver.resolve_current()
        assert result.phase_source == "state.json"
        assert result.phase_confidence == "high"
        assert result.current_phase == "implementation"

    def test_resolve_falls_back_to_state_when_no_commit_scope(self) -> None:
        resolver = self._make_resolver(
            commits=["chore: bump version"],
            state_phase="research",
            state_cycle=None,
        )
        result = resolver.resolve_current()
        assert result.phase_source == "state.json"
        assert result.current_phase == "research"

    def test_resolve_current_cycle_from_state(self) -> None:
        resolver = self._make_resolver(
            commits=["feat(P_IMPLEMENTATION_SP_C3_GREEN): add resolver"],
            state_cycle=3,
        )
        result = resolver.resolve_current()
        assert result.current_cycle == 3

    def test_resolve_ignores_stale_commit_sub_phase_when_state_sub_phase_cleared(self) -> None:
        resolver = self._make_resolver(
            commits=["feat(P_IMPLEMENTATION_SP_C1_REFACTOR): completed cycle one"],
            state_cycle=2,
            state_sub_phase=None,
        )

        result = resolver.resolve_current()

        assert result.current_phase == "implementation"
        assert result.current_cycle == 2
        assert result.sub_phase is None

    def test_resolve_raises_state_not_found_on_branch_mismatch(self) -> None:
        """After #298: resolver raises StateNotFoundError when no state for current branch."""
        git_reader = MagicMock()
        git_reader.get_current_branch.return_value = "feature/99-other"
        git_reader.get_recent_commits.return_value = []

        state_repo = InMemoryStateRepository()
        state_repo.save(
            BranchState(
                branch="feature/50-test",  # mismatch Ã¢â‚¬â€ different branch
                current_phase="research",
                workflow_name="feature",
                issue_number=50,
                parent_branch="main",
            )
        )

        detector = CommitPhaseDetector(workphases_config=_TEST_WORKPHASES)
        resolver = WorkflowStatusResolver(
            git_context_reader=git_reader,
            state_reader=state_repo,
            commit_phase_detector=detector,
        )
        with pytest.raises(StateNotFoundError):
            resolver.resolve_current()


# ---------------------------------------------------------------------------
# C2 RED Ã¢â‚¬â€ WorkflowStatusDTO Literal narrowing (issue #298)
# ---------------------------------------------------------------------------


class TestWorkflowStatusDTOLiteralNarrowing:
    """WorkflowStatusDTO must reject dead Literal values after narrowing."""

    def test_workflow_status_dto_rejects_commit_scope_phase_source(self) -> None:
        """phase_source='commit-scope' must raise ValidationError after narrowing."""
        with pytest.raises(ValidationError):
            WorkflowStatusDTO(
                current_phase="implementation",
                phase_source="commit-scope",  # type: ignore[arg-type]
                phase_confidence="high",
            )

    def test_workflow_status_dto_rejects_unknown_phase_source(self) -> None:
        """phase_source='unknown' must raise ValidationError after narrowing."""
        with pytest.raises(ValidationError):
            WorkflowStatusDTO(
                current_phase="implementation",
                phase_source="unknown",  # type: ignore[arg-type]
                phase_confidence="high",
            )

    def test_workflow_status_dto_rejects_medium_phase_confidence(self) -> None:
        """phase_confidence='medium' must raise ValidationError after narrowing."""
        with pytest.raises(ValidationError):
            WorkflowStatusDTO(
                current_phase="implementation",
                phase_source="state.json",
                phase_confidence="medium",  # type: ignore[arg-type]
            )

    def test_workflow_status_dto_rejects_unknown_phase_confidence(self) -> None:
        """phase_confidence='unknown' must raise ValidationError after narrowing."""
        with pytest.raises(ValidationError):
            WorkflowStatusDTO(
                current_phase="implementation",
                phase_source="state.json",
                phase_confidence="unknown",  # type: ignore[arg-type]
            )

    def test_workflow_status_dto_accepts_state_json_high(self) -> None:
        """phase_source='state.json' + phase_confidence='high' must construct without error."""
        dto = WorkflowStatusDTO(
            current_phase="implementation",
            phase_source="state.json",
            phase_confidence="high",
        )
        assert dto.phase_source == "state.json"
        assert dto.phase_confidence == "high"


# ---------------------------------------------------------------------------
# C3 RED Ã¢â‚¬â€ WorkflowStatusResolver inversion (issue #298)
# ---------------------------------------------------------------------------


class TestWorkflowStatusResolverInversion:
    """After C3: resolver uses state.json as primary source, never commit-scope."""

    def _make_resolver_with_state(
        self,
        *,
        branch: str = "feature/298-test",
        state_phase: str = "implementation",
        state_cycle: int | None = 3,
        state_sub_phase: str | None = None,
        commits: list[str] | None = None,
    ) -> WorkflowStatusResolver:
        git_reader = MagicMock()
        git_reader.get_current_branch.return_value = branch
        git_reader.get_recent_commits.return_value = commits or []
        state_repo = InMemoryStateRepository()
        state_repo.save(
            BranchState(
                branch=branch,
                current_phase=state_phase,
                current_cycle=state_cycle,
                current_sub_phase=state_sub_phase,
                workflow_name="feature",
                issue_number=298,
                parent_branch="main",
            )
        )
        detector = CommitPhaseDetector(workphases_config=_TEST_WORKPHASES)
        return WorkflowStatusResolver(
            git_context_reader=git_reader,
            state_reader=state_repo,
            commit_phase_detector=detector,
        )

    def _make_resolver_no_state(
        self,
        *,
        branch: str = "feature/298-test",
        commits: list[str] | None = None,
    ) -> WorkflowStatusResolver:
        git_reader = MagicMock()
        git_reader.get_current_branch.return_value = branch
        git_reader.get_recent_commits.return_value = commits or []
        state_repo = InMemoryStateRepository()
        # no save Ã¢â€ â€™ state absent
        detector = CommitPhaseDetector(workphases_config=_TEST_WORKPHASES)
        return WorkflowStatusResolver(
            git_context_reader=git_reader,
            state_reader=state_repo,
            commit_phase_detector=detector,
        )

    def test_resolve_uses_state_when_present_despite_high_confidence_commit(self) -> None:
        """Even with a high-confidence commit-scope signal, state.json wins."""
        resolver = self._make_resolver_with_state(
            state_phase="research",
            commits=["feat(P_IMPLEMENTATION_SP_C3_GREEN): will be ignored"],
        )
        result = resolver.resolve_current()
        assert result.phase_source == "state.json"
        assert result.phase_confidence == "high"
        assert result.current_phase == "research"

    def test_resolve_raises_state_not_found_when_absent(self) -> None:
        """When state.json is absent, resolve_current() must raise StateNotFoundError."""
        resolver = self._make_resolver_no_state()
        with pytest.raises(StateNotFoundError):
            resolver.resolve_current()

    def test_resolve_raises_branch_mismatch_when_present_wrong_branch(self) -> None:
        """State present with wrong branch raises StateBranchMismatchError."""

        class _WrongBranchReader:
            """Always returns state whose branch field does not match what was requested."""

            def load(self, _branch: str) -> BranchState:
                return BranchState(
                    branch="feature/298-test",  # deliberately mismatched
                    current_phase="research",
                    workflow_name="feature",
                    issue_number=298,
                    parent_branch="main",
                )

        git_reader = MagicMock()
        git_reader.get_current_branch.return_value = "feature/298-other"
        git_reader.get_recent_commits.return_value = []
        validated_reader = BranchValidatedStateReader(_WrongBranchReader())
        detector = CommitPhaseDetector(workphases_config=_TEST_WORKPHASES)
        resolver = WorkflowStatusResolver(
            git_context_reader=git_reader,
            state_reader=validated_reader,
            commit_phase_detector=detector,
        )
        with pytest.raises(StateBranchMismatchError):
            resolver.resolve_current()
