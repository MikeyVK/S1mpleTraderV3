# MCP Tools Reference

> [!IMPORTANT]
> **Legacy consolidated overview.** The authoritative current tool reference starts at
> [tools/README.md](tools/README.md) and its category pages. Live MCP tool schemas remain
> authoritative for callable parameters. This page is retained for broad orientation and
> must not be used as an independent workflow contract.

## Overview

The PhaseGate MCP Server provides **50 tools** for git workflow automation, project management, quality assurance, and documentation scaffolding. All tools are accessed through Model Context Protocol (MCP) from supported agent harnesses.

**Server Location:** `mcp_server/`
**Configuration:** `.vscode/mcp.json` → `phase-gate-mcp`
**Main Entry:** `mcp_server/__main__.py`

## Tool Categories

### 1. Git Workflow & Analysis (15 tools)

Comprehensive git automation with workflow-driven phase and optional implementation-cycle tracking.

| Tool | Purpose | Parameters | Example |
|------|---------|------------|---------|
| **CreateBranchTool** | Create feature/bug/docs/refactor/hotfix/chore/epic branch | `name` (kebab-case), `base_branch` (**required**), `branch_type` (default: feature) | `create_branch(name="feature/123-add-metrics", base_branch="main")` |
| **GitStatusTool** | Show working tree status | None | Returns current branch, staged, unstaged files |
| **GitCommitTool** | Commit with phase prefix + issue suffix | `message`, `workflow_phase`, `sub_phase`, `cycle_number` | `git_add_or_commit(workflow_phase="implementation", sub_phase="green", cycle_number=1, message="...")` |
| **GitCheckoutTool** | Switch branches | `branch` | `checkout main` |
| **GitFetchTool** | Fetch from remote | `remote`, `prune` | `git_fetch(remote="origin", prune=true)` |
| **GitPullTool** | Pull updates with optional rebase | `remote`, `rebase` | `git_pull(rebase=false)` |
| **GitPushTool** | Push to origin | `set_upstream` (optional, for new branches) | `push set_upstream=true` |
| **GitMergeTool** | Merge feature → main | `branch` to merge | `merge feature/new-feature` |
| **GitDeleteBranchTool** | Delete branch (safe by default) | `branch`, `force` (optional) | `delete_branch branch=feature/old force=false` |
| **GitStashTool** | Save/restore WIP | `action` (push/pop/list), `message` (optional for push) | `stash action=push message=wip` |
| **GitRestoreTool** | Restore files from a git ref | `files`, `source` | `git_restore(files=["path/to/file.py"], source="HEAD")` |
| **GitListBranchesTool** | List branches with verbosity options | `verbose`, `remote` | `git_list_branches(verbose=true)` |
| **GitDiffTool** | Diff statistics between branches | `target_branch`, `source_branch` | `git_diff_stat(target_branch="main")` |
| **GetParentBranchTool** | Detect parent branch via phase state | `branch` | `get_parent_branch(branch="feature/123")` |
| **CheckMergeTool** | Verify merge SHA is reachable from HEAD | `merge_sha` | `check_merge(merge_sha="abc123")` |

**Workflow Example:**
```
1. create_branch(name="feature/my-feature", base_branch="main")
2. git_checkout(branch="feature/my-feature")
3. (Make changes)
4. git_add_or_commit(workflow_phase="implementation", sub_phase="green", cycle_number=1, message="Add feature")
5. git_push(set_upstream=True)
6. transition_phase(to_phase="ready")
7. submit_pr(title="Add feature", head="feature/my-feature", base="main")
8. (After merge)
9. git_checkout(branch="main")
10. git_delete_branch(branch="feature/my-feature")  # mode="both" (default: deletes local + remote)
```

**Related:** [Project and Phase Management](tools/project.md) and [Agent Instructions Model](copilot-agent-instructions-model.md)

### 2. GitHub Integration (17 tools)

