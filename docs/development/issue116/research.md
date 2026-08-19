<!-- docs/development/issue116/research.md -->
<!-- template=research version=8b7bb3ab created=2026-08-19T13:54Z updated=2026-08-19T14:15Z -->
# Research: Automatic Issue Number Formatting in create_branch Tool

**Status:** APPROVED  
**Version:** 1.0.0  
**Last Updated:** 2026-08-19

---

## Purpose

Analyze the architecture, code paths, blast radius, constraints, and strategy for adding automatic issue number formatting with a required `issue_number` parameter to the `create_branch` tool in `phase-gate-mcp`.

## Scope

**In Scope:**
- `CreateBranchInput` Pydantic model in `mcp_server/tools/git_tools.py`
- `GitManager.create_branch` method in `mcp_server/managers/git_manager.py`
- `GitConfig` helpers and branch naming pattern validation in `mcp_server/config/schemas/git_config.py`
- Exhaustive test suite migration across all unit and integration tests calling `create_branch` or instantiating `CreateBranchInput`

**Out of Scope:**
- Changes to other git tools (`git_checkout`, `git_merge`, `git_delete_branch`, etc.)
- Ambient state guessing of issue numbers during `create_branch`
- Modification of unrelated config files

## Prerequisites

Read these first:
1. Read `get_issue(issue_number=116)`
2. Read [docs/coding_standards/ARCHITECTURE_PRINCIPLES.md](docs/coding_standards/ARCHITECTURE_PRINCIPLES.md)
3. Read [docs/coding_standards/DOCUMENTATION_STANDARD.md](docs/coding_standards/DOCUMENTATION_STANDARD.md)

---

## Problem Statement

The `create_branch` tool currently requires callers to manually prefix issue numbers into branch names (e.g. `name="116-create-branch-issue-number"`), which is error-prone and diverges from the mandatory `issue_number` parameter conventions used across other lifecycle tools (such as `initialize_project`).

---

## Research Goals

- Investigate how `create_branch` and `GitManager` construct and validate branch names.
- Identify the complete blast radius of adding a mandatory `issue_number` parameter.
- Determine architectural boundaries, edge cases (such as duplicate prefixes), and test migration scope.
- Establish baseline expected results and an approved strategy (`clean_break`) for Design and Planning phases.

---

## Background

In `pgmcp`, Prime Directive #1 dictates **Issue-First Development**: work never happens on `main` and always begins with `create_issue` -> `create_branch` -> `initialize_project`. Branches strictly follow Convention #5: `{branch_type}/{issue_number}-{name}` (e.g., `feature/116-create-branch-issue-number`).

Currently, `CreateBranchInput` in `mcp_server/tools/git_tools.py` only defines:
```python
class CreateBranchInput(BaseModel):
    name: str = Field(..., description="Branch name (kebab-case)")
    branch_type: str = Field(default="feature", description="Branch type")
    base_branch: str = Field(..., description="Base branch to create from")
```

Making `issue_number: int` a required parameter aligns `create_branch` with `initialize_project`, guarantees branch name conformity upfront, and eliminates downstream failures in `extract_issue_number` and state synchronizations.

---

## Findings

### 1. Architectural Layers and Responsibilities

| Layer | Component | Current State | Target Responsibility |
|---|---|---|---|
| **Tool (Entry Point)** | `CreateBranchInput` / `CreateBranchTool` | Accepts `name`, `branch_type`, `base_branch`. `args_model` has `extra="forbid"`. | Accepts required `issue_number: int = Field(..., ge=1)`. Passes `issue_number` to manager. |
| **Manager (Domain)** | `GitManager.create_branch` | Accepts `(name, branch_type, base_branch, note_context)`. Formats `f"{branch_type}/{name}"`. | Accepts `(issue_number, name, branch_type, base_branch, note_context)`. Assembles branch name `{branch_type}/{issue_number}-{normalized_name}`, validates against `GitConfig`. |
| **Config (SSOT)** | `GitConfig` (`git_config.py`) | Contains `branch_name_pattern: "^[a-z0-9-]+$"`, `branch_types`, and `extract_issue_number`. | Serves as SSOT for branch conventions and regex validation. |
| **Adapter (Infra)** | `GitAdapter.create_branch` | Accepts full branch name and base ref. Executes `git checkout -b <branch> <base>`. | Unchanged; executes git commands with provided full name. |

```mermaid
flowchart TD
    A[Caller: Agent / User] -->|issue_number: int, name: str, branch_type: str, base_branch: str| B[CreateBranchTool]
    B -->|execute| C[GitManager.create_branch]
    C -->|normalize name & format {branch_type}/{issue_number}-{name}| C
    C -->|validate branch_type & slug pattern| D[GitConfig]
    C -->|create_branch full_name| E[GitAdapter]
    E -->|git checkout -b full_name base| F[Git Repository]
```

