<!-- c:\temp\st3\docs\development\issue257\issue_body_closeout_draft.md -->
<!-- template=issue version=8dd42510 created=2026-04-06T07:46Z updated=2026-04-06 -->
# Reorder workflow phases: research → design → planning → tdd

Close-out summary for issue #257. What started as a narrow workflow-order patch grew into a full Config Layer SRP overhaul spanning 10 named TDD cycles, a scope pivot triggered by a 10/20 KPI crisis, a config architecture flag-day, and a closing Threshold B MCP clean-up. The branch ran from 2026-03-03 to 2026-04-06.

---

## Problem

The workflow order `research → planning → design → tdd` was epistemically wrong: deliverables were locked in planning **before** the design was known. The symptom at code level was `planning_deliverables.design` as a sub-key — a planning artefact referencing design decisions that did not yet exist.

During execution two deeper problems emerged that were tightly coupled to this:

1. **Config-layer SRP debt** — no central `ConfigLoader`; all schema classes self-loading; module-level singletons with import-time side effects everywhere; 44 SOLID violations identified across `mcp_server/config/`.
2. **MCP orchestration debt** — `PhaseStateEngine` was a God Class mixing gate dispatch, state reads, and lifecycle hooks; `get_state()` was not a pure query; cycle-phase transitions were hardcoded on `"implementation"` instead of being config-driven.

---

## Delivered Outcomes

### Layer 1 — PSE Config-First Architecture (Cycles C1–C7, 2026-03-12 to 2026-03-13)

Seven TDD cycles on the `feature/257` branch produced a Config-First PSE architecture:

| Component | What it delivers |
|-----------|-----------------|
| `StateRepository` + `AtomicJsonWriter` | SRP extraction from PSE; atomic JSON writes; `BranchState` immutable |
| `PhaseContractResolver` | Combines config + registry into `list[CheckSpec]`; fail-fast on `cycle_based + empty commit_type_map` |
| `EnforcementRunner` | Replaces `HookRunner` for both phase- and tool-enforcement |
| `GitConfig.extract_issue_number()` | Centralised branch-name parsing; no more inline regex |
| ISP split: `IStateReader` / `IStateRepository` | Read-only vs read+write interface separation |
| `tdd → implementation` rename | Flag-day, no alias, no migration layer |
| `projects.json` abolished | `state.json` per branch as SSOT |

**Test result at C7:** 2123 passed.

### Layer 2 — Gap Analysis Crisis (2026-03-13)

After 7 green TDD cycles a structured KPI check revealed **10 of 20 KPIs red**. Components existed and were fully tested but had never been wired into the running system. Eight root causes were documented (`GAP_ANALYSE_ISSUE257.md`, RC-1 through RC-8):

| RC | Core finding |
|----|-------------|
| RC-1 | `projects.json` still present after Cycle 1 — Stop/Go not enforced |
| RC-2 | `PhaseContractResolver` built and tested, never called from PSE exit-hooks |
| RC-3 | Behaviour tests only — no structural tests checking wiring |
| RC-4 | PSE (869+ lines, God Class) systematically avoided in TDD |
| RC-6 | `phase_contracts.yaml` hardcoded to `issue257/` paths — breaks every other branch |

The PSE recovery plan was abandoned once root analysis showed the real problem was one layer deeper: the entire config layer lacked structure.

### Layer 3 — Config Layer SRP: 10-cycle overhaul (2026-03-14 to 2026-03-26)

The scope pivoted to a complete Config Layer SRP remediation. `research_config_layer_srp.md` was written in 9 iterations (v1.0–v1.9), documenting 16 findings (F1–F16) and 15 architectural decisions (D1–D15). Planning was rewritten three times (`planning.md` v1.0 → v2.0 → v3.0) establishing 7 global rules (P-1 through P-7) — including the "Built and Wired" rule and "No Partial Migration" — before a single production cycle started.

**Ten production cycles:**

| Cycle | Delivered |
|-------|-----------|
| `C_SETTINGS.1` | `Settings.from_env()`; `MCP_LOG_LEVEL → LOG_LEVEL` env-var rename; DI stub wired in `server.py` |
| `C_SETTINGS.2` | Workflow singleton removed; full DI for both `Settings` and `WorkflowConfig` |
| `C_LOADER.1–2` | `ConfigLoader` introduced; `config/schemas/` subdir formalised; `from_file()` / `ClassVar` singletons removed from all schema classes |
| `C_LOADER.3` | Full DI rewiring across managers, core, scaffolding, tool layer (15+ files); `compat_roots.py` + `ServerSettings.config_root` introduced |
| `C_LOADER.4` | Baseline + config schema purity prep |
| `C_LOADER.5` | `GitHubManager.validate_issue_params()` added as DI-wired validation component in `server.py`; structural guards in place |
| `C_VALIDATOR` | Config startup cross-validation |
| `C_GITCONFIG` | GitConfig DI cleanup |
| `C_CLEANUP` | Flag-day: all remaining config compatibility wrappers removed |
| Cycles 8–10 | QA remediation; all 6 quality gates green |

