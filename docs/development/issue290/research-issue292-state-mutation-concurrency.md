<!-- c:\temp\st3\docs\development\issue290\research-issue292-state-mutation-concurrency.md -->
<!-- template=research version=8b7bb3ab created=2026-04-26T12:49Z updated=2026-04-26 -->
# Research — Issue #292 Workflow State Mutation Concurrency

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-04-26

---

## Purpose

Document the root cause, viable solution directions, architectural fit, findings, and expected results for issue #292 within epic #290.

## Scope

**In Scope:**
Write-side workflow state mutations, full-document replacement semantics, shared ownership of .st3/state.json, and operator-facing failure modes for transition and quality-gate flows.

**Out of Scope:**
Read-side snapshot unification from issue #231, branch submission atomicity, and unrelated documentation cleanup.

## Prerequisites

Read these first:
1. Issue #290 epic context
2. Issue #292 description
3. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
4. Current implementations of PhaseStateEngine, FileStateRepository, AtomicJsonWriter, and QAManager

---

## Problem Statement

Workflow state persistence is not protected by a single ownership and merge contract. Multiple mutation paths load and rewrite the full .st3/state.json payload, and at least one non-workflow writer stores incompatible top-level data in the same file. This allows lost updates, schema conflicts, and silent state replacement despite atomic file replacement.

## Research Goals

- Identify the absolute core problem behind issue #292 instead of reducing it to a generic locking bug.
- Map all relevant state.json writers and determine whether they share one persistence contract.
- Evaluate solution directions against docs/coding_standards/ARCHITECTURE_PRINCIPLES.md.
- Define expected results that planning and design can implement without conflating read-side and write-side fixes.

---

## Background

The codebase already centralizes normal workflow-state persistence through FileStateRepository and AtomicJsonWriter. However, transition methods in PhaseStateEngine still perform load-modify-save full-document writes, and QAManager directly reads and writes .st3/state.json for quality baseline tracking using a separate schema and write path.

Atomic replacement protects the file from partial writes or torn writes. It does not protect the logical contents from stale-read overwrite. If two callers each load a previous version of the file and then each replace the whole document, the last writer still wins.

---

## Findings

### Finding 1 — The root problem is shared document ownership, not just missing locking

Issue #292 should not be framed only as "two transitions can race". The deeper defect is that `.st3/state.json` lacks a single typed ownership contract.

Today at least two domains treat the same file as theirs:

- workflow state transitions via PhaseStateEngine and FileStateRepository
- quality baseline persistence via QAManager

That means the problem space is larger than transition concurrency. The platform currently has multiple writers with different schema assumptions and different write strategies against the same file.

### Finding 2 — PhaseStateEngine performs full-document replacement, so concurrent writers can lose valid updates

PhaseStateEngine transition paths follow the classic lost-update pattern:

1. load current BranchState
2. mutate a subset of fields
3. save the full serialized document

This happens in normal phase transitions, forced transitions, strict cycle transitions, forced cycle transitions, and recovery saves. Because the save replaces the whole file, two valid mutations can both report success while the later full-document write silently removes fields changed by the earlier writer.

AtomicJsonWriter makes the replace operation atomic at the filesystem level, but it does not merge logical updates.

### Finding 3 — QAManager currently bypasses the workflow-state persistence contract entirely

QAManager reads and writes `.st3/state.json` directly through `_load_state_json()` and `_save_state_json()`. It does not use FileStateRepository and it does not persist BranchState.

This is a direct architectural contract violation relative to the documented state subsystem, which says StateRepository should encapsulate state I/O and that tools/managers must not bypass it.

The bypass matters for more than style:

- it creates an unsynchronized second writer
- it avoids the BranchState validation boundary
- it normalizes a second schema contract for the same file

### Finding 4 — QAManager writes a schema that BranchState explicitly rejects

BranchState uses `extra="forbid"`. QAManager writes top-level `quality_gates` data into `.st3/state.json`. Those two choices are incompatible.

As a result, a quality-gates lifecycle run can create a state.json payload that the workflow state reader cannot validate as BranchState. The next workflow read may then treat the file as invalid or missing and reconstruct it, which can silently discard the quality baseline data again.

This means the current conflict is not only concurrent lost updates. It is also schema-level disagreement about what `state.json` is allowed to contain.

### Finding 5 — The current test suite codifies the conflicting contract

This is not an accidental leftover in one code path. The QA baseline tests explicitly write and assert a `quality_gates` top-level section inside `.st3/state.json`.

That confirms the platform currently institutionalizes two incompatible meanings for the same file:

- workflow branch state as a validated BranchState document
- quality baseline state as an ad hoc top-level extension document

Any fix for #292 must therefore address both runtime code and the tests that currently bless the mixed contract.

### Finding 6 — Operator-facing behavior is currently unsafe because success does not imply state integrity

