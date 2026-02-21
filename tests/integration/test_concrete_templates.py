"""
RED tests for Task 1.6: Concrete template existence and basic scaffolding.

Documents requirement that 5 concrete templates must exist and scaffold successfully:
- dto.py.jinja2
- worker.py.jinja2
- service_command.py.jinja2
- generic.py.jinja2
- design.md.jinja2
"""

import pytest

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.config.template_config import get_template_root
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer


class TestConcreteTemplateExistence:
    """Test that required concrete templates exist (Task 1.6 RED)."""

    def test_dto_template_exists(self):
        """dto.py.jinja2 must exist in templates/concrete/."""
        template_root = get_template_root()
        dto_template = template_root / "concrete" / "dto.py.jinja2"

        # REQUIREMENT: Concrete template for dto artifact type
        # Currently FAILS - file does not exist
        assert dto_template.exists(), f"Missing: {dto_template}"

    def test_worker_template_exists(self):
        """worker.py.jinja2 must exist in templates/concrete/."""
        template_root = get_template_root()
        worker_template = template_root / "concrete" / "worker.py.jinja2"

        # REQUIREMENT: Concrete template for worker artifact type
        assert worker_template.exists(), f"Missing: {worker_template}"

    def test_service_command_template_exists(self):
        """service_command.py.jinja2 must exist in templates/concrete/."""
        template_root = get_template_root()
        service_template = template_root / "concrete" / "service_command.py.jinja2"

        # REQUIREMENT: Concrete template for service_command artifact type
        assert service_template.exists(), f"Missing: {service_template}"

    def test_generic_template_exists(self):
        """generic.py.jinja2 must exist in templates/concrete/."""
        template_root = get_template_root()
        generic_template = template_root / "concrete" / "generic.py.jinja2"

        # REQUIREMENT: Concrete template for generic artifact type (catch-all)
        assert generic_template.exists(), f"Missing: {generic_template}"

    def test_design_template_exists(self):
        """design.md.jinja2 must exist in templates/concrete/."""
        template_root = get_template_root()
        design_template = template_root / "concrete" / "design.md.jinja2"

        # REQUIREMENT: Concrete template for design doc artifact type
        assert design_template.exists(), f"Missing: {design_template}"


