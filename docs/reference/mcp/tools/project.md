<!-- docs/reference/mcp/tools/project.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-02-08 -->
# Project & Phase Management Tools

**Status:** DEFINITIVE  
**Version:** 2.0  
**Last Updated:** 2026-02-08  

**Source:** [mcp_server/tools/project_tools.py](../../../../mcp_server/tools/project_tools.py), [phase_tools.py](../../../../mcp_server/tools/phase_tools.py)  
**Tests:** [tests/unit/test_project_tools.py](../../../../tests/unit/test_project_tools.py), [tests/unit/test_phase_tools.py](../../../../tests/unit/test_phase_tools.py)  

---

## Purpose

Complete reference documentation for project lifecycle and phase management tools. These 4 tools provide workflow initialization, phase plan inspection, sequential phase transitions, and emergency phase skipping with human approval.

Phase state persists in [.st3/state.json](../../../../.st3/state.json) and is synchronized with git branch operations.

---

## Overview

The MCP server provides **4 project/phase tools**:

| Tool | Purpose | Key Feature |
|------|---------|-------------|
| `initialize_project` | Initialize project with workflow selection | Human selects workflow type |
| `get_project_plan` | Inspect project phase plan | Read-only phase inspection |
| `transition_phase` | Sequential phase transition | Strict validation |
| `force_phase_transition` | Skip phases (emergency) | Requires reason + human approval |

All tools interact with:
- **PhaseStateEngine:** Phase state tracking and validation
- **[.st3/workflows.yaml](../../../../.st3/workflows.yaml):** Workflow definitions (feature, bug, docs, refactor, hotfix, epic, custom)
- **[.st3/state.json](../../../../.st3/state.json):** Current branch state (runtime, not committed)
- **[.st3/projects.json](../../../../.st3/projects.json):** Historical project registry

---

## API Reference

### initialize_project

**MCP Name:** `initialize_project`  
**Class:** `InitializeProjectTool`  
**File:** [mcp_server/tools/project_tools.py](../../../../mcp_server/tools/project_tools.py)

Initialize project with phase plan selection. Human selects workflow_name (feature/bug/docs/refactor/hotfix/epic/custom) to generate project-specific phase plan.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_number` | `int` | **Yes** | GitHub issue number |
| `issue_title` | `str` | **Yes** | Issue title |
| `workflow_name` | `str` | **Yes** | Workflow from workflows.yaml: `"feature"`, `"bug"`, `"docs"`, `"refactor"`, `"hotfix"`, `"epic"`, `"custom"` |
| `parent_branch` | `str` | No | Parent branch this feature/bug branches from (auto-detected from git reflog if not provided) |
| `custom_phases` | `list[str]` | **Conditional** | Custom phase list (REQUIRED if `workflow_name="custom"`) |
| `skip_reason` | `str` | No | Reason for custom phases (audit trail) |

#### Workflow Types

| Workflow | Phases | Use Case |
|----------|--------|----------|
| `feature` | 7 phases | New features (planning → research → red → green → refactor → documentation → merge-prep) |
| `bug` | 6 phases | Bug fixes (investigation → red → green → refactor → documentation → merge-prep) |
| `docs` | 2 phases | Documentation only (planning → documentation) |
| `refactor` | 5 phases | Code refactoring (planning → research → refactor → documentation → merge-prep) |
| `hotfix` | 3 phases | Critical fixes (red → green → merge-prep) |
| `epic` | 2 phases | Epic coordination (planning → tracking) |
| `custom` | User-defined | Custom workflows (requires `custom_phases` and `skip_reason`) |

#### Returns

```json
{
  "success": true,
  "message": "Project initialized with feature workflow",
  "project": {
    "issue_number": 123,
    "issue_title": "Add OAuth2 authentication",
    "workflow_name": "feature",
    "phases": [
      "planning",
      "research",
      "red",
      "green",
      "refactor",
      "documentation",
      "merge-prep"
    ],
    "current_phase": "planning",
    "parent_branch": "main"
  }
}
```

#### Example Usage

**Feature workflow:**
```json
{
  "issue_number": 123,
  "issue_title": "Add OAuth2 authentication",
  "workflow_name": "feature",
  "parent_branch": "main"
}
```

**Custom workflow:**
```json
{
  "issue_number": 456,
  "issue_title": "Experimental ML feature",
  "workflow_name": "custom",
  "custom_phases": ["research", "prototype", "evaluation", "implementation"],
  "skip_reason": "ML workflow requires prototype/evaluation phases"
}
```

#### Behavior Notes

- **State Persistence:** Writes to `.st3/state.json` and `.st3/projects.json`
- **Parent Branch Auto-Detection:** If `parent_branch` not provided, attempts detection via `git reflog`
- **Branch Validation:** Current branch must match pattern `<type>/<issue_number>-*`
- **Idempotency:** Re-running on same branch returns error (project already initialized)

---

### get_project_plan

**MCP Name:** `get_project_plan`  
**Class:** `GetProjectPlanTool`  
**File:** [mcp_server/tools/project_tools.py](../../../../mcp_server/tools/project_tools.py)

Get project phase plan for issue number.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_number` | `int` | **Yes** | GitHub issue number |

