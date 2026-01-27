"""
Tests for Tier 0 base template rendering (Issue #72 Task 1.3).

RED phase: Tests for tier0_base_artifact.jinja2 SCAFFOLD metadata generation
with format-adaptive comment styles.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"


class TestTier0BaseArtifactRendering:
    """Test Tier 0 base template rendering with different formats."""

    def test_render_python_format_uses_hash_comment(self):
        """Should use # comment style for Python format."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier0_base_artifact.jinja2")

        result = template.render(
            artifact_type="worker",
            version_hash="a3f7b2c1",
            timestamp="2026-01-23T10:30:00Z",
            output_path="src/workers/MyWorker.py",
            format="python"
        )

        assert result.startswith("# SCAFFOLD: worker:a3f7b2c1")
        assert "2026-01-23T10:30:00Z" in result
        assert "src/workers/MyWorker.py" in result
        # Should not have HTML comment markers
        assert "<!--" not in result
        assert "-->" not in result

    def test_render_yaml_format_uses_hash_comment(self):
        """Should use # comment style for YAML format."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier0_base_artifact.jinja2")

        result = template.render(
            artifact_type="workflow",
            version_hash="c5d6e7f8",
            timestamp="2026-01-23T11:00:00Z",
            output_path=".github/workflows/ci.yaml",
            format="yaml"
        )

        assert result.startswith("# SCAFFOLD: workflow:c5d6e7f8")
        assert "2026-01-23T11:00:00Z" in result
        assert ".github/workflows/ci.yaml" in result

    def test_render_markdown_format_uses_html_comment(self):
        """Should use <!-- --> comment style for Markdown format."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier0_base_artifact.jinja2")

        result = template.render(
            artifact_type="research",
            version_hash="b4e8f3c2",
            timestamp="2026-01-23T09:15:00Z",
            output_path="docs/development/issue72/research.md",
            format="markdown"
        )

        assert result.startswith("<!-- SCAFFOLD: research:b4e8f3c2")
        assert " -->" in result
        assert "2026-01-23T09:15:00Z" in result
        assert "docs/development/issue72/research.md" in result

    def test_render_shell_format_uses_hash_comment(self):
        """Should use # comment style for shell format."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier0_base_artifact.jinja2")

        result = template.render(
            artifact_type="script",
            version_hash="d7e9f0a1",
            timestamp="2026-01-23T12:00:00Z",
            output_path="scripts/deploy.sh",
            format="shell"
        )

        assert result.startswith("# SCAFFOLD: script:d7e9f0a1")

    def test_render_unknown_format_uses_html_comment(self):
        """Should default to HTML comment for unknown formats."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier0_base_artifact.jinja2")

        result = template.render(
            artifact_type="config",
            version_hash="e8f1a2b3",
            timestamp="2026-01-23T13:00:00Z",
            output_path="config.xml",
            format="xml"
        )

        assert result.startswith("<!-- SCAFFOLD: config:e8f1a2b3")
        assert " -->" in result


class TestTier0BaseArtifactBlocks:
    """Test Tier 0 block structure for inheritance."""

    def test_has_scaffold_metadata_block(self):
        """Should define scaffold_metadata block for overriding."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier0_base_artifact.jinja2")

        # Verify block exists by checking rendering works (2-line format)
        result = template.render(
            artifact_type="test",
            version_hash="12345678",
            timestamp="2026-01-23T10:00:00Z",
            output_path="test.py",
            format="python"
        )

        lines = result.strip().split("\n")
        # Line 1: filepath
        assert lines[0] == "# test.py"
        # Line 2: metadata (no SCAFFOLD: prefix)
        assert "template=test" in lines[1]
        assert "version=12345678" in lines[1]

    def test_has_content_block(self):
        """Should define empty content block for child templates."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier0_base_artifact.jinja2")

        result = template.render(
            artifact_type="test",
            version_hash="12345678",
            timestamp="2026-01-23T10:00:00Z",
            output_path="test.py",
            format="python"
        )

        # Content block is empty in Tier 0, only metadata should be present
        lines = result.strip().split("\n")
        assert len(lines) == 1  # Only SCAFFOLD header


class TestTier0BaseArtifactMetadata:
    """Test TEMPLATE_METADATA structure."""

    def test_template_has_metadata_comment(self):
        """Should have TEMPLATE_METADATA in Jinja2 comment."""
        template_path = TEMPLATE_DIR / "tier0_base_artifact.jinja2"
        content = template_path.read_text(encoding="utf-8")

        assert "TEMPLATE_METADATA:" in content
        assert "template_id: tier0_base_artifact" in content
        assert 'version: "1.0.0"' in content
        assert "tier: 0" in content

    def test_metadata_lists_required_variables(self):
        """Should document required variables in metadata."""
        template_path = TEMPLATE_DIR / "tier0_base_artifact.jinja2"
        content = template_path.read_text(encoding="utf-8")

        # Check required variables are documented
        assert "artifact_type" in content
        assert "version_hash" in content
        assert "timestamp" in content
        assert "output_path" in content
        assert "format" in content

    def test_metadata_lists_exported_blocks(self):
        """Should document exported blocks in metadata."""
        template_path = TEMPLATE_DIR / "tier0_base_artifact.jinja2"
        content = template_path.read_text(encoding="utf-8")

        assert "exports_blocks:" in content
        assert "scaffold_metadata" in content
        assert "content" in content
