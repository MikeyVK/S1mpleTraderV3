"""
tests/unit/tools/test_create_issue_errors.py
=============================================
Cycle 6 — Error handling in CreateIssueTool.execute().

Tests that all expected failure modes produce ToolResult.error() with actionable
messages instead of leaking raw exceptions to the caller.

Failure modes covered:
  1. ExecutionError from GitHubManager  → ToolResult.error
  2. JinjaRenderer TemplateError        → ToolResult.error
  3. ValueError from _assemble_labels  → ToolResult.error
  4. ToolResult.is_error is True in all failure cases
"""

from unittest.mock import MagicMock, patch

import jinja2
import pytest

from mcp_server.core.exceptions import ExecutionError
from mcp_server.tools.issue_tools import CreateIssueInput, CreateIssueTool, IssueBody

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

BODY = IssueBody(problem="Test error scenarios")

VALID_PARAMS = CreateIssueInput(
    issue_type="feature",
    title="Error test issue",
    priority="medium",
    scope="mcp-server",
    body=BODY,
)


def make_tool(manager: MagicMock | None = None) -> CreateIssueTool:
    """Return a CreateIssueTool with a mock manager."""
    mgr = manager or MagicMock()
    mgr.create_issue.return_value = {"number": 1, "title": "T", "url": ""}
    return CreateIssueTool(manager=mgr)


# ---------------------------------------------------------------------------
# TestExecutionErrorHandling
# ---------------------------------------------------------------------------


class TestExecutionErrorHandling:
    @pytest.mark.asyncio
    async def test_execution_error_returns_tool_result_error(self) -> None:
        """ExecutionError from GitHubManager must produce ToolResult.error()."""
        mock_manager = MagicMock()
        mock_manager.create_issue.side_effect = ExecutionError("GitHub API rate limit exceeded")
        tool = CreateIssueTool(manager=mock_manager)

        result = await tool.execute(VALID_PARAMS)

        assert result.is_error is True

    @pytest.mark.asyncio
    async def test_execution_error_message_is_included(self) -> None:
        mock_manager = MagicMock()
        mock_manager.create_issue.side_effect = ExecutionError("GitHub API rate limit exceeded")
        tool = CreateIssueTool(manager=mock_manager)

        result = await tool.execute(VALID_PARAMS)

        result_text = result.content[0]["text"]
        assert "rate limit" in result_text or "GitHub" in result_text

    @pytest.mark.asyncio
    async def test_execution_error_does_not_raise(self) -> None:
        """execute() must not raise — it must return ToolResult.error()."""
        mock_manager = MagicMock()
        mock_manager.create_issue.side_effect = ExecutionError("Network error")
        tool = CreateIssueTool(manager=mock_manager)

        # Must not raise
        result = await tool.execute(VALID_PARAMS)
        assert result is not None


# ---------------------------------------------------------------------------
# TestRenderingErrorHandling
# ---------------------------------------------------------------------------


class TestRenderingErrorHandling:
    @pytest.mark.asyncio
    async def test_template_error_returns_tool_result_error(self) -> None:
        """jinja2.TemplateError from _render_body must produce ToolResult.error()."""
        tool = make_tool()
        with patch.object(
            tool,
            "_render_body",
            side_effect=jinja2.TemplateError("Template not found"),
        ):
            result = await tool.execute(VALID_PARAMS)

        assert result.is_error is True

    @pytest.mark.asyncio
    async def test_template_error_does_not_raise(self) -> None:
        tool = make_tool()
        with patch.object(
            tool,
            "_render_body",
            side_effect=jinja2.TemplateError("Bad template"),
        ):
            result = await tool.execute(VALID_PARAMS)

        assert result is not None
        assert result.is_error is True

    @pytest.mark.asyncio
    async def test_template_not_found_error_is_handled(self) -> None:
        """jinja2.TemplateNotFound (subclass of TemplateError) is also caught."""
        tool = make_tool()
        with patch.object(
            tool,
            "_render_body",
            side_effect=jinja2.TemplateNotFound("issue.md.jinja2"),
        ):
            result = await tool.execute(VALID_PARAMS)

        assert result.is_error is True

    @pytest.mark.asyncio
    async def test_template_error_message_is_actionable(self) -> None:
        """TemplateError message must hint at the template path — not just 'Unexpected error'."""
        tool = make_tool()
        with patch.object(
            tool,
            "_render_body",
            side_effect=jinja2.TemplateError("template missing"),
        ):
            result = await tool.execute(VALID_PARAMS)

        result_text = result.content[0]["text"]
        assert "rendering" in result_text or "template" in result_text.lower()


# ---------------------------------------------------------------------------
# TestAssembleLabelErrorHandling
# ---------------------------------------------------------------------------


class TestAssembleLabelErrorHandling:
    @pytest.mark.asyncio
    async def test_value_error_from_label_assembly_returns_tool_result_error(self) -> None:
        """ValueError from _assemble_labels must produce ToolResult.error() not raise."""
        tool = make_tool()
        with patch.object(
            tool,
            "_assemble_labels",
            side_effect=ValueError("Unknown workflow: 'invalid'"),
        ):
            result = await tool.execute(VALID_PARAMS)

        assert result.is_error is True

    @pytest.mark.asyncio
    async def test_value_error_does_not_raise(self) -> None:
        tool = make_tool()
        with patch.object(
            tool,
            "_assemble_labels",
            side_effect=ValueError("Unknown workflow"),
        ):
            result = await tool.execute(VALID_PARAMS)

        assert result is not None


# ---------------------------------------------------------------------------
# TestNoExceptionLeaks
# ---------------------------------------------------------------------------


class TestNoExceptionLeaks:
    @pytest.mark.asyncio
    async def test_execution_error_does_not_propagate(self) -> None:
        """No known error type should propagate out of execute()."""
        mock_manager = MagicMock()
        mock_manager.create_issue.side_effect = ExecutionError("fail")
        tool = CreateIssueTool(manager=mock_manager)

        try:
            await tool.execute(VALID_PARAMS)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"execute() raised unexpectedly: {exc!r}")

    @pytest.mark.asyncio
    async def test_template_error_does_not_propagate(self) -> None:
        tool = make_tool()
        with patch.object(tool, "_render_body", side_effect=jinja2.TemplateError("fail")):
            try:
                await tool.execute(VALID_PARAMS)
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"execute() raised unexpectedly: {exc!r}")
