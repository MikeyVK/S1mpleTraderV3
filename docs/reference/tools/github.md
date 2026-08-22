<!-- docs/reference/mcp/tools/github.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-05-27 -->
# GitHub Integration Tools

**Status:** DEFINITIVE  
**Version:** 3.1  
**Last Updated:** 2026-08-22  

**Source:** [mcp_server/tools/issue_tools.py](../../../mcp_server/tools/issue_tools.py), [pr_tools.py](../../../mcp_server/tools/pr_tools.py), [label_tools.py](../../../mcp_server/tools/label_tools.py), [milestone_tools.py](../../../mcp_server/tools/milestone_tools.py)  
**Tests:** [issue tool tests](../../../tests/mcp_server/unit/tools/test_issue_tools.py), [PR tool tests](../../../tests/mcp_server/unit/tools/test_pr_tools.py), [label tool tests](../../../tests/mcp_server/unit/tools/test_label_tools.py), and [milestone tool tests](../../../tests/mcp_server/unit/tools/test_milestone_tools.py)  

---
## Purpose

Complete reference documentation for all 17 GitHub API integration tools covering issues, pull requests, labels, and milestones. These tools provide full GitHub workflow automation with Unicode safety, validation against repository state, and structured error handling.

All GitHub operations require a `GITHUB_TOKEN` to execute. The five issue tools remain
registered without a token so their schemas are discoverable; the twelve PR, label, and
milestone tools are active only when credentials are configured.

---

## Overview

The MCP server provides **17 GitHub tools** across 4 functional categories:

| Category | Tools | Key Features |
|----------|-------|-------------|
| **Issues** | 5 | Create, read, list, update, close with Unicode support |
| **Pull Requests** | 4 | Create, read single PR, list, merge with draft support and merge strategies |
| **Labels** | 5 | CRUD operations with LabelConfig validation |
| **Milestones** | 3 | List, create, close with state filtering |

All tools:
- ✅ Support Unicode content (emojis, non-ASCII characters)
- ✅ Validate inputs before API calls
- ✅ Return structured responses with detailed error messages
- ✅ Require `GITHUB_TOKEN` environment variable
- ✅ Detect repository from git remote or `GITHUB_REPO` env var

### Presentation and Cache Contract

GitHub tools return bounded Markdown projections and publish their complete frozen DTOs
at `pgmcp://cache/runs/{run_id}`. Detail and mutation tools present the fields needed to
confirm the requested action. `list_issues`, `list_prs`, `list_labels`, and
`list_milestones` render at most ten records, preserve adapter/DTO order, and report the
omitted count when more records exist. Flat label sequences use the same ten-item bound.

The cache remains authoritative for complete collections and intentionally omitted
metadata. The presenter does not sort, filter, or mutate GitHub results.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | **Yes** | None | GitHub personal access token (classic or fine-grained) |
| `GITHUB_REPO` | No | Auto-detected from git remote | Repository in `owner/repo` format |

**Token Permissions (minimum):**
- Issues: `repo` scope or fine-grained `issues:write`
- PRs: `repo` scope or fine-grained `pull_requests:write`
- Labels: `repo` scope or fine-grained `metadata:write`
- Milestones: `repo` scope or fine-grained `administration:write`

---

## Issue Management Tools

### create_issue

**MCP Name:** `create_issue`  
**Class:** `CreateIssueTool`  
**File:** [mcp_server/tools/issue_tools.py](../../../mcp_server/tools/issue_tools.py)

