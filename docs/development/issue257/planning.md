<!-- docs\development\issue257\planning.md -->
<!-- template=planning version=130ac5ea created=2026-03-12T12:19Z updated= -->
# Config-First PSE Architecture — Implementation Planning

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-12

---

## Purpose

Break down the design decisions from design.md (A–J) into six ordered, independently-testable implementation cycles. Each cycle has explicit stop/go criteria before the next cycle begins. Ordered for risk reduction: foundations and renames first, core abstractions second, then config layer, tool layer integration, enforcement, and deliverables tooling last.

## Scope

**In Scope:**
All components from design.md: phase_contracts.yaml, enforcement.yaml, deliverables.json, AtomicJsonWriter, PhaseContractResolver, StateRepository, EnforcementRunner, IStateReader/IStateRepository, PSE refactor, GitConfig.extract_issue_number(), tdd→implementation rename, projects.json abolishment

**Out of Scope:**
SHA-256 tamper detection for deliverables.json (issue #261); performance optimizations; multi-project support; backward-compatible migration layer

## Prerequisites

Read these first:
1. design.md APPROVED — all A–J decisions finalized
2. Branch feature/257-reorder-workflow-phases active, planning phase
3. Existing test suite green before cycle 1 starts
---

## Summary

Six implementation cycles that incrementally refactor the Phase State Engine to a Config-First architecture. Ordered by risk reduction: foundations and renames first, core abstractions second, then config layer, tool layer integration, enforcement, and finally deliverables tooling. Each cycle is independently testable and leaves the system in a deployable state.

---

## Dependencies

- Cycle 2 depends on Cycle 1: BranchState model references 'implementation' phase name
- Cycle 3 depends on Cycle 2: PhaseContractResolver receives IStateReader via constructor injection
- Cycle 4 depends on Cycles 2+3: PSE.get_state() returns BranchState; tool layer calls PCR.resolve()
- Cycle 5 depends on Cycle 4: EnforcementRunner injected at dispatch level alongside PSE
- Cycle 6 depends on Cycle 5: post-merge cleanup is an enforcement.yaml action; delete_file handler must exist

---

## TDD Cycles

### Cycle 1: Foundations & Renames (H + G + I3 + C)

**Design decisions:** H1–H4, G1–G2, I3, C2–C4

**Goal:** Eliminate dead code and rename all moving parts before new abstractions are introduced. Flag-day: `tdd` → `implementation`, `workflow_config.py` deleted, `GitConfig.extract_issue_number()` added, `projects.json` abolished.

**Tests:**
- All existing workflow tests pass with `implementation` replacing `tdd` in config and code
- `WorkflowConfig` methods (`get_workflow`, `validate_transition`, `get_first_phase`, `has_workflow`) available from `workflows.py` import path
- `GitConfig.extract_issue_number('feature/42-name')` returns `42`; returns `None` for branch without number
- PSE no longer contains `_extract_issue_from_branch()`; `GitConfig` injected instead
- `projects.json` does not exist; all references in PSE and ProjectManager removed
- No `import` from `workflow_config.py` anywhere in the codebase

**Success Criteria:**
- Full test suite green (no regressions)
- `grep` finds zero occurrences of `phase_deliverables`, `PhaseDeliverableResolver`, `HookRunner`, `workflow_config` in source
- `grep` finds zero occurrences of `projects.json` in source code (docs excluded)

**Stop/Go:** ✅ Go to Cycle 2 only if all three success criteria pass.

---

### Cycle 2: StateRepository + BranchState + AtomicJsonWriter (E + B3)

**Design decisions:** E1–E4, B3

**Goal:** Extract state I/O from PSE into a dedicated SRP component. Introduce `BranchState` (frozen Pydantic), `IStateReader`/`IStateRepository` Protocols, `FileStateRepository`, `InMemoryStateRepository`, and `AtomicJsonWriter`.

**Tests:**
- `BranchState` is a frozen Pydantic model; mutating any field raises `ValidationError`
- `FileStateRepository.load()` returns correct `BranchState` from `state.json` fixture
- `FileStateRepository.save()` writes `state.json` atomically (temp-file + rename; no partial writes)
- `InMemoryStateRepository` load/save round-trip without touching filesystem
- `AtomicJsonWriter` crash-test: simulate crash between write and rename; original file intact
- PSE receives `IStateRepository` via constructor injection; no direct file I/O in PSE
- `IStateReader`-typed consumers (`ScopeDecoder`, `PhaseContractResolver` stub) accept `IStateReader` and are rejected by Pyright when passed `IStateRepository`-only subtype

**Success Criteria:**
- PSE unit tests use `InMemoryStateRepository` (zero filesystem dependency in unit tests)
- Pyright `--strict` passes on `core/interfaces/`, state module, and PSE module
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 3 only if Pyright strict passes and InMemoryStateRepository is the default in all PSE unit tests.

---

### Cycle 3: phase_contracts.yaml loader + PhaseContractResolver (A + D + G3)

**Design decisions:** A1, A3, A5, A6, D1–D5, G3

**Goal:** Introduce the config layer: `phase_contracts.yaml` schema with Fail-Fast loader, `CheckSpec` Pydantic model, `PhaseContractResolver.resolve()`, and `PhaseConfigContext` facade.

**Tests:**
- Loader raises `ConfigError` at startup if `cycle_based: true` and `commit_type_map: {}` (decision A1)
- Loader fills missing fields with defaults: `subphases: []`, `commit_type_map: {}`, `cycle_based: false`
- `PhaseContractResolver.resolve('feature', 'implementation', cycle_number=1)` returns correct `list[CheckSpec]` from fixture YAML
- `PhaseContractResolver.resolve('docs', 'implementation', None)` returns `[]` without error (D3)
- `required=True` gates cannot be overridden by `deliverables.json` entries (resolver merge logic)
- `PhaseContractResolver` has no `import` of `StateRepository` or `pathlib.glob`
- `PhaseConfigContext` facade: tests inject one mock; resolver and workphases config both accessible
- `ConfigError` carries `file_path='.st3/config/phase_contracts.yaml'`

**Success Criteria:**
- Fail-Fast test passes: invalid `phase_contracts.yaml` raises `ConfigError` before first tool call
- Resolver returns `[]` for unknown phase (no exception)
- Pyright `--strict` passes on `PhaseContractResolver`, `CheckSpec`, `PhaseConfigContext`
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 4 only if Fail-Fast test and Pyright strict both pass.

---

### Cycle 4: Tool layer integration + PSE.get_state() + legacy param drop (J)

**Design decisions:** J1–J4

**Goal:** Wire the tool layer as composition root: `PSE.get_state(branch)` returns frozen `BranchState`, `GitManager.commit_with_scope()` receives `commit_type` as explicit parameter, legacy `phase=` parameter fully removed from `git_add_or_commit`.

**Tests:**
- `PSE.get_state('feature/42-name')` returns `BranchState` with correct fields
- `PSE.get_current_phase()` is a convenience wrapper over `get_state().current_phase`
- `GitManager.commit_with_scope(message, commit_type)` generates scoped commit message; no `PhaseContractResolver` dependency in `GitManager`
- `git_add_or_commit` tool raises `ValidationError` when called with legacy `phase=` kwarg
- Zero `phase=` kwargs remaining in `mcp_server/tools/`
- `TransitionPhaseTool` integration test: reads `cycle_number` from `PSE.get_state()`, passes it to `PCR.resolve()`, passes `commit_type` to `GitManager`

**Success Criteria:**
- `grep` finds zero `phase=` kwargs in `mcp_server/tools/` and `tests/`
- Backward-compat tests deleted (no dead test code)
- Pyright `--strict` passes on all tool files and PSE public API
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 5 only if grep check and Pyright strict both pass.

---

### Cycle 5: enforcement.yaml + EnforcementRunner (F + F3 + F5)

**Design decisions:** F1–F5

**Goal:** Introduce the enforcement layer: `enforcement.yaml` schema with plugin registration at startup, `EnforcementRunner` as separate service, `BaseTool.enforcement_event` class variable, dispatcher injection. `force_transition` catches hook exceptions as `ToolResult` warnings.

**Tests:**
- Loader raises `ConfigError` at startup if an action type has no registered handler (F2)
- `EnforcementRunner.run(event, timing, context)` calls the correct action-handler from registry
- `EnforcementRunner` unit tests: constructor-inject fake `EnforcementRegistry` with no-op handlers; zero dependency on `FileStateRepository` or PSE
- `BaseTool` subclass with `enforcement_event='transition_phase'` triggers pre/post hooks at dispatch level
- `BaseTool` subclass with `enforcement_event=None` incurs no registry lookup
- `force_transition`: `DeliverableCheckError` from hook returned as `ToolResult` warning, not raised (F5)
- `check_branch_policy` pre-hook on `create_branch` blocks creation if base restriction violated
- `commit_state_files` post-hook on `transition_phase` writes and commits `state.json`

**Success Criteria:**
- End-to-end test: `transition_phase` triggers post-hook → `state.json` committed automatically
- End-to-end test: `create_branch` with invalid base raises `ToolResult` error (not unhandled exception)
- `EnforcementRunner` unit tests have zero dependency on `FileStateRepository` or PSE
- Pyright `--strict` passes on `EnforcementRunner`, `EnforcementRegistry`, `BaseTool`
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 6 only if both end-to-end tests pass.

---

### Cycle 6: deliverables.json tools + state.json git-tracked (B1 + B2 + B4 + B5)

**Design decisions:** B1–B5

**Goal:** Implement `deliverables.json` tooling (`save`/`update` with completed-cycle guard), remove `state.json` from `.gitignore`, add post-merge cleanup action to `enforcement.yaml`, and add PSE startup guard for uncommitted state changes.

**Tests:**
- `save_planning_deliverables` creates `deliverables.json` with correct nested structure under issue number
- `update_planning_deliverables` raises `ValidationError` when attempting to modify a completed cycle in `cycle_history`
- `update_planning_deliverables` succeeds for open cycles
- All `deliverables.json` writes go through `AtomicJsonWriter` (no direct `open()` calls in tools)
- `state.json` not present in `.gitignore`; `git status` shows `state.json` as tracked after initialization
- Post-merge enforcement rule `delete_file` removes `deliverables.json` and `state.json` after merge
- `PSE.initialize_branch()` emits explicit warning (not exception) when `state.json` has uncommitted local changes

**Success Criteria:**
- Completed-cycle guard raises `ValidationError` with message identifying the cycle id
- `AtomicJsonWriter` used for all `deliverables.json` writes (grep verification)
- Integration test: full `transition_phase` flow commits `state.json` automatically (from Cycle 5 hook)
- Pyright `--strict` passes on `save_planning_deliverables` and `update_planning_deliverables` tools
- Full test suite green
- KPIs 1–20 in `research_config_first_pse.md` all verifiable

**Stop/Go:** ✅ KPIs 1–20 all verifiable → open PR.

---

## Risks & Mitigation

- **Risk:** Cycle 1 — `tdd` → `implementation` rename breaks active `state.json` files on other branches
  - **Mitigation:** Manual fix per decision H1. No migration code. Any active branch with `tdd` in `state.json` fixed by hand before Cycle 1 merges.
- **Risk:** Cycle 2 — PSE state refactor introduces regression in read/write path
  - **Mitigation:** `InMemoryStateRepository` used in all PSE unit tests. `FileStateRepository` tested in isolation with fixture files. `AtomicJsonWriter` crash-test validates no partial writes.
- **Risk:** Cycle 3 — `phase_contracts.yaml` schema mismatch with existing `.st3/config/` YAML files
  - **Mitigation:** Loader fills missing fields with defaults (decision A1). All existing YAML fixtures updated in Cycle 3. Fail-Fast catches schema errors at startup before any tool executes.
- **Risk:** Cycle 4 — legacy `phase=` param removal breaks undiscovered callers outside `mcp_server/tools/`
  - **Mitigation:** Full codebase `grep` pass (including tests and scripts) before removal. Pyright `--strict` catches remaining type errors at CI level.
- **Risk:** Cycle 5 — dispatch-level `EnforcementRunner` injection increases server startup complexity
  - **Mitigation:** `EnforcementRunner` independently testable via constructor injection of fake registry (zero PSE/filesystem dependency). Startup `ConfigError` for unknown action types catches config drift early.
- **Risk:** Cycle 6 — `.gitignore` removal of `state.json` affects all branches simultaneously
  - **Mitigation:** Single-line `.gitignore` removal. Active branches need `git add .st3/state.json` once. No data loss possible (file already present locally).

---

## Milestones

- After Cycle 1: codebase free of tdd, projects.json, workflow_config.py, old class names — green test suite
- After Cycle 2: PSE decoupled from filesystem; state I/O behind IStateRepository — Pyright strict passes
- After Cycle 3: phase gates config-driven; PhaseContractResolver independently testable — Fail-Fast validated
- After Cycle 4: tool layer is composition root; legacy param gone; commit scoping driven by phase_contracts.yaml
- After Cycle 5: enforcement layer live; state.json auto-committed on phase transition; branch policy enforced
- After Cycle 6: deliverables.json tooling complete; KPIs 1–20 in research_config_first_pse.md all verifiable — ready for PR

## Appendix — `save_planning_deliverables` Payload

> **Doel:** Één-op-één persisteerbare payload. Geen interpretatiestap vereist.
> Kopieer de JSON-block hieronder direct naar de `save_planning_deliverables` tool-aanroep.
>
> **Expliciete keuze over fase-entries:**
> - `design` → **inbegrepen**: design.md is APPROVED; twee structurele checks.
> - `validation` → **inbegrepen**: één check op aanwezigheid KPI-sectie na Cycle 6.
> - `documentation` → **inbegrepen**: één check op SCAFFOLD-header planning.md.
>
> **`validates`-types gebruikt:** `file_exists`, `contains_text`, `absent_text` — allemaal met verplicht `file`-veld, gevalideerd door `validate_spec` en `DeliverableChecker`.

```json
{
  "issue_number": 257,
  "planning_deliverables": {
    "tdd_cycles": {
      "total": 6,
      "cycles": [
        {
          "cycle_number": 1,
          "deliverables": [
            {
              "id": "D1.1",
              "description": "tdd → implementation: present in .st3/workflows.yaml (H rename)",
              "validates": {
                "type": "contains_text",
                "file": ".st3/workflows.yaml",
                "text": "- implementation"
              }
            },
            {
              "id": "D1.2",
              "description": "- tdd absent from .st3/workflows.yaml (H flag-day, no alias)",
              "validates": {
                "type": "absent_text",
                "file": ".st3/workflows.yaml",
                "text": "- tdd"
              }
            },
            {
              "id": "D1.3",
              "description": "GitConfig.extract_issue_number() implemented (I3 — cohesion in GitConfig)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/config/git_config.py",
                "text": "extract_issue_number"
              }
            },
            {
              "id": "D1.4",
              "description": "_extract_issue_from_branch removed from PSE (replaced by D1.3)",
              "validates": {
                "type": "absent_text",
                "file": "mcp_server/managers/phase_state_engine.py",
                "text": "_extract_issue_from_branch"
              }
            },
            {
              "id": "D1.5",
              "description": "projects.json references removed from PSE source (C abolishment)",
              "validates": {
                "type": "absent_text",
                "file": "mcp_server/managers/phase_state_engine.py",
                "text": "projects.json"
              }
            }
          ],
          "exit_criteria": "Full test suite green; absent: '- tdd' in .st3/workflows.yaml; absent: '_extract_issue_from_branch' in PSE; absent: 'projects.json' in PSE; present: 'extract_issue_number' in git_config.py"
        },
        {
          "cycle_number": 2,
          "deliverables": [
            {
              "id": "D2.1",
              "description": "state_repository.py created with BranchState + FileStateRepository + InMemoryStateRepository (E)",
              "validates": {
                "type": "file_exists",
                "file": "mcp_server/managers/state_repository.py"
              }
            },
            {
              "id": "D2.2",
              "description": "BranchState frozen=True — CQS enforced at type-system level (E)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/state_repository.py",
                "text": "frozen=True"
              }
            },
            {
              "id": "D2.3",
              "description": "InMemoryStateRepository present for test isolation (E4)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/state_repository.py",
                "text": "InMemoryStateRepository"
              }
            },
            {
              "id": "D2.4",
              "description": "AtomicJsonWriter implemented for crash-safe writes (B3)",
              "validates": {
                "type": "file_exists",
                "file": "mcp_server/utils/atomic_json_writer.py"
              }
            },
            {
              "id": "D2.5",
              "description": "IStateReader / IStateRepository Protocols created in core/interfaces/ (ISP split, E)",
              "validates": {
                "type": "file_exists",
                "file": "mcp_server/core/interfaces/__init__.py"
              }
            },
            {
              "id": "D2.6",
              "description": "PSE constructor receives IStateRepository — no direct file I/O in PSE (DIP, E)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/phase_state_engine.py",
                "text": "IStateRepository"
              }
            }
          ],
          "exit_criteria": "PSE unit tests use InMemoryStateRepository (zero filesystem dependency in unit tests); Pyright --strict passes on core/interfaces/, state_repository.py, phase_state_engine.py; full test suite green"
        },
        {
          "cycle_number": 3,
          "deliverables": [
            {
              "id": "D3.1",
              "description": "phase_contracts.yaml config file created in .st3/config/ (A — Config-First split)",
              "validates": {
                "type": "file_exists",
                "file": ".st3/config/phase_contracts.yaml"
              }
            },
            {
              "id": "D3.2",
              "description": "PhaseContractResolver implemented — SRP, no StateRepository dependency (D)",
              "validates": {
                "type": "file_exists",
                "file": "mcp_server/managers/phase_contract_resolver.py"
              }
            },
            {
              "id": "D3.3",
              "description": "CheckSpec Pydantic model defined in phase_contract_resolver.py (D2)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/phase_contract_resolver.py",
                "text": "class CheckSpec"
              }
            },
            {
              "id": "D3.4",
              "description": "Fail-Fast ConfigError raised for invalid phase_contracts.yaml (A1)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/phase_contract_resolver.py",
                "text": "ConfigError"
              }
            },
            {
              "id": "D3.5",
              "description": "PhaseConfigContext facade — single injection point for tool layer (D5, G)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/phase_contract_resolver.py",
                "text": "PhaseConfigContext"
              }
            }
          ],
          "exit_criteria": "Fail-Fast test passes: invalid phase_contracts.yaml raises ConfigError before first tool call; PhaseContractResolver.resolve() returns [] for unknown phase without exception; Pyright --strict passes on PhaseContractResolver, CheckSpec, PhaseConfigContext; full test suite green"
        },
        {
          "cycle_number": 4,
          "deliverables": [
            {
              "id": "D4.1",
              "description": "PSE.get_state(branch) → BranchState added — composition root (J1)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/phase_state_engine.py",
                "text": "def get_state"
              }
            },
            {
              "id": "D4.2",
              "description": "GitManager.commit_with_scope() with explicit commit_type param (J3)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/git_manager.py",
                "text": "commit_with_scope"
              }
            },
            {
              "id": "D4.3",
              "description": "Legacy phase= backward-compat path removed from git_tools.py (J4 flag-day)",
              "validates": {
                "type": "absent_text",
                "file": "mcp_server/tools/git_tools.py",
                "text": "LEGACY backward-compatible path"
              }
            },
            {
              "id": "D4.4",
              "description": "tdd literal guard removed from git_tools.py (workflow_phase == 'tdd' check gone after H)",
              "validates": {
                "type": "absent_text",
                "file": "mcp_server/tools/git_tools.py",
                "text": "workflow_phase == \"tdd\""
              }
            }
          ],
          "exit_criteria": "grep finds zero 'phase=' kwargs in mcp_server/tools/; backward-compat tests deleted; Pyright --strict passes on all tool files and PSE public API; full test suite green"
        },
        {
          "cycle_number": 5,
          "deliverables": [
            {
              "id": "D5.1",
              "description": "enforcement.yaml config file created in .st3/config/ (F — enforcement rules)",
              "validates": {
                "type": "file_exists",
                "file": ".st3/config/enforcement.yaml"
              }
            },
            {
              "id": "D5.2",
              "description": "EnforcementRunner service implemented — SRP, no PSE dependency (F)",
              "validates": {
                "type": "file_exists",
                "file": "mcp_server/managers/enforcement_runner.py"
              }
            },
            {
              "id": "D5.3",
              "description": "BaseTool.enforcement_event class variable added — declarative hook registration (F, Option C)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/tools/base.py",
                "text": "enforcement_event"
              }
            },
            {
              "id": "D5.4",
              "description": "EnforcementRegistry referenced in enforcement_runner.py — plugin fail-fast at startup (F2)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/enforcement_runner.py",
                "text": "EnforcementRegistry"
              }
            }
          ],
          "exit_criteria": "End-to-end test: transition_phase triggers post-hook → state.json committed automatically; end-to-end test: create_branch with invalid base raises ToolResult error (not unhandled exception); EnforcementRunner unit tests have zero dependency on FileStateRepository or PSE; Pyright --strict passes on EnforcementRunner, EnforcementRegistry, BaseTool; full test suite green"
        },
        {
          "cycle_number": 6,
          "deliverables": [
            {
              "id": "D6.1",
              "description": "project_manager.py writes to deliverables.json — projects.json abolished (B, C)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/project_manager.py",
                "text": "deliverables.json"
              }
            },
            {
              "id": "D6.2",
              "description": "projects_file attribute removed from ProjectManager (replaced by deliverables_file)",
              "validates": {
                "type": "absent_text",
                "file": "mcp_server/managers/project_manager.py",
                "text": "projects_file"
              }
            },
            {
              "id": "D6.3",
              "description": "AtomicJsonWriter used in project_manager.py for deliverables.json writes (B3)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/project_manager.py",
                "text": "AtomicJsonWriter"
              }
            },
            {
              "id": "D6.4",
              "description": "state.json removed from .gitignore — git-tracked per branch (B5)",
              "validates": {
                "type": "absent_text",
                "file": ".gitignore",
                "text": ".st3/state.json"
              }
            },
            {
              "id": "D6.5",
              "description": "PSE.initialize_branch() emits explicit warning for uncommitted state changes (B5, Explicit-over-Implicit)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/phase_state_engine.py",
                "text": "initialize_branch"
              }
            }
          ],
          "exit_criteria": "Completed-cycle guard raises ValidationError with cycle id; AtomicJsonWriter used for all deliverables.json writes (grep: no direct open() calls in project_manager.py for deliverables); integration test: full transition_phase flow commits state.json automatically; Pyright --strict passes on save/update tools and project_manager.py; full test suite green; KPIs 1–20 in research_config_first_pse.md all verifiable"
        }
      ]
    },
    "design": {
      "deliverables": [
        {
          "id": "DD.1",
          "description": "design.md status is APPROVED (scaffold workflow gate)",
          "validates": {
            "type": "contains_text",
            "file": "docs/development/issue257/design.md",
            "text": "Status:** APPROVED"
          }
        },
        {
          "id": "DD.2",
          "description": "design.md contains Key Design Decisions table for A–J",
          "validates": {
            "type": "contains_text",
            "file": "docs/development/issue257/design.md",
            "text": "### 3.1. Key Design Decisions"
          }
        }
      ]
    },
    "validation": {
      "deliverables": [
        {
          "id": "DV.1",
          "description": "KPI section present in research_config_first_pse.md — 20 KPIs verifiable after Cycle 6",
          "validates": {
            "type": "contains_text",
            "file": "docs/development/issue257/research_config_first_pse.md",
            "text": "## KPI"
          }
        }
      ]
    },
    "documentation": {
      "deliverables": [
        {
          "id": "DDOC.1",
          "description": "planning.md SCAFFOLD header present — template-tracked artifact",
          "validates": {
            "type": "contains_text",
            "file": "docs/development/issue257/planning.md",
            "text": "<!-- template=planning"
          }
        }
      ]
    }
  }
}
```

## Related Documentation
- **[design.md — Config-First PSE Architecture (decisions A–J, interfaces, component diagram)][related-1]**
- **[research_config_first_pse.md — Research source + KPIs 1–20 (frozen)][related-2]**
- **[../../coding_standards/ARCHITECTURE_PRINCIPLES.md — Binding architecture contract][related-3]**
- **[../../coding_standards/QUALITY_GATES.md — Gate 7: architectural review checklist][related-4]**

<!-- Link definitions -->

[related-1]: design.md — Config-First PSE Architecture (decisions A–J, interfaces, component diagram)
[related-2]: research_config_first_pse.md — Research source + KPIs 1–20 (frozen)
[related-3]: ../../coding_standards/ARCHITECTURE_PRINCIPLES.md — Binding architecture contract
[related-4]: ../../coding_standards/QUALITY_GATES.md — Gate 7: architectural review checklist

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |