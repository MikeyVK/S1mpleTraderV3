<!-- docs\development\issue257\planning_threshold_b_minimal_refactor.md -->
<!-- template=planning version=130ac5ea created=2026-04-04T14:51Z updated=2026-04-04 -->
# Threshold B Minimal Refactor — Implementation Planning

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-04  
**Research Reference:** [research_minimal_refactor_scope.md](research_minimal_refactor_scope.md) v1.0  
**Design Reference:** [design_threshold_b_minimal_refactor.md](design_threshold_b_minimal_refactor.md) v1.1  
**Retained Earlier Plan:** [planning.md](planning.md) remains in place for the previous config-layer SRP scope and is not overwritten by this document.

---

## Purpose

Turn the approved Threshold B design for issue #257 into an executable implementation plan with concrete cycles, deliverables, RED-phase tests, and stop/go criteria.

## Scope

**In Scope:**
WorkflowGateRunner introduction, StateReconstructor extraction, PhaseStateEngine responsibility reduction, cycle tool orchestration unification, enforcement scope narrowing, config ownership clarification, and transition-path rewiring needed to satisfy Threshold B.

**Out of Scope:**
Generalized effect frameworks, unrelated config-layer SRP work, broad YAML redesign beyond the active Threshold B scope, and implementation details not required to execute the final refactor cycle.

## Prerequisites

Read these first:
1. Threshold B selected and recorded in research
2. Threshold B design document committed on the active branch
3. Forced transition back to planning recorded for issue 257
4. Existing `planning_deliverables` in `.st3/projects.json` treated as historical scope until an explicit migration decision is made
---

## Summary

This planning document is the active implementation plan for the final Threshold B refactor on issue #257. It intentionally coexists with the older [planning.md](planning.md), which captured a different config-layer refactoring scope. The goal of this plan is narrower: remove God Class behavior from `PhaseStateEngine`, unify phase and cycle gate execution behind one runtime gate owner, restore CQS for state retrieval, and remove enforcement responsibilities that are not enforcement.

---

## Implementation Strategy

1. Move ownership before deleting legacy logic.
2. Keep normal and forced transition behavior explicit throughout the refactor.
3. Make `get_state()` pure only after reconstruction is extracted behind an injected dependency.
4. Delete tool-layer bypasses only after the shared orchestration path is proven by tests.
5. Keep configuration changes minimal and local to the responsibilities already approved in design.

---

## Dependencies

- C_GATE_WIRING depends on C_GATE_API
- C_STATE_RECOVERY depends on C_GATE_WIRING
- C_CYCLE_ORCHESTRATION depends on C_GATE_WIRING
- C_ENFORCEMENT_CLEANUP depends on C_GATE_WIRING and C_STATE_RECOVERY

---

## Cycle Summary

| Cycle | Focus | Depends On | Primary Exit Signal |
|---|---|---|---|
| C_GATE_API | Introduce gate/reconstruction contracts and RED tests | — | Contracts and first orchestration tests exist |
| C_GATE_WIRING | Put phase transitions on WorkflowGateRunner | C_GATE_API | `PhaseContractResolver.resolve()` is live on strict + forced phase transitions |
| C_STATE_RECOVERY | Extract reconstruction and purify `get_state()` | C_GATE_WIRING | `get_state()` becomes pure query behavior |
| C_CYCLE_ORCHESTRATION | Move cycle tools onto shared transition orchestration | C_GATE_WIRING | cycle tools stop validating/saving directly |
| C_ENFORCEMENT_CLEANUP | Narrow enforcement and align config ownership | C_GATE_WIRING, C_STATE_RECOVERY | enforcement scope is tool guards only |

---

## TDD Cycles

### Cycle 1: C_GATE_API

**Goal:**
Create the minimum contracts and test seam needed to make gate orchestration and reconstruction injectable responsibilities instead of hidden internals.

