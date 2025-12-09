# Python Resource Template

**Layer:** Resources
**Inherits:** `BaseResource`
**Path:** `mcp_server/resources/<name>.py`

## Purpose
Exposes data as an MCP Resource (URI-addressable).

## Structure

```python
"""
<Docstring>

@layer: Resources
@dependencies: [mcp_server.resources.base]
"""
from mcp_server.resources.base import BaseResource

class <Name>(BaseResource):
    """<Docstring>"""
    
    uri_pattern = "<scheme>://<path>"
    description = "<Description>"
    mime_type = "application/json"

    async def read(self, uri: str) -> str:
        """Read the resource content."""
        if not self.matches(uri):
             raise ValueError("Invalid URI")
        
        # Implementation
        return "{}"
```
