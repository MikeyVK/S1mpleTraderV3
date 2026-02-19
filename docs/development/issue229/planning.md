<!-- D:\dev\SimpleTraderV3\docs\development\issue229\planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-19 updated= -->
# Phase Deliverables Enforcement — Planning

**Status:** DRAFT  
**Version:** 1.2  
**Last Updated:** 2026-02-19

---

## Purpose

Plan the TDD cycles needed to implement phase deliverable enforcement in PhaseStateEngine and workphases.yaml, fixing the architectural gap confirmed during the #146 trial run (GAP-01/02/03/04).

## Scope

**In Scope:**
- Add `exit_requires` / `entry_expects` schema to `workphases.yaml` per phase
- Per-phase structural deliverable checker: `file_exists`, SCAFFOLD-header for `.md`, key-path for `.yaml`/`.json`
- Hard exit gate on the planning phase — blocked transition when declared deliverables are absent
- Soft entry warning on phases that declare `entry_expects`
- Expose `save_planning_deliverables` as MCP tool (fixing GAP-04)

**Out of Scope:**
- Content validation of scaffold output against template structure (separate issue, already in progress)
- YAML key-value validation (presence check is sufficient for now)
- Acceptance test files per phase
- Phase deliverable enforcement for non-Python artifact types

## Prerequisites

Read these first:
1. `research.md` approved (findings + gap analysis complete)
2. `findings.md` updated with validation strategy decision (Option C)
3. State in `state.json`: planning phase, no `planning_deliverables` in `projects.json` yet

---

## Summary

Issue #229 introduces a two-layer enforcement model for phase deliverables: a hard exit gate on phases that produce required deliverables, and a soft entry warning on phases that consume them. Validation is structural only: file existence + SCAFFOLD-header for documents, key-path presence for config/JSON. Content validation against template schema is explicitly out of scope and deferred to a future issue.

---

## Dependencies

- Requires #146 machinery active (scope format, cycle tracking) — branch is already based on `feature/146-tdd-cycle-tracking`
- `workphases.yaml` must be extensible without breaking existing phase definitions (additive fields only)

---

## TDD Cycles

### Cycle 1: workphases.yaml schema + structural deliverable checker

**Goal:** Extend `workphases.yaml` with `exit_requires` and `entry_expects` fields per phase, and introduce a structural checker that can validate each declared deliverable (`file_exists`, SCAFFOLD-header, key-path). No engine wiring yet — this cycle produces the foundational component.

**Tests:**
- `test_workphases_schema_exit_requires_field_is_parsed`
- `test_workphases_schema_entry_expects_field_is_parsed`
- `test_workphases_schema_backward_compat_phases_without_field`
- `test_deliverable_checker_file_not_found_raises`
- `test_deliverable_checker_md_missing_scaffold_header_raises`
- `test_deliverable_checker_md_valid_scaffold_header_passes`
- `test_deliverable_checker_json_key_path_present_passes`
- `test_deliverable_checker_json_key_path_missing_raises`

**Success Criteria:**
- All existing phases without `exit_requires` load without error (backward compat)
- Structural checker validates SCAFFOLD-header presence in `.md` files
- Structural checker resolves dot-notation key paths in JSON/YAML files
- All 8 unit tests pass

---

### Cycle 2: Gate relocation — GAP-01 + GAP-02

**Goal:** Fix the architectural misplacement identified in GAP-01 and GAP-02. Wire the structural checker into the planning phase exit. Remove the planning-deliverables check from TDD entry. These two changes are tightly coupled — both must land in the same cycle.

**Tests:**
- `test_planning_exit_gate_blocks_transition_when_deliverables_missing`
- `test_planning_exit_gate_passes_when_deliverables_present`
- `test_planning_exit_gate_response_includes_deliverable_ids`
- `test_tdd_entry_no_longer_validates_planning_deliverables`

**Success Criteria:**
- `planning → design` raises when `exit_requires` deliverables are absent
- `planning → design` passes and reports checked deliverable IDs when all present
- Entering TDD no longer independently blocks on planning deliverables
- All 4 tests pass

**Dependencies:** Cycle 1

---

### Cycle 3: Forced transition skipped-gate warning — GAP-03

**Goal:** When a forced transition bypasses one or more exit or entry gates, log a warning that lists which gates were skipped. The transition itself still succeeds — forced transitions remain an unconditional escape hatch.

**Tests:**
- `test_force_transition_logs_warning_for_skipped_exit_gate`
- `test_force_transition_logs_warning_for_skipped_entry_expects`
- `test_force_transition_without_gates_logs_no_warning`

**Success Criteria:**
- Forced transition on a phase with `exit_requires` produces a `logger.warning` naming the skipped gates
- Forced transition on a phase without gates remains silent
- All 3 tests pass

**Dependencies:** Cycle 2 (gates must exist to have something to skip)

---

### Cycle 4: SavePlanningDeliverablesTool — GAP-04

**Goal:** Expose `save_planning_deliverables` as a callable MCP tool so no direct `projects.json` editing is needed. Trial run confirmed this gap: deliverables had to be written manually.

**Tests:**
- `test_save_planning_deliverables_tool_persists_to_projects_json`
- `test_save_planning_deliverables_tool_rejects_duplicate`
- `test_save_planning_deliverables_tool_rejects_missing_tdd_cycles`

**Success Criteria:**
- Tool callable via MCP resolves to the same behaviour as internal `ProjectManager` method
- Duplicate calls are rejected with a clear error
- Invalid payload (missing `tdd_cycles`) is rejected with a clear error
- All 3 tests pass

**Dependencies:** None (orthogonal to Cycles 1–3)

---

## Risks & Mitigation

- **Risk:** `workphases.yaml` additive fields break existing phase load
  - **Mitigation:** Backward compat test for all existing phases without `exit_requires` in Cycle 1
- **Risk:** Phase engine mishandles phases with no `exit_requires` defined
  - **Mitigation:** Explicit test case for phases without the field in Cycle 2
- **Risk:** Relocating the planning deliverables gate changes observable behavior for existing tests
  - **Mitigation:** Backward compat test verifying TDD entry no longer raises independently (Cycle 2)

---

## Milestones

- Cycle 1 GREEN: `workphases.yaml` schema + structural checker passing (8 tests)
- Cycle 2 GREEN: planning exit gate wired, TDD entry gate removed (GAP-01 + GAP-02 fixed)
- Cycle 3 GREEN: forced transition logs skipped gates (GAP-03 fixed)
- Cycle 4 GREEN: `save_planning_deliverables` callable via MCP (GAP-04 fixed)
- All gaps confirmed resolved in `findings.md`

## Related Documentation
- **[docs/development/issue229/research.md][related-1]**
- **[docs/development/issue229/findings.md][related-2]**
- **[mcp_server/managers/phase_state_engine.py][related-3]**
- **[.st3/workphases.yaml][related-4]**

<!-- Link definitions -->

[related-1]: docs/development/issue229/research.md
[related-2]: docs/development/issue229/findings.md
[related-3]: mcp_server/managers/phase_state_engine.py
[related-4]: .st3/workphases.yaml

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.2 | 2026-02-19 | Agent | Expanded to 4 cycles: C1 infrastructure, C2 GAP-01/02, C3 GAP-03, C4 GAP-04; milestones aligned |
| 1.1 | 2026-02-19 | Agent | Remove design creep from scope/goals/criteria/risks; fix GAP-04 scope |
| 1.0 | 2026-02-19 | Agent | Initial draft |