**Implementation Focus:**
- Add `IWorkflowGateRunner` to `mcp_server/core/interfaces/__init__.py`
- Add `IStateReconstructor` to `mcp_server/core/interfaces/__init__.py`
- Add `WorkflowGateRunner` implementation skeleton at manager level
- Add constructor-injection seam to `PhaseStateEngine` for the two new dependencies

**RED Phase Tests:**
- `test_phase_state_engine_accepts_workflow_gate_runner_dependency`
- `test_phase_state_engine_accepts_state_reconstructor_dependency`
- `test_workflow_gate_runner_exposes_enforce_and_inspect_modes`

**Success Criteria:**
- Both protocol interfaces exist and are imported from the core interface surface
- `PhaseStateEngine` no longer hardcodes the future gate owner as an internal detail
- The new gate runner has an executable seam for later wiring without changing runtime ownership yet

### Cycle 2: C_GATE_WIRING

**Goal:**
Make `WorkflowGateRunner` the real runtime owner for phase-boundary gate execution and remove the phase-name dispatch burden from `PhaseStateEngine.transition()`.

**Implementation Focus:**
- Wire strict phase transitions to `workflow_gate_runner.enforce(...)`
- Wire forced phase transitions to `workflow_gate_runner.inspect(...)`
- Build resolver context per call and make `PhaseContractResolver.resolve()` live on the transition path
- Remove hardcoded `planning/research/design/validation/documentation/implementation` gate dispatch from `PhaseStateEngine.transition()`

**RED Phase Tests:**
- `test_transition_phase_uses_workflow_gate_runner_enforce`
- `test_force_phase_transition_uses_workflow_gate_runner_inspect`
- `test_transition_phase_uses_phase_contract_resolver_resolve`
- `test_phase_state_engine_transition_no_longer_relies_on_phase_specific_exit_dispatch`

**Success Criteria:**
- `PhaseContractResolver.resolve()` is no longer dead architecture for phase transitions
- Forced transitions still report bypass context, but gate ownership is outside `PhaseStateEngine`
- The phase-name if-chain disappears from transition orchestration

### Cycle 3: C_STATE_RECOVERY

**Goal:**
Remove reconstruction responsibility from `PhaseStateEngine` and restore command-query separation for branch-state reads.

**Implementation Focus:**
- Add `StateReconstructor` as dedicated reconstruction component
- Route reconstruction through `PhaseStateEngine.transition()` only
- Make `PhaseStateEngine.get_state()` a pure repository query
- Preserve repository save behavior only on explicit recovery inside transition orchestration

**RED Phase Tests:**
- `test_transition_reconstructs_state_via_state_reconstructor_when_load_fails`
- `test_transition_saves_reconstructed_state_before_continuing`
- `test_get_state_does_not_reconstruct_or_save_on_load_failure`
- `test_get_state_raises_when_repository_load_fails`

**Success Criteria:**
- `PhaseStateEngine.get_state()` performs no save and no reconstruction side effects
- Reconstruction logic is not implemented inside `PhaseStateEngine`
- Recovery orchestration remains explicit in `transition()` and nowhere else

### Cycle 4: C_CYCLE_ORCHESTRATION

**Goal:**
Move strict and forced cycle transitions onto the same orchestrated gate path as phase transitions.

**Implementation Focus:**
- Make `cycle_tools.py` thin like `phase_tools.py`
- Remove direct `DeliverableChecker` construction from cycle tools
- Remove direct `state_engine._save_state()` calls from cycle tools
- Reuse `WorkflowGateRunner` enforce/inspect modes for cycle boundaries

**RED Phase Tests:**
- `test_transition_cycle_delegates_to_domain_orchestration`
- `test_force_cycle_transition_uses_gate_inspection_path`
- `test_cycle_tools_do_not_instantiate_deliverable_checker_directly`
- `test_cycle_tools_do_not_call_protected_save_state_methods`

**Success Criteria:**
- Cycle transitions no longer bypass the shared ownership model
- Tool-layer cycle validation disappears
- State persistence for cycles follows the same orchestration path as phases

### Cycle 5: C_ENFORCEMENT_CLEANUP

