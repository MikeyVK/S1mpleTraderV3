<!-- docs\development\issue263\copilot_orchestration_packaging_research.md -->
<!-- template=research version=8b7bb3ab created=2026-03-18T18:35Z updated= -->
# Issue #263 Copilot Orchestration Package Boundary Research

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-18

---

## Purpose

Define the structural research outputs required before planning can begin for a reusable copilot orchestration sub-project.

## Scope

**In Scope:**
Current orchestration file inventory, target package boundary, cleanup-first migration order, test boundary correction, and planning prerequisites.

**Out of Scope:**
Direct implementation of v2 sub-role orchestration, MCP server changes, and final planning deliverables.

## Prerequisites

Read these first:
1. Baseline research findings recorded
2. Second-pass architecture audit completed
3. Current hook, prompt, wrapper, and test surfaces inventoried
---

## Problem Statement

The current VS Code orchestration layer is spread across hook scripts, agent wrappers, prompt files, and misplaced tests, which prevents a clean package boundary and blocks planning for a reusable sub-project.

## Research Goals

- Produce a concrete inventory of the current orchestration surface that would belong to a separate sub-project.
- Define the target package boundary and migration shape for a reusable copilot_orchestration project.
- Establish a cleanup-first research sequence that must complete before planning for v2 sub-role orchestration can land.

---

## Background
## Open Questions

The initial open questions are now answerable at research level, but not yet translated into implementation planning:
- Which current files should become thin adapters versus first-class package modules?
- Which behavior should stay declarative in config instead of remaining hardcoded in Python?
- What minimum structural cleanup is required before planning can describe phased implementation work truthfully?

## Findings

Current runtime behavior is concentrated in six hook scripts under scripts/copilot_hooks, while doctrine and operating contracts are split across root-level role guides, .github agent wrappers, and prompt files. Existing tests cover only two orchestration scripts and sit under tests/mcp_server/unit/utils, which is the wrong project boundary. The present layer therefore needs a cleanup-first research pass before any implementation planning for v2 can be considered stable.

## Open Questions

- ❓ Which current files should become thin adapters versus first-class package modules?
- ❓ Which behavior should stay declarative in config instead of remaining hardcoded in Python?
- ❓ What minimum structural cleanup is required before planning can describe phased implementation work truthfully?
## 1. Current Inventory

### 1.1 Runtime Hook Surface

The current runtime surface that belongs to the orchestration concern is:

| Current File | Current Role | Structural Assessment | Target Direction |
|---|---|---|---|
| `scripts/copilot_hooks/session_start.py` | Generic workspace SessionStart hook | Thin script, but duplicates git plumbing | Keep as adapter over shared session service |
| `scripts/copilot_hooks/session_start_imp.py` | `@imp` SessionStart hook | Role-specific script with duplicated git and snapshot logic | Split into adapter + package session context assembly |
| `scripts/copilot_hooks/session_start_qa.py` | `@qa` SessionStart hook | Role-specific script with duplicated git and snapshot logic | Split into adapter + package session context assembly |
| `scripts/copilot_hooks/pre_compact.py` | Neutral workspace PreCompact hook | Already thin and close to desired adapter shape | Keep as adapter |
| `scripts/copilot_hooks/pre_compact_agent.py` | Agent-specific PreCompact snapshot writer | Current SRP hotspot and parsing hub | Break into package contracts, parsing, extraction, and storage services |
| `scripts/copilot_hooks/stop_handover_guard.py` | Stop-hook enforcement | Hardcoded rule engine in script form | Move logic to package enforcement module with declarative config |

### 1.2 Agent and Doctrine Surface

