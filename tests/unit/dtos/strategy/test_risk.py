# tests/unit/dtos/strategy/test_risk.py
"""
Unit tests for Risk DTO.

Tests the risk detection output contract according to TDD principles.
Risk represents a detected risk and forms part of the quant
analysis framework.

NOTE: Pylance shows "missing affected_asset" warnings on Risk() calls.
This is a known Pylance/Pydantic v2 limitation where Field(None, default=None)
isn't recognized as making a parameter optional. All tests pass - the field IS
optional. Warnings suppressed with # type: ignore[call-arg].

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, backend.dtos.strategy.risk]
"""

# Standard Library Imports
from datetime import datetime, timezone

# Third-Party Imports
import pytest
from pydantic import ValidationError

# Our Application Imports
from backend.dtos.strategy.risk import Risk
from backend.dtos.causality import CausalityChain
from backend.utils.id_generators import (
    generate_tick_id,
    generate_risk_id,
    generate_schedule_id,
)


class TestRiskCreation:
    """Test suite for Risk instantiation."""

    def test_create_minimal_event(self):
        """Test creating event with required fields only."""
        event = Risk(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=datetime.now(timezone.utc),
            risk_type="MAX_DRAWDOWN_APPROACHING",
            severity=0.75
        )

        # Verify ID formats (cast to avoid Pylance FieldInfo warnings)
        # Verify causality chain
        assert event.causality.tick_id is not None
        assert event.causality.tick_id.startswith("TCK_")
        # Verify ID formats
        risk_id = str(event.risk_id)
        assert risk_id.startswith("RSK_")
        assert event.risk_type == "MAX_DRAWDOWN_APPROACHING"
        assert event.severity == 0.75
        assert event.affected_asset is None

    def test_create_event_with_affected_asset(self):
        """Test creating event with affected asset specified."""
        event = Risk(
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=datetime.now(timezone.utc),
            risk_type="UNUSUAL_VOLATILITY",
            severity=0.60,
            affected_asset="BTC/EUR"
        )

        assert event.affected_asset == "BTC/EUR"

    def test_risk_id_auto_generated(self):
        """Test that risk_id is auto-generated if not provided."""
        event = Risk(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=datetime.now(timezone.utc),
            risk_type="HEALTH_DEGRADED",
            severity=0.50
        )

        risk_id = str(event.risk_id)
        assert risk_id.startswith("RSK_")

    def test_custom_risk_id_accepted(self):
        """Test that custom risk_id can be provided."""
        custom_id = generate_risk_id()
        event = Risk(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            risk_id=custom_id,
            timestamp=datetime.now(timezone.utc),
            risk_type="EMERGENCY_HALT",
            severity=1.0
        )

        assert event.risk_id == custom_id




class TestRiskThreatIDValidation:
    """Test suite for risk_id validation."""

    def test_valid_risk_id_format(self):
        """Test that RSK_ prefix with UUID is valid."""
        event = Risk(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            risk_id=generate_risk_id(),
            timestamp=datetime.now(timezone.utc),
            risk_type="TEST",
            severity=0.5
        )

        risk_id = str(event.risk_id)
        assert risk_id.startswith("RSK_")

    def test_invalid_risk_id_prefix_rejected(self):
        """Test that non-RSK_ prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                risk_id="OPP_550e8400-e29b-41d4-a716-446655440000",
                timestamp=datetime.now(timezone.utc),
                risk_type="TEST",
                severity=0.5
            )

        assert "risk_id" in str(exc_info.value)


class TestRiskTimestampValidation:
    """Test suite for timestamp validation."""

    def test_naive_datetime_converted_to_utc(self):
        """Test that naive datetime is converted to UTC."""
        naive_dt = datetime(2025, 1, 15, 10, 30, 0)
        event = Risk(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=naive_dt,
            risk_type="TEST",
            severity=0.5
        )

        expected_utc = naive_dt.replace(tzinfo=timezone.utc)
        # Test via input variable properties, not FieldInfo access
        assert naive_dt.year == 2025
        assert naive_dt.month == 1
        assert naive_dt.day == 15
        # Verify timestamp conversion
        assert event.timestamp == expected_utc

    def test_aware_datetime_preserved(self):
        """Test that timezone-aware datetime is preserved."""
        aware_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        event = Risk(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=aware_dt,
            risk_type="TEST",
            severity=0.5
        )

        assert event.timestamp == aware_dt


class TestRiskThreatTypeValidation:
    """Test suite for risk_type field validation."""

    def test_valid_risk_types(self):
        """Test that valid UPPER_SNAKE_CASE threat types are accepted."""
        valid_types = [
            "MAX_DRAWDOWN_APPROACHING",
            "UNUSUAL_VOLATILITY",
            "HEALTH_DEGRADED",
            "EMERGENCY_HALT",
            "RISK_LIMIT_BREACHED",
        ]

        for risk_type in valid_types:
            event = Risk(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                risk_type=risk_type,
                severity=0.5
            )
            assert event.risk_type == risk_type

    def test_risk_type_too_short_rejected(self):
        """Test that risk_type < 3 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                risk_type="AB",
                severity=0.5
            )

        assert "risk_type" in str(exc_info.value)

    def test_risk_type_too_long_rejected(self):
        """Test that risk_type > 25 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                risk_type="A" * 26,
                severity=0.5
            )

        assert "risk_type" in str(exc_info.value)

    def test_risk_type_lowercase_rejected(self):
        """Test that lowercase risk_type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                risk_type="max_drawdown",
                severity=0.5
            )

        assert "risk_type" in str(exc_info.value)

    def test_risk_type_reserved_prefix_rejected(self):
        """Test that reserved prefixes are rejected."""
        reserved_types = [
            "SYSTEM_EVENT",
            "INTERNAL_THREAT",
            "_PRIVATE"
        ]

        for reserved_type in reserved_types:
            with pytest.raises(ValidationError) as exc_info:
                Risk(  # type: ignore[call-arg]
                    causality=CausalityChain(tick_id=generate_tick_id()),
                    timestamp=datetime.now(timezone.utc),
                    risk_type=reserved_type,
                    severity=0.5
                )

            assert "reserved prefix" in str(exc_info.value).lower()


