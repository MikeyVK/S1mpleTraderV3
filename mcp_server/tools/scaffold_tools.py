"""Scaffold tools for template-driven code generation."""
# pyright: reportIncompatibleMethodOverride=false
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field

from mcp_server.core.exceptions import ValidationError
from mcp_server.managers.scaffold_manager import ScaffoldManager
from mcp_server.tools.base import BaseTool, ToolResult


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
    input_dto: str | None = Field(default=None, description="For Workers: input DTO class name")
    output_dto: str | None = Field(default=None, description="For Workers: output DTO class name")
    methods: list[dict[str, Any]] | None = Field(
        default=None,
        description="For Adapters/Interfaces/Services: list of method definitions"
    )
    docstring: str | None = Field(default=None, description="Optional docstring for the component")
    generate_test: bool = Field(
        default=True,
        description="Whether to generate a test file (DTOs only)"
    )
    
    # New fields
    input_schema: dict[str, Any] | None = Field(default=None, description="For Tools: Input schema dict")
    uri_pattern: str | None = Field(default=None, description="For Resources: URI pattern")
    mime_type: str | None = Field(default=None, description="For Resources: MIME type")
    models: list[dict[str, Any]] | None = Field(
        default=None,
        description="For Schemas: List of Pydantic models"
    )
    dependencies: list[str] | None = Field(
        default=None,
        description="For Services: List of dependencies"
    )
    service_type: str = Field(default="orchestrator", description="For Services: service subtype")
    template_name: str | None = Field(
        default=None,
        description="For Generic: Relative template path"
    )
    context: dict[str, Any] | None = Field(default=None, description="For Generic: Context variables")


class ScaffoldComponentTool(BaseTool):
    """Tool to scaffold a new component (DTO, Worker, Adapter, etc.)."""

    name = "scaffold_component"
    description = "Generate a new component from template (dto, worker, adapter, manager, tool)"
    args_model = ScaffoldComponentInput

    def __init__(self, manager: ScaffoldManager | None = None) -> None:
        self.manager = manager or ScaffoldManager()

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

        handler = handlers.get(params.component_type)
        if not handler:
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

        content = self.manager.render_dto(
            name=params.name,
            fields=params.fields,
            docstring=params.docstring
        )
        self.manager.write_file(params.output_path, content)
        created = [params.output_path]

        if params.generate_test:
            module_path = params.output_path.replace("/", ".").replace("\\", ".").rstrip(".py")
            test_content = self.manager.render_dto_test(
                dto_name=params.name,
                module_path=module_path
            )
            test_path = params.output_path.replace(".py", "_test.py")
            if "backend/" in test_path:
                test_path = test_path.replace("backend/", "tests/unit/")
            self.manager.write_file(test_path, test_content)
            created.append(test_path)

        return created

    async def _scaffold_worker(self, params: ScaffoldComponentInput) -> list[str]:
        if not params.input_dto or not params.output_dto:
            raise ValidationError("input_dto and output_dto are required for Worker generation")

        content = self.manager.render_worker(
            name=params.name, input_dto=params.input_dto, output_dto=params.output_dto
        )
        self.manager.write_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_adapter(self, params: ScaffoldComponentInput) -> list[str]:
        if not params.methods:
            raise ValidationError("Methods are required for Adapter generation")

        content = self.manager.render_adapter(name=params.name, methods=params.methods)
        self.manager.write_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_tool(self, params: ScaffoldComponentInput) -> list[str]:
        content = self.manager.render_tool(
            name=params.name,
            description=params.docstring or "",
            input_schema=params.input_schema,
            docstring=params.docstring
        )
        self.manager.write_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_resource(self, params: ScaffoldComponentInput) -> list[str]:
        content = self.manager.render_resource(
            name=params.name,
            description=params.docstring or "",
            uri_pattern=params.uri_pattern,
            mime_type=params.mime_type,
            docstring=params.docstring
        )
        self.manager.write_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_schema(self, params: ScaffoldComponentInput) -> list[str]:
        content = self.manager.render_schema(
            name=params.name,
            description=params.docstring,
            models=params.models,
            docstring=params.docstring
        )
        self.manager.write_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_interface(self, params: ScaffoldComponentInput) -> list[str]:
        content = self.manager.render_interface(
            name=params.name,
            description=params.docstring,
            methods=params.methods,  # type: ignore
            docstring=params.docstring
        )
        self.manager.write_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_service(self, params: ScaffoldComponentInput) -> list[str]:
        content = self.manager.render_service(
            name=params.name,
            service_type=params.service_type,
            dependencies=params.dependencies,
            methods=params.methods,
            description=params.docstring
        )
        self.manager.write_file(params.output_path, content)
        return [params.output_path]

    async def _scaffold_generic(self, params: ScaffoldComponentInput) -> list[str]:
        if not params.template_name or not params.context:
            raise ValidationError("template_name and context required for generic type")

        content = self.manager.render_generic(params.template_name, params.context)
        self.manager.write_file(params.output_path, content)
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
    context: dict[str, Any] | None = Field(default=None, description="Context for generic documents")


class ScaffoldDesignDocTool(BaseTool):
    """Tool to scaffold a design document from template."""

    name = "scaffold_design_doc"
    description = "Generate a design document from template"
    args_model = ScaffoldDesignDocInput

    def __init__(self, manager: ScaffoldManager | None = None) -> None:
        self.manager = manager or ScaffoldManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: ScaffoldDesignDocInput) -> ToolResult:
        if params.doc_type == "generic":
            render_context = params.context or {}
            render_context.update({
                "title": params.title,
                "author": params.author,
                "status": params.status,
                "output_path": params.output_path
            })
            content = self.manager.render_generic_doc(**render_context)
        else:
            content = self.manager.render_design_doc(
                title=params.title,
                author=params.author,
                summary=params.summary,
                sections=params.sections,
                status=params.status
            )

        self.manager.write_file(params.output_path, content)
        return ToolResult.text(f"Created {params.doc_type} document: {params.output_path}")
