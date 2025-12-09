# ST3 Workflow MCP Server - User Guide

**Status:** v1.0 (Foundation)
**Last Updated:** 2025-01-21

---

## 1. Introduction

The ST3 Workflow MCP Server is a Model Context Protocol server designed to assist with the development of the SimpleTraderV3 project. It provides AI agents with context about the project's state, coding standards, and facilitates workflows like TDD and GitHub integration.

## 2. Installation

The MCP server is part of the repository. You can install it in editable mode:

```bash
# From the root of the repository
pip install -e "./mcp_server"

# To include development dependencies (for running tests)
pip install -e "./mcp_server[dev]"
```

## 3. Configuration

The server is configured via a YAML file (`mcp_config.yaml`) or environment variables.

### 3.1 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub Personal Access Token (required for GitHub integration) | None |
| `MCP_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `MCP_CONFIG_PATH` | Path to configuration file | `mcp_config.yaml` |

### 3.2 Configuration File (`mcp_config.yaml`)

Example configuration:

```yaml
server:
  name: "st3-workflow"
  version: "1.0.0"
  workspace_root: "."

logging:
  level: "INFO"
  audit_log: "logs/mcp_audit.log"

github:
  owner: "MikeyVK"
  repo: "S1mpleTraderV3"
  project_number: 1
```

## 4. Running the Server

To run the server using the `mcp` SDK's standard I/O transport:

```bash
python -m mcp_server
```

This command starts the server and listens on `stdin` for JSON-RPC messages, writing responses to `stdout`. Logs are written to `stderr` and the audit log file.

## 5. Claude Desktop Integration

To use this MCP server with Claude Desktop, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "st3-workflow": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/absolute/path/to/SimpleTraderV3",
      "env": {
        "GITHUB_TOKEN": "your-github-token"
      }
    }
  }
}
```

Replace `/absolute/path/to/SimpleTraderV3` with the actual path to your repository.

## 6. Available Resources

Currently, the following resources are available:

### `st3://rules/coding_standards`

Returns a JSON object containing the project's coding standards, including:
- Python version and style guide (PEP 8)
- Testing requirements
- Tooling (ruff, pyright, pytest)

**Usage:**
read_resource("st3://rules/coding_standards")

## 7. Available Tools

*Note: Concrete tools are currently under development. This section describes the foundation.*

The server infrastructure supports tools that return text, images, or embedded resources.

### Implemented Infrastructure
- **BaseTool:** Abstract base class for all tools.
- **ToolResult:** structured result object supporting text, image, and resource content.
- **Error Handling:** Graceful error reporting to the agent.

Future updates will include tools for:
- Git operations (branching, committing)
- GitHub integration (issues, PRs)
- Code scaffolding
- Quality checks
