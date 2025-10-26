# tests/unit/dtos/execution/test_threat_signal.py
"""
Unit tests for ThreatSignal DTO.

Tests the threat/risk detection output contract according to TDD principles.
ThreatSignal represents a detected threat and forms part of the SWOT
analysis framework.

NOTE: Pylance shows "missing affected_asset" warnings on ThreatSignal() calls.
This is a known Pylance/Pydantic v2 limitation where Field(None, default=None)
isn't recognized as making a parameter optional. All tests pass - the field IS
optional. Warnings suppressed with # type: ignore[call-arg].

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, backend.dtos.execution.threat_signal]
"""

# Standard Library Imports
from datetime import datetime, timezone

# Third-Party Imports
import pytest
from pydantic import ValidationError

# Our Application Imports
from backend.dtos.strategy.threat_signal import ThreatSignal
from backend.dtos.causality import CausalityChain
from backend.utils.id_generators import (
    generate_tick_id,
    generate_threat_id,
    generate_schedule_id,
)


class TestThreatSignalCreation:
    """Test suite for ThreatSignal instantiation."""

    def test_create_minimal_event(self):
        """Test creating event with required fields only."""
        event = ThreatSignal(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=datetime.now(timezone.utc),
            threat_type="MAX_DRAWDOWN_APPROACHING",
            severity=0.75
        )

        # Verify ID formats (cast to avoid Pylance FieldInfo warnings)
        # Verify causality chain
        assert event.causality.tick_id is not None
        assert event.causality.tick_id.startswith("TCK_")
        # Verify ID formats
        threat_id = str(event.threat_id)
        assert threat_id.startswith("THR_")
        assert event.threat_type == "MAX_DRAWDOWN_APPROACHING"
        assert event.severity == 0.75
        assert event.affected_asset is None

    def test_create_event_with_affected_asset(self):
        """Test creating event with affected asset specified."""
        event = ThreatSignal(
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=datetime.now(timezone.utc),
            threat_type="UNUSUAL_VOLATILITY",
            severity=0.60,
            affected_asset="BTC/EUR"
        )

        assert event.affected_asset == "BTC/EUR"

    def test_threat_id_auto_generated(self):
        """Test that threat_id is auto-generated if not provided."""
        event = ThreatSignal(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=datetime.now(timezone.utc),
            threat_type="HEALTH_DEGRADED",
            severity=0.50
        )

        threat_id = str(event.threat_id)
        assert threat_id.startswith("THR_")

    def test_custom_threat_id_accepted(self):
        """Test that custom threat_id can be provided."""
        custom_id = generate_threat_id()
        event = ThreatSignal(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            threat_id=custom_id,
            timestamp=datetime.now(timezone.utc),
            threat_type="EMERGENCY_HALT",
            severity=1.0
        )

        assert event.threat_id == custom_id




