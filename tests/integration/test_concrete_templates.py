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

from mcp_server.config.template_config import get_template_root


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
        from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
        from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
        from mcp_server.scaffolding.renderer import JinjaRenderer
        from mcp_server.config.template_config import get_template_root

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
                {"name": "id", "type": "str"},
                {"name": "value", "type": "int"}
            ]
        )

        # REQUIREMENT: Module docstring must exist after SCAFFOLD header
        content = result.content
        lines = content.split("\n")

        # Find SCAFFOLD line
        scaffold_line_idx = None
        for idx, line in enumerate(lines):
            if line.startswith("# SCAFFOLD:"):
                scaffold_line_idx = idx
                break

        assert scaffold_line_idx is not None, "SCAFFOLD header missing"

        # Module docstring should be next (after SCAFFOLD)
        docstring_start_idx = scaffold_line_idx + 1
        assert lines[docstring_start_idx].strip().startswith('"""'), \
            "Module docstring must follow SCAFFOLD header"

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
        assert "@layer:" in docstring_text, \
            "Module docstring must contain @layer annotation"
        assert "Backend (DTOs)" in docstring_text, \
            "Module docstring must contain layer value"

        # REQUIREMENT: Must contain @dependencies
        assert "@dependencies:" in docstring_text, \
            "Module docstring must contain @dependencies annotation"

        # REQUIREMENT: Must contain @responsibilities
        assert "@responsibilities:" in docstring_text, \
            "Module docstring must contain @responsibilities annotation"

    def test_scaffolded_worker_has_import_section_headers(self):
        """Scaffolded worker must have import section headers.
        
        RED: This test WILL FAIL until tier1_base_code adds section headers.
        """
        from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
        from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
        from mcp_server.scaffolding.renderer import JinjaRenderer
        from mcp_server.config.template_config import get_template_root

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
            responsibilities=["Process background tasks"]
        )

        content = result.content
        lines = content.split("\n")

        # REQUIREMENT: Must have "# Standard library" header
        assert any("# Standard library" in line for line in lines), \
            "Import section must have '# Standard library' header"

        # REQUIREMENT: Must have "# Third-party" header
        assert any("# Third-party" in line for line in lines), \
            "Import section must have '# Third-party' header"

        # REQUIREMENT: Must have "# Project modules" header
        assert any("# Project modules" in line for line in lines), \
            "Import section must have '# Project modules' header"

    def test_scaffolded_generic_has_complete_coding_standards(self):
        """Scaffolded generic class must have both module docstring AND import headers.
        
        RED: This test WILL FAIL until both features are implemented.
        """
        from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
        from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
        from mcp_server.scaffolding.renderer import JinjaRenderer
        from mcp_server.config.template_config import get_template_root

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
                "project": ["from backend.core import Something"]
            }
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


class TestConcreteTemplateStructure:
    """Test that concrete templates have required Jinja2 structure (Task 1.6 RED)."""

    @pytest.mark.parametrize("template_name", [
        "dto.py.jinja2",
        "worker.py.jinja2",
        "service_command.py.jinja2",
        "generic.py.jinja2"
    ])
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
        assert "TEMPLATE_METADATA" in content, \
            f"{template_name} missing TEMPLATE_METADATA"

        # REQUIREMENT: Must extend tier chain (inheritance)
        assert "extends" in content or "{% extends" in content, \
            f"{template_name} must extend base template for inheritance"

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
