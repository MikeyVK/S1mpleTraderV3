# tests/unit/mcp_server/tools/test_quality_tools.py
"""Tests for quality tools."""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false

# Standard library
from typing import Any
from unittest.mock import MagicMock

# Third-party
import pytest
from pydantic import ValidationError

# Module under test
from mcp_server.tools.quality_tools import RunQualityGatesInput, RunQualityGatesTool
from mcp_server.tools.tool_result import ToolResult


def _summary_text(result: ToolResult) -> str:
    """Extract summary text from content[0] (type='text')."""
    item = result.content[0]
    assert item["type"] == "text", f"Expected content[0] type='text', got '{item['type']}'"
    return item["text"]


def _compact_payload(result: ToolResult) -> dict[str, Any]:
    """Extract compact JSON payload from content[1] (type='json')."""
    item = result.content[1]
    assert item["type"] == "json", f"Expected content[1] type='json', got '{item['type']}'"
    return item["json"]


class TestRunQualityGatesTool:
    """Tests for RunQualityGatesTool."""

    @pytest.mark.asyncio
    async def test_no_files_triggers_project_level(self) -> None:
        """Test scope='project' resolves to empty list and is forwarded to manager."""
        mock_manager = MagicMock()
        mock_manager._resolve_scope.return_value = []
        mock_manager.run_quality_gates.return_value = {
            "version": "2.0",
            "mode": "project-level",
            "files": [],
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 3,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "gates": [
                {
                    "name": "Tests",
                    "passed": True,
                    "status": "passed",
                    "score": "Pass",
                    "issues": [],
                }
            ],
            "overall_pass": True,
        }
        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(scope="project"))

        text = _summary_text(result)
        assert "Quality gates" in text
        mock_manager._resolve_scope.assert_called_once_with("project", files=None)
        mock_manager.run_quality_gates.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_quality_gates_passed(self) -> None:
        """Test clean quality pass returns ✅ summary line."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "overall_pass": True,
            "gates": [
                {
                    "name": "pylint",
                    "passed": True,
                    "status": "passed",
                    "score": 10.0,
                    "issues": [],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(scope="files", files=["foo.py"]))

        text = _summary_text(result)
        assert "✅" in text

    @pytest.mark.asyncio
    async def test_quality_gates_failed_with_issues(self) -> None:
        """Test failed quality gates returns ❌ summary line."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "total_violations": 1,
                "auto_fixable": 0,
            },
            "overall_pass": False,
            "gates": [
                {
                    "name": "pylint",
                    "passed": False,
                    "status": "failed",
                    "score": 5.0,
                    "issues": [
                        {
                            "file": "foo.py",
                            "line": 10,
                            "column": 4,
                            "code": "C0111",
                            "message": "Missing docstring",
                        }
                    ],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(scope="files", files=["foo.py"]))

        text = _summary_text(result)
        assert "❌" in text

    @pytest.mark.asyncio
    async def test_quality_gates_failed_prints_hints(self) -> None:
        """Test gate with hints — summary line is still returned."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "total_violations": 1,
                "auto_fixable": 0,
            },
            "overall_pass": False,
            "gates": [
                {
                    "name": "Gate 3: Line Length",
                    "passed": False,
                    "status": "failed",
                    "score": "Fail",
                    "issues": [{"message": "E501"}],
                    "hints": ["Re-run: python -m ruff check file.py"],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(scope="files", files=["foo.py"]))

        text = _summary_text(result)
        assert "❌" in text
        assert "Quality gates" in text

    @pytest.mark.asyncio
    async def test_quality_gates_issues_missing_fields(self) -> None:
        """Test result with empty issues dict — summary line is returned without crash."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "overall_pass": False,
            "gates": [
                {
                    "name": "check",
                    "passed": False,
                    "status": "failed",
                    "score": 0,
                    "issues": [{}],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(scope="files", files=["foo.py"]))

        text = _summary_text(result)
        assert "Quality gates" in text

    @pytest.mark.asyncio
    async def test_response_is_native_json_object(self) -> None:
        """Tool returns text summary at content[0], compact JSON at content[1]."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "version": "2.0",
            "mode": "file-specific",
            "files": ["foo.py"],
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "gates": [
                {
                    "id": 1,
                    "name": "Gate 0: Ruff Format",
                    "passed": True,
                    "status": "passed",
                    "skip_reason": None,
                    "score": "Pass",
                    "issues": [],
                }
            ],
            "overall_pass": True,
        }
        # C36: _build_compact_result is now an instance method (not static).
        # The MagicMock would return a MagicMock by default; configure it to
        # return a realistic compact payload so the tool-response contract test
        # exercises what it is designed to test.
        mock_manager._build_compact_result.return_value = {
            "overall_pass": True,
            "duration_ms": 0,
            "gates": [
                {
                    "id": "Gate 0: Ruff Format",
                    "passed": True,
                    "skipped": False,
                    "status": "passed",
                    "violations": [],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(scope="files", files=["foo.py"]))

        # content[0] is text summary
        assert result.content[0]["type"] == "text"
        assert isinstance(result.content[0]["text"], str)

        # content[1] is compact JSON payload
        assert result.content[1]["type"] == "json"
        data = result.content[1]["json"]
        assert isinstance(data, dict)
        assert "gates" in data

    def test_schema(self) -> None:
        """Test tool schema has files property."""
        tool = RunQualityGatesTool(manager=MagicMock())
        schema = tool.input_schema
        assert "files" in schema["properties"]


class TestRunQualityGatesInputC28:
    """C28: scope="files" as 4th Literal value with conditional files companion field.

    RED tests — all must fail until C28 GREEN is implemented.
    """

    # --- Validator: files REQUIRED when scope="files" ---

    def test_scope_files_without_files_raises(self) -> None:
        """scope='files' with no files field raises ValidationError (files required)."""
        with pytest.raises(ValidationError):
            RunQualityGatesInput(scope="files")

    def test_scope_files_with_empty_list_raises(self) -> None:
        """scope='files' with empty list raises ValidationError (empty not allowed)."""
        with pytest.raises(ValidationError):
            RunQualityGatesInput(scope="files", files=[])

    def test_scope_files_with_files_is_valid(self) -> None:
        """scope='files' with non-empty files is valid."""
        params = RunQualityGatesInput(scope="files", files=["a.py", "b.py"])
        assert params.scope == "files"
        assert params.files == ["a.py", "b.py"]

    # --- Validator: files FORBIDDEN when scope != "files" ---

    def test_scope_auto_with_files_raises(self) -> None:
        """scope='auto' with files supplied raises ValidationError (files forbidden)."""
        with pytest.raises(ValidationError):
            RunQualityGatesInput(scope="auto", files=["a.py"])

    def test_scope_branch_with_files_raises(self) -> None:
        """scope='branch' with files supplied raises ValidationError (files forbidden)."""
        with pytest.raises(ValidationError):
            RunQualityGatesInput(scope="branch", files=["a.py"])

    def test_scope_project_with_files_raises(self) -> None:
        """scope='project' with files supplied raises ValidationError (files forbidden)."""
        with pytest.raises(ValidationError):
            RunQualityGatesInput(scope="project", files=["a.py"])

    # --- Valid non-files scopes ---

    def test_scope_auto_without_files_is_valid(self) -> None:
        """scope='auto' with no files is valid."""
        params = RunQualityGatesInput(scope="auto")
        assert params.scope == "auto"
        assert params.files is None

    def test_scope_branch_without_files_is_valid(self) -> None:
        """scope='branch' with no files is valid."""
        params = RunQualityGatesInput(scope="branch")
        assert params.scope == "branch"

    def test_scope_project_without_files_is_valid(self) -> None:
        """scope='project' with no files is valid."""
        params = RunQualityGatesInput(scope="project")
        assert params.scope == "project"

    # --- Default scope ---

    def test_default_scope_is_auto(self) -> None:
        """Default scope is 'auto' when no scope is provided."""
        params = RunQualityGatesInput()
        assert params.scope == "auto"

    # --- Old bare-files API rejected ---

    def test_bare_files_api_without_scope_rejected(self) -> None:
        """Bare files=[] without scope raises ValidationError (old API no longer valid)."""
        with pytest.raises(ValidationError):
            RunQualityGatesInput(files=[])

    # --- Schema reflects new API ---

    def test_schema_has_scope_not_bare_files(self) -> None:
        """Input schema exposes 'scope' field."""
        tool = RunQualityGatesTool(manager=MagicMock())
        schema = tool.input_schema
        assert "scope" in schema["properties"]

    # --- execute() routes scope="files" correctly ---

    @pytest.mark.asyncio
    async def test_execute_scope_files_passes_list_to_manager(self) -> None:
        """execute(scope='files', files=[...]) passes the list verbatim to run_quality_gates."""
        mock_manager = MagicMock()
        mock_manager._resolve_scope.return_value = ["src/foo.py"]
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "overall_pass": True,
            "gates": [],
        }
        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(scope="files", files=["src/foo.py"]))

        mock_manager.run_quality_gates.assert_called_once_with(["src/foo.py"])
        assert result.content[0]["type"] == "text"
