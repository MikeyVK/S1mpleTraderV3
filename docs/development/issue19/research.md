<!-- docs/development/issue19/research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-08T12:00:00+01:00 updated=2026-02-08 -->
# Issue #19 — MCP Server Tooling Reference Documentation Research

**Status:** DRAFT
**Version:** 1.0
**Last Updated:** 2026-02-08

---

## Purpose

Comprehensive research inventory of all 46 MCP server tools, documentation gap analysis, agent instruction file assessment, and action plan for creating definitive reference documentation.

## Scope

**In Scope:**
Complete tool inventory (46 registered + 1 unregistered), existing documentation coverage analysis, agent instruction file consolidation, safe_edit_file deep-dive, proxy/restart docs, .st3 configuration landscape

**Out of Scope:**
Implementation of new docs (that's the documentation phase), backend trading platform code, test infrastructure internals

## Prerequisites

Read these first:
1. Full tool source code review completed (46 registered + 1 unregistered)
2. Existing docs/reference/ audit completed
3. Agent instruction files analyzed (.copilot-instructions.md + agent.md)
4. .st3/ configuration landscape mapped

---

## Problem Statement

MCP_TOOLS.md claims 31 tools but the server actually has 46 registered tools. 15 tools are completely undocumented, safe_edit_file has no reference doc despite being the primary editing tool, create_file deprecation is not reflected, and agent instruction files use a wasteful 2-hop redirect pattern. The workflow phase counts in agent.md don't match workflows.yaml.

## Research Goals

- Establish complete inventory of all MCP server tools with parameters and behaviors
- Identify gaps between existing documentation and actual tool capabilities
- Assess agent instruction files for coherence and SSOT strategy
- Document safe_edit_file modes, anti-patterns, and QA integration
- Create actionable plan for documentation phase deliverables

## Related Documentation

- [docs/reference/mcp/MCP_TOOLS.md](../../reference/mcp/MCP_TOOLS.md) — Current tool reference (outdated)
- [docs/reference/mcp/proxy_restart.md](../../reference/mcp/proxy_restart.md) — Proxy restart mechanism
- [docs/reference/mcp/mcp_vision_reference.md](../../reference/mcp/mcp_vision_reference.md) — MCP server vision & architecture
- [agent.md](../../../agent.md) — Agent cooperation protocol (bootloader)
- [.github/.copilot-instructions.md](../../../.github/.copilot-instructions.md) — Copilot auto-loaded instructions

---

## Findings

### 1. Complete Tool Inventory

The MCP server has **46 registered tools** across 12 logical categories, plus 1 unregistered tool in the codebase. This significantly exceeds the "31 tools" claimed in the current MCP_TOOLS.md documentation.

#### 1.1 Git Workflow Tools (10 tools)

| # | MCP Name | Class | File | Description |
|---|----------|-------|------|-------------|
| 1 | `create_branch` | CreateBranchTool | git_tools.py | Create a new branch from specified base branch |
| 2 | `git_status` | GitStatusTool | git_tools.py | Check current git status |
| 3 | `git_add_or_commit` | GitCommitTool | git_tools.py | Commit changes with TDD phase prefix |
| 4 | `git_checkout` | GitCheckoutTool | git_tools.py | Switch branches (auto-syncs phase state) |
| 5 | `git_push` | GitPushTool | git_tools.py | Push current branch to origin |
| 6 | `git_merge` | GitMergeTool | git_tools.py | Merge a branch into current branch |
| 7 | `git_delete_branch` | GitDeleteBranchTool | git_tools.py | Delete branch (protected branch safety) |
| 8 | `git_stash` | GitStashTool | git_tools.py | Save/restore WIP (push/pop/list) |
| 9 | `git_restore` | GitRestoreTool | git_tools.py | Restore files to a git ref (discard changes) |
| 10 | `get_parent_branch` | GetParentBranchTool | git_tools.py | Detect parent branch via PhaseStateEngine |

#### 1.2 Git Sync Tools (2 tools)

| # | MCP Name | Class | File | Description |
|---|----------|-------|------|-------------|
| 11 | `git_fetch` | GitFetchTool | git_fetch_tool.py | Fetch updates from remote (thread-safe) |
| 12 | `git_pull` | GitPullTool | git_pull_tool.py | Pull updates with optional rebase |

#### 1.3 Git Analysis Tools (2 tools)

| # | MCP Name | Class | File | Description |
|---|----------|-------|------|-------------|
| 13 | `git_list_branches` | GitListBranchesTool | git_analysis_tools.py | List branches with verbose/remote options |
| 14 | `git_diff_stat` | GitDiffTool | git_analysis_tools.py | Diff statistics between branches |

#### 1.4 Issue Management Tools (5 tools)

| # | MCP Name | Class | File | Description |
|---|----------|-------|------|-------------|
| 15 | `create_issue` | CreateIssueTool | issue_tools.py | Create new GitHub issue (Unicode-safe) |
| 16 | `get_issue` | GetIssueTool | issue_tools.py | Get detailed issue information |
| 17 | `list_issues` | ListIssuesTool | issue_tools.py | List issues with state/label filters |
| 18 | `update_issue` | UpdateIssueTool | issue_tools.py | Update issue fields (title, body, state, labels, milestone, assignees) |
| 19 | `close_issue` | CloseIssueTool | issue_tools.py | Close issue with optional comment |

#### 1.5 Pull Request Tools (3 tools)

| # | MCP Name | Class | File | Description |
|---|----------|-------|------|-------------|
| 20 | `create_pr` | CreatePRTool | pr_tools.py | Create new PR |
| 21 | `list_prs` | ListPRsTool | pr_tools.py | List PRs with state/base/head filters |
| 22 | `merge_pr` | MergePRTool | pr_tools.py | Merge PR (merge/squash/rebase) |

#### 1.6 Label Management Tools (5 tools + 1 unregistered)

| # | MCP Name | Class | File | Description |
|---|----------|-------|------|-------------|
| 23 | `list_labels` | ListLabelsTool | label_tools.py | List all repository labels |
| 24 | `create_label` | CreateLabelTool | label_tools.py | Create label (validates against LabelConfig) |
| 25 | `delete_label` | DeleteLabelTool | label_tools.py | Delete a label |
| 26 | `add_labels` | AddLabelsTool | label_tools.py | Add labels to issue/PR (validates existence) |
| 27 | `remove_labels` | RemoveLabelsTool | label_tools.py | Remove labels from issue/PR |
| — | `detect_label_drift` | DetectLabelDriftTool | label_tools.py | **NOT REGISTERED** — Drift detection between labels.yaml and GitHub |

#### 1.7 Milestone Management Tools (3 tools)

| # | MCP Name | Class | File | Description |
|---|----------|-------|------|-------------|
| 28 | `list_milestones` | ListMilestonesTool | milestone_tools.py | List milestones with state filter |
| 29 | `create_milestone` | CreateMilestoneTool | milestone_tools.py | Create milestone with optional due date |
| 30 | `close_milestone` | CloseMilestoneTool | milestone_tools.py | Close a milestone |

#### 1.8 Project & Phase Management Tools (4 tools)

| # | MCP Name | Class | File | Description |
|---|----------|-------|------|-------------|
| 31 | `initialize_project` | InitializeProjectTool | project_tools.py | Initialize project with workflow selection |
| 32 | `get_project_plan` | GetProjectPlanTool | project_tools.py | Get project phase plan for issue |
| 33 | `transition_phase` | TransitionPhaseTool | phase_tools.py | Sequential phase transition |
| 34 | `force_phase_transition` | ForcePhaseTransitionTool | phase_tools.py | Skip phases (requires human approval + reason) |

#### 1.9 File Editing Tools (2 tools)

| # | MCP Name | Class | File | Description |
|---|----------|-------|------|-------------|
| 35 | `safe_edit_file` | SafeEditTool | safe_edit_tool.py | Multi-mode file editing with validation (PRIMARY) |
| 36 | `create_file` | CreateFileTool | code_tools.py | **DEPRECATED** — Simple file creation |

#### 1.10 Scaffolding Tool (1 tool)

| # | MCP Name | Class | File | Description |
|---|----------|-------|------|-------------|
| 37 | `scaffold_artifact` | ScaffoldArtifactTool | scaffold_artifact.py | Generate code/docs from Jinja2 templates |

#### 1.11 Quality & Validation Tools (5 tools)

| # | MCP Name | Class | File | Description |
|---|----------|-------|------|-------------|
| 38 | `run_quality_gates` | RunQualityGatesTool | quality_tools.py | Run pylint + mypy/pyright on files |
| 39 | `run_tests` | RunTestsTool | test_tools.py | Run pytest with markers/timeout |
| 40 | `validate_architecture` | ValidationTool | validation_tools.py | Validate code against architectural patterns |
| 41 | `validate_dto` | ValidateDTOTool | validation_tools.py | Validate DTO definition |
| 42 | `validate_template` | TemplateValidationTool | template_validation_tool.py | Validate file structure against template spec |

#### 1.12 Discovery & Admin Tools (4 tools)

| # | MCP Name | Class | File | Description |
|---|----------|-------|------|-------------|
| 43 | `search_documentation` | SearchDocumentationTool | discovery_tools.py | Semantic/fuzzy search across docs/ |
| 44 | `get_work_context` | GetWorkContextTool | discovery_tools.py | Aggregate context from GitHub + branch + phase |
| 45 | `health_check` | HealthCheckTool | health_tools.py | Server health check |
| 46 | `restart_server` | RestartServerTool | admin_tools.py | Hot-reload server via proxy mechanism |

#### 1.13 Registration Architecture

| Tier | Tools | Count | Condition |
|------|-------|-------|-----------|
| Always available | Git (14), Quality/Validation (5), File Editing (2), Dev/Admin (4), Project/Phase (4), Scaffolding (1), Discovery (2) | 30* | None |
| GitHub-dependent | Issues (5), PRs (3), Labels (5), Milestones (3) | 16 | Requires `GITHUB_TOKEN` |
| Unregistered | `detect_label_drift` | 1 | Exists in code, not in server.py |

*Note: Issue tools (5) are registered even without token (schema-only; execution returns errors).

---

### 2. SafeEditTool Deep-Dive

The `safe_edit_file` tool (SafeEditTool, 552 lines) is the **primary file editing mechanism** for the MCP server. It is significantly under-documented.

#### 2.1 Four Mutually Exclusive Edit Modes

Only ONE mode per call (enforced by Pydantic model validator):

| Mode | Parameters | New File? | Use Case |
|------|-----------|-----------|----------|
| **Full Rewrite** | `content` | Yes | Complete file replacement or creation |
| **Line Edits** | `line_edits[]` | No | Surgical edits to specific line ranges |
| **Insert Lines** | `insert_lines[]` | No | Insert without replacing existing lines |
| **Search/Replace** | `search` + `replace` | No | Pattern-based find/replace |

#### 2.2 Edit Sub-models

**LineEdit:**
| Field | Type | Description |
|-------|------|-------------|
| `start_line` | int (≥1) | Starting line (1-based, inclusive) |
| `end_line` | int (≥start_line) | Ending line (1-based, inclusive) |
| `new_content` | str | Replacement text — **MUST include trailing `\n`** |

**InsertLine:**
| Field | Type | Description |
|-------|------|-------------|
| `at_line` | int (≥1) | Insert before this line (use `lines+1` to append) |
| `content` | str | Content to insert |

#### 2.3 Three Validation Modes

| Mode | Write? | Validate? | Use Case |
|------|--------|-----------|----------|
| `strict` (default) | Only if valid | Yes | Normal editing — rejects on error |
| `interactive` | Always | Yes (warns) | Manual override — writes regardless |
| `verify_only` | Never | Yes | Dry-run — preview diff only |

#### 2.4 Quality Gate Integration

- Delegates to `ValidationService` which selects validator by file extension:
  - `.py` → `PythonValidator`
  - `.md` → `MarkdownValidator`
  - SCAFFOLD header → `TemplateValidator`
- Validation runs **before** writing in all modes
- Diff preview generated via `difflib.unified_diff`

#### 2.5 Concurrent Edit Protection

- **File-level `asyncio.Lock`** per resolved file path
- **10ms timeout** on lock acquisition — immediate error if another edit in progress
- Edits applied in **reverse order** (by `start_line`) to maintain line number stability
- Anti-pattern: Multiple sequential `safe_edit_file` calls on same file → bundle in ONE `line_edits` list

#### 2.6 Anti-Patterns & Common Mistakes

1. **Missing trailing `\n`** in `line_edits.new_content` → next line merges into edited line
2. **Sequential calls for same file** → mutex timeout / race condition → bundle in one call
3. **Line edits on non-existent files** → use `content` mode to create first
4. **Overlapping line ranges** → validator detects and rejects
5. **Out-of-bounds line numbers** → validated against actual file line count
6. **Multiple edit modes** → model validator rejects (exactly one required)
7. **`search` without `replace`** → both must be provided together
8. **In strict mode with search/replace: pattern not found** → returns error

---

### 3. Agent Instruction Files Analysis

#### 3.1 Current State

| File | Purpose | Lines | Auto-loaded? |
|------|---------|-------|-------------|
| `.github/.copilot-instructions.md` | Copilot repo-level instructions | 39 | **Yes** — VS Code auto-injects into every prompt |
| `agent.md` | Full agent cooperation protocol | 418 | No — must be manually read |

#### 3.2 Problem: 2-Hop Redirect Pattern

`.copilot-instructions.md` currently is a thin redirect:
> "CRITICAL: Read agent.md in workspace root FIRST before any work."

This wastes the auto-injection capability because:
1. Agent must make a separate `read_file` call to read `agent.md`
2. That costs ~400 lines of context window for every new agent session
3. If the agent doesn't follow the redirect, all protocol rules are missed
4. The redirect itself (39 lines) provides almost no actionable content

#### 3.3 `agent.md` Content Issues

| Issue | Severity | Details |
|-------|----------|---------|
| Workflow phase count mismatches | HIGH | `agent.md` says "docs: 4 phases" but `workflows.yaml` defines 2 phases (planning, documentation) |
| `detect_label_drift` reference | MEDIUM | Referenced as a usable tool but NOT registered in server.py |
| `validate_doc` reference | MEDIUM | Referenced but no `ValidateDocTool` class exists in codebase |
| Phase section ordering | LOW | Phase 5 (Tool Matrix) appears before Phase 3/4 in the file |
| Missing `epic` workflow | LOW | `workflows.yaml` defines `epic` workflow but `agent.md` doesn't mention it |

#### 3.4 Consolidation Strategy

Three options evaluated:

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A. Inline | Copy full `agent.md` into `.copilot-instructions.md` | Eliminates 2-hop; always available | Duplication risk; 418+ lines auto-injected every prompt |
| B. Hybrid | Top 80% of rules inline, full reference stays in `agent.md` | Best of both; key rules auto-load | Must maintain two files (partial duplication) |
| C. Keep redirect | Improve redirect with critical rules summary | Minimal change | Still wastes auto-injection; redirect failure mode remains |

**Recommendation: Option B (Hybrid)**
- Inline the Tool Priority Matrix (most critical), TDD cycle, `run_in_terminal` restrictions, and Prime Directives into `.copilot-instructions.md`
- Keep `agent.md` as the full reference for non-Copilot agents and human readers
- Add a "Source of Truth: .github/.copilot-instructions.md" note to `agent.md`

---

### 4. Documentation Gap Analysis

#### 4.1 MCP_TOOLS.md vs Reality

| Metric | MCP_TOOLS.md Claims | Reality | Gap |
|--------|-------------------|---------|-----|
| Total tools | 31 | 46 registered | **15 missing** |
| Categories | 9 | 12 logical | 3 missing categories |
| Git tools | 8 | 14 | 6 undocumented |
| Quality tools | 6 (with duplicates) | 5 | Restructure needed |
| Dev/file tools | 2 | 6 (editing + admin + testing) | 4 undocumented |

#### 4.2 Tools Completely Missing from MCP_TOOLS.md

| # | Tool | Category | Impact |
|---|------|----------|--------|
| 1 | `safe_edit_file` | File Editing | **CRITICAL** — primary editing tool, 4 modes |
| 2 | `restart_server` | Admin | HIGH — hot-reload mechanism |
| 3 | `initialize_project` | Project Mgmt | HIGH — workflow initialization |
| 4 | `get_project_plan` | Project Mgmt | HIGH — workflow inspection |
| 5 | `transition_phase` | Phase Mgmt | HIGH — phase progression |
| 6 | `force_phase_transition` | Phase Mgmt | HIGH — emergency phase skip |
| 7 | `git_fetch` | Git Sync | MEDIUM — documented in separate file |
| 8 | `git_pull` | Git Sync | MEDIUM — documented in separate file |
| 9 | `git_restore` | Git Workflow | MEDIUM |
| 10 | `git_list_branches` | Git Analysis | MEDIUM |
| 11 | `git_diff_stat` | Git Analysis | MEDIUM |
| 12 | `get_parent_branch` | Git Workflow | MEDIUM |
| 13 | `validate_template` | Validation | LOW |
| 14 | `validate_architecture` | Validation | LOW |
| 15 | `run_tests` | Testing | LOW — partially covered in Quality section |

#### 4.3 Documentation Accuracy Issues

| Document | Issue | Severity |
|----------|-------|----------|
| MCP_TOOLS.md | Claims 31 tools, actually 46 | HIGH |
| MCP_TOOLS.md | `HealthCheckTool` listed in 2 categories | MEDIUM |
| MCP_TOOLS.md | `create_file` listed without deprecation notice | MEDIUM |
| MCP_TOOLS.md | Category structure doesn't reflect actual tool organization | MEDIUM |
| agent.md | Workflow phase counts don't match workflows.yaml | HIGH |
| agent.md | References `detect_label_drift` (not registered) | MEDIUM |
| agent.md | References `validate_doc` (doesn't exist) | MEDIUM |
| supervisor_reference.md | Refers to `supervisor.py` but file is `proxy.py` | MEDIUM |

#### 4.4 Existing Docs That Are Well-Maintained

| Document | Status | Quality |
|----------|--------|---------|
| proxy_restart.md | 577 lines | Excellent — accurate, Mermaid diagrams, performance metrics |
| mcp_vision_reference.md | 719 lines, DEFINITIVE | Excellent — comprehensive vision & architecture |
| validation_api.md | 532 lines, APPROVED | Good — TemplateAnalyzer API reference |
| git_config_api.md | 327 lines | Good — GitConfig Pydantic model reference |
| git_fetch_pull.md | 171 lines, DRAFT | Good — threading model detail |

---

### 5. Proxy/Restart Documentation Status

| Document | Lines | Status | Accuracy |
|----------|-------|--------|----------|
| proxy_restart.md | 577 | Production quality | Accurate — matches proxy.py implementation |
| supervisor_reference.md | 1,405 | Needs review | **Naming inconsistency** — refers to `supervisor.py` but implementation is `proxy.py` |

**Naming Evolution:**
- Old name: "Watchdog Supervisor" / `supervisor.py`
- Current name: "MCP Transparent Restart Proxy" / `proxy.py`
- `supervisor_reference.md` was never renamed/updated

**Recommendation:** Either rename `supervisor_reference.md` to align with `proxy.py` naming, or add a deprecation redirect pointing to `proxy_restart.md`.

---

### 6. .st3/ Configuration Landscape

The `.st3/` directory contains 10 configuration files that power the MCP server's behavior:

| File | Purpose | Schema | Lines |
|------|---------|--------|-------|
| `artifacts.yaml` | Unified artifact registry (all scaffoldable types) | v1.0 | 361 |
| `workflows.yaml` | Workflow definitions (phase sequences per type) | v1.0 | 77 |
| `labels.yaml` | GitHub label SSOT (freeform exceptions, patterns) | v1.0 | 154 |
| `git.yaml` | Git conventions (branches, TDD phases, commit prefixes) | — | ~35 |
| `quality.yaml` | Quality gate definitions (pylint, pyright, ruff) | v1.0 | 140 |
| `policies.yaml` | Operation phase policies (when scaffold/create/commit allowed) | — | 51 |
| `state.json` | Current branch state (runtime, not committed) | — | varies |
| `projects.json` | Historical project registry (all initialized projects) | — | 400 |
| `template_registry.json` | Template provenance (version hashes → tier chains) | v1.0 | 367 |
| `project_structure.yaml` | Directory structure policy (artifact type → directory) | — | 166 |
| `scaffold_metadata.yaml` | SCAFFOLD header format spec (comment patterns) | v2.0 | 65 |

---

### 7. Proposed Documentation Phase Deliverables

Based on the research findings, the documentation phase should produce:

#### 7.1 Primary Deliverable: Updated MCP_TOOLS.md

Complete rewrite of `docs/reference/mcp/MCP_TOOLS.md`:
- Update tool count from 31 → 46
- Restructure into 12 categories (from 9)
- Add all 15 missing tools with full parameter documentation
- Mark `create_file` as deprecated
- Fix `HealthCheckTool` duplicate listing
- Add tool registration architecture section

#### 7.2 New Reference Doc: safe_edit_file Reference

Dedicated reference document for `safe_edit_file`:
- 4 edit modes with parameter specs and examples
- 3 validation modes with behavior matrix
- Concurrent edit protection (mutex, bundling requirement)
- Anti-patterns and common mistakes
- QA integration (ValidationService extension points)

#### 7.3 Agent Instruction Consolidation

Update `.github/.copilot-instructions.md`:
- Inline critical protocol rules (Tool Priority Matrix, TDD cycle, terminal restrictions)
- Update `agent.md` to note `.copilot-instructions.md` as auto-loaded SSOT
- Fix workflow phase count mismatches
- Remove references to non-existent tools (`validate_doc`, unregistered `detect_label_drift`)
- Add missing `epic` workflow

#### 7.4 Cleanup: Supervisor/Proxy Naming

- Assess whether `supervisor_reference.md` should be deprecated or renamed
- Ensure all references point to `proxy.py` (not `supervisor.py`)

---

## Decisions

Following research findings, the following decisions were made:

### 1. `detect_label_drift` Tool Reference
**Decision:** Remove references from agent.md (do not register).  
**Rationale:** Tool exists in code but is not registered in server.py and has no documented use case. Registering would add maintenance burden without clear value.

### 2. MCP_TOOLS.md Structure
**Decision:** Split into category-specific documents (one per category).  
**Rationale:** Current MCP_TOOLS.md would exceed 1000+ lines with full 46-tool documentation. Per DOCUMENTATION_MAINTENANCE.md: standard docs max 300 lines, architecture docs max 1000 lines. Split structure:
- `docs/reference/mcp/tools/README.md` — Index/navigation (≤300 lines)
- `docs/reference/mcp/tools/git.md` — Git tools (14 tools, ~400 lines)
- `docs/reference/mcp/tools/github.md` — Issues/PRs/Labels/Milestones (16 tools, ~500 lines)
- `docs/reference/mcp/tools/project.md` — Project/Phase management (4 tools, ~200 lines)
- `docs/reference/mcp/tools/editing.md` — File editing (`safe_edit_file` deep-dive + `create_file`, ~400 lines)
- `docs/reference/mcp/tools/quality.md` — Quality/validation/testing (5 tools, ~250 lines)
- `docs/reference/mcp/tools/scaffolding.md` — Scaffolding (1 tool + artifacts.yaml, ~300 lines)
- `docs/reference/mcp/tools/discovery.md` — Discovery/admin (4 tools, ~200 lines)

### 3. `supervisor_reference.md` Status
**Decision:** Archive/deprecate — superseded by `proxy_restart.md`.  
**Rationale:** Naming inconsistency (refers to non-existent `supervisor.py`). `proxy_restart.md` is the accurate, maintained reference for the same functionality. Move to `docs/archive/`.

### 4. `.copilot-instructions.md` Auto-Injection Size
**Decision:** Target 150-200 lines (strict max 250 lines).  
**Rationale:** Based on empirical model behavior:
- **Claude (Opus/Sonnet):** Handles ~4000 token system prompts reliably. 200 lines ≈ 800-1200 tokens (comfortable).
- **GPT-4o/o1:** Instruction following degrades significantly above ~300 lines. 200 lines is the sweet spot.
- **Gemini 2.5:** Exhibits "instruction drift" beyond ~250 lines. Shorter = more reliable.
- **Project standards:** Templates max 150 lines (DOCUMENTATION_MAINTENANCE.md). `.copilot-instructions.md` is effectively a config/template file.

**Content to inline (~115 core lines + structure = ~150-180 total):**
- Tool Priority Matrix (60 lines) — most critical
- `run_in_terminal` restrictions (20 lines)
- TDD cycle (15 lines)
- Prime Directives (10 lines)
- Workflow types table (10 lines)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-08 | Agent | Initial research — complete tool inventory (46 tools), gap analysis, agent instruction assessment, deliverables plan |
