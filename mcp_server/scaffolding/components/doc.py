"""Design Document Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import BaseScaffolder


class DesignDocScaffolder(BaseScaffolder):
    """Scaffolds Design Documents."""

    def scaffold(self, name: str, **kwargs: Any) -> str:  # noqa: ANN401
        """Scaffold a Design Document.

        Args:
            name: Document title
            **kwargs: Document args (doc_type, etc.)

        Returns:
            Rendered Markdown
        """
        doc_type = kwargs.get("doc_type", "design")

        if doc_type == "generic":
            template_path = "documents/generic.md.jinja2"
        else:
            # Default design doc
            template_path = "documents/design.md.jinja2"

        try:
            return str(self.renderer.render(
                template_path,
                title=name,
                **kwargs
            ))
        except Exception as e:
            # Fallback to generic document template
            if "not found" in str(e).lower():
                return str(self.renderer.render(
                    "documents/generic.md.jinja2",
                    title=name,
                    **kwargs
                ))
            raise
