<!-- docs/reference/mcp/tools/git.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-02-08 -->
# Git Workflow & Analysis Tools

**Status:** DEFINITIVE  
**Version:** 3.0  
**Last Updated:** 2026-06-15  

**Source:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py), [git_fetch_tool.py](../../../../mcp_server/tools/git_fetch_tool.py), [git_pull_tool.py](../../../../mcp_server/tools/git_pull_tool.py), [git_analysis_tools.py](../../../../mcp_server/tools/git_analysis_tools.py)  
**Tests:** [tests/unit/test_git_tools.py](../../../../tests/unit/test_git_tools.py)  

---

## Purpose

Complete reference documentation for all 15 Git automation tools provided by the Phase-Gate MCP Server.

---

## Overview

The MCP server provides **15 Git tools** across 4 functional categories:

| Category | Tools | Key Features |
|----------|-------|-------------|
| **Git Workflow** | 11 | Branch CRUD, commits with TDD phases, checkout, merge, stash, restore, push, delete, parent detection, reachability gate |
| **Git Sync** | 2 | Thread-safe fetch/pull with lock files |
| **Git Analysis** | 2 | Branch listing with verbose info, diff statistics |
| **TOTAL** | **15** | — |
- ✅ Execute in workspace root (detected from environment)
- ✅ Return structured responses via the MCP Resource Cache (using Pydantic DTOs)
- ✅ Validate inputs before git operations
- ✅ Integrate with PhaseStateEngine for branch state tracking

> [!NOTE]
> **Unified DTO & MCP Resource Caching:** Every Git tool returns a single `TextContent` block containing a human-readable summary and the resource cache link (`pgmcp://cache/runs/{run_id}`). The raw JSON objects documented in the `#### Returns` sections below are stored as DTOs in the MCP Resource Cache and can be retrieved by client/caller using the cached resource URI.

---

## Git Workflow Tools (10 tools)

### create_branch

**MCP Name:** `create_branch`  
**Class:** `CreateBranchTool`  
**File:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py)

Create a new branch from specified base branch.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | **Yes** | Branch name (kebab-case) — e.g., `"feature/123-my-feature"` |
| `base_branch` | `str` | **Yes** | Base branch to create from (e.g., `"HEAD"`, `"main"`, `"develop"`) |
| `branch_type` | `str` | No | Branch type (default: `"feature"`). Valid values are populated at runtime from `git.yaml` via the `branch_types` config; enum is injected via A4 schema override. |

#### Returns

```json
{
  "success": true,
  "message": "Branch 'feature/123-my-feature' created from 'main'",
  "branch": "feature/123-my-feature"
}
```

#### Example Usage

```json
{
  "name": "feature/123-oauth-integration",
  "base_branch": "main",
  "branch_type": "feature"
}
```

#### Behavior Notes

- **Naming Convention:** Validates against [.pgmcp/git.yaml](../../../../.pgmcp/git.yaml) patterns
- **Protected Branches:** Validates `base_branch` against protected branch list
- **Branch Exists:** Returns error if branch already exists
- **Base Branch Validation:** Returns error if base branch doesn't exist
- **No Auto-Checkout:** The branch is created but **not** automatically checked out. Call `git_checkout` after creation before making changes or committing.

---

### git_status

**MCP Name:** `git_status`  
**Class:** `GitStatusTool`  
**File:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py)

Check current git status (working directory and staging area).

#### Parameters

None.

#### Returns

```json
{
  "success": true,
  "branch": "feature/123-my-feature",
  "status": {
    "staged": ["backend/dtos/user.py", "tests/test_user.py"],
    "unstaged": ["backend/services/order_service.py"],
    "untracked": ["temp_notes.md"]
  },
  "clean": false
}
```

#### Example Usage

```json
{}
```

#### Behavior Notes

- **Current Branch:** Includes current branch name
- **Status Categories:** Staged, unstaged, untracked files
- **Clean Flag:** `true` if no changes, `false` otherwise
- **File Paths:** Relative to workspace root

---

### git_add_or_commit

