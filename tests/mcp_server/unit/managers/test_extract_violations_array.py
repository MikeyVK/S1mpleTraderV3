from __future__ import annotations

import pytest

from mcp_server.config.quality_config import JsonViolationsParsing, ViolationDTO
from mcp_server.managers.qa_manager import QAManager

_FLAT_MAP: dict[str, str] = {
    "file": "filename",
    "message": "message",
    "line": "line",
    "col": "column",
    "rule": "code",
}


class TestExtractViolationsArray:
    """QAManager._extract_violations_array: resolve nested violations list (Issue #251 C9).

    ``violations_path`` is a dot-separated key path.  ``None`` means the
    root payload itself is the array.  Supports single-level and multi-level paths.
    """

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager()

    # ------------------------------------------------------------------
    # violations_path=None  → root is the list
    # ------------------------------------------------------------------

    def test_none_path_returns_root_list(self, manager: QAManager) -> None:
        """When violations_path is None the root array is returned unchanged."""
        raw: list[dict] = [{"filename": "a.py", "message": "msg"}]
        parsing = JsonViolationsParsing(field_map=_FLAT_MAP)
        result = manager._extract_violations_array(raw, parsing)
        assert result is raw

    def test_none_path_empty_list(self, manager: QAManager) -> None:
        """Empty root list yields empty result."""
        parsing = JsonViolationsParsing(field_map=_FLAT_MAP)
        assert manager._extract_violations_array([], parsing) == []

    # ------------------------------------------------------------------
    # violations_path single-level
    # ------------------------------------------------------------------

    def test_single_key_extracts_nested_array(self, manager: QAManager) -> None:
        """Single-segment path extracts data['generalDiagnostics']."""
        raw = {
            "generalDiagnostics": [
                {"filename": "a.py", "message": "error in a"},
            ],
            "summary": {"errorCount": 1},
        }
        parsing = JsonViolationsParsing(field_map=_FLAT_MAP, violations_path="generalDiagnostics")
        result = manager._extract_violations_array(raw, parsing)
        assert result == raw["generalDiagnostics"]

    def test_single_key_missing_returns_empty_list(self, manager: QAManager) -> None:
        """Missing path key returns empty list (graceful degradation)."""
        raw = {"summary": {}}
        parsing = JsonViolationsParsing(field_map=_FLAT_MAP, violations_path="generalDiagnostics")
        result = manager._extract_violations_array(raw, parsing)
        assert result == []

    # ------------------------------------------------------------------
    # violations_path multi-level
    # ------------------------------------------------------------------

    def test_dotted_path_extracts_deep_array(self, manager: QAManager) -> None:
        """Multi-segment dot path descends into nested dicts."""
        raw = {"result": {"diagnostics": [{"filename": "b.py", "message": "deep"}]}}
        parsing = JsonViolationsParsing(field_map=_FLAT_MAP, violations_path="result.diagnostics")
        result = manager._extract_violations_array(raw, parsing)
        assert result == [{"filename": "b.py", "message": "deep"}]

    def test_dotted_path_partial_missing_returns_empty_list(self, manager: QAManager) -> None:
        """Partial path miss returns empty list."""
        raw = {"result": {}}  # 'diagnostics' key missing
        parsing = JsonViolationsParsing(field_map=_FLAT_MAP, violations_path="result.diagnostics")
        result = manager._extract_violations_array(raw, parsing)
        assert result == []

    # ------------------------------------------------------------------
    # integration: _extract_violations_array feeds _parse_json_violations
    # ------------------------------------------------------------------

    def test_full_pipeline_pyright_style(self, manager: QAManager) -> None:
        """Extracted array flows correctly into _parse_json_violations."""
        raw = {
            "generalDiagnostics": [
                {
                    "filename": "backend/core/enums.py",
                    "message": "Unknown type",
                    "line": 10,
                    "column": 5,
                    "code": "reportMissingImports",
                }
            ]
        }
        parsing = JsonViolationsParsing(field_map=_FLAT_MAP, violations_path="generalDiagnostics")
        array = manager._extract_violations_array(raw, parsing)
        dtos = manager._parse_json_violations(array, parsing)
        assert len(dtos) == 1
        dto = dtos[0]
        assert isinstance(dto, ViolationDTO)
        assert dto.file == "backend/core/enums.py"
        assert dto.line == 10
        assert dto.rule == "reportMissingImports"