| Current File | Current Role | Structural Assessment | Target Direction |
|---|---|---|---|
| `.github/agents/imp.agent.md` | VS Code wrapper for `@imp` | Acceptable wrapper boundary, but still points at script entrypoints | Keep as thin wrapper over package-backed hooks |
| `.github/agents/qa.agent.md` | VS Code wrapper for `@qa` | Acceptable wrapper boundary, but still points at script entrypoints | Keep as thin wrapper over package-backed hooks |
| `imp_agent.md` | Implementation doctrine | Contains role identity plus repo-coupled operational details | Reduce to doctrine and boundaries only |
| `qa_agent.md` | QA doctrine | Contains role identity plus repo-coupled operational details | Reduce to doctrine and review boundaries only |

### 1.3 Prompt Surface

The current prompt contract surface is:
- `.github/prompts/start-implementation.prompt.md`
- `.github/prompts/resume-implementation.prompt.md`
- `.github/prompts/prepare-handover.prompt.md`
- `.github/prompts/request-qa-review.prompt.md`
- `.github/prompts/prepare-qa-brief.prompt.md`
- `.github/prompts/prepare-implementation-brief.prompt.md`
- `.github/prompts/plan-executionDirectiveBatchCoordination.prompt.md`

Assessment:
- The first six prompts are orchestration-relevant.
- `plan-executionDirectiveBatchCoordination.prompt.md` does not belong to the minimal implementation/QA cockpit and should not be treated as part of the reusable core unless later research proves otherwise.
- Prompt expectations currently overlap with doctrine and stop-hook enforcement, so they are not yet a clean contract layer.

### 1.4 Test Surface

The current explicit orchestration tests are:
- `tests/mcp_server/unit/utils/test_pre_compact_agent.py`
- `tests/mcp_server/unit/utils/test_stop_handover_guard.py`

Assessment:
- The test subtree is wrong for this concern.
- Both tests import script files via `spec_from_file_location(...)`, which confirms there is no stable module seam yet.
- There is no direct test coverage for `session_start.py`, `session_start_imp.py`, `session_start_qa.py`, or the prompt contracts.

### 1.5 Inventory Conclusion

The present implementation is not a package with adapters around it. It is a set of repository-local scripts with documentation and prompts around them. Research must therefore define the package seam before planning tries to describe phased implementation work.

---

## 2. Target Package Boundary

### 2.1 Proposed Project Shape

Decision for this run:
- only `copilot_orchestration` receives a new package seam and `src/`-based target layout
- `mcp_server` is explicitly out of scope for this migration run
- the ST3/backend application layer is explicitly out of scope for this migration run
- this run does **not** migrate the whole repository to a uniform multi-package `src/` model

Concrete target for the scope of this issue:

```text
src/
  copilot_orchestration/
    adapters/
      vscode_hooks/
    compact/
    config/
    contracts/
    enforcement/
    session/
    storage/
```

Future-compatible repository model if other boundaries are ever migrated later:

```text
src/
  copilot_orchestration/
  mcp_server/
  st3/
```

Research interpretation:
- `copilot_orchestration` is the only new package boundary being designed now
- `mcp_server` and `st3` remain where they are during this run
- the future sibling-package model is architectural context only, not current migration scope

### 2.2 Boundary Rules

The reusable `copilot_orchestration` project should own:
- typed contracts for snapshot payloads, transcript records, handover policies, role definitions, and sub-role definitions
- transcript parsing and extraction logic
- session-context assembly logic
- stop-hook validation logic
- storage interfaces and default filesystem implementation
- orchestration configuration loading and validation

The repository-local layer should own only:
- VS Code hook registration in `.github/agents/*.agent.md`
- thin entry scripts under `scripts/copilot_hooks/`
- local prompt wording that intentionally remains repository-specific
- repo-specific doctrine in `imp_agent.md` and `qa_agent.md`

### 2.3 What Must Not Cross The Boundary

The reusable package must not directly depend on:
- `.st3/state.json`
- `.st3/projects.json`
- issue numbering conventions
- S1mpleTrader-specific branch or phase semantics
- repository-specific slash-command names as hardcoded source of truth

The reusable package may accept those things only through explicit configuration passed in by the integrating repository.

### 2.4 Adapter Strategy

