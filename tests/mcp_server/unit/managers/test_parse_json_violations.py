from __future__ import annotations

import pytest

from mcp_server.config.quality_config import JsonViolationsParsing, ViolationDTO
from mcp_server.managers.qa_manager import QAManager


class TestParseJsonViolationsRootArray:
    """_parse_json_violations: happy path for root-array JSON (Issue #251 C7).

    Uses flat key lookup only.  Nested path extraction (C8) is tested separately.
    """

    _FLAT_FIELD_MAP: dict[str, str] = {
        "file": "filename",
        "message": "message",
        "line": "line",
        "col": "column",
        "rule": "code",
        "fixable": "fix",
    }

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager()

    @pytest.fixture
    def flat_parsing(self) -> JsonViolationsParsing:
        return JsonViolationsParsing(field_map=self._FLAT_FIELD_MAP)

    def test_single_violation_maps_to_dto(
        self, manager: QAManager, flat_parsing: JsonViolationsParsing
    ) -> None:
        """Root-array with one entry maps to one ViolationDTO."""
        payload = [
            {
                "code": "E501",
                "message": "Line too long (104 > 100)",
                "line": 12,
                "column": 101,
                "fix": None,
                "filename": "backend/core/enums.py",
            }
        ]
        result = manager._parse_json_violations(payload, flat_parsing)
        assert len(result) == 1
        dto = result[0]
        assert isinstance(dto, ViolationDTO)
        assert dto.file == "backend/core/enums.py"
        assert dto.message == "Line too long (104 > 100)"
        assert dto.line == 12
        assert dto.col == 101
        assert dto.rule == "E501"

    def test_empty_array_returns_empty_list(
        self, manager: QAManager, flat_parsing: JsonViolationsParsing
    ) -> None:
        """Empty root array produces empty result list."""
        result = manager._parse_json_violations([], flat_parsing)
        assert result == []

    def test_multiple_violations(
        self, manager: QAManager, flat_parsing: JsonViolationsParsing
    ) -> None:
        """Multiple entries in root array each map to a ViolationDTO."""
        payload = [
            {
                "code": "E501",
                "message": "Line too long",
                "line": 5,
                "column": 101,
                "fix": None,
                "filename": "a.py",
            },
            {
                "code": "F401",
                "message": "Unused import",
                "line": 1,
                "column": 1,
                "fix": {"applicability": "safe", "edits": []},
                "filename": "b.py",
            },
        ]
        result = manager._parse_json_violations(payload, flat_parsing)
        assert len(result) == 2
        assert result[0].file == "a.py"
        assert result[0].rule == "E501"
        assert result[1].file == "b.py"
        assert result[1].rule == "F401"

    def test_missing_optional_field_uses_none(
        self, manager: QAManager, flat_parsing: JsonViolationsParsing
    ) -> None:
        """ViolationDTO optional fields default when absent from payload."""
        payload = [{"message": "some message", "filename": "a.py"}]
        result = manager._parse_json_violations(payload, flat_parsing)
        assert result[0].line is None
        assert result[0].col is None
        assert result[0].rule is None

    def test_fixable_false_when_fix_is_none(
        self, manager: QAManager, flat_parsing: JsonViolationsParsing
    ) -> None:
        """fixable=False when the mapped fix field is null/None."""
        payload = [{"filename": "a.py", "message": "msg", "fix": None}]
        result = manager._parse_json_violations(payload, flat_parsing)
        assert result[0].fixable is False

    def test_fixable_true_when_fix_is_truthy(
        self, manager: QAManager, flat_parsing: JsonViolationsParsing
    ) -> None:
        """fixable=True when the mapped fix field is a truthy dict."""
        payload = [
            {
                "filename": "a.py",
                "message": "msg",
                "fix": {"applicability": "safe", "edits": []},
            }
        ]
        result = manager._parse_json_violations(payload, flat_parsing)
        assert result[0].fixable is True
