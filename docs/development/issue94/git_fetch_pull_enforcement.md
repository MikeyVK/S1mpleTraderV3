# Git Fetch/Pull as Enforcement Primitives

**Status:** DRAFT
**Author:** ST3 Agent (Copilot)
**Created:** 2026-01-07
**Last Updated:** 2026-01-07
**Issue:** #94 (knowledge targets Epic #18)

---

## 1. Overview

### 1.1 Purpose

Describe how `git fetch` and `git pull` should exist as MCP tools and how they can be used as *enforcement primitives* (Issue #18) to prevent “remote drift” and reduce workflow/state inconsistencies caused by falling back to CLI.

This document focuses on:
- Where remote sync belongs in the **enforcement** architecture (policy), not just “adding a tool”.
- Whether we should add a new phase (fasing uitbreiden) or enforce at existing **choke points**.

### 1.2 Scope

**In Scope:**
- Analyze current workflow phases and tool choke points.
- Propose minimal tool contracts for `git_fetch` and `git_pull`.
- Propose a policy-driven “sync gate” that can be invoked by choke points.

**Out of Scope:**
- Interactive conflict resolution UX.
- Full remote management surface (`remote add/set-url/remove`) unless required.
- Replacing PhaseStateEngine’s core behavior.

### 1.3 Related Documents

- [Agent protocol (tool-first)](../../../agent_prompt.md)
- [MCP server architecture](../../mcp_server/ARCHITECTURE.md)
- [SafeEditTool enforcement model (policy + choke points)](../mcp_server/SAFE_EDIT_TOOL_FLOW_ENFORCEMENT.md)

---

## 2. Background

### 2.1 Context: Issue #18 and Issue #42

- **Issue #18** defines enforcement as policy: “WHEN and WHERE tools must be used”, not tool implementation.
- **Issue #42** corrected phase semantics to align with real TDD by removing the “component → tdd” anti-pattern; current feature workflow is:
  - `research → planning → design → tdd → integration → documentation`

This makes it especially important that *enforcement* lives in choke points and phase transitions, rather than inventing more phases for “do X now”.

### 2.2 Current State (observed)

**Workflow definitions**
- Defined in `.st3/workflows.yaml` and validated by `mcp_server/config/workflows.py`.

**PhaseStateEngine behavior**
- `PhaseStateEngine.get_state(branch)` is the recovery mechanism: if `.st3/state.json` is missing/stale, it reconstructs state from projects + git commits.
- This recovery only happens when a tool calls `get_state()`.

**Git tool surface**
- Local ops + `push` exist (checkout, merge, stash, commit, etc.).
- `git_list_branches` and `git_diff_stat` exist in `mcp_server/tools/git_analysis_tools.py`.
- **Remote sync (`fetch`, `pull`) does not exist as MCP tooling**, so developers frequently fall back to CLI.

### 2.3 Problem Statement

We want enforcement tooling that is:
- **Tool-first** (agent_prompt.md): developers should not need CLI for routine operations.
- **Deterministic**: choke points decide what gates must pass.
- **Safe-by-default**: avoid destructive operations and avoid “silent merges”.

Without `fetch/pull` as tools:
- “Remote state” is not reliably visible to the enforcement system.
- Branches may drift from parent/main unnoticed until PR/merge, where it’s most expensive.
- Using CLI bypasses MCP-specific behaviors (e.g., state sync patterns), creating *state drift* risk.

### 2.4 Requirements

#### Functional Requirements
- [ ] Provide MCP tools `git_fetch` and `git_pull` (minimal contracts).
- [ ] Provide a reusable “sync gate” policy that choke points can call.
- [ ] Ensure `git_pull` (and possibly `git_fetch`) re-syncs phase state (calls `PhaseStateEngine.get_state()` for current branch) to reduce state drift.

#### Non-Functional Requirements
- [ ] **Safety:** `pull` should block on dirty working tree by default; `fetch` should not.
- [ ] **Performance:** do not force network calls on high-frequency tools unless policy requires it.
- [ ] **Testability:** sync policy must be unit-testable (mock git adapter/manager).

---

## 3. Design

### 3.1 Architecture Position

This fits as an **enforcement gate** callable by multiple tools:

```
Client
  |
  v
[Tool Entry Points / Choke Points]
  - git_add_or_commit
  - transition_phase
  - create_pr
  - merge_pr
  - close_issue
  |
  v
[Policy Decision]
  - determines required gates
  |
  v
[Gates]
  - tests / quality gates / artifacts
  - sync gate (fetch + divergence checks)
```

Key point: `git_fetch`/`git_pull` are *capabilities*. Enforcement decides when they’re required.

### 3.2 The Core Design Choice: new phase vs choke point

#### Option 1: Add a new “sync” phase
**Pros:**
- Very explicit: “in this phase you sync”.

**Cons:**
- Phase model becomes activity-mandatory rather than policy-driven.
- Forces extra transitions and complicates workflows.yaml.
- Still needs enforcement (otherwise it’s just semantics).

#### Option 2: Add / extend choke points with a sync gate (recommended)
**Pros:**
- Matches the established enforcement model (SafeEdit doc): enforcement at commit/PR/close/transition.
- Policy-driven per phase; can be strict only when it matters (e.g., entering integration).
- Avoids bloating the phase model (Issue #42 intent).

**Cons:**
- Requires a policy engine / gate plumbing (but that is already the direction of Issue #18).

**Decision:** Prefer **Option 2**. Only consider a new phase if we later discover we need “sync” as a persistent, restrictive activity window (unlikely).

### 3.3 Proposed Policy Model: Sync Gate

Define a gate (conceptual) `git_sync_gate(context)`:

- **Inputs:**
  - current branch
  - parent branch (from PhaseStateEngine state)
  - workflow + current_phase
  - operation (commit/transition/pr/close)

- **Steps:**
  1) **Fetch** remote state (at least `origin`) if policy says remote freshness is required.
  2) Compute **divergence** between:
     - current branch vs parent branch
     - (optionally) current branch vs `origin/<parent>` or `origin/<base>`
  3) Block or allow based on policy.

