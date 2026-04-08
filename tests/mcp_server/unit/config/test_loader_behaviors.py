# tests/mcp_server/unit/config/test_loader_behaviors.py
# template=unit_test version=manual created=2026-03-26T00:00Z updated=
"""Focused behavioral tests for ConfigLoader helper branches.

@layer: Tests (Unit)
@dependencies: [pathlib, pytest, mcp_server.config.loader, mcp_server.config.schemas]
"""

from pathlib import Path

import pytest

from mcp_server.config.loader import (
    ConfigLoader,
    normalize_config_root,
    resolve_config_root,
)
from mcp_server.config.schemas import ArtifactRegistryConfig, WorkflowConfig
from mcp_server.core.exceptions import ConfigError


def _write_yaml(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _minimal_workflow_config() -> WorkflowConfig:
    return WorkflowConfig(
        version="1.0",
        workflows={
            "feature": {
                "name": "feature",
                "phases": ["planning", "implementation"],
                "default_execution_mode": "interactive",
                "description": "Feature workflow",
            }
        },
    )


def _minimal_artifact_registry() -> ArtifactRegistryConfig:
    return ArtifactRegistryConfig(
        version="1.0",
        artifact_types=[
            {
                "type": "code",
                "type_id": "dto",
                "name": "DTO",
                "description": "Data transfer object",
                "file_extension": ".py",
                "state_machine": {
                    "states": ["draft"],
                    "initial_state": "draft",
                    "valid_transitions": [],
                },
            }
        ],
    )


def test_normalize_config_root_handles_workspace_and_st3_paths(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    config_root = workspace_root / ".st3" / "config"

    assert normalize_config_root(workspace_root) == config_root.resolve()
    assert normalize_config_root(workspace_root / ".st3") == config_root.resolve()
    assert normalize_config_root(config_root) == config_root.resolve()


def test_resolve_config_root_uses_preferred_workspace_root(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    config_root = workspace_root / ".st3" / "config"
    _write_yaml(config_root / "git.yaml", "branch_types: []\n")

    assert (
        resolve_config_root(
            preferred_root=workspace_root,
            required_files=("git.yaml",),
        )
        == config_root.resolve()
    )


def test_resolve_config_root_returns_explicit_root_when_required_files_exist(
    tmp_path: Path,
) -> None:
    config_root = tmp_path / ".st3" / "config"
    _write_yaml(config_root / "workflows.yaml", "version: '1.0'\nworkflows: {}\n")

    assert (
        resolve_config_root(
            explicit_root=config_root,
            required_files=("workflows.yaml",),
        )
        == config_root.resolve()
    )


def test_resolve_config_root_raises_for_missing_required_file_in_explicit_root(
    tmp_path: Path,
) -> None:
    config_root = tmp_path / ".st3" / "config"
    config_root.mkdir(parents=True)

    with pytest.raises(FileNotFoundError, match="missing required files"):
        resolve_config_root(
            explicit_root=config_root,
            required_files=("workflows.yaml",),
        )


def test_resolve_config_root_raises_for_nonexistent_explicit_root(tmp_path: Path) -> None:
    missing_root = tmp_path / ".st3" / "config"

    with pytest.raises(FileNotFoundError, match="does not exist"):
        resolve_config_root(explicit_root=missing_root)


def test_load_enforcement_config_allows_missing_file(tmp_path: Path) -> None:
    loader = ConfigLoader(tmp_path / ".st3" / "config")

    assert loader.load_enforcement_config().enforcement == []


def test_load_artifact_registry_rejects_empty_yaml(tmp_path: Path) -> None:
    config_root = tmp_path / ".st3" / "config"
    artifacts_path = _write_yaml(config_root / "artifacts.yaml", "")
    loader = ConfigLoader(config_root)

    with pytest.raises(ConfigError, match="Empty artifact registry"):
        loader.load_artifact_registry_config(config_path=artifacts_path)


def test_load_artifact_registry_rejects_non_mapping_root(tmp_path: Path) -> None:
    config_root = tmp_path / ".st3" / "config"
    artifacts_path = _write_yaml(config_root / "artifacts.yaml", "- dto\n")
    loader = ConfigLoader(config_root)

    with pytest.raises(ConfigError, match="expected mapping"):
        loader.load_artifact_registry_config(config_path=artifacts_path)


def test_load_operation_policies_uses_workflow_loader_fallback(tmp_path: Path) -> None:
    config_root = tmp_path / ".st3" / "config"
    _write_yaml(
        config_root / "workflows.yaml",
        """
version: "1.0"
workflows:
  feature:
    name: "feature"
    phases: ["planning", "implementation"]
    default_execution_mode: "interactive"
    description: "Feature workflow"
""".strip()
        + "\n",
    )
    policies_path = _write_yaml(
        config_root / "policies.yaml",
        """
operations:
  commit:
    description: "Commit changes"
    allowed_phases: ["planning"]
    blocked_patterns: []
    allowed_extensions: []
    require_tdd_prefix: false
    allowed_prefixes: []
""".strip()
        + "\n",
    )

    config = ConfigLoader(config_root).load_operation_policies_config(
        config_path=policies_path,
    )

    assert config.get_operation_policy("commit").allowed_phases == ["planning"]


def test_load_operation_policies_requires_operations_key(tmp_path: Path) -> None:
    config_root = tmp_path / ".st3" / "config"
    policies_path = _write_yaml(config_root / "policies.yaml", "version: '1.0'\n")
    loader = ConfigLoader(config_root)

    with pytest.raises(ConfigError, match="Missing 'operations' key"):
        loader.load_operation_policies_config(config_path=policies_path)


def test_load_operation_policies_rejects_unknown_phase_reference(tmp_path: Path) -> None:
    config_root = tmp_path / ".st3" / "config"
    policies_path = _write_yaml(
        config_root / "policies.yaml",
        """
operations:
  commit:
    description: "Commit changes"
    allowed_phases: ["unknown"]
    blocked_patterns: []
    allowed_extensions: []
    require_tdd_prefix: false
    allowed_prefixes: []
""".strip()
        + "\n",
    )
    loader = ConfigLoader(config_root)

    with pytest.raises(ConfigError, match="references unknown phases"):
        loader.load_operation_policies_config(
            config_path=policies_path,
            workflow_config=_minimal_workflow_config(),
        )


def test_load_project_structure_uses_registry_loader_fallback(tmp_path: Path) -> None:
    config_root = tmp_path / ".st3" / "config"
    _write_yaml(
        config_root / "artifacts.yaml",
        """
version: "1.0"
artifact_types:
  - type: code
    type_id: dto
    name: DTO
    description: Data transfer object
    file_extension: .py
    generate_test: false
    required_fields: []
    optional_fields: []
    state_machine:
      states: [draft]
      initial_state: draft
      valid_transitions: []
""".strip()
        + "\n",
    )
    structure_path = _write_yaml(
        config_root / "project_structure.yaml",
        """
version: "1.0"
directories:
  backend:
    description: Backend code
    allowed_artifact_types: [dto]
    allowed_extensions: [.py]
    require_scaffold_for: []
""".strip()
        + "\n",
    )

    config = ConfigLoader(config_root).load_project_structure_config(
        config_path=structure_path,
    )

    assert config.get_directory("backend") is not None


def test_load_project_structure_requires_directories_key(tmp_path: Path) -> None:
    config_root = tmp_path / ".st3" / "config"
    structure_path = _write_yaml(config_root / "project_structure.yaml", "version: '1.0'\n")
    loader = ConfigLoader(config_root)

    with pytest.raises(ConfigError, match="Missing 'directories' key"):
        loader.load_project_structure_config(config_path=structure_path)


def test_load_project_structure_rejects_unknown_artifact_type(tmp_path: Path) -> None:
    config_root = tmp_path / ".st3" / "config"
    structure_path = _write_yaml(
        config_root / "project_structure.yaml",
        """
version: "1.0"
directories:
  backend:
    description: Backend code
    allowed_artifact_types: [worker]
    allowed_extensions: [.py]
    require_scaffold_for: []
""".strip()
        + "\n",
    )
    loader = ConfigLoader(config_root)

    with pytest.raises(ConfigError, match="references unknown artifact types"):
        loader.load_project_structure_config(
            config_path=structure_path,
            artifact_registry=_minimal_artifact_registry(),
        )


def test_load_project_structure_rejects_unknown_parent_reference(tmp_path: Path) -> None:
    config_root = tmp_path / ".st3" / "config"
    structure_path = _write_yaml(
        config_root / "project_structure.yaml",
        """
version: "1.0"
directories:
  backend:
    description: Backend code
    allowed_artifact_types: [dto]
    allowed_extensions: [.py]
    require_scaffold_for: []
  backend/dtos:
    parent: missing
    description: DTOs
    allowed_artifact_types: [dto]
    allowed_extensions: [.py]
    require_scaffold_for: []
""".strip()
        + "\n",
    )
    loader = ConfigLoader(config_root)

    with pytest.raises(ConfigError, match="references unknown parent"):
        loader.load_project_structure_config(
            config_path=structure_path,
            artifact_registry=_minimal_artifact_registry(),
        )
