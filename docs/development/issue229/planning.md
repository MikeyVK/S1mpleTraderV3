<!-- D:\dev\SimpleTraderV3\docs\development\issue229\planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-19 updated= -->
# Phase Deliverables Enforcement — Planning

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-19

---

## Purpose

Plan the TDD cycles needed to implement phase deliverable enforcement in PhaseStateEngine and workphases.yaml, fixing the architectural gap confirmed during the #146 trial run (GAP-01/02/03/04).

## Scope

**In Scope:**
- Add `exit_requires` / `entry_expects` schema to `workphases.yaml` per phase
- Generic hook dispatch in `PhaseStateEngine._transition()` for exit/entry gates
- Structural deliverable checker: `file_exists` + SCAFFOLD-header for `.md`, key-path for `.yaml`/`.json`
- Relocate planning deliverables hard gate from `on_enter_tdd_phase` to `on_exit_planning_phase`
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

**Goal:** Add `exit_requires` / `entry_expects` fields to `workphases.yaml` and implement `DeliverableChecker` that validates `file_exists` + SCAFFOLD-header (`.md`) or key-path (`.yaml`/`.json`).

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
- `DeliverableChecker` validates `.md` SCAFFOLD-header in first 3 lines
- `DeliverableChecker` resolves dot-notation key paths in JSON/YAML
- All 7 unit tests pass

---

### Cycle 2: PhaseStateEngine generic dispatch + gate relocation

**Goal:** Replace hardcoded `on_enter_tdd_phase` planning-deliverables check with a generic exit/entry gate dispatch that reads `workphases.yaml` `exit_requires` / `entry_expects`. Move hard gate to `on_exit_planning_phase`. Add soft entry warning on `on_enter_*` for `entry_expects` mismatches.

**Tests:**
- `test_planning_exit_gate_blocks_transition_when_deliverables_missing`
- `test_planning_exit_gate_passes_when_deliverables_present`
- `test_tdd_entry_no_longer_validates_planning_deliverables`
- `test_entry_expects_warning_logged_when_deliverable_absent`
- `test_force_transition_logs_skipped_gates_warning`
- `test_save_planning_deliverables_mcp_tool_exposed`

**Success Criteria:**
- `planning → design` raises `PhaseDeliverableError` when `exit_requires` deliverables missing
- `planning → design` passes silently when deliverables present
- `on_enter_tdd_phase` no longer references `planning_deliverables` directly (test verifies absence)
- `force_transition` logs a warning listing skipped gates
- `save_planning_deliverables` is callable via MCP tool (integration test)
- All 6 tests pass

**Dependencies:** Cycle 1 (DeliverableChecker + workphases.yaml schema)

---

## Risks & Mitigation

- **Risk:** `workphases.yaml` additive fields break existing phase load if parser is strict
  - **Mitigation:** Use optional fields with default empty lists; add schema test for backward compat in Cycle 1
- **Risk:** Generic hook dispatch may miss edge cases for phases with no `exit_requires` defined
  - **Mitigation:** Default to no-op when `exit_requires` is absent; explicit test case in Cycle 2
- **Risk:** Relocating the gate from `on_enter_tdd` to `on_exit_planning` changes observable behavior for existing callers
  - **Mitigation:** Test backward compat: `on_enter_tdd` must NOT raise after relocation (Cycle 2 test)

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
| 1.0 | 2026-02-19 | Agent | Initial draft |
