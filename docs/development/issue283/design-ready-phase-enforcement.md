<!-- docs\development\issue283\design-ready-phase-enforcement.md -->
<!-- template=design version=5827e841 created=2026-04-09T12:19Z updated= -->
# Ready Phase Enforcement — Design

**Status:** FINAL
**Version:** 2.0
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
terminal phase injection (explicit parameter, called from `server.py`), `MergeReadinessContext`
facade dataclass, new `EnforcementRunner` handlers (`exclude_branch_local_artifacts`,
`check_merge_readiness`), `enforcement.yaml` new entries, `ConfigValidator` cross-validation of
`pr_allowed_phase`, `GitCommitTool` and `CreatePRTool` enforcement event declarations, removal
of debug scripts and `.gitattributes` `merge=ours`.

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

    def get_pr_allowed_phase(self) -> str:
        """Return the phase name that permits PR creation. Single query path (P5 CQS)."""
        return self.merge_policy.pr_allowed_phase
```

`merge_policy` is **required**. If absent from `phase_contracts.yaml`, Pydantic raises a
`ValidationError` at startup (P4 Fail-Fast). The Flag Day guarantee — config and code deploy
together — makes a `None`-safe fallback unnecessary (P9 YAGNI).

The `get_pr_allowed_phase()` method is the single query path for this value. Callers (handlers)
never traverse `config.merge_policy.pr_allowed_phase` directly — this would violate the Law of
Demeter (P6) by drilling two levels into a nested object.

### 2.5 `ConfigLoader` — Terminal Phase Injection

`ConfigLoader` gains a new static helper `_inject_terminal_phase`. It must **not** be called
from inside `load_workflow_config()` — that would introduce a hidden second file read (file-I/O
side effect inside what D6 declares a pure transform), violating both P5 CQS and the explicit
dependency injection principle (P4).

```python
# mcp_server/config/loader.py

@staticmethod
def _inject_terminal_phase(
    workflow_config: WorkflowConfig,
    workphases_config: WorkphasesConfig,   # explicit parameter — no hidden file read
) -> WorkflowConfig:
    """Return a new WorkflowConfig with the terminal phase appended to every workflow.

    Pure transform: input → new output. No file I/O, no mutation (CQS / P5).
    """
    terminal = workphases_config.get_terminal_phase()
    enriched = {}
    for name, wf in workflow_config.workflows.items():
        if terminal not in wf.phases:
            enriched[name] = wf.model_copy(update={"phases": [*wf.phases, terminal]})
        else:
            enriched[name] = wf
    return workflow_config.model_copy(update={"workflows": enriched})
```

**`load_workflow_config()` is NOT changed.** It continues to load only `workflows.yaml`.

**Calling convention — `server.py` composition root:**

The caller (`MCPServer.__init__`) loads both configs independently and calls the inject helper
before passing to `ConfigValidator`. This matches the existing `server.py` pattern:

```python
# mcp_server/server.py — MCPServer.__init__  (addition, no removals)

workflow_config = loader.load_workflow_config()
workphases_config = loader.load_workphases_config()
workflow_config = ConfigLoader._inject_terminal_phase(workflow_config, workphases_config)
# ConfigValidator receives the enriched workflow_config — injection MUST precede validator
config_validator = ConfigValidator(
    workflow_config=workflow_config,
    workphases_config=workphases_config,
    ...
)
```

**Ordering constraint (N6):** Injection must always precede `ConfigValidator` construction.
The enriched `workflow_config` is the single object passed to all downstream consumers. The
caller (`server.py`) is responsible for the sequence: load → inject → validate → construct.

**CQS contract:** `_inject_terminal_phase` returns a new `WorkflowConfig`; it never mutates
the input objects. All `model_copy` calls produce new Pydantic instances. The function has
no side effects — it is a pure transform (D6).

### 2.6 `GitCommitTool` — Enforcement Event Declaration

> ⚠️ **Gedeeltelijk vervangen.** `design-git-add-commit-regression-fix.md` breidt het `execute()`-contract van `GitCommitTool` uit: een `context: NoteContext`-parameter wordt toegevoegd en `ExclusionNote`-entries worden uitgelezen voor `skip_paths`-doorgave aan `GitManager`. De `enforcement_event`-declaratie in dit sectie blijft ongewijzigd geldig. Autoriteitsvolgorde: de regression fix design prevaleert voor het `execute()`-contract; dit document prevaleert voor de `enforcement_event`-declaratie.

`GitCommitTool` follows the identical pattern already in use by `CreateBranchTool` in the same
file (`git_tools.py` line 121): declare the `enforcement_event` class variable. No changes to
`execute()`.

```python
# mcp_server/tools/git_tools.py

