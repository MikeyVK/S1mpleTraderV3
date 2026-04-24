# Issue 94 - Planning: git_fetch + git_pull tools

**Status:** DRAFT
**Author:** ST3 Agent (Copilot)
**Created:** 2026-01-07
**Last Updated:** 2026-01-07
**Issue:** #94

---

## Objective

Implement missing remote sync primitives as MCP tools:
- `git_fetch`
- `git_pull`

…and ensure they are registered in the MCP server so they are discoverable via `list_tools` and callable by agents (tool-first enforcement).

This planning intentionally avoids detailed design (that follows in the next phase).

---

## Deliverables

- New adapter methods in `mcp_server/adapters/git_adapter.py`: `fetch()` and `pull()`.
- New manager methods in `mcp_server/managers/git_manager.py`: `fetch()` and `pull()` with policy preflight.
- New tools (module placement TBD by design, but likely `mcp_server/tools/git_tools.py`): `GitFetchTool`, `GitPullTool`.
- Tools registered in `mcp_server/server.py` tool list.
- Unit tests for adapter/manager/tools.
- (Optional) Update `agent.md` tool matrix to include `fetch/pull` so CLI usage is no longer “required”.

---

## Scope (In/Out)

**In Scope:**
- Minimal, safe-by-default `fetch`/`pull` behaviors.
- Clear user-facing error messages with actionable next steps.
- No network assumptions beyond a configured remote.

**Out of Scope:**
- Interactive conflict resolution.
- Advanced remote management (`remote add/set-url/remove`).
- Auto-stash / auto-merge behaviors (unless explicitly added later).

---

## Work Breakdown

1) **Adapter capabilities** (GitPython)
- Add `GitAdapter.fetch(remote="origin", prune=False)`.
- Add `GitAdapter.pull(remote="origin", rebase=False)`.

2) **Manager policy + preflight**
- Add `GitManager.fetch(...)` (thin wrapper; fetch allowed even when dirty).
- Add `GitManager.pull(...)` with safety defaults:
  - Block if working tree dirty (modified OR untracked).
  - Block if detached HEAD.
  - Block if remote missing / upstream missing (depending on contract).
- **Operational safety constraint (Issue #85):** any blocking git + state work must be offloaded from the event loop (use `anyio.to_thread.run_sync`, not inline I/O in async context).

3) **Tool layer**
- Expose `git_fetch` and `git_pull` as MCP tools.
- For `git_pull`: after a successful pull, re-sync state by calling `PhaseStateEngine.get_state(current_branch)` (same motivation as checkout sync).

4) **Server registration**
- Add imports + instances in `mcp_server/server.py` so tools are discoverable.

---

## TDD Cycles (Fetch / Pull)

We will run **two independent TDD loops**, one per tool:

### Cycle 1: `git_fetch`

**RED**
- Add failing unit tests:
  - Tool returns a *structured* error when remote is missing (avoid uncaught exceptions that can cause tool disablement in VS Code sessions; see Issue #77).
  - Adapter/manager call correct GitPython remote fetch.
  - Tool offloads blocking work via `anyio.to_thread.run_sync` (regression guard for Issue #85-style hangs).

**GREEN**
- Implement `GitAdapter.fetch`.
- Implement `GitManager.fetch`.
- Implement `GitFetchTool`.

**REFACTOR**
- Run quality gates on touched files.
- Normalize error handling (consistent exceptions → `ToolResult.error`).

### Cycle 2: `git_pull`

**RED**
- Add failing unit tests:
  - `pull` blocks on dirty working tree.
  - `pull` blocks on detached HEAD.
  - `pull` returns actionable (structured) error when no remote/upstream (avoid uncaught exceptions; see Issue #77).
  - Tool performs PhaseStateEngine re-sync after successful pull.
  - Tool offloads blocking work via `anyio.to_thread.run_sync` (regression guard for Issue #85-style hangs).

**GREEN**
- Implement `GitAdapter.pull`.
- Implement `GitManager.pull` with preflight.
- Implement `GitPullTool` + state sync.

**REFACTOR**
- Run quality gates on touched files.
- Ensure messages are consistent and non-leaky (no raw stack traces).

---

## Test Plan

Primary intent: keep tests deterministic and fast.

- **Adapter unit tests**: mock GitPython `Repo` and `Remote` objects to validate calls.
- **Manager unit tests**: mock adapter + status to validate preflight decisions.
- **Tool unit tests**: mock manager + PhaseStateEngine sync call for `git_pull`.

Test placement guideline:
- `tests/unit/mcp_server/adapters/test_git_adapter_*.py`
- `tests/unit/mcp_server/managers/test_git_manager_*.py`
- `tests/unit/mcp_server/tools/test_git_fetch_pull_tools.py`

---

## Integration Decision

**Default decision:** integration tests are *not required* for the first implementation, provided unit tests cover:
- remote-missing handling
- clean/dirty preflight behavior
- state-sync side effect

**Optional follow-up (if confidence is low):** a local-only integration test using two temporary repos:
- create a bare repo as `origin`
- clone into a temp workdir
- create a new commit in origin and verify fetch/pull behavior

This stays offline and deterministic but is more verbose and may be deferred.

---

## Tool Exposure Checklist

We must ensure tools are available inside the server:
- Implement tool classes (`name` must be unique and stable: `git_fetch`, `git_pull`).
- Add them to `mcp_server/server.py` imports.
- Add instances into `MCPServer.tools` list.
- Verify `list_tools` includes them (later in integration phase).

---

## Risks / Mitigations

- **Risk:** Pull semantics differ based on upstream configuration.
  - **Mitigation:** start with strict contract and clear errors; allow extension later.
- **Risk:** Network operations can hang or block stdio tool responses (Issue #85).
  - **Mitigation:** run `fetch/pull` in a worker thread (`anyio.to_thread.run_sync`), and force non-interactive git behavior (disable pager + prompts via env like `GIT_TERMINAL_PROMPT=0`, `GIT_PAGER=cat` / `PAGER=cat`).
- **Risk:** An exception bubbles out of the tool call and VS Code disables tools for the session (Issue #77).
  - **Mitigation:** tools should catch and return structured errors (no raw stack traces; log internally).
- **Risk:** State drift if pull changes commits but state is stale.
  - **Mitigation:** tool-level state re-sync after pull.

---

## Acceptance Criteria

- [ ] `git_fetch` tool exists, is registered, and returns a clear success/failure message.
- [ ] `git_pull` tool exists, is registered, blocks on dirty tree by default, and re-syncs PhaseStateEngine state after success.
- [ ] Unit test suite covers both tools and their preflight rules.
- [ ] Quality gates pass for the changed files.
