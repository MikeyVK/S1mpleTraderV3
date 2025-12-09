"""Discovery tools for AI self-orientation."""
# pyright: reportIncompatibleMethodOverride=false
import re
from typing import Any, Dict, Optional

from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.managers.doc_manager import DocManager
from mcp_server.managers.git_manager import GitManager
from mcp_server.config.settings import settings
from mcp_server.core.exceptions import MCPError


class SearchDocumentationTool(BaseTool):
    """Tool to search documentation files."""

    name = "search_documentation"
    description = (
        "Semantic/fuzzy search across all docs/ files. "
        "Returns ranked results with snippets for understanding project structure."
    )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query (e.g., 'how to implement a worker', "
                        "'DTO validation rules')"
                    )
                },
                "scope": {
                    "type": "string",
                    "description": "Optional scope to filter results",
                    "enum": [
                        "all",
                        "architecture",
                        "coding_standards",
                        "development",
                        "reference",
                        "implementation"
                    ],
                    "default": "all"
                }
            },
            "required": ["query"]
        }

    async def execute(
        self,
        query: str,
        scope: str = "all",
        **kwargs: Any
    ) -> ToolResult:
        """Execute documentation search."""
        manager = DocManager()
        scope_filter = None if scope == "all" else scope

        results = manager.search(query, scope=scope_filter, max_results=10)

        if not results:
            return ToolResult.text(
                f"No results found for query: '{query}'\n"
                "Try broader search terms or different scope."
            )

        # Format results for output
        output_lines = [f"Found {len(results)} results for '{query}':\n"]

        for i, result in enumerate(results, 1):
            output_lines.append(
                f"{i}. **{result['title']}** ({result['file_path']})\n"
                f"   Line {result['line_number']} | "
                f"Score: {result['relevance_score']:.2f}\n"
                f"   > {result['snippet']}\n"
            )

        return ToolResult.text("\n".join(output_lines))


class GetWorkContextTool(BaseTool):
    """Tool to aggregate work context from Git and GitHub."""

    name = "get_work_context"
    description = (
        "Aggregates context from GitHub Issues, current branch, and TDD phase "
        "to understand what to work on next."
    )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "include_closed_recent": {
                    "type": "boolean",
                    "description": (
                        "Include recently closed issues (last 7 days) for context"
                    ),
                    "default": False
                }
            },
            "required": []
        }

    async def execute(
        self,
        include_closed_recent: bool = False,
        **kwargs: Any
    ) -> ToolResult:
        """Execute work context aggregation."""
        context: Dict[str, Any] = {}

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
        # pylint: disable=no-member
        if settings.github.token and issue_number:
            try:
                from mcp_server.managers.github_manager import GitHubManager
                gh_manager = GitHubManager()
                issue = gh_manager.get_issue(issue_number)

                if issue:
                    context["active_issue"] = {
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "body": issue.get("body", "")[:500],
                        "labels": [
                            label.get("name")
                            for label in issue.get("labels", [])
                        ],
                        "acceptance_criteria": self._extract_checklist(
                            issue.get("body", "")
                        )
                    }
            except (OSError, ValueError, RuntimeError, ImportError, MCPError):
                pass  # GitHub integration optional

        return ToolResult.text(self._format_context(context))

    def _extract_issue_number(self, branch: str) -> Optional[int]:
        """Extract issue number from branch name.

        Patterns:
        - feature/42-description
        - fix/123-bug-name
        - issue-42-something
        """
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
        elif latest.startswith("feat:") or "pass" in latest:
            return "green"
        elif latest.startswith("refactor:"):
            return "refactor"
        elif latest.startswith("docs:"):
            return "docs"

        return "unknown"

    def _extract_checklist(self, body: str) -> list[str]:
        """Extract checklist items from issue body."""
        if not body:
            return []

        pattern = r"- \[[ x]\] (.+)"
        matches = re.findall(pattern, body)
        return matches[:10]  # Limit to 10 items

    def _format_context(self, context: Dict[str, Any]) -> str:
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

        # Recent commits
        if context.get("recent_commits"):
            lines.append("\n**Recent Commits:**")
            for commit in context["recent_commits"][:3]:
                lines.append(f"- {commit}")

        return "\n".join(lines)