class GitCommitTool(BaseTool):
    enforcement_event: str | None = "git_commit"   # NEW — one line only
    # execute() is NOT modified
```

All enforcement logic belongs in the `EnforcementRunner` handler registered for this event (see
§2.8). Tool layer is closed for modification when enforcement rules change (OCP — P1.2). SRP is
preserved: `GitCommitTool` has exactly one reason to change — git commit mechanics.

### 2.7 `CreatePRTool` — Enforcement Event Declaration

> ℹ️ **Volledig van kracht.** `CreatePRTool.execute()` wordt niet gewijzigd door de regression fix. Alleen §2.6 is gedeeltelijk vervangen.

`CreatePRTool` follows the same pattern:

```python
# mcp_server/tools/pr_tools.py

class CreatePRTool(BaseTool):
    enforcement_event: str | None = "create_pr"   # NEW — one line only
    # execute() is NOT modified
```

All enforcement logic belongs in the `EnforcementRunner` handler for this event (see §2.8).
Adding new PR enforcement rules (future) requires only adding a handler and an `enforcement.yaml`
entry — `CreatePRTool` is never opened for modification.

### 2.8 `enforcement.yaml` — New Entries

Two new enforcement rules are added to `.st3/config/enforcement.yaml`, after the existing
`create_branch` rule:

```yaml
# .st3/config/enforcement.yaml  (additions)

  - event_source: tool
    tool: git_commit
    timing: pre
    actions:
      - type: exclude_branch_local_artifacts

  - event_source: tool
    tool: create_pr
    timing: pre
    actions:
      - type: check_merge_readiness
```

`EnforcementRunner._validate_registered_actions()` performs a fail-fast startup check: every
`action.type` in `enforcement.yaml` must have a registered handler. Both
`exclude_branch_local_artifacts` and `check_merge_readiness` are registered in
`_build_default_registry()` (see §2.9). Config and code ship atomically — the deadlock (N1) is
impossible because the handler registration precedes the config validation in the boot sequence.

### 2.9 `MergeReadinessContext` Facade and Enforcement Handlers

The two new handlers need `terminal_phase`, `pr_allowed_phase`, and `branch_local_artifacts` —
data that lives across two separate config objects (`WorkphasesConfig`, `PhaseContractsConfig`).
Following the existing `PhaseConfigContext` pattern (`phase_contract_resolver.py:19`), a frozen
dataclass bundles this data for downstream consumers.

**New dataclass** (new file or alongside `PhaseConfigContext`):

```python
# mcp_server/managers/phase_contract_resolver.py  (addition)

from dataclasses import dataclass
from mcp_server.config.schemas.workphases import WorkphasesConfig
from mcp_server.config.schemas.phase_contracts_config import BranchLocalArtifact, PhaseContractsConfig

@dataclass(frozen=True)
class MergeReadinessContext:
    """Facade bundling merge-readiness data for EnforcementRunner handlers."""

    terminal_phase: str                             # from WorkphasesConfig.get_terminal_phase()
    pr_allowed_phase: str                           # from PhaseContractsConfig.get_pr_allowed_phase()
    branch_local_artifacts: tuple[BranchLocalArtifact, ...]  # from PhaseContractsConfig
```

**Construction in `server.py` (composition root),** after configs are loaded and injected:

```python
# mcp_server/server.py — MCPServer.__init__  (after injection step)

merge_readiness_context = MergeReadinessContext(
    terminal_phase=workphases_config.get_terminal_phase(),
    pr_allowed_phase=phase_contracts_config.get_pr_allowed_phase(),
    branch_local_artifacts=tuple(phase_contracts_config.merge_policy.branch_local_artifacts),
)
enforcement_runner = EnforcementRunner(
    workspace_root=workspace_root,
    config=enforcement_config,
    merge_readiness_context=merge_readiness_context,   # new constructor parameter
)
```

**`EnforcementRunner` constructor** gains one new optional parameter. It stores it and makes it
available through `EnforcementContext`:

```python
# mcp_server/managers/enforcement_runner.py

