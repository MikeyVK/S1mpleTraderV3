# mcp_server/managers/git_manager.py
"""
Git Manager — business logic for git workflow conventions.

Coordinates git operations with workflow-phase awareness. Delegates all raw
git calls to GitAdapter. Applies branch-naming conventions, scope encoding,
and commit message formatting based on the active workflow state.

@layer: Backend (Managers)
@dependencies: [yaml, mcp_server.adapters.git_adapter, mcp_server.core.exceptions,
                mcp_server.core.logging, mcp_server.core.scope_encoder,
                mcp_server.schemas]
@responsibilities:
    - Enforce branch naming and type validation (via GitConfig)
    - Generate scoped commit messages (type(scope): message)
    - Forward skip_paths to GitAdapter.commit() unchanged
    - Pre-flight checks (clean working directory) before branch operations
"""

from dataclasses import dataclass
from typing import Any, Literal

from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.core.exceptions import ExecutionError, PreflightError, ValidationError
from mcp_server.core.logging import get_logger
from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.core.scope_encoder import ScopeEncoder
from mcp_server.schemas import GitConfig, WorkphasesConfig


@dataclass(frozen=True)
class BranchDeleteResult:
    """Result of a branch deletion operation."""

    local_status: Literal["deleted", "absent", "skipped"]
    remote_status: Literal["deleted", "absent", "skipped"]


