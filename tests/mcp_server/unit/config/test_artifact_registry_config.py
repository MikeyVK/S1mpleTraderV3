"""Unit tests for ArtifactRegistryConfig (Issue #56, Cycle 1).

Tests configuration loading from artifacts.yaml with:
- Singleton pattern
- Field validation
- Error handling (missing file, invalid YAML)
- LLM-friendly error messages

Author: AI Agent
Created: 2024
"""

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import yaml

from mcp_server.config.artifact_registry_config import (
    ArtifactDefinition,
    ArtifactRegistryConfig,
    ArtifactType,
    StateMachine,
)
from mcp_server.core.exceptions import ConfigError


@pytest.fixture
def minimal_yaml() -> dict[str, Any]:
    """Minimal valid artifacts.yaml structure."""
    return {
        "version": "1.0",
        "artifact_types": [
            {
                "type": "code",
                "type_id": "dto",
                "name": "Data Transfer Object",
                "description": "Test DTO",
                "file_extension": ".py",
                "required_fields": ["name"],
                "optional_fields": [],
                "state_machine": {
                    "states": ["CREATED"],
                    "initial_state": "CREATED",
                    "valid_transitions": [],
                },
            }
        ],
    }


@pytest.fixture
def temp_yaml_file(minimal_yaml: dict[str, Any], tmp_path: Path) -> Path:
    """Create temporary artifacts.yaml file."""
    file_path = tmp_path / "artifacts.yaml"
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(minimal_yaml, f)
    return file_path


@pytest.fixture(autouse=True)
def reset_singleton() -> Generator[None, None, None]:
    """Reset singleton before each test."""
    ArtifactRegistryConfig.reset_instance()
    yield
    ArtifactRegistryConfig.reset_instance()


class TestArtifactRegistryConfigLoading:
    """Test configuration loading and singleton pattern."""

    def test_loads_from_file(self, temp_yaml_file: Path) -> None:
        """Config loads from artifacts.yaml."""
        config = ArtifactRegistryConfig.from_file(temp_yaml_file)

        assert config.version == "1.0"
        assert len(config.artifact_types) == 1
        assert config.artifact_types[0].type_id == "dto"

    def test_singleton_pattern(self, temp_yaml_file: Path) -> None:
        """Subsequent calls return cached instance."""
        config1 = ArtifactRegistryConfig.from_file(temp_yaml_file)
        config2 = ArtifactRegistryConfig.from_file(temp_yaml_file)

        assert config1 is config2

    def test_reset_instance_clears_singleton(self, temp_yaml_file: Path) -> None:
        """reset_instance() clears cached instance."""
        config1 = ArtifactRegistryConfig.from_file(temp_yaml_file)
        ArtifactRegistryConfig.reset_instance()
        config2 = ArtifactRegistryConfig.from_file(temp_yaml_file)

        assert config1 is not config2

    def test_missing_file_raises_config_error(
        self,
    ) -> None:
        """ConfigError raised when file not found."""
        with pytest.raises(ConfigError) as exc_info:
            ArtifactRegistryConfig.from_file(Path("nonexistent.yaml"))

        assert "not found" in str(exc_info.value)
        assert "Fix:" in str(exc_info.value)

    def test_empty_file_raises_config_error(self, tmp_path: Path) -> None:
        """ConfigError raised on empty YAML."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        with pytest.raises(ConfigError) as exc_info:
            ArtifactRegistryConfig.from_file(empty_file)

        assert "Empty" in str(exc_info.value)

    def test_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """ConfigError raised on invalid YAML syntax."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: syntax: error:")

        with pytest.raises(ConfigError) as exc_info:
            ArtifactRegistryConfig.from_file(invalid_file)

        assert "Invalid YAML" in str(exc_info.value)
        assert "Fix:" in str(exc_info.value)


