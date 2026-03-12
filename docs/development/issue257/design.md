# Design: Config-First PSE Architecture

**Status:** In Progress — design phase active
**Issue:** #257
**Branch:** feature/257-reorder-workflow-phases
**Last updated:** 2026-03-12

---

## Purpose

This document records the formal design decisions for issue #257 — the Config-First PSE architecture. It is extracted from the research document (`research_config_first_pse.md`) which serves as source reference and decision backlog.

> **Rule:** New design rounds happen here. The research document is frozen as source + backlog.

---

## Scope (quick reference)

**New components:**
- `phase_contracts.yaml` — per-workflow×phase enforcement contract (renamed from `phase_deliverables.yaml`)
- `enforcement.yaml` — phase- and tool-level enforcement rules (renamed from `lifecycle.yaml`)
- `deliverables.json` — issue-specific additief register for TDD/cycle planning
- `AtomicJsonWriter` — shared utility for all atomic JSON writes
- `PhaseContractResolver` — SRP class combining config-layer + registry-layer into `list[CheckSpec]`
- `StateRepository` — SRP class for atomic state read/write (extracted from PSE)
- `EnforcementRunner` — replaces HookRunner, handles phase + tool enforcement events
- `IStateReader` + `IStateRepository` — ISP-split Protocols in `core/interfaces/`

**Key renames:** `tdd` → `implementation` (phase), `lifecycle.yaml` → `enforcement.yaml`, `HookRunner` → `EnforcementRunner`, `phase_deliverables.yaml` → `phase_contracts.yaml`, `PhaseDeliverableResolver` → `PhaseContractResolver`, `current_tdd_cycle` → `current_cycle`

**Removed:** `projects.json`, `_extract_issue_from_branch()` in PSE, deprecated `phase` parameter in `git_add_or_commit`

---

## Design Decisions

### A — `phase_contracts.yaml` Schema

#### A1 — Field defaults and startup validation

**Decision:** Fields are optional with defaults: `subphases: []`, `commit_type_map: {}`, `cycle_based: false`. The loader fills in missing fields with these defaults.

**Fail-Fast constraint:** The loader validates at startup: `cycle_based: true` + `commit_type_map: {}` = `ConfigError`. A cycle-based phase without a commit_type_map causes a silent failure on the first commit. The error is detected at server startup, not at runtime.

#### A3 — `cycle_based` is a boolean

**Decision:** `cycle_based` is a boolean. `max_cycles` is a planning artifact stored in `deliverables.json`, not in config. No range check at config level.

#### A5 — Two files, two responsibilities

**Decision:** `workphases.yaml` = pure phase metadata (display_name, description, subphase whitelist). `phase_contracts.yaml` = per-workflow×phase contracts (exit_requires, commit_type_map, cycle_based). No overlap.

#### A6 — Required vs. recommended gate distinction + tamper detection

**Decision:** Issue-specific gates may *extend* (`recommended`) but may **not** override `required` config gates. Merge order in `PhaseContractResolver`:
- `required` gates in `phase_contracts.yaml`: immutable contract, never overridable by issue-specific entries
- `recommended` gates: extendable and overridable via `deliverables.json`, but only via authorized tools (`save_planning_deliverables`, `update_planning_deliverables`)

The `required`/`recommended` distinction is a field on each gate-spec in `phase_contracts.yaml`. Tamper detection for `deliverables.json` (SHA-256 sidecar) is issue #261 — outside scope of this issue.

---

### B — `deliverables.json` Schema and Lifecycle

#### B1 — JSON structure

**Decision:** Nested: `{ "257": { "phases": { "design": [...], "implementation": {...} }, "created_at": "...", "workflow_name": "feature" } }`. Nested structure allows issue-level metadata alongside phase entries.

#### B2 — Mutability and completed-cycle guard

**Decision:** Mutable. `save_planning_deliverables` creates, `update_planning_deliverables` modifies.

**Guard:** `update_planning_deliverables` contains a guard on closed cycles: a cycle in `cycle_history` (status: completed) is read-only. Attempting to modify raises `ValidationError`. Open cycles are mutable.

#### B3 — 1-writer principle

**Decision:** Only `save_planning_deliverables` and `update_planning_deliverables` write to `deliverables.json`. Shared private `AtomicJsonWriter` utility for all JSON writes (incl. `state.json`), so atomic writing is implemented in one place.