**MCP Name:** `git_add_or_commit`  
**Class:** `GitCommitTool`  
**File:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py)

Stage and commit changes with auto-generated phase prefix. Integrates with PhaseStateEngine for automatic scope generation.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | `str` | **Yes** | Commit message (WITHOUT prefix — prefix is auto-added) |
| `workflow_phase` | `str` | No | Phase override (e.g. `"implementation"`, `"documentation"`) — auto-detected from `.pgmcp/state.json` if omitted. Valid values populated at runtime from `workphases.yaml`. |
| `sub_phase` | `str` | No | Sub-phase for `implementation`: `"red"`, `"green"`, `"refactor"`. Valid values populated at runtime from `workphases.yaml`. |
| `cycle_number` | `int` | No | **Required when the active phase is cycle-based (e.g. implementation).** TDD cycle number (e.g. `1`, `2`, `3`). Optional otherwise. |
| `commit_type` | `str` | No | Override commit type (e.g. `"feat"`, `"fix"`, `"docs"`). Valid values populated at runtime from `git.yaml` via the `commit_types` config. Use only as explicit override. |
| `files` | `list[str]` | No | Specific file paths to stage — default: stage all changed files |
| `skip_paths` | `frozenset[str]` | No | File paths to exclude from staging (advanced use) |

#### Returns

```json
{
  "success": true,
  "message": "Changes committed",
  "commit": {
    "sha": "abc123def456",
    "message": "feat(P_IMPLEMENTATION_SP_C1_GREEN): Implement user authentication (#42)"
  }
}
```

#### Example Usage

**Implementation cycle — RED (write failing test):**
```json
{
  "workflow_phase": "implementation",
  "sub_phase": "red",
  "cycle_number": 1,
  "message": "Add failing test for user authentication"
}
```

**Implementation cycle — GREEN, specific files:**
```json
{
  "workflow_phase": "implementation",
  "sub_phase": "green",
  "cycle_number": 1,
  "message": "Implement user authentication logic",
  "files": ["backend/services/auth_service.py", "backend/dtos/user.py"]
}
```

**Documentation phase:**
```json
{
  "workflow_phase": "documentation",
  "message": "Update API reference docs"
}
```

#### Commit Scope Format

| Phase | Sub-phase | Scope | Prefix |
|-------|-----------|-------|--------|
| `implementation` | `red` | `P_IMPLEMENTATION_SP_C1_RED` | `test(...)` |
| `implementation` | `green` | `P_IMPLEMENTATION_SP_C1_GREEN` | `feat(...)` |
| `implementation` | `refactor` | `P_IMPLEMENTATION_SP_C1_REFACTOR` | `refactor(...)` |
| `documentation` | — | `P_DOCUMENTATION` | `docs(...)` |
| `research` | — | `P_RESEARCH` | `docs(...)` |

#### Behavior Notes

- **Auto-Stage:** If `files` specified, stages those files; otherwise stages all changes
- **No Changes:** Returns error if no changes to commit
- **Issue suffix auto-append (#228):** The active issue number is extracted from the current branch name via `extract_issue_number()` and appended to the commit message as ` (#NNN)`. For branches without a parseable issue number (e.g. `main`, `feature/no-number`), no suffix is added. This happens transparently — no parameter needed.
- **`phase` parameter:** Does NOT exist — `GitCommitInput` uses `extra="forbid"`. Passing `phase` crashes with a validation error.
- **`cycle_number`:** Required when the active phase is cycle-based (e.g. `implementation`) — omitting it causes an error
- **Ready-phase auto-exclude (#283):** When in `ready` phase, `.pgmcp/state.json` and `.pgmcp/deliverables.json` are automatically removed from the commit index before committing

---

### git_checkout

**MCP Name:** `git_checkout`  
**Class:** `GitCheckoutTool`  
**File:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py)

Switch to an existing branch (auto-syncs phase state).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `branch` | `str` | **Yes** | Branch name to checkout |

#### Returns

```json
{
  "success": true,
  "message": "Switched to branch 'feature/123-my-feature'",
  "branch": "feature/123-my-feature",
  "phase": "implementation"
}
```

#### Example Usage

```json
{
  "branch": "feature/123-oauth"
}
```

#### Behavior Notes

- **Phase Sync:** Loads phase state from `.pgmcp/state.json` after checkout
- **Dirty Working Directory:** Returns error if uncommitted changes exist (use `git_stash` first)
- **Branch Validation:** Returns error if branch doesn't exist
- **Protected Branches:** Can checkout protected branches (read-only warning)

---

### git_push

**MCP Name:** `git_push`  
**Class:** `GitPushTool`  
**File:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py)

