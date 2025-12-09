# MCP Server Documentation

This directory contains the authoritative documentation for the SimpleTraderV3 MCP Server.

## Core Documentation

- **[Architecture](ARCHITECTURE.md)**  
  High-level design, layers, and component responsibilities.

- **[Implementation Plan](IMPLEMENTATION_PLAN.md)**  
  Step-by-step roadmap, build order, and milestones.

- **[Resources](RESOURCES.md)**  
  Specification of available MCP resources (`st3://...`) for reading project state.

- **[Tools](TOOLS.md)**  
  Specification of available MCP tools for performing actions.

- **[Phase Workflows](PHASE_WORKFLOWS.md)**  
  Detailed workflows for development phases (Discovery, Planning, Implementation, etc.).

- **[GitHub Setup](GITHUB_SETUP.md)**  
  Configuration guide for GitHub integration (Secrets, Permissions, Project Board).

## Standardized Development

We provide automated scaffolding to ensure all components adhere to our [Coding Standards](../coding_standards/CODE_STYLE.md).

### Creating Components

Use the `scaffold_component` tool to generate new files:

| Component | Type | Example |
| :--- | :--- | :--- |
| **MCP Tool** | `tool` | `scaffold_component(type="tool", name="MyTool", ...)` |
| **MCP Resource** | `resource` | `scaffold_component(type="resource", name="MyResource", ...)` |
| **Service** | `service` | `scaffold_component(type="service", service_type="command", ...)` |
| **Schema** | `schema` | `scaffold_component(type="schema", name="MyConfig", ...)` |
| **Interface** | `interface` | `scaffold_component(type="interface", name="IMyContract", ...)` |

For detailed reference templates, see **[docs/reference/templates](../reference/templates/README.md)**.

## Quick Reference

| Resource URI | Description |
|--------------|-------------|
| `st3://status/implementation` | Live implementation status and metrics |
| `st3://github/issues` | Active GitHub issues |
| `st3://git/status` | Current branch and TDD phase |

| Tool Category | Key Tools |
|---------------|-----------|
| **Discovery** | `search_documentation`, `get_work_context` |
| **Documentation** | `scaffold_document`, `validate_document_structure` |
| **GitHub** | `create_issue`, `submit_pr` |
| **Implementation** | `scaffold_component`, `scaffold_design_doc` |
| **Quality** | `run_quality_gates`, `fix_whitespace` |
| **Git** | `create_feature_branch`, `commit_tdd_phase` |
