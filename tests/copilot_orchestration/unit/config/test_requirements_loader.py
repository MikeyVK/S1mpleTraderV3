# tests\copilot_orchestration\unit\config\test_requirements_loader.py
# template=unit_test version=3d15d309 created=2026-03-21T12:32Z updated=
"""
Unit tests for copilot_orchestration.config.requirements_loader.

Tests SubRoleRequirementsLoader: YAML+Pydantic parsing, fallback chain,
Fail-Fast on unknown sub-role and malformed YAML.

@layer: Tests (Unit)
@dependencies: [pytest, copilot_orchestration.config.requirements_loader]
@responsibilities:
    - Test TestSubRoleRequirementsLoader functionality
    - Verify YAML parsing, fallback chain, frozenset contents, marker retrieval, error cases
    - Cover fallback chain from project config to package default
"""

# Standard library
import logging
from pathlib import Path

# Third-party
import pytest
from pydantic import ValidationError

# Project modules
from copilot_orchestration.config.requirements_loader import (
    ConfigError,
    SubRoleRequirementsLoader,
)

_MINIMAL_YAML = """\
roles:
  imp:
    default_sub_role: implementer
    sub_roles:
      implementer:
        requires_crosschat_block: true
        heading: "H"
        block_template: "```text\nimplementer\n{markers_list}\n```"
        markers: []
        description: ""
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: true
        heading: "H"
        block_template: "```text\nverifier\n{markers_list}\n```"
        markers: []
        description: ""
"""