class TestThreatSignalThreatIDValidation:
    """Test suite for threat_id validation."""

    def test_valid_threat_id_format(self):
        """Test that THR_ prefix with UUID is valid."""
        event = ThreatSignal(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            threat_id=generate_threat_id(),
            timestamp=datetime.now(timezone.utc),
            threat_type="TEST",
            severity=0.5
        )

        threat_id = str(event.threat_id)
        assert threat_id.startswith("THR_")

    def test_invalid_threat_id_prefix_rejected(self):
        """Test that non-THR_ prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatSignal(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                threat_id="OPP_550e8400-e29b-41d4-a716-446655440000",
                timestamp=datetime.now(timezone.utc),
                threat_type="TEST",
                severity=0.5
            )

        assert "threat_id" in str(exc_info.value)


class TestThreatSignalTimestampValidation:
    """Test suite for timestamp validation."""

    def test_naive_datetime_converted_to_utc(self):
        """Test that naive datetime is converted to UTC."""
        naive_dt = datetime(2025, 1, 15, 10, 30, 0)
        event = ThreatSignal(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=naive_dt,
            threat_type="TEST",
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
        event = ThreatSignal(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=aware_dt,
            threat_type="TEST",
            severity=0.5
        )

        assert event.timestamp == aware_dt


class TestThreatSignalThreatTypeValidation:
    """Test suite for threat_type field validation."""

    def test_valid_threat_types(self):
        """Test that valid UPPER_SNAKE_CASE threat types are accepted."""
        valid_types = [
            "MAX_DRAWDOWN_APPROACHING",
            "UNUSUAL_VOLATILITY",
            "HEALTH_DEGRADED",
            "EMERGENCY_HALT",
            "RISK_LIMIT_BREACHED",
        ]

        for threat_type in valid_types:
            event = ThreatSignal(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                threat_type=threat_type,
                severity=0.5
            )
            assert event.threat_type == threat_type

    def test_threat_type_too_short_rejected(self):
        """Test that threat_type < 3 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatSignal(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                threat_type="AB",
                severity=0.5
            )

        assert "threat_type" in str(exc_info.value)

    def test_threat_type_too_long_rejected(self):
        """Test that threat_type > 25 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatSignal(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                threat_type="A" * 26,
                severity=0.5
            )

        assert "threat_type" in str(exc_info.value)

    def test_threat_type_lowercase_rejected(self):
        """Test that lowercase threat_type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatSignal(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                threat_type="max_drawdown",
                severity=0.5
            )

        assert "threat_type" in str(exc_info.value)

    def test_threat_type_reserved_prefix_rejected(self):
        """Test that reserved prefixes are rejected."""
        reserved_types = [
            "SYSTEM_EVENT",
            "INTERNAL_THREAT",
            "_PRIVATE"
        ]

        for reserved_type in reserved_types:
            with pytest.raises(ValidationError) as exc_info:
                ThreatSignal(  # type: ignore[call-arg]
                    causality=CausalityChain(tick_id=generate_tick_id()),
                    timestamp=datetime.now(timezone.utc),
                    threat_type=reserved_type,
                    severity=0.5
                )

            assert "reserved prefix" in str(exc_info.value).lower()


class TestThreatSignalSeverityValidation:
    """Test suite for severity field validation (SWOT framework)."""

    def test_valid_severity_range(self):
        """Test that severity values in [0.0, 1.0] are accepted."""
        valid_values = [0.0, 0.25, 0.5, 0.75, 1.0]

        for sev in valid_values:
            event = ThreatSignal(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                threat_type="TEST",
                severity=sev
            )
            assert event.severity == sev

    def test_severity_below_zero_rejected(self):
        """Test that severity < 0.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatSignal(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                threat_type="TEST",
                severity=-0.1
            )

        assert "severity" in str(exc_info.value)

    def test_severity_above_one_rejected(self):
        """Test that severity > 1.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatSignal(  # type: ignore[call-arg]
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                threat_type="TEST",
                severity=1.1
            )

        assert "severity" in str(exc_info.value)


class TestThreatSignalAffectedAssetValidation:
    """Test suite for affected_asset field validation."""

    def test_system_wide_threat_no_asset(self):
        """Test that system-wide threats can have no affected_asset."""
        event = ThreatSignal(
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=datetime.now(timezone.utc),
            threat_type="EXCHANGE_DOWNTIME",
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
            event = ThreatSignal(
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                threat_type="UNUSUAL_VOLATILITY",
                severity=0.6,
                affected_asset=asset
            )
            assert event.affected_asset == asset

    def test_asset_too_short_rejected(self):
        """Test that too short asset is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatSignal(
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                threat_type="TEST",
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
                ThreatSignal(
                    causality=CausalityChain(tick_id=generate_tick_id()),
                    timestamp=datetime.now(timezone.utc),
                    threat_type="TEST",
                    severity=0.5,
                    affected_asset=invalid_asset
                )


class TestThreatSignalImmutability:
    """Test suite for ThreatSignal immutability."""

    def test_event_is_frozen(self):
        """Test that ThreatSignal is immutable after creation."""
        event = ThreatSignal(  # type: ignore[call-arg]
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=datetime.now(timezone.utc),
            threat_type="TEST",
            severity=0.5
        )

        with pytest.raises(ValidationError):
            event.severity = 0.9  # type: ignore

    def test_no_extra_fields_allowed(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatSignal(
                causality=CausalityChain(tick_id=generate_tick_id()),
                timestamp=datetime.now(timezone.utc),
                threat_type="TEST",
                severity=0.5,
                extra_field="not allowed"  # type: ignore
            )

        assert "extra_field" in str(exc_info.value).lower()
