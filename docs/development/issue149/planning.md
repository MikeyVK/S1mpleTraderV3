<!-- docs/development/issue149/planning.md -->
<!-- template=planning version=1.0 created=2026-02-18 updated=2026-02-18 -->
# Planning — Issue #149: Redesign `create_issue` Tool

**Status:** draft
**Version:** 1.1
**Last Updated:** 2026-02-18

---

## Purpose

Break down the redesign of `create_issue` into logical, independently testable TDD cycles. Each cycle produces a shippable increment. Integration and documentation phases are explicitly planned.

## Scope

**In Scope:**
- `mcp_server/tools/issue_tools.py`
- `mcp_server/config/` — new config classes
- `.st3/issues.yaml`, `.st3/scopes.yaml`, `.st3/milestones.yaml`, `.st3/contributors.yaml`
- `.st3/labels.yaml` — cleanup (`status:*` removal, `parent:*` pattern, `type:chore`)
- `.st3/git.yaml` — `issue_title_max_length` addition
- `tests/unit/tools/test_issue_tools.py`
- `tests/unit/mcp_server/integration/test_github.py`
- `tests/unit/mcp_server/integration/test_all_tools.py`

**Out of Scope:**
- `get_issue` / `list_issues` alignment → issue #150
- `create_branch` enrichment → issue #116
- GitHub Projects integration
- Retroactive issue title renaming (manual task)
- Sync tooling for milestones/contributors

## Prerequisites

- Research complete → [docs/development/issue149/research.md](research.md)
- `issues.yaml`, `scopes.yaml`, `milestones.yaml`, `contributors.yaml` do not yet exist
- `labels.yaml` requires cleanup (cycle 2)

## Summary

The `create_issue` tool currently accepts free-form, unvalidated input. This plan divides the work into 6 TDD cycles plus integration and documentation phases. Cycle 1 establishes the config infrastructure. Cycles 2–6 incrementally build the new `CreateIssueInput` and `CreateIssueTool`. Each cycle closes with all quality gates passing before the next begins.

---

## Cycle Dependencies

```
Cycle 1 (config infra) ──────────────────────┐
                                              ├─→ Cycle 3 (IssueBody) ──→ Cycle 4 (schema) ──→ Cycle 5 (label assembly)
Cycle 2 (labels.yaml cleanup) ───────────────┘                                                       │
                                                                                                      └──→ Cycle 6 (error handling)
```

---

## Coding Standards Requirements (apply to every cycle)

> These requirements derive from `docs/coding_standards/` and apply to **every** cycle. They are not repeated per cycle but must be applied consciously at each RED/GREEN/REFACTOR step.

- **Scaffolding first:** All new Python files (`*_config.py`, `test_*.py`) are created via `scaffold_artifact` — never manually. Templates auto-generate module headers (`@layer`, `@dependencies`, `@responsibilities`), import structure, and class skeleton.
- **Test functions:** All test functions have `-> None` return type (Gate 1 ANN rule).
- **Fixture pattern:** Fixtures that inject other fixtures use `@pytest.fixture(name="x")` with a private function name `_x` (avoids W0621 name collision).
- **Quality gate closure:** Every cycle closes by running `run_quality_gates` over all modified files: Ruff format → Ruff lint → type check → pytest → coverage ≥ 90%.
- **`json_schema_extra`:** All Pydantic models exposed via MCP (tool inputs) must include at least 2 examples in `json_schema_extra`.

---

## TDD Cycles

---

### Cycle 1 — Config infrastructure: new YAML files + singleton classes

**Goal:** Introduce `issues.yaml`, `scopes.yaml`, `milestones.yaml`, `contributors.yaml` and corresponding config classes following the `GitConfig.from_file()` singleton pattern.

**Deliverables:**
- `.st3/issues.yaml`
- `.st3/scopes.yaml`
- `.st3/milestones.yaml`
- `.st3/contributors.yaml`
- `mcp_server/config/issue_config.py`
- `mcp_server/config/scope_config.py`
- `mcp_server/config/milestone_config.py`
- `mcp_server/config/contributor_config.py`
- `tests/unit/config/test_issue_config.py`
- `tests/unit/config/test_scope_config.py`
- `tests/unit/config/test_milestone_config.py`
- `tests/unit/config/test_contributor_config.py`

**RED — Failing tests first:**
> Create test files via `scaffold_artifact(artifact_type="test", ...)`. All test functions `-> None`. Fixtures use `@pytest.fixture(name="...")` with private name and a temporary YAML file (see pattern in `test_git_tools_config.py`).

- `IssueConfig.from_file()` loads and validates the `issue_types` list
- `IssueConfig` raises on unknown issue type
- `IssueConfig.get_workflow(issue_type)` returns the correct workflow name
- `IssueConfig.get_label(issue_type)` returns the correct `type:*` label (including `hotfix → type:bug`)
- `IssueConfig` loads the `optional_label_inputs` section correctly
- `ScopeConfig.from_file()` loads and validates scopes (names only, no labels)
- `ScopeConfig.has_scope(name)` returns `True`/`False`
- `MilestoneConfig.from_file()` loads (empty list is valid)
- `MilestoneConfig.validate_milestone(title)` returns `True` when list is empty (permissive when unpopulated)
- `ContributorConfig.from_file()` loads (empty list is valid)
- `ContributorConfig.validate_assignee(login)` returns `True` when list is empty (permissive when unpopulated)