The six existing hook scripts should become adapter entrypoints only.

Target adapter responsibility:
1. read VS Code hook input
2. call one package service
3. serialize package output back to VS Code JSON

Anything beyond that belongs in the package.

### 2.5 V1 Migration Shape Versus V2 Target

This distinction is critical for the scope of this issue.

**V1 migration shape for the first cleanup run:**
- create the package seam under `src/copilot_orchestration/`
- move the current orchestration implementation under that package boundary in a coarse-grained way
- keep the current script-level decomposition largely intact
- leave `scripts/copilot_hooks/*.py` as thin entry shims or adapter shells
- do **not** use the first run to fully decompose the code into final `compact/`, `session/`, `contracts/`, `config/`, and `enforcement/` modules unless a tiny helper extraction is technically unavoidable

Minimal acceptable V1 package fill:

```text
src/
  copilot_orchestration/
    __init__.py
    hooks/
      session_start.py
      session_start_imp.py
      session_start_qa.py
      pre_compact.py
      pre_compact_agent.py
      stop_handover_guard.py
```

**V2 target after the seam exists:**
- split coarse hook implementations into stable submodules such as parsing, storage, enforcement, and contracts
- redesign the normative-versus-declarative boundary
- separate role identity from prompt operations more strictly
- revisit which parts deserve lasting tests and where they belong
- apply deeper architecture hardening inside the new package boundary

Research consequence:
- the richer package tree in this document is a target architecture, not a mandatory first-fill structure
- the first cleanup run is allowed to be structurally coarse as long as it establishes the package boundary cleanly
- deeper decomposition belongs to the later refactor, not to the initial migration

---

## 3. Cleanup-First Research Sequence

This is the research-backed order that should exist before formal planning begins.

### Stage R1: Define Contracts And Boundary

Deliverables:
- typed snapshot contract
- typed transcript record contract
- typed handover requirement contract
- explicit list of what is package-owned versus repo-owned

Research exit condition:
- script behavior can be described in terms of package services rather than script internals

### Stage R2: Define Storage And Config Model

Deliverables:
- storage abstraction for `.copilot/` persistence
- config schema for roles, sub-roles, markers, defaults, and recommendations
- fail-fast validation rules for invalid orchestration configuration

Research exit condition:
- hardcoded rule matrices and heuristics can be mapped to explicit config entries or rejected as non-reusable

### Stage R3: Define Module Migration Targets

Deliverables:
- mapping of current script functions to future package modules
- decision on what remains adapter-only versus what becomes a reusable service
- decision on prompt contracts that stay repo-local versus package-informed

Research exit condition:
- each current file has a clear migration disposition: keep, thin, split, move, or retire

### Stage R4: Define Correct Test Boundary

Deliverables:
- dedicated test subtree under `tests/copilot_orchestration/`
- package import strategy without `spec_from_file_location(...)`
- coverage target focused on contracts, adapters, parser behavior, storage behavior, and enforcement behavior

Research exit condition:
- the orchestration layer can be verified without pretending it belongs to `mcp_server`

### Stage R5: Define Planning Preconditions

Deliverables:
- list of research assumptions that are now resolved
- list of unresolved questions that still block implementation planning
- explicit statement that v2 sub-role work is now plan-worthy or still premature

Research exit condition:
- planning can describe implementation phases without hiding structural cleanup inside them

---

## 4. Migration Risks

1. **False package extraction risk**
   - Moving files into `src/copilot_orchestration/` without first defining contracts would only relocate the current script mess.

2. **Prompt leakage risk**
   - If prompt wording is treated as the source of truth instead of a client of package contracts, doctrine and enforcement will remain duplicated.

3. **Over-reuse risk**
   - Not every repo-local prompt or slash command should become reusable core behavior.
   - The reusable package must stay smaller than the full local orchestration setup.

4. **Silent-compatibility risk**
   - If malformed transcript or snapshot data remains silently tolerated during migration, the extracted package will preserve current fail-soft behavior.

