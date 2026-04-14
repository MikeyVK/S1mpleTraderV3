"""Tests for ScopeEncoder - Commit scope generation with strict validation.

Tests scope encoding for git commits in format:
- Phase only: P_RESEARCH
- Phase + subphase: P_IMPLEMENTATION_SP_RED
- Phase + cycle + subphase: P_IMPLEMENTATION_SP_C1_RED

Validation:
- Phase must exist in workphases.yaml
- sub_phase must be in workphases.yaml[phase].subphases (STRICT)
- Empty subphases list = no subphases allowed

@layer: Tests (Unit)
@dependencies: pytest, mcp_server.core.scope_encoder
"""

from pathlib import Path

import pytest

from mcp_server.config.schemas.workphases import PhaseDefinition, WorkphasesConfig
from mcp_server.core.scope_encoder import ScopeEncoder

_TEST_WORKPHASES = WorkphasesConfig.model_validate(
    {
        "phases": {
            "research": {"commit_type_hint": "docs", "subphases": []},
            "planning": {"commit_type_hint": "docs", "subphases": ["c1", "c2", "c3"]},
            "design": {
                "commit_type_hint": "docs",
                "subphases": ["contracts", "flows", "schemas"],
            },
            "implementation": {
                "commit_type_hint": "test",
                "subphases": ["red", "green", "refactor"],
            },
            "integration": {
                "commit_type_hint": "test",
                "subphases": ["e2e", "acceptance"],
            },
            "documentation": {
                "commit_type_hint": "docs",
                "subphases": ["reference", "guides", "agent"],
            },
            "coordination": {
                "commit_type_hint": "chore",
                "subphases": ["delegation", "sync", "review"],
            },
            "ready": {"terminal": True},
        }
    }
)


@pytest.fixture
def workphases_cfg() -> WorkphasesConfig:
    """Return test WorkphasesConfig with all standard phases."""
    return _TEST_WORKPHASES


class TestScopeEncoderBasicGeneration:
    """Test basic scope generation without validation errors."""

    def test_phase_only_scope(self, workphases_cfg: WorkphasesConfig) -> None:
        """Generate scope for phase without subphase."""
        encoder = ScopeEncoder(workphases_cfg)
        scope = encoder.generate_scope(phase="research")
        assert scope == "P_RESEARCH"

    def test_phase_with_subphase(self, workphases_cfg: WorkphasesConfig) -> None:
        """Generate scope for phase with subphase."""
        encoder = ScopeEncoder(workphases_cfg)
        scope = encoder.generate_scope(phase="implementation", sub_phase="red")
        assert scope == "P_IMPLEMENTATION_SP_RED"

    def test_phase_with_cycle_and_subphase(self, workphases_cfg: WorkphasesConfig) -> None:
        """Generate scope with cycle number in TDD format."""
        encoder = ScopeEncoder(workphases_cfg)
        scope = encoder.generate_scope(phase="implementation", sub_phase="red", cycle_number=1)
        assert scope == "P_IMPLEMENTATION_SP_C1_RED"

    def test_all_tdd_subphases_valid(self, workphases_cfg: WorkphasesConfig) -> None:
        """All configured TDD subphases should generate valid scopes."""
        encoder = ScopeEncoder(workphases_cfg)
        assert encoder.generate_scope("implementation", "red") == "P_IMPLEMENTATION_SP_RED"
        assert encoder.generate_scope("implementation", "green") == "P_IMPLEMENTATION_SP_GREEN"
        assert (
            encoder.generate_scope("implementation", "refactor") == "P_IMPLEMENTATION_SP_REFACTOR"
        )

    def test_coordination_phase_valid(self, workphases_cfg: WorkphasesConfig) -> None:
        """Coordination phase (NEW) should generate valid scope."""
        encoder = ScopeEncoder(workphases_cfg)
        scope = encoder.generate_scope(phase="coordination", sub_phase="delegation")
        assert scope == "P_COORDINATION_SP_DELEGATION"


