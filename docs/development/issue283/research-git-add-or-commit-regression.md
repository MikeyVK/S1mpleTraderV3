<!-- docs\development\issue283\research-git-add-or-commit-regression.md -->
<!-- template=research version=8b7bb3ab created=2026-04-10T16:26Z updated=2026-04-11 -->
# Research — git_add_or_commit branch-local artifact regression (Issue #283)

**Status:** DRAFT  
**Version:** 1.5  
**Last Updated:** 2026-04-11

---

## Purpose

Capture the current observed behavior and verified findings around git_add_or_commit before designing a durable fix. This document is intentionally limited to research and problem framing.

## Scope

**In Scope:**
Observed runtime behavior of git_add_or_commit in ready phase; interaction between pre-enforcement and commit execution; user-visible response semantics; current test coverage boundaries; architecture-boundary findings related to issue #257 ConfigLoader wiring; verified Git evidence from the active branch; **closure of the five remaining config-root hardcoding violations** (`workphases.yaml` callsites in `ScopeDecoder`, `GitManager`, `PhaseDetection`, `PhaseStateEngine`, and `server.py`).

**Out of Scope:**
Implementation proposal, patch shape, API redesign, commit message formatting changes unrelated to the defect, and any workaround that edits state directly instead of using workflow tools.

**Flag-day constraint (binding, non-negotiable):**

The fix resulting from this research is a **breaking refactor**. No backward compatibility is required and no legacy interfaces shall be preserved. The sole binding architectural constraint at research level is: no callsite in production code may accept raw `Path` objects for YAML configuration after the composition root — this is already closed by the Config-First / DI principles in `ARCHITECTURE_PRINCIPLES.md`. Transitional shims and deprecated overloads are forbidden. All other clean-cut requirements (note contract shape, staging semantics) are design-phase decisions and must not be pre-empted here.

## Prerequisites

Read these first:
1. Issue #283 context and current branch state
2. Existing issue-283 research and design documents
3. Recent runtime verification of create_pr and git_add_or_commit behavior
4. Issue #257 ConfigLoader / constructor-injection design history

---

## Problem Statement

Issue #283 aims to prevent branch-local artifacts from contaminating main. The create_pr guard now blocks correctly, but the preceding git_add_or_commit path still behaves inconsistently: branch-local artifacts can be uncached during pre-enforcement yet still end up tracked or even included again in the resulting commit, while the tool response reports only a generic commit success message. This leaves both repository hygiene and operator feedback unreliable at the exact point where the workflow expects ready-phase preparation to be safe and explicit.

## Research Goals

- Confirm the exact interaction between ready-phase pre-enforcement and the subsequent commit execution path.
- Document why branch-local artifacts can still remain tracked or re-enter the commit path after pre-enforcement.
- Record what the user currently sees in the commit tool response and why that is insufficient for non-silent behavior.
- Identify the current test coverage gap between enforcement-only tests and the full server dispatch plus commit execution path.
- Audit whether the issue-257 config-root boundary is still respected in the current runtime, especially inside the issue-283 path.
- Prepare a clean factual basis for joint design of a durable fix without relying on short cuts or masking behavior.

---

## Background

The active branch refactor/283-ready-phase-enforcement already fixed the create_pr pre-enforcement path so blocked PR creation returns a proper validation response instead of hanging. After that fix, a ready-phase git_add_or_commit run was expected to remove .st3/state.json and .st3/deliverables.json from the commit index before creating a PR-preparation commit. Inspection of the resulting HEAD commit showed that .st3/state.json still appeared in the commit diff and .st3/deliverables.json remained tracked in the repository tree, which triggered a deeper review of the commit path and response semantics.

Issue #257 is also directly relevant. Its planning and research documents establish ConfigLoader plus constructor injection as the normative boundary for YAML-backed configuration: resolve the config root once at the composition root, load typed config objects once, and stop allowing downstream runtime classes to rediscover `.st3/config/...` for themselves.

---

## Findings

### Verified runtime behavior

- A live create_pr call now returns a direct validation error when branch-local artifacts remain tracked, which confirms the create_pr pre-enforcement path is functioning as intended.
- Inspection of the current HEAD commit showed that `.st3/state.json` was still part of the latest ready-phase commit diff.
- Inspection of the HEAD tree also showed that both `.st3/state.json` and `.st3/deliverables.json` remain tracked in the repository.

