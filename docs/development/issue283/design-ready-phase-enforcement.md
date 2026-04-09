<!-- docs\development\issue283\design-ready-phase-enforcement.md -->
<!-- template=design version=5827e841 created=2026-04-09T12:19Z updated= -->
# Ready Phase Enforcement — Design

**Status:** FINAL
**Version:** 1.0
**Last Updated:** 2026-04-09

---

## Purpose

Translate Expected Results E1–E9 from the research document into concrete, implementable designs:
YAML structures, Pydantic model contracts, loader behavior, tool contracts, and error message
specifications. This document is the authoritative specification for the implementation phase.

## Scope

**In Scope:**
`workphases.yaml` schema extension (`terminal` field), `phase_contracts.yaml` `merge_policy`
section, `PhaseDefinition` and `WorkphasesConfig` Pydantic model contracts, `ConfigLoader`
terminal phase injection, `CreatePRTool` phase gate and artifact pre-flight, `GitCommitTool`
artifact auto-exclusion in terminal phase, removal of debug scripts and `.gitattributes`
`merge=ours`.

**Out of Scope:**
Implementation cycles and test definitions (planning phase), performance optimization,
backward compatibility, workflows beyond feature/bug/hotfix/refactor/docs/epic.

## Prerequisites

Read these first:
1. Research document FINAL: `docs/development/issue283/research-ready-phase-enforcement.md`
2. All open questions resolved — see research doc Open Questions section
3. `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md` — Principles 2, 3, 4, 8, 9, 10, 13

---

## 1. Context & Requirements

### 1.1 Problem Statement

Branch-local MCP artifacts (`.st3/state.json`, `.st3/deliverables.json`) reach `main` during PR
merges. Three git-level root causes make `.gitattributes merge=ours` unreliable. The files are
intentionally git-tracked (multi-machine continuity) and cannot be removed from tracking. A
workflow-native solution is required. See research doc for full root cause analysis.

### 1.2 Functional Requirements

| # | Requirement | Research Ref |
|---|-------------|-------------|
| F1 | Exactly one terminal phase declared in `workphases.yaml`; MCP server refuses to start on violation | E1, E8 |
| F2 | Branch-local artifact list declared once in `phase_contracts.yaml` with per-artifact reasons | E2 |
| F3 | `CreatePRTool` (draft + non-draft) blocked outside terminal phase; error is actionable | E3 |
| F4 | `GitCommitTool` auto-excludes branch-local artifacts from index in terminal phase; per-artifact output shown | E4 |
| F5 | `CreatePRTool` verifies no branch-local artifacts are git-tracked before creating PR | E5 |
| F6 | No hardcoded terminal phase name in Python; phase identity read from config | E6 |
| F7 | Every workflow's active phase list contains the terminal phase as the last entry after loading | E7 |

### 1.3 Non-Functional Requirements

- All new config fields have explicit Pydantic types; no silent `None` defaults for required flags.
- Error messages name the blocking condition and the corrective action.
- Terminal phase injection in `ConfigLoader` must not mutate the source `WorkflowConfig` object (CQS / Principle 5).
- `PhaseDefinition.terminal` defaults to `False` so existing `workphases.yaml` loads without change until the terminal phase entry is added.

### 1.4 Constraints

| Principle | Constraint |
|-----------|-----------|
| P2 DRY/SSOT | Branch-local artifact list has one authoritative config location — no duplication in Python |
| P3 Config-First | No phase names or artifact paths hardcoded in Python |
| P4 Fail-Fast | Zero or multiple terminal phases → `ConfigError` at startup |
| P8 Explicit | Terminal phase identity read from a declared flag, not inferred from position or name |
| P9 YAGNI | No backward-compat layer; clean break only |
| P10 Cohesion | `terminal` flag belongs on the `PhaseDefinition`, not in a separate registry |
| P13 Config-First enforcement | Artifact exclusion behavior declared in `phase_contracts.yaml` |
| P5 CQS | `_inject_terminal_phase()` returns a new `WorkflowConfig`; source object never mutated |