**Mid-cycle detour:** PR #264 (feature/263 VS Code orchestration) was merged 2026-03-17 and reverted via 3 commits on 2026-03-25 after the artefacts were judged out of scope for branch #257.

**Test result at validation close (2026-03-26):** `2670 passed, 12 skipped, 2 xfailed`. All 6 active quality gates: PASS. Branch pushed to remote.

### Layer 4 — Threshold B MCP Close-out (2026-04-04 to 2026-04-05)

After the config-layer work was complete, issue #257 received a focused Threshold B close-out scoped to the MCP orchestration layer. Planning and design documents (`planning_threshold_b_minimal_refactor.md`, `design_threshold_b_minimal_refactor.md`) framed the remaining blockers before any code was touched.

| Blocker | Resolution |
|---------|------------|
| **B1** — `test_issue39_cross_machine.py` failing | 4 tests updated to respect the pure-query `get_state()` contract; recovery exercised via `transition()`, not direct state mutation |
| **M1a** — Dead legacy gate-dispatch methods | 5 methods removed from `PhaseStateEngine`: `_legacy_planning_exit_gate`, `on_exit_research_phase`, `on_exit_design_phase`, `on_exit_validation_phase`, `on_exit_documentation_phase` |
| **M1b/c** — `"implementation"` hardcoding | Replaced by `cycle_based` config lookup via `IWorkflowGateRunner.is_cycle_based_phase()`; error messages updated to say "cycle-based phase" |
| **M2** — Missing code-style headers | Added to `state_reconstructor.py` and `workflow_gate_runner.py` |

**Focused MCP verification:** `2158 passed, 12 skipped, 2 xfailed, 19 warnings`. File-scoped quality gates on all modified MCP files: PASS. Server restart + `health_check()` = OK.

---

## Lessons Learned

Six concrete lessons extracted and anchored in `research_config_layer_srp.md §17` as the **Gap Prevention Protocol**:

| # | Lesson |
|---|--------|
| **L-1** | Stop/Go is a hard gate — run verification commands; a green test suite is not structural proof |
| **L-2** | Built AND wired — a component with full test coverage but zero consumers has zero production effect |
| **L-3** | Structural tests alongside behavioural tests — at least one structural test per RED phase (grep, ast, isinstance) |
| **L-4** | Highest-risk work first — planning places the God Class in Cycle 1, not avoided until the end |
| **L-5** | No issue-specific values in workflow-level YAML — use `{issue_number}` interpolation |
| **L-6** | Scope-pivot is sometimes the only real fix — the Config Layer SRP overhaul produced better architecture than the PSE recovery plan would have delivered |

---

## Non-blocking Follow-ups

| Issue | Scope |
|-------|-------|
| **#269** | Align phase/cycle transition tool base classes and API contracts |
| **#270** | Remove dead legacy fields (`exit_requires`, `entry_expects`, `allowed_prefixes`) from `workphases.yaml` and `policies.yaml` |

Both are deliberately included in this close-out narrative for completeness. Neither blocks closure.

---

## Related Documentation

- **[docs/development/issue257/TIJDLIJN_ISSUE257.md][related-1]** — full chronological timeline v1.1 (2026-03-03 to 2026-04-06)
- **[docs/development/issue257/research_config_layer_srp.md][related-2]** — config SRP findings + Gap Prevention Protocol
- **[docs/development/issue257/planning.md][related-3]** — 10-cycle planning v3.0 with rules P-1–P-7
- **[docs/development/issue257/GAP_ANALYSE_ISSUE257.md][related-4]** — 8 root-causes from the 10/20 KPI crisis
- **[docs/development/issue257/design_threshold_b_minimal_refactor.md][related-5]** — Threshold B architectural decisions

[related-1]: docs/development/issue257/TIJDLIJN_ISSUE257.md
[related-2]: docs/development/issue257/research_config_layer_srp.md
[related-3]: docs/development/issue257/planning.md
[related-4]: docs/development/issue257/GAP_ANALYSE_ISSUE257.md
[related-5]: docs/development/issue257/design_threshold_b_minimal_refactor.md
