<!-- c:\temp\st3\docs\development\issue251\design_v3.md -->
<!-- template=design version=5827e841 created=2026-02-28T13:56Z updated=2026-02-28 -->
# Issue #251 Design v3: minimal scope-safe state contract for run_quality_gates

**Status:** APPROVED  
**Version:** 1.2  
**Last Updated:** 2026-02-28

---

## Purpose

Define the minimal design contract needed to keep stabilization TDD cycles focused and prevent scope creep.

## Scope

**In Scope:**
Scope-safe baseline mutation policy, failed_files semantics, and explicit effective-scope propagation for run_quality_gates only.

**Out of Scope:**
Shared optimization engine, context-fingerprint architecture rollout, run_tests refactor, and broad performance improvements.

## Prerequisites

Read these first:
1. research_v3 approved

---

## 1. Context & Requirements

### 1.1. Problem Statement

Current run_quality_gates behavior is unstable across scope switching because state mutation and rerun semantics are not strictly bound to effective scope.

### 1.2. Requirements

**Functional:**
- [x] Only effective auto runs may mutate auto baseline lifecycle fields.
- [x] failed_files must represent actual failing targets only.
- [x] Effective scope must be explicit and consistent through tool-to-manager run flow.
- [x] Scope switching must preserve deterministic state behavior.

**Non-Functional:**
- [x] Minimal implementation impact within issue251 boundaries.
- [x] Deterministic and debuggable state transitions.
- [x] No behavior regression for intended auto lifecycle semantics.

### 1.3. Constraints

- Do not broaden issue251 into multi-tool optimization refactor.
- Keep changes test-driven and limited to stabilization blockers.
- Avoid introducing new persistent schema structures in this issue.

---

## 2. Design Options

### Option A — Full architecture rollout now

- Apply shared optimization architecture immediately (fingerprints + orchestrator concepts).
- **Pros:** long-term alignment with issue255 target model.
- **Cons:** high change surface, high risk of destabilizing issue251 timeline.

### Option B — Ad-hoc localized fixes only

- Patch each bug location independently without explicit contract.
- **Pros:** fastest initial coding.
- **Cons:** high risk of inconsistent semantics between cycles and regressions on scope switches.

### Option C — Minimal policy contract (chosen)

- Introduce a strict minimal contract for scope mutation + failed target semantics + explicit effective scope propagation.
- **Pros:** smallest stable path, clear TDD boundaries, low refactor risk.
- **Cons:** does not deliver long-term optimization architecture (deferred to issue255).

---

## 3. Chosen Design

**Decision:** Adopt a minimal policy-guard design: enforce explicit effective-scope contracts and constrain state mutation semantics without introducing a new optimization architecture.

**Rationale:** This is the smallest design surface that can deliver stable daily usage quickly while deferring broad architectural refactor to issue255.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| D1 — Auto-only baseline mutation | Prevents non-auto runs from mutating global baseline lifecycle fields and corrupting `auto` behavior. |
| D2 — Fail-subset-only persistence | Keeps `failed_files` semantically correct and deterministic for rerun narrowing. |
| D3 — Explicit effective scope propagation | Ensures one authoritative scope value across tool invocation and manager mutation policy. |
| D4 — Scope-switch invariants as contract tests | Locks behavior for `auto↔files`, `branch↔files`, `project→auto` so stability is verifiable. |

### 3.2. Contract Rules (implementation-level)

1. Non-auto scopes (`files`, `branch`, `project`) must not update `baseline_sha`.
2. Non-auto scopes must not clear or overwrite auto lifecycle `failed_files` state.
3. Persisted failed set updates must derive from actual failing targets only.
4. Effective scope used for target resolution must be the same scope used for mutation policy.
5. Switching sequence `auto→files→auto` must preserve expected auto rerun candidates and baseline lifecycle invariants.

### 3.3. Mapping to Planning Cycles

- Cycle 1 ↔ D1
- Cycle 2 ↔ D2
- Cycle 3 ↔ D3
- Cycle 4 ↔ D4 (+ Contract Rule 5)
- Cycle 5 validates all D1–D4 and Contract Rule 5 via live scenarios

### 3.4. Not Needed for issue251 (explicit deferrals)

- Context fingerprint storage model redesign
- Shared cross-tool optimization orchestrator
- run_tests implementation alignment

Those belong to issue255.

---

## 4. Review (Critical)

### 4.1 Is extra design work still needed before TDD?

No additional broad design is required.

This `design_v3` is sufficient because it defines:
- strict boundaries,
- concrete contract rules,
- one-to-one mapping with planning cycles,
- explicit deferrals to issue255.

### 4.2 Remaining ambiguity to close during TDD

Only low-level code placement choices remain (where the scope guard helper lives, and exact test module placement). These are implementation details, not architecture decisions.

### 4.3 Focus check

If any cycle proposes new state schema, fingerprint model, or cross-tool abstractions, it is out-of-scope for issue251 and must be rejected or moved to issue255.

## Related Documentation
- **[docs/development/issue251/research_v3.md][related-1]**
- **[docs/development/issue251/planning_v3.md][related-2]**
- **[docs/development/issue255/research_scope_aware_rerun_optimization.md][related-3]**

<!-- Link definitions -->

[related-1]: docs/development/issue251/research_v3.md
[related-2]: docs/development/issue251/planning_v3.md
[related-3]: docs/development/issue255/research_scope_aware_rerun_optimization.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-28 | Agent | Initial scaffold draft |
| 1.1 | 2026-02-28 | Agent | Added minimal policy contract, option analysis, cycle mapping, explicit deferrals, and critical readiness review |
| 1.2 | 2026-02-28 | Agent | Corrected prerequisite order (research before design) and added explicit switch-invariant contract rule |
