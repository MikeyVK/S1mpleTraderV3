# tests/unit/dtos/strategy/test_aggregated_context_assessment.py
"""
Unit tests for AggregatedContextAssessment DTO.

Tests the aggregated SWOT assessment that combines multiple ContextFactors
into strengths and weaknesses quadrants for opportunity/threat detection.

@layer: Tests (Unit)
@dependencies: [pytest, backend.dtos.strategy.aggregated_context_assessment]
"""

# Standard Library Imports
from datetime import datetime, timezone
from typing import Any, Dict

# Third-Party Imports
import pytest

# Our Application Imports
from backend.dtos.strategy.aggregated_context_assessment import AggregatedContextAssessment
from backend.dtos.strategy.context_factor import ContextFactor
from backend.core.enums import ContextType
from backend.core.context_factors import BaseFactorType


class TestAggregatedContextAssessmentCreation:
    """Test suite for AggregatedContextAssessment instantiation."""

    def test_create_minimal_assessment_with_strengths_only(self):
        """Test creating assessment with only strengths (no weaknesses)."""
        strength = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        assessment = AggregatedContextAssessment(
            timestamp=datetime.now(timezone.utc),
            strengths=[strength],
            weaknesses=[]
        )

        # Verify auto-generated ID format
        assessment_id = str(assessment.assessment_id)
        assert assessment_id.startswith("ASS_")
        assert len(assessment.strengths) == 1
        assert len(assessment.weaknesses) == 0
        assert assessment.metadata is None

    def test_create_minimal_assessment_with_weaknesses_only(self):
        """Test creating assessment with only weaknesses (no strengths)."""
        weakness = ContextFactor(
            factor_type=BaseFactorType.VOLATILE_REGIME.value,
            strength=None,
            weakness=0.60,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        assessment = AggregatedContextAssessment(
            timestamp=datetime.now(timezone.utc),
            strengths=[],
            weaknesses=[weakness]
        )

        assessment_id = str(assessment.assessment_id)
        assert assessment_id.startswith("ASS_")
        assert len(assessment.strengths) == 0
        assert len(assessment.weaknesses) == 1

    def test_create_balanced_assessment(self):
        """Test creating assessment with both strengths and weaknesses."""
        strength = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        weakness = ContextFactor(
            factor_type=BaseFactorType.LOW_LIQUIDITY.value,
            strength=None,
            weakness=0.60,
            source_plugin="test_plugin",
            source_context_type=ContextType.MICROSTRUCTURE_ANALYSIS.value
        )

        assessment = AggregatedContextAssessment(
            timestamp=datetime.now(timezone.utc),
            strengths=[strength],
            weaknesses=[weakness]
        )

        assert len(assessment.strengths) == 1
        assert len(assessment.weaknesses) == 1


class TestAggregatedContextAssessmentValidation:
    """Test suite for validation logic."""

    def test_both_lists_empty_allowed(self):
        """Test that both empty lists are currently allowed (edge case)."""
        # NOTE: This might be changed to reject empty assessments in future
        assessment = AggregatedContextAssessment(
            timestamp=datetime.now(timezone.utc),
            strengths=[],
            weaknesses=[]
        )

        assert len(assessment.strengths) == 0
        assert len(assessment.weaknesses) == 0

    def test_multiple_strengths(self):
        """Test assessment with multiple strength factors."""
        strength1 = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="plugin_a",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        strength2 = ContextFactor(
            factor_type=BaseFactorType.MOMENTUM_ALIGNMENT.value,
            strength=0.80,
            weakness=None,
            source_plugin="plugin_b",
            source_context_type=ContextType.INDICATOR_CALCULATION.value
        )

        assessment = AggregatedContextAssessment(
            timestamp=datetime.now(timezone.utc),
            strengths=[strength1, strength2],
            weaknesses=[]
        )

        assert len(assessment.strengths) == 2
        assert assessment.strengths[0].factor_type == "TRENDING_REGIME"
        assert assessment.strengths[1].factor_type == "MOMENTUM_ALIGNMENT"

    def test_multiple_weaknesses(self):
        """Test assessment with multiple weakness factors."""
        weakness1 = ContextFactor(
            factor_type=BaseFactorType.VOLATILE_REGIME.value,
            strength=None,
            weakness=0.60,
            source_plugin="plugin_a",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        weakness2 = ContextFactor(
            factor_type=BaseFactorType.LOW_LIQUIDITY.value,
            strength=None,
            weakness=0.55,
            source_plugin="plugin_b",
            source_context_type=ContextType.MICROSTRUCTURE_ANALYSIS.value
        )

        assessment = AggregatedContextAssessment(
            timestamp=datetime.now(timezone.utc),
            strengths=[],
            weaknesses=[weakness1, weakness2]
        )

        assert len(assessment.weaknesses) == 2


class TestAggregatedContextAssessmentTimestampValidation:
    """Test suite for timestamp validation."""

    def test_timezone_aware_timestamp_accepted(self):
        """Test that timezone-aware timestamps are accepted."""
        strength = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        aware_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assessment = AggregatedContextAssessment(
            timestamp=aware_dt,
            strengths=[strength],
            weaknesses=[]
        )

        # Verify timestamp properties (cast to avoid Pylance FieldInfo warning)
        assert assessment.timestamp == aware_dt
        assert aware_dt.tzinfo == timezone.utc
        assert aware_dt.year == 2025

    def test_naive_timestamp_rejected(self):
        """Test that naive (non-timezone-aware) timestamps are rejected."""
        strength = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        naive_dt = datetime(2025, 1, 15, 10, 30, 0)  # No timezone

        with pytest.raises(ValueError) as exc_info:
            AggregatedContextAssessment(
                timestamp=naive_dt,
                strengths=[strength],
                weaknesses=[]
            )

        assert "timezone-aware" in str(exc_info.value).lower()


class TestAggregatedContextAssessmentIDGeneration:
    """Test suite for assessment_id generation."""

    def test_assessment_id_auto_generated(self):
        """Test that assessment_id is automatically generated with ASS_ prefix."""
        strength = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        assessment = AggregatedContextAssessment(
            timestamp=datetime.now(timezone.utc),
            strengths=[strength],
            weaknesses=[]
        )

        assessment_id = str(assessment.assessment_id)
        assert assessment_id.startswith("ASS_")
        # ID format: ASS_<UUID>
        assert len(assessment_id) > 4

    def test_assessment_id_uniqueness(self):
        """Test that each assessment gets unique ID."""
        strength = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        assessment1 = AggregatedContextAssessment(
            timestamp=datetime.now(timezone.utc),
            strengths=[strength],
            weaknesses=[]
        )

        assessment2 = AggregatedContextAssessment(
            timestamp=datetime.now(timezone.utc),
            strengths=[strength],
            weaknesses=[]
        )

        assert assessment1.assessment_id != assessment2.assessment_id


class TestAggregatedContextAssessmentImmutability:
    """Test suite for immutability constraints."""

    def test_assessment_is_frozen(self):
        """Test that AggregatedContextAssessment is immutable after creation."""
        strength = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        assessment = AggregatedContextAssessment(
            timestamp=datetime.now(timezone.utc),
            strengths=[strength],
            weaknesses=[]
        )

        with pytest.raises(ValueError):
            assessment.strengths = []  # type: ignore

    def test_no_extra_fields_allowed(self):
        """Test that extra fields are forbidden."""
        strength = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        with pytest.raises(ValueError) as exc_info:
            AggregatedContextAssessment(
                timestamp=datetime.now(timezone.utc),
                strengths=[strength],
                weaknesses=[],
                extra_field="not_allowed"  # type: ignore
            )

        assert "extra_field" in str(exc_info.value).lower()


class TestAggregatedContextAssessmentMetadata:
    """Test suite for optional metadata field."""

    def test_metadata_optional(self):
        """Test that metadata field is optional."""
        strength = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        assessment = AggregatedContextAssessment(
            timestamp=datetime.now(timezone.utc),
            strengths=[strength],
            weaknesses=[]
        )

        assert assessment.metadata is None

    def test_metadata_with_dict(self):
        """Test that metadata accepts dictionary values."""
        strength = ContextFactor(
            factor_type=BaseFactorType.TRENDING_REGIME.value,
            strength=0.75,
            weakness=None,
            source_plugin="test_plugin",
            source_context_type=ContextType.REGIME_CLASSIFICATION.value
        )

        metadata: Dict[str, Any] = {
            "total_workers": 5,
            "aggregation_method": "weighted_avg",
            "confidence": 0.85
        }

        assessment = AggregatedContextAssessment(
            timestamp=datetime.now(timezone.utc),
            strengths=[strength],
            weaknesses=[],
            metadata=metadata
        )

        assert assessment.metadata == metadata
        assert assessment.metadata["total_workers"] == 5  # type: ignore[index]
