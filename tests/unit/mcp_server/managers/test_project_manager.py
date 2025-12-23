"""Tests for ProjectManager with Phase 0.5 ProjectPhaseSelector.

Phase 0.5: Project Type Selection & Phase Planning
- Human selects issue_type during project initialization
- 5 templates: feature (7), bug (6), docs (4), refactor (5), hotfix (3)
- Project plan stored in .st3/projects.json
"""
import json

import pytest

from mcp_server.managers.project_manager import ProjectManager, PHASE_TEMPLATES


class TestProjectPhaseSelector:
    """Test Phase 0.5: ProjectPhaseSelector with issue_type templates."""
    
    @pytest.fixture
    def workspace_root(self, tmp_path):
        """Create temporary workspace."""
        return tmp_path
    
    @pytest.fixture
    def manager(self, workspace_root):
        """Create ProjectManager instance."""
        return ProjectManager(workspace_root=workspace_root)
    
    def test_phase_templates_exist(self):
        """Test that PHASE_TEMPLATES contains all 5 issue types."""
        assert "feature" in PHASE_TEMPLATES
        assert "bug" in PHASE_TEMPLATES
        assert "docs" in PHASE_TEMPLATES
        assert "refactor" in PHASE_TEMPLATES
        assert "hotfix" in PHASE_TEMPLATES
    
    def test_feature_template_has_7_phases(self):
        """Test feature template has all 7 phases."""
        template = PHASE_TEMPLATES["feature"]
        assert len(template["required_phases"]) == 7
        expected = ("discovery", "planning", "design", "component", "tdd", "integration", "documentation")
        assert template["required_phases"] == expected
    
    def test_bug_template_has_6_phases_skip_design(self):
        """Test bug template skips design phase."""
        template = PHASE_TEMPLATES["bug"]
        assert len(template["required_phases"]) == 6
        assert "design" not in template["required_phases"]
        assert "tdd" in template["required_phases"]
    
    def test_docs_template_has_4_phases_skip_tdd_integration(self):
        """Test docs template skips tdd and integration."""
        template = PHASE_TEMPLATES["docs"]
        assert len(template["required_phases"]) == 4
        assert "tdd" not in template["required_phases"]
        assert "integration" not in template["required_phases"]
        assert "documentation" in template["required_phases"]
    
    def test_refactor_template_has_5_phases_skip_design_component(self):
        """Test refactor template skips design and component."""
        template = PHASE_TEMPLATES["refactor"]
        assert len(template["required_phases"]) == 5
        assert "design" not in template["required_phases"]
        assert "component" not in template["required_phases"]
        assert "tdd" in template["required_phases"]
    
    def test_hotfix_template_has_3_phases_minimal(self):
        """Test hotfix template has minimal 3 phases."""
        template = PHASE_TEMPLATES["hotfix"]
        assert len(template["required_phases"]) == 3
        expected = ("component", "tdd", "integration")
        assert template["required_phases"] == expected
    
    def test_initialize_project_with_feature_type(self, manager, workspace_root):
        """Test initialize_project creates feature project plan."""
        result = manager.initialize_project(
            issue_number=42,
            issue_title="Add user authentication",
            issue_type="feature"
        )
        
        assert result["success"] is True
        assert result["issue_type"] == "feature"
        assert len(result["required_phases"]) == 7
        
        # Check project metadata file created
        projects_file = workspace_root / ".st3" / "projects.json"
        assert projects_file.exists()
        
        projects = json.loads(projects_file.read_text())
        assert "42" in projects
        assert projects["42"]["issue_type"] == "feature"
    
    def test_initialize_project_with_bug_type(self, manager, workspace_root):
        """Test initialize_project creates bug project plan (skip design)."""
        result = manager.initialize_project(
            issue_number=99,
            issue_title="Fix login validation",
            issue_type="bug"
        )
        
        assert result["success"] is True
        assert result["issue_type"] == "bug"
        assert len(result["required_phases"]) == 6
        assert "design" not in result["required_phases"]
    
    def test_initialize_project_with_docs_type(self, manager, workspace_root):
        """Test initialize_project creates docs project plan."""
        result = manager.initialize_project(
            issue_number=77,
            issue_title="Update API documentation",
            issue_type="docs"
        )
        
        assert result["success"] is True
        assert result["issue_type"] == "docs"
        assert len(result["required_phases"]) == 4
        assert "tdd" not in result["required_phases"]
        assert "integration" not in result["required_phases"]
    
    def test_initialize_project_with_custom_phases(self, manager, workspace_root):
        """Test initialize_project with custom phase list."""
        custom_phases = ("planning", "component", "documentation")
        result = manager.initialize_project(
            issue_number=123,
            issue_title="Custom workflow",
            issue_type="custom",
            custom_phases=custom_phases,
            skip_reason="Special case: POC without tests"
        )
        
        assert result["success"] is True
        assert result["issue_type"] == "custom"
        assert result["required_phases"] == custom_phases
        assert result["skip_reason"] == "Special case: POC without tests"
    
    def test_initialize_project_invalid_issue_type(self, manager):
        """Test initialize_project rejects invalid issue_type."""
        with pytest.raises(ValueError, match="Invalid issue_type"):
            manager.initialize_project(
                issue_number=999,
                issue_title="Invalid",
                issue_type="invalid_type"
            )
    
    def test_initialize_project_custom_without_phases(self, manager):
        """Test initialize_project requires custom_phases when issue_type=custom."""
        with pytest.raises(ValueError, match="custom_phases required"):
            manager.initialize_project(
                issue_number=888,
                issue_title="Custom without phases",
                issue_type="custom"
            )
    
    def test_get_project_plan_returns_stored_plan(self, manager, workspace_root):
        """Test get_project_plan retrieves stored project plan."""
        # Initialize project
        manager.initialize_project(
            issue_number=42,
            issue_title="Test",
            issue_type="feature"
        )
        
        # Retrieve plan
        plan = manager.get_project_plan(issue_number=42)
        assert plan is not None
        assert plan["issue_type"] == "feature"
        assert len(plan["required_phases"]) == 7
    
    def test_get_project_plan_nonexistent_returns_none(self, manager):
        """Test get_project_plan returns None for nonexistent project."""
        plan = manager.get_project_plan(issue_number=999)
        assert plan is None
