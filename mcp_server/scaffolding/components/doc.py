"""Design Document Scaffolder Component."""
from typing import Any

from mcp_server.core.exceptions import ExecutionError
from mcp_server.scaffolding.base import ComponentScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer


class DesignDocScaffolder(ComponentScaffolder):
    """Scaffolds Design Documents."""

    def __init__(self, renderer: JinjaRenderer) -> None:
        """Initialize design doc scaffolder."""
        self.renderer = renderer

    def validate(self, **kwargs: Any) -> bool:
        """Validate document arguments."""
        # No strict naming convention for titles, but could add checks here
        return True

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a Design Document.

        Args:
            name: Document title
            **kwargs: Document args

        Returns:
            Rendered Markdown
        """
        try:
            return self.renderer.render(
                "documents/design.md.jinja2",
                title=name,
                **kwargs
            )
        except ExecutionError:
            return self._render_fallback(name, **kwargs)

    def _render_fallback(self, title: str, **kwargs: Any) -> str:
        """Fallback rendering."""
        author = kwargs.get("author")
        summary = kwargs.get("summary")
        sections = kwargs.get("sections")
        status = kwargs.get("status", "DRAFT")

        lines = [
            f"# {title}",
            "",
            f"**Status:** {status}",
        ]

        if author:
            lines.append(f"**Author:** {author}")

        lines.append("")

        if summary:
            lines.extend(["## Summary", "", summary, ""])

        for section in (sections or ["Overview", "Requirements", "Design"]):
            lines.extend([f"## {section}", "", "TODO: Add content", ""])

        return "\n".join(lines)
