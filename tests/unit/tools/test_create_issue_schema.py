"""C9 RED: input_schema for CreateIssueTool must not contain $ref or $defs.

VS Code / Copilot Chat does not resolve JSON Schema $ref references when
constructing MCP tool call arguments. If the schema contains
  body: {"$ref": "#/$defs/IssueBody"}
Claude cannot build the nested object and returns "no response".

Fix: override input_schema in CreateIssueTool to inline all $ref references
so that the schema is fully self-contained (no $defs, no $ref).
"""

import json

import pytest

from mcp_server.tools.issue_tools import CreateIssueTool


class TestCreateIssueInputSchemaNoRefs:
    """CreateIssueTool.input_schema must be fully inlined — no $ref / $defs."""

    @pytest.fixture
    def schema(self) -> dict:  # type: ignore[type-arg]
        tool = CreateIssueTool.__new__(CreateIssueTool)
        return tool.input_schema

    def test_schema_has_no_defs_key(self, schema: dict) -> None:  # type: ignore[type-arg]
        """$defs key must be absent from the top-level schema."""
        assert "$defs" not in schema, (
            "input_schema must not contain $defs — use inlined properties instead"
        )

    def test_schema_body_has_no_ref(self, schema: dict) -> None:  # type: ignore[type-arg]
        """body property must not be a $ref — it must be inlined."""
        body_prop = schema.get("properties", {}).get("body", {})
        assert "$ref" not in body_prop, (
            "body property must not use $ref — inline IssueBody properties directly"
        )

    def test_schema_body_is_object_type(self, schema: dict) -> None:  # type: ignore[type-arg]
        """body property must declare type: object."""
        body_prop = schema.get("properties", {}).get("body", {})
        assert body_prop.get("type") == "object", (
            "body property must have type: object after $ref resolution"
        )

    def test_schema_body_has_problem_property(self, schema: dict) -> None:  # type: ignore[type-arg]
        """body.properties.problem must exist after inlining."""
        body_prop = schema.get("properties", {}).get("body", {})
        body_properties = body_prop.get("properties", {})
        assert "problem" in body_properties, (
            "body.properties.problem must exist after $ref is resolved"
        )

    def test_schema_has_no_ref_anywhere(self, schema: dict) -> None:  # type: ignore[type-arg]
        """No $ref should appear anywhere in the serialized schema."""
        serialized = json.dumps(schema)
        assert '"$ref"' not in serialized, (
            "input_schema must not contain any $ref references — all must be inlined"
        )