---

## 2. Design

### 2.1 `workphases.yaml` — Terminal Phase Declaration

Add a `terminal` boolean field to each phase entry. All existing phases declare `terminal: false`
(or omit the field, relying on the Pydantic default). Exactly one phase declares `terminal: true`.

The chosen terminal phase name is **`ready`**. It is appended at the bottom of `workphases.yaml`.

```yaml
# .st3/config/workphases.yaml  (addition at bottom)

  ready:
    display_name: "Ready"
    description: "Branch is clean, branch-local artifacts excluded; PR creation is permitted."
    commit_type_hint: "chore"
    terminal: true
    subphases: []
```

All other existing phases have `terminal` omitted (defaults to `false` via Pydantic).

### 2.2 `phase_contracts.yaml` — `merge_policy` Section

Add a top-level `merge_policy` section before the `workflows:` key. This is the single
authoritative declaration of (a) which phase permits PR creation, and (b) which files are
branch-local and must never reach `main`.

```yaml
# .st3/config/phase_contracts.yaml  (new global section at top)

merge_policy:
  pr_allowed_phase: ready
  branch_local_artifacts:
    - path: .st3/state.json
      reason: "MCP workflow state — branch-local, must never reach main"
    - path: .st3/deliverables.json
      reason: "MCP workflow deliverables — branch-local, must never reach main"
```

The `pr_allowed_phase` value references a phase by name. It is read by tools; it is never
hardcoded as a string in Python.

### 2.3 Pydantic Schema — `PhaseDefinition` and `WorkphasesConfig`

**`PhaseDefinition`** gains one new field:

```python
# mcp_server/config/schemas/workphases.py

class PhaseDefinition(BaseModel):
    display_name: str = ""
    description: str = ""
    commit_type_hint: str | None = None
    subphases: list[str] = Field(default_factory=list)
    exit_requires: list[dict[str, Any]] = Field(default_factory=list)
    entry_expects: list[dict[str, Any]] = Field(default_factory=list)
    terminal: bool = False          # NEW — exactly one phase may be True
```

**`WorkphasesConfig`** gains a `model_validator` and a query method:

```python
# mcp_server/config/schemas/workphases.py

from pydantic import model_validator

class WorkphasesConfig(BaseModel):
    version: str = ""
    phases: dict[str, PhaseDefinition] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_single_terminal_phase(self) -> "WorkphasesConfig":
        terminal = [name for name, phase in self.phases.items() if phase.terminal]
        if len(terminal) == 0:
            raise ValueError(
                "workphases.yaml must declare exactly one terminal phase. "
                "None found. Add 'terminal: true' to the intended phase."
            )
        if len(terminal) > 1:
            raise ValueError(
                f"workphases.yaml declares multiple terminal phases: {terminal}. "
                "Exactly one is permitted."
            )
        return self

    def get_terminal_phase(self) -> str:
        """Return the name of the single terminal phase. Guaranteed by validator."""
        return next(name for name, phase in self.phases.items() if phase.terminal)

    # existing methods unchanged
    def get_exit_requires(self, phase: str) -> list[dict[str, Any]]: ...
    def get_entry_expects(self, phase: str) -> list[dict[str, Any]]: ...
```

### 2.4 `phase_contracts.yaml` — New Schema Models

Two new Pydantic models to represent the `merge_policy` section:

```python
# mcp_server/config/schemas/phase_contracts_config.py  (new models alongside existing ones)

class BranchLocalArtifact(BaseModel):
    path: str
    reason: str

class MergePolicy(BaseModel):
    pr_allowed_phase: str
    branch_local_artifacts: list[BranchLocalArtifact] = Field(default_factory=list)
```

**`PhaseContractsConfig`** gains a required `merge_policy` field (consistent with
`model_config = ConfigDict(extra="forbid")` already in that class):

