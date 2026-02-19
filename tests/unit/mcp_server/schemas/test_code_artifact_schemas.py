# tests/unit/mcp_server/schemas/test_code_artifact_schemas.py
# template=generic version=74378193 created=2026-02-17T00:00Z updated=
"""Tests for Cycle 5 code artifact context schemas.

Covers 7 code artifact types: worker, tool, schema, service, generic,
unit_test, integration_test.

Per type:
- Context schema validation (happy path + required field errors)
- RenderContext enrichment (context fields + lifecycle fields)

@layer: Test Infrastructure
"""

# Standard library
import logging
from datetime import UTC, datetime
from pathlib import Path

# Third-party
import pytest
from pydantic import ValidationError

# Project modules
from mcp_server.schemas.contexts.generic import GenericContext
from mcp_server.schemas.contexts.integration_test import IntegrationTestContext
from mcp_server.schemas.contexts.schema import SchemaContext
from mcp_server.schemas.contexts.service import ServiceContext
from mcp_server.schemas.contexts.tool import ToolContext
from mcp_server.schemas.contexts.unit_test import UnitTestContext
from mcp_server.schemas.contexts.worker import WorkerContext
from mcp_server.schemas.render_contexts.generic import GenericRenderContext
from mcp_server.schemas.render_contexts.integration_test import IntegrationTestRenderContext
from mcp_server.schemas.render_contexts.schema import SchemaRenderContext
from mcp_server.schemas.render_contexts.service import ServiceRenderContext
from mcp_server.schemas.render_contexts.tool import ToolRenderContext
from mcp_server.schemas.render_contexts.unit_test import UnitTestRenderContext
from mcp_server.schemas.render_contexts.worker import WorkerRenderContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_LIFECYCLE = {
    "output_path": Path("/tmp/test_artifact.py"),
    "scaffold_created": datetime.now(tz=UTC),
    "template_id": "worker",
    "version_hash": "abc12345",
}


# ===========================================================================
# WorkerContext
# ===========================================================================


class TestWorkerContext:
    """Test WorkerContext schema validation."""

    def test_worker_context_validation_happy(self) -> None:
        """Valid worker input should create WorkerContext instance."""
        ctx = WorkerContext(
            name="MarketDataWorker",
            layer="platform",
        )
        assert ctx.name == "MarketDataWorker"
        assert ctx.layer == "platform"

    def test_worker_context_optional_fields(self) -> None:
        """Worker optional fields should have sensible defaults."""
        ctx = WorkerContext(name="MyWorker", layer="strategy")
        assert ctx.responsibilities == []
        assert ctx.capabilities == []
        assert ctx.use_async is False
        assert ctx.module_description is None
        assert ctx.worker_scope is None

    def test_worker_context_all_optional_populated(self) -> None:
        """All optional worker fields should be storable."""
        ctx = WorkerContext(
            name="AdvancedWorker",
            layer="platform",
            module_description="Handles market data processing",
            worker_scope="platform",
            responsibilities=["ingest prices", "publish events"],
            capabilities=["event_bus", "config"],
            use_async=True,
        )
        assert ctx.use_async is True
        assert len(ctx.capabilities) == 2

    def test_worker_context_missing_required_name(self) -> None:
        """Missing name should raise ValidationError."""
        with pytest.raises(ValidationError):
            WorkerContext(layer="platform")  # type: ignore[call-arg]

    def test_worker_context_missing_required_layer(self) -> None:
        """Missing layer should raise ValidationError."""
        with pytest.raises(ValidationError):
            WorkerContext(name="MyWorker")  # type: ignore[call-arg]

    def test_worker_context_empty_name_rejected(self) -> None:
        """Empty name string should raise ValidationError."""
        with pytest.raises(ValidationError, match="name"):
            WorkerContext(name="", layer="platform")


class TestWorkerRenderContext:
    """Test WorkerRenderContext enrichment."""

    def test_worker_render_context_enrichment(self) -> None:
        """WorkerRenderContext should combine worker + lifecycle fields."""
        render_ctx = WorkerRenderContext(
            name="MarketDataWorker",
            layer="platform",
            **_LIFECYCLE,
        )
        assert render_ctx.name == "MarketDataWorker"
        assert render_ctx.layer == "platform"
        assert render_ctx.output_path == Path("/tmp/test_artifact.py")
        assert render_ctx.template_id == "worker"
        assert render_ctx.version_hash == "abc12345"


