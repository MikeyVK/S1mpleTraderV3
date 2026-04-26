<!-- c:\temp\st3\docs\development\issue290\research-issue231-state-snapshot.md -->
<!-- template=research version=8b7bb3ab created=2026-04-26T12:47Z updated=2026-04-26 -->
# Research — Issue #231 State Snapshot And Reconciliation

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-04-26

---

## Purpose

Document the root cause, viable solution directions, architectural fit, findings, and expected results for issue #231 within epic #290.

## Scope

**In Scope:**
Read-side state semantics for workflow tools, including persisted BranchState, reconstruction behavior, phase detection metadata, and high-impact consumers such as get_work_context and get_project_plan.

**Out of Scope:**
Implementation design details for write-path concurrency fixes, branch submission atomicity, and unrelated agent orchestration features.

## Prerequisites

Read these first:
1. Issue #290 epic context
2. Issue #231 description
3. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
4. Current implementations of PhaseStateEngine, ProjectManager, ScopeDecoder, StateReconstructor, and GetWorkContextTool

---

## Problem Statement

State reads across the workflow stack are fragmented. Callers can read persisted BranchState, detect phase via commit scopes, or reconstruct missing state, but there is no single typed query model that returns a coherent snapshot of phase, subphase, cycle data, source metadata, and reconstruction/drift status.

## Research Goals

- Identify the absolute core problem behind issue #231 instead of treating it as a generic state bug.
- Map the current read-side code paths for persisted state, reconstruction, and phase detection.
- Evaluate solution directions against docs/coding_standards/ARCHITECTURE_PRINCIPLES.md.
- Define expected results that design and planning can implement without reopening research.

---

## Background

The current codebase already contains several partial building blocks:

- BranchState is a frozen validated value object used as persisted branch state.
- FileStateRepository and InMemoryStateRepository satisfy the same repository contract.
- PhaseStateEngine keeps `get_state()` as a pure read and isolates reconstruction in `_load_state_or_reconstruct()` for transition flows.
- ScopeDecoder already returns `workflow_phase`, `sub_phase`, `source`, `confidence`, and `error_message`.
- StateReconstructor can rebuild missing state from branch metadata and commit history.

The problem is therefore not that the platform has no state model. The problem is that the platform has several partial read models and asks consumers to compose them ad hoc.

---

## Findings

### Finding 1 — The core problem is read-model fragmentation, not missing state persistence

The current platform already persists the branch workflow state in BranchState and already has a separate reconstruction path. The unresolved problem is that different consumers read different subsets of workflow truth:

- `PhaseStateEngine.get_state()` returns persisted BranchState only.
- `StateReconstructor.reconstruct()` can infer state when persistence is missing or invalid.
- `ScopeDecoder.detect_phase()` returns phase/subphase plus source/confidence metadata.
- `GetWorkContextTool` combines commit-scope detection with a separate state read for cycle details.
- `ProjectManager.get_project_plan()` mutates a project-plan response with phase detection output.

Each part is reasonable in isolation. The system-level defect is that there is no dedicated typed snapshot contract that composes these pieces for read-side consumers.

### Finding 2 — The missing contract is a coherent query result, not another persistence schema

Issue #231 should not start by redefining `.st3/state.json` or by replacing BranchState. BranchState is the persisted storage model and already fits CQS well: queries return frozen data, commands persist separately.

What is missing is a higher-level query result that answers the question a consumer actually has:

- What phase is the branch effectively in?
- What subphase or cycle context is known?
- Did this answer come from persisted state, commit-scope evidence, reconstruction, or fallback?
- Is the state exact, reconstructed, or potentially drifted?

That is a different responsibility from persistence. Overloading BranchState with detection metadata would blur storage concerns and query concerns.

### Finding 3 — High-impact consumers already show the fragmentation clearly

Two read-side consumers demonstrate the mismatch:

- `get_work_context` reports workflow phase through ScopeDecoder, but reaches into BranchState separately for cycle information.
- `get_project_plan` returns project-plan data and then injects `current_phase` through phase detection, effectively mixing workflow-definition data with dynamic branch-state read semantics.

This means the platform currently has no single place where "effective workflow state for this branch" is defined. The behavior exists as duplicated assembly logic in consumers.

### Finding 4 — Issue #231 is the correct place to unify stale symptom issues without re-solving them independently

Code inspection indicates that some older linked issues are now at least partially overtaken:

- `get_project_plan` already adds `current_phase`, `phase_source`, and `phase_detection_error`.
- `get_work_context` already reports full workflow phases, subphase details, and detection source/confidence.

That does not invalidate #231. It sharpens it. The remaining problem is no longer "tool X knows too little". The remaining problem is "tools compute overlapping workflow-state answers through separate local assembly logic".

This makes #231 the right consolidation issue for read-side workflow intelligence.

### Finding 5 — Reconstruction and detection metadata exist, but they are not first-class read semantics

The current platform already has useful trust signals:

- `BranchState.reconstructed`
- ScopeDecoder `source`
- ScopeDecoder `confidence`
- fallback and recovery error messaging

However, these signals are scattered and consumer-specific. There is no single typed object that guarantees they are exposed together and interpreted consistently. As a result, one consumer may present a reconstructed phase as authoritative while another consumer may silently fall back to different evidence.