class EnforcementRunner:
    def __init__(
        self,
        workspace_root: Path,
        config: EnforcementConfig,
        registry: EnforcementRegistry | dict[str, ActionHandler] | None = None,
        merge_readiness_context: MergeReadinessContext | None = None,  # NEW
    ) -> None:
        ...
        self._merge_readiness_context = merge_readiness_context
```

**New handlers** registered in `_build_default_registry()`:

```python
registry.register("exclude_branch_local_artifacts", self._handle_exclude_branch_local_artifacts)
registry.register("check_merge_readiness", self._handle_check_merge_readiness)
```

**Handler — `_handle_exclude_branch_local_artifacts`:**

Executes `git rm --cached <path>` for each artifact in `merge_readiness_context.branch_local_artifacts`
that is currently git-tracked. Skips untracked artifacts silently. Returns an exclusion note
included in `ToolResult` output:

```
Branch-local artifacts excluded from commit index:
  - .st3/state.json
    Reason: MCP workflow state — branch-local, must never reach main
  - .st3/deliverables.json
    Reason: MCP workflow deliverables — branch-local, must never reach main

Source: .st3/config/phase_contracts.yaml → merge_policy.branch_local_artifacts
```

**Phase-gating:** The handler only runs when the current branch phase equals
`merge_readiness_context.terminal_phase`. Phase is read from `StateRepository` via
`context.workspace_root`. No string literal `"ready"` appears in the handler.

**Handler — `_handle_check_merge_readiness`:**

Two sequential checks, both raise `ValidationError` on failure:

*Check 1 — Phase gate:*
```
current_phase = StateRepository(context.workspace_root).get_current_phase(branch)
pr_allowed   = merge_readiness_context.pr_allowed_phase

if current_phase != pr_allowed:
    raise ValidationError(
        f"PR creation requires phase '{pr_allowed}'. Current phase: '{current_phase}'.",
        hints=[f"transition_phase(to_phase=\"{pr_allowed}\")"],
    )
```

*Check 2 — Artifact pre-flight (runs only when phase check passes):*
```
tracked = [a for a in merge_readiness_context.branch_local_artifacts
           if git_ls_files(context.workspace_root, a.path)]

if tracked:
    raise ValidationError(
        "Branch-local artifacts are still git-tracked and would contaminate main:",
        hints=[f"  - {a.path}\n    Reason: {a.reason}" for a in tracked]
              + ["Commit first in the ready phase to auto-exclude them:",
                 "  git_add_or_commit(message=\"chore: prepare branch for PR\")",
                 "Source: .st3/config/phase_contracts.yaml → merge_policy.branch_local_artifacts"],
    )
```

### 2.10 `ConfigValidator` — `pr_allowed_phase` Cross-Validation

Following the existing `_validate_workflow_phases()` pattern, add a new validation method that
cross-validates `merge_policy.pr_allowed_phase` against the known workphase names. A typo in
`phase_contracts.yaml` (e.g., `pr_allowed_phase: redy`) passes Pydantic type validation (valid
string) but silently disables PR enforcement at runtime — caught here at startup instead.

```python
# mcp_server/config/validator.py

def _validate_merge_policy_phase(
    self,
    phase_contracts_config: PhaseContractsConfig,
    workphases_config: WorkphasesConfig,
) -> None:
    """Fail fast if pr_allowed_phase references a phase not in workphases.yaml."""
    pr_phase = phase_contracts_config.merge_policy.pr_allowed_phase
    if pr_phase not in workphases_config.phases:
        raise ConfigError(
            f"phase_contracts.yaml: pr_allowed_phase '{pr_phase}' is not a known workphase. "
            f"Known phases: {sorted(workphases_config.phases)}"
        )