# ===========================================================================
# ToolContext
# ===========================================================================


class TestToolContext:
    """Test ToolContext schema validation."""

    def test_tool_context_validation_happy(self) -> None:
        """Valid tool input should create ToolContext instance."""
        ctx = ToolContext(name="GitCommitTool")
        assert ctx.name == "GitCommitTool"

    def test_tool_context_optional_fields_defaults(self) -> None:
        """Tool optional fields should have sensible defaults."""
        ctx = ToolContext(name="MyTool")
        assert ctx.description is None
        assert ctx.layer is None
        assert ctx.responsibilities == []

    def test_tool_context_all_optional_populated(self) -> None:
        """All optional tool fields should be storable."""
        ctx = ToolContext(
            name="FilesystemTool",
            description="Reads and writes workspace files",
            layer="mcp_server",
            responsibilities=["read files", "write files"],
        )
        assert ctx.description == "Reads and writes workspace files"
        assert len(ctx.responsibilities) == 2

    def test_tool_context_missing_required_name(self) -> None:
        """Missing name should raise ValidationError."""
        with pytest.raises(ValidationError):
            ToolContext()  # type: ignore[call-arg]

    def test_tool_context_empty_name_rejected(self) -> None:
        """Empty name should raise ValidationError."""
        with pytest.raises(ValidationError, match="name"):
            ToolContext(name="")


class TestToolRenderContext:
    """Test ToolRenderContext enrichment."""

    def test_tool_render_context_enrichment(self) -> None:
        """ToolRenderContext should combine tool + lifecycle fields."""
        render_ctx = ToolRenderContext(
            name="GitCommitTool",
            **{**_LIFECYCLE, "template_id": "tool"},
        )
        assert render_ctx.name == "GitCommitTool"
        assert render_ctx.template_id == "tool"


# ===========================================================================
# SchemaContext
# ===========================================================================


class TestSchemaContext:
    """Test SchemaContext schema validation."""

    def test_schema_context_validation_happy(self) -> None:
        """Valid schema input should create SchemaContext instance."""
        ctx = SchemaContext(name="WorkflowConfig")
        assert ctx.name == "WorkflowConfig"

    def test_schema_context_optional_fields_defaults(self) -> None:
        """Schema optional fields should have sensible defaults."""
        ctx = SchemaContext(name="MySchema")
        assert ctx.description is None
        assert ctx.layer is None
        assert ctx.fields == []
        assert ctx.frozen is True  # default: frozen schemas
        assert ctx.examples == []

    def test_schema_context_all_optional_populated(self) -> None:
        """All optional schema fields should be storable."""
        ctx = SchemaContext(
            name="LabelConfig",
            description="Validates .st3/labels.yaml",
            layer="mcp_server",
            fields=["name: str", "color: str"],
            frozen=False,
            examples=["name: 'type:feature', color: '0e8a16'"],
        )
        assert ctx.frozen is False
        assert len(ctx.fields) == 2

    def test_schema_context_missing_required_name(self) -> None:
        """Missing name should raise ValidationError."""
        with pytest.raises(ValidationError):
            SchemaContext()  # type: ignore[call-arg]

    def test_schema_context_empty_name_rejected(self) -> None:
        """Empty name should raise ValidationError."""
        with pytest.raises(ValidationError, match="name"):
            SchemaContext(name="")


class TestSchemaRenderContext:
    """Test SchemaRenderContext enrichment."""

    def test_schema_render_context_enrichment(self) -> None:
        """SchemaRenderContext should combine schema + lifecycle fields."""
        render_ctx = SchemaRenderContext(
            name="WorkflowConfig",
            **{**_LIFECYCLE, "template_id": "schema"},
        )
        assert render_ctx.name == "WorkflowConfig"
        assert render_ctx.template_id == "schema"


# ===========================================================================
# ServiceContext
# ===========================================================================