5. **Test theatre risk**
   - Keeping the old tests while only adding package tests could create duplicate, contradictory evidence.
   - Research should allow the current mislocated tests to be retired and replaced when the new seam exists.

---

## 5. Planning Preconditions

Planning should not start until research can answer these points concretely:

1. Which current files are adapters and which become package modules?
2. Which orchestration rules are configuration and which are executable policy?
3. What is the exact test boundary for the extracted project?
4. Which prompt behaviors remain repository-local and which should be package-informed?
5. What fail-fast behavior is required for malformed hook input, malformed snapshots, and invalid orchestration config?

Current assessment:
- Questions 1 through 5 are now much clearer than before, but they are not yet translated into a formal migration map per function and per file.
- That means research has advanced enough to justify a cleanup-first migration design, but not yet a final implementation plan.

---



## 6. Function-Level Migration Map

This section answers follow-up step 1 directly: which current functions should stay as adapter concerns, which should move into package modules, and which should be consolidated.

### 6.1 SessionStart Runtime Mapping

| Current File | Current Function | Target Module | Migration Disposition | Reason |
|---|---|---|---|---|
| `scripts/copilot_hooks/session_start.py` | `main()` | `copilot_orchestration.adapters.vscode_hooks.session_start_workspace` | Keep thin, rewrite around service call | Adapter entrypoint only |
| `scripts/copilot_hooks/session_start.py` | `get_changed_files()` | `copilot_orchestration.session.git_status` | Move and consolidate | Shared git status concern |
| `scripts/copilot_hooks/session_start.py` | `run_git_command()` | `copilot_orchestration.session.git_status` | Move and consolidate | Shared subprocess wrapper |
| `scripts/copilot_hooks/session_start_imp.py` | `main()` | `copilot_orchestration.adapters.vscode_hooks.session_start_imp` | Keep thin, rewrite around service call | Adapter entrypoint only |
| `scripts/copilot_hooks/session_start_imp.py` | `get_changed_files()` | `copilot_orchestration.session.git_status` | Delete local copy after extraction | Duplicate of workspace logic |
| `scripts/copilot_hooks/session_start_imp.py` | `run_git_command()` | `copilot_orchestration.session.git_status` | Delete local copy after extraction | Duplicate of workspace logic |
| `scripts/copilot_hooks/session_start_imp.py` | `read_json_file()` | `copilot_orchestration.storage.snapshot_store` | Move | Snapshot read concern |
| `scripts/copilot_hooks/session_start_imp.py` | `is_usable_snapshot()` | `copilot_orchestration.session.snapshot_relevance` | Move | Snapshot relevance policy |
| `scripts/copilot_hooks/session_start_imp.py` | `as_clean_text()` | `copilot_orchestration.contracts.normalization` | Consolidate | Shared normalization helper |
| `scripts/copilot_hooks/session_start_imp.py` | `as_string_list()` | `copilot_orchestration.contracts.normalization` | Consolidate | Shared normalization helper |
| `scripts/copilot_hooks/session_start_imp.py` | `truncate()` | `copilot_orchestration.contracts.normalization` | Consolidate or inline | Shared formatting concern |
| `scripts/copilot_hooks/session_start_qa.py` | `main()` | `copilot_orchestration.adapters.vscode_hooks.session_start_qa` | Keep thin, rewrite around service call | Adapter entrypoint only |
| `scripts/copilot_hooks/session_start_qa.py` | `get_changed_files()` | `copilot_orchestration.session.git_status` | Delete local copy after extraction | Duplicate of workspace logic |
| `scripts/copilot_hooks/session_start_qa.py` | `run_git_command()` | `copilot_orchestration.session.git_status` | Delete local copy after extraction | Duplicate of workspace logic |
| `scripts/copilot_hooks/session_start_qa.py` | `read_json_file()` | `copilot_orchestration.storage.snapshot_store` | Move | Snapshot read concern |
| `scripts/copilot_hooks/session_start_qa.py` | `is_usable_snapshot()` | `copilot_orchestration.session.snapshot_relevance` | Move | Snapshot relevance policy |
| `scripts/copilot_hooks/session_start_qa.py` | `as_clean_text()` | `copilot_orchestration.contracts.normalization` | Consolidate | Shared normalization helper |
| `scripts/copilot_hooks/session_start_qa.py` | `as_string_list()` | `copilot_orchestration.contracts.normalization` | Consolidate | Shared normalization helper |
| `scripts/copilot_hooks/session_start_qa.py` | `truncate()` | `copilot_orchestration.contracts.normalization` | Consolidate or inline | Shared formatting concern |