**GREEN:**
- Scaffold `.st3/issues.yaml`, `.st3/scopes.yaml`, `.st3/milestones.yaml`, `.st3/contributors.yaml` (YAML files)
- Scaffold `mcp_server/config/issue_config.py` via `scaffold_artifact(artifact_type="component", ...)` — module header auto-generated
- Same for `scope_config.py`, `milestone_config.py`, `contributor_config.py`
- Implement `IssueConfig`, `ScopeConfig`, `MilestoneConfig`, `ContributorConfig` (fill in methods)
- **Quality gates:** run `run_quality_gates` over all new files (Ruff format + lint + type check + pytest + coverage)

---

### Cycle 2 — `labels.yaml` cleanup

**Goal:** Align `labels.yaml` with the new conventions: remove `status:*`, update the `parent:*` pattern, add `type:chore`.

**Deliverables:**
- `.st3/labels.yaml` (updated)
- `tests/unit/config/test_labels_yaml_conventions.py`

**RED:**
> Create test file via `scaffold_artifact`. All test functions `-> None`.

- `status:blocked`, `status:in-progress`, `status:needs-info`, `status:ready` are **not** present in `labels.yaml`
- `parent:*` pattern is `^parent:\d+$` (not `^parent:issue-\d+$`)
- `parent:*` example is `parent:91` (not `parent:issue-18`)
- `type:chore` label exists in the TYPE section of `labels.yaml`

**GREEN:**
- Remove the `status:*` section from `.st3/labels.yaml`
- Update the `label_patterns` entry: pattern and example
- Add `type:chore` to the TYPE section
- **Quality gates:** run `run_quality_gates` over `test_labels_yaml_conventions.py`

---

### Cycle 3 — `IssueBody` nested model + Jinja2 rendering

**Goal:** Introduce `IssueBody` Pydantic model and verify that `CreateIssueTool` can render it to markdown via `issue.md.jinja2`.

**Deliverables:**
- `IssueBody` class in `mcp_server/tools/issue_tools.py`
- `_render_body()` helper in `CreateIssueTool`
- `tests/unit/tools/test_issue_body.py`

**RED:**
> Create test file via `scaffold_artifact`. All test functions `-> None`.

- `IssueBody` requires the `problem` field
- All optional fields default to `None`
- Rendering `IssueBody` via `issue.md.jinja2` produces a `## Problem` section
- Rendering with `expected`/`actual`/`context`/`steps_to_reproduce` produces the correct sections
- Rendering with `related_docs: list[str]` produces a Related Documentation section (list of links/items)
- Rendering with only `problem` produces minimal valid markdown

**GREEN:**
- Implement `IssueBody` in `mcp_server/tools/issue_tools.py` — add `json_schema_extra` with ≥ 2 examples (minimal body + full body)
- Implement `_render_body(body: IssueBody) -> str` in `CreateIssueTool` via `JinjaRenderer`
- **Quality gates:** run `run_quality_gates` over modified files (Ruff format + lint + type check + pytest)

---

### Cycle 4 — `CreateIssueInput` schema refactor

**Goal:** Replace the current `CreateIssueInput` with the new schema: required `issue_type`, `title` (max 72 chars), `priority`, `scope`, `body` (`IssueBody`), and optional `is_epic`, `parent_issue`, `milestone`, `assignees`. Remove the `labels` field. Update all existing test call sites.

**Deliverables:**
- Updated `CreateIssueInput` in `mcp_server/tools/issue_tools.py`
- `issue_title_max_length: 72` added to `.st3/git.yaml`
- Updated `tests/unit/tools/test_issue_tools.py`
- Updated `tests/unit/mcp_server/integration/test_all_tools.py`
- Updated `tests/unit/mcp_server/integration/test_github.py`

**RED:**
- `issue_type` is required, validated against `IssueConfig`
- Unknown `issue_type` raises `ValidationError` with a hint listing valid values
- `title` is required, max 72 chars (from `git.yaml`)
- `title` exceeding 72 chars raises `ValidationError`
- `priority` is required, validated against `labels.yaml` `priority:*`
- `scope` is required, validated against `ScopeConfig` (valid: `architecture`, `mcp-server`, `platform`, `tooling`, `workflow`, `documentation`)
- `body` is required, must be an `IssueBody` instance
- `is_epic` optional bool, default `False`
- `parent_issue` optional, rejects values `< 1`
- `milestone` optional, validated against `MilestoneConfig` (always valid when list is empty)
- `assignees` optional list, each value validated against `ContributorConfig` (always valid when list is empty)
- `CreateIssueInput(title=..., body="string")` raises `ValidationError` (breaking change confirmed)