### Architecture interaction map

The current ready-phase commit path is not a single cohesive operation. It is a chain of four components whose responsibilities only partially line up:

1. `MCPServer.handle_call_tool(...)` runs pre-enforcement via `_run_tool_enforcement(...)` before dispatching the actual tool.
2. `EnforcementRunner.run(...)` executes `exclude_branch_local_artifacts`, mutates the git index with `git rm --cached`, and returns human-readable success notes.
3. `GitCommitTool.execute(...)` delegates to `GitManager.commit_with_scope(...)` and returns only `Committed: <hash>`.
4. `GitAdapter.commit(...)` stages all changes with `git add .` when `files=None`, which can re-stage files that enforcement just uncached.

This yields two separate interaction defects:

- The server discards successful enforcement notes by returning `None` on success from `_run_tool_enforcement(...)`.
- The adapter re-stages the entire working tree after pre-enforcement has intentionally removed branch-local artifacts from the index.

```mermaid
flowchart TD
    A[User calls git_add_or_commit] --> B[MCPServer.handle_call_tool]
    B --> C[Pre-enforcement via _run_tool_enforcement]
    C --> D[EnforcementRunner.run]
    D --> E[exclude_branch_local_artifacts]
    E --> F[git rm --cached on branch-local artifacts]
    E -. success notes .-> D
    D -. notes returned .-> C
    C -. notes dropped on success .-> B
    B --> G[GitCommitTool.execute]
    G --> H[GitManager.commit_with_scope]
    H --> I[GitAdapter.commit]
    I --> J[git add . when files=None]
    J --> K[Previously uncached artifacts can be re-staged]
    K --> L[Commit created]
```

### Commit-path findings

- The ready-phase pre-enforcement handler in `mcp_server/managers/enforcement_runner.py` does produce a note stating that branch-local artifacts were excluded from the commit index.
- The server currently treats those notes as side information and does not propagate them into the final git_add_or_commit response.
- The downstream commit path in `mcp_server/adapters/git_adapter.py` stages all changes with `git add .` when `files=None`.
- That means a successful pre-enforcement uncache can be undone later in the same tool invocation when the commit executes the default stage-all path.
- The current behavior is therefore not a pure enforcement failure; it is an interaction defect between pre-enforcement, response assembly, and commit execution semantics.

### Design/runtime gap inside issue #283

Issue #283's design is strongly config-first, but its implementation boundary was drawn around enforcement hooks rather than around the full commit transaction.

- The issue-283 design and planning documents correctly route new policy through `workphases.yaml`, `phase_contracts.yaml`, `enforcement.yaml`, `ConfigLoader`, and server-level composition.
- The same design explicitly treated `GitCommitTool` as an enforcement-event declaration only, with no planned change to `execute()`.
- That assumption is safe only if the downstream commit path preserves the index state created by pre-enforcement.
- In the actual runtime, `GitAdapter.commit(files=None)` performs a fresh stage-all operation, so the enforcement-only design boundary was too narrow for the real behavior.

This is important because it means issue #283 did not fail due to a missing rule. It failed because the abstraction boundary stopped at enforcement, while the observable behavior depends on the later commit implementation as well.

### Response/UX findings

- The server now preserves error semantics for blocked enforcement paths such as create_pr, which fixed the original hang.
- The success path is still asymmetric: successful enforcement notes are generated, but the user never sees them.
- The git commit tool itself returns only `Committed: <hash>` on success.
- As a result, even when the tool performs non-trivial index mutation before commit, the user does not receive an explicit success message that files were uncached.
- This creates silent success for behavior that is workflow-critical and operationally significant.

### Config-root boundary audit

Issue #257 established a clear rule: YAML-backed configuration should be resolved once via `ConfigLoader(config_root)` at the composition root and injected downward. The current runtime only partially follows that rule.

**What is still correct:**

