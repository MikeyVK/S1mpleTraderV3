# tests\mcp_server\integration\test_git_add_commit_ready_phase_c3.py
# template=integration_test version=85ea75d4 created=2026-04-14T09:10Z updated=
"""
Integration tests for C3 NoteContext end-to-end dispatch.

Full layer-integration proof: EnforcementRunner → NoteContext → GitCommitTool,
driven by a real git repository. Verifies:
  1. EnforcementRunner.run() writes ExclusionNote to NoteContext
  2. GitCommitTool.execute() reads ExclusionNote → skip_paths → zero delta on state.json
  3. NoteContext.render_to_response() renders the exclusion message in the response

@layer: Tests (Integration)
@dependencies: [json, pathlib, pytest, pytest-asyncio, git (GitPython),
    mcp_server.adapters.git_adapter, mcp_server.config.loader,
    mcp_server.core.operation_notes, mcp_server.managers.enforcement_runner,
    mcp_server.managers.git_manager, mcp_server.tools.git_tools,
    mcp_server.tools.tool_result]
@responsibilities:
    - Prove end-to-end NoteContext wiring across all three C3 layers
    - Prove zero-delta postcondition on .st3/state.json in a real git repo
    - Prove render_to_response produces exclusion path in user-visible response
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


def _init_repo_with_initial_commit(repo_dir: Path) -> GitRepo:
    """Create a real git repo with state.json and deliverables.json committed.

    Both branch-local artifacts are included so that _git_is_tracked() returns
    True for both paths without patching.
    """
    repo = GitRepo.init(str(repo_dir))
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "test@example.com")

    normal = repo_dir / "normal.py"
    state_dir = repo_dir / ".st3"
    state_dir.mkdir()
    state_file = state_dir / "state.json"
    deliverables_file = state_dir / "deliverables.json"

    normal.write_text("# v1\n", encoding="utf-8")
    state_file.write_text(
        json.dumps({"current_phase": "ready", "branch": "refactor/283"}),
        encoding="utf-8",
    )
    deliverables_file.write_text("{}", encoding="utf-8")

    repo.index.add(["normal.py", _STATE_JSON, _DELIVERABLES_JSON])
    repo.index.commit("initial commit")
    return repo


def _make_runner(tmp_path: Path) -> EnforcementRunner:
    """Build EnforcementRunner backed by the live enforcement.yaml."""
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
    """Build GitCommitTool backed by a real GitManager + GitAdapter at tmp_path."""
    loader = ConfigLoader(config_root=_REPO_ROOT / ".st3" / "config")
    git_config = loader.load_git_config()
    manager = GitManager(
        git_config=git_config,
        adapter=GitAdapter(str(tmp_path)),
        workphases_config=loader.load_workphases_config(),
    )
    return GitCommitTool(manager=manager)


class TestGitAddCommitReadyPhaseC3:
    """Integration proof: C3 NoteContext wiring across all three layers.

    Uses a real git repository. No network or GitHub calls required.
    """

    @pytest.mark.asyncio
    async def test_ready_phase_full_dispatch_zero_delta_and_exclusion_message(
        self, tmp_path: Path
    ) -> None:
        """End-to-end C3 dispatch: zero delta on state.json AND exclusion message rendered.

        Planning.md C3 deliverable #5: Integration proof.

        Verifies the full NoteContext wire-through across three layers:

        Layer 1 — EnforcementRunner:
          run(..., note_context=note_context) writes ExclusionNote per tracked
          branch-local artifact; performs no git rm operations.

        Layer 2 — GitCommitTool:
          execute(params, note_context) reads ExclusionNote entries → frozenset;
          passes as skip_paths to commit_with_scope() → GitAdapter.commit();
          state.json absent from commit.diff(parent) (zero-delta postcondition).

        Layer 3 — NoteContext.render_to_response():
          rendered response text contains the excluded file path.

        RED: Fails because run() does not yet accept note_context parameter and
        execute() does not yet accept context parameter (TypeError).
        """
        repo = _init_repo_with_initial_commit(tmp_path)

        # Modify both tracked files to simulate pre-ready-commit state.
        # normal.py changes will appear in the commit; state.json must not.
        (tmp_path / "normal.py").write_text("# v2\n", encoding="utf-8")
        (tmp_path / _STATE_JSON).write_text(
            json.dumps({"current_phase": "ready", "branch": "refactor/283", "cycle": 3}),
            encoding="utf-8",
        )

        # ── Layer 1: EnforcementRunner writes ExclusionNote ───────────────────
        runner = _make_runner(tmp_path)
        enforcement_ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="git_add_or_commit",
            params={},
        )
        note_context = NoteContext()

        # RED: TypeError — run() does not yet accept note_context keyword argument.
        runner.run(
            event="git_add_or_commit",
            timing="pre",
            enforcement_ctx=enforcement_ctx,
            note_context=note_context,
        )

        exclusion_notes = note_context.of_type(ExclusionNote)
        excluded_paths = {n.file_path for n in exclusion_notes}
        assert _STATE_JSON in excluded_paths, (
            f"Expected ExclusionNote for '{_STATE_JSON}' but got: {sorted(excluded_paths)}"
        )

        # ── Layer 2: GitCommitTool reads ExclusionNote → zero-delta commit ────
        tool = _make_commit_tool(tmp_path)
        params = GitCommitInput(
            message="ready phase commit",
            workflow_phase="documentation",
        )

        # RED: TypeError — execute() does not yet accept context parameter.
        result = await tool.execute(params, note_context)

        assert not result.is_error, f"Expected commit success but got error: {result}"

        # Zero-delta assertion: state.json must NOT appear in the commit diff.
        commits = list(repo.iter_commits(max_count=1))
        last_commit = commits[0]
        diff_paths = {d.a_path for d in last_commit.diff(last_commit.parents[0])}
        assert _STATE_JSON not in diff_paths, (
            f"Non-zero delta on '{_STATE_JSON}' — skip_paths not applied correctly. "
            f"All changed paths in commit: {sorted(diff_paths)}"
        )
        assert "normal.py" in diff_paths, (
            "normal.py missing from commit diff — sanity check failed "
            "(test setup integrity: normal.py modification was not committed)"
        )

        # ── Layer 3: render_to_response renders exclusion message ──────────────
        base = ToolResult.text("committed")
        rendered = note_context.render_to_response(base)

        all_text = " ".join(c["text"] for c in rendered.content if c.get("type") == "text")
        assert _STATE_JSON in all_text, (
            f"Expected '{_STATE_JSON}' in rendered response text but got: {all_text!r}"
        )


class TestGitAddCommitReadyPhaseC3ServerDispatch:
    """Primary server-dispatch proof: C3 NoteContext wiring via MCPServer.handle_call_tool.

    Proves the full wire-through via the server's request_handlers[CallToolRequest]
    dispatcher, consistent with how real MCP clients invoke tools. The enforcement
    runner writes ExclusionNote → GitCommitTool reads it → state.json absent from
    the resulting commit diff.
    """

    @pytest.mark.asyncio
    async def test_server_dispatch_excludes_state_json_from_commit(self, tmp_path: Path) -> None:
        """Primary C3 integration proof via MCPServer.handle_call_tool dispatch.

        Planning.md C3 deliverable #5 (primary path):
          1. Set up a real git repo in tmp_path (state.json + normal.py committed).
          2. Instantiate MCPServer with workspace_root=tmp_path.
          3. Invoke dispatch via server.request_handlers[CallToolRequest].
          4. Assert response text does NOT include an error.
          5. Assert state.json absent from the last commit diff (zero-delta).
          6. Assert .st3/state.json path appears in response text
             (rendered ExclusionNote).
        """
        # ── Setup: real git repo with both branch-local artifacts tracked ─────
        repo = _init_repo_with_initial_commit(tmp_path)

        # Modify both files to simulate pre-ready-commit state.
        (tmp_path / "normal.py").write_text("# v2\n", encoding="utf-8")
        (tmp_path / _STATE_JSON).write_text(
            json.dumps({"current_phase": "ready", "branch": "refactor/283", "cycle": 3}),
            encoding="utf-8",
        )

        # Copy .st3/config from real workspace so MCPServer can initialise
        config_dir = tmp_path / ".st3" / "config"
        repo_root = Path(__file__).parent.parent.parent.parent
        copytree(repo_root / ".st3" / "config", config_dir, dirs_exist_ok=True)

        # ── Instantiate MCPServer pointing at tmp_path ────────────────────────
        settings = Settings(
            server=ServerSettings(
                workspace_root=str(tmp_path),
                config_root=str(config_dir),
            )
        )
        # Patch github token to None so no real API calls are attempted
        with patch("mcp_server.server.Settings") as mock_settings_cls:
            mock_settings_cls.from_env.return_value = settings
            server = MCPServer()

        # ── Re-register GitCommitTool so it operates on tmp_path ─────────────
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

        # ── Dispatch via real server handler ──────────────────────────────────
        handler = server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            params=CallToolRequestParams(
                name="git_add_or_commit",
                arguments={
                    "message": "ready phase server dispatch test",
                    "workflow_phase": "documentation",
                    "commit_type": "docs",
                },
            )
        )
        response = await handler(req)

        # ── Assertions ────────────────────────────────────────────────────────
        content_texts = [c.text for c in response.root.content if hasattr(c, "text")]
        all_text = " ".join(content_texts)

        assert not response.root.isError, f"Expected success but got error: {all_text!r}"

        # Zero-delta: state.json must NOT appear in the commit diff
        commits = list(repo.iter_commits(max_count=1))
        last_commit = commits[0]
        diff_paths = {d.a_path for d in last_commit.diff(last_commit.parents[0])}
        assert _STATE_JSON not in diff_paths, (
            f"Non-zero delta on '{_STATE_JSON}' — NoteContext wiring failed via server dispatch. "
            f"All paths in commit: {sorted(diff_paths)}"
        )
        assert "normal.py" in diff_paths, (
            "normal.py missing from commit diff — test setup integrity failure"
        )

        # ExclusionNote rendered: state.json path visible in response
        assert _STATE_JSON in all_text, (
            f"Expected '{_STATE_JSON}' in rendered response but got: {all_text!r}"
        )
