# QA Handover — Design Revision Required (Issue #283)

**From:** QA (@qa)
**To:** Implementer (@imp)
**Date:** 2026-04-09
**Branch:** `refactor/283-ready-phase-enforcement`
**Design file:** `docs/development/issue283/design-ready-phase-enforcement.md` (Status: FINAL v1.1)
**Verdict:** NO-GO — seventeen violations (V1–V9, Vmissing, N1–N6, N_PCR_DOUBLE) remain; revision required before implementation

---

## Executive Summary

Seventeen violations were identified across three QA rounds, a test-suite blast radius scan, and
a full production code scan. Violations V1–V5 were found in QA rounds 1–3; V6–V9 in the initial
test scan; Vmissing during config-trein architecture analysis; N1–N6 and N_PCR_DOUBLE in the
subsequent full production code scan. None of V1–V9 have been addressed in v1.1.

The most severe: §2.6/2.7 place enforcement logic inside tool `execute()` methods (V1 + V2 + V3),
which directly contradicts the existing ADR in `docs/architecture/03_tool_layer.md`. N1 creates an
implementation deadlock: no valid path exists under the current §2.6/§2.7 design. N2 shows the
correct pattern (enforcement_event class variable) already exists in the same source file the design
ignores. A required architectural element is missing (Vmissing: `MergeReadinessContext`). Multiple
test files will fail on first run with zero code changes (V6–V9, N_PCR_DOUBLE).

---

## Section 1 — Design Violations (V1–V5 + Vmissing)

### V1 — CRITICAL: §2.6 and §2.7 implement enforcement logic inside tool execute()

**Principle breached:** P13 (enforcement separation), ADR `docs/architecture/03_tool_layer.md`

The ADR explicitly classifies "tool-level enforcement hooks" as a rejected alternative. The current
design §2.6 (`GitCommitTool`) and §2.7 (`CreatePRTool`) both add enforcement logic directly into
`execute()`:

- §2.6: terminal-phase detection + `git rm --cached` auto-exclusion of branch-local artifacts
- §2.7: `current_phase != pr_allowed_phase` gate check + artifact pre-flight check

**Required correction:**

Both tools must only declare their `enforcement_event` class variable. All enforcement logic moves
to new `EnforcementRunner` handlers (see Vmissing).

```python
class GitCommitTool(BaseTool):
    enforcement_event: str | None = "git_commit"
    # execute() unchanged — no enforcement logic added

class CreatePRTool(BaseTool):
    enforcement_event: str | None = "create_pr"
    # execute() unchanged — no enforcement logic added
```

New entries in `.st3/config/enforcement.yaml`:
```yaml
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

New handlers in `EnforcementRunner._build_default_registry()`:
```python
registry["exclude_branch_local_artifacts"] = _exclude_branch_local_artifacts
registry["check_merge_readiness"] = _check_merge_readiness
```

### V2 — CRITICAL: SRP test fails on both tools after applying the design

**Principle breached:** P1.1 Single Responsibility Principle

After the design is applied as written, both `GitCommitTool` and `CreatePRTool` have two
distinct reasons to change:

1. Git/PR mechanics change → change `execute()`
2. Enforcement policy changes (new artifact type, new phase rule) → change `execute()` again

The SRP test: "Can I name a single axis of change for this class?" fails for both tools after §2.6
and §2.7 are applied. This is a direct consequence of V1 but is independently testable — @imp
must verify SRP is restored on each tool after revision.

**Resolved automatically** by fixing V1.

### V3 — MODERATE: OCP violated — new enforcement requires modifying existing tools

**Principle breached:** P1.2 Open/Closed Principle

In the current design, adding a new enforcement rule (e.g., "disallow commit when lint fails")
requires opening and modifying `GitCommitTool.execute()`. In the correct architecture,
adding a new enforcement rule requires only adding a new handler + one enforcement.yaml entry.
The tool itself is closed for modification.

**Resolved automatically** by fixing V1.

### V4 — MODERATE: Law of Demeter — 3-level access chain in handler signatures

**Principle breached:** P6 Law of Demeter

Where design pseudocode accesses `config.merge_policy.pr_allowed_phase` or
`context.merge_readiness.merge_policy.pr_allowed_phase` — this is 3 levels deep from the root.

**Required correction:**

Add a query method to `PhaseContractsConfig`:
```python
def get_pr_allowed_phase(self) -> str:
    return self.merge_policy.pr_allowed_phase
