"""Tests for JsonViolationsParsing Pydantic model (Issue #251 C2).

Validates model acceptance of field_map, violations_path, line_offset,
and fixable_when — covering both ruff and pyright schema variants.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_server.config.quality_config import JsonViolationsParsing


class TestJsonViolationsParsingRequired:
    """Test JsonViolationsParsing construction with required field only."""

    def test_field_map_only(self) -> None:
        """Model accepts field_map as sole required field."""
        model = JsonViolationsParsing(field_map={"file": "filename", "message": "message"})
        assert model.field_map == {"file": "filename", "message": "message"}

    def test_field_map_missing_raises(self) -> None:
        """Model raises ValidationError when field_map is absent."""
        with pytest.raises(ValidationError):
            JsonViolationsParsing()  # type: ignore[call-arg]


class TestJsonViolationsParsingDefaults:
    """Test default values for optional fields."""

    def test_violations_path_defaults_to_none(self) -> None:
        model = JsonViolationsParsing(field_map={"file": "f"})
        assert model.violations_path is None

    def test_line_offset_defaults_to_zero(self) -> None:
        model = JsonViolationsParsing(field_map={"file": "f"})
        assert model.line_offset == 0

    def test_fixable_when_defaults_to_none(self) -> None:
        model = JsonViolationsParsing(field_map={"file": "f"})
        assert model.fixable_when is None


class TestJsonViolationsParsingRuffVariant:
    """Validate the ruff check schema: root-level array, no offset."""

    def test_ruff_schema(self) -> None:
        model = JsonViolationsParsing(
            field_map={
                "file": "filename",
                "line": "location/row",
                "col": "location/column",
                "rule": "code",
                "message": "message",
            },
            fixable_when="fix/applicability",
        )
        assert model.violations_path is None
        assert model.line_offset == 0
        assert model.fixable_when == "fix/applicability"
        assert model.field_map["file"] == "filename"


class TestJsonViolationsParsingPyrightVariant:
    """Validate the pyright schema: nested array, 0-based line offset."""

    def test_pyright_schema(self) -> None:
        model = JsonViolationsParsing(
            field_map={
                "file": "file",
                "line": "range/start/line",
                "col": "range/start/character",
                "rule": "rule",
                "message": "message",
                "severity": "severity",
            },
            violations_path="generalDiagnostics",
            line_offset=1,
        )
        assert model.violations_path == "generalDiagnostics"
        assert model.line_offset == 1
        assert model.fixable_when is None
        assert model.field_map["line"] == "range/start/line"