---

## Architecture Check

### Alignment with SRP

A dedicated snapshot model aligns with SRP if responsibilities stay split:

- BranchState remains persisted branch state.
- StateRepository remains persistence.
- StateReconstructor remains reconstruction.
- ScopeDecoder remains phase detection.
- A new query-oriented snapshot layer composes these outputs for readers.

Merging all of this into PhaseStateEngine persistence code or stuffing extra runtime-only fields into BranchState would weaken SRP.

### Alignment with CQS

The architecture contract is explicit: `get_state()` must remain a pure query and must not save. The current split between `get_state()` and `_load_state_or_reconstruct()` is correct.

Therefore the compliant direction is:

- keep persisted-state reads pure
- add a separate query path for "effective snapshot"
- do not make ordinary reads mutate state just to reconcile them

If exact reconciliation needs persistence, that should be an explicit command path, not a hidden side effect of a read API.

### Alignment with ISP and DIP

Read-only consumers should not depend on write-capable interfaces. A snapshot API should therefore be injectable as a read-focused contract or built from read-focused collaborators. Consumers like `get_work_context` should not need to know how repository load, reconstruction, and commit-scope detection are sequenced internally.

### Alignment with Explicit over Implicit

The snapshot result must expose source and trust metadata directly. Silent precedence rules are not sufficient. If the platform chooses persisted state, reconstructed state, or commit-scope evidence, the caller should receive that choice as data, not infer it from behavior.

### Alignment with YAGNI

The smallest compliant improvement is not a general workflow-intelligence framework. The smallest compliant improvement is one typed read model plus one query API for the high-impact consumers already suffering from duplicated assembly logic.

---

## Solution Directions

### Direction A — Introduce a dedicated StateSnapshot query model

Create a typed read model that represents effective branch workflow state for consumers. Candidate fields:

- branch
- workflow_name
- current_phase
- sub_phase
- current_cycle
- last_cycle
- reconstructed
- source
- confidence
- drift_flags or warnings
- issue_number / parent_branch if needed for consumers

This direction fits the architectural principles best because it keeps persistence, reconstruction, and detection separate while giving consumers one read contract.

### Direction B — Add `get_state_snapshot(branch)` as a query API without changing `get_state()`

Add a new explicit query entry point rather than altering existing `get_state()` behavior. This preserves CQS and avoids breaking consumers that rely on persisted-state-only semantics.

### Direction C — Migrate high-impact consumers onto the snapshot incrementally

The migration order should be driven by duplication and user-facing confusion:

1. `get_work_context`
2. `get_project_plan`
3. branch-switch / transition-adjacent read paths that display phase or cycle context

This avoids a risky flag day and keeps the first implementation slice testable.

### Direction D — Do not solve write-path concurrency under #231

Issue #292 is the correct write-path companion. #231 should define coherent read semantics and trust metadata. It should not absorb locking, transactionality, or conflict resolution for writers.

---

## Expected Results

This research supports the following expected outcomes for issue #231:

- A dedicated typed snapshot model exists for effective branch workflow state.
- The snapshot exposes phase, subphase, cycle context, reconstruction status, and source/confidence metadata in one query result.
- `get_state()` remains a pure persisted-state query with no hidden save/reconstruct side effects.
- `get_work_context` stops assembling workflow truth from separate ad hoc reads and instead consumes the shared snapshot contract.
- `get_project_plan` stops embedding its own local phase-assembly logic and instead reads the shared snapshot contract for dynamic branch-state fields.
- The platform can distinguish between persisted truth, reconstructed truth, and inferred truth without silent ambiguity.
- Tests cover persisted-state reads, reconstructed-state reads, source/confidence reporting, and consumer migration behavior.

## Open Questions

- Should drift be represented as structured flags, warnings, or both?
- Which fields are mandatory for every snapshot versus optional for implementation-phase branches only?
- Should the snapshot API live on PhaseStateEngine, or should a separate query-oriented service own it to keep the engine narrower?

## Related Documentation

- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[docs/development/issue288/backlog-inventory.md][related-2]**
- **[mcp_server/managers/phase_state_engine.py][related-3]**
- **[mcp_server/managers/state_reconstructor.py][related-4]**
- **[mcp_server/managers/project_manager.py][related-5]**
- **[mcp_server/tools/discovery_tools.py][related-6]**
- **[mcp_server/core/phase_detection.py][related-7]**
- **[mcp_server/managers/state_repository.py][related-8]**
- **[mcp_server/core/interfaces/__init__.py][related-9]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: docs/development/issue288/backlog-inventory.md
[related-3]: mcp_server/managers/phase_state_engine.py
[related-4]: mcp_server/managers/state_reconstructor.py
[related-5]: mcp_server/managers/project_manager.py
[related-6]: mcp_server/tools/discovery_tools.py
[related-7]: mcp_server/core/phase_detection.py
[related-8]: mcp_server/managers/state_repository.py
[related-9]: mcp_server/core/interfaces/__init__.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Agent | Initial scaffolded draft |
| 1.1 | 2026-04-26 | Agent | Added root-cause analysis, solution directions, architecture check, and expected results for issue #231 |