**GREEN:**
- Refactor `CreateIssueInput` with new fields, `@field_validator`s, and `json_schema_extra` with ≥ 2 examples (minimal input + full input)
- Add `issue_title_max_length: 72` to `.st3/git.yaml`
- Update all three existing test files (replace call sites, add `-> None` where missing)
- **Quality gates:** run `run_quality_gates` over all modified files (Ruff format + lint + type check + pytest + coverage)

---

### Cycle 5 — Label assembly in `CreateIssueTool.execute()`

**Goal:** Implement internal label derivation: assemble the full label list from structured inputs before passing to `GitHubManager`. The tool no longer accepts or forwards free-form labels.

**Deliverables:**
- `_assemble_labels()` in `CreateIssueTool`
- Updated `execute()` in `CreateIssueTool`
- `tests/unit/tools/test_create_issue_label_assembly.py`

**RED:**
- `issue_type='feature'` → `type:feature` label
- `issue_type='hotfix'` → `type:bug` label (not `type:hotfix`) — via `IssueConfig.get_label()`
- `is_epic=True` → `type:epic` label, overrides `issue_type` label
- `parent_issue=91` → `parent:91` label
- `scope='tooling'` → `scope:tooling` label
- `priority='medium'` → `priority:medium` label
- Automatic `phase:*` label derived from the first workflow phase of the issue type
- `body` is rendered to a markdown string before passing to `GitHubManager`
- Tool forwards **no** free `labels` to `GitHubManager`

**GREEN:**
- Implement `_assemble_labels()` using `IssueConfig`, `ScopeConfig`, and `workflows.yaml` first-phase lookup
- Wire `_assemble_labels()` and `_render_body()` into `execute()`
- **Quality gates:** run `run_quality_gates` over all modified files (Ruff format + lint + type check + pytest + coverage)

---

### Cycle 6 — Error handling + ToolResult contract

**Goal:** All validation errors and GitHub API errors produce `ToolResult.error()` with actionable messages. No raw exceptions leak to the caller.

**Deliverables:**
- Updated `execute()` error handling in `CreateIssueTool`
- `tests/unit/tools/test_create_issue_errors.py`

**RED:**
- Pydantic `ValidationError` on unknown `issue_type` → `ToolResult.error` with hint about valid values
- `ExecutionError` from `GitHubManager` → `ToolResult.error`
- `JinjaRenderer` failure → `ToolResult.error` (no unhandled exception)
- Milestone not in `milestones.yaml` → `ToolResult.error` before API call

**GREEN:**
- Add `try/except` in `execute()` for `ValidationError`, `ExecutionError`, and rendering failures
- Error messages reference valid config values
- **Quality gates:** run `run_quality_gates` over all modified files (Ruff format + lint + type check + pytest + coverage ≥ 90% full suite)

---

## Integration Phase

> Goal: real-world validation against the live GitHub API. No unit tests — proof of correct tool integration.

**Deliverables:**
- `tests/integration/test_create_issue_e2e.py`
- Manual verification script (or pytest mark `integration`) covering:
  - Create issue with minimal input → correct issue visible on GitHub with the right labels
  - Create issue with all options → all labels applied correctly
  - Invalid input → tool refuses before GitHub API call
  - Milestone validation → known milestone accepted, unknown refused

**Approach:**
- Tests run against a test repository (not production)
- Marker: `@pytest.mark.integration` — excluded from standard CI run
- Results documented manually in `docs/development/issue149/integration_smoke_test.md`

---

## Documentation Phase

**Deliverables:**

1. **`agent.md` §2.1 workflow sequence** — update `create_issue` call signature in the workflow table: `create_issue(issue_type, title, priority, scope, body)` (replaces current `create_issue(title, body, labels)`)
2. **`agent.md` §2.1 example call** — add a concrete example with all required fields
3. **Config reference docs** — brief description of each new `.st3/` config file added to `docs/reference/` (one entry per file: purpose, structure, who owns it)
4. **Inline docstrings** — `CreateIssueInput`, `IssueBody`, `_assemble_labels()`, `_render_body()` fully documented
5. **`labels.yaml` CHANGELOG** — record removal of `status:*` and `parent:*` pattern change

---

## Risks

1. `JinjaRenderer` interface is scaffolding-oriented — may need adjustment for inline use inside a tool
2. `milestones.yaml` and `contributors.yaml` start empty — validation is a no-op until populated; document this explicitly
3. Breaking change on `body` field (`str → IssueBody`) affects all existing callers — coordinate update in cycle 4

---

## Related Docs

- [docs/development/issue149/research.md](research.md)
- `.st3/labels.yaml`, `.st3/workflows.yaml`
- `mcp_server/config/git_config.py` (singleton pattern reference)
- `mcp_server/tools/git_tools.py` (validator pattern reference)
- `mcp_server/scaffolding/templates/concrete/issue.md.jinja2`
- `docs/coding_standards/CODE_STYLE.md`
- Issue #150 (consumer), Issue #116 (consumer)
