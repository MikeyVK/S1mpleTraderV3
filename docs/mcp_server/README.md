# MCP Server Documentation

This directory is the operational index for the S1mpleTrader V3 MCP Server.

## What Is Authoritative

To avoid contract drift, the authoritative public MCP tool documentation lives in:

- [docs/reference/mcp/MCP_TOOLS.md](../reference/mcp/MCP_TOOLS.md) for the public tool inventory
- [docs/reference/mcp/tools/README.md](../reference/mcp/tools/README.md) for category navigation
- [docs/reference/mcp/tools/git.md](../reference/mcp/tools/git.md) for git workflow tools
- [docs/reference/mcp/tools/github.md](../reference/mcp/tools/github.md) for issue, PR, label, and milestone tools
- [docs/reference/mcp/tools/project.md](../reference/mcp/tools/project.md) for project and phase tools
- [docs/reference/mcp/tools/quality.md](../reference/mcp/tools/quality.md) for tests, gates, and validation
- [docs/reference/mcp/tools/scaffolding.md](../reference/mcp/tools/scaffolding.md) for `scaffold_artifact`
- [docs/reference/mcp/tools/discovery.md](../reference/mcp/tools/discovery.md) for `search_documentation` and `get_work_context`

This directory links the MCP server architecture and operational guidance around those references.

## Core Documentation

- **[Architecture](ARCHITECTURE.md)**
  High-level design, layers, component responsibilities, and composition root.
- **[Implementation Plan](IMPLEMENTATION_PLAN.md)**
  Historical roadmap for the MCP server rollout.
- **[Resources](RESOURCES.md)**
  Specification of available MCP resources (`st3://...`).
- **[Tools](TOOLS.md)**
  Current public tool surface summary derived from [mcp_server/server.py](../../mcp_server/server.py).
- **[Phase Workflows](PHASE_WORKFLOWS.md)**
  Development phase workflows and lifecycle guidance.
- **[GitHub Setup](GITHUB_SETUP.md)**
  GitHub integration and token setup.

## Standardized Development

Use `scaffold_artifact` to generate code and documentation artifacts from the artifact registry in `.st3/config/artifacts.yaml`.

| Artifact Type | Example Usage |
| :--- | :--- |
| **DTO** | `scaffold_artifact(artifact_type="dto", name="ExecutionRequest", context={...})` |
| **Worker** | `scaffold_artifact(artifact_type="worker", name="MomentumScanner", context={...})` |
| **Adapter** | `scaffold_artifact(artifact_type="adapter", name="IBAdapter", context={...})` |
| **Design Doc** | `scaffold_artifact(artifact_type="design", name="momentum-scanner-design", context={...})` |
| **Architecture Doc** | `scaffold_artifact(artifact_type="architecture", name="system-overview", context={...})` |

For template and registry details, see [docs/reference/mcp/tools/scaffolding.md](../reference/mcp/tools/scaffolding.md).

## Quick Reference

### Resources

| Resource URI | Description |
|--------------|-------------|
| `st3://rules/coding_standards` | Active coding standards derived from `.st3/config/quality.yaml` |
| `st3://status/phase` | Current phase and git status |
| `st3://github/issues` | Active GitHub issues resource |

### Public Tool Surface

| Category | Key Tools |
|----------|-----------|
| **Discovery** | `search_documentation`, `get_work_context` |
| **Git** | `create_branch`, `git_add_or_commit`, `git_checkout`, `git_fetch`, `git_pull`, `git_push`, `git_merge`, `git_delete_branch`, `git_stash`, `git_restore`, `git_list_branches`, `git_diff_stat`, `get_parent_branch` |
| **GitHub** | `create_issue`, `list_issues`, `get_issue`, `update_issue`, `close_issue`, `submit_pr`, `list_prs`, `merge_pr`, `list_labels`, `create_label`, `delete_label`, `add_labels`, `remove_labels`, `list_milestones`, `create_milestone`, `close_milestone` |
| **Project & Phase** | `initialize_project`, `get_project_plan`, `save_planning_deliverables`, `update_planning_deliverables`, `transition_phase`, `force_phase_transition`, `transition_cycle`, `force_cycle_transition` |
| **Editing & Scaffolding** | `safe_edit_file`, `create_file`, `scaffold_artifact` |
| **Quality** | `run_quality_gates`, `run_tests`, `validate_architecture`, `validate_dto`, `validate_template` |
| **Admin** | `health_check`, `restart_server` |

### PR Workflow

Use `submit_pr` for public PR creation. The tool:

1. Neutralizes branch-local artifacts against the merge-base.
2. Commits the neutralization in `ready` phase.
3. Pushes the branch.
4. Creates the GitHub PR.
5. Writes `PRStatus.OPEN` to cache.

`submit_pr` is blocked unless the workflow phase is `ready`, and all `branch_mutating` tools are blocked while the branch has an open PR.
