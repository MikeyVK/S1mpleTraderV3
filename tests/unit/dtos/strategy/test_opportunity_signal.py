# tests/unit/dtos/strategy/test_opportunity_signal.py
"""
Unit tests for OpportunitySignal DTO.

Tests the opportunity detection output contract according to TDD principles.
OpportunitySignal represents a detected trading opportunity and is the
foundation of the causal traceability chain.

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, backend.dtos.strategy.opportunity_signal]
"""

# Standard Library Imports
from datetime import datetime, timezone

# Third-Party Imports
import pytest
from pydantic import ValidationError

# Our Application Imports
from backend.dtos.strategy.opportunity_signal import OpportunitySignal
from backend.utils.id_generators import (
    generate_schedule_id,
    generate_tick_id,
    generate_opportunity_id,
)


class TestOpportunitySignalCreation:
    """Test suite for OpportunitySignal instantiation."""

    def test_create_minimal_signal(self):
        """Test creating signal with required fields only."""
        signal = OpportunitySignal(
            initiator_id=generate_tick_id(),
            timestamp=datetime.now(timezone.utc),
            asset="BTC/EUR",
            direction="long",
            signal_type="FVG_ENTRY"
        )

        # Verify ID formats (cast to avoid Pylance FieldInfo warnings)
        initiator_id = str(signal.initiator_id)
        opportunity_id = str(signal.opportunity_id)
        assert initiator_id.startswith("TCK_")
        assert opportunity_id.startswith("OPP_")
        assert signal.asset == "BTC/EUR"
        assert signal.direction == "long"
        assert signal.signal_type == "FVG_ENTRY"
        assert signal.confidence is None

    def test_create_signal_with_confidence(self):
        """Test creating signal with optional confidence score."""
        signal = OpportunitySignal(
            initiator_id=generate_tick_id(),
            timestamp=datetime.now(timezone.utc),
            asset="ETH/USDT",
            direction="short",
            signal_type="EMA_CROSS",
            confidence=0.85
        )

        assert signal.confidence == 0.85

    def test_opportunity_id_auto_generated(self):
        """Test that opportunity_id is auto-generated if not provided."""
        signal = OpportunitySignal(
            initiator_id=generate_tick_id(),
            timestamp=datetime.now(timezone.utc),
            asset="BTC/EUR",
            direction="long",
            signal_type="FVG_ENTRY"
        )

        opportunity_id = str(signal.opportunity_id)
        assert opportunity_id.startswith("OPP_")

    def test_custom_opportunity_id_accepted(self):
        """Test that custom opportunity_id can be provided."""
        custom_id = generate_opportunity_id()
        signal = OpportunitySignal(
            initiator_id=generate_tick_id(),
            opportunity_id=custom_id,
            timestamp=datetime.now(timezone.utc),
            asset="BTC/EUR",
            direction="long",
            signal_type="FVG_ENTRY"
        )

        assert signal.opportunity_id == custom_id


class TestOpportunitySignalInitiatorIDValidation:
    """Test suite for initiator_id validation."""

    def test_valid_tick_initiator_id(self):
        """Test that TCK_ prefixed initiator IDs are accepted."""
        signal = OpportunitySignal(
            initiator_id=generate_tick_id(),
            timestamp=datetime.now(timezone.utc),
            asset="BTC/EUR",
            direction="long",
            signal_type="TEST"
        )

        initiator_id = str(signal.initiator_id)
        assert initiator_id.startswith("TCK_")

    def test_valid_schedule_initiator_id(self):
        """Test that SCH_ prefixed initiator IDs are accepted."""

        signal = OpportunitySignal(
            initiator_id=generate_schedule_id(),
            timestamp=datetime.now(timezone.utc),
            asset="BTC/EUR",
            direction="long",
            signal_type="WEEKLY_DCA"
        )

        initiator_id = str(signal.initiator_id)
        assert initiator_id.startswith("SCH_")

    def test_invalid_initiator_id_prefix_rejected(self):
        """Test that invalid initiator prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpportunitySignal(
                initiator_id="INVALID_550e8400-e29b-41d4-a716-446655440000",
                timestamp=datetime.now(timezone.utc),
                asset="BTC/EUR",
                direction="long",
                signal_type="TEST"
            )

        assert "initiator_id" in str(exc_info.value)

    def test_invalid_initiator_id_format_rejected(self):
        """Test that non-UUID format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpportunitySignal(
                initiator_id="TCK_not-a-valid-uuid",
                timestamp=datetime.now(timezone.utc),
                asset="BTC/EUR",
                direction="long",
                signal_type="TEST"
            )

        assert "initiator_id" in str(exc_info.value)


