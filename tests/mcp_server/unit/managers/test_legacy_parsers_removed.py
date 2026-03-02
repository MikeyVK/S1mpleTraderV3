from __future__ import annotations

import mcp_server.config.quality_config as quality_config_module
from mcp_server.managers.qa_manager import QAManager


class TestLegacyParsersRemoved:
    """Guard tests: legacy parser methods must not exist on QAManager (Issue #251 C14).

    These tests FAIL while the legacy methods are still present and pass after removal.
    """

    def test_parse_ruff_json_is_removed(self) -> None:
        """_parse_ruff_json must no longer exist on QAManager."""
        assert not hasattr(QAManager, "_parse_ruff_json"), (
            "_parse_ruff_json still exists; it has no callers and must be deleted"
        )

    def test_parse_json_field_issues_is_removed(self) -> None:
        """_parse_json_field_issues must no longer exist on QAManager."""
        assert not hasattr(QAManager, "_parse_json_field_issues"), (
            "_parse_json_field_issues still exists; issue parsing now routes via "
            "capabilities.parsing_strategy in _execute_gate"
        )

    def test_extract_json_fields_is_removed(self) -> None:
        """_extract_json_fields must no longer exist on QAManager."""
        assert not hasattr(QAManager, "_extract_json_fields"), (
            "_extract_json_fields still exists; json_field parsing strategy "
            "has been removed — use capabilities.parsing_strategy instead"
        )

    def test_get_skip_reason_is_removed(self) -> None:
        """_get_skip_reason must no longer exist on QAManager (inlined in C31)."""
        assert not hasattr(QAManager, "_get_skip_reason"), (
            "_get_skip_reason still exists; it was inlined in C31 and must be deleted"
        )

    def test_exit_code_parsing_is_removed(self) -> None:
        """ExitCodeParsing must no longer exist in quality_config (removed in C31)."""
        assert not hasattr(quality_config_module, "ExitCodeParsing"), (
            "ExitCodeParsing still exists; only JsonViolationsParsing and "
            "TextViolationsParsing are the two valid parsing strategy types"
        )