class TestScaffoldedOutputCodingStandards:
    """Test that scaffolded output adheres to coding standards (Task 1.6 RED).

    REQUIREMENT: Generated code must include:
    - Module docstring with @layer, @dependencies, @responsibilities
    - Import section headers: "# Standard library", "# Third-party", "# Project modules"
    """

    def test_scaffolded_dto_has_module_docstring_with_annotations(self):
        """Scaffolded DTO must have module docstring with @layer/@dependencies/@responsibilities.

        RED: This test WILL FAIL until tier1_base_code adds module_docstring block.
        """
        # Setup scaffolder
        registry = ArtifactRegistryConfig.from_file()
        renderer = JinjaRenderer(template_dir=get_template_root())
        scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)

        # Scaffold DTO with coding standards context
        result = scaffolder.scaffold(
            artifact_type="dto",
            name="TestDTO",
            layer="Backend (DTOs)",
            dependencies=["pydantic", "typing"],
            responsibilities=["Define data contract", "Validate input"],
            fields=[
                {"name": "id", "type": "str", "description": "Unique identifier"},
                {"name": "value", "type": "int", "description": "Numeric value"},
            ],
            frozen=True,
            examples=[{"id": "test-123", "value": 42}],
        )

        # REQUIREMENT: Module docstring must exist after SCAFFOLD header (2-line format)
        content = result.content
        lines = content.split("\n")

        # In 2-line format:
        # Line 0: # filepath
        # Line 1: # template=... metadata
        # Line 2: (blank or docstring start)
        assert lines[0].startswith("#"), "Line 0 should be filepath comment"
        assert "template=" in lines[1], "Line 1 should have metadata"

        # Module docstring should follow SCAFFOLD metadata (line 2 or after blank line)
        docstring_start_idx = 2
        # Skip blank line if present
        if not lines[docstring_start_idx].strip():
            docstring_start_idx = 3

        assert lines[docstring_start_idx].strip().startswith('"""'), (
            f"Module docstring must follow SCAFFOLD header, found: {lines[docstring_start_idx]}"
        )

        # Collect full docstring
        docstring_lines = []
        in_docstring = False
        for line in lines[docstring_start_idx:]:
            if '"""' in line:
                if not in_docstring:
                    in_docstring = True
                    docstring_lines.append(line)
                else:
                    docstring_lines.append(line)
                    break
            elif in_docstring:
                docstring_lines.append(line)

        docstring_text = "\n".join(docstring_lines)

        # REQUIREMENT: Must contain @layer
        assert "@layer:" in docstring_text, "Module docstring must contain @layer annotation"
        assert "Backend (DTOs)" in docstring_text, "Module docstring must contain layer value"

        # REQUIREMENT: Must contain @dependencies
        assert "@dependencies:" in docstring_text, (
            "Module docstring must contain @dependencies annotation"
        )

        # REQUIREMENT: Must contain @responsibilities
        assert "@responsibilities:" in docstring_text, (
            "Module docstring must contain @responsibilities annotation"
        )

    def test_scaffolded_worker_has_import_section_headers(self):
        """Scaffolded worker must have import section headers.

        RED: This test WILL FAIL until tier1_base_code adds section headers.
        """
        # Setup scaffolder
        registry = ArtifactRegistryConfig.from_file()
        renderer = JinjaRenderer(template_dir=get_template_root())
        scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)

        # Scaffold worker with coding standards context
        result = scaffolder.scaffold(
            artifact_type="worker",
            name="TestWorker",
            layer="Backend (Workers)",
            dependencies=["typing", "asyncio"],
            responsibilities=["Process background tasks"],
            imports={"stdlib": ["asyncio", "typing"], "third_party": [], "project": []},
        )

        content = result.content
        lines = content.split("\n")

        # REQUIREMENT: Must have "# Standard library" header
        assert any("# Standard library" in line for line in lines), (
            "Import section must have '# Standard library' header"
        )

        # REQUIREMENT: Must have "# Third-party" header
        assert any("# Third-party" in line for line in lines), (
            "Import section must have '# Third-party' header"
        )

        # REQUIREMENT: Must have "# Project modules" header
        assert any("# Project modules" in line for line in lines), (
            "Import section must have '# Project modules' header"
        )

    def test_scaffolded_generic_has_complete_coding_standards(self):
        """Scaffolded generic class must have both module docstring AND import headers.

        RED: This test WILL FAIL until both features are implemented.
        """
        # Setup scaffolder
        registry = ArtifactRegistryConfig.from_file()
        renderer = JinjaRenderer(template_dir=get_template_root())
        scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)

        # Scaffold generic class WITH imports to test section headers
        result = scaffolder.scaffold(
            artifact_type="generic",
            name="TestClass",
            layer="Backend (Utils)",
            dependencies=["os", "sys"],
            responsibilities=["Utility functionality"],
            imports={
                "stdlib": ["import os", "import sys"],
                "third_party": ["from typing import Any"],
                "project": ["from myproject.utils import Something"],
            },
        )

        content = result.content

        # REQUIREMENT 1: Module docstring with annotations
        assert "@layer:" in content
        assert "@dependencies:" in content
        assert "@responsibilities:" in content

        # REQUIREMENT 2: Import section headers (only when imports present)
        assert "# Standard library" in content
        assert "# Third-party" in content
        assert "# Project modules" in content


