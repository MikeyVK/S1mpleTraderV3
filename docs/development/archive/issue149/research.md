<!-- docs/development/issue149/research.md -->
<!-- template=research version=1.0 created=2026-02-18 updated=2026-02-18 -->
# Research — Issue #149: Redesign `create_issue` Tool

**Status:** complete
**Version:** 1.1
**Last Updated:** 2026-02-18

---

## Purpose

Map the current `create_issue` implementation, identify all gaps versus desired conventions, and define the full set of changes needed including new config infrastructure.

## Scope

**In Scope:**
- `mcp_server/tools/issue_tools.py` — `CreateIssueInput`, `CreateIssueTool`
- `mcp_server/managers/github_manager.py` — `create_issue()`
- `.st3/labels.yaml` — `status:*` removal, `parent:*` pattern change
- `.st3/workflows.yaml` — first-phase derivation per issue type
- `mcp_server/scaffolding/templates/concrete/issue.md.jinja2` — body rendering
- All test files that instantiate `CreateIssueInput`

**Out of Scope:**
- `get_issue` / `list_issues` alignment → issue #150
- `create_branch` issue_number param → issue #116
- GitHub Projects integration
- Retroactive issue title renaming (manual task, no tooling)

## Prerequisites

- `.st3/labels.yaml` (existing)
- `.st3/workflows.yaml` (existing)
- `mcp_server/scaffolding/templates/concrete/issue.md.jinja2` (existing, tested)
- New files: `issues.yaml`, `scopes.yaml`, `milestones.yaml`, `contributors.yaml` (created in this issue)

---

## Problem Statement

The current `create_issue` tool accepts a free-form `title` (no length limit, no prefix enforcement), unvalidated `labels: list[str]`, a raw string `body` with no structure, and has no awareness of issue types, scopes, milestones, or assignees beyond forwarding them to the GitHub API unchecked. This makes automated issue creation convention-blind.

---

## Findings

### Current `CreateIssueInput` Schema

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `title` | `str` | ✅ | none |
| `body` | `str` | ✅ | none |
| `labels` | `list[str] \| None` | ❌ | none |
| `milestone` | `int \| None` | ❌ | none |
| `assignees` | `list[str] \| None` | ❌ | none |

### Call Sites (breakage surface)

All existing call sites use only `title` + `body`. All three break when `issue_type`, `scope`, and `priority` become required fields:

| File | Call |
|------|------|
| `tests/unit/tools/test_issue_tools.py:31` | `CreateIssueInput(title="New Issue", body="Description")` |
| `tests/unit/mcp_server/integration/test_all_tools.py:284` | `CreateIssueInput(title=..., body=...)` |
| `tests/unit/mcp_server/integration/test_github.py:48` | `CreateIssueInput(title="New Issue", body="Body")` |

No production code outside `issue_tools.py` instantiates `CreateIssueInput` directly.

### Infrastructure to Reuse

| Component | Reuse |
|-----------|-------|
| `GitConfig.from_file()` singleton | Replicate for `IssueConfig`, `ScopeConfig`, `MilestoneConfig`, `ContributorConfig` |
| `@field_validator("branch_type")` in `CreateBranchInput` | Same pattern for `issue_type`, `scope`, `priority` |
| `issue.md.jinja2` template | Existing, tested — render `IssueBody` via this template |
| `JinjaRenderer` in `mcp_server/scaffolding/` | Reuse for body rendering in `execute()` |

---

## New Config File Schemas

### `.st3/issues.yaml`

```yaml
version: "1.0"
issue_types:
  - name: feature
    workflow: feature
    label: "type:feature"
  - name: bug
    workflow: bug
    label: "type:bug"
  - name: hotfix
    workflow: hotfix
    label: "type:bug"
  - name: refactor
    workflow: refactor
    label: "type:refactor"
  - name: docs
    workflow: docs
    label: "type:docs"
  - name: chore
    workflow: feature
    label: "type:chore"
  - name: epic
    workflow: epic
    label: "type:epic"
required_label_categories:
  - type
  - priority
  - scope

optional_label_inputs:
  is_epic:
    type: bool
    label: "type:epic"
    behavior: "Overrides type:* label from issue_type"
  parent_issue:
    type: int
    label_pattern: "parent:{value}"
    description: "Applies parent:{issue_number} label (e.g., parent:91)"
```

Issue types are aligned with Conventional Commits (`git.yaml`):
`feature=feat, bug=fix, hotfix=fix(urgent), refactor=refactor, docs=docs, chore=chore, epic=container`

Dropped: `enhancement` (ambiguous — use feature or refactor), `technical-debt` + `housekeeping` (merged into `chore`).