Push current branch to origin remote.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `set_upstream` | `bool` | No | Set upstream tracking for new branches (default: `False`) |

#### Returns

```json
{
  "success": true,
  "message": "Branch 'feature/123-oauth' pushed to origin",
  "branch": "feature/123-oauth"
}
```

#### Example Usage

**Push existing branch:**
```json
{
  "set_upstream": false
}
```

**Push new branch (first time):**
```json
{
  "set_upstream": true
}
```

#### Behavior Notes

- **Upstream Tracking:** Use `set_upstream=true` for new branches to enable `git pull` later
- **No Remote:** Returns error if no `origin` remote configured
- **Protected Branches:** Push to protected branches may be blocked by remote (not enforced locally)
- **Force Push:** NOT supported (safety)

---

### git_merge

**MCP Name:** `git_merge`  
**Class:** `GitMergeTool`  
**File:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py)

Merge a branch into the current branch.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `branch` | `str` | **Yes** | Branch name to merge into current branch |

#### Returns

```json
{
  "success": true,
  "message": "Branch 'feature/123-oauth' merged into 'main'",
  "merge_commit": "abc123def456"
}
```

#### Example Usage

```json
{
  "branch": "feature/123-oauth"
}
```

#### Behavior Notes

- **Merge Strategy:** Uses default git merge (creates merge commit if not fast-forward)
- **Conflicts:** Returns error if merge conflicts occur (must resolve manually)
- **Fast-Forward:** Detects and uses fast-forward merge when possible
- **No Commit Yet:** Does NOT auto-commit; use `git_add_or_commit` after resolving any issues

---

### git_delete_branch

**MCP Name:** `git_delete_branch`  
**Class:** `GitDeleteBranchTool`  
**File:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py)

Delete a branch locally, remotely, or both (default). Protected-branch safety always applies.

> **⚠️ Breaking Change (issue #345):** The default deletion scope changed from local-only to
> `both` (local + remote). Callers that previously relied on the local-only behavior must now
> pass `mode="local"` explicitly.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `branch` | `str` | **Yes** | Branch name to delete |
| `force` | `bool` | No | Force delete unmerged branch (default: `False`) |
| `mode` | `str` | No | Deletion scope: `"local"`, `"remote"`, or `"both"` (default: `"both"`) |

#### Returns

```json
{
  "success": true,
  "message": "Deleted branch: feature/123-oauth (local: deleted, remote: deleted)"
}
```

#### Example Usage

**Delete branch from both local and remote (default):**
```json
{
  "branch": "feature/123-oauth"
}
```

**Delete local branch only:**
```json
{
  "branch": "feature/123-oauth",
  "mode": "local"
}
```

**Delete remote branch only:**
```json
{
  "branch": "feature/123-oauth",
  "mode": "remote"
}
```

**Force delete unmerged branch:**
```json
{
  "branch": "feature/123-oauth",
  "force": true
}
```

#### Behavior Notes

- **Protected Branches:** Returns error if attempting to delete protected branches (`main`, `develop`, etc. from [.pgmcp/git.yaml](../../../../.pgmcp/git.yaml))
- **Unmerged Changes:** Default `force=false` returns error if local branch has unmerged commits (applies to `mode="local"` and `mode="both"`)
- **Current Branch:** Returns error if attempting to delete the current local branch (applies to `mode="local"` and `mode="both"`; skipped for `mode="remote"`)
- **Remote Absent:** When `mode="remote"` or `mode="both"`, a branch that is not present on the remote is treated as `absent` (not an error)
- **Migration note:** If you used `git_delete_branch` for local-only cleanup, add `mode="local"` to preserve the old behavior

---

### git_stash

**MCP Name:** `git_stash`  
**Class:** `GitStashTool`  
**File:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py)

