<!-- docs/reference/mcp/tools/README.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-03-01 -->
# MCP Tools Reference — Navigation Index

**Status:** DEFINITIVE  
**Version:** 2.1  
**Last Updated:** 2026-03-01  

**Source:** [mcp_server/server.py](../../../../mcp_server/server.py)  
**Tests:** [tests/mcp_server/](../../../../tests/mcp_server/)  

---

## Purpose

Comprehensive navigation index for all 46 MCP server tools organized by functional category. This document serves as the entry point to the MCP Tools Reference suite, providing quick lookup and category-based navigation to detailed tool documentation.

The MCP server exposes a rich set of tools across eight functional domains: Git workflow automation, GitHub API integration, project lifecycle management, file editing, code scaffolding, quality assurance, documentation discovery, and server administration.

---

## Tool Inventory Overview

The MCP server has **46 registered tools** across 8 categories:

| Category | Tools | Documentation |
|----------|-------|---------------|
| **Git Workflow & Analysis** | 14 | [git.md](git.md) |
| **GitHub Integration** | 16 | [github.md](github.md) |
| **Project & Phase Management** | 4 | [project.md](project.md) |
| **File Editing** | 2 | [editing.md](editing.md) |
| **Scaffolding** | 1 | [scaffolding.md](scaffolding.md) |
| **Quality & Validation** | 5 | [quality.md](quality.md) |
| **Discovery & Admin** | 4 | [discovery.md](discovery.md) |
| **TOTAL** | **46** | — |

---

## Quick Reference by Category

### 1. Git Workflow & Analysis (14 tools)

Comprehensive Git automation with branch management, commit workflows, merge operations, and repository analysis.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_branch` | Create feature/bug/docs branches | `name`, `base_branch`, `branch_type` |
| `git_status` | Check working directory status | None |
| `git_add_or_commit` | Stage and commit with TDD phase prefix | `phase`, `message`, `files` |
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

**📖 See:** [git.md](git.md) for complete parameter specs, examples, and behavior details.

---

### 2. GitHub Integration (16 tools)

Full GitHub API integration for issues, pull requests, labels, and milestones. Requires `GITHUB_TOKEN` environment variable.

#### Issues (5 tools)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_issue` | Create new issue (Unicode-safe) | `title`, `body`, `labels`, `milestone`, `assignees` |
| `get_issue` | Get detailed issue information | `issue_number` |
| `list_issues` | List issues with filters | `state`, `labels` |
| `update_issue` | Update issue fields | `issue_number`, `title`, `body`, `state`, `labels`, `milestone`, `assignees` |
| `close_issue` | Close issue with optional comment | `issue_number`, `comment` |

#### Pull Requests (3 tools)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_pr` | Create new pull request | `title`, `body`, `head`, `base`, `draft` |
| `list_prs` | List PRs with filters | `state`, `head`, `base` |
| `merge_pr` | Merge PR with strategy | `pr_number`, `merge_method`, `commit_message` |

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

### 3. Project & Phase Management (4 tools)

Workflow lifecycle management with phase tracking and transition validation.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `initialize_project` | Initialize project with workflow selection | `issue_number`, `issue_title`, `workflow_name`, `parent_branch`, `custom_phases` |
| `get_project_plan` | Get project phase plan for issue | `issue_number` |
| `transition_phase` | Sequential phase transition | `branch`, `to_phase`, `human_approval` |
| `force_phase_transition` | Skip phases (requires reason + approval) | `branch`, `to_phase`, `skip_reason`, `human_approval` |

**📖 See:** [project.md](project.md) for workflow types, phase validation rules, and state tracking.

---

### 4. File Editing (2 tools)

Multi-mode file editing with quality gate integration and concurrent edit protection.

| Tool | Purpose | Status | Key Features |
|------|---------|--------|-------------|
| `safe_edit_file` | Multi-mode editing with validation | **PRIMARY** | 4 edit modes, 3 validation modes, file-level mutex |
| `create_file` | Simple file creation | **DEPRECATED** | Use `safe_edit_file` with `content` mode instead |

**📖 See:** [editing.md](editing.md) for the complete `safe_edit_file` deep-dive including anti-patterns, concurrent edit protection, and QA integration.

---

### 5. Scaffolding (1 tool)

Unified artifact generation from Jinja2 templates for code and documentation artifacts.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `scaffold_artifact` | Generate code/docs from templates | `artifact_type`, `name`, `output_path`, `context` |

**Supported Artifact Types:**
- **Code:** `dto`, `worker`, `adapter`, `tool`, `manager`, `service`
- **Documentation:** `design`, `architecture`, `tracking`, `research`, `reference`, `planning`, `guide`, `procedure`

**📖 See:** [scaffolding.md](scaffolding.md) for artifact registry structure, template resolution, and context variables.

---

### 6. Quality & Validation (5 tools)