```

This method is called from `ConfigValidator.validate()` after both config objects are loaded.

### 2.11 `.gitattributes` Cleanup

The existing `merge=ours` entry for `state.json` is removed from `.gitattributes` as part of
this change. The workflow-native enforcement makes it redundant, and its presence is misleading
(it implies a protection that does not work — see research doc Root Causes 1-3).

```diff
- .st3/state.json merge=ours
```

**Flag-Day atomic checklist (N4):** All three steps must be deployed atomically on the same
commit. If code ships without the config updates, `WorkphasesConfig.model_validator` and
`PhaseContractsConfig` will both raise `ValidationError` at MCP server startup.

| Step | File | Change |
|------|------|--------|
| 1 | `.st3/config/workphases.yaml` | Add `ready` phase with `terminal: true` (§2.1) |
| 2 | `.st3/config/phase_contracts.yaml` | Add `merge_policy` section (§2.2) |
| 3 | Ship Python code | Pydantic validators and enforcement handlers active |

### 2.12 Debug Script Removal

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
| D6 | `_inject_terminal_phase()` is a static pure transform; called from `server.py` | CQS (P5); no file I/O side effects; D6 is now truthfully pure |
| D7 | Tools declare `enforcement_event` class variable only; no enforcement in `execute()` | SRP (P1.1); OCP (P1.2); follows existing `CreateBranchTool` pattern in same module |
| D8 | Enforcement handlers receive `MergeReadinessContext` via `EnforcementRunner` | Law of Demeter (P6/P7); handlers access at most 2 levels; no drill into config internals |
| D9 | `ready` not listed in `workflows.yaml` — loader injects it | DRY/SSOT (P2); terminal phase defined once in `workphases.yaml` |
| D10 | `MergeReadinessContext` frozen dataclass at composition root | `PhaseConfigContext` pattern; P11 DI; P4 Fail-Fast — constructed once at startup |
| D11 | `ConfigValidator._validate_merge_policy_phase()` cross-validates `pr_allowed_phase` | P4 Fail-Fast; typo-safe; follows `_validate_workflow_phases()` pattern |
| D12 | `_inject_terminal_phase` `workphases_config` parameter is explicit; ordering: load → inject → validate → construct | P5 CQS; P4 Fail-Fast; eliminates hidden file-read side effect in what D6 declares pure |

---

## 4. Test Strategy — Blast Radius and Fix Contracts

The following test files will fail on first run the moment the Pydantic schema changes (§2.3, §2.4)
are applied. Each item has a concrete fix contract so the implementer can apply fixes alongside the
schema changes within the same TDD cycle.

### V6 — `WorkphasesConfig` validator blast radius

Every in-memory `WorkphasesConfig(phases={...})` construction without a `terminal: true` phase
fails with `ValidationError`.

| File | Fix |
|------|-----|
| `tests/mcp_server/unit/config/test_label_startup.py` (lines 104, 282) | Add `"ready": PhaseDefinition(display_name="Ready", terminal=True)` to each in-memory `WorkphasesConfig` |
| `tests/mcp_server/unit/managers/test_phase_contract_resolver.py` (workspace_root fixture) | Add `ready` entry with `terminal: true` to inline `workphases.yaml` |
| `tests/mcp_server/unit/tools/test_force_phase_transition_tool.py` (~4 workspace fixtures) | Add `ready` entry with `terminal: true` to each inline `workphases.yaml` fixture |
| `tests/mcp_server/core/test_scope_encoder.py` (workphases_yaml fixture) | Add `ready` entry with `terminal: true` to the fixture YAML |

**Fix pattern (in-memory):**
```python
WorkphasesConfig(phases={..., "ready": PhaseDefinition(display_name="Ready", terminal=True)})
```

**Fix pattern (inline YAML):**
```yaml
  ready:
    display_name: "Ready"
    terminal: true
```

### V7 — `test_support.py` fallback construction

`tests/mcp_server/test_support.py` line 238 constructs `PhaseContractsConfig` without
`merge_policy` as a fallback for tests without a `phase_contracts.yaml` fixture.

**Fix:**
```python
# Before
phase_contracts_config = PhaseContractsConfig.model_validate({"workflows": {}})

# After
phase_contracts_config = PhaseContractsConfig.model_validate({
    "workflows": {},
    "merge_policy": {"pr_allowed_phase": "ready", "branch_local_artifacts": []},
})
```

This single fix eliminates the widest blast radius in the suite (all tests routed through
`make_phase_state_engine`).

### V8 — `test_workflow_config.py` isolated-fixture classes

`TestWorkflowConfigLoading` and `TestTransitionValidation` use `tmp_path` fixtures that write
only a `workflows.yaml`. Because `_inject_terminal_phase` is now called from `server.py` (not
from `load_workflow_config()`), these tests are **no longer affected by a hidden file read**.
V5 fix resolves the `ConfigError` blast radius automatically.

One remaining fix for the exact phase list assertion at line 201:
```python
# Before
assert workflow.phases == ["research", "planning", "design", "tdd", "validation", "documentation"]