#### Returns

```json
{
  "success": true,
  "project": {
    "issue_number": 123,
    "issue_title": "Add OAuth2 authentication",
    "workflow_name": "feature",
    "phases": [
      "planning",
      "research",
      "red",
      "green",
      "refactor",
      "documentation",
      "merge-prep"
    ],
    "current_phase": "green",
    "completed_phases": ["planning", "research", "red"],
    "parent_branch": "main",
    "created_at": "2026-02-08T10:00:00Z",
    "updated_at": "2026-02-08T12:00:00Z"
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

- **Read-Only:** Does not modify state
- **Historical Access:** Reads from `.st3/projects.json` (historical registry)
- **Not Found:** Returns error if project not initialized

---

### transition_phase

**MCP Name:** `transition_phase`  
**Class:** `TransitionPhaseTool`  
**File:** [mcp_server/tools/phase_tools.py](../../../../mcp_server/tools/phase_tools.py)

Transition branch to next phase (strict sequential validation).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `branch` | `str` | **Yes** | Branch name (e.g., `"feature/123-oauth"`) |
| `to_phase` | `str` | **Yes** | Target phase to transition to |
| `human_approval` | `str` | No | Optional human approval message (audit trail) |

#### Returns

```json
{
  "success": true,
  "message": "Transitioned from 'red' to 'green'",
  "transition": {
    "branch": "feature/123-oauth",
    "from_phase": "red",
    "to_phase": "green",
    "timestamp": "2026-02-08T12:00:00Z"
  }
}
```

#### Example Usage

**Sequential transition:**
```json
{
  "branch": "feature/123-oauth",
  "to_phase": "green"
}
```

**With human approval:**
```json
{
  "branch": "feature/123-oauth",
  "to_phase": "documentation",
  "human_approval": "Tests passing, code reviewed, ready for docs"
}
```

#### Behavior Notes

- **Sequential Validation:** Target phase must be the **next** phase in workflow (no skipping)
- **State Update:** Updates `.st3/state.json` atomically
- **Audit Trail:** Records timestamp and optional human approval in `.st3/projects.json`
- **Not Initialized:** Returns error if project not initialized

#### Example Error (Attempting to Skip)

**Request:**
```json
{
  "branch": "feature/123-oauth",
  "to_phase": "merge-prep"  // Trying to skip from "red" to "merge-prep"
}
```

**Response:**
```json
{
  "success": false,
  "error": "Invalid phase transition: cannot skip from 'red' to 'merge-prep'. Next phase is 'green'. Use force_phase_transition if intentional."
}
```

---

### force_phase_transition

**MCP Name:** `force_phase_transition`  
**Class:** `ForcePhaseTransitionTool`  
**File:** [mcp_server/tools/phase_tools.py](../../../../mcp_server/tools/phase_tools.py)

Force non-sequential phase transition (skip/jump with reason and human approval).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `branch` | `str` | **Yes** | Branch name (e.g., `"feature/123-oauth"`) |
| `to_phase` | `str` | **Yes** | Target phase to transition to (can skip phases) |
| `skip_reason` | `str` | **Yes** | Reason for skipping validation (audit trail) |
| `human_approval` | `str` | **Yes** | Human approval message (REQUIRED for forced transitions) |

#### Returns

```json
{
  "success": true,
  "message": "Forced transition from 'red' to 'merge-prep' (skipped: green, refactor, documentation)",
  "transition": {
    "branch": "feature/123-oauth",
    "from_phase": "red",
    "to_phase": "merge-prep",
    "skipped_phases": ["green", "refactor", "documentation"],
    "skip_reason": "Emergency hotfix approved by team lead",
    "human_approval": "Team lead approval: critical security fix",
    "timestamp": "2026-02-08T12:00:00Z"
  }
}
```

#### Example Usage

```json
{
  "branch": "feature/123-oauth",
  "to_phase": "merge-prep",
  "skip_reason": "Emergency hotfix: critical security vulnerability discovered",
  "human_approval": "Approved by Tech Lead (John Doe) - immediate merge required"
}
```

#### Behavior Notes

- **No Validation:** Bypasses sequential phase validation
- **Audit Trail:** Records `skip_reason`, `human_approval`, skipped phases, and timestamp in `.st3/projects.json`
- **Use Sparingly:** Intended for emergency situations only
- **Required Fields:** Both `skip_reason` and `human_approval` are REQUIRED (not optional)

---

## State Management

### .st3/state.json

Current branch state (runtime, not committed to git):

```json
{
  "feature/123-oauth": {
    "issue_number": 123,
    "issue_title": "Add OAuth2 authentication",
    "workflow_name": "feature",
    "current_phase": "green",
    "parent_branch": "main",
    "updated_at": "2026-02-08T12:00:00Z"
  }
}
```

**Behavior:**
- Updated by `initialize_project`, `transition_phase`, `force_phase_transition`
- Synchronized by `git_checkout` (loads state when switching branches)
- **Not committed** to git (local state only)

---

### .st3/projects.json

Historical project registry (committed to git):

```json
{
  "123": {
    "issue_number": 123,
    "issue_title": "Add OAuth2 authentication",
    "workflow_name": "feature",
    "phases": ["planning", "research", "red", "green", "refactor", "documentation", "merge-prep"],
    "created_at": "2026-02-08T10:00:00Z",
    "transitions": [
      {
        "from_phase": null,
        "to_phase": "planning",
        "timestamp": "2026-02-08T10:00:00Z"
      },
      {
        "from_phase": "planning",
        "to_phase": "research",
        "timestamp": "2026-02-08T10:30:00Z"
      }
    ]
  }
}
```

**Behavior:**
- Append-only history of all project initializations and phase transitions
- Committed to git (shared across team)
- Provides audit trail for phase skips and forced transitions

---

## Workflow Definitions

### .st3/workflows.yaml

```yaml
workflows:
  feature:
    phases:
      - planning
      - research
      - red
      - green
      - refactor
      - documentation
      - merge-prep
  
  bug:
    phases:
      - investigation
      - red
      - green
      - refactor
      - documentation
      - merge-prep
  
  docs:
    phases:
      - planning
      - documentation
  
  refactor:
    phases:
      - planning
      - research
      - refactor
      - documentation
      - merge-prep
  
  hotfix:
    phases:
      - red
      - green
      - merge-prep
  
  epic:
    phases:
      - planning
      - tracking
  
  custom:
    # User-defined phases via custom_phases parameter
