<!-- D:\dev\SimpleTraderV3\docs\development\issue229\planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-19 updated= -->
# Phase Deliverables Enforcement — Planning

**Status:** DRAFT  
**Version:** 1.2  
**Last Updated:** 2026-02-20

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

### Cycle 3: Forced transition skipped-gate warning — GAP-03 + GAP-08

**Goal:** When a forced transition bypasses one or more exit or entry gates, log a warning that lists which gates were skipped (GAP-03). Additionally, when `force_cycle_transition` skips cycles with unvalidated deliverables, warn about those too (GAP-08). Both transitions remain unconditional escape hatches — warnings are informational only.

**Tests:**
- `test_force_transition_logs_warning_for_skipped_exit_gate`
- `test_force_transition_logs_warning_for_skipped_entry_expects`
- `test_force_transition_without_gates_logs_no_warning`
- `test_force_cycle_transition_warns_unvalidated_skipped_cycle_deliverables` *(D3.2)*
- `test_force_cycle_transition_no_warning_when_skipped_cycles_pass_checks` *(D3.2)*

**Success Criteria:**
- Forced transition on a phase with `exit_requires` produces a `logger.warning` naming the skipped gates
- Forced transition on a phase without gates remains silent
- `force_cycle_transition` skip from C2→C4 produces `⚠️ Unvalidated cycle deliverables: cycle:3:D3.1 (...)` in tool response when C3 deliverables fail checks
- `force_cycle_transition` skip produces no warning when all skipped cycle deliverables pass checks
- All 5 tests pass

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

### Cycle 5: update_planning_deliverables tool — GAP-09

**Goal:** Add `update_planning_deliverables` MCP tool with merge-strategy so cycles and deliverables can evolve after the initial write. Keep `save_planning_deliverables` write-once (intentional first-commit guard). The new tool merges: new cycles append by cycle number; existing cycle deliverables merge by `id`; existing entries update in place.

**Tests:**
- `test_update_planning_deliverables_tool_appends_new_cycle`
- `test_update_planning_deliverables_tool_merges_deliverable_by_id`
- `test_update_planning_deliverables_tool_updates_existing_deliverable_by_id`
- `test_update_planning_deliverables_tool_rejects_before_initial_save`
- `test_update_planning_deliverables_tool_validates_validates_entry_schema`

**Success Criteria:**
- New cycle appended without touching existing cycles
- Existing deliverable with matching `id` updated (description/validates)
- New deliverable with new `id` added to existing cycle
- Call before `save_planning_deliverables` raises clear error
- Layer 2 validates-schema validation identical to `save_planning_deliverables`
- All tests pass

**Dependencies:** Cycle 4 (Layer 2 `validate_spec` reusable)

---

### Cycle 6: exit_requires file_glob support + research phase gate — GAP-10

**Goal:** Extend `exit_requires` in `workphases.yaml` with a `type: file_glob` variant that checks the file system instead of `projects.json`. Support `{issue_number}` placeholder interpolation. Configure the research phase with a gate requiring a `*research*.md` file.

**Tests:**
- `test_exit_requires_file_glob_passes_when_file_exists`
- `test_exit_requires_file_glob_blocks_when_no_match`
- `test_exit_requires_file_glob_interpolates_issue_number`
- `test_research_exit_gate_blocks_without_research_doc`
- `test_research_exit_gate_passes_with_research_doc`

**Success Criteria:**
- `PhaseStateEngine` reads `type: file_glob` entries from `exit_requires`
- `{issue_number}` in `file:` is interpolated at gate-check time
- Research → planning blocked when no `*research*.md` exists for issue
- Research → planning passes when file exists
- Forced transition logs `⚠️ Skipped gates: research.exit_requires[0]` (reuses C3 pattern)
- All tests pass

**Dependencies:** Cycle 1 (DeliverableChecker._check_file_glob), Cycle 3 (skipped-gate warning pattern)

---

