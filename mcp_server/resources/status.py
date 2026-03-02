"""Status resource."""
import json
import time

from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.core.exceptions import MCPSystemError
from mcp_server.resources.base import BaseResource


class StatusResource(BaseResource):
    """Resource for project status."""

    uri_pattern = "st3://status/phase"
    description = "Current development phase and git status"

    def __init__(self, git_adapter: GitAdapter | None = None) -> None:
        self.git = git_adapter or GitAdapter()

    async def read(self, _uri: str) -> str:
        """Read status."""
        try:
            git_status = self.git.get_status()

            # Simple logic to determine phase based on branch
            branch = git_status["branch"]
            phase = "Implementation"  # Default
            if branch == "main":
                phase = "Maintenance"
            elif branch.startswith("docs/"):
                phase = "Documentation"

            data = {
                "current_phase": phase,
                "active_branch": branch,
                "is_clean": git_status["is_clean"],
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            return json.dumps(data, indent=2)

        except MCPSystemError as e:
            return json.dumps({"error": str(e)})
