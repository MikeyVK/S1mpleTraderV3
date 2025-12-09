"""Documentation Manager."""
import re
from pathlib import Path
from typing import Any

from mcp_server.config.settings import settings
from mcp_server.core.exceptions import ValidationError


class DocManager:
    """Manager for documentation operations.

    Provides template validation and semantic search across docs/ files.
    """

    TEMPLATES = {
        "architecture": "ARCHITECTURE_TEMPLATE.md",
        "design": "DESIGN_TEMPLATE.md",
        "reference": "REFERENCE_TEMPLATE.md",
        "tracking": "TRACKING_TEMPLATE.md"
    }

    SCOPE_DIRS = {
        "architecture": "architecture",
        "coding_standards": "coding_standards",
        "development": "development",
        "reference": "reference",
        "implementation": "implementation",
    }

    def __init__(self, docs_dir: Path | None = None) -> None:
        """Initialize DocManager.

        Args:
            docs_dir: Path to docs directory. Defaults to workspace/docs.
        """
        if docs_dir is None:
            # pylint: disable=no-member
            workspace = Path(settings.server.workspace_root)
            self.docs_dir = workspace / "docs"
        else:
            self.docs_dir = docs_dir

        self._index: list[dict[str, Any]] = []
        self._build_index()

    def _build_index(self) -> None:
        """Build index of all markdown files in docs directory."""
        self._index = []

        if not self.docs_dir.exists():
            return

        for md_file in self.docs_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                title = self._extract_title(content)
                relative_path = str(md_file.relative_to(self.docs_dir.parent))

                self._index.append({
                    "path": md_file,
                    "relative_path": relative_path,
                    "title": title,
                    "content": content,
                    "lines": content.split("\n")
                })
            except (OSError, UnicodeDecodeError):
                continue  # Skip unreadable files

    def _extract_title(self, content: str) -> str:
        """Extract title from markdown content."""
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        return match.group(1) if match else "Untitled"

    def search(
        self,
        query: str,
        scope: str | None = None,
        max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search documentation for matching content.

        Args:
            query: Search query string.
            scope: Optional scope to filter by (e.g., 'architecture').
            max_results: Maximum number of results to return.

        Returns:
            List of search results with file_path, title, snippet,
            relevance_score, and line_number.
        """
        if not query or not query.strip():
            return []

        query_lower = query.lower()
        query_terms = query_lower.split()
        results: list[dict[str, Any]] = []

        for doc in self._index:
            # Filter by scope if specified
            if scope and scope in self.SCOPE_DIRS:
                scope_dir = self.SCOPE_DIRS[scope]
                if scope_dir not in doc["relative_path"]:
                    continue

            # Search through lines
            content_lower = doc["content"].lower()

            # Calculate relevance score based on term matches
            score = self._calculate_relevance(content_lower, query_terms)

            if score > 0:
                # Find best matching line
                line_number, snippet = self._find_best_match(
                    doc["lines"], query_terms
                )

                results.append({
                    "file_path": doc["relative_path"],
                    "title": doc["title"],
                    "snippet": snippet,
                    "relevance_score": min(score, 1.0),
                    "line_number": line_number
                })

        # Sort by relevance and limit results
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:max_results]

    def _calculate_relevance(
        self, content: str, query_terms: list[str]
    ) -> float:
        """Calculate relevance score for content against query terms."""
        if not query_terms:
            return 0.0

        matches = 0
        for term in query_terms:
            if term in content:
                # Count occurrences
                count = content.count(term)
                matches += min(count, 5)  # Cap contribution per term

        # Normalize score
        base_score = matches / (len(query_terms) * 5)

        # Boost exact phrase matches
        query_phrase = " ".join(query_terms)
        if query_phrase in content:
            base_score += 0.3

        return min(base_score, 1.0)

    def _find_best_match(
        self, lines: list[str], query_terms: list[str]
    ) -> tuple[int, str]:
        """Find the line with best match and extract snippet.

        Returns:
            Tuple of (line_number, snippet).
        """
        best_line = 1
        best_score = 0
        best_snippet = ""

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            score = sum(1 for term in query_terms if term in line_lower)

            if score > best_score:
                best_score = score
                best_line = i
                # Create snippet with context
                start = max(0, i - 2)
                end = min(len(lines), i + 1)
                snippet_lines = lines[start:end]
                best_snippet = " ".join(
                    line.strip() for line in snippet_lines if line.strip()
                )[:150]

        # Default snippet if no good match found
        if not best_snippet and lines:
            best_snippet = " ".join(
                line.strip() for line in lines[:3] if line.strip()
            )[:150]

        return best_line, best_snippet

    def get_document_count(self) -> int:
        """Return the number of indexed documents."""
        return len(self._index)

    def list_documents(self) -> list[str]:
        """Return list of all indexed document paths."""
        return [doc["relative_path"] for doc in self._index]

    def validate_structure(self, content: str, template_type: str) -> dict[str, Any]:
        """Validate document structure against template."""
        if template_type not in self.TEMPLATES:
            raise ValidationError(f"Unknown template type: {template_type}")

        # Basic validation logic (stubbed)
        issues = []
        if "# " not in content:
            issues.append("Missing title")

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

    def get_template(self, template_type: str) -> str:
        """Get template content."""
        if template_type not in self.TEMPLATES:
            raise ValidationError(f"Unknown template type: {template_type}")

        # In real implementation, read from file
        return f"# {{TITLE}}\n\n## Overview\n\n(Template: {template_type})"