### Cycle 7: planning_deliverables schema generalization — GAP-11

**Goal:** Extend `planning_deliverables` to support per-phase deliverable definitions beyond `tdd_cycles`. `PhaseStateEngine` exit gate for each phase checks `planning_deliverables.<phase>.deliverables` via `DeliverableChecker`. `hotfix` workflow remains exempt (no planning phase).

**Tests:**
- `test_save_planning_deliverables_accepts_design_phase_deliverables`
- `test_save_planning_deliverables_accepts_validation_phase_deliverables`
- `test_phase_exit_gate_checks_planning_deliverables_for_phase`
- `test_phase_exit_gate_skips_when_no_phase_key_in_planning_deliverables`
- `test_update_planning_deliverables_accepts_non_tdd_phase_deliverables`

**Success Criteria:**
- `save_planning_deliverables` accepts `design`, `validation`, `documentation` keys alongside `tdd_cycles`
- `PhaseStateEngine` exit gate for `design` checks `planning_deliverables.design.deliverables` when present
- When key absent, gate is skipped (optional — not all agents plan all phases)
- `DeliverableChecker` reused without modification
- `hotfix` workflow unaffected
- All tests pass

**Dependencies:** Cycle 5 (update_planning_deliverables for evolving phase deliverables), Cycle 6 (gate pattern)

---

### Cycle 8: update_planning_deliverables completeness — GAP-12 + GAP-15

**Goal:** Two gaps found during C7 live validation reveal that `update_planning_deliverables` is incomplete in two distinct ways.

**GAP-15:** Per-fase keys (`design`, `validation`, `documentation`) are silently ignored. A call with `{"design": {"deliverables": [...]}}` returns `✅ Planning deliverables updated` but nothing changes in `projects.json`. The merge loop only processes `tdd_cycles`. Without this fix, agents cannot evolve per-phase gate specs after the initial `save_planning_deliverables` call — a direct `projects.json` edit is the only workaround.

**GAP-12:** `exit_criteria` at the cycle level is ignored during merge. When a cycle update includes a corrected `exit_criteria`, only the `deliverables` list is merged by id; the cycle-level `exit_criteria` string is left unchanged. This makes it impossible to fix a typo or tighten criteria after the initial save.

**Rationale for combining in one cycle:** Both gaps are in the same method (`ProjectManager.update_planning_deliverables`). Fixing one without the other leaves the tool partially broken. The test surface is small and self-contained; splitting into two cycles would add overhead without benefit.

**Note on GAP-13** (no mechanism to delete a cycle): Treated as a design decision rather than a bug — cycles are intentionally append-only to preserve audit history. This will be documented as a constraint in the tool's docstring rather than fixed.

**Tests:**
- `test_update_planning_deliverables_merges_design_key`
- `test_update_planning_deliverables_merges_validation_key`
- `test_update_planning_deliverables_merges_documentation_key`
- `test_update_planning_deliverables_per_phase_merge_by_id`
- `test_update_planning_deliverables_updates_exit_criteria_on_existing_cycle`
- `test_update_planning_deliverables_tdd_cycles_backward_compat`

**Success Criteria:**
- `update_planning_deliverables(229, {"design": {"deliverables": [...]}})` updates `projects.json` design deliverables
- Per-fase merge by id: existing entry with matching `id` updated, new `id` appended
- `exit_criteria` on an existing cycle is overwritten when provided in the update payload
- `tdd_cycles` merge behaviour unchanged (backward compat)
- All 6 tests pass

**Dependencies:** Cycle 7 (per-fase keys schema in place), Cycle 5 (original tdd_cycles merge logic to extend)

---

### Cycle 9: validation + documentation exit hooks — GAP-16

**Goal:** C7 introduced per-phase deliverable exit gates but only wired `on_exit_design_phase`. GAP-16, confirmed by live test on 2026-02-20: a `validation → documentation` transition passes without error even when `planning_deliverables.validation.deliverables` contains a spec pointing to a non-existent file. The same gap exists for `documentation → done`. `on_exit_validation_phase` and `on_exit_documentation_phase` do not exist; neither is wired in `transition()`.