- `mcp_server/server.py` resolves `config_root` through `resolve_config_root(...)`.
- `mcp_server/server.py` constructs `ConfigLoader(config_root=config_root)` and loads typed config objects there.
- Issue #283's new configuration data is loaded through that path: `workphases.yaml`, `phase_contracts.yaml`, and `enforcement.yaml` all enter the runtime via `ConfigLoader`.
- `PhaseContractResolver` and `MergeReadinessContext` are then built from typed config objects, which is consistent with issue #257's intended boundary.

**What still violates the boundary in active runtime code:**

Five callsites in production code bypass `ConfigLoader` and reconstruct `.st3/config/...` paths directly. All five involve the same file: `workphases.yaml`.

| # | File | Line | Nature |
|---|------|------|--------|
| 1 | `mcp_server/server.py` | 211 | `ScopeDecoder(workphases_path=workspace_root / ".st3" / "config" / "workphases.yaml")` for `StateReconstructor` |
| 2 | `mcp_server/server.py` | 222 | Identical for `PhaseStateEngine` internal `scope_decoder` |
| 3 | `mcp_server/core/phase_detection.py` | 85 | `self.workphases_path = workphases_path or Path(".st3/config/workphases.yaml")` — CWD-sensitive fallback |
| 4 | `mcp_server/managers/phase_state_engine.py` | 91 | Checks file existence to decide whether to relax an already-injected `WorkphasesConfig` object |
| 5 | `mcp_server/managers/git_manager.py` | 26 | Default `_workphases_path`; re-opened as raw YAML inside `commit_with_scope(...)` |

All other `.st3/config` strings in production are display-only constants in `ConfigError.file_path` (`_ENFORCEMENT_DISPLAY_PATH`, `_PHASE_CONTRACTS_DISPLAY_PATH`). These do not open files, but they still violate the total-ban policy established in the regression fix design: in implementation they will be replaced with a generic `{configRoot}/filename` form (e.g. `{configRoot}/enforcement.yaml`). Additionally, `_WORKPHASES_DISPLAY_PATH` in `phase_contract_resolver.py` is dead code — defined but never referenced anywhere — and will be removed without replacement.

The root cause in all five cases is the same: `ScopeDecoder` and `GitManager` still accept a `workphases_path: Path` in their constructor instead of a typed `WorkphasesConfig` object. Replacing that interface eliminates all five violations simultaneously.

**What is not a config-root violation:**

- Direct access to `.st3/state.json` and `.st3/deliverables.json` is not, by itself, evidence of a config-boundary problem. Those files are runtime state and registry artifacts, not YAML configuration sources.

**Conclusion of the audit:**

- The issue-257 boundary is not fully respected in the current post-257 runtime.
- Issue #283 itself partially respects that boundary: its new policy inputs are config-driven and loaded through `ConfigLoader`, which is good.
- Issue #283 also still runs through downstream consumers that directly reconstruct `.st3/config/...` paths, which means the architecture remains mixed at execution time.
- The current defect therefore sits at the intersection of two debts: interaction debt in the commit path, and remaining config-boundary debt in downstream consumers.

### Config-root hardcoding — expected result (in scope for issue #283)

**Finding summary:** Five production callsites reconstruct `.st3/config/workphases.yaml` as a raw `Path` instead of consuming an already-loaded `WorkphasesConfig` object. This is the only remaining category of config-root hardcoding in production code.

**Expected result when resolved:**

- `ScopeDecoder.__init__` accepts `workphases_config: WorkphasesConfig` instead of `workphases_path: Path`.
- `GitManager.__init__` accepts `workphases_config: WorkphasesConfig` instead of `workphases_path: Path`; `commit_with_scope(...)` no longer opens any file.
- `PhaseStateEngine.__init__` removes the file-existence check at line 91; config-relaxation logic operates on the already-injected config object.
- `server.py` wires `ScopeDecoder(workphases_config=workphases_config)` at both construction sites.
- A structural test (`tests/mcp_server/unit/config/test_c_loader_structural.py`) fails on any future re-introduction of direct `.st3/config/` path construction in production code, acting as a mechanical guardrail.

### Architecture-principles assessment

Against `ARCHITECTURE_PRINCIPLES.md`, the strongest confirmed tensions are:

