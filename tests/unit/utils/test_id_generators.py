# tests/unit/utils/test_id_generators.py
"""
Unit tests for typed ID generation utilities.

Tests the standardized ID generation with type prefixes for causal
traceability across the trading system.

@layer: Tests (Unit)
@dependencies: [pytest, backend.utils.id_generators]
"""

# Standard Library Imports
import re

# Third-Party Imports
import pytest

# Our Application Imports
from backend.utils.id_generators import (
    generate_tick_id,
    generate_schedule_id,
    generate_news_id,
    generate_manual_id,
    generate_opportunity_id,
    generate_threat_id,
    generate_assessment_id,
    generate_trade_id,
    extract_id_type,
)


class TestFlowInitiatorIDGeneration:
    """Test suite for flow initiator ID generators."""

    def test_generate_tick_id_has_correct_prefix(self):
        """Test that tick IDs start with TCK_ prefix."""
        tick_id = generate_tick_id()
        assert tick_id.startswith("TCK_")

    def test_generate_tick_id_has_valid_uuid(self):
        """Test that tick IDs contain valid UUID format."""
        tick_id = generate_tick_id()
        # Format: TCK_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        pattern = (
            r'^TCK_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
            r'[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert re.match(pattern, tick_id)

    def test_generate_tick_id_is_unique(self):
        """Test that consecutive tick IDs are unique."""
        id1 = generate_tick_id()
        id2 = generate_tick_id()
        assert id1 != id2

    def test_generate_schedule_id_has_correct_prefix(self):
        """Test that schedule IDs start with SCH_ prefix."""
        schedule_id = generate_schedule_id()
        assert schedule_id.startswith("SCH_")

    def test_generate_schedule_id_has_valid_uuid(self):
        """Test that schedule IDs contain valid UUID format."""
        schedule_id = generate_schedule_id()
        pattern = (
            r'^SCH_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
            r'[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert re.match(pattern, schedule_id)

    def test_generate_news_id_has_correct_prefix(self):
        """Test that news IDs start with NWS_ prefix."""
        news_id = generate_news_id()
        assert news_id.startswith("NWS_")

    def test_generate_news_id_has_valid_uuid(self):
        """Test that news IDs contain valid UUID format."""
        news_id = generate_news_id()
        pattern = (
            r'^NWS_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
            r'[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert re.match(pattern, news_id)

    def test_generate_manual_id_has_correct_prefix(self):
        """Test that manual IDs start with MAN_ prefix."""
        manual_id = generate_manual_id()
        assert manual_id.startswith("MAN_")

    def test_generate_manual_id_has_valid_uuid(self):
        """Test that manual IDs contain valid UUID format."""
        manual_id = generate_manual_id()
        pattern = (
            r'^MAN_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
            r'[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert re.match(pattern, manual_id)


class TestCausalChainIDGeneration:
    """Test suite for causal chain ID generators."""

    def test_generate_opportunity_id_has_correct_prefix(self):
        """Test that opportunity IDs start with OPP_ prefix."""
        opp_id = generate_opportunity_id()
        assert opp_id.startswith("OPP_")

    def test_generate_opportunity_id_has_valid_uuid(self):
        """Test that opportunity IDs contain valid UUID format."""
        opp_id = generate_opportunity_id()
        pattern = (
            r'^OPP_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
            r'[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert re.match(pattern, opp_id)

    def test_generate_opportunity_id_is_unique(self):
        """Test that consecutive opportunity IDs are unique."""
        id1 = generate_opportunity_id()
        id2 = generate_opportunity_id()
        assert id1 != id2

    def test_generate_threat_id_has_correct_prefix(self):
        """Test that threat IDs start with THR_ prefix."""
        threat_id = generate_threat_id()
        assert threat_id.startswith("THR_")

    def test_generate_threat_id_has_valid_uuid(self):
        """Test that threat IDs contain valid UUID format."""
        threat_id = generate_threat_id()
        pattern = (
            r'^THR_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
            r'[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert re.match(pattern, threat_id)

    def test_generate_threat_id_is_unique(self):
        """Test that consecutive threat IDs are unique."""
        id1 = generate_threat_id()
        id2 = generate_threat_id()
        assert id1 != id2

    def test_generate_assessment_id_has_correct_prefix(self):
        """Test that assessment IDs start with ASS_ prefix."""
        assessment_id = generate_assessment_id()
        assert assessment_id.startswith("ASS_")

    def test_generate_assessment_id_has_valid_uuid(self):
        """Test that assessment IDs contain valid UUID format."""
        assessment_id = generate_assessment_id()
        pattern = (
            r'^ASS_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
            r'[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert re.match(pattern, assessment_id)

    def test_generate_assessment_id_is_unique(self):
        """Test that consecutive assessment IDs are unique."""
        id1 = generate_assessment_id()
        id2 = generate_assessment_id()
        assert id1 != id2

    def test_generate_trade_id_has_correct_prefix(self):
        """Test that trade IDs start with TRD_ prefix."""
        trade_id = generate_trade_id()
        assert trade_id.startswith("TRD_")

    def test_generate_trade_id_has_valid_uuid(self):
        """Test that trade IDs contain valid UUID format."""
        trade_id = generate_trade_id()
        pattern = (
            r'^TRD_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
            r'[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert re.match(pattern, trade_id)


class TestIDTypeExtraction:
    """Test suite for ID type extraction utility."""

    def test_extract_type_from_tick_id(self):
        """Test extracting type from tick ID."""
        tick_id = generate_tick_id()
        assert extract_id_type(tick_id) == "TCK"

    def test_extract_type_from_schedule_id(self):
        """Test extracting type from schedule ID."""
        schedule_id = generate_schedule_id()
        assert extract_id_type(schedule_id) == "SCH"

    def test_extract_type_from_news_id(self):
        """Test extracting type from news ID."""
        news_id = generate_news_id()
        assert extract_id_type(news_id) == "NWS"

    def test_extract_type_from_manual_id(self):
        """Test extracting type from manual ID."""
        manual_id = generate_manual_id()
        assert extract_id_type(manual_id) == "MAN"

    def test_extract_type_from_opportunity_id(self):
        """Test extracting type from opportunity ID."""
        opp_id = generate_opportunity_id()
        assert extract_id_type(opp_id) == "OPP"

    def test_extract_type_from_threat_id(self):
        """Test extracting type from threat ID."""
        threat_id = generate_threat_id()
        assert extract_id_type(threat_id) == "THR"

    def test_extract_type_from_assessment_id(self):
        """Test extracting type from assessment ID."""
        assessment_id = generate_assessment_id()
        assert extract_id_type(assessment_id) == "ASS"

    def test_extract_type_from_trade_id(self):
        """Test extracting type from trade ID."""
        trade_id = generate_trade_id()
        assert extract_id_type(trade_id) == "TRD"

    def test_extract_type_rejects_invalid_format(self):
        """Test that invalid ID format raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            extract_id_type("invalid-id-without-underscore")

        assert "Invalid typed ID format" in str(exc_info.value)

    def test_extract_type_rejects_unknown_prefix(self):
        """Test that unknown prefix raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            extract_id_type("XXX_550e8400-e29b-41d4-a716-446655440000")

        assert "Unknown ID prefix" in str(exc_info.value)

    def test_extract_type_handles_multiple_underscores(self):
        """Test that only first underscore is used for prefix."""
        # Edge case: what if UUID somehow contains underscore?
        custom_id = "OPP_abc_def_ghi"
        assert extract_id_type(custom_id) == "OPP"
