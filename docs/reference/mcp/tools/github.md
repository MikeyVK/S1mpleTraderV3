<!-- docs/reference/mcp/tools/github.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-02-08 -->
# GitHub Integration Tools

**Status:** DEFINITIVE  
**Version:** 2.0  
**Last Updated:** 2026-02-08  

**Source:** [mcp_server/tools/issue_tools.py](../../../../mcp_server/tools/issue_tools.py), [pr_tools.py](../../../../mcp_server/tools/pr_tools.py), [label_tools.py](../../../../mcp_server/tools/label_tools.py), [milestone_tools.py](../../../../mcp_server/tools/milestone_tools.py)  
**Tests:** [tests/unit/test_github_tools.py](../../../../tests/unit/test_github_tools.py)  

---

## Purpose

Complete reference documentation for all 16 GitHub API integration tools covering issues, pull requests, labels, and milestones. These tools provide full GitHub workflow automation with Unicode safety, validation against repository state, and structured error handling.

All GitHub tools require a `GITHUB_TOKEN` environment variable. Tools are registered even without a token (schema-only), but execution returns errors if the token is missing.

---

## Overview

The MCP server provides **16 GitHub tools** across 4 functional categories:

| Category | Tools | Key Features |
|----------|-------|-------------|
| **Issues** | 5 | Create, read, list, update, close with Unicode support |
| **Pull Requests** | 3 | Create, list, merge with draft support and merge strategies |
| **Labels** | 5 | CRUD operations with LabelConfig validation |
| **Milestones** | 3 | List, create, close with state filtering |

All tools:
- ✅ Support Unicode content (emojis, non-ASCII characters)
- ✅ Validate inputs before API calls
- ✅ Return structured responses with detailed error messages
- ✅ Require `GITHUB_TOKEN` environment variable
- ✅ Detect repository from git remote or `GITHUB_REPO` env var

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
**File:** [mcp_server/tools/issue_tools.py](../../../../mcp_server/tools/issue_tools.py)

Create a new GitHub issue with optional labels, milestone, and assignees.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | `str` | **Yes** | Issue title (Unicode-safe) |
| `body` | `str` | **Yes** | Issue description (supports Markdown and Unicode) |
| `labels` | `list[str]` | No | List of label names to apply (validates against existing labels) |
| `milestone` | `int` | No | Milestone number (not title) |
| `assignees` | `list[str]` | No | List of GitHub usernames to assign |

#### Returns

```json
{
  "success": true,
  "issue": {
    "number": 123,
    "url": "https://github.com/owner/repo/issues/123",
    "title": "Feature request: Add user authentication",
    "state": "open",
    "labels": ["type:feature", "priority:high"],
    "milestone": 5,
    "assignees": ["username1", "username2"]
  }
}
```

#### Example Usage

```json
{
  "title": "Feature: Add OAuth2 authentication 🔐",
  "body": "## Description\n\nImplement OAuth2 authentication with Google and GitHub providers.\n\n## Acceptance Criteria\n- [ ] Google OAuth2 integration\n- [ ] GitHub OAuth2 integration\n- [ ] Token refresh logic",
  "labels": ["type:feature", "priority:high"],
  "milestone": 5,
  "assignees": ["developer1"]
}
```

#### Behavior Notes

- **Unicode Support:** Title and body support full Unicode including emojis (no stripping)
- **Label Validation:** If label doesn't exist, GitHub API returns error
- **Milestone Validation:** Must use milestone **number** (not title)
- **Assignee Validation:** Usernames must be valid collaborators
- **Default State:** Issues always created in `open` state

---

### get_issue

**MCP Name:** `get_issue`  
**Class:** `GetIssueTool`  
**File:** [mcp_server/tools/issue_tools.py](../../../../mcp_server/tools/issue_tools.py)

