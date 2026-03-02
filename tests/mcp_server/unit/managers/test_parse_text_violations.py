from __future__ import annotations

import pytest

from mcp_server.config.quality_config import TextViolationsParsing, ViolationDTO
from mcp_server.managers.qa_manager import QAManager

# Pattern that captures file, line, col, rule, message (mypy-like)
_MYPY_PATTERN = r"(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+): (?P<severity>\w+): (?P<message>.+)  \[(?P<rule>\w+)\]"  # noqa: E501

# Simpler pattern without severity or rule groups
_SIMPLE_PATTERN = r"(?P<file>[^:]+):(?P<line>\d+): (?P<message>.+)"


class TestParseTextViolations:
    """QAManager._parse_text_violations: line-based tool output parsing (Issue #251 C11).

    Each output line is matched against ``parsing.pattern``.  Non-matching lines
    are silently skipped.  Named groups map directly to ViolationDTO fields.
    """

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager()

    # ------------------------------------------------------------------
    # Basic matching
    # ------------------------------------------------------------------

    def test_single_matching_line_produces_one_dto(self, manager: QAManager) -> None:
        """A line matching the pattern produces one ViolationDTO."""
        parsing = TextViolationsParsing(pattern=_SIMPLE_PATTERN)
        output = "backend/core/enums.py:42: some error message"
        result = manager._parse_text_violations(output, parsing)
        assert len(result) == 1
        dto = result[0]
        assert isinstance(dto, ViolationDTO)
        assert dto.file == "backend/core/enums.py"
        assert dto.line == 42
        assert dto.message == "some error message"

    def test_non_matching_lines_are_skipped(self, manager: QAManager) -> None:
        """Lines that don't match the pattern are silently ignored."""
        parsing = TextViolationsParsing(pattern=_SIMPLE_PATTERN)
        output = "Found 1 error in 1 file\nbackend/a.py:1: msg\nSummary: 1 error"
        result = manager._parse_text_violations(output, parsing)
        assert len(result) == 1
        assert result[0].file == "backend/a.py"

    def test_empty_output_returns_empty_list(self, manager: QAManager) -> None:
        """Empty string produces empty list."""
        parsing = TextViolationsParsing(pattern=_SIMPLE_PATTERN)
        assert manager._parse_text_violations("", parsing) == []

    def test_multiple_matching_lines(self, manager: QAManager) -> None:
        """Multiple matching lines each produce a ViolationDTO in order."""
        parsing = TextViolationsParsing(pattern=_SIMPLE_PATTERN)
        output = "a.py:1: first\nb.py:2: second"
        result = manager._parse_text_violations(output, parsing)
        assert len(result) == 2
        assert result[0].file == "a.py"
        assert result[0].line == 1
        assert result[1].file == "b.py"
        assert result[1].line == 2

    # ------------------------------------------------------------------
    # Named groups → ViolationDTO field mapping
    # ------------------------------------------------------------------

    def test_full_pattern_maps_all_fields(self, manager: QAManager) -> None:
        """All named groups in _MYPY_PATTERN populate the corresponding DTO fields."""
        parsing = TextViolationsParsing(pattern=_MYPY_PATTERN)
        line = "backend/core/enums.py:12:3: error: Cannot find module  [import]"
        result = manager._parse_text_violations(line, parsing)
        assert len(result) == 1
        dto = result[0]
        assert dto.file == "backend/core/enums.py"
        assert dto.line == 12
        assert dto.col == 3
        assert dto.severity == "error"
        assert dto.message == "Cannot find module"
        assert dto.rule == "import"

    def test_line_and_col_are_integers(self, manager: QAManager) -> None:
        """Named groups 'line' and 'col' are converted to int."""
        parsing = TextViolationsParsing(pattern=_MYPY_PATTERN)
        line = "a.py:99:5: warning: msg  [rule]"
        result = manager._parse_text_violations(line, parsing)
        assert isinstance(result[0].line, int)
        assert isinstance(result[0].col, int)

    # ------------------------------------------------------------------
    # severity_default fallback
    # ------------------------------------------------------------------

    def test_severity_default_used_when_group_absent(self, manager: QAManager) -> None:
        """severity_default is used when pattern has no 'severity' group."""
        parsing = TextViolationsParsing(pattern=_SIMPLE_PATTERN, severity_default="warning")
        output = "a.py:1: msg"
        result = manager._parse_text_violations(output, parsing)
        assert result[0].severity == "warning"
