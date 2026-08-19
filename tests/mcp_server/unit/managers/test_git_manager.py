"""Unit tests for GitManager.

@layer: Tests (Unit)
@dependencies: pytest, mcp_server.managers.git_manager, mcp_server.config.schemas
"""

from tests.mcp_server.test_support import get_default_server_root
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false, reportPrivateUsage=false
# Suppress Pydantic false positives; reportPrivateUsage allows protected member access in test setup

# Standard library
from pathlib import Path
from unittest.mock import MagicMock

# Third-party
import pytest

from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import GitConfig
from mcp_server.config.schemas.workphases import PhaseDefinition, WorkphasesConfig
from mcp_server.core.exceptions import ExecutionError, PreflightError, ValidationError
from mcp_server.core.operation_notes import Note, NoteContext

# Module under test
from mcp_server.managers.git_manager import GitManager, GitPushResult

_TEST_WORKPHASES = WorkphasesConfig(
    phases={
        "research": PhaseDefinition(commit_type_hint="docs"),
        "implementation": PhaseDefinition(
            commit_type_hint=None,
            subphases=["red", "green", "refactor"],
        ),
        "coordination": PhaseDefinition(
            commit_type_hint="chore",
            subphases=["delegation", "sync", "review"],
            terminal=True,
        ),
    }
)


@pytest.fixture
def git_config() -> GitConfig:
    """Fixture for project git config."""
    return ConfigLoader(Path(f"{get_default_server_root()}/config")).load_git_config()


