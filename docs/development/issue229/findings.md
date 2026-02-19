# Issue #229 — Trial Run Findings

**Type:** LIVING DOCUMENT  
**Branch:** `feature/229-phase-deliverables-enforcement`  
**Last Updated:** 2026-02-19

This document records gaps and observations found during the live trial run of the #229 branch. It covers both #146 machinery validation and newly discovered gaps not present in research.md.

---

## Gap Index

| ID | Severity | Area | Status |
|----|----------|------|--------|
| [GAP-01](#gap-01) | High | PhaseStateEngine | Confirmed |
| [GAP-02](#gap-02) | High | PhaseStateEngine | Confirmed |
| [GAP-03](#gap-03) | Medium | PhaseStateEngine | Confirmed |
| [GAP-04](#gap-04) | Medium | MCP Tools | Confirmed |
| [GAP-05](#gap-05) | Low | Scaffold templates | Confirmed |

---

## GAP-01

**Title:** Planning exit is silent — no deliverable gate  
**Severity:** High  
**Observed:** `planning → design` transition succeeded with no `planning_deliverables` in `projects.json`  
**Expected:** `ValueError` blocking the transition until deliverables are saved  
**Root cause:** `transition()` has no `on_exit_planning_phase` hook; only TDD hooks are wired  
**Addressed by:** #229 (this issue)

---

## GAP-02

**Title:** TDD entry gate placed at wrong layer  
**Severity:** High  
**Observed:** `design → tdd` raised `ValueError: Planning deliverables not found for issue 229`  
**Expected:** The check should have fired on Planning *exit*, not TDD *entry*  
**Root cause:** `on_enter_tdd_phase` validates planning deliverables — violates separation of concerns  
**Addressed by:** #229 (this issue)

---

## GAP-03

**Title:** Forced transition bypasses all hooks and deliverable checks  
**Severity:** Medium  
**Observed:** `force_transition(tdd → planning)` succeeded with no hooks, no warnings, no checks  
**Expected:** At minimum a `logger.warning` that a forced transition skipped deliverable validation  
**Note:** Forced transitions already require `skip_reason + human_approval` — the audit trail exists, but nothing is logged about skipped gates  
**Addressed by:** #229 (open question: in or out of scope for this issue)

---

## GAP-04

**Title:** `save_planning_deliverables` not exposed as MCP tool  
**Severity:** Medium  
**Observed:** No MCP tool exists to save planning deliverables — only `ProjectManager.save_planning_deliverables()` as internal API  
**Expected:** Agent/user should be able to call a tool to persist deliverables from the planning phase without directly editing `projects.json`  
**Impact:** Trial run required direct `projects.json` editing to set up deliverables — not a valid workflow  
**Addressed by:** Separate issue needed (out of scope for #229)

---

## GAP-05

**Title:** Scaffold template renders list fields as Python repr instead of Markdown bullets  
**Severity:** Low  
**Observed:** `scope_in`, `scope_out`, and `findings` in `research.md` were rendered as `['item1', 'item2']` instead of `- item1\n- item2`  
**Root cause:** Template likely lacks a loop/join filter for list-type context variables  
**Impact:** Manual post-scaffold editing required to fix list formatting  
**Addressed by:** Separate issue needed (template bug, out of scope for #229)

---

## Validation Strategy Discussion

**Open question from trial:** How do we validate that phase deliverables are *actually* delivered, beyond a JSON entry that is essentially self-declared?

Options under consideration (see planning.md when created):

| Option | Mechanism | Depth |
|--------|-----------|-------|
| A | `validates` key per deliverable: `yaml_key`, `file_exists`, `scaffold_header` checks | Structural |
| B | Acceptance test per phase: `tests/acceptance/issue229/` | Test-suite integrated |
| C | SCAFFOLD-header check for docs + key-path check for config | Hybrid structural |
| D | Combination of C + B | Structural + automated |

**Current lean:** Option D — structural checks in the engine, acceptance tests in the suite.

---

## #146 Trial Observations

| Step | Result | Notes |
|------|--------|-------|
| `initialize_project(229)` | ✅ | `state.json` created with `current_tdd_cycle=None`, `tdd_cycle_history=[]` |
| `research → planning` (sequential) | ✅ | No issues |
| `planning → research` (forced backward) | ✅ | `forced=True`, `skip_reason` recorded in `state.json` |
| `planning → design` (no deliverables) | ✅ silent | **GAP-01 confirmed** — exit gate missing |
| `design → tdd` (no deliverables) | ❌ blocked | **GAP-02 confirmed** — gate fires on wrong layer |
| `force_transition(tdd → planning)` | ✅ no hooks | **GAP-03 confirmed** — forced bypasses everything |
| `save_planning_deliverables` via tool | ❌ no tool | **GAP-04 confirmed** — internal API only |

Pending (after planning deliverables are legitimately produced):

| Step | #146 Feature | Expected |
|------|-------------|---------|
| `planning → design → tdd` with deliverables | `on_enter_tdd_phase` init | `current_tdd_cycle=1` |
| Commit `cycle_number=1, sub_phase="red"` | Scope generation | `test(P_TDD_SP_C1_RED): ...` |
| `transition_cycle(to_cycle=2)` | Cycle history | `current_tdd_cycle=2` |
| `tdd → validation` | `on_exit_tdd_phase` | `last_tdd_cycle=2`, `current_tdd_cycle=None` |
