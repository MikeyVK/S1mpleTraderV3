"""Tests for ViolationDTO dataclass (Issue #251 C1).

Validates object creation, field defaults, and required field enforcement
for the uniform violation contract returned by all gate parsers.
"""

from __future__ import annotations

import pytest

from mcp_server.config.quality_config import ViolationDTO


class TestViolationDTOCreation:
    """Test ViolationDTO construction with required and optional fields."""

    def test_required_fields_only(self) -> None:
        """Create DTO with only the two required fields."""
        dto = ViolationDTO(file="mcp_server/foo.py", message="Missing return type")
        assert dto.file == "mcp_server/foo.py"
        assert dto.message == "Missing return type"

    def test_all_fields_explicit(self) -> None:
        """Create DTO with all fields set to non-default values."""
        dto = ViolationDTO(
            file="mcp_server/foo.py",
            message="Missing return type",
            line=42,
            col=1,
            rule="ANN201",
            fixable=True,
            severity="warning",
        )
        assert dto.file == "mcp_server/foo.py"
        assert dto.message == "Missing return type"
        assert dto.line == 42
        assert dto.col == 1
        assert dto.rule == "ANN201"
        assert dto.fixable is True
        assert dto.severity == "warning"


class TestViolationDTODefaults:
    """Test that optional fields default to the correct sentinel values."""

    def test_line_defaults_to_none(self) -> None:
        dto = ViolationDTO(file="f.py", message="m")
        assert dto.line is None

    def test_col_defaults_to_none(self) -> None:
        dto = ViolationDTO(file="f.py", message="m")
        assert dto.col is None

    def test_rule_defaults_to_none(self) -> None:
        dto = ViolationDTO(file="f.py", message="m")
        assert dto.rule is None

    def test_fixable_defaults_to_false(self) -> None:
        dto = ViolationDTO(file="f.py", message="m")
        assert dto.fixable is False

    def test_severity_defaults_to_error(self) -> None:
        dto = ViolationDTO(file="f.py", message="m")
        assert dto.severity == "error"
