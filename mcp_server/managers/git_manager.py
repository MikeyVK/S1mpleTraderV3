"""Git Manager for business logic."""

from pathlib import Path
from typing import Any

import yaml

from backend.core.scope_encoder import ScopeEncoder
from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.config.git_config import GitConfig
from mcp_server.core.exceptions import PreflightError, ValidationError
from mcp_server.core.logging import get_logger


class GitManager:
    """Manager for Git operations and conventions."""

    def __init__(
        self, adapter: GitAdapter | None = None, workphases_path: Path | None = None
    ) -> None:
        self.adapter = adapter or GitAdapter()
        self._git_config = GitConfig.from_file()
        self._workphases_path = workphases_path or Path(".st3/workphases.yaml")

    def get_status(self) -> dict[str, Any]:
        """Get git status."""
        return self.adapter.get_status()

    def create_branch(self, name: str, branch_type: str, base_branch: str) -> str:
        """Create a new branch with explicit base_branch (Issue #64).

        Args:
            name: Branch name in kebab-case
            branch_type: Type (feature, fix, refactor, docs, epic)
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
            raise ValidationError(
                f"Invalid branch type: {branch_type}",
                hints=[f"Allowed types: {', '.join(self._git_config.branch_types)}"],
            )

        # Convention #5: Branch name pattern via GitConfig
        if not self._git_config.validate_branch_name(name):
            raise ValidationError(
                f"Invalid branch name: {name}",
                hints=[f"Must match pattern: {self._git_config.branch_name_pattern}"],
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
            raise PreflightError(
                "Working directory is not clean",
                blockers=["Commit or stash changes before creating a new branch"],
            )

        self.adapter.create_branch(full_name, base=base_branch)

        logger.info(
            "Branch created successfully",
            extra={"props": {"full_name": full_name, "base_branch": base_branch}},
        )

        return full_name

    def commit_tdd_phase(self, phase: str, message: str, files: list[str] | None = None) -> str:
        """Commit changes with TDD phase prefix.

        Args:
            phase: TDD phase (red/green/refactor/docs).
            message: Commit message (without prefix).
            files: Optional list of file paths to stage + commit.
        """
        # Convention #2: Phase validation via GitConfig
        if not self._git_config.has_phase(phase):
            raise ValidationError(
                f"Invalid TDD phase: {phase}",
                hints=[f"Allowed phases: {', '.join(self._git_config.tdd_phases)}"],
            )

        if files is not None and not files:
            raise ValidationError(
                "Files list cannot be empty",
                hints=["Omit 'files' to commit everything, or provide at least one path"],
            )

        # Convention #3: Prefix mapping via GitConfig
        prefix = self._git_config.get_prefix(phase)
        full_message = f"{prefix}: {message}"
        return self.adapter.commit(full_message, files=files)

    def commit_docs(self, message: str, files: list[str] | None = None) -> str:
        """Commit changes with docs prefix.

        Args:
            message: Commit message (without prefix).
            files: Optional list of file paths to stage + commit.
        """
        if files is not None and not files:
            raise ValidationError(
                "Files list cannot be empty",
                hints=["Omit 'files' to commit everything, or provide at least one path"],
            )
        full_message = f"docs: {message}"
        return self.adapter.commit(full_message, files=files)

    def commit_with_scope(
        self,
        workflow_phase: str,
        message: str,
        sub_phase: str | None = None,
        cycle_number: int | None = None,
        files: list[str] | None = None,
    ) -> str:
        """Commit changes with workflow phase scope.

        Args:
            workflow_phase: Workflow phase (research, planning, design, tdd, ...).
            message: Commit message (without type/scope prefix).
            sub_phase: Optional subphase (red, green, refactor, c1, ...).
            cycle_number: Optional cycle number (1, 2, 3, ...).
            files: Optional list of file paths to stage + commit.

        Returns:
            Commit hash.

        Raises:
            ValueError: Invalid phase or sub_phase with actionable message.
            ValidationError: Empty files list.

        Example:
            >>> manager.commit_with_scope("tdd", "add tests", sub_phase="red")
            # Generates: "test(P_TDD_SP_RED): add tests"
        """
        if files is not None and not files:
            raise ValidationError(
                "Files list cannot be empty",
                hints=["Omit 'files' to commit everything, or provide at least one path"],
            )

        # Load workphases config to get commit_type
        with open(self._workphases_path) as f:
            workphases_config = yaml.safe_load(f)

        phases = workphases_config.get("phases", {})
        phase_config = phases.get(workflow_phase.lower())

        if phase_config is None:
            # ScopeEncoder will raise ValueError with actionable message
            encoder = ScopeEncoder(self._workphases_path)
            encoder.generate_scope(workflow_phase, sub_phase, cycle_number)
            # Should never reach here due to ValueError above
            raise RuntimeError("Unexpected: phase validation failed silently")

        commit_type = phase_config.get("commit_type", "chore")

        # Generate scope using ScopeEncoder (validates phase + subphase)
        encoder = ScopeEncoder(self._workphases_path)
        scope = encoder.generate_scope(workflow_phase, sub_phase, cycle_number)

        # Format: type(scope): message
        full_message = f"{commit_type}({scope}): {message}"
        return self.adapter.commit(full_message, files=files)

    def restore(self, files: list[str], source: str = "HEAD") -> None:
        """Restore files to a given source ref.

        Args:
            files: File paths to restore.
            source: Git ref to restore from (default HEAD).
        """
        if not files:
            raise ValidationError(
                "Files list cannot be empty",
                hints=["Provide at least one path to restore"],
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

    def pull(self, remote: str = "origin", rebase: bool = False) -> str:
        """Pull updates from a remote into the current branch.

        Responsibilities:
        - Enforce safe-by-default preflight (clean tree, not detached, upstream configured).
        - Delegate execution to GitAdapter.pull().

        Usage example:
        - manager.pull(remote="origin", rebase=False)
        """
        if not self.adapter.is_clean():
            raise PreflightError(
                "Working directory is not clean",
                blockers=["Commit or stash changes before pulling"],
            )

        if self.adapter.get_current_branch() == "HEAD":
            raise PreflightError(
                "Detached HEAD - cannot pull",
                blockers=["Checkout a branch before pulling"],
            )

        if not self.adapter.has_upstream():
            raise PreflightError(
                "No upstream configured for current branch",
                blockers=[
                    "Set upstream tracking (e.g. 'git branch --set-upstream-to=origin/<branch>')",
                    "Or pull with an explicit refspec (not supported yet)",
                ],
            )

        return self.adapter.pull(remote=remote, rebase=rebase)

    def merge(self, branch_name: str) -> None:
        """Merge a branch into current branch."""
        if not self.adapter.is_clean():
            raise PreflightError(
                "Working directory is not clean",
                blockers=["Commit or stash changes before merging"],
            )
        self.adapter.merge(branch_name)

    def delete_branch(self, branch_name: str, force: bool = False) -> None:
        """Delete a branch."""
        # Convention #4: Protected branches via GitConfig
        if self._git_config.is_protected(branch_name):
            raise ValidationError(
                f"Cannot delete protected branch: {branch_name}",
                hints=[f"Protected branches: {', '.join(self._git_config.protected_branches)}"],
            )
        self.adapter.delete_branch(branch_name, force=force)

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
