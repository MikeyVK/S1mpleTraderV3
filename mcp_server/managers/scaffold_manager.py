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
            tmpl = self.env.get_template("dto.jinja2")
            return tmpl.render(name=name, fields=fields)
        except TemplateNotFound:
            lines = ["from dataclasses import dataclass", "", f"@dataclass", f"class {name}:"]
            if not fields:
                lines.append("    pass")
            else:
                for f in fields:
                    default = f.get("default")
                    if default is not None:
                        lines.append(f"    {f['name']}: {f['type']} = {default}")
                    else:
                        lines.append(f"    {f['name']}: {f['type']}")
            return "\n".join(lines)

    # --- Render Worker ---
    def render_worker(self, name: str, input_type: str, output_type: str, dependencies: Optional[list[str]] = None) -> str:
        try:
            tmpl = self.env.get_template("worker.jinja2")
            return tmpl.render(name=f"{name}Worker", input_type=input_type, output_type=output_type, dependencies=dependencies or [])
        except TemplateNotFound:
            cls_name = f"{name}Worker"
            lines = [f"class {cls_name}(BaseWorker[{input_type}, {output_type}]):"]
            if dependencies:
                lines.append("    def __init__(self) -> None:")
                for dep in dependencies:
                    attr = dep.split(":")[0].strip()
                    lines.append(f"        self.{attr} = {attr}")
            else:
                lines.append("    def __init__(self) -> None:")
                lines.append("        pass")
            return "\n".join(lines)

    # --- Render Adapter ---
    def render_adapter(self, name: str, methods: list[dict[str, str]]) -> str:
        try:
            tmpl = self.env.get_template("adapter.jinja2")
            return tmpl.render(name=f"{name}Adapter", methods=methods)
        except TemplateNotFound:
            lines = [f"class {name}Adapter:"]
            if not methods:
                lines.append("    pass")
            else:
                for m in methods:
                    params = m.get("params", "")
                    rt = m.get("return_type", "None")
                    lines.append(f"    def {m['name']}(self, {params}) -> {rt}:")
                    lines.append("        pass")
            return "\n".join(lines)

    # --- Render Tools/Resources/Schema/Interface ---
    def render_tool(self, name: str, description: str) -> str:
        tmpl = self.env.get_template("tool.jinja2")
        return tmpl.render(name=name, description=description)

    def render_resource(self, name: str, description: str) -> str:
        tmpl = self.env.get_template("resource.jinja2")
        return tmpl.render(name=name, description=description)

    def render_schema(self, name: str) -> str:
        tmpl = self.env.get_template("schema.jinja2")
        return tmpl.render(name=name)

    def render_interface(self, name: str) -> str:
        tmpl = self.env.get_template("interface.jinja2")
        return tmpl.render(name=name)

    # --- Render Tests ---
    def render_dto_test(self, dto_name: str, import_path: str) -> str:
        try:
            tmpl = self.env.get_template("dto_test.jinja2")
            return tmpl.render(dto_name=dto_name, import_path=import_path)
        except TemplateNotFound:
            lines = [f"from {import_path} import {dto_name}", "", f"class Test{dto_name}:", "    def test_init(self) -> None:", f"        _ = {dto_name}()"]
            return "\n".join(lines)

    def render_worker_test(self, worker_name: str, import_path: str) -> str:
        try:
            tmpl = self.env.get_template("worker_test.jinja2")
            return tmpl.render(worker_name=worker_name, import_path=import_path)
        except TemplateNotFound:
            lines = [f"from {import_path} import {worker_name}", "", "class TestMyWorkerProcessing:", "    def test_process(self) -> None:", f"        _ = {worker_name}()"]
            return "\n".join(lines)

    # --- Generic rendering ---
    def render_generic(self, template_name: str, context: dict[str, Any]) -> str:
        tmpl = self.get_template(template_name)
        return tmpl.render(**context)

    # --- Advanced Docs ---
    def render_service(self, name: str, service_type: str) -> str:
        tmpl = self.env.get_template("service.jinja2")
        return tmpl.render(name=name, service_type=service_type)

    def render_design_doc(self, title: str, author: str, summary: str | None = None) -> str:
        try:
            tmpl = self.env.get_template("design_doc.jinja2")
            return tmpl.render(title=title, author=author, summary=summary)
        except TemplateNotFound:
            lines = [f"# {title}", "", f"**Author:** {author}"]
            if summary:
                lines += ["", "## Summary", summary]
            return "\n".join(lines)

    def render_generic_doc(self, title: str) -> str:
        tmpl = self.env.get_template("generic_doc.jinja2")
        return tmpl.render(title=title)

    def render_architecture_doc(self, title: str) -> str:
        tmpl = self.env.get_template("architecture_doc.jinja2")
        return tmpl.render(title=title)

    def render_reference_doc(self, title: str) -> str:
        tmpl = self.env.get_template("reference_doc.jinja2")
        return tmpl.render(title=title)

    def render_tracking_doc(self, title: str) -> str:
        tmpl = self.env.get_template("tracking_doc.jinja2")
        return tmpl.render(title=title)

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
