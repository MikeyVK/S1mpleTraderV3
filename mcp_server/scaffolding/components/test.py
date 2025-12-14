"""Test Scaffolder Component."""
from typing import Any

from mcp_server.core.exceptions import ValidationError
from mcp_server.scaffolding.base import BaseScaffolder
from mcp_server.scaffolding.utils import validate_pascal_case


class TestScaffolder(BaseScaffolder):
    """Scaffolds Test files."""

    def validate(self, **kwargs: Any) -> bool:
        """Validate test arguments."""
        if "name" in kwargs:
            validate_pascal_case(kwargs["name"])

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
        self.validate(name=name, **kwargs)
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

        return str(self.renderer.render(
            "components/dto_test.py.jinja2",
            dto_name=name,
            **kwargs
        ))

    def _scaffold_worker_test(self, name: str, **kwargs: Any) -> str:
        """Scaffold Worker tests."""
        return str(self.renderer.render(
            "components/worker_test.py.jinja2",
            worker_name=name,
            **kwargs
        ))
