<!-- docs/development/issue257/documentation_phase_plan.md -->
# Documentation Phase Plan — Issue #257

**Status:** Draft  
**Version:** 1.0  
**Last Updated:** 2026-04-05

---

## Purpose

Capture the documentation-phase close-out plan for issue #257 after the Threshold B minimal refactor, blocker remediation, validation pass, validation-to-documentation transition, and post-restart server health check.

This plan has two goals:
1. Bring the issue #257 documentation set in sync with the actual implemented state.
2. Define a safe next pass for further completion of `.st3/config/phase_contracts.yaml` without reopening broad refactor scope.

---

## Current Baseline

### Branch / Phase

- Branch: `feature/257-reorder-workflow-phases`
- Current workflow phase: `documentation`
- Validation-to-documentation transition completed on 2026-04-05
- MCP server restart completed successfully; health check returned `OK`

### Verified Implementation State

The following implementation outcomes are already complete and verified:

- Cross-machine recovery tests now respect the pure-query `get_state()` contract.
- Dead legacy gate-dispatch methods were removed from `PhaseStateEngine`.
- Cycle transitions and cycle-phase checks are now driven by the `cycle_based` config contract instead of hardcoded `"implementation"` checks.
- Legacy and manager test doubles were aligned with the `IWorkflowGateRunner.is_cycle_based_phase(...)` seam.
- Focused quality gates on all changed MCP files passed.
- `tests/mcp_server/` passed at documentation-phase entry with:
  - `2158 passed, 12 skipped, 2 xfailed, 19 warnings`

### Existing Documentation Assets

The issue already has these relevant documents:

- `research.md`
- `planning.md`
- `planning_threshold_b_minimal_refactor.md`
- `design_threshold_b_minimal_refactor.md`
- `validation_report.md`
- `TIJDLIJN_ISSUE257.md`
- multiple historical session handovers in `SESSIE_OVERDRACHT*.md`

### Current `phase_contracts.yaml` Gap

`.st3/config/phase_contracts.yaml` currently covers only a partial subset of the configured workflows:

- `feature` has basic phase exit contracts plus `implementation.cycle_based`
- `docs` has a `documentation` contract
- `bug`, `hotfix`, `refactor`, and `epic` are still missing from the contract file
- `coordination` has no contract definition yet
- cycle metadata is still defined only once, even though multiple workflows contain an `implementation` phase with TDD-style cycle semantics

---

## Documentation Update Plan

### Workstream A — Refresh issue #257 close-out documents

#### A1. Update `validation_report.md`

Bring `validation_report.md` in line with the final MCP-scoped verification state.

Required updates:
- replace stale pass counts and stale HEAD reference with the final verified state from 2026-04-05
- record that blocker set B1, M1a, M1b/c, and requested M2 style updates were resolved
- record the focused MCP verification result (`2158 passed, 12 skipped, 2 xfailed, 19 warnings`)
- record that focused file-scoped quality gates passed for all touched MCP files
- record that server restart and health check succeeded after the refactor
- clearly separate validated scope from known out-of-scope debt

#### A2. Create a documentation-phase handover

Create one final documentation-phase handover for issue #257 that summarizes:
- actual delivered scope
- key design decisions now live in code
- files materially changed in the Threshold B close-out
- exact validation evidence
- known non-blocking follow-up work that remains outside this issue

Preferred artifact name:
- `SESSIE_OVERDRACHT_20260405_DOCUMENTATIE.md`

#### A3. Update Threshold B plan/design status markers

Review and update the status framing in:
- `planning_threshold_b_minimal_refactor.md`
- `design_threshold_b_minimal_refactor.md`

Required adjustments:
- mark implemented cycles as completed instead of leaving them as live draft intent
- add a short outcome section describing which parts became code and which parts remain deferred
- make sure the docs no longer imply that cycle 5 is still open

#### A4. Extend `TIJDLIJN_ISSUE257.md`

Append a 2026-04-05 timeline entry covering:
- blocker handover intake
- B1 fix
- M1a cleanup
- M1b/c config-driven cycle phase completion
- M2 documentation/style pass
- focused verification green
- validation transition
- documentation transition
- server restart + health check

#### A5. Optional cross-reference cleanup

If needed, add one short cross-reference note in a shared reference doc only when it reflects already-landed architecture, for example:
- `docs/reference/WORKFLOWS.md`
- a workflow/config architecture reference under `docs/reference/` or `docs/architecture/`

Constraint:
- do not start a broader documentation rewrite outside issue #257 in this phase.

---

## `phase_contracts.yaml` Completion Plan

### Goal

Fill `phase_contracts.yaml` out to match the workflows already declared in `.st3/config/workflows.yaml`, while keeping contracts:
- workflow-generic
- issue-agnostic
- aligned with current runtime semantics
- limited to gate/cycle metadata responsibility

### Workstream B — Safe contract completion

#### B1. Mirror every workflow from `workflows.yaml`