class TestRiskSeverityValidation:
    """Test suite for severity field validation (SWOT framework)."""

    def test_valid_severity_range(self):
        """Test that severity values in [0.0, 1.0] are accepted."""
        valid_values = [0.0, 0.25, 0.5, 0.75, 1.0]

        for sev in valid_values:
            event = Risk(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                risk_type="TEST",
                severity=sev
            )
            assert event.severity == sev

    def test_severity_below_zero_rejected(self):
        """Test that severity < 0.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                risk_type="TEST",
                severity=-0.1
            )

        assert "severity" in str(exc_info.value)

    def test_severity_above_one_rejected(self):
        """Test that severity > 1.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                risk_type="TEST",
                severity=1.1
            )

        assert "severity" in str(exc_info.value)


class TestRiskAffectedAssetValidation:
    """Test suite for affected_asset field validation."""

    def test_system_wide_threat_no_asset(self):
        """Test that system-wide threats can have no affected_asset."""
        event = Risk(
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=datetime.now(timezone.utc),
            risk_type="EXCHANGE_DOWNTIME",
            severity=0.9,
            affected_asset=None
        )

        assert event.affected_asset is None

    def test_valid_asset_formats(self):
        """Test that valid asset formats are accepted."""
        valid_assets = [
            "BTC/EUR",
            "ETH/USDT",
            "BTC_PERP/USDT",
            "ETH_FUTURE/USD",
        ]

        for asset in valid_assets:
            event = Risk(
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                risk_type="UNUSUAL_VOLATILITY",
                severity=0.6,
                affected_asset=asset
            )
            assert event.affected_asset == asset

    def test_asset_too_short_rejected(self):
        """Test that too short asset is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                risk_type="TEST",
                severity=0.5,
                affected_asset="A/B"
            )

        assert "affected_asset" in str(exc_info.value)

    def test_asset_invalid_format_rejected(self):
        """Test that invalid asset format is rejected."""
        invalid_assets = [
            "btc/eur",  # lowercase
            "BTC-EUR",  # dash instead of slash
            "BTC",  # no quote
        ]

        for invalid_asset in invalid_assets:
            with pytest.raises(ValidationError):
                Risk(
                    causality=CausalityChain(tick_id=generate_tick_id()),
                    timestamp=datetime.now(timezone.utc),
                    risk_type="TEST",
                    severity=0.5,
                    affected_asset=invalid_asset
                )


class TestRiskImmutability:
    """Test suite for Risk immutability."""

    def test_event_is_frozen(self):
        """Test that Risk is immutable after creation."""
        event = Risk(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=datetime.now(timezone.utc),
            risk_type="TEST",
            severity=0.5
        )

        with pytest.raises(ValidationError):
            event.severity = 0.9  # type: ignore

    def test_no_extra_fields_allowed(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                risk_type="TEST",
                severity=0.5,
                extra_field="not allowed"  # type: ignore
            )

        assert "extra_field" in str(exc_info.value).lower()
