from __future__ import annotations

import pytest

from mcp_server.config.quality_config import TextViolationsParsing
from mcp_server.managers.qa_manager import QAManager

# Pattern without a 'rule' group, but with a 'code' group we can use for interpolation
_PATTERN_NO_RULE = r"(?P<file>[^:]+):(?P<line>\d+): (?P<code>\w+) (?P<message>.+)"

# Pattern with all common groups
_FULL_PATTERN = r"(?P<file>[^:]+):(?P<line>\d+): (?P<message>.+)"


class TestParseTextViolationsDefaults:
    """_parse_text_violations: defaults interpolation for absent groups (Issue #251 C12).

    When a named group is absent from the match (or the field has no group at
    all), ``parsing.defaults`` is consulted.  Values can be static strings or
    ``{placeholder}`` references to captured group names.
    """

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager()

    # ------------------------------------------------------------------
    # Static defaults
    # ------------------------------------------------------------------

    def test_static_default_fills_absent_field(self, manager: QAManager) -> None:
        """A static default value is used when the field has no named group."""
        parsing = TextViolationsParsing(
            pattern=_FULL_PATTERN, defaults={"rule": "generic-rule"}
        )
        result = manager._parse_text_violations("a.py:1: some message", parsing)
        assert result[0].rule == "generic-rule"

    def test_static_default_not_used_when_group_matches(self, manager: QAManager) -> None:
        """When the group captures a value, the default is ignored."""
        # _PATTERN_NO_RULE has a 'code' group, not 'rule'.
        # Map 'rule' default only → group 'rule' absent → should use default.
        # But 'message' IS captured → should not use any default.
        parsing = TextViolationsParsing(
            pattern=_FULL_PATTERN, defaults={"message": "fallback-msg"}
        )
        result = manager._parse_text_violations("a.py:5: real message", parsing)
        assert result[0].message == "real message"

    # ------------------------------------------------------------------
    # Interpolated defaults
    # ------------------------------------------------------------------

    def test_interpolated_default_uses_captured_group(self, manager: QAManager) -> None:
        """A {placeholder} default is interpolated using the captured group value."""
        parsing = TextViolationsParsing(
            pattern=_PATTERN_NO_RULE, defaults={"rule": "{code}"}
        )
        result = manager._parse_text_violations("a.py:3: E501 line too long", parsing)
        # 'rule' not in pattern → use defaults["rule"] = "{code}" → "E501"
        assert result[0].rule == "E501"

    def test_multiple_defaults_applied_together(self, manager: QAManager) -> None:
        """Multiple default fields are all applied to the same DTO."""
        parsing = TextViolationsParsing(
            pattern=_FULL_PATTERN,
            defaults={"rule": "fallback", "severity": "warning"},
        )
        result = manager._parse_text_violations("a.py:1: msg", parsing)
        assert result[0].rule == "fallback"
        assert result[0].severity == "warning"
