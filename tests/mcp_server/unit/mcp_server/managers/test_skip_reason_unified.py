from __future__ import annotations

import pytest

from mcp_server.config.quality_config import (
    CapabilitiesMetadata,
    ExecutionConfig,
    ExitCodeParsing,
    QualityGate,
    SuccessCriteria,
)
from mcp_server.managers.qa_manager import QAManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXEC = ExecutionConfig(command=["ruff", "check"], timeout_seconds=10)
_PARSING = ExitCodeParsing(strategy="exit_code")
_SUCCESS = SuccessCriteria(mode="exit_code", exit_codes_ok=[0])


def _static_gate() -> QualityGate:
    return QualityGate(
        name="test-static-gate",
        execution=_EXEC,
        parsing=_PARSING,
        success=_SUCCESS,
        capabilities=CapabilitiesMetadata(file_types=[".py"], supports_autofix=False),
    )


@pytest.fixture()
def manager() -> QAManager:
    return QAManager()


# ---------------------------------------------------------------------------
# Tests: unified skip reason (C18 — remove mode bifurcation)
# ---------------------------------------------------------------------------


class TestSkipReasonUnified:
    """_get_skip_reason must return unified 'Skipped (no matching files)' in all cases.

    After C18, mode-specific skip messages are eliminated:
    - Old: "Skipped (project-level mode - static analysis unavailable)"
    - New: "Skipped (no matching files)" regardless of is_file_specific_mode
    """

    def test_no_files_project_level_returns_unified_skip(self, manager: QAManager) -> None:
        """is_file_specific_mode=False + empty gate_files → 'Skipped (no matching files)'."""
        gate = _static_gate()
        reason = manager._get_skip_reason(gate, [], is_file_specific_mode=False)
        assert reason == "Skipped (no matching files)", (
            f"Expected unified skip reason, got: {reason!r}"
        )

    def test_no_files_file_specific_returns_unified_skip(self, manager: QAManager) -> None:
        """is_file_specific_mode=True + empty gate_files → 'Skipped (no matching files)'."""
        gate = _static_gate()
        reason = manager._get_skip_reason(gate, [], is_file_specific_mode=True)
        assert reason == "Skipped (no matching files)"