class TestServiceContext:
    """Test ServiceContext schema validation."""

    def test_service_context_validation_happy(self) -> None:
        """Valid service input should create ServiceContext instance."""
        ctx = ServiceContext(name="ScaffoldArtifactCommand")
        assert ctx.name == "ScaffoldArtifactCommand"

    def test_service_context_optional_fields_defaults(self) -> None:
        """Service optional fields should have sensible defaults."""
        ctx = ServiceContext(name="MyService")
        assert ctx.description is None
        assert ctx.layer is None
        assert ctx.responsibilities == []
        assert ctx.parameters == []
        assert ctx.return_type is None

    def test_service_context_all_optional_populated(self) -> None:
        """All optional service fields should be storable."""
        ctx = ServiceContext(
            name="CreateIssueCommand",
            description="Creates GitHub issue via MCP",
            layer="mcp_server",
            responsibilities=["validate input", "call GitHub API"],
            parameters=["title: str", "body: str", "labels: list[str]"],
            return_type="IssueResult",
        )
        assert ctx.return_type == "IssueResult"
        assert len(ctx.parameters) == 3

    def test_service_context_missing_required_name(self) -> None:
        """Missing name should raise ValidationError."""
        with pytest.raises(ValidationError):
            ServiceContext()  # type: ignore[call-arg]

    def test_service_context_empty_name_rejected(self) -> None:
        """Empty name should raise ValidationError."""
        with pytest.raises(ValidationError, match="name"):
            ServiceContext(name="")


class TestServiceRenderContext:
    """Test ServiceRenderContext enrichment."""

    def test_service_render_context_enrichment(self) -> None:
        """ServiceRenderContext should combine service + lifecycle fields."""
        render_ctx = ServiceRenderContext(
            name="ScaffoldArtifactCommand",
            **{**_LIFECYCLE, "template_id": "service"},
        )
        assert render_ctx.name == "ScaffoldArtifactCommand"
        assert render_ctx.template_id == "service"


# ===========================================================================
# GenericContext
# ===========================================================================


class TestGenericContext:
    """Test GenericContext schema validation."""

    def test_generic_context_validation_happy(self) -> None:
        """Valid generic input should create GenericContext instance."""
        ctx = GenericContext(name="TemplateHasher")
        assert ctx.name == "TemplateHasher"

    def test_generic_context_optional_fields_defaults(self) -> None:
        """Generic optional fields should have sensible defaults."""
        ctx = GenericContext(name="MyHelper")
        assert ctx.description is None
        assert ctx.methods == []

    def test_generic_context_all_optional_populated(self) -> None:
        """All optional generic fields should be storable."""
        ctx = GenericContext(
            name="PathUtils",
            description="Path manipulation utilities",
            methods=["normalize_path", "ensure_dir"],
        )
        assert len(ctx.methods) == 2

    def test_generic_context_missing_required_name(self) -> None:
        """Missing name should raise ValidationError."""
        with pytest.raises(ValidationError):
            GenericContext()  # type: ignore[call-arg]

    def test_generic_context_empty_name_rejected(self) -> None:
        """Empty name should raise ValidationError."""
        with pytest.raises(ValidationError, match="name"):
            GenericContext(name="")


class TestGenericRenderContext:
    """Test GenericRenderContext enrichment."""

    def test_generic_render_context_enrichment(self) -> None:
        """GenericRenderContext should combine generic + lifecycle fields."""
        render_ctx = GenericRenderContext(
            name="TemplateHasher",
            **{**_LIFECYCLE, "template_id": "generic"},
        )
        assert render_ctx.name == "TemplateHasher"
        assert render_ctx.template_id == "generic"


# ===========================================================================
# UnitTestContext
# ===========================================================================


