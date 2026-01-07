# Issue 94 - Missing ST3 Git Tools (Research) - S1mpleTraderV3

<!--
GENERATED DOCUMENT
Template: generic.md.jinja2
Type: generic
-->

<!-- ═══════════════════════════════════════════════════════════════════════════
     HEADER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

**Status:** DRAFT
**Version:** 0.2
**Last Updated:** 2026-01-07

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTEXT SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Purpose

Inventory the current MCP git tool surface in this repo and specify what’s missing (notably remote sync operations like fetch/pull), plus a minimal/safe contract proposal for adding those tools.

## Scope

**In Scope:**
- Inventory existing git tools and their backing manager/adapter methods.
- Identify missing operations required for “sync with remote” workflows.
- Propose minimal tool contracts + safety defaults.
- Outline a test plan for the missing tools.

**Out of Scope:**
- Large git UX features (interactive conflict resolution, partial staging UI, branch selection UIs).
- Rewriting existing git tooling or changing PhaseStateEngine semantics.
- Adding extra remote management commands unless required by fetch/pull.

## Prerequisites

- Workspace is a valid Git repository.
- GitPython is installed and functional.
- For remote sync operations: an `origin` remote exists and (for pull) upstream tracking is configured.

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTENT SECTION
     ═══════════════════════════════════════════════════════════════════════════ -->

## Overview

Today, the repo’s MCP git tools cover local operations (status/checkout/merge/stash/etc.) and `push`, but there is no equivalent for “sync from remote” (`fetch` / `pull`). This gap forces developers to drop to CLI, which is error-prone in this codebase because MCP git tools also handle PhaseStateEngine state synchronization during some operations (notably checkout).

The goal of Issue 94 is to provide the missing remote sync primitives so common workflows can remain tool-first.

## Current Tooling Inventory

### MCP git tools (server-side)

Implemented in `mcp_server/tools/git_tools.py`:
- `create_branch` (CreateBranchTool)
- `git_status` (GitStatusTool)
- `git_add_or_commit` (GitCommitTool)
- `git_restore` (GitRestoreTool)
- `git_checkout` (GitCheckoutTool) — includes PhaseStateEngine sync after checkout
- `git_push` (GitPushTool)
- `git_merge` (GitMergeTool)
- `git_delete_branch` (GitDeleteBranchTool)
- `git_stash` (GitStashTool)
- `get_parent_branch` (GetParentBranchTool) — reads “parent” from PhaseStateEngine state

### Business layer

In `mcp_server/managers/git_manager.py` (wraps adapter with validation/preflight):
- Branch creation conventions and clean-tree preflight for merge/branch creation.
- Commit helpers with TDD prefixes.
- Delegates actual git operations to `mcp_server/adapters/git_adapter.py`.

### Git adapter

In `mcp_server/adapters/git_adapter.py`:
- Uses GitPython `Repo` for local ops: status, checkout, commit, restore, merge, delete branch, stash.
- Remote-facing support exists only for `push`.

## Gaps / Missing Operations

### Missing remote sync operations

Not implemented (tool/manager/adapter):
- `fetch` (at least `origin fetch`)
- `pull` (at least `origin pull` / upstream pull)

### Secondary missing pieces (may be required by pull)

To support a safe `pull` contract, we likely need one or more of:
- Upstream detection / validation for the current branch (is there a tracking branch?).
- A clear policy for dirty working trees (block vs auto-stash).

## Proposed Tool Contracts

Goal: keep contracts minimal, predictable, and safe-by-default. Prefer “fetch first” workflows; make `pull` stricter than `fetch`.

### `git_fetch`

**Tool name:** `git_fetch`

**Inputs (minimal):**
- `remote: str = "origin"`
- `prune: bool = False` (optional)

**Behavior:**
- Does not require a clean working tree.
- Fails with a clear error if the remote does not exist.
- Does not modify local branches directly (only updates remote-tracking refs).

**Output:**
- Text summary indicating which remote was fetched (and whether prune ran).

### `git_pull`

**Tool name:** `git_pull`

**Inputs (minimal):**
- `remote: str = "origin"` (optional; if upstream exists, allow omitting remote and use upstream)
- `rebase: bool = False` (optional; default merge-style pull)

**Safety defaults:**
- Block if working tree is not clean (modified or untracked files) unless we explicitly decide otherwise.
- Block if upstream is not configured (or if remote is missing), with actionable guidance.

**Behavior:**
- Pulls updates into the currently checked-out branch.
- On failure, return a user-facing error string that points to next steps (e.g., “set upstream first”).

**Output:**
- Text summary of the pull operation.

## Edge Cases & Safety

- **No git repo:** adapter should raise a system-level error (“Invalid git repository”).
- **No `origin` remote:** `git_fetch`/`git_pull` should fail fast with a clear message.
- **Detached HEAD:** `pull` likely should refuse (no meaningful branch target).
- **Dirty working tree:**
  - `fetch`: allowed.
  - `pull`: default block (reduces risk of conflicts and state drift).
- **Merge conflicts / non-fast-forward:** report as a failure with a clear hint that manual resolution may be required.
- **Timeouts / transient network errors:** return actionable failure text; do not attempt retries silently.

## Test Plan

- Unit tests for `GitAdapter`:
  - `fetch` errors when no origin remote exists (mock Repo remote lookup).
  - `pull` errors when upstream missing / detached head.
- Unit tests for `GitManager` policy:
  - `pull` blocks on dirty working tree.
  - `fetch` does not block on dirty working tree.
- Tool-level tests (`mcp_server/tools/...`):
  - Tool schema validation for inputs.
  - Tool returns `ToolResult.error(...)` on expected failures.

## Open Questions

- Should `git_pull` require upstream only (no explicit `remote`), or allow explicit remote + branch?
- Should the default pull strategy be merge or rebase?
- Do we want a `git_fetch` that also performs `--prune` by default, or keep prune opt-in?

---

## Related Documentation

- **[README.md](../../../README.md)** - Project overview

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | YYYY-MM-DD |  | Initial creation |
| 0.2 | 2026-01-07 |  | Replace broken headings; draft inventory + gaps + contracts |