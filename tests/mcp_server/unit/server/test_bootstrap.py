# tests\mcp_server\unit\server\test_bootstrap.py
# template=unit_test version=3d15d309 created=2026-06-09T09:48Z updated=2026-08-19T19:50Z
"""Unit tests for mcp_server.bootstrap.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.bootstrap, unittest.mock]
@responsibilities:
    - Test TestBootstrap functionality
    - Verify immutability of ConfigLayer and ManagerGraph
    - Test ServerBootstrapper config loading and manager creation
"""

import dataclasses
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from mcp_server.bootstrap import (
    ConfigLayer,
    ManagerGraph,
    ServerBootstrapper,
    SupportedToolContract,
    ToolAssembly,
)
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
from mcp_server.core.exceptions import ConfigError
from mcp_server.core.interfaces import ICoreTool, IToolResponsePublisher
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.managers.enforcement_runner import EnforcementRunner
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.managers.phase_contract_resolver import PhaseContractResolver
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.qa_manager import QAManager
from mcp_server.managers.quality_state_repository import FileQualityStateRepository
from mcp_server.managers.state_repository import FileStateRepository
from mcp_server.managers.workflow_gate_runner import WorkflowGateRunner
from mcp_server.managers.workflow_state_mutator import WorkflowStateMutator
from mcp_server.managers.workflow_status_resolver import WorkflowStatusResolver
from mcp_server.scaffolding.template_registry import TemplateRegistry
from mcp_server.server import MCPServer
from mcp_server.state.context_loaded_cache import ContextLoadedCache
from mcp_server.state.pr_status_cache import PRStatusCache
from tests.mcp_server.test_support import get_default_server_root



class _AssemblyInput(BaseModel):
    """Synthetic core-tool input for assembly contract tests."""


class _AssemblyOutput(BaseModel):
    """Synthetic core-tool output for assembly contract tests."""


class _AlternativeAssemblyOutput(BaseModel):
    """Conflicting synthetic output model."""


class _GenericAssemblyTool(ICoreTool[_AssemblyInput, _AssemblyOutput]):
    """Concrete generic specialization without explicit output_model metadata."""

    def __init__(self, name: str = "generic_tool") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Synthetic assembly tool"

    @property
    def args_model(self) -> type[BaseModel]:
        return _AssemblyInput

    async def execute(
        self, params: _AssemblyInput, context: NoteContext
    ) -> _AssemblyOutput:
        del params, context
        return _AssemblyOutput()


class _ConflictingAssemblyTool(_GenericAssemblyTool):
    """Tool whose explicit output metadata conflicts with its generic contract."""

    output_model = _AlternativeAssemblyOutput


class _UnresolvedAssemblyTool:
    """Tool-shaped object without output-model metadata."""

    name = "unresolved_tool"


class TestToolAssembly:
    """Durable public-contract tests for supported and active tool assembly."""

    def test_derives_frozen_supported_contracts_from_generic_specialization(self) -> None:
        tool = _GenericAssemblyTool()

        assembly = ToolAssembly.create(
            supported_tools=(tool,),
            active_tools=(tool,),
        )

        assert assembly.supported_contracts == (
            SupportedToolContract(name="generic_tool", output_model=_AssemblyOutput),
        )
        assert assembly.supported_tools == (tool,)
        assert assembly.active_tools == (tool,)
        with pytest.raises(dataclasses.FrozenInstanceError):
            assembly.active_tools = ()  # type: ignore[misc]

    @pytest.mark.parametrize(
        ("supported_tools", "expected_message"),
        [
            ((_GenericAssemblyTool(""),), "non-empty"),
            (
                (
                    _GenericAssemblyTool("duplicate"),
                    _GenericAssemblyTool("duplicate"),
                ),
                "duplicate",
            ),
            ((_UnresolvedAssemblyTool(),), "output model"),
            ((_ConflictingAssemblyTool(),), "conflicting"),
        ],
    )
    def test_rejects_invalid_supported_contracts(
        self,
        supported_tools: tuple[object, ...],
        expected_message: str,
    ) -> None:
        with pytest.raises(ConfigError, match=expected_message):
            ToolAssembly.create(
                supported_tools=supported_tools,
                active_tools=(),
            )

    def test_rejects_active_tool_outside_supported_object_set(self) -> None:
        supported = _GenericAssemblyTool("supported")
        unrelated = _GenericAssemblyTool("unrelated")

        with pytest.raises(ConfigError, match="active"):
            ToolAssembly.create(
                supported_tools=(supported,),
                active_tools=(unrelated,),
            )