Note: `hotfix` maps to `label: "type:bug"` (not `type:hotfix`) — this non-obvious mapping is the reason the `label` field exists in `issues.yaml`. For scopes, no such exception exists, so no label field appears there.

### `.st3/scopes.yaml`

```yaml
version: "1.0"
scopes:
  - architecture
  - mcp-server
  - platform
  - tooling
  - workflow
  - documentation
```

Name `scopes.yaml` (not `projects.yaml`) — avoids confusion with GitHub Projects.

**No `label` field in `scopes.yaml`.** `labels.yaml` is SSOT for label existence (name, colour, description). The tool derives `scope:{name}` by convention — no explicit mapping needed. Compare: `git.yaml` only has `branch_types: [feature, fix, ...]` without label references. Adding a `label` field would violate SSOT and duplicate `labels.yaml`.

**Exception in `issues.yaml`:** the `label` field is justified there because `hotfix` maps to `type:bug` (not `type:hotfix`). No such exceptions exist for scopes, so the field is omitted.

### `.st3/milestones.yaml`

```yaml
version: "1.0"
milestones: []
# { number: int, title: str, state: open|closed }
```

### `.st3/contributors.yaml`

```yaml
version: "1.0"
contributors: []
# { login: str, name: str }
```

---

## New `CreateIssueInput` Schema

| Field | Type | Required | Validation | Effect |
|-------|------|----------|------------|--------|
| `issue_type` | `str` | ✅ | `issues.yaml` | → `type:*` label + initial `phase:*` label |
| `title` | `str` | ✅ | max 72 chars (`git.yaml`) | — |
| `priority` | `str` | ✅ | `labels.yaml` `priority:*` | → `priority:*` label |
| `scope` | `str` | ✅ | `scopes.yaml` | → `scope:*` label |
| `body` | `IssueBody` | ✅ | nested model, rendered via Jinja2 | — |
| `is_epic` | `bool` | ❌ | — | overrides `issue_type` to `type:epic` internally |
| `parent_issue` | `int \| None` | ❌ | `>= 1` | → `parent:{n}` label |
| `milestone` | `str \| None` | ❌ | `milestones.yaml` | — |
| `assignees` | `list[str] \| None` | ❌ | each value against `contributors.yaml` | — |

**Removed:** `labels` (free field) — fully derived from the structured fields above.

## `IssueBody` Nested Model

```python
class IssueBody(BaseModel):
    problem: str                           # required
    expected: str | None = None
    actual: str | None = None
    context: str | None = None
    steps_to_reproduce: str | None = None
    related_docs: list[str] | None = None
```

Rendered via `issue.md.jinja2` in `CreateIssueTool.execute()` before forwarding to `GitHubManager`.

---

## Label Assembly Logic (internal to `execute()`)

```
1. issue_type → issues.yaml lookup → get_label(issue_type) → type:* label
2. is_epic=True → override: type:epic label (replaces type:* from step 1)
3. scope → scopes.yaml lookup → scope:* label
4. priority → direct → priority:* label
5. parent_issue=N → parent:N label
6. phase → first phase of workflow from issues.yaml → workflows.yaml → phase:* label (automatic, never exposed to caller)
```

---

## `labels.yaml` Changes Required

- Remove `status:*` category entirely (4 labels: `status:blocked`, `status:in-progress`, `status:needs-info`, `status:ready`) — phase:* covers workflow state
- Update `parent:*` pattern: `^parent:issue-\d+$` → `^parent:\d+$` (example: `parent:91`)
- Add `type:chore` label to the TYPE section

---

## Validator Patterns

All config-driven validators follow the `GitConfig.from_file()` singleton pattern and are implemented as synchronous `@field_validator` methods. Milestone and assignee validation happens in `execute()` (pre-API-call, against local yaml).

---

## Open Questions

1. Milestone validation: only against `milestones.yaml` (local, no live API call) — accepted.
2. `is_epic=True` overrides `issue_type` to `epic` internally — no dual type labels.
3. `contributors.yaml` initially populated manually; sync tooling is a future enhancement.

---

## References

- Issue #149
- Issue #116 (consumer of `get_issue` — depends on #150)
- Issue #150 (consumer of new label structure)
- `.st3/labels.yaml`, `.st3/workflows.yaml`
- `mcp_server/tools/issue_tools.py`
- `mcp_server/managers/github_manager.py`
- `mcp_server/scaffolding/templates/concrete/issue.md.jinja2`
- `mcp_server/tools/git_tools.py` (validator pattern reference)
- `mcp_server/config/git_config.py` (singleton config pattern reference)
- `docs/coding_standards/CODE_STYLE.md`