- **SRP / cohesive boundaries:** enforcement, success messaging, and final staging behavior are split across existing layers (server, runner, tool, adapter). Each layer has its own responsibility; the defect is not that no single class owns everything, but that the **contract between layers is broken** — pre-enforcement mutates the index under an implicit assumption that downstream stages will preserve that state. No layer communicates this invariant explicitly.
- **Config-First / constructor injection:** server startup follows the issue-257 pattern, but downstream consumers still rediscover `.st3/config/...` instead of consuming injected config state. The architecture principles close this question: raw config paths must not cross injection boundaries after the composition root.
- **Fail-Fast:** blocked enforcement now fails fast correctly for create_pr, but successful enforcement still degrades into silent behavior later in the call chain.
- **Explicit over implicit:** the user-visible success response hides the fact that the tool is mutating the index before commit. The implicit assumption that stage-all is safe post-enforcement is the architectural root of the regression.
- **Test via Public API (Principle 14):** the runner is tested, but those tests access private methods directly. The full public-path interaction is not yet locked down — and the existing private-method tests provide a false sense of coverage.

### Test-coverage findings

- Existing enforcement tests validate `EnforcementRunner.run(...)` and the exclusion note format in isolation.
- There is a real-git enforcement test that proves the runner can remove an artifact from the index before commit.
- There is not yet a server-level or end-to-end test that proves `git_add_or_commit` preserves that exclusion through the subsequent stage-and-commit path and surfaces the exclusion note in the final response.
- This leaves the most important defect boundary under-tested: the full dispatch path from pre-enforcement into commit execution and final user-visible output.

**Principle 14 (Test via Public API) debt — explicit finding:**

The existing unit tests in `tests/mcp_server/unit/managers/test_enforcement_runner_c3.py` violate Principle 14 by calling private methods and accessing internal state directly (e.g. `_handle_exclude_branch_local_artifacts`, `_merge_readiness_context`). This is not a minor gap — it is the exact antipattern that `ARCHITECTURE_PRINCIPLES.md` Principle 14 forbids. The consequence is that those tests are structurally coupled to implementation details and provide no protection against behavioral regressions in the public dispatch path. Design must treat the existing test coverage as partially invalid and must require replacement tests that only call public API surfaces.

### Success-notes problem statement

The research surfaced a concrete transparency defect: enforcement produces operationally significant output, but that output is discarded before reaching the user.

**The observable problem:**

- `EnforcementRunner.run(...)` returns a `list[str]` describing what it did (e.g. files excluded from the index).
- `MCPServer._run_tool_enforcement(...)` receives this list but returns `None` on success, dropping all notes.
- The user sees only `Committed: <hash>` — no indication that branch-local artifacts were uncached.

**Why `list[str]` is structurally insufficient as a contract:**

A `list[str]` cannot be validated in tests without string parsing. No test can assert that `.st3/state.json` was specifically excluded without inspecting message content, binding the test to the exact wording of the note. This is implicit coupling between producer and consumer through untyped text rather than a machine-readable contract.

**Existing contract to evaluate first:**

`ToolResult` in `mcp_server/tools/tool_result.py` already has a `hints: list[str] | None` field as a secondary output channel. Before introducing any new contract type, design must evaluate whether `ToolResult.hints` can carry enforcement notes with the necessary semantics. Only if `ToolResult` demonstrably cannot carry the required structure (e.g. because notes need to be machine-inspectable per-entry) may a richer contract be introduced — and even then, that is strictly a design decision, not a research conclusion.

**Research boundary:**

This section records the problem only. What typed structure enforcement notes should have, whether `ToolResult.hints` suffices, and who assembles the final response are design decisions to be made in the design phase with full visibility of the existing contracts.

## Conclusions

1. The ready-phase regression is an interaction failure, not merely a missing rule in enforcement configuration.
2. The defect is a **contract breach between existing layers**, not the absence of a single central owner. Each layer (server, runner, tool, adapter) already has a defined responsibility; the failure is that no layer explicitly communicates the invariant "index state after enforcement must be preserved through commit execution". Design must harden this inter-layer contract, not replace the layer structure.
3. The runtime contains five active downstream `.st3/config/...` path dependencies that violate the issue-257 config-root boundary. Closing these is **in scope for issue #283** and is a non-negotiable part of the flag-day refactor.
4. Any durable fix needs to address both correctness and visibility: excluded files must stay excluded, and the user must be told explicitly what the tool did.
5. The next design step should be based on full-path ownership and tests, not on another isolated enforcement-only patch.

