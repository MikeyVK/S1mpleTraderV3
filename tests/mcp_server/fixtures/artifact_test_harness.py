"""
@module: tests.fixtures.artifact_test_harness
@layer: Test Infrastructure
@dependencies: pytest, mcp_server.config, mcp_server.adapters, mcp_server.managers
@responsibilities:
  - Hermetic test fixtures for unified artifact system
  - Temp workspace with real config/templates
  - E2E test helpers
"""

# Standard library
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path

# Third-party
import pytest
import yaml

# Project
from mcp_server.adapters.filesystem import FilesystemAdapter
from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import ArtifactRegistryConfig
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.validation.validation_service import ValidationService
from tests.mcp_server.test_support import get_default_server_root


@pytest.fixture(name="temp_workspace")
def _temp_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """
    Hermetic workspace with temp directory.

    Automatically cleaned up after test.
    Changes CWD to temp workspace for template resolution.
    Uses monkeypatch for safe CWD management in parallel tests.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Set TEMPLATE_ROOT to actual project templates (not relative to temp CWD)
    from tests.mcp_server.test_support import get_template_root  # noqa: PLC0415

    template_root = get_template_root()
    monkeypatch.setenv(
        "PGMCP_TEMPLATE_ROOT",
        str(workspace / get_default_server_root() / "templates"),
    )
    monkeypatch.setenv(
        "PGMCP_CONFIG_ROOT",
        str(workspace / get_default_server_root() / "config"),
    )
    monkeypatch.setenv("TEMPLATE_ROOT", str(template_root))

    # Change CWD to workspace (template paths are relative)
    monkeypatch.chdir(workspace)

    yield workspace


@pytest.fixture(name="artifacts_yaml_content")
def _artifacts_yaml_content() -> str:
    """Minimal artifacts.yaml for testing."""
    return """version: "1.0.0"

artifact_types:
  - type: doc
    type_id: design
    template_version: "1.0.0"
    name: "Design Document"
    description: "Design document for features"
    template_path: documents/design.md.jinja2
    fallback_template: null
    name_suffix: null
    file_extension: ".md"
    generate_test: false
    context_schema:
      issue_number:
        type: "string"
        title: "Issue Number"
        description: "The issue number"
        required: true
      title:
        type: "string"
        title: "Title"
        description: "The design title"
        required: true
      author:
        type: "string"
        title: "Author"
        description: "The author"
        required: true
      status:
        type: "string"
        title: "Status"
        description: "Lifecycle status"
        required: false
      version:
        type: "string"
        title: "Version"
        description: "Version"
        required: false
      last_updated:
        type: "string"
        title: "Last Updated"
        description: "Last updated date"
        required: false
      problem_statement:
        type: "string"
        title: "Problem Statement"
        description: "Problem statement"
        required: false
      requirements_functional:
        type: "array"
        title: "Functional Requirements"
        description: "Functional requirements"
        required: false
      requirements_nonfunctional:
        type: "array"
        title: "Non-Functional Requirements"
        description: "Non-functional requirements"
        required: false
      decision:
        type: "string"
        title: "Decision"
        description: "The decision"
        required: false
      rationale:
        type: "string"
        title: "Rationale"
        description: "The rationale"
        required: false
      options:
        type: "array"
        title: "Options"
        description: "Design options"
        required: false
      key_decisions:
        type: "array"
        title: "Key Decisions"
        description: "Key decisions"
        required: false
      sections:
        type: "array"
        title: "Sections"
        description: "Sections list"
        required: false
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
    template_version: "1.0.0"
    name: "Data Transfer Object"
    description: "Pydantic DTO"
    template_path: components/dto.py.jinja2
    fallback_template: null
    name_suffix: null
    file_extension: ".py"
    generate_test: true
    context_schema:
      name:
        type: "string"
        title: "Name"
        description: "DTO Name"
        required: true
      dto_name:
        type: "string"
        title: "DTO Name"
        description: "DTO Name"
        required: false
      description:
        type: "string"
        title: "Description"
        description: "DTO Description"
        required: true
      fields:
        type: "array"
        title: "Fields"
        description: "Fields list"
        required: false
    state_machine:
      states: [CREATED]
      initial_state: CREATED
      valid_transitions: []
