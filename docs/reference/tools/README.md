<!-- docs/reference/tools/README.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-03-01 -->
# MCP Tools Reference — Navigation Index

**Status:** DEFINITIVE  
**Version:** 4.0  
**Last Updated:** 2026-08-22  

**Source:** [mcp_server/bootstrap.py](../../../mcp_server/bootstrap.py)  
**Tests:** [tests/mcp_server/](../../../tests/mcp_server/)  

---

## Purpose

Comprehensive navigation index for all 50 supported MCP server tools organized by functional category. This document serves as the entry point to the MCP Tools Reference suite, providing quick lookup and category-based navigation to detailed tool documentation.
The MCP server exposes tools across seven functional categories: Git workflow automation, GitHub API integration, project lifecycle management, file editing, code scaffolding, quality assurance, and discovery/server administration.

---

## Tool Inventory Overview

The MCP server supports **50 tools** across 7 categories:
| Category | Tools | Documentation |
|----------|-------|---------------|
| **Git Workflow & Analysis** | 15 | [git.md](git.md) |
| **GitHub Integration** | 17 | [github.md](github.md) |
| **Project & Phase Management** | 8 | [project.md](project.md) |
| **File Editing** | 1 | [editing.md](editing.md) |
| **Scaffolding** | 2 | [scaffolding.md](scaffolding.md) |
| **Quality & Validation** | 4 | [quality.md](quality.md) |
| **Discovery & Admin** | 3 | [discovery.md](discovery.md) |
| **TOTAL** | **50** | — |
## Quick Reference by Category

### 1. Git Workflow & Analysis (15 tools)

Comprehensive Git automation with branch management, commit workflows, merge operations, and repository analysis.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_branch` | Create configured feature/bug/docs/refactor/hotfix/chore/epic branches | `name`, `base_branch`, `branch_type` |
| `git_status` | Check working directory status | None |
| `git_add_or_commit` | Stage and commit with workflow phase prefix | `workflow_phase`, `sub_phase`, `cycle_number`, `message` |
| `git_checkout` | Switch branches (syncs phase state) | `branch` |
| `git_push` | Push to origin with upstream tracking | `set_upstream` |
| `git_merge` | Merge branch into current branch | `branch` |
| `git_delete_branch` | Delete local branch (protected safety) | `branch`, `force` |
| `git_stash` | Save/restore work in progress | `action` (push/pop/list), `message` |
| `git_restore` | Discard local changes | `files`, `source` |
| `get_parent_branch` | Detect parent via PhaseStateEngine | `branch` |
| `git_fetch` | Fetch updates from remote | `remote`, `prune` |
| `git_pull` | Pull updates with optional rebase | `remote`, `rebase` |
| `git_list_branches` | List branches with verbose info | `verbose`, `remote` |
| `git_diff_stat` | Diff statistics between branches | `target_branch`, `source_branch` |
| `check_merge` | Verify merge SHA is reachable from HEAD | `merge_sha` |

**📖 See:** [git.md](git.md) for complete parameter specs, examples, and behavior details.

---

### 2. GitHub Integration (17 tools)

Full GitHub API integration for issues, pull requests, labels, and milestones. Requires `GITHUB_TOKEN` environment variable.

#### Issues (5 tools)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_issue` | Create new issue with structured input (`issue_type`, `priority`, `scope`, `body`) | `issue_type`, `title`, `priority`, `scope`, `body` |
| `get_issue` | Get detailed issue information | `issue_number` |
| `list_issues` | List issues with filters | `state`, `labels` |
| `update_issue` | Update issue fields | `issue_number`, `title`, `body`, `state`, `labels`, `milestone`, `assignees` |
| `close_issue` | Close issue with optional comment | `issue_number`, `comment` |

#### Pull Requests (4 tools)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `submit_pr` | Atomically neutralize, commit, push, and create PR | `head`, `title`, `base`, `body`, `draft` |
| `list_prs` | List PRs with filters | `state`, `head`, `base` |
| `merge_pr` | Merge PR with strategy | `pr_number`, `merge_method`, `commit_message` |
| `get_pr` | Get detailed information about a specific PR | `pr_number` |

#### Labels (5 tools)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `list_labels` | List all repository labels | None |
| `create_label` | Create label (validates against LabelConfig) | `name`, `color`, `description` |
| `delete_label` | Delete a label | `name` |
| `add_labels` | Add labels to issue/PR | `issue_number`, `labels` |
| `remove_labels` | Remove labels from issue/PR | `issue_number`, `labels` |

#### Milestones (3 tools)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `list_milestones` | List milestones with state filter | `state` |
| `create_milestone` | Create milestone | `title`, `description`, `due_on` |
| `close_milestone` | Close a milestone | `milestone_number` |

**📖 See:** [github.md](github.md) for GitHub-specific behaviors, error handling, and Unicode support.