class TestWorkerIWorkerLifecyclePattern:
    """Test that scaffolded worker implements IWorkerLifecycle pattern (Task 2.2 RED).

    REQUIREMENT (Issue #72 Phase 2 Task 2.2):
    Worker template MUST generate IWorkerLifecycle pattern:
    - __init__(self, build_spec: BuildSpec) - Construction phase (config only)
    - initialize(self, strategy_cache, **capabilities) - Runtime init (DI)
    - shutdown(self) - Cleanup phase
    - name property (IWorker requirement)

    This ensures V3 two-phase initialization pattern (not V2 constructor injection).
    """

    def test_scaffolded_worker_has_iworker_lifecycle_imports(self):
        """Worker must import IWorker, IWorkerLifecycle, BuildSpec, and related types.

        RED: This test WILL FAIL until worker.py.jinja2 exists with IWorkerLifecycle pattern.
        """
        registry = ArtifactRegistryConfig.from_file()
        renderer = JinjaRenderer(template_dir=get_template_root())
        scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)

        result = scaffolder.scaffold(
            artifact_type="worker",
            name="TestWorker",
            layer="Backend (Workers)",
            worker_scope="strategy",  # strategy|platform|platform_within_strategy
            responsibilities=["Process trading signals"],
        )

        content = result.content

        # REQUIREMENT: Must import IWorker + IWorkerLifecycle protocols
        assert "IWorker" in content or "IWorkerLifecycle" in content, (
            "Worker must import IWorker/IWorkerLifecycle protocols"
        )

        # REQUIREMENT: Must import BuildSpec for construction
        assert "BuildSpec" in content, "Worker must import BuildSpec for __init__ signature"

        # REQUIREMENT: Must import IStrategyCache for initialize()
        assert "IStrategyCache" in content, (
            "Worker must import IStrategyCache for initialize() signature"
        )

    def test_scaffolded_worker_implements_protocols(self):
        """Worker class must explicitly implement IWorker and IWorkerLifecycle.

        RED: This test WILL FAIL until template generates protocol implementation.
        """
        registry = ArtifactRegistryConfig.from_file()
        renderer = JinjaRenderer(template_dir=get_template_root())
        scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)

        result = scaffolder.scaffold(
            artifact_type="worker",
            name="SignalDetector",
            layer="Backend (Workers)",
            worker_scope="strategy",
            responsibilities=["Detect trading signals"],
        )

        content = result.content

        # REQUIREMENT: Class must implement both protocols
        assert (
            "class SignalDetector(IWorker, IWorkerLifecycle):" in content
            or "class SignalDetector(IWorkerLifecycle):" in content
        ), "Worker class must implement IWorker + IWorkerLifecycle protocols"

    def test_scaffolded_worker_has_build_spec_constructor(self):
        """Worker __init__ must accept BuildSpec only (no dependencies).

        RED: This test WILL FAIL until template generates V3 construction pattern.
        """
        registry = ArtifactRegistryConfig.from_file()
        renderer = JinjaRenderer(template_dir=get_template_root())
        scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)

        result = scaffolder.scaffold(
            artifact_type="worker",
            name="RiskMonitor",
            layer="Backend (Workers)",
            worker_scope="strategy",
            responsibilities=["Monitor portfolio risk"],
        )

        content = result.content

        # REQUIREMENT: __init__ signature must be (self, build_spec: BuildSpec)
        assert "def __init__(self, build_spec: BuildSpec)" in content, (
            "Worker __init__ must accept BuildSpec only (V3 pattern, not V2 constructor injection)"
        )

        # REQUIREMENT: Must NOT have dependency parameters in __init__
        # (dependencies injected via initialize(), not constructor)
        init_section = content[content.find("def __init__") : content.find("def __init__") + 200]
        assert "EventBus" not in init_section, (
            "Worker __init__ must NOT accept EventBus (use initialize() for DI)"
        )
        assert "Logger" not in init_section or "# " in init_section, (
            "Worker __init__ must NOT accept Logger in parameters (use initialize() for DI)"
        )

    def test_scaffolded_worker_has_initialize_method(self):
        """Worker must have initialize() method for two-phase initialization.

        RED: This test WILL FAIL until template generates initialize() method.
        """
        registry = ArtifactRegistryConfig.from_file()
        renderer = JinjaRenderer(template_dir=get_template_root())
        scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)

        result = scaffolder.scaffold(
            artifact_type="worker",
            name="DataProcessor",
            layer="Backend (Workers)",
            worker_scope="platform",  # Platform worker: cache=None
            responsibilities=["Process market data"],
        )

        content = result.content

        # REQUIREMENT: Must have initialize() method (can be multi-line)
        assert (
            "def initialize(" in content
            and "strategy_cache: IStrategyCache" in content
            and "**capabilities" in content
        ), "Worker must have initialize() method for runtime DI"

        # REQUIREMENT: Must validate strategy_cache based on worker_scope
        if "worker_scope='platform'" in content or 'worker_scope="platform"' in content:
            # Platform workers expect cache=None
            assert "strategy_cache is None" in content or "cache validation" in content, (
                "Platform worker must validate strategy_cache is None"
            )

    def test_scaffolded_worker_has_shutdown_method(self):
        """Worker must have shutdown() method for cleanup.

        RED: This test WILL FAIL until template generates shutdown() method.
        """
        registry = ArtifactRegistryConfig.from_file()
        renderer = JinjaRenderer(template_dir=get_template_root())
        scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)

        result = scaffolder.scaffold(
            artifact_type="worker",
            name="ConnectionManager",
            layer="Backend (Workers)",
            worker_scope="strategy",
            responsibilities=["Manage database connections"],
        )

        content = result.content

        # REQUIREMENT: Must have shutdown() method
        assert "def shutdown(self)" in content, "Worker must have shutdown() method for cleanup"

        # REQUIREMENT: Shutdown must be idempotent (comment or implementation)
        shutdown_section = content[
            content.find("def shutdown") : content.find("def shutdown") + 300
        ]
        assert (
            "idempotent" in shutdown_section.lower()
            or "safely called multiple times" in shutdown_section.lower()
            or "pass" in shutdown_section
        ), "shutdown() must document idempotent behavior"

    def test_scaffolded_worker_has_name_property(self):
        """Worker must have name property (IWorker requirement).

        RED: This test WILL FAIL until template generates name property.
        """
        registry = ArtifactRegistryConfig.from_file()
        renderer = JinjaRenderer(template_dir=get_template_root())
        scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)

        result = scaffolder.scaffold(
            artifact_type="worker",
            name="EventProcessor",
            layer="Backend (Workers)",
            worker_scope="strategy",
            responsibilities=["Process domain events"],
        )

        content = result.content

        # REQUIREMENT: Must have @property decorator + name getter
        assert "@property" in content and "def name(self)" in content, (
            "Worker must have name property (IWorker protocol requirement)"
        )

        # REQUIREMENT: Name should return worker name
        assert "return" in content[content.find("def name") : content.find("def name") + 150], (
            "name property must return worker name"
        )


