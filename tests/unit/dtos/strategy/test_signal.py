# tests/unit/dtos/strategy/test_signal.py
"""
Unit tests for Signal DTO.

Tests the signal detection output contract according to TDD principles.
Signal represents a detected trading signal and is a PRE-CAUSALITY DTO.
It does NOT have a causality field - CausalityChain is created by
StrategyPlanner when it makes a decision based on the signal.

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, decimal, backend.dtos.strategy.signal]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives for optional fields

# Standard Library Imports
from datetime import UTC, datetime
from decimal import Decimal

# Third-Party Imports
import pytest
from pydantic import ValidationError

# Our Application Imports
from backend.dtos.strategy.signal import Signal
from backend.utils.id_generators import generate_signal_id


class TestSignalCreation:
    """Test suite for Signal instantiation."""

    def test_create_minimal_signal(self):
        """Test creating signal with required fields only (no causality!)."""
        signal = Signal(
            timestamp=datetime.now(UTC),
            symbol="BTC_USDT",
            direction="long",
            signal_type="FVG_ENTRY"
        )

        # Verify NO causality field (Signal is pre-causality)
        assert not hasattr(signal, 'causality')
        # Verify ID formats
        signal_id = str(signal.signal_id)
        assert signal_id.startswith("SIG_")
        assert signal.symbol == "BTC_USDT"
        assert signal.direction == "long"
        assert signal.signal_type == "FVG_ENTRY"
        assert signal.confidence is None

    def test_create_signal_with_confidence(self):
        """Test creating signal with optional confidence score (Decimal)."""
        signal = Signal(
            timestamp=datetime.now(UTC),
            symbol="ETH_USDT",
            direction="short",
            signal_type="EMA_CROSS",
            confidence=Decimal("0.85")
        )

        assert signal.confidence == Decimal("0.85")
        assert isinstance(signal.confidence, Decimal)

    def test_signal_id_auto_generated(self):
        """Test that signal_id is auto-generated if not provided."""
        signal = Signal(
            timestamp=datetime.now(UTC),
            symbol="BTC_EUR",
            direction="long",
            signal_type="FVG_ENTRY"
        )

        signal_id = str(signal.signal_id)
        assert signal_id.startswith("SIG_")

    def test_custom_signal_id_accepted(self):
        """Test that custom signal_id can be provided."""
        custom_id = generate_signal_id()
        signal = Signal(
            signal_id=custom_id,
            timestamp=datetime.now(UTC),
            symbol="BTC_EUR",
            direction="long",
            signal_type="FVG_ENTRY"
        )

        assert signal.signal_id == custom_id


class TestSignalPreCausality:
    """Test suite verifying Signal is a pre-causality DTO."""

    def test_signal_has_no_causality_field(self):
        """Signal should NOT have a causality field - it's pre-causality."""
        signal = Signal(
            timestamp=datetime.now(UTC),
            symbol="BTC_USDT",
            direction="long",
            signal_type="BREAKOUT"
        )

        # Signal is pre-causality - CausalityChain is created by StrategyPlanner
        assert not hasattr(signal, 'causality')

    def test_signal_creation_without_causality_succeeds(self):
        """Should create Signal without any causality parameter."""
        # This should NOT require causality parameter
        signal = Signal(
            timestamp=datetime.now(UTC),
            symbol="ETH_USDT",
            direction="short",
            signal_type="REVERSAL"
        )

        assert signal.signal_id.startswith("SIG_")


