"""C38 RED — Gate 4b pyright severity field extraction (F-17).

Pyright --outputjson produces ``generalDiagnostics[i].severity`` as a plain
string (``"error"`` / ``"warning"`` / ``"information"``).  The gate4_pyright
field_map maps ``severity: "severity"``, yet live runs showed ``severity: null``
on every violation.

Root cause: ``_parse_json_violations`` unconditionally sets ``severity=None``
instead of reading ``fmap["severity"]`` via ``_resolve_field_path``.
"""

from __future__ import annotations

import pytest

from mcp_server.config.quality_config import JsonViolationsParsing
from mcp_server.managers.qa_manager import QAManager

# ---------------------------------------------------------------------------
# Fixtures / constants
# ---------------------------------------------------------------------------

# Mirrors the field_map as configured in .st3/quality.yaml gate4_pyright
_PYRIGHT_FIELD_MAP: dict[str, str] = {
    "file": "file",
    "line": "range/start/line",
    "col": "range/start/character",
    "message": "message",
    "rule": "rule",
    "severity": "severity",
}

_PYRIGHT_PARSING = JsonViolationsParsing(
    field_map=_PYRIGHT_FIELD_MAP,
    line_offset=1,
)

# Representative pyright --outputjson diagnostic
_PYRIGHT_DIAG_ERROR = {
    "file": "backend/dtos/validation_fixture_gate4.py",
    "severity": "error",
    "message": 'Type "str" is not assignable to declared type "int"',
    "range": {"start": {"line": 15, "character": 14}, "end": {"line": 15, "character": 28}},
    "rule": "reportAssignmentType",
}

_PYRIGHT_DIAG_WARNING = {
    "file": "backend/dtos/example.py",
    "severity": "warning",
    "message": 'Variable "x" is not used',
    "range": {"start": {"line": 3, "character": 4}, "end": {"line": 3, "character": 5}},
    "rule": "reportUnusedVariable",
}

_PYRIGHT_DIAG_INFORMATION = {
    "file": "backend/core/enums.py",
    "severity": "information",
    "message": 'Import "os" could not be resolved from source',
    "range": {"start": {"line": 0, "character": 7}, "end": {"line": 0, "character": 11}},
    "rule": "reportMissingModuleSource",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPyrightSeverityMapping:
    """Gate 4b: severity string must be extracted from the pyright JSON field_map."""

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager()

    # --- error ---

    def test_error_severity_is_extracted(self, manager: QAManager) -> None:
        """Pyright 'error' diagnostic → ViolationDTO.severity == 'error'."""
        result = manager._parse_json_violations([_PYRIGHT_DIAG_ERROR], _PYRIGHT_PARSING)
        assert len(result) == 1
        assert result[0].severity == "error"

    # --- warning ---

    def test_warning_severity_is_extracted(self, manager: QAManager) -> None:
        """Pyright 'warning' diagnostic → ViolationDTO.severity == 'warning'."""
        result = manager._parse_json_violations([_PYRIGHT_DIAG_WARNING], _PYRIGHT_PARSING)
        assert len(result) == 1
        assert result[0].severity == "warning"

    # --- information ---

    def test_information_severity_is_extracted(self, manager: QAManager) -> None:
        """Pyright 'information' diagnostic → ViolationDTO.severity == 'information'."""
        result = manager._parse_json_violations([_PYRIGHT_DIAG_INFORMATION], _PYRIGHT_PARSING)
        assert len(result) == 1
        assert result[0].severity == "information"

    # --- batch ---

    def test_multiple_diagnostics_each_have_correct_severity(self, manager: QAManager) -> None:
        """Mixed-severity batch: each DTO gets its own severity string, not null."""
        results = manager._parse_json_violations(
            [_PYRIGHT_DIAG_ERROR, _PYRIGHT_DIAG_WARNING, _PYRIGHT_DIAG_INFORMATION],
            _PYRIGHT_PARSING,
        )
        assert [dto.severity for dto in results] == ["error", "warning", "information"]

    # --- absent field_map key → None is acceptable ---

    def test_missing_severity_key_in_field_map_yields_none(self, manager: QAManager) -> None:
        """When severity is absent from field_map, ViolationDTO.severity == None."""
        parsing_no_severity = JsonViolationsParsing(
            field_map={k: v for k, v in _PYRIGHT_FIELD_MAP.items() if k != "severity"},
            line_offset=1,
        )
        result = manager._parse_json_violations([_PYRIGHT_DIAG_ERROR], parsing_no_severity)
        assert result[0].severity is None

    # --- other fields not regressed ---

    def test_other_fields_still_extracted_correctly(self, manager: QAManager) -> None:
        """Severity fix must not regress other field extractions."""
        result = manager._parse_json_violations([_PYRIGHT_DIAG_ERROR], _PYRIGHT_PARSING)
        dto = result[0]
        assert dto.file == "backend/dtos/validation_fixture_gate4.py"
        assert dto.rule == "reportAssignmentType"
        assert dto.message == 'Type "str" is not assignable to declared type "int"'
        assert dto.line == 16  # 15 + line_offset=1
        assert dto.col == 14
