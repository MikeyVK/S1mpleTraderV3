# tests\unit\tools\test_render_body_scaffold_header.py
# template=unit_test version=3d15d309 created=2026-02-21T16:03Z updated=
"""
Unit tests for mcp_server.tools.issue_tools.

Tests for _render_body() SCAFFOLD header output (Issue #239 C3)

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.tools.issue_tools, unittest.mock]
@responsibilities:
    - Rendered body has compact SCAFFOLD header (template=issue version=XXXXXXXX)
    - Rendered body has NO created= / updated= fields
    - Rendered body has NO empty filepath comment line
    - Hash is deterministic (same template -> same hash)
    - Rendered body uses HTML comment format (not Python # comment)
"""

# Standard library
import re
from unittest.mock import MagicMock

# Third-party
import pytest

# Project modules
from mcp_server.tools.issue_tools import CreateIssueTool, IssueBody


@pytest.fixture(name="tool")
def fixture_tool() -> CreateIssueTool:
    """CreateIssueTool with mocked GitHubManager (no real git/API calls)."""
    mock_manager = MagicMock()
    return CreateIssueTool(manager=mock_manager)


@pytest.fixture(name="minimal_body")
def fixture_minimal_body() -> IssueBody:
    """Minimal IssueBody for rendering tests."""
    return IssueBody(problem="Reproduce the issue")


class TestRenderBodyScaffoldHeader:
    """Test _render_body() SCAFFOLD header correctness after C3 fix."""

    def test_rendered_body_contains_template_fingerprint(
        self, tool: CreateIssueTool, minimal_body: IssueBody
    ) -> None:
        """Rendered body contains compact SCAFFOLD header with template and version fields."""
        result = tool._render_body(minimal_body, title="Test Issue")

        # Should have: <!-- template=issue version=XXXXXXXX -->
        assert "template=issue" in result, f"Expected 'template=issue' in:\n{result}"
        assert "version=" in result, f"Expected 'version=' in:\n{result}"

        # Version hash should be 8 hex chars
        match = re.search(r"version=([0-9a-f]{8})\b", result)
        assert match is not None, f"Expected 8-char hex version hash in:\n{result}"

    def test_rendered_body_has_no_created_field(
        self, tool: CreateIssueTool, minimal_body: IssueBody
    ) -> None:
        """Rendered body without output_path must NOT contain created= or updated= fields."""
        result = tool._render_body(minimal_body, title="Test Issue")

        assert "created=" not in result, f"Unexpected 'created=' in:\n{result}"
        assert "updated=" not in result, f"Unexpected 'updated=' in:\n{result}"

    def test_rendered_body_has_no_empty_filepath_line(
        self, tool: CreateIssueTool, minimal_body: IssueBody
    ) -> None:
        """Rendered body must NOT contain an empty HTML comment line (<!--  -->)."""
        result = tool._render_body(minimal_body, title="Test Issue")

        # Empty filepath line would be: <!--  --> or <!-- -->
        assert "<!--  -->" not in result, f"Unexpected empty HTML comment in:\n{result}"
        assert "<!-- -->" not in result, f"Unexpected empty HTML comment in:\n{result}"

    def test_hash_is_deterministic(self, tool: CreateIssueTool, minimal_body: IssueBody) -> None:
        """Same template produces same hash in repeated _render_body calls."""
        result1 = tool._render_body(minimal_body, title="Issue A")
        result2 = tool._render_body(minimal_body, title="Issue B")

        hash1_match = re.search(r"version=([0-9a-f]{8})\b", result1)
        hash2_match = re.search(r"version=([0-9a-f]{8})\b", result2)

        assert hash1_match is not None, "No hash in first call"
        assert hash2_match is not None, "No hash in second call"
        assert hash1_match.group(1) == hash2_match.group(1), (
            f"Hash not deterministic: {hash1_match.group(1)} != {hash2_match.group(1)}"
        )

    def test_rendered_body_uses_html_comment_format(
        self, tool: CreateIssueTool, minimal_body: IssueBody
    ) -> None:
        """SCAFFOLD header must be HTML comment (<!-- ... -->) not Python comment (# ...)."""
        result = tool._render_body(minimal_body, title="Test Issue")
        lines = result.strip().split("\n")

        # First line should be HTML comment, not Python comment
        first_line = lines[0]
        assert first_line.startswith("<!--"), f"Expected HTML comment header, got: {first_line!r}"
        assert not first_line.startswith("# "), (
            f"Got Python comment instead of HTML comment: {first_line!r}"
        )
