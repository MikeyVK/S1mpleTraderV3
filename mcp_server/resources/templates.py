"""Resource for templates."""
import json
from mcp_server.resources.base import BaseResource
from mcp_server.managers.doc_manager import DocManager

class TemplatesResource(BaseResource):
    """Resource for available templates."""

    uri_pattern = "st3://templates/list"
    description = "List of available documentation templates"

    async def read(self, uri: str) -> str:
        return json.dumps(DocManager.TEMPLATES, indent=2)
