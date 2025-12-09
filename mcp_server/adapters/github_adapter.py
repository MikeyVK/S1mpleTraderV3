"""GitHub adapter for the MCP server."""
from typing import Any

from github import Github, GithubException
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Repository import Repository

from mcp_server.config.settings import settings
from mcp_server.core.exceptions import ExecutionError, MCPSystemError


class GitHubAdapter:
    """Adapter for interacting with the GitHub API."""

    def __init__(self) -> None:
        """Initialize the GitHub adapter."""
        if not settings.github.token:  # pylint: disable=no-member
            raise MCPSystemError(
                "GitHub token not configured",
                fallback="Configure GITHUB_TOKEN environment variable"
            )

        self.client = Github(settings.github.token)  # pylint: disable=no-member
        self._repo: Repository | None = None

    @property
    def repo(self) -> Repository:
        """Get the configured repository."""
        if not self._repo:
            try:
                repo_name = f"{settings.github.owner}/{settings.github.repo}"  # pylint: disable=no-member
                self._repo = self.client.get_repo(repo_name)
            except GithubException as e:
                raise MCPSystemError(
                    f"Failed to access repository: {e}",
                    fallback="Check repository permissions"
                ) from e
        return self._repo

    def get_issue(self, issue_number: int) -> Issue:
        """Get an issue by number."""
        try:
            return self.repo.get_issue(issue_number)
        except GithubException as e:
            if e.status == 404:
                raise ExecutionError(
                    f"Issue #{issue_number} not found",
                    recovery=["Check issue number"]
                ) from e
            raise MCPSystemError(f"GitHub API error: {e}") from e

    def create_issue(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None,
        milestone_number: int | None = None,
        assignees: list[str] | None = None
    ) -> Issue:
        """Create a new issue."""
        kwargs: dict[str, Any] = {
            "title": title,
            "body": body,
        }

        if labels:
            kwargs["labels"] = labels

        if milestone_number:
            try:
                milestone = self.repo.get_milestone(milestone_number)
                kwargs["milestone"] = milestone
            except GithubException as e:
                raise ExecutionError(f"Milestone {milestone_number} not found") from e

        if assignees:
            kwargs["assignees"] = assignees

        try:
            return self.repo.create_issue(**kwargs)
        except GithubException as e:
            raise ExecutionError(f"Failed to create issue: {e}") from e

    def list_issues(
        self,
        state: str = "open",
        labels: list[str] | None = None
    ) -> list[Issue]:
        """List issues with filtering."""
        kwargs: dict[str, Any] = {"state": state}
        if labels:
            kwargs["labels"] = labels

        return list(self.repo.get_issues(**kwargs))

    def create_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = False
    ) -> PullRequest:
        """Create a new pull request."""
        try:
            return self.repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base,
                draft=draft
            )
        except GithubException as e:
            raise ExecutionError(f"Failed to create PR: {e}") from e

    def add_labels(self, issue_number: int, labels: list[str]) -> None:
        """Add labels to an issue or PR."""
        try:
            issue = self.get_issue(issue_number)
            issue.add_to_labels(*labels)
        except GithubException as e:
            raise ExecutionError(f"Failed to add labels: {e}") from e

    def close_issue(
        self,
        issue_number: int,
        comment: str | None = None
    ) -> Issue:
        """Close an issue with optional comment.

        Args:
            issue_number: The issue number to close.
            comment: Optional comment to add before closing.

        Returns:
            The closed issue object.
        """
        try:
            issue = self.get_issue(issue_number)

            # Add comment if provided
            if comment:
                issue.create_comment(comment)

            # Close the issue
            issue.edit(state="closed")

            return issue
        except GithubException as e:
            raise ExecutionError(f"Failed to close issue: {e}") from e
