"""GitHub Manager for business logic."""

from typing import TYPE_CHECKING, Any

from mcp_server.adapters.github_adapter import GitHubAdapter
from mcp_server.schemas import (
    ContributorConfig,
    GitConfig,
    IssueConfig,
    LabelConfig,
    MilestoneConfig,
    ScopeConfig,
)

if TYPE_CHECKING:
    from github.Issue import Issue
    from github.Label import Label
    from github.Milestone import Milestone
    from github.PullRequest import PullRequest

    from mcp_server.core.interfaces import PRStatus


class GitHubManager:
    """Manager for GitHub operations."""

    def __init__(
        self,
        adapter: GitHubAdapter | None = None,
        issue_config: IssueConfig | None = None,
        label_config: LabelConfig | None = None,
        scope_config: ScopeConfig | None = None,
        milestone_config: MilestoneConfig | None = None,
        contributor_config: ContributorConfig | None = None,
        git_config: GitConfig | None = None,
    ) -> None:
        """Initialize the GitHub manager."""
        self._adapter = adapter
        self._issue_config = issue_config
        self._label_config = label_config
        self._scope_config = scope_config
        self._milestone_config = milestone_config
        self._contributor_config = contributor_config
        self._git_config = git_config

    @property
    def adapter(self) -> GitHubAdapter:
        """Lazily construct the GitHub adapter when first used."""
        if self._adapter is None:
            self._adapter = GitHubAdapter()
        return self._adapter

    def validate_issue_params(
        self,
        issue_type: str,
        title: str,
        priority: str,
        scope: str,
        milestone: str | None = None,
        assignees: list[str] | None = None,
    ) -> None:
        """Validate issue creation parameters against injected config objects.

        Raises ValueError for any invalid parameter; returns None on success.
        """
        if self._issue_config is None:
            raise ValueError("IssueConfig must be injected for validate_issue_params")
        if not self._issue_config.has_issue_type(issue_type):
            valid = sorted(t.name for t in self._issue_config.issue_types)
            raise ValueError(f"Unknown issue type: '{issue_type}'. Valid types: {valid}")

        if self._label_config is not None:
            valid_priorities = {
                lbl.name.split(":", 1)[1]
                for lbl in self._label_config.get_labels_by_category("priority")
            }
            if valid_priorities and priority not in valid_priorities:
                raise ValueError(
                    f"Unknown priority: '{priority}'. Valid values: {sorted(valid_priorities)}"
                )

        if self._scope_config is not None and not self._scope_config.has_scope(scope):
            raise ValueError(
                f"Unknown scope: '{scope}'. Valid values: {sorted(self._scope_config.scopes)}"
            )

        if self._git_config is not None:
            max_len = self._git_config.issue_title_max_length
            if len(title) > max_len:
                raise ValueError(
                    f"Title too long: {len(title)} chars (max {max_len} from git.yaml)"
                )

        if (
            milestone is not None
            and self._milestone_config is not None
            and not self._milestone_config.validate_milestone(milestone)
        ):
            raise ValueError(
                f"Unknown milestone: '{milestone}'. Must match a title in milestones.yaml."
            )

        if assignees is not None and self._contributor_config is not None:
            for login in assignees:
                if not self._contributor_config.validate_assignee(login):
                    raise ValueError(
                        f"Unknown assignee: '{login}'. Must be listed in contributors.yaml."
                    )

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
            ],
        }

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def create_issue(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None,
        milestone: int | None = None,
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new issue and return details."""
        issue = self.adapter.create_issue(
            title=title, body=body, labels=labels, milestone_number=milestone, assignees=assignees
        )
        return {"number": issue.number, "url": issue.html_url, "title": issue.title}

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def create_pr(
        self, title: str, body: str, head: str, base: str = "main", draft: bool = False
    ) -> dict[str, Any]:
        """Create a new pull request."""
        pr = self.adapter.create_pr(title=title, body=body, head=head, base=base, draft=draft)
        return {"number": pr.number, "url": pr.html_url, "title": pr.title}

    def add_labels(self, issue_number: int, labels: list[str]) -> None:
        """Add labels to an issue or PR."""
        self.adapter.add_labels(issue_number, labels)

    def list_issues(self, state: str = "open", labels: list[str] | None = None) -> list["Issue"]:
        """List issues with optional filtering."""
        return self.adapter.list_issues(state=state, labels=labels)

    def get_issue(self, issue_number: int) -> "Issue":
        """Get a specific issue by number."""
        return self.adapter.get_issue(issue_number)

    def close_issue(self, issue_number: int, comment: str | None = None) -> "Issue":
        """Close an issue with optional comment."""
        return self.adapter.close_issue(issue_number, comment=comment)

    def list_labels(self) -> list["Label"]:
        """List all labels in the repository."""
        return self.adapter.list_labels()

    def create_label(self, name: str, color: str, description: str = "") -> "Label":
        """Create a new label in the repository."""
        return self.adapter.create_label(name=name, color=color, description=description)

    def delete_label(self, name: str) -> None:
        """Delete a label from the repository."""
        self.adapter.delete_label(name)

    def remove_labels(self, issue_number: int, labels: list[str]) -> None:
        """Remove labels from an issue or PR."""
        self.adapter.remove_labels(issue_number, labels)

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def update_issue(
        self,
        issue_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        milestone: int | None = None,
        assignees: list[str] | None = None,
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
        self, title: str, description: str | None = None, due_on: str | None = None
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
        self, state: str = "open", base: str | None = None, head: str | None = None
    ) -> list["PullRequest"]:
        """List pull requests with optional filtering."""
        return self.adapter.list_prs(state=state, base=base, head=head)

    def merge_pr(
        self, pr_number: int, commit_message: str | None = None, merge_method: str = "merge"
    ) -> dict[str, Any]:
        """Merge a pull request."""
        return self.adapter.merge_pr(
            pr_number=pr_number,
            commit_message=commit_message,
            merge_method=merge_method,
        )

    def get_pr_status(self, branch: str) -> "PRStatus":
        """Return current PR status for *branch* by querying the GitHub API.

        Stub — full implementation in C4 (branch lockdown rollout).
        PRStatusCache calls this on cold start (cache miss).
        """
        raise NotImplementedError("GitHubManager.get_pr_status() implemented in C4")
