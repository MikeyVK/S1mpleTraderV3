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
from datetime import datetime, timezone

# Third-Party Imports
import pytest

# Our Application Imports
from backend.utils.id_generators import (
    generate_tick_id,
    generate_schedule_id,
    generate_news_id,
    generate_signal_id,
    generate_risk_id,
    generate_strategy_directive_id,
    generate_entry_plan_id,
    generate_size_plan_id,
    generate_exit_plan_id,
    generate_execution_command_id,
    generate_trade_plan_id,
    extract_id_type,
    extract_id_timestamp,
)


class TestBirthIDGeneration:
    """Test suite for birth ID generators (strategy run initiators)."""

    def test_generate_tick_id_has_correct_prefix(self):
        """Test that tick IDs start with TCK_ prefix."""
        tick_id = generate_tick_id()
        assert tick_id.startswith("TCK_")

    def test_generate_tick_id_has_valid_datetime_format(self):
        """Test that tick IDs contain valid datetime format."""
        tick_id = generate_tick_id()
        # Format: TCK_YYYYMMDD_HHMMSS_8charhash
        pattern = r'^TCK_\d{8}_\d{6}_[0-9a-f]{8}$'
        assert re.match(pattern, tick_id), f"Invalid format: {tick_id}"

    def test_generate_tick_id_is_unique(self):
        """Test that consecutive tick IDs are unique."""
        id1 = generate_tick_id()
        id2 = generate_tick_id()
        assert id1 != id2

    def test_generate_schedule_id_has_correct_prefix(self):
        """Test that schedule IDs start with SCH_ prefix."""
        schedule_id = generate_schedule_id()
        assert schedule_id.startswith("SCH_")

    def test_generate_schedule_id_has_valid_datetime_format(self):
        """Test that schedule IDs contain valid datetime format."""
        schedule_id = generate_schedule_id()
        # Format: SCH_YYYYMMDD_HHMMSS_8charhash
        pattern = r'^SCH_\d{8}_\d{6}_[0-9a-f]{8}$'
        assert re.match(pattern, schedule_id), f"Invalid format: {schedule_id}"

    def test_generate_news_id_has_correct_prefix(self):
        """Test that news IDs start with NWS_ prefix."""
        news_id = generate_news_id()
        assert news_id.startswith("NWS_")

    def test_generate_news_id_has_valid_datetime_format(self):
        """Test that news IDs contain valid datetime format."""
        news_id = generate_news_id()
        # Format: NWS_YYYYMMDD_HHMMSS_8charhash
        pattern = r'^NWS_\d{8}_\d{6}_[0-9a-f]{8}$'
        assert re.match(pattern, news_id), f"Invalid format: {news_id}"


