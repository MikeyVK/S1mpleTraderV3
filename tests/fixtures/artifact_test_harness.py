"""
@module: tests.fixtures.artifact_test_harness
@layer: Test Infrastructure
@dependencies: pytest, mcp_server.config, mcp_server.adapters, mcp_server.managers
@responsibilities:
  - Hermetic test fixtures for unified artifact system
  - Temp workspace with real config/templates
  - E2E test helpers
"""

# pylint: disable=redefined-outer-name
# Standard library
from pathlib import Path
from typing import Generator

# Third-party
import pytest

# Project
from mcp_server.adapters.filesystem import FilesystemAdapter
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.validation.validation_service import ValidationService


@pytest.fixture
def temp_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[Path, None, None]:
    """
    Hermetic workspace with temp directory.

    Automatically cleaned up after test.
    Changes CWD to temp workspace for template resolution.
    Uses monkeypatch for safe CWD management in parallel tests.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Change CWD to workspace (template paths are relative)
    monkeypatch.chdir(workspace)

    yield workspace


@pytest.fixture
def artifacts_yaml_content() -> str:
    """Minimal artifacts.yaml for testing."""
    return """version: "1.0"

artifact_types:
  - type: doc
    type_id: design
    name: "Design Document"
    description: "Design document for features"
    template_path: documents/design.md.jinja2
    fallback_template: null
    name_suffix: null
    file_extension: ".md"
    generate_test: false
    required_fields:
      - issue_number
      - title
      - author
    optional_fields:
      - sections
      - status
    state_machine:
      states: [DRAFT, APPROVED, DEFINITIVE]
      initial_state: DRAFT
      valid_transitions:
        - from: DRAFT
          to: [APPROVED, DEFINITIVE]
        - from: APPROVED
          to: [DEFINITIVE]

  - type: code
    type_id: dto
    name: "Data Transfer Object"
    description: "Pydantic DTO"
    template_path: components/dto.py.jinja2
    fallback_template: null
    name_suffix: null
    file_extension: ".py"
    generate_test: true
    required_fields:
      - name
      - description
    optional_fields:
      - fields
      - validation_rules
    state_machine:
      states: [CREATED]
      initial_state: CREATED
      valid_transitions: []
"""


@pytest.fixture
def artifacts_yaml_file(
    temp_workspace: Path,
    artifacts_yaml_content: str,
) -> Path:
    """
    Write artifacts.yaml to temp workspace.

    Returns path to .st3/artifacts.yaml
    """
    st3_dir = temp_workspace / ".st3"
    st3_dir.mkdir()

    artifacts_file = st3_dir / "artifacts.yaml"
    artifacts_file.write_text(artifacts_yaml_content, encoding="utf-8")

    # Create dummy templates for testing
    template_dir = temp_workspace / "documents"
    template_dir.mkdir(parents=True)

    dummy_design_template = template_dir / "design.md.jinja2"
    dummy_design_template.write_text(
        "# {{ title }}\n\nIssue: #{{ issue_number }}\nAuthor: {{ author }}\n",
        encoding="utf-8"
    )

    # Create code template for dto
    code_template_dir = temp_workspace / "components"
    code_template_dir.mkdir(parents=True)

    dummy_dto_template = code_template_dir / "dto.py.jinja2"
    dummy_dto_template.write_text(
        '"""{{ description }}"""\n'
        'from pydantic import BaseModel\n\n'
        'class {{ name }}(BaseModel):\n'
        '    """{{ description }}"""\n'
        '{% for field in fields %}'
        '    {{ field.name }}: {{ field.type }}\n'
        '{% endfor %}',
        encoding="utf-8"
    )

    return artifacts_file


@pytest.fixture
def fs_adapter(temp_workspace: Path) -> FilesystemAdapter:
    """FilesystemAdapter scoped to temp workspace."""
    return FilesystemAdapter(root_path=str(temp_workspace))


@pytest.fixture
def artifact_registry(
    artifacts_yaml_file: Path,
) -> Generator[ArtifactRegistryConfig, None, None]:
    """Load ArtifactRegistryConfig from temp artifacts.yaml."""
    # Reset singleton BEFORE loading
    ArtifactRegistryConfig.reset_instance()

    # Load from test YAML
    registry = ArtifactRegistryConfig.from_file(artifacts_yaml_file)

    yield registry

    # Cleanup: reset singleton after test
    ArtifactRegistryConfig.reset_instance()


@pytest.fixture
def template_scaffolder(
    artifact_registry: ArtifactRegistryConfig,
    temp_workspace: Path,
) -> TemplateScaffolder:
    """
    TemplateScaffolder instance with hermetic template directory.

    Uses temp workspace templates instead of production templates.
    """
    from mcp_server.scaffolding.renderer import JinjaRenderer

    # Point renderer to temp workspace (hermetic)
    renderer = JinjaRenderer(template_dir=temp_workspace)
    return TemplateScaffolder(registry=artifact_registry, renderer=renderer)


@pytest.fixture
def validation_service() -> ValidationService:
    """ValidationService instance."""
    return ValidationService()


@pytest.fixture
def artifact_manager(
    temp_workspace: Path,
    artifact_registry: ArtifactRegistryConfig,
    template_scaffolder: TemplateScaffolder,
    validation_service: ValidationService,
    fs_adapter: FilesystemAdapter,
) -> ArtifactManager:
    """
    Complete ArtifactManager with all dependencies wired.

    Ready for E2E testing.
    """
    return ArtifactManager(
        workspace_root=temp_workspace,
        registry=artifact_registry,
        scaffolder=template_scaffolder,
        validation_service=validation_service,
        fs_adapter=fs_adapter,
    )
