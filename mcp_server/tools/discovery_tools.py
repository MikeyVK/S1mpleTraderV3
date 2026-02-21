"""Discovery tools for AI self-orientation."""

# pyright: reportIncompatibleMethodOverride=false
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.core.phase_detection import PhaseDetectionResult, ScopeDecoder
from mcp_server.config.settings import settings
from mcp_server.core.exceptions import ExecutionError, MCPError
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.services.document_indexer import DocumentIndexer
from mcp_server.services.search_service import SearchService
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class SearchDocumentationInput(BaseModel):
    """Input for SearchDocumentationTool."""

    query: str = Field(
        ..., description="Search query (e.g., 'how to implement a worker', 'DTO validation rules')"
    )
    scope: str = Field(
        default="all",
        description="Optional scope to filter results",
        pattern="^(all|architecture|coding_standards|development|reference|implementation)$",
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
                    "Add markdown files to document project",
                ],
            )

        index = DocumentIndexer.build_index(docs_dir)

        # Map scope filter (None if 'all')
        scope_filter = None if params.scope == "all" else params.scope

        # Search index
        results = SearchService.search_index(
            index=index, query=params.query, max_results=10, scope=scope_filter
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
        default=False, description="Include recently closed issues (last 7 days) for context"
    )


class GetWorkContextTool(BaseTool):
    """Tool to aggregate work context from Git and GitHub."""

    name = "get_work_context"
    description = (
        "Aggregates context from GitHub Issues, current branch, and workflow phase "
        "to understand what to work on next. Uses deterministic phase detection."
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

        # Detect workflow phase deterministically from commit-scope + state.json
        try:
            recent_commits = git_manager.get_recent_commits(limit=5)
            phase_result = self._detect_workflow_phase(recent_commits)
            context["workflow_phase"] = phase_result["workflow_phase"]
            context["sub_phase"] = phase_result.get("sub_phase")
            context["phase_source"] = phase_result["source"]
            context["phase_confidence"] = phase_result["confidence"]
            context["phase_error_message"] = phase_result.get("error_message")
            context["recent_commits"] = recent_commits
        except (OSError, ValueError, RuntimeError):
            context["workflow_phase"] = "unknown"
            context["sub_phase"] = None
            context["phase_source"] = "unknown"
            context["phase_confidence"] = "unknown"
            context["phase_error_message"] = None
            context["recent_commits"] = []

        # Issue #146 Cycle 3: TDD Cycle Info (conditional visibility)
        if context.get("workflow_phase") == "tdd" and issue_number:
            try:
                workspace_root = Path(settings.server.workspace_root)
                project_manager = ProjectManager(workspace_root=workspace_root)
                state_engine = PhaseStateEngine(
                    workspace_root=workspace_root, project_manager=project_manager
                )

                # Get current TDD cycle from state
                state = state_engine.get_state(branch)
                current_cycle = state.get("current_tdd_cycle")

                # Get planning deliverables
                project_plan = project_manager.get_project_plan(issue_number)
                if project_plan is None:
                    raise ValueError("Project plan not found")
                planning_deliverables = project_plan.get("planning_deliverables")
                if planning_deliverables and current_cycle:
                    tdd_cycles = planning_deliverables.get("tdd_cycles", {})
                    cycles = tdd_cycles.get("cycles", [])
                    total = tdd_cycles.get("total", 0)

                    # Find current cycle details
                    cycle_details = next(
                        (c for c in cycles if c.get("cycle_number") == current_cycle), None
                    )

                    if cycle_details:
                        context["tdd_cycle_info"] = {
                            "current": current_cycle,
                            "total": total,
                            "name": cycle_details.get("name"),
                            "deliverables": cycle_details.get("deliverables", []),
                            "exit_criteria": cycle_details.get("exit_criteria"),
                            # Always in_progress when cycle is active (Issue #146, design.md:375)
                            "status": "in_progress",
                        }
            except (OSError, ValueError, RuntimeError, KeyError):
                pass  # Graceful degradation if cycle info unavailable

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
                            "acceptance_criteria": self._extract_checklist(issue.body or ""),
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

    def _detect_workflow_phase(self, commits: list[str]) -> PhaseDetectionResult:
        """
        Detect workflow phase deterministically using ScopeDecoder.

        Uses commit-scope precedence: commit-scope > state.json > unknown
        NO type-heuristic guessing.

        Args:
            commits: Recent commit messages

        Returns:
            PhaseDetectionResult dict with workflow_phase, sub_phase, source, confidence
        """
        if not commits:
            return {
                "workflow_phase": "unknown",
                "sub_phase": None,
                "source": "unknown",
                "confidence": "unknown",
                "raw_scope": None,
                "error_message": None,
            }

        # Use most recent commit for phase detection
        latest_commit = commits[0]

        # Deterministic phase detection via ScopeDecoder
        decoder = ScopeDecoder()
        return decoder.detect_phase(commit_message=latest_commit, fallback_to_state=True)

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

        # Workflow Phase (all 7 phases supported)
        phase = context.get("workflow_phase", "unknown")
        sub_phase = context.get("sub_phase")
        source = context.get("phase_source", "unknown")
        confidence = context.get("phase_confidence", "unknown")

        # Phase emoji mapping (7 workflow phases + unknown)
        phase_emoji = {
            "research": "🔍",
            "planning": "📋",
            "design": "🎨",
            "tdd": "🧪",
            "validation": "✅",
            "documentation": "📝",
            "coordination": "🤝",
            "unknown": "❓",
        }.get(phase, "❓")

        # Sub-phase emoji (TDD-specific for now, expandable)
        subphase_emoji = {
            "red": "🔴",
            "green": "🟢",
            "refactor": "🔄",
        }

        phase_display = f"{phase_emoji} {phase}"
        if sub_phase:
            emoji = subphase_emoji.get(sub_phase, "")
            phase_display += f" → {emoji} {sub_phase}"

        lines.append(f"**Workflow Phase:** {phase_display}")
        lines.append(f"**Phase Detection:** {source} (confidence: {confidence})")

        # Show error_message if phase detection failed with recovery info
        error_message = context.get("phase_error_message")
        if error_message:
            lines.append(f"**⚠️ Recovery Info:** {error_message}")

        # Issue #146 Cycle 3: TDD Cycle Info (conditional visibility during TDD phase)
        if "tdd_cycle_info" in context:
            cycle_info = context["tdd_cycle_info"]
            lines.append("\n### 🧪 TDD Cycle Progress")
            lines.append(
                f"**Cycle {cycle_info['current']}/{cycle_info['total']}:** {cycle_info['name']}"
            )
            if cycle_info.get("status"):
                lines.append(f"**Status:** {cycle_info['status']}")
            lines.append("\n**Deliverables:**")
            for deliverable in cycle_info.get("deliverables", []):
                lines.append(f"- {deliverable}")
            lines.append(f"\n**Exit Criteria:** {cycle_info.get('exit_criteria', 'N/A')}")

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