```python
class PhaseContractsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merge_policy: MergePolicy
    workflows: dict[str, dict[str, PhaseContractPhase]] = Field(default_factory=dict)
```

`merge_policy` is **required**. If absent from `phase_contracts.yaml`, Pydantic raises a
`ValidationError` at startup (P4 Fail-Fast). The Flag Day guarantee — config and code deploy
together — makes a `None`-safe fallback unnecessary (P9 YAGNI).

### 2.5 `ConfigLoader` — Terminal Phase Injection

`ConfigLoader.load_workflow_config()` is extended to inject the terminal phase at the end of
every workflow's phase list after loading:

```python
# mcp_server/config/loader.py

def load_workflow_config(self, config_path: Path | None = None) -> WorkflowConfig:
    data, resolved_path = self._load_yaml("workflows.yaml", config_path=config_path)
    workflow_config = self._validate_schema(WorkflowConfig, data, resolved_path)
    return self._inject_terminal_phase(workflow_config)

def _inject_terminal_phase(self, workflow_config: WorkflowConfig) -> WorkflowConfig:
    """Return a new WorkflowConfig with the terminal phase appended to every workflow."""
    workphases = self.load_workphases_config()
    terminal = workphases.get_terminal_phase()
    enriched = {}
    for name, wf in workflow_config.workflows.items():
        if terminal not in wf.phases:
            enriched[name] = wf.model_copy(update={"phases": [*wf.phases, terminal]})
        else:
            enriched[name] = wf
    return workflow_config.model_copy(update={"workflows": enriched})
```

**CQS contract:** `_inject_terminal_phase` returns a new `WorkflowConfig`; it never mutates
the input object. All `model_copy` calls produce new Pydantic instances.

**No hardcoded name:** `terminal` is obtained from `workphases.get_terminal_phase()`, never
as a string literal.

### 2.6 `GitCommitTool` — Auto-Exclusion in Terminal Phase

When `GitCommitTool` executes and the current phase is the terminal phase, it:

1. Reads `merge_policy.branch_local_artifacts` from `PhaseContractsConfig`.
2. For each artifact, calls `git rm --cached <path>` if the file is currently tracked.
3. Proceeds with the normal commit.
4. Appends an exclusion report to the tool output.

**Output contract (exact format):**

```
Committed (SHA abc1234): "chore(P_READY): ..."

Branch-local artifacts excluded from commit index:
  - .st3/state.json
    Reason: MCP workflow state — branch-local, must never reach main
  - .st3/deliverables.json
    Reason: MCP workflow deliverables — branch-local, must never reach main

Source: .st3/config/phase_contracts.yaml → merge_policy.branch_local_artifacts
```

If an artifact is not tracked (already absent from index), it is silently skipped — no
output entry for it.

**Phase detection:** The tool reads the current phase from `StateRepository`, then calls
`workphases_config.get_terminal_phase()` to obtain the terminal phase name. It compares by
value; no string literal `"ready"` appears in the tool.

### 2.7 `CreatePRTool` — Phase Gate and Artifact Pre-Flight

`CreatePRTool` performs two pre-flight checks before creating any PR (draft or non-draft):

**Check 1 — Phase gate:**

```
Current phase is read from StateRepository.
pr_allowed = phase_contracts_config.merge_policy.pr_allowed_phase
```

If `current_phase != pr_allowed`:

```
Error: PR creation requires phase '{pr_allowed}'. Current phase: '{current_phase}'.
To proceed: transition_phase(to_phase="{pr_allowed}")
```

**Check 2 — Artifact tracking pre-flight:**

After the phase check passes, `CreatePRTool` runs `git ls-files` for each path in
`merge_policy.branch_local_artifacts`. If any are still tracked:

```
Error: Branch-local artifacts are still git-tracked and would contaminate main:
  - .st3/state.json
    Reason: MCP workflow state — branch-local, must never reach main

Commit first in the ready phase to auto-exclude them:
  git_add_or_commit(message="chore: prepare branch for PR")
Source: .st3/config/phase_contracts.yaml → merge_policy.branch_local_artifacts
```

**Happy path:** Both checks pass → PR creation proceeds normally.

### 2.8 `.gitattributes` Cleanup

The existing `merge=ours` entry for `state.json` is removed from `.gitattributes` as part of
this change. The workflow-native enforcement makes it redundant, and its presence is misleading
(it implies a protection that does not work — see research doc Root Causes 1-3).

```diff
- .st3/state.json merge=ours
```

### 2.9 Debug Script Removal

The following files are deleted from the repository as part of this change (they were committed
to a feature branch by mistake and must be absent from `main`):

- `check_yaml.py`
- `fix_yaml.py`
- `revert_yaml.py`
- `show_yaml.py`

---

## 3. Design Decisions Summary

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Terminal phase name: `ready` | Explicit, intention-revealing, matches workflow vocabulary |
| D2 | `terminal` flag on `PhaseDefinition`, default `False` | Cohesion (P10); flag belongs where the phase is defined |
| D3 | `model_validator` on `WorkphasesConfig` for single-terminal enforcement | Fail-Fast (P4); detected at startup, not at tool call time |
| D4 | `get_terminal_phase()` query method on `WorkphasesConfig` | CQS (P5); single query path; callers never inspect `phases` directly |
| D5 | `merge_policy` in `phase_contracts.yaml` (global section) | Config-First enforcement (P13); existing file for phase-triggered behavior |
| D6 | `_inject_terminal_phase()` in `ConfigLoader` returns new object | CQS (P5); source config never mutated |
| D7 | `GitCommitTool` reads phase via `StateRepository`, not hardcoded | Config-First (P3); E6 compliance |
| D8 | `CreatePRTool` performs two independent pre-flight checks | Separation of concerns; phase check is cheap, artifact scan is IO |
| D9 | `ready` not listed in `workflows.yaml` — loader injects it | DRY/SSOT (P2); terminal phase defined once in `workphases.yaml` |

---

## Open Questions (Resolved)

| Q | Question | Answer |
|---|----------|--------|
| Q1 | Authoritative config for phase enforcement? | `phase_contracts.yaml` global `merge_policy` section — P13 |
| Q2 | Which loader file injects the terminal phase? | `ConfigLoader.load_workflow_config()` in `mcp_server/config/loader.py` |
| Q3 | Which tests break on terminal phase injection? | Tests asserting exact phase counts or order on loaded workflows; `PhaseDefinition`/`WorkphasesConfig` instantiation tests are unaffected (`terminal` defaults to `False`) |
| Q4 | In-flight branches on deploy day? | `force_phase_transition` + release note; no automated migration (YAGNI — research Flag Day) |

---

## Related Documentation

- [docs/development/issue283/research-ready-phase-enforcement.md](research-ready-phase-enforcement.md)
- [mcp_server/config/schemas/workphases.py](../../../mcp_server/config/schemas/workphases.py)
- [mcp_server/config/schemas/phase_contracts_config.py](../../../mcp_server/config/schemas/phase_contracts_config.py)
- [mcp_server/config/loader.py](../../../mcp_server/config/loader.py)
- [mcp_server/tools/pr_tools.py](../../../mcp_server/tools/pr_tools.py)
- [mcp_server/tools/git_tools.py](../../../mcp_server/tools/git_tools.py)
- [.st3/config/workphases.yaml](../../../.st3/config/workphases.yaml)
- [.st3/config/phase_contracts.yaml](../../../.st3/config/phase_contracts.yaml)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-09 | Agent | Initial design — all sections complete |
| 1.1 | 2026-04-09 | Agent | QA fixes A1–A5: duplicate removed, filename corrected, `merge_policy` required, Open Questions table added, P5 CQS constraint added |

