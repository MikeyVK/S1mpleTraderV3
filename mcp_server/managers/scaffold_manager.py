"""Scaffold Manager for template-driven code generation."""
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from mcp_server.config.settings import settings
from mcp_server.core.exceptions import ExecutionError, ValidationError


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
        description: str | None = None,
        extended_description: str | None = None,
        id_prefix: str | None = None,
        has_causality: bool = False,
        has_timestamp: bool = True,
        has_id_generator: bool = False,
        frozen: bool = True,
        layer: str = "Strategy",
        examples: list[dict[str, Any]] | None = None,
        custom_validators: list[dict[str, Any]] | None = None,
    ) -> str:
        """Render a DTO (Data Transfer Object).

        Generates a Pydantic-based DTO following project coding standards:
        - Proper import grouping (stdlib, third-party, project)
        - ID validation with military datetime format
        - Optional causality tracking
        - UTC timestamp handling
        - json_schema_extra with examples
        - frozen=True by default

        Args:
            name: DTO class name (PascalCase)
            fields: List of field definitions with keys:
                - name: Field name
                - type: Field type
                - default: Optional default value
                - optional: If True, makes field optional (X | None)
                - description: Field description for Field()
                - ge, le, min_length, max_length, pattern: Validation constraints
            docstring: Optional class docstring
            description: Short description for module docstring
            extended_description: Extended description for module docstring
            id_prefix: ID prefix for validation (e.g., 'SIG' for Signal DTO)
            has_causality: Include CausalityChain field
            has_timestamp: Include timestamp field with UTC validation
            has_id_generator: Use id_generator from backend.utils
            frozen: Whether DTO is immutable (default: True)
            layer: Architecture layer (e.g., 'Strategy', 'Execution')
            examples: List of example dicts for json_schema_extra
            custom_validators: List of custom validators with keys:
                - field: Field name to validate
                - type: Field type
                - description: Validator docstring
                - code: Validation code

        Returns:
            Rendered Python code as string
        """
        self._validate_pascal_case(name)

        # Derive id_prefix from name if not provided
        if not id_prefix:
            # Extract prefix from name: SignalDTO -> SIG, EntryPlan -> ENT
            clean_name = name.replace("DTO", "").replace("Plan", "")
            id_prefix = clean_name[:3].upper()

        try:
            template = self.get_template("components/dto.py.jinja2")
            return template.render(
                name=name,
                fields=fields,
                docstring=docstring or f"{name} data transfer object.",
                description=description,
                extended_description=extended_description,
                id_prefix=id_prefix,
                has_causality=has_causality,
                has_timestamp=has_timestamp,
                has_id_generator=has_id_generator,
                frozen=frozen,
                layer=layer,
                examples=examples,
                custom_validators=custom_validators,
            )
        except ExecutionError:
            # Fallback: generate without template
            return self._render_dto_fallback(name, fields, docstring)

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
        worker_type: str = "context_worker",
        dependencies: list[str] | None = None,
        description: str | None = None,
        extended_description: str | None = None,
        responsibilities: list[str] | None = None,
        pipeline_position: str | None = None,
        has_causality: bool = True,
        input_dto_module: str | None = None,
        output_dto_module: str | None = None,
    ) -> str:
        """Render a Worker class.

        Generates a Worker following project patterns:
        - Proper import grouping
        - BaseWorker inheritance with generic types
        - IStrategyCache dependency injection
        - Async process method
        - DispositionType handling
        - ContextWorker objective data constraints

        Args:
            name: Worker name (will add 'Worker' suffix if needed)
            input_dto: Input DTO class name
            output_dto: Output DTO class name
            worker_type: Worker category (context_worker, signal_detector,
                risk_monitor, planning_worker, strategy_planner, execution_worker)
            dependencies: List of dependency declarations (e.g., ['config: Config'])
            description: Short description for module docstring
            extended_description: Extended description
            responsibilities: List of worker responsibilities
            pipeline_position: Position in processing pipeline
            has_causality: Whether to chain causality from input to output
            input_dto_module: Import path for input DTO
            output_dto_module: Import path for output DTO

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
                worker_type=worker_type,
                dependencies=dependencies or [],
                description=description,
                extended_description=extended_description,
                responsibilities=responsibilities,
                pipeline_position=pipeline_position,
                has_causality=has_causality,
                input_dto_module=input_dto_module,
                output_dto_module=output_dto_module,
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
        description: str | None = None,
        extended_description: str | None = None,
        responsibilities: list[str] | None = None,
        constructor_params: str | None = None,
        exception_type: str = "ExecutionError",
        layer: str = "Infrastructure",
    ) -> str:
        """Render an Adapter class.

        Generates an Adapter following project patterns:
        - Interface definition (Protocol)
        - Proper import grouping
        - Error handling with project exceptions
        - Dependency injection via constructor

        Args:
            name: Adapter name (will add 'Adapter' suffix if needed)
            methods: List of method definitions with keys:
                - name: Method name
                - params: Parameter string (e.g., 'data: dict[str, Any]')
                - return_type: Return type
                - description: Method docstring
                - return_description: Description of return value
            description: Short description for module docstring
            extended_description: Extended description
            responsibilities: List of adapter responsibilities
            constructor_params: Constructor parameter string
            exception_type: Exception type to raise on errors
            layer: Architecture layer

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
                description=description,
                extended_description=extended_description,
                responsibilities=responsibilities,
                constructor_params=constructor_params,
                exception_type=exception_type,
                layer=layer,
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
        description: str | None = None,
        id_prefix: str | None = None,
        has_timestamp: bool = True,
        has_causality: bool = False,
        frozen: bool = True,
        required_fields: list[dict[str, Any]] | None = None,
        optional_fields: list[dict[str, Any]] | None = None,
        validated_fields: list[dict[str, Any]] | None = None,
    ) -> str:
        """Render a test file for a DTO.

        Generates comprehensive tests following project TDD requirements:
        - 20+ tests for complex DTOs
        - Creation, validation, immutability, edge cases
        - ID format validation
        - Timestamp UTC handling (if applicable)
        - Field-specific validation tests

        Args:
            dto_name: Name of the DTO class to test
            module_path: Import path for the DTO module
            description: Test module description
            id_prefix: ID prefix for validation tests
            has_timestamp: Whether DTO has timestamp field
            has_causality: Whether DTO tracks causality
            frozen: Whether DTO is immutable
            required_fields: List of required fields with keys:
                - name: Field name
                - example: Example value for tests
            optional_fields: List of optional fields
            validated_fields: List of fields with validation to test, with keys:
                - name: Field name
                - valid_example: Valid value
                - invalid_example: Invalid value (optional)
                - min_value, max_value: Range bounds (optional)

        Returns:
            Rendered Python test code as string
        """
        # Derive id_prefix from name if not provided
        if not id_prefix:
            clean_name = dto_name.replace("DTO", "").replace("Plan", "")
            id_prefix = clean_name[:3].upper()

        # Combine all fields for certain tests
        all_fields = (required_fields or []) + (optional_fields or [])

        try:
            template = self.get_template("components/dto_test.py.jinja2")
            return template.render(
                dto_name=dto_name,
                module_path=module_path,
                description=description,
                id_prefix=id_prefix,
                has_timestamp=has_timestamp,
                has_causality=has_causality,
                frozen=frozen,
                required_fields=required_fields or [],
                optional_fields=optional_fields or [],
                validated_fields=validated_fields or [],
                all_fields=all_fields,
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

    def render_worker_test(
        self,
        worker_name: str,
        module_path: str,
        input_dto: str | None = None,
        output_dto: str | None = None,
        worker_type: str = "context_worker",
        description: str | None = None,
        dependencies: list[str] | None = None,
    ) -> str:
        """Render a test file for a Worker.

        Generates comprehensive tests following project TDD requirements:
        - Processing tests with valid/invalid input
        - Dependency injection tests
        - Error handling and recovery
        - Output contract validation

        Args:
            worker_name: Name of the Worker class to test
            module_path: Import path for the Worker module
            input_dto: Input DTO class name
            output_dto: Output DTO class name
            worker_type: Type of worker (context_worker, signal_detector, etc.)
            description: Test module description
            dependencies: List of dependencies to mock in tests

        Returns:
            Rendered Python test code as string
        """
        try:
            template = self.get_template("components/worker_test.py.jinja2")
            return template.render(
                worker_name=worker_name,
                module_path=module_path,
                input_dto=input_dto,
                output_dto=output_dto,
                worker_type=worker_type,
                description=description,
                dependencies=dependencies or [],
            )
        except ExecutionError:
            return self._render_worker_test_fallback(worker_name, module_path)

    def _render_worker_test_fallback(self, worker_name: str, module_path: str) -> str:
        """Fallback worker test rendering without template."""
        return f'''"""Tests for {worker_name}."""
import pytest
from {module_path} import {worker_name}


class Test{worker_name}Processing:
    """Tests for {worker_name} processing logic."""

    def test_process_valid_input(self) -> None:
        """Test processing with valid input."""
        # TODO: Add test implementation
        pass

    def test_process_invalid_input(self) -> None:
        """Test processing with invalid input raises error."""
        # TODO: Add test implementation
        pass


class Test{worker_name}ErrorHandling:
    """Tests for {worker_name} error handling."""

    def test_handles_missing_dependency(self) -> None:
        """Test graceful handling of missing dependencies."""
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
        version: str = "0.1.0",
        context: str | None = None,
        problem_statement: str | None = None,
        goals: list[str] | None = None,
        requirements: list[dict[str, str]] | None = None,
        design_decision: str | None = None,
        alternatives: list[dict[str, str]] | None = None,
        implementation_steps: list[str] | None = None,
        tdd_phases: list[dict[str, Any]] | None = None,
        risks: list[dict[str, str]] | None = None,
    ) -> str:
        """Render a design document.

        Generates comprehensive design documentation following project standards:
        - Version history with status tracking
        - Problem statement and context
        - Goals and requirements (functional/non-functional)
        - Design decisions with alternatives considered
        - TDD implementation phases
        - Risk assessment

        Args:
            title: Document title
            author: Document author
            summary: Executive summary
            sections: List of section headings to include (for simple docs)
            status: Document status (DRAFT, REVIEW, APPROVED)
            version: Document version (semver)
            context: System context description
            problem_statement: Problem being solved
            goals: List of goals
            requirements: List of requirements with keys:
                - id: Requirement ID (FR-001, NFR-001)
                - description: Requirement description
                - priority: Priority (Must/Should/Could)
            design_decision: Main design decision description
            alternatives: List of alternatives with keys:
                - name: Alternative name
                - pros: Pros description
                - cons: Cons description
            implementation_steps: List of implementation steps
            tdd_phases: List of TDD phases with keys:
                - phase: Phase name (Red/Green/Refactor)
                - tasks: List of task descriptions
            risks: List of risks with keys:
                - description: Risk description
                - mitigation: Mitigation strategy
                - impact: Impact level (High/Medium/Low)

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
                version=version,
                context=context,
                problem_statement=problem_statement,
                goals=goals or [],
                requirements=requirements or [],
                design_decision=design_decision,
                alternatives=alternatives or [],
                implementation_steps=implementation_steps or [],
                tdd_phases=tdd_phases or [],
                risks=risks or [],
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
