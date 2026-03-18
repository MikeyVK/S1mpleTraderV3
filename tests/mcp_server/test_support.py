"""Shared test helpers for DI-heavy MCP components and tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

from mcp_server.config.compat_roots import (
    get_candidate_config_roots,
)
from mcp_server.config.compat_roots import (
    resolve_config_root as resolve_runtime_config_root,
)
from mcp_server.config.loader import ConfigLoader
from mcp_server.core.directory_policy_resolver import DirectoryPolicyResolver
from mcp_server.core.policy_engine import PolicyEngine
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_contract_resolver import PhaseConfigContext
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.qa_manager import QAManager
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.metadata import ScaffoldMetadataParser
from mcp_server.schemas import (
    ArtifactRegistryConfig,
    GitConfig,
    ProjectStructureConfig,
    QualityConfig,
    ScaffoldMetadataConfig,
    WorkflowConfig,
)
from mcp_server.tools.git_tools import CreateBranchInput
from mcp_server.tools.issue_tools import CreateIssueInput, CreateIssueTool
from mcp_server.tools.pr_tools import CreatePRInput


def _candidate_config_roots(workspace_root: Path | str | None = None) -> list[Path]:
    """Return workspace-first candidate .st3 roots from the shared runtime resolver."""
    return get_candidate_config_roots(workspace_root)


def resolve_config_root(
    workspace_root: Path | str | None = None,
    required_paths: tuple[str | Path, ...] = (),
) -> Path:
    """Resolve the best .st3 config root for one workspace under test."""
    return resolve_runtime_config_root(
        preferred_root=workspace_root,
        required_files=required_paths,
    )


def make_config_loader(
    workspace_root: Path | str | None = None,
    required_paths: tuple[str | Path, ...] = (),
) -> ConfigLoader:
    """Create a ConfigLoader for the requested workspace."""
    return ConfigLoader(resolve_config_root(workspace_root, required_paths=required_paths))


def _load_config(
    workspace_root: Path | str | None,
    required_path: str | Path,
    load_method: str,
    **kwargs: object,
) -> object:
    """Load one config file with workspace-first, file-specific fallback."""
    loader = make_config_loader(workspace_root, required_paths=(required_path,))
    return getattr(loader, load_method)(**kwargs)


def load_issue_tool_dependencies(workspace_root: Path | str | None = None) -> dict[str, object]:
    """Load explicit issue-tool dependencies through ConfigLoader."""
    return {
        "issue_config": _load_config(workspace_root, "issues.yaml", "load_issue_config"),
        "git_config": _load_config(workspace_root, "git.yaml", "load_git_config"),
        "label_config": _load_config(workspace_root, "labels.yaml", "load_label_config"),
        "scope_config": _load_config(workspace_root, "scopes.yaml", "load_scope_config"),
        "milestone_config": _load_config(
            workspace_root,
            "milestones.yaml",
            "load_milestone_config",
        ),
        "contributor_config": _load_config(
            workspace_root,
            "contributors.yaml",
            "load_contributor_config",
        ),
        "workflow_config": _load_config(
            workspace_root,
            "workflows.yaml",
            "load_workflow_config",
        ),
    }


def configure_create_issue_input(workspace_root: Path | str | None = None) -> None:
    """Configure CreateIssueInput validators with explicit config objects."""
    dependencies = load_issue_tool_dependencies(workspace_root)
    CreateIssueInput.configure(
        issue_config=dependencies["issue_config"],
        git_config=dependencies["git_config"],
        label_config=dependencies["label_config"],
        scope_config=dependencies["scope_config"],
        milestone_config=dependencies["milestone_config"],
        contributor_config=dependencies["contributor_config"],
    )


def configure_create_branch_input(workspace_root: Path | str | None = None) -> GitConfig:
    """Configure CreateBranchInput validators with explicit git config."""
    git_config = cast(
        GitConfig,
        _load_config(workspace_root, "git.yaml", "load_git_config"),
    )
    CreateBranchInput.configure(git_config)
    return git_config


def configure_create_pr_input(workspace_root: Path | str | None = None) -> GitConfig:
    """Configure CreatePRInput validators with explicit git config."""
    git_config = cast(
        GitConfig,
        _load_config(workspace_root, "git.yaml", "load_git_config"),
    )
    CreatePRInput.configure(git_config)
    return git_config


def make_git_manager(workspace_root: Path | str | None = None) -> GitManager:
    """Build a GitManager with explicit GitConfig."""
    git_config = cast(
        GitConfig,
        _load_config(workspace_root, "git.yaml", "load_git_config"),
    )
    return GitManager(git_config=git_config)


def load_workflow_config(workspace_root: Path | str | None = None) -> WorkflowConfig:
    """Load WorkflowConfig through the shared ConfigLoader helper."""
    return cast(
        WorkflowConfig,
        _load_config(workspace_root, "workflows.yaml", "load_workflow_config"),
    )


def make_project_manager(
    workspace_root: Path | str,
    workflow_config: WorkflowConfig | None = None,
    git_manager: GitManager | None = None,
) -> ProjectManager:
    """Build a ProjectManager with explicit workflow config injection."""
    resolved_workflow_config = workflow_config or load_workflow_config(workspace_root)
    resolved_git_manager = git_manager
    if resolved_git_manager is None:
        git_roots = _candidate_config_roots(workspace_root)
        if any((candidate / "git.yaml").exists() for candidate in git_roots):
            resolved_git_manager = make_git_manager(workspace_root)
    return ProjectManager(
        workspace_root=workspace_root,
        workflow_config=resolved_workflow_config,
        git_manager=resolved_git_manager,
    )


def make_phase_state_engine(
    workspace_root: Path | str,
    project_manager: ProjectManager | None = None,
    state_repository: object | None = None,
) -> PhaseStateEngine:
    """Build a PhaseStateEngine with explicit config objects."""
    manager = project_manager or make_project_manager(workspace_root)
    kwargs: dict[str, object] = {}
    if state_repository is not None:
        kwargs["state_repository"] = state_repository
    return PhaseStateEngine(
        workspace_root=workspace_root,
        project_manager=manager,
        git_config=cast(GitConfig, _load_config(workspace_root, "git.yaml", "load_git_config")),
        workflow_config=cast(
            WorkflowConfig,
            _load_config(workspace_root, "workflows.yaml", "load_workflow_config"),
        ),
        workphases_config=_load_config(
            workspace_root,
            "workphases.yaml",
            "load_workphases_config",
        ),
        **kwargs,
    )


def make_phase_config_context(
    workspace_root: Path | str,
    issue_number: int | None = None,
) -> PhaseConfigContext:
    """Build a PhaseConfigContext explicitly from config and optional deliverables."""
    planning_deliverables = None
    workspace_path = Path(workspace_root)
    deliverables_path = workspace_path / ".st3" / "deliverables.json"
    if issue_number is not None and deliverables_path.exists():
        data = json.loads(deliverables_path.read_text(encoding="utf-8-sig"))
        issue_data = data.get(str(issue_number), {})
        candidate = issue_data.get("planning_deliverables")
        if isinstance(candidate, dict):
            planning_deliverables = candidate
    return PhaseConfigContext(
        workphases=_load_config(
            workspace_root,
            "workphases.yaml",
            "load_workphases_config",
        ),
        phase_contracts=_load_config(
            workspace_root,
            "phase_contracts.yaml",
            "load_phase_contracts_config",
        ),
        planning_deliverables=planning_deliverables,
    )


def make_policy_engine(workspace_root: Path | str | None = None) -> PolicyEngine:
    """Build a PolicyEngine with explicit config objects."""
    config_root = resolve_config_root(
        workspace_root,
        required_paths=("policies.yaml", "git.yaml", "workflows.yaml", "artifacts.yaml"),
    )
    loader = ConfigLoader(config_root)
    artifact_registry = loader.load_artifact_registry_config()
    project_structure = loader.load_project_structure_config(artifact_registry=artifact_registry)
    workflow_config = loader.load_workflow_config()
    return PolicyEngine(
        config_root=config_root,
        operation_config=loader.load_operation_policies_config(workflow_config=workflow_config),
        git_config=loader.load_git_config(),
        project_structure_config=project_structure,
    )


def make_directory_policy_resolver(
    workspace_root: Path | str | None = None,
    project_structure_config: ProjectStructureConfig | None = None,
) -> DirectoryPolicyResolver:
    """Build a DirectoryPolicyResolver with explicit project structure config."""
    config = project_structure_config
    if config is None:
        registry = cast(
            ArtifactRegistryConfig,
            _load_config(
                workspace_root,
                "artifacts.yaml",
                "load_artifact_registry_config",
            ),
        )
        config = cast(
            ProjectStructureConfig,
            _load_config(
                workspace_root,
                "project_structure.yaml",
                "load_project_structure_config",
                artifact_registry=registry,
            ),
        )
    return DirectoryPolicyResolver(config)


def make_template_scaffolder(
    workspace_root: Path | str | None = None,
    registry: ArtifactRegistryConfig | None = None,
    renderer: object | None = None,
) -> TemplateScaffolder:
    """Build a TemplateScaffolder with explicit registry injection."""
    resolved_registry = registry or cast(
        ArtifactRegistryConfig,
        _load_config(
            workspace_root,
            "artifacts.yaml",
            "load_artifact_registry_config",
        ),
    )
    return TemplateScaffolder(registry=resolved_registry, renderer=renderer)


def make_metadata_parser(
    workspace_root: Path | str | None = None,
    config: ScaffoldMetadataConfig | None = None,
) -> ScaffoldMetadataParser:
    """Build a ScaffoldMetadataParser with explicit metadata config."""
    metadata_config = config or cast(
        ScaffoldMetadataConfig,
        _load_config(
            workspace_root,
            "scaffold_metadata.yaml",
            "load_scaffold_metadata_config",
        ),
    )
    return ScaffoldMetadataParser(metadata_config)


def make_qa_manager(
    workspace_root: Path | str | None = None,
    quality_config: QualityConfig | None = None,
) -> QAManager:
    """Build a QAManager with explicit quality config injection."""
    resolved_quality = quality_config or cast(
        QualityConfig,
        _load_config(
            workspace_root,
            "quality.yaml",
            "load_quality_config",
        ),
    )
    resolved_workspace = Path(workspace_root) if workspace_root is not None else None
    return QAManager(workspace_root=resolved_workspace, quality_config=resolved_quality)


def make_artifact_manager(workspace_root: Path | str) -> ArtifactManager:
    """Build an ArtifactManager with explicit registry and project structure config."""
    registry = cast(
        ArtifactRegistryConfig,
        _load_config(
            workspace_root,
            "artifacts.yaml",
            "load_artifact_registry_config",
        ),
    )
    project_structure = cast(
        ProjectStructureConfig,
        _load_config(
            workspace_root,
            "project_structure.yaml",
            "load_project_structure_config",
            artifact_registry=registry,
        ),
    )
    return ArtifactManager(
        workspace_root=workspace_root,
        registry=registry,
        project_structure_config=project_structure,
    )


def make_create_issue_tool(manager: MagicMock | None = None) -> CreateIssueTool:
    """Create CreateIssueTool with explicit config objects and a mock manager."""
    dependencies = load_issue_tool_dependencies()
    return CreateIssueTool(manager=manager or MagicMock(), **dependencies)
