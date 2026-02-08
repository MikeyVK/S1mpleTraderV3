<!-- docs/reference/mcp/tools/git.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-02-08 -->
# Git Workflow & Analysis Tools

**Status:** DEFINITIVE  
**Version:** 2.0  
**Last Updated:** 2026-02-08  

**Source:** [mcp_server/tools/git_tools.py](../../../../mcp_server/tools/git_tools.py), [git_fetch_tool.py](../../../../mcp_server/tools/git_fetch_tool.py), [git_pull_tool.py](../../../../mcp_server/tools/git_pull_tool.py), [git_analysis_tools.py](../../../../mcp_server/tools/git_analysis_tools.py)  
**Tests:** [tests/unit/test_git_tools.py](../../../../tests/unit/test_git_tools.py)  

---

## Purpose

Complete reference documentation for all 14 Git automation tools covering branch management, commit workflow, merge operations, stash management, repository synchronization, and analysis. These tools provide full Git workflow automation with phase state synchronization, thread-safe operations, and TDD cycle integration.

---

## Overview

The MCP server provides **14 Git tools** across 4 functional categories:

| Category | Tools | Key Features |
|----------|-------|-------------|
| **Git Workflow** | 10 | Branch CRUD, commits with TDD phases, checkout with phase sync, merge, stash, restore, parent detection |
| **Git Sync** | 2 | Thread-safe fetch/pull with lock files |
| **Git Analysis** | 2 | Branch listing with verbose info, diff statistics |
| **TOTAL** | 14 | — |

All tools:
- ✅ Execute in workspace root (detected from environment)
- ✅ Return structured responses with `success` boolean
- ✅ Validate inputs before git operations
- ✅ Integrate with PhaseStateEngine for branch state tracking

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
| `branch_type` | `str` | No | Branch type: `"feature"`, `"bug"`, `"docs"`, `"refactor"`, `"hotfix"` (default: `"feature"`) |

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

- **Naming Convention:** Validates against [.st3/git.yaml](../../../../.st3/git.yaml) patterns
- **Protected Branches:** Validates `base_branch` against protected branch list
- **Branch Exists:** Returns error if branch already exists
- **Base Branch Validation:** Returns error if base branch doesn't exist

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

Stage and commit changes with TDD phase prefix (red/green/refactor/docs).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `phase` | `str` | **Yes** | TDD phase: `"red"` (test), `"green"` (feat), `"refactor"`, `"docs"` |
| `message` | `str` | **Yes** | Commit message (WITHOUT prefix — prefix is auto-added) |
| `files` | `list[str]` | No | Optional list of file paths to stage — default: commit all changes |

#### Returns

```json
{
  "success": true,
  "message": "Changes committed",
  "commit": {
    "sha": "abc123def456",
    "message": "test: Add failing test for user authentication"
  }
}
```

#### Example Usage

**Commit all changes:**
```json
{
  "phase": "red",
  "message": "Add failing test for user authentication"
}
```

**Commit specific files:**
```json
{
  "phase": "green",
  "message": "Implement user authentication logic",
  "files": ["backend/services/auth_service.py", "backend/dtos/user.py"]
}
```

#### TDD Phase Prefixes

| Phase | Prefix | Description |
|-------|--------|-------------|
| `red` | `test:` | Add failing test |
| `green` | `feat:` | Implement feature to pass test |
| `refactor` | `refactor:` | Refactor without changing behavior |
| `docs` | `docs:` | Documentation updates |

**Example Commit Messages:**
- `phase="red"`, `message="Add user login test"` → `test: Add user login test`
- `phase="green"`, `message="Implement user login"` → `feat: Implement user login`

#### Behavior Notes

- **Auto-Stage:** If `files` specified, stages those files; otherwise stages all changes
- **No Changes:** Returns error if no changes to commit
- **Phase Validation:** Validates `phase` against [.st3/git.yaml](../../../../.st3/git.yaml) definitions
- **Message Format:** Follows conventional commits (phase prefix + message)

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

- **Phase Sync:** Loads phase state from `.st3/state.json` after checkout
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

Delete a local branch (protected branch safety).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `branch` | `str` | **Yes** | Branch name to delete |
| `force` | `bool` | No | Force delete unmerged branch (default: `False`) |

#### Returns

```json
{
  "success": true,
  "message": "Branch 'feature/123-oauth' deleted"
}
```

#### Example Usage

**Delete merged branch:**
```json
{
  "branch": "feature/123-oauth"
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

- **Protected Branches:** Returns error if attempting to delete protected branches (`main`, `develop`, etc. from [.st3/git.yaml](../../../../.st3/git.yaml))
- **Unmerged Changes:** Default `force=false` returns error if branch has unmerged commits
- **Current Branch:** Returns error if attempting to delete current branch
- **Remote Branch:** Does NOT delete remote branch (only local)

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

- **State Source:** Reads `parent_branch` from `.st3/state.json` (set during `initialize_project`)
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

- **Thread-Safe:** Uses lock file (`.git/st3_fetch.lock`) to prevent concurrent fetch operations
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

- **Thread-Safe:** Uses same lock file as `git_fetch`
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
    {"name": "bugfix/122-login", "current": false}
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

## Configuration

### .st3/git.yaml

Git conventions and TDD phases:

```yaml
git:
  protected_branches:
    - main
    - develop
    - master
  
  branch_patterns:
    feature: "^feature/\\d+-[a-z0-9-]+$"
    bug: "^bugfix/\\d+-[a-z0-9-]+$"
    docs: "^docs/[a-z0-9-]+$"
  
  tdd_phases:
    red:
      prefix: "test"
      description: "Add failing test"
    green:
      prefix: "feat"
      description: "Implement feature"
    refactor:
      prefix: "refactor"
      description: "Refactor code"
    docs:
      prefix: "docs"
      description: "Update documentation"
```

---

## Thread Safety

### Fetch/Pull Lock Mechanism

Both `git_fetch` and `git_pull` use a file-based lock to prevent concurrent operations:

- **Lock File:** `.git/st3_fetch.lock`
- **Timeout:** 30 seconds
- **Behavior:** If lock file exists, waits up to 30s for release; returns error if timeout exceeded
- **Cleanup:** Lock file automatically removed after operation completes

**See Also:** [docs/reference/mcp/git_fetch_pull.md](../git_fetch_pull.md) for detailed threading architecture.

---

## Related Documentation

- [README.md](README.md) — MCP Tools navigation index
- [project.md](project.md) — Phase management and TDD workflow
- [.st3/git.yaml](../../../../.st3/git.yaml) — Git conventions configuration
- [docs/reference/mcp/git_fetch_pull.md](../git_fetch_pull.md) — Thread-safe fetch/pull implementation
- [docs/development/issue19/research.md](../../../development/issue19/research.md) — Tool inventory research (Section 1.1-1.3: Git tools)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-02-08 | Agent | Complete reference for 14 Git tools: workflow (10), sync (2), analysis (2) |
