from __future__ import annotations

from mcp_server.managers.qa_manager import QAManager


class TestSkipReasonUnified:
    """Guard: _get_skip_reason was inlined and removed in C31 (Issue #251).

    The skip decision is now inlined: `skip_reason = "Skipped (no matching files)" if not gate_files else None`
    No separate method exists.
    """

    def test_get_skip_reason_is_removed(self) -> None:
        """_get_skip_reason must no longer exist on QAManager (inlined in C31)."""
        assert not hasattr(QAManager, "_get_skip_reason"), (
            "_get_skip_reason still exists; it was inlined in C31 and must be deleted"
        )
