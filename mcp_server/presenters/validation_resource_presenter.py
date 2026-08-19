# mcp_server\presenters\validation_resource_presenter.py
# template=generic version=e866e4ff created=2026-08-19T19:00Z updated=2026-08-19T19:05Z
"""Presenter for validation error schemas as embedded resources.

@layer: Presentation
@dependencies: [json, pydantic, mcp_server.core.interfaces.ipresenter]
@responsibilities:
    - Implement IResourcePresenter protocol
    - Extract input_schema and return schema://validation PresentationResource
"""

import json
from typing import Any

from pydantic import BaseModel

from mcp_server.core.interfaces.ipresenter import IResourcePresenter
from mcp_server.schemas.error_outputs import ValidationErrorOutput
from mcp_server.schemas.presentation_output import PresentationResource


class ValidationResourcePresenter(IResourcePresenter):
    """Extracts and serializes validation schemas into embedded presentation resources."""

    def present_resources(
        self,
        tool_name: str,  # noqa: ARG002
        data: BaseModel | dict[str, Any],
    ) -> list[PresentationResource]:
        """Extract and format presentation resources from the execution data."""
        schema_dict: dict[str, Any] | None = None

        if isinstance(data, ValidationErrorOutput) and data.input_schema is not None:
            schema_dict = data.input_schema
        elif isinstance(data, dict):
            error_type = data.get("error_type")
            if error_type == "ValidationError" and "input_schema" in data:
                raw_schema = data["input_schema"]
                if isinstance(raw_schema, dict):
                    schema_dict = raw_schema

        if schema_dict is not None:
            return [
                PresentationResource(
                    uri="schema://validation",
                    mime_type="application/json",
                    content=json.dumps(schema_dict, indent=2),
                )
            ]

        return []