class TestGitManagerValidation:
    """Test suite for GitManager validation and branching logic."""

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        """Fixture for mocked GitAdapter."""
        adapter = MagicMock()
        adapter.is_clean.return_value = True
        return adapter

    @pytest.fixture
    def manager(self, mock_adapter: MagicMock, git_config: GitConfig) -> GitManager:
        """Fixture for GitManager with mocked adapter."""
        return GitManager(git_config=git_config, adapter=mock_adapter)

    def test_init_default(self) -> None:
        """Test initialization with default adapter."""
        mgr = GitManager(
            git_config=ConfigLoader(Path(f"{get_default_server_root()}/config")).load_git_config()
        )
        assert mgr.adapter is not None

    def test_get_status(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test get_status delegation."""
        mock_adapter.get_status.return_value = {"branch": "main"}
        status = manager.get_status()
        assert status == {"branch": "main"}
        mock_adapter.get_status.assert_called_once()

    def test_create_branch_valid(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test creating a branch with explicit base."""
        name = manager.create_branch("my-feature", "feature", "HEAD", NoteContext())

        assert name == "feature/my-feature"
        mock_adapter.create_branch.assert_called_once_with("feature/my-feature", base="HEAD")
        mock_adapter.is_clean.assert_called_once()

    def test_create_branch_epic_valid(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test creating an epic branch with explicit base."""
        name = manager.create_branch("91-test-suite-cleanup", "epic", "HEAD", NoteContext())

        assert name == "epic/91-test-suite-cleanup"
        mock_adapter.create_branch.assert_called_once_with(
            "epic/91-test-suite-cleanup", base="HEAD"
        )
        mock_adapter.is_clean.assert_called_once()

    def test_create_branch_invalid_type(self, manager: GitManager) -> None:
        """Test validation of branch type."""
        with pytest.raises(ValidationError, match="Invalid branch type"):
            manager.create_branch("valid-name", "invalid-type", "HEAD", NoteContext())

    def test_create_branch_invalid_name(self, manager: GitManager) -> None:
        """Test validation of branch name (regex)."""
        with pytest.raises(ValidationError, match="Invalid branch name"):
            manager.create_branch("Bad Name!", "feature", "HEAD", NoteContext())

    def test_create_branch_dirty(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test pre-flight check failure for dirty working directory."""
        mock_adapter.is_clean.return_value = False

        with pytest.raises(PreflightError, match="Working directory is not clean"):
            manager.create_branch("valid-name", "feature", "HEAD", NoteContext())

    def test_delete_branch_protected(self, manager: GitManager) -> None:
        """Test deletion of protected branch is prevented."""
        with pytest.raises(ValidationError, match="Cannot delete protected branch"):
            manager.delete_branch("main", NoteContext())


class TestGitManagerOperations:
    """Test suite for GitManager operations (commit, merge, stash)."""

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        """Fixture for mocked GitAdapter."""
        adapter = MagicMock()
        adapter.is_clean.return_value = True
        return adapter

    @pytest.fixture
    def manager(self, mock_adapter: MagicMock, git_config: GitConfig) -> GitManager:
        """Fixture for GitManager with mocked adapter."""
        return GitManager(git_config=git_config, adapter=mock_adapter)

    def test_restore_success(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test restore operation."""
        manager.restore(files=["a.py", "b.py"], note_context=NoteContext(), source="HEAD")

        mock_adapter.restore.assert_called_once_with(files=["a.py", "b.py"], source="HEAD")

    def test_restore_requires_files(self, manager: GitManager) -> None:
        """Test restore operation requires files."""
        with pytest.raises(ValidationError):
            manager.restore(files=[], note_context=NoteContext())

    def test_checkout(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test checkout delegation."""
        manager.checkout("main")
        mock_adapter.checkout.assert_called_once_with("main")

    def test_push(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test push delegation."""
        manager.push(set_upstream=True)
        mock_adapter.push.assert_called_once_with(set_upstream=True)

    def test_merge_clean(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test merge with clean state."""
        manager.merge("feature-branch", NoteContext())
        mock_adapter.merge.assert_called_once_with("feature-branch")

    def test_merge_dirty(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test merge fails with dirty state."""
        mock_adapter.is_clean.return_value = False
        with pytest.raises(PreflightError, match="Working directory is not clean"):
            manager.merge("feature-branch", NoteContext())

    def test_delete_branch_valid(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test deleting a valid branch."""
        manager.delete_branch("feature/old", NoteContext())
        mock_adapter.delete_local_branch.assert_called_once_with("feature/old", force=False)

    def test_delete_branch_mode_local(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test mode=local only calls local delete."""
        manager.delete_branch("feature/old", NoteContext(), mode="local")
        mock_adapter.delete_local_branch.assert_called_once_with("feature/old", force=False)
        mock_adapter.delete_remote_branch.assert_not_called()

    def test_delete_branch_mode_remote(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test mode=remote only calls remote delete, not local."""
        manager.delete_branch("feature/old", NoteContext(), mode="remote")
        mock_adapter.delete_local_branch.assert_not_called()
        mock_adapter.delete_remote_branch.assert_called_once_with("feature/old")

    def test_delete_branch_mode_both(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test mode=both calls both local and remote delete."""
        manager.delete_branch("feature/old", NoteContext(), mode="both")
        mock_adapter.delete_local_branch.assert_called_once_with("feature/old", force=False)
        mock_adapter.delete_remote_branch.assert_called_once_with("feature/old")

    def test_delete_branch_mode_both_local_absent(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test mode=both with absent local branch does not raise; remote still called."""
        mock_adapter.delete_local_branch.side_effect = ExecutionError(
            "Branch feature/old does not exist"
        )
        manager.delete_branch("feature/old", NoteContext(), mode="both")
        mock_adapter.delete_remote_branch.assert_called_once_with("feature/old")

    def test_stash_operations(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test stash delegations."""
        manager.stash("saving work")
        mock_adapter.stash.assert_called_with(message="saving work", include_untracked=False)

        manager.stash("saving work", include_untracked=True)
        mock_adapter.stash.assert_called_with(message="saving work", include_untracked=True)

        manager.stash_pop()
        mock_adapter.stash_pop.assert_called_once()

        mock_adapter.stash_list.return_value = ["stash@{0}"]
        assert manager.stash_list() == ["stash@{0}"]

    def test_get_current_branch(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test getting current branch."""
        mock_adapter.get_current_branch.return_value = "main"
        assert manager.get_current_branch() == "main"

    def test_has_net_diff_for_path_delegates(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """has_net_diff_for_path must delegate to adapter with identical arguments."""
        mock_adapter.has_net_diff_for_path.return_value = True
        result = manager.has_net_diff_for_path(f"{get_default_server_root()}/state.json", "main")
        assert result is True
        mock_adapter.has_net_diff_for_path.assert_called_once_with(
            f"{get_default_server_root()}/state.json", "main"
        )

    def test_neutralize_to_base_delegates(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """neutralize_to_base must delegate to adapter with identical arguments."""
        paths = frozenset(
            {
                f"{get_default_server_root()}/state.json",
                f"{get_default_server_root()}/deliverables.json",
            }
        )
        manager.neutralize_to_base(paths, "main")
        mock_adapter.neutralize_to_base.assert_called_once_with(paths, "main")

    def test_list_branches(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test listing branches."""
        mock_adapter.list_branches.return_value = ["main", "dev"]
        assert manager.list_branches(verbose=True) == ["main", "dev"]
        mock_adapter.list_branches.assert_called_with(verbose=True, remote=False)

    def test_compare_branches(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test diff stat delegation."""
        mock_adapter.get_diff_stat.return_value = "diff"
        assert manager.compare_branches("main", "feat") == "diff"
        mock_adapter.get_diff_stat.assert_called_with("main", "feat")

    def test_get_recent_commits(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test retrieving recent commits."""
        mock_adapter.get_recent_commits.return_value = ["msg1"]
        assert manager.get_recent_commits(1) == ["msg1"]


class TestGitManagerCreateBranch:
    """Tests for NEW create_branch method with explicit base_branch (Issue #64)."""

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        """Fixture for mocked GitAdapter."""
        adapter = MagicMock()
        adapter.is_clean.return_value = True
        adapter.get_current_branch.return_value = "refactor/51-mcp"
        return adapter

    @pytest.fixture
    def manager(self, mock_adapter: MagicMock, git_config: GitConfig) -> GitManager:
        """Fixture for GitManager with mocked adapter."""
        return GitManager(git_config=git_config, adapter=mock_adapter)

    def test_create_branch_requires_base_branch_parameter(self, manager: GitManager) -> None:
        """RED: create_branch should require base_branch parameter (no default)."""
        with pytest.raises(TypeError):
            manager.create_branch("test", "feature")  # type: ignore[call-arg]

    def test_create_branch_passes_base_to_adapter(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """RED: Should pass base_branch to adapter.create_branch as base."""
        manager.create_branch("test", "feature", "main", NoteContext())

        mock_adapter.create_branch.assert_called_once_with("feature/test", base="main")


class TestGitManagerCommitWithScope:
    """Tests for commit_with_scope method with workflow phase scopes."""

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        """Fixture for mocked GitAdapter."""
        return MagicMock()

    @pytest.fixture
    def manager(self, mock_adapter: MagicMock) -> GitManager:
        """Fixture for GitManager with mocked adapter and test workphases."""
        return GitManager(
            git_config=git_config,
            adapter=mock_adapter,
            workphases_config=_TEST_WORKPHASES,
        )

    def test_commit_with_scope_phase_only(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test commit with phase-only scope (no subphase)."""
        mock_adapter.commit.return_value = "abc123"

        result = manager.commit_with_scope(
            workflow_phase="research",
            message="investigate alternatives",
            note_context=NoteContext(),
        )

        assert result == "abc123"
        mock_adapter.commit.assert_called_once_with(
            "docs(P_RESEARCH): investigate alternatives", files=None, skip_paths=frozenset()
        )

    def test_commit_with_scope_phase_and_subphase(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test commit with phase and subphase."""
        mock_adapter.commit.return_value = "def456"

        result = manager.commit_with_scope(
            workflow_phase="implementation",
            sub_phase="red",
            message="add failing test",
            commit_type="test",
            note_context=NoteContext(),
        )

        assert result == "def456"
        mock_adapter.commit.assert_called_once_with(
            "test(P_IMPLEMENTATION_SP_RED): add failing test", files=None, skip_paths=frozenset()
        )

    def test_commit_with_scope_with_cycle_number(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test commit with cycle number in TDD format."""
        mock_adapter.commit.return_value = "ghi789"

        result = manager.commit_with_scope(
            workflow_phase="implementation",
            sub_phase="green",
            cycle_number=1,
            message="implement feature",
            commit_type="feat",
            note_context=NoteContext(),
        )

        assert result == "ghi789"
        mock_adapter.commit.assert_called_once_with(
            "feat(P_IMPLEMENTATION_SP_C1_GREEN): implement feature",
            files=None,
            skip_paths=frozenset(),
        )

    def test_commit_with_scope_coordination_phase(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test commit with coordination phase (new phase type)."""
        mock_adapter.commit.return_value = "jkl012"

        result = manager.commit_with_scope(
            workflow_phase="coordination",
            sub_phase="delegation",
            message="delegate to child issues",
            note_context=NoteContext(),
        )

        assert result == "jkl012"
        mock_adapter.commit.assert_called_once_with(
            "chore(P_COORDINATION_SP_DELEGATION): delegate to child issues",
            files=None,
            skip_paths=frozenset(),
        )

    def test_commit_with_scope_with_files(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test commit with specific files."""
        mock_adapter.commit.return_value = "mno345"

        result = manager.commit_with_scope(
            workflow_phase="implementation",
            sub_phase="refactor",
            message="clean up code",
            files=["src/app.py", "tests/test_app.py"],
            commit_type="refactor",
            note_context=NoteContext(),
        )

        assert result == "mno345"
        mock_adapter.commit.assert_called_once_with(
            "refactor(P_IMPLEMENTATION_SP_REFACTOR): clean up code",
            files=["src/app.py", "tests/test_app.py"],
            skip_paths=frozenset(),
        )

    def test_commit_with_scope_with_commit_type_override(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test commit with explicit commit_type override."""
        mock_adapter.commit.return_value = "pqr678"

        result = manager.commit_with_scope(
            workflow_phase="implementation",
            sub_phase="red",
            message="fix failing test",
            commit_type="fix",  # Override default 'test'
            note_context=NoteContext(),
        )

        assert result == "pqr678"
        mock_adapter.commit.assert_called_once_with(
            "fix(P_IMPLEMENTATION_SP_RED): fix failing test",
            files=None,
            skip_paths=frozenset(),
        )

    def test_commit_with_scope_invalid_phase_raises_error(self, manager: GitManager) -> None:
        """Test that invalid phase raises ValueError with actionable message."""
        with pytest.raises(ValueError, match="Unknown workflow phase"):
            manager.commit_with_scope(
                workflow_phase="invalid_phase",
                message="test",
                note_context=NoteContext(),
            )

    def test_commit_with_scope_invalid_subphase_raises_error(self, manager: GitManager) -> None:
        """Test that invalid subphase raises ValueError with actionable message."""
        with pytest.raises(ValueError, match="Invalid sub_phase"):
            manager.commit_with_scope(
                workflow_phase="implementation",
                sub_phase="invalid_subphase",
                message="test",
                note_context=NoteContext(),
            )

    def test_commit_with_scope_empty_files_raises_error(self, manager: GitManager) -> None:
        """Test that empty files list raises ValidationError."""
        with pytest.raises(ValidationError, match="Files list cannot be empty"):
            manager.commit_with_scope(
                workflow_phase="research",
                message="test",
                files=[],
                note_context=NoteContext(),
            )

    def test_commit_with_scope_appends_issue_suffix(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """commit_with_scope(issue_number=228) → message ends with ' (#228)'."""
        mock_adapter.commit.return_value = "abc123"

        manager.commit_with_scope(
            workflow_phase="implementation",
            message="implement suffix injection",
            note_context=NoteContext(),
            sub_phase="green",
            commit_type="feat",
            issue_number=228,
        )

        call_args = mock_adapter.commit.call_args
        expected = "feat(P_IMPLEMENTATION_SP_GREEN): implement suffix injection (#228)"
        assert call_args[0][0] == expected

    def test_commit_with_scope_no_suffix_when_none(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """commit_with_scope(issue_number=None) → no suffix (regression guard)."""
        mock_adapter.commit.return_value = "abc123"

        manager.commit_with_scope(
            workflow_phase="research",
            message="update README",
            note_context=NoteContext(),
            issue_number=None,
        )

        call_args = mock_adapter.commit.call_args
        assert call_args[0][0] == "docs(P_RESEARCH): update README"
        assert "(#" not in call_args[0][0]


class TestGitManagerPrepareSubmission:
    """Tests for GitManager.prepare_submission — Issue #295 Cycles 2 & 3.

    All tests inject MagicMock(spec=GitAdapter) via GitManager(adapter=...) and
    call prepare_submission() through the public GitManager API (§14).
    """

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        """Fixture for spec-constrained GitAdapter mock."""
        adapter = MagicMock(spec=GitAdapter)
        adapter.is_clean.return_value = True
        adapter.has_upstream.return_value = True
        adapter.has_net_diff_for_path.return_value = False
        adapter.push.return_value = None
        adapter.get_current_branch.return_value = "main"
        return adapter

    @pytest.fixture
    def manager(self, mock_adapter: MagicMock, git_config: GitConfig) -> GitManager:
        """Fixture for GitManager with mocked adapter and real workphases config."""
        workphases = ConfigLoader(
            Path(f"{get_default_server_root()}/config")
        ).load_workphases_config()
        return GitManager(
            git_config=git_config,
            adapter=mock_adapter,
            workphases_config=workphases,
        )

    # --- Cycle 2: preflights + artifact filter ---

    def test_prepare_submission_raises_preflight_error_when_dirty(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Dirty working tree -> BlockerNote produced + PreflightError raised; no mutation."""
        mock_adapter.is_clean.return_value = False
        context = NoteContext()

        with pytest.raises(PreflightError, match="Working directory is not clean"):
            manager.prepare_submission(
                artifact_paths=frozenset({f"{get_default_server_root()}/state.json"}),
                base="main",
                note_context=context,
            )

        assert (
            len([n for n in context.of_type(Note) if n.key == "submit_pr_dirty_workspace_blocker"])
            == 1
        )
        mock_adapter.neutralize_to_base.assert_not_called()
        mock_adapter.push.assert_not_called()

    def test_prepare_submission_raises_preflight_error_when_no_upstream(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """No upstream -> BlockerNote produced + PreflightError raised; neutralize not called."""
        mock_adapter.is_clean.return_value = True
        mock_adapter.has_upstream.return_value = False
        context = NoteContext()

        with pytest.raises(PreflightError, match="No upstream configured for current branch"):
            manager.prepare_submission(
                artifact_paths=frozenset({f"{get_default_server_root()}/state.json"}),
                base="main",
                note_context=context,
            )

        assert (
            len([n for n in context.of_type(Note) if n.key == "submit_pr_no_upstream_blocker"]) == 1
        )
        mock_adapter.neutralize_to_base.assert_not_called()
        mock_adapter.push.assert_not_called()

    def test_prepare_submission_neutralizes_only_artifacts_with_net_diff(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Two artifacts: one with diff, one without.

        neutralize_to_base must be called with only the path that has a net diff.
        """
        mock_adapter.has_net_diff_for_path.side_effect = lambda path, _base: (
            path == f"{get_default_server_root()}/state.json"
        )
        context = NoteContext()

        manager.prepare_submission(
            artifact_paths=frozenset(
                {
                    f"{get_default_server_root()}/state.json",
                    f"{get_default_server_root()}/deliverables.json",
                }
            ),
            base="main",
            note_context=context,
        )

        mock_adapter.neutralize_to_base.assert_called_once_with(
            frozenset({f"{get_default_server_root()}/state.json"}), "main"
        )

    def test_prepare_submission_skips_neutralize_and_commit_when_no_diffs(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """No artifacts with a net diff: neutralize + commit skipped; push still called.

        Returns False (no neutralization commit was made).
        """
        mock_adapter.has_net_diff_for_path.return_value = False
        context = NoteContext()

        result = manager.prepare_submission(
            artifact_paths=frozenset(
                {
                    f"{get_default_server_root()}/state.json",
                    f"{get_default_server_root()}/deliverables.json",
                }
            ),
            base="main",
            note_context=context,
        )

        assert result is False
        mock_adapter.neutralize_to_base.assert_not_called()
        mock_adapter.commit.assert_not_called()
        mock_adapter.push.assert_called_once()

    # --- Cycle 3: conditional commit + push + rollbacks ---

    def test_prepare_submission_hard_resets_head_on_commit_failure(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Commit failure -> hard_reset('HEAD') + RecoveryNote + ExecutionError re-raised."""
        mock_adapter.has_net_diff_for_path.return_value = True
        mock_adapter.commit.side_effect = ExecutionError("commit failed")
        context = NoteContext()

        with pytest.raises(ExecutionError):
            manager.prepare_submission(
                artifact_paths=frozenset({f"{get_default_server_root()}/state.json"}),
                base="main",
                note_context=context,
            )

        mock_adapter.hard_reset.assert_called_once_with("HEAD")
        notes = [n for n in context.entries if n.key == "submit_pr_commit_failed_recovery"]
        assert len(notes) == 1
        assert "commit failed" in notes[0].params.get("error_details", "")
        mock_adapter.push.assert_not_called()

    def test_prepare_submission_hard_resets_head_minus_one_on_push_failure_after_commit(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Commit succeeds, push fails -> hard_reset('HEAD~1') + RecoveryNote + re-raised."""
        mock_adapter.has_net_diff_for_path.return_value = True
        mock_adapter.commit.return_value = "abc1234"
        mock_adapter.push.side_effect = ExecutionError("remote rejected")
        context = NoteContext()

        with pytest.raises(ExecutionError):
            manager.prepare_submission(
                artifact_paths=frozenset({f"{get_default_server_root()}/state.json"}),
                base="main",
                note_context=context,
            )

        mock_adapter.hard_reset.assert_called_once_with("HEAD~1")
        notes = [
            n for n in context.entries if n.key == "submit_pr_push_failed_with_rollback_recovery"
        ]
        assert len(notes) == 1
        assert "remote rejected" in notes[0].params.get("error_details", "")

    def test_prepare_submission_no_hard_reset_on_push_failure_when_no_commit(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """No diffs -> no commit; push fails -> hard_reset NOT called + RecoveryNote produced."""
        mock_adapter.has_net_diff_for_path.return_value = False
        mock_adapter.push.side_effect = ExecutionError("network error")
        context = NoteContext()

        with pytest.raises(ExecutionError):
            manager.prepare_submission(
                artifact_paths=frozenset({f"{get_default_server_root()}/state.json"}),
                base="main",
                note_context=context,
            )

        mock_adapter.hard_reset.assert_not_called()
        notes = [
            n for n in context.entries if n.key == "submit_pr_push_failed_no_rollback_recovery"
        ]
        assert len(notes) == 1
        assert "network error" in notes[0].params.get("error_details", "")

    def test_prepare_submission_happy_path_calls_steps_in_order(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """All succeed with artifacts present: correct call order; returns True."""
        mock_adapter.has_net_diff_for_path.return_value = True
        mock_adapter.commit.return_value = "abc1234"
        context = NoteContext()

        result = manager.prepare_submission(
            artifact_paths=frozenset({f"{get_default_server_root()}/state.json"}),
            base="main",
            note_context=context,
        )

        assert result is True
        mock_adapter.is_clean.assert_called_once()
        mock_adapter.has_upstream.assert_called_once()
        mock_adapter.has_net_diff_for_path.assert_called_once_with(
            f"{get_default_server_root()}/state.json", "main"
        )
        mock_adapter.neutralize_to_base.assert_called_once_with(
            frozenset({f"{get_default_server_root()}/state.json"}), "main"
        )
        mock_adapter.commit.assert_called_once()
        mock_adapter.push.assert_called_once()

    # --- C_228.3 RED: issue_number suffix in prepare_submission ---

    def test_prepare_submission_issue_branch_carries_suffix(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """feature/228-* branch → neutralize commit ends with ' (#228)'."""
        mock_adapter.has_net_diff_for_path.return_value = True
        mock_adapter.commit.return_value = "abc1234"
        mock_adapter.get_current_branch.return_value = "feature/228-add-issue-suffix"
        context = NoteContext()

        manager.prepare_submission(
            artifact_paths=frozenset({f"{get_default_server_root()}/state.json"}),
            base="main",
            note_context=context,
        )

        call_args = mock_adapter.commit.call_args
        assert call_args[0][0].endswith(" (#228)"), (
            f"Expected commit message to end with ' (#228)', got: {call_args[0][0]!r}"
        )

    def test_prepare_submission_main_no_suffix(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """'main' branch → neutralize commit has no issue suffix (regression guard)."""
        mock_adapter.has_net_diff_for_path.return_value = True
        mock_adapter.commit.return_value = "abc1234"
        mock_adapter.get_current_branch.return_value = "main"
        context = NoteContext()

        manager.prepare_submission(
            artifact_paths=frozenset({f"{get_default_server_root()}/state.json"}),
            base="main",
            note_context=context,
        )

        call_args = mock_adapter.commit.call_args
        assert "(#" not in call_args[0][0], (
            f"Expected no issue suffix for 'main', got: {call_args[0][0]!r}"
        )


class TestGitManagerRollbackPush:
    """C4: Tests for GitManager.rollback_push — remote rollback for Failure C."""

    @pytest.fixture()
    def mock_adapter(self) -> MagicMock:
        adapter = MagicMock(spec=GitAdapter)
        adapter.is_clean.return_value = True
        adapter.has_upstream.return_value = True
        return adapter

    @pytest.fixture()
    def manager(self, mock_adapter: MagicMock, git_config: GitConfig) -> GitManager:
        workphases = ConfigLoader(
            Path(f"{get_default_server_root()}/config")
        ).load_workphases_config()
        return GitManager(
            git_config=git_config,
            adapter=mock_adapter,
            workphases_config=workphases,
        )

    def test_rollback_push_hard_resets_and_force_pushes(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Both hard_reset and force_push_with_lease succeed; called in order; no exception."""
        context = NoteContext()

        manager.rollback_push(note_context=context)

        mock_adapter.hard_reset.assert_called_once_with("HEAD~1")
        mock_adapter.force_push_with_lease.assert_called_once()
        assert len(context.entries) == 0

    def test_rollback_push_produces_recovery_note_and_raises_on_force_push_failure(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """hard_reset succeeds; force_push_with_lease raises -> RecoveryNote + ExecutionError."""
        mock_adapter.force_push_with_lease.side_effect = ExecutionError("push rejected")
        context = NoteContext()

        with pytest.raises(ExecutionError):
            manager.rollback_push(note_context=context)

        mock_adapter.hard_reset.assert_called_once_with("HEAD~1")
        mock_adapter.force_push_with_lease.assert_called_once()
        notes = [n for n in context.entries if n.key == "rollback_remote_push_failed_recovery"]
        assert len(notes) == 1
        assert "push rejected" in notes[0].params.get("error_details", "")

    def test_rollback_push_produces_recovery_note_and_raises_on_hard_reset_failure(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """hard_reset raises -> RecoveryNote + force_push_with_lease NOT called + ExecutionError."""
        mock_adapter.hard_reset.side_effect = ExecutionError("reset failed")
        context = NoteContext()

        with pytest.raises(ExecutionError):
            manager.rollback_push(note_context=context)

        mock_adapter.hard_reset.assert_called_once_with("HEAD~1")
        mock_adapter.force_push_with_lease.assert_not_called()
        notes = [n for n in context.entries if n.key == "rollback_local_reset_failed_recovery"]
        assert len(notes) == 1
        assert "reset failed" in notes[0].params.get("error_details", "")


class TestGitManagerPush:
    """Tests for GitManager.push method and GitPushResult contract."""

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        """Fixture for mocked GitAdapter."""
        return MagicMock()

    @pytest.fixture
    def manager(self, mock_adapter: MagicMock, git_config: GitConfig) -> GitManager:
        """Fixture for GitManager with mocked adapter."""
        return GitManager(git_config=git_config, adapter=mock_adapter)

    def test_push_new_upstream_created_when_no_prior_tracking(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test push with set_upstream=True creates new tracking branch when none existed."""
        mock_adapter.get_current_branch.return_value = "feature/new"
        mock_adapter.has_upstream.side_effect = [False, True]

        result = manager.push(set_upstream=True)

        assert isinstance(result, GitPushResult)
        assert result.branch == "feature/new"
        assert result.set_upstream is True
        assert result.new_upstream_created is True
        mock_adapter.push.assert_called_once_with(set_upstream=True)

    def test_push_upstream_not_created_when_preexisting_tracking(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test push with set_upstream=True on existing tracking branch reports new_upstream_created=False."""
        mock_adapter.get_current_branch.return_value = "feature/existing"
        mock_adapter.has_upstream.side_effect = [True, True]

        result = manager.push(set_upstream=True)

        assert isinstance(result, GitPushResult)
        assert result.branch == "feature/existing"
        assert result.set_upstream is True
        assert result.new_upstream_created is False
        mock_adapter.push.assert_called_once_with(set_upstream=True)

    def test_push_without_set_upstream_does_not_create_new_upstream(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test push with set_upstream=False reports new_upstream_created=False."""
        mock_adapter.get_current_branch.return_value = "feature/existing"
        mock_adapter.has_upstream.side_effect = [False, False]

        result = manager.push(set_upstream=False)

        assert isinstance(result, GitPushResult)
        assert result.branch == "feature/existing"
        assert result.set_upstream is False
        assert result.new_upstream_created is False
        mock_adapter.push.assert_called_once_with(set_upstream=False)

    def test_push_set_upstream_fails_if_no_upstream_after(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test push with set_upstream=True raises ExecutionError if tracking is not present post-push."""
        mock_adapter.get_current_branch.return_value = "feature/broken"
        mock_adapter.has_upstream.side_effect = [False, False]

        with pytest.raises(
            ExecutionError,
            match="Requested upstream tracking branch could not be established on 'origin/feature/broken'",
        ):
            manager.push(set_upstream=True)
