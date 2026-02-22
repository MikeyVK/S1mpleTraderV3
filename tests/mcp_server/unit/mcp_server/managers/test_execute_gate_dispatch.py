from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.config.quality_config import (
    CapabilitiesMetadata,
    ExecutionConfig,
    ExitCodeParsing,
    JsonViolationsParsing,
    QualityGate,
    SuccessCriteria,
    TextViolationsParsing,
)
from mcp_server.managers.qa_manager import QAManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXEC = ExecutionConfig(command=["python", "-c", "pass"], timeout_seconds=10)
_EXIT_CODE_PARSING = ExitCodeParsing(strategy="exit_code")
_EXIT_CODE_SUCCESS = SuccessCriteria(mode="exit_code", exit_codes_ok=[0])
_BASE_CAPS = {"file_types": [".py"], "supports_autofix": False}
_JSON_PARSING = JsonViolationsParsing(
    field_map={"file": "filename", "message": "message", "rule": "code"},
)
_TEXT_PARSING = TextViolationsParsing(
    pattern=r"(?P<file>[^:]+):(?P<line>\d+): (?P<message>.+)",
)


def _make_gate(caps: dict) -> QualityGate:
    return QualityGate(
        name="test-gate",
        execution=_EXEC,
        parsing=_EXIT_CODE_PARSING,
        success=_EXIT_CODE_SUCCESS,
        capabilities=CapabilitiesMetadata(**caps),
    )


def _mock_proc(stdout: str, returncode: int = 0) -> MagicMock:
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.stdout = stdout
    proc.stderr = ""
    proc.returncode = returncode
    return proc


# ---------------------------------------------------------------------------
# Tests: CapabilitiesMetadata accepts new fields
# ---------------------------------------------------------------------------


class TestCapabilitiesMetadataViolationFields:
    """CapabilitiesMetadata must accept optional violation-parsing fields (Issue #251 C13)."""

    def test_accepts_parsing_strategy_json_violations(self) -> None:
        """parsing_strategy='json_violations' is accepted without error."""
        caps = CapabilitiesMetadata(
            **_BASE_CAPS, parsing_strategy="json_violations", json_violations=_JSON_PARSING
        )
        assert caps.parsing_strategy == "json_violations"

    def test_accepts_parsing_strategy_text_violations(self) -> None:
        """parsing_strategy='text_violations' is accepted without error."""
        caps = CapabilitiesMetadata(
            **_BASE_CAPS, parsing_strategy="text_violations", text_violations=_TEXT_PARSING
        )
        assert caps.parsing_strategy == "text_violations"

    def test_parsing_strategy_defaults_to_none(self) -> None:
        """parsing_strategy defaults to None when not provided."""
        caps = CapabilitiesMetadata(**_BASE_CAPS)
        assert caps.parsing_strategy is None


# ---------------------------------------------------------------------------
# Tests: _execute_gate dispatches on capabilities.parsing_strategy
# ---------------------------------------------------------------------------


class TestExecuteGateJsonViolationsDispatch:
    """_execute_gate routes through _parse_json_violations when
    capabilities.parsing_strategy == 'json_violations' (Issue #251 C13)."""

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager()

    def _gate(self) -> QualityGate:
        return _make_gate({
            **_BASE_CAPS,
            "parsing_strategy": "json_violations",
            "json_violations": _JSON_PARSING,
        })

    def test_violations_from_json_output_become_issues(self, manager: QAManager) -> None:
        """JSON output is parsed into issues via the json_violations pipeline."""
        payload = json.dumps([
            {"filename": "a.py", "message": "some error", "code": "E001"},
        ])
        with patch("subprocess.run", return_value=_mock_proc(payload)):
            result = manager._execute_gate(self._gate(), ["a.py"], gate_number=1)
        assert result["passed"] is False
        assert len(result["issues"]) == 1
        assert result["issues"][0]["message"] == "some error"

    def test_empty_json_array_gives_zero_issues(self, manager: QAManager) -> None:
        """An empty JSON array produces no violations and gate passes."""
        with patch("subprocess.run", return_value=_mock_proc("[]")):
            result = manager._execute_gate(self._gate(), ["a.py"], gate_number=1)
        assert result["passed"] is True
        assert result["issues"] == []


# ---------------------------------------------------------------------------


class TestExecuteGateTextViolationsDispatch:
    """_execute_gate routes through _parse_text_violations when
    capabilities.parsing_strategy == 'text_violations' (Issue #251 C13)."""

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager()

    def _gate(self) -> QualityGate:
        return _make_gate({
            **_BASE_CAPS,
            "parsing_strategy": "text_violations",
            "text_violations": _TEXT_PARSING,
        })

    def test_text_output_violations_become_issues(self, manager: QAManager) -> None:
        """Text output is parsed into issues via the text_violations pipeline."""
        text = "a.py:10: some lint warning"
        with patch("subprocess.run", return_value=_mock_proc(text, returncode=1)):
            result = manager._execute_gate(self._gate(), ["a.py"], gate_number=1)
        assert result["passed"] is False
        assert len(result["issues"]) == 1
        assert result["issues"][0]["message"] == "some lint warning"

    def test_no_matching_lines_gives_zero_issues(self, manager: QAManager) -> None:
        """Output with no matching lines produces no violations."""
        with patch("subprocess.run", return_value=_mock_proc("")):
            result = manager._execute_gate(self._gate(), ["a.py"], gate_number=1)
        assert result["passed"] is True
        assert result["issues"] == []
