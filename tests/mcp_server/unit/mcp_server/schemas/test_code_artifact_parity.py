# tests/unit/mcp_server/schemas/test_code_artifact_parity.py
# template=generic version=74378193 created=2026-02-18T00:00Z updated=
"""Parity tests for Cycle 5: Schema fields vs template introspection variables.

Validates that each Pydantic context schema exposes exactly the same field names
(required + optional) as the corresponding Jinja2 template declares via its
introspection block.

This is the Single Source of Truth contract:
  Template introspection  ←→  Pydantic context schema

Per artifact type (7 types × 5 assertions = 35 tests):
1. Schema required fields ⊆ template required variables
2. Template required variables ⊆ schema required fields
3. Schema optional fields ⊆ template optional variables
4. Template optional variables ⊆ schema optional fields
5. No field appears in both required AND optional

Template path mapping:
  worker         → concrete/worker.py.jinja2
  tool           → concrete/tool.py.jinja2
  schema         → concrete/config_schema.py.jinja2
  service        → concrete/service_command.py.jinja2
  generic        → concrete/generic.py.jinja2
  unit_test      → concrete/test_unit.py.jinja2
  integration_test → concrete/test_integration.py.jinja2

@layer: Test Infrastructure
"""

# Standard library
import logging
from pathlib import Path

# Third-party
import pytest

# Project modules
from mcp_server.scaffolding.template_introspector import (
    TemplateSchema,
    introspect_template_with_inheritance,
)
from mcp_server.schemas.contexts.generic import GenericContext
from mcp_server.schemas.contexts.integration_test import IntegrationTestContext
from mcp_server.schemas.contexts.schema import SchemaContext
from mcp_server.schemas.contexts.service import ServiceContext
from mcp_server.schemas.contexts.tool import ToolContext
from mcp_server.schemas.contexts.unit_test import UnitTestContext
from mcp_server.schemas.contexts.worker import WorkerContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_TEMPLATE_ROOT = Path(__file__).parents[5] / "mcp_server" / "scaffolding" / "templates"

# Tier2 structural vars that exist in parent templates but are overridden in concrete templates.
# Concrete templates (test_unit, test_integration, worker, etc.) override all tier2 blocks,
# so these vars are never agent-provided. They must be excluded from parity comparisons.
_TIER2_STRUCTURAL_FIELDS: frozenset[str] = frozenset(
    {
        "base_classes",
        "class_docstring",
        "class_name",
        "docstring",
        "dunder_methods",
        "imports",
        "init_params",
        "type_imports",
    }
)

_TEMPLATE_MAP: dict[str, str] = {
    "worker": "concrete/worker.py.jinja2",
    "tool": "concrete/tool.py.jinja2",
    "schema": "concrete/config_schema.py.jinja2",
    "service": "concrete/service_command.py.jinja2",
    "generic": "concrete/generic.py.jinja2",
    "unit_test": "concrete/test_unit.py.jinja2",
    "integration_test": "concrete/test_integration.py.jinja2",
}

_SCHEMA_MAP: dict[str, type] = {
    "worker": WorkerContext,
    "tool": ToolContext,
    "schema": SchemaContext,
    "service": ServiceContext,
    "generic": GenericContext,
    "unit_test": UnitTestContext,
    "integration_test": IntegrationTestContext,
}


def _get_template_schema(artifact_type: str) -> TemplateSchema:
    """Introspect the Jinja2 template for the given artifact type.

    Filters out tier2 structural variables which exist in parent templates
    but are overridden (never user-provided) in concrete templates.
    """
    template_path = _TEMPLATE_MAP[artifact_type]
    raw = introspect_template_with_inheritance(_TEMPLATE_ROOT, template_path)
    return TemplateSchema(
        required=[v for v in raw.required if v not in _TIER2_STRUCTURAL_FIELDS],
        optional=[v for v in raw.optional if v not in _TIER2_STRUCTURAL_FIELDS],
    )


def _get_schema_required(schema_class: type) -> set[str]:
    """Return field names that are required (no default) in the Pydantic schema.

    Excludes system lifecycle fields (inherited from BaseContext internals).
    """
    required: set[str] = set()
    for name, field_info in schema_class.model_fields.items():
        if field_info.is_required():
            required.add(name)
    return required


def _get_schema_optional(schema_class: type) -> set[str]:
    """Return field names that are optional (have a default) in the Pydantic schema."""
    optional: set[str] = set()
    for name, field_info in schema_class.model_fields.items():
        if not field_info.is_required():
            optional.add(name)
    return optional


# ---------------------------------------------------------------------------
# WorkerContext parity
# ---------------------------------------------------------------------------


