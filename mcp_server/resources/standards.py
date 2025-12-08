"""Resource for coding standards."""
import json

from mcp_server.resources.base import BaseResource


class StandardsResource(BaseResource):
    """Provides access to coding standards."""

    uri_pattern = "st3://rules/coding_standards"
    description = "Project coding standards and conventions"

    async def read(self, uri: str) -> str:
        """Read coding standards from file."""
        # In a real implementation, this might read from a file in docs/
        # For now, we return a structured JSON based on known standards

        standards = {
            "python": {
                "version": ">=3.11",
                "style": "pep8",
                "max_line_length": 100,
            },
            "testing": {
                "framework": "pytest",
                "coverage_min": 80,
            },
            "tools": {
                "formatter": "ruff",
                "linter": "ruff",
                "type_checker": "pyright",
            }
        }

        return json.dumps(standards, indent=2)