class TestBootstrap:
    """Test suite for bootstrap containers."""

    def test_config_layer_immutability(self) -> None:
        """Verify ConfigLayer is frozen and raises FrozenInstanceError on modification."""
        mock_configs = {
            "git_config": MagicMock(spec=GitConfig),
            "workflow_config": MagicMock(spec=WorkflowConfig),
            "workphases_config": MagicMock(spec=WorkphasesConfig),
            "quality_config": MagicMock(spec=QualityConfig),
            "label_config": MagicMock(spec=LabelConfig),
            "issue_config": MagicMock(spec=IssueConfig),
            "scope_config": MagicMock(spec=ScopeConfig),
            "milestone_config": MagicMock(spec=MilestoneConfig),
            "contributor_config": MagicMock(spec=ContributorConfig),
            "artifact_registry": MagicMock(spec=ArtifactRegistryConfig),
            "project_structure_config": MagicMock(spec=ProjectStructureConfig),
            "operation_policies_config": MagicMock(spec=OperationPoliciesConfig),
            "enforcement_config": MagicMock(spec=EnforcementConfig),
            "contracts_config": MagicMock(spec=ContractsConfig),
            "presentation_config": MagicMock(spec=PresentationConfig),
        }
        layer = ConfigLayer(**mock_configs)

        # Assert all fields are set
        for k, v in mock_configs.items():
            assert getattr(layer, k) is v

        # Assert mutation raises FrozenInstanceError
        with pytest.raises(dataclasses.FrozenInstanceError):
            layer.git_config = MagicMock(spec=GitConfig)

    def test_manager_graph_immutability(self) -> None:
        """Verify ManagerGraph is frozen and raises FrozenInstanceError on modification."""
        mock_managers = {
            "template_registry": MagicMock(spec=TemplateRegistry),
            "git_manager": MagicMock(spec=GitManager),
            "state_repository": MagicMock(spec=FileStateRepository),
            "workflow_status_resolver": MagicMock(spec=WorkflowStatusResolver),
            "project_manager": MagicMock(spec=ProjectManager),
            "phase_contract_resolver": MagicMock(spec=PhaseContractResolver),
            "workflow_gate_runner": MagicMock(spec=WorkflowGateRunner),
            "workflow_state_mutator": MagicMock(spec=WorkflowStateMutator),
            "context_loaded_cache": MagicMock(spec=ContextLoadedCache),
            "phase_state_engine": MagicMock(spec=PhaseStateEngine),
            "quality_state_repository": MagicMock(spec=FileQualityStateRepository),
            "qa_manager": MagicMock(spec=QAManager),
            "github_manager": MagicMock(spec=GitHubManager),
            "artifact_manager": MagicMock(spec=ArtifactManager),
            "pr_status_cache": MagicMock(spec=PRStatusCache),
            "enforcement_runner": MagicMock(spec=EnforcementRunner),
            "response_cache": MagicMock(spec=IToolResponsePublisher),
        }
        graph = ManagerGraph(**mock_managers)

        # Assert all fields are set
        for k, v in mock_managers.items():
            assert getattr(graph, k) is v

        # Assert mutation raises FrozenInstanceError
        with pytest.raises(dataclasses.FrozenInstanceError):
            graph.git_manager = MagicMock(spec=GitManager)


