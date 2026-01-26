# SCAFFOLD: template=test_unit version=xxx created=2026-01-26T21:20:00Z
"""
Tests for Tier 0 base template rendering (Issue #72, TDD Cycle 2).

RED phase: Tests for tier0_base_artifact.jinja2 2-line SCAFFOLD format:
- Line 1: # {filepath} (ONLY filepath)
- Line 2: # template={type} version={hash} created={iso8601} updated=
- NO "SCAFFOLD:" prefix
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
import pytest

# Template directory
TEMPLATE_DIR = (
    Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
)


class TestTier0TwoLineScaffoldFormat:
    """Test Tier 0 2-line SCAFFOLD format (Cycle 2)."""

    def test_python_format_two_line_scaffold(self):
        """Python format must use 2-line SCAFFOLD (no SCAFFOLD: prefix)."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier0_base_artifact.jinja2")

        result = template.render(
            artifact_type="worker",
            version_hash="a3f7b2c1",
            timestamp="2026-01-23T10:30:00Z",
            output_path="src/workers/MyWorker.py",
            format="python",
        )

        lines = result.strip().split("\n")
        # Line 1: ONLY filepath (no SCAFFOLD: prefix)
        assert lines[0] == "# src/workers/MyWorker.py", \
            f"Line 1 must be filepath only, got: {lines[0]}"
        # Line 2: metadata (no SCAFFOLD: prefix)
        assert lines[1].startswith("# template=worker version=a3f7b2c1"), \
            f"Line 2 must start with metadata, got: {lines[1]}"
        assert "created=2026-01-23T10:30:00Z" in lines[1]
        assert "updated=" in lines[1]
        # NO "SCAFFOLD:" anywhere
        assert "SCAFFOLD:" not in result

    def test_markdown_format_two_line_scaffold(self):
        """Markdown format must use 2-line HTML comment SCAFFOLD."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier0_base_artifact.jinja2")

        result = template.render(
            artifact_type="research",
            version_hash="b4e8f3c2",
            timestamp="2026-01-23T09:15:00Z",
            output_path="docs/development/issue72/research.md",
            format="markdown",
        )

        lines = result.strip().split("\n")
        # Line 1: ONLY filepath in HTML comment
        assert lines[0] == "<!-- docs/development/issue72/research.md -->", \
            f"Line 1 must be filepath only, got: {lines[0]}"
        # Line 2: metadata in HTML comment
        assert lines[1].startswith("<!-- template=research version=b4e8f3c2"), \
            f"Line 2 must start with metadata, got: {lines[1]}"
        assert "created=2026-01-23T09:15:00Z" in lines[1]
        assert "updated=" in lines[1]
        assert "-->" in lines[1]
        # NO "SCAFFOLD:" anywhere
        assert "SCAFFOLD:" not in result

    def test_yaml_format_two_line_scaffold(self):
        """YAML format must use 2-line SCAFFOLD with # comments."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier0_base_artifact.jinja2")

        result = template.render(
            artifact_type="workflow",
            version_hash="c5d6e7f8",
            timestamp="2026-01-23T11:00:00Z",
            output_path=".github/workflows/ci.yaml",
            format="yaml",
        )

        lines = result.strip().split("\n")
        assert lines[0] == "# .github/workflows/ci.yaml"
        assert lines[1].startswith("# template=workflow version=c5d6e7f8")
        assert "SCAFFOLD:" not in result
