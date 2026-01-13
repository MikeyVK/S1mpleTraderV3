"""Scaffold tools for template-driven code generation."""
# pyright: reportIncompatibleMethodOverride=false
from typing import Any, Callable, Awaitable, cast

from pydantic import BaseModel, Field

from mcp_server.config.component_registry import ComponentRegistryConfig
from mcp_server.core.directory_policy_resolver import DirectoryPolicyResolver
from mcp_server.core.exceptions import ValidationError
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult
from mcp_server.scaffolding.base import ComponentScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.scaffolding.utils import write_scaffold_file

from mcp_server.scaffolding.components.dto import DTOScaffolder
from mcp_server.scaffolding.components.worker import WorkerScaffolder
from mcp_server.scaffolding.components.adapter import AdapterScaffolder
from mcp_server.scaffolding.components.tool import ToolScaffolder
from mcp_server.scaffolding.components.resource import ResourceScaffolder
from mcp_server.scaffolding.components.schema import SchemaScaffolder
from mcp_server.scaffolding.components.interface import InterfaceScaffolder
from mcp_server.scaffolding.components.service import ServiceScaffolder
from mcp_server.scaffolding.components.generic import GenericScaffolder
from mcp_server.scaffolding.components.doc import DesignDocScaffolder
from mcp_server.scaffolding.components.test import TestScaffolder


class ScaffoldComponentInput(BaseModel):
    """Input for ScaffoldComponentTool."""
    component_type: str = Field(..., description="Type of component to generate")
    name: str = Field(..., description="Component name (PascalCase)")
    output_path: str = Field(..., description="Output file path relative to workspace")

    # Specific fields
    fields: list[dict[str, Any]] | None = Field(
        default=None,
        description="For DTOs: list of {name, type, default} objects"
    )
    input_dto: str | None = Field(
        default=None,
        description="For Workers: input DTO class name"
    )
    output_dto: str | None = Field(
        default=None,
        description="For Workers: output DTO class name"
    )
    methods: list[dict[str, Any]] | None = Field(
        default=None,
        description="For Adapters/Interfaces/Services: list of method definitions"
    )
    docstring: str | None = Field(
        default=None,
        description="Optional docstring for the component"
    )
    generate_test: bool = Field(
        default=True,
        description="Whether to generate a test file (DTOs only)"
    )

    # New fields
    input_schema: dict[str, Any] | None = Field(
        default=None,
        description="For Tools: Input schema dict"
    )
    uri_pattern: str | None = Field(
        default=None,
        description="For Resources: URI pattern"
    )
    mime_type: str | None = Field(
        default=None,
        description="For Resources: MIME type"
    )
    models: list[dict[str, Any]] | None = Field(
        default=None,
        description="For Schemas: List of Pydantic models"
    )
    dependencies: list[str] | None = Field(
        default=None,
        description="For Services: List of dependencies"
    )
    service_type: str = Field(
        default="orchestrator",
        description="For Services: service subtype"
    )
    template_name: str | None = Field(
        default=None,
        description="For Generic: Relative template path"
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="For Generic: Context variables"
    )


