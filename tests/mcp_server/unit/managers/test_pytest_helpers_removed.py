from __future__ import annotations

from mcp_server.managers.qa_manager import QAManager


class TestPytestHelpersRemoved:
    """Pytest-specific helper methods must be removed (C17: Remove dead pytest helpers)."""

    def test_supports_pytest_json_report_no_longer_exists(self) -> None:
        """_supports_pytest_json_report must not exist on QAManager."""
        assert not hasattr(QAManager, "_supports_pytest_json_report"), (
            "_supports_pytest_json_report still exists — should be removed in C17"
        )

    def test_maybe_enable_pytest_json_report_no_longer_exists(self) -> None:
        """_maybe_enable_pytest_json_report must not exist on QAManager."""
        assert not hasattr(QAManager, "_maybe_enable_pytest_json_report"), (
            "_maybe_enable_pytest_json_report still exists — should be removed in C17"
        )