def _setup_mock_config_loader(mock_config_loader_cls: MagicMock) -> MagicMock:
    """Helper to mock all configurations returned by ConfigLoader."""
    mock_loader = mock_config_loader_cls.return_value
    mock_loader.load_git_config.return_value = MagicMock(spec=GitConfig)
    mock_loader.load_workflow_config.return_value = MagicMock(spec=WorkflowConfig)

    mock_workphases = MagicMock(spec=WorkphasesConfig)
    mock_workphases.get_terminal_phase.return_value = "ready"
    mock_loader.load_workphases_config.return_value = mock_workphases

    mock_loader.load_quality_config.return_value = MagicMock(spec=QualityConfig)
    mock_loader.load_label_config.return_value = MagicMock(spec=LabelConfig)
    mock_loader.load_issue_config.return_value = MagicMock(spec=IssueConfig)
    mock_loader.load_scope_config.return_value = MagicMock(spec=ScopeConfig)
    mock_loader.load_milestone_config.return_value = MagicMock(spec=MilestoneConfig)
    mock_loader.load_contributor_config.return_value = MagicMock(spec=ContributorConfig)
    mock_loader.load_artifact_registry_config.return_value = MagicMock(spec=ArtifactRegistryConfig)
    mock_loader.load_project_structure_config.return_value = MagicMock(spec=ProjectStructureConfig)
    mock_loader.load_operation_policies_config.return_value = MagicMock(
        spec=OperationPoliciesConfig
    )

    mock_enforcement = MagicMock(spec=EnforcementConfig)
    mock_enforcement.enforcement = []
    mock_enforcement.categories = {}
    mock_loader.load_enforcement_config.return_value = mock_enforcement

    mock_contracts = MagicMock(spec=ContractsConfig)
    mock_contracts.get_pr_allowed_phase.return_value = "ready"
    mock_contracts.merge_policy = MagicMock()
    mock_contracts.merge_policy.branch_local_artifacts = []
    mock_loader.load_contracts_config.return_value = mock_contracts
    mock_pres = PresentationConfig.model_validate({"global": {}, "tools": {}})
    mock_loader.load_presentation_config.return_value = mock_pres
    return mock_loader


