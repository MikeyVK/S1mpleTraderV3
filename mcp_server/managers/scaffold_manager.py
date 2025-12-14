"""Scaffolding manager for rendering templates and writing files."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from mcp_server.core.exceptions import ExecutionError, ValidationError
from mcp_server.config.settings import settings


class ScaffoldManager:
    """Manager responsible for scaffolding code and docs via templates."""

    def __init__(self, template_dir: Optional[Path] = None) -> None:
        self.template_dir = template_dir or (Path(__file__).resolve().parent.parent / "templates")
        self._env: Environment | None = None

    @property
    def env(self) -> Environment:
        if self._env is None:
            loader = FileSystemLoader(str(self.template_dir))
            self._env = Environment(loader=loader, autoescape=False)
        return self._env

    def get_template(self, name: str):
        try:
            return self.env.get_template(name)
        except TemplateNotFound as e:
            raise ExecutionError(f"Template not found: {name}") from e

    def list_templates(self) -> list[Path]:
        return [Path(str(p.relative_to(self.template_dir))) for p in self.template_dir.rglob("*.jinja2")]

    # --- Validation helpers ---
    def _validate_pascal_case(self, name: str) -> None:
        if not name or not name[0].isupper() or "_" in name or not name.replace("_", "").isalpha():
            raise ValidationError("Invalid name: must be PascalCase without underscores")

    # --- Render DTO ---
    def render_dto(self, name: str, fields: list[dict[str, Any]]) -> str:
        self._validate_pascal_case(name)
        try:
            tmpl = self.env.get_template("components/dto.py.jinja2")
            return tmpl.render(name=name, fields=fields)
        except TemplateNotFound:
            # Fall back to base component template for .py files
            tmpl = self.env.get_template("base/base_component.py.jinja2")
            return tmpl.render(name=name, fields=fields, component_type="DTO")

    # --- Render Worker ---
    def render_worker(self, name: str, input_type: str, output_type: str, dependencies: Optional[list[str]] = None) -> str:
        try:
            tmpl = self.env.get_template("components/worker.py.jinja2")
            return tmpl.render(name=f"{name}Worker", input_type=input_type, output_type=output_type, dependencies=dependencies or [])
        except TemplateNotFound:
            # Fall back to base component template for .py files
            tmpl = self.env.get_template("base/base_component.py.jinja2")
            return tmpl.render(name=f"{name}Worker", input_type=input_type, output_type=output_type, dependencies=dependencies or [], component_type="Worker")

    # --- Render Adapter ---
    def render_adapter(self, name: str, methods: list[dict[str, str]]) -> str:
        try:
            tmpl = self.env.get_template("components/adapter.py.jinja2")
            return tmpl.render(name=f"{name}Adapter", methods=methods)
        except TemplateNotFound:
            # Fall back to base component template for .py files
            tmpl = self.env.get_template("base/base_component.py.jinja2")
            return tmpl.render(name=f"{name}Adapter", methods=methods, component_type="Adapter")

    def render_tool(self, name: str, description: str) -> str:
        try:
            tmpl = self.env.get_template("components/tool.py.jinja2")
            return tmpl.render(name=name, description=description)
        except TemplateNotFound:
            # Fall back to base component template for .py files
            tmpl = self.env.get_template("base/base_component.py.jinja2")
            return tmpl.render(name=name, description=description, component_type="Tool")

    def render_resource(self, name: str, description: str) -> str:
        try:
            tmpl = self.env.get_template("components/resource.py.jinja2")
            return tmpl.render(name=name, description=description)
        except TemplateNotFound:
            # Fall back to base component template for .py files
            tmpl = self.env.get_template("base/base_component.py.jinja2")
            return tmpl.render(name=name, description=description, component_type="Resource")

    def render_schema(self, name: str) -> str:
        try:
            tmpl = self.env.get_template("components/schema.py.jinja2")
            return tmpl.render(name=name)
        except TemplateNotFound:
            # Fall back to base component template for .py files
            tmpl = self.env.get_template("base/base_component.py.jinja2")
            return tmpl.render(name=name, component_type="Schema")

    def render_interface(self, name: str) -> str:
        try:
            tmpl = self.env.get_template("components/interface.py.jinja2")
            return tmpl.render(name=name)
        except TemplateNotFound:
            # Fall back to base component template for .py files
            tmpl = self.env.get_template("base/base_component.py.jinja2")
            return tmpl.render(name=name, component_type="Interface")

    # --- Render Tests ---
    def render_dto_test(self, dto_name: str, import_path: str) -> str:
        try:
            tmpl = self.env.get_template("tests/dto_test.py.jinja2")
            return tmpl.render(dto_name=dto_name, import_path=import_path)
        except TemplateNotFound:
            # Fall back to base test template for .py files
            tmpl = self.env.get_template("base/base_test.py.jinja2")
            return tmpl.render(test_name=f"Test{dto_name}", import_path=import_path, test_type="DTO", component_name=dto_name)

    def render_worker_test(self, worker_name: str, import_path: str) -> str:
        try:
            tmpl = self.env.get_template("tests/worker_test.py.jinja2")
            return tmpl.render(worker_name=worker_name, import_path=import_path)
        except TemplateNotFound:
            # Fall back to base test template for .py files
            tmpl = self.env.get_template("base/base_test.py.jinja2")
            return tmpl.render(test_name=f"Test{worker_name}", import_path=import_path, test_type="Worker", component_name=worker_name)

    # --- Generic rendering ---
    def render_generic(self, template_name: str, context: dict[str, Any]) -> str:
        tmpl = self.get_template(template_name)
        return tmpl.render(**context)

    # --- Advanced Docs ---
    def render_service(self, name: str, service_type: str) -> str:
        try:
            tmpl = self.env.get_template("components/service.py.jinja2")
            return tmpl.render(name=name, service_type=service_type)
        except TemplateNotFound:
            # Fall back to base component template for .py files
            tmpl = self.env.get_template("base/base_component.py.jinja2")
            return tmpl.render(name=name, service_type=service_type, component_type="Service")

    def render_design_doc(self, title: str, author: str, summary: str | None = None) -> str:
        try:
            tmpl = self.env.get_template("documents/design_doc.md.jinja2")
            return tmpl.render(title=title, author=author, summary=summary)
        except TemplateNotFound:
            # Fall back to base document template for .md files
            tmpl = self.env.get_template("base/base_document.md.jinja2")
            return tmpl.render(title=title, author=author, summary=summary, doc_type="Design")

    def render_generic_doc(self, title: str) -> str:
        try:
            tmpl = self.env.get_template("documents/generic_doc.md.jinja2")
            return tmpl.render(title=title)
        except TemplateNotFound:
            # Fall back to base document template for .md files
            tmpl = self.env.get_template("base/base_document.md.jinja2")
            return tmpl.render(title=title, doc_type="Generic")

    def render_architecture_doc(self, title: str) -> str:
        try:
            tmpl = self.env.get_template("documents/architecture_doc.md.jinja2")
            return tmpl.render(title=title)
        except TemplateNotFound:
            # Fall back to base document template for .md files
            tmpl = self.env.get_template("base/base_document.md.jinja2")
            return tmpl.render(title=title, doc_type="Architecture")

    def render_reference_doc(self, title: str) -> str:
        try:
            tmpl = self.env.get_template("documents/reference_doc.md.jinja2")
            return tmpl.render(title=title)
        except TemplateNotFound:
            # Fall back to base document template for .md files
            tmpl = self.env.get_template("base/base_document.md.jinja2")
            return tmpl.render(title=title, doc_type="Reference")

    def render_tracking_doc(self, title: str) -> str:
        try:
            tmpl = self.env.get_template("documents/tracking_doc.md.jinja2")
            return tmpl.render(title=title)
        except TemplateNotFound:
            # Fall back to base document template for .md files
            tmpl = self.env.get_template("base/base_document.md.jinja2")
            return tmpl.render(title=title, doc_type="Tracking")

    # --- File writing ---
    def write_file(self, relative_path: str, content: str, overwrite: bool = False) -> bool:
        root = Path(settings.server.workspace_root)
        full_path = root / relative_path
        if full_path.exists() and not overwrite:
            raise ExecutionError("File exists: use overwrite=True")
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
