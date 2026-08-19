"""Shared test helpers for DI-heavy MCP components and tools.

@layer: Tests (Support)
@dependencies: shared test helpers, mcp_server managers, scaffolders, and policy components
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

from mcp_server.config.loader import (
    ConfigLoader,
    normalize_config_root,
)
from mcp_server.config.settings import Settings as RealSettings
from mcp_server.core.directory_policy_resolver import DirectoryPolicyResolver
from mcp_server.core.interfaces import GateReport
from mcp_server.core.phase_detection import ScopeDecoder
from mcp_server.core.policy_engine import PolicyEngine
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_contract_resolver import (
    PhaseConfigContext,
)
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.qa_manager import QAManager
from mcp_server.managers.quality_state_repository import FileQualityStateRepository
from mcp_server.managers.state_repository import FileStateRepository
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.metadata import ScaffoldMetadataParser
from mcp_server.schemas import (
    ArtifactRegistryConfig,
    ContractsConfig,
    GitConfig,
    ProjectStructureConfig,
    QualityConfig,
    ScaffoldMetadataConfig,
    WorkflowConfig,
    WorkphasesConfig,
)
from mcp_server.tools.issue_tools import CreateIssueTool

if TYPE_CHECKING:
    from mcp_server.config.settings import Settings
    from mcp_server.core.interfaces import IGitContextReader, IQualityStateRepository, IStateReader
    from mcp_server.managers.workflow_status_resolver import WorkflowStatusResolver
    from mcp_server.server import MCPServer


def get_default_server_root() -> str:
    """Get the default server root directory name from Settings."""
    from unittest.mock import Mock  # noqa: PLC0415

    try:
        from mcp_server.config.settings import Settings  # noqa: PLC0415

        settings = Settings.from_env()
        if isinstance(settings, Mock) or isinstance(getattr(settings, "server", None), Mock):
            return ".pgmcp"
        val = settings.server.server_root_dir
        if isinstance(val, Mock):
            return ".pgmcp"
        return str(val)
    except Exception:
        return ".pgmcp"


def get_template_root() -> Path:
    """Get the template root directory from settings."""
    from mcp_server.config.settings import Settings  # noqa: PLC0415

    return Settings.from_env().server.resolved_template_root


class _NopGateRunner:
    """No-op gate runner for unit tests: all gates pass, correct cycle-based detection.

    Uses ContractsConfig for is_cycle_based_phase so that PSE cycle-phase guards
    work correctly without requiring real deliverable files on disk.
    """

    def __init__(self, contracts_config: ContractsConfig) -> None:
        self._contracts_config = contracts_config

    def is_cycle_based_phase(self, workflow_name: str, phase: str) -> bool:
        wf = self._contracts_config.workflows.get(workflow_name)
        if not wf:
            return False
        for p in wf.phases:
            if p.name == phase:
                return p.cycle_based
        return False

    def enforce_phase_exit(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number
        return GateReport()

    def inspect_phase_exit(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number
        return GateReport()

    def enforce_cycle_exit(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int,
    ) -> GateReport:
        del workflow_name, phase, cycle_number
        return GateReport()

    def inspect_cycle_exit(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int,
    ) -> GateReport:
        del workflow_name, phase, cycle_number
        return GateReport()


def _candidate_config_roots(workspace_root: Path | str | None = None) -> list[Path]:
    """Return workspace-first candidate canonical config roots for tests."""
    candidates: list[Path] = []

    def _probe(root: Path | str) -> list[Path]:
        try:
            return [normalize_config_root(root)]
        except FileNotFoundError:
            # Plain workspace root — probe conventional hidden state directories.
            p = Path(root).resolve()
            return [p / hidden / "config" for hidden in (get_default_server_root(),)]

    if workspace_root is not None:
        candidates.extend(_probe(workspace_root))
    candidates.extend(_probe(Path.cwd()))
    candidates.extend(_probe(Path(__file__).resolve().parents[2]))

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_candidates.append(candidate)
    return unique_candidates


def resolve_config_root(
    workspace_root: Path | str | None = None,
    required_paths: tuple[str | Path, ...] = (),
) -> Path:
    """Resolve the best config root for one workspace under test."""
    settings = RealSettings.from_env()
    if workspace_root is not None:
        candidate = Path(workspace_root)
        if candidate.name != "config":
            candidate = candidate / settings.server.server_root_dir / "config"

        def _file_exists(f: str | Path) -> bool:
            if str(f) == "artifacts.yaml":
                return (candidate.parent / "templates" / "config" / "artifacts.yaml").exists()
            return (candidate / f).exists()

        if candidate.exists() and all(_file_exists(f) for f in required_paths):
            return candidate
    return settings.server.resolved_config_root


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
        "contracts_config": _load_config(
            workspace_root,
            "contracts.yaml",
            "load_contracts_config",
        ),
        # kept for legacy callers; new code should use contracts_config
        "workflow_config": _load_config(
            workspace_root,
            "workflows.yaml",
            "load_workflow_config",
        ),
    }


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


def load_contracts_config(workspace_root: Path | str | None = None) -> ContractsConfig:
    """Load ContractsConfig through the shared ConfigLoader helper."""
    return cast(
        ContractsConfig,
        _load_config(workspace_root, "contracts.yaml", "load_contracts_config"),
    )


def make_project_manager(
    workspace_root: Path | str,
    contracts_config: ContractsConfig | None = None,
    git_manager: GitManager | None = None,
    workflow_status_resolver: WorkflowStatusResolver | None = None,
) -> ProjectManager:
    """Build a ProjectManager with explicit contracts config injection."""
    resolved_contracts_config = contracts_config or load_contracts_config(workspace_root)
    resolved_git_manager = git_manager
    if resolved_git_manager is None:
        git_roots = _candidate_config_roots(workspace_root)
        if any((candidate / "git.yaml").exists() for candidate in git_roots):
            resolved_git_manager = make_git_manager(workspace_root)
    workphases_config = cast(
        WorkphasesConfig,
        _load_config(workspace_root, "workphases.yaml", "load_workphases_config"),
    )
    if workflow_status_resolver is None:
        from mcp_server.core.commit_phase_detector import CommitPhaseDetector  # noqa: PLC0415
        from mcp_server.managers.workflow_status_resolver import (  # noqa: PLC0415
            WorkflowStatusResolver,
        )

        workspace_path = Path(workspace_root)
        _git_reader = resolved_git_manager or make_git_manager(workspace_root)
        _state_reader = FileStateRepository(
            state_file=workspace_path / get_default_server_root() / "state.json"
        )
        _detector = CommitPhaseDetector(workphases_config=workphases_config)
        workflow_status_resolver = WorkflowStatusResolver(
            git_context_reader=_git_reader,
            state_reader=_state_reader,
            commit_phase_detector=_detector,
        )
    return ProjectManager(
        workspace_root=workspace_root,
        contracts_config=resolved_contracts_config,
        git_manager=resolved_git_manager,
        workphases_config=workphases_config,
        workflow_status_resolver=workflow_status_resolver,
        server_root=Path(workspace_root) / get_default_server_root(),
    )


def make_phase_state_engine(
    workspace_root: Path | str,
    project_manager: ProjectManager | None = None,
    state_repository: object | None = None,
    scope_decoder: object | None = None,
    workflow_gate_runner: object | None = None,
    workflow_state_mutator: object | None = None,
    context_loaded_writer: object | None = None,
) -> PhaseStateEngine:
    """Build a PhaseStateEngine with explicit config objects and injected seams."""
    workspace_path = Path(workspace_root)
    manager = project_manager or make_project_manager(workspace_root)
    git_config = cast(GitConfig, _load_config(workspace_root, "git.yaml", "load_git_config"))
    workphases_config = _load_config(
        workspace_root,
        "workphases.yaml",
        "load_workphases_config",
    )
    contracts_config = cast(
        ContractsConfig,
        _load_config(workspace_root, "contracts.yaml", "load_contracts_config"),
    )
    resolved_state_repository = state_repository or FileStateRepository(
        state_file=workspace_path / get_default_server_root() / "state.json"
    )
    resolved_scope_decoder = scope_decoder or ScopeDecoder(
        workphases_config=cast(WorkphasesConfig, workphases_config)
    )
    resolved_workflow_gate_runner = workflow_gate_runner or _NopGateRunner(contracts_config)
    if workflow_state_mutator is None:
        from mcp_server.managers.workflow_state_mutator import WorkflowStateMutator  # noqa: PLC0415

        workflow_state_mutator = WorkflowStateMutator(
            state_repository=resolved_state_repository,
        )
    return PhaseStateEngine(
        workspace_root=workspace_root,
        project_manager=manager,
        git_config=git_config,
        contracts_config=contracts_config,
        state_repository=resolved_state_repository,
        scope_decoder=resolved_scope_decoder,
        workflow_gate_runner=resolved_workflow_gate_runner,
        workflow_state_mutator=workflow_state_mutator,  # type: ignore[arg-type]
        server_root=workspace_path / get_default_server_root(),
        context_loaded_writer=context_loaded_writer,  # type: ignore[arg-type]
    )


def make_phase_config_context(
    workspace_root: Path | str,
    issue_number: int | None = None,
) -> PhaseConfigContext:
    """Build a PhaseConfigContext explicitly from config and optional deliverables."""
    planning_deliverables = None
    workspace_path = Path(workspace_root)
    deliverables_path = workspace_path / get_default_server_root() / "deliverables.json"
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
        contracts=cast(
            ContractsConfig,
            _load_config(
                workspace_root,
                "contracts.yaml",
                "load_contracts_config",
            ),
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
    return PolicyEngine(
        config_root=config_root,
        operation_config=loader.load_operation_policies_config(),
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
    quality_state_repository: IQualityStateRepository | None = None,
    git_context_reader: IGitContextReader | None = None,
    state_reader: IStateReader | None = None,
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
    resolved_quality_state_repo: IQualityStateRepository = quality_state_repository or (
        FileQualityStateRepository(
            backing_file=resolved_workspace / get_default_server_root() / "quality_state.json"
        )
        if resolved_workspace is not None
        else MagicMock()
    )
    resolved_git_context_reader: IGitContextReader = git_context_reader or MagicMock()
    if state_reader is not None:
        resolved_state_reader: IStateReader = state_reader
    else:
        _default_sr = MagicMock()
        _default_sr.load.side_effect = FileNotFoundError
        resolved_state_reader = _default_sr
    return QAManager(
        workspace_root=resolved_workspace,
        quality_config=resolved_quality,
        quality_state_repository=resolved_quality_state_repo,
        git_context_reader=resolved_git_context_reader,
        state_reader=resolved_state_reader,
    )


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
        server_root=Path(workspace_root) / get_default_server_root(),
    )


def make_create_issue_tool(manager: MagicMock | None = None) -> CreateIssueTool:
    """Create CreateIssueTool with explicit config objects and a mock manager."""
    dependencies = load_issue_tool_dependencies()
    return CreateIssueTool(
        manager=manager or MagicMock(),
        issue_config=dependencies["issue_config"],
        milestone_config=dependencies["milestone_config"],
        contracts_config=dependencies["contracts_config"],
        label_config=dependencies["label_config"],
        scope_config=dependencies["scope_config"],
        git_config=dependencies["git_config"],
    )


def make_test_server(settings: Settings | None = None) -> MCPServer:
    """Create a fully bootstrapped MCPServer for tests using ServerBootstrapper."""
    from mcp_server.bootstrap import ServerBootstrapper  # noqa: PLC0415
    from mcp_server.config.settings import Settings as ServerSettings  # noqa: PLC0415

    resolved_settings = settings or ServerSettings.from_env()
    bootstrapper = ServerBootstrapper(resolved_settings)
    return bootstrapper.bootstrap()


def assert_itool_result(
    result: Any,  # noqa: ANN401
    text_contains: str | None = None,
) -> str:
    """Verifies the ToolResult structure for ITool (pure text, no JSON)."""
    is_err = getattr(result, "is_error", None)
    if is_err is None:
        is_err = getattr(result, "isError", False)
    assert not is_err, f"Expected successful tool result, got error: {result}"

    json_blocks = []
    text_blocks = []
    for c in result.content:
        c_type = c.get("type") if isinstance(c, dict) else getattr(c, "type", None)
        if c_type == "json":
            json_blocks.append(c)
        elif c_type == "text":
            text_blocks.append(c)

    assert len(json_blocks) == 0, f"Expected no json block, got {len(json_blocks)}"
    assert len(text_blocks) == 1, f"Expected exactly one text block, got {len(text_blocks)}"

    first_text = text_blocks[0]
    text_content = (
        first_text["text"] if isinstance(first_text, dict) else getattr(first_text, "text", "")
    )

    if text_contains:
        assert text_contains in text_content

    return text_content