class TestWorkerOutputIDGeneration:
    """Test suite for worker output ID generators."""

    def test_generate_signal_id_has_correct_prefix(self):
        """Test that signal IDs start with SIG_ prefix."""
        sig_id = generate_signal_id()
        assert sig_id.startswith("SIG_")

    def test_generate_signal_id_has_valid_datetime_format(self):
        """Test that signal IDs contain valid datetime format."""
        sig_id = generate_signal_id()
        # Format: SIG_YYYYMMDD_HHMMSS_8charhash
        pattern = r'^SIG_\d{8}_\d{6}_[0-9a-f]{8}$'
        assert re.match(pattern, sig_id), f"Invalid format: {sig_id}"

    def test_generate_signal_id_is_unique(self):
        """Test that consecutive signal IDs are unique."""
        id1 = generate_signal_id()
        id2 = generate_signal_id()
        assert id1 != id2

    def test_generate_risk_id_has_correct_prefix(self):
        """Test that risk IDs start with RSK_ prefix."""
        risk_id = generate_risk_id()
        assert risk_id.startswith("RSK_")

    def test_generate_risk_id_has_valid_datetime_format(self):
        """Test that risk IDs contain valid datetime format."""
        risk_id = generate_risk_id()
        # Format: RSK_YYYYMMDD_HHMMSS_8charhash
        pattern = r'^RSK_\d{8}_\d{6}_[0-9a-f]{8}$'
        assert re.match(pattern, risk_id), f"Invalid format: {risk_id}"

    def test_generate_risk_id_is_unique(self):
        """Test that consecutive risk IDs are unique."""
        id1 = generate_risk_id()
        id2 = generate_risk_id()
        assert id1 != id2

    def test_generate_trade_plan_id_has_correct_prefix(self):
        """Test that trade plan IDs start with TPL_ prefix."""
        plan_id = generate_trade_plan_id()
        assert plan_id.startswith("TPL_")

    def test_generate_directive_id_has_correct_prefix(self):
        """Test that directive IDs start with STR_ prefix."""
        directive_id = generate_strategy_directive_id()
        assert directive_id.startswith("STR_")

    def test_generate_directive_id_has_valid_datetime_format(self):
        """Test that directive IDs contain valid datetime format."""
        directive_id = generate_strategy_directive_id()
        # Format: STR_YYYYMMDD_HHMMSS_8charhash
        pattern = r'^STR_\d{8}_\d{6}_[0-9a-f]{8}$'
        assert re.match(pattern, directive_id), f"Invalid format: {directive_id}"

    def test_generate_entry_plan_id_has_correct_prefix(self):
        """Test that entry plan IDs start with ENT_ prefix."""
        plan_id = generate_entry_plan_id()
        assert plan_id.startswith("ENT_")

    def test_generate_size_plan_id_has_correct_prefix(self):
        """Test that size plan IDs start with SIZ_ prefix."""
        plan_id = generate_size_plan_id()
        assert plan_id.startswith("SIZ_")

    def test_generate_exit_plan_id_has_correct_prefix(self):
        """Test that exit plan IDs start with EXT_ prefix."""
        plan_id = generate_exit_plan_id()
        assert plan_id.startswith("EXT_")

    def test_generate_execution_command_id_has_correct_prefix(self):
        """Test that execution command IDs start with EXC_ prefix."""
        command_id = generate_execution_command_id()
        assert command_id.startswith("EXC_")

    def test_generate_execution_command_id_has_valid_datetime_format(self):
        """Test that execution command IDs contain valid datetime format."""
        command_id = generate_execution_command_id()
        # Format: EXC_YYYYMMDD_HHMMSS_8charhash
        pattern = r'^EXC_\d{8}_\d{6}_[0-9a-f]{8}$'
        assert re.match(pattern, command_id), f"Invalid format: {command_id}"

    def test_generate_execution_command_id_is_unique(self):
        """Test that consecutive execution command IDs are unique."""
        id1 = generate_execution_command_id()
        id2 = generate_execution_command_id()
        assert id1 != id2


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

    def test_extract_type_from_signal_id(self):
        """Test extracting 'SIG' from signal ID."""
        sig_id = generate_signal_id()
        assert extract_id_type(sig_id) == "SIG"

    def test_extract_type_from_risk_id(self):
        """Test extracting 'RSK' from risk ID."""
        risk_id = generate_risk_id()
        assert extract_id_type(risk_id) == "RSK"

    def test_extract_type_from_trade_plan_id(self):
        """Test extracting type from trade plan ID."""
        plan_id = generate_trade_plan_id()
        assert extract_id_type(plan_id) == "TPL"

    def test_extract_type_from_directive_id(self):
        """Test extracting type from directive ID."""
        directive_id = generate_strategy_directive_id()
        assert extract_id_type(directive_id) == "STR"

    def test_extract_type_from_execution_command_id(self):
        """Test extracting 'EXC' from execution command ID."""
        command_id = generate_execution_command_id()
        assert extract_id_type(command_id) == "EXC"

    def test_extract_type_rejects_invalid_format(self):
        """Test that invalid ID format raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            extract_id_type("invalid-id-without-underscore")

        assert "Invalid typed ID format" in str(exc_info.value)

    def test_extract_type_rejects_unknown_prefix(self):
        """Test that unknown prefix raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            extract_id_type("XXX_20251026_100000_a1b2c3d4")

        assert "Unknown ID prefix" in str(exc_info.value)

    def test_extract_type_handles_multiple_underscores(self):
        """Test that only first underscore is used for prefix."""
        custom_id = "SIG_20251026_100000_a1b2c3d4"
        assert extract_id_type(custom_id) == "SIG"


class TestIDTimestampExtraction:
    """Test suite for ID timestamp extraction utility."""

    def test_extract_timestamp_from_tick_id(self):
        """Test extracting timestamp from tick ID."""
        tick_id = generate_tick_id()
        timestamp = extract_id_timestamp(tick_id)

        # Should be recent (within last minute)
        now = datetime.now(timezone.utc)
        assert (now - timestamp).total_seconds() < 60

    def test_extract_timestamp_from_signal_id(self):
        """Test extracting timestamp from signal ID."""
        sig_id = generate_signal_id()
        timestamp = extract_id_timestamp(sig_id)

        # Should be recent (within last minute)
        now = datetime.now(timezone.utc)
        assert (now - timestamp).total_seconds() < 60

    def test_extract_timestamp_rejects_invalid_format(self):
        """Test that invalid datetime format raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            extract_id_timestamp("TCK_invalid_datetime_a1b2c3d4")

        assert "Invalid timestamp in ID" in str(exc_info.value)

    def test_extract_timestamp_preserves_datetime(self):
        """Test that extracted timestamp matches ID datetime."""
        # Generate ID and immediately extract timestamp
        directive_id = generate_strategy_directive_id()
        timestamp = extract_id_timestamp(directive_id)

        # Extract datetime part from ID
        parts = directive_id.split("_")
        date_str = parts[1]  # YYYYMMDD
        time_str = parts[2]  # HHMMSS

        # Reconstruct expected datetime
        expected = datetime.strptime(
            f"{date_str}_{time_str}",
            "%Y%m%d_%H%M%S"
        ).replace(tzinfo=timezone.utc)

        # Should match
        assert timestamp == expected