```

`MergeReadinessContext` must be flat by construction (see Vmissing), so handler access is at
most 2 levels: `context.merge_readiness.terminal_phase`.

### V5 — MODERATE: `_inject_terminal_phase` hidden file dependency inside `load_workflow_config`

**Principle breached:** P1.1 SRP, P4 explicit dependency injection

The design §2.5 shows `_inject_terminal_phase` being called inside `load_workflow_config()`, which
internally calls `self.load_workphases_config()` — reading a second YAML file without declaring
this dependency. The caller has no way to know `load_workflow_config()` performs two file reads.

**Impact (see also V8 in Section 2):** All isolated-fixture tests that call
`load_workflow_config()` on a `ConfigLoader` without a `workphases.yaml` file in scope will
fail with `ConfigError`.

**Required correction:**

`_inject_terminal_phase` must receive `workphases_config` as an explicit parameter:

```python
# WRONG (current §2.5)
def load_workflow_config(self) -> WorkflowConfig:
    ...
    return self._inject_terminal_phase(workflow_config)   # hidden second file read

# CORRECT
def _inject_terminal_phase(
    self,
    workflow_config: WorkflowConfig,
    workphases_config: WorkphasesConfig,   # explicit parameter
) -> WorkflowConfig:
    terminal_phase = workphases_config.get_terminal_phase()
    ...
```

The CALLER (`server.py`) loads both configs and passes both:
```python
workflow_config = loader.load_workflow_config()
workphases_config = loader.load_workphases_config()
workflow_config = loader._inject_terminal_phase(workflow_config, workphases_config)
```

This is the pattern `server.py` already follows: load configs independently, compose at the
composition root. Fixing V5 also eliminates test blast radius item V8 automatically.

### Vmissing — CRITICAL: `MergeReadinessContext` facade absent from design

**Principle breached:** P1.1 SRP (EnforcementRunner implicitly coupled to config schemas), P4

Identified during config-trein architecture analysis. The new handlers
(`_exclude_branch_local_artifacts`, `_check_merge_readiness`) need `terminal_phase`,
`pr_allowed_phase`, and `branch_local_artifacts` — from two separate config objects.

The design has no facade that bundles this data. The pattern to follow:
`PhaseConfigContext` at `mcp_server/managers/phase_contract_resolver.py:19` —
a `@dataclass(frozen=True)` that bundles config objects for downstream consumers.

**Required addition to design:**

New dataclass:
```python
@dataclass(frozen=True)
class MergeReadinessContext:
    terminal_phase: str                                   # from WorkphasesConfig.get_terminal_phase()
    pr_allowed_phase: str                                 # from PhaseContractsConfig.get_pr_allowed_phase()
    branch_local_artifacts: list[BranchLocalArtifact]    # from PhaseContractsConfig
```

Construction in `server.py` (composition root), after `ConfigValidator`:
```python
merge_readiness_context = MergeReadinessContext(
    terminal_phase=workphases_config.get_terminal_phase(),
    pr_allowed_phase=phase_contracts_config.get_pr_allowed_phase(),
    branch_local_artifacts=phase_contracts_config.merge_policy.branch_local_artifacts,
)
enforcement_runner = EnforcementRunner(
    workspace_root=workspace_root,
    config=enforcement_config,
    merge_readiness_context=merge_readiness_context,   # new constructor parameter
)
```

`EnforcementRunner` receives it via constructor injection; makes it available to handlers via
`EnforcementContext`. This enables V1's new handlers to work without coupling to config schemas.

---

## Section 2 — Test Suite Blast Radius (V6–V9)

Discovered during final scan. The design contains no test impact analysis. All of these breaks
are guaranteed on first run with zero additional code changes.

### V6 — CRITICAL: `WorkphasesConfig.model_validator` blast radius

**Every** test that constructs `WorkphasesConfig(phases={...})` in memory without a `terminal: true`
entry will fail with `ValidationError` the moment the new `model_validator` is added.

Affected files confirmed:
- `tests/mcp_server/unit/config/test_label_startup.py` lines 104 and 282
- `tests/mcp_server/unit/managers/test_phase_contract_resolver.py` workspace_root fixture
- `tests/mcp_server/unit/tools/test_force_phase_transition_tool.py` (~4 workspace fixtures)
- `tests/mcp_server/core/test_scope_encoder.py` workphases_yaml fixture

**Fix pattern:** Add a terminal phase to every in-memory `WorkphasesConfig` construction and
every inline `workphases.yaml` fixture YAML:
```python
# In-memory
WorkphasesConfig(phases={..., "ready": PhaseDefinition(display_name="Ready", terminal=True)})