class ScaffoldComponentTool(BaseTool):
    """Tool to scaffold a new component (DTO, Worker, Adapter, etc.)."""

    name = "scaffold_component"
    description = "Generate a new component from template (dto, worker, adapter, manager, tool)"
    args_model = ScaffoldComponentInput

    def __init__(
        self,
        renderer: JinjaRenderer | None = None,
        config_dir: str = ".st3"
    ) -> None:
        self.renderer = renderer or JinjaRenderer()

        # Load config foundation (Issue #54)
        self.component_config = ComponentRegistryConfig.from_file(
            f"{config_dir}/components.yaml"
        )
        self.dir_resolver = DirectoryPolicyResolver()

        # Initialize component scaffolders map
        # Cast to ComponentScaffolder to satisfy Protocol typing
        self.scaffolders: dict[str, ComponentScaffolder] = {
            "dto": cast(ComponentScaffolder, DTOScaffolder(self.renderer)),
            "worker": cast(ComponentScaffolder, WorkerScaffolder(self.renderer)),
            "adapter": cast(ComponentScaffolder, AdapterScaffolder(self.renderer)),
            "tool": cast(ComponentScaffolder, ToolScaffolder(self.renderer)),
            "resource": cast(ComponentScaffolder, ResourceScaffolder(self.renderer)),
            "schema": cast(ComponentScaffolder, SchemaScaffolder(self.renderer)),
            "interface": cast(ComponentScaffolder, InterfaceScaffolder(self.renderer)),
            "service": cast(ComponentScaffolder, ServiceScaffolder(self.renderer)),
            "generic": cast(ComponentScaffolder, GenericScaffolder(self.renderer)),
        }
        self.test_scaffolder = TestScaffolder(self.renderer)

    def _validate_component_type(self, component_type: str) -> None:
        """Validate component type against ComponentRegistryConfig.

        Args:
            component_type: Type to validate

        Raises:
            ValidationError: If component type not in config
        """
        if not self.component_config.has_component_type(component_type):
            available = self.component_config.get_available_types()
            raise ValidationError(
                f"Unknown component type: '{component_type}'",
                hints=[f"Available types: {', '.join(available)}"]
            )

    def _validate_path(self, component_type: str, output_path: str) -> None:
        """Validate path allows component type via DirectoryPolicyResolver.

        Args:
            component_type: Component type to validate
            output_path: Path where component will be created

        Raises:
            ValidationError: If component type not allowed in directory
        """
        dir_policy = self.dir_resolver.resolve(output_path)

        if not dir_policy.allows_component_type(component_type):
            raise ValidationError(
                f"Component type '{component_type}' not allowed in "
                f"'{dir_policy.path}'",
                hints=[
                    f"Allowed types: {', '.join(dir_policy.allowed_component_types or ['all'])}"
                ]
            )

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: ScaffoldComponentInput) -> ToolResult:
        handlers: dict[str, Callable[[ScaffoldComponentInput], Awaitable[list[str]]]] = {
            "dto": self._scaffold_dto,
            "worker": self._scaffold_worker,
            "adapter": self._scaffold_adapter,
            "tool": self._scaffold_tool,
            "resource": self._scaffold_resource,
            "schema": self._scaffold_schema,
            "interface": self._scaffold_interface,
            "service": self._scaffold_service,
            "generic": self._scaffold_generic,
        }

        # Validate component type against config (Issue #54)
        self._validate_component_type(params.component_type)

        # Validate path allows component type (Issue #54)
        if params.output_path:
            self._validate_path(params.component_type, params.output_path)

        handler = handlers.get(params.component_type)
        if not handler:
            # Should not reach here after _validate_component_type
            raise ValidationError(
                f"Unknown component type: {params.component_type}",
                hints=[
                    "Use dto, worker, adapter, tool, resource, schema, interface, service, generic"
                ]
            )

        created_files = await handler(params)

        return ToolResult.text(
            f"Scaffolded {params.component_type} '{params.name}':\n" +
            "\n".join(f"  - {f}" for f in created_files)
        )

    async def _scaffold_dto(self, params: ScaffoldComponentInput) -> list[str]:
        if not params.fields:
            raise ValidationError(
                "Fields are required for DTO generation",
                hints=["Provide fields as list of {name, type} objects"]
            )

        content = self.scaffolders["dto"].scaffold(
            name=params.name,
            fields=params.fields,
            docstring=params.docstring
        )
        write_scaffold_file(params.output_path, content)
        created = [params.output_path]

        if params.generate_test:
            module_path = params.output_path.replace("/", ".").replace("\\", ".").rstrip(".py")
            # Basic module path heuristic
            
            # Split fields into required and optional for test generation
            required_fields = [f for f in params.fields if "default" not in f]
            optional_fields = [f for f in params.fields if "default" in f]

            test_content = self.test_scaffolder.scaffold(
                name=params.name,
                test_type="dto",
                module_path=module_path,
                required_fields=required_fields,
                optional_fields=optional_fields
            )
            test_path = params.output_path.replace(".py", "_test.py")
            if "backend/" in test_path:
                test_path = test_path.replace("backend/", "tests/unit/")
            write_scaffold_file(test_path, test_content)
            created.append(test_path)

        return created

    async def _scaffold_worker(self, params: ScaffoldComponentInput) -> list[str]:
        if not params.input_dto or not params.output_dto:
            raise ValidationError("input_dto and output_dto are required for Worker generation")

        content = self.scaffolders["worker"].scaffold(
            name=params.name,
            input_dto=params.input_dto,
            output_dto=params.output_dto
        )
        write_scaffold_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_adapter(self, params: ScaffoldComponentInput) -> list[str]:
        if not params.methods:
            raise ValidationError("Methods are required for Adapter generation")

        content = self.scaffolders["adapter"].scaffold(name=params.name, methods=params.methods)
        write_scaffold_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_tool(self, params: ScaffoldComponentInput) -> list[str]:
        content = self.scaffolders["tool"].scaffold(
            name=params.name,
            description=params.docstring or "",
            input_schema=params.input_schema,
            docstring=params.docstring
        )
        write_scaffold_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_resource(self, params: ScaffoldComponentInput) -> list[str]:
        content = self.scaffolders["resource"].scaffold(
            name=params.name,
            description=params.docstring or "",
            uri_pattern=params.uri_pattern,
            mime_type=params.mime_type,
            docstring=params.docstring
        )
        write_scaffold_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_schema(self, params: ScaffoldComponentInput) -> list[str]:
        content = self.scaffolders["schema"].scaffold(
            name=params.name,
            description=params.docstring,
            models=params.models,
            docstring=params.docstring
        )
        write_scaffold_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_interface(self, params: ScaffoldComponentInput) -> list[str]:
        content = self.scaffolders["interface"].scaffold(
            name=params.name,
            description=params.docstring,
            methods=params.methods,
            docstring=params.docstring
        )
        write_scaffold_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_service(self, params: ScaffoldComponentInput) -> list[str]:
        content = self.scaffolders["service"].scaffold(
            name=params.name,
            service_type=params.service_type,
            dependencies=params.dependencies,
            methods=params.methods,
            description=params.docstring
        )
        write_scaffold_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_generic(self, params: ScaffoldComponentInput) -> list[str]:
        if not params.template_name or not params.context:
            raise ValidationError("template_name and context required for generic type")

        content = self.scaffolders["generic"].scaffold(
            params.name,
            template_name=params.template_name,
            **params.context
        )
        write_scaffold_file(params.output_path, content)
        return [params.output_path]


