# tests/unit/dtos/strategy/test_risk.py
"""
Unit tests for Risk DTO.

Tests the risk detection output contract according to TDD principles.
Risk represents a detected risk and is a PRE-CAUSALITY DTO.
It does NOT have a causality field - CausalityChain is created by
StrategyPlanner when it makes a decision based on the risk.

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, decimal, backend.dtos.strategy.risk]
"""

# Standard Library Imports
from datetime import UTC, datetime
from decimal import Decimal

# Third-Party Imports
import pytest
from pydantic import ValidationError

# Our Application Imports
from backend.dtos.strategy.risk import Risk
from backend.utils.id_generators import generate_risk_id


class TestRiskCreation:
    """Test suite for Risk instantiation."""

    def test_create_minimal_risk(self):
        """Test creating risk with required fields only (no causality!)."""
        risk = Risk(
            timestamp=datetime.now(UTC),
            risk_type="MAX_DRAWDOWN_APPROACHING",
            severity=Decimal("0.75")
        )

        # Verify NO causality field (Risk is pre-causality)
        assert not hasattr(risk, 'causality')
        # Verify ID formats
        risk_id = str(risk.risk_id)
        assert risk_id.startswith("RSK_")
        assert risk.risk_type == "MAX_DRAWDOWN_APPROACHING"
        assert risk.severity == Decimal("0.75")
        assert risk.affected_symbol is None

    def test_create_risk_with_affected_symbol(self):
        """Test creating risk with affected symbol specified."""
        risk = Risk(
            timestamp=datetime.now(UTC),
            risk_type="UNUSUAL_VOLATILITY",
            severity=Decimal("0.60"),
            affected_symbol="BTC_EUR"
        )

        assert risk.affected_symbol == "BTC_EUR"

    def test_risk_id_auto_generated(self):
        """Test that risk_id is auto-generated if not provided."""
        risk = Risk(
            timestamp=datetime.now(UTC),
            risk_type="HEALTH_DEGRADED",
            severity=Decimal("0.50")
        )

        risk_id = str(risk.risk_id)
        assert risk_id.startswith("RSK_")

    def test_custom_risk_id_accepted(self):
        """Test that custom risk_id can be provided."""
        custom_id = generate_risk_id()
        risk = Risk(
            risk_id=custom_id,
            timestamp=datetime.now(UTC),
            risk_type="EMERGENCY_HALT",
            severity=Decimal("1.0")
        )

        assert risk.risk_id == custom_id


class TestRiskPreCausality:
    """Test suite verifying Risk is a pre-causality DTO."""

    def test_risk_has_no_causality_field(self):
        """Risk should NOT have a causality field - it's pre-causality."""
        risk = Risk(
            timestamp=datetime.now(UTC),
            risk_type="DRAWDOWN_BREACH",
            severity=Decimal("0.80")
        )

        # Risk is pre-causality - CausalityChain is created by StrategyPlanner
        assert not hasattr(risk, 'causality')

    def test_risk_creation_without_causality_succeeds(self):
        """Should create Risk without any causality parameter."""
        risk = Risk(
            timestamp=datetime.now(UTC),
            risk_type="POSITION_RISK",
            severity=Decimal("0.65")
        )

        assert risk.risk_id.startswith("RSK_")


