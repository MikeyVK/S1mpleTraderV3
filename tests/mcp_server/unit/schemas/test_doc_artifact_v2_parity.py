# tests/unit/mcp_server/schemas/test_doc_artifact_v2_parity.py
# SCAFFOLD: test:manual | 2026-02-18T00:00:00Z | tests/unit/mcp_server/schemas/test_doc_artifact_v2_parity.py  # noqa: E501
"""V2 parity tests for document artifact types (Issue #135 Cycle 6).

SCOPE (Cycle 6 - Doc Artifact V2):
  research, planning, design, architecture, reference

3 tests per artifact type (15 total):
  1. context_validates_minimal  - schema creates with required fields only; fails if schema absent
  2. v2_routing_confirmed       - _enrich_context_v2 IS called; fails while not in registry
  3. v2_rejects_invalid_context - empty context raises ValidationError;
     fails while V1 fallback active

Note on parity definition (aligned with Cycle 5 docstring):
  Parity = smoke: both pipelines produce valid markdown with metadata header.
  True output-equivalence deferred to Cycle 6 template simplification.
"""

import asyncio  # noqa: I001
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from mcp_server.core.exceptions import ValidationError
from mcp_server.managers.artifact_manager import ArtifactManager


# ---------------------------------------------------------------------------
# Shared helpers (identical pattern to test_code_artifact_v2_parity.py)
# ---------------------------------------------------------------------------


def _make_manager(tmp_path: Path) -> ArtifactManager:
    return ArtifactManager(workspace_root=str(tmp_path))


