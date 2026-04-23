# ST3 Workflow MCP Server - Public Tool Surface

**Status:** CURRENT
**Last Updated:** 2026-04-23
**Derived From:** [mcp_server/server.py](../../mcp_server/server.py)

> This document is the current public MCP tool surface summary. Detailed per-tool behavior lives in [docs/reference/mcp/MCP_TOOLS.md](../reference/mcp/MCP_TOOLS.md) and the category references under [docs/reference/mcp/tools/](../reference/mcp/tools/README.md).

---

## Purpose

Provide an implementation-synchronized summary of the MCP tools currently exposed by the server.
This replaces older planning-era tool specs that documented tools which never became part of the
public server surface.

---

## Registration Model

The server exposes:

- **34 always-available tools**
- **16 GitHub-dependent tools** when `GITHUB_TOKEN` is configured
- **50 total tools** when GitHub integration is active

GitHub issue tools are registered only when GitHub integration is available. `submit_pr`,
`list_prs`, and `merge_pr` are the public PR tools.

---

## Tool Categories

### 1. Git Workflow & Analysis

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_branch` | Create feature/bug/docs/refactor/hotfix/epic branches | `name`, `branch_type`, `base_branch` |
| `git_status` | Show working tree status | none |
| `git_add_or_commit` | Commit with workflow-aware prefixing | `message`, `workflow_phase`, `sub_phase`, `cycle_number`, `commit_type` |
| `git_checkout` | Switch branches and sync state | `branch` |
| `git_fetch` | Fetch from remote | `remote`, `prune` |
| `git_pull` | Pull with optional rebase | `remote`, `rebase` |
| `git_push` | Push to origin | `set_upstream` |
| `git_merge` | Merge branch into current branch | `branch` |
| `git_delete_branch` | Delete a branch safely | `branch`, `force` |
| `git_stash` | Push, pop, or list stash entries | `action`, `message`, `include_untracked` |
| `git_restore` | Restore files from a git ref | `files`, `source` |
| `git_list_branches` | List branches with optional verbosity | `verbose`, `remote` |
| `git_diff_stat` | Compare branches | `target_branch`, `source_branch` |
| `get_parent_branch` | Detect parent branch | `branch` |

### 2. GitHub Issues

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_issue` | Create issue with workflow-aware labels | `issue_type`, `title`, `priority`, `scope`, `body`, `is_epic`, `parent_issue`, `milestone`, `assignees` |
| `list_issues` | List issues with filters | `state`, `labels` |
| `get_issue` | Get issue detail | `issue_number` |
| `update_issue` | Update title, body, state, labels, milestone, assignees | `issue_number`, optional fields |
| `close_issue` | Close issue with optional comment | `issue_number`, `comment` |

### 3. Pull Requests

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `submit_pr` | Atomically neutralize, commit, push, and create a PR | `head`, `title`, `base`, `body`, `draft` |
| `list_prs` | List PRs with filters | `state`, `base`, `head` |
| `merge_pr` | Merge PR and clear PR status cache | `pr_number`, `commit_message`, `merge_method` |

#### `submit_pr` Contract

**Required parameters:**
- `head: str`
- `title: str`

**Optional parameters:**
- `base: str | None` — defaults to the repository default branch
- `body: str | None`
- `draft: bool` — defaults to `False`

**Execution behavior:**
1. Computes net branch-local artifact diffs against the merge-base.
2. Neutralizes `.st3/state.json` and `.st3/deliverables.json` when needed.
3. Commits the neutralization with `workflow_phase="ready"`.
4. Pushes the branch.
5. Creates the GitHub PR.
6. Writes `PRStatus.OPEN` to cache.

**Safeguards:**
- Blocked unless `.st3/state.json` reports `current_phase == "ready"`
- Blocked for any branch-mutating tool while the branch already has `PRStatus.OPEN`
- Returns a `RecoveryNote` when the flow fails after neutralization and the branch tip may have changed

**Public output:**
- Success: `Created PR #<number>: <url>`
- Failure: error result with the underlying execution message

### 4. Labels & Milestones

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `list_labels` | List repository labels | none |
| `create_label` | Create label | `name`, `color`, `description` |
| `delete_label` | Delete label | `name` |
| `add_labels` | Add labels to issue or PR | `issue_number`, `labels` |
| `remove_labels` | Remove labels from issue or PR | `issue_number`, `labels` |
| `list_milestones` | List milestones | `state` |
| `create_milestone` | Create milestone | `title`, `description`, `due_on` |
| `close_milestone` | Close milestone | `milestone_number` |

### 5. Project & Phase Management

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `initialize_project` | Initialize workflow state for an issue | issue/workflow parameters |
| `get_project_plan` | Get workflow phase plan | issue/workflow context |
| `save_planning_deliverables` | Save planning deliverables | `issue_number` |
| `update_planning_deliverables` | Merge planning deliverables | `issue_number` |
| `transition_phase` | Sequential phase transition | `branch`, `to_phase` |
| `force_phase_transition` | Forced phase transition | `branch`, `to_phase`, `skip_reason`, `human_approval` |
| `transition_cycle` | Sequential TDD cycle transition | `to_cycle` |
| `force_cycle_transition` | Forced TDD cycle transition | `to_cycle`, `skip_reason`, `human_approval` |

### 6. Editing & Scaffolding

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `safe_edit_file` | Multi-mode file editing with validation | `path`, `content` or edit payload, `mode` |
| `create_file` | Create a generic file | `path`, `content` |
| `scaffold_artifact` | Generate code/docs from `.st3/config/artifacts.yaml` | `artifact_type`, `name`, `output_path`, `context` |

### 7. Quality & Validation

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `run_quality_gates` | Run quality gates | `scope`, `files` |
| `run_tests` | Run pytest | `path`, `scope`, `markers`, `timeout`, `last_failed_only` |
| `validate_architecture` | Validate architecture rules | `scope` |
| `validate_dto` | Validate DTO definitions | `file_path` |
| `validate_template` | Validate template/file structure | `path`, `template_type` |

### 8. Discovery & Admin

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `search_documentation` | Semantic/fuzzy docs search | `query`, `scope` |
| `get_work_context` | Aggregate current work context | `include_closed_recent` |
| `health_check` | Report server health | none |
| `restart_server` | Hot-reload the MCP server | `reason` |

---

## Removed Or Internal-Only Paths

These names should not be used as public tool contracts:

- `create_pr` — deleted as a public tool; replaced by `submit_pr`
- `create_feature_branch` — old alias; use `create_branch`
- `commit_tdd_phase` — old name; use `git_add_or_commit`
- `validate_doc` / `validate_document_structure` — not part of the current public server surface
- `fix_whitespace` — not part of the current public server surface

---

## Canonical References

- [docs/reference/mcp/MCP_TOOLS.md](../reference/mcp/MCP_TOOLS.md)
- [docs/reference/mcp/tools/README.md](../reference/mcp/tools/README.md)
- [docs/reference/mcp/tools/github.md](../reference/mcp/tools/github.md)
- [docs/reference/mcp/tools/git.md](../reference/mcp/tools/git.md)
- [docs/reference/mcp/tools/project.md](../reference/mcp/tools/project.md)
- [docs/reference/mcp/tools/quality.md](../reference/mcp/tools/quality.md)
