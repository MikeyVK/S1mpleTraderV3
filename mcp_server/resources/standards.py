"""Resource for coding standards."""
import json
from pathlib import Path

from mcp_server.config.quality_config import QualityConfig
from mcp_server.resources.base import BaseResource


class StandardsResource(BaseResource):
    """Provides access to coding standards."""

    uri_pattern = "st3://rules/coding_standards"
    description = "Project coding standards and conventions"

    async def read(self, uri: str) -> str:
        """Read coding standards from quality.yaml."""
        # Load quality configuration from .st3/quality.yaml
        config_path = Path(".st3/quality.yaml")
        quality_config = QualityConfig.load(config_path)

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
            },
            "quality_gates": {
                "active_gates": quality_config.active_gates,
                "gate_count": len(quality_config.active_gates),
            }
        }

        return json.dumps(standards, indent=2)