Save or restore work in progress (git stash).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | `str` | **Yes** | Stash action: `"push"` (save), `"pop"` (restore), `"list"` |
| `message` | `str` | **Conditional** | Optional stash name (only for `action="push"`) |
| `include_untracked` | `bool` | No | Include untracked files when stashing (default: `False`) |

#### Returns

**For `push`:**
```json
{
  "success": true,
  "message": "Changes stashed",
  "stash_id": "stash@{0}"
}
```

**For `pop`:**
```json
{
  "success": true,
  "message": "Stash applied and dropped"
}
```

**For `list`:**
```json
{
  "success": true,
  "stashes": [
    {"id": "stash@{0}", "message": "WIP: OAuth implementation"},
    {"id": "stash@{1}", "message": "WIP on feature/123-oauth"}
  ]
}
```

#### Example Usage

**Save work:**
```json
{
  "action": "push",
  "message": "WIP: OAuth implementation"
}
```

**Save with untracked files:**
```json
{
  "action": "push",
  "include_untracked": true
}
```

**Restore work:**
```json
{
  "action": "pop"
}
```

**List stashes:**
```json
{
  "action": "list"
}
```

#### Behavior Notes

- **Push:** Saves current changes and reverts working directory to clean state
- **Pop:** Applies most recent stash and removes it from stash list
- **Apply vs Pop:** Use `git stash apply` manually if you want to keep stash after applying
- **Conflicts:** `pop` returns error if applying stash causes conflicts

---

### git_restore

**MCP Name:** `git_restore`  
**Class:** `GitRestoreTool`  
**File:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py)

Restore files to a git ref (discard local changes).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `files` | `list[str]` | **Yes** | File paths to restore (≥1 file required) |
| `source` | `str` | No | Git ref to restore from (default: `"HEAD"`) |

#### Returns

```json
{
  "success": true,
  "message": "Files restored from HEAD",
  "files": ["backend/dtos/user.py", "tests/test_user.py"]
}
```

#### Example Usage

**Discard uncommitted changes:**
```json
{
  "files": ["backend/dtos/user.py", "tests/test_user.py"]
}
```

**Restore to specific commit:**
```json
{
  "files": ["backend/services/auth_service.py"],
  "source": "abc123def"
}
```

#### Behavior Notes

- **Destructive:** Permanently discards local changes (cannot undo)
- **Source Validation:** Validates `source` is a valid git ref
- **Missing Files:** Returns error if any file doesn't exist in source ref
- **Staged Changes:** Also discards staged changes

---

### get_parent_branch

**MCP Name:** `get_parent_branch`  
**Class:** `GetParentBranchTool`  
**File:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py)

Detect parent branch for a branch (via PhaseStateEngine state).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `branch` | `str` | No | Branch name to inspect (default: current branch) |

#### Returns

```json
{
  "success": true,
  "branch": "feature/123-oauth",
  "parent_branch": "main"
}
```

#### Example Usage

**Get parent of current branch:**
```json
{}
```

**Get parent of specific branch:**
```json
{
  "branch": "feature/123-oauth"
}
```

#### Behavior Notes

- **State Source:** Reads `parent_branch` from `.pgmcp/state.json` (set during `initialize_project`)
- **Fallback:** If no state found, attempts detection via git reflog
- **Returns Null:** If parent cannot be determined, returns `parent_branch: null`

---

## Git Sync Tools (2 tools)

### git_fetch

**MCP Name:** `git_fetch`  
**Class:** `GitFetchTool`  
**File:** [mcp_server/tools/git_fetch_tool.py](../../../../mcp_server/tools/git_fetch_tool.py)

Fetch updates from a remote (thread-safe).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `remote` | `str` | No | Remote name to fetch from (default: `"origin"`) |
| `prune` | `bool` | No | Prune deleted remote-tracking branches (default: `False`) |