#### B4 — Post-merge cleanup via enforcement

**Decision:** Delete on PR merge. Config over code: cleanup is a `post_merge` lifecycle action in `enforcement.yaml`, not hardcoded in Python. Git history is the ultimate source of truth after merge.

#### B5 — state.json git-tracked per branch + startup guard

**Decision:** `state.json` removed from `.gitignore` so it is tracked per branch in git. After branch switch, `state.json` of that branch is available via git checkout.

**Enforcement:** A `post`-enforcement rule on `transition_phase` triggers `commit_state_files` action, ensuring uncommitted `state.json` is never silently lost.

**Startup guard:** PSE checks at `initialize_branch()` whether `state.json` has uncommitted local changes not from a known tool call. If so: explicit warning to the agent (Explicit over Implicit). Not blocked, not silently ignored.

---

### C — `projects.json` Abolishment

#### C2/C3 — Single-branch state + graceful degradation

**Decision:** Single-branch `state.json` remains — `projects.json` as multi-branch register is abolished. GitHub issues + local git branches are single source of truth.

Mode 2 reconstruction graceful degradation: `workflow_name: "unknown"` if GitHub API is unreachable. Offline scenario is not a priority.

#### C4 — Flag-day

**Decision:** Flag-day. `projects.json` is deleted. Existing entries are not migrated. Consistent with BC approach (see F24 in research).

---

### D — `PhaseContractResolver` Interface

#### D1 + D5 — Explicit cycle_number parameter

**Decision (DIP):** `cycle_number` as explicit parameter. Signature: `resolve(workflow_name: str, phase: str, cycle_number: int | None) -> list[CheckSpec]`. Tool layer reads `cycle_number` from `StateRepository` and passes it explicitly. `PhaseContractResolver` has no dependency on `StateRepository`.

#### D2 — CheckSpec is a Pydantic model

**Decision:** Pydantic model. Already in the stack (`pydantic>=2.5.0`). Gives runtime validation when loading `phase_contracts.yaml` entries and a type-safe interface with `DeliverableChecker`.

#### D3 — Empty list is normal

**Decision:** Empty list is normal and not an error. Example: `docs` workflow has no `implementation` phase in `phase_contracts.yaml` — resolver returns `[]` without error.

#### D4 — ConfigError from resolver

**Decision:** `ConfigError` with `file_path=".st3/config/phase_contracts.yaml"`. `ConfigError` is a subclass of `MCPError` and is caught by `@tool_error_handler` on the tool layer. No try/except needed in PSE or manager.

---

### E — `StateRepository` Interface

#### E1 — Abstract base class

**Decision:** ABC (`abc.ABC` + `@abstractmethod`). Production: `FileStateRepository(StateRepository)`. Tests: `InMemoryStateRepository(StateRepository)`. Constructor injection.

#### E2 — Typed return: BranchState (Pydantic, frozen)

**Decision:** Typed Pydantic model `BranchState`. Consistent with D2 (CheckSpec is also Pydantic). Pyright-strict compatible, runtime validation when reading `state.json`.

`BranchState` is declared with `model_config = ConfigDict(frozen=True)`. The type system enforces CQS: queries can never mutate.

#### E3 — AtomicJsonWriter utility