class TestServerBootstrapperConfigsAndManagers:
    """Test suite for ServerBootstrapper config loading and manager creation."""

    def test_bootstrapper_initialization(self) -> None:
        """Verify ServerBootstrapper stores settings during initialization."""
        # We verify this via public bootstrap() side-effect of passing settings to MCPServer
        mock_settings = MagicMock()
        mock_settings.github.token = None
        mock_settings.server.name = "test-server"
        mock_settings.server.workspace_root = "/fake/root"
        mock_settings.server.server_root_dir = get_default_server_root()
        mock_settings.server.logs_dir = "logs"
        mock_settings.logging.level = "WARNING"
        mock_settings.logging.audit_log = "/fake/root/.pgmcp/logs/mcp_audit.log"
        with (
            patch("mcp_server.bootstrap.setup_logging"),
            patch("mcp_server.bootstrap.TemplateRegistry"),
            patch("mcp_server.bootstrap.ConfigLoader") as mock_config_loader_cls,
            patch("mcp_server.bootstrap.ConfigValidator"),
            patch("mcp_server.bootstrap.MCPServer") as mock_mcp_server_cls,
        ):
            _setup_mock_config_loader(mock_config_loader_cls)

            bootstrapper = ServerBootstrapper(mock_settings)
            bootstrapper.bootstrap()

            call_kwargs = mock_mcp_server_cls.call_args[1]
            assert call_kwargs["settings"] is mock_settings

    def test_bootstrapper_bootstrap_returns_mcpserver(self) -> None:
        """Verify bootstrap() returns an MCPServer with all managers wired."""
        mock_settings = MagicMock()
        mock_settings.github.token = None
        mock_settings.server.name = "test-server"
        mock_settings.server.workspace_root = "/fake/root"
        mock_settings.server.server_root_dir = get_default_server_root()
        mock_settings.server.logs_dir = "logs"
        mock_settings.logging.level = "WARNING"
        mock_settings.logging.audit_log = "/fake/root/.pgmcp/logs/mcp_audit.log"

        with (
            patch("mcp_server.bootstrap.setup_logging") as mock_setup_logging,
            patch("mcp_server.bootstrap.TemplateRegistry") as mock_template_registry_cls,
            patch("mcp_server.bootstrap.ConfigLoader") as mock_config_loader_cls,
            patch("mcp_server.bootstrap.ConfigValidator") as mock_config_validator_cls,
            patch("mcp_server.bootstrap.MCPServer") as mock_mcp_server_cls,
        ):
            _setup_mock_config_loader(mock_config_loader_cls)

            bootstrapper = ServerBootstrapper(mock_settings)
            server = bootstrapper.bootstrap()

            # Verify side-effects
            mock_setup_logging.assert_called_once()
            mock_template_registry_cls.assert_called_once()
            mock_config_validator_cls.return_value.validate_startup.assert_called_once()

            # Verify MCPServer was created with injected dependencies
            assert mock_mcp_server_cls.called
            call_kwargs = mock_mcp_server_cls.call_args[1]
            assert call_kwargs["settings"] is mock_settings
            assert isinstance(call_kwargs["tools"], list)
            assert isinstance(call_kwargs["resources"], list)
            assert "presenter" in call_kwargs
            assert "publisher" in call_kwargs
            assert server is mock_mcp_server_cls.return_value

    def test_bootstrap_missing_version_raises_config_error(self) -> None:
        """Verify bootstrap() raises ConfigError if version file is missing."""
        mock_settings = MagicMock()
        mock_settings.server.bypass_version_check = False
        mock_settings.server.resolved_server_root = Path("/fake/root")
        mock_settings.logging.level = "WARNING"
        mock_settings.logging.audit_log = "/fake/root/.pgmcp/logs/mcp_audit.log"

        with (
            patch("mcp_server.bootstrap.setup_logging"),
            pytest.raises(ConfigError) as exc_info,
        ):
            bootstrapper = ServerBootstrapper(mock_settings)
            bootstrapper.bootstrap()

        assert "version tracking file is missing" in str(exc_info.value)

    def test_bootstrap_version_mismatch_raises_config_error(self, tmp_path: Path) -> None:
        """Verify bootstrap() raises ConfigError if workspace version mismatches."""
        mock_settings = MagicMock()
        mock_settings.server.bypass_version_check = False
        mock_settings.server.resolved_server_root = tmp_path
        mock_settings.server.version = "1.0.0"
        mock_settings.logging.level = "WARNING"
        mock_settings.logging.audit_log = str(tmp_path / "audit.log")

        # Write incorrect version to file
        version_file = tmp_path / ".version"
        version_file.write_text("9.9.9\n", encoding="utf-8")

        with (
            patch("mcp_server.bootstrap.setup_logging"),
            pytest.raises(ConfigError) as exc_info,
        ):
            bootstrapper = ServerBootstrapper(mock_settings)
            bootstrapper.bootstrap()

        assert "Workspace version mismatch" in str(exc_info.value)

    def test_bootstrap_version_match_success(self, tmp_path: Path) -> None:
        """Verify bootstrap() succeeds if version matches."""
        mock_settings = MagicMock()
        mock_settings.server.bypass_version_check = False
        mock_settings.server.resolved_server_root = tmp_path
        mock_settings.server.version = "1.0.0"
        mock_settings.logging.level = "WARNING"
        mock_settings.logging.audit_log = str(tmp_path / "audit.log")

        # Write matching version
        version_file = tmp_path / ".version"
        version_file.write_text("1.0.0\n", encoding="utf-8")

        with (
            patch("mcp_server.bootstrap.setup_logging"),
            patch("mcp_server.bootstrap.TemplateRegistry"),
            patch("mcp_server.bootstrap.ConfigLoader") as mock_config_loader_cls,
            patch("mcp_server.bootstrap.ConfigValidator"),
            patch("mcp_server.bootstrap.MCPServer") as mock_mcp_server_cls,
        ):
            _setup_mock_config_loader(mock_config_loader_cls)
            bootstrapper = ServerBootstrapper(mock_settings)
            server = bootstrapper.bootstrap()
            assert server is mock_mcp_server_cls.return_value

    def test_bootstrap_bypass_skips_validation(self) -> None:
        """Verify bootstrap() skips validation if bypass_version_check is True."""
        mock_settings = MagicMock()
        mock_settings.server.bypass_version_check = True
        mock_settings.server.resolved_server_root = Path("/fake/root")
        mock_settings.logging.level = "WARNING"
        mock_settings.logging.audit_log = "/fake/root/.pgmcp/logs/mcp_audit.log"

        with (
            patch("mcp_server.bootstrap.setup_logging"),
            patch("mcp_server.bootstrap.TemplateRegistry"),
            patch("mcp_server.bootstrap.ConfigLoader") as mock_config_loader_cls,
            patch("mcp_server.bootstrap.ConfigValidator"),
            patch("mcp_server.bootstrap.MCPServer") as mock_mcp_server_cls,
        ):
            _setup_mock_config_loader(mock_config_loader_cls)
            bootstrapper = ServerBootstrapper(mock_settings)
            server = bootstrapper.bootstrap()
            assert server is mock_mcp_server_cls.return_value