The issue description is correct on the key user-facing risk: callers can receive successful tool results even when the final persisted state no longer reflects all successful operations.

The current platform has no conflict detection and no explicit operator-facing signal for stale-write overwrite. In practice that means the branch appears to transition cleanly until a later tool reads state and discovers drift, invalid structure, or missing fields.

---

## Architecture Check

### Alignment with SRP

A quality baseline store and a workflow branch-state store are separate responsibilities. Having both domains write top-level data into the same state file weakens SRP at the persistence boundary, even if the managers themselves look narrowly scoped.

### Alignment with DRY and SSOT

The documented subsystem says StateRepository owns state I/O. QAManager bypassing that contract creates a second effective source of truth for how `.st3/state.json` is shaped and written. That is a direct SSOT violation.

### Alignment with CQS

The platform needs explicit command semantics for mutation. Hidden whole-document rewrites that overwrite neighboring fields are not an acceptable command contract. A command should either preserve unrelated state deterministically or fail explicitly.

### Alignment with Explicit over Implicit

Conflict detection cannot stay implicit. If a write loses a concurrent change, encounters a stale base, or refuses to merge incompatible domains, the caller must get an explicit explanation and recovery path.

### Alignment with YAGNI

The smallest compliant fix is not distributed locking across every possible environment. The smallest compliant fix is:

- one ownership contract for workflow state
- one explicit place for quality baseline metadata
- one deterministic mutation strategy for concurrent updates on the same document

---

## Solution Directions

### Direction A — Restore single ownership for workflow state

Workflow branch state should have one persistence owner. Two viable ways to achieve that are:

- move quality baseline data out of `.st3/state.json` into its own file
- or introduce a typed envelope/repository that formally owns both workflow state and quality baseline state

The first direction is simpler and aligns better with SRP. The second direction is only justified if shared storage is truly required.

### Direction B — Replace blind full-document writes with a deterministic mutation contract

Whole-document replacement based on stale reads is the immediate lost-update mechanism. Viable fixes include:

- serialized update access around the state file
- compare-and-swap/versioned writes with retry or rejection
- a repository-level patch/merge operation that updates only owned fields

The important requirement is not the exact primitive. The important requirement is that success must mean unrelated valid updates were not silently lost.

### Direction C — Make conflict handling operator-visible

When the system detects stale state, merge conflict, lock contention, or incompatible schema, the tool call should not report silent success. The result should include an explicit explanation and a recovery hint/note.

### Direction D — Keep #292 scoped to write integrity

Issue #231 should continue to own read-side snapshot semantics. #292 should own write integrity, shared-document ownership, and conflict signaling.

---

## Expected Results

This research supports the following expected outcomes for issue #292:

- `.st3/state.json` has a single explicit ownership contract.
- Workflow-state writes no longer compete with an ad hoc direct writer using a different schema.
- A successful transition or quality-state mutation cannot silently discard unrelated valid state changes.
- Conflict or stale-write conditions surface explicit operator-facing feedback instead of silent last-writer-wins behavior.
- Tests cover both concurrent workflow mutations and the separation or formalization of quality baseline persistence.
- The architecture documentation and tests reflect the same state ownership contract as the production code.

## Open Questions

- Should quality baseline metadata move to a dedicated file, or is there a strong reason to keep it co-located with workflow state?
- If co-location is retained, what typed envelope should replace raw BranchState-at-root semantics?
- Is an in-process mutex sufficient for current usage, or do we need repository-level optimistic concurrency checks as well?

## Related Documentation

- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[docs/mcp_server/architectural_diagrams/02_workflow_state_subsystem.md][related-2]**
- **[docs/mcp_server/architectural_diagrams/04_enforcement_layer.md][related-3]**
- **[mcp_server/managers/phase_state_engine.py][related-4]**
- **[mcp_server/managers/qa_manager.py][related-5]**
- **[mcp_server/managers/state_repository.py][related-6]**
- **[mcp_server/utils/atomic_json_writer.py][related-7]**
- **[tests/mcp_server/unit/managers/test_baseline_advance.py][related-8]**
- **[tests/mcp_server/managers/test_phase_state_engine_async.py][related-9]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: docs/mcp_server/architectural_diagrams/02_workflow_state_subsystem.md
[related-3]: docs/mcp_server/architectural_diagrams/04_enforcement_layer.md
[related-4]: mcp_server/managers/phase_state_engine.py
[related-5]: mcp_server/managers/qa_manager.py
[related-6]: mcp_server/managers/state_repository.py
[related-7]: mcp_server/utils/atomic_json_writer.py
[related-8]: tests/mcp_server/unit/managers/test_baseline_advance.py
[related-9]: tests/mcp_server/managers/test_phase_state_engine_async.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Agent | Initial scaffolded draft |
| 1.1 | 2026-04-26 | Agent | Added root-cause analysis, architecture check, solution directions, and expected results for issue #292 |
