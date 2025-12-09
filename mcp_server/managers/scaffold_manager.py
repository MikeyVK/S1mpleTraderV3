"""Scaffold Manager for template-driven code generation."""
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from mcp_server.core.exceptions import ValidationError, ExecutionError
from mcp_server.config.settings import settings


class ScaffoldManager:
    """Manager for template-driven code and document generation.
    
    Uses Jinja2 templates to generate:
    - DTOs (frozen dataclasses)
    - Workers (async processors)
    - Adapters (external integrations)
    - Tests (pytest test files)
    - Design documents (markdown)
    """

    def __init__(self, template_dir: Path | None = None) -> None:
        """Initialize the scaffold manager.
        
        Args:
            template_dir: Path to templates directory. Defaults to mcp_server/templates.
        """
        if template_dir:
            self.template_dir = template_dir
        else:
            # Default to mcp_server/templates relative to this file
            self.template_dir = Path(__file__).parent.parent / "templates"
        
        self._env: Environment | None = None

    @property
    def env(self) -> Environment:
        """Get or create the Jinja2 environment."""
        if self._env is None:
            self._env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True,
            )
        return self._env

    def get_template(self, template_name: str) -> Any:
        """Load a template by name.
        
        Args:
            template_name: Relative path to template (e.g., 'components/dto.py.jinja2')
            
        Returns:
            Loaded Jinja2 template
            
        Raises:
            ExecutionError: If template not found
        """
        try:
            return self.env.get_template(template_name)
        except TemplateNotFound as e:
            raise ExecutionError(
                f"Template not found: {template_name}",
                recovery=["Check template directory structure"]
            ) from e

    def list_templates(self) -> list[str]:
        """List all available templates.
        
        Returns:
            List of template names
        """
        templates: list[str] = []
        if self.template_dir.exists():
            for path in self.template_dir.rglob("*.jinja2"):
                templates.append(str(path.relative_to(self.template_dir)))
        return templates

    def _validate_pascal_case(self, name: str) -> None:
        """Validate name is PascalCase.
        
        Args:
            name: Name to validate
            
        Raises:
            ValidationError: If not PascalCase
        """
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
            raise ValidationError(
                f"Invalid name: {name}. Must be PascalCase.",
                hints=["Use PascalCase like 'OrderState' or 'ConfigDTO'"]
            )

    def render_dto(
        self,
        name: str,
        fields: list[dict[str, Any]],
        docstring: str | None = None,
    ) -> str:
        """Render a DTO (Data Transfer Object).
        
        Args:
            name: DTO class name (PascalCase)
            fields: List of field definitions with 'name', 'type', optional 'default', 'optional'
            docstring: Optional class docstring
            
        Returns:
            Rendered Python code as string
        """
        self._validate_pascal_case(name)
        
        # Process fields for optional handling
        processed_fields = []
        for field in fields:
            f = field.copy()
            if f.get("optional"):
                f["type"] = f"{f['type']} | None"
                if "default" not in f:
                    f["default"] = "None"
            processed_fields.append(f)
        
        try:
            template = self.get_template("components/dto.py.jinja2")
            return template.render(
                name=name,
                fields=processed_fields,
                docstring=docstring or f"{name} data transfer object.",
            )
        except ExecutionError:
            # Fallback: generate without template
            return self._render_dto_fallback(name, processed_fields, docstring)

    def _render_dto_fallback(
        self,
        name: str,
        fields: list[dict[str, Any]],
        docstring: str | None,
    ) -> str:
        """Fallback DTO rendering without template."""
        lines = [
            '"""Generated DTO module."""',
            "from dataclasses import dataclass",
            "from typing import Any",
            "",
            "",
            "@dataclass(frozen=True)",
            f"class {name}:",
            f'    """{docstring or f"{name} data transfer object."}"""',
            "",
        ]
        
        for field in fields:
            if "default" in field:
                lines.append(f"    {field['name']}: {field['type']} = {field['default']}")
            else:
                lines.append(f"    {field['name']}: {field['type']}")
        
        if not fields:
            lines.append("    pass")
        
        lines.append("")
        return "\n".join(lines)

    def render_worker(
        self,
        name: str,
        input_dto: str,
        output_dto: str,
        dependencies: list[str] | None = None,
    ) -> str:
        """Render a Worker class.
        
        Args:
            name: Worker name (will add 'Worker' suffix if needed)
            input_dto: Input DTO class name
            output_dto: Output DTO class name
            dependencies: Optional list of dependency declarations
            
        Returns:
            Rendered Python code as string
        """
        self._validate_pascal_case(name)
        
        worker_name = name if name.endswith("Worker") else f"{name}Worker"
        
        try:
            template = self.get_template("components/worker.py.jinja2")
            return template.render(
                name=worker_name,
                input_dto=input_dto,
                output_dto=output_dto,
                dependencies=dependencies or [],
            )
        except ExecutionError:
            return self._render_worker_fallback(
                worker_name, input_dto, output_dto, dependencies
            )

    def _render_worker_fallback(
        self,
        name: str,
        input_dto: str,
        output_dto: str,
        dependencies: list[str] | None,
    ) -> str:
        """Fallback Worker rendering without template."""
        deps_str = ""
        if dependencies:
            deps_str = ", " + ", ".join(dependencies)
        
        return f'''"""Generated Worker module."""
from typing import Any

from backend.core.interfaces.base_worker import BaseWorker


class {name}(BaseWorker[{input_dto}, {output_dto}]):
    """Worker that processes {input_dto} and produces {output_dto}."""

    def __init__(self{deps_str}) -> None:
        """Initialize the worker."""
        super().__init__()
{self._render_dep_assignments(dependencies)}
    async def process(self, input_data: {input_dto}) -> {output_dto}:
        """Process input and return output.
        
        Args:
            input_data: Input DTO to process
            
        Returns:
            Processed output DTO
        """
        raise NotImplementedError("Implement process method")
'''

    def _render_dep_assignments(self, dependencies: list[str] | None) -> str:
        """Render dependency assignments for __init__."""
        if not dependencies:
            return ""
        
        lines = []
        for dep in dependencies:
            name = dep.split(":")[0].strip()
            lines.append(f"        self.{name} = {name}")
        return "\n".join(lines) + "\n"

    def render_adapter(
        self,
        name: str,
        methods: list[dict[str, str]],
    ) -> str:
        """Render an Adapter class.
        
        Args:
            name: Adapter name (will add 'Adapter' suffix if needed)
            methods: List of method definitions with 'name', 'params', 'return_type'
            
        Returns:
            Rendered Python code as string
        """
        self._validate_pascal_case(name)
        
        adapter_name = name if name.endswith("Adapter") else f"{name}Adapter"
        
        try:
            template = self.get_template("components/adapter.py.jinja2")
            return template.render(
                name=adapter_name,
                methods=methods,
            )
        except ExecutionError:
            return self._render_adapter_fallback(adapter_name, methods)

    def _render_adapter_fallback(
        self,
        name: str,
        methods: list[dict[str, str]],
    ) -> str:
        """Fallback Adapter rendering without template."""
        lines = [
            '"""Generated Adapter module."""',
            "from typing import Any",
            "",
            "",
            f"class {name}:",
            f'    """{name} for external integration."""',
            "",
            "    def __init__(self) -> None:",
            '        """Initialize the adapter."""',
            "        pass",
            "",
        ]
        
        for method in methods:
            lines.extend([
                f"    def {method['name']}(self, {method['params']}) -> {method['return_type']}:",
                f'        """Execute {method["name"]} operation."""',
                "        raise NotImplementedError()",
                "",
            ])
        
        return "\n".join(lines)

    def render_dto_test(
        self,
        dto_name: str,
        module_path: str,
    ) -> str:
        """Render a test file for a DTO.
        
        Args:
            dto_name: Name of the DTO class to test
            module_path: Import path for the DTO module
            
        Returns:
            Rendered Python test code as string
        """
        try:
            template = self.get_template("components/dto_test.py.jinja2")
            return template.render(
                dto_name=dto_name,
                module_path=module_path,
            )
        except ExecutionError:
            return self._render_dto_test_fallback(dto_name, module_path)

    def _render_dto_test_fallback(self, dto_name: str, module_path: str) -> str:
        """Fallback test rendering without template."""
        return f'''"""Tests for {dto_name}."""
import pytest
from {module_path} import {dto_name}


class Test{dto_name}:
    """Tests for {dto_name} DTO."""

    def test_creation(self) -> None:
        """Test {dto_name} can be created."""
        # TODO: Add test implementation
        pass

    def test_immutability(self) -> None:
        """Test {dto_name} is immutable (frozen)."""
        # TODO: Add test implementation
        pass
'''

    def render_design_doc(
        self,
        title: str,
        author: str | None = None,
        summary: str | None = None,
        sections: list[str] | None = None,
        status: str = "DRAFT",
    ) -> str:
        """Render a design document.
        
        Args:
            title: Document title
            author: Document author
            summary: Executive summary
            sections: List of section headings to include
            status: Document status (DRAFT, REVIEW, APPROVED)
            
        Returns:
            Rendered Markdown as string
        """
        try:
            template = self.get_template("documents/design.md.jinja2")
            return template.render(
                title=title,
                author=author,
                summary=summary,
                sections=sections or ["Overview", "Requirements", "Design", "Implementation"],
                status=status,
            )
        except ExecutionError:
            return self._render_design_doc_fallback(
                title, author, summary, sections, status
            )

    def _render_design_doc_fallback(
        self,
        title: str,
        author: str | None,
        summary: str | None,
        sections: list[str] | None,
        status: str,
    ) -> str:
        """Fallback design doc rendering without template."""
        lines = [
            f"# {title}",
            "",
            f"**Status:** {status}",
        ]
        
        if author:
            lines.append(f"**Author:** {author}")
        
        lines.append("")
        
        if summary:
            lines.extend(["## Summary", "", summary, ""])
        
        for section in (sections or ["Overview", "Requirements", "Design"]):
            lines.extend([f"## {section}", "", "TODO: Add content", ""])
        
        return "\n".join(lines)

    def write_file(
        self,
        path: str,
        content: str,
        overwrite: bool = False,
    ) -> bool:
        """Write generated content to a file in the workspace.
        
        Args:
            path: Relative path within workspace
            content: Content to write
            overwrite: Whether to overwrite existing files
            
        Returns:
            True if file was written
            
        Raises:
            ExecutionError: If file exists and overwrite=False
        """
        # pylint: disable=no-member
        full_path = Path(settings.server.workspace_root) / path
        
        if full_path.exists() and not overwrite:
            raise ExecutionError(
                f"File exists: {path}. Use overwrite=True to replace.",
                recovery=["Set overwrite=True or choose a different path"]
            )
        
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True
