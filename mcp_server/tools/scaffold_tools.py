"""Scaffold tools for template-driven code generation."""
from typing import Any, Dict
from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.managers.scaffold_manager import ScaffoldManager
from mcp_server.core.exceptions import ValidationError


class ScaffoldComponentTool(BaseTool):
    """Tool to scaffold a new component (DTO, Worker, Adapter, etc.)."""

    name = "scaffold_component"
    description = "Generate a new component from template (dto, worker, adapter, manager, tool)"

    def __init__(self, manager: ScaffoldManager | None = None) -> None:
        self.manager = manager or ScaffoldManager()

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "component_type": {
                    "type": "string",
                    "enum": ["dto", "worker", "adapter"],
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
                    "description": "For DTOs: list of field objects with 'name', 'type', optional 'default'",
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
                    "description": "For Adapters: list of method definitions",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "params": {"type": "string"},
                            "return_type": {"type": "string"}
                        },
                        "required": ["name", "params", "return_type"]
                    }
                },
                "docstring": {
                    "type": "string",
                    "description": "Optional docstring for the component"
                },
                "generate_test": {
                    "type": "boolean",
                    "description": "Whether to generate a test file",
                    "default": True
                }
            },
            "required": ["component_type", "name", "output_path"]
        }

    async def execute(
        self,
        component_type: str,
        name: str,
        output_path: str,
        fields: list[dict[str, Any]] | None = None,
        input_dto: str | None = None,
        output_dto: str | None = None,
        methods: list[dict[str, str]] | None = None,
        docstring: str | None = None,
        generate_test: bool = True,
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
                # Derive module path from output path
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
                    "input_dto and output_dto are required for Worker generation",
                    hints=["Provide input_dto and output_dto class names"]
                )
            
            content = self.manager.render_worker(
                name=name,
                input_dto=input_dto,
                output_dto=output_dto
            )
            self.manager.write_file(output_path, content)
            created_files.append(output_path)
            
        elif component_type == "adapter":
            if not methods:
                raise ValidationError(
                    "Methods are required for Adapter generation",
                    hints=["Provide methods as list of {name, params, return_type} objects"]
                )
            
            content = self.manager.render_adapter(
                name=name,
                methods=methods
            )
            self.manager.write_file(output_path, content)
            created_files.append(output_path)
            
        else:
            raise ValidationError(
                f"Unknown component type: {component_type}",
                hints=["Use dto, worker, or adapter"]
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
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
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
                    "description": "List of section headings"
                },
                "status": {
                    "type": "string",
                    "enum": ["DRAFT", "REVIEW", "APPROVED"],
                    "default": "DRAFT"
                }
            },
            "required": ["title", "output_path"]
        }

    async def execute(
        self,
        title: str,
        output_path: str,
        author: str | None = None,
        summary: str | None = None,
        sections: list[str] | None = None,
        status: str = "DRAFT",
        **kwargs: Any
    ) -> ToolResult:
        """Execute design document scaffolding."""
        content = self.manager.render_design_doc(
            title=title,
            author=author,
            summary=summary,
            sections=sections,
            status=status
        )
        
        self.manager.write_file(output_path, content)
        
        return ToolResult.text(f"Created design document: {output_path}")
