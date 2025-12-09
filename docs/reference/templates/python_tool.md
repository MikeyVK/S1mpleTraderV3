# Python Tool Template

**Layer:** Tools
**Inherits:** `BaseTool`
**Path:** `mcp_server/tools/<name>.py`

## Purpose
Implements a specific MCP Tool that exposes functionality to the AI.

## Structure

```python
"""
<Docstring describing the tool's purpose>

@layer: Tools
@dependencies: [mcp_server.tools.base]
"""
from typing import Any
from mcp_server.tools.base import BaseTool, ToolResult

class <Name>Tool(BaseTool):
    """<Docstring>"""
    
    name = "<name_snake_case>"
    description = "<Description>"
    
    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                # Define fields here
            }
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool logic."""
        # Implementation
        return ToolResult.text("Success")
```
