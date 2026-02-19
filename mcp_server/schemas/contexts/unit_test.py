# mcp_server/schemas/contexts/unit_test.py
# template=schema version=74378193 created=2026-02-17T00:00Z updated=
"""UnitTestContext schema.

Context schema for test_unit artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Standard library
from typing import Any

# Third-party
from pydantic import ConfigDict, Field, field_validator

# Project modules
from mcp_server.schemas.base import BaseContext


class UnitTestContext(BaseContext):
    """Context schema for test_unit artifact scaffolding (user-facing).

    User provides unit-test-specific fields when scaffolding unit test artifacts.
    Does NOT include lifecycle fields - those are added by UnitTestRenderContext.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    module_under_test: str = Field(
        description="Fully qualified module path (e.g. 'mcp_server.schemas.contexts.dto')",
    )
    test_class_name: str = Field(
        description="Name of the test class (PascalCase, e.g. TestDTOContext)",
    )
    test_description: str | None = Field(
        default=None,
        description="Optional test suite description",
    )
    test_focus: str | None = Field(
        default=None,
        description="What this test suite focuses on (docstring line)",
    )
    additional_responsibility: str | None = Field(
        default=None,
        description="Extra responsibility line in docstring",
    )
    imported_classes: list[str] = Field(
        default_factory=list,
        description="List of class names to import from module_under_test",
    )
    has_mocks: bool = Field(
        default=True,
        description="If True, include unittest.mock imports",
    )
    has_async_tests: bool = Field(
        default=False,
        description="If True, include asyncio imports and pytest-asyncio markers",
    )
    has_pydantic: bool = Field(
        default=False,
        description="If True, include pydantic ValidationError import",
    )
    test_methods: list[Any] = Field(
        default_factory=list,
        description="List of test method definitions for the template",
    )

    @field_validator("module_under_test")
    @classmethod
    def validate_module_not_empty(cls, v: str) -> str:
        """Validate module_under_test is not empty."""
        if not v or not v.strip():
            raise ValueError("module_under_test must be non-empty string")
        return v

    @field_validator("test_class_name")
    @classmethod
    def validate_test_class_name_not_empty(cls, v: str) -> str:
        """Validate test_class_name is not empty."""
        if not v or not v.strip():
            raise ValueError("test_class_name must be non-empty string")
        return v