Create a new GitHub issue. Uses a structured input contract: `issue_type`, `priority`, and `scope` are required top-level fields with config-driven enum values (A4 schema override); free-form `labels` are assembled internally from those values.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_type` | `str` | **Yes** | Issue type enum — valid values injected at runtime from `LabelConfig` (e.g. `feature`, `bug`, `hotfix`, `refactor`, `docs`, `chore`, `epic`) |
| `title` | `str` | **Yes** | Issue title (Unicode-safe, maximum 72 characters) |
| `priority` | `str` | **Yes** | Priority enum — valid values injected at runtime from `LabelConfig` (e.g. `critical`, `high`, `medium`, `low`, `triage`) |
| `scope` | `str` | **Yes** | Scope enum — valid values injected at runtime from `ScopeConfig` (e.g. `architecture`, `mcp-server`, `platform`, `tooling`, `workflow`, `documentation`) |
| `body` | `str` | **Yes** | Pre-rendered markdown body. Generate using `scaffold_artifact(artifact_type='issue')` before calling this tool. |
| `is_epic` | `bool` | No | Mark issue as an epic (default: `false`) |
| `parent_issue` | `int` | No | Parent issue number (positive integer) for child issues |
| `milestone` | `str` | No | Milestone **title** (string, not number) |
| `assignees` | `list[str]` | No | List of GitHub usernames to assign |

| `steps_to_reproduce` | `str` | No | Numbered steps to reproduce the issue |
| `related_docs` | `list[str]` | No | List of related documentation paths or URLs |

#### Returns

The mutation confirmation presents issue number, title, realized state, URL, milestone
title, assignee summary, and up to ten labels. The complete `IssueOutput`, including body,
timestamps, and author, is stored in the resource cache.

#### Example Usage

```json
{
  "issue_type": "feature",
  "title": "Add structured issue creation",
  "priority": "medium",
  "scope": "mcp-server",
  "body": "## Problem\n\nThe create_issue tool lacks validation."
}
```
```json
{
  "issue_type": "bug",
  "title": "Login fails on Windows when username contains spaces",
  "priority": "high",
  "scope": "platform",
  "body": "## Problem\n\nLogin fails with 500 error.\n\n## Expected Behavior\n\nRedirect to dashboard.\n\n## Actual Behavior\n\n500 Internal Server Error.\n\n## Context\n\nWindows 11, Python 3.13.\n\n## Steps to Reproduce\n\n1. Enter username with space\n2. Click Login",
  "is_epic": false,
  "parent_issue": 91,
  "milestone": "v2.0",
  "assignees": ["alice"]
}
```
- **Milestone:** Pass the milestone **title** (string), not the milestone number
- **Label assembly:** Labels are derived from `issue_type`, `priority`, and `scope`
- **Assignee validation:** Usernames must be valid collaborators
- **Default state:** Issues always created in `open` state
- **Enum values:** `issue_type`, `priority`, and `scope` enums are injected at runtime from config (A4 pattern) — inspect the tool schema for current valid values
- **Body generation:** Use `scaffold_artifact(artifact_type='issue', name="<slug>", context={...})` to generate a pre-rendered markdown body before calling this tool. The slash prompt `/create-issue` automates this two-step flow.


---

### get_issue

**MCP Name:** `get_issue`  
**Class:** `GetIssueTool`  
**File:** [mcp_server/tools/issue_tools.py](../../../mcp_server/tools/issue_tools.py)

Retrieve detailed information about a specific issue.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_number` | `int` | **Yes** | Issue number to retrieve |

#### Returns (via MCP Resource Cache)

`get_issue` presents the number, title, state, milestone title, assignee summary, URL,
bounded labels, created/updated/closed timestamps, and body. The author remains
cache-only.

The DTO is stored in the MCP Resource cache at `pgmcp://cache/runs/{run_id}` and contains the following fields:
- `success`: `bool`
- `error_message`: `string | null`
- `post_tool_instruction`: `string | null`
- `number`: `int`
- `title`: `string`
- `state`: `string`
- `milestone_title`: `string`
- `assignees_summary`: `string`
- `html_url`: `string`
- `body`: `string`
- `labels`: `list[string]`
- `created_at`: `string`
- `updated_at`: `string`
- `closed_at`: `string | null`
- `author`: `string`

#### Example Usage

```json
{
  "issue_number": 123
}
```

#### Behavior Notes

- Returns normalized milestone and assignee summaries rather than nested GitHub objects
- `closed_at` is `null` for open issues
- Includes timestamps in ISO 8601 format

---

### list_issues

**MCP Name:** `list_issues`  
**Class:** `ListIssuesTool`  
**File:** [mcp_server/tools/issue_tools.py](../../../mcp_server/tools/issue_tools.py)

