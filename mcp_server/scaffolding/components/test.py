"""Test Scaffolder Component."""
from typing import Any

from mcp_server.core.exceptions import ExecutionError, ValidationError
from mcp_server.scaffolding.base import ComponentScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer


class TestScaffolder(ComponentScaffolder):
    """Scaffolds Test files."""

    def __init__(self, renderer: JinjaRenderer) -> None:
        """Initialize test scaffolder."""
        self.renderer = renderer

    def validate(self, **kwargs: Any) -> bool:
        """Validate test arguments."""
        if "test_type" not in kwargs:
            raise ValidationError("Missing 'test_type' (dto or worker)")
        return True

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a Test file.

        Args:
            name: Component name being tested.
            **kwargs: Test arguments:
                - test_type: 'dto' or 'worker'
                - module_path: Import path
                - ...

        Returns:
            Rendered Python code
        """
        self.validate(**kwargs)
        test_type = kwargs["test_type"]

        if test_type == "dto":
            return self._scaffold_dto_test(name, **kwargs)
        if test_type == "worker":
            return self._scaffold_worker_test(name, **kwargs)

        raise ValidationError(f"Unknown test_type: {test_type}")

    def _scaffold_dto_test(self, name: str, **kwargs: Any) -> str:
        """Scaffold DTO tests."""
        # Derive id_prefix if needed
        id_prefix = kwargs.get("id_prefix")
        if not id_prefix:
            clean_name = name.replace("DTO", "").replace("Plan", "")
            id_prefix = clean_name[:3].upper()
            kwargs["id_prefix"] = id_prefix

        # Combine fields
        required = kwargs.get("required_fields", [])
        optional = kwargs.get("optional_fields", [])
        kwargs["all_fields"] = required + optional

        try:
            return self.renderer.render(
                "components/dto_test.py.jinja2",
                dto_name=name,
                **kwargs
            )
        except ExecutionError:
            return self._render_dto_fallback(name, kwargs.get("module_path", "module"))

    def _scaffold_worker_test(self, name: str, **kwargs: Any) -> str:
        """Scaffold Worker tests."""
        try:
            return self.renderer.render(
                "components/worker_test.py.jinja2",
                worker_name=name,
                **kwargs
            )
        except ExecutionError:
            return self._render_worker_fallback(name, kwargs.get("module_path", "module"))

    def _render_dto_fallback(self, dto_name: str, module_path: str) -> str:
        """Fallback DTO test rendering."""
        return f'''"""Tests for {dto_name}."""
import pytest
from {module_path} import {dto_name}


class Test{dto_name}:
    """Tests for {dto_name} DTO."""

    def test_creation(self) -> None:
        """Test {dto_name} can be created."""
        # TODO: Add test implementation
        pass

    def test_immutability(self) -> None:
        """Test {dto_name} is immutable (frozen)."""
        # TODO: Add test implementation
        pass
'''

    def _render_worker_fallback(self, worker_name: str, module_path: str) -> str:
        """Fallback worker test rendering."""
        return f'''"""Tests for {worker_name}."""
import pytest
from {module_path} import {worker_name}


class Test{worker_name}Processing:
    """Tests for {worker_name} processing logic."""

    def test_process_valid_input(self) -> None:
        """Test processing with valid input."""
        # TODO: Add test implementation
        pass

    def test_process_invalid_input(self) -> None:
        """Test processing with invalid input raises error."""
        # TODO: Add test implementation
        pass


class Test{worker_name}ErrorHandling:
    """Tests for {worker_name} error handling."""

    def test_handles_missing_dependency(self) -> None:
        """Test graceful handling of missing dependencies."""
        # TODO: Add test implementation
        pass
'''