Retrieve detailed information about a specific issue.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_number` | `int` | **Yes** | Issue number to retrieve |

#### Returns

```json
{
  "success": true,
  "issue": {
    "number": 123,
    "url": "https://github.com/owner/repo/issues/123",
    "title": "Feature request: Add user authentication",
    "body": "## Description\n\nDetailed issue body...",
    "state": "open",
    "labels": ["type:feature", "priority:high"],
    "milestone": {
      "number": 5,
      "title": "v2.0",
      "state": "open"
    },
    "assignees": ["username1"],
    "created_at": "2026-02-01T10:00:00Z",
    "updated_at": "2026-02-08T12:00:00Z",
    "closed_at": null,
    "author": "username2"
  }
}
```

#### Example Usage

```json
{
  "issue_number": 123
}
```

#### Behavior Notes

- Returns full issue details including milestone object (not just number)
- `closed_at` is `null` for open issues
- Includes timestamps in ISO 8601 format

---

### list_issues

**MCP Name:** `list_issues`  
**Class:** `ListIssuesTool`  
**File:** [mcp_server/tools/issue_tools.py](../../../../mcp_server/tools/issue_tools.py)

List repository issues with optional state and label filters.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `state` | `str` | No | Filter by state: `"open"`, `"closed"`, `"all"` (default: `None` = all) |
| `labels` | `list[str]` | No | Filter by labels (AND logic — all labels must match) |

#### Returns

```json
{
  "success": true,
  "issues": [
    {
      "number": 123,
      "title": "Feature request",
      "state": "open",
      "labels": ["type:feature"],
      "milestone": 5,
      "assignees": ["user1"]
    },
    {
      "number": 124,
      "title": "Bug report",
      "state": "closed",
      "labels": ["type:bug", "priority:high"],
      "milestone": null,
      "assignees": []
    }
  ],
  "count": 2
}
```

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
- **Pagination:** Currently returns first 100 issues (GitHub API default)
- **Sort Order:** Newest first (by creation date)

---

### update_issue

**MCP Name:** `update_issue`  
**Class:** `UpdateIssueTool`  
**File:** [mcp_server/tools/issue_tools.py](../../../../mcp_server/tools/issue_tools.py)

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

```json
{
  "success": true,
  "issue": {
    "number": 123,
    "url": "https://github.com/owner/repo/issues/123",
    "title": "Updated title",
    "state": "closed",
    "labels": ["type:feature", "status:resolved"],
    "milestone": 6,
    "assignees": ["newuser"]
  }
}
```

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
  "labels": ["type:feature", "status:resolved", "phase:done"]
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
**File:** [mcp_server/tools/issue_tools.py](../../../../mcp_server/tools/issue_tools.py)

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

### create_pr

**MCP Name:** `create_pr`  
**Class:** `CreatePRTool`  
**File:** [mcp_server/tools/pr_tools.py](../../../../mcp_server/tools/pr_tools.py)

Create a new pull request.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | `str` | **Yes** | PR title (Unicode-safe) |
| `body` | `str` | **Yes** | PR description (supports Markdown and Unicode) |
| `head` | `str` | **Yes** | Source branch (e.g., `"feature/123-my-feature"`) |
| `base` | `str` | No | Target branch (default: `"main"`) |
| `draft` | `bool` | No | Create as draft PR (default: `False`) |

#### Returns

```json
{
  "success": true,
  "pr": {
    "number": 45,
    "url": "https://github.com/owner/repo/pull/45",
    "title": "Feature: Add OAuth2 authentication",
    "head": "feature/123-oauth",
    "base": "main",
    "state": "open",
    "draft": false
  }
}
```

#### Example Usage

**Create regular PR:**
```json
{
  "title": "Feature: Add OAuth2 authentication 🔐",
  "body": "## Changes\n\n- Implemented Google OAuth2\n- Implemented GitHub OAuth2\n- Added token refresh\n\nCloses #123",
  "head": "feature/123-oauth",
  "base": "main"
}
```

**Create draft PR:**
```json
{
  "title": "WIP: OAuth2 authentication",
  "body": "Early draft for feedback.",
  "head": "feature/123-oauth",
  "draft": true
}
```

#### Behavior Notes

- **Default Base:** If `base` not specified, defaults to repository's default branch (usually `main`)
- **Draft PRs:** Draft PRs cannot be merged until marked ready for review
- **Unicode Support:** Title and body support full Unicode
- **Branch Validation:** Head branch must exist; base branch must exist
- **Auto-link Issues:** Use `Closes #123` in body to auto-link issues

---

### list_prs

**MCP Name:** `list_prs`  
**Class:** `ListPRsTool`  
**File:** [mcp_server/tools/pr_tools.py](../../../../mcp_server/tools/pr_tools.py)

List repository pull requests with optional state, base, and head filters.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `state` | `str` | No | Filter by state: `"open"`, `"closed"`, `"all"` (default: `"open"`) |
| `base` | `str` | No | Filter by base branch (e.g., `"main"`) |
| `head` | `str` | No | Filter by head branch (e.g., `"feature/123-my-feature"`) |

#### Returns