class TestConcreteTemplateStructure:
    """Test that concrete templates have required Jinja2 structure (Task 1.6 RED)."""

    @pytest.mark.parametrize(
        "template_name",
        ["dto.py.jinja2", "worker.py.jinja2", "service_command.py.jinja2", "generic.py.jinja2"],
    )
    def test_python_templates_have_scaffold_metadata(self, template_name: str):
        """Python concrete templates must have SCAFFOLD metadata block.

        REQUIREMENT (Task 1.6): Templates MUST inherit Tier 0 SCAFFOLD block
        for provenance tracking.
        """
        template_root = get_template_root()
        template_path = template_root / "concrete" / template_name

        # Skip if template doesn't exist yet (RED phase)
        if not template_path.exists():
            pytest.skip(f"Template not created yet: {template_name}")

        content = template_path.read_text(encoding="utf-8")

        # REQUIREMENT: Must contain TEMPLATE_METADATA block
        assert "TEMPLATE_METADATA" in content, f"{template_name} missing TEMPLATE_METADATA"

        # REQUIREMENT: Must extend tier chain (inheritance)
        assert "extends" in content or "{% extends" in content, (
            f"{template_name} must extend base template for inheritance"
        )

    def test_design_template_has_scaffold_metadata(self):
        """design.md.jinja2 must have SCAFFOLD metadata block."""
        template_root = get_template_root()
        template_path = template_root / "concrete" / "design.md.jinja2"

        if not template_path.exists():
            pytest.skip("Template not created yet")

        content = template_path.read_text(encoding="utf-8")

        # REQUIREMENT: Markdown also needs TEMPLATE_METADATA
        assert "TEMPLATE_METADATA" in content
        assert "extends" in content or "{% extends" in content