# After
assert workflow.phases == ["research", "planning", "design", "tdd", "validation", "documentation", "ready"]
```
(Only applies if the test loads via the composition root path that calls `_inject_terminal_phase`.)

### V9 — `workflow_fixtures.py` semantic contract change

`tests/mcp_server/fixtures/workflow_fixtures.py` — `feature_phases`, `bug_phases`,
`hotfix_phases` fixtures gain `"ready"` as last element after injection is active in server.py.

Review all tests using:
- `phases[-1]` — was `"documentation"` → becomes `"ready"` (valid for tests checking terminal)
- `len(phases)` — was 6 → becomes 7 (update count assertions)

Forward index access (e.g., `phases[0]`, `phases[2]`) is unaffected.

### N_PCR_DOUBLE — `test_phase_contract_resolver.py` dual blast point

`tests/mcp_server/unit/managers/test_phase_contract_resolver.py` — `workspace_root` fixture
writes both `workphases.yaml` and `phase_contracts.yaml` inline. Both are missing required fields.
Both must be fixed atomically:

```yaml
# workphases.yaml fixture — add terminal phase
  ready:
    display_name: "Ready"
    terminal: true
```
```yaml
# phase_contracts.yaml fixture — add merge_policy
merge_policy:
  pr_allowed_phase: ready
  branch_local_artifacts: []
```

---

## Open Questions (Resolved)

| Q | Question | Answer |
|---|----------|--------|
| Q1 | Authoritative config for phase enforcement? | `phase_contracts.yaml` global `merge_policy` section — P13 |
| Q2 | Which loader file injects the terminal phase? | `ConfigLoader._inject_terminal_phase(workflow_config, workphases_config)` — static helper in `mcp_server/config/loader.py`, called from `MCPServer.__init__` in `server.py`. **NOT** from `load_workflow_config()` (see §2.5). |
| Q3 | Which tests break on terminal phase injection? | V6 (WorkphasesConfig validator), V7 (test_support.py fallback), V8 (workflow_config isolated fixtures — resolved by V5 fix), V9 (workflow_fixtures.py phase count/index), N_PCR_DOUBLE (phase_contract_resolver.py dual blast). Full fix contracts in §4. |
| Q4 | In-flight branches on deploy day? | `force_phase_transition` + release note; no automated migration (YAGNI — research Flag Day) |

---

## Related Documentation

- [docs/development/issue283/research-ready-phase-enforcement.md](research-ready-phase-enforcement.md)
- [mcp_server/config/schemas/workphases.py](../../../mcp_server/config/schemas/workphases.py)
- [mcp_server/config/schemas/phase_contracts_config.py](../../../mcp_server/config/schemas/phase_contracts_config.py)
- [mcp_server/config/loader.py](../../../mcp_server/config/loader.py)
- [mcp_server/config/validator.py](../../../mcp_server/config/validator.py)
- [mcp_server/managers/enforcement_runner.py](../../../mcp_server/managers/enforcement_runner.py)
- [mcp_server/managers/phase_contract_resolver.py](../../../mcp_server/managers/phase_contract_resolver.py)
- [mcp_server/server.py](../../../mcp_server/server.py)
- [mcp_server/tools/pr_tools.py](../../../mcp_server/tools/pr_tools.py)
- [mcp_server/tools/git_tools.py](../../../mcp_server/tools/git_tools.py)
- [.st3/config/workphases.yaml](../../../.st3/config/workphases.yaml)
- [.st3/config/phase_contracts.yaml](../../../.st3/config/phase_contracts.yaml)
- [.st3/config/enforcement.yaml](../../../.st3/config/enforcement.yaml)
- [docs/architecture/03_tool_layer.md](../../../docs/architecture)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-09 | Agent | Initial design — all sections complete |
| 1.1 | 2026-04-09 | Agent | QA fixes A1–A5: duplicate removed, filename corrected, `merge_policy` required, Open Questions table added, P5 CQS constraint added |
| 2.0 | 2026-04-09 | Agent | QA v2 revision: V1–V9, Vmissing, N1–N6, N_PCR_DOUBLE — §2.5 calling convention fixed (explicit param, server.py), §2.6/§2.7 rewritten (enforcement_event only), §2.8–§2.10 added (enforcement.yaml, MergeReadinessContext, ConfigValidator), §2.11 atomic checklist added, §3 decisions D6–D8 revised D10–D12 added, §4 test strategy added |

