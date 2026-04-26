<!-- docs\development\issue231\planning.md -->
<!-- template=planning version=130ac5ea created=2026-04-26T20:46Z updated=2026-04-26 -->
# Issue 231 / Issue 292 v2.4 — Implementation Planning

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-26  
**Research reference:** [research.md](research.md) v2.1  
**Design reference:** [design.md](design.md) v2.4

---

## Purpose

Human-readable planning audit trace and executable deliverables manifest for the v2.4 design hardening slice.

**Dual purpose:**
This document is both the implementation guide for the upcoming cycles and the canonical source for the `save_planning_deliverables` payload stored in `.st3/deliverables.json`. Deliverable ids below are mirrored one-to-one in the persisted JSON. Symbolic cycle labels are mirrored as `cycle_id`, while persistence order is enforced by sequential `cycle_number` values.

---

## Summary

This plan implements the approved v2.4 design without widening scope. The expected end state is:
- branch-safe reads use one explicit mismatch contract (`StateBranchMismatchError`)
- `PhaseStateEngine.get_state()` and `get_current_phase()` no longer translate mismatch to `FileNotFoundError`
- `git_tools.py` and `git_pull_tool.py` stay on engine queries, not the resolver, but handle the new exception directly
- `WorkflowStatusResolver` becomes the only shared user-facing workflow-status assembler for `ProjectManager` and `GetWorkContextTool`
- QA baseline state leaves `.st3/state.json` and moves to `.st3/quality_state.json`
- workflow writes move behind one coordinated mutator boundary
- phase/cycle/quality tools surface explicit conflict feedback through `ToolResult.error(...)` plus `RecoveryNote`
- the final cleanup cycle leaves no legacy translation shim, raw QA state write path, or stale test assumptions behind

---

## Prerequisites

- [x] [design.md](design.md) v2.4 committed on the active branch
- [x] Branch `feature/231-state-snapshot-cqrs` active in `planning` phase
- [x] Clean-break decision accepted: no `FileNotFoundError` translation shim, no constructor fallback compatibility layer
- [x] Resolver adoption boundary accepted: only `ProjectManager` and `GetWorkContextTool` move to `WorkflowStatusResolver`
- [x] Planning deliverables entry for issue `231` not yet written to `.st3/deliverables.json`

---

## Global Planning Rules

### Rule P-1: Clean Break Means Actual Break
No cycle may reintroduce a translation shim, deprecated constructor shape, optional backward-compatible dependency, or fallback path that contradicts v2.4.

### Rule P-2: No Resolver Creep
`git_tools.py`, `git_pull_tool.py`, and the `GitCommitTool` auto-detect path remain on engine queries. Their exception handling changes; their query source does not.

### Rule P-3: Foundation Before Adoption
No resolver adoption work may start before the branch-safe read contract exists and the engine clean-break semantics are already enforced.

### Rule P-4: Write Ownership Must Stay Explicit
`QAManager` ownership split and workflow mutator work are separate cycles. No mixed read/write migration is allowed inside one oversized cycle.

### Rule P-5: Cleanup Is Mandatory
The final cycle is not optional polish. It is the flag-day closure for legacy code paths, stale tests, and grep-visible remnants.

---

## Dependency Order

```text
C_READ_GUARD
  -> C_ENGINE_BREAK
  -> C_RESOLVER_CORE
  -> C_RESOLVER_ADOPTION
  -> C_QA_STATE_SPLIT
  -> C_MUTATOR_CORE
  -> C_TOOL_CONFLICTS
  -> C_CLEANUP
```