**Rationale:** The design intent in C7 was to generalise gate enforcement to all non-tdd phases. The implementation stopped at `design`. Completing enforcement for `validation` and `documentation` is a direct continuation of that design — the pattern (`on_exit_<phase>_phase` → `DeliverableChecker`) is already established and reusable.

**Note on GAP-14** (`validates.text` specs in D7.1/D7.2 not matching actual implementation): Fixed as part of this cycle's success criteria — D7.1 and D7.2 specs in the live `projects.json` will be corrected via `update_planning_deliverables` once C8 is implemented.

**Tests:**
- `test_validation_exit_gate_blocks_transition_when_deliverable_missing`
- `test_validation_exit_gate_passes_when_deliverable_present`
- `test_validation_exit_gate_skips_when_no_validation_key_in_plan`
- `test_documentation_exit_gate_blocks_transition_when_deliverable_missing`
- `test_documentation_exit_gate_passes_when_deliverable_present`
- `test_documentation_exit_gate_skips_when_no_documentation_key_in_plan`

**Success Criteria:**
- `on_exit_validation_phase` implemented and wired in `transition()` for `from_phase == "validation"`
- `on_exit_documentation_phase` implemented and wired in `transition()` for `from_phase == "documentation"`
- Both gates are optional: silent pass when key absent in `planning_deliverables`
- `DeliverableChecker` reused without modification
- Forced transition still bypasses hooks (uses existing C3 skip-warning pattern)
- D7.1 and D7.2 `validates.text` specs in `projects.json` corrected via `update_planning_deliverables` (GAP-14 resolved)
- All 6 tests pass

**Dependencies:** Cycle 7 (on_exit_design_phase pattern), Cycle 8 (update_planning_deliverables per-fase merge needed to fix GAP-14 specs)

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
- Cycle 3 GREEN: forced transition logs skipped gates (GAP-03 fixed); force_cycle_transition warns unvalidated skipped cycles (GAP-08 fixed)
- Cycle 4 GREEN: `save_planning_deliverables` callable via MCP with Layer 2 schema validation (GAP-04 + GAP-06 fixed)
- Cycle 5 GREEN: `update_planning_deliverables` tool with merge-strategy (GAP-09 fixed)
- Cycle 6 GREEN: `exit_requires` supports `type: file_glob` + `{issue_number}` interpolation; research phase gate configured (GAP-10 fixed)
- Cycle 7 GREEN: `planning_deliverables` generalised to all phases; exit gates per phase (GAP-11 fixed)
- Cycle 8 GREEN: `update_planning_deliverables` merges per-fase keys + `exit_criteria` (GAP-12 + GAP-15 fixed)
- Cycle 9 GREEN: `on_exit_validation_phase` + `on_exit_documentation_phase` wired; GAP-14 specs corrected (GAP-16 fixed)
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
| 1.6 | 2026-02-20 | Agent | Added C8 (GAP-12 + GAP-15) and C9 (GAP-16); GAP-13 as design decision; GAP-14 resolved in C9; milestones updated |
| 1.5 | 2026-02-19 | Agent | Added C5 (GAP-09), C6 (GAP-10), C7 (GAP-11) — discovered during validation phase smoke-test |
| 1.3 | 2026-02-19 | Agent | C2 extended with file_glob (GAP-05); C4 extended with Layer 2 schema validation + error messages (GAP-06); scope + milestones updated |
| 1.2 | 2026-02-19 | Agent | Expanded to 4 cycles: C1 infrastructure, C2 GAP-01/02, C3 GAP-03, C4 GAP-04; milestones aligned |
| 1.1 | 2026-02-19 | Agent | Remove design creep from scope/goals/criteria/risks; fix GAP-04 scope |
| 1.0 | 2026-02-19 | Agent | Initial draft |
