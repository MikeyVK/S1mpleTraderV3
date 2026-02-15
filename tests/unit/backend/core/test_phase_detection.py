# tests/unit/backend/core/test_phase_detection.py
# template=unit_test version=6b0f1f7e created=2026-02-15T06:35Z updated=
"""
Unit tests for backend.core.phase_detection.

Test PhaseDetectionResult TypedDict schema validation and field types

@layer: Tests (Unit)
@dependencies: [pytest, backend.core.phase_detection, unittest.mock]
@responsibilities:
    - Test PhaseDetectionResult TypedDict schema
    - Verify ScopeDecoder.detect_phase() deterministic precedence
    - Cover error handling scenarios (graceful degradation)
"""

# Standard library
import json
from pathlib import Path

# Third-party
# Project modules
from backend.core.phase_detection import PhaseDetectionResult, ScopeDecoder


class TestPhaseDetectionResult:
    """Test suite for PhaseDetectionResult TypedDict schema."""

    def test_phase_detection_result_schema(self):
        """Verify PhaseDetectionResult has all 6 required fields with correct types."""
        # Arrange - Create instance using TypedDict syntax
        result: PhaseDetectionResult = {
            "workflow_phase": "tdd",
            "sub_phase": "red",
            "source": "commit-scope",
            "confidence": "high",
            "raw_scope": "P_TDD_SP_RED",
            "error_message": None,
        }

        # Assert - Verify all required fields present and correct
        assert result["workflow_phase"] == "tdd"
        assert result["sub_phase"] == "red"
        assert result["source"] == "commit-scope"
        assert result["confidence"] == "high"
        assert result["raw_scope"] == "P_TDD_SP_RED"
        assert result["error_message"] is None


class TestScopeDecoder:
    """Test suite for ScopeDecoder deterministic phase detection."""

    def test_parse_commit_scope_phase_only(self):
        """Parse commit scope with P_PHASE format (no subphase)."""
        # Arrange
        decoder = ScopeDecoder()
        commit_message = "docs(P_RESEARCH): complete problem analysis"

        # Act
        result = decoder.detect_phase(commit_message, fallback_to_state=False)

        # Assert
        assert result["workflow_phase"] == "research"
        assert result["sub_phase"] is None
        assert result["source"] == "commit-scope"
        assert result["confidence"] == "high"
        assert result["raw_scope"] == "P_RESEARCH"
        assert result["error_message"] is None

    def test_parse_commit_scope_phase_and_subphase(self):
        """Parse commit scope with P_PHASE_SP_SUBPHASE format."""
        # Arrange
        decoder = ScopeDecoder()
        commit_message = "test(P_TDD_SP_RED): add user validation tests"

        # Act
        result = decoder.detect_phase(commit_message, fallback_to_state=False)

        # Assert
        assert result["workflow_phase"] == "tdd"
        assert result["sub_phase"] == "red"
        assert result["source"] == "commit-scope"
        assert result["confidence"] == "high"
        assert result["raw_scope"] == "P_TDD_SP_RED"
        assert result["error_message"] is None

    def test_fallback_to_state_json_when_commit_scope_missing(self, tmp_path):
        """Fallback to state.json when commit message has no valid scope (medium confidence)."""
        # Arrange
        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps({"current_phase": "integration", "workflow_name": "feature"})
        )
        decoder = ScopeDecoder(state_path=state_file)
        commit_message = "docs: update README"  # No scope

        # Act
        result = decoder.detect_phase(commit_message, fallback_to_state=True)

        # Assert - state.json fallback with medium confidence
        assert result["workflow_phase"] == "integration"
        assert result["sub_phase"] is None
        assert result["source"] == "state.json"
        assert result["confidence"] == "medium"
        assert result["raw_scope"] is None
        assert result["error_message"] is None

    def test_fallback_to_state_json_on_invalid_scope_format(self, tmp_path):
        """Fallback to state.json when commit scope format is invalid."""
        # Arrange
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"current_phase": "planning", "workflow_name": "bug"}))
        decoder = ScopeDecoder(state_path=state_file)
        commit_message = "feat(INVALID_SCOPE): implement feature"  # Invalid format

        # Act
        result = decoder.detect_phase(commit_message, fallback_to_state=True)

        # Assert
        assert result["workflow_phase"] == "planning"
        assert result["source"] == "state.json"
        assert result["confidence"] == "medium"

    def test_unknown_fallback_when_all_sources_fail(self):
        """Return unknown with actionable error when commit-scope and state.json both fail."""
        # Arrange
        decoder = ScopeDecoder(state_path=Path("/nonexistent/state.json"))
        commit_message = "docs: no scope here"

        # Act
        result = decoder.detect_phase(commit_message, fallback_to_state=True)

        # Assert - unknown fallback
        assert result["workflow_phase"] == "unknown"
        assert result["sub_phase"] is None
        assert result["source"] == "unknown"
        assert result["confidence"] == "unknown"
        assert result["raw_scope"] is None
        assert result["error_message"] is not None

    def test_unknown_error_message_contains_recovery_steps(self):
        """Verify unknown fallback includes actionable recovery instructions."""
        # Arrange
        decoder = ScopeDecoder()
        commit_message = None  # No commit message

        # Act
        result = decoder.detect_phase(commit_message, fallback_to_state=False)

        # Assert - error message has recovery steps
        assert "Phase detection failed" in result["error_message"]
        assert "transition_phase" in result["error_message"]
        assert "type(P_PHASE): message" in result["error_message"]
        assert "research, planning, design, tdd" in result["error_message"]

    def test_graceful_degradation_old_commit_format(self, tmp_path):
        """Old commits without scope gracefully fallback without errors."""
        # Arrange
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"current_phase": "tdd", "workflow_name": "feature"}))
        decoder = ScopeDecoder(state_path=state_file)
        old_commit = "feat: implement user service"  # Legacy format

        # Act
        result = decoder.detect_phase(old_commit, fallback_to_state=True)

        # Assert - graceful fallback to state.json
        assert result["workflow_phase"] == "tdd"
        assert result["source"] == "state.json"
        assert result["confidence"] == "medium"
        # No exception raised - graceful degradation