Full GitHub API integration for issues, pull requests, labels, and milestones. Requires `GITHUB_TOKEN` environment variable.

#### Issues (5 tools)

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **CreateIssueTool** | Create new issue | **Required:** `issue_type` (feature/bug/hotfix/refactor/docs/chore/epic), `title`, `priority` (critical/high/medium/low/triage), `scope` (architecture/mcp-server/platform/tooling/workflow/documentation), `body` (str: pre-rendered markdown — generate with `scaffold_artifact(artifact_type='issue')`) · **Optional:** `is_epic` (bool), `parent_issue` (int), `milestone` (title string), `assignees` (list) | Issue number, URL |
| **ListIssuesTool** | List issues with filters | `state` (open/closed/all), `labels` (optional list) | Formatted list with numbers, titles, labels |
| **GetIssueTool** | Get issue details | `issue_number` | Full issue data, acceptance criteria extracted |
| **CloseIssueTool** | Close issue | `issue_number`, `comment` (optional) | Confirmation message |
| **UpdateIssueTool** | Modify issue fields | `issue_number`, then any of: `title`, `body`, `state`, `labels`, `milestone_number`, `assignees` | Updated issue |

**Usage Example:**
```
1. list_issues state=open
2. get_issue issue_number=4
3. update_issue issue_number=4 state=in-progress labels=["bug", "critical"]
4. close_issue issue_number=4 comment="Fixed in PR #123"
```

#### Pull Requests (4 tools)

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **SubmitPRTool** | Create PR (atomic flow) | `title`, `head` (source branch), `body` (optional), `base` (default: main), `draft` (optional) | PR number, URL |
| **ListPRsTool** | List PRs with filters | `state` (open/closed/all), `base` (optional), `head` (optional) | Formatted list with numbers, titles, status |
| **MergePRTool** | Merge PR | `pr_number`, `commit_message` (optional), `merge_method` (only `"merge"` is supported) | Merge result, SHA, message |
| **GetPRTool** | Get PR details | `pr_number` | PR number, title, state, base/head branch, merged_at, merge_sha, body |

