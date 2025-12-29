"""Git Manager for business logic."""
import re
from typing import Any

from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.core.exceptions import PreflightError, ValidationError


class GitManager:
    """Manager for Git operations and conventions."""

    def __init__(self, adapter: GitAdapter | None = None) -> None:
        self.adapter = adapter or GitAdapter()

    def get_status(self) -> dict[str, Any]:
        """Get git status."""
        return self.adapter.get_status()


    def create_branch(self, name: str, branch_type: str, base_branch: str) -> str:
        """Create a new branch with explicit base_branch (Issue #64).

        Args:
            name: Branch name in kebab-case
            branch_type: Type (feature, fix, refactor, docs)
            base_branch: Base to create from (required - no default!)

        Returns:
            Full branch name (e.g., 'feature/123-my-feature')

        Raises:
            ValidationError: If name or type invalid
            PreflightError: If working directory not clean
        """
        from mcp_server.core.logging import get_logger  # pylint: disable=import-outside-toplevel
        logger = get_logger("managers.git")

        # Validation
        if branch_type not in ["feature", "fix", "refactor", "docs"]:
            raise ValidationError(
                f"Invalid branch type: {branch_type}",
                hints=["Use feature, fix, refactor, or docs"]
            )

        if not re.match(r"^[a-z0-9-]+$", name):
            raise ValidationError(
                f"Invalid branch name: {name}",
                hints=["Use kebab-case (lowercase, numbers, hyphens only)"]
            )

        full_name = f"{branch_type}/{name}"

        current_branch = self.adapter.get_current_branch()

        logger.info(
            "Creating branch",
            extra={"props": {
                "full_name": full_name,
                "branch_type": branch_type,
                "base_branch": base_branch,
                "current_branch": current_branch
            }}
        )

        # Pre-flight check
        if not self.adapter.is_clean():
            raise PreflightError(
                "Working directory is not clean",
                blockers=["Commit or stash changes before creating a new branch"]
            )

        self.adapter.create_branch(full_name, base=base_branch)

        logger.info(
            "Branch created successfully",
            extra={"props": {
                "full_name": full_name,
                "base_branch": base_branch
            }}
        )

        return full_name

    def commit_tdd_phase(self, phase: str, message: str, files: list[str] | None = None) -> str:
        """Commit changes with TDD phase prefix.

        Args:
            phase: TDD phase (red/green/refactor).
            message: Commit message (without prefix).
            files: Optional list of file paths to stage + commit.
        """
        if phase not in ["red", "green", "refactor"]:
            raise ValidationError(
                f"Invalid TDD phase: {phase}",
                hints=["Use red, green, or refactor"]
            )

        if files is not None and not files:
            raise ValidationError(
                "Files list cannot be empty",
                hints=["Omit 'files' to commit everything, or provide at least one path"]
            )

        prefix_map = {
            "red": "test",
            "green": "feat",
            "refactor": "refactor"
        }

        full_message = f"{prefix_map[phase]}: {message}"
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
                hints=["Omit 'files' to commit everything, or provide at least one path"]
            )
        full_message = f"docs: {message}"
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
                hints=["Provide at least one path to restore"]
            )
        self.adapter.restore(files=files, source=source)

    def checkout(self, branch_name: str) -> None:
        """Checkout to an existing branch."""
        self.adapter.checkout(branch_name)

    def push(self, set_upstream: bool = False) -> None:
        """Push current branch to origin."""
        self.adapter.push(set_upstream=set_upstream)

    def merge(self, branch_name: str) -> None:
        """Merge a branch into current branch."""
        if not self.adapter.is_clean():
            raise PreflightError(
                "Working directory is not clean",
                blockers=["Commit or stash changes before merging"]
            )
        self.adapter.merge(branch_name)

    def delete_branch(self, branch_name: str, force: bool = False) -> None:
        """Delete a branch."""
        protected_branches = ["main", "master", "develop"]
        if branch_name in protected_branches:
            raise ValidationError(
                f"Cannot delete protected branch: {branch_name}",
                hints=[f"Protected branches: {', '.join(protected_branches)}"]
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