class TestUnitTestContext:
    """Test UnitTestContext schema validation."""

    def test_unit_test_context_validation_happy(self) -> None:
        """Valid unit test input should create UnitTestContext instance."""
        ctx = UnitTestContext(
            module_under_test="mcp_server.schemas.contexts.dto",
            test_class_name="TestDTOContext",
        )
        assert ctx.module_under_test == "mcp_server.schemas.contexts.dto"
        assert ctx.test_class_name == "TestDTOContext"

    def test_unit_test_context_optional_fields_defaults(self) -> None:
        """UnitTest optional fields should have sensible defaults."""
        ctx = UnitTestContext(
            module_under_test="mcp_server.some_module",
            test_class_name="TestSomeModule",
        )
        assert ctx.test_description is None
        assert ctx.has_mocks is True  # default: mocking enabled
        assert ctx.has_async_tests is False
        assert ctx.has_pydantic is False
        assert ctx.test_methods == []

    def test_unit_test_context_missing_module_under_test(self) -> None:
        """Missing module_under_test should raise ValidationError."""
        with pytest.raises(ValidationError):
            UnitTestContext(test_class_name="TestFoo")  # type: ignore[call-arg]

    def test_unit_test_context_missing_test_class_name(self) -> None:
        """Missing test_class_name should raise ValidationError."""
        with pytest.raises(ValidationError):
            UnitTestContext(module_under_test="mcp_server.foo")  # type: ignore[call-arg]

    def test_unit_test_context_empty_module_rejected(self) -> None:
        """Empty module_under_test should raise ValidationError."""
        with pytest.raises(ValidationError):
            UnitTestContext(module_under_test="", test_class_name="TestFoo")


class TestUnitTestRenderContext:
    """Test UnitTestRenderContext enrichment."""

    def test_unit_test_render_context_enrichment(self) -> None:
        """UnitTestRenderContext should combine unit_test + lifecycle fields."""
        render_ctx = UnitTestRenderContext(
            module_under_test="mcp_server.schemas.contexts.dto",
            test_class_name="TestDTOContext",
            **{**_LIFECYCLE, "template_id": "unit_test"},
        )
        assert render_ctx.module_under_test == "mcp_server.schemas.contexts.dto"
        assert render_ctx.template_id == "unit_test"


# ===========================================================================
# IntegrationTestContext
# ===========================================================================


class TestIntegrationTestContext:
    """Test IntegrationTestContext schema validation."""

    def test_integration_test_context_validation_happy(self) -> None:
        """Valid integration test input should create IntegrationTestContext."""
        ctx = IntegrationTestContext(
            test_scenario="scaffold_dto_end_to_end",
            test_class_name="TestScaffoldDTOE2E",
        )
        assert ctx.test_scenario == "scaffold_dto_end_to_end"
        assert ctx.test_class_name == "TestScaffoldDTOE2E"

    def test_integration_test_context_optional_fields_defaults(self) -> None:
        """IntegrationTest optional fields should have sensible defaults."""
        ctx = IntegrationTestContext(
            test_scenario="my_scenario",
            test_class_name="TestMyScenario",
        )
        assert ctx.test_description is None
        assert ctx.managers_needed == []
        assert ctx.workspace_fixture is True  # default: use temp workspace
        assert ctx.test_methods == []

    def test_integration_test_context_missing_test_scenario(self) -> None:
        """Missing test_scenario should raise ValidationError."""
        with pytest.raises(ValidationError):
            IntegrationTestContext(test_class_name="TestFoo")  # type: ignore[call-arg]

    def test_integration_test_context_missing_test_class_name(self) -> None:
        """Missing test_class_name should raise ValidationError."""
        with pytest.raises(ValidationError):
            IntegrationTestContext(test_scenario="my_scenario")  # type: ignore[call-arg]

    def test_integration_test_context_empty_scenario_rejected(self) -> None:
        """Empty test_scenario should raise ValidationError."""
        with pytest.raises(ValidationError):
            IntegrationTestContext(test_scenario="", test_class_name="TestFoo")


class TestIntegrationTestRenderContext:
    """Test IntegrationTestRenderContext enrichment."""

    def test_integration_test_render_context_enrichment(self) -> None:
        """IntegrationTestRenderContext should combine fields + lifecycle."""
        render_ctx = IntegrationTestRenderContext(
            test_scenario="scaffold_dto_end_to_end",
            test_class_name="TestScaffoldDTOE2E",
            **{**_LIFECYCLE, "template_id": "integration_test"},
        )
        assert render_ctx.test_scenario == "scaffold_dto_end_to_end"
        assert render_ctx.template_id == "integration_test"