class TestSignalIDValidation:
    """Test suite for signal_id validation."""

    def test_valid_signal_id_format(self):
        """Test that SIG_ prefix with military datetime is valid."""
        signal = Signal(
            signal_id=generate_signal_id(),
            timestamp=datetime.now(UTC),
            symbol="BTC_EUR",
            direction="long",
            signal_type="TEST"
        )

        signal_id = str(signal.signal_id)
        assert signal_id.startswith("SIG_")

    def test_invalid_signal_id_prefix_rejected(self):
        """Test that non-SIG_ prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                signal_id="TCK_550e8400-e29b-41d4-a716-446655440000",
                timestamp=datetime.now(UTC),
                symbol="BTC_EUR",
                direction="long",
                signal_type="TEST"
            )

        assert "signal_id" in str(exc_info.value)


class TestSignalTimestampValidation:
    """Test suite for timestamp validation."""

    def test_naive_datetime_converted_to_utc(self):
        """Test that naive datetime is assumed to be UTC."""
        naive_dt = datetime(2025, 1, 15, 10, 30, 0)
        signal = Signal(
            timestamp=naive_dt,
            symbol="BTC_EUR",
            direction="long",
            signal_type="TEST"
        )

        # Naive datetime gets timezone applied - verify with aware_dt
        assert naive_dt.year == 2025
        assert naive_dt.month == 1
        assert naive_dt.day == 15
        assert signal.timestamp == naive_dt.replace(tzinfo=UTC)

    def test_aware_datetime_preserved(self):
        """Test that timezone-aware datetime is preserved."""
        aware_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        signal = Signal(
            timestamp=aware_dt,
            symbol="BTC_EUR",
            direction="long",
            signal_type="TEST"
        )

        assert signal.timestamp == aware_dt


class TestSignalSymbolValidation:
    """Test suite for symbol field validation (renamed from asset)."""

    def test_valid_symbol_formats(self):
        """Test that valid symbol formats are accepted (underscore separator)."""
        valid_symbols = [
            "BTC_EUR",
            "ETH_USDT",
            "BTC_PERP",
            "DOGE_BTC",
            "SOL_USDC",
        ]

        for symbol in valid_symbols:
            signal = Signal(
                timestamp=datetime.now(UTC),
                symbol=symbol,
                direction="long",
                signal_type="TEST"
            )
            assert signal.symbol == symbol

    def test_symbol_too_short_rejected(self):
        """Test that too short symbol is rejected (min 3 chars)."""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                timestamp=datetime.now(UTC),
                symbol="AB",
                direction="long",
                signal_type="TEST"
            )

        assert "symbol" in str(exc_info.value)

    def test_symbol_too_long_rejected(self):
        """Test that too long symbol is rejected."""
        long_symbol = "A" * 25
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                timestamp=datetime.now(UTC),
                symbol=long_symbol,
                direction="long",
                signal_type="TEST"
            )

        assert "symbol" in str(exc_info.value)

    def test_symbol_invalid_format_rejected(self):
        """Test that invalid symbol format is rejected."""
        invalid_symbols = [
            "btc_eur",      # lowercase
            "BTC/EUR",      # slash instead of underscore (OLD format)
            "BTC-EUR",      # dash separator
            "BTC_eur",      # mixed case
            "btc_EUR",      # mixed case
            "123_456",      # starts with number
        ]

        for invalid_symbol in invalid_symbols:
            with pytest.raises(ValidationError):
                Signal(
                    timestamp=datetime.now(UTC),
                    symbol=invalid_symbol,
                    direction="long",
                    signal_type="TEST"
                )


class TestSignalDirectionValidation:
    """Test suite for direction field validation."""

    def test_long_direction_accepted(self):
        """Test that 'long' direction is accepted."""
        signal = Signal(
            timestamp=datetime.now(UTC),
            symbol="BTC_EUR",
            direction="long",
            signal_type="TEST"
        )

        assert signal.direction == "long"

    def test_short_direction_accepted(self):
        """Test that 'short' direction is accepted."""
        signal = Signal(
            timestamp=datetime.now(UTC),
            symbol="BTC_EUR",
            direction="short",
            signal_type="TEST"
        )

        assert signal.direction == "short"

    def test_invalid_direction_rejected(self):
        """Test that invalid direction is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                timestamp=datetime.now(UTC),
                symbol="BTC_EUR",
                direction="neutral",  # type: ignore
                signal_type="TEST"
            )

        assert "direction" in str(exc_info.value)


