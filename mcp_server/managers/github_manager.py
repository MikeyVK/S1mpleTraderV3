"""GitHub Manager for business logic."""
from typing import Any, Dict
from mcp_server.adapters.github import GitHubAdapter
from mcp_server.core.exceptions import ExecutionError

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
                    "labels": [l.name for l in i.labels],
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
    ) -> Dict[str, Any]:
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
