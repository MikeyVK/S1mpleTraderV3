"""Unit tests for TemplateEngine (Issue #108 Cycle 1).

Tests TemplateEngine extracted from mcp_server/scaffolding/renderer.py
to backend/services/template_engine.py for reusability.
"""

from pathlib import Path

import pytest
from jinja2 import TemplateNotFound, UndefinedError

from backend.services.template_engine import TemplateEngine


class TestTemplateEngineInitialization:
    """Test TemplateEngine initialization and configuration."""

    def test_accepts_template_root_parameter(self) -> None:
        """TemplateEngine accepts template_root as Path or str."""
        template_root = Path("mcp_server/scaffolding/templates")

        # Should accept Path
        engine = TemplateEngine(template_root=template_root)
        assert engine.template_root == template_root

        # Should accept str
        engine_str = TemplateEngine(template_root=str(template_root))
        assert engine_str.template_root == template_root

    def test_raises_on_nonexistent_root(self) -> None:
        """TemplateEngine raises ValueError if root doesn't exist."""
        with pytest.raises(ValueError, match="Template root does not exist"):
            TemplateEngine(template_root="/nonexistent/path")


class TestTemplateEngineRendering:
    """Test basic template rendering functionality."""

    @pytest.fixture
    def engine(self) -> TemplateEngine:
        """Provide TemplateEngine with test templates."""
        template_root = Path("mcp_server/scaffolding/templates")
        return TemplateEngine(template_root=template_root)

    def test_renders_simple_template(self, engine: TemplateEngine) -> None:
        """TemplateEngine renders template with context variables."""
        # Use a simple tier0 template
        output = engine.render(
            "tier0_base_artifact.jinja2",
            artifact_type="test",
            version_hash="abc123",
            timestamp="2026-02-13T15:00:00Z",
            output_path="test.py",
            format="python",
        )

        assert "test.py" in output
        assert "template=test" in output
        assert "version=abc123" in output

    def test_raises_on_missing_template(self, engine: TemplateEngine) -> None:
        """TemplateEngine raises TemplateNotFound for missing templates."""
        with pytest.raises(TemplateNotFound):
            engine.render("nonexistent_template.jinja2")


class TestTemplateEngineInheritance:
    """Test 5-tier template inheritance support (Issue #72)."""

    @pytest.fixture
    def engine(self) -> TemplateEngine:
        """Provide TemplateEngine with test templates."""
        template_root = Path("mcp_server/scaffolding/templates")
        return TemplateEngine(template_root=template_root)

    def test_supports_extends_chain(self, engine: TemplateEngine) -> None:
        """TemplateEngine resolves {% extends %} inheritance chain."""
        # Use dto.py template which extends tier2 → tier1 → tier0
        output = engine.render(
            "concrete/dto.py.jinja2",
            artifact_type="dto",
            version_hash="test_v1",
            timestamp="2026-02-13T15:00:00Z",
            output_path="test_dto.py",
            format="python",
            name="TestDTO",
            layer="dtos",
            dependencies=[],
            description="Test DTO",
            fields=[{"name": "id", "type": "str", "description": "ID"}],
            validators=[],
            examples=["TestDTO(id='test')"],
            frozen=True,
        )

        # Should have tier0 SCAFFOLD metadata
        assert "# test_dto.py" in output
        assert "template=dto" in output

        # Should have tier1 module structure
        assert "@layer: dtos" in output

        # Should have tier2 Python imports
        assert "from pydantic import" in output

        # Should have concrete DTO class
        assert "class TestDTO" in output


class TestTemplateEngineCustomFilters:
    """Test custom Jinja2 filters."""

    @pytest.fixture
    def engine(self) -> TemplateEngine:
        """Provide TemplateEngine with test templates."""
        template_root = Path("mcp_server/scaffolding/templates")
        return TemplateEngine(template_root=template_root)

    def test_pascalcase_filter(self, engine: TemplateEngine) -> None:
        """TemplateEngine provides pascalcase filter."""
        # Create test template inline
        template_str = "{{ name | pascalcase }}"
        output = engine.env.from_string(template_str).render(name="test_name")
        assert output == "TestName"

    def test_snakecase_filter(self, engine: TemplateEngine) -> None:
        """TemplateEngine provides snakecase filter."""
        template_str = "{{ name | snakecase }}"
        output = engine.env.from_string(template_str).render(name="TestName")
        assert output == "test_name"

    def test_kebabcase_filter(self, engine: TemplateEngine) -> None:
        """TemplateEngine provides kebabcase filter."""
        template_str = "{{ name | kebabcase }}"
        output = engine.env.from_string(template_str).render(name="TestName")
        assert output == "test-name"

    def test_validate_identifier_filter(self, engine: TemplateEngine) -> None:
        """TemplateEngine provides validate_identifier filter."""
        template_str = "{{ name | validate_identifier }}"

        # Valid identifier
        output = engine.env.from_string(template_str).render(name="valid_name")
        assert output == "valid_name"

        # Invalid identifier should raise
        with pytest.raises((ValueError, UndefinedError)):  # Jinja2 error from filter
            engine.env.from_string(template_str).render(name="123invalid")


class TestTemplateEngineErrorHandling:
    """Test error handling and messages."""

    @pytest.fixture
    def engine(self) -> TemplateEngine:
        """Provide TemplateEngine with test templates."""
        template_root = Path("mcp_server/scaffolding/templates")
        return TemplateEngine(template_root=template_root)

    def test_template_not_found_message(self, engine: TemplateEngine) -> None:
        """TemplateNotFound includes helpful template name."""
        with pytest.raises(TemplateNotFound) as exc_info:
            engine.render("missing/template.jinja2")

        assert "missing/template.jinja2" in str(exc_info.value)

    def test_missing_variable_error(self, engine: TemplateEngine) -> None:
        """Missing required variable raises clear error."""
        # Create template that truly requires a variable
        template_str = "{{ required_var.field }}"  # Will raise on missing required_var

        with pytest.raises((UndefinedError, Exception)) as exc_info:
            engine.env.from_string(template_str).render()

        # Error should mention undefined/missing
        error_msg = str(exc_info.value).lower()
        assert "undefined" in error_msg or "required_var" in error_msg
