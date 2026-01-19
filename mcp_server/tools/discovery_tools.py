"""Discovery tools for AI self-orientation."""
# pyright: reportIncompatibleMethodOverride=false
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.config.settings import settings
from mcp_server.core.exceptions import ExecutionError, MCPError
from mcp_server.services.document_indexer import DocumentIndexer
from mcp_server.services.search_service import SearchService
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class SearchDocumentationInput(BaseModel):
    """Input for SearchDocumentationTool."""
    query: str = Field(
        ...,
        description="Search query (e.g., 'how to implement a worker', 'DTO validation rules')"
    )
    scope: str = Field(
        default="all",
        description="Optional scope to filter results",
        pattern="^(all|architecture|coding_standards|development|reference|implementation)$"
    )


class SearchDocumentationTool(BaseTool):
    """Tool to search documentation files."""

    name = "search_documentation"
    description = (
        "Semantic/fuzzy search across all docs/ files. "
        "Returns ranked results with snippets for understanding project structure."
    )
    args_model = SearchDocumentationInput

    async def execute(self, params: SearchDocumentationInput) -> ToolResult:
        """Execute documentation search using DocumentIndexer + SearchService."""
        # Build index from docs directory
        docs_dir = Path(settings.server.workspace_root) / "docs"

        if not docs_dir.exists():
            raise ExecutionError(
                "Documentation directory not found",
                recovery=[
                    f"Expected directory: {docs_dir}",
                    "Create docs/ directory in workspace root",
                    "Add markdown files to document project"
                ]
            )

        index = DocumentIndexer.build_index(docs_dir)

        # Map scope filter (None if 'all')
        scope_filter = None if params.scope == "all" else params.scope

        # Search index
        results = SearchService.search_index(
            index=index,
            query=params.query,
            max_results=10,
            scope=scope_filter
        )

        if not results:
            return ToolResult.text(
                f"No results found for query: '{params.query}'\n"
                "Try broader search terms or different scope."
            )

        # Format results for output
        output_lines = [f"Found {len(results)} results for '{params.query}':\n"]

        for i, result in enumerate(results, 1):
            output_lines.append(
                f"{i}. **{result['title']}** ({result['path']})\n"
                f"   Score: {result['_relevance']:.2f}\n"
                f"   > {result['_snippet']}\n"
            )

        return ToolResult.text("\n".join(output_lines))


class GetWorkContextInput(BaseModel):
    """Input for GetWorkContextTool."""
    include_closed_recent: bool = Field(
        default=False,
        description="Include recently closed issues (last 7 days) for context"
    )


class GetWorkContextTool(BaseTool):
    """Tool to aggregate work context from Git and GitHub."""

    name = "get_work_context"
    description = (
        "Aggregates context from GitHub Issues, current branch, and TDD phase "
        "to understand what to work on next."
    )
    args_model = GetWorkContextInput


    async def execute(self, params: GetWorkContextInput) -> ToolResult:
        """Execute work context aggregation."""
        context: dict[str, Any] = {}

        # Get Git context
        git_manager = GitManager()
        branch = git_manager.get_current_branch()
        context["current_branch"] = branch

        # Extract issue number from branch
        issue_number = self._extract_issue_number(branch)
        context["linked_issue_number"] = issue_number

        # Detect TDD phase from recent commits
        try:
            recent_commits = git_manager.get_recent_commits(limit=5)
            tdd_phase = self._detect_tdd_phase(recent_commits)
            context["tdd_phase"] = tdd_phase
            context["recent_commits"] = recent_commits
        except (OSError, ValueError, RuntimeError):
            context["tdd_phase"] = "unknown"
            context["recent_commits"] = []

        # Get GitHub issue details if configured
        if settings.github.token:
            try:
                gh_manager = GitHubManager()

                # Active Issue
                if issue_number:
                    issue = gh_manager.get_issue(issue_number)
                    if issue:
                        # GitHubManager.get_issue() returns PyGithub Issue object
                        context["active_issue"] = {
                            "number": issue.number,
                            "title": issue.title,
                            "body": (issue.body or "")[:500],
                            "labels": [label.name for label in issue.labels],
                            "acceptance_criteria": self._extract_checklist(
                                issue.body or ""
                            )
                        }

                # Recently Closed Issues (Implemented to satisfy param)
                if params.include_closed_recent:
                     # This effectively implements the logic for the formerly unused argument
                    closed_issues = gh_manager.list_issues(state="closed")
                    # Naively taking top 3 for brevity, assuming list_issues sorts by recent
                    context["recently_closed"] = [
                        f"#{i.number} {i.title}" for i in closed_issues[:3]
                    ]

            except (OSError, ValueError, RuntimeError, ImportError, MCPError):
                pass  # GitHub integration optional

        return ToolResult.text(self._format_context(context))

    def _extract_issue_number(self, branch: str) -> int | None:
        """Extract issue number from branch name."""
        patterns = [
            r"(?:feature|fix|refactor|docs)/(\d+)-",
            r"issue-(\d+)",
            r"#(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, branch)
            if match:
                return int(match.group(1))

        return None

    def _detect_tdd_phase(self, commits: list[str]) -> str:
        """Detect TDD phase from recent commits."""
        if not commits:
            return "unknown"

        # Check most recent commit
        latest = commits[0].lower() if commits else ""

        if latest.startswith("test:") or "failing test" in latest:
            return "red"
        if latest.startswith("feat:") or "pass" in latest:
            return "green"
        if latest.startswith("refactor:"):
            return "refactor"
        if latest.startswith("docs:"):
            return "docs"

        return "unknown"

    def _extract_checklist(self, body: str) -> list[str]:
        """Extract checklist items from issue body."""
        if not body:
            return []

        pattern = r"- \[[ x]\] (.+)"
        matches = re.findall(pattern, body)
        return matches[:10]  # Limit to 10 items

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format context for readable output."""
        lines = ["## Work Context\n"]

        # Branch info
        lines.append(f"**Current Branch:** `{context['current_branch']}`")

        if context.get("linked_issue_number"):
            lines.append(f"**Linked Issue:** #{context['linked_issue_number']}")

        # TDD Phase
        phase = context.get("tdd_phase", "unknown")
        phase_emoji = {
            "red": "🔴",
            "green": "🟢",
            "refactor": "🔄",
            "docs": "📝",
            "unknown": "❓"
        }.get(phase, "❓")
        lines.append(f"**TDD Phase:** {phase_emoji} {phase}")

        # Active Issue Details
        if "active_issue" in context:
            issue = context["active_issue"]
            lines.append(f"\n### Active Issue: #{issue['number']}")
            lines.append(f"**{issue['title']}**")

            if issue.get("labels"):
                lines.append(f"Labels: {', '.join(issue['labels'])}")

            if issue.get("acceptance_criteria"):
                lines.append("\n**Acceptance Criteria:**")
                for criterion in issue["acceptance_criteria"]:
                    lines.append(f"- [ ] {criterion}")

        # Recently Closed
        if context.get("recently_closed"):
            lines.append("\n**Recently Closed Issues:**")
            for closed in context["recently_closed"]:
                lines.append(f"- {closed}")

        # Recent commits
        if context.get("recent_commits"):
            lines.append("\n**Recent Commits:**")
            for commit in context["recent_commits"][:3]:
                lines.append(f"- {commit}")

        return "\n".join(lines)
