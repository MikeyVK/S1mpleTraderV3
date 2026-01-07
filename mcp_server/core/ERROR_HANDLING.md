# MCP Tool Error Handling

## Overview

This module provides automatic error handling for all MCP tools to prevent VS Code from disabling tools when exceptions occur during execution.

## Problem

When MCP tools raise uncaught exceptions:
1. VS Code MCP client interprets it as a tool crash
2. VS Code marks the tool as "disabled" for the entire session
3. Agent sees misleading message: "Tool is currently disabled by the user"
4. Only recovery: Restart VS Code or start new chat session

## Solution

The `@tool_error_handler` decorator catches all exceptions and converts them to `ToolResult.error()` responses:
- VS Code receives valid response (not a crash)
- Tool remains "enabled" and callable
- Agent gets actionable error message
- Errors are logged for debugging

## How It Works

### Automatic Application

All tools inheriting from `BaseTool` automatically have error handling via `__init_subclass__`:

```python
class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful"
    
    async def execute(self, params: MyInput) -> ToolResult:
        # Just write normal code - errors handled automatically!
        if not params.value:
            raise ValueError("value is required")
        
        result = do_something(params.value)
        return ToolResult.text(f"Result: {result}")
```

### Error Classification

Exceptions are automatically classified and logged appropriately:

| Exception Type | Category | Log Level | Example |
|---------------|----------|-----------|---------|
| `ValueError` | USER | Warning | Invalid parameter value |
| `FileNotFoundError` | CONFIG | Error | Missing configuration file |
| Other exceptions | BUG | Exception | Unexpected runtime error |

### Example Flow

```python
# Tool raises ValueError
class ValidateTool(BaseTool):
    async def execute(self, params: dict) -> ToolResult:
        if "name" not in params:
            raise ValueError("name parameter required")
        return ToolResult.text("Valid!")

# Without decorator (old behavior):
# → VS Code sees exception
# → Marks tool as disabled
# → Agent cannot use tool anymore

# With decorator (new behavior):
# → Exception caught
# → Returns ToolResult.error("Invalid input: name parameter required")
# → VS Code receives valid response
# → Tool stays enabled
# → Agent sees error message and can retry with fix
```

## Benefits

1. **Tool Availability**: Tools stay enabled after errors
2. **Better UX**: Agent gets actionable error messages
3. **Debugging**: All errors logged with context
4. **Zero Overhead**: Automatic via base class
5. **Clean Code**: No try-catch blocks in tool code

## Implementation Details

- **File**: `mcp_server/core/error_handling.py`
- **Decorator**: `@tool_error_handler`
- **Base Class Hook**: `BaseTool.__init_subclass__`
- **Tests**: 
  - Unit: `tests/unit/mcp_server/core/test_error_handling.py`
  - Integration: `tests/unit/mcp_server/tools/test_base_tool_error_handling.py`

## Manual Usage (if needed)

If you need to use the decorator outside of `BaseTool`:

```python
from mcp_server.core import tool_error_handler

@tool_error_handler
async def my_async_function() -> ToolResult:
    # Your code here
    ...
```

## Related Issues

- Issue #77: MCP Tool Error Handling & VS Code Tool Availability
- Design Doc: `docs/development/issue77/error_handling_design.md`
- Research: `docs/development/issue77/research.md`
