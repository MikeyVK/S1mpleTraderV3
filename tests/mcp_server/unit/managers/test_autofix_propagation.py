# tests/mcp_server/unit/managers/test_autofix_propagation.py
"""
C37 RED: Autofix propagation for text_violations gates (F-14).

Planning C37 / state cycle 38:
  Gate 0 (ruff format) has supports_autofix=true but violations currently
  report fixable=False because _parse_text_violations always hardcodes fixable=False.

  The fix: add fixable_when="gate" to TextViolationsParsing; when set, fixable
  is True iff the gate's supports_autofix=True.

Exit criteria:
  - Gate 0 violations expose fixable=True when gate has supports_autofix=True.
  - Gates without supports_autofix (or supports_autofix=False) still emit fixable=False.
  - Behaviour is config-driven and symmetric with json_violations fixable_when.

RED contract:
  _parse_text_violations always sets fixable=False → assertions fail.
  TextViolationsParsing has no fixable_when field → ValidationError on construction.
"""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from pathlib import Path

from mcp_server.config.quality_config import QualityConfig, TextViolationsParsing
from mcp_server.managers.qa_manager import QAManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUFF_FORMAT_OUTPUT = """\
--- mcp_server/utils/path_resolver.py\t2026-02-27 10:00:00.000000 +0000
+++ mcp_server/utils/path_resolver.py\t2026-02-27 10:00:01.000000 +0000
@@ -1,3 +1,3 @@
-import os
+import os  # formatted
"""

_GATE0_PATTERN = "^--- (?P<file>.+)$"


def _make_manager() -> QAManager:
    return QAManager(workspace_root=Path("D:/dev/SimpleTraderV3"))


# ---------------------------------------------------------------------------
# TextViolationsParsing: fixable_when field must be accepted
# ---------------------------------------------------------------------------


class TestTextViolationsParsingFixableWhen:
    """TextViolationsParsing must accept fixable_when="gate" field."""

    def test_fixable_when_gate_accepted(self) -> None:
        """fixable_when='gate' is a valid TextViolationsParsing field."""
        parsing = TextViolationsParsing(
            pattern=_GATE0_PATTERN,
            severity_default="error",
            fixable_when="gate",
        )
        assert parsing.fixable_when == "gate"

    def test_fixable_when_none_by_default(self) -> None:
        """fixable_when defaults to None (backward compatible)."""
        parsing = TextViolationsParsing(
            pattern=_GATE0_PATTERN,
            severity_default="error",
        )
        assert parsing.fixable_when is None


# ---------------------------------------------------------------------------
# _parse_text_violations: fixable propagation
# ---------------------------------------------------------------------------


class TestParseTextViolationsFixable:
    """_parse_text_violations respects fixable_when="gate" + supports_autofix."""

    def test_fixable_true_when_gate_supports_autofix(self) -> None:
        """When fixable_when='gate' and supports_autofix=True, violations are fixable."""
        manager = _make_manager()
        parsing = TextViolationsParsing(
            pattern=_GATE0_PATTERN,
            severity_default="error",
            fixable_when="gate",
        )

        violations = manager._parse_text_violations(
            _RUFF_FORMAT_OUTPUT,
            parsing,
            supports_autofix=True,
        )

        assert len(violations) == 1
        assert violations[0].fixable is True, (
            "Expected fixable=True for gate with supports_autofix=True and fixable_when='gate'"
        )

    def test_fixable_false_when_gate_does_not_support_autofix(self) -> None:
        """When fixable_when='gate' but supports_autofix=False, violations are not fixable."""
        manager = _make_manager()
        parsing = TextViolationsParsing(
            pattern=_GATE0_PATTERN,
            severity_default="error",
            fixable_when="gate",
        )

        violations = manager._parse_text_violations(
            _RUFF_FORMAT_OUTPUT,
            parsing,
            supports_autofix=False,
        )

        assert len(violations) == 1
        assert violations[0].fixable is False

    def test_fixable_false_without_fixable_when(self) -> None:
        """Without fixable_when, violations are always fixable=False (backward compat)."""
        manager = _make_manager()
        parsing = TextViolationsParsing(
            pattern=_GATE0_PATTERN,
            severity_default="error",
        )

        violations = manager._parse_text_violations(
            _RUFF_FORMAT_OUTPUT,
            parsing,
            supports_autofix=True,
        )

        assert len(violations) == 1
        assert violations[0].fixable is False


# ---------------------------------------------------------------------------
# Integration: Gate 0 config wired end-to-end
# ---------------------------------------------------------------------------


class TestGate0AutofixIntegration:
    """Gate 0 quality.yaml config must produce fixable=True violations after GREEN."""

    def test_gate0_parsing_config_has_fixable_when_gate(self) -> None:
        """Gate 0 text_violations config in quality.yaml includes fixable_when='gate'."""
        config = QualityConfig.load()
        gate0 = config.gates.get("gate0_ruff_format")
        assert gate0 is not None, "gate0_ruff_format must exist in quality.yaml"
        assert gate0.capabilities.text_violations is not None
        assert gate0.capabilities.text_violations.fixable_when == "gate", (
            "Gate 0 text_violations must have fixable_when='gate' to propagate autofix"
        )