List repository issues with optional state and label filters.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `state` | `str` | No | Filter by state: `"open"`, `"closed"`, `"all"` (default: `None` = all) |
| `labels` | `list[str]` | No | Filter by labels (AND logic — all labels must match) |

#### Returns

The text response shows `issues_count` and up to ten one-line issue records containing
number, state, title, URL, bounded labels, assignee summary, and creation timestamp. For
example:

```text
Found 25 issues matching criteria.

Issues:
- #456 [open] feat: Compact actionable tool summaries — https://github.com/.../456 | labels: priority:high, type:feature | assignees: Unassigned | created: 2026-08-19T20:28:16+00:00
- … 15 more issues
```

The cached `ListIssuesOutput` contains `issues_count` and the complete
`issues: list[IssueSummaryDTO]` collection.

#### Example Usage

**List all open issues:**
```json
{
  "state": "open"
}
```

**List issues with specific labels:**
```json
{
  "state": "open",
  "labels": ["type:feature", "priority:high"]
}
```

#### Behavior Notes

- **Label Filter Logic:** ALL labels must be present (AND, not OR)
- **Default State:** If `state` is `null`, returns issues in all states
- **Presentation limit:** At most ten returned DTO records are rendered inline; this does not change the cached collection.
- **Order:** The presenter preserves the order supplied by the adapter; it does not add a sort policy.

---

### update_issue

**MCP Name:** `update_issue`  
**Class:** `UpdateIssueTool`  
**File:** [mcp_server/tools/issue_tools.py](../../../mcp_server/tools/issue_tools.py)

Update any combination of issue fields: title, body, state, labels, milestone, assignees.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_number` | `int` | **Yes** | Issue number to update |
| `title` | `str` | No | New title (Unicode-safe) |
| `body` | `str` | No | New body (supports Markdown and Unicode) |
| `state` | `str` | No | New state: `"open"` or `"closed"` |
| `labels` | `list[str]` | No | **Replace** labels with this list (not additive) |
| `milestone` | `int` | No | Milestone number to assign (`null` to remove) |
| `assignees` | `list[str]` | No | **Replace** assignees with this list (not additive) |

#### Returns

The mutation confirmation uses the same bounded `IssueOutput` projection as
`create_issue`: number, title, realized state, URL, milestone title, assignee summary,
and labels. Body, timestamps, and author remain available in the cached DTO.

#### Example Usage

**Update title and close issue:**
```json
{
  "issue_number": 123,
  "title": "[RESOLVED] Feature request: Add user authentication",
  "state": "closed"
}
```

**Replace labels:**
```json
{
  "issue_number": 123,
  "labels": ["type:feature", "phase:documentation"]
}
```

#### Behavior Notes

- **Partial Updates:** Only specified fields are updated
- **Label Replacement:** Labels are **replaced**, not merged (to add labels, use `add_labels` tool instead)
- **Assignees Replacement:** Assignees are **replaced**, not merged
- **State Change:** Closing via `state="closed"` does NOT add a closing comment (use `close_issue` for that)

---

### close_issue

**MCP Name:** `close_issue`  
**Class:** `CloseIssueTool`  
**File:** [mcp_server/tools/issue_tools.py](../../../mcp_server/tools/issue_tools.py)

Close an issue with an optional closing comment.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_number` | `int` | **Yes** | Issue number to close |
| `comment` | `str` | No | Optional closing comment (supports Markdown and Unicode) |

#### Returns

```json
{
  "success": true,
  "message": "Issue #123 closed",
  "issue": {
    "number": 123,
    "state": "closed",
    "closed_at": "2026-02-08T12:00:00Z"
  }
}
```

#### Example Usage

**Close without comment:**
```json
{
  "issue_number": 123
}
```

**Close with comment:**
```json
{
  "issue_number": 123,
  "comment": "Resolved in PR #45. All tests passing. ✅"
}
```

#### Behavior Notes