---

### 3. Project & Phase Management (8 tools)

Workflow lifecycle management with phase tracking and transition validation.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `initialize_project` | Initialize project with workflow selection | `issue_number`, `issue_title`, `workflow_name`, `parent_branch`, `custom_phases` |
| `get_project_plan` | Get project phase plan for issue | `issue_number` |
| `save_planning_deliverables` | Save planning deliverables for issue | `issue_number` |
| `update_planning_deliverables` | Update/merge planning deliverables | `issue_number` |
| `transition_phase` | Sequential phase transition | `branch`, `to_phase`, `human_approval_message` |
| `force_phase_transition` | Skip phases (requires reason + approval) | `branch`, `to_phase`, `skip_reason`, `human_approval_message` |
| `transition_cycle` | Sequential TDD cycle transition | `to_cycle` |
| `force_cycle_transition` | Skip to cycle (requires reason + approval) | `to_cycle`, `skip_reason`, `human_approval_message` |

**📖 See:** [project.md](project.md) for workflow types, phase validation rules, and state tracking.

---

### 4. File Editing (1 tool)

Multi-mode file editing with quality gate integration and concurrent edit protection.

| Tool | Purpose | Status | Key Features |
|------|---------|--------|-------------|
| `safe_edit_file` | Frictionless 4-operation editing with validation | **PRIMARY** | 4 operations (replace, append, rewrite, pattern_replace), must_exist=True governance, fuzzy diagnostics |

**📖 See:** [editing.md](editing.md) for the complete `safe_edit_file` deep-dive including anti-patterns, concurrent edit protection, and QA integration.

---

### 5. Scaffolding (2 tools)

Unified artifact generation from Jinja2 templates for code and documentation artifacts.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `scaffold_artifact` | Generate code/docs from templates | `artifact_type`, `name`, `output_path`, `context` |
| `scaffold_schema` | Return JSON Schema for artifact type context | `artifact_type` |

**Supported Artifact Types:**
- **Code:** `dto`, `typescript_dto`, `worker`, `adapter`, `tool`, `manager`, `service`
- **Documentation:** `design`, `architecture`, `tracking`, `research`, `reference`, `planning`, `guide`, `procedure`
**📖 See:** [scaffolding.md](scaffolding.md) for artifact registry structure, template resolution, and context variables.

---

### 6. Quality & Validation (4 tools)

Automated quality gates, test execution, and architectural validation.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `auto_fix` | Apply configured mechanical quality fixes | None |
| `run_quality_gates` | Run config-driven quality gates | `scope` (`auto`/`branch`/`project`/`files`), `files` (required only with `scope="files"`) |
| `run_tests` | Run pytest — outputs presented human-readable text pointing to the DTO cached in the MCP Resource cache | `path` (space-sep), `scope` (`"full"`), `markers`, `last_failed_only`, `timeout`, `coverage`, `verbose`, `collect_only` |
| `validate_template` | Validate file structure vs template | `path`, `template_type` |

**📖 See:** [quality.md](quality.md) for quality gate configuration, test markers, and validation rule details.

---

### 7. Discovery & Admin (3 tools)

Work context aggregation and server administration.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `get_work_context` | Aggregate branch + workflow context | None |
| `health_check` | Server health check | None |
| `restart_server` | Hot-reload server via proxy mechanism | `reason` |

**📖 See:** [discovery.md](discovery.md) for work context structure, health checks, and restart behavior.

---

## Tool Registration Architecture

| Tier | Tools | Count | Registration Condition |
|---|---|---:|---|
| **Core active set** | Git (15), Quality (4), File Editing (1), Project/Phase (8), Scaffolding (2), Discovery & Admin (3) | **33** | Always registered |
| **Issue tools** | Issues (5) | **5** | Registered without a token so their schemas remain available; execution still requires GitHub credentials |
| **Credential-dependent set** | PRs (4), Labels (5), Milestones (3) | **12** | Active only with `GITHUB_TOKEN` |
| **Active without token** | Core + Issues | **38** | — |
| **Active with token** | Complete supported catalog | **50** | — |

The complete supported catalog is derived from the constructed tool instances at runtime
and always contains all 50 name/output-model contracts. Startup validates
`presentation.yaml` against that complete catalog, while settings select the smaller
active subset exposed to the client.

---

## Common Use Cases

### Starting a New Feature Branch

```
1. create_branch(name="feature/123-my-feature", base_branch="main")
2. git_checkout(branch="feature/123-my-feature")
3. initialize_project(issue_number=123, issue_title="My Feature", workflow_name="feature")
4. get_work_context()
5. get_project_plan(issue_number=123)
```

### Implementing with TDD Cycle

