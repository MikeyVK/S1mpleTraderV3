<!-- c:\temp\st3\docs\development\issue290\research-issue45-state-json-structure-revalidation.md -->
<!-- template=research version=8b7bb3ab created=2026-04-26T13:03Z updated=2026-04-26 -->
# Research — Issue #45 State JSON Structure Revalidation

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-04-26

---

## Purpose

Revalidate whether issue #45 still matches the current state persistence architecture or has become stale after the state repository redesign.

## Scope

**In Scope:**
PhaseStateEngine persistence path, FileStateRepository, BranchState schema, and current state.json ownership contract.

**Out of Scope:**
Quality baseline coexistence, workflow phase detection precedence, and branch creation behavior.

## Prerequisites

Read these first:
1. Issue #45 description
2. mcp_server/managers/phase_state_engine.py
3. mcp_server/managers/state_repository.py
4. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Problem Statement

Issue #45 reported a mismatch between documented multi-branch state.json structure and the PhaseStateEngine implementation.

## Research Goals

- Check the current state persistence model against the original issue statement.
- Determine whether the issue is still active, partially resolved, or superseded.
- Capture the current root problem if the original statement is stale.
- Define expected results for either closure or reframing.

---

## Background

Issue #45 came from an earlier design period when docs and code allegedly disagreed about whether state.json stored a versioned branch map or a flat structure.

The current persistence design is materially different from that historical picture. PhaseStateEngine now delegates persistence to FileStateRepository, and FileStateRepository reads and writes a validated single `BranchState` document.

---

## Findings

### Finding 1 — The original issue statement is substantially stale

The current implementation no longer matches the architectural shape described in issue #45.

Today:

- PhaseStateEngine does not manually iterate a multi-branch JSON map
- FileStateRepository loads one document into `BranchState`
- the persisted payload is a single validated branch-state object with fields like `branch`, `workflow_name`, `current_phase`, `current_cycle`, and `transitions`

That means the original flat-vs-nested multi-branch structure dispute is no longer the active design problem.

### Finding 2 — The current state contract is single-document, strongly typed, and explicit

The important current invariant is not whether branch names live under a `branches` map. The important invariant is that `.st3/state.json` must validate cleanly as one `BranchState` payload.

This is a stronger and clearer contract than the one described in the old issue.

### Finding 3 — The modern risk surface has moved from shape mismatch to shared ownership and schema collision

The current state-related problems in this codebase are not well described by issue #45. The more relevant active problems are:

- multiple writers mutating the same shared document
- schema drift between subsystems that treat `.st3/state.json` as their own extension surface

That is much closer to issue #292 than to the historical flat-vs-nested structure complaint.

### Finding 4 — Versioning may still be a valid future concern, but not under the original issue framing

The old issue also mentioned schema versioning and migration. That can still be a legitimate future design concern.

However, it should be raised as a forward-looking schema-evolution question, not as an implementation/docs mismatch based on the old multi-branch data model.

---

## Architecture Check

### Alignment with Explicit over Implicit

The current BranchState-based repository model is explicit and typed. That is better than relying on undocumented loose JSON shapes.

### Alignment with SRP and DIP

PhaseStateEngine now depends on a state repository abstraction rather than hand-parsing the file directly. That is a cleaner architectural boundary than the one assumed in the issue.

### Alignment with SSOT

The remaining state risks are about shared ownership of the document, not ambiguity over the top-level container shape.

---

## Solution Directions

### Direction A — Close or rewrite issue #45 as stale

The issue should not remain open in its current wording because it describes a persistence architecture that no longer exists.

### Direction B — If follow-up work is needed, reframe it around current schema governance

A replacement issue could focus on one of these modern concerns:

- schema versioning for BranchState evolution
- coexistence rules for other subsystems writing adjacent state
- stronger protection against incompatible writes to `.st3/state.json`

### Direction C — Point active state-risk work toward issue #292-style ownership problems

If the goal is to reduce current risk, the highest-value work is not container-shape migration. It is shared-document ownership, mutation safety, and schema compatibility.

---

## Expected Results

This research supports the following expected outcomes for issue #45:

- The original issue should be treated as stale because the underlying persistence architecture has changed substantially.
- Any replacement issue should describe current BranchState/schema-governance concerns rather than historical flat-vs-nested map differences.
- Active state-work prioritization should favor shared-ownership/schema-collision problems over obsolete container-shape mismatches.

## Open Questions

- Do we want an explicit schema-version field for future BranchState migrations, even though it is not the main current problem?
- Should state-related follow-up issues be consolidated under one schema-governance/ownership umbrella?

## Related Documentation

- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[mcp_server/managers/phase_state_engine.py][related-2]**
- **[mcp_server/managers/state_repository.py][related-3]**
- **[docs/development/issue290/research-issue292-state-mutation-concurrency.md][related-4]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: mcp_server/managers/phase_state_engine.py
[related-3]: mcp_server/managers/state_repository.py
[related-4]: docs/development/issue290/research-issue292-state-mutation-concurrency.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Agent | Initial scaffolded draft |
| 1.1 | 2026-04-26 | Agent | Revalidated issue #45 against the current BranchState repository architecture and marked the historical shape-mismatch framing as stale |
