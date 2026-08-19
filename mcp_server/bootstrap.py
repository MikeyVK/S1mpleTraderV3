# mcp_server\bootstrap.py
# template=generic version=f35abd82 created=2026-06-09T09:48Z updated=
"""Bootstrap module.

Dependency injection and bootstrap orchestration layer.

@layer: MCP Server
@dependencies: [
    pathlib,
    dataclasses,
    mcp_server.config.loader,
    mcp_server.config.schemas,
    mcp_server.config.settings,
    mcp_server.config.validator,
    mcp_server.core.*,
    mcp_server.managers.*,
    mcp_server.state.*
]
@responsibilities:
    - Define immutable dataclasses for config models and managers.
    - Orchestrate composition root build phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import (
    ArtifactRegistryConfig,
    ContractsConfig,
    ContributorConfig,
    EnforcementConfig,
    GitConfig,
    IssueConfig,
    LabelConfig,
    MilestoneConfig,
    OperationPoliciesConfig,
    PresentationConfig,
    ProjectStructureConfig,
    QualityConfig,
    ScopeConfig,
    WorkflowConfig,
    WorkphasesConfig,
)
from mcp_server.config.settings import Settings
from mcp_server.config.validator import ConfigValidator
from mcp_server.core.commit_phase_detector import CommitPhaseDetector
from mcp_server.core.interfaces import IToolResponsePublisher, IToolResponseReader
from mcp_server.core.logging import get_logger, setup_logging
from mcp_server.core.phase_detection import ScopeDecoder
from mcp_server.core.tool_factory import ToolFactory as CoreToolFactory
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.managers.branch_parent_reader import BranchStateParentReader
from mcp_server.managers.deliverable_checker import DeliverableChecker
from mcp_server.managers.enforcement_runner import EnforcementRunner
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.managers.phase_contract_resolver import (
    MergeReadinessContext,
    PhaseConfigContext,
    PhaseContractResolver,
)
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.pytest_runner import PytestRunner
from mcp_server.managers.qa_manager import QAManager
from mcp_server.managers.quality_state_repository import FileQualityStateRepository
from mcp_server.managers.state_repository import BranchValidatedStateReader, FileStateRepository
from mcp_server.managers.workflow_gate_runner import WorkflowGateRunner
from mcp_server.managers.workflow_state_mutator import WorkflowStateMutator
from mcp_server.managers.workflow_status_resolver import WorkflowStatusResolver
from mcp_server.managers.workspace_version_validator import WorkspaceVersionValidator
from mcp_server.presenters.response_presenter import ResponsePresenter
from mcp_server.presenters.text_presenter import (
    TextPresenter,
    validate_presentation_alignment,
)
from mcp_server.presenters.validation_resource_presenter import (
    ValidationResourcePresenter,
)
from mcp_server.resources.base import BaseResource
from mcp_server.resources.cache import CachedResponseResource
from mcp_server.resources.github import GitHubIssuesResource
from mcp_server.resources.standards import StandardsResource
from mcp_server.resources.status import StatusResource
from mcp_server.scaffolding.template_registry import TemplateRegistry
from mcp_server.server import MCPServer
from mcp_server.state.context_loaded_cache import ContextLoadedCache
from mcp_server.state.pr_status_cache import PRStatusCache
from mcp_server.state.response_cache import ResponseCacheManager
from mcp_server.tools.admin_tools import RestartServerTool
from mcp_server.tools.cycle_tools import ForceCycleTransitionTool, TransitionCycleTool
from mcp_server.tools.discovery_tools import GetWorkContextTool
from mcp_server.tools.git_analysis_tools import GitDiffTool, GitListBranchesTool
from mcp_server.tools.git_fetch_tool import GitFetchTool
from mcp_server.tools.git_pull_tool import GitPullTool
from mcp_server.tools.git_tools import (
    CheckMergeTool,
    CreateBranchTool,
    GetParentBranchTool,
    GitCheckoutTool,
    GitCommitTool,
    GitDeleteBranchTool,
    GitMergeTool,
    GitPushTool,
    GitRestoreTool,
    GitStashTool,
    GitStatusTool,
    build_commit_type_resolver,
    build_phase_guard,
)
from mcp_server.tools.health_tools import HealthCheckTool
from mcp_server.tools.issue_tools import (
    CloseIssueTool,
    CreateIssueTool,
    GetIssueTool,
    ListIssuesTool,
    UpdateIssueTool,
)
from mcp_server.tools.label_tools import (
    AddLabelsTool,
    CreateLabelTool,
    DeleteLabelTool,
    ListLabelsTool,
    RemoveLabelsTool,
)
from mcp_server.tools.milestone_tools import (
    CloseMilestoneTool,
    CreateMilestoneTool,
    ListMilestonesTool,
)
from mcp_server.tools.phase_tools import ForcePhaseTransitionTool, TransitionPhaseTool
from mcp_server.tools.pr_tools import GetPRTool, ListPRsTool, MergePRTool, SubmitPRTool
from mcp_server.tools.project_tools import (
    GetProjectPlanTool,
    InitializeProjectTool,
    SavePlanningDeliverablesTool,
    UpdatePlanningDeliverablesTool,
)
from mcp_server.tools.quality_tools import AutoFixTool, RunQualityGatesTool
from mcp_server.tools.safe_edit_tool import SafeEditTool
from mcp_server.tools.scaffold_artifact import ScaffoldArtifactTool
from mcp_server.tools.scaffold_schema_tool import ScaffoldSchemaTool
from mcp_server.tools.template_validation_tool import TemplateValidationTool
from mcp_server.tools.test_tools import RunTestsTool

if TYPE_CHECKING:
    from mcp_server.server import MCPServer
logger = get_logger("bootstrap")
lifecycle_logger = get_logger("server_lifecycle")


@dataclass(frozen=True)
class ConfigLayer:
    """Immutable layer containing all validated configurations."""

    git_config: GitConfig
    workflow_config: WorkflowConfig
    workphases_config: WorkphasesConfig
    quality_config: QualityConfig
    label_config: LabelConfig
    issue_config: IssueConfig
    scope_config: ScopeConfig
    milestone_config: MilestoneConfig
    contributor_config: ContributorConfig
    artifact_registry: ArtifactRegistryConfig
    project_structure_config: ProjectStructureConfig
    operation_policies_config: OperationPoliciesConfig
    enforcement_config: EnforcementConfig
    contracts_config: ContractsConfig
    presentation_config: PresentationConfig


@dataclass(frozen=True)
class ManagerGraph:
    """Immutable graph of instantiated managers and services."""

    template_registry: TemplateRegistry
    git_manager: GitManager
    state_repository: FileStateRepository
    workflow_status_resolver: WorkflowStatusResolver
    project_manager: ProjectManager
    phase_contract_resolver: PhaseContractResolver
    workflow_gate_runner: WorkflowGateRunner
    workflow_state_mutator: WorkflowStateMutator
    context_loaded_cache: ContextLoadedCache
    phase_state_engine: PhaseStateEngine
    quality_state_repository: FileQualityStateRepository
    qa_manager: QAManager
    github_manager: GitHubManager
    artifact_manager: ArtifactManager
    pr_status_cache: PRStatusCache
    enforcement_runner: EnforcementRunner
    response_cache: IToolResponsePublisher | IToolResponseReader


class ServerBootstrapper:
    """Orchestrates configuration loading and manager graph instantiation."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize bootstrapper with settings."""
        self._settings = settings or Settings.from_env()

    def bootstrap(self) -> MCPServer:
        """Bootstrap logging, config, registry, and managers, and return MCPServer."""
        settings = self._settings

        # Configure logging
        _server_root_early = settings.server.resolved_server_root
        _logs_dir_early = _server_root_early / settings.server.logs_dir
        _audit_log = settings.logging.audit_log or str(_logs_dir_early / "mcp_audit.log")
        setup_logging(settings.logging.level, _audit_log)

        lifecycle_logger.info("MCP server starting via bootstrapper")

        # Validate workspace version
        self._validate_version()

        # Initialize template registry
        server_root = settings.server.resolved_server_root
        registry_path = server_root / "template_registry.json"

        if not registry_path.exists():
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            lifecycle_logger.info("Bootstrapping template registry: %s", registry_path)

        template_registry = TemplateRegistry(registry_path=registry_path)
        lifecycle_logger.info("Template registry initialized")

        # Build ConfigLayer
        configs = self._build_config_layer()

        # Build ManagerGraph
        managers = self._build_manager_graph(configs, template_registry)

        # Build Tools and Resources
        core_tools = self._build_tools(configs, managers)
        resources = self._build_resources(configs, managers)

        text_presenter = TextPresenter(config=configs.presentation_config)
        validate_presentation_alignment(text_presenter, core_tools)
        resource_presenter = ValidationResourcePresenter()
        presenter = ResponsePresenter(
            text_presenter=text_presenter,
            resource_presenter=resource_presenter,
        )

        # Decorate core tools using ToolFactory composition root
        factory = CoreToolFactory(
            enforcement_runner=managers.enforcement_runner,
            workspace_root=Path(settings.server.workspace_root),
        )
        tools = [factory.create_tool(t) for t in core_tools]

        return MCPServer(
            settings=settings,
            tools=tools,
            resources=resources,
            presenter=presenter,
            publisher=managers.response_cache,
        )

    def _validate_version(self) -> None:
        """Validate that the workspace version matches the running server version."""
        validator = WorkspaceVersionValidator()
        validator.validate(
            server_root=self._settings.server.resolved_server_root,
            expected_version=self._settings.server.version,
            bypass_version_check=self._settings.server.bypass_version_check,
        )

    def _build_config_layer(self) -> ConfigLayer:
        """Load and validate all configurations."""
        config_root = self._settings.server.resolved_config_root

        config_loader = ConfigLoader(
            config_root=config_root,
            template_root=self._settings.server.resolved_template_root,
        )
        git_config = config_loader.load_git_config()
        workflow_config = config_loader.load_workflow_config()
        workphases_config = config_loader.load_workphases_config()
        quality_config = config_loader.load_quality_config()
        label_config = config_loader.load_label_config()
        issue_config = config_loader.load_issue_config()
        scope_config = config_loader.load_scope_config()
        milestone_config = config_loader.load_milestone_config()
        contributor_config = config_loader.load_contributor_config()
        artifact_registry = config_loader.load_artifact_registry_config()
        project_structure_config = config_loader.load_project_structure_config(
            artifact_registry=artifact_registry
        )
        operation_policies_config = config_loader.load_operation_policies_config()
        enforcement_config = config_loader.load_enforcement_config()
        contracts_config = config_loader.load_contracts_config()
        presentation_config = config_loader.load_presentation_config()

        ConfigValidator().validate_startup(
            policies=operation_policies_config,
            workflow=workflow_config,
            structure=project_structure_config,
            artifact=artifact_registry,
            contracts=contracts_config,
            workphases=workphases_config,
        )

        return ConfigLayer(
            git_config=git_config,
            workflow_config=workflow_config,
            workphases_config=workphases_config,
            quality_config=quality_config,
            label_config=label_config,
            issue_config=issue_config,
            scope_config=scope_config,
            milestone_config=milestone_config,
            contributor_config=contributor_config,
            artifact_registry=artifact_registry,
            project_structure_config=project_structure_config,
            operation_policies_config=operation_policies_config,
            enforcement_config=enforcement_config,
            contracts_config=contracts_config,
            presentation_config=presentation_config,
        )

    def _build_manager_graph(
        self, configs: ConfigLayer, template_registry: TemplateRegistry
    ) -> ManagerGraph:
        """Instantiate all managers and services."""
        workspace_root = Path(self._settings.server.workspace_root)
        server_root = workspace_root / self._settings.server.server_root_dir
        logs_dir = server_root / self._settings.server.logs_dir

        git_manager = GitManager(
            git_config=configs.git_config,
            workphases_config=configs.workphases_config,
        )
        state_repository = FileStateRepository(state_file=server_root / "state.json")
        branch_validated_reader = BranchValidatedStateReader(inner=state_repository)
        commit_phase_detector = CommitPhaseDetector(
            workphases_config=configs.workphases_config,
        )
        workflow_status_resolver = WorkflowStatusResolver(
            git_context_reader=git_manager,
            state_reader=branch_validated_reader,
            commit_phase_detector=commit_phase_detector,
        )
        project_manager = ProjectManager(
            workspace_root=workspace_root,
            contracts_config=configs.contracts_config,
            git_manager=git_manager,
            workphases_config=configs.workphases_config,
            workflow_status_resolver=workflow_status_resolver,
            server_root=server_root,
        )
        phase_contract_resolver = PhaseContractResolver(
            PhaseConfigContext(
                workphases=configs.workphases_config,
                contracts=configs.contracts_config,
            )
        )
        workflow_gate_runner = WorkflowGateRunner(
            deliverable_checker=DeliverableChecker(workspace_root),
            phase_contract_resolver=phase_contract_resolver,
        )
        workflow_state_mutator = WorkflowStateMutator(
            state_repository=state_repository,
        )
        context_loaded_cache = ContextLoadedCache()
        phase_state_engine = PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=project_manager,
            git_config=configs.git_config,
            contracts_config=configs.contracts_config,
            state_repository=state_repository,
            scope_decoder=ScopeDecoder(
                workphases_config=configs.workphases_config,
            ),
            workflow_gate_runner=workflow_gate_runner,
            context_loaded_writer=context_loaded_cache,
            server_root=server_root,
        )
        quality_state_repository = FileQualityStateRepository(
            backing_file=server_root / "quality_state.json"
        )
        qa_manager = QAManager(
            workspace_root=workspace_root,
            quality_config=configs.quality_config,
            logs_dir=logs_dir,
            quality_state_repository=quality_state_repository,
            git_context_reader=git_manager,
            state_reader=branch_validated_reader,
        )
        github_manager = GitHubManager(
            issue_config=configs.issue_config,
            label_config=configs.label_config,
            scope_config=configs.scope_config,
            milestone_config=configs.milestone_config,
            contributor_config=configs.contributor_config,
            git_config=configs.git_config,
        )
        artifact_manager = ArtifactManager(
            workspace_root=workspace_root,
            server_root=server_root,
            template_registry=template_registry,
            registry=configs.artifact_registry,
            project_structure_config=configs.project_structure_config,
        )
        pr_status_cache = PRStatusCache(github_manager=github_manager)
        enforcement_runner = EnforcementRunner(
            workspace_root=workspace_root,
            config=configs.enforcement_config,
            git_config=configs.git_config,
            state_reader=state_repository,
            pr_status_reader=pr_status_cache,
            server_root=server_root,
            context_loaded_reader=context_loaded_cache,
        )
        response_cache = ResponseCacheManager(max_size=50)
        return ManagerGraph(
            template_registry=template_registry,
            git_manager=git_manager,
            state_repository=state_repository,
            workflow_status_resolver=workflow_status_resolver,
            project_manager=project_manager,
            phase_contract_resolver=phase_contract_resolver,
            workflow_gate_runner=workflow_gate_runner,
            workflow_state_mutator=workflow_state_mutator,
            context_loaded_cache=context_loaded_cache,
            phase_state_engine=phase_state_engine,
            quality_state_repository=quality_state_repository,
            qa_manager=qa_manager,
            github_manager=github_manager,
            artifact_manager=artifact_manager,
            pr_status_cache=pr_status_cache,
            enforcement_runner=enforcement_runner,
            response_cache=response_cache,
        )

    def _build_tools(self, configs: ConfigLayer, managers: ManagerGraph) -> list[Any]:
        """Compose the list of available tools."""
        settings = self._settings

        _branch_validated_reader = BranchValidatedStateReader(inner=managers.state_repository)

        tools: list[Any] = [
            # Git tools
            CreateBranchTool(manager=managers.git_manager),
            GitStatusTool(manager=managers.git_manager),
            GitCommitTool(
                manager=managers.git_manager,
                phase_guard=build_phase_guard(
                    state_reader=_branch_validated_reader,
                    phase_contract_resolver=managers.phase_contract_resolver,
                ),
                commit_type_resolver=build_commit_type_resolver(
                    managers.phase_state_engine,
                    managers.phase_contract_resolver,
                ),
                state_engine=managers.phase_state_engine,
                phase_contract_resolver=managers.phase_contract_resolver,
            ),
            GitCheckoutTool(
                manager=managers.git_manager,
                state_engine=managers.phase_state_engine,
                context_loaded_writer=managers.context_loaded_cache,
            ),
            GitFetchTool(manager=managers.git_manager),
            GitPullTool(
                manager=managers.git_manager,
                state_engine=managers.phase_state_engine,
                context_loaded_writer=managers.context_loaded_cache,
            ),
            GitPushTool(manager=managers.git_manager),
            GitMergeTool(manager=managers.git_manager),
            GitDeleteBranchTool(manager=managers.git_manager),
            GitStashTool(manager=managers.git_manager),
            GitRestoreTool(manager=managers.git_manager),
            GitListBranchesTool(manager=managers.git_manager),
            GitDiffTool(manager=managers.git_manager),
            GetParentBranchTool(
                manager=managers.git_manager, state_engine=managers.phase_state_engine
            ),
            CheckMergeTool(manager=managers.git_manager),
            # Quality tools
            RunQualityGatesTool(manager=managers.qa_manager),
            SafeEditTool(),
            TemplateValidationTool(),
            # Development tools
            HealthCheckTool(),
            RestartServerTool(
                server_root=Path(settings.server.workspace_root) / settings.server.server_root_dir
            ),
            RunTestsTool(runner=PytestRunner(), settings=settings),
            # Project tools (Phase 0.5)
            InitializeProjectTool(
                workspace_root=Path(settings.server.workspace_root),
                manager=managers.project_manager,
                git_manager=managers.git_manager,
                state_engine=managers.phase_state_engine,
                contracts_config=configs.contracts_config,
            ),
            GetProjectPlanTool(manager=managers.project_manager),
            SavePlanningDeliverablesTool(manager=managers.project_manager),
            UpdatePlanningDeliverablesTool(manager=managers.project_manager),
            # Phase tools (Phase B)
            TransitionPhaseTool(
                workspace_root=Path(settings.server.workspace_root),
                project_manager=managers.project_manager,
                state_engine=managers.phase_state_engine,
                server_root=Path(settings.server.workspace_root) / settings.server.server_root_dir,
                workphases_config=configs.workphases_config,
            ),
            ForcePhaseTransitionTool(
                workspace_root=Path(settings.server.workspace_root),
                project_manager=managers.project_manager,
                state_engine=managers.phase_state_engine,
                server_root=Path(settings.server.workspace_root) / settings.server.server_root_dir,
                workphases_config=configs.workphases_config,
            ),
            # TDD Cycle tools (Issue #146)
            TransitionCycleTool(
                workspace_root=Path(settings.server.workspace_root),
                project_manager=managers.project_manager,
                state_engine=managers.phase_state_engine,
                git_manager=managers.git_manager,
                gate_runner=managers.workflow_gate_runner,
                server_root=Path(settings.server.workspace_root) / settings.server.server_root_dir,
            ),
            ForceCycleTransitionTool(
                workspace_root=Path(settings.server.workspace_root),
                project_manager=managers.project_manager,
                state_engine=managers.phase_state_engine,
                git_manager=managers.git_manager,
                gate_runner=managers.workflow_gate_runner,
                server_root=Path(settings.server.workspace_root) / settings.server.server_root_dir,
            ),
            # Scaffold tools (unified artifact scaffolding)
            ScaffoldArtifactTool(manager=managers.artifact_manager),
            ScaffoldSchemaTool(manager=managers.artifact_manager),
            # Discovery tools
            GetWorkContextTool(
                settings=settings,
                git_manager=managers.git_manager,
                project_manager=managers.project_manager,
                state_engine=managers.phase_state_engine,
                github_manager=managers.github_manager,
                workphases_config=configs.workphases_config,
                workflow_status_resolver=managers.workflow_status_resolver,
                contracts_config=configs.contracts_config,
                context_loaded_writer=managers.context_loaded_cache,
            ),
        ]

        if settings.github.token:
            _merge_readiness_context = MergeReadinessContext(
                terminal_phase=configs.workphases_config.get_terminal_phase(),
                pr_allowed_phase=configs.contracts_config.get_pr_allowed_phase(),
                branch_local_artifacts=tuple(
                    configs.contracts_config.merge_policy.branch_local_artifacts
                ),
            )
            tools.extend(
                [
                    # GitHub Issue tools
                    CreateIssueTool(
                        manager=managers.github_manager,
                        issue_config=configs.issue_config,
                        milestone_config=configs.milestone_config,
                        contracts_config=configs.contracts_config,
                        label_config=configs.label_config,
                        scope_config=configs.scope_config,
                        git_config=configs.git_config,
                    ),
                    ListIssuesTool(manager=managers.github_manager),
                    GetIssueTool(manager=managers.github_manager),
                    CloseIssueTool(manager=managers.github_manager),
                    UpdateIssueTool(manager=managers.github_manager),
                    # PR and Label tools (require token at init time)
                    ListPRsTool(manager=managers.github_manager, git_config=configs.git_config),
                    GetPRTool(manager=managers.github_manager),
                    MergePRTool(
                        manager=managers.github_manager,
                        git_config=configs.git_config,
                        pr_status_writer=managers.pr_status_cache,
                    ),
                    SubmitPRTool(
                        git_manager=managers.git_manager,
                        github_manager=managers.github_manager,
                        pr_status_writer=managers.pr_status_cache,
                        merge_readiness_context=_merge_readiness_context,
                        branch_parent_reader=BranchStateParentReader(
                            state_reader=managers.state_repository,
                            git_config=configs.git_config,
                        ),
                    ),
                    AddLabelsTool(
                        manager=managers.github_manager,
                        label_config=configs.label_config,
                        workphases_config=configs.workphases_config,
                    ),
                    ListLabelsTool(
                        manager=managers.github_manager, label_config=configs.label_config
                    ),
                    CreateLabelTool(
                        manager=managers.github_manager,
                        label_config=configs.label_config,
                        workphases_config=configs.workphases_config,
                    ),
                    DeleteLabelTool(
                        manager=managers.github_manager, label_config=configs.label_config
                    ),
                    RemoveLabelsTool(
                        manager=managers.github_manager, label_config=configs.label_config
                    ),
                    ListMilestonesTool(manager=managers.github_manager),
                    CreateMilestoneTool(manager=managers.github_manager),
                    CloseMilestoneTool(manager=managers.github_manager),
                ]
            )
        else:
            tools.extend(
                [
                    CreateIssueTool(
                        manager=managers.github_manager,
                        issue_config=configs.issue_config,
                        milestone_config=configs.milestone_config,
                        contracts_config=configs.contracts_config,
                        label_config=configs.label_config,
                        scope_config=configs.scope_config,
                        git_config=configs.git_config,
                    ),
                    ListIssuesTool(manager=managers.github_manager),
                    GetIssueTool(manager=managers.github_manager),
                    CloseIssueTool(manager=managers.github_manager),
                    UpdateIssueTool(manager=managers.github_manager),
                ]
            )

        tools.append(AutoFixTool(qa_manager=managers.qa_manager))
        return tools

    def _build_resources(
        self,
        configs: ConfigLayer,  # noqa: ARG002
        managers: ManagerGraph,  # noqa: ARG002
    ) -> list[BaseResource]:
        """Compose the list of available resources."""
        resources: list[BaseResource] = []
        resources.append(StandardsResource())
        resources.append(StatusResource())
        resources.append(CachedResponseResource(cache=managers.response_cache))

        if self._settings.github.token:
            resources.append(GitHubIssuesResource())

        return resources
