"""GitHub Manager for business logic."""
from typing import TYPE_CHECKING, Any

from mcp_server.adapters.github_adapter import GitHubAdapter

if TYPE_CHECKING:
    from github.Issue import Issue
    from github.Label import Label
    from github.Milestone import Milestone
    from github.PullRequest import PullRequest


class GitHubManager:
    """Manager for GitHub operations."""

    def __init__(self, adapter: GitHubAdapter | None = None) -> None:
        """Initialize the GitHub manager."""
        self.adapter = adapter or GitHubAdapter()

    def get_issues_resource_data(self) -> dict[str, Any]:
        """Get data for st3://github/issues resource."""
        issues = self.adapter.list_issues(state="open")

        return {
            "open_count": len(issues),
            "issues": [
                {
                    "number": i.number,
                    "title": i.title,
                    "state": i.state,
                    "labels": [label.name for label in i.labels],
                    "assignees": [a.login for a in i.assignees],
                    "created_at": i.created_at.isoformat(),
                    "updated_at": i.updated_at.isoformat(),
                }
                for i in issues
            ]
        }

    def create_issue(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None,
        milestone: int | None = None,
        assignees: list[str] | None = None
    ) -> dict[str, Any]:
        """Create a new issue and return details."""
        issue = self.adapter.create_issue(
            title=title,
            body=body,
            labels=labels,
            milestone_number=milestone,
            assignees=assignees
        )
        return {
            "number": issue.number,
            "url": issue.html_url,
            "title": issue.title
        }

    def create_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = False
    ) -> dict[str, Any]:
        """Create a new pull request."""
        pr = self.adapter.create_pr(
            title=title,
            body=body,
            head=head,
            base=base,
            draft=draft
        )
        return {
            "number": pr.number,
            "url": pr.html_url,
            "title": pr.title
        }

    def add_labels(self, issue_number: int, labels: list[str]) -> None:
        """Add labels to an issue or PR."""
        self.adapter.add_labels(issue_number, labels)

    def list_issues(
        self,
        state: str = "open",
        labels: list[str] | None = None
    ) -> list["Issue"]:
        """List issues with optional filtering."""
        return self.adapter.list_issues(state=state, labels=labels)

    def get_issue(self, issue_number: int) -> "Issue":
        """Get a specific issue by number."""
        return self.adapter.get_issue(issue_number)

    def close_issue(
        self,
        issue_number: int,
        comment: str | None = None
    ) -> "Issue":
        """Close an issue with optional comment."""
        return self.adapter.close_issue(issue_number, comment=comment)

    def list_labels(self) -> list["Label"]:
        """List all labels in the repository."""
        return self.adapter.list_labels()

    def create_label(
        self,
        name: str,
        color: str,
        description: str = ""
    ) -> "Label":
        """Create a new label in the repository."""
        return self.adapter.create_label(
            name=name,
            color=color,
            description=description
        )

    def delete_label(self, name: str) -> None:
        """Delete a label from the repository."""
        self.adapter.delete_label(name)

    def remove_labels(self, issue_number: int, labels: list[str]) -> None:
        """Remove labels from an issue or PR."""
        self.adapter.remove_labels(issue_number, labels)

    def update_issue(
        self,
        issue_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        milestone: int | None = None,
        assignees: list[str] | None = None
    ) -> "Issue":
        """Update fields on an issue."""
        return self.adapter.update_issue(
            issue_number=issue_number,
            title=title,
            body=body,
            state=state,
            labels=labels,
            milestone_number=milestone,
            assignees=assignees,
        )

    def list_milestones(self, state: str = "open") -> list["Milestone"]:
        """List milestones for the repository."""
        return self.adapter.list_milestones(state=state)

    def create_milestone(
        self,
        title: str,
        description: str | None = None,
        due_on: str | None = None
    ) -> "Milestone":
        """Create a new milestone."""
        return self.adapter.create_milestone(
            title=title,
            description=description,
            due_on=due_on,
        )

    def close_milestone(self, milestone_number: int) -> "Milestone":
        """Close a milestone."""
        return self.adapter.close_milestone(milestone_number)

    def list_prs(
        self,
        state: str = "open",
        base: str | None = None,
        head: str | None = None
    ) -> list["PullRequest"]:
        """List pull requests with optional filtering."""
        return self.adapter.list_prs(state=state, base=base, head=head)

    def merge_pr(
        self,
        pr_number: int,
        commit_message: str | None = None,
        merge_method: str = "merge"
    ) -> dict[str, Any]:
        """Merge a pull request."""
        return self.adapter.merge_pr(
            pr_number=pr_number,
            commit_message=commit_message,
            merge_method=merge_method,
        )
