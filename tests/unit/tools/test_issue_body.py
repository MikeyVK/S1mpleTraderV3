"""
tests/unit/tools/test_issue_body.py
====================================
Cycle 3 — IssueBody Pydantic model and _render_body() helper.

Tests:
- IssueBody field requirements and defaults
- Rendering via CreateIssueTool._render_body() with issue.md.jinja2
"""

import pytest
from pydantic import ValidationError

from mcp_server.config.template_config import get_template_root
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.tools.issue_tools import CreateIssueTool, IssueBody


@pytest.fixture(name="renderer")
def _renderer() -> JinjaRenderer:
    return JinjaRenderer(template_dir=get_template_root())


@pytest.fixture(name="tool")
def _tool(renderer: JinjaRenderer) -> CreateIssueTool:
    tool = CreateIssueTool.__new__(CreateIssueTool)
    tool._renderer = renderer  # inject without GitHubManager
    return tool


# ---------------------------------------------------------------------------
# TestIssueBodyModel
# ---------------------------------------------------------------------------


class TestIssueBodyModel:
    def test_problem_is_required(self) -> None:
        with pytest.raises(ValidationError):
            IssueBody()  # type: ignore[call-arg]

    def test_problem_is_accepted(self) -> None:
        body = IssueBody(problem="Some problem")
        assert body.problem == "Some problem"

    def test_all_optional_fields_default_to_none(self) -> None:
        body = IssueBody(problem="p")
        assert body.expected is None
        assert body.actual is None
        assert body.context is None
        assert body.steps_to_reproduce is None
        assert body.related_docs is None

    def test_related_docs_accepts_list_of_strings(self) -> None:
        body = IssueBody(problem="p", related_docs=["docs/a.md", "docs/b.md"])
        assert body.related_docs == ["docs/a.md", "docs/b.md"]

    def test_related_docs_rejects_plain_string(self) -> None:
        with pytest.raises(ValidationError):
            IssueBody(problem="p", related_docs="docs/a.md")  # type: ignore[arg-type]

    def test_full_body_accepted(self) -> None:
        body = IssueBody(
            problem="p",
            expected="e",
            actual="a",
            context="c",
            steps_to_reproduce="1. step",
            related_docs=["docs/planning.md"],
        )
        assert body.expected == "e"
        assert body.steps_to_reproduce == "1. step"


# ---------------------------------------------------------------------------
# TestRenderBody
# ---------------------------------------------------------------------------


class TestRenderBody:
    def test_render_produces_problem_section(self, tool: CreateIssueTool) -> None:
        body = IssueBody(problem="Widget explodes on startup")
        result = tool._render_body(body)
        assert "## Problem" in result
        assert "Widget explodes on startup" in result

    def test_render_minimal_body_excludes_optional_sections(self, tool: CreateIssueTool) -> None:
        body = IssueBody(problem="minimal")
        result = tool._render_body(body)
        assert "## Expected Behavior" not in result
        assert "## Actual Behavior" not in result
        assert "## Context" not in result

    def test_render_includes_expected_section(self, tool: CreateIssueTool) -> None:
        body = IssueBody(problem="p", expected="Should work")
        result = tool._render_body(body)
        assert "## Expected Behavior" in result
        assert "Should work" in result

    def test_render_includes_actual_section(self, tool: CreateIssueTool) -> None:
        body = IssueBody(problem="p", actual="Does not work")
        result = tool._render_body(body)
        assert "## Actual Behavior" in result
        assert "Does not work" in result

    def test_render_includes_context_section(self, tool: CreateIssueTool) -> None:
        body = IssueBody(problem="p", context="Only on Windows")
        result = tool._render_body(body)
        assert "## Context" in result
        assert "Only on Windows" in result

    def test_render_includes_steps_to_reproduce(self, tool: CreateIssueTool) -> None:
        body = IssueBody(problem="p", steps_to_reproduce="1. Open app\n2. Click crash")
        result = tool._render_body(body)
        assert "## Steps to Reproduce" in result
        assert "1. Open app" in result

    def test_render_includes_related_docs_section(self, tool: CreateIssueTool) -> None:
        body = IssueBody(problem="p", related_docs=["docs/planning.md", "docs/design.md"])
        result = tool._render_body(body)
        assert "planning.md" in result
        assert "design.md" in result

    def test_render_returns_string(self, tool: CreateIssueTool) -> None:
        body = IssueBody(problem="p")
        result = tool._render_body(body)
        assert isinstance(result, str)
        assert len(result) > 0
