# tests/unit/dtos/shared/test_disposition_envelope.py
"""
Unit tests for DispositionEnvelope DTO.

Tests the worker output flow control contract according to TDD principles:
- CONTINUE: Default disposition, no additional fields required
- PUBLISH: Requires event_name and event_payload
- STOP: Flow termination signal, no additional fields required

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, backend.dtos.shared.disposition_envelope]
"""

# Third-Party Imports
import pytest
from pydantic import BaseModel, ValidationError

# Our Application Imports
from backend.dtos.shared.disposition_envelope import DispositionEnvelope


class MockSystemDTO(BaseModel):
    """Mock System DTO for testing event payloads."""
    value: float
    description: str


class TestDispositionEnvelopeContinue:
    """Test suite for CONTINUE disposition."""

    def test_continue_default_disposition(self):
        """Test that CONTINUE is the default disposition."""
        envelope = DispositionEnvelope()
        assert envelope.disposition == "CONTINUE"
        assert envelope.event_name is None
        assert envelope.event_payload is None

    def test_continue_explicit(self):
        """Test explicit CONTINUE disposition."""
        envelope = DispositionEnvelope(disposition="CONTINUE")
        assert envelope.disposition == "CONTINUE"
        assert envelope.event_name is None
        assert envelope.event_payload is None

    def test_continue_ignores_extra_fields(self):
        """Test that CONTINUE ignores event_name and event_payload if provided."""
        # This should NOT raise an error (fields are optional for CONTINUE)
        envelope = DispositionEnvelope(
            disposition="CONTINUE",
            event_name="IGNORED",
            event_payload=MockSystemDTO(value=1.0, description="test")
        )
        assert envelope.disposition == "CONTINUE"


class TestDispositionEnvelopePublish:
    """Test suite for PUBLISH disposition."""

    def test_publish_requires_event_name(self):
        """Test that PUBLISH disposition requires event_name."""
        with pytest.raises(ValidationError) as exc_info:
            DispositionEnvelope(
                disposition="PUBLISH",
                event_payload=MockSystemDTO(value=1.0, description="test")
            )

        assert "event_name is required" in str(exc_info.value)

    def test_publish_allows_no_payload(self):
        """Test that PUBLISH disposition works without payload (pure signal)."""
        # Pure signal events don't need payload
        envelope = DispositionEnvelope(
            disposition="PUBLISH",
            event_name="EMERGENCY_HALT"
        )

        assert envelope.disposition == "PUBLISH"
        assert envelope.event_name == "EMERGENCY_HALT"
        assert envelope.event_payload is None

    def test_publish_with_valid_payload(self):
        """Test PUBLISH disposition with valid event_name and event_payload."""
        payload = MockSystemDTO(value=42.0, description="Test signal")
        envelope = DispositionEnvelope(
            disposition="PUBLISH",
            event_name="SIGNAL_GENERATED",
            event_payload=payload
        )

        assert envelope.disposition == "PUBLISH"
        assert envelope.event_name == "SIGNAL_GENERATED"
        assert envelope.event_payload == payload
        # Verify payload content (cast to avoid Pylance FieldInfo warning)
        assert payload.value == 42.0

    def test_publish_payload_type_validation(self):
        """Test that event_payload validates against BaseModel type hint."""
        # Pydantic will accept various types and try to coerce them
        # We test that valid BaseModel instances work correctly
        payload = MockSystemDTO(value=42.0, description="Valid DTO")
        envelope = DispositionEnvelope(
            disposition="PUBLISH",
            event_name="TEST_EVENT",
            event_payload=payload
        )
        assert isinstance(envelope.event_payload, BaseModel)
        assert envelope.event_payload == payload


class TestDispositionEnvelopeStop:
    """Test suite for STOP disposition."""

    def test_stop_explicit(self):
        """Test explicit STOP disposition."""
        envelope = DispositionEnvelope(disposition="STOP")
        assert envelope.disposition == "STOP"
        assert envelope.event_name is None
        assert envelope.event_payload is None

    def test_stop_ignores_extra_fields(self):
        """Test that STOP ignores event_name and event_payload if provided."""
        envelope = DispositionEnvelope(
            disposition="STOP",
            event_name="IGNORED",
            event_payload=MockSystemDTO(value=1.0, description="test")
        )
        assert envelope.disposition == "STOP"