```json
{
  "success": true,
  "prs": [
    {
      "number": 45,
      "title": "Feature: Add OAuth2 authentication",
      "head": "feature/123-oauth",
      "base": "main",
      "state": "open",
      "draft": false,
      "mergeable": true
    },
    {
      "number": 44,
      "title": "Bugfix: Fix login issue",
      "head": "bugfix/122-login",
      "base": "main",
      "state": "closed",
      "draft": false,
      "mergeable": null
    }
  ],
  "count": 2
}
```

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
- **Pagination:** Returns first 100 PRs (GitHub API default)
- **mergeable Field:** `true`, `false`, or `null` (GitHub hasn't computed merge status yet)
- **Draft PRs:** Included in results with `draft: true`

---

### merge_pr

**MCP Name:** `merge_pr`  
**Class:** `MergePRTool`  
**File:** [mcp_server/tools/pr_tools.py](../../../../mcp_server/tools/pr_tools.py)

Merge a pull request with specified merge strategy.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pr_number` | `int` | **Yes** | Pull request number to merge |
| `merge_method` | `str` | No | Merge strategy: `"merge"`, `"squash"`, `"rebase"` (default: `"merge"`) |
| `commit_message` | `str` | No | Optional custom commit message (for merge/squash) |

#### Returns

```json
{
  "success": true,
  "message": "PR #45 merged successfully",
  "merge": {
    "sha": "abc123def456",
    "merged": true,
    "method": "squash"
  }
}
```

#### Example Usage

**Merge with default strategy:**
```json
{
  "pr_number": 45
}
```

**Squash merge with custom message:**
```json
{
  "pr_number": 45,
  "merge_method": "squash",
  "commit_message": "Feature: Add OAuth2 authentication (#45)\n\nCloses #123"
}
```

**Rebase merge:**
```json
{
  "pr_number": 45,
  "merge_method": "rebase"
}
```

#### Merge Strategies

| Method | Behavior | Commit History | Use Case |
|--------|----------|----------------|----------|
| `merge` (default) | Creates merge commit | All commits preserved | Feature branches with meaningful commit history |
| `squash` | Squashes all commits into one | Single commit | Clean up messy WIP commits |
| `rebase` | Rebases and fast-forwards | Linear history | Maintain linear history |

#### Behavior Notes

- **Draft PRs:** Cannot merge draft PRs (returns error)
- **Merge Conflicts:** Returns error if conflicts exist (must resolve first)
- **Branch Protection:** Respects branch protection rules (required reviews, status checks)
- **Auto-Delete:** Does NOT automatically delete head branch (GitHub repo setting controls this)

---

## Label Management Tools

### list_labels

**MCP Name:** `list_labels`  
**Class:** `ListLabelsTool`  
**File:** [mcp_server/tools/label_tools.py](../../../../mcp_server/tools/label_tools.py)

List all labels defined in the repository.

#### Parameters

None.

#### Returns

```json
{
  "success": true,
  "labels": [
    {
      "name": "type:feature",
      "color": "0e8a16",
      "description": "New feature or request"
    },
    {
      "name": "type:bug",
      "color": "d73a4a",
      "description": "Something isn't working"
    },
    {
      "name": "priority:high",
      "color": "ff0000",
      "description": "High priority"
    }
  ],
  "count": 3
}
```

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
**File:** [mcp_server/tools/label_tools.py](../../../../mcp_server/tools/label_tools.py)

Create a new label in the repository. Validates against `LabelConfig` patterns.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | **Yes** | Label name (e.g., `"type:feature"`) — validates against patterns |
| `color` | `str` | **Yes** | Color hex code WITHOUT `#` (e.g., `"0e8a16"`) |
| `description` | `str` | No | Label description (default: empty string) |

#### Returns

```json
{
  "success": true,
  "label": {
    "name": "type:feature",
    "color": "0e8a16",
    "description": "New feature or request"
  }
}
```

#### Example Usage

```json
{
  "name": "type:feature",
  "color": "0e8a16",
  "description": "New feature or request"
}
```

#### Behavior Notes

- **LabelConfig Validation:** Validates name against patterns in [.st3/labels.yaml](../../../../.st3/labels.yaml)
- **Duplicate Check:** Returns error if label already exists
- **Color Format:** Must be 6-character hex WITHOUT `#` (validated by Pydantic)

---

### delete_label

**MCP Name:** `delete_label`  
**Class:** `DeleteLabelTool`  
**File:** [mcp_server/tools/label_tools.py](../../../../mcp_server/tools/label_tools.py)

Delete a label from the repository.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | **Yes** | Label name to delete |

#### Returns

```json
{
  "success": true,
  "message": "Label 'type:feature' deleted"
}
```

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
**File:** [mcp_server/tools/label_tools.py](../../../../mcp_server/tools/label_tools.py)

Add labels to an issue or pull request. Validates label existence before applying.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_number` | `int` | **Yes** | Issue or PR number |
| `labels` | `list[str]` | **Yes** | List of label names to add |

#### Returns

```json
{
  "success": true,
  "message": "Labels added to issue #123",
  "labels": ["type:feature", "priority:high"]
}
```

#### Example Usage

```json
{
  "issue_number": 123,
  "labels": ["priority:high", "status:in-progress"]
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
**File:** [mcp_server/tools/label_tools.py](../../../../mcp_server/tools/label_tools.py)

Remove labels from an issue or pull request.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_number` | `int` | **Yes** | Issue or PR number |
| `labels` | `list[str]` | **Yes** | List of label names to remove |

#### Returns

```json
{
  "success": true,
  "message": "Labels removed from issue #123",
  "labels": ["status:in-progress"]
}
```

#### Example Usage

```json
{
  "issue_number": 123,
  "labels": ["status:in-progress"]
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
**File:** [mcp_server/tools/milestone_tools.py](../../../../mcp_server/tools/milestone_tools.py)

List repository milestones with optional state filter.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `state` | `str` | No | Filter by state: `"open"`, `"closed"`, `"all"` (default: `"open"`) |

#### Returns

```json
{
  "success": true,
  "milestones": [
    {
      "number": 5,
      "title": "v2.0",
      "state": "open",
      "description": "Version 2.0 release",
      "due_on": "2026-03-01T00:00:00Z",
      "open_issues": 12,
      "closed_issues": 8
    },
    {
      "number": 4,
      "title": "v1.5",
      "state": "closed",
      "description": null,
      "due_on": null,
      "open_issues": 0,
      "closed_issues": 15
    }
  ],
  "count": 2
}
```

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
- **due_on:** ISO 8601 timestamp or `null` if no due date
- **Issue Counts:** Includes open/closed issue counts

---

### create_milestone

**MCP Name:** `create_milestone`  
**Class:** `CreateMilestoneTool`  
**File:** [mcp_server/tools/milestone_tools.py](../../../../mcp_server/tools/milestone_tools.py)

Create a new milestone in the repository.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | `str` | **Yes** | Milestone title (Unicode-safe) |
| `description` | `str` | No | Milestone description (supports Markdown and Unicode) |
| `due_on` | `str` | No | Due date in ISO 8601 format (e.g., `"2026-03-01T00:00:00Z"`) |

#### Returns

```json
{
  "success": true,
  "milestone": {
    "number": 6,
    "title": "v2.1",
    "state": "open",
    "description": "Minor release",
    "due_on": "2026-04-01T00:00:00Z"
  }
}
```

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
**File:** [mcp_server/tools/milestone_tools.py](../../../../mcp_server/tools/milestone_tools.py)

Close a milestone by number.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `milestone_number` | `int` | **Yes** | Milestone number to close |

#### Returns

```json
{
  "success": true,
  "message": "Milestone #5 'v2.0' closed",
  "milestone": {
    "number": 5,
    "title": "v2.0",
    "state": "closed"
  }
}
```

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

### .st3/labels.yaml

Labels created via `create_label` are validated against patterns in [.st3/labels.yaml](../../../../.st3/labels.yaml):

```yaml
label_config:
  patterns:
    - pattern: "type:(feature|bug|docs|refactor|test|chore)"
      required: true
    - pattern: "priority:(low|medium|high|critical)"
      required: false
    - pattern: "status:(backlog|in-progress|review|done)"
      required: false
```

**Freeform Exception:**
Labels matching `freeform-*` pattern bypass pattern validation.

---

## Related Documentation

- [README.md](README.md) — MCP Tools navigation index
- [project.md](project.md) — Project initialization and phase management
- [.st3/labels.yaml](../../../../.st3/labels.yaml) — Label configuration
- [docs/development/issue19/research.md](../../../development/issue19/research.md) — Tool inventory research (Section 1.4-1.7: GitHub tools)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-02-08 | Agent | Complete reference for 16 GitHub tools: issues (5), PRs (3), labels (5), milestones (3) |