# Inline YAML
  documentation:
    display_name: "Documentation"
    terminal: true
```

### V7 — CRITICAL: `merge_policy` required field breaks `test_support.py:238`

**File:** `tests/mcp_server/test_support.py` line 238
**Code:** `phase_contracts_config = PhaseContractsConfig.model_validate({"workflows": {}})`
**Break cause:** This fallback is executed whenever a test workspace has no `phase_contracts.yaml`.
When `merge_policy` becomes required, this raises `ValidationError` across ALL tests routed
through `make_phase_state_engine` — the widest blast radius in the test suite (dozens of tests).

**Fix:**
```python
phase_contracts_config = PhaseContractsConfig.model_validate({
    "workflows": {},
    "merge_policy": {"pr_allowed_phase": "ready", "branch_local_artifacts": []},
})
```

### V8 — CRITICAL: `_inject_terminal_phase` inside `load_workflow_config` breaks isolated-fixture tests

**Break cause:** `TestWorkflowConfigLoading` and `TestTransitionValidation` in
`tests/mcp_server/unit/config/test_workflow_config.py` use isolated `tmp_path` fixtures that
write only `workflows.yaml`. If `load_workflow_config()` internally calls
`self.load_workphases_config()`, the loader raises `ConfigError` (file not found) for the
entire `TestWorkflowConfigLoading` and `TestTransitionValidation` class hierarchies.

Additionally, `test_workflow_config.py:201` asserts an exact phase list:
```python
assert workflow.phases == ["research", "planning", "design", "tdd", "validation", "documentation"]
```
After injection this list gains `"ready"` as the 7th element — assertion fails.

**Fix (primary):** Fix V5 — `_inject_terminal_phase` accepts `workphases_config` as explicit
parameter, called from `server.py` not `load_workflow_config()`. This eliminates the FileNotFound
failures for the entire class without any test changes.

**Fix (secondary):** Update the exact phase list assertion to include `"ready"`.

### V9 — MODERATE: `workflow_fixtures.py` semantic breakage

**File:** `tests/mcp_server/fixtures/workflow_fixtures.py`
**Break cause:** `feature_phases`, `bug_phases`, `hotfix_phases` fixtures load from live
`.st3/config/workflows.yaml` via `ConfigLoader`. After `_inject_terminal_phase` is active in the
load path, `"ready"` is appended as the last element. The semantic contract of these fixtures
changes:

- `feature_phases[-1]` was `"documentation"` → becomes `"ready"`
- `len(feature_phases)` was 6 → becomes 7

**Note:** Forward index access for phases before injection point is safe: `feature_phases[2]`
(`"design"`) is unaffected.

**Fix:** Review and update all tests that assert `[-1]` index identity or exact phase count on
these fixtures.

---

## Section 2b — Production Code Scan Findings (N1–N6, N_PCR_DOUBLE)

Discovered during the full production code scan (research + design + all production + all test code).
These were not visible in the design-layer or test-layer analyses performed earlier.

### N1 — CRITICAL: enforcement.yaml deadlock — no valid implementation path exists

**File:** `mcp_server/managers/enforcement_runner.py`
**Method:** `_validate_registered_actions()`

`EnforcementRunner._validate_registered_actions()` raises `ConfigError` at startup for every
action `type` listed in `enforcement.yaml` that has no registered handler in
`_build_default_registry()`. This is a fail-fast guard — correct design for known action types.

The deadlock under the current §2.6/§2.7 plan:

- **Option A:** Update `enforcement.yaml` with `exclude_branch_local_artifacts` and
  `check_merge_readiness` **before** registering handlers → startup `ConfigError` on next boot.
- **Option B:** Skip updating `enforcement.yaml` → P13 violated; enforcement never runs.
- **Option C:** Register handlers without updating `enforcement.yaml` → dead code, enforcement
  never triggered.

There is no ordering through which the current design delivers working enforcement without
triggering a startup crash or silently skipping enforcement. The V1 fix (enforcement_event class
variable pattern) resolves this automatically: handlers are registered before config validation,
so atomic flag-day ships both together safely.

**Evidence:** `enforcement_runner.py._validate_registered_actions()` — the guard is real and tested.

### N2 — CRITICAL: Correct pattern already exists in same file — design regresses against it

**File:** `mcp_server/tools/git_tools.py`, line 121
**Code:** `enforcement_event = "create_branch"` on `CreateBranchTool`

`CreateBranchTool` in the same file as `GitCommitTool` already uses the correct pattern:
```python
class CreateBranchTool(BaseTool):
    enforcement_event = "create_branch"
    # execute() has no enforcement logic
