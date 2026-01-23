"""
Tests for Tier 1 base templates (Issue #72 Task 1.3).

RED phase: Tests for tier1_base_{code,document,config}.jinja2 inheritance
from Tier 0, block structure, and format-specific patterns.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"


class TestTier1CodeTemplate:
    """Test tier1_base_code.jinja2 template."""

    def test_inherits_from_tier0(self):
        """Should extend tier0_base_artifact.jinja2."""
        template_path = TEMPLATE_DIR / "tier1_base_code.jinja2"
        content = template_path.read_text(encoding="utf-8")

        assert 'extends "tier0_base_artifact.jinja2"' in content

    def test_renders_with_scaffold_metadata(self):
        """Should include SCAFFOLD metadata from Tier 0."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_code.jinja2")

        result = template.render(
            artifact_type="worker",
            version_hash="12345678",
            timestamp="2026-01-23T10:00:00Z",
            output_path="src/workers/test.py",
            format="python",
            class_name="TestWorker",
            class_docstring="Test worker class"
        )

        assert result.startswith("# SCAFFOLD: worker:12345678")
        assert "2026-01-23T10:00:00Z" in result

    def test_renders_class_structure(self):
        """Should render class structure block."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_code.jinja2")

        result = template.render(
            artifact_type="worker",
            version_hash="12345678",
            timestamp="2026-01-23T10:00:00Z",
            output_path="src/workers/test.py",
            format="python",
            class_name="MyWorker",
            class_docstring="Worker for processing tasks"
        )

        assert "class MyWorker:" in result
        assert '"""Worker for processing tasks"""' in result
        assert "pass" in result

    def test_renders_imports_sections(self):
        """Should render imports in organized sections."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_code.jinja2")

        result = template.render(
            artifact_type="worker",
            version_hash="12345678",
            timestamp="2026-01-23T10:00:00Z",
            output_path="src/workers/test.py",
            format="python",
            class_name="TestWorker",
            class_docstring="Test",
            imports={
                "stdlib": ["import os", "from pathlib import Path"],
                "third_party": ["import yaml"],
                "project": ["from backend.core import Worker"]
            }
        )

        assert "import os" in result
        assert "from pathlib import Path" in result
        assert "import yaml" in result
        assert "from backend.core import Worker" in result


class TestTier1DocumentTemplate:
    """Test tier1_base_document.jinja2 template."""

    def test_inherits_from_tier0(self):
        """Should extend tier0_base_artifact.jinja2."""
        template_path = TEMPLATE_DIR / "tier1_base_document.jinja2"
        content = template_path.read_text(encoding="utf-8")

        assert 'extends "tier0_base_artifact.jinja2"' in content

    def test_renders_with_scaffold_metadata(self):
        """Should include SCAFFOLD metadata from Tier 0."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_document.jinja2")

        result = template.render(
            artifact_type="research",
            version_hash="abcd1234",
            timestamp="2026-01-23T09:00:00Z",
            output_path="docs/research.md",
            format="markdown",
            title="Issue #72 Research"
        )

        assert result.startswith("<!-- SCAFFOLD: research:abcd1234")
        assert " -->" in result

    def test_renders_document_title(self):
        """Should render document title as H1."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_document.jinja2")

        result = template.render(
            artifact_type="research",
            version_hash="abcd1234",
            timestamp="2026-01-23T09:00:00Z",
            output_path="docs/research.md",
            format="markdown",
            title="Template Library Design"
        )

        assert "# Template Library Design" in result

    def test_renders_sections(self):
        """Should render sections with H2 headings."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_document.jinja2")

        result = template.render(
            artifact_type="research",
            version_hash="abcd1234",
            timestamp="2026-01-23T09:00:00Z",
            output_path="docs/research.md",
            format="markdown",
            title="Research Doc",
            sections=[
                {"heading": "Background", "content": "Context for this research"},
                {"heading": "Findings", "content": "Results from investigation"}
            ]
        )

        assert "## Background" in result
        assert "Context for this research" in result
        assert "## Findings" in result
        assert "Results from investigation" in result


class TestTier1ConfigTemplate:
    """Test tier1_base_config.jinja2 template."""

    def test_inherits_from_tier0(self):
        """Should extend tier0_base_artifact.jinja2."""
        template_path = TEMPLATE_DIR / "tier1_base_config.jinja2"
        content = template_path.read_text(encoding="utf-8")

        assert 'extends "tier0_base_artifact.jinja2"' in content

    def test_renders_with_scaffold_metadata(self):
        """Should include SCAFFOLD metadata from Tier 0."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_config.jinja2")

        result = template.render(
            artifact_type="workflow",
            version_hash="ef123456",
            timestamp="2026-01-23T11:00:00Z",
            output_path=".github/workflows/ci.yaml",
            format="yaml",
            config_name="CI Pipeline"
        )

        assert result.startswith("# SCAFFOLD: workflow:ef123456")

    def test_renders_config_name(self):
        """Should render config name field."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_config.jinja2")

        result = template.render(
            artifact_type="workflow",
            version_hash="ef123456",
            timestamp="2026-01-23T11:00:00Z",
            output_path=".github/workflows/ci.yaml",
            format="yaml",
            config_name="CI Workflow"
        )

        assert "name: CI Workflow" in result

    def test_renders_config_entries(self):
        """Should render key-value config entries."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_config.jinja2")

        result = template.render(
            artifact_type="workflow",
            version_hash="ef123456",
            timestamp="2026-01-23T11:00:00Z",
            output_path=".github/workflows/ci.yaml",
            format="yaml",
            config_name="CI",
            config_entries={
                "on": "push",
                "jobs": "build",
                "runs-on": "ubuntu-latest"
            }
        )

        assert "on: push" in result
        assert "jobs: build" in result
        assert "runs-on: ubuntu-latest" in result


class TestTier1MetadataStructure:
    """Test TEMPLATE_METADATA structure in Tier 1 templates."""

    def test_code_template_has_metadata(self):
        """Should have TEMPLATE_METADATA with tier=1."""
        template_path = TEMPLATE_DIR / "tier1_base_code.jinja2"
        content = template_path.read_text(encoding="utf-8")

        assert "TEMPLATE_METADATA:" in content
        assert "template_id: tier1_base_code" in content
        assert "tier: 1" in content
        assert "parent: tier0_base_artifact" in content

    def test_document_template_has_metadata(self):
        """Should have TEMPLATE_METADATA with tier=1."""
        template_path = TEMPLATE_DIR / "tier1_base_document.jinja2"
        content = template_path.read_text(encoding="utf-8")

        assert "TEMPLATE_METADATA:" in content
        assert "template_id: tier1_base_document" in content
        assert "tier: 1" in content

    def test_config_template_has_metadata(self):
        """Should have TEMPLATE_METADATA with tier=1."""
        template_path = TEMPLATE_DIR / "tier1_base_config.jinja2"
        content = template_path.read_text(encoding="utf-8")

        assert "TEMPLATE_METADATA:" in content
        assert "template_id: tier1_base_config" in content
        assert "tier: 1" in content
