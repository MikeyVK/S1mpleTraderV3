"""Scaffold tools for template-driven code generation."""
# pyright: reportIncompatibleMethodOverride=false
from typing import Any

from mcp_server.core.exceptions import ValidationError
from mcp_server.managers.scaffold_manager import ScaffoldManager
from mcp_server.tools.base import BaseTool, ToolResult


class ScaffoldComponentTool(BaseTool):
    """Tool to scaffold a new component (DTO, Worker, Adapter, etc.)."""

    name = "scaffold_component"
    description = "Generate a new component from template (dto, worker, adapter, manager, tool)"

    def __init__(self, manager: ScaffoldManager | None = None) -> None:
        self.manager = manager or ScaffoldManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "component_type": {
                    "type": "string",
                    "enum": [
                        "dto", "worker", "adapter", 
                        "tool", "resource", "schema", 
                        "interface", "service", "generic"
                    ],
                    "description": "Type of component to generate"
                },
                "name": {
                    "type": "string",
                    "description": "Component name (PascalCase)"
                },
                "output_path": {
                    "type": "string",
                    "description": "Output file path relative to workspace"
                },
                "fields": {
                    "type": "array",
                    "description": "For DTOs: list of {name, type, default} objects",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "default": {"type": "string"},
                            "optional": {"type": "boolean"}
                        },
                        "required": ["name", "type"]
                    }
                },
                "input_dto": {
                    "type": "string",
                    "description": "For Workers: input DTO class name"
                },
                "output_dto": {
                    "type": "string",
                    "description": "For Workers: output DTO class name"
                },
                "methods": {
                    "type": "array",
                    "description": "For Adapters/Interfaces/Services: list of method definitions",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "params": {"type": "string"},
                            "return_type": {"type": "string"},
                            "docstring": {"type": "string"},
                            "command_type": {"type": "string"},
                            "query_type": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                },
                "docstring": {
                    "type": "string",
                    "description": "Optional docstring for the component"
                },
                "generate_test": {
                    "type": "boolean",
                    "description": "Whether to generate a test file (DTOs only)",
                    "default": True
                },
                # -- New Fields --
                "input_schema": {
                    "type": "object",
                    "description": "For Tools: Input schema dict"
                },
                "uri_pattern": {
                    "type": "string",
                    "description": "For Resources: URI pattern"
                },
                "mime_type": {
                    "type": "string",
                    "description": "For Resources: MIME type"
                },
                "models": {
                    "type": "array",
                    "description": "For Schemas: List of Pydantic models",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "fields": {"type": "array"}
                        }
                    }
                },
                "dependencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "For Services: List of dependencies"
                },
                "service_type": {
                    "type": "string",
                    "enum": ["orchestrator", "command", "query"],
                    "description": "For Services: service subtype"
                },
                "template_name": {
                    "type": "string",
                    "description": "For Generic: Relative template path"
                },
                "context": {
                    "type": "object",
                    "description": "For Generic: Context variables"
                }
            },
            "required": ["component_type", "name", "output_path"]
        }

    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    async def execute(
        self,
        component_type: str,
        name: str,
        output_path: str,
        fields: list[dict[str, Any]] | None = None,
        input_dto: str | None = None,
        output_dto: str | None = None,
        methods: list[dict[str, Any]] | None = None,
        docstring: str | None = None,
        generate_test: bool = True,
        # New args
        input_schema: dict[str, Any] | None = None,
        uri_pattern: str | None = None,
        mime_type: str | None = None,
        models: list[dict[str, Any]] | None = None,
        dependencies: list[str] | None = None,
        service_type: str = "orchestrator",
        template_name: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any
    ) -> ToolResult:
        """Execute component scaffolding."""
        created_files = []

        if component_type == "dto":
            if not fields:
                raise ValidationError(
                    "Fields are required for DTO generation",
                    hints=["Provide fields as list of {name, type} objects"]
                )

            content = self.manager.render_dto(
                name=name,
                fields=fields,
                docstring=docstring
            )
            self.manager.write_file(output_path, content)
            created_files.append(output_path)

            if generate_test:
                module_path = output_path.replace("/", ".").replace("\\", ".").rstrip(".py")
                test_content = self.manager.render_dto_test(
                    dto_name=name,
                    module_path=module_path
                )
                test_path = output_path.replace(".py", "_test.py")
                if "backend/" in test_path:
                    test_path = test_path.replace("backend/", "tests/unit/")
                self.manager.write_file(test_path, test_content)
                created_files.append(test_path)

        elif component_type == "worker":
            if not input_dto or not output_dto:
                raise ValidationError(
                    "input_dto and output_dto are required for Worker generation"
                )
            content = self.manager.render_worker(
                name=name, input_dto=input_dto, output_dto=output_dto
            )
            self.manager.write_file(output_path, content)
            created_files.append(output_path)

        elif component_type == "adapter":
            if not methods:
                raise ValidationError("Methods are required for Adapter generation")
            # Convert generic methods dict to expected string format if necessary
            # Adapter template expects list of dicts: name, params, return_type
            content = self.manager.render_adapter(name=name, methods=methods)
            self.manager.write_file(output_path, content)
            created_files.append(output_path)

        # -- New Types --

        elif component_type == "tool":
            content = self.manager.render_tool(
                name=name, 
                description=docstring or "", 
                input_schema=input_schema,
                docstring=docstring
            )
            self.manager.write_file(output_path, content)
            created_files.append(output_path)

        elif component_type == "resource":
            content = self.manager.render_resource(
                name=name,
                description=docstring or "",
                uri_pattern=uri_pattern,
                mime_type=mime_type,
                docstring=docstring
            )
            self.manager.write_file(output_path, content)
            created_files.append(output_path)
        
        elif component_type == "schema":
            content = self.manager.render_schema(
                name=name,
                description=docstring,
                models=models,
                docstring=docstring
            )
            self.manager.write_file(output_path, content)
            created_files.append(output_path)

        elif component_type == "interface":
            content = self.manager.render_interface(
                name=name,
                description=docstring,
                methods=methods, # type: ignore
                docstring=docstring
            )
            self.manager.write_file(output_path, content)
            created_files.append(output_path)

        elif component_type == "service":
            content = self.manager.render_service(
                name=name,
                service_type=service_type,
                dependencies=dependencies,
                methods=methods,
                description=docstring
            )
            self.manager.write_file(output_path, content)
            created_files.append(output_path)

        elif component_type == "generic":
            if not template_name or not context:
                raise ValidationError("template_name and context required for generic type")
            content = self.manager.render_generic(template_name, context)
            self.manager.write_file(output_path, content)
            created_files.append(output_path)

        else:
            raise ValidationError(
                f"Unknown component type: {component_type}",
                hints=["Use dto, worker, adapter, tool, resource, schema, interface, service, generic"]
            )

        return ToolResult.text(
            f"Scaffolded {component_type} '{name}':\n" +
            "\n".join(f"  - {f}" for f in created_files)
        )


