<!-- c:\temp\st3\docs\development\issue290\research-issue139-get-project-plan-current-phase.md -->
<!-- template=research version=8b7bb3ab created=2026-04-26T13:03Z updated=2026-04-26 -->
# Research — Issue #139 GetProjectPlan Current Phase

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-04-26

---

## Purpose

Revalidate whether issue #139 still reflects the current implementation or has been resolved or superseded by later plan/state integration work.

## Scope

**In Scope:**
ProjectManager.get_project_plan, returned phase fields, phase-source semantics, and relation to state-aware detection.

**Out of Scope:**
GetWorkContextTool output, submit_pr behavior, and branch creation semantics.

## Prerequisites

Read these first:
1. Issue #139 description
2. mcp_server/managers/project_manager.py
3. mcp_server/core/phase_detection.py
4. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Problem Statement

Issue #139 reported that get_project_plan returned workflow definition data but omitted current phase information from state-aware phase detection.

## Research Goals

- Check the current ProjectManager.get_project_plan implementation against the original issue statement.
- Determine whether the issue is still active, partially resolved, or superseded.
- Capture any remaining root problem if the original statement is stale.
- Define expected results for either closure or reframing.

---

## Background

Issue #139 originated when get_project_plan reportedly returned only workflow metadata without current phase information.

The current implementation now explicitly documents Issue #139 in the method body and augments the returned plan with `current_phase`, `phase_source`, and `phase_detection_error` fields via ScopeDecoder.

---

## Findings

### Finding 1 — The original issue statement is substantially stale

The current ProjectManager.get_project_plan implementation does return current phase information. The method now appends:

- `current_phase`
- `phase_source`
- `phase_detection_error`

That means the issue's original complaint, "does not return current_phase," no longer matches the current implementation.

### Finding 2 — The tool has moved from omission to interpretation

The remaining question is no longer whether current phase is returned. The question is whether the returned phase is interpreted correctly in edge cases.

The method uses ScopeDecoder with commit-aware detection and fallback-to-state behavior. So the current risk is interpretive precedence, not missing data.

### Finding 3 — Any remaining defect is about reconciliation semantics, not absent fields

Immediately after transitions or forced transitions, commit-scope precedence may still produce a phase value that lags the most recently persisted state transition until a new phase-aligned commit exists.

If that behavior is undesirable, then the follow-up issue should be framed around precedence or read-model reconciliation. It should not remain framed as a missing `current_phase` field bug.

### Finding 4 — The tool is now more explicit than the original request demanded

By returning `phase_source` and `phase_detection_error` alongside `current_phase`, the tool already exposes more diagnostic information than the original issue requested.

That is good architectural progress because it makes interpretation provenance explicit.

---

## Architecture Check

### Alignment with Explicit over Implicit

The current implementation improves on the original gap by surfacing not just a phase value, but also where that phase came from.

### Alignment with SSOT

The remaining tension is not a total SSOT violation. It is a reconciliation question between state.json and commit-derived evidence.

### Alignment with SRP

If this surface still needs improvement, the next step should be a clearer shared workflow snapshot contract, not more one-off plan mutations.

---

## Solution Directions

### Direction A — Close or rewrite issue #139 as stale

The issue should not remain open under its original wording because the named missing field is now present.

### Direction B — If follow-up work is needed, reframe it around phase precedence semantics

A narrower follow-up could ask whether `current_phase` in plan output should prioritize recent transitions differently in certain local workflow windows.

### Direction C — Keep tests focused on both presence and provenance

Tests in this area should continue verifying not just that `current_phase` exists, but that `phase_source` and error semantics remain explicit.

---

## Expected Results

This research supports the following expected outcomes for issue #139:

- The original issue should be treated as largely resolved or stale in its current wording.
- Any replacement issue should focus on precedence/reconciliation semantics rather than missing `current_phase` output.
- get_project_plan should continue returning `current_phase`, `phase_source`, and `phase_detection_error` together.

## Open Questions

- Should current phase in plan output prefer the most recent persisted transition over commit-scope in certain forced-transition windows?
- Do we want get_project_plan and get_work_context to share one typed workflow snapshot contract?

## Related Documentation

- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[mcp_server/managers/project_manager.py][related-2]**
- **[mcp_server/core/phase_detection.py][related-3]**
- **[docs/development/issue290/research-issue231-state-snapshot.md][related-4]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: mcp_server/managers/project_manager.py
[related-3]: mcp_server/core/phase_detection.py
[related-4]: docs/development/issue290/research-issue231-state-snapshot.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Agent | Initial scaffolded draft |
| 1.1 | 2026-04-26 | Agent | Revalidated issue #139 against current code and marked the original missing-field bug statement as substantially stale |
