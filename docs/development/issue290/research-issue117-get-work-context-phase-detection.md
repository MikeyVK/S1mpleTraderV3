<!-- c:\temp\st3\docs\development\issue290\research-issue117-get-work-context-phase-detection.md -->
<!-- template=research version=8b7bb3ab created=2026-04-26T13:03Z updated=2026-04-26 -->
# Research — Issue #117 GetWorkContext Phase Detection

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-04-26

---

## Purpose

Revalidate whether issue #117 still reflects the current implementation or has been superseded by later workflow-phase detection work.

## Scope

**In Scope:**
GetWorkContextTool, ScopeDecoder integration, displayed workflow phase data, and relationship to state.json.

**Out of Scope:**
Project plan output, branch creation behavior, and submit_pr atomicity.

## Prerequisites

Read these first:
1. Issue #117 description
2. mcp_server/tools/discovery_tools.py
3. mcp_server/core/phase_detection.py
4. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Problem Statement

Issue #117 reported that get_work_context only exposed narrow TDD commit phases and ignored authoritative workflow state from state.json.

## Research Goals

- Check the current GetWorkContextTool implementation against the original issue statement.
- Determine whether the issue is still active, partially resolved, or superseded.
- Capture the current root problem if the original statement is stale.
- Define expected results for either closure or reframing.

---

## Background

Issue #117 originated when get_work_context reportedly inferred only TDD-style phases from commit prefixes and ignored broader workflow state.

The current implementation surface is materially different: GetWorkContextTool now delegates phase detection to ScopeDecoder and returns structured fields for workflow phase, sub-phase, source, confidence, and optional implementation-cycle details.

---

## Findings

### Finding 1 — The original issue statement is substantially stale

The current GetWorkContextTool no longer uses a narrow `_detect_tdd_phase()` style heuristic. It calls deterministic workflow phase detection and exposes:

- `workflow_phase`
- `sub_phase`
- `phase_source`
- `phase_confidence`
- `phase_error_message`

That means the core complaint in issue #117, "only detects TDD phase, not full workflow phases," no longer matches the current code.

### Finding 2 — state-aware workflow detection is already integrated

GetWorkContextTool calls ScopeDecoder-based detection with fallback to state.json semantics. It also conditionally adds cycle metadata when the detected workflow phase is `implementation`.

So the current tool is already aligned with the broader workflow model rather than a commit-prefix-only TDD model.

### Finding 3 — The remaining problem is read-model quality, not missing phase exposure

Although the original bug is largely gone, a different class of problem remains in this area: read-side workflow information is still assembled from multiple partial sources and precedence rules.

That is closer to issue #231 than to the original wording of #117. The current weakness is not that workflow phase is absent. The weakness is that phase, source, confidence, and cycle context are not yet surfaced through one dedicated typed snapshot model.

### Finding 4 — There may still be edge cases around precedence, but that is not the original bug

If there is a remaining defect here, it is likely about reconciliation between commit-scope and state.json immediately after transitions or forced transitions.

That is a precedence/consistency problem, not a "get_work_context only shows TDD phase" problem.

---

## Architecture Check

### Alignment with Explicit over Implicit

The current implementation is materially better than the one described in the issue because it exposes source and confidence explicitly instead of silently guessing from commit prefixes.

### Alignment with SSOT

The tool is no longer bypassing workflow state entirely. It participates in a deterministic state-aware phase-detection path.

### Alignment with SRP

The remaining opportunity is not to add more ad hoc output fields to GetWorkContextTool, but to depend on a single typed read model for workflow snapshot data.

---

## Solution Directions

### Direction A — Close or rewrite issue #117 as stale

The current issue text should not remain open unchanged because it no longer describes the current implementation accurately.

### Direction B — If follow-up work is desired, reframe it around unified read models

Any new work should focus on the remaining read-side fragmentation and precedence semantics, not on restoring basic workflow-phase visibility that already exists.

### Direction C — Keep regression tests focused on source-aware phase reporting

Tests in this area should verify that get_work_context continues to expose workflow phase, sub-phase, source, and cycle information together.

---

## Expected Results

This research supports the following expected outcomes for issue #117:

- The issue should be treated as largely resolved or stale in its current wording.
- Any replacement issue should target unified workflow snapshot/read-model semantics instead of basic phase visibility.
- get_work_context should continue exposing workflow phase, sub-phase, phase source, confidence, and implementation-cycle context.

## Open Questions

- Should issue #117 be closed outright, or rewritten to point at the remaining read-model and precedence gaps?
- Do we want one shared workflow snapshot DTO for both get_work_context and get_project_plan style read surfaces?

## Related Documentation

- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[mcp_server/tools/discovery_tools.py][related-2]**
- **[mcp_server/core/phase_detection.py][related-3]**
- **[docs/development/issue290/research-issue231-state-snapshot.md][related-4]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: mcp_server/tools/discovery_tools.py
[related-3]: mcp_server/core/phase_detection.py
[related-4]: docs/development/issue290/research-issue231-state-snapshot.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Agent | Initial scaffolded draft |
| 1.1 | 2026-04-26 | Agent | Revalidated issue #117 against current code and marked original bug statement as substantially stale |
