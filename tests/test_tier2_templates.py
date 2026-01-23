"""
Tests for Tier 2 language base templates (Issue #72 Task 1.4).

RED phase: Tests for tier2_base_{python,markdown,yaml}.jinja2 inheritance
from Tier 1, language-specific patterns, and SCAFFOLD metadata propagation.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


class TestTier2PythonTemplate:
    """Tests for tier2_base_python.jinja2."""

    @staticmethod
    def get_env() -> Environment:
        """Get Jinja2 environment with templates directory."""
        templates_dir = Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
        return Environment(loader=FileSystemLoader(str(templates_dir)))

    def test_inherits_from_tier1_code(self):
        """Tier 2 Python template should inherit from Tier 1 CODE template."""
        templates_dir = Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
        template_path = templates_dir / "tier2_base_python.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert 'extends "tier1_base_code.jinja2"' in content

    def test_renders_with_tier0_scaffold_metadata(self):
        """Tier 2 Python should propagate Tier 0 SCAFFOLD metadata via inheritance chain."""
        env = self.get_env()
        template = env.get_template("tier2_base_python.jinja2")
        context = {
            "artifact_type": "dto",
            "format": "python",
            "class_name": "TestDTO",
        }
        result = template.render(context)
        assert "SCAFFOLD" in result
        assert "dto:" in result  # Compact format: "# SCAFFOLD: dto: |  | "

    def test_renders_python_typing_imports(self):
        """Tier 2 Python should render typing imports."""
        env = self.get_env()
        template = env.get_template("tier2_base_python.jinja2")
        context = {
            "artifact_type": "dto",
            "format": "python",
            "class_name": "TestDTO",
            "type_imports": ["Optional", "List", "Dict"],
        }
        result = template.render(context)
        assert "from typing import Optional, List, Dict" in result

    def test_renders_class_with_docstring(self):
        """Tier 2 Python should render class with docstring."""
        env = self.get_env()
        template = env.get_template("tier2_base_python.jinja2")
        context = {
            "artifact_type": "dto",
            "format": "python",
            "class_name": "TestDTO",
            "docstring": "Test data transfer object.",
        }
        result = template.render(context)
        assert "class TestDTO:" in result
        assert '"""Test data transfer object."""' in result

    def test_renders_init_with_typed_params(self):
        """Tier 2 Python should render __init__ with typed parameters."""
        env = self.get_env()
        template = env.get_template("tier2_base_python.jinja2")
        context = {
            "artifact_type": "dto",
            "format": "python",
            "class_name": "TestDTO",
            "init_params": [
                {"name": "id", "type": "str"},
                {"name": "value", "type": "int"},
            ],
        }
        result = template.render(context)
        assert "def __init__(self, id: str, value: int):" in result
        assert "self.id = id" in result
        assert "self.value = value" in result

    def test_renders_dunder_methods(self):
        """Tier 2 Python should render dunder methods with docstrings."""
        env = self.get_env()
        template = env.get_template("tier2_base_python.jinja2")
        context = {
            "artifact_type": "dto",
            "format": "python",
            "class_name": "TestDTO",
            "dunder_methods": [
                {"name": "str", "return_type": "str", "body": "return f'{self.id}'"},
            ],
        }
        result = template.render(context)
        assert "def __str__(self) -> str:" in result
        assert "return f'{self.id}'" in result


class TestTier2MarkdownTemplate:
    """Tests for tier2_base_markdown.jinja2."""

    @staticmethod
    def get_env() -> Environment:
        """Get Jinja2 environment with templates directory."""
        templates_dir = Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
        return Environment(loader=FileSystemLoader(str(templates_dir)))

    def test_inherits_from_tier1_document(self):
        """Tier 2 Markdown template should inherit from Tier 1 DOCUMENT template."""
        templates_dir = Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
        template_path = templates_dir / "tier2_base_markdown.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert 'extends "tier1_base_document.jinja2"' in content

    def test_renders_with_tier0_scaffold_metadata(self):
        """Tier 2 Markdown should propagate Tier 0 SCAFFOLD metadata via inheritance chain."""
        env = self.get_env()
        template = env.get_template("tier2_base_markdown.jinja2")
        context = {
            "artifact_type": "design",
            "format": "markdown",
            "title": "Test Design",
        }
        result = template.render(context)
        assert "SCAFFOLD" in result
        assert "design:" in result  # Compact format: "<!-- SCAFFOLD: design: |  |  -->"

    def test_renders_yaml_frontmatter(self):
        """Tier 2 Markdown should render YAML frontmatter."""
        env = self.get_env()
        template = env.get_template("tier2_base_markdown.jinja2")
        context = {
            "artifact_type": "design",
            "format": "markdown",
            "title": "Test Design",
            "frontmatter": {"author": "Alice", "date": "2026-01-23"},
        }
        result = template.render(context)
        assert "---" in result
        assert "author: Alice" in result
        assert "date: 2026-01-23" in result

    def test_renders_code_blocks(self):
        """Tier 2 Markdown should render code blocks with language tags."""
        env = self.get_env()
        template = env.get_template("tier2_base_markdown.jinja2")
        context = {
            "artifact_type": "design",
            "format": "markdown",
            "title": "Test Design",
            "code_blocks": [
                {"language": "python", "code": "print('hello')"},
                {"language": "yaml", "code": "key: value"},
            ],
        }
        result = template.render(context)
        assert "```python" in result
        assert "print('hello')" in result
        assert "```yaml" in result
        assert "key: value" in result


class TestTier2YAMLTemplate:
    """Tests for tier2_base_yaml.jinja2."""

    @staticmethod
    def get_env() -> Environment:
        """Get Jinja2 environment with templates directory."""
        templates_dir = Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
        return Environment(loader=FileSystemLoader(str(templates_dir)))

    def test_inherits_from_tier1_config(self):
        """Tier 2 YAML template should inherit from Tier 1 CONFIG template."""
        templates_dir = Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
        template_path = templates_dir / "tier2_base_yaml.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert 'extends "tier1_base_config.jinja2"' in content

    def test_renders_with_tier0_scaffold_metadata(self):
        """Tier 2 YAML should propagate Tier 0 SCAFFOLD metadata via inheritance chain."""
        env = self.get_env()
        template = env.get_template("tier2_base_yaml.jinja2")
        context = {
            "artifact_type": "config",
            "format": "yaml",
            "name": "test_config",
        }
        result = template.render(context)
        assert "SCAFFOLD" in result
        assert "config:" in result  # Compact format: "# SCAFFOLD: config: |  | "

    def test_renders_header_comment(self):
        """Tier 2 YAML should render header comment."""
        env = self.get_env()
        template = env.get_template("tier2_base_yaml.jinja2")
        context = {
            "artifact_type": "config",
            "format": "yaml",
            "name": "test_config",
            "header_comment": "Configuration file for testing",
        }
        result = template.render(context)
        assert "# Configuration file for testing" in result

    def test_renders_nested_structures(self):
        """Tier 2 YAML should render nested structures with indentation."""
        env = self.get_env()
        template = env.get_template("tier2_base_yaml.jinja2")
        context = {
            "artifact_type": "config",
            "format": "yaml",
            "name": "test_config",
            "nested_structures": [
                {
                    "key": "database",
                    "entries": [
                        {"key": "host", "value": "localhost"},
                        {"key": "port", "value": 5432},
                    ],
                },
            ],
        }
        result = template.render(context)
        assert "database:" in result
        assert "  host: localhost" in result
        assert "  port: 5432" in result


class TestTier2MetadataStructure:
    """Tests for TEMPLATE_METADATA structure in Tier 2 templates."""

    @staticmethod
    def get_env():
        """Get Jinja2 environment with templates directory."""
        templates_dir = Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
        return Environment(loader=FileSystemLoader(str(templates_dir)))

    def test_python_template_has_metadata(self):
        """Tier 2 Python template should have TEMPLATE_METADATA."""
        templates_dir = Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
        template_path = templates_dir / "tier2_base_python.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert "TEMPLATE_METADATA:" in content
        assert "template_id: tier2_base_python" in content
        assert "tier: 2" in content
        assert "parent: tier1_base_code" in content

    def test_markdown_template_has_metadata(self):
        """Tier 2 Markdown template should have TEMPLATE_METADATA."""
        templates_dir = Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
        template_path = templates_dir / "tier2_base_markdown.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert "TEMPLATE_METADATA:" in content
        assert "template_id: tier2_base_markdown" in content
        assert "tier: 2" in content
        assert "parent: tier1_base_document" in content

    def test_yaml_template_has_metadata(self):
        """Tier 2 YAML template should have TEMPLATE_METADATA."""
        templates_dir = Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
        template_path = templates_dir / "tier2_base_yaml.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert "TEMPLATE_METADATA:" in content
        assert "template_id: tier2_base_yaml" in content
        assert "tier: 2" in content
        assert "parent: tier1_base_config" in content