### 6.2 PreCompact Runtime Mapping

| Current File | Current Function | Target Module | Migration Disposition | Reason |
|---|---|---|---|---|
| `scripts/copilot_hooks/pre_compact.py` | `main()` | `copilot_orchestration.adapters.vscode_hooks.pre_compact_workspace` | Keep thin | Neutral adapter already |
| `scripts/copilot_hooks/pre_compact_agent.py` | `main()` | `copilot_orchestration.adapters.vscode_hooks.pre_compact_agent` | Keep thin, rewrite around services | Adapter only after extraction |
| `scripts/copilot_hooks/pre_compact_agent.py` | `derive_chat_id()` | `copilot_orchestration.compact.chat_identity` | Move | Event-to-chat-id contract |
| `scripts/copilot_hooks/pre_compact_agent.py` | `read_transcript()` | `copilot_orchestration.compact.transcript_loader` | Move | Transcript IO concern |
| `scripts/copilot_hooks/pre_compact_agent.py` | `parse_transcript_content()` | `copilot_orchestration.compact.transcript_parser` | Move | Core parser service |
| `scripts/copilot_hooks/pre_compact_agent.py` | `read_json_file()` | `copilot_orchestration.storage.snapshot_store` | Consolidate | Shared storage concern |
| `scripts/copilot_hooks/pre_compact_agent.py` | `read_stdin_json()` | `copilot_orchestration.adapters.vscode_hooks.input_parser` | Move | Adapter boundary concern |
| `scripts/copilot_hooks/pre_compact_agent.py` | `collect_message_records()` | `copilot_orchestration.compact.transcript_projection` | Move | Transcript projection concern |
| `scripts/copilot_hooks/pre_compact_agent.py` | `collect_text_fragments()` | `copilot_orchestration.compact.transcript_projection` | Move | Transcript projection concern |
| `scripts/copilot_hooks/pre_compact_agent.py` | `_visit_message_nodes()` | `copilot_orchestration.compact.transcript_projection` | Move | Internal traversal helper |
| `scripts/copilot_hooks/pre_compact_agent.py` | `_visit_text_nodes()` | `copilot_orchestration.compact.transcript_projection` | Move | Internal traversal helper |
| `scripts/copilot_hooks/pre_compact_agent.py` | `_extract_text()` | `copilot_orchestration.compact.transcript_projection` | Move | Internal traversal helper |
| `scripts/copilot_hooks/pre_compact_agent.py` | `_deduplicate_records()` | `copilot_orchestration.compact.transcript_projection` | Move | Internal traversal helper |
| `scripts/copilot_hooks/pre_compact_agent.py` | `_deduplicate_fragments()` | `copilot_orchestration.compact.transcript_projection` | Move | Internal traversal helper |
| `scripts/copilot_hooks/pre_compact_agent.py` | `extract_last_user_goal()` | `copilot_orchestration.compact.goal_extraction` | Move | Single extraction concern |
| `scripts/copilot_hooks/pre_compact_agent.py` | `extract_goal_from_text_fragments()` | `copilot_orchestration.compact.goal_extraction` | Move | Single extraction concern |
| `scripts/copilot_hooks/pre_compact_agent.py` | `infer_active_role()` | `copilot_orchestration.compact.role_detection` | Move then redesign | Current heuristic must later become config-driven |
| `scripts/copilot_hooks/pre_compact_agent.py` | `infer_role_from_text_fragments()` | `copilot_orchestration.compact.role_detection` | Move then redesign | Current heuristic must later become config-driven |
| `scripts/copilot_hooks/pre_compact_agent.py` | `extract_files_in_scope()` | `copilot_orchestration.compact.file_scope_extraction` | Move | Dedicated extraction concern |
| `scripts/copilot_hooks/pre_compact_agent.py` | `extract_files_from_text_fragments()` | `copilot_orchestration.compact.file_scope_extraction` | Move | Dedicated extraction concern |
| `scripts/copilot_hooks/pre_compact_agent.py` | `extract_pending_handover_summary()` | `copilot_orchestration.compact.handover_extraction` | Move then redesign | Current prose markers should later become declarative |
| `scripts/copilot_hooks/pre_compact_agent.py` | `extract_handover_from_text_fragments()` | `copilot_orchestration.compact.handover_extraction` | Move then redesign | Current prose markers should later become declarative |
| `scripts/copilot_hooks/pre_compact_agent.py` | `extract_handover_prompt_block()` | `copilot_orchestration.compact.handover_extraction` | Move | Dedicated extraction concern |
| `scripts/copilot_hooks/pre_compact_agent.py` | `_extract_fenced_text_block()` | `copilot_orchestration.compact.handover_extraction` | Move | Internal extraction helper |
| `scripts/copilot_hooks/pre_compact_agent.py` | `_has_handover_shape()` | `copilot_orchestration.compact.handover_extraction` | Move then redesign | Current marker logic should later be config-backed |
| `scripts/copilot_hooks/pre_compact_agent.py` | `as_clean_text()` | `copilot_orchestration.contracts.normalization` | Consolidate | Shared normalization helper |
| `scripts/copilot_hooks/pre_compact_agent.py` | `as_string_list()` | `copilot_orchestration.contracts.normalization` | Consolidate | Shared normalization helper |
| `scripts/copilot_hooks/pre_compact_agent.py` | `truncate()` | `copilot_orchestration.contracts.normalization` | Consolidate or inline | Shared formatting concern |

