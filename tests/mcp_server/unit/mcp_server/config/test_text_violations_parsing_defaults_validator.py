from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_server.config.quality_config import TextViolationsParsing


class TestDefaultsPlaceholderValidation:
    """TextViolationsParsing: {placeholder} in defaults must reference a named group (C6).

    When a defaults value contains a ``{name}`` interpolation token, that
    ``name`` must exist as a named capture group in ``pattern``. Unknown
    placeholders are rejected with a descriptive ValidationError.
    """

    def test_unknown_placeholder_raises_validation_error(self) -> None:
        """{group} in defaults that is absent from pattern raises ValidationError."""
        with pytest.raises(ValidationError, match="unknown_group"):
            TextViolationsParsing(
                pattern=r"(?P<file>.+):(?P<line>\d+): (?P<message>.+)",
                defaults={"rule": "{unknown_group}"},
            )

    def test_known_placeholder_is_valid(self) -> None:
        """{file} in defaults when 'file' is a named group is valid."""
        model = TextViolationsParsing(
            pattern=r"(?P<file>.+):(?P<line>\d+): (?P<message>.+)",
            defaults={"display": "{file}"},
        )
        assert model.defaults["display"] == "{file}"

    def test_multiple_unknown_placeholders_raises(self) -> None:
        """Multiple {unknown} tokens raise ValidationError listing all offenders."""
        with pytest.raises(ValidationError):
            TextViolationsParsing(
                pattern=r"(?P<message>.+)",
                defaults={
                    "rule": "{no_such_group}",
                    "severity": "{also_missing}",
                },
            )

    def test_static_value_without_braces_is_always_valid(self) -> None:
        """Static string values (no {}) are always accepted regardless of pattern."""
        model = TextViolationsParsing(
            pattern=r"(?P<message>.+)",
            defaults={"rule": "misc", "severity": "error"},
        )
        assert model.defaults["rule"] == "misc"

    def test_mixed_valid_and_invalid_placeholder_raises(self) -> None:
        """One valid + one invalid {placeholder} still raises ValidationError."""
        with pytest.raises(ValidationError, match="bad_group"):
            TextViolationsParsing(
                pattern=r"(?P<file>.+):(?P<line>\d+): (?P<message>.+)",
                defaults={
                    "display": "{file}",       # valid — 'file' in pattern
                    "rule": "{bad_group}",      # invalid — 'bad_group' not in pattern
                },
            )

    def test_no_defaults_is_always_valid(self) -> None:
        """Empty defaults dict skips placeholder validation."""
        model = TextViolationsParsing(
            pattern=r"(?P<message>.+)",
            defaults={},
        )
        assert model.defaults == {}
