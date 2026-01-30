"""
Unit tests for tier3_pattern_python_async.jinja2 template.

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib, mcp_server.scaffolding]
"""

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


@pytest.fixture
def jinja_env():
    """Create Jinja2 environment with test templates path."""
    templates_path = (
        Path(__file__).parent.parent.parent.parent
        / "mcp_server"
        / "scaffolding"
        / "templates"
    )
    return Environment(loader=FileSystemLoader(str(templates_path)))


class TestTier3PatternPythonAsync:
    """Test suite for tier3_pattern_python_async.jinja2 template."""

    def test_template_exists(self, jinja_env):
        """Test that template file exists and can be loaded."""
        template = jinja_env.get_template("tier3_pattern_python_async.jinja2")
        assert template is not None
        assert template.filename is not None

    def test_template_no_extends(self):
        """Test that tier3 pattern template does not extend (standalone blocks)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_async.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        # Tier3 patterns are standalone block libraries
        assert "{% extends" not in content

    def test_template_has_metadata(self):
        """Test that template contains TEMPLATE_METADATA."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_async.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content

    def test_has_pattern_async_imports_block(self):
        """Test that template defines pattern_async_imports block."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_async.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% macro pattern_async_imports" in content

    def test_has_pattern_async_methods_block(self):
        """Test that template defines pattern_async_methods block."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_async.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% macro pattern_async_methods" in content

    def test_has_pattern_async_context_managers_block(self):
        """Test that template defines pattern_async_context_managers block."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_async.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% macro pattern_async_context_managers" in content

    def test_pattern_async_imports_renders(self, jinja_env):
        """Test that pattern_async_imports macro renders correctly."""
        template = jinja_env.get_template("tier3_pattern_python_async.jinja2")
        from jinja2 import Template
        # Import the template and call the macro
        rendered = template.module.pattern_async_imports()
        assert "import asyncio" in rendered
        assert "from typing import" in rendered

    def test_pattern_async_methods_renders(self, jinja_env):
        """Test that pattern_async_methods macro renders async method structure."""
        template = jinja_env.get_template("tier3_pattern_python_async.jinja2")
        rendered = template.module.pattern_async_methods(
            method_name="process_data",
            params="data: str"
        )
        assert "async def process_data" in rendered
        assert "data: str" in rendered

    def test_pattern_async_context_managers_renders(self, jinja_env):
        """Test that pattern_async_context_managers macro renders."""
        template = jinja_env.get_template("tier3_pattern_python_async.jinja2")
        rendered = template.module.pattern_async_context_managers(
            context_name="resource_manager"
        )
        assert "async with" in rendered or "__aenter__" in rendered
        assert "resource_manager" in rendered

    def test_macro_imports_include_awaitable(self, jinja_env):
        """Test that async imports include Awaitable type."""
        template = jinja_env.get_template("tier3_pattern_python_async.jinja2")
        rendered = template.module.pattern_async_imports()
        assert "Awaitable" in rendered or "AsyncIterator" in rendered

    def test_macro_methods_support_await(self, jinja_env):
        """Test that async methods support await keyword."""
        template = jinja_env.get_template("tier3_pattern_python_async.jinja2")
        rendered = template.module.pattern_async_methods(
            method_name="fetch",
            params="url: str",
            body="return await http_client.get(url)"
        )
        assert "async def fetch" in rendered
        assert "await" in rendered