#### Returns

```json
{
  "success": true,
  "message": "Fetched from origin",
  "remote": "origin"
}
```

#### Example Usage

**Fetch from origin:**
```json
{
  "remote": "origin"
}
```

**Fetch and prune:**
```json
{
  "remote": "origin",
  "prune": true
}
```

#### Behavior Notes

- **Thread-Safe:** Offloaded to a worker thread to prevent event loop / stdio deadlocks
- **No Working Directory Changes:** Only updates remote-tracking branches
- **Prune:** `prune=true` removes remote-tracking branches that no longer exist on remote
- **Timeout:** 30 second timeout on fetch operation

---

### git_pull

**MCP Name:** `git_pull`  
**Class:** `GitPullTool`  
**File:** [mcp_server/tools/git_pull_tool.py](../../../../mcp_server/tools/git_pull_tool.py)

Pull updates from a remote with optional rebase.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `remote` | `str` | No | Remote name to pull from (default: `"origin"`) |
| `rebase` | `bool` | No | Use `--rebase` instead of merge (default: `False`) |

#### Returns

```json
{
  "success": true,
  "message": "Pulled from origin",
  "remote": "origin",
  "updates": {
    "files_changed": 5,
    "insertions": 120,
    "deletions": 45
  }
}
```

#### Example Usage

**Pull with merge:**
```json
{
  "remote": "origin"
}
```

**Pull with rebase:**
```json
{
  "remote": "origin",
  "rebase": true
}
```

#### Behavior Notes

- **Thread-Safe:** Offloaded to a worker thread to prevent event loop / stdio deadlocks
- **Upstream Required:** Returns error if current branch has no upstream tracking
- **Conflicts:** Returns error if merge/rebase conflicts occur
- **Rebase vs Merge:** `rebase=true` maintains linear history; `rebase=false` creates merge commit

---

## Git Analysis Tools (2 tools)

### git_list_branches

**MCP Name:** `git_list_branches`  
**Class:** `GitListBranchesTool`  
**File:** [mcp_server/tools/git_analysis_tools.py](../../../../mcp_server/tools/git_analysis_tools.py)

List git branches with optional verbose info and remotes.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `verbose` | `bool` | No | Include upstream/hash info (`-vv` flag) (default: `False`) |
| `remote` | `bool` | No | Include remote branches (`-r` flag) (default: `False`) |

#### Returns

**Without verbose:**
```json
{
  "success": true,
  "branches": [
    {"name": "main", "current": false},
    {"name": "feature/123-oauth", "current": true},
    {"name": "bug/122-login", "current": false}
  ]
}
```

**With verbose:**
```json
{
  "success": true,
  "branches": [
    {
      "name": "main",
      "current": false,
      "hash": "abc123d",
      "upstream": "origin/main",
      "status": "[ahead 2, behind 1]"
    },
    {
      "name": "feature/123-oauth",
      "current": true,
      "hash": "def456a",
      "upstream": "origin/feature/123-oauth",
      "status": "[ahead 3]"
    }
  ]
}
```

#### Example Usage

**List local branches:**
```json
{
  "verbose": false,
  "remote": false
}
```

**List with verbose info:**
```json
{
  "verbose": true
}
```

**List remote branches:**
```json
{
  "remote": true
}
```

#### Behavior Notes

- **Current Branch:** Marked with `current: true`
- **Verbose:** Includes commit hash, upstream branch, ahead/behind status
- **Remote Branches:** Shows branches on remote (origin/main, origin/feature/..., etc.)

---

### git_diff_stat

**MCP Name:** `git_diff_stat`  
**Class:** `GitDiffTool`  
**File:** [mcp_server/tools/git_analysis_tools.py](../../../../mcp_server/tools/git_analysis_tools.py)