| Cycle | Priority | Size | Depends On | Why It Must Be Here |
|---|---|---|---|---|
| C_READ_GUARD | P0 | S | — | Establishes the one branch-safe read contract all later slices depend on |
| C_ENGINE_BREAK | P0 | S | C_READ_GUARD | Makes the clean break real before any new read-side adoption |
| C_RESOLVER_CORE | P0 | S | C_READ_GUARD | Introduces the new read-side building blocks without consumer churn |
| C_RESOLVER_ADOPTION | P0 | S | C_RESOLVER_CORE, C_ENGINE_BREAK | Moves only the researched user-facing consumers to the resolver |
| C_QA_STATE_SPLIT | P0 | M | C_READ_GUARD | Splits QA ownership out of workflow state before write coordination work |
| C_MUTATOR_CORE | P0 | M | C_QA_STATE_SPLIT | Moves workflow writes and hook writes behind one coordination seam |
| C_TOOL_CONFLICTS | P1 | S | C_MUTATOR_CORE | Exposes mutation failures to operators through existing tool UX contracts |
| C_CLEANUP | P0 | S | C_ENGINE_BREAK, C_RESOLVER_ADOPTION, C_QA_STATE_SPLIT, C_MUTATOR_CORE, C_TOOL_CONFLICTS | Removes every remaining legacy code/test remnant and verifies grep closure |

---

## JSON Registration Note

The actual tool input envelope for the first save must look like this:

```json
{
  "issue_number": 231,
  "planning_deliverables": {
    "tdd_cycles": {
      "total": 8,
      "cycles": [
        {
          "cycle_number": 1,
          "cycle_id": "C_READ_GUARD",
          "goal": "Introduce the dedicated mismatch exception and the single approved branch-safe read adapter.",
          "deliverables": [
            {
              "id": "c1.state_branch_mismatch_error",
              "artifact": "mcp_server/managers/state_repository.py",
              "expected_result": "StateBranchMismatchError exists as the dedicated branch-mismatch read contract"
            }
          ],
          "exit_criteria": "A mismatched branch load raises StateBranchMismatchError via BranchValidatedStateReader, and the repository tests lock both the accepted and rejected read paths."
        }
      ]
    }
  }
}
```

Optional but recommended deliverable fields are `title`, `design_trace`, and `validates`. The persisted inner JSON in `.st3/deliverables.json` is the `planning_deliverables` object shown above, but the tool call itself must include the outer `issue_number` plus `planning_deliverables` wrapper.

Rules for the first write:
- `tdd_cycles.total` must equal the number of cycle entries
- `cycle_number` must be sequential `1..8`
- every cycle must have a non-empty `deliverables` list
- every cycle must have a non-empty string `exit_criteria`
- every deliverable object must carry a stable `id`, even on the first write, because later updates merge by deliverable id

---

## Cycle 1 — C_READ_GUARD

**Goal:** Introduce the dedicated mismatch exception and the single approved branch-safe read adapter.

**Depends On:** —

**Design trace:** [design.md](design.md) §3.3, §3.13, §3.15

### Deliverables

| id | artifact | expected result |
|---|---|---|
| `c1.state_branch_mismatch_error` | `mcp_server/managers/state_repository.py` | `StateBranchMismatchError` exists as the dedicated branch-mismatch read contract |
| `c1.branch_validated_state_reader` | `mcp_server/managers/state_repository.py` | `BranchValidatedStateReader` wraps `IStateReader` and rejects mismatched `state.branch` |
| `c1.read_guard_tests` | `tests/mcp_server/unit/managers/test_state_repository.py` | repository tests cover both match and mismatch paths |

**Exit criteria:** A mismatched branch load raises `StateBranchMismatchError` via `BranchValidatedStateReader`, and the repository tests lock both the accepted and rejected read paths.

**Expected result covered:** Later cycles can depend on one shared branch-safe reader instead of ad hoc caller-side guards.

---

## Cycle 2 — C_ENGINE_BREAK

**Goal:** Apply the clean break to engine query methods and the engine-query tool callers.

**Depends On:** C_READ_GUARD

**Design trace:** [design.md](design.md) §3.3, §3.6, §3.9, §3.14, §3.15

### Deliverables