### 6.3 Stop Hook Runtime Mapping

| Current File | Current Function | Target Module | Migration Disposition | Reason |
|---|---|---|---|---|
| `scripts/copilot_hooks/stop_handover_guard.py` | `RoleRequirement` | `copilot_orchestration.contracts.handover_rules` | Move and rename | Typed contract belongs in package |
| `scripts/copilot_hooks/stop_handover_guard.py` | `main()` | `copilot_orchestration.adapters.vscode_hooks.stop_guard` | Keep thin, rewrite around service call | Adapter entrypoint only |
| `scripts/copilot_hooks/stop_handover_guard.py` | `evaluate_stop_hook()` | `copilot_orchestration.enforcement.stop_guard_service` | Move | Core enforcement logic |
| `scripts/copilot_hooks/stop_handover_guard.py` | `normalize_role()` | `copilot_orchestration.contracts.role_resolution` | Move then redesign | Role resolution should align with config |
| `scripts/copilot_hooks/stop_handover_guard.py` | `is_stop_retry_active()` | `copilot_orchestration.enforcement.stop_guard_service` | Move | Enforcement state concern |
| `scripts/copilot_hooks/stop_handover_guard.py` | `read_transcript()` | `copilot_orchestration.compact.transcript_loader` | Consolidate | Duplicate transcript IO |
| `scripts/copilot_hooks/stop_handover_guard.py` | `parse_transcript_content()` | `copilot_orchestration.compact.transcript_parser` | Consolidate | Duplicate parser |
| `scripts/copilot_hooks/stop_handover_guard.py` | `read_stdin_json()` | `copilot_orchestration.adapters.vscode_hooks.input_parser` | Consolidate | Adapter boundary concern |
| `scripts/copilot_hooks/stop_handover_guard.py` | `collect_message_records()` | `copilot_orchestration.compact.transcript_projection` | Consolidate | Duplicate projection |
| `scripts/copilot_hooks/stop_handover_guard.py` | `_visit_message_nodes()` | `copilot_orchestration.compact.transcript_projection` | Consolidate | Duplicate traversal |
| `scripts/copilot_hooks/stop_handover_guard.py` | `extract_text()` | `copilot_orchestration.compact.transcript_projection` | Consolidate | Duplicate extraction helper |
| `scripts/copilot_hooks/stop_handover_guard.py` | `deduplicate_records()` | `copilot_orchestration.compact.transcript_projection` | Consolidate | Duplicate dedupe helper |
| `scripts/copilot_hooks/stop_handover_guard.py` | `clean_text()` | `copilot_orchestration.contracts.normalization` | Consolidate | Shared normalization helper |
| `scripts/copilot_hooks/stop_handover_guard.py` | `extract_last_assistant_text()` | `copilot_orchestration.enforcement.stop_guard_service` | Move | Enforcement-oriented helper |
| `scripts/copilot_hooks/stop_handover_guard.py` | `has_valid_handover()` | `copilot_orchestration.enforcement.stop_guard_service` | Move then redesign | Should use declarative rules, not hardcoded matrix |
| `scripts/copilot_hooks/stop_handover_guard.py` | `build_stop_reason()` | `copilot_orchestration.enforcement.stop_guard_service` | Move then redesign | Reason text should be built from declarative requirement data |