```

The design §2.6 ignores this and proposes adding enforcement into `GitCommitTool.execute()` —
architecturally regressive against its own sibling in the same module. The implementer would be
asked to write code that contradicts a pattern they can read on line 121 of the file they are
editing.

**Required correction:** Follow `CreateBranchTool` exactly. `GitCommitTool.enforcement_event = "git_commit"`, no `execute()` changes.

### N3 — MODERATE: D6 self-contradiction — pure transform label violates its own impl

**Design Decision D6 (as written):** "_inject_terminal_phase returns a new WorkflowConfig; source
object never mutated."

D6 classifies `_inject_terminal_phase` as a pure transform (input → new output, no side effects).
Yet §2.5 places the call inside `load_workflow_config()`, which calls
`self.load_workphases_config()` internally — a file I/O side effect inside the declared-pure
function. The design contradicts its own stated decision.

**Required correction:** V5 fix (explicit `workphases_config` parameter) is required to make D6
true. The §2.5 description must be updated to reflect the corrected calling convention; D6 then
holds without reservation.

### N4 — MODERATE: §2.8 deployment checklist incomplete — flag-day will fail at startup

**Section:** §2.8 (Flag Day migration)

§2.8 mentions only `.gitattributes` removal and code ship. It omits the two config files that
must be updated atomically with the code change:

1. `.st3/config/workphases.yaml` — must add `ready` phase with `terminal: true`; without this,
   `WorkphasesConfig.model_validator` raises `ValidationError` at startup.
2. `.st3/config/phase_contracts.yaml` — must add `merge_policy` section; without this,
   `PhaseContractsConfig` raises `ValidationError` at startup (if `merge_policy` is required).

Both config files are confirmed absent these fields in the live baseline. A deployment that ships
only code without these config updates will fail on first startup.

**Required correction:** §2.8 must enumerate an explicit atomic checklist:
1. Update `workphases.yaml` — add terminal phase
2. Update `phase_contracts.yaml` — add merge_policy section
3. Ship code (fail-fast startup validates both on next boot)

### N5 — MODERATE: P4 fail-fast gap — `pr_allowed_phase` not cross-validated in ConfigValidator

**File:** `mcp_server/config/validator.py`
**Method:** `_validate_workflow_phases()`

`ConfigValidator._validate_workflow_phases()` cross-validates workflow phase names against
known workphases (prevents typos). There is no equivalent check for
`merge_policy.pr_allowed_phase: str`.

A typo in `phase_contracts.yaml` (e.g., `pr_allowed_phase: redy`) passes Pydantic type
validation (it's a valid string), passes `ConfigValidator`, and silently disables PR
enforcement at runtime with no warning.

**Evidence:**  `_validate_workflow_phases()` in `validator.py` is the reference pattern to follow.

**Required correction:** Add `_validate_merge_policy_phase()` to `ConfigValidator`:
```python
def _validate_merge_policy_phase(
    self,
    phase_contracts_config: PhaseContractsConfig,
    workphases_config: WorkphasesConfig,
) -> None:
    pr_phase = phase_contracts_config.merge_policy.pr_allowed_phase
    if pr_phase not in workphases_config.phases:
        raise ConfigError(f"pr_allowed_phase '{pr_phase}' not in known workphases")
