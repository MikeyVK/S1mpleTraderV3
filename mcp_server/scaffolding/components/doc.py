"""Design Document Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import BaseScaffolder


class DesignDocScaffolder(BaseScaffolder):
    """Scaffolds Design Documents."""

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a Design Document.

        Args:
            name: Document title
            **kwargs: Document args (doc_type, etc.)

        Returns:
            Rendered Markdown
        """
        doc_type = kwargs.get("doc_type", "design")

        if doc_type == "generic":
            return str(self.renderer.render(
                "documents/generic.md.jinja2",
                title=name,
                **kwargs
            ))

        # Default design doc
        return str(self.renderer.render(
            "documents/design.md.jinja2",
            title=name,
            **kwargs
        ))
