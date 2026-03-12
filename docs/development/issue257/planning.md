<!-- docs\development\issue257\planning.md -->
<!-- template=planning version=130ac5ea created=2026-03-12T12:19Z updated= -->
# Config-First PSE Architecture — Implementation Planning

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-12

---

## Purpose

Break down the design decisions from design.md (A–J) into six ordered, independently-testable implementation cycles. Each cycle has explicit stop/go criteria before the next cycle begins. Ordered for risk reduction: foundations and renames first, core abstractions second, then config layer, tool layer integration, enforcement, and deliverables tooling last.

## Scope

**In Scope:**
All components from design.md: phase_contracts.yaml, enforcement.yaml, deliverables.json, AtomicJsonWriter, PhaseContractResolver, StateRepository, EnforcementRunner, IStateReader/IStateRepository, PSE refactor, GitConfig.extract_issue_number(), tdd→implementation rename, projects.json abolishment

**Out of Scope:**
SHA-256 tamper detection for deliverables.json (issue #261); performance optimizations; multi-project support; backward-compatible migration layer

## Prerequisites

Read these first:
1. design.md APPROVED — all A–J decisions finalized
2. Branch feature/257-reorder-workflow-phases active, planning phase
3. Existing test suite green before cycle 1 starts
---

## Summary

Six implementation cycles that incrementally refactor the Phase State Engine to a Config-First architecture. Ordered by risk reduction: foundations and renames first, core abstractions second, then config layer, tool layer integration, enforcement, and finally deliverables tooling. Each cycle is independently testable and leaves the system in a deployable state.

---

## Dependencies

- Cycle 2 depends on Cycle 1: BranchState model references 'implementation' phase name
- Cycle 3 depends on Cycle 2: PhaseContractResolver receives IStateReader via constructor injection
- Cycle 4 depends on Cycles 2+3: PSE.get_state() returns BranchState; tool layer calls PCR.resolve()
- Cycle 5 depends on Cycle 4: EnforcementRunner injected at dispatch level alongside PSE
- Cycle 6 depends on Cycle 5: post-merge cleanup is an enforcement.yaml action; delete_file handler must exist

---

## TDD Cycles

### Cycle 1: Foundations & Renames (H + G + I3 + C)

**Design decisions:** H1–H4, G1–G2, I3, C2–C4

**Goal:** Eliminate dead code and rename all moving parts before new abstractions are introduced. Flag-day: `tdd` → `implementation`, `workflow_config.py` deleted, `GitConfig.extract_issue_number()` added, `projects.json` abolished.

**Tests:**
- All existing workflow tests pass with `implementation` replacing `tdd` in config and code
- `WorkflowConfig` methods (`get_workflow`, `validate_transition`, `get_first_phase`, `has_workflow`) available from `workflows.py` import path
- `GitConfig.extract_issue_number('feature/42-name')` returns `42`; returns `None` for branch without number
- PSE no longer contains `_extract_issue_from_branch()`; `GitConfig` injected instead
- `projects.json` does not exist; all references in PSE and ProjectManager removed
- No `import` from `workflow_config.py` anywhere in the codebase

**Success Criteria:**
- Full test suite green (no regressions)
- `grep` finds zero occurrences of `phase_deliverables`, `PhaseDeliverableResolver`, `HookRunner`, `workflow_config` in source
- `grep` finds zero occurrences of `projects.json` in source code (docs excluded)

**Stop/Go:** ✅ Go to Cycle 2 only if all three success criteria pass.

---

### Cycle 2: StateRepository + BranchState + AtomicJsonWriter (E + B3)

**Design decisions:** E1–E4, B3

**Goal:** Extract state I/O from PSE into a dedicated SRP component. Introduce `BranchState` (frozen Pydantic), `IStateReader`/`IStateRepository` Protocols, `FileStateRepository`, `InMemoryStateRepository`, and `AtomicJsonWriter`.

**Tests:**
- `BranchState` is a frozen Pydantic model; mutating any field raises `ValidationError`
- `FileStateRepository.load()` returns correct `BranchState` from `state.json` fixture
- `FileStateRepository.save()` writes `state.json` atomically (temp-file + rename; no partial writes)
- `InMemoryStateRepository` load/save round-trip without touching filesystem
- `AtomicJsonWriter` crash-test: simulate crash between write and rename; original file intact
- PSE receives `IStateRepository` via constructor injection; no direct file I/O in PSE
- `IStateReader`-typed consumers (`ScopeDecoder`, `PhaseContractResolver` stub) accept `IStateReader` and are rejected by Pyright when passed `IStateRepository`-only subtype

**Success Criteria:**
- PSE unit tests use `InMemoryStateRepository` (zero filesystem dependency in unit tests)
- Pyright `--strict` passes on `core/interfaces/`, state module, and PSE module
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 3 only if Pyright strict passes and InMemoryStateRepository is the default in all PSE unit tests.

---

### Cycle 3: phase_contracts.yaml loader + PhaseContractResolver (A + D + G3)

**Design decisions:** A1, A3, A5, A6, D1–D5, G3

**Goal:** Introduce the config layer: `phase_contracts.yaml` schema with Fail-Fast loader, `CheckSpec` Pydantic model, `PhaseContractResolver.resolve()`, and `PhaseConfigContext` facade.

**Tests:**
- Loader raises `ConfigError` at startup if `cycle_based: true` and `commit_type_map: {}` (decision A1)
- Loader fills missing fields with defaults: `subphases: []`, `commit_type_map: {}`, `cycle_based: false`
- `PhaseContractResolver.resolve('feature', 'implementation', cycle_number=1)` returns correct `list[CheckSpec]` from fixture YAML
- `PhaseContractResolver.resolve('docs', 'implementation', None)` returns `[]` without error (D3)
- `required=True` gates cannot be overridden by `deliverables.json` entries (resolver merge logic)
- `PhaseContractResolver` has no `import` of `StateRepository` or `pathlib.glob`
- `PhaseConfigContext` facade: tests inject one mock; resolver and workphases config both accessible
- `ConfigError` carries `file_path='.st3/config/phase_contracts.yaml'`

**Success Criteria:**
- Fail-Fast test passes: invalid `phase_contracts.yaml` raises `ConfigError` before first tool call
- Resolver returns `[]` for unknown phase (no exception)
- Pyright `--strict` passes on `PhaseContractResolver`, `CheckSpec`, `PhaseConfigContext`
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 4 only if Fail-Fast test and Pyright strict both pass.

---

### Cycle 4: Tool layer integration + PSE.get_state() + legacy param drop (J)

**Design decisions:** J1–J4

**Goal:** Wire the tool layer as composition root: `PSE.get_state(branch)` returns frozen `BranchState`, `GitManager.commit_with_scope()` receives `commit_type` as explicit parameter, legacy `phase=` parameter fully removed from `git_add_or_commit`.

**Tests:**
- `PSE.get_state('feature/42-name')` returns `BranchState` with correct fields
- `PSE.get_current_phase()` is a convenience wrapper over `get_state().current_phase`
- `GitManager.commit_with_scope(message, commit_type)` generates scoped commit message; no `PhaseContractResolver` dependency in `GitManager`
- `git_add_or_commit` tool raises `ValidationError` when called with legacy `phase=` kwarg
- Zero `phase=` kwargs remaining in `mcp_server/tools/`
- `TransitionPhaseTool` integration test: reads `cycle_number` from `PSE.get_state()`, passes it to `PCR.resolve()`, passes `commit_type` to `GitManager`

**Success Criteria:**
- `grep` finds zero `phase=` kwargs in `mcp_server/tools/` and `tests/`
- Backward-compat tests deleted (no dead test code)
- Pyright `--strict` passes on all tool files and PSE public API
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 5 only if grep check and Pyright strict both pass.

---

### Cycle 5: enforcement.yaml + EnforcementRunner (F + F3 + F5)

**Design decisions:** F1–F5

**Goal:** Introduce the enforcement layer: `enforcement.yaml` schema with plugin registration at startup, `EnforcementRunner` as separate service, `BaseTool.enforcement_event` class variable, dispatcher injection. `force_transition` catches hook exceptions as `ToolResult` warnings.

**Tests:**
- Loader raises `ConfigError` at startup if an action type has no registered handler (F2)
- `EnforcementRunner.run(event, timing, context)` calls the correct action-handler from registry
- `EnforcementRunner` unit tests: constructor-inject fake `EnforcementRegistry` with no-op handlers; zero dependency on `FileStateRepository` or PSE
- `BaseTool` subclass with `enforcement_event='transition_phase'` triggers pre/post hooks at dispatch level
- `BaseTool` subclass with `enforcement_event=None` incurs no registry lookup
- `force_transition`: `DeliverableCheckError` from hook returned as `ToolResult` warning, not raised (F5)
- `check_branch_policy` pre-hook on `create_branch` blocks creation if base restriction violated
- `commit_state_files` post-hook on `transition_phase` writes and commits `state.json`

**Success Criteria:**
- End-to-end test: `transition_phase` triggers post-hook → `state.json` committed automatically
- End-to-end test: `create_branch` with invalid base raises `ToolResult` error (not unhandled exception)
- `EnforcementRunner` unit tests have zero dependency on `FileStateRepository` or PSE
- Pyright `--strict` passes on `EnforcementRunner`, `EnforcementRegistry`, `BaseTool`
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 6 only if both end-to-end tests pass.

---

### Cycle 6: deliverables.json tools + state.json git-tracked (B1 + B2 + B4 + B5)

**Design decisions:** B1–B5

**Goal:** Implement `deliverables.json` tooling (`save`/`update` with completed-cycle guard), remove `state.json` from `.gitignore`, add post-merge cleanup action to `enforcement.yaml`, and add PSE startup guard for uncommitted state changes.

**Tests:**
- `save_planning_deliverables` creates `deliverables.json` with correct nested structure under issue number
- `update_planning_deliverables` raises `ValidationError` when attempting to modify a completed cycle in `cycle_history`
- `update_planning_deliverables` succeeds for open cycles
- All `deliverables.json` writes go through `AtomicJsonWriter` (no direct `open()` calls in tools)
- `state.json` not present in `.gitignore`; `git status` shows `state.json` as tracked after initialization
- Post-merge enforcement rule `delete_file` removes `deliverables.json` and `state.json` after merge
- `PSE.initialize_branch()` emits explicit warning (not exception) when `state.json` has uncommitted local changes

**Success Criteria:**
- Completed-cycle guard raises `ValidationError` with message identifying the cycle id
- `AtomicJsonWriter` used for all `deliverables.json` writes (grep verification)
- Integration test: full `transition_phase` flow commits `state.json` automatically (from Cycle 5 hook)
- Pyright `--strict` passes on `save_planning_deliverables` and `update_planning_deliverables` tools
- Full test suite green
- KPIs 1–20 in `research_config_first_pse.md` all verifiable

**Stop/Go:** ✅ KPIs 1–20 all verifiable → open PR.

---

## Risks & Mitigation

- **Risk:** Cycle 1 — `tdd` → `implementation` rename breaks active `state.json` files on other branches
  - **Mitigation:** Manual fix per decision H1. No migration code. Any active branch with `tdd` in `state.json` fixed by hand before Cycle 1 merges.
- **Risk:** Cycle 2 — PSE state refactor introduces regression in read/write path
  - **Mitigation:** `InMemoryStateRepository` used in all PSE unit tests. `FileStateRepository` tested in isolation with fixture files. `AtomicJsonWriter` crash-test validates no partial writes.
- **Risk:** Cycle 3 — `phase_contracts.yaml` schema mismatch with existing `.st3/config/` YAML files
  - **Mitigation:** Loader fills missing fields with defaults (decision A1). All existing YAML fixtures updated in Cycle 3. Fail-Fast catches schema errors at startup before any tool executes.
- **Risk:** Cycle 4 — legacy `phase=` param removal breaks undiscovered callers outside `mcp_server/tools/`
  - **Mitigation:** Full codebase `grep` pass (including tests and scripts) before removal. Pyright `--strict` catches remaining type errors at CI level.
- **Risk:** Cycle 5 — dispatch-level `EnforcementRunner` injection increases server startup complexity
  - **Mitigation:** `EnforcementRunner` independently testable via constructor injection of fake registry (zero PSE/filesystem dependency). Startup `ConfigError` for unknown action types catches config drift early.
- **Risk:** Cycle 6 — `.gitignore` removal of `state.json` affects all branches simultaneously
  - **Mitigation:** Single-line `.gitignore` removal. Active branches need `git add .st3/state.json` once. No data loss possible (file already present locally).

---

## Milestones

- After Cycle 1: codebase free of tdd, projects.json, workflow_config.py, old class names — green test suite
- After Cycle 2: PSE decoupled from filesystem; state I/O behind IStateRepository — Pyright strict passes
- After Cycle 3: phase gates config-driven; PhaseContractResolver independently testable — Fail-Fast validated
- After Cycle 4: tool layer is composition root; legacy param gone; commit scoping driven by phase_contracts.yaml
- After Cycle 5: enforcement layer live; state.json auto-committed on phase transition; branch policy enforced
- After Cycle 6: deliverables.json tooling complete; KPIs 1–20 in research_config_first_pse.md all verifiable — ready for PR

## Related Documentation
- **[design.md — Config-First PSE Architecture (decisions A–J, interfaces, component diagram)][related-1]**
- **[research_config_first_pse.md — Research source + KPIs 1–20 (frozen)][related-2]**
- **[../../coding_standards/ARCHITECTURE_PRINCIPLES.md — Binding architecture contract][related-3]**
- **[../../coding_standards/QUALITY_GATES.md — Gate 7: architectural review checklist][related-4]**

<!-- Link definitions -->

[related-1]: design.md — Config-First PSE Architecture (decisions A–J, interfaces, component diagram)
[related-2]: research_config_first_pse.md — Research source + KPIs 1–20 (frozen)
[related-3]: ../../coding_standards/ARCHITECTURE_PRINCIPLES.md — Binding architecture contract
[related-4]: ../../coding_standards/QUALITY_GATES.md — Gate 7: architectural review checklist

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |