# tests/mcp_server/integration/test_git_add_commit_regression_c6.py
# template=integration_test version=3d15d309 created=2026-04-29T00:00Z updated=
"""
C6 regression integration tests for git_add_or_commit ready-phase dispatch.

Extends C3 coverage with the explicit ``files=`` parameter path.

Scenarios:
  1. ``files=None`` (stage-all route): state.json excluded via ExclusionNote / skip_paths.
     Zero-delta postcondition + rendered exclusion message (regressions C3 deliverables).
  2. ``files=["state.json", "normal.py"]`` (explicit list): state.json excluded via
     ExclusionNote / skip_paths even when the caller explicitly names it; zero-delta + message.

@layer: Tests (Integration)
@dependencies: [json, pathlib, pytest, pytest-asyncio, git (GitPython),
    mcp_server.adapters.git_adapter, mcp_server.config.loader,
    mcp_server.core.operation_notes, mcp_server.managers.enforcement_runner,
    mcp_server.managers.git_manager, mcp_server.tools.git_tools,
    mcp_server.tools.tool_result]
@responsibilities:
    - Regression: zero-delta on .st3/state.json in files=None commit (C3 confirmed still green)
    - C6 new: zero-delta on .st3/state.json when files=[state.json, normal.py] (explicit list)
    - C6 new: rendered response contains exclusion message in both code paths
"""

# Standard library
import json
from pathlib import Path
from shutil import copytree
from unittest.mock import patch

# Third-party
import pytest
from git import Repo as GitRepo
from mcp.types import CallToolRequest, CallToolRequestParams

# Project modules
from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.phase_contracts_config import BranchLocalArtifact
from mcp_server.config.settings import ServerSettings, Settings
from mcp_server.core.operation_notes import ExclusionNote, NoteContext
from mcp_server.managers.enforcement_runner import (
    EnforcementContext,
    EnforcementRunner,
)
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_contract_resolver import MergeReadinessContext
from mcp_server.server import MCPServer
from mcp_server.tools.git_tools import (
    GitCommitInput,
    GitCommitTool,
    build_commit_type_resolver,
    build_phase_guard,
)
from mcp_server.tools.tool_result import ToolResult

_REPO_ROOT = Path(__file__).parent.parent.parent.parent

_STATE_JSON = ".st3/state.json"
_DELIVERABLES_JSON = ".st3/deliverables.json"

_ARTIFACT_STATE = BranchLocalArtifact(
    path=_STATE_JSON,
    reason="MCP workflow state — branch-local, must never reach main",
)
_ARTIFACT_DELIVERABLES = BranchLocalArtifact(
    path=_DELIVERABLES_JSON,
    reason="MCP workflow deliverables — branch-local, must never reach main",
)


def _init_repo(repo_dir: Path) -> GitRepo:
    """Create a real git repo with state.json, deliverables.json, and normal.py committed."""
    repo = GitRepo.init(str(repo_dir))
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "test@example.com")

    state_dir = repo_dir / ".st3"
    state_dir.mkdir()
    (repo_dir / "normal.py").write_text("# v1\n", encoding="utf-8")
    (state_dir / "state.json").write_text(
        json.dumps({"current_phase": "ready", "branch": "refactor/283"}),
        encoding="utf-8",
    )
    (state_dir / "deliverables.json").write_text("{}", encoding="utf-8")

    repo.index.add(["normal.py", _STATE_JSON, _DELIVERABLES_JSON])
    repo.index.commit("initial commit")
    return repo


def _make_runner(tmp_path: Path) -> EnforcementRunner:
    enforcement_yaml = _REPO_ROOT / ".st3" / "config" / "enforcement.yaml"
    loader = ConfigLoader(config_root=_REPO_ROOT / ".st3" / "config")
    enforcement_config = loader.load_enforcement_config(config_path=enforcement_yaml)
    merge_ctx = MergeReadinessContext(
        terminal_phase="ready",
        pr_allowed_phase="ready",
        branch_local_artifacts=(_ARTIFACT_STATE, _ARTIFACT_DELIVERABLES),
    )
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=enforcement_config,
        merge_readiness_context=merge_ctx,
    )


def _make_commit_tool(tmp_path: Path) -> GitCommitTool:
    loader = ConfigLoader(config_root=_REPO_ROOT / ".st3" / "config")
    manager = GitManager(
        git_config=loader.load_git_config(),
        adapter=GitAdapter(str(tmp_path)),
        workphases_config=loader.load_workphases_config(),
    )
    return GitCommitTool(manager=manager)


def _modify_files(tmp_path: Path) -> None:
    """Modify tracked files to simulate pre-ready-commit state."""
    (tmp_path / "normal.py").write_text("# v2\n", encoding="utf-8")
    (tmp_path / _STATE_JSON).write_text(
        json.dumps({"current_phase": "ready", "branch": "refactor/283", "cycle": 6}),
        encoding="utf-8",
    )


class TestGitAddCommitRegressionC6:
    """C6 regression: zero-delta + exclusion message across both git staging code paths."""

    @pytest.mark.asyncio
    async def test_ready_phase_full_dispatch_no_delta_rendered_exclusion(
        self, tmp_path: Path
    ) -> None:
        """Regression (files=None): state.json excluded from commit AND message rendered.

        Verifies C3 deliverables remain intact after C6 proxy replacement:
          - EnforcementRunner.run() writes ExclusionNote for state.json.
          - GitCommitTool.execute() reads ExclusionNote → skip_paths → zero-delta commit.
          - NoteContext.render_to_response() contains state.json path in output.
        """
        repo = _init_repo(tmp_path)
        _modify_files(tmp_path)

        # Layer 1 — EnforcementRunner
        runner = _make_runner(tmp_path)
        enforcement_ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="git_add_or_commit",
            params={},
        )
        note_context = NoteContext()
        runner.run(
            event="git_add_or_commit",
            timing="pre",
            enforcement_ctx=enforcement_ctx,
            note_context=note_context,
        )

        assert _STATE_JSON in {n.file_path for n in note_context.of_type(ExclusionNote)}

        # Layer 2 — GitCommitTool (files=None stage-all route)
        tool = _make_commit_tool(tmp_path)
        params = GitCommitInput(
            message="c6 regression: files=None",
            workflow_phase="documentation",
        )
        result = await tool.execute(params, note_context)
        assert not result.is_error, f"Commit failed: {result}"

        last_commit = list(repo.iter_commits(max_count=1))[0]
        diff_paths = {d.a_path for d in last_commit.diff(last_commit.parents[0])}
        assert _STATE_JSON not in diff_paths, (
            f"Non-zero delta on '{_STATE_JSON}' (files=None path). "
            f"Commit contained: {sorted(diff_paths)}"
        )
        assert "normal.py" in diff_paths

        # Layer 3 — render_to_response
        rendered = note_context.render_to_response(ToolResult.text("committed"))
        all_text = " ".join(c["text"] for c in rendered.content if c.get("type") == "text")
        assert _STATE_JSON in all_text, (
            f"Expected '{_STATE_JSON}' in rendered response. Got: {all_text!r}"
        )

    @pytest.mark.asyncio
    async def test_explicit_files_list_state_json_still_excluded(self, tmp_path: Path) -> None:
        """C6 new (files=[state.json, normal.py]): state.json excluded even when caller names it.

        When the caller explicitly passes files=['.st3/state.json', 'normal.py'], the
        ExclusionNote mechanism must still suppress state.json via skip_paths.
        Zero-delta postcondition must hold on the explicit-files code path.
        """
        repo = _init_repo(tmp_path)
        _modify_files(tmp_path)

        runner = _make_runner(tmp_path)
        enforcement_ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="git_add_or_commit",
            params={},
        )
        note_context = NoteContext()
        runner.run(
            event="git_add_or_commit",
            timing="pre",
            enforcement_ctx=enforcement_ctx,
            note_context=note_context,
        )

        assert _STATE_JSON in {n.file_path for n in note_context.of_type(ExclusionNote)}

        # Explicit files list includes both state.json AND normal.py
        tool = _make_commit_tool(tmp_path)
        params = GitCommitInput(
            message="c6 regression: explicit files list",
            workflow_phase="documentation",
            files=[_STATE_JSON, "normal.py"],
        )
        result = await tool.execute(params, note_context)
        assert not result.is_error, f"Commit failed: {result}"

        last_commit = list(repo.iter_commits(max_count=1))[0]
        diff_paths = {d.a_path for d in last_commit.diff(last_commit.parents[0])}
        assert _STATE_JSON not in diff_paths, (
            f"Non-zero delta on '{_STATE_JSON}' (explicit files path). "
            f"Commit contained: {sorted(diff_paths)}"
        )
        assert "normal.py" in diff_paths

        # Exclusion message present in response
        rendered = note_context.render_to_response(ToolResult.text("committed"))
        all_text = " ".join(c["text"] for c in rendered.content if c.get("type") == "text")
        assert _STATE_JSON in all_text, (
            f"Expected '{_STATE_JSON}' in rendered response. Got: {all_text!r}"
        )


