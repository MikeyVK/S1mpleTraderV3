<!-- docs\development\issue283\planning.md -->
<!-- template=planning version=130ac5ea created=2026-04-13T00:00Z updated= -->
# git_add_or_commit regression fix — NoteContext protocol, config-boundary closure

**Status:** DRAFT
**Version:** 1.1
**Last Updated:** 2026-04-14
**Design reference:** [design-git-add-commit-regression-fix.md](design-git-add-commit-regression-fix.md) v11.0
**Research reference:** [research-git-add-or-commit-regression.md](research-git-add-or-commit-regression.md) v1.5

---

## 1. Purpose

Executable implementation specification and deliverables manifest for the `git_add_or_commit` ready-phase regression fix (issue #283).

This document translates the five coordinated design changes in the v11.0 design into six concrete TDD cycles with verifiable exit criteria, a complete deliverables.json draft, and cycle-by-cycle gate proofs. It serves as both an implementation guide and the input to `save_planning_deliverables`.

---

## 2. Scope

**In Scope:**

| Area | Change |
|------|--------|
| `mcp_server/core/operation_notes.py` | New module: all NoteEntry variants, `NoteContext`, `Renderable` protocol |
| `mcp_server/adapters/git_adapter.py` | `commit()` gains `skip_paths: frozenset[str]` postcondition |
| `mcp_server/managers/git_manager.py` | `commit_with_scope()` gains `skip_paths` parameter; constructor accepts `WorkphasesConfig` |
| `mcp_server/managers/enforcement_runner.py` | Declarative rewrite: returns `None`, writes `ExclusionNote` to `NoteContext`; no git ops |
| `mcp_server/tools/base.py` | `BaseTool.execute()` gains `context: NoteContext` second parameter |
| `mcp_server/tools/git_tools.py` | `GitCommitTool.execute()` reads `ExclusionNote`, writes `CommitNote` |
| All tool implementations | Accept and pass through `context: NoteContext` |
| `mcp_server/server.py` | `handle_call_tool` threads `NoteContext`; wires `WorkphasesConfig` at 2 callsites |
| `mcp_server/core/exceptions.py` | Remove `MCPError.hints`, `PreflightError(blockers=)`, `ExecutionError(recovery=)` |
| `mcp_server/tools/tool_result.py` | Remove `ToolResult.hints` |
| `mcp_server/core/error_handling.py` | `tool_error_handler`: remove `hints` extraction; stays context-agnostic |
| All raise-sites (26) | Migrate to typed notes (`BlockerNote`, `RecoveryNote`, `SuggestionNote`) |
| `mcp_server/core/phase_detection.py` | Constructor accepts `WorkphasesConfig` |
| `mcp_server/managers/phase_state_engine.py` | Remove file-existence check; use injected config |
| `mcp_server/managers/enforcement_runner.py` | `_handle_check_merge_readiness`: corrected proxy using `_has_net_diff_for_path` |
| Structural regression tests | 3 AST-walk guards in `test_c_loader_structural.py` |
| Public-path integration tests | Replace Principle-14-violating private-method tests |

**Out of Scope:**

| Area | Reason |
|------|--------|
| `workphases.yaml` / `phase_contracts.yaml` schema | No schema change needed |
| Commit message formatting | Separate concern |
| `OperationResult[T]` / `NotesAggregator` | Superseded by `NoteContext`; never implemented |
| `MCPSystemError.fallback` | Separate concern — not in `hints` |

---

## 3. Prerequisites

- [ ] `design-git-add-commit-regression-fix.md` v11.0 committed on active branch (QA GO)
- [ ] `research-git-add-or-commit-regression.md` v1.5 committed on active branch (QA GO)
- [ ] Branch `refactor/283-ready-phase-enforcement` active, `planning` phase
- [ ] `pytest tests/mcp_server/ --override-ini="addopts=" --tb=no -q` → all pass, 0 errors at cycle start

---

## 4. Summary

Six TDD cycles closing the ready-phase commit regression. The cycle order respects the contract dependency graph: the new note protocol (C1) is the foundation; git semantics (C2) are purely mechanical; wiring the complete dispatch flow (C3) is the integration proof; exception flag-day migration (C4) is the flag-day clean-break cycle; config-boundary closure (C5) eliminates all five remaining config-root violations; and the final cycle (C6) corrects the create_pr proxy and locks down public-path regression coverage.

| Cycle | Title | Critical Path | Safe to parallelize with |
|-------|-------|---------------|--------------------------|
| C1 | NoteEntry types, NoteContext, structural guards | Yes — foundation | — |
| C2 | GitAdapter `skip_paths` postcondition | Yes | — |
| C3 | NoteContext wiring (enforcement, tool, server) | Yes | — |
| C4 | Exception flag-day migration | Yes | C5 (touches different modules) |
| C5 | WorkphasesConfig injection (5 callsites) | Depends on C1+C2 | C4 |
| C6 | create_pr proxy + public-path regression | Depends on C3+C4+C5 | — |

---

## 5. Design-to-Research Coverage Map

| Requirement cluster | Design sections | Research findings | Planned cycle(s) | Concrete deliverables | Validation proof |
|--------------------|-----------------|-------------------|------------------|-----------------------|-----------------|
| NoteContext protocol and typed notes | §3.3 (NoteEntry), §3.4 (NoteContext), §3.5 (BaseTool) | Notes-problem statement: `list[str]` is unvalidatable; implicit coupling | C1, C3 | `operation_notes.py` module; `NoteContext.produce/of_type/render_to_response`; `BaseTool.execute(context:)` signature | `test_note_context_unit.py`; integration: rendered TextContent block present |
| `tool_error_handler` and exception-path migration | §3.11 (decorator migration, semantic contract, raise-site pattern) | `_augment_text_with_error_metadata` only renders hints on error; success path is dead | C4 | `tool_error_handler` with no hints extraction; all 26 raise-sites migrated to typed notes; `MCPError.hints` removed; `ToolResult.hints` removed | structural: `test_no_hints_kwarg_on_mcp_error_callsites`; integration: BlockerNote/RecoveryNote rendered |
| `GitAdapter.commit()` skip_paths postcondition | §3.8 (semantics, zero-delta guarantee) | `git add .` re-stages excluded files post-enforcement | C2 | `commit(skip_paths=frozenset[str])` on `GitAdapter`; `commit_with_scope(skip_paths=)` on `GitManager` | unit: no delta for skip_paths in commit diff (files= and add . routes) |
| `EnforcementRunner` declarative rewrite | §3.6 (producer boundary), §3.2 (sequence diagram) | Notes dropped on success path; enforcement returns `list[str]` that `_run_tool_enforcement` discards | C3 | `EnforcementRunner.run()` → `None`, writes `ExclusionNote`; no git ops in runner; `_run_tool_enforcement` wired with `note_context` | `test_enforcement_runner_unit.py`: `run()` returns None; `context.of_type(ExclusionNote)` has entry |
| `create_pr` proxy correction | §3.9 (`_has_net_diff_for_path`, net-diff vs tracked-check) | `_git_is_tracked` → `git ls-files` tests HEAD tree not net delta; false positive blocks PR | C6 | `_has_net_diff_for_path` helper; `_handle_check_merge_readiness` uses `git diff merge_base..HEAD`; `context` not discarded | integration: clean branch not blocked; contaminated branch blocked |
| `WorkphasesConfig` injection (all 5 callsites) | §3.12 (callsite table, before/after constructors) | Config-root audit: 5 violations in `server.py:211`, `server.py:222`, `phase_detection.py:85`, `phase_state_engine.py:91`, `git_manager.py:26` | C5 | `ScopeDecoder(workphases_config=)`, `GitManager(workphases_config=)`, `PhaseDetection(workphases_config=)`, `PhaseStateEngine` without file check; `server.py` wired | unit: `commit_with_scope` executes without `open()` call; structural: `test_no_raw_st3_config_paths_in_production` |
| Structural regression tests | §3.14 (three AST-walk guards) | Principle 14 debt: private-method tests provide false coverage; config-path literals unchecked | C1 | Three structural tests in `test_c_loader_structural.py` | All three structural tests pass immediately after C1 GREEN |
| Public-path integration coverage | §3.14 (test targets, Principle 14) | `test_enforcement_runner_c3.py` calls private methods directly; no full dispatch path test | C6 | Integration tests: full `git_add_or_commit` dispatch → no delta → rendered exclusion message; replace `test_enforcement_runner_c3.py` private-method dependencies | named integration tests pass; private-method call patterns removed |
| Deliverables gating model | §2 (design options), §3.1 (decisions) | No end-to-end test exists; false sense of coverage from isolated enforcement tests | All cycles | One deliverable per cycle per concrete observable outcome; each cycle has named gate proofs | `save_planning_deliverables` JSON validated; `run_tests` passes after each cycle |

---

## 6. Dependencies and Cycle Order

### 6.1 Critical Path

```
C1 (contract surface)
  └── C2 (git semantics)
        ├── C3 (wiring — enforcement/tool/server) ─┐
        │     └── C4 (flag-day exception migration) ─┤
        └── C5 (config injection) ─────────────────┤
                                                     └── C6 (proxy correction + regression suite)
```

| Dependency edge | Reason |
|----------------|--------|
| C1 → C2 | C2 only needs `ExclusionNote` type; git semantics do not require full NoteContext threading |
| C2 → C3 | `GitCommitTool` reads `ExclusionNote` → `skip_paths`; `GitAdapter.commit(skip_paths=)` must exist first |
| C3 → C4 | Exception flag-day migration writes typed notes to a `NoteContext` at each raise-site; the context must be in scope (threaded through the call chain) before migration is safe |
| C2 → C5 | `WorkphasesConfig` injection only needs the typed config object (C1) and the `GitManager` constructor already modified in C2 for `skip_paths`; C3 wiring is not a prerequisite for constructor signature changes |
| C3 + C4 + C5 → C6 | The create_pr proxy fix and public-path integration tests require: (a) the full note flow working end-to-end (C3); (b) exception paths rendering typed notes (C4); (c) config boundary closed so server wire-up is clean (C5) |

### 6.2 Safe Parallelization

C4 and C5 touch non-overlapping modules: C4 is exception callsites, C5 is constructor signatures. They may be implemented concurrently after C3, provided:
- C4 does not modify `GitManager` (only raise-site patterns in managers that raise exceptions)
- C5 does not add new note types (only constructor interface change)

In practice, sequential execution (C4 then C5) is recommended to avoid merge conflicts on `server.py`, which is touched by both cycles.

### 6.3 Flag-Day Migration Ordering

The exception migration (C4) is safe to perform as a single flat sweep in one cycle because:
1. C1 structural guard (`test_no_hints_kwarg_on_mcp_error_callsites`) provides the mechanical check that catches any missed callsite.
2. C3 has already threaded `NoteContext` through the dispatch chain, so every raise-site that needs `note_context` has it in scope.
3. The flag-day constraint (no shims, no deprecated overloads) is satisfied: all 26 callsites migrate in one cycle; Pyright type errors act as compile-time confirmation that the sweep is complete.

### 6.4 Cycle-by-Cycle Responsibilities

| Concern | Established in cycle |
|---------|---------------------|
| Contract surfaces (`NoteEntry`, `NoteContext`, `Renderable`) | C1 |
| Structural guards (no config literals, no `hints=`, no `blockers=`/`recovery=`) | C1 |
| Git exclusion semantics (`skip_paths` postcondition) | C2 |
| Full dispatch wiring (enforcement → tool → server → render) | C3 |
| Exception flag-day migration | C4 |
| Config-boundary closure (5 callsites) | C5 |
| create_pr merge-readiness semantics | C6 |
| Public-path regression tests | C6 |

---

## 7. TDD Cycles

---

### Cycle 1 — NoteEntry types, NoteContext, and structural regression guards

**Goal:** Establish the complete typed notes protocol in a single new module (`operation_notes.py`) and install three AST-walk structural regression tests that enforce the flag-day invariants for the rest of the implementation. This cycle creates the contract surface all other cycles build on — it must complete and be green before any other cycle starts.

**Why This Cycle Exists Now:** Every other cycle either produces notes (`ExclusionNote`, typed exception notes), consumes notes (`ExclusionNote` → `skip_paths`), or is guarded by the structural tests. Nothing can be verified as correctly migrated until the types exist and the guards are in place.

**Design Refs:** §3.3 (NoteEntry type definitions), §3.4 (NoteContext), §3.13 (module placement), §3.14 (structural regression tests).

**Research Refs:** Notes-problem statement (list[str] is unvalidatable); Principle 14 debt finding (private-method tests provide false coverage).

**Files or Modules Likely Touched:**
- `mcp_server/core/operation_notes.py` — new
- `tests/mcp_server/unit/config/test_c_loader_structural.py` — new
- `tests/mcp_server/unit/core/test_note_context_unit.py` — new
- `mcp_server/core/__init__.py` — add export if needed

**RED:** Write and confirm failing:
- `test_operation_notes_module_exists` — `from mcp_server.core.operation_notes import NoteContext` raises `ImportError` (module absent)
- `test_note_context_produce_of_type_insertion_order` — `NoteContext.produce/of_type` not yet implemented
- `test_note_context_render_empty_returns_base_unchanged` — `render_to_response` not yet implemented
- `test_note_context_render_renderable_appends_text_content` — same
- `test_no_raw_st3_config_paths_in_production` — fails because `phase_detection.py`, `phase_state_engine.py`, `git_manager.py`, `server.py` still contain `.st3/config/` literals
- `test_no_hints_kwarg_on_mcp_error_callsites` — fails because `MCPError` callsites still pass `hints=`
- `test_no_blockers_or_recovery_kwargs_on_exception_callsites` — fails because `PreflightError(blockers=)` and `ExecutionError(recovery=)` callsites still exist

**GREEN:**
- Create `mcp_server/core/operation_notes.py` with: `Renderable` (runtime_checkable Protocol), `ExclusionNote`, `CommitNote`, `SuggestionNote`, `BlockerNote`, `RecoveryNote`, `InfoNote`, `NoteEntry` union, `NoteContext` (with `produce`, `of_type`, `render_to_response`)
- Note: structural tests for config literals and exception kwargs will still fail at this point — they reflect future implementation state, not C1 state. GREEN for C1 means: note-protocol unit tests pass; structural tests are committed as failing-but-known (they become GREEN after C4/C5)

**REFACTOR:**
- Verify Pyright generates no errors in `operation_notes.py` (exhaustiveness, frozen dataclasses)
- Confirm `CommitNote` does NOT implement `to_message()` — render_to_response test verifies CommitNote is not emitted
- Docstring completeness on NoteContext invariants

**Deliverables For This Cycle:**
1. `operation_notes.py` exists with all six note types, `NoteEntry` union, `NoteContext`
2. `NoteContext.render_to_response()` returns base unchanged when no Renderable entries present
3. `NoteContext.render_to_response()` appends TextContent block with all Renderable entries in insertion order
4. Three structural regression tests committed (initially failing for config/exception sites — will turn green in C4/C5)
5. `CommitNote` has no `to_message()` method and produces no user-visible output

**Exit Criteria:**
- `test_note_context_unit.py` all pass (produce/of_type/render variations)
- `test_c_loader_structural.py` committed; note counts for expected current-state failures documented
- Pyright clean on `operation_notes.py`
- `pytest tests/mcp_server/unit/core/test_note_context_unit.py` → all pass

**Gate Proof:** `pytest tests/mcp_server/unit/core/test_note_context_unit.py -v` → 5 passed; `pytest tests/mcp_server/unit/config/test_c_loader_structural.py` → 3 failed (expected, by design)

**Cycle 1 — Structural Red State (recorded 2026-04-14)**

The three structural regression guards in `test_c_loader_structural.py` are intentionally
failing in Cycle 1 and must remain red until their designated resolution cycles:

| Test | Why failing in C1 | Resolved in |
|------|-------------------|-------------|
| `test_no_raw_st3_config_paths_in_production` | `phase_detection.py`, `phase_state_engine.py`, `git_manager.py`, and `server.py` still contain raw `.st3/config/` string literals. These are removed via `WorkphasesConfig` injection. | **C5** |
| `test_no_hints_kwarg_on_mcp_error_callsites` | Exception constructor callsites throughout `mcp_server/` still pass `hints=` kwargs to `MCPError` subclasses. Removal is part of the exception flag-day migration. | **C4** |
| `test_no_blockers_or_recovery_kwargs_on_exception_callsites` | `PreflightError(blockers=...)` and `ExecutionError(recovery=...)` callsites still exist. These constructor params are removed via the C4 raise-site rewrite. | **C4** |

These tests are **not regressions**. They must not be fixed prematurely outside their
respective cycles. Their permanent presence acts as a mechanical gate ensuring C4 and C5
close the violations they guard.

**Dependencies:** None (this is the foundational cycle)

---

### Cycle 2 — GitAdapter `skip_paths` postcondition

**Goal:** Add `skip_paths: frozenset[str]` to `GitAdapter.commit()` and `GitManager.commit_with_scope()` such that any path in `skip_paths` is unconditionally removed from the staging area after all staging operations (`files=` or `git add .`), producing a zero-delta commit for those paths. This is the purely mechanical git-semantics cycle.

**Why This Cycle Exists Now:** Defect A (`git add .` re-staging) must be fixed at the adapter level before C3 can wire enforcement notes to commit behavior. The postcondition must exist and be unit-tested before the tool is modified to supply `skip_paths`.

**Design Refs:** §3.8 (GitAdapter skip_paths semantics, zero-delta guarantee), §3.1 (key decision: GitAdapter owns all git exclusion ops).

**Research Refs:** Commit-path findings: `GitAdapter.commit(files=None)` calls `git add .`, re-staging files that enforcement uncached; interaction defect between pre-enforcement and commit execution.

**Files or Modules Likely Touched:**
- `mcp_server/adapters/git_adapter.py` — `commit()` signature and body
- `mcp_server/managers/git_manager.py` — `commit_with_scope()` signature
- `tests/mcp_server/unit/adapters/test_git_adapter_skip_paths.py` — new
- `tests/mcp_server/unit/managers/test_git_manager_skip_paths.py` — new (or extend existing)

**RED:**
- `test_commit_with_skip_paths_files_none_no_delta` — `GitAdapter.commit(message=..., skip_paths=frozenset({".st3/state.json"}))` does not yet exist (TypeError)
- `test_commit_with_skip_paths_explicit_files_no_delta` — same
- `test_commit_without_skip_paths_no_restore_staged` — `git restore --staged` not called when `skip_paths=frozenset()`
- `test_commit_with_scope_passes_skip_paths_to_adapter` — `GitManager.commit_with_scope(..., skip_paths=frozenset({...}))` — parameter missing

**GREEN:**
- `GitAdapter.commit()`: add `skip_paths: frozenset[str] = frozenset()` parameter; after all staging, iterate `skip_paths` and call `self.repo.git.restore("--staged", path)` for each
- `GitManager.commit_with_scope()`: add `skip_paths: frozenset[str] = frozenset()` parameter; pass through to `GitAdapter.commit()`

**REFACTOR:**
- Verify the zero-delta property in unit test using a real or mocked git repo: after `commit(skip_paths={path})`, `path` does not appear in `commit.diff(commit.parents[0])`
- Confirm no staging branches in the postcondition: `git restore --staged` runs for every `skip_path` regardless of `files=` route

**Deliverables For This Cycle:**
1. `GitAdapter.commit()` accepts `skip_paths: frozenset[str]`; postcondition applies after all staging
2. `GitManager.commit_with_scope()` accepts and forwards `skip_paths`
3. Unit test: `skip_paths` path absent from commit diff when `files=None`
4. Unit test: `skip_paths` path absent from commit diff when explicit `files=` list supplied
5. Unit test: no `git restore --staged` called when `skip_paths=frozenset()`

**Exit Criteria:**
- All five deliverables above testable and green
- No `open()` or YAML reads introduced in this cycle
- `pytest tests/mcp_server/unit/adapters/` and `tests/mcp_server/unit/managers/` relevant tests pass

**Gate Proof:** `pytest tests/mcp_server/unit/adapters/test_git_adapter_skip_paths.py -v` → all pass

**Dependencies:** C1 (only `ExclusionNote` type; git semantics themselves are independent of NoteContext threading)

---

### Cycle 3 — NoteContext wiring: EnforcementRunner declarative, GitCommitTool consumer, server orchestration

**Goal:** Wire the complete per-call NoteContext flow through the three layers: `EnforcementRunner` becomes declarative (writes `ExclusionNote`, performs no git ops, returns `None`); `GitCommitTool.execute()` gains the `context: NoteContext` parameter and reads `ExclusionNote` to build `skip_paths`; `MCPServer.handle_call_tool()` creates `NoteContext` once, threads it through enforcement and tool execution, and calls `render_to_response()` unconditionally. This cycle proves the protocol end-to-end.

**Why This Cycle Exists Now:** This is the integration proof cycle. C1 defined the types; C2 provided the git mechanism; C3 connects them. After C3, a ready-phase `git_add_or_commit` call must produce a commit with no delta on `state.json` AND a rendered exclusion message in the response.

**Design Refs:** §3.2 (happy-path sequence diagram), §3.5 (BaseTool.execute contract change), §3.6 (EnforcementRunner producer boundary), §3.7 (GitCommitTool consumer), §3.10 (server flow, simplified diff).

**Research Refs:** Architecture interaction map: server discards enforcement notes; adapter re-stages excluded files; the defect is an inter-layer contract breach, not an individual layer failure.

**Files or Modules Likely Touched:**
- `mcp_server/managers/enforcement_runner.py` — `run()` signature and body
- `mcp_server/tools/base.py` — `BaseTool.execute()` abstract method signature
- `mcp_server/tools/git_tools.py` — `GitCommitTool.execute()`; add `CommitNote`
- All other tool `execute()` implementations — add `context: NoteContext` param (accept and ignore)
- `mcp_server/server.py` — `handle_call_tool`, `_run_tool_enforcement` — thread NoteContext; call `render_to_response`; delete `_augment_text_with_error_metadata`, `_tool_result_from_exception`
- `tests/mcp_server/unit/managers/test_enforcement_runner_unit.py` — new (public-path unit: `run()` returns None; ExclusionNote in context)
- `tests/mcp_server/integration/test_git_add_commit_ready_phase_c3.py` — new (integration: full dispatch, rendered exclusion message)

**RED:**
- `test_enforcement_runner_run_returns_none` — `run()` currently returns `list[str]` not `None`
- `test_enforcement_runner_writes_exclusion_note` — `context.of_type(ExclusionNote)` currently empty after `run()`
- `test_enforcement_runner_no_git_ops` — runner currently calls `git rm --cached`; after C3 it must not
- `test_git_commit_tool_execute_accepts_context` — `execute(params, context)` not yet on `GitCommitTool`
- `test_git_commit_tool_reads_exclusion_note` — tool not yet reading `ExclusionNote`
- `test_server_renders_exclusion_note_in_response` — server does not yet call `render_to_response`

**GREEN:**
- `EnforcementRunner.run()`: return type → `None`; `_handle_exclude_branch_local_artifacts` writes `ExclusionNote` entries; no `git rm --cached` calls
- `BaseTool.execute()`: abstract method updated to `async def execute(self, params: Any, context: NoteContext) -> ToolResult`
- All tool `execute()` implementations: add `context: NoteContext` as second parameter (accept and ignore)
- `GitCommitTool.execute()`: read `ExclusionNote` entries → `frozenset`; call `commit_with_scope(..., skip_paths=...)`; write `CommitNote`
- `MCPServer.handle_call_tool()`: create `NoteContext` per call; pass to `_run_tool_enforcement` and `tool.execute`; call `context.render_to_response(result)` on both success and error paths; delete old hint methods

**REFACTOR:**
- Confirm `CommitNote` is not rendered (unit test: render with only `CommitNote` → base unchanged)
- Verify the server never calls `of_type()` — only `render_to_response()`
- Confirm `_augment_text_with_error_metadata` and `_tool_result_from_exception` are fully deleted

**Deliverables For This Cycle:**
1. `EnforcementRunner.run()` returns `None` and writes `ExclusionNote` per excluded path
2. `EnforcementRunner._handle_exclude_branch_local_artifacts` contains zero `git rm --cached` calls
3. `BaseTool.execute(params, context: NoteContext)` signature enforced on base class
4. `GitCommitTool.execute()` reads `ExclusionNote` and passes `skip_paths` to `commit_with_scope`
5. Integration test: ready-phase `git_add_or_commit` dispatch — rendered response contains exclusion message AND commit has zero delta on `.st3/state.json`

**Exit Criteria:**
- All unit tests in `test_enforcement_runner_unit.py` pass
- Integration test `test_git_add_commit_ready_phase_c3.py` passes (real git)
- `_augment_text_with_error_metadata` and `_tool_result_from_exception` absent from `server.py`
- Pyright clean on modified modules

**Gate Proof:** `pytest tests/mcp_server/unit/managers/test_enforcement_runner_unit.py tests/mcp_server/integration/test_git_add_commit_ready_phase_c3.py -v` → all pass

**Dependencies:** C1 (NoteContext, ExclusionNote types), C2 (GitAdapter.commit skip_paths postcondition)

---

### Cycle 4 — Exception flag-day migration: MCPError.hints, ToolResult.hints, blockers=/recovery= removal

**Goal:** Perform the complete flag-day breaking removal of all untyped hint channels and legacy exception constructor parameters. Remove `MCPError.hints`, `ToolResult.hints`, `PreflightError(blockers=)`, `ExecutionError(recovery=)`, and the `hints` extraction from `tool_error_handler`. Migrate all 26 raise-sites to write typed notes before raising. Delete `_run_git_command(recovery=...)`.

**Why This Cycle Exists Now:** C3 threads `NoteContext` through the dispatch chain, so all raise-sites that need `note_context` now have it in scope. The flag-day migration is safe exactly because C3 established the context threading contract. Deferring this cycle would leave two parallel untyped/typed channels operating simultaneously, which violates the design constraint.

**Design Refs:** §3.11 (semantic contract, raise-site pattern, decorator migration, callsite table), §3.3 (note variant responsibilities), §1.3 (flag-day constraints).

**Research Refs:** Success-notes problem: `_augment_text_with_error_metadata` only renders hints when `is_error=True` — dead on success path. Principle 14 violation: `test_tool_error_contract_e2e.py` asserts on `hints` content (implicit string parsing).

**Files or Modules Likely Touched:**
- `mcp_server/core/exceptions.py` — remove `MCPError.hints`, `PreflightError(blockers=)`, `ExecutionError(recovery=)`
- `mcp_server/tools/tool_result.py` — remove `ToolResult.hints`, `ToolResult.error(hints=...)`
- `mcp_server/core/error_handling.py` — `tool_error_handler`: remove `hints` extraction, `hints=` in `ToolResult.error` calls
- `mcp_server/managers/enforcement_runner.py` — all raise-sites with `blockers=`/`recovery=`/`hints=` kwargs
- `mcp_server/managers/git_manager.py` — raise-sites
- `mcp_server/managers/phase_state_engine.py` — raise-sites
- `mcp_server/core/phase_detection.py` — raise-sites
- All other `mcp_server/` modules with raise-sites
- `mcp_server/adapters/git_adapter.py` — `_run_git_command`: remove `recovery=` kwarg
- `tests/mcp_server/unit/core/test_tool_error_handler_c4.py` — new
- `tests/mcp_server/integration/test_blocker_recovery_note_dispatch.py` — new
- Existing tests asserting on `.hints` field: rewrite to assert on rendered response TextContent

**RED:**
- `test_mcp_error_has_no_hints_field` — `MCPError(message="x", hints=["y"])` currently accepted; after C4 it must raise `TypeError`
- `test_tool_result_has_no_hints_field` — `ToolResult.error(hints=["y"])` currently accepted; after C4 must raise `TypeError`
- `test_tool_error_handler_returns_no_hints` — decorator currently produces `hints` in error ToolResult
- `test_blocker_note_rendered_in_dispatch` — `BlockerNote` not yet written by any raise-site
- `test_recovery_note_rendered_in_dispatch` — same for `RecoveryNote`
- Structural: `test_no_hints_kwarg_on_mcp_error_callsites` — currently failing (installed in C1; turns green in C4)
- Structural: `test_no_blockers_or_recovery_kwargs_on_exception_callsites` — currently failing (turns green in C4)

**GREEN:**
- Remove `hints: list[str] | None` from `MCPError` and all subclasses
- Remove `blockers: list[str] | None` from `PreflightError`; remove `recovery: list[str] | None` from `ExecutionError`
- Remove `hints: list[str] | None` from `ToolResult`; remove `hints=` from `ToolResult.error()`
- `tool_error_handler`: delete `hints` variable, all `exc.hints` references, `hints=hints` in `ToolResult.error(...)` and `ToolResult(...)` constructor calls
- Sweep all 26 raise-sites: write appropriate typed note (`BlockerNote`, `RecoveryNote`, `SuggestionNote`) before each raise; remove `blockers=`, `recovery=`, `hints=` kwargs
- `_run_git_command`: remove `recovery=` parameter; callers write `RecoveryNote` before re-raising `ExecutionError`
- Display-only constants: replace `_ENFORCEMENT_DISPLAY_PATH` and similar with `{configRoot}/filename` form; remove dead `_WORKPHASES_DISPLAY_PATH`
- Rewrite `test_tool_error_contract_e2e.py` assertions from `.hints` content to rendered TextContent inspection

**REFACTOR:**
- Verify Pyright raises no errors in `exceptions.py`, `tool_result.py`, `error_handling.py`
- Confirm structural tests `test_no_hints_kwarg_on_mcp_error_callsites` and `test_no_blockers_or_recovery_kwargs_on_exception_callsites` now pass
- Verify `tool_error_handler` does not import `operation_notes` (stays context-agnostic)

**Deliverables For This Cycle:**
1. `MCPError.hints` field absent; all `hints=` callsites raise `TypeError` (verified by structural test)
2. `ToolResult.hints` field absent; `ToolResult.error(hints=...)` parameter removed
3. `tool_error_handler` contains no `hints` variable, no `exc.hints`, no `hints=` kwarg; does not import `operation_notes`
4. `PreflightError(blockers=)` and `ExecutionError(recovery=)` parameters absent (verified by structural test)
5. Integration test: `BlockerNote` written at raise-site renders as separate TextContent block in dispatch response
6. Structural tests `test_no_hints_kwarg_on_mcp_error_callsites` and `test_no_blockers_or_recovery_kwargs_on_exception_callsites` both GREEN

**Exit Criteria:**
- Both structural tests GREEN
- `test_tool_error_handler_c4.py` all pass
- `test_blocker_recovery_note_dispatch.py` all pass
- Pyright clean on `exceptions.py`, `tool_result.py`, `error_handling.py`
- No `except` block suppresses typed notes (verify note written before raise, not in except)

**Gate Proof:** `pytest tests/mcp_server/unit/config/test_c_loader_structural.py tests/mcp_server/unit/core/test_tool_error_handler_c4.py tests/mcp_server/integration/test_blocker_recovery_note_dispatch.py -v` → all pass

**Dependencies:** C1 (typed note types), C3 (NoteContext threaded through dispatch chain — callsites have `note_context` in scope)

---

### Cycle 5 — WorkphasesConfig injection: all 5 callsites

**Goal:** Eliminate all five remaining raw `Path` config violations by replacing `workphases_path: Path` constructor parameters with `workphases_config: WorkphasesConfig` in `ScopeDecoder`, `GitManager`, `PhaseDetection`, and `PhaseStateEngine`; update both `server.py` callsites to wire the typed config object. After C5, the structural test `test_no_raw_st3_config_paths_in_production` turns GREEN.

**Why This Cycle Exists Now:** This is the mechanical config-boundary sweep. It must follow C3 (because `GitManager` is already updated in C2/C3) and can safely run in parallel with C4 — but sequential is recommended to avoid `server.py` conflicts. The structural guard (C1) provides immediate verification.

**Design Refs:** §3.12 (5-callsite table, before/after constructors), §2.E (option rationale: replace interface to eliminate all five simultaneously), §1.3 (DI/Config-First constraint).

**Research Refs:** Config-root boundary audit: five active violations; `ScopeDecoder` and `GitManager` still accept `workphases_path: Path`; root cause is a `Path`-accepting interface — replacing it eliminates all five simultaneously.

**Files or Modules Likely Touched:**
- `mcp_server/core/phase_detection.py` — constructor: `workphases_config: WorkphasesConfig` replaces `workphases_path: Path`; remove CWD-sensitive fallback
- `mcp_server/managers/phase_state_engine.py` — remove file-existence check at line 91; operate on already-injected config
- `mcp_server/managers/git_manager.py` — constructor: `workphases_config: WorkphasesConfig`; `commit_with_scope` reads `self._workphases_config.phases[...]` directly
- `mcp_server/core/phase_detection.py` — `ScopeDecoder.__init__`: replace `workphases_path: Path` with `workphases_config: WorkphasesConfig`
- `mcp_server/server.py` — lines 211, 222: `ScopeDecoder(workphases_config=workphases_config)`
- `tests/mcp_server/unit/managers/test_git_manager_no_file_open.py` — new (or extend): `commit_with_scope` executes without `open()` call
- `tests/mcp_server/unit/config/test_c_loader_structural.py` — `test_no_raw_st3_config_paths_in_production` turns GREEN after this cycle

**RED:**
- `test_scope_decoder_accepts_workphases_config` — currently `ScopeDecoder(workphases_path=...)` accepted; after C5 `workphases_config=` required
- `test_git_manager_accepts_workphases_config` — `GitManager(workphases_config=...)` not yet accepted
- `test_phase_detection_accepts_workphases_config` — `PhaseDetection(workphases_config=...)` not yet accepted
- `test_phase_state_engine_no_file_check` — `PhaseStateEngine` currently checks file existence
- `test_no_raw_st3_config_paths_in_production` — currently failing (C1-installed); turns GREEN in C5
- `test_git_manager_commit_with_scope_no_open` — `commit_with_scope` currently opens YAML file

**GREEN:**
- Update constructor signatures: `ScopeDecoder`, `GitManager`, `PhaseDetection`, `PhaseStateEngine`
- Remove all raw `Path` construction for `workphases.yaml` in these classes
- Remove `PhaseStateEngine` file-existence check; use `self._workphases_config` directly
- Update `server.py` callsites 211, 222
- Update all test fixtures that construct these classes

**REFACTOR:**
- Verify structural test `test_no_raw_st3_config_paths_in_production` GREEN
- Confirm `commit_with_scope` reads `self._workphases_config.phases[workflow_phase]` with no file I/O
- Pyright clean on all modified constructors

**Deliverables For This Cycle:**
1. `ScopeDecoder.__init__` accepts `workphases_config: WorkphasesConfig`; `workphases_path: Path` removed from constructor
2. `GitManager.__init__` accepts `workphases_config: WorkphasesConfig`; `commit_with_scope` performs no file I/O
3. `PhaseDetection.__init__` accepts `workphases_config: WorkphasesConfig`; CWD-sensitive fallback removed
4. `PhaseStateEngine.__init__` removes file-existence check; operates on injected config only
5. Structural test `test_no_raw_st3_config_paths_in_production` turns GREEN
6. `server.py` both callsites use `ScopeDecoder(workphases_config=workphases_config)`

**Exit Criteria:**
- `test_no_raw_st3_config_paths_in_production` GREEN
- Unit test: `GitManager.commit_with_scope` executes without `open()` call
- All existing tests that construct the four affected classes updated and passing
- Pyright clean on all five changed constructors

**Gate Proof:** `pytest tests/mcp_server/unit/config/test_c_loader_structural.py::test_no_raw_st3_config_paths_in_production tests/mcp_server/unit/managers/test_git_manager_no_file_open.py -v` → all pass

**Dependencies:** C1 (structural guard must exist), C2 (GitManager `commit_with_scope` already has `skip_paths` parameter — no signature conflict), C3 (server wire-up structure stable)

---

### Cycle 6 — create_pr proxy correction and public-path integration regression tests

**Goal:** Replace the false-positive `_git_is_tracked` proxy in `_handle_check_merge_readiness` with the correct net-state-change proxy (`_has_net_diff_for_path` using `git diff merge_base..HEAD`). Install the complete public-path regression suite that proves branch-local artifacts stay excluded through the full dispatch path and verifies both branches of the `create_pr` gate. Replace the Principle-14-violating private-method tests in `test_enforcement_runner_c3.py`.

**Why This Cycle Exists Now:** This is the final proof cycle. It requires the full note flow (C3), migrated exception paths (C4), and clean config injection (C5) to be in place so the integration tests exercise a fully correct runtime state. The `create_pr` proxy correction is blocked until C3 establishes the `NoteContext` threading that allows `_handle_check_merge_readiness` to write `RecoveryNote` on error.

**Design Refs:** §3.9 (`_has_net_diff_for_path`, corrected proxy, relationship to §3.8 postcondition, `base` parameter source), §3.14 (test targets table, Principle 14 enforcement).

**Research Refs:** `_git_is_tracked` tests HEAD tree not net delta — false positive confirmed. Principle 14 debt: `test_enforcement_runner_c3.py` calls `_handle_exclude_branch_local_artifacts` directly — exactly the pattern ARCHITECTURE_PRINCIPLES §14 forbids.

**Files or Modules Likely Touched:**
- `mcp_server/managers/enforcement_runner.py` — `_handle_check_merge_readiness`: replace `_git_is_tracked` with `_has_net_diff_for_path`; keep `context` (not discarded); add `_has_net_diff_for_path` helper
- `tests/mcp_server/unit/managers/test_enforcement_runner_c3.py` — replace private-method call patterns with public-path assertions
- `tests/mcp_server/integration/test_git_add_commit_regression_c6.py` — new: full ready-phase dispatch regression suite
- `tests/mcp_server/integration/test_create_pr_merge_readiness_c6.py` — new: clean branch / contaminated branch gate tests

**RED:**
- `test_create_pr_not_blocked_on_clean_branch` — currently `_git_is_tracked` may produce false positive against a clean branch
- `test_create_pr_blocked_on_contaminated_branch` — branch with artifact directly committed must be blocked
- `test_git_add_commit_full_dispatch_no_delta` — full server dispatch: `git_add_or_commit` ready-phase → no delta for `.st3/state.json` in resulting commit
- `test_git_add_commit_full_dispatch_explicit_files_no_delta` — same with `files=` param
- `test_git_add_commit_rendered_response_includes_exclusion` — full dispatch → response TextContent contains exclusion message
- `test_enforcement_runner_private_method_access_absent` — current `test_enforcement_runner_c3.py` calls `_handle_exclude_branch_local_artifacts` directly — must be removed

**GREEN:**
- Add `_has_net_diff_for_path(workspace_root, path, base)` helper to `enforcement_runner.py`
- Update `_handle_check_merge_readiness`: `del action` only (keep `context`); read `base = str(context.get_param("base"))`; replace `_git_is_tracked` check with `_has_net_diff_for_path`; on `ExecutionError`, write `RecoveryNote` before re-raise
- Rewrite `test_enforcement_runner_c3.py` to call `EnforcementRunner.run()` (public API) and assert via `context.of_type(ExclusionNote)` at unit boundary; remove all private-method calls
- Write integration test suite: real git repo; commit with `skip_paths` active; verify no delta; verify rendered response; both `create_pr` gate branches

**REFACTOR:**
- Verify `_has_net_diff_for_path` raises `ExecutionError` (not returns `False`) on non-zero git exit code
- Confirm no hard-coded branch names in `_handle_check_merge_readiness`
- Confirm `context` is NOT discarded in `_handle_check_merge_readiness` (previous `del action, context` removed)
- Run full test suite: `pytest tests/mcp_server/` → all pass

**Deliverables For This Cycle:**
1. `_has_net_diff_for_path` helper in `enforcement_runner.py`: uses `git diff --name-only merge_base..HEAD -- path`; raises `ExecutionError` on non-zero exit codes
2. `_handle_check_merge_readiness` uses `_has_net_diff_for_path`; `context` not discarded; `base` read from tool params
3. Integration test: full `git_add_or_commit` ready-phase dispatch → no delta for `.st3/state.json` in commit diff
4. Integration test: full `git_add_or_commit` ready-phase dispatch → rendered TextContent block contains `"Excluded from commit index: .st3/state.json"`
5. Integration test: `create_pr` with clean branch (artifact never committed) → not blocked
6. Integration test: `create_pr` with artifact directly committed → blocked; response contains contamination error
7. `test_enforcement_runner_c3.py` private-method call patterns replaced; public `run()` API used exclusively

**Exit Criteria:**
- `test_git_add_commit_regression_c6.py` all pass (real git integration)
- `test_create_pr_merge_readiness_c6.py` both branches pass (real git integration)
- `test_enforcement_runner_c3.py` zero references to private methods (`_handle_exclude_branch_local_artifacts`, `_merge_readiness_context`)
- Full suite `pytest tests/mcp_server/` → 0 failures, 0 errors
- All three structural tests GREEN

**Gate Proof:** `pytest tests/mcp_server/ -v` → all pass; `grep -r "_handle_exclude_branch_local_artifacts" tests/` → 0 matches

**Dependencies:** C3 (full NoteContext dispatch wiring), C4 (exception migration; `context` available in `_handle_check_merge_readiness`), C5 (config injection closed; `GitManager` wired correctly)

---

## 8. Deliverables.json Draft

**Migration Note:** Issue 283 already has `planning_deliverables` in `.st3/deliverables.json` (5-cycle plan from 2026-04-09). The `save_planning_deliverables` guard raises `ValueError` if the key is already present. Before calling `save_planning_deliverables(283, <payload>)`, manually remove the `"planning_deliverables"` key from the `"283"` entry in `.st3/deliverables.json`. The old 5-cycle plan is superseded by this 6-cycle replan.

```json
{
  "tdd_cycles": {
    "total": 6,
    "cycles": [
      {
        "cycle_number": 1,
        "deliverables": [
          {
            "id": "C1.1",
            "description": "mcp_server/core/operation_notes.py exists with all six NoteEntry variants, NoteEntry union, Renderable protocol, and NoteContext",
            "validates": {
              "type": "file_exists",
              "file": "mcp_server/core/operation_notes.py"
            }
          },
          {
            "id": "C1.2",
            "description": "NoteContext.render_to_response returns base unchanged when no Renderable entries present",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/unit/core/test_note_context_unit.py",
              "text": "test_render_empty_returns_base_unchanged"
            }
          },
          {
            "id": "C1.3",
            "description": "NoteContext.render_to_response appends TextContent block with all Renderable entries in insertion order",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/unit/core/test_note_context_unit.py",
              "text": "test_render_renderable_appends_text_content"
            }
          },
          {
            "id": "C1.4",
            "description": "Structural test test_no_raw_st3_config_paths_in_production committed to test_c_loader_structural.py",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/unit/config/test_c_loader_structural.py",
              "text": "test_no_raw_st3_config_paths_in_production"
            }
          },
          {
            "id": "C1.5",
            "description": "Structural test test_no_hints_kwarg_on_mcp_error_callsites committed to test_c_loader_structural.py",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/unit/config/test_c_loader_structural.py",
              "text": "test_no_hints_kwarg_on_mcp_error_callsites"
            }
          },
          {
            "id": "C1.6",
            "description": "Structural test test_no_blockers_or_recovery_kwargs_on_exception_callsites committed to test_c_loader_structural.py",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/unit/config/test_c_loader_structural.py",
              "text": "test_no_blockers_or_recovery_kwargs_on_exception_callsites"
            }
          },
          {
            "id": "C1.7",
            "description": "CommitNote has no to_message() method: render_to_response with only CommitNote returns base unchanged",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/unit/core/test_note_context_unit.py",
              "text": "test_commit_note_not_renderable"
            }
          }
        ],
        "exit_criteria": "pytest tests/mcp_server/unit/core/test_note_context_unit.py → all pass; test_c_loader_structural.py importable; Pyright clean on operation_notes.py"
      },
      {
        "cycle_number": 2,
        "deliverables": [
          {
            "id": "C2.1",
            "description": "GitAdapter.commit() accepts skip_paths: frozenset[str] parameter with postcondition",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/adapters/git_adapter.py",
              "text": "skip_paths: frozenset[str]"
            }
          },
          {
            "id": "C2.2",
            "description": "GitAdapter.commit() calls git restore --staged for each path in skip_paths after all staging",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/adapters/git_adapter.py",
              "text": "restore"
            }
          },
          {
            "id": "C2.3",
            "description": "GitManager.commit_with_scope() accepts and forwards skip_paths parameter",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/managers/git_manager.py",
              "text": "skip_paths: frozenset[str]"
            }
          },
          {
            "id": "C2.4",
            "description": "Unit test: skip_paths path absent from commit diff when files=None (stage-all route)",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/unit/adapters/test_git_adapter_skip_paths.py",
              "text": "test_commit_with_skip_paths_files_none_no_delta"
            }
          },
          {
            "id": "C2.5",
            "description": "Unit test: skip_paths path absent from commit diff when explicit files= list supplied",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/unit/adapters/test_git_adapter_skip_paths.py",
              "text": "test_commit_with_skip_paths_explicit_files_no_delta"
            }
          }
        ],
        "exit_criteria": "pytest tests/mcp_server/unit/adapters/test_git_adapter_skip_paths.py → all pass"
      },
      {
        "cycle_number": 3,
        "deliverables": [
          {
            "id": "C3.1",
            "description": "EnforcementRunner.run() return type is None; no git rm --cached calls in body",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/managers/enforcement_runner.py",
              "text": "git rm"
            }
          },
          {
            "id": "C3.2",
            "description": "EnforcementRunner.run() writes ExclusionNote to note_context for each excluded file",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/managers/enforcement_runner.py",
              "text": "ExclusionNote"
            }
          },
          {
            "id": "C3.3",
            "description": "BaseTool.execute abstract method signature includes context: NoteContext parameter",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/tools/base.py",
              "text": "context: NoteContext"
            }
          },
          {
            "id": "C3.4",
            "description": "GitCommitTool.execute reads ExclusionNote entries and passes skip_paths to commit_with_scope",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/tools/git_tools.py",
              "text": "of_type(ExclusionNote)"
            }
          },
          {
            "id": "C3.5",
            "description": "MCPServer.handle_call_tool calls context.render_to_response unconditionally on success and error paths",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/server.py",
              "text": "render_to_response"
            }
          },
          {
            "id": "C3.6",
            "description": "Integration test: full git_add_or_commit ready-phase dispatch produces zero delta on .st3/state.json in commit diff AND rendered response contains exclusion message",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/integration/test_git_add_commit_ready_phase_c3.py",
              "text": "test_ready_phase_commit_excludes_state_json"
            }
          }
        ],
        "exit_criteria": "pytest tests/mcp_server/unit/managers/test_enforcement_runner_unit.py tests/mcp_server/integration/test_git_add_commit_ready_phase_c3.py → all pass; _augment_text_with_error_metadata absent from server.py"
      },
      {
        "cycle_number": 4,
        "deliverables": [
          {
            "id": "C4.1",
            "description": "MCPError.hints field absent from exceptions.py",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/core/exceptions.py",
              "text": "hints: list"
            }
          },
          {
            "id": "C4.2",
            "description": "ToolResult.hints field absent from tool_result.py",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/tools/tool_result.py",
              "text": "hints"
            }
          },
          {
            "id": "C4.3",
            "description": "tool_error_handler contains no hints variable or exc.hints reference",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/core/error_handling.py",
              "text": "hints"
            }
          },
          {
            "id": "C4.4",
            "description": "hints= kwarg absent from mcp_server/tools/git_tools.py (structural test test_no_hints_kwarg_on_mcp_error_callsites GREEN)",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/tools/git_tools.py",
              "text": "hints="
            }
          },
          {
            "id": "C4.5",
            "description": "blockers= kwarg absent from mcp_server/tools/git_tools.py (structural test test_no_blockers_or_recovery_kwargs_on_exception_callsites GREEN)",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/tools/git_tools.py",
              "text": "blockers="
            }
          },
          {
            "id": "C4.6",
            "description": "Integration test: BlockerNote written at raise-site renders as TextContent block in dispatch response",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/integration/test_blocker_recovery_note_dispatch.py",
              "text": "test_blocker_note_rendered_in_dispatch"
            }
          }
        ],
        "exit_criteria": "pytest tests/mcp_server/unit/config/test_c_loader_structural.py → test_no_hints_kwarg and test_no_blockers_or_recovery both GREEN; pytest tests/mcp_server/unit/core/test_tool_error_handler_c4.py → all pass"
      },
      {
        "cycle_number": 5,
        "deliverables": [
          {
            "id": "C5.1",
            "description": "ScopeDecoder.__init__ accepts workphases_config: WorkphasesConfig; workphases_path: Path constructor param absent",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/core/phase_detection.py",
              "text": "workphases_path: Path"
            }
          },
          {
            "id": "C5.2",
            "description": "GitManager.__init__ accepts workphases_config: WorkphasesConfig; commit_with_scope performs no file I/O",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/managers/git_manager.py",
              "text": "workphases_path"
            }
          },
          {
            "id": "C5.3",
            "description": "PhaseDetection.__init__ CWD-sensitive fallback Path('.st3/config/workphases.yaml') absent",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/core/phase_detection.py",
              "text": ".st3/config/workphases.yaml"
            }
          },
          {
            "id": "C5.4",
            "description": "PhaseStateEngine file-existence check absent; operates on injected WorkphasesConfig",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/managers/phase_state_engine.py",
              "text": "workphases_path"
            }
          },
          {
            "id": "C5.5",
            "description": "server.py both ScopeDecoder callsites use workphases_config= kwarg",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/server.py",
              "text": "ScopeDecoder(workphases_config="
            }
          },
          {
            "id": "C5.6",
            "description": "Hard-coded .st3/config/workphases.yaml absent from phase_detection.py (structural test test_no_raw_st3_config_paths_in_production GREEN)",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/core/phase_detection.py",
              "text": ".st3/config/workphases.yaml"
            }
          }
        ],
        "exit_criteria": "pytest tests/mcp_server/unit/config/test_c_loader_structural.py::test_no_raw_st3_config_paths_in_production → GREEN; unit test commit_with_scope executes without open() call → pass"
      },
      {
        "cycle_number": 6,
        "deliverables": [
          {
            "id": "C6.1",
            "description": "_has_net_diff_for_path helper in enforcement_runner.py uses git diff --name-only merge_base..HEAD",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/managers/enforcement_runner.py",
              "text": "_has_net_diff_for_path"
            }
          },
          {
            "id": "C6.2",
            "description": "_handle_check_merge_readiness does not reference _git_is_tracked",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/managers/enforcement_runner.py",
              "text": "_git_is_tracked"
            }
          },
          {
            "id": "C6.3",
            "description": "Integration test: full git_add_or_commit ready-phase dispatch → no delta for .st3/state.json AND rendered exclusion message",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/integration/test_git_add_commit_regression_c6.py",
              "text": "test_ready_phase_full_dispatch_no_delta_rendered_exclusion"
            }
          },
          {
            "id": "C6.4",
            "description": "Integration test: create_pr with clean branch (artifact never committed) → not blocked",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/integration/test_create_pr_merge_readiness_c6.py",
              "text": "test_create_pr_not_blocked_on_clean_branch"
            }
          },
          {
            "id": "C6.5",
            "description": "Integration test: create_pr with artifact directly committed → blocked; response contains contamination error",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/integration/test_create_pr_merge_readiness_c6.py",
              "text": "test_create_pr_blocked_on_contaminated_branch"
            }
          },
          {
            "id": "C6.6",
            "description": "test_enforcement_runner_c3.py contains zero direct calls to _handle_exclude_branch_local_artifacts",
            "validates": {
              "type": "absent_text",
              "file": "tests/mcp_server/unit/managers/test_enforcement_runner_c3.py",
              "text": "_handle_exclude_branch_local_artifacts"
            }
          },
          {
            "id": "C6.7",
            "description": "_augment_text_with_error_metadata absent from server.py; full test suite pytest tests/mcp_server/ → 0 failures, 0 errors",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/server.py",
              "text": "_augment_text_with_error_metadata"
            }
          }
        ],
        "exit_criteria": "pytest tests/mcp_server/ → 0 failures, 0 errors; all three structural tests GREEN; grep -r '_handle_exclude_branch_local_artifacts' tests/ → 0 matches"
      }
    ]
  }
}
```

---

## 9. Cycle Gate Rules

**Rule G-1: Sequential Cycle Completion**
No cycle may begin implementation until all exit criteria of the previous cycle are met. C4 and C5 may run in parallel only after C3 is fully green; sequential is recommended to avoid `server.py` conflicts.

**Rule G-2: Structural Tests Are Non-Negotiable**
The three structural tests in `test_c_loader_structural.py` (installed in C1) must be GREEN by the end of C5. Any cycle that introduces a new `.st3/config/` path literal, a `hints=` kwarg, or a `blockers=`/`recovery=` kwarg is a false GO.

**Rule G-3: Flag-Day Means Flag-Day**
C4 is a flag-day cycle. No `hints=`, `blockers=`, or `recovery=` kwargs may remain in any `mcp_server/` module after C4 GREEN. A cycle exit with residual old-pattern calls is a cycle failure.

**Rule G-4: No Private-Method Tests After C6**
After C6, `test_enforcement_runner_c3.py` must contain zero calls to private enforcement methods. Principle 14 compliance is mandatory at the validation gate.

**Rule G-5: Integration Tests Use Real Git**
Integration tests in C3, C4, and C6 must exercise a real git repository (not mocked). `skip_paths` zero-delta guarantee can only be verified against a real `commit.diff()`.

**Rule G-6: Pyright Clean Per Cycle**
Every cycle exit must be Pyright-clean on all modified modules. Type errors are cycle-blockers.

---

## 10. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Missed raise-site in C4's 26-site sweep | Medium | flag-day check fails | C1 structural test `test_no_hints_kwarg_on_mcp_error_callsites` provides mechanical sweep verification; Pyright raises `TypeError` at construction sites |
| `BaseTool.execute()` signature change misses a tool implementation | Medium | RuntimeError on tool dispatch | Abstract base raises `TypeError` at subclass definition time; Pyright catch missing `context` arg |
| `PhaseStateEngine` file-existence check removal breaks edge case | Low | ConfigError on startup | Unit test: `PhaseStateEngine` initializes correctly with `WorkphasesConfig` that has empty phase list; integration: server startup test passes |
| `server.py` `ScopeDecoder` wiring uses wrong config object | Low | ScopeDecoder sees wrong phases | Unit test: `ScopeDecoder` initialized with known `WorkphasesConfig` resolves expected phase names |
| `_has_net_diff_for_path` returns `False` on non-zero git exit code instead of raising | High if not caught | Silently passes contaminated branches | Design explicitly specifies `ExecutionError` on non-zero; unit test confirms `_run_git_command` non-zero → exception, never `False` |
| `CommitNote` accidentally made `Renderable` | Low | Duplicate commit hash in response | Unit test: `render_to_response` with only `CommitNote` returns base unchanged; `CommitNote` has no `to_message()` method |
| `context` discarded in `_handle_check_merge_readiness` (regression to `del action, context`) | Low | `RecoveryNote` can't be written on `ExecutionError` | C6 RED test: `_handle_check_merge_readiness` with `ExecutionError` → response contains `RecoveryNote` message |

---

## 11. Planning Readiness Check

| Item | Status |
|------|--------|
| Design v11.0 QA GO | ✅ |
| Research v1.5 QA GO | ✅ |
| All research expected-results mapped to cycles | ✅ |
| Every cycle has RED/GREEN/REFACTOR | ✅ |
| Every cycle has named gate proof | ✅ |
| Every cycle has concrete deliverables | ✅ |
| No cycle depends on a later cycle's contract | ✅ |
| Deliverables.json draft complete | ✅ |
| Principle 14 compliance verified (public-path tests in C6) | ✅ |
| Flag-day migration ordering safe (C3 threads context before C4 migration) | ✅ |
| Config-boundary closure accounts for all 5 callsites | ✅ |
| Structural guards cover all three flag-day invariants | ✅ |
| No private-helper testing planned as acceptable coverage | ✅ |
| No obsolete assumptions (execute() changes confirmed; git_add_or_commit is HIT tool id; net-delta proxy confirmed) | ✅ |

---

## 12. Related Documentation

- [docs/development/issue283/design-git-add-commit-regression-fix.md](design-git-add-commit-regression-fix.md) — PRIMARY design authority (v11.0)
- [docs/development/issue283/research-git-add-or-commit-regression.md](research-git-add-or-commit-regression.md) — Research baseline (v1.5)
- [docs/development/issue283/design-ready-phase-enforcement.md](design-ready-phase-enforcement.md) — Sibling design (enforcement_event wiring context)
- [docs/development/issue257/planning.md](../../issue257/planning.md) — ConfigLoader / WorkphasesConfig injection precedent
- [docs/coding_standards/ARCHITECTURE_PRINCIPLES.md](../../../coding_standards/ARCHITECTURE_PRINCIPLES.md) — Principle 14, Config-First, SRP
- [mcp_server/core/exceptions.py](../../../../mcp_server/core/exceptions.py) — Current MCPError hierarchy (hints to be removed)
- [mcp_server/tools/tool_result.py](../../../../mcp_server/tools/tool_result.py) — Current ToolResult contract (hints to be removed)
- [mcp_server/core/error_handling.py](../../../../mcp_server/core/error_handling.py) — tool_error_handler (decorator migration in C4)
- [mcp_server/managers/enforcement_runner.py](../../../../mcp_server/managers/enforcement_runner.py) — EnforcementRunner (declarative rewrite in C3)
- [mcp_server/adapters/git_adapter.py](../../../../mcp_server/adapters/git_adapter.py) — GitAdapter (skip_paths postcondition in C2)
- [tests/mcp_server/unit/managers/test_enforcement_runner_c3.py](../../../../tests/mcp_server/unit/managers/test_enforcement_runner_c3.py) — Principle-14-violating tests (replaced in C6)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-13 | Agent | Initial planning document — 6 cycles, full deliverables.json draft, coverage map, dependency analysis |