class TestWorkerContextParity:
    """Parity: WorkerContext fields ↔ worker.py.jinja2 introspection."""

    @pytest.fixture(scope="class")
    def template_schema(self) -> TemplateSchema:
        return _get_template_schema("worker")

    def test_schema_required_subset_of_template_required(
        self, template_schema: TemplateSchema
    ) -> None:
        """Schema required fields must all exist in template required variables."""
        schema_req = _get_schema_required(WorkerContext)
        template_req = set(template_schema.required)
        extra = schema_req - template_req
        assert not extra, (
            f"WorkerContext has required fields not in template: {sorted(extra)}\n"
            f"Template required: {sorted(template_req)}"
        )

    def test_template_required_subset_of_schema_required(
        self, template_schema: TemplateSchema
    ) -> None:
        """Template required variables must all be required in schema."""
        schema_req = _get_schema_required(WorkerContext)
        template_req = set(template_schema.required)
        missing = template_req - schema_req
        assert not missing, (
            f"Template requires fields missing from WorkerContext: {sorted(missing)}\n"
            f"Schema required: {sorted(schema_req)}"
        )

    def test_schema_optional_subset_of_template_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        """Schema optional fields must all exist in template optional variables."""
        schema_opt = _get_schema_optional(WorkerContext)
        template_opt = set(template_schema.optional)
        extra = schema_opt - template_opt
        assert not extra, (
            f"WorkerContext has optional fields not in template: {sorted(extra)}\n"
            f"Template optional: {sorted(template_opt)}"
        )

    def test_template_optional_subset_of_schema_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        """Template optional variables must all be optional in schema."""
        schema_opt = _get_schema_optional(WorkerContext)
        template_opt = set(template_schema.optional)
        missing = template_opt - schema_opt
        assert not missing, (
            f"Template optionals missing from WorkerContext: {sorted(missing)}\n"
            f"Schema optional: {sorted(schema_opt)}"
        )

    def test_no_field_in_both_required_and_optional(self, template_schema: TemplateSchema) -> None:
        """No field should appear in both required and optional."""
        overlap = set(template_schema.required) & set(template_schema.optional)
        assert not overlap, f"Fields in both required+optional: {sorted(overlap)}"


# ---------------------------------------------------------------------------
# ToolContext parity
# ---------------------------------------------------------------------------


