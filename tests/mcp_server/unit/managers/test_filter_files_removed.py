from __future__ import annotations

from mcp_server.managers.qa_manager import QAManager


class TestFilterFilesRemoved:
    """_filter_files must be removed (C16: Remove hardcoded global .py filter)."""

    def test_filter_files_no_longer_exists(self) -> None:
        """_filter_files must not exist on QAManager (hardcoded .py filter removed)."""
        assert not hasattr(QAManager, "_filter_files"), (
            "_filter_files still exists on QAManager — it should be removed in C16"
        )
