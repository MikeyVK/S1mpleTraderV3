# tests\copilot_orchestration\unit\config\test_requirements_loader.py
# template=unit_test version=3d15d309 created=2026-03-21T12:32Z updated=
"""
Unit tests for copilot_orchestration.config.requirements_loader.

Tests SubRoleRequirementsLoader: YAML+Pydantic parsing, fallback chain, Fail-Fast on unknown sub-role and malformed YAML.

@layer: Tests (Unit)
@dependencies: [pytest, copilot_orchestration.config.requirements_loader]
@responsibilities:
    - Test TestSubRoleRequirementsLoader functionality
    - Verify YAML parsing, fallback chain, frozenset contents, marker retrieval, error cases
    - Cover fallback chain from project config to package default
"""

# Standard library
from pathlib import Path

# Third-party
import pytest

# Project modules
from copilot_orchestration.config.requirements_loader import SubRoleRequirementsLoader, ConfigError


class TestSubRoleRequirementsLoader:
    """Test suite for requirements_loader."""

    def test_loads_valid_yaml(
        self,
        tmp_path: Path    ):
        """Constructs loader from a valid YAML file without error."""
        # Arrange - Setup test data and preconditions
        yaml_content = '''
        roles:
          imp:
            default_sub_role: implementer
            sub_roles:
              researcher:
                requires_crosschat_block: false
                heading: ""
                block_prefix: ""
                guide_line: ""
                markers: ["Problem Statement", "Findings", "Open Questions"]
              implementer:
                requires_crosschat_block: true
                heading: "Implementation Hand-Over"
                block_prefix: "@qa verifier"
                guide_line: "Review the latest implementation work."
                markers: ["Scope", "Files Changed", "Proof", "Ready-for-QA"]
          qa:
            default_sub_role: verifier
            sub_roles:
              verifier:
                requires_crosschat_block: true
                heading: "Verification Review"
                block_prefix: "@imp implementer"
                guide_line: "QA findings must be resolved."
                markers: ["Findings", "Proof Verification", "Verdict"]
        '''
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(yaml_content)

        # Act - Execute the functionality being tested
        loader = SubRoleRequirementsLoader(yaml_path)

        # Assert - Verify the expected outcome
        assert loader is not None
    def test_valid_sub_roles_imp_returns_six(
        self,
        tmp_path: Path    ):
        """valid_sub_roles('imp') returns frozenset of all 6 imp sub-roles."""
        # Arrange - Setup test data and preconditions
        yaml_content = '''
        roles:
          imp:
            default_sub_role: implementer
            sub_roles:
              researcher: {requires_crosschat_block: false, heading: "", block_prefix: "", guide_line: "", markers: []}
              planner: {requires_crosschat_block: false, heading: "", block_prefix: "", guide_line: "", markers: []}
              designer: {requires_crosschat_block: false, heading: "", block_prefix: "", guide_line: "", markers: []}
              implementer: {requires_crosschat_block: true, heading: "H", block_prefix: "P", guide_line: "G", markers: ["Scope"]}
              validator: {requires_crosschat_block: true, heading: "H", block_prefix: "P", guide_line: "G", markers: ["Results"]}
              documenter: {requires_crosschat_block: false, heading: "", block_prefix: "", guide_line: "", markers: []}
          qa:
            default_sub_role: verifier
            sub_roles:
              verifier: {requires_crosschat_block: true, heading: "H", block_prefix: "P", guide_line: "G", markers: ["Findings"]}
        '''
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(yaml_content)

        # Act - Execute the functionality being tested
        loader = SubRoleRequirementsLoader(yaml_path)
        result = loader.valid_sub_roles("imp")

        # Assert - Verify the expected outcome
        assert result == frozenset({"researcher", "planner", "designer", "implementer", "validator", "documenter"})
    def test_valid_sub_roles_qa_returns_five(
        self,
        tmp_path: Path    ):
        """valid_sub_roles('qa') returns frozenset of all 5 qa sub-roles."""
        # Arrange - Setup test data and preconditions
        yaml_content = '''
        roles:
          imp:
            default_sub_role: implementer
            sub_roles:
              implementer: {requires_crosschat_block: true, heading: "H", block_prefix: "P", guide_line: "G", markers: ["Scope"]}
          qa:
            default_sub_role: verifier
            sub_roles:
              plan-reviewer: {requires_crosschat_block: false, heading: "", block_prefix: "", guide_line: "", markers: []}
              design-reviewer: {requires_crosschat_block: false, heading: "", block_prefix: "", guide_line: "", markers: []}
              verifier: {requires_crosschat_block: true, heading: "H", block_prefix: "P", guide_line: "G", markers: ["Findings"]}
              validation-reviewer: {requires_crosschat_block: false, heading: "", block_prefix: "", guide_line: "", markers: []}
              doc-reviewer: {requires_crosschat_block: false, heading: "", block_prefix: "", guide_line: "", markers: []}
        '''
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(yaml_content)

        # Act - Execute the functionality being tested
        loader = SubRoleRequirementsLoader(yaml_path)
        result = loader.valid_sub_roles("qa")

        # Assert - Verify the expected outcome
        assert result == frozenset({"plan-reviewer", "design-reviewer", "verifier", "validation-reviewer", "doc-reviewer"})
    def test_get_requirement_returns_correct_spec(
        self,
        tmp_path: Path    ):
        """get_requirement returns correct spec for imp/implementer with markers."""
        # Arrange - Setup test data and preconditions
        yaml_content = '''
        roles:
          imp:
            default_sub_role: implementer
            sub_roles:
              implementer:
                requires_crosschat_block: true
                heading: "Implementation Hand-Over"
                block_prefix: "@qa verifier"
                guide_line: "Review it."
                markers: ["Scope", "Files Changed", "Proof", "Ready-for-QA"]
          qa:
            default_sub_role: verifier
            sub_roles:
              verifier: {requires_crosschat_block: true, heading: "V", block_prefix: "B", guide_line: "G", markers: []}
        '''
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(yaml_content)

        # Act - Execute the functionality being tested
        loader = SubRoleRequirementsLoader(yaml_path)
        result = loader.get_requirement("imp", "implementer")

        # Assert - Verify the expected outcome
        assert result["requires_crosschat_block"] is True
        assert result["heading"] == "Implementation Hand-Over"
        assert "Scope" in result["markers"]
    def test_raises_on_malformed_yaml(
        self,
        tmp_path: Path    ):
        """Raises an exception when YAML structure does not match expected schema."""
        # Arrange
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text("roles: {not_valid_key: {}")

        # Act + Assert — constructor raises on malformed / non-conforming YAML
        with pytest.raises(Exception):
            SubRoleRequirementsLoader(yaml_path)
    def test_raises_file_not_found_when_yaml_missing(
        self,
        tmp_path: Path    ):
        """Raises FileNotFoundError when the YAML file does not exist."""
        # Arrange - Setup test data and preconditions
        yaml_path = tmp_path / "does_not_exist.yaml"

        # Act - Execute the functionality being tested
        # raises is both Act and Assert

        # Assert - Verify the expected outcome
        with pytest.raises(FileNotFoundError):
            SubRoleRequirementsLoader(yaml_path)
    def test_raises_config_error_for_unknown_sub_role(
        self,
        tmp_path: Path    ):
        """Raises ConfigError for unknown (role, sub_role) pair."""
        # Arrange - Setup test data and preconditions
        yaml_content = '''
        roles:
          imp:
            default_sub_role: implementer
            sub_roles:
              implementer: {requires_crosschat_block: true, heading: "H", block_prefix: "P", guide_line: "G", markers: []}
          qa:
            default_sub_role: verifier
            sub_roles:
              verifier: {requires_crosschat_block: true, heading: "H", block_prefix: "P", guide_line: "G", markers: []}
        '''
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(yaml_content)

        # Act - Execute the functionality being tested
        loader = SubRoleRequirementsLoader(yaml_path)

        # Assert - Verify the expected outcome
        with pytest.raises(ConfigError):
            loader.get_requirement("imp", "unknown-sub-role")
    def test_from_copilot_dir_loads_project_yaml(
        self,
        tmp_path: Path    ):
        """from_copilot_dir loads project YAML when .copilot/sub-role-requirements.yaml exists."""
        # Arrange - Setup test data and preconditions
        copilot_dir = tmp_path / ".copilot"
        copilot_dir.mkdir()

        # Act - Execute the functionality being tested
        project_yaml = copilot_dir / "sub-role-requirements.yaml"
        project_yaml.write_text('''
        roles:
          imp:
            default_sub_role: researcher
            sub_roles:
              researcher: {requires_crosschat_block: false, heading: "", block_prefix: "", guide_line: "", markers: []}
          qa:
            default_sub_role: verifier
            sub_roles:
              verifier: {requires_crosschat_block: true, heading: "H", block_prefix: "P", guide_line: "G", markers: []}
        ''')
        loader = SubRoleRequirementsLoader.from_copilot_dir(tmp_path)

        # Assert - Verify the expected outcome
        assert loader.default_sub_role("imp") == "researcher"