| id | artifact | expected result |
|---|---|---|
| `c2.get_state_clean_break` | `mcp_server/managers/phase_state_engine.py` | `get_state()` propagates `StateBranchMismatchError` without translating it |
| `c2.get_current_phase_clean_break` | `mcp_server/managers/phase_state_engine.py` | `get_current_phase()` remains a thin wrapper and propagates the same exception |
| `c2.git_tools_error_handling` | `mcp_server/tools/git_tools.py` | direct `get_state()` and `get_current_phase()` callers catch `StateBranchMismatchError` and keep explicit operator guidance |
| `c2.git_pull_error_handling` | `mcp_server/tools/git_pull_tool.py` | pull-time state sync handles `StateBranchMismatchError` directly |
| `c2.clean_break_tests` | `tests/mcp_server/unit/tools/test_git_tools.py`, `tests/mcp_server/unit/tools/test_git_checkout_state_sync.py`, `tests/mcp_server/unit/tools/test_git_pull_tool_behavior.py`, `tests/mcp_server/unit/managers/test_phase_state_engine_c1.py` | tests assert the new exception contract instead of the removed translation shim |

**Exit criteria:** `PhaseStateEngine` no longer translates branch mismatch to `FileNotFoundError`, and the engine-query git tools handle `StateBranchMismatchError` directly while preserving the current explicit operator guidance.

**Expected result covered:** The clean break is real before resolver adoption begins, and no engine-query caller silently relies on the old `FileNotFoundError` shim.

---

## Cycle 3 — C_RESOLVER_CORE

**Goal:** Introduce the read-side core types without changing consumer behavior yet.

**Depends On:** C_READ_GUARD

**Design trace:** [design.md](design.md) §3.2, §3.4, §3.5, §3.13

### Deliverables

| id | artifact | expected result |
|---|---|---|
| `c3.workflow_status_dto` | `mcp_server/state/workflow_status.py` | immutable `WorkflowStatusDTO` exists in the state package, not in `schemas` |
| `c3.git_context_reader_contract` | `mcp_server/core/interfaces/__init__.py` | `IGitContextReader` exists as the resolver-facing git metadata contract |
| `c3.commit_phase_detector` | `mcp_server/core/commit_phase_detector.py` | commit-only detector wraps `ScopeDecoder` with `fallback_to_state=False` |
| `c3.workflow_status_resolver` | `mcp_server/managers/workflow_status_resolver.py` | resolver depends only on `IGitContextReader`, `IStateReader`, and `CommitPhaseDetector` |
| `c3.resolver_tests` | `tests/mcp_server/unit/managers/test_workflow_status_resolver.py` | resolver behavior is covered before consumer migration |

**Exit criteria:** The DTO, interface contract, detector, and resolver exist together as an independently testable read-side core with no consumer adoption mixed into the same cycle.

**Expected result covered:** The shared read-side abstraction exists and is independently testable before any adoption work.

---

## Cycle 4 — C_RESOLVER_ADOPTION

**Goal:** Move only the researched user-facing consumers to the new resolver and wire them through the composition root.

**Depends On:** C_RESOLVER_CORE, C_ENGINE_BREAK

**Design trace:** [design.md](design.md) §3.6, §3.12, §3.13, §3.15

### Deliverables

| id | artifact | expected result |
|---|---|---|
| `c4.project_manager_adoption` | `mcp_server/managers/project_manager.py` | `get_project_plan()` stops assembling workflow status locally and uses `WorkflowStatusResolver` |
| `c4.get_work_context_adoption` | `mcp_server/tools/discovery_tools.py` | `GetWorkContextTool` uses the resolver and gates cycle enrichment on `current_cycle is not None` |
| `c4.server_wiring` | `mcp_server/server.py`, `tests/mcp_server/test_support.py`, `tests/mcp_server/unit/test_server.py` | resolver and branch-validated state reader are injected consistently from the composition root |
| `c4.consumer_tests` | `tests/mcp_server/unit/managers/test_project_manager.py`, `tests/mcp_server/unit/tools/test_discovery_tools.py` | user-facing consumer migration is fully covered |