**Decision:** Temp-file + rename moves to shared `AtomicJsonWriter` utility (see B3). No new dependency on `filelock`. Existing approach proven on Windows (Issue #85).

#### E4 — ISP split: IStateReader + IStateRepository

**Decision:** `IStateReader` (Protocol): `load()` only — for read-only consumers (ScopeDecoder, PhaseContractResolver). `IStateRepository(IStateReader)` (Protocol): `load()` + `save()` — for writing consumers (PSE, EnforcementRunner).

`FileStateRepository` implements both via structural subtyping. Interfaces live in `mcp_server/core/interfaces/`.

---

### F — PSE OCP Hook Registry → enforcement.yaml

#### F1 — enforcement.yaml explicit structure

**Decision:** YAML in `.st3/enforcement.yaml`. Enforcement works on two levels: phase events and tool-call events. Explicit field structure — no implicit key-encoding:

```yaml
enforcement:
  - event_source: phase
    phase: planning
    timing: exit
    actions:
      - type: check_deliverable

  - event_source: tool
    tool: transition_phase
    timing: post
    actions:
      - type: commit_state_files
        paths: [".st3/state.json"]
        message: "chore: persist state after phase transition"

  - event_source: tool
    tool: create_branch
    timing: pre
    actions:
      - type: check_branch_policy
        policy: base_restriction

  - event_source: merge
    timing: post
    actions:
      - type: delete_file
        path: .st3/state.json
      - type: delete_file
        path: .st3/registries/deliverables.json
```

`event_source`, `timing`, and the identifier are each separately validated Pydantic fields. Identified action types: `check_deliverable`, `state_mutation`, `delete_file`, `commit_state_files`, `check_branch_policy`.

#### F2 — Plugin registration at startup + fail-fast

**Decision:** Plugin pattern (module registration at startup) + fail-fast. At server startup each module registers its action-handler. The `enforcement.yaml` loader validates at startup that every `type` name has a registered handler — `ConfigError` if not.

#### F3 — EnforcementRunner + BaseTool class variable (Option C)

**Decision:** `EnforcementRunner` as separate service. PSE's responsibility: validate and persist state transitions. `EnforcementRunner` orchestrates enforcement rules, delegating to SRP-helpers per action type.

**Tool-level enforcement — Option C:** `BaseTool` declares `enforcement_event: str | None = None` as a **class variable**. `EnforcementRunner` is injected at server dispatch level — not in each tool. Each tool declares its event declaratively:

```python
class TransitionPhaseTool(BaseTool):
    name = "transition_phase"
    enforcement_event = "transition_phase"  # declarative, visible in class
```

At dispatch: `runner.run(tool.enforcement_event, timing="pre"|"post", context)`.

#### F4 — EnforcementRegistry testable via constructor injection

**Decision:** Trivially testable via constructor injection of a fake `EnforcementRegistry` with no-op action-handlers. `EnforcementRunner` is independently testable from PSE and server-dispatcher. Each action-helper is independently testable with its own unit tests.

#### F5 — force_transition uses same hooks with exception catching

**Decision (Option C):** `force_transition()` calls the same hooks as `transition()`. Exceptions (`DeliverableCheckError`, `ConfigError`) are caught by PSE and returned as active warnings in the ToolResult — not blocked, not silently ignored.

The blocking/warn distinction is a transition-mechanism property, not a hook property. Tool separation (`transition` vs `force_transition`) is the enforcement mechanism for requiring human approval.

---

### G — Consumer Consolidation

#### G1 + G2 — WorkflowConfig consolidated, ClassVar pattern

**Decision:** `workflow_config.py` deleted. All methods (`get_workflow`, `validate_transition`, `get_first_phase`, `has_workflow`) in one `WorkflowConfig` in `workflows.py`. All callers migrate to this single import path. Module-level singleton removed, replaced with `ClassVar` + lazy init pattern.

#### G3 — PhaseConfigContext facade

**Decision:** `PhaseConfigContext` facade (dataclass with `workphases: WorkphasesConfig` + `phase_contracts: PhaseContractsConfig`). Injected via constructor. Tests inject one mock object.

---

### H — `tdd` → `implementation` Rename

#### H1 — Manual fix for existing state.json files

**Decision:** Manual fix if needed. No automatic migration at startup, no backward-compat read code.

#### H2 — Full removal, no alias

**Decision:** Fully removed. No alias, no deprecation period. Consistent with flag-day BC approach.

#### H3 — GitHub labels unchanged

**Decision:** GitHub labels (`phase:tdd`, `phase:red`, etc.) retained as-is. External system, label migration is overkill. `phase:red`, `phase:green`, `phase:refactor` remain valid as sub-labels of `implementation`.

#### H4 — `docs` workflow has no implementation phase

**Decision:** Phase absent from `phase_contracts.yaml` for the `docs` workflow. Resolver returns `[]` (see D3).

---

### I — branch_name_pattern and branch_types

#### I1 — Name-only pattern + fail-fast combined validation

**Decision:** `branch_name_pattern` validates the name-part (after the slash) only. `GitConfig` builds the combined validation pattern dynamically via `build_branch_type_regex()` + name pattern. Applied fail-fast at `create_branch()`.

Combined pattern: `^{build_branch_type_regex()}/{branch_name_pattern.lstrip('^')}` — config-driven, built once at startup.

#### I2 — Branch policies as enforcement rules

**Decision:** Branch policies (`base_restrictions`, `merge_targets`) modeled as enforcement rules in `enforcement.yaml` with `event_source: tool, tool: create_branch, timing: pre`. No separate branch policies config file.

#### I3 — GitConfig.extract_issue_number() (Option B)

**Decision:** `GitConfig.extract_issue_number(branch: str) -> int | None` as its own method on `GitConfig`. Extraction of an issue number from a branch name is a question about git conventions — the domain of `GitConfig`. PSE `_extract_issue_from_branch()` is deleted. PSE gets `GitConfig` as injectable dependency.

---

### J — commit_type_map Availability in Tool Layer

#### J1 — Tool layer resolves (Option A)

**Decision:** Option A — tool layer is composition root. `GitManager.commit_with_scope()` receives `commit_type` as explicit parameter. `PhaseContractResolver` sits in the tool layer. `GitManager` remains pure and has no dependency on `PhaseContractResolver`.

#### J2 — PSE.get_state(branch) → BranchState (Option B)

**Decision:** `PSE.get_state(branch: str) -> BranchState` as public method. PSE delegates internally to `StateRepository` for I/O (DIP). Tool layer talks to PSE as single point of contact (Law of Demeter). `get_current_phase()` becomes a convenience wrapper over `get_state()`.

`BranchState` declared with `model_config = ConfigDict(frozen=True)` — CQS enforced by type system.

#### J3 — Legacy `phase` parameter dropped (Option a)

**Decision:** Legacy `phase` parameter fully dropped. Breaking change, all callers already use `workflow_phase` (renamed to `phase` per F23 in research). Backward-compat tests deleted.

#### J4 — ConfigError from PhaseContractResolver

**Decision:** `ConfigError` with `file_path=".st3/config/phase_contracts.yaml"`. Caught by `@tool_error_handler` on tool layer.

---

## Interface Specifications

### BranchState (Pydantic, frozen)

```python
class BranchState(BaseModel):
    model_config = ConfigDict(frozen=True)

    branch: str
    workflow_name: str
    current_phase: str
    current_cycle: int | None = None
    last_cycle: int | None = None
    cycle_history: list[dict[str, Any]] = Field(default_factory=list)
    required_phases: list[str] = Field(default_factory=list)
    execution_mode: str = "normal"
    skip_reason: str | None = None
    issue_title: str | None = None
    parent_branch: str | None = None
    created_at: str | None = None
```

### IStateReader / IStateRepository (Protocols in core/interfaces/)

```python
class IStateReader(Protocol):
    def load(self, branch: str) -> BranchState: ...

class IStateRepository(IStateReader, Protocol):
    def save(self, state: BranchState) -> None: ...
```

### CheckSpec (Pydantic)

```python
class CheckSpec(BaseModel):
    id: str
    type: str                    # "file_glob", "heading_present", etc.
    required: bool = True        # required vs. recommended
    file: str | None = None
    heading: str | None = None
    # ... type-specific fields
```

---

## Architecture Diagram (Component Boundaries)

```
                   Tool Layer (composition root)
┌─────────────────────────────────────────────────────┐
│  TransitionPhaseTool                                 │
│  GitCommitTool  enforcement_event = "transition_..." │
│  CreateBranchTool                                    │
└───────┬──────────────────────┬──────────────────────┘
        │ PSE.get_state()       │ PhaseContractResolver.resolve()
        ▼                       ▼
  ┌──────────┐          ┌──────────────────────┐
  │   PSE    │          │  PhaseContractResolver│
  │          │          │  (config + registry)  │
  └────┬─────┘          └──────────────────────┘
       │ IStateRepository        ▲
       ▼                    IStateReader
  ┌──────────────────┐
  │ FileStateRepository │  ← AtomicJsonWriter
  └──────────────────┘

  EnforcementRunner  ← enforcement.yaml (YAML-driven rules)
  (injected at dispatch level, not per tool)
```

---

## Related Documentation

- **Research + decision backlog:** [research_config_first_pse.md](research_config_first_pse.md)
- **KPI definitions:** [research_config_first_pse.md — Expected Results section](research_config_first_pse.md)
- **Issue:** #257
- **Tamper detection (deliverables.json):** Issue #261

---

## Version History

| Date | Author | Change |
|---|---|---|
| 2026-03-12 | agent | Initial extraction from research document — all A–J decisions formalized |
