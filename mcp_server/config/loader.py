"""Central config loader for migrated YAML-backed schemas."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

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

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def normalize_config_root(config_root: Path | str) -> Path:
    """Return the canonical .st3/config directory for a workspace or config path."""
    candidate = Path(config_root).resolve()
    if candidate.name == "config" and candidate.parent.name == ".st3":
        return candidate
    if candidate.name == ".st3":
        return candidate / "config"
    return candidate / ".st3" / "config"


def resolve_config_root(
    preferred_root: Path | str | None = None,
    explicit_root: Path | str | None = None,
    required_files: Iterable[str] = (),
) -> Path:
    """Resolve one canonical ST3 config root without legacy compatibility fallbacks."""
    required = tuple(required_files)

    def _has_required_files(candidate: Path) -> bool:
        return all((candidate / file_name).exists() for file_name in required)

    if explicit_root is not None:
        explicit_candidate = normalize_config_root(explicit_root)
        if explicit_candidate.exists() and _has_required_files(explicit_candidate):
            return explicit_candidate
        missing = [
            file_name for file_name in required if not (explicit_candidate / file_name).exists()
        ]
        if missing:
            missing_text = ", ".join(str(file_name) for file_name in missing)
            raise FileNotFoundError(
                "Explicit config_root is missing required files: "
                f"{missing_text} ({explicit_candidate})"
            )
        raise FileNotFoundError(f"Explicit config_root does not exist: {explicit_candidate}")

    candidates: list[Path] = []
    if preferred_root is not None:
        candidates.append(normalize_config_root(preferred_root))
    candidates.append(normalize_config_root(Path.cwd()))
    candidates.append(normalize_config_root(Path(__file__).resolve().parents[2]))

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_candidates.append(candidate)

    for candidate in unique_candidates:
        if candidate.exists() and _has_required_files(candidate):
            return candidate

    raise FileNotFoundError("Could not locate canonical ST3 config directory")


class ConfigLoader:
    """Single YAML reader for migrated config schemas."""

    def __init__(self, config_root: Path) -> None:
        self.config_root = normalize_config_root(config_root)

    def load_git_config(self, config_path: Path | None = None) -> GitConfig:
        data, resolved_path = self._load_yaml("git.yaml", config_path=config_path)
        return self._validate_schema(GitConfig, data, resolved_path)

    def load_label_config(self, config_path: Path | None = None) -> LabelConfig:
        data, resolved_path = self._load_yaml("labels.yaml", config_path=config_path)
        return self._validate_schema(LabelConfig, data, resolved_path)

    def load_scope_config(self, config_path: Path | None = None) -> ScopeConfig:
        data, resolved_path = self._load_yaml("scopes.yaml", config_path=config_path)
        return self._validate_schema(ScopeConfig, data, resolved_path)

    def load_workflow_config(self, config_path: Path | None = None) -> WorkflowConfig:
        data, resolved_path = self._load_yaml("workflows.yaml", config_path=config_path)
        return self._validate_schema(WorkflowConfig, data, resolved_path)

    def load_workphases_config(self, config_path: Path | None = None) -> WorkphasesConfig:
        data, resolved_path = self._load_yaml("workphases.yaml", config_path=config_path)
        return self._validate_schema(WorkphasesConfig, data, resolved_path)

    def load_artifact_registry_config(
        self,
        config_path: Path | None = None,
    ) -> ArtifactRegistryConfig:
        resolved_path = self._resolve_yaml_path("artifacts.yaml", config_path=config_path)
        if not resolved_path.exists():
            raise ConfigError(
                "Artifact registry not found: "
                f"{resolved_path}. Expected: .st3/config/artifacts.yaml. "
                "Fix: Create .st3/config/artifacts.yaml manually or restore from backup.",
                file_path=str(resolved_path),
            )

        try:
            with resolved_path.open(encoding="utf-8") as file_handle:
                raw_loaded = yaml.safe_load(file_handle)
        except yaml.YAMLError as exc:
            raise ConfigError(
                "Invalid YAML syntax: "
                f"{exc}. Fix: Check YAML syntax; common issues are incorrect "
                "indentation, missing colons, and unquoted special characters. "
                "Use a YAML validator.",
                file_path=str(resolved_path),
            ) from exc

        if raw_loaded is None:
            raise ConfigError(
                "Empty artifact registry: "
                f"{resolved_path}. Fix: Add artifact_types array with at least "
                "one artifact definition.",
                file_path=str(resolved_path),
            )
        if not isinstance(raw_loaded, dict):
            raise ConfigError(
                f"Invalid YAML root in {resolved_path.name}: expected mapping",
                file_path=str(resolved_path),
            )

        try:
            return ArtifactRegistryConfig.model_validate(raw_loaded)
        except ValidationError as exc:
            raise ConfigError(
                "Failed to load artifact registry: "
                f"{exc}. Fix: Check file permissions and YAML structure.",
                file_path=str(resolved_path),
            ) from exc

    def load_contributor_config(self, config_path: Path | None = None) -> ContributorConfig:
        data, resolved_path = self._load_yaml("contributors.yaml", config_path=config_path)
        return self._validate_schema(ContributorConfig, data, resolved_path)

    def load_issue_config(self, config_path: Path | None = None) -> IssueConfig:
        data, resolved_path = self._load_yaml("issues.yaml", config_path=config_path)
        return self._validate_schema(IssueConfig, data, resolved_path)

    def load_milestone_config(self, config_path: Path | None = None) -> MilestoneConfig:
        data, resolved_path = self._load_yaml("milestones.yaml", config_path=config_path)
        return self._validate_schema(MilestoneConfig, data, resolved_path)

    def load_operation_policies_config(
        self,
        config_path: Path | None = None,
        workflow_config: WorkflowConfig | None = None,
    ) -> OperationPoliciesConfig:
        data, resolved_path = self._load_yaml("policies.yaml", config_path=config_path)
        operations = data.get("operations")
        if not isinstance(operations, dict):
            raise ConfigError(
                f"Missing 'operations' key in {resolved_path.name}",
                file_path=str(resolved_path),
            )

        payload = {
            **data,
            "operations": {
                operation_id: {"operation_id": operation_id, **operation_data}
                for operation_id, operation_data in operations.items()
            },
        }
        config = self._validate_schema(OperationPoliciesConfig, payload, resolved_path)
        effective_workflow_config = workflow_config or self.load_workflow_config()
        self._validate_operation_policy_phases(config, effective_workflow_config, resolved_path)
        return config

    def load_project_structure_config(
        self,
        config_path: Path | None = None,
        artifact_registry: ArtifactRegistryConfig | None = None,
    ) -> ProjectStructureConfig:
        data, resolved_path = self._load_yaml(
            "project_structure.yaml",
            config_path=config_path,
        )
        directories = data.get("directories")
        if not isinstance(directories, dict):
            raise ConfigError(
                f"Missing 'directories' key in {resolved_path.name}",
                file_path=str(resolved_path),
            )

        payload = {
            **data,
            "directories": {
                directory_path: {"path": directory_path, **directory_data}
                for directory_path, directory_data in directories.items()
            },
        }
        config = self._validate_schema(ProjectStructureConfig, payload, resolved_path)
        effective_artifact_registry = artifact_registry or self.load_artifact_registry_config()
        self._validate_project_structure_artifact_types(
            config,
            effective_artifact_registry,
            resolved_path,
        )
        self._validate_project_structure_parent_references(config, resolved_path)
        return config

    def load_quality_config(self, config_path: Path | None = None) -> QualityConfig:
        data, resolved_path = self._load_yaml("quality.yaml", config_path=config_path)
        return self._validate_schema(QualityConfig, data, resolved_path)

    def load_scaffold_metadata_config(
        self,
        config_path: Path | None = None,
    ) -> ScaffoldMetadataConfig:
        data, resolved_path = self._load_yaml(
            "scaffold_metadata.yaml",
            config_path=config_path,
        )
        return self._validate_schema(ScaffoldMetadataConfig, data, resolved_path)

    def load_enforcement_config(self, config_path: Path | None = None) -> EnforcementConfig:
        data, resolved_path = self._load_yaml(
            "enforcement.yaml",
            config_path=config_path,
            allow_missing=True,
        )
        return self._validate_schema(EnforcementConfig, data, resolved_path)

    def load_phase_contracts_config(
        self,
        config_path: Path | None = None,
    ) -> PhaseContractsConfig:
        data, resolved_path = self._load_yaml(
            "phase_contracts.yaml",
            config_path=config_path,
        )
        return self._validate_schema(PhaseContractsConfig, data, resolved_path)

    def _validate_operation_policy_phases(
        self,
        config: OperationPoliciesConfig,
        workflow_config: WorkflowConfig,
        resolved_path: Path,
    ) -> None:
        valid_phases: set[str] = set()
        for workflow in workflow_config.workflows.values():
            valid_phases.update(workflow.phases)

        for operation_id, policy in config.operations.items():
            invalid_phases = set(policy.allowed_phases) - valid_phases
            if invalid_phases:
                raise ConfigError(
                    f"Operation '{operation_id}' references unknown phases: "
                    f"{sorted(invalid_phases)}. Valid phases from workflow config: "
                    f"{sorted(valid_phases)}",
                    file_path=str(resolved_path),
                )

    def _validate_project_structure_artifact_types(
        self,
        config: ProjectStructureConfig,
        artifact_registry: ArtifactRegistryConfig,
        resolved_path: Path,
    ) -> None:
        valid_types = set(artifact_registry.list_type_ids())
        for directory_path, policy in config.directories.items():
            invalid_types = set(policy.allowed_artifact_types) - valid_types
            if invalid_types:
                raise ConfigError(
                    f"Directory '{directory_path}' references unknown artifact types: "
                    f"{sorted(invalid_types)}. Valid types from artifact registry: "
                    f"{sorted(valid_types)}",
                    file_path=str(resolved_path),
                )

    def _validate_project_structure_parent_references(
        self,
        config: ProjectStructureConfig,
        resolved_path: Path,
    ) -> None:
        for directory_path, policy in config.directories.items():
            if policy.parent is not None and policy.parent not in config.directories:
                raise ConfigError(
                    f"Directory '{directory_path}' references unknown parent: '{policy.parent}'",
                    file_path=str(resolved_path),
                )

    def _resolve_yaml_path(self, file_name: str | Path, config_path: Path | None = None) -> Path:
        if config_path is None:
            return self.config_root / file_name
        return Path(config_path).resolve()

    def _load_yaml(
        self,
        file_name: str | Path,
        config_path: Path | None = None,
        allow_missing: bool = False,
    ) -> tuple[dict[str, Any], Path]:
        resolved_path = self._resolve_yaml_path(file_name, config_path=config_path)

        if not resolved_path.exists():
            if allow_missing:
                return {}, resolved_path
            raise ConfigError(
                f"Config file not found: {resolved_path.name}",
                file_path=str(resolved_path),
            )

        try:
            with resolved_path.open(encoding="utf-8") as file_handle:
                loaded = yaml.safe_load(file_handle) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(
                f"Invalid YAML in {resolved_path.name}: {exc}",
                file_path=str(resolved_path),
            ) from exc

        if not isinstance(loaded, dict):
            raise ConfigError(
                f"Invalid YAML root in {resolved_path.name}: expected mapping",
                file_path=str(resolved_path),
            )

        return loaded, resolved_path

    def _validate_schema(
        self,
        schema_cls: type[SchemaT],
        data: dict[str, Any],
        resolved_path: Path,
    ) -> SchemaT:
        try:
            return schema_cls.model_validate(data)
        except ValidationError as exc:
            raise ConfigError(
                f"Config validation failed for {resolved_path.name}: {exc}",
                file_path=str(resolved_path),
            ) from exc