### 2. Blast Radius Analysis

The blast radius has been exhaustively mapped across production code and test suites:

#### Production Code:
- `mcp_server/tools/git_tools.py`: `CreateBranchInput` and `CreateBranchTool.execute`
- `mcp_server/managers/git_manager.py`: `GitManager.create_branch` signature, validation, and name formatting

#### Test Suite (Call Sites Requiring Parameter Updates):
- `tests/mcp_server/unit/tools/test_git_tools.py`:
  - `test_create_branch_tool_calls_manager_with_explicit_base`
  - `test_create_branch_tool_with_branch_name_as_base`
  - Validation test for missing/invalid `issue_number` (`ge=1`)
- `tests/mcp_server/unit/managers/test_git_manager.py`:
  - `test_create_branch_valid`
  - `test_create_branch_epic_valid`
  - `test_create_branch_invalid_type`
  - `test_create_branch_invalid_name`
  - `test_create_branch_dirty`
  - `test_create_branch_requires_base_branch_parameter`
  - `test_create_branch_passes_base_to_adapter`
- `tests/mcp_server/managers/test_git_manager_config.py`:
  - `test_create_branch_uses_git_config_branch_types`
  - `test_create_branch_uses_git_config_name_pattern`
- `tests/mcp_server/unit/integration/test_git.py`:
  - `test_git_manager_create_branch_valid`
  - `test_git_manager_create_branch_epic_valid`
  - `test_git_manager_create_branch_dirty`
  - `test_git_manager_create_branch_invalid_name`
- `tests/mcp_server/unit/integration/test_all_tools.py`:
  - `test_create_branch_tool_flow`
- `tests/mcp_server/unit/managers/test_note_migration.py`:
  - `test_dirty_workspace_produces_generic_note`

### 3. Edge Cases & Normalization

- **Normalization / Idempotency:** If a caller passes `issue_number=116` and `name="116-create-branch"`, name formatting normalizes the slug to avoid double prefixing (`feature/116-116-create-branch`).
- **Validation Bounds:** `issue_number` must be a positive integer (`ge=1`). Negative numbers or `0` are rejected fail-fast by Pydantic validation.

---

## Strategy Evaluation

| Strategy Option | Consistency with PGMCP | Complexity | Risk | Recommendation |
|---|---|---|---|---|
| **Option 1: Mandatory `issue_number` (Clean Break)** | High (Strict Issue-First alignment, matching `initialize_project`) | Low | Low (isolated to git tool & unit tests) | **Approved** |
| **Option 2: Optional `issue_number` (Preserve Compatibility)** | Low (Permits invalid branches lacking issue numbers) | Low | Medium (downstream extraction issues) | Rejected |
| **Option 3: Ambient Context Auto-detection** | Very Low (Implicit behavior) | Medium | High (violates Explicit over Implicit §8) | Rejected |

---

## Approved Strategy

**Selected Strategy:** `clean_break`

**Policy per Boundary:**
- `CreateBranchInput`: `issue_number: int = Field(..., ge=1, description="GitHub issue number")` (mandatory parameter).
- `GitManager.create_branch`: `(self, issue_number: int, name: str, branch_type: str, base_branch: str, note_context: NoteContext) -> str`.
- Full branch name is deterministically formatted as `{branch_type}/{issue_number}-{normalized_name}`.
- Test Suite: All call sites in test fixtures and unit/integration tests will be updated to pass `issue_number` in the same implementation cycle.

---

## Expected Results

1. `CreateBranchInput` requires `issue_number: int = Field(..., ge=1, description="GitHub issue number")`.
2. Calling `create_branch` without `issue_number` or with `issue_number <= 0` fails fast with a validation error.
3. `create_branch` constructs and returns full branch name `{branch_type}/{issue_number}-{name}`.
4. If `name` already starts with `{issue_number}-`, it normalizes gracefully without duplicate prefixing.
5. `GitConfig` and `GitManager` validation ensures branch names and types conform to `.pgmcp/config/git.yaml`.
6. 100% of unit, manager, and integration tests in the blast radius are updated and pass with green test suite.

---

## Open Questions

- ❓ Should slug normalization (stripping leading `{issue_number}-` if present) live as a helper on `GitConfig` or in `GitManager`? (To be decided in Design Phase).

---

## Related Documentation

- **[https://github.com/MikeyVK/phase-gate-mcp/issues/116][related-1]**
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-2]**
- **[docs/coding_standards/DOCUMENTATION_STANDARD.md][related-3]**

<!-- Link definitions -->

[related-1]: https://github.com/MikeyVK/phase-gate-mcp/issues/116
[related-2]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-3]: docs/coding_standards/DOCUMENTATION_STANDARD.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-08-19 | Agent | Initial evidence-based research draft with clean_break mandatory issue_number strategy |
