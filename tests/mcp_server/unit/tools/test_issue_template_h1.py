# tests\mcp_server\unit\tools\test_issue_template_h1.py
"""C3 RED: issue.md.jinja2 must not render a duplicate H1 title.

GitHub renders the issue title as H1 natively. The template must not
add a redundant # <title> line that creates a double H1 in the rendered output.

@layer: Tests (Unit)
@dependencies: [pytest, jinja2]
"""

import re

import pytest
from jinja2 import Environment, FileSystemLoader

from tests.mcp_server.test_support import get_template_root

TEMPLATE_DIR = get_template_root()


@pytest.fixture
def issue_env() -> Environment:
    return Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def render_issue(env: Environment, **kwargs: object) -> str:
    """Render issue.md.jinja2 with minimal required context."""
    tpl = env.get_template("concrete/issue.md.jinja2")
    defaults = {
        "title": "Test Issue Title",
        "problem": "Something is broken.",
        "artifact_type": "issue",
        "version_hash": "abc12345",
        "timestamp": "",
        "output_path": None,
        "format": "markdown",
        "summary": None,
        "expected": None,
        "actual": None,
        "context": None,
        "steps_to_reproduce": None,
        "related_docs": [],
        "labels": [],
        "milestone": None,
        "assignees": [],
    }
    defaults.update(kwargs)
    return tpl.render(**defaults)


class TestIssueTemplateNoH1:
    def test_rendered_output_has_no_markdown_h1(self, issue_env: Environment) -> None:
        """Rendered issue body must not contain a # H1 heading line."""
        result = render_issue(issue_env)
        h1_lines = [line for line in result.splitlines() if re.match(r"^# ", line)]
        assert h1_lines == [], f"Template rendered unexpected H1 line(s): {h1_lines}"

    def test_rendered_output_does_not_start_with_title_h1(self, issue_env: Environment) -> None:
        """Output must not start with # Test Issue Title."""
        result = render_issue(issue_env)
        assert not result.lstrip().startswith("# Test Issue Title"), (
            "Template rendered duplicate H1 title"
        )

    def test_summary_still_renders_without_h1(self, issue_env: Environment) -> None:
        """Summary section renders correctly when no H1 is present."""
        result = render_issue(issue_env, summary="A short summary.")
        assert "A short summary." in result
        h1_lines = [line for line in result.splitlines() if re.match(r"^# ", line)]
        assert h1_lines == [], "H1 appeared despite summary being present"

    def test_problem_section_still_renders(self, issue_env: Environment) -> None:
        """Problem section renders correctly after H1 removal."""
        result = render_issue(issue_env, problem="Widget explodes on startup.")
        assert "Widget explodes on startup." in result
        assert "## Problem" in result