### 6.4 Migration Map Conclusion

The migration map confirms that only six functions should remain adapter-entry concerns: the various `main()` entrypoints and the neutral workspace `pre_compact.py` behavior. Almost everything else belongs in shared package modules, and a large subset should be consolidated because the same parsing and normalization logic currently exists in multiple scripts.

---

## 7. Proposed Test Boundary

This section answers follow-up step 3 directly: what the next orchestration test tree should look like, and which current tests should be retired or rewritten.

### 7.1 Proposed Test Tree

```text
tests/
  copilot_orchestration/
    adapters/
      vscode_hooks/
        test_pre_compact_workspace_adapter.py
        test_pre_compact_agent_adapter.py
        test_session_start_workspace_adapter.py
        test_session_start_imp_adapter.py
        test_session_start_qa_adapter.py
        test_stop_guard_adapter.py
    compact/
      test_transcript_loader.py
      test_transcript_parser.py
      test_transcript_projection.py
      test_goal_extraction.py
      test_role_detection.py
      test_file_scope_extraction.py
      test_handover_extraction.py
      test_chat_identity.py
    session/
      test_git_status.py
      test_snapshot_relevance.py
      test_session_context_builder.py
    enforcement/
      test_stop_guard_service.py
      test_handover_rules.py
    storage/
      test_snapshot_store.py
    config/
      test_orchestration_config_loader.py
      test_orchestration_config_validation.py
    contracts/
      test_snapshot_contracts.py
      test_role_resolution.py
      test_normalization.py
```

### 7.2 What Happens To Current Tests

| Current Test | Current Problem | Target Action | Future Replacement |
|---|---|---|---|
| `tests/mcp_server/unit/utils/test_pre_compact_agent.py` | Wrong project subtree; imports script via `spec_from_file_location(...)`; covers only parser fragments of one script | Retire after package extraction begins | Replace with `test_transcript_parser.py`, `test_transcript_projection.py`, `test_goal_extraction.py`, `test_file_scope_extraction.py`, `test_handover_extraction.py`, and `test_pre_compact_agent_adapter.py` |
| `tests/mcp_server/unit/utils/test_stop_handover_guard.py` | Wrong project subtree; imports script via `spec_from_file_location(...)`; tests hardcoded role behavior at script boundary | Retire after package extraction begins | Replace with `test_stop_guard_service.py`, `test_handover_rules.py`, and `test_stop_guard_adapter.py` |

