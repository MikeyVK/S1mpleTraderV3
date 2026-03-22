# tests\copilot_orchestration\unit\hooks\test_notify_compaction.py
# template=unit_test version=3d15d309 created=2026-03-22T21:30Z updated=
"""
Unit tests for copilot_orchestration.hooks.notify_compaction.

Tests build_compaction_output: returns systemMessage when sub_role present,
empty dict when absent. Logging tests verify INFO when sub_role found,
DEBUG when no sub_role.

@layer: Tests (Unit)
@dependencies: [pytest, copilot_orchestration.hooks.notify_compaction]
@responsibilities:
    - Test build_compaction_output (sub_role present / absent / falsy)
    - Verify INFO log when sub_role found in state
    - Verify DEBUG log when no sub_role in state
"""

# Standard library
import logging

# Third-party
import pytest

# Project modules
# ImportError here is intentional RED — build_compaction_output does not exist yet.
from copilot_orchestration.hooks.notify_compaction import build_compaction_output

_LOGGER_NAME = "copilot_orchestration.hooks.notify_compaction"


class TestBuildCompactionOutput:
    """Test suite for build_compaction_output."""

    def test_emits_system_message_when_sub_role_present(self) -> None:
        """Returns systemMessage dict when state contains a sub_role."""
        result = build_compaction_output({"sub_role": "implementer"})
        assert "systemMessage" in result
        assert "implementer" in result["systemMessage"]

    def test_emits_empty_when_no_sub_role_key(self) -> None:
        """Returns empty dict when state has no sub_role key."""
        result = build_compaction_output({})
        assert result == {}

    def test_emits_empty_when_sub_role_falsy(self) -> None:
        """Returns empty dict when sub_role is empty string."""
        result = build_compaction_output({"sub_role": ""})
        assert result == {}

    def test_logs_info_when_sub_role_present(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """build_compaction_output logs at INFO when sub_role is found."""
        with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
            build_compaction_output({"sub_role": "implementer"})
        assert any(r.levelno == logging.INFO for r in caplog.records)

    def test_logs_debug_when_no_sub_role(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """build_compaction_output logs at DEBUG when no sub_role in state."""
        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            build_compaction_output({})
        assert any(r.levelno == logging.DEBUG for r in caplog.records)