```
1. scaffold_artifact(artifact_type="dto", name="MyFeature", context={...})
2. git_add_or_commit(workflow_phase="implementation", sub_phase="red", cycle_number=1, message="Add failing test for MyFeature")
3. safe_edit_file(path="...", operation={"op": "replace", "target_content": "...", "replacement": "..."})  # Implement
4. run_tests(path="tests/test_my_feature.py")
5. git_add_or_commit(workflow_phase="implementation", sub_phase="green", cycle_number=1, message="Implement MyFeature logic")
6. run_quality_gates(scope="files", files=["backend/dtos/my_feature.py"])
```

### Completing and Merging Work

```
1. transition_phase(branch="feature/123-my-feature", to_phase="validation")
2. transition_phase(branch="feature/123-my-feature", to_phase="ready")
3. submit_pr(title="...", body="...", head="feature/123-my-feature")  # base auto-detected from state.json
4. (after human approval)
5. merge_pr(pr_number=42, merge_method="merge")
```

---

## Design Principles

Each tool has one clear purpose. Complex workflows compose multiple tools rather than creating monolithic tools.

### 1. Unified DTO & MCP Resource Caching Architecture

All registered tools implement the `ITool` interface and return a pure, frozen Pydantic
DTO, decoupled from protocol-level concerns. The server publishes the complete DTO as an
MCP Resource (`pgmcp://cache/runs/{run_id}`), then renders a bounded Markdown projection
from `presentation.yaml`.

The projection can include configured scalar fields, bounded scalar sequences, nested
ordered collections, enum-selected guidance, and operation notes. Collection item limits
preserve DTO order, and one final limiter keeps the complete composed text at or below
8,000 UTF-8 bytes while retaining the cache reference when publication succeeded.

Use the inline response for routine decisions. Read the cached DTO for completeness,
fields deliberately kept cache-only, or verbose diagnostics. Validation-input failures
may additionally include an embedded `schema://validation` resource. See
[Presentation Architecture](../presentation_architecture.md) for the complete contract.

### 2. Fail-Fast Validation

Tools validate inputs before execution. Invalid parameters return structured errors, not partial operations.

### 3. State Management

Phase state persists in `.pgmcp/state.json`. Tools like `git_checkout`, `transition_phase`, and `initialize_project` modify state atomically.

### 4. Unicode Safety

All GitHub tools (issues, PRs, labels, milestones) handle Unicode content correctly. No emoji stripping or encoding issues.

### 5. Thread Safety

- Git fetch/pull run asynchronously in worker threads to prevent stdio deadlocks
- `safe_edit_file` uses file-level `asyncio.Lock` with 10ms timeout
- `restart_server` coordinates via proxy to avoid race conditions

### 6. Quality Gate Integration

`safe_edit_file` delegates to `ValidationService` which selects validators by file extension:
- `.py` → `PythonValidator` (Ruff, Pyright — config-driven via `.pgmcp/config/quality.yaml`)
- `.md` → `MarkdownValidator` (structure, SCAFFOLD headers)
- SCAFFOLD headers → `TemplateValidator` (template conformance)

---

## Environment Variables

| Variable | Required For | Default | Description |
|----------|-------------|---------|-------------|
| `GITHUB_TOKEN` | GitHub tools (14) | None | GitHub API personal access token |
| `GITHUB_REPO` | GitHub tools (14) | Detected from git remote | Repository in `owner/repo` format |
| `PGMCP_WORKSPACE_ROOT` | All tools | Detected | Absolute path to workspace root |

---

## Related Documentation

- [editing.md](editing.md) — `safe_edit_file` deep-dive (4 operations: replace, append, rewrite, pattern_replace)
- [scaffolding.md](scaffolding.md) — `scaffold_artifact` and `scaffold_schema` and the modular configuration registry
- [project.md](project.md) — Workflow types and phase management
- [docs/reference/mcp/proxy_restart.md](../proxy_restart.md) — Hot-reload mechanism for `restart_server`
- [docs/reference/mcp/mcp_vision_reference.md](../mcp_vision_reference.md) — MCP server architecture and vision
- [docs/development/archive/issue268/validation.md](../../development/archive/issue268/validation.md) — Historical validation evidence for the delivered `get_work_context` contract and context-loaded gate

---

## Version History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 4.0 | 2026-08-22 | Agent | Document runtime supported/active catalog and bounded presentation/cache contract |
| 3.1 | 2026-07-16 | Agent | Updated scaffolding reference to modular configurations and added typescript_dto type. |
| 3.0 | 2026-06-15 | Agent | Document ITool DTO and MCP Resource Caching migration (#402) |
| 2.2 | 2026-05-23 | Agent | Update discovery/index guidance for the delivered `get_work_context` contract and startup flow |
| 2.1 | 2026-04-10 | Agent | Fix tool counts (50 total, Project/Phase 8, GitHub-Dependent 16); fix stale params and merge_method |