class TestSubRoleRequirementsLoader:
    """Test suite for requirements_loader."""

    def test_loads_valid_yaml(self, tmp_path: Path) -> None:
        """Constructs loader from a valid YAML file without error."""
        # Arrange
        yaml_content = """\
roles:
  imp:
    default_sub_role: implementer
    sub_roles:
      researcher:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: ["Problem Statement", "Findings", "Open Questions"]
        description: ""
      implementer:
        requires_crosschat_block: true
        heading: "Implementation Hand-Over"
        block_template: |-
          ```text
          verifier
          {markers_list}
          ```
        markers: ["Scope", "Files Changed", "Proof", "Ready-for-QA"]
        description: "Implement the current cycle."
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: true
        heading: "Verification Review"
        block_template: |-
          ```text
          implementer
          {markers_list}
          ```
        markers: ["Findings", "Proof Verification", "Verdict"]
        description: ""
"""
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(yaml_content)

        # Act
        loader = SubRoleRequirementsLoader(yaml_path)

        # Assert
        assert loader is not None

    def test_valid_sub_roles_imp_returns_six(self, tmp_path: Path) -> None:
        """valid_sub_roles('imp') returns frozenset of all 6 imp sub-roles."""
        # Arrange
        yaml_content = """\
roles:
  imp:
    default_sub_role: implementer
    sub_roles:
      researcher:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
      planner:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
      designer:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
      implementer:
        requires_crosschat_block: true
        heading: "H"
        block_template: "```text\nverifier\n{markers_list}\n```"
        markers: ["Scope"]
        description: ""
      validator:
        requires_crosschat_block: true
        heading: "H"
        block_template: "```text\nverifier\n{markers_list}\n```"
        markers: ["Results"]
        description: ""
      documenter:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: true
        heading: "H"
        block_template: "```text\nimplementer\n{markers_list}\n```"
        markers: ["Findings"]
        description: ""
"""
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(yaml_content)

        # Act
        result = SubRoleRequirementsLoader(yaml_path).valid_sub_roles("imp")

        # Assert
        assert result == frozenset(
            {"researcher", "planner", "designer", "implementer", "validator", "documenter"}
        )

    def test_valid_sub_roles_qa_returns_five(self, tmp_path: Path) -> None:
        """valid_sub_roles('qa') returns frozenset of all 5 qa sub-roles."""
        # Arrange
        yaml_content = """\
roles:
  imp:
    default_sub_role: implementer
    sub_roles:
      implementer:
        requires_crosschat_block: true
        heading: "H"
        block_template: "```text\nverifier\n{markers_list}\n```"
        markers: ["Scope"]
        description: ""
  qa:
    default_sub_role: verifier
    sub_roles:
      plan-reviewer:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
      design-reviewer:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
      verifier:
        requires_crosschat_block: true
        heading: "H"
        block_template: "```text\nimplementer\n{markers_list}\n```"
        markers: ["Findings"]
        description: ""
      validation-reviewer:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
      doc-reviewer:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
"""
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(yaml_content)

        # Act
        result = SubRoleRequirementsLoader(yaml_path).valid_sub_roles("qa")

        # Assert
        assert result == frozenset(
            {"plan-reviewer", "design-reviewer", "verifier", "validation-reviewer", "doc-reviewer"}
        )

    def test_get_requirement_returns_correct_spec(self, tmp_path: Path) -> None:
        """get_requirement returns correct spec for imp/implementer with markers."""
        # Arrange
        yaml_content = """\
roles:
  imp:
    default_sub_role: implementer
    sub_roles:
      implementer:
        requires_crosschat_block: true
        heading: "Implementation Hand-Over"
        block_template: |-
          ```text
          verifier
          {markers_list}
          ```
        markers: ["Scope", "Files Changed", "Proof", "Ready-for-QA"]
        description: "Implement the current cycle."
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: true
        heading: "V"
        block_template: "```text\nimplementer\n{markers_list}\n```"
        markers: []
        description: ""
"""
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(yaml_content)

        # Act
        result = SubRoleRequirementsLoader(yaml_path).get_requirement("imp", "implementer")

        # Assert
        assert result["requires_crosschat_block"] is True
        assert result["heading"] == "Implementation Hand-Over"
        assert "Scope" in result["markers"]
        assert result["description"] == "Implement the current cycle."

    def test_raises_validation_error_when_description_missing(self, tmp_path: Path) -> None:
        """YAML without description must fail validation in C_DESC.1."""
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(_MINIMAL_YAML.replace('        description: ""\n', '', 2))

        with pytest.raises(ValidationError):
            SubRoleRequirementsLoader(yaml_path)

    def test_raises_on_malformed_yaml(self, tmp_path: Path) -> None:
        """Raises ValidationError when YAML structure does not match expected schema."""
        # Arrange — valid YAML but wrong schema (missing required fields)
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text("roles:\n  not_valid_key: {}")

        # Act + Assert
        with pytest.raises(ValidationError):
            SubRoleRequirementsLoader(yaml_path)

    def test_raises_file_not_found_when_yaml_missing(self, tmp_path: Path) -> None:
        """Raises FileNotFoundError when the YAML file does not exist."""
        # Arrange
        yaml_path = tmp_path / "does_not_exist.yaml"

        # Act + Assert
        with pytest.raises(FileNotFoundError):
            SubRoleRequirementsLoader(yaml_path)

    def test_raises_config_error_for_unknown_sub_role(self, tmp_path: Path) -> None:
        """Raises ConfigError for unknown (role, sub_role) pair."""
        # Arrange
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(_MINIMAL_YAML)
        loader = SubRoleRequirementsLoader(yaml_path)

        # Act + Assert
        with pytest.raises(ConfigError):
            loader.get_requirement("imp", "unknown-sub-role")

    def test_valid_sub_roles_raises_config_error_for_unknown_role(self, tmp_path: Path) -> None:
        """valid_sub_roles raises ConfigError for an unknown role (not KeyError)."""
        # Arrange
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(_MINIMAL_YAML)
        loader = SubRoleRequirementsLoader(yaml_path)

        # Act + Assert
        with pytest.raises(ConfigError, match="Unknown role"):
            loader.valid_sub_roles("nonexistent-role")

    def test_default_sub_role_raises_config_error_for_unknown_role(self, tmp_path: Path) -> None:
        """default_sub_role raises ConfigError for an unknown role (not KeyError)."""
        # Arrange
        yaml_path = tmp_path / "requirements.yaml"
        yaml_path.write_text(_MINIMAL_YAML)
        loader = SubRoleRequirementsLoader(yaml_path)

        # Act + Assert
        with pytest.raises(ConfigError, match="Unknown role"):
            loader.default_sub_role("nonexistent-role")

    def test_from_copilot_dir_loads_project_yaml(self, tmp_path: Path) -> None:
        """from_copilot_dir loads project YAML when .copilot/sub-role-requirements.yaml exists."""
        # Arrange
        copilot_dir = tmp_path / ".copilot"
        copilot_dir.mkdir()
        project_yaml = copilot_dir / "sub-role-requirements.yaml"
        project_yaml.write_text("""\
roles:
  imp:
    default_sub_role: researcher
    sub_roles:
      researcher:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: true
        heading: "H"
        block_template: "```text\nresearcher\n{markers_list}\n```"
        markers: []
        description: ""
""")

        # Act
        loader = SubRoleRequirementsLoader.from_copilot_dir(tmp_path)

        # Assert
        assert loader.default_sub_role("imp") == "researcher"

    def test_model_validator_raises_for_empty_block_template_when_crosschat_true(
        self, tmp_path: Path
    ) -> None:
        """ValidationError when requires_crosschat_block=True and block_template is empty.

        C_CROSSCHAT.2 RED: @model_validator not yet present in _SubRoleSchema.
        """
        yaml_content = """\
roles:
  imp:
    default_sub_role: implementer
    sub_roles:
      implementer:
        requires_crosschat_block: true
        heading: "H"
        block_template: ""
        markers: []
        description: ""
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
"""
        yaml_path = tmp_path / "r.yaml"
        yaml_path.write_text(yaml_content)
        with pytest.raises(ValidationError):
            SubRoleRequirementsLoader(yaml_path)

    def test_block_prefix_hint_absent_from_schema(self) -> None:
        """_SubRoleSchema no longer declares block_prefix_hint in model_fields.

        C_CROSSCHAT.2 RED: field still exists until _SubRoleSchema is updated.
        """
        from copilot_orchestration.config.requirements_loader import (  # noqa: PLC0415
            _SubRoleSchema,
        )

        assert "block_prefix_hint" not in _SubRoleSchema.model_fields

    def test_model_validator_passes_when_crosschat_false_and_template_empty(
        self, tmp_path: Path
    ) -> None:
        """No ValidationError when requires_crosschat_block=False and block_template is empty."""
        yaml_content = """\
roles:
  imp:
    default_sub_role: researcher
    sub_roles:
      researcher:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
"""
        yaml_path = tmp_path / "r.yaml"
        yaml_path.write_text(yaml_content)
        loader = SubRoleRequirementsLoader(yaml_path)
        assert loader is not None