class ScaffoldDesignDocInput(BaseModel):
    """Input for ScaffoldDesignDocTool."""
    title: str = Field(..., description="Document title")
    output_path: str = Field(..., description="Output file path relative to workspace")
    doc_type: str = Field(
        default="design",
        description="Type of document to generate",
        pattern="^(design|architecture|tracking|generic)$"
    )
    author: str | None = Field(default=None, description="Document author")
    summary: str | None = Field(default=None, description="Executive summary")
    sections: list[str] | None = Field(default=None, description="List of section headings")
    status: str = Field(
        default="DRAFT",
        description="Status",
        pattern="^(DRAFT|REVIEW|APPROVED)$"
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="Context for generic documents"
    )


class ScaffoldDesignDocTool(BaseTool):
    """Tool to scaffold a design document from template."""

    name = "scaffold_design_doc"
    description = "Generate a design document from template"
    args_model = ScaffoldDesignDocInput

    def __init__(self, renderer: JinjaRenderer | None = None) -> None:
        self.renderer = renderer or JinjaRenderer()
        self.design_doc_scaffolder = DesignDocScaffolder(self.renderer)

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: ScaffoldDesignDocInput) -> ToolResult:
        content = self.design_doc_scaffolder.scaffold(
            name=params.title,
            doc_type=params.doc_type,
            author=params.author,
            summary=params.summary,
            sections=params.sections,
            status=params.status,
            **(params.context or {})
        )

        write_scaffold_file(params.output_path, content)
        return ToolResult.text(f"Created {params.doc_type} document: {params.output_path}")