class TestServerBootstrapperToolsAndResources:
    """Test suite for ServerBootstrapper tool and resource extraction."""

    def test_build_tools_without_github_token(self) -> None:
        """Verify bootstrap returns MCPServer with only non-GitHub tools when token is None."""
        mock_settings = MagicMock()
        mock_settings.github.token = None
        mock_settings.server.name = "test-server"
        mock_settings.server.workspace_root = "/fake/root"
        mock_settings.server.server_root_dir = get_default_server_root()
        mock_settings.server.logs_dir = "logs"
        mock_settings.logging.level = "WARNING"
        mock_settings.logging.audit_log = "/fake/root/.pgmcp/logs/mcp_audit.log"

        with (
            patch("mcp_server.bootstrap.setup_logging"),
            patch("mcp_server.bootstrap.TemplateRegistry"),
            patch("mcp_server.bootstrap.ConfigLoader") as mock_config_loader_cls,
            patch("mcp_server.bootstrap.ConfigValidator"),
        ):
            _setup_mock_config_loader(mock_config_loader_cls)

            bootstrapper = ServerBootstrapper(mock_settings)
            server = bootstrapper.bootstrap()
            tool_names = {t.name for t in server.tools}
            assert "create_issue" in tool_names
            assert "get_pr" not in tool_names
            assert "git_status" in tool_names

    def test_build_tools_with_github_token(self) -> None:
        """Verify bootstrap returns GitHub tools when token is present."""
        mock_settings = MagicMock()
        mock_settings.github.token = "token"
        mock_settings.server.name = "test-server"
        mock_settings.server.workspace_root = "/fake/root"
        mock_settings.server.server_root_dir = get_default_server_root()
        mock_settings.server.logs_dir = "logs"
        mock_settings.logging.level = "WARNING"
        mock_settings.logging.audit_log = "/fake/root/.pgmcp/logs/mcp_audit.log"

        with (
            patch("mcp_server.bootstrap.setup_logging"),
            patch("mcp_server.bootstrap.TemplateRegistry"),
            patch("mcp_server.bootstrap.ConfigLoader") as mock_config_loader_cls,
            patch("mcp_server.bootstrap.ConfigValidator"),
        ):
            _setup_mock_config_loader(mock_config_loader_cls)

            bootstrapper = ServerBootstrapper(mock_settings)
            server = bootstrapper.bootstrap()
            tool_names = {t.name for t in server.tools}
            assert "create_issue" in tool_names
            assert "get_pr" in tool_names

    def test_build_resources_without_github_token(self) -> None:
        """Verify bootstrap returns only core resources when token is None."""
        mock_settings = MagicMock()
        mock_settings.github.token = None
        mock_settings.server.name = "test-server"
        mock_settings.server.workspace_root = "/fake/root"
        mock_settings.server.server_root_dir = get_default_server_root()
        mock_settings.server.logs_dir = "logs"
        mock_settings.logging.level = "WARNING"
        mock_settings.logging.audit_log = "/fake/root/.pgmcp/logs/mcp_audit.log"

        with (
            patch("mcp_server.bootstrap.setup_logging"),
            patch("mcp_server.bootstrap.TemplateRegistry"),
            patch("mcp_server.bootstrap.ConfigLoader") as mock_config_loader_cls,
            patch("mcp_server.bootstrap.ConfigValidator"),
        ):
            _setup_mock_config_loader(mock_config_loader_cls)

            bootstrapper = ServerBootstrapper(mock_settings)
            server = bootstrapper.bootstrap()
            resource_uris = {r.uri_pattern for r in server.resources}
            assert "pgmcp://rules/coding_standards" in resource_uris
            assert "pgmcp://github/issues" not in resource_uris

    def test_build_resources_with_github_token(self) -> None:
        """Verify bootstrap returns GitHub issues resource when token is present."""
        mock_settings = MagicMock()
        mock_settings.github.token = "token"
        mock_settings.server.name = "test-server"
        mock_settings.server.workspace_root = "/fake/root"
        mock_settings.server.server_root_dir = get_default_server_root()
        mock_settings.server.logs_dir = "logs"
        mock_settings.logging.level = "WARNING"
        mock_settings.logging.audit_log = "/fake/root/.pgmcp/logs/mcp_audit.log"

        with (
            patch("mcp_server.bootstrap.setup_logging"),
            patch("mcp_server.bootstrap.TemplateRegistry"),
            patch("mcp_server.bootstrap.ConfigLoader") as mock_config_loader_cls,
            patch("mcp_server.bootstrap.ConfigValidator"),
        ):
            _setup_mock_config_loader(mock_config_loader_cls)

            bootstrapper = ServerBootstrapper(mock_settings)
            server = bootstrapper.bootstrap()
            resource_uris = {r.uri_pattern for r in server.resources}
            assert "pgmcp://rules/coding_standards" in resource_uris
            assert "pgmcp://github/issues" in resource_uris


