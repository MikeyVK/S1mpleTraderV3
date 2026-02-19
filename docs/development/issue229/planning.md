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
- Per-phase structural deliverable checker: `file_exists`, `file_glob`, SCAFFOLD-header for `.md`, key-path for `.yaml`/`.json`
- Hard exit gate on the planning phase — blocked transition when declared deliverables are absent
- Soft entry warning on phases that declare `entry_expects`
- Expose `save_planning_deliverables` as MCP tool with Layer 2 schema validation (fixing GAP-04 + GAP-06)

**Out of Scope:**
- Content validation of scaffold output against template structure (separate issue, already in progress)
- YAML key-value validation (presence check is sufficient for now)
- Acceptance test files per phase
- Phase deliverable enforcement for non-Python artifact types

## Prerequisites

Read these first:
1. `research.md` approved (findings + gap analysis complete)
2. `findings.md` updated with validation strategy decision (structural checks only — no acceptance tests per phase)
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

### Cycle 2: Gate relocation + file_glob support + commit phase guard — GAP-01 + GAP-02 + GAP-05 + GAP-07

**Goal:** Fix the architectural misplacement identified in GAP-01 and GAP-02. Wire the structural checker into the planning phase exit. Remove the planning-deliverables check from TDD entry. Add `file_glob` check type to `DeliverableChecker` (GAP-05) — agents need pattern-based file existence checks without knowing exact filenames. Add phase/cycle mismatch guard to `git_add_or_commit` (GAP-07) — tool should block commits when the provided phase/cycle doesn't match `state.json`.

**Tests (original — gate relocation):**
- `test_planning_exit_gate_blocks_transition_when_deliverables_missing`
- `test_planning_exit_gate_passes_when_deliverables_present`
- `test_planning_exit_gate_uses_workphases_config_for_required_keys`
- `test_planning_exit_gate_runs_deliverable_checker_on_validates_entries`
- `test_tdd_entry_no_longer_validates_planning_deliverables`
- `test_transition_from_planning_calls_exit_planning_gate`

**Tests (re-run addition — file_glob):**
- `test_deliverable_checker_file_glob_match_passes`
- `test_deliverable_checker_file_glob_no_match_raises`
- `test_deliverable_checker_file_glob_pattern_in_subdir_passes`

**Tests (re-run addition — commit phase guard):**
- `test_git_add_or_commit_raises_on_phase_mismatch`

**Success Criteria:**
- `planning → design` raises when `exit_requires` deliverables are absent
- `planning → design` passes when all deliverables present
- Entering TDD no longer independently blocks on planning deliverables
- `file_glob` type: at least one matching file → pass; zero matches → `DeliverableCheckError`
- `git_add_or_commit` raises `CommitPhaseMismatchError` when `workflow_phase` ≠ `state.json.current_phase` (or `cycle_number` ≠ `current_tdd_cycle`)
- All tests pass

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

### Cycle 4: SavePlanningDeliverablesTool + schema validation — GAP-04 + GAP-06

**Goal:** Expose `save_planning_deliverables` as a callable MCP tool. Extend it with Layer 2 schema validation: every `validates` entry in the payload is validated before persisting. On error, the tool returns a structured message listing the valid `type` values and their required fields — matching the pattern of the scaffold tool.

**Layer model:**
- **Layer 1** (free): MCP tool JSON Schema exposes parameter shapes to agents automatically
- **Layer 2** (this cycle): Runtime validation of `validates` entries — catches invalid `type`, missing `file`, missing `text`/`path` per type, before writing to disk

**Tests:**
- `test_save_planning_deliverables_tool_persists_to_projects_json`
- `test_save_planning_deliverables_tool_rejects_duplicate`
- `test_save_planning_deliverables_tool_rejects_missing_tdd_cycles`
- `test_save_planning_deliverables_tool_rejects_unknown_validates_type`
- `test_save_planning_deliverables_tool_rejects_validates_missing_required_field`
- `test_save_planning_deliverables_tool_error_lists_available_types_and_fields`

**Success Criteria:**
- Tool callable via MCP; persists to `projects.json` correctly
- Duplicate calls rejected with clear error
- Invalid `validates.type` rejected with message: `"Unknown type 'X'. Valid types: file_exists, file_glob, contains_text, absent_text, key_path. Required fields: ..."`
- Missing required field (e.g. `file`, `text`) rejected with per-type field list
- All 6 tests pass

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
- Cycle 2 GREEN: planning exit gate wired, TDD entry gate removed, `file_glob` type added (GAP-01 + GAP-02 + GAP-05)
- Cycle 3 GREEN: forced transition logs skipped gates (GAP-03 fixed)
- Cycle 4 GREEN: `save_planning_deliverables` callable via MCP with Layer 2 schema validation (GAP-04 + GAP-06 fixed)
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
| 1.3 | 2026-02-19 | Agent | C2 extended with file_glob (GAP-05); C4 extended with Layer 2 schema validation + error messages (GAP-06); scope + milestones updated |
| 1.2 | 2026-02-19 | Agent | Expanded to 4 cycles: C1 infrastructure, C2 GAP-01/02, C3 GAP-03, C4 GAP-04; milestones aligned |
| 1.1 | 2026-02-19 | Agent | Remove design creep from scope/goals/criteria/risks; fix GAP-04 scope |
| 1.0 | 2026-02-19 | Agent | Initial draft |
