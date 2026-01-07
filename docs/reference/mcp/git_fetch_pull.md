# Git Fetch & Pull Tools Reference - S1mpleTraderV3

<!--
GENERATED DOCUMENT
Template: generic.md.jinja2
Type: Tool Reference
-->

<!-- ═══════════════════════════════════════════════════════════════════════════
     HEADER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

**Status:** DRAFT
**Version:** 0.1
**Last Updated:** 2026-01-07

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTEXT SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Purpose

Reference documentation for the `git_fetch` and `git_pull` MCP tools.

These tools exist to keep local branches in sync with remote state using the ST3 MCP toolset (instead of ad-hoc CLI usage), while maintaining the reliability constraints required for stdio-based MCP servers.

## Scope

**In Scope:**
- Tool schemas (inputs, defaults)
- Tool behavior and output semantics
- Error handling behavior (what becomes a `ToolResult.error`)
- Thread offloading behavior via `anyio.to_thread.run_sync`
- `git_pull` phase-state re-sync behavior (best-effort)

**Out of Scope:**
- Full Git workflow guidance (branching, rebasing strategy)
- Enforced policy (when you *must* fetch/pull) — that is decided by workflow rules

## Prerequisites

- A valid git repository (this workspace)
- A configured remote (usually `origin`)
- For `git_pull`: upstream tracking configured for the current branch

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTENT SECTION
     ═══════════════════════════════════════════════════════════════════════════ -->

## Tools Overview

**Registration:** tools are registered in `mcp_server/server.py`.

**Execution model:** both tools offload git operations to a worker thread using `anyio.to_thread.run_sync` to reduce the risk of blocking the event loop / stdio deadlocks (see Issue #85 findings).

**Non-interactive behavior:** underlying git operations are configured to avoid interactive prompts and paging.

## git_fetch

**Tool Name:** `git_fetch`

**Description:** Fetch updates from a remote.

**Location:** `mcp_server/tools/git_fetch_tool.py`

### Input Schema

| Field | Type | Default | Meaning |
|------|------|---------|---------|
| `remote` | `str` | `"origin"` | Remote name to fetch from |
| `prune` | `bool` | `false` | Prune deleted remote-tracking branches |

### Behavior

- Runs a `fetch` against the specified remote.
- Allowed even with a dirty working tree (fetch does not modify the working tree).

### Output

- On success: `ToolResult.text(...)` containing a short summary.
- On failure:
  - `MCPError` subclasses become `ToolResult.error(str(exc))`.
  - Other runtime failures become `ToolResult.error("Fetch failed: ...")`.

## git_pull

**Tool Name:** `git_pull`

**Description:** Pull updates from a remote into the current branch.

**Location:** `mcp_server/tools/git_pull_tool.py`

### Input Schema

| Field | Type | Default | Meaning |
|------|------|---------|---------|
| `remote` | `str` | `"origin"` | Remote name to pull from |
| `rebase` | `bool` | `false` | Use rebase instead of merge |

### Behavior

- Performs conservative preflight checks via `GitManager` before running pull (safe-by-default).
- Offloads the pull to a worker thread.
- After a successful pull, performs a best-effort phase-state re-sync (does not fail the tool if sync fails).

### Output

- On success: `ToolResult.text(...)` containing a short summary.
- On failure:
  - `MCPError` subclasses become `ToolResult.error(str(exc))`.
  - Other runtime failures become `ToolResult.error("Pull failed: ...")`.

## Examples

### Fetch from origin (default)

```json
{ "remote": "origin", "prune": false }
```

### Fetch and prune remote-tracking branches

```json
{ "remote": "origin", "prune": true }
```

### Pull from origin (default)

```json
{ "remote": "origin", "rebase": false }
```

### Pull with rebase

```json
{ "remote": "origin", "rebase": true }
```

## Error Handling

Both tools convert common errors into `ToolResult.error(...)` so the MCP server remains stable.

Typical error categories:
- Preflight errors (e.g., dirty tree for pull, missing upstream)
- Git runtime failures (network, auth, ref update failures)
- State sync errors after pull (logged as warnings; tool still returns success)

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     FOOTER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Related Documentation

- [docs/reference/mcp/MCP_TOOLS.md](MCP_TOOLS.md) - High-level MCP tools overview
- [docs/development/issue94/research.md](../../development/issue94/research.md) - Issue #94 research
- [docs/development/issue94/planning.md](../../development/issue94/planning.md) - Issue #94 planning

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-07 | GitHub Copilot | Initial creation |
