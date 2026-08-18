# Phase-Gate MCP Server

> [!IMPORTANT]
> **Upgrading to v2.0.0?** If you are updating an existing workspace from v1.x to v2.0.0, follow the step-by-step **[Workspace Upgrade Guide](docs/setup/workspace-upgrade.md)** to run `pgmcp --upgrade` with automated fail-safe backups and smart asset preservation. See **[CHANGELOG.md](CHANGELOG.md)** for full release notes.

An MCP (Model Context Protocol) server that enforces structured software development lifecycles. It gives AI agents a toolset to navigate, manage, and execute work strictly within predefined project phases — ensuring consistent state management, quality enforcement, and repository orchestration.

---

## For AI Agents

> **STOP. Do not guess. Do not scan random files.**
>
> Read **[AGENTS.md](AGENTS.md)** immediately to initialize your cooperation protocol.
> It contains the binding tool priority matrix, TDD cycle protocol, three-agent model, and all operating constraints.
>
For MCP server architecture details, see [docs/reference/mcp_vision_reference.md](docs/reference/mcp_vision_reference.md).

---

## What It Does

Phase-Gate MCP Server acts as an orchestrator and gatekeeper between an AI agent and a software repository. Rather than allowing arbitrary modifications, it mandates a structured workflow and prevents phase progression until all deliverables and quality contracts are fulfilled.

**Supported workflow types:** `feature`, `bug`, `refactor`, `docs`, `hotfix`, `chore`, `epic`

Each workflow defines an ordered sequence of phases (e.g. `research → design → planning → implementation → validation → documentation → ready`). The server tracks which phase is active, enforces transitions, and manages TDD cycle state within implementation phases.

---

## Core Capabilities

- **Phase & cycle state management** — tracks active phase and TDD cycle via `.pgmcp/state.json`; blocks progression until contracts are met
- **Intelligent scaffolding** — generates code, documents, and test files from a centralised template registry with schema validation
- **Quality gates** — runs Ruff (format + lint), Pyright, import checks, and line-length checks before allowing commits or PRs
- **Repository orchestration** — native Git and GitHub integrations for branching, committing, PR creation, issue tracking, and label management
- **Config-driven policy enforcement** — workflow rules, phase contracts, artifact requirements, and quality thresholds defined in YAML

---

## Architecture

```
mcp_server/
├── core/          # Phase state engine, proxy, operation notes, error handling
├── managers/      # State persistence, git operations, pytest runner, QA manager
├── tools/         # MCP tool interfaces exposed to the agent
├── scaffolders/   # Jinja2 template engine and scaffold orchestration
├── scaffolding/   # Scaffolding metadata and registry helpers
├── validation/    # File and artifact validators
├── config/        # Settings, schema loading, config contracts
├── schemas/       # Pydantic schemas for all internal contracts
└── assets/        # Packaged release assets (templates, configs, docs)
```

Configuration lives in `.pgmcp/config/` (per-project, not in this repo):

| File | Purpose |
| :--- | :--- |
| `workflows.yaml` / `workphases.yaml` | Phase sequences and lifecycle states |
| `policies.yaml` / `enforcement.yaml` | Transition rules and strictness levels |
| `artifacts/` / `contracts.yaml` | Expected deliverables per phase |
| `quality.yaml` | Active quality gates and thresholds |
| `git.yaml` | Branch naming conventions |

---

## Environment Variables

| Variable | Required | Description |
| :--- | :--- | :--- |
| `PGMCP_WORKSPACE_ROOT` | Yes | Absolute path to the repository root |
| `PGMCP_SERVER_PROJECT_DIR` | No | Phase-gate config dir (default: `.pgmcp`) |
| `GITHUB_TOKEN` | Yes | Personal access token with `repo` and `workflow` scopes |
| `GITHUB_OWNER` | Yes | GitHub account or org name |
| `GITHUB_REPO` | Yes | Repository name |
| `GITHUB_PROJECT_NUMBER` | No | GitHub Projects number for issue tracking |
| `PGMCP_SERVER_NAME` | No | Server name reported in MCP handshake (default: `phase-gate-mcp`) |
| `LOG_LEVEL` | No | Logging verbosity (default: `INFO`) |

---

## Getting Started & Installation

**Requirements:** Python 3.11+

Depending on your use case, choose one of the following guides to get started:

- 🔄 **[Workspace Upgrade Guide (v1.x → v2.0.0)](docs/setup/workspace-upgrade.md)**: Step-by-step instructions for upgrading existing `.pgmcp/` workspace directories to server v2.0.0 using `pgmcp --upgrade` (offline wheel, local editable, or PyPI).
- 🚀 **[Manual Setup Guide](docs/setup/README.md)**: Detailed step-by-step instructions for manual installation and configuration in your IDE (VS Code or Google Antigravity).
- 🤖 **[Agentic Bootstrap Guide](docs/setup/agentic-bootstrap.md)**: A step-by-step automated guide to help AI agents bootstrap `pgmcp` in a new workspace or integrate it into an existing repository without manual terminal commands.

### Local Development Setup

To clone and set up the repository for local development:

```bash
git clone https://github.com/MikeyVK/phase-gate-mcp.git
cd phase-gate-mcp
pip install -e .[dev]
```

### Starting the server

The entry point is `mcp_server.core.proxy` — a thin proxy that handles stdio transport and auto-restart on exit code 42:

```bash
python -m mcp_server.core.proxy
```

### CLI Commands (`pgmcp`)

- **`pgmcp --init`**: Initialize `.pgmcp/` workspace configuration and template assets in a new repository.
- **`pgmcp --upgrade`**: Upgrade existing `.pgmcp/` workspace configuration to match server release v2.0.0 (creates fail-safe timestamped backup, updates templates, preserves user custom YAML configs, and retains dynamic runtime state). See the **[Workspace Upgrade Guide](docs/setup/workspace-upgrade.md)** for detailed instructions.

For MCP client configuration, see [docs/setup/mcp.json](docs/setup/mcp.json) for a reference server definition.

---

## Running Tests

```bash
pytest tests/mcp_server/
```

For coverage:

```bash
pytest tests/mcp_server/ --cov=mcp_server --cov-branch --cov-fail-under=90
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
