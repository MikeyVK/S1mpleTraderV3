"""Git adapter for the MCP server."""
from typing import Any

from git import InvalidGitRepositoryError, Repo

from mcp_server.config.settings import settings
from mcp_server.core import logging as core_logging
from mcp_server.core.exceptions import ExecutionError, MCPSystemError


class GitAdapter:
    """Adapter for interacting with local Git repository."""

    def __init__(self, repo_path: str | None = None) -> None:
        """Initialize the Git adapter."""
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

    def create_branch(self, branch_name: str, base: str) -> None:
        """Create a new branch from specified base.

        Args:
            branch_name: Name of the branch to create
            base: Base reference - can be 'HEAD', branch name, or commit hash

        Raises:
            ExecutionError: If branch already exists or creation fails
        """
        logger = core_logging.get_logger("git_adapter")

        # Resolve base reference
        if base == "HEAD":
            base_ref = self.repo.head.commit
            resolved_base = f"HEAD ({base_ref.hexsha[:7]})"
        else:
            base_ref = base  # type: ignore[assignment]
            resolved_base = base

        logger.debug(
            "Creating git branch",
            extra={"props": {
                "branch_name": branch_name,
                "base": base,
                "resolved_base": resolved_base,
                "current_branch": self.get_current_branch()
            }}
        )

        try:
            if branch_name in self.repo.heads:
                raise ExecutionError(f"Branch {branch_name} already exists")

            new_branch = self.repo.create_head(branch_name, base_ref)
            new_branch.checkout()

            logger.info(
                "Created and checked out branch",
                extra={"props": {
                    "branch_name": branch_name,
                    "base": resolved_base
                }}
            )
        except ExecutionError:
            raise
        except Exception as e:
            logger.error(
                "Failed to create branch",
                extra={"props": {
                    "branch_name": branch_name,
                    "base": base,
                    "error": str(e)
                }}
            )
            raise ExecutionError(f"Failed to create branch {branch_name}: {e}") from e

    def commit(self, message: str, files: list[str] | None = None) -> str:
        """Commit changes.

        Args:
            message: Commit message.
            files: Optional list of file paths to stage and commit. When omitted,
                stages all changes (equivalent to `git add .`).
        """
        try:
            if files is None:
                self.repo.git.add(".")
            else:
                self.repo.git.add(*files)
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except Exception as e:
            raise ExecutionError(f"Failed to commit: {e}") from e

    def restore(self, files: list[str], source: str = "HEAD") -> None:
        """Restore files to a given source ref (default: HEAD).

        This restores both staged and working tree changes for the given files.

        Args:
            files: List of file paths to restore.
            source: Git ref to restore from.
        """
        try:
            # Restore both index and working tree from the given source.
            self.repo.git.restore(f"--source={source}", "--staged", "--worktree", "--", *files)
        except Exception as e:
            raise ExecutionError(f"Failed to restore files: {e}") from e

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
        """Push current branch to origin.
        
        Raises:
            ExecutionError: If push is rejected (e.g., non-fast-forward)
        """
        try:
            origin = self.repo.remote("origin")
        except ValueError as e:
            raise ExecutionError(
                "No origin remote configured"
            ) from e

        try:
            branch = self.get_current_branch()
            if set_upstream:
                push_infos = origin.push(
                    refspec=f"{branch}:{branch}",
                    set_upstream=True
                )
            else:
                push_infos = origin.push()
            
            # Check push status for rejections
            for info in push_infos:
                # PushInfo flags: ERROR=1, REJECTED=1024, REMOTE_REJECTED=2048
                if info.flags & (1 | 1024 | 2048):
                    raise ExecutionError(
                        f"Push rejected: {info.summary}"
                    )
        except ExecutionError:
            # Re-raise our own ExecutionErrors
            raise
        except Exception as e:
            raise ExecutionError(f"Failed to push: {e}") from e

    def fetch(self, remote: str = "origin", prune: bool = False) -> str:
        """Fetch updates from a remote.

        Responsibilities:
        - Perform a non-interactive fetch (disable pager/prompts) to avoid stdio hangs.

        Usage example:
        - adapter.fetch(remote="origin", prune=False)

        Args:
            remote: Remote name (default: origin).
            prune: Whether to prune deleted remote-tracking branches.

        Returns:
            A short human-readable summary.

        Raises:
            ExecutionError: When remote is missing or fetch fails.
        """
        try:
            # Ensure non-interactive behavior even when Git spawns subprocesses.
            self.repo.git.update_environment(
                GIT_TERMINAL_PROMPT="0",
                GIT_PAGER="cat",
                PAGER="cat",
            )

            remote_obj = self.repo.remote(remote)
            fetch_info = remote_obj.fetch(prune=prune)
            return f"Fetched from {remote}: {len(fetch_info)} ref(s)"
        except ValueError as e:
            raise ExecutionError(
                f"Remote '{remote}' is not configured",
                recovery=[
                    "Configure a remote (e.g. 'origin')",
                    "Check remotes via 'git remote -v'",
                ],
            ) from e
        except Exception as e:
            raise ExecutionError(f"Failed to fetch from remote '{remote}': {e}") from e


    def has_upstream(self) -> bool:
        """Check whether the current branch has an upstream tracking branch.

        Responsibilities:
        - Provide a safe upstream presence check for GitManager preflight.

        Usage example:
        - adapter.has_upstream()

        Returns:
            True if the active branch has a tracking branch; False otherwise.
        """
        try:
            # Detached head raises TypeError in get_current_branch; active_branch access
            # can raise in detached states.
            tracking = self.repo.active_branch.tracking_branch()
            return tracking is not None
        except TypeError:
            return False
        except Exception as e:
            raise ExecutionError(f"Failed to check upstream: {e}") from e

    def pull(self, remote: str = "origin", rebase: bool = False) -> str:
        """Pull updates from a remote into the current branch.

        Responsibilities:
        - Perform a non-interactive pull (disable pager/prompts) to avoid stdio hangs.

        Usage example:
        - adapter.pull(remote="origin", rebase=False)

        Args:
            remote: Remote name (default: origin).
            rebase: Use --rebase instead of merge.

        Returns:
            A short human-readable summary.

        Raises:
            ExecutionError: When remote is missing or pull fails.
        """
        try:
            self.repo.git.update_environment(
                GIT_TERMINAL_PROMPT="0",
                GIT_PAGER="cat",
                PAGER="cat",
            )

            # Validate remote exists early for clearer errors.
            self.repo.remote(remote)

            args: list[str] = [remote]
            if rebase:
                args.append("--rebase")

            output = str(self.repo.git.pull(*args)).strip()
            if output:
                return output
            return f"Pulled from {remote}"
        except ValueError as e:
            raise ExecutionError(
                f"Remote '{remote}' is not configured",
                recovery=[
                    "Configure a remote (e.g. 'origin')",
                    "Check remotes via 'git remote -v'",
                ],
            ) from e
        except Exception as e:
            raise ExecutionError(f"Failed to pull from remote '{remote}': {e}") from e
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

    def stash(self, message: str | None = None, include_untracked: bool = False) -> None:
        """Stash current changes.

        Args:
            message: Optional message for the stash entry.
            include_untracked: Include untracked files in the stash entry.
        """
        try:
            args: list[str] = ["push"]
            if include_untracked:
                args.append("-u")
            if message:
                args.extend(["-m", message])
            self.repo.git.stash(*args)
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
            output = str(self.repo.git.stash("list"))
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
            output = str(self.repo.git.branch(*args))
            if not output:
                return []
            return [line.strip() for line in output.split("\n") if line.strip()]
        except Exception as e:
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
            # Usually strict comparison 'target...source' is better for
            # "what is in source that is not in target"
            # Command: git diff target...source --stat
            return str(self.repo.git.diff(f"{target}...{source}", "--stat"))
        except Exception as e:
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