**Goal:**
Return enforcement to actual tool guards only and finish the minimal config ownership cleanup needed by the design.

**Implementation Focus:**
- Remove `commit_state_files` from `.st3/config/enforcement.yaml`
- Remove forced-tool-name heuristics from `server.py`
- Ensure `EnforcementRunner` no longer depends on collaborators needed only for state commit side effects
- Keep `workflows.yaml` as legal movement source and `phase_contracts.yaml` as gate-contract source
- Remove issue-specific hardcoded gate paths from `phase_contracts.yaml`

**RED Phase Tests:**
- `test_enforcement_runner_handles_tool_guards_only`
- `test_server_does_not_use_force_tool_name_heuristics`
- `test_enforcement_config_does_not_register_commit_state_files`
- `test_phase_contracts_gate_paths_are_not_issue_specific`

**Success Criteria:**
- Enforcement means "may the tool run?" and not "what should happen after success?"
- `commit_state_files` is gone from the enforcement path
- Gate contracts are workflow-generic and no longer pinned to issue #257 paths

---

## Validation Strategy

- Each cycle starts with RED tests that prove ownership is moving, not just behavior staying green by accident.
- Structural assertions are acceptable where the branch goal is architectural deletion of bypass paths.
- For touched runtime flows, prefer unit tests around collaborators first and targeted integration coverage second.
- End-of-cycle verification should include grep-style closure checks for deleted bypasses and legacy ownership patterns.

---

## Stop/Go Criteria

**Per-cycle GO rules:**
- The listed RED-phase tests for the cycle exist first
- The new owner is called in production code, not only constructed or imported
- The legacy path scheduled for removal in that cycle is actually deleted
- No direct bypass remains in tool code for the responsibility moved in that cycle

**Branch exit criteria for this planning scope:**
- `PhaseStateEngine` no longer owns phase-specific gate dispatch
- `PhaseStateEngine` no longer owns branch-state reconstruction
- `PhaseStateEngine.get_state()` is a pure query
- `cycle_tools.py` no longer validates deliverables directly and no longer calls protected state-save methods
- `EnforcementRunner` and `enforcement.yaml` contain only tool-guard semantics

---

## Risks & Mitigation

- **Risk:** Phase and cycle paths drift again during incremental rewiring.  
  **Mitigation:** Do not start cycle-path cleanup before `WorkflowGateRunner` is already authoritative for phase transitions.
- **Risk:** `get_state()` appears pure in tests while hidden persistence survives in a fallback helper.  
  **Mitigation:** Add explicit failure-path tests that assert no save call occurs during query access.
- **Risk:** Config cleanup expands beyond the approved design boundary.  
  **Mitigation:** Restrict config edits to enforcement scope, gate-contract ownership, and issue-specific hardcoding removal only.
- **Risk:** Existing `.st3/projects.json` planning deliverables remain tied to the historical planning scope.  
  **Mitigation:** Keep this document as the active planning artifact first; treat planning-deliverables migration as a separate explicit decision because current tooling is write-once plus merge-oriented.

---

## Milestones

- Design committed before planning work
- Branch returned to planning via forced audited transition
- New planning document committed without overwriting the earlier [planning.md](planning.md)
- Shared gate ownership live for both phase and cycle transitions
- `PhaseStateEngine` cleared of gate dispatch and reconstruction responsibilities
- Enforcement narrowed to tool guards only

## Related Documentation
- **[research_minimal_refactor_scope.md][related-1]**
- **[research_runner_architecture_baseline.md][related-2]**
- **[research_enforcement_analysis.md][related-3]**
- **[design_threshold_b_minimal_refactor.md][related-4]**
- **[planning.md][related-5]**

<!-- Link definitions -->

[related-1]: research_minimal_refactor_scope.md
[related-2]: research_runner_architecture_baseline.md
[related-3]: research_enforcement_analysis.md
[related-4]: design_threshold_b_minimal_refactor.md
[related-5]: planning.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-04 | imp | Initial Threshold B planning document created as a new file alongside the earlier issue257 planning.md |