class TestGitAddCommitRegressionC6ServerDispatch:
    """C6 server-dispatch regression: explicit ``files=`` path via MCPServer dispatch.

    Proves that the C6 NoteContext wiring holds when a real MCP client passes an
    explicit ``files`` list that includes ``.st3/state.json``.  The MCPServer must
    suppress state.json via the ExclusionNote → skip_paths wire-through even in
    that code path.
    """

    @pytest.mark.asyncio
    async def test_server_dispatch_explicit_files_excludes_state_json(self, tmp_path: Path) -> None:
        """Full MCPServer dispatch with files=[state.json, normal.py]: zero-delta on state.json.

        Mirrors the C3 server-dispatch proof but exercises the explicit-files
        staging route introduced in C6.  The test:
          1. Sets up a real git repo (state.json + normal.py committed on initial).
          2. Modifies both files to simulate pre-ready-phase commit state.
          3. Instantiates MCPServer with workspace_root=tmp_path.
          4. Dispatches git_add_or_commit with files=['state.json path','normal.py'].
          5. Asserts zero-delta on state.json and exclusion message in response.
        """
        repo = _init_repo(tmp_path)
        _modify_files(tmp_path)

        # Copy .st3/config from real workspace so MCPServer can initialise
        config_dir = tmp_path / ".st3" / "config"
        copytree(_REPO_ROOT / ".st3" / "config", config_dir, dirs_exist_ok=True)

        settings = Settings(
            server=ServerSettings(
                workspace_root=str(tmp_path),
                config_root=str(config_dir),
            )
        )
        with patch("mcp_server.server.Settings") as mock_settings_cls:
            mock_settings_cls.from_env.return_value = settings
            server = MCPServer()

        # Re-register GitCommitTool to operate on tmp_path
        git_commit_tool = GitCommitTool(
            manager=GitManager(
                git_config=server.git_manager.git_config,
                adapter=GitAdapter(str(tmp_path)),
                workphases_config=ConfigLoader(config_root=config_dir).load_workphases_config(),
            ),
            phase_guard=build_phase_guard(tmp_path),
            commit_type_resolver=build_commit_type_resolver(
                server.phase_state_engine,
                server.phase_contract_resolver,
            ),
            state_engine=server.phase_state_engine,
        )
        server.tools = [
            t if t.name != "git_add_or_commit" else git_commit_tool for t in server.tools
        ]

        handler = server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            params=CallToolRequestParams(
                name="git_add_or_commit",
                arguments={
                    "message": "c6 server dispatch: explicit files",
                    "workflow_phase": "documentation",
                    "commit_type": "docs",
                    "files": [_STATE_JSON, "normal.py"],
                },
            )
        )
        response = await handler(req)

        content_texts = [c.text for c in response.root.content if hasattr(c, "text")]
        all_text = " ".join(content_texts)

        assert not response.root.isError, f"Expected success but got error: {all_text!r}"

        # Zero-delta: state.json must NOT appear in commit diff
        last_commit = list(repo.iter_commits(max_count=1))[0]
        diff_paths = {d.a_path for d in last_commit.diff(last_commit.parents[0])}
        assert _STATE_JSON not in diff_paths, (
            f"Non-zero delta on '{_STATE_JSON}' via server dispatch (explicit files). "
            f"Commit contained: {sorted(diff_paths)}"
        )
        assert "normal.py" in diff_paths, (
            "normal.py missing from commit diff — test setup integrity failure"
        )

        # ExclusionNote rendered in response
        assert _STATE_JSON in all_text, (
            f"Expected '{_STATE_JSON}' in rendered server response. Got: {all_text!r}"
        )