Divergence categories:
- **Up-to-date:** branch contains parent head (OK)
- **Behind:** parent has commits you don’t have (likely block for integration/PR)
- **Ahead:** branch has commits parent doesn’t (normal for feature branches)
- **Diverged:** both sides have unique commits (block; requires merge/rebase decision)

### 3.4 Proposed Tools

#### `git_fetch`
Minimal capability:
- Parameters: `remote="origin"`, `prune=false`
- Behavior:
  - Does not require clean tree.
  - Updates remote-tracking refs.
  - Returns a summary (remote + basic result).

#### `git_pull`
Minimal capability:
- Parameters: `remote="origin"`, `rebase=false`
- Safety defaults:
  - **Block if dirty** (modified/untracked) unless a future explicit override exists.
  - **Block if detached HEAD**.
  - **Block if no upstream** (or no remote configured), with actionable hint.
- Post-condition:
  - Call `PhaseStateEngine.get_state(current_branch)` to ensure `.st3/state.json` exists and is aligned with current branch after new commits land.

Note: `git_pull` is inherently higher-risk than `fetch` because it changes the working branch.

### 3.5 Integration Points (Choke Points)

Recommended enforcement touchpoints:

1) **`transition_phase`**
- Add sync gate when transitioning into `integration` (and optionally into `documentation`).
- Rationale: integration is where “surprises” (missing upstream fixes) are most expensive.

2) **`create_pr` / `merge_pr`**
- Require sync gate against PR base (usually `main`) with remote freshness.
- Rationale: PR is the canonical “merge boundary”.

3) **`close_issue`**
- Optionally require “no divergence from parent” before closure (policy-driven).
- Rationale: ensures the work is actually integrated or intentionally deferred.

4) **`git_add_or_commit`**
- Avoid remote fetch here by default (performance). Only enforce local invariants (tests/quality) unless policy explicitly enables remote checks.

### 3.6 Failure Modes & UX

All failures should be actionable and tool-first:
- “No origin remote configured” → instruct to add remote (or fail with hint).
- “Branch is behind parent/main by N commits” → suggest running `git_pull` (if safe) or merging/rebasing.
- “Branch diverged” → suggest merge/rebase decision; do not auto-resolve.

---

## 4. Implementation Plan (high-level)

1) Implement `GitAdapter.fetch()` and `GitAdapter.pull()`.
2) Implement `GitManager.fetch()/pull()` with policy preflight:
   - pull blocks on dirty tree.
3) Expose tools `git_fetch` and `git_pull`.
4) Add a sync gate module (policy layer) and wire it into `transition_phase` and `create_pr` first (highest ROI).
5) Update agent_prompt.md tool matrix to include fetch/pull (removes incentive to CLI).

---

## 5. Alternatives Considered

- “Just add git pull tool” (without policy integration): helps, but does not achieve enforcement.
- “Make sync its own phase”: explicit but bloats the workflow model and still needs enforcement.

---

## 6. Open Questions

- Should policy compare against **parent branch** from PhaseStateEngine or always against `main`?
- Should `git_pull` default to merge or rebase?
- Should `transition_phase` auto-run `git_fetch` when policy requires remote freshness, or should it hard-require the user to run `git_fetch` explicitly first?

---

## 7. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-07 | Prefer choke point sync gate over new phase | Aligns with Issue #18 enforcement model and Issue #42 phase semantics |

---

## 8. References

- [Agent protocol](../../../agent_prompt.md)
- [Issue #18](https://github.com/) (see repository issue tracker)
- [Issue #42](https://github.com/) (see repository issue tracker)
