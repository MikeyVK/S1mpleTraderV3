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
import yaml

# Project
from mcp_server.adapters.filesystem import FilesystemAdapter
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer
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

    # Set TEMPLATE_ROOT to actual project templates (not relative to temp CWD)
    project_root = Path(__file__).parent.parent.parent
    template_root = project_root / "mcp_server" / "scaffolding" / "templates"
    monkeypatch.setenv("TEMPLATE_ROOT", str(template_root))

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
        '    model_config = {"frozen": True, "extra": "forbid"}\n\n'
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


# Helper functions for dynamic artifact/template creation

def add_artifact_to_yaml(
    artifacts_yaml_path: Path,
    type_id: str,
    artifact_type: str,
    name: str,
    template_path: str,
    file_extension: str,
    description: str | None = None,
    required_fields: list[str] | None = None,
    optional_fields: list[str] | None = None,
    generate_test: bool = False
) -> None:
    """
    Add artifact type to existing artifacts.yaml.

    Args:
        artifacts_yaml_path: Path to artifacts.yaml
        type_id: Artifact type ID (e.g., 'dto_invalid')
        artifact_type: Type category ('code' or 'doc')
        name: Display name
        template_path: Relative template path
        file_extension: File extension (e.g., '.py', '.md')
        description: Artifact description
        required_fields: Required template fields
        optional_fields: Optional template fields
        generate_test: Whether to generate test file
    """
    # Load existing YAML
    with open(artifacts_yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Create new artifact definition
    artifact_def = {
        "type": artifact_type,
        "type_id": type_id,
        "name": name,
        "description": description or f"{name} artifact",
        "template_path": template_path,
        "fallback_template": None,
        "name_suffix": None,
        "file_extension": file_extension,
        "generate_test": generate_test,
        "required_fields": required_fields or ["name"],
        "optional_fields": optional_fields or [],
        "state_machine": {
            "states": ["CREATED"],
            "initial_state": "CREATED",
            "valid_transitions": []
        }
    }

    # Append to artifact_types
    data["artifact_types"].append(artifact_def)

    # Write back
    with open(artifacts_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def create_template(
    workspace_root: Path,
    template_relpath: str,
    template_content: str
) -> Path:
    """
    Create template file in workspace.

    Args:
        workspace_root: Workspace root path
        template_relpath: Relative path (e.g., 'components/dto.py.jinja2')
        template_content: Template content (Jinja2)

    Returns:
        Absolute path to created template
    """
    template_path = workspace_root / template_relpath
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(template_content, encoding="utf-8")
    return template_path