Automated quality gates, test execution, and architectural validation.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `run_quality_gates` | Run config-driven quality gates | `scope` (`auto`/`branch`/`project`/`files`), `files` (required only with `scope="files"`) |
| `run_tests` | Run pytest — structured JSON output with traceback per failure | `path` (space-sep), `scope` (`"full"`), `markers`, `last_failed_only`, `timeout` |
| `validate_architecture` | Validate code against patterns | `scope` (all/dtos/workers/platform) |
| `validate_dto` | Validate DTO definition | `file_path` |
| `validate_template` | Validate file structure vs template | `path`, `template_type` |

**📖 See:** [quality.md](quality.md) for quality gate configuration, test markers, and validation rule details.

---

### 7. Discovery & Admin (4 tools)

Documentation search, work context aggregation, and server administration.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `search_documentation` | Semantic/fuzzy search across docs/ | `query`, `scope` |
| `get_work_context` | Aggregate context from GitHub + branch + phase | `include_closed_recent` |
| `health_check` | Server health check | None |
| `restart_server` | Hot-reload server via proxy mechanism | `reason` |

**📖 See:** [discovery.md](discovery.md) for semantic search scopes, work context structure, and restart behavior.

---

## Tool Registration Architecture

| Tier | Tools | Count | Registration Condition |
|------|-------|-------|------------------------|
| **Always Available** | Git (14), Quality (5), File Editing (2), Dev/Admin (4), Project/Phase (4), Scaffolding (1), Discovery (2) | **32** | None |
| **GitHub-Dependent** | Issues (5), PRs (3), Labels (5), Milestones (3) | **14** | Requires `GITHUB_TOKEN` environment variable |
| **TOTAL** | — | **46** | — |

**Note:** Issue management tools (5) are registered even without a token (schema-only registration). Tool calls will return errors if `GITHUB_TOKEN` is missing.

---

## Common Use Cases

### Starting a New Feature Branch

```
1. create_branch(name="feature/123-my-feature", base_branch="main")
2. git_checkout(branch="feature/123-my-feature")
3. initialize_project(issue_number=123, issue_title="My Feature", workflow_name="feature")
```

### Implementing with TDD Cycle

```
1. scaffold_artifact(artifact_type="dto", name="MyFeature", context={...})
2. git_add_or_commit(workflow_phase="tdd", sub_phase="red", message="Add failing test for MyFeature")
3. safe_edit_file(path="...", line_edits=[...])  # Implement
4. run_tests(path="tests/test_my_feature.py")
5. git_add_or_commit(workflow_phase="tdd", sub_phase="green", message="Implement MyFeature logic")
6. run_quality_gates(scope="files", files=["backend/dtos/my_feature.py"])
```

### Completing and Merging Work

```
1. transition_phase(branch="feature/123-my-feature", to_phase="integration")
2. git_push(set_upstream=True)
3. create_pr(title="...", body="...", head="feature/123-my-feature", base="main")
4. merge_pr(pr_number=42, merge_method="squash")
```

---

## Design Principles

### 1. Single Responsibility

Each tool has one clear purpose. Complex workflows compose multiple tools rather than creating monolithic tools.

### 2. Fail-Fast Validation

Tools validate inputs before execution. Invalid parameters return structured errors, not partial operations.

### 3. State Management

Phase state persists in `.st3/state.json`. Tools like `git_checkout`, `transition_phase`, and `initialize_project` modify state atomically.

### 4. Unicode Safety

All GitHub tools (issues, PRs, labels, milestones) handle Unicode content correctly. No emoji stripping or encoding issues.

### 5. Thread Safety

- Git fetch/pull use thread-safe lock files
- `safe_edit_file` uses file-level `asyncio.Lock` with 10ms timeout
- `restart_server` coordinates via proxy to avoid race conditions

### 6. Quality Gate Integration

`safe_edit_file` delegates to `ValidationService` which selects validators by file extension:
- `.py` → `PythonValidator` (Ruff, Pyright — config-driven via `.st3/quality.yaml`)
- `.md` → `MarkdownValidator` (structure, SCAFFOLD headers)
- SCAFFOLD headers → `TemplateValidator` (template conformance)

---

## Environment Variables

| Variable | Required For | Default | Description |
|----------|-------------|---------|-------------|
| `GITHUB_TOKEN` | GitHub tools (14) | None | GitHub API personal access token |
| `GITHUB_REPO` | GitHub tools (14) | Detected from git remote | Repository in `owner/repo` format |
| `ST3_WORKSPACE_ROOT` | All tools | Detected | Absolute path to workspace root |

---

## Related Documentation

- [editing.md](editing.md) — `safe_edit_file` deep-dive (4 edit modes, anti-patterns)
- [scaffolding.md](scaffolding.md) — `scaffold_artifact` and artifacts.yaml registry
- [project.md](project.md) — Workflow types and phase management
- [docs/reference/mcp/proxy_restart.md](../proxy_restart.md) — Hot-reload mechanism for `restart_server`
- [docs/reference/mcp/mcp_vision_reference.md](../mcp_vision_reference.md) — MCP server architecture and vision
- [docs/development/issue19/research.md](../../../development/issue19/research.md) — Tool inventory research

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-02-08 | Agent | Complete navigation index for 46 tools across 8 categories |
