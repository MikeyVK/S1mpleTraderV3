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
**Addressed by:** #229 Cycle 2 (D2.3) — `SavePlanningDeliverablesTool` in `project_tools.py`

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

**Decision: Option C — Structural checks only (no acceptance tests per phase)**

Rationale:
- Acceptance tests written by the same agent doing the phase work = "slager keurt eigen vlees" — self-verification without independence
- Per-phase test files distract the agent from the actual phase deliverable
- Content-level validation of scaffold output against template structure is not yet possible (no template-vs-artifact diff tooling)
- Extensibility: structural checks are a sound foundation to layer richer checks on later

**Selected approach:**

| Deliverable type | Check | Mechanism |
|-----------------|-------|-----------|
| Scaffolded document (`.md`) | File exists + `<!-- template=X version=Y -->` SCAFFOLD header present | Engine reads first 3 lines |
| Config key (YAML/JSON) | Key path exists in file | Engine resolves dot-notation path |
| Future | Structural diff against template schema | Not in scope for #229 |

**Response verbosity design:**

| Scenario | Response |
|----------|----------|
| Transition with exit gate — deliverables pass | `✅ planning → design \| exit gate: N/N deliverables checked (D1.1 ✓ D1.2 ✓ ...)` |
| Transition without exit gate | `✅ research → planning` (stil, geen gate) |
| Transition with exit gate — deliverable fails | `❌ ... \| exit gate: D1.2 FAILED — file not found: mcp_server/managers/deliverable_checker.py` |

Conditionally verbose: alleen rapporteren wanneer er daadwerkelijk een gate was. Onderdeel van Cycle 2.

**Deliberately out of scope for #229:**
- Validating scaffold output *content* against template structure
- YAML-key value validation (presence is enough)
- Acceptance test files per phase
- Detailed validation logic per artifact type beyond the two checks above

**Extension path:** The `validates` schema on each deliverable entry is intentionally simple now. A future issue can add `type: yaml_key_value`, `type: test_passes`, etc. without breaking existing deliverables.

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
