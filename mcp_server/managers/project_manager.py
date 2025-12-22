"""ProjectManager: orchestrates project initialization workflow.

Responsibilities:
1. Validate dependency graph (no cycles)
2. Create GitHub milestone
3. Create parent issue (if needed)
4. Create sub-issues for each phase
5. Update parent issue with sub-issue links
6. Persist ProjectMetadata to .st3/projects.json
7. Return ProjectSummary

Uses GitHubAdapter for all GitHub operations (dependency injection).
"""

from difflib import SequenceMatcher
import json
import time
from pathlib import Path
from typing import Any
from mcp_server.managers.dependency_graph_validator import DependencyGraphValidator
from mcp_server.state.project import (
    PhaseSpec,
    ProjectMetadata,
    ProjectSpec,
    ProjectSummary,
    SubIssueMetadata,
)


class ProjectManager:  # pylint: disable=too-few-public-methods
    """Manages project initialization with dependency validation.

    Note: Single-purpose manager focused on project initialization.
    Additional methods will be added as project management features expand.
    """

    def __init__(self, github_adapter: Any, workspace_root: Path) -> None:
        """Initialize ProjectManager.

        Args:
            github_adapter: GitHub API adapter (duck-typed for mocking)
            workspace_root: Path to workspace root (for .st3/projects.json)
        """
        self.github_adapter = github_adapter
        self.workspace_root = workspace_root
        self.validator = DependencyGraphValidator()

    def initialize_project(self, spec: ProjectSpec) -> ProjectSummary:
        """Initialize project with phases and dependencies.

        Steps:
        1. Validate dependency graph (reject cycles)
        2. Create GitHub milestone
        3. Create parent issue (if parent_issue_number not provided)
        4. Create sub-issues for each phase
        5. Update parent issue with sub-issue links
        6. Persist ProjectMetadata to .st3/projects.json
        7. Return ProjectSummary

        Args:
            spec: Project specification with phases and dependencies

        Returns:
            ProjectSummary with project_id, milestone_id, parent_issue,
            sub_issues, dependency_graph

        Raises:
            ValueError: If dependency graph contains cycles
            Exception: If GitHub API calls fail (propagates from adapter)
        """
        # Step 1: Validate dependency graph
        self._validate_graph(spec.phases)

        # Step 2: Create GitHub milestone
        milestone_id = self._create_milestone(spec.project_title)

        # Step 3: Create or use existing parent issue
        parent_number, parent_url = self._create_or_get_parent_issue(
            spec, milestone_id
        )

        # Step 4: Create sub-issues for each phase
        sub_issues = self._create_sub_issues(spec.phases, milestone_id)

        # Step 5: Update parent issue with sub-issue links
        self._update_parent_with_links(parent_number, spec, sub_issues)

        # Step 6: Persist ProjectMetadata
        project_id = self._generate_project_id(spec.project_title)
        project_metadata = ProjectMetadata(
            project_id=project_id,
            parent_issue={"number": parent_number, "url": parent_url},
            milestone_id=milestone_id,
            phases=sub_issues,
        )
        self._persist_project_metadata(project_metadata)

        # Step 7: Return ProjectSummary
        return self._build_summary(project_metadata, spec.phases)

    def _validate_graph(self, phases: list[PhaseSpec]) -> None:
        """Validate dependency graph is acyclic.

        Raises:
            ValueError: If circular dependency detected
        """
        is_valid, cycle = self.validator.validate_acyclic(phases)
        if not is_valid:
            cycle_path = " → ".join(cycle) if cycle else "unknown"
            raise ValueError(f"Circular dependency detected: {cycle_path}")

    def _create_milestone(self, project_title: str) -> int:
        """Create GitHub milestone.

        Args:
            project_title: Title for milestone

        Returns:
            Milestone ID
        """
        milestone_response = self.github_adapter.create_milestone(
            title=project_title,
            description=f"Milestone for {project_title}",
        )
        milestone_id: int = milestone_response["number"]
        return milestone_id

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles (0.0 - 1.0).

        Uses SequenceMatcher for fuzzy string matching.
        """
        # Normalize titles for comparison
        norm1 = title1.lower().strip()
        norm2 = title2.lower().strip()
        return SequenceMatcher(None, norm1, norm2).ratio()

    def _find_similar_parent_issues(
        self, project_title: str
    ) -> list[dict[str, Any]]:
        """Find potentially matching parent issues using fuzzy search.

        Args:
            project_title: Project title to search for

        Returns:
            List of matching issues with similarity scores, sorted by similarity
        """
        # Extract keywords for search (first 3 words)
        keywords = project_title.replace(":", "").split()[:3]
        search_query = f'is:issue is:open {" ".join(keywords)} in:title'

        # Search GitHub
        results = self.github_adapter.search_issues(search_query, max_results=10)

        # Calculate similarity scores
        matches = []
        for issue in results:
            similarity = self._calculate_title_similarity(
                project_title,
                issue.title
            )
            matches.append({
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "similarity": similarity
            })

        # Sort by similarity (highest first)
        return sorted(matches, key=lambda x: x["similarity"], reverse=True)

    def _create_or_get_parent_issue(
        self, spec: ProjectSpec, milestone_id: int
    ) -> tuple[int, str]:
        """Create parent issue or use existing with duplicate detection.

        Args:
            spec: Project specification
            milestone_id: Milestone to assign to

        Returns:
            Tuple of (issue_number, issue_url)

        Raises:
            ValueError: If parent_issue_number provided but doesn't exist,
                       or if similar issues found without force_create_parent
        """
        # Case 1: Explicit parent issue number provided
        if spec.parent_issue_number is not None:
            parent_number = spec.parent_issue_number
            try:
                parent_issue = self.github_adapter.get_issue(parent_number)
                return parent_number, parent_issue.html_url
            except Exception as e:
                raise ValueError(
                    f"Parent issue #{parent_number} not found or inaccessible. "
                    f"Error: {e}"
                ) from e

        # Case 2: Auto-create parent with duplicate detection
        if not spec.force_create_parent:
            similar = self._find_similar_parent_issues(spec.project_title)

            # High confidence match (> 80% similarity)
            if similar and similar[0]["similarity"] > 0.8:
                match = similar[0]
                raise ValueError(
                    f"Found likely duplicate issue #{match['number']}: "
                    f"{match['title']}\n"
                    f"Similarity: {match['similarity']:.0%}\n"
                    f"URL: {match['url']}\n\n"
                    f"Options:\n"
                    f"1. Use existing issue: Set parent_issue_number: "
                    f"{match['number']}\n"
                    f"2. Force create new: Set force_create_parent: true"
                )

            # Medium confidence matches (> 60% similarity)
            if similar and similar[0]["similarity"] > 0.6:
                options = "\n".join([
                    f"  #{m['number']}: {m['title']} "
                    f"({m['similarity']:.0%} match)"
                    for m in similar[:3]
                ])
                raise ValueError(
                    f"Found {len(similar[:3])} potentially related issues:\n"
                    f"{options}\n\n"
                    f"Options:\n"
                    f"1. Use existing: Set parent_issue_number: <number>\n"
                    f"2. Modify title to be more specific\n"
                    f"3. Force create: Set force_create_parent: true"
                )

        # Case 3: No duplicates found or force_create_parent = true
        parent_response = self.github_adapter.create_issue(
            title=f"[PARENT] {spec.project_title}",
            body=(
                f"Parent issue for {spec.project_title}\n\n"
                "## Sub-issues\n(will be updated after creation)"
            ),
            milestone=milestone_id,
        )
        return parent_response["number"], parent_response["html_url"]

    def _create_sub_issues(
        self, phases: list[PhaseSpec], milestone_id: int
    ) -> dict[str, SubIssueMetadata]:
        """Create sub-issues for each phase.

        Args:
            phases: List of phase specifications
            milestone_id: Milestone to assign to

        Returns:
            Mapping of phase_id to SubIssueMetadata
        """
        sub_issues: dict[str, SubIssueMetadata] = {}
        for phase in phases:
            issue_response = self.github_adapter.create_issue(
                title=f"[{phase.phase_id}] {phase.title}",
                body=self._build_phase_issue_body(phase),
                milestone=milestone_id,
                labels=phase.labels,
            )
            sub_issues[phase.phase_id] = SubIssueMetadata(
                issue_number=issue_response["number"],
                url=issue_response["html_url"],
                depends_on=phase.depends_on,
                blocks=phase.blocks,
                status="open",
            )
        return sub_issues

    def _update_parent_with_links(
        self,
        parent_issue_number: int,
        spec: ProjectSpec,
        sub_issues: dict[str, SubIssueMetadata],
    ) -> None:
        """Update parent issue with sub-issue links.

        Args:
            parent_issue_number: Parent issue number
            spec: Project specification
            sub_issues: Created sub-issues
        """
        parent_body = self._build_parent_issue_body(spec, sub_issues)
        self.github_adapter.update_issue(
            issue_number=parent_issue_number,
            body=parent_body,
        )

    def _build_summary(
        self,
        project_metadata: ProjectMetadata,
        phases: list[PhaseSpec],
    ) -> ProjectSummary:
        """Build ProjectSummary result.

        Args:
            project_metadata: Complete project metadata
            phases: Phase specifications for dependency graph

        Returns:
            ProjectSummary with all project information
        """
        dependency_graph = self._build_dependency_graph(phases)
        return ProjectSummary(
            project_id=project_metadata.project_id,
            milestone_id=project_metadata.milestone_id,
            parent_issue=project_metadata.parent_issue,
            sub_issues=project_metadata.phases,
            dependency_graph=dependency_graph,
        )

    def _generate_project_id(self, project_title: str) -> str:
        """Generate project ID from title.
        
        Uses lowercase, hyphenated format with timestamp.
        """
        base = project_title.lower().replace(" ", "-")
        timestamp = int(time.time())
        return f"{base}-{timestamp}"

    def _build_phase_issue_body(self, phase: PhaseSpec) -> str:
        """Build issue body for phase sub-issue."""
        body = f"# {phase.title}\n\n"
        if phase.depends_on:
            body += f"**Depends on:** {', '.join(phase.depends_on)}\n\n"
        if phase.blocks:
            body += f"**Blocks:** {', '.join(phase.blocks)}\n\n"
        body += f"**Labels:** {', '.join(phase.labels)}\n"
        return body

    def _build_parent_issue_body(
        self, spec: ProjectSpec, sub_issues: dict[str, SubIssueMetadata]
    ) -> str:
        """Build parent issue body with sub-issue links."""
        body = f"# {spec.project_title}\n\n## Sub-issues\n\n"
        for phase in spec.phases:
            sub_issue = sub_issues[phase.phase_id]
            body += (
                f"- [{phase.phase_id}] {phase.title}: "
                f"#{sub_issue.issue_number}\n"
            )
        return body

    def _build_dependency_graph(self, phases: list[PhaseSpec]) -> dict[str, list[str]]:
        """Build dependency graph from phases (maps phase_id → list of blocked phase_ids)."""
        graph: dict[str, list[str]] = {}
        for phase in phases:
            graph[phase.phase_id] = phase.blocks.copy()
        return graph

    def _persist_project_metadata(self, metadata: ProjectMetadata) -> None:
        """Persist ProjectMetadata to .st3/projects.json (atomic write).

        Loads existing projects, adds new project, writes atomically via .tmp file.
        """
        # Load existing projects
        projects_file = self.workspace_root / ".st3" / "projects.json"
        existing_projects = self._load_projects()

        # Add new project
        existing_projects[metadata.project_id] = metadata.model_dump()

        # Write atomically via .tmp file
        projects_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = projects_file.with_suffix(".json.tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump({"projects": existing_projects}, f, indent=2)
        temp_file.replace(projects_file)

    def _load_projects(self) -> dict[str, Any]:
        """Load existing projects from .st3/projects.json.

        Returns:
            dict mapping project_id → project data, or empty dict if file
            doesn't exist
        """
        projects_file = self.workspace_root / ".st3" / "projects.json"
        if not projects_file.exists():
            return {}

        with open(projects_file, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        projects: dict[str, Any] = data.get("projects", {})
        return projects