class TestArtifactDefinitionValidation:
    """Test artifact definition field validation."""

    def test_validates_required_fields(self, tmp_path: Path) -> None:
        """Missing required field raises validation error."""
        invalid_data = {
            "version": "1.0",
            "artifact_types": [
                {
                    "type": "code",
                    # Missing type_id, name, description, file_extension
                    "state_machine": {
                        "states": ["CREATED"],
                        "initial_state": "CREATED",
                    },
                }
            ],
        }

        invalid_file = tmp_path / "invalid.yaml"
        with open(invalid_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(invalid_data, f)

        with pytest.raises(Exception):  # Pydantic validation error
            ArtifactRegistryConfig.from_file(invalid_file)

    def test_type_id_must_be_lowercase(self) -> None:
        """type_id must be lowercase with underscores."""
        with pytest.raises(ValueError) as exc_info:
            ArtifactDefinition(
                type=ArtifactType.CODE,
                type_id="InvalidID",
                name="Test",
                description="Test",
                file_extension=".py",
                scaffolder_class=None,
                scaffolder_module=None,
                template_path=None,
                fallback_template=None,
                name_suffix=None,
                generate_test=False,
                state_machine=StateMachine(states=["CREATED"], initial_state="CREATED"),
            )

        assert "lowercase" in str(exc_info.value)
        assert "Fix:" in str(exc_info.value)

    def test_initial_state_must_be_in_states(
        self,
    ) -> None:
        """initial_state must exist in states list."""
        with pytest.raises(ValueError) as exc_info:
            StateMachine(
                states=["CREATED", "APPROVED"],
                initial_state="INVALID",
                valid_transitions=[],
            )

        assert "not in states list" in str(exc_info.value)
        assert "Fix:" in str(exc_info.value)


class TestArtifactRegistryConfigMethods:
    """Test configuration access methods."""

    def test_get_artifact_by_type_id(self, temp_yaml_file: Path) -> None:
        """get_artifact() returns definition by type_id."""
        config = ArtifactRegistryConfig.from_file(temp_yaml_file)
        artifact = config.get_artifact("dto")

        assert artifact.type_id == "dto"
        assert artifact.name == "Data Transfer Object"

    def test_get_artifact_not_found(self, temp_yaml_file: Path) -> None:
        """get_artifact() raises ConfigError for unknown type_id."""
        config = ArtifactRegistryConfig.from_file(temp_yaml_file)

        with pytest.raises(ConfigError) as exc_info:
            config.get_artifact("unknown")

        assert "not found" in str(exc_info.value)
        assert "Available types:" in str(exc_info.value)
        assert "Fix:" in str(exc_info.value)

    def test_list_type_ids_all(self, temp_yaml_file: Path) -> None:
        """list_type_ids() returns all type_ids."""
        config = ArtifactRegistryConfig.from_file(temp_yaml_file)
        type_ids = config.list_type_ids()

        assert type_ids == ["dto"]

    def test_list_type_ids_filtered(self, tmp_path: Path) -> None:
        """list_type_ids() filters by ArtifactType."""
        mixed_data = {
            "version": "1.0",
            "artifact_types": [
                {
                    "type": "code",
                    "type_id": "dto",
                    "name": "DTO",
                    "description": "Test",
                    "file_extension": ".py",
                    "state_machine": {
                        "states": ["CREATED"],
                        "initial_state": "CREATED",
                    },
                },
                {
                    "type": "doc",
                    "type_id": "research",
                    "name": "Research",
                    "description": "Test",
                    "file_extension": ".md",
                    "state_machine": {
                        "states": ["DRAFT"],
                        "initial_state": "DRAFT",
                    },
                },
            ],
        }

        mixed_file = tmp_path / "mixed.yaml"
        with open(mixed_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(mixed_data, f)

        config = ArtifactRegistryConfig.from_file(mixed_file)

        code_types = config.list_type_ids(ArtifactType.CODE)
        doc_types = config.list_type_ids(ArtifactType.DOC)

        assert code_types == ["dto"]
        assert doc_types == ["research"]


class TestArtifactDefinitionFields:
    """Test ArtifactDefinition field parsing (Cycle 2)."""

    def test_parses_all_required_fields(self, tmp_path: Path) -> None:
        """Parses artifact with all required fields."""
        data = {
            "version": "1.0",
            "artifact_types": [
                {
                    "type": "code",
                    "type_id": "dto",
                    "name": "Data Transfer Object",
                    "description": "DTO for data transfer",
                    "file_extension": ".py",
                    "state_machine": {
                        "states": ["CREATED"],
                        "initial_state": "CREATED",
                    },
                }
            ],
        }

        file_path = tmp_path / "required.yaml"
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        config = ArtifactRegistryConfig.from_file(file_path)
        artifact = config.get_artifact("dto")

        assert artifact.type == ArtifactType.CODE
        assert artifact.type_id == "dto"
        assert artifact.name == "Data Transfer Object"
        assert artifact.description == "DTO for data transfer"
        assert artifact.file_extension == ".py"
        assert artifact.state_machine.states == ["CREATED"]

    def test_optional_fields_work(self, tmp_path: Path) -> None:
        """Optional fields (LEGACY, template, suffix) parse correctly."""
        data = {
            "version": "1.0",
            "artifact_types": [
                {
                    "type": "code",
                    "type_id": "worker",
                    "name": "Worker",
                    "description": "Test worker",
                    "file_extension": ".py",
                    # Optional LEGACY fields
                    "scaffolder_class": "WorkerScaffolder",
                    "scaffolder_module": "mcp_server.scaffolders.worker",
                    # Optional template fields
                    "template_path": "templates/worker.py.jinja2",
                    "fallback_template": "templates/generic.py.jinja2",
                    "name_suffix": "Worker",
                    "generate_test": True,
                    # Optional scaffolding fields
                    "required_fields": ["name", "input_dto"],
                    "optional_fields": ["dependencies"],
                    "state_machine": {
                        "states": ["CREATED"],
                        "initial_state": "CREATED",
                    },
                }
            ],
        }

        file_path = tmp_path / "optional.yaml"
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        config = ArtifactRegistryConfig.from_file(file_path)
        artifact = config.get_artifact("worker")

        # LEGACY fields
        assert artifact.scaffolder_class == "WorkerScaffolder"
        assert artifact.scaffolder_module == "mcp_server.scaffolders.worker"
        # Template fields
        assert artifact.template_path == "templates/worker.py.jinja2"
        assert artifact.fallback_template == "templates/generic.py.jinja2"
        assert artifact.name_suffix == "Worker"
        assert artifact.generate_test is True
        # Scaffolding fields
        assert artifact.required_fields == ["name", "input_dto"]
        assert artifact.optional_fields == ["dependencies"]

    def test_optional_fields_default_to_none_or_empty(self, tmp_path: Path) -> None:
        """Optional fields have sensible defaults when omitted."""
        data = {
            "version": "1.0",
            "artifact_types": [
                {
                    "type": "doc",
                    "type_id": "reference",
                    "name": "Reference",
                    "description": "Test doc",
                    "file_extension": ".md",
                    "state_machine": {
                        "states": ["DRAFT"],
                        "initial_state": "DRAFT",
                    },
                }
            ],
        }

        file_path = tmp_path / "defaults.yaml"
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        config = ArtifactRegistryConfig.from_file(file_path)
        artifact = config.get_artifact("reference")

        assert artifact.scaffolder_class is None
        assert artifact.scaffolder_module is None
        assert artifact.template_path is None
        assert artifact.fallback_template is None
        assert artifact.name_suffix is None
        assert artifact.generate_test is False
        assert artifact.required_fields == []
        assert artifact.optional_fields == []


class TestStateMachineDefinition:
    """Test state machine structure (Epic #18 will use)."""

    def test_state_machine_parsed(self, temp_yaml_file: Path) -> None:
        """State machine definitions parsed correctly."""
        config = ArtifactRegistryConfig.from_file(temp_yaml_file)
        artifact = config.get_artifact("dto")

        assert artifact.state_machine.states == ["CREATED"]
        assert artifact.state_machine.initial_state == "CREATED"
        assert artifact.state_machine.valid_transitions == []

    def test_state_transitions_parsed(self, tmp_path: Path) -> None:
        """State transitions with from/to parsed correctly."""
        data = {
            "version": "1.0",
            "artifact_types": [
                {
                    "type": "doc",
                    "type_id": "research",
                    "name": "Research",
                    "description": "Test",
                    "file_extension": ".md",
                    "state_machine": {
                        "states": ["DRAFT", "APPROVED"],
                        "initial_state": "DRAFT",
                        "valid_transitions": [{"from": "DRAFT", "to": ["APPROVED"]}],
                    },
                }
            ],
        }

        file_path = tmp_path / "transitions.yaml"
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        config = ArtifactRegistryConfig.from_file(file_path)
        artifact = config.get_artifact("research")

        assert len(artifact.state_machine.valid_transitions) == 1
        transition = artifact.state_machine.valid_transitions[0]
        assert transition.from_state == "DRAFT"
        assert transition.to_states == ["APPROVED"]
