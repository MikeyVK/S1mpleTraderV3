"""Git adapter for the MCP server."""
from typing import Any

from git import InvalidGitRepositoryError, Repo  # type: ignore[import-untyped]

from mcp_server.config.settings import settings
from mcp_server.core.exceptions import ExecutionError, MCPSystemError


class GitAdapter:
    """Adapter for interacting with local Git repository."""

    def __init__(self, repo_path: str | None = None) -> None:
        """Initialize the Git adapter."""
        # pylint: disable=no-member
        self.repo_path = repo_path or settings.server.workspace_root
        self._repo: Repo | None = None

    @property
    def repo(self) -> Repo:
        """Get the git repository object."""
        if not self._repo:
            try:
                self._repo = Repo(self.repo_path)
            except InvalidGitRepositoryError as e:
                raise MCPSystemError(
                    f"Invalid git repository at {self.repo_path}",
                    fallback="Initialize git repository"
                ) from e
            except Exception as e:
                raise MCPSystemError(f"Failed to access git repo: {e}") from e
        return self._repo

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        try:
            return self.repo.active_branch.name
        except TypeError:
            # Detached head
            return "HEAD"
        except Exception as e:
            raise ExecutionError(f"Failed to get current branch: {e}") from e

    def is_clean(self) -> bool:
        """Check if the working directory is clean."""
        return not self.repo.is_dirty() and not self.repo.untracked_files

    def get_status(self) -> dict[str, Any]:
        """Get the current git status."""
        return {
            "branch": self.get_current_branch(),
            "is_clean": self.is_clean(),
            "is_dirty": self.repo.is_dirty(),
            "untracked_files": self.repo.untracked_files,
            "modified_files": [item.a_path for item in self.repo.index.diff(None)]
        }

    def create_branch(self, branch_name: str, base: str = "main") -> None:
        """Create a new branch."""
        try:
            if branch_name in self.repo.heads:
                raise ExecutionError(f"Branch {branch_name} already exists")

            # Ensure we have the base branch (in a real scenario, we might want to fetch first)
            # For now, we assume local operation

            new_branch = self.repo.create_head(branch_name, base)
            new_branch.checkout()
        except Exception as e:
            raise ExecutionError(f"Failed to create branch {branch_name}: {e}") from e

    def commit(self, message: str) -> str:
        """Commit changes."""
        try:
            self.repo.git.add(".")
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except Exception as e:
            raise ExecutionError(f"Failed to commit: {e}") from e

    def checkout(self, branch_name: str) -> None:
        """Checkout to an existing branch."""
        try:
            if branch_name not in self.repo.heads:
                raise ExecutionError(f"Branch {branch_name} does not exist")
            self.repo.heads[branch_name].checkout()
        except ExecutionError:
            raise
        except Exception as e:
            raise ExecutionError(f"Failed to checkout {branch_name}: {e}") from e

    def push(self, set_upstream: bool = False) -> None:
        """Push current branch to origin."""
        try:
            origin = self.repo.remote("origin")
        except ValueError as e:
            raise ExecutionError(
                "No origin remote configured"
            ) from e

        try:
            branch = self.get_current_branch()
            if set_upstream:
                origin.push(refspec=f"{branch}:{branch}", set_upstream=True)
            else:
                origin.push()
        except Exception as e:
            raise ExecutionError(f"Failed to push: {e}") from e

    def merge(self, branch_name: str) -> None:
        """Merge a branch into current branch."""
        try:
            if branch_name not in self.repo.heads:
                raise ExecutionError(f"Branch {branch_name} does not exist")
            self.repo.git.merge(branch_name)
        except ExecutionError:
            raise
        except Exception as e:
            raise ExecutionError(f"Failed to merge {branch_name}: {e}") from e

    def delete_branch(self, branch_name: str, force: bool = False) -> None:
        """Delete a branch."""
        try:
            if branch_name not in self.repo.heads:
                raise ExecutionError(f"Branch {branch_name} does not exist")
            if self.get_current_branch() == branch_name:
                raise ExecutionError(
                    f"Cannot delete current branch {branch_name}"
                )
            self.repo.delete_head(branch_name, force=force)
        except ExecutionError:
            raise
        except Exception as e:
            raise ExecutionError(f"Failed to delete {branch_name}: {e}") from e

    def stash(self, message: str | None = None) -> None:
        """Stash current changes.

        Args:
            message: Optional message for the stash entry.
        """
        try:
            if message:
                self.repo.git.stash("push", "-m", message)
            else:
                self.repo.git.stash("push")
        except Exception as e:
            raise ExecutionError(f"Failed to stash changes: {e}") from e

    def stash_pop(self) -> None:
        """Pop the latest stash entry."""
        try:
            self.repo.git.stash("pop")
        except Exception as e:
            raise ExecutionError(f"Failed to pop stash: {e}") from e

    def stash_list(self) -> list[str]:
        """List all stash entries.

        Returns:
            List of stash entry descriptions.
        """
        try:
            output = self.repo.git.stash("list")
            if not output:
                return []
            return output.strip().split("\n")
        except Exception as e:
            raise ExecutionError(f"Failed to list stashes: {e}") from e

    def list_branches(self, verbose: bool = False, remote: bool = False) -> list[str]:
        """List branches with optional verbose info and remotes.

        Args:
            verbose: Include upstream/hash info (-vv)
            remote: Include remote branches (-r)

        Returns:
            List of raw branch strings
        """
        try:
            args = []
            if remote:
                args.append("-r")
            if verbose:
                args.append("-vv")

            # GitPython's repo.git.branch returns the raw string output
            output = self.repo.git.branch(*args)
            if not output:
                return []
            return [line.strip() for line in output.split("\n") if line.strip()]
        except Exception as e:  # pylint: disable=broad-exception-caught
            raise ExecutionError(f"Failed to list branches: {e}") from e

    def get_diff_stat(self, target: str, source: str = "HEAD") -> str:
        """Get diff statistics between two references.

        Args:
            target: Target reference (e.g. main)
            source: Source reference (default HEAD)

        Returns:
            Diff stat string
        """
        try:
            # git diff source...target --stat (triple dot for merge base comparison?)
            # Usually strict comparison 'target...source' is better for "what is in source that is not in target"
            # Command: git diff target...source --stat
            return self.repo.git.diff(f"{target}...{source}", "--stat")
        except Exception as e:  # pylint: disable=broad-exception-caught
            raise ExecutionError(f"Failed to get diff stat: {e}") from e

    def get_recent_commits(self, limit: int = 5) -> list[str]:
        """Get recent commit messages.

        Args:
            limit: Maximum number of commits to return.

        Returns:
            List of commit messages (most recent first).
        """
        try:
            commits = list(self.repo.iter_commits(max_count=limit))
            return [
                str(commit.message).split("\n", maxsplit=1)[0]
                for commit in commits
            ]
        except Exception as e:
            raise ExecutionError(f"Failed to get recent commits: {e}") from e