class TestToolContextParity:
    """Parity: ToolContext fields ↔ tool.py.jinja2 introspection."""

    @pytest.fixture(scope="class")
    def template_schema(self) -> TemplateSchema:
        return _get_template_schema("tool")

    def test_schema_required_subset_of_template_required(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_req = _get_schema_required(ToolContext)
        template_req = set(template_schema.required)
        extra = schema_req - template_req
        assert not extra, (
            f"ToolContext has required fields not in template: {sorted(extra)}\n"
            f"Template required: {sorted(template_req)}"
        )

    def test_template_required_subset_of_schema_required(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_req = _get_schema_required(ToolContext)
        template_req = set(template_schema.required)
        missing = template_req - schema_req
        assert not missing, (
            f"Template requires fields missing from ToolContext: {sorted(missing)}\n"
            f"Schema required: {sorted(schema_req)}"
        )

    def test_schema_optional_subset_of_template_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_opt = _get_schema_optional(ToolContext)
        template_opt = set(template_schema.optional)
        extra = schema_opt - template_opt
        assert not extra, (
            f"ToolContext has optional fields not in template: {sorted(extra)}\n"
            f"Template optional: {sorted(template_opt)}"
        )

    def test_template_optional_subset_of_schema_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_opt = _get_schema_optional(ToolContext)
        template_opt = set(template_schema.optional)
        missing = template_opt - schema_opt
        assert not missing, (
            f"Template optionals missing from ToolContext: {sorted(missing)}\n"
            f"Schema optional: {sorted(schema_opt)}"
        )

    def test_no_field_in_both_required_and_optional(self, template_schema: TemplateSchema) -> None:
        overlap = set(template_schema.required) & set(template_schema.optional)
        assert not overlap, f"Fields in both required+optional: {sorted(overlap)}"


# ---------------------------------------------------------------------------
# SchemaContext parity
# ---------------------------------------------------------------------------


class TestSchemaContextParity:
    """Parity: SchemaContext fields ↔ config_schema.py.jinja2 introspection."""

    @pytest.fixture(scope="class")
    def template_schema(self) -> TemplateSchema:
        return _get_template_schema("schema")

    def test_schema_required_subset_of_template_required(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_req = _get_schema_required(SchemaContext)
        template_req = set(template_schema.required)
        extra = schema_req - template_req
        assert not extra, (
            f"SchemaContext has required fields not in template: {sorted(extra)}\n"
            f"Template required: {sorted(template_req)}"
        )

    def test_template_required_subset_of_schema_required(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_req = _get_schema_required(SchemaContext)
        template_req = set(template_schema.required)
        missing = template_req - schema_req
        assert not missing, (
            f"Template requires fields missing from SchemaContext: {sorted(missing)}\n"
            f"Schema required: {sorted(schema_req)}"
        )

    def test_schema_optional_subset_of_template_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_opt = _get_schema_optional(SchemaContext)
        template_opt = set(template_schema.optional)
        extra = schema_opt - template_opt
        assert not extra, (
            f"SchemaContext has optional fields not in template: {sorted(extra)}\n"
            f"Template optional: {sorted(template_opt)}"
        )

    def test_template_optional_subset_of_schema_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_opt = _get_schema_optional(SchemaContext)
        template_opt = set(template_schema.optional)
        missing = template_opt - schema_opt
        assert not missing, (
            f"Template optionals missing from SchemaContext: {sorted(missing)}\n"
            f"Schema optional: {sorted(schema_opt)}"
        )

    def test_no_field_in_both_required_and_optional(self, template_schema: TemplateSchema) -> None:
        overlap = set(template_schema.required) & set(template_schema.optional)
        assert not overlap, f"Fields in both required+optional: {sorted(overlap)}"


# ---------------------------------------------------------------------------
# ServiceContext parity
# ---------------------------------------------------------------------------


class TestServiceContextParity:
    """Parity: ServiceContext fields ↔ service_command.py.jinja2 introspection."""

    @pytest.fixture(scope="class")
    def template_schema(self) -> TemplateSchema:
        return _get_template_schema("service")

    def test_schema_required_subset_of_template_required(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_req = _get_schema_required(ServiceContext)
        template_req = set(template_schema.required)
        extra = schema_req - template_req
        assert not extra, (
            f"ServiceContext has required fields not in template: {sorted(extra)}\n"
            f"Template required: {sorted(template_req)}"
        )

    def test_template_required_subset_of_schema_required(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_req = _get_schema_required(ServiceContext)
        template_req = set(template_schema.required)
        missing = template_req - schema_req
        assert not missing, (
            f"Template requires fields missing from ServiceContext: {sorted(missing)}\n"
            f"Schema required: {sorted(schema_req)}"
        )

    def test_schema_optional_subset_of_template_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_opt = _get_schema_optional(ServiceContext)
        template_opt = set(template_schema.optional)
        extra = schema_opt - template_opt
        assert not extra, (
            f"ServiceContext has optional fields not in template: {sorted(extra)}\n"
            f"Template optional: {sorted(template_opt)}"
        )

    def test_template_optional_subset_of_schema_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_opt = _get_schema_optional(ServiceContext)
        template_opt = set(template_schema.optional)
        missing = template_opt - schema_opt
        assert not missing, (
            f"Template optionals missing from ServiceContext: {sorted(missing)}\n"
            f"Schema optional: {sorted(schema_opt)}"
        )

    def test_no_field_in_both_required_and_optional(self, template_schema: TemplateSchema) -> None:
        overlap = set(template_schema.required) & set(template_schema.optional)
        assert not overlap, f"Fields in both required+optional: {sorted(overlap)}"


# ---------------------------------------------------------------------------
# GenericContext parity
# ---------------------------------------------------------------------------


class TestGenericContextParity:
    """Parity: GenericContext fields ↔ generic.py.jinja2 introspection."""

    @pytest.fixture(scope="class")
    def template_schema(self) -> TemplateSchema:
        return _get_template_schema("generic")

    def test_schema_required_subset_of_template_required(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_req = _get_schema_required(GenericContext)
        template_req = set(template_schema.required)
        extra = schema_req - template_req
        assert not extra, (
            f"GenericContext has required fields not in template: {sorted(extra)}\n"
            f"Template required: {sorted(template_req)}"
        )

    def test_template_required_subset_of_schema_required(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_req = _get_schema_required(GenericContext)
        template_req = set(template_schema.required)
        missing = template_req - schema_req
        assert not missing, (
            f"Template requires fields missing from GenericContext: {sorted(missing)}\n"
            f"Schema required: {sorted(schema_req)}"
        )

    def test_schema_optional_subset_of_template_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_opt = _get_schema_optional(GenericContext)
        template_opt = set(template_schema.optional)
        extra = schema_opt - template_opt
        assert not extra, (
            f"GenericContext has optional fields not in template: {sorted(extra)}\n"
            f"Template optional: {sorted(template_opt)}"
        )

    def test_template_optional_subset_of_schema_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_opt = _get_schema_optional(GenericContext)
        template_opt = set(template_schema.optional)
        missing = template_opt - schema_opt
        assert not missing, (
            f"Template optionals missing from GenericContext: {sorted(missing)}\n"
            f"Schema optional: {sorted(schema_opt)}"
        )

    def test_no_field_in_both_required_and_optional(self, template_schema: TemplateSchema) -> None:
        overlap = set(template_schema.required) & set(template_schema.optional)
        assert not overlap, f"Fields in both required+optional: {sorted(overlap)}"


# ---------------------------------------------------------------------------
# UnitTestContext parity
# ---------------------------------------------------------------------------


class TestUnitTestContextParity:
    """Parity: UnitTestContext fields ↔ test_unit.py.jinja2 introspection."""

    @pytest.fixture(scope="class")
    def template_schema(self) -> TemplateSchema:
        return _get_template_schema("unit_test")

    def test_schema_required_subset_of_template_required(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_req = _get_schema_required(UnitTestContext)
        template_req = set(template_schema.required)
        extra = schema_req - template_req
        assert not extra, (
            f"UnitTestContext has required fields not in template: {sorted(extra)}\n"
            f"Template required: {sorted(template_req)}"
        )

    def test_template_required_subset_of_schema_required(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_req = _get_schema_required(UnitTestContext)
        template_req = set(template_schema.required)
        missing = template_req - schema_req
        assert not missing, (
            f"Template requires fields missing from UnitTestContext: {sorted(missing)}\n"
            f"Schema required: {sorted(schema_req)}"
        )

    def test_schema_optional_subset_of_template_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_opt = _get_schema_optional(UnitTestContext)
        template_opt = set(template_schema.optional)
        extra = schema_opt - template_opt
        assert not extra, (
            f"UnitTestContext has optional fields not in template: {sorted(extra)}\n"
            f"Template optional: {sorted(template_opt)}"
        )

    def test_template_optional_subset_of_schema_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_opt = _get_schema_optional(UnitTestContext)
        template_opt = set(template_schema.optional)
        missing = template_opt - schema_opt
        assert not missing, (
            f"Template optionals missing from UnitTestContext: {sorted(missing)}\n"
            f"Schema optional: {sorted(schema_opt)}"
        )

    def test_no_field_in_both_required_and_optional(self, template_schema: TemplateSchema) -> None:
        overlap = set(template_schema.required) & set(template_schema.optional)
        assert not overlap, f"Fields in both required+optional: {sorted(overlap)}"


# ---------------------------------------------------------------------------
# IntegrationTestContext parity
# ---------------------------------------------------------------------------


class TestIntegrationTestContextParity:
    """Parity: IntegrationTestContext fields ↔ test_integration.py.jinja2 introspection."""

    @pytest.fixture(scope="class")
    def template_schema(self) -> TemplateSchema:
        return _get_template_schema("integration_test")

    def test_schema_required_subset_of_template_required(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_req = _get_schema_required(IntegrationTestContext)
        template_req = set(template_schema.required)
        extra = schema_req - template_req
        assert not extra, (
            f"IntegrationTestContext has required fields not in template: {sorted(extra)}\n"
            f"Template required: {sorted(template_req)}"
        )

    def test_template_required_subset_of_schema_required(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_req = _get_schema_required(IntegrationTestContext)
        template_req = set(template_schema.required)
        missing = template_req - schema_req
        assert not missing, (
            f"Template requires fields missing from IntegrationTestContext: {sorted(missing)}\n"
            f"Schema required: {sorted(schema_req)}"
        )

    def test_schema_optional_subset_of_template_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_opt = _get_schema_optional(IntegrationTestContext)
        template_opt = set(template_schema.optional)
        extra = schema_opt - template_opt
        assert not extra, (
            f"IntegrationTestContext has optional fields not in template: {sorted(extra)}\n"
            f"Template optional: {sorted(template_opt)}"
        )

    def test_template_optional_subset_of_schema_optional(
        self, template_schema: TemplateSchema
    ) -> None:
        schema_opt = _get_schema_optional(IntegrationTestContext)
        template_opt = set(template_schema.optional)
        missing = template_opt - schema_opt
        assert not missing, (
            f"Template optionals missing from IntegrationTestContext: {sorted(missing)}\n"
            f"Schema optional: {sorted(schema_opt)}"
        )

    def test_no_field_in_both_required_and_optional(self, template_schema: TemplateSchema) -> None:
        overlap = set(template_schema.required) & set(template_schema.optional)
        assert not overlap, f"Fields in both required+optional: {sorted(overlap)}"