```

### N6 — MODERATE: §2.5 injection ordering unspecified — wrong order breaks validator

**Section:** §2.5 (ConfigLoader._inject_terminal_phase)

If V5 is fixed (injection moved to `server.py` composition root), the loading sequence in
`server.py` must be:

1. `load_workflow_config()` — loads raw workflow (no terminal phase yet)
2. `load_workphases_config()` — loads workphases (terminal phase defined here)
3. `_inject_terminal_phase(workflow_config, workphases_config)` — enriches workflow
4. `ConfigValidator(enriched_workflow_config, workphases_config, ...)` — validates enriched result

If step 4 runs before step 3, the validator sees the un-enriched workflow (terminal phase absent)
and may produce false-negative or false-positive validation results. The design §2.5 does not
specify this ordering constraint.

**Required correction:** §2.5 must state the explicit ordering guarantee:
> "Injection must precede ConfigValidator construction. The caller (`server.py`) is responsible
> for passing the enriched WorkflowConfig to ConfigValidator."

**Current `server.py` (line 237):** `EnforcementRunner(workspace_root, config=enforcement_config)` —
`MergeReadinessContext` not yet passed. Injection ordering must be specified before this is
extended.

### N_PCR_DOUBLE — CRITICAL: test_phase_contract_resolver.py has two independent blast points

**File:** `tests/mcp_server/unit/managers/test_phase_contract_resolver.py`
**Fixture:** `workspace_root`

The `workspace_root` fixture writes both an inline `workphases.yaml` **and** an inline
`phase_contracts.yaml`. Both are missing the new required fields:

- Inline `workphases.yaml`: no `terminal: true` entry → triggers V6 `ValidationError`
- Inline `phase_contracts.yaml`: no `merge_policy` section → triggers V7 `ValidationError`

These are two **independent** blast points in a single fixture. Fixing only one leaves the other
active. Both must be updated atomically or the fixture continues to fail.

**Fix:**
```yaml
# workphases.yaml fixture
phases:
  research:
    display_name: "Research"
  ...
  ready:
    display_name: "Ready"
    terminal: true
```
```yaml
# phase_contracts.yaml fixture
workflows:
  ...
merge_policy:
  pr_allowed_phase: ready
  branch_local_artifacts: []