> **Note:** `CreatePRTool` has been deleted (issue #283). Use `submit_pr` — it performs an
> atomically robust submission: preflights before any mutation (dirty-tree + upstream checks),
> conditional artifact neutralization + commit, push, GitHub API call, and `PRStatus.OPEN`.
> On any failure the branch is rolled back to a clean, retryable state (recovery note produced).
> Blocked unless `current_phase == "ready"`.

**Usage Example:**
```
1. transition_phase(to_phase="ready")
2. submit_pr(title="Add feature X", body="...", head="feature/x")
3. (after human approval)
4. merge_pr(pr_number=42)
```

#### Labels (5 tools)

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **ListLabelsTool** | List all labels | None | Formatted list with colors, descriptions |
| **CreateLabelTool** | Create new label | `name`, `color` (hex), `description` (optional) | Label created |
| **DeleteLabelTool** | Delete label | `name` | Confirmation |
| **AddLabelsTool** | Add labels to issue/PR | `issue_number`, `labels` (list) | Confirmation |
| **RemoveLabelsTool** | Remove labels from issue/PR | `issue_number`, `labels` (list) | Confirmation |

**Suggested Labels:**
- `bug` - Bug report / fix
- `feature` - New feature request
- `enhancement` - Improvement to existing feature
- `documentation` - Docs only
- `critical` - High priority
- `in-progress` - Currently being worked on
- `blocked` - Blocked by another issue

#### Milestones (3 tools)

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **ListMilestonesTool** | List milestones | `state` (open/closed/all) | Formatted list with titles, due dates, progress |
| **CreateMilestoneTool** | Create milestone | `title`, `description` (optional), `due_on` (optional ISO 8601) | Milestone created |
| **CloseMilestoneTool** | Close milestone | `milestone_number` | Confirmation |

**ISO 8601 Format:** `2025-12-31T00:00:00Z` or `2025-12-31T00:00:00+00:00`

### 3. Project & Phase Management (8 tools)

Workflow lifecycle management: project initialization, phase transitions, TDD cycle management, and planning deliverables.

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **InitializeProjectTool** | Initialize project with workflow state | `issue_number`, `issue_title`, `workflow_name`, `parent_branch`, `custom_phases` | Initialized state confirmation |
| **GetProjectPlanTool** | Get project phase plan for issue | `issue_number` | Phase plan with exit criteria |
| **SavePlanningDeliverablesTool** | Save planning deliverables | `issue_number` | Confirmation |
| **UpdatePlanningDeliverablesTool** | Update/merge planning deliverables | `issue_number` | Confirmation |
| **TransitionPhaseTool** | Sequential phase transition | `branch`, `to_phase`, `human_approval_message` | New phase state |
| **ForcePhaseTransitionTool** | Skip phases with reason + approval | `branch`, `to_phase`, `skip_reason`, `human_approval_message` | New phase state |
| **TransitionCycleTool** | Sequential TDD cycle transition | `to_cycle` | New cycle state |
| **ForceCycleTransitionTool** | Skip to cycle with reason + approval | `to_cycle`, `skip_reason`, `human_approval_message` | New cycle state |

### 4. File Editing (1 tool)

Multi-mode file editing with quality gate integration and concurrent edit protection.

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **SafeEditFileTool** | Frictionless 4-operation file editing with validation | `path`, `operation` (`replace`/`append`/`rewrite`/`pattern_replace`), `mode` | `SafeEditOutput` (success, path, passed, issues, written) |

### 5. Scaffolding (2 tools)

Generate new artifacts from templates (unified system).

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **ScaffoldArtifactTool** | Generate code/docs from artifacts.yaml | `artifact_type` (dto/worker/design/etc), `name`, context fields (varies by type), `output_path` (optional) | Generated file path |
| **ScaffoldSchemaTool** | Return JSON Schema for artifact type context | `artifact_type` | JSON Schema for the context parameter |

**Representative artifact types (authoritative registry: `.pgmcp/templates/config/`):**
- `dto` - Data Transfer Object with Pydantic
- `worker` - Background job/processor
- `design` - Design document
- `adapter` - External API integration
- `tool` - MCP tool

See `.pgmcp/templates/config/` for the complete registry and required context fields per type.

### 6. Quality & Validation (4 tools)

Apply mechanical fixes, run quality gates and tests, and validate templates.

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **AutoFixTool** | Apply configured mechanical quality fixes | None | Modified-file and gate summary |
| **RunQualityGatesTool** | Run config-driven quality gates | `scope` (`auto`/`branch`/`project`/`files`), `files` (required + non-empty only when `scope="files"`), `verbose` (optional: bool) | Single text block with summary + resource cache link to `RunQualityGatesOutput` DTO |
| **RunTestsTool** | Run pytest | `path` (space-sep, mutually exclusive with `scope`), `scope` (`"full"`), `markers`, `last_failed_only`, `timeout`, `coverage`, `verbose` | Single text block with summary + resource cache link to `RunTestsOutput` DTO |
| **TemplateValidationTool** | Validate file structure against template | `path`, `template_type` | Pass/fail with violation details |

**Quality Gates Standard (`.pgmcp/quality.yaml`):**
- **Gates 0–3:** Ruff format, strict lint, imports, line length
- **Gate 4:** Mypy-based type gate
- **Gate 4b:** Pyright type gate
- Test execution belongs to `run_tests` (not `run_quality_gates`).

### 7. Discovery & Admin (3 tools)

Work context aggregation and server administration.

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| **GetWorkContextTool** | Get current work state | `none` | Orientation header with TODO reminder, phase instructions, optional hand-over template |
| **HealthCheckTool** | Server health check | None | OK/ERROR (Sole tool registered in degraded mode) |
| **RestartServerTool** | Hot-reload server via proxy mechanism | `reason` | Confirmation (Unavailable in degraded mode) |

> [!NOTE]
> If a domain configuration error occurs during startup, the server runs in **degraded mode**. In this mode, only `HealthCheckTool` is available. `RestartServerTool` is excluded, requiring a manual restart of the server process after configuration fixes are applied.

**Usage Example:**
```
1. get_work_context() → Returns text like:
   Branch: `feature/x` | Workflow: feature | Issue: #4
   Phase: 🧪 implementation | Role: implementer
   TODO discipline: create or refresh your TODO list now; keep exactly one item in progress and update it after each material step.
   ---
   ### 🎯 Phase Instructions
```

## Architecture

### Tool Registration

All tools are registered in `mcp_server/server.py`:

**Always Available (33 tools):**
- Git tools (15)
- Project/Phase tools (8)
- Quality tools (4)
- File Editing (1)
- Scaffold tools (2)
- Discovery & Admin tools (3)

**GitHub-Dependent (17 tools, requires GITHUB_TOKEN):**
- Issue tools (5)
- PR tools (4)
- Label tools (5)
- Milestone tools (3)

**Total: 50 tools** (33 always-available + 17 GitHub-dependent)

### Execution Flow

```
User Request (VS Code)
    ↓
MCP Client (VS Code Extension)
    ↓
MCP Protocol (stdio)
    ↓
MCPServer.execute_tool()
    ↓
Tool.execute(**params)
    ↓
Manager.operation() [business logic]
    ↓
Adapter.method() [external API calls]
    ↓
ToolResult (success/error)
    ↓
MCP Response
    ↓
VS Code Display
```

### Error Handling

All tools use three exception types:

| Exception | When | Recovery |
|-----------|------|----------|
| **ExecutionError** | Tool fails to complete (API error, file not found) | Check parameters, retry |
| **ValidationError** | Invalid input parameters | Review schema, adjust input |
| **MCPSystemError** | Server misconfiguration (missing token, no repo access) | Configure settings, check permissions |

## Configuration

### Environment Variables

```bash
GITHUB_TOKEN=ghp_xxxxx           # Enable GitHub tools
GITHUB_OWNER=MikeyVK             # Repository owner
GITHUB_REPO=phase-gate-mcp        # Repository name
```

### VS Code Configuration

File: `.vscode/mcp.json`

```json
{
  "servers": {
    "phase-gate-mcp": {
      "type": "stdio",
      "command": "d:\\...\\python.exe",
      "args": ["-m", "mcp_server"],
      "cwd": "${workspaceFolder}",
      "env": {
        "GITHUB_TOKEN": "${env:GITHUB_TOKEN}"
      }
    }
  }
}
```

## Usage Examples

### Feature Workflow Orientation

A feature follows the phase order in `.pgmcp/config/contracts.yaml`: Research, Design,
Planning, Implementation, Validation, Documentation, and Ready. At each phase or cycle
boundary, call `get_work_context` and follow the returned contract. Use strict
RED → GREEN → REFACTOR only when the active contract and approved plan require it.
Run focused checks during implementation, broader verification in the phase that owns it,
and submit the PR from Ready with `submit_pr`.

### Issue Lifecycle Management

```
1. scaffold_artifact(
     artifact_type="issue",
     name="bug-memory-leak-cache",
     context={
       "title": "Bug: Memory leak in cache layer",
       "problem": "Memory grows unbounded after 1h of operation.",
       "steps_to_reproduce": "1. Start server\n2. Run 1000 requests",
       "expected": "Stable memory usage",
       "actual": "RSS grows to 2GB"
     }
   )
   → Returns: scaffolded body (pre-rendered markdown)
2. create_issue(
     issue_type="bug",
     title="Bug: Memory leak in cache layer",
     priority="high",
     scope="mcp-server",
     body="<rendered markdown from step 1>",
     milestone="v1.0.0"
   )
   → Returns: Created issue #47: Bug: Memory leak in cache layer
2. update_issue issue_number=47 state=in-progress
3. (Create PR linked to issue)
4. close_issue issue_number=47 comment="Fixed in PR #124"
```

Labels are assembled automatically from the required and optional fields. Do not pass a `labels` list — the tool enforces label policy from
`.pgmcp/config/issues.yaml` and `.pgmcp/config/labels.yaml`. `body` accepts pre-rendered markdown (string); generate it with `scaffold_artifact(artifact_type='issue')` before calling `create_issue`. Use the `/create-issue` slash prompt to automate the two-step scaffold → submit flow.

### Release Milestone Workflow

```
1. create_milestone title="v1.0.0" description="First stable release" due_on="2025-12-31T00:00:00Z"
2. create_issue issue_type="feature" title="Feature A" priority="medium" scope="platform" body="## Problem\n\n..." milestone="v1.0.0"
3. create_issue issue_type="feature" title="Feature B" priority="medium" scope="platform" body="## Problem\n\n..." milestone="v1.0.0"
4. (As features complete)
5. update_issue issue_number=X state=closed
6. (When all done)
7. close_milestone milestone_number=1
```

## Best Practices

### Workflow-Driven Testing and Verification

The active workflow contract and approved plan determine whether strict TDD applies.
Treat test code as first-class code and add or adapt tests only when they provide durable
evidence. Run the narrowest sufficient tests and gates during implementation. Run broad
branch- or workspace-level verification only in the phase that owns it, and reuse fresh
evidence until later changes invalidate it.

### Label Strategy

- Use labels for quick filtering (state, priority, type)
- Assign to milestones for release planning
- Link issues to PRs for traceability
- Keep labels consistent across projects

### Documentation with Tools

```
1. Use the host application's native repository search to find the related topic
2. scaffold_artifact artifact_type="design" name="new-feature-design" context='{"issue_number":"42","title":"New Feature Design","author":"Developer"}'
3. write content in created file
4. run the documentation, link, template, or parity checks required by the active phase
5. git_add_or_commit(workflow_phase="documentation", message="Add design document")
```

## Related Documentation

- **Workflow and phase tools:** [tools/project.md](tools/project.md)
- **Agent Instructions Model:** [copilot-agent-instructions-model.md](copilot-agent-instructions-model.md)
- **Quality Standards:** [../coding_standards/QUALITY_GATES.md](../coding_standards/QUALITY_GATES.md)
- **Architecture:** [../manuals/architecture.md](../manuals/architecture.md)

## Troubleshooting

### Tool Returns "GitHub token not configured"

**Fix:** Set `GITHUB_TOKEN` environment variable and restart MCP server

### Quality Gates Show "N/A" for Pyright/Mypy

**Fix:** Server was just started. Type checker needs venv initialization. Retry the command.

### CreatePRTool Fails: "Head branch not found"

**Fix:** Branch must exist on remote. Run `git_push set_upstream=true` first.

### MergePRTool Returns "Merge failed"

**Fix:** Check PR has no merge conflicts, you have merge permissions, and PR is approved.

## Roadmap

**Completed:**
- ✅ Git workflow (15 tools)
- ✅ Issue management (5 tools)
- ✅ PR management (4 tools)
- ✅ Label management (5 tools)
- ✅ Milestone management (3 tools)

**Future:**
- 🚧 Review management (approve/request changes/dismiss)
- 🚧 Project board automation (move cards, auto-assign)
- 🚧 Documentation quality tooling (structure validation, link checking)
- 🚧 Release notes generation
- 🚧 Changelog automation

## Support

**Issues or suggestions?**
- Create issue with `mcp:` label
- Search existing [MCP reference](tools/README.md)
- Check the [Agent Instructions Model](copilot-agent-instructions-model.md) for workflow-driven testing and verification policy
