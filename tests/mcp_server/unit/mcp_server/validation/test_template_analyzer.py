# tests/unit/mcp_server/validation/test_template_analyzer.py
"""
Unit tests for TemplateAnalyzer.

Tests according to TDD principles with comprehensive coverage.

@layer: Tests (Unit)
@dependencies: [pytest]
"""

# Standard library
from pathlib import Path

# Third-party
import pytest

# Module under test
from mcp_server.validation.template_analyzer import TemplateAnalyzer


class TestTemplateAnalyzer:
    """Test suite for TemplateAnalyzer."""

    @pytest.fixture
    def template_root(self, tmp_path: Path) -> Path:
        """Fixture for temporary template root directory."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        return templates_dir

    @pytest.fixture
    def analyzer(self, template_root: Path) -> TemplateAnalyzer:
        """Fixture for TemplateAnalyzer instance."""
        return TemplateAnalyzer(template_root)

    def test_extract_metadata_with_frontmatter(
        self, analyzer: TemplateAnalyzer, template_root: Path
    ) -> None:
        """Test extracting metadata from template with YAML frontmatter."""
        # Arrange
        template_file = template_root / "test.jinja2"
        template_file.write_text("""
{#- TEMPLATE_METADATA:
  enforcement: STRICT
  level: format
  version: "2.0"
  validates:
    strict:
      - rule: test_rule
        description: "Test rule"
-#}
{# Regular comment #}
<div>{{ content }}</div>
""")

        # Act
        metadata = analyzer.extract_metadata(template_file)

        # Assert
        assert metadata["enforcement"] == "STRICT"
        assert metadata["level"] == "format"
        assert metadata["version"] == "2.0"
        assert "strict" in metadata["validates"]
        assert len(metadata["validates"]["strict"]) == 1

    def test_extract_metadata_without_frontmatter(
        self, analyzer: TemplateAnalyzer, template_root: Path
    ) -> None:
        """Test metadata extraction from template without frontmatter."""
        # Arrange
        template_file = template_root / "test.jinja2"
        template_file.write_text("""
{# Regular comment #}
<div>{{ content }}</div>
""")

        # Act
        metadata = analyzer.extract_metadata(template_file)

        # Assert
        assert metadata == {}

    def test_extract_metadata_invalid_yaml(
        self, analyzer: TemplateAnalyzer, template_root: Path
    ) -> None:
        """Test extracting metadata with invalid YAML raises ValueError."""
        # Arrange
        template_file = template_root / "test.jinja2"
        template_file.write_text("""
{#- TEMPLATE_METADATA:
  invalid: [unclosed
-#}
""")

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to parse"):
            analyzer.extract_metadata(template_file)

    def test_get_base_template_with_extends(
        self, analyzer: TemplateAnalyzer, template_root: Path
    ) -> None:
        """Test resolving base template when template extends another."""
        # Arrange
        base_dir = template_root / "base"
        base_dir.mkdir()
        base_template = base_dir / "base_component.py.jinja2"
        base_template.write_text("Base content")

        template_file = template_root / "worker.py.jinja2"
        template_file.write_text("""
{% extends "base/base_component.py.jinja2" %}
""")

        # Act
        base = analyzer.get_base_template(template_file)

        # Assert
        assert base is not None
        assert base.name == "base_component.py.jinja2"

    def test_get_base_template_without_extends(
        self, analyzer: TemplateAnalyzer, template_root: Path
    ) -> None:
        """Test get_base_template returns None when no inheritance."""
        # Arrange
        template_file = template_root / "test.jinja2"
        template_file.write_text("<div>{{ content }}</div>")

        # Act
        base = analyzer.get_base_template(template_file)

        # Assert
        assert base is None

    def test_get_inheritance_chain(self, analyzer: TemplateAnalyzer, template_root: Path) -> None:
        """Test getting full inheritance chain from specific to base."""
        # Arrange
        base_dir = template_root / "base"
        base_dir.mkdir()
        base_template = base_dir / "base_component.py.jinja2"
        base_template.write_text("Base content")

        worker_template = template_root / "worker.py.jinja2"
        worker_template.write_text('{% extends "base/base_component.py.jinja2" %}')

        # Act
        chain = analyzer.get_inheritance_chain(worker_template)

        # Assert
        assert len(chain) == 2
        assert chain[0].name == "worker.py.jinja2"
        assert chain[1].name == "base_component.py.jinja2"

    def test_merge_metadata_concatenates_strict_rules(self, analyzer: TemplateAnalyzer) -> None:
        """Test merging metadata concatenates strict rules."""
        # Arrange
        child = {"validates": {"strict": [{"rule": "child_rule", "description": "Child"}]}}
        parent = {"validates": {"strict": [{"rule": "parent_rule", "description": "Parent"}]}}

        # Act
        merged = analyzer.merge_metadata(child, parent)

        # Assert
        assert len(merged["validates"]["strict"]) == 2
        assert merged["validates"]["strict"][0]["rule"] == "child_rule"
        assert merged["validates"]["strict"][1]["rule"] == "parent_rule"

    def test_merge_metadata_child_overrides_enforcement(self, analyzer: TemplateAnalyzer) -> None:
        """Test child enforcement level overrides parent."""
        # Arrange
        child = {"enforcement": "ARCHITECTURAL"}
        parent = {"enforcement": "STRICT"}

        # Act
        merged = analyzer.merge_metadata(child, parent)

        # Assert
        assert merged["enforcement"] == "ARCHITECTURAL"

    def test_extract_jinja_variables(self, analyzer: TemplateAnalyzer, template_root: Path) -> None:
        """Test extracting undeclared Jinja2 variables from template."""
        # Arrange
        template_file = template_root / "test.jinja2"
        template_file.write_text("""
<div class="{{ class_name }}">
    <h1>{{ title }}</h1>
    <p>{{ description }}</p>
</div>
""")

        # Act
        variables = analyzer.extract_jinja_variables(template_file)

        # Assert
        assert "class_name" in variables
        assert "title" in variables
        assert "description" in variables
