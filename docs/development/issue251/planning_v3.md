<!-- c:\temp\st3\docs\development\issue251\planning_v3.md -->
<!-- template=planning version=130ac5ea created=2026-02-28T13:51Z updated=2026-02-28 -->
# Issue #251 Planning v3: minimal stabilization for multi-scope reliability

**Status:** COMPLETED (HISTORICAL RECORD)  
**Version:** 1.2  
**Last Updated:** 2026-02-28

---

## Purpose

Define a minimal-effort, correctness-first cycle plan from research_v3 to stable daily usage.

## Scope

**In Scope:**
Scope-safe baseline mutations, explicit scope-context propagation, failed_files semantics hardening, and live validation for all four scopes.

**Out of Scope:**
Broad shared optimization refactor (issue #255), run_tests behavior changes, and performance optimization.

## Prerequisites

Read these first:
1. research_v3 approved
2. design_v3 approved (cycle contract baseline)
3. branch phase transitioned to planning
4. baseline live scenarios from live-validation-plan-v2 available
---

## Summary

Plan focused TDD cycles that fix only open stability blockers in run_quality_gates across auto, branch, project, and files including scope switching, explicitly grounded in the minimal contract defined in `design_v3.md`.

---

## Dependencies

- Cycle 1 must complete before Cycle 2 state assertions
- Cycle 2 semantics tests must pass before Cycle 3 integration checks
- Cycle 4 requires Cycles 1–3 fully green to keep switch-invariant failures non-ambiguous

---

## TDD Cycles

### Cycle 1: Scope-guard baseline mutation (F-21)

**Goal:**
Ensure baseline lifecycle mutations are allowed only for effective `scope="auto"` runs.

**Tests:**
- RED: add/adjust unit test proving `scope="files"` pass must not advance `baseline_sha`.
- RED: add/adjust unit test proving `scope="branch"`/`scope="project"` pass must not clear `failed_files`.
- GREEN: implement strict scope guard in post-run mutation path.
- REFACTOR: centralize scope guard predicate to avoid duplicated branch logic.

**Success Criteria:**
- Non-auto scopes never mutate auto baseline lifecycle fields.
- Existing auto lifecycle tests keep current intended behavior.

### Cycle 2: Tighten failed_files semantics (S-2)

**Goal:**
Align `failed_files` updates to actual failing targets only.

**Tests:**
- RED: auto-scope mixed-result run must persist only the failing-file subset.
- RED: auto-scope mixed-result run must not persist the full evaluated set when only a subset fails.
- GREEN: update accumulation/update logic to use true fail subset.
- REFACTOR: remove broad-set mutation paths that are not subset-accurate.

**Success Criteria:**
- Persisted failed set is deterministic and subset-accurate.
- `scope="auto"` rerun candidates remain explainable from state.

### Cycle 3: Enforce explicit effective-scope propagation (S-1)

**Goal:**
Guarantee one authoritative effective scope value across tool → manager → state mutation decisions.

**Tests:**
- RED: given `scope="files"`, post-run state must keep `baseline_sha` and `failed_files` unchanged regardless of overall_pass.
- RED: alternating scope calls (`auto`, `files`, `auto`) keep expected state transitions.
- GREEN: propagate/normalize effective scope as explicit input for mutation policy.
- REFACTOR: reduce implicit/default scope branches in mutation code.

**Success Criteria:**
- Scope intent is explicit and consistent across run pipeline.
- No mutation side effects based on ambiguous default scope handling.

### Cycle 4: Add scope-switch invariants test set (S-3)

**Goal:**
Lock practical stability across scope switching with focused invariant tests.

**Tests:**
- RED: `auto → files → auto` preserves expected auto rerun candidates.
- RED: `branch → files → branch` introduces no auto baseline side effects.
- RED: `project → auto` does not corrupt auto lifecycle assumptions.
- GREEN: implement minimal glue/guards needed for all invariants.
- REFACTOR: simplify repeated state setup in tests via shared fixtures.

**Success Criteria:**
- All switch-path invariants pass reliably.
- State transitions are deterministic and debuggable.

### Cycle 5: Acceptance validation closure (non-TDD cycle)

**Goal:**
Validate that issue251 acceptance criteria are met in realistic tool execution.

**Tests / Validation Steps:**
- This cycle has no automated RED phase; it is a live acceptance execution step.
- Execute focused scenarios from `live-validation-plan-v2.md` for all four scopes.
- Execute explicit switch paths: `auto↔files`, `branch↔files`, `project→auto`.
- Verify no unwanted baseline mutation on non-auto runs.
- Verify `auto` lifecycle: fail preserves baseline + updates failed set; all-pass advances baseline + clears failed set.

**Success Criteria:**
- All minimal stabilization acceptance criteria from `research_v3.md` are satisfied.
- Tool is stable enough for daily use without broad refactor.


---

## Risks & Mitigation

- **Risk:** Auto lifecycle behavior regresses while fixing non-auto mutation guards.
  - **Mitigation:** Keep explicit regression checks for current auto all-pass/fail behavior in every cycle.
- **Risk:** Scope-switch bugs remain hidden if tests only cover isolated single-scope runs.
  - **Mitigation:** Make switch-path invariants mandatory in Cycle 4 before live validation.
- **Risk:** Broad refactor creep slows stabilization delivery.
  - **Mitigation:** Enforce issue boundary: minimal guards/semantics only; defer architecture redesign to issue #255.

---

## Milestones

- M1: state mutation guard in place
- M2: failed-target semantics deterministic
- M3: 4-scope + switch-path validation pass

## Related Documentation
- **[docs/development/issue251/research_v3.md][related-1]**
- **[docs/development/issue251/live-validation-plan-v2.md][related-2]**
- **[docs/development/issue251/design_v3.md][related-3]**
- **[docs/development/issue255/research_scope_aware_rerun_optimization.md][related-4]**

<!-- Link definitions -->

[related-1]: docs/development/issue251/research_v3.md
[related-2]: docs/development/issue251/live-validation-plan-v2.md
[related-3]: docs/development/issue251/design_v3.md
[related-4]: docs/development/issue255/research_scope_aware_rerun_optimization.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-28 | Agent | Initial scaffold draft |
| 1.1 | 2026-02-28 | Agent | Added TDD-ready stabilization cycles, risks/mitigation, and explicit issue251 scope boundaries |
| 1.2 | 2026-02-28 | Agent | Addressed QA pre-TDD review: dependencies, cycle specificity, non-TDD acceptance closure, and explicit design_v3 grounding |