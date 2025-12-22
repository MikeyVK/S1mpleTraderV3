"""GitHub adapter for the MCP server."""
from datetime import datetime
from typing import Any

from github import Github, GithubException
from github.Issue import Issue
from github.Label import Label
from github.Milestone import Milestone
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

    def update_issue(
        self,
        issue_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        milestone_number: int | None = None,
        assignees: list[str] | None = None
    ) -> Issue:
        """Update fields on an issue."""
        try:
            issue = self.get_issue(issue_number)

            kwargs: dict[str, Any] = {}
            if title is not None:
                kwargs["title"] = title
            if body is not None:
                kwargs["body"] = body
            if state is not None:
                kwargs["state"] = state
            if labels is not None:
                kwargs["labels"] = labels
            if milestone_number is not None:
                try:
                    kwargs["milestone"] = self.repo.get_milestone(milestone_number)
                except GithubException as e:
                    raise ExecutionError(
                        f"Milestone {milestone_number} not found"
                    ) from e
            if assignees is not None:
                kwargs["assignees"] = assignees

            issue.edit(**kwargs)
            return issue
        except GithubException as e:
            raise ExecutionError(f"Failed to update issue: {e}") from e

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

    def search_issues(self, query: str, max_results: int = 10) -> list[Issue]:
        """Search for issues using GitHub search syntax.

        Args:
            query: GitHub search query (e.g., 'is:issue is:open "text" in:title')
            max_results: Maximum number of results to return

        Returns:
            List of matching issues

        Example:
            search_issues('is:issue is:open "Project Init" in:title')
        """
        try:
            # GitHub search returns paginated results
            results = self.client.search_issues(query, sort="created", order="desc")
            # Explicit cast to list of Issue objects
            issues: list[Issue] = list(results[:max_results])
            return issues
        except GithubException:
            # Search can fail but shouldn't crash the flow
            return []

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

    def list_labels(self) -> list[Label]:
        """List all labels in the repository."""
        try:
            return list(self.repo.get_labels())
        except GithubException as e:
            raise MCPSystemError(f"Failed to list labels: {e}") from e

    def create_label(
        self,
        name: str,
        color: str,
        description: str = ""
    ) -> Label:
        """Create a new label in the repository."""
        try:
            return self.repo.create_label(
                name=name,
                color=color,
                description=description
            )
        except GithubException as e:
            if e.status == 422:
                raise ExecutionError(
                    f"Label '{name}' already exists",
                    recovery=["Use a different name or delete existing label"]
                ) from e
            raise ExecutionError(f"Failed to create label: {e}") from e

    def delete_label(self, name: str) -> None:
        """Delete a label from the repository."""
        try:
            label = self.repo.get_label(name)
            label.delete()
        except GithubException as e:
            if e.status == 404:
                raise ExecutionError(
                    f"Label '{name}' not found",
                    recovery=["Check label name"]
                ) from e
            raise ExecutionError(f"Failed to delete label: {e}") from e

    def remove_labels(self, issue_number: int, labels: list[str]) -> None:
        """Remove labels from an issue or PR."""
        try:
            issue = self.get_issue(issue_number)
            for label_name in labels:
                try:
                    issue.remove_from_labels(label_name)
                except GithubException:
                    pass  # Label might not be on issue, ignore
        except GithubException as e:
            raise ExecutionError(f"Failed to remove labels: {e}") from e

    def list_milestones(self, state: str = "open") -> list[Milestone]:
        """List milestones in the repository."""
        try:
            return list(self.repo.get_milestones(state=state))
        except GithubException as e:
            raise ExecutionError(f"Failed to list milestones: {e}") from e

    def create_milestone(
        self,
        title: str,
        description: str | None = None,
        due_on: str | None = None
    ) -> Milestone:
        """Create a milestone."""
        parsed_due_on: datetime | None = None
        if due_on is not None:
            try:
                parsed_due_on = datetime.fromisoformat(due_on.replace("Z", "+00:00"))
            except ValueError as e:
                raise ExecutionError(
                    "Invalid due_on format. Use ISO 8601 (e.g., 2025-12-01T00:00:00Z)."
                ) from e

        try:
            kwargs: dict[str, Any] = {"title": title}
            if description is not None:
                kwargs["description"] = description
            if parsed_due_on is not None:
                kwargs["due_on"] = parsed_due_on.date()

            return self.repo.create_milestone(**kwargs)
        except GithubException as e:
            raise ExecutionError(f"Failed to create milestone: {e}") from e

    def close_milestone(self, milestone_number: int) -> Milestone:
        """Close a milestone."""
        try:
            milestone = self.repo.get_milestone(milestone_number)
            milestone.edit(title=milestone.title, state="closed")
            return milestone
        except GithubException as e:
            if e.status == 404:
                raise ExecutionError(
                    f"Milestone {milestone_number} not found",
                    recovery=["Check milestone number"]
                ) from e
            raise ExecutionError(f"Failed to close milestone: {e}") from e

    def list_prs(
        self,
        state: str = "open",
        base: str | None = None,
        head: str | None = None
    ) -> list[PullRequest]:
        """List pull requests with optional filtering."""
        kwargs: dict[str, Any] = {"state": state}
        if base:
            kwargs["base"] = base
        if head:
            kwargs["head"] = head

        try:
            return list(self.repo.get_pulls(**kwargs))
        except GithubException as e:
            raise ExecutionError(f"Failed to list pull requests: {e}") from e

    def merge_pr(
        self,
        pr_number: int,
        commit_message: str | None = None,
        merge_method: str = "merge"
    ) -> dict[str, Any]:
        """Merge a pull request."""
        try:
            pr = self.repo.get_pull(pr_number)
            kwargs: dict[str, Any] = {"merge_method": merge_method}
            if commit_message is not None:
                kwargs["commit_message"] = commit_message
            result = pr.merge(**kwargs)
        except GithubException as e:
            if e.status == 404:
                raise ExecutionError(
                    f"Pull request #{pr_number} not found",
                    recovery=["Check PR number"]
                ) from e
            raise ExecutionError(f"Failed to merge PR: {e}") from e

        if not result.merged:
            raise ExecutionError(
                f"Merge failed: {result.message}",
                recovery=["Resolve conflicts", "Verify merge permissions"]
            )

        return {
            "merged": result.merged,
            "sha": result.sha,
            "message": result.message
        }
