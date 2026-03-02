from __future__ import annotations

import pytest

from mcp_server.config.quality_config import JsonViolationsParsing
from mcp_server.managers.qa_manager import QAManager

_BASE_MAP: dict[str, str] = {
    "file": "filename",
    "message": "message",
    "line": "line",
    "col": "column",
    "rule": "code",
}


class TestLineOffset:
    """_parse_json_violations: line_offset shifts the mapped line value (Issue #251 C10).

    ``line_offset`` is added to the extracted line integer.
    Useful for tools that report 0-based line numbers.
    """

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager()

    def test_zero_offset_is_no_op(self, manager: QAManager) -> None:
        """line_offset=0 (default) leaves the line value unchanged."""
        parsing = JsonViolationsParsing(field_map=_BASE_MAP, line_offset=0)
        payload = [{"filename": "a.py", "message": "msg", "line": 5}]
        result = manager._parse_json_violations(payload, parsing)
        assert result[0].line == 5

    def test_positive_offset_is_added(self, manager: QAManager) -> None:
        """line_offset=1 converts 0-based line 0 → 1."""
        parsing = JsonViolationsParsing(field_map=_BASE_MAP, line_offset=1)
        payload = [{"filename": "a.py", "message": "msg", "line": 0}]
        result = manager._parse_json_violations(payload, parsing)
        assert result[0].line == 1

    def test_offset_applied_to_each_item(self, manager: QAManager) -> None:
        """Offset is applied to every item in the payload."""
        parsing = JsonViolationsParsing(field_map=_BASE_MAP, line_offset=1)
        payload = [
            {"filename": "a.py", "message": "x", "line": 2},
            {"filename": "b.py", "message": "y", "line": 9},
        ]
        result = manager._parse_json_violations(payload, parsing)
        assert result[0].line == 3
        assert result[1].line == 10

    def test_offset_not_applied_when_line_is_none(self, manager: QAManager) -> None:
        """When line field is absent (None), offset is not applied."""
        parsing = JsonViolationsParsing(field_map=_BASE_MAP, line_offset=1)
        payload = [{"filename": "a.py", "message": "msg"}]
        result = manager._parse_json_violations(payload, parsing)
        assert result[0].line is None


class TestFixableWhen:
    """_parse_json_violations: fixable_when overrides field_map fixable key (Issue #251 C10).

    When ``fixable_when`` is set on the parsing config, the named source key
    is used for the truthy fixable check **instead of** ``field_map["fixable"]``.
    """

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager()

    def test_fixable_when_truthy_sets_fixable_true(self, manager: QAManager) -> None:
        """fixable=True when the fixable_when field is truthy."""
        parsing = JsonViolationsParsing(field_map=_BASE_MAP, fixable_when="has_fix")
        payload = [{"filename": "a.py", "message": "msg", "has_fix": True}]
        result = manager._parse_json_violations(payload, parsing)
        assert result[0].fixable is True

    def test_fixable_when_falsy_sets_fixable_false(self, manager: QAManager) -> None:
        """fixable=False when the fixable_when field is falsy."""
        parsing = JsonViolationsParsing(field_map=_BASE_MAP, fixable_when="has_fix")
        payload = [{"filename": "a.py", "message": "msg", "has_fix": False}]
        result = manager._parse_json_violations(payload, parsing)
        assert result[0].fixable is False

    def test_fixable_when_key_absent_sets_fixable_false(self, manager: QAManager) -> None:
        """fixable=False when the fixable_when key is missing from the item."""
        parsing = JsonViolationsParsing(field_map=_BASE_MAP, fixable_when="has_fix")
        payload = [{"filename": "a.py", "message": "msg"}]
        result = manager._parse_json_violations(payload, parsing)
        assert result[0].fixable is False

    def test_fixable_when_overrides_field_map_fixable(self, manager: QAManager) -> None:
        """fixable_when takes precedence over field_map['fixable'] when both are present."""
        combined_map = {**_BASE_MAP, "fixable": "fix"}
        parsing = JsonViolationsParsing(field_map=combined_map, fixable_when="has_fix")
        # field_map["fixable"] → "fix" is truthy; fixable_when → "has_fix" is False
        payload = [{"filename": "a.py", "message": "msg", "fix": {"edits": []}, "has_fix": False}]
        result = manager._parse_json_violations(payload, parsing)
        assert result[0].fixable is False