class TestDispositionEnvelopeImmutability:
    """Test suite for envelope immutability."""

    def test_envelope_is_frozen(self):
        """Test that DispositionEnvelope is immutable after creation."""
        envelope = DispositionEnvelope(disposition="CONTINUE")

        with pytest.raises(ValidationError):
            envelope.disposition = "PUBLISH"  # type: ignore

    def test_no_extra_fields_allowed(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            DispositionEnvelope(
                disposition="CONTINUE",
                extra_field="not_allowed"  # type: ignore
            )

        assert "extra_field" in str(exc_info.value).lower()


class TestDispositionEnvelopeInvalidDisposition:
    """Test suite for invalid disposition values."""

    def test_invalid_disposition_rejected(self):
        """Test that invalid disposition values are rejected."""
        with pytest.raises(ValidationError):
            DispositionEnvelope(disposition="INVALID")  # type: ignore


class TestDispositionEnvelopeEventNameValidation:
    """Test suite for event name validation."""

    def test_event_name_must_be_upper_snake_case(self):
        """Test that event names must follow UPPER_SNAKE_CASE convention."""
        # Valid names
        valid_names = [
            "SIGNAL_GENERATED",
            "EMERGENCY_HALT",
            "POSITION_OPENED",
            "WEEKLY_DCA_TICK",
            "DATA_VALIDATED",
        ]

        for name in valid_names:
            envelope = DispositionEnvelope(
                disposition="PUBLISH",
                event_name=name
            )
            assert envelope.event_name == name

    def test_event_name_rejects_lowercase(self):
        """Test that lowercase event names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DispositionEnvelope(
                disposition="PUBLISH",
                event_name="signal_generated"
            )

        assert "UPPER_SNAKE_CASE" in str(exc_info.value)

    def test_event_name_rejects_camel_case(self):
        """Test that camelCase event names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DispositionEnvelope(
                disposition="PUBLISH",
                event_name="signalGenerated"
            )

        assert "UPPER_SNAKE_CASE" in str(exc_info.value)

    def test_event_name_rejects_kebab_case(self):
        """Test that kebab-case event names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DispositionEnvelope(
                disposition="PUBLISH",
                event_name="SIGNAL-GENERATED"
            )

        assert "UPPER_SNAKE_CASE" in str(exc_info.value)

    def test_event_name_rejects_reserved_system_prefix(self):
        """Test that SYSTEM_ prefix is reserved."""
        with pytest.raises(ValidationError) as exc_info:
            DispositionEnvelope(
                disposition="PUBLISH",
                event_name="SYSTEM_OVERRIDE"
            )

        assert "reserved prefix" in str(exc_info.value).lower()

    def test_event_name_rejects_reserved_internal_prefix(self):
        """Test that INTERNAL_ prefix is reserved."""
        with pytest.raises(ValidationError) as exc_info:
            DispositionEnvelope(
                disposition="PUBLISH",
                event_name="INTERNAL_EVENT"
            )

        assert "reserved prefix" in str(exc_info.value).lower()

    def test_event_name_rejects_underscore_prefix(self):
        """Test that _ prefix is reserved."""
        with pytest.raises(ValidationError) as exc_info:
            DispositionEnvelope(
                disposition="PUBLISH",
                event_name="_PRIVATE_EVENT"
            )

        assert "reserved prefix" in str(exc_info.value).lower()

    def test_event_name_rejects_too_long(self):
        """Test that event names cannot exceed 100 characters."""
        long_name = "A" * 101

        with pytest.raises(ValidationError) as exc_info:
            DispositionEnvelope(
                disposition="PUBLISH",
                event_name=long_name
            )

        assert "100" in str(exc_info.value)

    def test_event_name_minimum_length(self):
        """Test that event names must be at least 3 characters."""
        with pytest.raises(ValidationError) as exc_info:
            DispositionEnvelope(
                disposition="PUBLISH",
                event_name="AB"
            )

        assert "at least 3 characters" in str(exc_info.value).lower()