"""


@pytest.fixture(name="artifacts_yaml_file")
def _artifacts_yaml_file_phase_gate(
    temp_workspace: Path,
    artifacts_yaml_content: str,
) -> Path:
    """
    Write artifacts.yaml to temp workspace.

    Returns path to templates/config/artifacts.yaml
    """
    config_dir = temp_workspace / get_default_server_root() / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    artifacts_file = config_dir / "artifacts.yaml"
    artifacts_file.write_text(artifacts_yaml_content, encoding="utf-8")

    # Create dummy templates for testing
    template_dir = temp_workspace / get_default_server_root() / "templates" / "documents"
    template_dir.mkdir(parents=True, exist_ok=True)

    dummy_design_template = template_dir / "design.md.jinja2"
    dummy_design_template.write_text(
        "{#- Version: 1.0.0 -#}\n"
        "# {{ title }}\n\n"
        "Issue: #{{ issue_number }}\n"
        "Author: {{ author }}\n",
        encoding="utf-8",
    )

    # Create code template for dto
    code_template_dir = temp_workspace / get_default_server_root() / "templates" / "components"
    code_template_dir.mkdir(parents=True, exist_ok=True)

    dummy_dto_template = code_template_dir / "dto.py.jinja2"
    dummy_dto_template.write_text(
        "{#- Version: 1.0.0 -#}\n"
        '"""{{ description }}"""\n'
        "from pydantic import BaseModel\n\n"
        "class {{ name }}(BaseModel):\n"
        '    """{{ description }}"""\n'
        '    model_config = {"frozen": True, "extra": "forbid"}\n\n'
        "{% for field in fields %}"
        "    {{ field.name }}: {{ field.type }}\n"
        "{% endfor %}",
        encoding="utf-8",
    )

    return artifacts_file


@pytest.fixture(name="fs_adapter")
def _fs_adapter(temp_workspace: Path) -> FilesystemAdapter:
    """FilesystemAdapter scoped to temp workspace."""
    return FilesystemAdapter(root_path=str(temp_workspace))


@pytest.fixture(name="artifact_registry")
def _artifact_registry(
    artifacts_yaml_file: Path,
    temp_workspace: Path,
) -> ArtifactRegistryConfig:
    """Load ArtifactRegistryConfig from temp artifacts.yaml via ConfigLoader."""
    loader = ConfigLoader(
        config_root=artifacts_yaml_file.parent,
        template_root=temp_workspace / get_default_server_root() / "templates",
    )
    return loader.load_artifact_registry_config(config_path=artifacts_yaml_file)


@pytest.fixture(name="template_scaffolder")
def _template_scaffolder_alternate(
    artifact_registry: ArtifactRegistryConfig,
    temp_workspace: Path,
) -> TemplateScaffolder:
    """
    TemplateScaffolder instance with hermetic template directory.

    Uses temp workspace templates instead of production templates.
    """
    template_root = temp_workspace / get_default_server_root() / "templates"
    renderer = JinjaRenderer(template_dir=template_root)
    return TemplateScaffolder(registry=artifact_registry, renderer=renderer)


@pytest.fixture(name="validation_service")
def _validation_service_alternate() -> ValidationService:
    """ValidationService instance."""
    return ValidationService()


@pytest.fixture(name="artifact_manager")
def _artifact_manager(
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
        server_root=temp_workspace / get_default_server_root(),
    )


# Helper functions for dynamic artifact/template creation


@dataclass
class ArtifactIdentity:
    """Artifact type and ID."""

    type_id: str
    artifact_type: str  # 'code' or 'doc'


@dataclass
class TemplateFields:
    """Template field specification."""

    required: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)


@dataclass
class ArtifactSpec:
    """Specification for adding an artifact to artifacts.yaml."""

    identity: ArtifactIdentity
    name: str
    template_path: str
    file_extension: str
    description: str | None = None
    template_fields: TemplateFields = field(default_factory=TemplateFields)
    generate_test: bool = False
    strict_validation: bool | None = None
    template_version: str = "1.0.0"


def add_artifact_to_yaml(artifacts_yaml_path: Path, spec: ArtifactSpec) -> None:
    """
    Add artifact type to existing artifacts.yaml.

    Args:
        artifacts_yaml_path: Path to artifacts.yaml
        spec: Artifact specification
    """
    # Load existing YAML
    with open(artifacts_yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Build context_schema
    context_schema = {}
    for f in spec.template_fields.required or ["name"]:
        context_schema[f] = {
            "type": "string",
            "title": f.replace("_", " ").title(),
            "description": f,
            "required": True,
        }
    for f in spec.template_fields.optional or []:
        context_schema[f] = {
            "type": "string",
            "title": f.replace("_", " ").title(),
            "description": f,
            "required": False,
        }
    if "name" not in context_schema:
        context_schema["name"] = {
            "type": "string",
            "title": "Name",
            "description": "Name",
            "required": False,
        }
    if "description" not in context_schema:
        context_schema["description"] = {
            "type": "string",
            "title": "Description",
            "description": "Description",
            "required": False,
        }

    # Create new artifact definition
    strict_val = spec.strict_validation
    if strict_val is None:
        strict_val = spec.identity.artifact_type in ("code", "tracking")

    artifact_def = {
        "type": spec.identity.artifact_type,
        "type_id": spec.identity.type_id,
        "template_version": spec.template_version,
        "name": spec.name,
        "description": spec.description or f"{spec.name} artifact",
        "template_path": spec.template_path,
        "fallback_template": None,
        "name_suffix": None,
        "file_extension": spec.file_extension,
        "generate_test": spec.generate_test,
        "strict_validation": strict_val,
        "context_schema": context_schema,
        "state_machine": {
            "states": ["CREATED"],
            "initial_state": "CREATED",
            "valid_transitions": [],
        },
    }

    # Append to artifact_types
    data["artifact_types"].append(artifact_def)

    # Write back
    with open(artifacts_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def create_template(workspace_root: Path, template_relpath: str, template_content: str) -> Path:
    """
    Create template file in workspace.

    Args:
        workspace_root: Workspace root path
        template_relpath: Relative path (e.g., 'components/dto.py.jinja2')
        template_content: Template content (Jinja2)

    Returns:
        Absolute path to created template
    """
    template_root = workspace_root / get_default_server_root() / "templates"
    template_path = template_root / template_relpath
    template_path.parent.mkdir(parents=True, exist_ok=True)
    if "{#- Version:" not in template_content:
        template_content = "{#- Version: 1.0.0 -#}\n" + template_content
    template_path.write_text(template_content, encoding="utf-8")
    return template_path
