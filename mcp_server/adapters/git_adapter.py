# mcp_server/adapters/git_adapter.py
"""
Git Adapter — local git repository operations.

Wraps GitPython's Repo object with a domain-facing API. All git operations
performed by the MCP server route through this adapter. Sole owner of all
git staging and unstaging operations, including the skip_paths zero-delta
postcondition: every path in skip_paths is removed from the index via
git restore --staged before index.commit().

@layer: Backend (Adapters)
@dependencies: [GitPython, mcp_server.config.settings, mcp_server.core.exceptions,
                mcp_server.core.logging]
@responsibilities:
    - Expose git operations (commit, checkout, branch, push, fetch, restore)
    - Enforce skip_paths postcondition: restore --staged for each path after
      all staging, before index.commit()
    - Raise ExecutionError / MCPSystemError on git failures
"""

from pathlib import Path
from typing import Any

from git import InvalidGitRepositoryError, Repo

from mcp_server.config.settings import Settings
from mcp_server.core import logging as core_logging
from mcp_server.core.exceptions import ExecutionError, MCPSystemError


class GitAdapter:
    """Adapter for interacting with local Git repository."""

    def __init__(
        self,
        repo_path: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the Git adapter."""
        base_repo_path = repo_path or (
            settings.server.workspace_root if settings else str(Path.cwd())
        )
        self.repo_path = base_repo_path
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
                    fallback="Initialize git repository",
                ) from e
            except Exception as e:
                raise MCPSystemError(f"Failed to access git repo: {e}") from e
        return self._repo

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        try:
            return self.repo.active_branch.name
        except TypeError:
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
            "modified_files": [item.a_path for item in self.repo.index.diff(None)],
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

        if base == "HEAD":
            base_ref = self.repo.head.commit
            resolved_base = f"HEAD ({base_ref.hexsha[:7]})"
        else:
            base_ref = base  # type: ignore[assignment]
            resolved_base = base

        logger.debug(
            "Creating git branch",
            extra={
                "props": {
                    "branch_name": branch_name,
                    "base": base,
                    "resolved_base": resolved_base,
                    "current_branch": self.get_current_branch(),
                }
            },
        )

        try:
            if branch_name in self.repo.heads:
                raise ExecutionError(f"Branch {branch_name} already exists")

            new_branch = self.repo.create_head(branch_name, base_ref)
            new_branch.checkout()

            logger.info(
                "Created and checked out branch",
                extra={"props": {"branch_name": branch_name, "base": resolved_base}},
            )
        except ExecutionError:
            raise
        except Exception as e:
            logger.error(
                "Failed to create branch",
                extra={"props": {"branch_name": branch_name, "base": base, "error": str(e)}},
            )
            raise ExecutionError(f"Failed to create branch {branch_name}: {e}") from e

    def commit(
        self,
        message: str,
        files: list[str] | None = None,
        skip_paths: frozenset[str] = frozenset(),
    ) -> str:
        """Commit changes.

        Args:
            message: Commit message.
            files: Optional list of file paths to stage and commit. When omitted,
                stages all changes (equivalent to `git add .`).
            skip_paths: Paths to remove from the staging index after all staging.
                Applied unconditionally as a postcondition regardless of the
                `files=` route used. Produces zero delta for these paths in the
                resulting commit. Defaults to frozenset() — no-op.
        """
        try:
            if files is None:
                self.repo.git.add(".")
            else:
                self.repo.git.add(*files)
            for path in skip_paths:
                self.repo.git.restore("--staged", path)
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except Exception as e:
            raise ExecutionError(f"Failed to commit changes: {e}") from e

    def restore(self, files: list[str], source: str = "HEAD") -> None:
        """Restore files to a given source ref (default: HEAD)."""
        try:
            self.repo.git.restore(f"--source={source}", "--staged", "--worktree", "--", *files)
        except Exception as e:
            raise ExecutionError(f"Failed to restore files: {e}") from e

    def neutralize_to_base(self, paths: frozenset[str], base: str) -> None:
        """Align each path in `paths` to the state at the merge-base of HEAD and `base`.

        Computes the merge-base of HEAD and `base` once, then for each path:
            git restore --source=<merge_base_sha> --staged --worktree -- <path>

        Behaviour per path:
          - Path absent in merge-base tree → removed from index and working tree.
          - Path present in merge-base tree → index and working tree set to
            merge-base version.

        Postcondition (after caller commits the staged changes):
            git diff --name-only <merge_base_sha>..HEAD -- <path>
            produces no output for any path in `paths`.

        Args:
            paths: Set of workspace-relative paths to neutralize.
            base:  Base branch name (e.g. "main", "epic/76-...").

        Raises:
            ExecutionError: if git merge-base fails (e.g. base not found) or
                            git restore fails for any path.
        """
        try:
            merge_base_sha = str(self.repo.git.merge_base("HEAD", base)).strip()
        except Exception as e:
            raise ExecutionError(f"git merge-base failed for base='{base}': {e}") from e

        for path in paths:
            try:
                self.repo.git.restore(
                    f"--source={merge_base_sha}",
                    "--staged",
                    "--worktree",
                    "--",
                    path,
                )
            except Exception as e:
                raise ExecutionError(
                    f"git restore --source={merge_base_sha} failed for '{path}': {e}"
                ) from e

    def has_net_diff_for_path(self, path: str, base: str) -> bool:
        """Return True if *path* has a net delta between the merge-base and HEAD.

        Uses ``git diff --name-only <merge_base>..HEAD -- <path>`` to determine
        whether this branch introduced commits that modified *path* relative to
        *base*. Raises ExecutionError on non-zero git exit codes.
        """
        try:
            merge_base_sha = str(self.repo.git.merge_base("HEAD", base)).strip()
        except Exception as e:
            raise ExecutionError(f"git merge-base failed for base='{base}': {e}") from e

        try:
            diff_output = str(
                self.repo.git.diff("--name-only", f"{merge_base_sha}..HEAD", "--", path)
            )
        except Exception as e:
            raise ExecutionError(f"git diff failed for path='{path}': {e}") from e

        return path in diff_output.splitlines()

    def checkout(self, branch_name: str) -> None:
        """Checkout branch (local or remote-tracking)."""
        try:
            normalized_branch = branch_name.removeprefix("origin/")

            if normalized_branch in self.repo.heads:
                self.repo.heads[normalized_branch].checkout()
                return

            try:
                origin = self.repo.remote("origin")
            except ValueError as e:
                raise ExecutionError("Origin remote not configured") from e

            remote_ref_name = f"origin/{normalized_branch}"
            remote_ref = next((ref for ref in origin.refs if ref.name == remote_ref_name), None)

            if remote_ref is None:
                raise ExecutionError(
                    f"Branch {normalized_branch} does not exist (checked: local, origin). "
                    f"Hint: Run git_fetch to update remote branch information."
                )

            local_branch = self.repo.create_head(normalized_branch, remote_ref)
            local_branch.set_tracking_branch(remote_ref)
            local_branch.checkout()

        except ExecutionError:
            raise
        except Exception as e:
            raise ExecutionError(f"Failed to checkout {branch_name}: {e}") from e

    def push(self, set_upstream: bool = False) -> None:
        """Push current branch to origin."""
        try:
            origin = self.repo.remote("origin")
        except ValueError as e:
            raise ExecutionError("No origin remote configured") from e

        try:
            branch = self.get_current_branch()
            if set_upstream:
                origin.push(refspec=f"{branch}:{branch}", set_upstream=True)
            else:
                origin.push()
        except Exception as e:
            raise ExecutionError(f"Failed to push: {e}") from e

    def fetch(self, remote: str = "origin", prune: bool = False) -> str:
        """Fetch updates from a remote."""
        try:
            self.repo.git.update_environment(
                GIT_TERMINAL_PROMPT="0",
                GIT_PAGER="cat",
                PAGER="cat",
            )

            remote_obj = self.repo.remote(remote)
            fetch_info = remote_obj.fetch(prune=prune)
            return f"Fetched from {remote}: {len(fetch_info)} ref(s)"
        except ValueError as e:
            raise ExecutionError(f"Remote '{remote}' is not configured") from e
        except Exception as e:
            raise ExecutionError(f"Failed to fetch from remote '{remote}': {e}") from e

    def has_upstream(self) -> bool:
        """Check whether the current branch has an upstream tracking branch."""
        try:
            tracking = self.repo.active_branch.tracking_branch()
            return tracking is not None
        except TypeError:
            return False
        except Exception as e:
            raise ExecutionError(f"Failed to check upstream: {e}") from e

    def pull(self, remote: str = "origin", rebase: bool = False) -> str:
        """Pull updates from a remote into the current branch."""
        try:
            self.repo.git.update_environment(
                GIT_TERMINAL_PROMPT="0",
                GIT_PAGER="cat",
                PAGER="cat",
            )

            self.repo.remote(remote)

            args: list[str] = [remote]
            if rebase:
                args.append("--rebase")

            output = str(self.repo.git.pull(*args)).strip()
            if output:
                return output
            return f"Pulled from {remote}"
        except ValueError as e:
            raise ExecutionError(f"Remote '{remote}' is not configured") from e
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
                raise ExecutionError(f"Cannot delete current branch {branch_name}")
            self.repo.delete_head(branch_name, force=force)
        except ExecutionError:
            raise
        except Exception as e:
            raise ExecutionError(f"Failed to delete {branch_name}: {e}") from e

    def stash(self, message: str | None = None, include_untracked: bool = False) -> None:
        """Stash current changes."""
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
        """List all stash entries."""
        try:
            output = str(self.repo.git.stash("list"))
            if not output:
                return []
            return output.strip().split("\n")
        except Exception as e:
            raise ExecutionError(f"Failed to list stashes: {e}") from e

    def list_branches(self, verbose: bool = False, remote: bool = False) -> list[str]:
        """List branches with optional verbose info and remotes."""
        try:
            args = []
            if remote:
                args.append("-r")
            if verbose:
                args.append("-vv")

            output = str(self.repo.git.branch(*args))
            if not output:
                return []
            return [line.strip() for line in output.split("\n") if line.strip()]
        except Exception as e:
            raise ExecutionError(f"Failed to list branches: {e}") from e

    def get_diff_stat(self, target: str, source: str = "HEAD") -> str:
        """Get diff statistics between two references."""
        try:
            return str(self.repo.git.diff(f"{target}...{source}", "--stat"))
        except Exception as e:
            raise ExecutionError(f"Failed to get diff stat: {e}") from e

    def get_recent_commits(self, limit: int = 5) -> list[str]:
        """Get recent commit messages."""
        try:
            commits = list(self.repo.iter_commits(max_count=limit))
            return [str(commit.message).split("\n", maxsplit=1)[0] for commit in commits]
        except Exception as e:
            raise ExecutionError(f"Failed to get recent commits: {e}") from e
