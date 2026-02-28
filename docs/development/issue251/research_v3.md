<!-- c:\temp\st3\docs\development\issue251\research_v3.md -->
<!-- template=research version=8b7bb3ab created=2026-02-28T13:45Z updated=2026-02-28 -->
# Issue #251 Research v3: Scope stability blockers for run_quality_gates

**Status:** READY FOR PLANNING  
**Version:** 1.1  
**Last Updated:** 2026-02-28

---

## Purpose

Provide a precise, execution-ready baseline of the **currently open** issues that prevent stable daily usage of `run_quality_gates` across all four scope modes (`auto`, `branch`, `project`, `files`), including switching between scopes.

## Scope

**In Scope:**
- Current open stability blockers in `run_quality_gates`
- Scope-switch behavior (`auto↔files`, `branch↔files`, `project→auto`)
- Root-cause mapping to existing code paths
- Minimal acceptance criteria for stabilization cycles in issue #251

**Out of Scope:**
- Broad optimization/refactor architecture across tools (`run_quality_gates` + `run_tests`)  
  → owned by issue #255
- New optimization engine implementation (context-fingerprint orchestrator)
- Performance benchmarking and throughput tuning
- Re-documenting already resolved findings unless they are still open

## Prerequisites

Read these first:
1. [live-validation-plan-v2.md](live-validation-plan-v2.md)
2. [planning.md](planning.md)
3. [research_scope_aware_rerun_optimization.md](research_scope_aware_rerun_optimization.md) (relocation note to issue #255)
4. [../issue255/research_scope_aware_rerun_optimization.md](../issue255/research_scope_aware_rerun_optimization.md) (architecture context only)

---

## Problem Statement

`run_quality_gates` currently has state-handling and rerun-semantic gaps that make behavior unreliable when moving between scopes. The most critical issue is scope-agnostic baseline mutation (F-21): a successful narrow-scope run can mutate global baseline state (`baseline_sha`, `failed_files`) as if a full workspace validation occurred.

As a result, users can observe false cleanup of failure state, incorrect rerun candidates, and non-deterministic outcomes after scope switches.

## Research Goals

- Document only open blockers that currently impact stability.
- For each blocker: describe symptom, reproducible scope-switch path, root cause, and operational impact.
- Define minimal stabilization acceptance criteria that planning/TDD can execute with low effort in issue #251.

## Related Documentation

- [live-validation-plan-v2.md](live-validation-plan-v2.md)
- [planning.md](planning.md)
- [quality_gate_findings.md](quality_gate_findings.md)
- [../issue255/research_scope_aware_rerun_optimization.md](../issue255/research_scope_aware_rerun_optimization.md)

---

## Findings

### Finding overview by cluster

| Cluster | Findings | Status | Blocks stable daily use? |
|---------|----------|--------|--------------------------|
| A — State mutation safety | F-21 | Open | ✅ Yes |
| B — Scope context coupling | S-1 | Open | ✅ Yes |
| C — Failed-files semantics | S-2 | Open | ✅ Yes |
| D — Scope-switch isolation | S-3 | Open | ✅ Yes |

---

## Investigation A: State Mutation Safety (F-21)

**Finding:** F-21 (from live validation)  
**Severity:** Critical  
**Blocks stable daily use:** Yes

### Symptom

After a passing run in `scope="files"` (or other narrow scopes), baseline-related state is mutated as if a full `auto`-state validation succeeded.

Observed effect:
- `failed_files` can be cleared although only a subset was evaluated.
- `baseline_sha` can advance to `HEAD` even when unresolved failures still exist outside that subset.

### Repro path (scope switch)

1. Start with non-empty `failed_files` in `state.json`.
2. Run a passing `scope="files"` call on one clean file.
3. Switch to `scope="auto"`.
4. Observe inconsistent rerun set versus expected persisted failures.

### Root cause (code area)

In `mcp_server/managers/qa_manager.py`, post-run baseline mutation logic is applied without strict scope guard tied to `scope="auto"` semantics.

### Required stabilization direction (minimal)

- Apply baseline mutation (`_advance_baseline_on_all_pass`, `_accumulate_failed_files_on_failure`) only when effective run mode is `auto`.
- Treat `files`, `branch`, `project` as scoped evaluations that must not claim global baseline success/failure for auto-state.

---

## Investigation B: Scope Context Coupling Gap (S-1)

**Finding:** S-1 (open architectural/flow gap)  
**Severity:** High  
**Blocks stable daily use:** Yes

### Symptom

Scope is resolved in tool flow, but mutation behavior is not consistently driven by the same explicit scope context in downstream state transitions.

### Repro path (scope switch)

1. Alternate `auto` and `files` runs in short sequence.
2. Compare expected state transitions per scope intent with actual state mutation.
3. Mutation side-effects can reflect generic run outcome rather than scope contract.

### Root cause (code area)

Coupling mismatch between `mcp_server/tools/quality_tools.py` run invocation context and state mutation decisions in `mcp_server/managers/qa_manager.py`.

### Required stabilization direction (minimal)

- Make effective scope explicit and authoritative through the full run pipeline.
- Ensure state mutation policy reads that same effective scope (single source of truth).

---

## Investigation C: Failed-files Semantics Drift (S-2)

**Finding:** S-2 (open correctness gap)  
**Severity:** High  
**Blocks stable daily use:** Yes

### Symptom

`failed_files` handling can drift from actual failing subset semantics, causing reruns to include wrong files or miss intended narrowing behavior.

### Repro path (scope switch)

1. Run a mixed-result scope where only a subset fails.
2. Switch to `auto` and inspect rerun candidates.
3. Candidate set may not align exactly with true failing files from the prior effective auto-context.

### Root cause (code area)

Failure accumulation/update logic in `mcp_server/managers/qa_manager.py` is not strictly constrained to target-level failing outcomes under correct scope policy.

### Required stabilization direction (minimal)

- Accumulate only true failing targets.
- Preserve deterministic semantics: rerun set must reflect `persisted_failed ∪ changed_since_baseline` for `auto`.
- Avoid broad replacement/clearing side effects from non-auto runs.

---

## Investigation D: Scope-switch Isolation Risk (S-3)

**Finding:** S-3 (open model limitation in current flow)  
**Severity:** High  
**Blocks stable daily use:** Yes

### Symptom

Current state model for auto baseline can be affected by non-auto runs, creating practical cross-scope contamination risk.

### Repro path (scope switch matrix)

| Switch path | Expected | Current risk |
|-------------|----------|--------------|
| `auto → files → auto` | `files` run is local check only; auto-state remains authoritative | `files` outcome may mutate auto-state |
| `branch → files → branch` | branch checks remain independent of auto baseline mutation | narrow run side-effects can alter subsequent expectations |
| `project → auto` | project run informs local outcome only; auto drives baseline lifecycle | prior scoped mutations can distort auto rerun inputs |

### Root cause (code area)

Single local state artifacts (`.st3/state.json`) with insufficient scope-isolation guarantees in current mutation path.

### Required stabilization direction (minimal)

- Enforce operational isolation rule: non-auto scopes cannot mutate auto baseline lifecycle fields.
- Keep broad context-fingerprint redesign in issue #255; only apply minimal guardrails here.

---

## Minimal Stabilization Acceptance Criteria (Issue #251)

Issue #251 can proceed to GO for practical daily use when all are true:

1. `scope="files"`, `scope="branch"`, and `scope="project"` no longer mutate `baseline_sha` or clear/override `failed_files` used by `auto` baseline lifecycle.
2. `scope="auto"` continues to perform deterministic lifecycle updates:
   - on all-pass: advance `baseline_sha`, clear `failed_files`;
   - on fail: keep baseline, update failed set from actual failing targets only.
3. Switching sequence `auto→files→auto` preserves correct auto rerun candidates.
4. Switching sequence `branch→files→branch` does not induce baseline side-effects.
5. Live validation can reproduce stable behavior across all four scopes without state corruption indicators.

---

## Planning Input (next phase)

Recommended low-effort execution order in issue #251:

1. Add strict scope guard on baseline mutation path.
2. Tighten failed-target accumulation semantics.
3. Add focused tests for scope-switch transitions and state invariants.
4. Re-run live validation scenarios for all 4 scopes with switch paths.

This sequence intentionally avoids broad refactor and preserves the issue251 boundary.

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-28 | Agent | Initial scaffold draft |
| 1.1 | 2026-02-28 | Agent | Added open blocker analysis, scope-switch investigations, and minimal stabilization acceptance criteria for issue #251 |
