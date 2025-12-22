# tests/unit/dtos/strategy/test_phasespec.py
"""
Unit tests for PhaseSpec DTO.

Tests the PhaseSpec contract according to TDD principles.
Comprehensive coverage: creation, validation, immutability, edge cases.

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, mcp_server.state.project]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives

# Standard library
from datetime import datetime, timezone
from decimal import Decimal

# Third-party
import pytest
from pydantic import ValidationError

# Module under test
from mcp_server.state.project import PhaseSpec


class TestPhaseSpecCreation:
    """Tests for PhaseSpec creation and defaults."""

    def test_creation_with_required_fields(self) -> None:
        """Test PhaseSpec can be created with only required fields."""
        dto = PhaseSpec()
        assert dto is not None

    def test_creation_with_all_fields(self) -> None:
        """Test PhaseSpec can be created with all fields."""
        dto = PhaseSpec(
            phase_id=,
            title=,
            depends_on=,
            blocks=,
            labels=,
        )
        assert dto is not None
        assert getattr(dto, "phase_id") == 
        assert getattr(dto, "title") == 
        assert getattr(dto, "depends_on") == 
        assert getattr(dto, "blocks") == 
        assert getattr(dto, "labels") == 

    def test_id_auto_generation(self) -> None:
        """Test phasespec_id is auto-generated if not provided."""
        dto = PhaseSpec()
        dto_id = getattr(dto, "phasespec_id")
        assert dto_id.startswith("PHA_")

    def test_custom_id_accepted(self) -> None:
        """Test custom phasespec_id is accepted when valid."""
        custom_id = "PHA_20250101_120000_abc123"
        dto = PhaseSpec(
            phasespec_id=custom_id,
        )
        assert getattr(dto, "phasespec_id") == custom_id


class TestPhaseSpecIDValidation:
    """Tests for phasespec_id validation."""

    def test_valid_id_format_accepted(self) -> None:
        """Test valid PHA_YYYYMMDD_HHMMSS_hash format is accepted."""
        valid_id = "PHA_20250115_143052_a1b2c3"
        dto = PhaseSpec(
            phasespec_id=valid_id,
        )
        assert getattr(dto, "phasespec_id") == valid_id

    def test_invalid_prefix_rejected(self) -> None:
        """Test ID with wrong prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseSpec(
                phasespec_id="WRONG_20250101_120000_abc123",
            )
        assert "phasespec_id" in str(exc_info.value)

    def test_malformed_id_rejected(self) -> None:
        """Test malformed ID format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseSpec(
                phasespec_id="invalid-format",
            )
        assert "phasespec_id" in str(exc_info.value)


class TestPhaseSpecImmutability:
    """Tests for PhaseSpec immutability (frozen=True)."""

    def test_fields_cannot_be_modified(self) -> None:
        """Test that PhaseSpec fields cannot be changed after creation."""
        dto = PhaseSpec()
        with pytest.raises(ValidationError):
            dto.phasespec_id = "PHA_20250101_999999_new123"

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseSpec(
                nonexistent_field="should_fail",
            )
        assert "extra" in str(exc_info.value).lower()


class TestPhaseSpecEdgeCases:
    """Tests for PhaseSpec edge cases and serialization."""

    def test_all_optional_fields_none(self) -> None:
        """Test PhaseSpec with all optional fields as None."""
        dto = PhaseSpec(
        )
        assert getattr(dto, "phase_id") is None
        assert getattr(dto, "title") is None
        assert getattr(dto, "depends_on") is None
        assert getattr(dto, "blocks") is None
        assert getattr(dto, "labels") is None

    def test_roundtrip_serialization(self) -> None:
        """Test PhaseSpec can be serialized and deserialized."""
        dto = PhaseSpec(
            phase_id=,
            title=,
            depends_on=,
            blocks=,
            labels=,
        )
        json_data = dto.model_dump_json()
        restored = PhaseSpec.model_validate_json(json_data)
        assert restored == dto

    def test_json_schema_examples_valid(self) -> None:
        """Test that json_schema_extra examples are valid PhaseSpec instances."""
        schema = PhaseSpec.model_json_schema()
        examples = schema.get("examples", [])
        # Examples should exist per coding standards
        assert len(examples) >= 1, "At least one example required"
