"""
RED tests for Task 1.6: Concrete template existence and basic scaffolding.

Documents requirement that 5 concrete templates must exist and scaffold successfully:
- dto.py.jinja2
- worker.py.jinja2  
- service_command.py.jinja2
- generic.py.jinja2
- design.md.jinja2
"""

from pathlib import Path

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
