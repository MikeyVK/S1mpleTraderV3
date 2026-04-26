<!-- c:\temp\st3\docs\development\issue290\research-issue230-implementation-cycle-resume.md -->
<!-- template=research version=8b7bb3ab created=2026-04-26T13:03Z updated=2026-04-26 -->
# Research — Issue #230 Implementation Cycle Resume

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-04-26

---

## Purpose

Revalidate and translate issue #230 into the current implementation-phase/cycle terminology, and confirm whether the underlying bug still exists.

## Scope

**In Scope:**
PhaseStateEngine implementation-phase hooks, current_cycle/last_cycle semantics, and planning-deliverable cycle metadata.

**Out of Scope:**
Workflow phase detection, branch creation, and submit_pr semantics.

## Prerequisites

Read these first:
1. Issue #230 description
2. mcp_server/managers/phase_state_engine.py
3. mcp_server/managers/project_manager.py
4. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Problem Statement

Issue #230 reported that the cycle counter resets to 1 when the workflow re-enters the implementation phase after a detour, instead of resuming from the next cycle.

## Research Goals

- Check the current implementation-phase entry and exit hooks against the original issue statement.
- Determine whether the underlying bug still exists under the renamed implementation/cycle model.
- Capture the current root cause precisely.
- Define expected results for a future fix.

---

## Background

Issue #230 was filed using older `tdd`-phase terminology, but the behavioral claim maps directly onto the current `implementation` phase with numbered cycles.

The relevant current hooks are:

- `on_exit_implementation_phase()` preserving `last_cycle` and clearing `current_cycle`
- `on_enter_implementation_phase()` reinitializing cycle state on re-entry

---

## Findings

### Finding 1 — The underlying bug still exists

The terminology in the issue is stale, but the behavioral defect remains current.

On exit, the engine preserves the current cycle by writing:

- `last_cycle = current_cycle`
- `current_cycle = None`

On re-entry, the engine currently checks only whether `current_cycle is None`. If so, it resets:

- `current_cycle = 1`
- `last_cycle = 0`

That means prior progress is discarded on re-entry instead of being resumed.

### Finding 2 — The root cause is incomplete re-entry semantics

The bug is not just an off-by-one mistake. The deeper problem is that implementation-phase re-entry is modeled as fresh initialization rather than resumption.

The entry hook does not consult:

- `last_cycle`
- `cycle_history`
- planned cycle definitions in planning deliverables

So the engine has no way to distinguish first entry from re-entry after a detour.

### Finding 3 — Current state fields already contain enough information to do better

The current state model already persists both `current_cycle` and `last_cycle`, and planning deliverables expose cycle definitions. That means the defect is not missing storage. It is missing re-entry policy.

### Finding 4 — A robust fix should derive the next active cycle from completed history, not just increment blindly

`last_cycle + 1` is a better default than resetting to 1, but the more defensible rule is to derive the next unstarted cycle from:

- planning deliverables
- current `cycle_history`
- persisted `last_cycle`

That avoids hard-coding assumptions about how many cycles exist or whether history and planning data diverge.

---

## Architecture Check

### Alignment with Explicit over Implicit

The current entry hook hides a destructive reset behind a generic "enter implementation" action. Re-entry semantics should be explicit and derived from persisted cycle state.

### Alignment with SSOT

The engine already has persisted cycle state and planned cycle definitions. Ignoring them on re-entry weakens the SSOT model.

### Alignment with SRP

The correct fix belongs in implementation-phase entry semantics. It should not be pushed onto users via force-cycle-transition workarounds.

---

## Solution Directions

### Direction A — Differentiate first entry from re-entry

The implementation entry hook should not treat every `current_cycle is None` case as a fresh start. It should explicitly distinguish first-time initialization from re-entry after prior completed cycles.

### Direction B — Resume from the next unstarted cycle

A minimum fix is:

- if `last_cycle` exists and `current_cycle is None`, resume at `last_cycle + 1`

A more robust fix is:

- inspect planned cycles and cycle history
- choose the lowest cycle number not yet completed or active

### Direction C — Add regression tests for detour re-entry

Tests should cover at least:

- first entry into implementation starts at cycle 1
- exit and re-entry after a detour resumes at the correct next cycle
- forced cycle transitions still remain exceptional, not the normal recovery path

---

## Expected Results

This research supports the following expected outcomes for issue #230:

- The issue remains active in substance, but should be translated to current implementation/cycle terminology.
- Re-entering the implementation phase after a detour no longer resets progress to cycle 1 by default.
- The next active cycle is derived from persisted cycle state and, ideally, planning deliverables.
- force_cycle_transition is no longer required for normal mid-stream detour recovery.

## Open Questions

- Is `last_cycle + 1` sufficient for current workflows, or do we want the more robust "lowest unstarted cycle" rule immediately?
- Should re-entry fail fast when planning deliverables are missing, or fall back to `last_cycle + 1`?

## Related Documentation

- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[mcp_server/managers/phase_state_engine.py][related-2]**
- **[mcp_server/managers/project_manager.py][related-3]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: mcp_server/managers/phase_state_engine.py
[related-3]: mcp_server/managers/project_manager.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Agent | Initial scaffolded draft |
| 1.1 | 2026-04-26 | Agent | Revalidated issue #230 against the current implementation-phase hooks and confirmed the underlying resume bug still exists |
