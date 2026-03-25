# tests\copilot_orchestration\unit\hooks\test_notify_compaction.py
# template=unit_test version=3d15d309 created=2026-03-22T21:30Z updated=
"""
Unit tests for copilot_orchestration.hooks.notify_compaction.

Tests build_compaction_output: returns systemMessage when sub_role present,
empty dict when absent. Logging tests verify INFO when sub_role found,
DEBUG when no sub_role. Crosschat block injection verified for enforcing loader.

@layer: Tests (Unit)
@dependencies: [pytest, copilot_orchestration.hooks.notify_compaction]
@responsibilities:
    - Test build_compaction_output (sub_role present / absent / falsy)
    - Verify INFO log when sub_role found in state
    - Verify DEBUG log when no sub_role in state
    - Verify canonical instruction injected when requires_crosschat_block=True
    - Verify base-only message when requires_crosschat_block=False
"""

# Standard library
import logging

# Third-party
import pytest

# Project modules
from copilot_orchestration.contracts.interfaces import SubRoleSpec
from copilot_orchestration.hooks.notify_compaction import build_compaction_output

_LOGGER_NAME = "copilot_orchestration.hooks.notify_compaction"

_SPEC_STUB = SubRoleSpec(
    requires_crosschat_block=True,
    heading="### Hand-Over",
    block_template=(
        "[{sub_role}] End your response with this block:\n\n"
        "```text\n@next: take over.\nUse the guide.\n\n"
        "{markers_list}\n```"
    ),
    markers=["Task:", "Files:"],
    description="",
)


class _NonEnforcingLoader:
    """Stub loader where no sub-role requires a crosschat block."""

    def requires_crosschat_block(self, role: str, sub_role: str) -> bool:  # noqa: ARG002
        return False

    def get_requirement(self, role: str, sub_role: str) -> SubRoleSpec:  # noqa: ARG002
        return _SPEC_STUB


class _EnforcingLoader:
    """Stub loader where all sub-roles require a crosschat block."""

    def requires_crosschat_block(self, role: str, sub_role: str) -> bool:  # noqa: ARG002
        return True

    def get_requirement(self, role: str, sub_role: str) -> SubRoleSpec:  # noqa: ARG002
        return _SPEC_STUB


class TestBuildCompactionOutput:
    """Test suite for build_compaction_output."""

    def test_emits_system_message_when_sub_role_present(self) -> None:
        """Returns systemMessage dict when state contains a sub_role."""
        result = build_compaction_output({"sub_role": "implementer"}, _NonEnforcingLoader(), "imp")
        assert "systemMessage" in result
        msg = result["systemMessage"]  # type: ignore[index]
        assert isinstance(msg, str)
        assert "implementer" in msg

    def test_emits_empty_when_no_sub_role_key(self) -> None:
        """Returns empty dict when state has no sub_role key."""
        result = build_compaction_output({}, _NonEnforcingLoader(), "imp")
        assert result == {}

    def test_emits_empty_when_sub_role_falsy(self) -> None:
        """Returns empty dict when sub_role is empty string."""
        result = build_compaction_output({"sub_role": ""}, _NonEnforcingLoader(), "imp")
        assert result == {}

    def test_non_enforced_sub_role_returns_base_message_only(self) -> None:
        """Non-enforced sub-role returns base compaction message without block instruction."""
        result = build_compaction_output({"sub_role": "researcher"}, _NonEnforcingLoader(), "imp")
        msg = result["systemMessage"]  # type: ignore[index]
        assert isinstance(msg, str)
        assert "researcher" in msg
        assert "```text" not in msg

    def test_enforced_sub_role_injects_canonical_instruction(self) -> None:
        """Enforced sub-role appends the canonical crosschat block instruction."""
        result = build_compaction_output({"sub_role": "implementer"}, _EnforcingLoader(), "imp")
        msg = result["systemMessage"]  # type: ignore[index]
        assert isinstance(msg, str)
        assert "implementer" in msg
        assert "```text" in msg
        assert "Task:" in msg
        assert "Files:" in msg

    def test_enforced_sub_role_uses_double_newline_separator(self) -> None:
        """Canonical instruction is separated from base by double newline (not space)."""
        result = build_compaction_output({"sub_role": "implementer"}, _EnforcingLoader(), "imp")
        msg = result["systemMessage"]  # type: ignore[index]
        assert isinstance(msg, str)
        # The base ends with "." and the instruction starts with "[implementer]"
        assert "\n\n[implementer]" in msg

    def test_logs_info_when_sub_role_present(self, caplog: pytest.LogCaptureFixture) -> None:
        """build_compaction_output logs at INFO when sub_role is found."""
        with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
            build_compaction_output({"sub_role": "implementer"}, _EnforcingLoader(), "imp")
        assert any(r.levelno == logging.INFO for r in caplog.records)

    def test_logs_debug_when_no_sub_role(self, caplog: pytest.LogCaptureFixture) -> None:
        """build_compaction_output logs at DEBUG when no sub_role in state."""
        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            build_compaction_output({}, _NonEnforcingLoader(), "imp")
        assert any(r.levelno == logging.DEBUG for r in caplog.records)