Get diff statistics between two branches.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target_branch` | `str` | **Yes** | Target branch to compare against (e.g., `"main"`) |
| `source_branch` | `str` | No | Source branch (default: `"HEAD"` = current branch) |

#### Returns

```json
{
  "success": true,
  "diff": {
    "source": "feature/123-oauth",
    "target": "main",
    "files_changed": 12,
    "insertions": 456,
    "deletions": 123,
    "files": [
      {"path": "backend/dtos/user.py", "additions": 45, "deletions": 10},
      {"path": "tests/test_user.py", "additions": 120, "deletions": 5}
    ]
  }
}
```

#### Example Usage

**Compare current branch to main:**
```json
{
  "target_branch": "main"
}
```

**Compare two specific branches:**
```json
{
  "source_branch": "feature/123-oauth",
  "target_branch": "develop"
}
```

#### Behavior Notes

- **File-Level Stats:** Includes per-file addition/deletion counts
- **Branch Validation:** Returns error if either branch doesn't exist
- **Empty Diff:** Returns `files_changed: 0` if branches are identical

---

### check_merge

**MCP Name:** `check_merge`  
**Class:** `CheckMergeTool`  
**File:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py)

Verify that a merge commit SHA is reachable from the current HEAD. Wraps `git merge-base --is-ancestor <sha> HEAD`. Use this as the reachability gate in end-issue cleanup before deleting a merged branch.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `merge_sha` | `str` | **Yes** | The merge commit SHA to verify (e.g., the SHA returned by `merge_pr`) |

#### Returns

On success (SHA is reachable):
```
SHA <sha> is reachable from HEAD (merge confirmed)
```

On failure (SHA not reachable — `is_error: true`):
```
SHA <sha> is NOT reachable from HEAD — merge may not have landed yet
```

On git error (status ≥2 — `is_error: true`):
```
ExecutionError surfaced via error_handling decorator
```

#### Example Usage

**Verify merge commit reachability after git_pull:**
```json
{
  "merge_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
}
```

#### Behavior Notes

- **Exit 0:** SHA is an ancestor of HEAD → returns success text result
- **Exit 1:** SHA is not an ancestor → returns `is_error: true` (expected non-error case — branch cleanup must not proceed)
- **Exit ≥2:** Git command failed → `ExecutionError` surfaced via `error_handling` decorator → `is_error: true` result
- **Read-only:** No state mutations; safe to call multiple times
- **Use case:** Call after `git_pull()` in end-issue cleanup (step 6 of `end-issue.prompt.md`) before calling `git_delete_branch`
- **Enforcement:** `enforcement_event = None` — this tool has no phase gate; callable in any phase

---

## Configuration

### .pgmcp/git.yaml

Git conventions loaded on server startup:

```yaml
# Branch types allowed by create_branch
branch_types:
  - feature
  - bug
  - refactor
  - docs
  - hotfix
  - chore
  - epic

# Branches that cannot be deleted
protected_branches:
  - main
  - master
  - develop

# Regex pattern for branch name suffix (kebab-case)
branch_name_pattern: "^[a-z0-9-]+$"

# Conventional Commit types (https://www.conventionalcommits.org/)
commit_types:
  - feat
  - fix
  - docs
  - style
  - refactor
  - test
  - chore
  - perf
  - ci
  - build
  - revert

# Default base branch for PR creation
default_base_branch: main

# Maximum length for issue titles
issue_title_max_length: 72
```

---

## Thread Safety

Both `git_fetch` and `git_pull` execute potentially blocking GitPython network operations via `anyio.to_thread.run_sync` to protect against event loop blocking / stdio deadlocks (preventing MCP hanging).

**See Also:** [docs/reference/mcp/git_fetch_pull.md](../git_fetch_pull.md) for detailed threading architecture.

---

## Related Documentation

- [README.md](README.md) — MCP Tools navigation index
- [project.md](project.md) — Phase management and TDD workflow
- [.pgmcp/git.yaml](../../../../.pgmcp/git.yaml) — Git conventions configuration
- [docs/reference/mcp/git_fetch_pull.md](../git_fetch_pull.md) — Thread-safe fetch/pull implementation
- [docs/development/issue19/research.md](../../../development/issue19/research.md) — Tool inventory research (Section 1.1-1.3: Git tools)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-02-08 | Agent | Complete reference for 14 Git tools: workflow (10), sync (2), analysis (2) |