class TestRiskIDValidation:
    """Test suite for risk_id validation."""

    def test_valid_risk_id_format(self):
        """Test that RSK_ prefix with military datetime is valid."""
        risk = Risk(
            risk_id=generate_risk_id(),
            timestamp=datetime.now(UTC),
            risk_type="TEST",
            severity=Decimal("0.5")
        )

        risk_id = str(risk.risk_id)
        assert risk_id.startswith("RSK_")

    def test_invalid_risk_id_prefix_rejected(self):
        """Test that non-RSK_ prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(
                risk_id="OPP_550e8400-e29b-41d4-a716-446655440000",
                timestamp=datetime.now(UTC),
                risk_type="TEST",
                severity=Decimal("0.5")
            )

        assert "risk_id" in str(exc_info.value)


class TestRiskTimestampValidation:
    """Test suite for timestamp validation."""

    def test_naive_datetime_converted_to_utc(self):
        """Test that naive datetime is converted to UTC."""
        naive_dt = datetime(2025, 1, 15, 10, 30, 0)
        risk = Risk(
            timestamp=naive_dt,
            risk_type="TEST",
            severity=Decimal("0.5")
        )

        expected_utc = naive_dt.replace(tzinfo=UTC)
        assert risk.timestamp == expected_utc

    def test_aware_datetime_preserved(self):
        """Test that timezone-aware datetime is preserved."""
        aware_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        risk = Risk(
            timestamp=aware_dt,
            risk_type="TEST",
            severity=Decimal("0.5")
        )

        assert risk.timestamp == aware_dt


class TestRiskTypeValidation:
    """Test suite for risk_type field validation."""

    def test_valid_risk_types(self):
        """Test that valid UPPER_SNAKE_CASE risk types are accepted."""
        valid_types = [
            "MAX_DRAWDOWN_APPROACHING",
            "UNUSUAL_VOLATILITY",
            "HEALTH_DEGRADED",
            "EMERGENCY_HALT",
            "RISK_LIMIT_BREACHED",
        ]

        for risk_type in valid_types:
            risk = Risk(
                timestamp=datetime.now(UTC),
                risk_type=risk_type,
                severity=Decimal("0.5")
            )
            assert risk.risk_type == risk_type

    def test_risk_type_too_short_rejected(self):
        """Test that risk_type < 3 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(
                timestamp=datetime.now(UTC),
                risk_type="AB",
                severity=Decimal("0.5")
            )

        assert "risk_type" in str(exc_info.value)

    def test_risk_type_too_long_rejected(self):
        """Test that risk_type > 25 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(
                timestamp=datetime.now(UTC),
                risk_type="A" * 26,
                severity=Decimal("0.5")
            )

        assert "risk_type" in str(exc_info.value)

    def test_risk_type_lowercase_rejected(self):
        """Test that lowercase risk_type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(
                timestamp=datetime.now(UTC),
                risk_type="max_drawdown",
                severity=Decimal("0.5")
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
                Risk(
                    timestamp=datetime.now(UTC),
                    risk_type=reserved_type,
                    severity=Decimal("0.5")
                )

            assert "reserved prefix" in str(exc_info.value).lower()


class TestRiskSeverityValidation:
    """Test suite for severity field validation (now Decimal)."""

    def test_severity_is_decimal_type(self):
        """Test that severity is stored as Decimal for precision."""
        risk = Risk(
            timestamp=datetime.now(UTC),
            risk_type="TEST",
            severity=Decimal("0.75")
        )

        assert isinstance(risk.severity, Decimal)
        assert risk.severity == Decimal("0.75")

    def test_severity_float_converted_to_decimal(self):
        """Test that float input is converted to Decimal."""
        risk = Risk(
            timestamp=datetime.now(UTC),
            risk_type="TEST",
            severity=0.85
        )

        assert isinstance(risk.severity, Decimal)

    def test_valid_severity_range(self):
        """Test that severity values in [0.0, 1.0] are accepted."""
        valid_values = [
            Decimal("0.0"),
            Decimal("0.25"),
            Decimal("0.5"),
            Decimal("0.75"),
            Decimal("1.0")
        ]

        for sev in valid_values:
            risk = Risk(
                timestamp=datetime.now(UTC),
                risk_type="TEST",
                severity=sev
            )
            assert risk.severity == sev

    def test_severity_below_zero_rejected(self):
        """Test that severity < 0.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(
                timestamp=datetime.now(UTC),
                risk_type="TEST",
                severity=Decimal("-0.1")
            )

        assert "severity" in str(exc_info.value)

    def test_severity_above_one_rejected(self):
        """Test that severity > 1.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(
                timestamp=datetime.now(UTC),
                risk_type="TEST",
                severity=Decimal("1.1")
            )

        assert "severity" in str(exc_info.value)


class TestRiskAffectedSymbolValidation:
    """Test suite for affected_symbol field validation (renamed from affected_asset)."""

    def test_system_wide_risk_has_no_symbol(self):
        """Test that system-wide risks can have no affected_symbol."""
        risk = Risk(
            timestamp=datetime.now(UTC),
            risk_type="EXCHANGE_DOWNTIME",
            severity=Decimal("0.9"),
            affected_symbol=None
        )

        assert risk.affected_symbol is None

    def test_valid_symbol_formats(self):
        """Test that valid symbol formats are accepted (underscore separator)."""
        valid_symbols = [
            "BTC_EUR",
            "ETH_USDT",
            "BTC_PERP",
            "SOL_USDC",
        ]

        for symbol in valid_symbols:
            risk = Risk(
                timestamp=datetime.now(UTC),
                risk_type="UNUSUAL_VOLATILITY",
                severity=Decimal("0.6"),
                affected_symbol=symbol
            )
            assert risk.affected_symbol == symbol

    def test_symbol_too_short_rejected(self):
        """Test that too short symbol is rejected (min 3 chars)."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(
                timestamp=datetime.now(UTC),
                risk_type="TEST",
                severity=Decimal("0.5"),
                affected_symbol="AB"
            )

        assert "affected_symbol" in str(exc_info.value)

    def test_symbol_invalid_format_rejected(self):
        """Test that invalid symbol format is rejected."""
        invalid_symbols = [
            "btc_eur",      # lowercase
            "BTC/EUR",      # slash instead of underscore (OLD format)
            "BTC-EUR",      # dash separator
            "123_456",      # starts with number
        ]

        for invalid_symbol in invalid_symbols:
            with pytest.raises(ValidationError):
                Risk(
                    timestamp=datetime.now(UTC),
                    risk_type="TEST",
                    severity=Decimal("0.5"),
                    affected_symbol=invalid_symbol
                )


class TestRiskImmutability:
    """Test suite for Risk immutability."""

    def test_risk_is_frozen(self):
        """Test that Risk is immutable after creation."""
        risk = Risk(
            timestamp=datetime.now(UTC),
            risk_type="TEST",
            severity=Decimal("0.5")
        )

        with pytest.raises(ValidationError):
            risk.severity = Decimal("0.9")  # type: ignore

    def test_no_extra_fields_allowed(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            Risk(
                timestamp=datetime.now(UTC),
                risk_type="TEST",
                severity=Decimal("0.5"),
                extra_field="not allowed"  # type: ignore
            )

        assert "extra_field" in str(exc_info.value).lower()


class TestRiskSerialization:
    """Test suite for Risk JSON serialization."""

    def test_risk_to_json(self):
        """Test Risk serializes to JSON correctly."""
        risk = Risk(
            timestamp=datetime(2025, 12, 1, 14, 30, 0, tzinfo=UTC),
            risk_type="STOP_LOSS_HIT",
            severity=Decimal("0.90"),
            affected_symbol="BTC_USDT"
        )

        json_data = risk.model_dump(mode='json')

        assert json_data["risk_type"] == "STOP_LOSS_HIT"
        assert json_data["affected_symbol"] == "BTC_USDT"
        assert "causality" not in json_data  # Pre-causality!

    def test_risk_from_json(self):
        """Test Risk deserializes from JSON correctly."""
        json_data = {
            "timestamp": "2025-12-01T14:30:00Z",
            "risk_type": "DRAWDOWN_BREACH",
            "severity": "0.85",
            "affected_symbol": "ETH_USDT"
        }

        risk = Risk.model_validate(json_data)

        assert risk.risk_type == "DRAWDOWN_BREACH"
        assert risk.severity == Decimal("0.85")
        assert risk.affected_symbol == "ETH_USDT"

    def test_system_wide_risk_from_json(self):
        """Test system-wide Risk deserializes correctly."""
        json_data = {
            "timestamp": "2025-12-01T14:35:00Z",
            "risk_type": "EXCHANGE_DOWN",
            "severity": "1.0",
            "affected_symbol": None
        }

        risk = Risk.model_validate(json_data)

        assert risk.affected_symbol is None
        assert risk.severity == Decimal("1.0")