```

---

## Section 3 — Items Confirmed Correct (Do Not Change)

- **§2.1 — `PhaseDefinition.terminal: bool = False`**: correct. Default `False` preserves
  backward-compatible YAML loading before flag-day config update.
- **§2.2 — `WorkphasesConfig.model_validator`**: requiring exactly one terminal phase is correct.
  `get_terminal_phase()` return type and semantics are correct.
- **§2.3 — `BranchLocalArtifact` and `MergePolicy` schemas**: correct. `merge_policy` being
  required (not `Optional`) is correctly designed.
- **§2.4 — `PhaseContractsConfig` extension**: correct. Add `get_pr_allowed_phase()` query method
  (V4 fix).
- **§2.5 PARTIAL — `_inject_terminal_phase` algorithm**: injection logic (check then append) is
  correct. Only the calling convention must change (V5).
- **§2.8 — Flag Day migration note**: correct intent, but checklist is incomplete (N4).
- **§2.9 — Error message specifications**: all messages correctly specified.

---

## Section 4 — Required Deliverables from Revised Design (v2.0)

1. **§2.6 rewrite**: `GitCommitTool` adds `enforcement_event = "git_commit"` class variable only.
   No `execute()` changes. Reference new `enforcement.yaml` entry and handler. (V1, N2)
2. **§2.7 rewrite**: `CreatePRTool` adds `enforcement_event = "create_pr"` class variable only.
   No `execute()` changes. Reference new `enforcement.yaml` entry and handler. (V1)
3. **§2.NEW — `MergeReadinessContext`**: full schema, construction in `server.py`, injection into
   `EnforcementRunner`, usage by new handlers. (Vmissing)
4. **§2.NEW2 — New enforcement handlers**: `_exclude_branch_local_artifacts` and
   `_check_merge_readiness` pseudocode. These are the only locations where enforcement logic lives.
5. **§2.5 update**: `_inject_terminal_phase` signature with explicit `workphases_config` parameter;
   updated calling convention (`server.py` calls it after independent loads). (V5, N3, N6)
6. **§3 (Test Strategy) update**: enumerate V6–V9 + N_PCR_DOUBLE with concrete fix per item.
7. **§2.8 atomic checklist update**: enumerate `workphases.yaml` + `phase_contracts.yaml` updates
   as required steps before code ship. (N4)
8. **ConfigValidator extension**: add `_validate_merge_policy_phase()` cross-validating
   `pr_allowed_phase` against known workphases. (N5)
9. **§2.5 injection ordering note**: explicit statement that injection precedes ConfigValidator
   construction; `server.py` caller responsibility. (N6)
10. **Status**: bump to v2.0; Status remains FINAL only after QA re-review.

---

## Section 5 — MCPServer Refactoring (Out of Scope for #283)

`server.py` (~530 lines) mixes composition root assembly and runtime protocol dispatch — pre-existing
debt, not introduced by #283. Adding `MergeReadinessContext` construction to `MCPServer.__init__`
IS correct for #283 (follows existing `PhaseConfigContext` pattern, does not worsen the debt).

Separate tracking: **Issue #285** — `Separate MCPServer composition root from runtime dispatch`
(type:refactor, priority:medium, scope:architecture). Do not address within #283.

---

## Section 6 — Violation Summary Table

| ID | Severity | Round Found | Status | Section |
|----|----------|-------------|--------|---------|
| V1 | CRITICAL | Round 3 | Open | §2.6, §2.7 |
| V2 | CRITICAL | Round 3 | Open (resolved by V1 fix) | §2.6, §2.7 |
| V3 | MODERATE | Round 3 | Open (resolved by V1 fix) | §2.6, §2.7 |
| V4 | MODERATE | Round 3 | Open | §2.4, handler signatures |
| V5 | MODERATE | Round 3 | Open | §2.5 |
| Vmissing | CRITICAL | Config-trein analysis | Open | Missing from design |
| V6 | CRITICAL | Final scan | Open | test_label_startup.py, 4 fixture files |
| V7 | CRITICAL | Final scan | Open | test_support.py:238 |
| V8 | CRITICAL | Final scan | Open | test_workflow_config.py (whole classes) |
| V9 | MODERATE | Final scan | Open | workflow_fixtures.py |
| N1 | CRITICAL | Production code scan | Open | enforcement_runner.py — startup deadlock |
| N2 | CRITICAL | Production code scan | Open | git_tools.py:121 — correct pattern ignored |
| N3 | MODERATE | Production code scan | Open | D6 self-contradiction in design |
| N4 | MODERATE | Production code scan | Open | §2.8 deployment checklist incomplete |
| N5 | MODERATE | Production code scan | Open | ConfigValidator — pr_allowed_phase gap |
| N6 | MODERATE | Production code scan | Open | §2.5 injection ordering unspecified |
| N_PCR_DOUBLE | CRITICAL | Production code scan | Open | test_phase_contract_resolver.py — dual blast |

**Critical count: 8 (V1, V2, Vmissing, V6, V7, V8, N1, N2, N_PCR_DOUBLE)**
**Moderate count: 5 (V3, V4, V5, V9, N3, N4, N5, N6)** *(V2, V3 auto-resolve with V1 fix)*
*(N_PCR_DOUBLE auto-resolves with V6+V7 fixes if applied atomically)*

---

## Section 7 — Reference Map

| Symbol | File |
|--------|------|
| `PhaseConfigContext` (facade pattern) | `mcp_server/managers/phase_contract_resolver.py` (line 19) |
| `EnforcementRunner._build_default_registry` | `mcp_server/managers/enforcement_runner.py` |
| `EnforcementRunner._validate_registered_actions` | `mcp_server/managers/enforcement_runner.py` |
| `CreateBranchTool.enforcement_event` (N2 reference) | `mcp_server/tools/git_tools.py` (line 121) |
| `PhaseContractsConfig` | `mcp_server/config/schemas/phase_contracts_config.py` (line 53) |
| `WorkphasesConfig` | `mcp_server/config/schemas/workphases.py` |
| `load_workflow_config` | `mcp_server/config/loader.py` (line 109) |
| `ConfigValidator._validate_workflow_phases` (N5 pattern) | `mcp_server/config/validator.py` |
| `test_support.py` blast point | `tests/mcp_server/test_support.py` (line 238) |
| `N_PCR_DOUBLE` fixture | `tests/mcp_server/unit/managers/test_phase_contract_resolver.py` |
| `enforcement.yaml` | `.st3/config/enforcement.yaml` |
| ADR tool layer | `docs/architecture/03_tool_layer.md` |
| MCPServer God Class issue | GitHub Issue #285 |