```

---

## Integration with Git Tools

Phase state is **synchronized** with git branch operations:

| Git Operation | Phase State Behavior |
|---------------|---------------------|
| `git_checkout` | Loads phase state from `.st3/state.json` after switching branches |
| `create_branch` | No phase state (must run `initialize_project` after) |
| `git_delete_branch` | Removes phase state from `.st3/state.json` |

---

## Common Workflows

### Starting a New Feature

```
1. create_branch(name="feature/123-oauth", base_branch="main")
2. git_checkout(branch="feature/123-oauth")
3. initialize_project(issue_number=123, issue_title="Add OAuth2", workflow_name="feature")
```

### TDD Cycle with Phase Transitions

```
1. transition_phase(branch="feature/123-oauth", to_phase="red")
2. scaffold_artifact(artifact_type="dto", name="OAuthToken")
3. git_add_or_commit(phase="red", message="Add failing test for OAuthToken")
4. transition_phase(branch="feature/123-oauth", to_phase="green")
5. safe_edit_file(...)  # Implement
6. run_tests(path="tests/test_oauth.py")
7. git_add_or_commit(phase="green", message="Implement OAuthToken")
```

### Emergency Phase Skip (Hotfix)

```
1. force_phase_transition(
     branch="bugfix/456-security",
     to_phase="merge-prep",
     skip_reason="Critical security vulnerability - zero-day exploit",
     human_approval="CTO approval (Jane Smith) - immediate production deployment"
   )
2. git_push(set_upstream=True)
3. create_pr(title="HOTFIX: Security patch", body="...", head="bugfix/456-security")
4. merge_pr(pr_number=78, merge_method="merge")
```

---

## Related Documentation

- [README.md](README.md) — MCP Tools navigation index
- [git.md](git.md) — Git workflow tools (branch, checkout, commit)
- [.st3/workflows.yaml](../../../../.st3/workflows.yaml) — Workflow definitions
- [.st3/state.json](../../../../.st3/state.json) — Current branch state
- [.st3/projects.json](../../../../.st3/projects.json) — Historical project registry
- [docs/development/issue19/research.md](../../../development/issue19/research.md) — Tool inventory research (Section 1.8: Project/Phase tools)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-02-08 | Agent | Complete reference for 4 project/phase tools: initialize, inspect, transition, force-transition |
