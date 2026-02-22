from __future__ import annotations

import pytest

from mcp_server.config.quality_config import JsonViolationsParsing, ViolationDTO
from mcp_server.managers.qa_manager import QAManager


class TestParseJsonViolationsNestedPaths:
    """_parse_json_violations: nested field extraction via '/' paths (Issue #251 C8).

    When a field_map value contains '/', each segment is used to descend into
    the nested JSON object.  E.g. ``"location/row"`` maps to
    ``item["location"]["row"]``.
    """

    _RUFF_FIELD_MAP: dict[str, str] = {
        "file": "filename",
        "message": "message",
        "line": "location/row",
        "col": "location/column",
        "rule": "code",
        "fixable": "fix",
    }

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager()

    @pytest.fixture
    def nested_parsing(self) -> JsonViolationsParsing:
        return JsonViolationsParsing(field_map=self._RUFF_FIELD_MAP)

    def test_nested_path_extracts_line_and_col(
        self, manager: QAManager, nested_parsing: JsonViolationsParsing
    ) -> None:
        """'location/row' and 'location/column' are resolved via nested lookup."""
        payload = [
            {
                "code": "E501",
                "message": "Line too long (104 > 100)",
                "location": {"row": 12, "column": 101},
                "fix": None,
                "filename": "backend/core/enums.py",
            }
        ]
        result = manager._parse_json_violations(payload, nested_parsing)
        assert len(result) == 1
        dto = result[0]
        assert isinstance(dto, ViolationDTO)
        assert dto.line == 12
        assert dto.col == 101

    def test_nested_path_missing_parent_returns_none(
        self, manager: QAManager, nested_parsing: JsonViolationsParsing
    ) -> None:
        """If the parent key is absent, the field should be None."""
        payload = [{"filename": "a.py", "message": "msg", "code": "W001"}]
        result = manager._parse_json_violations(payload, nested_parsing)
        # 'location' key absent → line and col should both be None
        assert result[0].line is None
        assert result[0].col is None

    def test_nested_path_missing_leaf_returns_none(
        self, manager: QAManager, nested_parsing: JsonViolationsParsing
    ) -> None:
        """If the leaf key is absent inside the parent dict, field should be None."""
        payload = [
            {
                "filename": "a.py",
                "message": "msg",
                "location": {"row": 5},  # 'column' key missing
            }
        ]
        result = manager._parse_json_violations(payload, nested_parsing)
        assert result[0].line == 5
        assert result[0].col is None

    def test_nested_path_three_segments(
        self, manager: QAManager
    ) -> None:
        """Three-level nested path 'a/b/c' resolves item['a']['b']['c']."""
        parsing = JsonViolationsParsing(field_map={"line": "outer/inner/value"})
        payload = [{"outer": {"inner": {"value": 99}}}]
        result = manager._parse_json_violations(payload, parsing)
        assert result[0].line == 99

    def test_flat_and_nested_paths_coexist(
        self, manager: QAManager, nested_parsing: JsonViolationsParsing
    ) -> None:
        """file (flat) and line (nested) can coexist in the same field_map."""
        payload = [
            {
                "filename": "combo.py",
                "message": "test",
                "location": {"row": 7, "column": 42},
                "code": "E302",
                "fix": {"applicability": "safe"},
            }
        ]
        result = manager._parse_json_violations(payload, nested_parsing)
        dto = result[0]
        assert dto.file == "combo.py"
        assert dto.line == 7
        assert dto.col == 42
        assert dto.rule == "E302"
        assert dto.fixable is True
