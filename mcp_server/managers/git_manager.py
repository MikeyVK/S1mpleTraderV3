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

    def create_feature_branch(self, name: str, branch_type: str = "feature") -> str:
        """Create a new feature branch enforcing naming conventions."""
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

        # Pre-flight check
        if not self.adapter.is_clean():
            raise PreflightError(
                "Working directory is not clean",
                blockers=["Commit or stash changes before creating a new branch"]
            )

        self.adapter.create_branch(full_name)
        return full_name

    def commit_tdd_phase(self, phase: str, message: str) -> str:
        """Commit changes with TDD phase prefix."""
        if phase not in ["red", "green", "refactor"]:
            raise ValidationError(
                f"Invalid TDD phase: {phase}",
                hints=["Use red, green, or refactor"]
            )

        prefix_map = {
            "red": "test",
            "green": "feat",
            "refactor": "refactor"
        }

        full_message = f"{prefix_map[phase]}: {message}"
        return self.adapter.commit(full_message)

    def commit_docs(self, message: str) -> str:
        """Commit changes with docs prefix."""
        full_message = f"docs: {message}"
        return self.adapter.commit(full_message)

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