_REQUIREMENTS_LOGGER_NAME = "copilot_orchestration.config.requirements_loader"


class TestSubRoleRequirementsLoaderLogging:
    """Logging behaviour of SubRoleRequirementsLoader."""

    def test_successful_load_emits_debug_log(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """SubRoleRequirementsLoader.__init__ logs at DEBUG when config is loaded."""
        yaml_path = tmp_path / "r.yaml"
        yaml_path.write_text(_MINIMAL_YAML)
        with caplog.at_level(logging.DEBUG, logger=_REQUIREMENTS_LOGGER_NAME):
            SubRoleRequirementsLoader(yaml_path)
        assert any(r.levelno == logging.DEBUG for r in caplog.records)

    def test_warning_logged_when_fence_first_word_not_valid_sub_role(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Loader logs WARNING when block_template fence first word is unknown sub-role.

        C_CROSSCHAT.2 RED: WARNING-log logic not yet present in loader.
        """
        yaml_content = """\
roles:
  imp:
    default_sub_role: implementer
    sub_roles:
      implementer:
        requires_crosschat_block: true
        heading: "H"
        block_template: |-
          ```text
          unknown_role
          {markers_list}
          ```
        markers: ["Scope"]
        description: ""
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: false
        heading: ""
        block_template: ""
        markers: []
        description: ""
"""
        yaml_path = tmp_path / "r.yaml"
        yaml_path.write_text(yaml_content)
        with caplog.at_level(logging.WARNING, logger=_REQUIREMENTS_LOGGER_NAME):
            SubRoleRequirementsLoader(yaml_path)
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_no_warning_when_fence_first_word_is_valid_sub_role(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Loader logs no WARNING when block_template fence first word is a known sub-role."""
        yaml_content = """\
roles:
  imp:
    default_sub_role: implementer
    sub_roles:
      implementer:
        requires_crosschat_block: true
        heading: "H"
        block_template: |-
          ```text
          verifier
          {markers_list}
          ```
        markers: ["Scope"]
        description: ""
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: true
        heading: "H"
        block_template: |-
          ```text
          implementer
          {markers_list}
          ```
        markers: ["Findings"]
        description: ""
"""
        yaml_path = tmp_path / "r.yaml"
        yaml_path.write_text(yaml_content)
        with caplog.at_level(logging.WARNING, logger=_REQUIREMENTS_LOGGER_NAME):
            SubRoleRequirementsLoader(yaml_path)
        assert not any(r.levelno == logging.WARNING for r in caplog.records)
