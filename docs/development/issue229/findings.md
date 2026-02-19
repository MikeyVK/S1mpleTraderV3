# Issue #229 — Trial Run Findings

**Type:** LIVING DOCUMENT  
**Branch:** `feature/229-phase-deliverables-enforcement`  
**Last Updated:** 2026-02-19

This document records gaps and observations found during the live trial run of the #229 branch. It covers both #146 machinery validation and newly discovered gaps not present in research.md.

---

## Gap Index

| ID | Severity | Area | Status |
|----|----------|------|--------|
| [GAP-01](#gap-01) | High | PhaseStateEngine | ✅ Fixed (C2) |
| [GAP-02](#gap-02) | High | PhaseStateEngine | ✅ Fixed (C2) |
| [GAP-03](#gap-03) | Medium | PhaseStateEngine | ✅ Fixed (C3) |
| [GAP-04](#gap-04) | Medium | MCP Tools | Pending (C4) |
| [GAP-05](#gap-05) | Medium | DeliverableChecker | ✅ Fixed (C2 re-run) |
| [GAP-06](#gap-06) | Medium | SavePlanningDeliverablesTool | Pending (C4) |
| [GAP-07](#gap-07) | Medium | MCP Git Tool | ✅ Fixed (C2 re-run) |
| [GAP-08](#gap-08) | Medium | ForceCycleTransitionTool | ✅ Fixed (C3) |

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
**Addressed by:** #229 Cycle 3 — forced transition skipped-gate warning

---

## GAP-04

**Title:** `save_planning_deliverables` not exposed as MCP tool  
**Severity:** Medium  
**Observed:** No MCP tool exists to save planning deliverables — only `ProjectManager.save_planning_deliverables()` as internal API  
**Expected:** Agent/user should be able to call a tool to persist deliverables from the planning phase without directly editing `projects.json`  
**Impact:** Trial run required direct `projects.json` editing to set up deliverables — not a valid workflow  
**Addressed by:** #229 Cycle 4 (D4.1/D4.2) — `SavePlanningDeliverablesTool` in `project_tools.py` + registered in `server.py`

---

## Post-Implementation Gaps (2026-02-19 smoke-test session)

Discovered during smoke-test of the live implementation and follow-up Q&A after C1+C2 completion.

| ID | Severity | Area | Status |
|----|----------|------|--------|
| [GAP-05](#gap-05) | Medium | DeliverableChecker | ✅ Fixed |
| [GAP-06](#gap-06) | Medium | SavePlanningDeliverablesTool | Pending |
| [GAP-07](#gap-07) | Medium | MCP Git Tool | ✅ Fixed (C2 re-run) |
| [GAP-08](#gap-08) | Medium | ForceCycleTransitionTool | ✅ Fixed (C3) |

---

## GAP-05

**Title:** `file_exists` has no glob/pattern support  
**Severity:** Medium  
**Observed:** `_check_file_exists` resolves `spec["file"]` as a literal path via `Path(relative_file)`. A pattern like `docs/development/issue229/*research*.md` is interpreted as a filename and fails because no such literal file exists.  
**Expected:** Agents should be able to declare deliverables without knowing the exact filename upfront — e.g. "a `*research*.md` file must exist in `docs/development/issue229/`".  
**Root cause:** `_resolve()` always produces a single `Path` object; `glob()` is never called.  
**Proposed fix:** Add `file_glob` check type (or optional `glob: true` flag on `file_exists`) that uses `Path.glob()` and raises if no matches are found.  
**Addressed by:** #229 Cycle 2 re-run

---

## GAP-06

**Title:** `SavePlanningDeliverablesTool` has no input schema validation  
**Severity:** Medium  
**Observed (anticipated):** The tool will accept any JSON payload via MCP. An agent can save deliverables with invalid or incomplete `validates` entries (wrong `type`, missing `file`, etc.) that only fail at planning exit gate — not at save time.  
**Expected:** The tool should validate each `validates` entry on write, and return a structured error listing available types and required fields per type — matching the pattern established by the scaffold tool.  
**Note:** MCP tool input schema (JSON Schema exposed via the MCP protocol) serves as Layer 1 contract — agents know the top-level parameter shape. Layer 2 (semantic validation inside the tool at runtime) is needed for the `validates` sub-entries which are dynamically typed (`type` determines which other fields are required).  
**Addressed by:** #229 Cycle 4 scope extension (schema validation + helpful error messages)

---

## GAP-07

**Title:** `git_add_or_commit` does not validate `workflow_phase` + `cycle_number` against `state.json`  
**Severity:** Medium  
**Observed:** Agent committed with `workflow_phase="tdd"`, `cycle_number=2` while `state.json.current_phase="design"`. Tool accepted the call without error. Commits were scoped correctly per the parameters, but the state was inconsistent — no enforcement of the actual project phase.  
**Expected:** Tool blocks when the provided `workflow_phase` doesn't match `state.json.current_phase`, or (in TDD) when `cycle_number` doesn't match `state.json.current_tdd_cycle`. Error message should name the mismatch and the transitions needed to resolve it.  
**Root cause:** `git_add_or_commit` uses `workflow_phase` / `cycle_number` purely for commit message scope generation — it never reads `state.json`.  
**Proposed fix:** Before generating the commit, read `state.json`, compare `workflow_phase` vs `current_phase` (and `cycle_number` vs `current_tdd_cycle` when phase is `tdd`), raise `CommitPhaseMismatchError` with actionable message if mismatched.  
**Addressed by:** #229 Cycle 2 re-run (D2.4) — small addition to existing C2 scope

---

## GAP-08

**Title:** `force_cycle_transition` does not warn when skipped cycles have unvalidated deliverables  
**Severity:** Medium  
**Observed:** `force_cycle_transition(to_cycle=4)` while cycle 3 deliverables (D3.1) not yet validated — tool succeeded silently. The `skipped_cycles` list is written to the audit trail, but no warning is surfaced about unvalidated work.  
**Expected:** Tool warns when any skipped cycle has deliverables that don't pass `DeliverableChecker`. The transition still succeeds (forced = unconditional escape hatch), but the agent/user sees which deliverables were bypassed.  
**Root cause:** `ForceCycleTransitionTool.execute()` checks `planning_deliverables` for existence but never runs `DeliverableChecker` on the skipped cycles' deliverables.  
**Proposed fix:** After computing `skipped_cycles`, iterate each skipped cycle's `deliverables` list, run `DeliverableChecker.check()` per entry, collect failures, and append `⚠️ Unvalidated cycle deliverables: cycle:N:ID (description)` to the tool response — same pattern as GAP-03.  
**Addressed by:** #229 Cycle 3 (D3.2) — scope extension aligned with GAP-03 pattern

---

## Validation Strategy Discussion

**Decision: Structural checks only — no acceptance tests per phase**

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

## #146 Trial Observations *(pre-remediation snapshot)*

> These observations were recorded before planning was finalised. They reflect the system state with no deliverable gates in place. Do not use as post-remediation validation — see design/TDD phase for that.

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
