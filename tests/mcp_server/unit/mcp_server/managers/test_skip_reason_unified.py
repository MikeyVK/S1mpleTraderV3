from __future__ import annotations

import pytest

from mcp_server.managers.qa_manager import QAManager


@pytest.fixture()
def manager() -> QAManager:
    return QAManager()


# ---------------------------------------------------------------------------
# Tests: unified skip reason (C17/C18 — remove mode bifurcation)
# ---------------------------------------------------------------------------


class TestSkipReasonUnified:
    """_get_skip_reason returns 'Skipped (no matching files)' when files list is empty.

    After C17/C18, mode-specific logic and is_file_specific_mode parameter are removed.
    The skip decision is purely capability-driven: no files → skip.
    """

    def test_no_files_returns_skip_reason(self, manager: QAManager) -> None:
        """Empty gate_files → 'Skipped (no matching files)' always."""
        reason = manager._get_skip_reason([])
        assert reason == "Skipped (no matching files)", (
            f"Expected unified skip reason, got: {reason!r}"
        )

    def test_with_files_returns_none(self, manager: QAManager) -> None:
        """Non-empty gate_files → None (gate should run)."""
        reason = manager._get_skip_reason(["mcp_server/foo.py"])
        assert reason is None
