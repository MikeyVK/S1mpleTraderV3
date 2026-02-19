# mcp_server/schemas/contexts/integration_test.py
# template=schema version=74378193 created=2026-02-17T00:00Z updated=
"""IntegrationTestContext schema.

Context schema for test_integration artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Standard library
from typing import Any

# Third-party
from pydantic import ConfigDict, Field, field_validator

# Project modules
from mcp_server.schemas.base import BaseContext


class IntegrationTestContext(BaseContext):
    """Context schema for test_integration artifact scaffolding (user-facing).

    User provides integration-test-specific fields when scaffolding integration test artifacts.
    Does NOT include lifecycle fields - those are added by IntegrationTestRenderContext.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    test_scenario: str = Field(
        description="Name of the integration scenario being tested (snake_case)",
    )
    test_class_name: str = Field(
        description="Name of the test class (PascalCase, e.g. TestScaffoldDTOE2E)",
    )
    test_description: str | None = Field(
        default=None,
        description="Optional test suite description",
    )
    managers_needed: list[str] = Field(
        default_factory=list,
        description="List of manager class names needed for the integration test",
    )
    workspace_fixture: bool = Field(
        default=True,
        description="If True, scaffold a temp_workspace pytest fixture",
    )
    test_methods: list[Any] = Field(
        default_factory=list,
        description="List of test method definitions for the template",
    )

    @field_validator("test_scenario")
    @classmethod
    def validate_test_scenario_not_empty(cls, v: str) -> str:
        """Validate test_scenario is not empty."""
        if not v or not v.strip():
            raise ValueError("test_scenario must be non-empty string")
        return v

    @field_validator("test_class_name")
    @classmethod
    def validate_test_class_name_not_empty(cls, v: str) -> str:
        """Validate test_class_name is not empty."""
        if not v or not v.strip():
            raise ValueError("test_class_name must be non-empty string")
        return v