- **Comment Order:** Comment is posted BEFORE closing (appears as last comment)
- **Already Closed:** Closing an already-closed issue returns success (idempotent)
- **vs. update_issue:** Use `close_issue` when you want to add a closing comment; use `update_issue(state="closed")` for silent close

---

## Pull Request Tools

### submit_pr

**MCP Name:** `submit_pr`
**Class:** `SubmitPRTool`
**File:** [mcp_server/tools/pr_tools.py](../../../mcp_server/tools/pr_tools.py)

Create a pull request via an **atomic, self-contained flow** that handles branch-local
artifact neutralization, the final commit, push, GitHub PR creation, and PR-status
cache update in a single operation.

> **Design note (issue #283):** `CreatePRTool` has been deleted. `SubmitPRTool` is the
> sole public agent-facing tool for PR creation. It replaces the old multi-step pattern
> of `git_add_or_commit → create_pr` and owns the full ready-phase transition sequence.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | `str` | **Yes** | PR title (Unicode-safe) |
| `body` | `str` | No | PR description (supports Markdown and Unicode) |
| `head` | `str` | **Yes** | Source branch (e.g., `"feature/123-my-feature"`) |
| `base` | `str` | No | Target branch. Resolution chain when omitted: (1) detected parent branch from `.pgmcp/state.json`, (2) `git_config.default_base_branch` (typically `"main"`). Pass explicitly to override. |
| `draft` | `bool` | No | Create as draft PR (default: `False`) |


#### Base Branch Resolution

When `base` is omitted, `submit_pr` resolves the target branch in this order:

1. **Parent branch detection:** Look up the parent branch for the source branch from `.pgmcp/state.json` via `IBranchParentReader`.
2. **Fallback:** Use `git_config.default_base_branch` (typically `"main"`).

This allows epic child branches (e.g., `bug/357-...` branched from `epic/320-...`) to automatically target their epic parent rather than `main`. Pass `base` explicitly to override the entire chain.

#### Atomic Execution Flow

`submit_pr` executes the following steps in order, stopping on the first failure:

```
1. Preflight and prepare branch for submission
   └─ GitManager.prepare_submission(artifact_paths, base, note_context) → bool
      a. Preflight: assert clean working tree           (PreflightError if dirty)
      b. Preflight: assert upstream exists              (PreflightError if missing)
      c. Filter: identify branch-local artifacts with a net diff against base
      d. Conditional: neutralize and commit (only if diffs detected)
         └─ GitManager.neutralize_to_base(paths, base)
         └─ GitManager.commit_with_scope(workflow_phase="ready", ...)
          → on commit failure: hard_reset("HEAD") + a recovery note + raises
       e. Push the branch to origin (always)
          → on push failure: hard_reset("HEAD~1") if commit made + a recovery note + raises
      Returns True if a neutralization commit was made, False otherwise
2. Create the GitHub PR via API
   └─ GitHubManager.create_pr(...)
   → on failure + commit_made=True: rollback_push called automatically
      └─ GitManager.rollback_push(note_context) — hard_reset("HEAD~1") + force-push
       Produces a recovery note; branch left in pre-submit state
3. Write PRStatus.OPEN to the session cache
   └─ IPRStatusWriter.set_pr_status(branch, PRStatus.OPEN)
```

| Failure stage | Error type | Branch state after | Retry safe? |
|---------------|-----------|-------------------|-------------|
| Preflight (dirty tree / no upstream) | `PreflightError` | Unchanged | Yes |
| Commit or push (inside `prepare_submission`) | `ExecutionError` | Rolled back internally; recovery note produced | Yes |
| GitHub API (`create_pr`) | `ExecutionError` | Auto-rolled back via `rollback_push`; recovery note produced | Yes |


#### Branch-Local Artifacts

The following files are neutralized to the merge-base before the PR commit so they
never reach `main`:

| Artifact | Path | Reason |
|----------|------|--------|
| Workflow state | `.pgmcp/state.json` | Branch-local TDD phase tracking |
| Deliverables | `.pgmcp/deliverables.json` | Branch-local planning deliverables |

Configured in `.pgmcp/config/contracts.yaml` → `branch_local_artifacts`.

#### Enforcement Guards

`submit_pr` is subject to enforcement checks and internal preflights:

**Enforcement runner** (`.pgmcp/config/enforcement.yaml`, runs before execution):
1. **`check_phase_readiness`** — blocks unless `state.json` shows `current_phase == "ready"`.
   Produces a `suggestion` note with `transition_phase(to_phase="ready")`.
2. **`check_pr_status`** (via dynamic `branch_mutating` category configuration) — blocks if the branch already has
   `PRStatus.OPEN` in cache. Produces a `suggestion` note to call `merge_pr` first.

**Internal preflights** (inside `GitManager.prepare_submission`, run before any mutation):
3. **Dirty-tree check** — blocks with `PreflightError` if working tree is not clean.
4. **Upstream check** — blocks with `PreflightError` if branch has no upstream configured.

#### Returns

The success response confirms PR number, title, state, URL, target branch, and source
branch. The cached `PROutput` additionally retains body and merge fields.

Error result on failure:
```
<error details from PreflightError or ExecutionError>
(A recovery note in context describes rollback status and retry instructions.)
```

#### Example Usage

```json
{
  "title": "feat: Add OAuth2 authentication",
  "body": "## Changes\n\n- Google OAuth2\n- GitHub OAuth2\n- Token refresh\n\nCloses #123",
  "head": "feature/123-oauth",
  "base": "main"
}
```

**Draft PR:**
```json
{
  "title": "WIP: OAuth2 authentication",
  "body": "Early draft for feedback.",
  "head": "feature/123-oauth",
  "draft": true
}
```

#### Behavior Notes

- **Phase Required:** Must be in `ready` phase. Call `transition_phase(to_phase="ready")` first.
- **Open PR Guard:** Blocked if an open PR already exists for this branch.
- **Artifact Neutralization:** Skipped if no branch-local artifacts have a net diff (clean branch).
- **Draft PRs:** Cannot be merged until marked ready for review on GitHub.
- **Auto-link Issues:** Use `Closes #123` in body to auto-link issues.
- **`MergePRTool` excluded from `branch_mutating` category list:** Intentional — it is the escape hatch
  that clears `PRStatus.OPEN`. Including it would cause a deadlock.

---

### list_prs

**MCP Name:** `list_prs`  
**Class:** `ListPRsTool`  
**File:** [mcp_server/tools/pr_tools.py](../../../mcp_server/tools/pr_tools.py)

List repository pull requests with optional state, base, and head filters.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `state` | `str` | No | Filter by state: `"open"`, `"closed"`, `"all"` (default: `"open"`) |
| `base` | `str` | No | Filter by base branch (e.g., `"main"`) |
| `head` | `str` | No | Filter by head branch (e.g., `"feature/123-my-feature"`) |

#### Returns

The text response shows `prs_count` and up to ten pull requests with number, state,
title, URL, head branch, and base branch. The cached `ListPRsOutput` retains the complete
`pull_requests: list[PRSummaryDTO]` collection.

#### Example Usage

**List all open PRs:**
```json
{
  "state": "open"
}
```

**List PRs targeting main:**
```json
{
  "base": "main"
}
```

**Check if feature branch has open PR:**
```json
{
  "head": "feature/123-oauth",
  "state": "open"
}
```

#### Behavior Notes

- **Default State:** `"open"` (unlike `list_issues` which defaults to all states)
- **Presentation limit:** At most ten returned DTO records are rendered inline.
- **Order:** The presenter preserves adapter/DTO order.

---

### merge_pr

**MCP Name:** `merge_pr`  
**Class:** `MergePRTool`  
**File:** [mcp_server/tools/pr_tools.py](../../../mcp_server/tools/pr_tools.py)

Merge a pull request with specified merge strategy.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pr_number` | `int` | **Yes** | Pull request number to merge |
| `merge_method` | `str` | No | Merge strategy: only `"merge"` is supported (default: `"merge"`). `"squash"` and `"rebase"` are not supported and will return a validation error. |
| `commit_message` | `str` | No | Optional custom commit message |

#### Returns

The success response confirms `pr_number`, `merge_method`, and `merge_sha`; the same
structured fields are stored in `MergePROutput`.

#### Example Usage

**Merge PR (default strategy):**
```json
{
  "pr_number": 45
}
```

**Merge with custom commit message:**
```json
{
  "pr_number": 45,
  "commit_message": "Feature: Add OAuth2 authentication (#45)\n\nCloses #123"
}
```

#### Behavior Notes

- **Draft PRs:** Cannot merge draft PRs (returns error)
- **Merge Conflicts:** Returns error if conflicts exist (must resolve first)
- **Branch Protection:** Respects branch protection rules (required reviews, status checks)
- **Auto-Delete:** Does NOT automatically delete head branch (GitHub repo setting controls this)

---

### get_pr

**MCP Name:** `get_pr`  
**Class:** `GetPRTool`  
**File:** [mcp_server/tools/pr_tools.py](../../../mcp_server/tools/pr_tools.py)

Retrieve detailed information about a specific pull request.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pr_number` | `int` | **Yes** | Pull request number to retrieve |

#### Returns (via MCP Resource Cache)

`get_pr` presents number, title, state, URL, base/head branches, merge timestamp, merge
SHA, and body. The complete `PROutput` uses the same fields in the cache.

The DTO is stored in the MCP Resource cache at `pgmcp://cache/runs/{run_id}` and contains the following fields:
- `success`: `bool`
- `error_message`: `string | null`
- `post_tool_instruction`: `string | null`
- `number`: `int`
- `title`: `string`
- `html_url`: `string`
- `state`: `string`
- `base_ref`: `string`
- `head_ref`: `string`
- `merged_at`: `string | null`
- `merge_sha`: `string | null`
- `body`: `string`
#### Example Usage

```json
{
  "pr_number": 45
}
```

#### Behavior Notes

- `merged_at` is `null` for open or closed-but-not-merged PRs; ISO 8601 string when merged
- `merge_sha` is `null` when not merged
- Returns an `"error"` type result when PR is not found (404)

---

## Label Management Tools

### list_labels

**MCP Name:** `list_labels`  
**Class:** `ListLabelsTool`  
**File:** [mcp_server/tools/label_tools.py](../../../mcp_server/tools/label_tools.py)

List all labels defined in the repository.

#### Parameters

None.

#### Returns

The text response shows `total_labels` and up to ten labels with name, color, and
description. The complete `labels: list[LabelOutputModel]` remains in the cached
`ListLabelsOutput`.

#### Example Usage

```json
{}
```

#### Behavior Notes

- Returns ALL repository labels (no pagination)
- Color returned WITHOUT `#` prefix (e.g., `"0e8a16"` not `"#0e8a16"`)
- Used for validation in `create_issue`, `add_labels` tools

---

### create_label

**MCP Name:** `create_label`  
**Class:** `CreateLabelTool`  
**File:** [mcp_server/tools/label_tools.py](../../../mcp_server/tools/label_tools.py)

Create a new label in the repository. Validates against `LabelConfig` patterns.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | **Yes** | Label name in `category:value` format. Allowed categories: `type`, `priority`, `status`, `phase`, `scope`, `component`, `effort`, `parent`. Value: lowercase letters, digits, hyphens only. Example: `"type:feature"`. |
| `color` | `str` | **Yes** | Hex color code WITHOUT `#` prefix — exactly 6 characters (0-9, A-F, case-insensitive). Example: `"0e8a16"`. Pattern: `^[0-9A-Fa-f]{6}$` |
| `description` | `str` | No | Label description (default: empty string) |

#### Returns

The mutation response confirms `label_name` and `color`. Description is caller input and
is not duplicated in the `CreateLabelOutput` DTO.

#### Example Usage

```json
{
  "name": "type:feature",
  "color": "0e8a16",
  "description": "New feature or request"
}
```

#### Behavior Notes

- **LabelConfig Validation:** Validates name against patterns in [.pgmcp/config/labels.yaml](../../../.pgmcp/config/labels.yaml)
- **Duplicate Check:** Returns error if label already exists
- **Color Format:** Must be 6-character hex WITHOUT `#` (validated by Pydantic)

---

### delete_label

**MCP Name:** `delete_label`  
**Class:** `DeleteLabelTool`  
**File:** [mcp_server/tools/label_tools.py](../../../mcp_server/tools/label_tools.py)

Delete a label from the repository.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | **Yes** | Label name to delete |

#### Returns

The mutation response confirms `label_name` through `DeleteLabelOutput`.

#### Example Usage

```json
{
  "name": "type:feature"
}
```

#### Behavior Notes

- **Cascade:** Removes label from all issues/PRs
- **Non-existent Label:** Returns error (not idempotent)
- **No Undo:** Deletion is permanent

---

### add_labels

**MCP Name:** `add_labels`  
**Class:** `AddLabelsTool`  
**File:** [mcp_server/tools/label_tools.py](../../../mcp_server/tools/label_tools.py)

Add labels to an issue or pull request. Validates label existence before applying.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_number` | `int` | **Yes** | Issue or PR number |
| `labels` | `list[str]` | **Yes** | List of label names to add. Labels must follow the `category:value` naming pattern (e.g., `"priority:high"`, `"type:feature"`). |

#### Returns

The mutation response confirms `issue_number` and up to ten structured `labels` from
`LabelOperationOutput`; no preformatted duplicate label field exists.

#### Example Usage

```json
{
  "issue_number": 123,
  "labels": ["priority:high", "phase:implementation"]
}
```

#### Behavior Notes

- **Additive:** Adds labels without removing existing ones
- **Idempotent:** Adding already-present labels is safe (no error)
- **Validation:** Returns error if any label doesn't exist in repository

---

### remove_labels

**MCP Name:** `remove_labels`  
**Class:** `RemoveLabelsTool`  
**File:** [mcp_server/tools/label_tools.py](../../../mcp_server/tools/label_tools.py)

Remove labels from an issue or pull request.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_number` | `int` | **Yes** | Issue or PR number |
| `labels` | `list[str]` | **Yes** | List of label names to remove |

#### Returns

The mutation response uses the same bounded `LabelOperationOutput` projection as
`add_labels`.

#### Example Usage

```json
{
  "issue_number": 123,
  "labels": ["phase:implementation"]
}
```

#### Behavior Notes

- **Idempotent:** Removing non-existent labels is safe (no error)
- **Partial Removal:** Does not affect other labels on the issue/PR

---

## Milestone Management Tools

### list_milestones

**MCP Name:** `list_milestones`  
**Class:** `ListMilestonesTool`  
**File:** [mcp_server/tools/milestone_tools.py](../../../mcp_server/tools/milestone_tools.py)

List repository milestones with optional state filter.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `state` | `str` | No | Filter by state: `"open"`, `"closed"`, `"all"` (default: `"open"`) |

#### Returns

The text response shows `total_milestones` and up to ten records with number, state, and
title. The complete `milestones: list[MilestoneSummaryDTO]` remains in the cached
`ListMilestonesOutput`.

#### Example Usage

**List open milestones:**
```json
{
  "state": "open"
}
```

**List all milestones:**
```json
{
  "state": "all"
}
```

#### Behavior Notes

- **Default State:** `"open"` (only open milestones)
- **Presentation:** Due dates, descriptions, and issue counts are not part of `MilestoneSummaryDTO`.

---

### create_milestone

**MCP Name:** `create_milestone`  
**Class:** `CreateMilestoneTool`  
**File:** [mcp_server/tools/milestone_tools.py](../../../mcp_server/tools/milestone_tools.py)

Create a new milestone in the repository.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | `str` | **Yes** | Milestone title (Unicode-safe) |
| `description` | `str` | No | Milestone description (supports Markdown and Unicode) |
| `due_on` | `str` | No | Due date in ISO 8601 format (e.g., `"2026-03-01T00:00:00Z"`) |

#### Returns

The mutation response confirms milestone `number`, `title`, and realized `state` through
`MilestoneOutput`. Description and due date are caller inputs and are not duplicated in
the output DTO.

#### Example Usage

**Create milestone with due date:**
```json
{
  "title": "v2.1 Release",
  "description": "Minor feature release",
  "due_on": "2026-04-01T00:00:00Z"
}
```

**Create milestone without due date:**
```json
{
  "title": "Backlog",
  "description": "Future work items"
}
```

#### Behavior Notes

- **Default State:** Always created in `open` state
- **due_on Format:** Must be ISO 8601 string (validated by GitHub API)
- **Unicode Support:** Title and description support full Unicode

---

### close_milestone

**MCP Name:** `close_milestone`  
**Class:** `CloseMilestoneTool`  
**File:** [mcp_server/tools/milestone_tools.py](../../../mcp_server/tools/milestone_tools.py)

Close a milestone by number.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `milestone_number` | `int` | **Yes** | Milestone number to close |

#### Returns

The mutation response confirms milestone `number`, `title`, and realized `state` through
`MilestoneOutput`.

#### Example Usage

```json
{
  "milestone_number": 5
}
```

#### Behavior Notes

- **Idempotent:** Closing an already-closed milestone returns success
- **Issues:** Does NOT automatically close issues in the milestone
- **Reopen:** Use `update_milestone` (not currently implemented) to reopen

---

## Error Handling

All GitHub tools return structured error responses:

```json
{
  "success": false,
  "error": "GitHub API error: 404 Not Found",
  "details": "Issue #999 does not exist"
}
```

### Common Error Scenarios

| Error | Cause | Solution |
|-------|-------|----------|
| `GITHUB_TOKEN not set` | Missing environment variable | Set `GITHUB_TOKEN` in environment |
| `401 Unauthorized` | Invalid or expired token | Regenerate GitHub token |
| `403 Forbidden` | Insufficient token permissions | Grant additional scopes to token |
| `404 Not Found` | Resource doesn't exist (issue, PR, label, milestone) | Verify resource number/name |
| `422 Unprocessable Entity` | Invalid input (e.g., label name doesn't match pattern) | Check input format and validation rules |

---

## Unicode Support

All GitHub tools fully support Unicode content including emojis, non-ASCII characters, and international text:

**Supported Everywhere:**
- Issue/PR titles and bodies
- Label names, colors, and descriptions
- Milestone titles and descriptions
- Comments

**Example:**
```json
{
  "title": "🚀 Feature: Add multilingual support (日本語, 한국어, العربية)",
  "body": "Implement i18n for Japanese (日本語), Korean (한국어), and Arabic (العربية) languages.\n\n✅ Completed tasks:\n- [ ] Setup i18n framework\n- [ ] Add translation files\n- [ ] Update UI components",
  "labels": ["type:feature", "area:i18n"]
}
```

---

## Configuration

### .pgmcp/config/labels.yaml

Labels created via `create_label` are validated against patterns in [.pgmcp/config/labels.yaml](../../../.pgmcp/config/labels.yaml):

```yaml
# Labels are defined in .pgmcp/config/labels.yaml
# See the file for the full list — key categories:
#
# labels:              # Named labels (type:*, priority:*, scope:*)
# label_patterns:      # Regex patterns for dynamic labels (parent:NNN, phase:SLUG)
# freeform_exceptions: # Labels exempt from pattern validation
```

**Freeform Exception:**
Labels matching `freeform-*` pattern bypass pattern validation.

---

## Related Documentation

- [README.md](README.md) — MCP Tools navigation index
- [project.md](project.md) — Project initialization and phase management
- [.pgmcp/config/labels.yaml](../../../.pgmcp/config/labels.yaml) — Label configuration
- [docs/development/archive/issue19/research.md](../../development/archive/issue19/research.md) — Historical tool inventory research (Section 1.4-1.7: GitHub tools)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 3.1 | 2026-08-22 | Agent | Align credential activation, bounded list/detail projections, and cached DTO contracts |
| 2.0 | 2026-02-08 | Agent | Complete reference for 16 GitHub tools: issues (5), PRs (3), labels (5), milestones (3) |
