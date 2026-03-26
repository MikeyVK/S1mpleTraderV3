# pyright: reportMissingImports=false
"""MCP Server Entrypoint."""

import asyncio
import json
import sys
import time
import uuid
from io import TextIOWrapper
from pathlib import Path
from typing import Any, cast

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    Resource,
    TextContent,
    Tool,
)
from pydantic import AnyUrl, BaseModel, ValidationError

# Config
from mcp_server.config.loader import ConfigLoader, resolve_config_root
from mcp_server.config.settings import Settings
from mcp_server.config.validator import ConfigValidator
from mcp_server.core.exceptions import MCPError
from mcp_server.core.logging import get_logger, setup_logging
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.managers.enforcement_runner import EnforcementContext, EnforcementRunner
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.managers.phase_contract_resolver import PhaseConfigContext, PhaseContractResolver
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.qa_manager import QAManager
from mcp_server.resources.github import GitHubIssuesResource

# Resources
from mcp_server.resources.standards import StandardsResource
from mcp_server.resources.status import StatusResource

# Scaffolding infrastructure (Issue #72)
from mcp_server.scaffolding.template_registry import TemplateRegistry
from mcp_server.tools.admin_tools import RestartServerTool
from mcp_server.tools.base import BaseTool
from mcp_server.tools.code_tools import CreateFileTool
from mcp_server.tools.cycle_tools import ForceCycleTransitionTool, TransitionCycleTool
from mcp_server.tools.discovery_tools import GetWorkContextTool, SearchDocumentationTool
from mcp_server.tools.git_analysis_tools import GitDiffTool, GitListBranchesTool
from mcp_server.tools.git_fetch_tool import GitFetchTool
from mcp_server.tools.git_pull_tool import GitPullTool
from mcp_server.tools.git_tools import (
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

# Tools
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
from mcp_server.tools.pr_tools import CreatePRTool, ListPRsTool, MergePRTool
from mcp_server.tools.project_tools import (
    GetProjectPlanTool,
    InitializeProjectTool,
    SavePlanningDeliverablesTool,
    UpdatePlanningDeliverablesTool,
)
from mcp_server.tools.quality_tools import RunQualityGatesTool
from mcp_server.tools.safe_edit_tool import SafeEditTool
from mcp_server.tools.scaffold_artifact import ScaffoldArtifactTool
from mcp_server.tools.template_validation_tool import TemplateValidationTool
from mcp_server.tools.test_tools import RunTestsTool
from mcp_server.tools.tool_result import ToolResult
from mcp_server.tools.validation_tools import ValidateDTOTool, ValidationTool

logger = get_logger("server")
lifecycle_logger = get_logger("server_lifecycle")


class MCPServer:
    """Main MCP server class that handles resources and tools."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the MCP server with resources and tools."""
        settings = settings or Settings.from_env()
        self._settings = settings
        server_name = settings.server.name

        # Configure logging with values from settings
        setup_logging(settings.logging.level, settings.logging.audit_log)

        # Log server startup
        lifecycle_logger.info("MCP server starting")

        # Initialize template registry (Issue #72 Task 1.6)
        workspace_root = Path(settings.server.workspace_root)
        self._workspace_root = workspace_root
        registry_path = workspace_root / ".st3" / "template_registry.json"

        # Bootstrap registry file if missing
        if not registry_path.exists():
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            lifecycle_logger.info("Bootstrapping template registry: %s", registry_path)

        self.template_registry = TemplateRegistry(registry_path=registry_path)
        lifecycle_logger.info("Template registry initialized")

        explicit_config_root = settings.server.config_root
        if explicit_config_root is not None and not str(explicit_config_root).strip():
            explicit_config_root = None

        config_root = resolve_config_root(
            preferred_root=workspace_root,
            explicit_root=explicit_config_root,
            required_files=("git.yaml", "workflows.yaml", "workphases.yaml"),
        )

        config_loader = ConfigLoader(config_root=config_root)
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
        operation_policies_config = config_loader.load_operation_policies_config(
            workflow_config=workflow_config
        )
        enforcement_config = config_loader.load_enforcement_config()
        phase_contracts_config = config_loader.load_phase_contracts_config()
        ConfigValidator().validate_startup(
            policies=operation_policies_config,
            workflow=workflow_config,
            structure=project_structure_config,
            artifact=artifact_registry,
            phase_contracts=phase_contracts_config,
            workphases=workphases_config,
        )

        self.git_manager = GitManager(git_config=git_config)
        self.project_manager = ProjectManager(
            workspace_root=workspace_root,
            workflow_config=workflow_config,
            git_manager=self.git_manager,
        )
        self.phase_state_engine = PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=self.project_manager,
            git_config=git_config,
            workflow_config=workflow_config,
            workphases_config=workphases_config,
        )
        self.qa_manager = QAManager(
            workspace_root=workspace_root,
            quality_config=quality_config,
        )
        self.github_manager = GitHubManager(
            issue_config=issue_config,
            label_config=label_config,
            scope_config=scope_config,
            milestone_config=milestone_config,
            contributor_config=contributor_config,
            git_config=git_config,
        )
        self.artifact_manager = ArtifactManager(
            workspace_root=workspace_root,
            template_registry=self.template_registry,
            registry=artifact_registry,
            project_structure_config=project_structure_config,
        )
        self.phase_contract_resolver = PhaseContractResolver(
            PhaseConfigContext(
                workphases=workphases_config,
                phase_contracts=phase_contracts_config,
            )
        )
        self.enforcement_runner = EnforcementRunner(
            workspace_root=workspace_root,
            config=enforcement_config,
            git_manager=self.git_manager,
            project_manager=self.project_manager,
            state_engine=self.phase_state_engine,
        )

        self.server = Server(server_name)

        # Core resources (always available)
        self.resources = [
            StandardsResource(),
            StatusResource(),
        ]

        # Core tools (always available)
        self.tools = [
            # Git tools
            CreateBranchTool(manager=self.git_manager),
            GitStatusTool(manager=self.git_manager),
            GitCommitTool(
                manager=self.git_manager,
                phase_guard=build_phase_guard(Path(settings.server.workspace_root)),
                commit_type_resolver=build_commit_type_resolver(
                    self.phase_state_engine,
                    self.phase_contract_resolver,
                ),
                state_engine=self.phase_state_engine,
            ),
            GitCheckoutTool(manager=self.git_manager, state_engine=self.phase_state_engine),
            GitFetchTool(manager=self.git_manager),
            GitPullTool(manager=self.git_manager, state_engine=self.phase_state_engine),
            GitPushTool(manager=self.git_manager),
            GitMergeTool(manager=self.git_manager),
            GitDeleteBranchTool(manager=self.git_manager),
            GitStashTool(manager=self.git_manager),
            GitRestoreTool(manager=self.git_manager),
            GitListBranchesTool(manager=self.git_manager),
            GitDiffTool(manager=self.git_manager),
            GetParentBranchTool(manager=self.git_manager, state_engine=self.phase_state_engine),
            # Quality tools
            RunQualityGatesTool(manager=self.qa_manager),
            ValidationTool(manager=self.qa_manager),
            ValidateDTOTool(),
            SafeEditTool(),
            TemplateValidationTool(),
            # Development tools
            HealthCheckTool(),
            RestartServerTool(),
            RunTestsTool(settings=settings),
            CreateFileTool(settings=settings),
            # Project tools (Phase 0.5)
            InitializeProjectTool(
                workspace_root=Path(settings.server.workspace_root),
                workflow_config=workflow_config,
                manager=self.project_manager,
                git_manager=self.git_manager,
                state_engine=self.phase_state_engine,
            ),
            GetProjectPlanTool(manager=self.project_manager),
            SavePlanningDeliverablesTool(manager=self.project_manager),
            UpdatePlanningDeliverablesTool(manager=self.project_manager),
            # Phase tools (Phase B)
            TransitionPhaseTool(
                workspace_root=Path(settings.server.workspace_root),
                project_manager=self.project_manager,
                state_engine=self.phase_state_engine,
            ),
            ForcePhaseTransitionTool(
                workspace_root=Path(settings.server.workspace_root),
                project_manager=self.project_manager,
                state_engine=self.phase_state_engine,
            ),
            # TDD Cycle tools (Issue #146)
            TransitionCycleTool(
                workspace_root=Path(settings.server.workspace_root),
                project_manager=self.project_manager,
                state_engine=self.phase_state_engine,
                git_manager=self.git_manager,
            ),
            ForceCycleTransitionTool(
                workspace_root=Path(settings.server.workspace_root),
                project_manager=self.project_manager,
                state_engine=self.phase_state_engine,
                git_manager=self.git_manager,
            ),
            # Scaffold tools (unified artifact scaffolding)
            ScaffoldArtifactTool(manager=self.artifact_manager),
            # Discovery tools
            SearchDocumentationTool(settings=settings),
            GetWorkContextTool(
                settings=settings,
                git_manager=self.git_manager,
                project_manager=self.project_manager,
                state_engine=self.phase_state_engine,
                github_manager=self.github_manager,
            ),
        ]

        # GitHub-dependent resources and additional tools (only if token is configured)
        github_token = settings.github.token
        if github_token:
            self.resources.append(GitHubIssuesResource())
            self.tools.extend(
                [
                    # GitHub Issue tools
                    CreateIssueTool(
                        manager=self.github_manager,
                        issue_config=issue_config,
                        milestone_config=milestone_config,
                        workflow_config=workflow_config,
                    ),
                    ListIssuesTool(manager=self.github_manager),
                    GetIssueTool(manager=self.github_manager),
                    CloseIssueTool(manager=self.github_manager),
                    UpdateIssueTool(manager=self.github_manager),
                    # PR and Label tools (require token at init time)
                    CreatePRTool(manager=self.github_manager, git_config=git_config),
                    ListPRsTool(manager=self.github_manager, git_config=git_config),
                    MergePRTool(manager=self.github_manager, git_config=git_config),
                    AddLabelsTool(manager=self.github_manager, label_config=label_config),
                    ListLabelsTool(manager=self.github_manager, label_config=label_config),
                    CreateLabelTool(manager=self.github_manager, label_config=label_config),
                    DeleteLabelTool(manager=self.github_manager, label_config=label_config),
                    RemoveLabelsTool(manager=self.github_manager, label_config=label_config),
                    ListMilestonesTool(),
                    CreateMilestoneTool(),
                    CloseMilestoneTool(),
                ]
            )
            logger.info("GitHub integration enabled")
        else:
            # Register issue tools without token so schemas are available; execution will error.
            self.tools.extend(
                [
                    CreateIssueTool(
                        manager=self.github_manager,
                        issue_config=issue_config,
                        milestone_config=milestone_config,
                        workflow_config=workflow_config,
                    ),
                    ListIssuesTool(manager=self.github_manager),
                    GetIssueTool(manager=self.github_manager),
                    CloseIssueTool(manager=self.github_manager),
                    UpdateIssueTool(manager=self.github_manager),
                ]
            )
            logger.info(
                "GitHub token not configured - GitHub issue tools available but will "
                "return error on use. Set GITHUB_TOKEN to enable full functionality."
            )

        self.setup_handlers()

    def _validate_tool_arguments(
        self, tool: BaseTool, arguments: dict[str, Any] | None, call_id: str, name: str
    ) -> BaseModel | dict[str, Any] | list[TextContent | ImageContent | EmbeddedResource]:
        """Validate tool arguments against args_model.

        Returns:
            - Validated BaseModel instance if validation succeeds
            - Raw arguments dict if no args_model
            - List of content with error if validation fails
        """
        if not getattr(tool, "args_model", None):
            return arguments or {}

        model_cls = cast(type[BaseModel], tool.args_model)
        logger.debug(
            "Validating tool arguments",
            extra={
                "props": {
                    "call_id": call_id,
                    "tool_name": name,
                    "model": model_cls.__name__,
                }
            },
        )
        try:
            model_validated = model_cls(**(arguments or {}))
            logger.debug(
                "Arguments validated successfully",
                extra={
                    "props": {
                        "call_id": call_id,
                        "tool_name": name,
                    }
                },
            )
            return model_validated
        except ValidationError as validation_error:
            logger.warning(
                "Argument validation failed: %s",
                validation_error,
                extra={
                    "props": {
                        "call_id": call_id,
                        "tool_name": name,
                        "model": model_cls.__name__,
                        "arguments": arguments,
                    }
                },
            )
            error_details = str(validation_error)
            return [TextContent(type="text", text=f"Invalid input for {name}: {error_details}")]

    @staticmethod
    def _augment_text_with_error_metadata(text: str, result: ToolResult) -> str:
        """Add error_code and hints to text when result is error."""
        if not result.is_error or not hasattr(result, "error_code"):
            return text

        if result.error_code:
            text += f"\n\nError code: {result.error_code}"
        if hasattr(result, "hints") and result.hints:
            text += "\nHints:"
            for hint in result.hints:
                text += f"\n  - {hint}"
        return text

    def _convert_tool_result_to_content(
        self, result: ToolResult
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Convert ToolResult to MCP content list."""
        response_content: list[TextContent | ImageContent | EmbeddedResource] = []

        for content in result.content:
            if content.get("type") == "text":
                text = content["text"]
                text = self._augment_text_with_error_metadata(text, result)
                response_content.append(TextContent(type="text", text=text))
            elif content.get("type") == "json":
                response_content.append(
                    TextContent(
                        type="text",
                        text=json.dumps(content["json"], indent=2, default=str),
                    )
                )
            elif content.get("type") == "image":
                response_content.append(
                    ImageContent(type="image", data=content["data"], mimeType=content["mimeType"])
                )
            elif content.get("type") == "resource":
                response_content.append(
                    EmbeddedResource(type="resource", resource=content["resource"])
                )

        return response_content

    @staticmethod
    def _tool_result_from_exception(exc: Exception) -> ToolResult:
        """Convert one enforcement exception into ToolResult.error()."""
        if isinstance(exc, MCPError):
            return ToolResult.error(
                message=exc.message,
                error_code=exc.code,
                hints=exc.hints if exc.hints else None,
            )
        if isinstance(exc, ValueError):
            return ToolResult.error(f"Invalid input: {exc}")
        if isinstance(exc, FileNotFoundError):
            return ToolResult.error(f"Configuration error: {exc}")
        return ToolResult.error(f"Unexpected error: {type(exc).__name__}: {exc}")

    def _run_tool_enforcement(
        self,
        tool: BaseTool,
        timing: str,
        params: BaseModel | dict[str, Any],
        result: ToolResult | None = None,
    ) -> ToolResult | None:
        """Execute pre/post enforcement for one tool when configured."""
        event = getattr(tool, "enforcement_event", None)
        if event is None:
            return None

        context = EnforcementContext(
            workspace_root=self._workspace_root,
            tool_name=tool.name,
            params=params,
            tool_result=result,
        )
        try:
            self.enforcement_runner.run(event=event, timing=timing, context=context)
        except Exception as exc:  # noqa: BLE001
            enforcement_result = self._tool_result_from_exception(exc)
            if timing == "post" and result is not None and tool.name.startswith("force_"):
                warning_text = enforcement_result.content[0]["text"]
                original_text = result.content[0]["text"]
                result.content[0]["text"] = f"⚠️ {warning_text}\n{original_text}"
                return None
            return enforcement_result
        return None

    def setup_handlers(self) -> None:
        """Set up the MCP protocol handlers."""

        @self.server.list_resources()  # type: ignore[no-untyped-call, untyped-decorator]
        async def handle_list_resources() -> list[Resource]:
            return [
                Resource(
                    uri=AnyUrl(r.uri_pattern),
                    name=r.uri_pattern.rsplit("/", maxsplit=1)[-1],
                    description=r.description,
                    mimeType=r.mime_type,
                )
                for r in self.resources
            ]

        @self.server.read_resource()  # type: ignore[no-untyped-call, untyped-decorator]
        async def handle_read_resource(uri: str) -> str:
            for resource in self.resources:
                if resource.matches(uri):
                    return await resource.read(uri)
            raise ValueError(f"Resource not found: {uri}")

        @self.server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
        async def handle_list_tools() -> list[Tool]:
            return [
                Tool(name=t.name, description=t.description, inputSchema=t.input_schema)
                for t in self.tools
            ]

        @self.server.call_tool()  # type: ignore[untyped-decorator]
        async def handle_call_tool(
            name: str, arguments: dict[str, Any] | None
        ) -> list[TextContent | ImageContent | EmbeddedResource]:
            call_id = uuid.uuid4().hex
            start_time = time.perf_counter()
            argument_keys = sorted((arguments or {}).keys())

            logger.debug(
                "Tool call received",
                extra={
                    "props": {
                        "call_id": call_id,
                        "tool_name": name,
                        "argument_keys": argument_keys,
                    }
                },
            )

            for tool in self.tools:
                if tool.name == name:
                    try:
                        # Validate arguments
                        validated = self._validate_tool_arguments(tool, arguments, call_id, name)
                        # Early return if validation failed
                        if isinstance(validated, list):
                            return validated

                        pre_result = self._run_tool_enforcement(tool, "pre", validated)
                        if pre_result is not None:
                            return self._convert_tool_result_to_content(pre_result)

                        # Execute tool
                        result = await tool.execute(validated)

                        if not result.is_error:
                            post_result = self._run_tool_enforcement(
                                tool,
                                "post",
                                validated,
                                result=result,
                            )
                            if post_result is not None:
                                return self._convert_tool_result_to_content(post_result)

                        # Convert result to MCP content
                        response_content = self._convert_tool_result_to_content(result)

                        duration_ms = (time.perf_counter() - start_time) * 1000.0

                        logger.debug(
                            "Tool call completed",
                            extra={
                                "props": {
                                    "call_id": call_id,
                                    "tool_name": name,
                                    "duration_ms": duration_ms,
                                }
                            },
                        )
                        return response_content
                    except asyncio.CancelledError:
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        logger.info(
                            "Tool call cancelled",
                            extra={
                                "props": {
                                    "call_id": call_id,
                                    "tool_name": name,
                                    "duration_ms": duration_ms,
                                }
                            },
                        )
                        raise
                    except (KeyError, AttributeError, TypeError) as e:
                        # Response processing error (dict access, attribute access, type issues)
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        logger.error(
                            "Response processing failed: %s",
                            e,
                            exc_info=True,
                            extra={
                                "props": {
                                    "call_id": call_id,
                                    "tool_name": name,
                                    "duration_ms": duration_ms,
                                    "error_type": type(e).__name__,
                                }
                            },
                        )
                        return [
                            TextContent(type="text", text=f"Error processing tool response: {e!s}")
                        ]
            raise ValueError(f"Tool not found: {name}")

    async def run(self) -> None:
        """Run the MCP server."""
        server_name = self._settings.server.name

        logger.info("Starting MCP server: %s", server_name)
        lifecycle_logger.info("MCP server running")

        # Force LF only on Windows to prevent "invalid trailing data"
        # and other CRLF issues in the JSON-RPC stream
        stdout = anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n"))

        try:
            async with stdio_server(stdout=stdout) as (read_stream, write_stream):
                await self.server.run(
                    read_stream, write_stream, self.server.create_initialization_options()
                )
        except KeyboardInterrupt:
            lifecycle_logger.info("MCP server interrupted by user")
        except Exception as e:
            lifecycle_logger.error(
                "MCP server crashed: %s",
                e,
                exc_info=True,
                extra={"props": {"error_type": type(e).__name__, "error_message": str(e)}},
            )
            # Re-raise to ensure proper exit code
            raise
        finally:
            lifecycle_logger.info("MCP server shutting down")

    async def shutdown(self) -> None:
        """Shutdown the MCP server gracefully."""
        lifecycle_logger.info("MCP server shutting down")


def main(settings: Settings | None = None) -> None:
    """Entry point for the MCP server."""
    settings = settings or Settings.from_env()
    server = MCPServer(settings=settings)
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