### 7.3 Coverage Priorities

The first target is not raw percentage theatre but honest coverage at the right seam.

Priority order:
1. package contracts and validation errors
2. transcript parsing and projection behavior
3. storage behavior and malformed snapshot handling
4. stop-hook enforcement behavior
5. adapter translation in and out of VS Code hook JSON
6. prompt contract checks, if they remain part of the reusable package surface

### 7.4 Prompt Testing Position

Prompt tests should be added only if prompt output shape is treated as package-informed contract.

Two acceptable research outcomes exist:
1. prompts remain repository-local and get light snapshot tests or markdown contract checks in this repository only
2. prompts consume package-defined rule data, in which case package-level contract tests should verify the underlying rule data rather than the markdown prose itself

Current research direction:
- prompt files are important, but they should not be the primary source of truth
- however, prompt and role separation is not part of the first cleanup/migration run
- that stricter separation belongs to the later v2 refactor research where the normative-versus-declarative boundary is the real design question

### 7.5 Test Boundary Conclusion

User direction for this issue is explicit:
- the current orchestration test suite is ad hoc, weak, and not materially important to the first cleanup run
- test rebuilding or test migration is not in scope for the initial package extraction and relocation work
- the current tests are therefore disposable rather than migration-critical

Research consequence:
- the proposed `tests/copilot_orchestration/` tree remains a valid future direction
- it is not a prerequisite deliverable for the first cleanup/migration pass
- test strategy should be revisited only after the package seam exists and the v2 refactor clarifies what deserves stable coverage

---

## 8. Research Answers To The Open Questions

### 8.1 Which current files become adapters versus package modules?

Research answer:
- The target remains a later loadable package: `copilot_orchestration`
- Adapter files: the six existing hook entry scripts and the two `.github/agents/*.agent.md` wrappers
- Package modules: almost all non-entry logic currently embedded in `session_start_imp.py`, `session_start_qa.py`, `pre_compact_agent.py`, and `stop_handover_guard.py`
- Repo-local doctrine: `imp_agent.md`, `qa_agent.md`, and most prompt wording stay outside the reusable package
- Role guides and prompt files should remain repository-specific and user-adjustable surfaces, even after extraction

### 8.2 Which behavior should become declarative config?

Research answer:
- This question is only partially answerable in the first cleanup round by design
- the substantive normative-versus-declarative split belongs to v2 research, not to the first migration run
- for now, only package-shaping configuration should be assumed: storage settings, compatibility rules, and later role/sub-role metadata if required by v2

Research answer for non-config behavior:
- transcript parsing, JSON decoding, traversal, normalization, storage IO, and the first cleanup extraction work remain executable package logic
- strict role-versus-prompt separation is intentionally deferred until the refactor where those boundaries are redesigned together

### 8.3 What minimum cleanup must land before planning is trustworthy?

Research answer:
1. confirm the project is aimed at a later loadable package, not just an internal folder move
2. define typed package contracts and the adapter-versus-package boundary
3. extract shared parser, projection, storage, and git-status logic behind that boundary
4. keep test migration and test rebuilding out of the first cleanup scope
5. keep strict architectural hardening and normative-versus-declarative redesign out of the first cleanup scope

Conclusion:
- The blocking open questions for the current research scope are now answered to a satisfactory level
- What remains is not missing direction but intentionally deferred v2 research on stricter role/prompt separation, declarative contracts, and post-cleanup hardening

---

## Related Documentation
- **[docs/development/issue263/research.md][related-1]**
- **[docs/development/issue263/design.md][related-2]**
- **[docs/development/issue263/design_v2_sub_role_orchestration.md][related-3]**

<!-- Link definitions -->

[related-1]: docs/development/issue263/research.md
[related-2]: docs/development/issue263/design.md
[related-3]: docs/development/issue263/design_v2_sub_role_orchestration.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-18 | Agent | Initial draft |
