# Component Templates

This directory contains reference templates for Python code components. These serve as the **Source of Truth** for the project's coding standards.

## Available Templates

| Template | Type | Use Case |
| :--- | :--- | :--- |
| **[Tool](python_tool.md)** | `tool` | MCP Tools for AI execution. |
| **[Resource](python_resource.md)** | `resource` | MCP Resources for data reading. |
| **[Service](python_service.md)** | `service` | Business logic (Orchestrator/Command/Query). |
| **[Schema](python_schema.md)** | `schema` | Pydantic configuration/data models. |
| **[Interface](python_interface.md)** | `interface` | `typing.Protocol` dependency contracts. |

## Automation

These templates are automated via the `scaffold_component` tool.
Example:
```bash
# Generate a new tool based on python_tool.md standards
scaffold_component(type="tool", name="MyTool", ...)
```