Add missing top-level workflow sections for:
- `bug`
- `hotfix`
- `refactor`
- `epic`

Keep the existing `feature` and `docs` sections, but review them for consistency with the final refactor behavior.

#### B2. Add cycle metadata to every workflow that has an `implementation` phase

For these workflows, add an `implementation` contract with:
- `cycle_based: true`
- `subphases: [red, green, refactor]`
- `commit_type_map` matching the active implementation semantics

Target workflows:
- `feature`
- `bug`
- `hotfix`
- `refactor`

Rationale:
The code is now config-driven for cycle-based phases. Leaving cycle metadata present only on `feature.implementation` keeps the config behind the runtime abstraction.

#### B3. Fill generic exit gates for the non-cycle phases that already have stable document conventions

Add or align generic `file_glob` contracts for:
- `research`
- `planning`
- `design`
- `validation`
- `documentation`

Use patterns that stay issue-agnostic and match existing document naming conventions, for example:
- `issue*/research*.md`
- `issue*/planning*.md`
- `issue*/design*.md`
- `issue*/validation*.md`
- `issue*/SESSIE_OVERDRACHT*.md`

Constraint:
Do not reintroduce issue-specific literals like `issue257` into the contract file.

#### B4. Stage `epic.coordination` separately

`epic` includes a `coordination` phase in `workflows.yaml`, but there is not yet one clearly established documentation artifact convention for that phase.

Plan:
- first decide the coordination artifact convention
- then add the `coordination.exit_requires` contract in a second step

Candidate directions:
- child-issue tracking doc
- epic sync log
- coordination handover doc

Until the artifact convention is explicit, do not guess a brittle glob.

#### B5. Keep `phase_contracts.yaml` limited to its intended role

Do not use this follow-up to move unrelated metadata into the file.

`phase_contracts.yaml` should remain responsible for:
- gate contracts at phase/cycle boundaries
- cycle-based phase metadata
- commit-type maps tied to subphases

It should not absorb unrelated workflow narration already owned by:
- `workflows.yaml`
- `workphases.yaml`
- issue-specific planning documents

---

## Proposed Execution Order

1. Refresh `validation_report.md` with the final verified implementation state.
2. Create the final documentation-phase handover for issue #257.
3. Update Threshold B plan/design docs so their status matches reality.
4. Append the 2026-04-05 close-out path to `TIJDLIJN_ISSUE257.md`.
5. Expand `phase_contracts.yaml` for `bug`, `hotfix`, `refactor`, and the safe parts of `epic`.
6. Re-run targeted manager/cycle tests after any contract changes.
7. Re-run focused quality gates for touched MCP/config files.
8. Re-run server health check after config changes if the server is restarted again.

---

## Verification Plan For The `phase_contracts.yaml` Follow-up

After editing `.st3/config/phase_contracts.yaml`, verify with a focused pass:

### Tests

- `tests/mcp_server/unit/managers/test_phase_state_engine_c1.py`
- `tests/mcp_server/unit/managers/test_phase_state_engine_c2.py`
- `tests/mcp_server/unit/managers/test_phase_state_engine_c3_issue257.py`
- `tests/mcp_server/unit/managers/test_phase_state_engine_c4_issue257.py`
- `tests/mcp_server/unit/tools/test_cycle_tools.py`
- `tests/mcp_server/unit/tools/test_cycle_tools_legacy.py`
- `tests/mcp_server/integration/test_issue39_cross_machine.py`
- any workflow/config tests that directly load the contract file

### Gates

Run file-scoped quality gates for:
- `.st3/config/phase_contracts.yaml`
- touched manager files if code is adjusted to support new contract coverage
- touched documentation files when edited in this phase

### Runtime

- restart the server only if config/runtime wiring changes require it
- confirm `health_check()` returns `OK`

---

## Scope Guardrails

### In Scope

- updating issue #257 documentation to match the implemented refactor
- defining the next safe completion pass for `phase_contracts.yaml`
- filling missing workflow contract entries that are already implied by current config structure

### Out of Scope

- new runtime refactors outside documentation/config completion
- broad cleanup of unrelated ST3 debt
- speculative workflow renaming from `implementation` to `tdd` in this documentation-only pass
- redesign of `workflows.yaml` / `workphases.yaml` responsibilities beyond documenting and safely extending the current contract model

If filling `phase_contracts.yaml` reveals a runtime gap that requires code changes beyond trivial alignment, that work should re-enter a new validation/TDD cycle instead of being folded silently into documentation.

---

## Expected Documentation-Phase Outputs

By the end of the documentation phase, issue #257 should have:

- an updated `validation_report.md`
- one final documentation-phase handover
- refreshed Threshold B planning/design status docs
- an updated issue timeline
- a documented next step for completing `phase_contracts.yaml`
- optionally, a partially expanded `phase_contracts.yaml` covering the safe workflow set

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-05 | Agent | Initial documentation-phase close-out and phase-contract completion plan |