class ScaffoldDesignDocTool(BaseTool):
    """Tool to scaffold a design document from template."""

    name = "scaffold_design_doc"
    description = "Generate a design document from template"

    def __init__(self, manager: ScaffoldManager | None = None) -> None:
        self.manager = manager or ScaffoldManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "doc_type": {
                    "type": "string",
                    "enum": ["design", "architecture", "tracking", "generic"],
                    "default": "design",
                    "description": "Type of document to generate"
                },
                "title": {
                    "type": "string",
                    "description": "Document title"
                },
                "output_path": {
                    "type": "string",
                    "description": "Output file path relative to workspace"
                },
                "author": {
                    "type": "string",
                    "description": "Document author"
                },
                "summary": {
                    "type": "string",
                    "description": "Executive summary"
                },
                "sections": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of section headings (Design/Arch)"
                },
                "status": {
                    "type": "string",
                    "enum": ["DRAFT", "REVIEW", "APPROVED"],
                    "default": "DRAFT"
                },
                "context": {
                    "type": "object",
                    "description": "Context for generic documents"
                }
            },
            "required": ["title", "output_path"]
        }

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    async def execute(
        self,
        title: str,
        output_path: str,
        doc_type: str = "design",
        author: str | None = None,
        summary: str | None = None,
        sections: list[str] | None = None,
        status: str = "DRAFT",
        context: dict[str, Any] | None = None,
        **kwargs: Any
    ) -> ToolResult:
        """Execute document scaffolding."""
        if doc_type == "generic":
             render_context = context or {}
             render_context.update({
                 "title": title,
                 "author": author,
                 "status": status,
                 "output_path": output_path
             })
             # Merge any generic kwargs into context
             render_context.update(kwargs)
             
             content = self.manager.render_generic_doc(**render_context)
        else:
            # Re-map legacy arguments for specific templates
            # TODO: Future refactor to use separate render methods or unified approach
            content = self.manager.render_design_doc(
                title=title,
                author=author,
                summary=summary,
                sections=sections,
                status=status
            )

        self.manager.write_file(output_path, content)

        return ToolResult.text(f"Created {doc_type} document: {output_path}")