**Exit criteria:** `ProjectManager` and `GetWorkContextTool` consume one shared resolver, duplicate local workflow-status assembly is removed, and server/test wiring provides the new dependencies through the composition root.

**Expected result covered:** There is one shared user-facing workflow-status assembler and no duplicated local assembly remains in the two researched consumers.

---

## Cycle 5 — C_QA_STATE_SPLIT

**Goal:** Move QA baseline persistence out of workflow state and into its own typed file-backed repository.

**Depends On:** C_READ_GUARD

**Design trace:** [design.md](design.md) §3.7, §3.10, §3.13, §3.15

### Deliverables

| id | artifact | expected result |
|---|---|---|
| `c5.quality_state_model` | `mcp_server/state/quality_state.py` | `QualityState` exists as the dedicated QA baseline payload |
| `c5.quality_state_repository_contract` | `mcp_server/core/interfaces/__init__.py` | `IQualityStateRepository` exists as the dedicated QA-state persistence contract |
| `c5.quality_state_repository` | `mcp_server/managers/quality_state_repository.py` | `.st3/quality_state.json` reads and writes go through one repository abstraction |
| `c5.qa_manager_migration` | `mcp_server/managers/qa_manager.py` | baseline and failed-files logic no longer read/write workflow-owned QA data in `.st3/state.json` |
| `c5.branch_local_artifact_config` | `.st3/config/phase_contracts.yaml` | `.st3/quality_state.json` is treated as a branch-local artifact |
| `c5.qa_state_tests` | `tests/mcp_server/unit/managers/test_baseline_advance.py`, `tests/mcp_server/unit/managers/test_auto_scope_resolution.py` | QAManager tests assert the split state ownership |
| `c5.submit_pr_branch_local_artifact_test` | `tests/mcp_server/integration/test_submit_pr_atomic_flow.py` | PR submission flow neutralizes or protects `.st3/quality_state.json` exactly as branch-local policy requires |

**Exit criteria:** QA baseline state is isolated behind `IQualityStateRepository`, `QAManager` no longer mutates workflow-owned QA fields, and the submit-PR integration path recognizes `.st3/quality_state.json` as branch-local state.

**Expected result covered:** QA baseline data has one owner and no longer competes with workflow state persistence.

---

## Cycle 6 — C_MUTATOR_CORE

**Goal:** Move workflow writes and hook writes behind one coordinated mutator boundary.

**Depends On:** C_QA_STATE_SPLIT

**Design trace:** [design.md](design.md) §3.8, §3.9, §3.12, §3.13, §3.15

### Deliverables

| id | artifact | expected result |
|---|---|---|
| `c6.workflow_state_mutator_contract` | `mcp_server/core/interfaces/__init__.py` | `IWorkflowStateMutator` exists as the command-side workflow mutation contract |
| `c6.state_mutation_conflict_error` | `mcp_server/managers/workflow_state_mutator.py` | dedicated mutation conflict error exists with diagnostic and recovery fields |
| `c6.workflow_state_mutator` | `mcp_server/managers/workflow_state_mutator.py` | command-side workflow writes use one coordinated mutation seam |
| `c6.phase_state_engine_write_routing` | `mcp_server/managers/phase_state_engine.py` | initialize/transition/cycle operations and implementation hooks route through the mutator |
| `c6.mutator_wiring` | `mcp_server/server.py`, `tests/mcp_server/test_support.py` | composition root injects the mutator instead of leaving ad hoc save paths |
| `c6.mutator_tests` | `tests/mcp_server/unit/managers/test_phase_state_engine.py`, `tests/mcp_server/managers/test_phase_state_engine_async.py` | workflow write-path tests assert coordinated mutation behavior |

**Exit criteria:** Workflow command paths and implementation hooks write through `IWorkflowStateMutator`, conflicts surface through the dedicated error type, and no ad hoc workflow save path remains in the touched engine slice.

**Expected result covered:** Workflow writes stop relying on stale load-modify-save windows, including hook-driven implementation-phase writes.

---

## Cycle 7 — C_TOOL_CONFLICTS

