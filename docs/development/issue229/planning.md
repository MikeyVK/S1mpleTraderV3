<!-- D:\dev\SimpleTraderV3\docs\development\issue229\planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-19 updated= -->
# Phase Deliverables Enforcement — Planning

**Status:** DRAFT  
**Version:** 1.1  
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
- Content validation of scaffold output against template structure (GAP-05, future issue)
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

### Cycle 1: workphases.yaml schema + structural checker

**Goal:** Extend `workphases.yaml` with `exit_requires` and `entry_expects` fields per phase, and introduce a structural checker that validates each declared deliverable type (`file_exists`, SCAFFOLD-header, key-path).

**Tests:**
- `test_workphases_schema_exit_requires_field_is_parsed`
- `test_workphases_schema_entry_expects_field_is_parsed`
- `test_deliverable_checker_file_not_found_raises`
- `test_deliverable_checker_md_missing_scaffold_header_raises`
- `test_deliverable_checker_md_valid_scaffold_header_passes`
- `test_deliverable_checker_json_key_path_present_passes`
- `test_deliverable_checker_json_key_path_missing_raises`

**Success Criteria:**
- `workphases.yaml` accepts `exit_requires` and `entry_expects` without breaking existing phase load
- Structural checker validates SCAFFOLD-header presence in `.md` files (first 3 lines)
- Structural checker resolves dot-notation key paths in JSON/YAML files
- All 7 unit tests pass

---

### Cycle 2: PhaseStateEngine generic dispatch + gate relocation

**Goal:** Wire the structural checker into the phase transition engine reading `workphases.yaml`. Planning exit must block when declared deliverables are absent. TDD entry must no longer validate planning deliverables independently. Forced transitions must log which gates were skipped. Expose `save_planning_deliverables` as a callable MCP tool.

**Tests:**
- `test_planning_exit_gate_blocks_transition_when_deliverables_missing`
- `test_planning_exit_gate_passes_when_deliverables_present`
- `test_tdd_entry_no_longer_validates_planning_deliverables`
- `test_entry_expects_warning_logged_when_deliverable_absent`
- `test_force_transition_logs_skipped_gates_warning`
- `test_save_planning_deliverables_mcp_tool_exposed`

**Success Criteria:**
- `planning → design` raises when `exit_requires` deliverables are missing
- `planning → design` passes silently when all deliverables are present
- Entering TDD no longer blocks independently on planning deliverables
- Forced transition produces a logged warning listing skipped gates
- `save_planning_deliverables` is reachable via MCP (integration test)
- All 6 tests pass

**Dependencies:** Cycle 1 (DeliverableChecker + workphases.yaml schema)

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

- Cycle 1 GREEN: `workphases.yaml` schema + `DeliverableChecker` passing
- Cycle 2 GREEN: exit gate on planning, entry warning on all phases, MCP tool exposed
- Happy path trial: `planning → design → tdd` succeeds with deliverables present
- GAP-01/02/03/04 confirmed resolved in `findings.md`

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
| 1.1 | 2026-02-19 | Agent | Remove design creep from scope/goals/criteria/risks; fix GAP-04 scope |
| 1.0 | 2026-02-19 | Agent | Initial draft |