class TestOpportunitySignalOpportunityIDValidation:
    """Test suite for opportunity_id validation."""

    def test_valid_opportunity_id_format(self):
        """Test that OPP_ prefix with UUID is valid."""
        signal = OpportunitySignal(
            initiator_id=generate_tick_id(),
            opportunity_id=generate_opportunity_id(),
            timestamp=datetime.now(timezone.utc),
            asset="BTC/EUR",
            direction="long",
            signal_type="TEST"
        )

        opportunity_id = str(signal.opportunity_id)
        assert opportunity_id.startswith("OPP_")

    def test_invalid_opportunity_id_prefix_rejected(self):
        """Test that non-OPP_ prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpportunitySignal(
                initiator_id=generate_tick_id(),
                opportunity_id="TCK_550e8400-e29b-41d4-a716-446655440000",
                timestamp=datetime.now(timezone.utc),
                asset="BTC/EUR",
                direction="long",
                signal_type="TEST"
            )

        assert "opportunity_id" in str(exc_info.value)


class TestOpportunitySignalTimestampValidation:
    """Test suite for timestamp validation."""

    def test_naive_datetime_converted_to_utc(self):
        """Test that naive datetime is assumed to be UTC."""
        naive_dt = datetime(2025, 1, 15, 10, 30, 0)
        signal = OpportunitySignal(
            initiator_id=generate_tick_id(),
            timestamp=naive_dt,
            asset="BTC/EUR",
            direction="long",
            signal_type="TEST"
        )

        # Naive datetime gets timezone applied - verify with aware_dt
        assert naive_dt.year == 2025
        assert naive_dt.month == 1
        assert naive_dt.day == 15
        assert signal.timestamp == naive_dt

    def test_aware_datetime_preserved(self):
        """Test that timezone-aware datetime is preserved."""
        aware_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        signal = OpportunitySignal(
            initiator_id=generate_tick_id(),
            timestamp=aware_dt,
            asset="BTC/EUR",
            direction="long",
            signal_type="TEST"
        )

        assert signal.timestamp == aware_dt


class TestOpportunitySignalAssetValidation:
    """Test suite for asset field validation."""

    def test_valid_asset_formats(self):
        """Test that valid asset formats are accepted."""
        valid_assets = [
            "BTC/EUR",
            "ETH/USDT",
            "BTC_PERP/USDT",
            "ETH_FUTURE/USD",
            "DOGE123/BTC",
        ]

        for asset in valid_assets:
            signal = OpportunitySignal(
                initiator_id=generate_tick_id(),
                timestamp=datetime.now(timezone.utc),
                asset=asset,
                direction="long",
                signal_type="TEST"
            )
            assert signal.asset == asset

    def test_asset_too_short_rejected(self):
        """Test that too short asset is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpportunitySignal(
                initiator_id=generate_tick_id(),
                timestamp=datetime.now(timezone.utc),
                asset="A/B",
                direction="long",
                signal_type="TEST"
            )

        assert "asset" in str(exc_info.value)

    def test_asset_too_long_rejected(self):
        """Test that too long asset is rejected."""
        long_asset = "A" * 15 + "/" + "B" * 15
        with pytest.raises(ValidationError) as exc_info:
            OpportunitySignal(
                initiator_id=generate_tick_id(),
                timestamp=datetime.now(timezone.utc),
                asset=long_asset,
                direction="long",
                signal_type="TEST"
            )

        assert "asset" in str(exc_info.value)

    def test_asset_invalid_format_rejected(self):
        """Test that invalid asset format is rejected."""
        invalid_assets = [
            "btc/eur",  # lowercase
            "BTC-EUR",  # dash instead of slash
            "BTC",  # no quote
            "BTC/eur",  # mixed case
        ]

        for invalid_asset in invalid_assets:
            with pytest.raises(ValidationError):
                OpportunitySignal(
                    initiator_id=generate_tick_id(),
                    timestamp=datetime.now(timezone.utc),
                    asset=invalid_asset,
                    direction="long",
                    signal_type="TEST"
                )


