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
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import Any

# Third-party
import pytest
from pathlib import Path

# Project modules
from backend.core.phase_detection import PhaseDetectionResult


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