**Goal:** Surface write conflicts explicitly through the phase, cycle, and quality tools.

**Depends On:** C_MUTATOR_CORE

**Design trace:** [design.md](design.md) §3.11, §3.13, §3.15

### Deliverables

| id | artifact | expected result |
|---|---|---|
| `c7.phase_tool_conflicts` | `mcp_server/tools/phase_tools.py` | phase tools return `ToolResult.error(...)` and emit `RecoveryNote` on mutation conflicts |
| `c7.cycle_tool_conflicts` | `mcp_server/tools/cycle_tools.py` | cycle tools expose the same operator-facing conflict behavior |
| `c7.quality_tool_conflicts` | `mcp_server/tools/quality_tools.py` | quality tool surfaces quality-state mutation conflicts explicitly |
| `c7.conflict_feedback_tests` | `tests/mcp_server/unit/tools/test_transition_phase_tool.py`, `tests/mcp_server/unit/tools/test_force_phase_transition_tool.py`, `tests/mcp_server/unit/tools/test_cycle_tools.py`, `tests/mcp_server/unit/tools/test_cycle_tools_legacy.py`, `tests/mcp_server/unit/tools/test_quality_tools.py` | tool-layer tests lock the operator feedback contract across phase, cycle, and quality tools |

**Exit criteria:** All three tool families convert mutation conflicts into explicit operator-facing errors with recovery guidance, and the corresponding unit tests lock that contract.

**Expected result covered:** Mutation conflicts become visible to operators through the existing tool response path instead of disappearing into logs.

---

## Cycle 8 — C_CLEANUP

**Goal:** Remove every legacy remnant left behind by the previous seven cycles.

**Depends On:** C_ENGINE_BREAK, C_RESOLVER_ADOPTION, C_QA_STATE_SPLIT, C_MUTATOR_CORE, C_TOOL_CONFLICTS

**Design trace:** [design.md](design.md) §1.3, §3.13, §3.14, §3.15

### Deliverables

| id | artifact | expected result |
|---|---|---|
| `c8.translation_and_fallback_grep_closure` | branch-wide grep closure | no `FileNotFoundError` translation shim, no constructor fallback compatibility layer, no stale branch-mismatch assumptions remain |
| `c8.legacy_test_cleanup` | touched unit/integration tests | obsolete tests and helpers for removed translation/fallback behavior are deleted or rewritten |
| `c8.final_wiring_cleanup` | touched production files + `tests/mcp_server/test_support.py` | no unused seams, dead helper code, or stale temporary wiring remain |
| `c8.final_verification` | focused tests + branch quality gates | the branch is ready to enter implementation with no known legacy baggage |

**Exit criteria:** Grep, focused tests, and branch quality gates show no remaining legacy translation, fallback constructor shape, stale helper, or obsolete test assumption in the touched slice.

**Expected result covered:** The branch ends implementation with zero intentional legacy code or legacy tests related to this slice.

---

## Deliverables JSON Appendix

The persisted JSON must use:
- `tdd_cycles.total = 8`
- sequential `cycle_number` values `1..8`
- stable symbolic `cycle_id` values matching the cycle labels in this document
- the exact deliverable ids listed in the cycle tables above
- one non-empty string `exit_criteria` per cycle

The persisted payload must stay aligned with this document. If the plan changes later, the update happens through `update_planning_deliverables` and this document is revised in the same slice.

---

## Related Documentation

- [design.md](design.md)
- [research.md](research.md)
- [docs/development/issue290/research-issue231-state-snapshot.md](../issue290/research-issue231-state-snapshot.md)
- [docs/development/issue290/research-issue292-state-mutation-concurrency.md](../issue290/research-issue292-state-mutation-concurrency.md)
- [docs/coding_standards/ARCHITECTURE_PRINCIPLES.md](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Agent | Initial planning audit trace with eight bounded implementation cycles, explicit dependency order, JSON-ready cycle mapping, interface-contract slices, and mandatory final cleanup cycle |