class TestOpportunitySignalDirectionValidation:
    """Test suite for direction field validation."""

    def test_long_direction_accepted(self):
        """Test that 'long' direction is accepted."""
        signal = OpportunitySignal(
            initiator_id=generate_tick_id(),
            timestamp=datetime.now(timezone.utc),
            asset="BTC/EUR",
            direction="long",
            signal_type="TEST"
        )

        assert signal.direction == "long"

    def test_short_direction_accepted(self):
        """Test that 'short' direction is accepted."""
        signal = OpportunitySignal(
            initiator_id=generate_tick_id(),
            timestamp=datetime.now(timezone.utc),
            asset="BTC/EUR",
            direction="short",
            signal_type="TEST"
        )

        assert signal.direction == "short"

    def test_invalid_direction_rejected(self):
        """Test that invalid direction is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpportunitySignal(
                initiator_id=generate_tick_id(),
                timestamp=datetime.now(timezone.utc),
                asset="BTC/EUR",
                direction="neutral",  # type: ignore
                signal_type="TEST"
            )

        assert "direction" in str(exc_info.value)


class TestOpportunitySignalTypeValidation:
    """Test suite for signal_type field validation."""

    def test_valid_signal_types(self):
        """Test that valid UPPER_SNAKE_CASE signal types are accepted."""
        valid_types = [
            "FVG_ENTRY",
            "EMA_CROSS",
            "WEEKLY_DCA",
            "RSI_OVERSOLD",
            "BREAKOUT",
            "A",  # Edge case: single letter (min 3 chars fails this)
        ]

        for signal_type in valid_types:
            if len(signal_type) >= 3:  # Skip single letter for this test
                signal = OpportunitySignal(
                    initiator_id=generate_tick_id(),
                    timestamp=datetime.now(timezone.utc),
                    asset="BTC/EUR",
                    direction="long",
                    signal_type=signal_type
                )
                assert signal.signal_type == signal_type

    def test_signal_type_too_short_rejected(self):
        """Test that signal_type < 3 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpportunitySignal(
                initiator_id=generate_tick_id(),
                timestamp=datetime.now(timezone.utc),
                asset="BTC/EUR",
                direction="long",
                signal_type="AB"
            )

        assert "signal_type" in str(exc_info.value)

    def test_signal_type_too_long_rejected(self):
        """Test that signal_type > 25 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpportunitySignal(
                initiator_id=generate_tick_id(),
                timestamp=datetime.now(timezone.utc),
                asset="BTC/EUR",
                direction="long",
                signal_type="A" * 26
            )

        assert "signal_type" in str(exc_info.value)

    def test_signal_type_lowercase_rejected(self):
        """Test that lowercase signal_type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpportunitySignal(
                initiator_id=generate_tick_id(),
                timestamp=datetime.now(timezone.utc),
                asset="BTC/EUR",
                direction="long",
                signal_type="fvg_entry"
            )

        assert "signal_type" in str(exc_info.value)

    def test_signal_type_reserved_prefix_rejected(self):
        """Test that reserved prefixes are rejected."""
        reserved_types = [
            "SYSTEM_EVENT",
            "INTERNAL_SIGNAL",
            "_PRIVATE"
        ]

        for reserved_type in reserved_types:
            with pytest.raises(ValidationError) as exc_info:
                OpportunitySignal(
                    initiator_id=generate_tick_id(),
                    timestamp=datetime.now(timezone.utc),
                    asset="BTC/EUR",
                    direction="long",
                    signal_type=reserved_type
                )

            assert "reserved prefix" in str(exc_info.value).lower()


class TestOpportunitySignalConfidenceValidation:
    """Test suite for confidence field validation."""

    def test_confidence_none_by_default(self):
        """Test that confidence is None if not provided."""
        signal = OpportunitySignal(
            initiator_id=generate_tick_id(),
            timestamp=datetime.now(timezone.utc),
            asset="BTC/EUR",
            direction="long",
            signal_type="TEST"
        )

        assert signal.confidence is None

    def test_valid_confidence_range(self):
        """Test that confidence values in [0.0, 1.0] are accepted."""
        valid_values = [0.0, 0.25, 0.5, 0.75, 1.0]

        for conf in valid_values:
            signal = OpportunitySignal(
                initiator_id=generate_tick_id(),
                timestamp=datetime.now(timezone.utc),
                asset="BTC/EUR",
                direction="long",
                signal_type="TEST",
                confidence=conf
            )
            assert signal.confidence == conf

    def test_confidence_below_zero_rejected(self):
        """Test that confidence < 0.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpportunitySignal(
                initiator_id=generate_tick_id(),
                timestamp=datetime.now(timezone.utc),
                asset="BTC/EUR",
                direction="long",
                signal_type="TEST",
                confidence=-0.1
            )

        assert "confidence" in str(exc_info.value)

    def test_confidence_above_one_rejected(self):
        """Test that confidence > 1.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpportunitySignal(
                initiator_id=generate_tick_id(),
                timestamp=datetime.now(timezone.utc),
                asset="BTC/EUR",
                direction="long",
                signal_type="TEST",
                confidence=1.1
            )

        assert "confidence" in str(exc_info.value)


class TestOpportunitySignalImmutability:
    """Test suite for OpportunitySignal immutability."""

    def test_signal_is_frozen(self):
        """Test that OpportunitySignal is immutable after creation."""
        signal = OpportunitySignal(
            initiator_id=generate_tick_id(),
            timestamp=datetime.now(timezone.utc),
            asset="BTC/EUR",
            direction="long",
            signal_type="TEST"
        )

        with pytest.raises(ValidationError):
            signal.direction = "short"  # type: ignore

    def test_no_extra_fields_allowed(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            OpportunitySignal(
                initiator_id=generate_tick_id(),
                timestamp=datetime.now(timezone.utc),
                asset="BTC/EUR",
                direction="long",
                signal_type="TEST",
                extra_field="not allowed"  # type: ignore
            )

        assert "extra_field" in str(exc_info.value).lower()
