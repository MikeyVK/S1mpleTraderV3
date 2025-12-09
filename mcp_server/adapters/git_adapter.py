"""Git adapter for the MCP server."""
from typing import Any

from git import Repo, InvalidGitRepositoryError  # type: ignore[import-untyped]

from mcp_server.core.exceptions import MCPSystemError, ExecutionError
from mcp_server.config.settings import settings


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