class TestMCPServerBootstrap:
    """Test suite for MCPServer dependency injection requirements."""

    def test_mcp_server_requires_injected_dependencies(self) -> None:
        """Verify that MCPServer raises TypeError when initialized without dependencies."""
        mock_settings = MagicMock()
        # Once the fallback code is deleted, this must raise a TypeError
        # (missing required arguments)
        with pytest.raises(TypeError):
            MCPServer(settings=mock_settings)  # type: ignore[call-arg]

    def test_mcp_server_accepts_injected_dependencies(self) -> None:
        """Verify MCPServer successfully initializes with all dependencies injected."""
        mock_settings = MagicMock()
        mock_tools = []
        mock_resources = []

        server = MCPServer(
            settings=mock_settings,
            tools=mock_tools,
            resources=mock_resources,
        )
        assert server._settings is mock_settings  # pyright: ignore[reportPrivateUsage]  # unavoidable test-infrastructure necessity to verify the constructor stores the settings dependency
        assert server.tools is mock_tools
        assert server.resources is mock_resources

    def test_make_test_server_creates_valid_server(self) -> None:
        """Verify make_test_server helper creates a valid MCPServer instance."""
        from tests.mcp_server.test_support import make_test_server  # noqa: PLC0415

        server = make_test_server()
        assert isinstance(server, MCPServer)
        assert server.tools is not None
        assert server.resources is not None