## Architecture Constraints (binding, answered by existing principles)

The following questions were raised during research but are **already answered** by `ARCHITECTURE_PRINCIPLES.md` and issue #257. They are not open for reconsideration in design; they are constraints.

- **Phase-aware consumers must receive typed config objects, not raw `Path` values.** Constructor injection is the normative pattern (Config-First / DI principles). `ScopeDecoder`, `GitManager`, and `PhaseStateEngine` accepting `workphases_path: Path` is a violation, not a design choice. This also applies after the flag-day refactor: no production callsite may reconstruct `.st3/config/...` paths independently of the composition root.
- **The five hardcoded `workphases.yaml` callsites (server.py:211, server.py:222, phase_detection.py:85, phase_state_engine.py:91, git_manager.py:26) must be eliminated as part of this issue.** The root cause is a `Path`-accepting interface — replacing that interface eliminates all five simultaneously. These violations are explicitly in scope for issue #283 and must not remain in the codebase when this issue closes.

## Open Questions

- Should ready-phase commit execution preserve the post-enforcement index state rather than re-stage the entire working tree when `files=None`?
- Which layer should own the explicit inter-layer contract for index-state preservation: should the server enforce it via pre-conditions, or should the adapter/manager expose a targeted staging API that makes stage-all the non-default?
- Should successful enforcement notes be surfaced via `ToolResult.hints` or does the use case require a richer per-entry structure — and if so, what is the minimum machine-readable shape that avoids duplicating `ToolResult`?
- What full-path regression tests are required to guarantee that branch-local artifacts stay out of ready-phase commits and that the user receives a non-silent success message?


## Related Documentation
- **[tests/mcp_server/integration/test_ready_phase_enforcement.py][related-1]**
- **[tests/mcp_server/unit/managers/test_enforcement_runner_c3.py][related-2]**
- **[mcp_server/tools/git_tools.py][related-3]**
- **[mcp_server/managers/git_manager.py][related-4]**
- **[mcp_server/adapters/git_adapter.py][related-5]**
- **[mcp_server/server.py][related-6]**
- **[docs/development/issue283/design-ready-phase-enforcement.md][related-7]**
- **[docs/development/issue283/planning-ready-phase-enforcement.md][related-8]**
- **[docs/development/issue257/planning.md][related-9]**
- **[docs/development/issue257/research_config_layer_srp.md][related-10]**
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-11]**

<!-- Link definitions -->

[related-1]: tests/mcp_server/integration/test_ready_phase_enforcement.py
[related-2]: tests/mcp_server/unit/managers/test_enforcement_runner_c3.py
[related-3]: mcp_server/tools/git_tools.py
[related-4]: mcp_server/managers/git_manager.py
[related-5]: mcp_server/adapters/git_adapter.py
[related-6]: mcp_server/server.py
[related-7]: docs/development/issue283/design-ready-phase-enforcement.md
[related-8]: docs/development/issue283/planning-ready-phase-enforcement.md
[related-9]: docs/development/issue257/planning.md
[related-10]: docs/development/issue257/research_config_layer_srp.md
[related-11]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.5 | 2026-04-11 | Agent | QA round 2: flag-day constraint scoped to raw-Path prohibition only; config-boundary closure pulled into issue-283 scope; "out of scope" note removed; Architecture Constraints and Conclusion 3 made consistent. |
| 1.4 | 2026-04-11 | Agent | QA remediation: flag-day constraint, Principle 14 debt explicit, 'single owner' → contract breach, NoteEntry stripped → problem-only section with ToolResult anchor, config-path moved to Architecture Constraints. |
| 1.3 | 2026-04-11 | Agent | Added design considerations: NoteEntry contract, NotesAggregator pattern, research boundary. |
| 1.2 | 2026-04-11 | Agent | Added config-root violation table, expected-result block (future cycle), clarified display-path exclusions. |
| 1.1 | 2026-04-11 | Agent | Added architecture interaction map, design/runtime gap analysis, config-root boundary audit, and principles alignment. |
| 1.0 | 2026-04-10 | Agent | Initial draft |
