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

We provide automated scaffolding via `scaffold_artifact` to ensure all components adhere to our [Coding Standards](../coding_standards/CODE_STYLE.md).

### Creating Artifacts

Use the unified `scaffold_artifact` tool to generate ANY artifact (code or docs):

| Artifact Type | Example Usage |
| :--- | :--- |
| **DTO** | `scaffold_artifact(artifact_type="dto", name="ExecutionRequest", context={...})` |
| **Worker** | `scaffold_artifact(artifact_type="worker", name="MomentumScanner", context={...})` |
| **Adapter** | `scaffold_artifact(artifact_type="adapter", name="IBAdapter", context={...})` |
| **Design Doc** | `scaffold_artifact(artifact_type="design", name="momentum-scanner-design", context={...})` |
| **Architecture Doc** | `scaffold_artifact(artifact_type="architecture", name="system-overview", context={...})` |

All artifacts are generated from templates in `.st3/artifacts.yaml` registry.

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
| **Documentation** | `validate_doc` |
| **GitHub** | `create_issue`, `submit_pr` |
| **Implementation** | `scaffold_artifact` (unified tool for code+docs) |
| **Quality** | `run_quality_gates`, `fix_whitespace` |
| **Git** | `create_feature_branch`, `commit_tdd_phase` |
