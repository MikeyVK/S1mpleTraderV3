# Recovery Plan Research — Issue #257 Implementation Gaps
<!-- template=research version=8b924f78 created=2026-03-13T21:30Z updated=2026-03-13 -->

**Status:** DRAFT
**Version:** 1.0
**Last Updated:** 2026-03-13

---

## Problem Statement

After 7 implementation cycles, 10 of 20 KPIs are red. The test suite is green (2132 passed)
but the system silently violates its own architectural contracts.

The pattern is consistent across all cycles: **new components were built and tested in
isolation but never wired into the existing system.** Key examples:

- `PhaseContractResolver` — fully built, fully tested, never called from PSE exit-hooks
- `EnforcementRunner` — active, but `delete_file` handler is unregistered → silent no-op
- `phase_contracts.yaml` — hardcoded to `issue257/` paths → breaks for every other branch
- `StateRepository` — injected into PSE, but PSE still instantiates `DeliverableChecker` 3×
  directly, bypassing its own DI boundary
- Config layer — `GitConfig`, `QualityConfig` look like config classes but are compile-time
  constants; the distinction is documented nowhere (see issue #262)

The testsuite is green because tests validate *behaviour*, not *structure*. No test checks:
"Does `PSE.transition()` call the exit-hook registry?" or "Is `PhaseContractResolver` wired?"

---

## Goals

1. Identify the minimum set of changes required to bring all 20 KPIs green
2. Define clear dependency ordering so cycles never build on incomplete previous cycles
3. Establish whether existing architecture is recoverable as-is or requires structural rethink
4. Classify each open item: dead (built, not wired) / mis-wired / config error / naming issue
5. Define verifiable acceptance criteria per recovery cycle (grep/Pyright/test output)

---

## Scope

**In Scope:**
- All 8 root causes (RC-1..RC-8) from GAP_ANALYSE_ISSUE257.md
- 14 open gaps (Gap 1, 2A, 2B, 3a, 3b, 4, 5, 8, 9, 10, 11, 12, 14, 18)
- 4 additional findings (A-01..A-04)
- KPI naming violations (KPI-11/12) and config inconsistency (issue #262)
- Dependency graph between the above items
- Recovery ordering and risk assessment

**Out of Scope:**
- Implementation detail (handled in design + TDD cycles)
- Backend application code (`backend/`)
- Features not mentioned in issue #257 planning
- Performance optimisation

---

## Prerequisites

- [x] GAP_ANALYSE_ISSUE257.md completed (2026-03-13)
- [x] Architectural diagrams 00-10 reviewed and committed
- [x] Issue #262 created (config layer inconsistency)
- [x] Test baseline: 2132 passed, 11 skipped, 2 xfailed

---

## Research Questions

1. **Wiring (highest impact):** What is the exact call chain needed so PSE exit-hooks invoke
   `PhaseContractResolver.resolve()` instead of the current direct dict-traversal?
2. **OCP dispatch:** What is the minimal PSE refactor to replace 6× `if from_phase ==` chains
   with a registry/dispatch pattern that remains backward-compatible with all existing tests?
3. **Directory migration:** Which source files contain hardcoded `.st3/state.json`,
   `.st3/deliverables.json`, `.st3/projects.json` paths? What is the blast radius of moving
   them to `.st3/registries/`?
4. **`{issue_number}` interpolation:** Where exactly does `PhaseContractResolver.resolve()`
   need to receive the current issue number, and how does it currently receive context?
5. **EnforcementRunner handlers:** What is the correct way to register a `delete_file`
   action handler? Is there an existing handler pattern in the registry to follow?
6. **Config layer (issue #262):** Decision required: make `GitConfig` YAML-backed, or rename
   it to `GitConventions` and move to `constants/`? What are the migration risks?
7. **Dead tool detection:** Are there any registered MCP tools that are fully unreachable
   because their underlying component is not wired (beyond `PhaseContractResolver`)?
8. **Stop/Go automation:** What mechanism can enforce that a cycle's verification commands
   are run and their output recorded before the next cycle starts?

---

## Findings

### Classification of Open Items

| ID | Category | Description | Blocked by |
|----|----------|-------------|-----------|
| **CRITICAL — breaks other branches** | | | |
| RC-6 / A-01 | Config error | `phase_contracts.yaml` hardcoded to `issue257/` paths | Nothing |
| **HIGH — system fails silently** | | | |
| RC-2 / Gap 3b | Dead wiring | `PhaseContractResolver` not called from PSE exit-hooks | Needs: PSE OCP refactor |
| A-01 | Dead wiring | `DeliverableChecker` instantiated 3× in PSE instead of injected | Needs: PSE DI cleanup |
| A-01 / Gap 2B | Missing handler | `delete_file` action type unregistered in `EnforcementRunner` | Nothing |
| Gap 2A | Missing rule | No `event_source: merge` rule in `enforcement.yaml` | Needs: delete_file handler |
| RC-7 / A-02 | Encapsulation breach | `cycle_tools` calls private `state_engine._save_state()` | Nothing |
| **MEDIUM — SOLID violations** | | | |
| Gap 8 / RC-4 | OCP violation | PSE: 6× `if from_phase ==` dispatch chains | Nothing (but risky) |
| Gap 10 / RC-4 | DRY violation | PSE: 5× separate `on_exit_*_phase` methods | Needed before PCR wiring |
| Gap 9 / RC-2 | SRP violation | PSE: `DeliverableChecker` 4× instantiated (3 PSE + 1 cycle_tools) | Nothing |
| Gap 5 / RC-3 | Code quality | PSE: f-string in `logger.info()` calls | Nothing |
| **LOW — cleanup** | | | |
| Gap 5 / RC-1 | Dead file | `.st3/projects.json` still exists physically | Nothing |
| Gap 3a / Gap 4 | Path migration | `deliverables.json` + `state.json` → `.st3/registries/` | Needs: blast radius check (RQ3) |
| Gap 12 / A-03 | Naming | `"tdd"` literals in git_tools, cycle_tools, test fixtures | Nothing |
| Gap 14 | Naming | `branch_name_pattern` does not enforce issue-number prefix | Nothing |
| KPI-11/12 | Naming | Tool file names and MCP names inconsistency | Nothing (naming-only change) |
| CFG-2 | Architecture | `issue_tools` imports 6 config classes directly | Nothing (non-blocking) |
| SC-1 | Architecture | `ArtifactManager` no DI for scaffolding classes | Nothing (non-blocking) |
| Issue #262 | Config design | `GitConfig`/`QualityConfig` hardcoded, not YAML-backed | Separate issue |

---

### Dependency Graph

```
[A] .st3/ migration (RQ3 + blast radius)
    → must happen before any path-reference changes
    → Gap 3a, Gap 4, Gap 5

[B] PSE OCP / DRY refactor (RC-4)
    → must happen BEFORE PCR wiring (PSE structure must be stable)
    → Gap 8, Gap 10, Gap 9, Gap 5

[C] PCR wiring into PSE exit-hooks (RC-2)
    → depends on [B] (stable PSE structure)
    → Gap 3b, RC-2

[D] phase_contracts.yaml {issue_number} interpolation (RC-6)
    → depends on [C] (PCR must be called first)
    → A-01, RC-6

[E] EnforcementRunner: delete_file handler + post-merge rule
    → independent of [A..D]
    → A-01 (gap 2B), Gap 2A, Gap 18

[F] cycle_tools cleanup
    → independent; A-02 (_save_state), A-03 (TDD strings)

[G] Naming cleanup (KPI-11/12, Gap 12, Gap 14, Gap 1)
    → independent; no structural changes

[H] Pyright strict sweep
    → depends on all above

[I] Explicit KPI 1-20 verification
    → final gate, depends on all above
```

**Critical path:** A → B → C → D, with E+F+G in parallel.

---

### Risk Assessment per Area

| Area | Risk | Mitigation |
|------|------|-----------|
| PSE OCP refactor (B) | High — 869 lines, heavy test coverage, structural change | TDD: write structural test first (does dispatch call registry?), then refactor |
| PCR wiring (C) | Medium — changes PSE `__init__` + 5 exit-hook methods | Use existing `InMemoryStateRepository` in all new tests; no filesystem |
| .st3/ migration (A) | Medium — blast radius unknown | Run RQ3 (grep for hardcoded paths) before starting |
| phase_contracts interpolation (D) | Low — isolated to `PhaseContractResolver.resolve()` | Existing PCR tests provide safety net |
| EnforcementRunner handlers (E) | Low — additive change | Registration pattern already exists; follow existing handler |
| Naming/literals (G) | Low — find-replace + test rename | Systematic; verify with grep after |

---

### Recovery Order (Proposed Cycles)

| Cycle | Focus | Items resolved | Acceptance criteria (grep/test verifiable) |
|-------|-------|---------------|---------------------------------------------|
| **C8** | .st3/ directory migration | Gap 3a, 4, 5 | `grep -r "\.st3/state\.json"` = 0 in source; `registries/` exists; `projects.json` absent |
| **C9** | PSE structural refactor (OCP + DRY + f-string) | Gap 8, 9, 10, 11, RC-4 | PSE has 0 `if from_phase ==` chains; 1 `on_exit` dispatcher; 0 `logger.info(f"...`)` |
| **C10** | PCR wiring + DeliverableChecker DI | RC-2, A-02, Gap 3b | `grep "PhaseContractResolver" phase_state_engine.py` ≥ 1; `DeliverableChecker()` count = 1 |
| **C11** | phase_contracts {issue_number} interpolation | RC-6, A-01 | `grep "issue257" phase_contracts.yaml` = 0; PCR test with branch `feature/99-test` passes |
| **C12** | EnforcementRunner delete_file + post-merge rule | A-01 (Gap 2B), Gap 2A, Gap 18 | `delete_file` in `_build_default_registry()`; `enforcement.yaml` has `event_source: merge` rule |
| **C13** | cycle_tools cleanup | A-02, A-03, Gap 12 | `_save_state` not in cycle_tools; "TDD" literal count = 0 in cycle/git tools |
| **C14** | Naming, KPI-11/12, Gap 14 | KPI-11, KPI-12, Gap 14 | MCP name audit passes; no singular filenames; branch pattern updated |
| **C15** | Pyright strict + KPI verification | RC-3 (process), KPI 1-20 | All 20 KPIs green; Pyright strict 0 errors on modified modules |

---

## Open Research Questions (to resolve before design)

- **RQ3 answered?** → Run `grep -r "st3/state.json\|st3/deliverables.json\|st3/projects.json" mcp_server/ tests/` to establish blast radius
- **RQ6 decided?** → Choose `GitConfig` fate (YAML-backed vs. `constants/` module) — decision needed for design of C8+
- **RQ7 answered?** → Audit all registered MCP tool names against their handler implementations for additional dead connections
- **RQ8 designed?** → Design the Stop/Go gate mechanism for TDD cycles (automated before cycle N+1 can start)

---

## Related Documentation

- [docs/development/issue257/GAP_ANALYSE_ISSUE257.md](docs/development/issue257/GAP_ANALYSE_ISSUE257.md)
- [docs/development/issue257/planning.md](docs/development/issue257/planning.md)
- [docs/mcp_server/architectural_diagrams/02_workflow_state_subsystem.md](docs/mcp_server/architectural_diagrams/02_workflow_state_subsystem.md)
- [docs/mcp_server/architectural_diagrams/04_enforcement_layer.md](docs/mcp_server/architectural_diagrams/04_enforcement_layer.md)
- [docs/mcp_server/architectural_diagrams/05_config_layer.md](docs/mcp_server/architectural_diagrams/05_config_layer.md)
- [docs/mcp_server/architectural_diagrams/10_config_consumers.md](docs/mcp_server/architectural_diagrams/10_config_consumers.md)
- [GitHub Issue #262 — Config layer: GitConfig/QualityConfig are constants, not YAML-backed](https://github.com/MikeyVK/S1mpleTraderV3/issues/262)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-13 | Agent | Initial research document — full gap consolidation and recovery order |
