# tests/unit/mcp_server/schemas/test_tracking_artifact_v2_parity.py
# SCAFFOLD: test:manual | 2026-02-18T00:00:00Z | tests/unit/mcp_server/schemas/test_tracking_artifact_v2_parity.py  # noqa: E501
"""V2 parity tests for tracking artifact types (Issue #135 Cycle 7).

SCOPE (Cycle 7 - Tracking Artifact V2):
  commit, pr, issue

3 tests per artifact type (9 total):
  1. context_validates_minimal  - schema creates with required fields only; fails if schema absent
  2. v2_routing_confirmed       - _enrich_context_v2 IS called; fails while not in registry
  3. v2_rejects_invalid_context - empty context raises ValidationError;
     fails while V1 fallback active

Note on ephemeral artifacts:
  Tracking artifacts (commit, pr, issue) use output_type: ephemeral — they write to .st3/temp/
  instead of via fs_adapter.write_file. _run_v2_tracking patches _validate_and_write to avoid
  actual file writes in unit tests.

Note on parity definition (aligned with Cycles 5+6 docstring):
  Parity = smoke: both pipelines produce valid output with routing confirmed.
  Tracking artifacts have no SCAFFOLD header (output_type=ephemeral, no disk persistence).
"""

import asyncio  # noqa: I001
import os
from pathlib import Path

import pytest

from mcp_server.core.exceptions import ValidationError
from mcp_server.managers.artifact_manager import ArtifactManager


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_manager(tmp_path: Path) -> ArtifactManager:
    return ArtifactManager(workspace_root=str(tmp_path))


def _run_v2_tracking(manager: ArtifactManager, artifact_type: str, context: dict) -> str:
    """Run V2 pipeline for tracking (ephemeral) artifacts, return rendered content.

    Unlike _run_v2 (which mocks fs_adapter.write_file), tracking artifacts bypass
    fs_adapter and write to .st3/temp/ via Path.write_text. We patch _validate_and_write
    to capture content before the ephemeral write occurs.
    """
    output_captured: list[str] = []
    original_vaw = manager._validate_and_write

    async def mock_vaw(
        art_type: str,  # noqa: ARG001
        path: str,  # noqa: ARG001
        content: str,
        **kwargs: object,  # noqa: ARG001
    ) -> str:
        output_captured.append(content)
        return "mocked_path"

    manager._validate_and_write = mock_vaw  # type: ignore[method-assign]
    os.environ["PYDANTIC_SCAFFOLDING_ENABLED"] = "true"
    try:
        asyncio.run(manager.scaffold_artifact(artifact_type, **context))
    finally:
        os.environ.pop("PYDANTIC_SCAFFOLDING_ENABLED", None)
        manager._validate_and_write = original_vaw  # type: ignore[method-assign]

    assert len(output_captured) == 1, f"V2 pipeline produced no output for {artifact_type}"
    return output_captured[0]


def _spy_v2_routed(manager: ArtifactManager) -> list[bool]:
    """Spy whether _enrich_context_v2 is called (V2 pipeline active, not V1 fallback)."""
    v2_calls: list[bool] = []
    original = manager._enrich_context_v2

    def spy(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        v2_calls.append(True)
        return original(*args, **kwargs)

    manager._enrich_context_v2 = spy  # type: ignore[method-assign]
    return v2_calls


# ---------------------------------------------------------------------------
# Commit (3 tests)
# ---------------------------------------------------------------------------


class TestCommitV2Parity:
    """V2 parity tests for commit tracking artifact."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        return _make_manager(tmp_path)

    _MINIMAL = {
        "type": "feat",
        "message": "add V2 schemas for tracking artifacts",
    }

    def test_commit_context_validates_minimal(self) -> None:
        """CommitContext schema accepts minimal required fields."""
        from mcp_server.schemas import CommitContext  # noqa: PLC0415

        ctx = CommitContext(**self._MINIMAL)
        assert ctx.type == self._MINIMAL["type"]
        assert ctx.message == self._MINIMAL["message"]

    def test_commit_v2_routing_confirmed(self, manager: ArtifactManager) -> None:
        """Commit V2 pipeline routes via _enrich_context_v2 (not V1 fallback)."""
        calls = _spy_v2_routed(manager)
        _run_v2_tracking(manager, "commit", self._MINIMAL)
        assert len(calls) == 1, "V2 routing not active for commit — not in _v2_context_registry"

    def test_commit_v2_rejects_invalid_context(self, manager: ArtifactManager) -> None:
        """Commit V2 pipeline rejects empty context with ValidationError."""
        with pytest.raises(ValidationError):
            _run_v2_tracking(manager, "commit", {})


# ---------------------------------------------------------------------------
# PR (3 tests)
# ---------------------------------------------------------------------------


class TestPRV2Parity:
    """V2 parity tests for pr tracking artifact."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        return _make_manager(tmp_path)

    _MINIMAL = {
        "title": "Cycle 7: Add V2 schemas for tracking artifacts",
        "changes": "Added CommitContext, PRContext, IssueContext schemas",
    }

    def test_pr_context_validates_minimal(self) -> None:
        """PRContext schema accepts minimal required fields."""
        from mcp_server.schemas import PRContext  # noqa: PLC0415

        ctx = PRContext(**self._MINIMAL)
        assert ctx.title == self._MINIMAL["title"]
        assert ctx.changes == self._MINIMAL["changes"]

    def test_pr_v2_routing_confirmed(self, manager: ArtifactManager) -> None:
        """PR V2 pipeline routes via _enrich_context_v2 (not V1 fallback)."""
        calls = _spy_v2_routed(manager)
        _run_v2_tracking(manager, "pr", self._MINIMAL)
        assert len(calls) == 1, "V2 routing not active for pr — not in _v2_context_registry"

    def test_pr_v2_rejects_invalid_context(self, manager: ArtifactManager) -> None:
        """PR V2 pipeline rejects empty context with ValidationError."""
        with pytest.raises(ValidationError):
            _run_v2_tracking(manager, "pr", {})


# ---------------------------------------------------------------------------
# Issue (3 tests)
# ---------------------------------------------------------------------------


class TestIssueV2Parity:
    """V2 parity tests for issue tracking artifact."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        return _make_manager(tmp_path)

    _MINIMAL = {
        "title": "Add V2 schemas for tracking artifacts",
        "problem": "Tracking artifact types commit/pr/issue lack Pydantic V2 schemas",
    }

    def test_issue_context_validates_minimal(self) -> None:
        """IssueContext schema accepts minimal required fields."""
        from mcp_server.schemas import IssueContext  # noqa: PLC0415

        ctx = IssueContext(**self._MINIMAL)
        assert ctx.title == self._MINIMAL["title"]
        assert ctx.problem == self._MINIMAL["problem"]

    def test_issue_v2_routing_confirmed(self, manager: ArtifactManager) -> None:
        """Issue V2 pipeline routes via _enrich_context_v2 (not V1 fallback)."""
        calls = _spy_v2_routed(manager)
        _run_v2_tracking(manager, "issue", self._MINIMAL)
        assert len(calls) == 1, "V2 routing not active for issue — not in _v2_context_registry"

    def test_issue_v2_rejects_invalid_context(self, manager: ArtifactManager) -> None:
        """Issue V2 pipeline rejects empty context with ValidationError."""
        with pytest.raises(ValidationError):
            _run_v2_tracking(manager, "issue", {})