class GitManager:
    """Manager for Git operations and conventions."""

    def __init__(
        self,
        git_config: GitConfig,
        adapter: GitAdapter | None = None,
        workphases_config: WorkphasesConfig | None = None,
    ) -> None:
        self.adapter = adapter or GitAdapter()
        self._git_config = git_config
        self._workphases_config = workphases_config

    @property
    def git_config(self) -> GitConfig:
        """Expose injected git conventions config to consumers."""
        return self._git_config

    def get_status(self) -> dict[str, Any]:
        """Get git status."""
        return self.adapter.get_status()

    def create_branch(
        self, name: str, branch_type: str, base_branch: str, note_context: NoteContext
    ) -> str:
        """Create a new branch with explicit base_branch (Issue #64).

        Args:
            name: Branch name in kebab-case
            branch_type: Configured branch type from GitConfig
            base_branch: Base to create from (required - no default!)

        Returns:
            Full branch name (e.g., 'feature/123-my-feature')

        Raises:
            ValidationError: If name or type invalid
            PreflightError: If working directory not clean
        """
        logger = get_logger("managers.git")

        # Convention #1: Branch type validation via GitConfig
        if not self._git_config.has_branch_type(branch_type):
            note_context.produce(
                Note(
                    key="allowed_branch_types",
                    params={"types": ", ".join(self._git_config.branch_types)},
                )
            )
            raise ValidationError(
                f"Invalid branch type: {branch_type}",
                error_code="invalid_branch_type",
                params={"branch_type": branch_type},
            )

        # Convention #5: Branch name pattern via GitConfig
        if not self._git_config.validate_branch_name(name):
            note_context.produce(
                Note(
                    key="branch_name_pattern_mismatch",
                    params={"pattern": self._git_config.branch_name_pattern},
                )
            )
            raise ValidationError(
                f"Invalid branch name: {name}",
                error_code="invalid_branch_name",
                params={"name": name},
            )

        full_name = f"{branch_type}/{name}"

        current_branch = self.adapter.get_current_branch()

        logger.info(
            "Creating branch",
            extra={
                "props": {
                    "full_name": full_name,
                    "branch_type": branch_type,
                    "base_branch": base_branch,
                    "current_branch": current_branch,
                }
            },
        )

        # Pre-flight check
        if not self.adapter.is_clean():
            note_context.produce(
                Note(
                    key="dirty_workspace_branch_blocker",
                    params={},
                )
            )
            raise PreflightError(
                "Working directory is not clean",
                error_code="dirty_workdir",
                params={"branch": current_branch},
            )

        self.adapter.create_branch(full_name, base=base_branch)

        logger.info(
            "Branch created successfully",
            extra={"props": {"full_name": full_name, "base_branch": base_branch}},
        )

        return full_name

    def commit_with_scope(
        self,
        workflow_phase: str,
        message: str,
        note_context: NoteContext,
        sub_phase: str | None = None,
        cycle_number: int | None = None,
        commit_type: str | None = None,
        files: list[str] | None = None,
        skip_paths: frozenset[str] = frozenset(),
        issue_number: int | None = None,
    ) -> str:
        """Commit changes with workflow phase scope.

        Args:
            workflow_phase: Workflow phase (research, planning, design, implementation, ...).
            message: Commit message (without type/scope prefix).
            sub_phase: Optional subphase (red, green, refactor, c1, ...).
            cycle_number: Optional cycle number (1, 2, 3, ...).
            commit_type: Optional commit type override (test, feat, refactor, docs, chore, fix).
                        Auto-determined from workphases.yaml if omitted.
            files: Optional list of file paths to stage + commit.
            skip_paths: Paths forwarded to GitAdapter.commit() as a postcondition.
                Each path is removed from the staging index after all staging,
                producing zero delta in the commit. Defaults to frozenset().

        Returns:
            Commit hash.

        Raises:
            ValueError: Invalid phase or sub_phase with actionable message.
            ValidationError: Empty files list.

        Example:
            >>> manager.commit_with_scope("implementation", "add tests", sub_phase="red")
            # Generates: "test(P_TDD_SP_RED): add tests"

            >>> manager.commit_with_scope(
            ...     "implementation",
            ...     "add tests",
            ...     sub_phase="red",
            ...     commit_type="fix",
            ... )
            # Generates: "fix(P_TDD_SP_RED): add tests" (override)
        """
        if files is not None and not files:
            note_context.produce(
                Note(
                    key="commit_empty_files_suggestion",
                    params={},
                )
            )
            raise ValidationError(
                "Files list cannot be empty",
                error_code="empty_files_list",
                params={},
            )

        if self._workphases_config is None:
            raise RuntimeError(
                "workphases_config is required for commit_with_scope. "
                "Pass workphases_config= to GitManager constructor."
            )

        # If commit_type override provided, use it
        if commit_type is None:
            phases = self._workphases_config.phases
            phase_config = phases.get(workflow_phase.lower())

            if phase_config is None:
                # ScopeEncoder will raise ValueError with actionable message
                encoder = ScopeEncoder(self._workphases_config)
                encoder.generate_scope(workflow_phase, sub_phase, cycle_number)
                # Should never reach here due to ValueError above
                raise RuntimeError("Unexpected: phase validation failed silently")

            commit_type = phase_config.commit_type_hint or "chore"

        # Generate scope using ScopeEncoder (validates phase + subphase)
        encoder = ScopeEncoder(self._workphases_config)
        scope = encoder.generate_scope(workflow_phase, sub_phase, cycle_number)

        # Format: type(scope): message (#NNN)
        suffix = f" (#{issue_number})" if issue_number is not None else ""
        full_message = f"{commit_type}({scope}): {message}{suffix}"
        return self.adapter.commit(full_message, files=files, skip_paths=skip_paths)

    def restore(self, files: list[str], note_context: NoteContext, source: str = "HEAD") -> None:
        """Restore files to a given source ref.

        Args:
            files: File paths to restore.
            note_context: NoteContext for typed note production.
            source: Git ref to restore from (default HEAD).
        """
        if not files:
            note_context.produce(
                Note(
                    key="restore_empty_files_suggestion",
                    params={},
                )
            )
            raise ValidationError(
                "Files list cannot be empty",
                error_code="empty_files_list",
                params={},
            )
        self.adapter.restore(files=files, source=source)

    def checkout(self, branch_name: str) -> None:
        """Checkout to an existing branch."""
        self.adapter.checkout(branch_name)

    def push(self, set_upstream: bool = False) -> None:
        """Push current branch to origin."""
        self.adapter.push(set_upstream=set_upstream)

    def fetch(self, remote: str = "origin", prune: bool = False) -> str:
        """Fetch updates from a remote.

        Responsibilities:
        - Delegate to GitAdapter.fetch().

        Usage example:
        - manager.fetch(remote="origin", prune=False)

        Notes:
        - Fetch is allowed even when the working tree is dirty.
        """
        return self.adapter.fetch(remote=remote, prune=prune)

    def pull(self, note_context: NoteContext, remote: str = "origin", rebase: bool = False) -> str:
        """Pull updates from a remote into the current branch.

        Responsibilities:
        - Enforce safe-by-default preflight (clean tree, not detached, upstream configured).
        - Delegate execution to GitAdapter.pull().

        Usage example:
        - manager.pull(note_context, remote="origin", rebase=False)
        """
        if not self.adapter.is_clean():
            note_context.produce(
                Note(
                    key="pull_dirty_workspace_blocker",
                    params={},
                )
            )
            raise PreflightError(
                "Working directory is not clean",
                error_code="dirty_workdir",
                params={"branch": self.adapter.get_current_branch()},
            )

        if self.adapter.get_current_branch() == "HEAD":
            note_context.produce(Note(key="pull_detached_head_blocker", params={}))

        if not self.adapter.has_upstream():
            note_context.produce(
                Note(
                    key="pull_no_upstream_blocker",
                    params={},
                )
            )
            note_context.produce(
                Note(
                    key="pull_refspec_not_supported_blocker",
                    params={},
                )
            )
            raise PreflightError(
                "No upstream configured for current branch",
                error_code="no_upstream",
                params={"branch": self.adapter.get_current_branch()},
            )

        return self.adapter.pull(remote=remote, rebase=rebase)

    def merge(self, branch_name: str, note_context: NoteContext) -> None:
        """Merge a branch into current branch."""
        if not self.adapter.is_clean():
            note_context.produce(
                Note(
                    key="merge_dirty_workspace_blocker",
                    params={},
                )
            )
            raise PreflightError(
                "Working directory is not clean",
                error_code="dirty_workdir",
                params={"branch": self.adapter.get_current_branch()},
            )
        self.adapter.merge(branch_name)

    def delete_branch(
        self,
        branch_name: str,
        note_context: NoteContext,
        force: bool = False,
        mode: Literal["local", "remote", "both"] = "both",
    ) -> BranchDeleteResult:
        """Delete a branch locally, remotely, or both."""
        # Convention #4: Protected branches via GitConfig
        if self._git_config.is_protected(branch_name):
            protected_list = ", ".join(self._git_config.protected_branches)
            note_context.produce(
                Note(
                    key="delete_protected_branch_suggestion",
                    params={"protected_branches": protected_list},
                )
            )
            raise ValidationError(
                f"Cannot delete protected branch: {branch_name}",
                error_code="cannot_delete_protected_branch",
                params={"branch_name": branch_name},
            )

        local_status: Literal["deleted", "absent", "skipped"] = "skipped"
        remote_status: Literal["deleted", "absent", "skipped"] = "skipped"

        if mode in ("local", "both"):
            try:
                self.adapter.delete_local_branch(branch_name, force=force)
                local_status = "deleted"
            except ExecutionError as e:
                if "does not exist" in str(e):
                    local_status = "absent"
                else:
                    raise

        if mode in ("remote", "both"):
            remote_status = self.adapter.delete_remote_branch(branch_name)

        return BranchDeleteResult(local_status=local_status, remote_status=remote_status)

    def stash(self, message: str | None = None, include_untracked: bool = False) -> None:
        """Stash current changes.

        Args:
            message: Optional message for the stash entry.
            include_untracked: Include untracked files in the stash entry.
        """
        self.adapter.stash(message=message, include_untracked=include_untracked)

    def stash_pop(self) -> None:
        """Pop the latest stash entry."""
        self.adapter.stash_pop()

    def stash_list(self) -> list[str]:
        """List all stash entries.

        Returns:
            List of stash entry descriptions.
        """
        return self.adapter.stash_list()

    def get_current_branch(self) -> str:
        """Get the current branch name.

        Returns:
            Current branch name.
        """
        return self.adapter.get_current_branch()

    def has_net_diff_for_path(self, path: str, base: str) -> bool:
        """Return True if *path* has a net delta between the merge-base and HEAD.

        Delegates to GitAdapter.has_net_diff_for_path.
        """
        return self.adapter.has_net_diff_for_path(path, base)

    def neutralize_to_base(self, paths: frozenset[str], base: str) -> None:
        """Align each path in *paths* to the state at the merge-base of HEAD and *base*.

        Delegates to GitAdapter.neutralize_to_base.
        """
        self.adapter.neutralize_to_base(paths, base)

    def list_branches(self, verbose: bool = False, remote: bool = False) -> list[str]:
        """List branches with optional details.

        Args:
            verbose: Include upstream/hash info.
            remote: Include remote branches.

        Returns:
            List of branch strings.
        """
        return self.adapter.list_branches(verbose=verbose, remote=remote)

    def compare_branches(self, target: str, source: str = "HEAD") -> str:
        """Compare two branches and return diff stat.

        Args:
            target: Target branch (e.g. main).
            source: Source branch (default HEAD).

        Returns:
            Diff statistics.
        """
        return self.adapter.get_diff_stat(target, source)

    def get_recent_commits(self, limit: int = 5) -> list[str]:
        """Get recent commit messages.

        Args:
            limit: Maximum number of commits to return.

        Returns:
            List of commit messages (most recent first).
        """
        return self.adapter.get_recent_commits(limit=limit)

    def prepare_submission(
        self,
        artifact_paths: frozenset[str],
        base: str,
        note_context: NoteContext,
    ) -> bool:
        """Atomically execute the full git side of branch submission.

        Steps (in order):
            1. Preflight — is_clean(): if False -> BlockerNote + PreflightError (no mutation)
            2. Preflight — has_upstream(): if False -> BlockerNote + PreflightError (no mutation)
            3. Filter    — for each path in artifact_paths: has_net_diff_for_path(path, base)
                           -> collect to_neutralize: frozenset[str]
            4. Neutralize (only when to_neutralize is not empty)
            5. Commit    (only when to_neutralize is not empty) [Cycle 3]
            6. Push      — always [Cycle 3 adds rollbacks]

        Args:
            artifact_paths: Full set of candidate branch-local artifact paths to check.
            base:           Base branch name (e.g. "main").
            note_context:   NoteContext for BlockerNote / RecoveryNote production.

        Returns:
            True if a neutralization commit was made. False otherwise.
            # CQS note: returns bool to gate rollback_push eligibility in SubmitPRTool.

        Raises:
            PreflightError:  If working tree is not clean or no upstream is configured.
            ExecutionError:  If commit or push fails (after rollback attempt).
        """
        # Step 1: dirty-tree preflight (root-cause fix for Failure B)
        if not self.adapter.is_clean():
            note_context.produce(
                Note(
                    key="submit_pr_dirty_workspace_blocker",
                    params={},
                )
            )
            raise PreflightError(
                "Working directory is not clean",
                error_code="dirty_workdir",
                params={"branch": self.adapter.get_current_branch()},
            )

        # Step 2: upstream preflight (Failure A)
        if not self.adapter.has_upstream():
            note_context.produce(
                Note(
                    key="submit_pr_no_upstream_blocker",
                    params={},
                )
            )
            raise PreflightError(
                "No upstream configured for current branch",
                error_code="no_upstream",
                params={"branch": self.adapter.get_current_branch()},
            )

        # Step 3: filter artifacts that have a net diff against base
        to_neutralize = frozenset(
            path for path in artifact_paths if self.adapter.has_net_diff_for_path(path, base)
        )

        # Step 4: conditional neutralize
        if to_neutralize:
            self.adapter.neutralize_to_base(to_neutralize, base)

        # Step 5: conditional commit (only when artifacts were neutralized)
        commit_made = False
        if to_neutralize:
            try:
                branch = self.adapter.get_current_branch()
                issue_number = self._git_config.extract_issue_number(branch)
                self.commit_with_scope(
                    workflow_phase="ready",
                    message=f"neutralize branch-local artifacts to '{base}'",
                    note_context=note_context,
                    commit_type="chore",
                    issue_number=issue_number,
                )
                commit_made = True
            except ExecutionError as exc:
                self.adapter.hard_reset("HEAD")
                note_context.produce(
                    Note(
                        key="submit_pr_commit_failed_recovery",
                        params={"error_details": str(exc)},
                    )
                )
                raise

        # Step 6: push (always); rollback depends on whether a commit was made
        try:
            self.adapter.push()
        except ExecutionError as exc:
            if commit_made:
                self.adapter.hard_reset("HEAD~1")
                note_context.produce(
                    Note(
                        key="submit_pr_push_failed_with_rollback_recovery",
                        params={"error_details": str(exc)},
                    )
                )
            else:
                note_context.produce(
                    Note(
                        key="submit_pr_push_failed_no_rollback_recovery",
                        params={"error_details": str(exc)},
                    )
                )
            raise

        return bool(to_neutralize)

    def rollback_push(self, note_context: NoteContext) -> None:
        """Roll back a pushed commit from the remote.

        Performs a local hard_reset to HEAD~1 then force-pushes to the remote.
        This is the recovery path for Failure C (GitHub API failure after push).

        Args:
            note_context: NoteContext for RecoveryNote production on meta-failure.

        Raises:
            ExecutionError: If hard_reset or force_push_with_lease fails.
                            On hard_reset failure, force_push is NOT attempted.
        """
        try:
            self.adapter.hard_reset("HEAD~1")
        except ExecutionError as exc:
            note_context.produce(
                Note(
                    key="rollback_local_reset_failed_recovery",
                    params={"error_details": str(exc)},
                )
            )
            raise

        try:
            self.adapter.force_push_with_lease()
        except ExecutionError as exc:
            note_context.produce(
                Note(
                    key="rollback_remote_push_failed_recovery",
                    params={"error_details": str(exc)},
                )
            )
            raise

    def is_ancestor(self, sha: str) -> bool:
        """Return True if sha is an ancestor of HEAD; False otherwise.

        Delegates to GitAdapter.is_ancestor. Raises ExecutionError on git error (status >=2).
        """
        return self.adapter.is_ancestor(sha)
