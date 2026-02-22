from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_server.config.quality_config import TextViolationsParsing


class TestTextViolationsParsingRequired:
    """TextViolationsParsing: pattern is required (Issue #251 C5)."""

    def test_missing_pattern_raises_validation_error(self) -> None:
        """TextViolationsParsing without pattern raises ValidationError."""
        with pytest.raises(ValidationError):
            TextViolationsParsing.model_validate({})

    def test_pattern_only_is_valid(self) -> None:
        """TextViolationsParsing with only pattern is valid."""
        model = TextViolationsParsing(pattern=r"(?P<file>.+):(?P<line>\d+): (?P<message>.+)")
        assert model.pattern == r"(?P<file>.+):(?P<line>\d+): (?P<message>.+)"


class TestTextViolationsParsingDefaults:
    """TextViolationsParsing: default field values (Issue #251 C5)."""

    def test_severity_default_is_error(self) -> None:
        """severity_default defaults to 'error'."""
        model = TextViolationsParsing(pattern=r"(?P<message>.+)")
        assert model.severity_default == "error"

    def test_defaults_dict_is_empty_by_default(self) -> None:
        """defaults dict is empty by default."""
        model = TextViolationsParsing(pattern=r"(?P<message>.+)")
        assert model.defaults == {}

    def test_extra_fields_are_forbidden(self) -> None:
        """Extra fields on TextViolationsParsing raise ValidationError."""
        with pytest.raises(ValidationError):
            TextViolationsParsing.model_validate(
                {"pattern": r"(?P<message>.+)", "unknown_field": "value"}
            )


class TestTextViolationsParsingFields:
    """TextViolationsParsing: field assignment (Issue #251 C5)."""

    def test_severity_default_can_be_set(self) -> None:
        """severity_default can be customised."""
        model = TextViolationsParsing(
            pattern=r"(?P<message>.+)",
            severity_default="warning",
        )
        assert model.severity_default == "warning"

    def test_defaults_dict_can_be_set(self) -> None:
        """defaults dict accepts string values."""
        model = TextViolationsParsing(
            pattern=r"(?P<message>.+)",
            defaults={"severity": "error", "rule": "unknown"},
        )
        assert model.defaults["severity"] == "error"
        assert model.defaults["rule"] == "unknown"

    def test_mypy_variant_pattern(self) -> None:
        """Realistic mypy-style pattern parses without error."""
        pattern = r"(?P<file>[^:]+):(?P<line>\d+):\s*(?P<severity>error|warning|note):\s*(?P<message>.+)"
        model = TextViolationsParsing(
            pattern=pattern,
            severity_default="error",
            defaults={"rule": "misc"},
        )
        assert "file" in model.pattern
        assert model.severity_default == "error"

    def test_pylint_variant_pattern(self) -> None:
        """Realistic pylint-style pattern parses without error."""
        pattern = (
            r"(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):"
            r"\s*(?P<severity>[A-Z]):\s*(?P<message>.+)\s*\((?P<rule>[^)]+)\)"
        )
        model = TextViolationsParsing(
            pattern=pattern,
            defaults={"fixable": "false"},
        )
        assert model.defaults.get("fixable") == "false"
