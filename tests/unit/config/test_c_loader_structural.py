# tests/unit/config/test_c_loader_structural.py
"""
Structural tests for C_LOADER schema migration cycles.

Zone 1 only: schema/package introspection and ConfigLoader behavior.
No manager/tool consumer rewiring is validated here.

@layer: Tests (Unit)
@dependencies: [pytest, yaml, pathlib, inspect, mcp_server.config.loader]
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest
import yaml

import mcp_server.config.schemas.scaffold_metadata_config as scaffold_schema
from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import (
    ArtifactRegistryConfig,
    ContributorConfig,
    EnforcementConfig,
    GitConfig,
    IssueConfig,
    LabelConfig,
    MilestoneConfig,
    OperationPoliciesConfig,
    PhaseContractsConfig,
    ProjectStructureConfig,
    QualityConfig,
    ScaffoldMetadataConfig,
    ScopeConfig,
    WorkflowConfig,
    WorkphasesConfig,
)
from mcp_server.core.exceptions import ConfigError
from mcp_server.managers import enforcement_runner, phase_contract_resolver


@pytest.fixture
def config_root(tmp_path: Path) -> Path:
    """Create a minimal config root covering all 15 migrated schemas."""

    config_dir = tmp_path / ".st3" / "config"

    def write_yaml(relative_path: str, data: dict[str, Any]) -> None:
        target = config_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    write_yaml(
        "git.yaml",
        {
            "branch_types": ["feature", "bug"],
            "tdd_phases": ["red", "green", "refactor"],
            "commit_prefix_map": {
                "red": "test",
                "green": "feat",
                "refactor": "refactor",
            },
            "protected_branches": ["main"],
            "branch_name_pattern": "^[a-z0-9-]+$",
            "commit_types": ["feat", "fix", "test"],
            "default_base_branch": "main",
            "issue_title_max_length": 72,
        },
    )
    write_yaml(
        "labels.yaml",
        {
            "version": "1.0",
            "labels": [
                {
                    "name": "type:feature",
                    "color": "1D76DB",
                    "description": "Feature",
                }
            ],
            "freeform_exceptions": [],
            "label_patterns": [],
        },
    )
    write_yaml("scopes.yaml", {"version": "1.0", "scopes": ["architecture", "workflow"]})
    write_yaml(
        "workflows.yaml",
        {
            "version": "1.0",
            "workflows": {
                "feature": {
                    "name": "feature",
                    "phases": ["research", "planning", "implementation"],
                    "default_execution_mode": "interactive",
                    "description": "Feature workflow",
                }
            },
        },
    )
    write_yaml(
        "workphases.yaml",
        {
            "version": "1.0",
            "phases": {
                "implementation": {
                    "display_name": "Implementation",
                    "description": "Implementation phase",
                    "commit_type_hint": None,
                    "subphases": ["red", "green", "refactor"],
                    "exit_requires": [],
                    "entry_expects": [],
                }
            },
        },
    )
    write_yaml(
        "artifacts.yaml",
        {
            "version": "1.0",
            "artifact_types": [
                {
                    "type": "code",
                    "type_id": "dto",
                    "name": "DTO",
                    "description": "Data transfer object",
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
        },
    )
    write_yaml(
        "contributors.yaml",
        {
            "version": "1.0",
            "contributors": [{"login": "alice", "name": "Alice Doe"}],
        },
    )
    write_yaml(
        "issues.yaml",
        {
            "version": "1.0",
            "issue_types": [{"name": "feature", "workflow": "feature", "label": "type:feature"}],
            "required_label_categories": ["type", "priority", "scope"],
            "optional_label_inputs": {},
        },
    )
    write_yaml(
        "milestones.yaml",
        {
            "version": "1.0",
            "milestones": [{"number": 1, "title": "v1.0", "state": "open"}],
        },
    )
    write_yaml(
        "policies.yaml",
        {
            "operations": {
                "create_file": {
                    "description": "Create file",
                    "allowed_phases": ["planning"],
                    "blocked_patterns": [],
                    "allowed_extensions": [".py"],
                    "require_tdd_prefix": False,
                    "allowed_prefixes": [],
                }
            }
        },
    )
    write_yaml(
        "project_structure.yaml",
        {
            "directories": {
                "src": {
                    "parent": None,
                    "description": "Source directory",
                    "allowed_artifact_types": ["dto"],
                    "allowed_extensions": [".py"],
                    "require_scaffold_for": [],
                }
            }
        },
    )
    write_yaml(
        "quality.yaml",
        {
            "version": "1.0",
            "artifact_logging": {
                "enabled": True,
                "output_dir": "temp/qa_logs",
                "max_files": 200,
            },
            "active_gates": [],
            "gates": {
                "ruff": {
                    "name": "Ruff",
                    "description": "Lint",
                    "execution": {
                        "command": ["ruff", "check"],
                        "timeout_seconds": 60,
                        "working_dir": None,
                    },
                    "success": {"exit_codes_ok": [0]},
                    "capabilities": {
                        "file_types": [".py"],
                        "supports_autofix": True,
                    },
                }
            },
        },
    )
    write_yaml(
        "scaffold_metadata.yaml",
        {
            "version": "2.0",
            "comment_patterns": [
                {
                    "syntax": "hash",
                    "prefix": r"#\\s*",
                    "filepath_line_regex": r"^#\\s*(.+\\.py)$",
                    "metadata_line_regex": r"^#\\s*template=.+$",
                    "extensions": [".py"],
                }
            ],
            "metadata_fields": [
                {
                    "name": "template",
                    "format_regex": r"^[a-z0-9_-]+$",
                    "required": True,
                }
            ],
        },
    )
    write_yaml("enforcement.yaml", {"enforcement": []})
    write_yaml(
        "phase_contracts.yaml",
        {
            "workflows": {
                "feature": {
                    "implementation": {
                        "subphases": ["red", "green", "refactor"],
                        "commit_type_map": {
                            "red": "test",
                            "green": "feat",
                            "refactor": "refactor",
                        },
                        "cycle_based": True,
                        "exit_requires": [],
                        "cycle_exit_requires": {},
                    }
                }
            }
        },
    )

    return config_dir


def test_config_loader_exists() -> None:
    """ConfigLoader must exist as the zone-1 composition entry for YAML loading."""
    assert callable(ConfigLoader)


def test_loader_raises_on_missing_git_yaml(tmp_path: Path) -> None:
    """ConfigLoader must fail fast with ConfigError when git.yaml is absent."""
    loader = ConfigLoader(config_root=tmp_path)

    with pytest.raises(ConfigError, match="git.yaml"):
        loader.load_git_config()


def test_loader_exposes_all_fifteen_schema_methods() -> None:
    """C_LOADER.2 requires explicit load_* coverage for all 15 schemas."""
    for method_name in (
        "load_git_config",
        "load_label_config",
        "load_scope_config",
        "load_workflow_config",
        "load_workphases_config",
        "load_artifact_registry_config",
        "load_contributor_config",
        "load_issue_config",
        "load_milestone_config",
        "load_operation_policies_config",
        "load_project_structure_config",
        "load_quality_config",
        "load_scaffold_metadata_config",
        "load_enforcement_config",
        "load_phase_contracts_config",
    ):
        assert hasattr(ConfigLoader, method_name), f"Missing ConfigLoader.{method_name}()"


def test_loader_loads_all_fifteen_migrated_schema_instances(config_root: Path) -> None:
    """ConfigLoader must construct all 15 migrated schema types."""
    loader = ConfigLoader(config_root=config_root)
    workflow_config = loader.load_workflow_config()
    artifact_registry = loader.load_artifact_registry_config()

    assert isinstance(loader.load_git_config(), GitConfig)
    assert isinstance(loader.load_label_config(), LabelConfig)
    assert isinstance(loader.load_scope_config(), ScopeConfig)
    assert isinstance(workflow_config, WorkflowConfig)
    assert isinstance(loader.load_workphases_config(), WorkphasesConfig)
    assert isinstance(artifact_registry, ArtifactRegistryConfig)
    assert isinstance(loader.load_contributor_config(), ContributorConfig)
    assert isinstance(loader.load_issue_config(), IssueConfig)
    assert isinstance(loader.load_milestone_config(), MilestoneConfig)
    assert isinstance(
        loader.load_operation_policies_config(workflow_config=workflow_config),
        OperationPoliciesConfig,
    )
    assert isinstance(
        loader.load_project_structure_config(artifact_registry=artifact_registry),
        ProjectStructureConfig,
    )
    assert isinstance(loader.load_quality_config(), QualityConfig)
    assert isinstance(loader.load_scaffold_metadata_config(), ScaffoldMetadataConfig)
    assert isinstance(loader.load_enforcement_config(), EnforcementConfig)
    assert isinstance(loader.load_phase_contracts_config(), PhaseContractsConfig)


def _assert_no_self_loading_methods() -> None:
    for schema_cls in (
        GitConfig,
        LabelConfig,
        ScopeConfig,
        WorkflowConfig,
        WorkphasesConfig,
        ArtifactRegistryConfig,
        ContributorConfig,
        IssueConfig,
        MilestoneConfig,
        OperationPoliciesConfig,
        ProjectStructureConfig,
        QualityConfig,
        ScaffoldMetadataConfig,
        EnforcementConfig,
        PhaseContractsConfig,
    ):
        for forbidden in ("from_file", "load", "reset_instance", "reset"):
            assert not hasattr(schema_cls, forbidden), (
                f"{schema_cls.__name__}.{forbidden}() must not exist in config.schemas. "
                "ConfigLoader is the sole loader."
            )
        for forbidden_attr in (
            "singleton_instance",
            "_instance",
            "_loaded_path",
            "_loaded_mtime",
        ):
            assert forbidden_attr not in schema_cls.__dict__, (
                f"{schema_cls.__name__}.{forbidden_attr} must not exist in config.schemas. "
                "Singleton cache state belongs to legacy compatibility wrappers only."
            )


def _assert_schema_package_has_no_hardcoded_config_paths() -> None:
    schema_dir = Path(inspect.getfile(scaffold_schema)).parent
    for schema_file in schema_dir.rglob("*.py"):
        source = schema_file.read_text(encoding="utf-8")
        assert ".st3/config/" not in source, (
            f"{schema_file.name} must not hardcode config-root paths in schema code"
        )


def test_all_fifteen_schema_classes_have_no_self_loading_methods() -> None:
    """Pure schema classes must not contain self-loading or singleton state."""
    _assert_no_self_loading_methods()


def test_no_from_file_on_any_config_schema() -> None:
    """Planning alias for the structural delete guard used in C_LOADER.4 proof."""
    _assert_no_self_loading_methods()


def test_config_package_contains_no_legacy_wrapper_modules() -> None:
    """The legacy config compatibility wrapper files must be deleted flag-day."""
    config_dir = Path(__file__).resolve().parents[3] / "mcp_server" / "config"
    legacy_wrappers = {
        "artifact_registry_config.py",
        "compat_roots.py",
        "contributor_config.py",
        "git_config.py",
        "issue_config.py",
        "label_config.py",
        "milestone_config.py",
        "operation_policies.py",
        "project_structure.py",
        "quality_config.py",
        "scaffold_metadata_config.py",
        "scope_config.py",
        "workflows.py",
        "workphases_config.py",
    }
    present_wrappers = sorted(
        path.name for path in config_dir.iterdir() if path.is_file() and path.name in legacy_wrappers
    )
    assert present_wrappers == []


def test_no_hardcoded_config_paths_in_schema_package() -> None:
    """Schema package must not embed canonical config-root path knowledge."""
    _assert_schema_package_has_no_hardcoded_config_paths()


def test_no_cross_config_dependency_fields_on_schema_roots() -> None:
    """Root config schemas must not carry cross-config dependency state."""
    assert "artifact_registry" not in ProjectStructureConfig.model_fields
    assert "workflow_config" not in OperationPoliciesConfig.model_fields


def test_no_schema_orchestration_methods_on_schema_roots() -> None:
    """Cross-config orchestration belongs in ConfigLoader, not schema value objects."""
    for schema_cls, forbidden_methods in (
        (ProjectStructureConfig, ("validate_artifact_types", "validate_parent_references")),
        (OperationPoliciesConfig, ("validate_phases",)),
    ):
        for method_name in forbidden_methods:
            assert method_name not in schema_cls.__dict__, (
                f"{schema_cls.__name__}.{method_name}() must live in loader/validator layer"
            )


def test_extracted_schema_classes_no_longer_defined_in_manager_modules() -> None:
    """C_LOADER.2 must extract misplaced YAML schemas out of managers/."""
    enforcement_source = inspect.getsource(enforcement_runner)
    resolver_source = inspect.getsource(phase_contract_resolver)

    assert "class EnforcementConfig" not in enforcement_source
    assert "class PhaseContractsConfig" not in resolver_source


def test_schema_package_contains_no_local_config_error_class() -> None:
    """Pure schema modules must reuse core.exceptions.ConfigError."""
    assert "class ConfigError" not in inspect.getsource(scaffold_schema)


def test_no_tool_calls_from_file() -> None:
    """No tool may call Config.from_file() — all configs must be injected via DI.

    C_LOADER.3 rewired all 14 entry-point tools; this guard prevents regression.
    Zone 1: source-code inspection only, no YAML or filesystem access.
    """
    tools_dir = Path(__file__).parent.parent.parent.parent / "mcp_server" / "tools"
    violations: list[str] = []
    for py_file in tools_dir.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), 1):
            if ".from_file(" in line and not line.strip().startswith("#"):
                violations.append(f"{py_file.name}:{lineno}: {line.strip()}")
    assert not violations, (
        "Tools must not call Config.from_file() — configs are injected via DI.\n"
        + "\n".join(violations)
    )


def test_no_manager_imports_config_schema_directly() -> None:
    """Managers must import config types via mcp_server.schemas, not mcp_server.config.*

    After C_LOADER.3 all managers receive configs via DI and reference schema types
    through mcp_server.schemas (the public re-export layer).
    Importing from mcp_server.config.* directly in managers is a violation of the
    layering contract and signals a regression to the old singleton-load pattern.
    Zone 1: source-code inspection only.
    """
    managers_dir = Path(__file__).parent.parent.parent.parent / "mcp_server" / "managers"
    violations: list[str] = []
    for py_file in managers_dir.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("#", '"""', "'''")):
                continue
            if "from mcp_server.config" in line:
                violations.append(f"{py_file.name}:{lineno}: {line.strip()}")
    assert not violations, (
        "Managers must not import from mcp_server.config directly. "
        "Import config types via mcp_server.schemas instead.\n" + "\n".join(violations)
    )