def _run_v2(manager: ArtifactManager, artifact_type: str, context: dict) -> str:
    """Run V2 pipeline (PYDANTIC_SCAFFOLDING_ENABLED=true), return rendered content."""
    output_captured: list[str] = []

    async def mock_validate(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202, ARG001
        return (True, "")

    manager.validation_service.validate = mock_validate
    manager.fs_adapter.write_file = Mock(
        side_effect=lambda p, c: output_captured.append(c)  # noqa: ARG005
    )

    os.environ["PYDANTIC_SCAFFOLDING_ENABLED"] = "true"
    try:
        asyncio.run(
            manager.scaffold_artifact(
                artifact_type, output_path="test_scaffold_output.py", **context
            )
        )
    finally:
        os.environ.pop("PYDANTIC_SCAFFOLDING_ENABLED", None)

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


def _assert_has_metadata_header(output: str, label: str) -> None:
    """Assert output has a SCAFFOLD or template= metadata header."""
    has_scaffold = "# SCAFFOLD:" in output[:300]
    has_template = "# template=" in output[:300]
    assert has_scaffold or has_template, (
        f"{label} output missing metadata header (SCAFFOLD or template=)"
    )


# ---------------------------------------------------------------------------
# Research (3 tests)
# ---------------------------------------------------------------------------


class TestResearchV2Parity:
    """V2 parity tests for research document artifact."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        return _make_manager(tmp_path)

    _MINIMAL = {
        "title": "V2 Research: Template Introspection",
        "problem_statement": "Investigate template introspection limitations",
        "goals": ["Understand block override impact", "Map required vs optional fields"],
    }

    def test_research_context_validates_minimal(self) -> None:
        """ResearchContext schema accepts minimal required fields."""
        from mcp_server.schemas import ResearchContext  # noqa: PLC0415

        ctx = ResearchContext(**self._MINIMAL)
        assert ctx.title == self._MINIMAL["title"]

    def test_research_v2_routing_confirmed(self, manager: ArtifactManager) -> None:
        """Research V2 pipeline routes via _enrich_context_v2 (not V1 fallback)."""
        calls = _spy_v2_routed(manager)
        _run_v2(manager, "research", self._MINIMAL)
        assert len(calls) == 1, "V2 routing not active for research — not in _v2_context_registry"

    def test_research_v2_rejects_invalid_context(self, manager: ArtifactManager) -> None:
        """Research V2 pipeline rejects empty context with ValidationError."""
        with pytest.raises(ValidationError):
            _run_v2(manager, "research", {})


# ---------------------------------------------------------------------------
# Planning (3 tests)
# ---------------------------------------------------------------------------


class TestPlanningV2Parity:
    """V2 parity tests for planning document artifact."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        return _make_manager(tmp_path)

    _MINIMAL = {
        "title": "V2 Planning: Cycle 6 Doc Schemas",
        "summary": "Implement Pydantic context schemas for 5 doc artifact types",
        "tdd_cycles": [
            "Cycle 6: RED — 15 failing tests",
            "Cycle 6: GREEN — 5 context + 5 render context schemas",
        ],
    }

    def test_planning_context_validates_minimal(self) -> None:
        """PlanningContext schema accepts minimal required fields."""
        from mcp_server.schemas import PlanningContext  # noqa: PLC0415

        ctx = PlanningContext(**self._MINIMAL)
        assert ctx.title == self._MINIMAL["title"]

    def test_planning_v2_routing_confirmed(self, manager: ArtifactManager) -> None:
        """Planning V2 pipeline routes via _enrich_context_v2 (not V1 fallback)."""
        calls = _spy_v2_routed(manager)
        _run_v2(manager, "planning", self._MINIMAL)
        assert len(calls) == 1, "V2 routing not active for planning — not in _v2_context_registry"

    def test_planning_v2_rejects_invalid_context(self, manager: ArtifactManager) -> None:
        """Planning V2 pipeline rejects empty context with ValidationError."""
        with pytest.raises(ValidationError):
            _run_v2(manager, "planning", {})


# ---------------------------------------------------------------------------
# Design (3 tests)
# ---------------------------------------------------------------------------


class TestDesignV2Parity:
    """V2 parity tests for design document artifact."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        return _make_manager(tmp_path)

    _MINIMAL = {
        "title": "V2 Design: Document Context Schemas",
        "status": "DRAFT",
        "version": "1.0",
        "problem_statement": "No Pydantic schemas exist for document artifact types",
        "requirements_functional": [
            "Schema validates required fields",
            "RenderContext adds lifecycle",
        ],
        "requirements_nonfunctional": ["Consistent with existing BaseContext pattern"],
        "decision": "Implement XxxContext + XxxRenderContext for each doc type",
        "rationale": "Uniform V2 pipeline coverage for all concrete templates",
    }

    def test_design_context_validates_minimal(self) -> None:
        """DesignContext schema accepts minimal required fields."""
        from mcp_server.schemas import DesignContext  # noqa: PLC0415

        ctx = DesignContext(**self._MINIMAL)
        assert ctx.title == self._MINIMAL["title"]

    def test_design_v2_routing_confirmed(self, manager: ArtifactManager) -> None:
        """Design V2 pipeline routes via _enrich_context_v2 (not V1 fallback)."""
        calls = _spy_v2_routed(manager)
        _run_v2(manager, "design", self._MINIMAL)
        assert len(calls) == 1, "V2 routing not active for design — not in _v2_context_registry"

    def test_design_v2_rejects_invalid_context(self, manager: ArtifactManager) -> None:
        """Design V2 pipeline rejects empty context with ValidationError."""
        with pytest.raises(ValidationError):
            _run_v2(manager, "design", {})


# ---------------------------------------------------------------------------
# Architecture (3 tests)
# ---------------------------------------------------------------------------


class TestArchitectureV2Parity:
    """V2 parity tests for architecture document artifact."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        return _make_manager(tmp_path)

    _MINIMAL = {
        "title": "V2 Architecture: Schema Infrastructure",
        "concepts": [
            "BaseContext: user-facing artifact fields",
            "BaseRenderContext: lifecycle-enriched for template rendering",
        ],
    }

    def test_architecture_context_validates_minimal(self) -> None:
        """ArchitectureContext schema accepts minimal required fields."""
        from mcp_server.schemas import ArchitectureContext  # noqa: PLC0415

        ctx = ArchitectureContext(**self._MINIMAL)
        assert ctx.title == self._MINIMAL["title"]

    def test_architecture_v2_routing_confirmed(self, manager: ArtifactManager) -> None:
        """Architecture V2 pipeline routes via _enrich_context_v2 (not V1 fallback)."""
        calls = _spy_v2_routed(manager)
        _run_v2(manager, "architecture", self._MINIMAL)
        assert len(calls) == 1, (
            "V2 routing not active for architecture — not in _v2_context_registry"
        )

    def test_architecture_v2_rejects_invalid_context(self, manager: ArtifactManager) -> None:
        """Architecture V2 pipeline rejects empty context with ValidationError."""
        with pytest.raises(ValidationError):
            _run_v2(manager, "architecture", {})


# ---------------------------------------------------------------------------
# Reference (3 tests)
# ---------------------------------------------------------------------------


class TestReferenceV2Parity:
    """V2 parity tests for reference document artifact."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        return _make_manager(tmp_path)

    _MINIMAL = {
        "title": "V2 Reference: ResearchContext",
        "source_file": "mcp_server/schemas/contexts/research.py",
        "test_file": "tests/unit/mcp_server/schemas/test_doc_artifact_v2_parity.py",
        "api_reference": [
            {"name": "ResearchContext", "description": "Context schema for research artifacts"},
        ],
    }

    def test_reference_context_validates_minimal(self) -> None:
        """ReferenceContext schema accepts minimal required fields."""
        from mcp_server.schemas import ReferenceContext  # noqa: PLC0415

        ctx = ReferenceContext(**self._MINIMAL)
        assert ctx.title == self._MINIMAL["title"]

    def test_reference_v2_routing_confirmed(self, manager: ArtifactManager) -> None:
        """Reference V2 pipeline routes via _enrich_context_v2 (not V1 fallback)."""
        calls = _spy_v2_routed(manager)
        _run_v2(manager, "reference", self._MINIMAL)
        assert len(calls) == 1, "V2 routing not active for reference — not in _v2_context_registry"

    def test_reference_v2_rejects_invalid_context(self, manager: ArtifactManager) -> None:
        """Reference V2 pipeline rejects empty context with ValidationError."""
        with pytest.raises(ValidationError):
            _run_v2(manager, "reference", {})