class TestSignalTypeValidation:
    """Test suite for signal_type field validation."""

    def test_valid_signal_types(self):
        """Test that valid UPPER_SNAKE_CASE signal types are accepted."""
        valid_types = [
            "FVG_ENTRY",
            "EMA_CROSS",
            "WEEKLY_DCA",
            "RSI_OVERSOLD",
            "BREAKOUT",
        ]

        for signal_type in valid_types:
            signal = Signal(
                timestamp=datetime.now(UTC),
                symbol="BTC_EUR",
                direction="long",
                signal_type=signal_type
            )
            assert signal.signal_type == signal_type

    def test_signal_type_too_short_rejected(self):
        """Test that signal_type < 3 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                timestamp=datetime.now(UTC),
                symbol="BTC_EUR",
                direction="long",
                signal_type="AB"
            )

        assert "signal_type" in str(exc_info.value)

    def test_signal_type_too_long_rejected(self):
        """Test that signal_type > 25 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                timestamp=datetime.now(UTC),
                symbol="BTC_EUR",
                direction="long",
                signal_type="A" * 26
            )

        assert "signal_type" in str(exc_info.value)

    def test_signal_type_lowercase_rejected(self):
        """Test that lowercase signal_type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                timestamp=datetime.now(UTC),
                symbol="BTC_EUR",
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
                Signal(
                    timestamp=datetime.now(UTC),
                    symbol="BTC_EUR",
                    direction="long",
                    signal_type=reserved_type
                )

            assert "reserved prefix" in str(exc_info.value).lower()


class TestSignalConfidenceValidation:
    """Test suite for confidence field validation (now Decimal)."""

    def test_confidence_none_by_default(self):
        """Test that confidence is None if not provided."""
        signal = Signal(
            timestamp=datetime.now(UTC),
            symbol="BTC_EUR",
            direction="long",
            signal_type="TEST"
        )

        assert signal.confidence is None

    def test_confidence_is_decimal_type(self):
        """Test that confidence is stored as Decimal for precision."""
        signal = Signal(
            timestamp=datetime.now(UTC),
            symbol="BTC_EUR",
            direction="long",
            signal_type="TEST",
            confidence=Decimal("0.75")
        )

        assert isinstance(signal.confidence, Decimal)
        assert signal.confidence == Decimal("0.75")

    def test_confidence_float_converted_to_decimal(self):
        """Test that float input is converted to Decimal."""
        signal = Signal(
            timestamp=datetime.now(UTC),
            symbol="BTC_EUR",
            direction="long",
            signal_type="TEST",
            confidence=0.85
        )

        # Should be converted to Decimal
        assert isinstance(signal.confidence, Decimal)

    def test_valid_confidence_range(self):
        """Test that confidence values in [0.0, 1.0] are accepted."""
        valid_values = [
            Decimal("0.0"),
            Decimal("0.25"),
            Decimal("0.5"),
            Decimal("0.75"),
            Decimal("1.0")
        ]

        for conf in valid_values:
            signal = Signal(
                timestamp=datetime.now(UTC),
                symbol="BTC_EUR",
                direction="long",
                signal_type="TEST",
                confidence=conf
            )
            assert signal.confidence == conf

    def test_confidence_below_zero_rejected(self):
        """Test that confidence < 0.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                timestamp=datetime.now(UTC),
                symbol="BTC_EUR",
                direction="long",
                signal_type="TEST",
                confidence=Decimal("-0.1")
            )

        assert "confidence" in str(exc_info.value)

    def test_confidence_above_one_rejected(self):
        """Test that confidence > 1.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                timestamp=datetime.now(UTC),
                symbol="BTC_EUR",
                direction="long",
                signal_type="TEST",
                confidence=Decimal("1.1")
            )

        assert "confidence" in str(exc_info.value)


class TestSignalImmutability:
    """Test suite for Signal immutability."""

    def test_signal_is_frozen(self):
        """Test that Signal is immutable after creation."""
        signal = Signal(
            timestamp=datetime.now(UTC),
            symbol="BTC_EUR",
            direction="long",
            signal_type="TEST"
        )

        with pytest.raises(ValidationError):
            signal.direction = "short"  # type: ignore

    def test_no_extra_fields_allowed(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                timestamp=datetime.now(UTC),
                symbol="BTC_EUR",
                direction="long",
                signal_type="TEST",
                extra_field="not allowed"  # type: ignore
            )

        assert "extra_field" in str(exc_info.value).lower()


class TestSignalSerialization:
    """Test suite for Signal JSON serialization."""

    def test_signal_to_json(self):
        """Test Signal serializes to JSON correctly."""
        signal = Signal(
            timestamp=datetime(2025, 12, 1, 14, 30, 0, tzinfo=UTC),
            symbol="BTC_USDT",
            direction="long",
            signal_type="FVG_ENTRY",
            confidence=Decimal("0.85")
        )

        json_data = signal.model_dump(mode='json')

        assert json_data["symbol"] == "BTC_USDT"
        assert json_data["direction"] == "long"
        assert json_data["signal_type"] == "FVG_ENTRY"
        assert "causality" not in json_data  # Pre-causality!
        # Confidence should serialize properly
        assert json_data["confidence"] is not None

    def test_signal_from_json(self):
        """Test Signal deserializes from JSON correctly."""
        json_data = {
            "timestamp": "2025-12-01T14:30:00Z",
            "symbol": "ETH_USDT",
            "direction": "short",
            "signal_type": "REVERSAL",
            "confidence": "0.72"
        }

        signal = Signal.model_validate(json_data)

        assert signal.symbol == "ETH_USDT"
        assert signal.direction == "short"
        assert signal.signal_type == "REVERSAL"
        assert signal.confidence == Decimal("0.72")