class TestScopeEncoderValidation:
    """Test strict validation of phases and subphases."""

    def test_invalid_phase_raises_error(self, workphases_cfg: WorkphasesConfig) -> None:
        """Unknown phase should raise ValueError with actionable message."""
        encoder = ScopeEncoder(workphases_cfg)

        with pytest.raises(ValueError) as exc_info:
            encoder.generate_scope(phase="invalid_phase")

        error_msg = str(exc_info.value)
        assert "Unknown workflow phase: 'invalid_phase'" in error_msg
        assert "Valid phases:" in error_msg
        assert "research" in error_msg
        assert "implementation" in error_msg
        assert "coordination" in error_msg
        assert "Example:" in error_msg
        assert "Recovery:" in error_msg

    def test_invalid_subphase_raises_error(self, workphases_cfg: WorkphasesConfig) -> None:
        """Invalid subphase should raise ValueError with actionable message."""
        encoder = ScopeEncoder(workphases_cfg)

        with pytest.raises(ValueError) as exc_info:
            encoder.generate_scope(phase="implementation", sub_phase="invalid")

        error_msg = str(exc_info.value)
        assert "Invalid sub_phase 'invalid' for workflow phase 'implementation'" in error_msg
        assert "Valid subphases for implementation:" in error_msg
        assert "red" in error_msg
        assert "green" in error_msg
        assert "refactor" in error_msg
        assert "Example:" in error_msg
        assert "Recovery:" in error_msg

    def test_subphase_on_phase_without_subphases_raises_error(
        self, workphases_cfg: WorkphasesConfig
    ) -> None:
        """Providing subphase for phase with empty subphases list should error."""
        encoder = ScopeEncoder(workphases_cfg)

        with pytest.raises(ValueError) as exc_info:
            encoder.generate_scope(phase="research", sub_phase="some_subphase")

        error_msg = str(exc_info.value)
        assert "Invalid sub_phase 'some_subphase' for workflow phase 'research'" in error_msg
        assert (
            "research does not support subphases" in error_msg
            or "Valid subphases for research: []" in error_msg
        )

    def test_missing_subphase_when_optional_is_ok(self, workphases_cfg: WorkphasesConfig) -> None:
        """Not providing subphase when subphases exist should be OK (optional)."""
        encoder = ScopeEncoder(workphases_cfg)
        scope = encoder.generate_scope(phase="implementation")  # No sub_phase
        assert scope == "P_IMPLEMENTATION"  # Phase-level commit OK


class TestScopeEncoderEdgeCases:
    """Test edge cases and error handling."""

    def test_scope_encoder_has_no_file_io(self, tmp_path: Path) -> None:
        """ScopeEncoder works without any file on disk (C5: config in memory)."""
        encoder = ScopeEncoder(_TEST_WORKPHASES)
        # No files created in tmp_path — encoder works purely from injected config
        scope = encoder.generate_scope(phase="research")
        assert scope == "P_RESEARCH"

    def test_case_insensitive_phase_names(self, workphases_cfg: WorkphasesConfig) -> None:
        """Phase names should be case-insensitive (normalized to uppercase in scope)."""
        encoder = ScopeEncoder(workphases_cfg)
        scope1 = encoder.generate_scope(phase="implementation")
        scope2 = encoder.generate_scope(phase="IMPLEMENTATION")
        scope3 = encoder.generate_scope(phase="Implementation")
        assert scope1 == scope2 == scope3 == "P_IMPLEMENTATION"

    def test_cycle_number_without_subphase_ignored(self, workphases_cfg: WorkphasesConfig) -> None:
        """Cycle number without subphase should be ignored (only for TDD subphases)."""
        encoder = ScopeEncoder(workphases_cfg)
        scope = encoder.generate_scope(phase="implementation", cycle_number=1)
        assert scope == "P_IMPLEMENTATION"  # Cycle ignored without sub_phase
