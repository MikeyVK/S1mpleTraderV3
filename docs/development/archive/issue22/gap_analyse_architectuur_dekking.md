<!-- docs\development\issue257\gap_analyse_architectuur_dekking.md -->
<!-- template=research version=8b7bb3ab created=2026-03-26T13:43Z updated= -->
# Gap Analysis — Architectuurschendingen vs. Planningsdekking

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-26

---

## Purpose

Volledig overzicht van alle geïdentificeerde architectuurschendingen in de MCP Server codebase (inclusief test suite), gecategoriseerd naar welke geplande refactor-cyclus dekking biedt en welke gaps nog geen geplande dekking hebben.

## Scope

**In Scope:**
Alle bestanden onder mcp_server/ en tests/mcp_server/ getoetst aan ARCHITECTURE_PRINCIPLES.md als absolute wet; categorisering per dekkingsgroep (Config SRP, PSE Refactor, geen dekking)

**Out of Scope:**
backend/, proof_of_concepts/, scripts/, performance-optimalisaties, SHA-256 tamper detection (issue #261), C_SPECBUILDERS (deferred)

## Prerequisites

Read these first:
1. ARCHITECTURE_PRINCIPLES.md gelezen als wetgevend document
2. planning.md v3.0 (Config Layer SRP — C_SETTINGS.1/2, C_LOADER.1–5, C_VALIDATOR, C_GITCONFIG, C_CLEANUP) volledig doorgenomen
3. planning_pse_v1.0_archived.md (PSE Refactor — Cycles 1–6 + 5.1) volledig doorgenomen
4. GAP_ANALYSE_ISSUE257.md (10/20 KPIs rood, RC-1–RC-8) doorgenomen
5. Productie codebase systematisch gescand op patronen: from_file, if-chain, DIP, Law of Demeter, CQS, DRY, frozen models
---

## Problem Statement

De gap-analyse uit de vorige sessie identificeerde 20+ architectuurschendingen in mcp_server/ en tests/. Onduidelijk was welke gaps al gedekt worden door de geplande Config Layer SRP refactor (C_SETTINGS, C_LOADER, C_VALIDATOR, C_GITCONFIG, C_CLEANUP) en de PSE Refactor (Cycles 1–6 + Cycle 5.1), en welke gaps helemaal geen geplande dekking hebben.

## Research Goals

- Alle geïdentificeerde architectuurschendingen categoriseren: gedekt door Config SRP, gedekt door PSE Refactor, of geen dekking
- Per ongedekte gap bepalen welk principe geschonden wordt en waarom het buiten bestaande planning valt
- Prioritering van ongedekte gaps als input voor nieuwe TDD-cycli of backlog items

---

## Background

Issue #257 bevat twee parallelle refactor-stromen op branch feature/257-reorder-workflow-phases. De Config Layer SRP refactor is gepland in planning.md v3.0 (10 cycli). De PSE Refactor is gepland in de gearchiveerde planning_pse_v1.0_archived.md (6 cycli + Cycle 5.1). Beide plannen zijn opgesteld vóór de uitgebreide codebase gap-analyse van 2026-03-26.

---

## Findings

## Methode

Systematische scans uitgevoerd op mcp_server/ en tests/mcp_server/ met grep-patronen voor:
- `from_file(|reset_instance(` — singleton/self-loading patronen
- `if.*phase.*==.*['"]` — hardcoded fase-namen (OCP)
- `DeliverableChecker(workspace_root` — directe instantiatie in exit-hooks (DIP)
- `_save_state|_state_repository` — private method access en state I/O (Law of Demeter, CQS)
- `Manager()` inline constructie in tool execute() (DIP)
- `frozen=True|model_config.*frozen` — frozen model compliance
- `ScopeDecoder()|ScopeEncoder()` — werkmap-injectie

Resultaten zijn gekruist met de deliverables uit planning.md v3.0 en planning_pse_v1.0_archived.md.

---

## Groep A — Gedekt door Config Layer SRP

| # | Gap | Bestand(en) | Cyclus | Deliverable id |
|---|-----|-------------|--------|----------------|
| A1 | 9 legacy config files: `from_file()` + `reset_instance()` | `config/workflows.py`, `scope_config.py`, `scaffold_metadata_config.py`, `project_structure.py`, `operation_policies.py`, `milestone_config.py`, `issue_config.py`, `git_config.py`, `contributor_config.py` | C_LOADER.3 (prod) + C_LOADER.4 (tests) + C_LOADER.5 (grep-closure) | `c_loader_3.tools_rewired`, `c_loader_5.grep_closure` |
| A2 | Duplicate schema classes | `config/workflows.py` vs `config/schemas/workflows.py`; `config/label_config.py` vs `config/schemas/label_config.py` | C_LOADER.4/5 | `c_loader_4.self_loading_deleted_green` |
| A3 | Inline fallback Manager() constructie in 5 tool-files | `discovery_tools.py`, `quality_tools.py`, `git_pull_tool.py`, `git_fetch_tool.py`, `git_analysis_tools.py`, `scaffold_artifact.py` | C_LOADER.3 | `c_loader_3.tools_rewired` |
| A4 | `qa_manager.py` `QualityConfig` self-loading path | `managers/qa_manager.py` | C_LOADER.3 | `c_loader_3.managers_rewired` |
| A5 | `git_config.py` schema `tdd_phases` DEPRECATED field (DRY — SSOT in workphases.yaml) | `config/schemas/git_config.py` | C_GITCONFIG | `c_gitconfig.no_python_defaults` |
| A6 | `config/template_config.py` misplaatst in config/ i.p.v. utils/ | `config/template_config.py` | C_CLEANUP | `c_cleanup.template_config_moved` |
| A7 | Hardcoded server version `"1.0.0"` in settings (SSOT) | `config/schemas/settings.py` | C_CLEANUP | `c_cleanup.server_version_metadata` |
| A8 | PSE `__init__` swallows ontbrekende `workphases.yaml` silently (Fail-Fast §§10) | `managers/phase_state_engine.py` | C_LOADER.5 | Composition root roept `ConfigLoader.load_workphases_config()` die `ConfigError` gooit vóór PSE construct |

---

## Groep B — Gedekt door PSE Refactor

| # | Gap | Bestand(en) | PSE Cyclus | Design Decision |
|---|-----|-------------|-----------|----------------|
| B1 | `transition()` hardcoded if-chain op 6 fase-namen (OCP §3) | `managers/phase_state_engine.py` L190–227 | Cycle 1 (H+G) | H1–H4, G1–G2 |
| B2 | `on_exit_*` methods: directe dict-traversal i.p.v. PCR delegering (SRP §2) | `managers/phase_state_engine.py` — 5 on_exit methoden | Cycle 3 (A+D) | A1, A3, A5, A6, D1–D5 |
| B3 | `DeliverableChecker` 4× geïnstantieerd in `on_exit_*` (DIP §6) | `managers/phase_state_engine.py` | Cycle 3 (D) | D1–D5 |
| B4 | `get_state()` roept `_save_state()` in auto-recovery pad (CQS §5) | `managers/phase_state_engine.py` L356 | Cycle 2 (E) | E1–E4 |
| B5 | `ScopeDecoder` in PSE `__init__` zonder injectie | `managers/phase_state_engine.py` | Cycle 2 (B) | B3 |
| B6 | `cycle_tools.py` `_extract_issue_number()` duplicaat (DRY §11) | `mcp_server/tools/cycle_tools.py` L161 + L356 | Cycle 1 (I3) + Cycle 5.1 (F6.3) | I3, F6.3 |
| B7 | `cycle_tools.py` `_create_engine()` in `execute()` (DIP §6) | `mcp_server/tools/cycle_tools.py` L72–73 + L251–252 | Cycle 5.1 (F6.1) | F6.1 |
| B8 | `cycle_tools.py` `state_engine._save_state()` private method call (Law of Demeter §7) | `mcp_server/tools/cycle_tools.py` L141 + L306 | Cycle 2 (E) + Cycle 4 (J) | E1–E4, J1–J4 |
| B9 | `enforcement_runner.py` ontbrekende `delete_file` handler + post-merge rule | `managers/enforcement_runner.py` | Cycle 5 (F) + Cycle 6 | F1–F5 |

---

## Groep C — Geen geplande dekking ⚠️

| # | Gap | Bestand(en) | Principe | Waarom niet gedekt |
|---|-----|-------------|----------|--------------------|
| C1 | **`qa_manager.py` `_save_state_json()`** schrijft `state.json` direct via `path.write_text()` — duplciaat van `StateRepository` verantwoordelijkheid | `managers/qa_manager.py` L51–80 | SRP §2 + SSOT §11 | C_LOADER.3 rewired alleen `QualityConfig` injectie; PSE Cycle 2 extraheerrde file I/O uit PSE maar noemt QAManager niet. Geen enkele deliverable zet QAManager op `IStateRepository`. |
| C2 | **`milestone_tools.py` inline `GitHubManager()` fallback** in drie tool-klassen | `mcp_server/tools/milestone_tools.py` | DIP §6 | C_LOADER.3 expliciete file list bevat `milestone_tools.py` niet. C_LOADER.5 grep-check zoekt alleen op `from_file/reset_instance`, niet op inline `Manager()` constructie. |
| C3 | **`ScopeDecoder()` zonder path-injectie** in `discovery_tools.py` L268 en `project_manager.py` L460 — interne `Path.cwd()` afhankelijkheid | `mcp_server/tools/discovery_tools.py`, `mcp_server/managers/project_manager.py` | DIP §6 | C_LOADER.3 rewired `discovery_tools.py` voor config loading maar de `ScopeDecoder()` instantiatie met impliciete `cwd` is een aparte DIP-overtreding. PSE Cycle 2 behandelt alleen `IStateReader`-consumenten. |
| C4 | **Hardcoded `"implementation"` in `phase_contract_resolver.py` L116** | `managers/phase_contract_resolver.py` | OCP §3 | PSE plan richt zich op de if-chain in PSE `transition()`; PCR's interne fase-naam is niet als deliverable opgenomen. |
| C5 | **Hardcoded `"implementation"` in `enforcement_runner.py` L186** | `managers/enforcement_runner.py` | OCP §3 | PSE Cycle 5 bouwt EnforcementRunner maar noemt de hardcoded fase-naam niet expliciet. |
| C6 | **`schemas/contexts/commit.py` `frozen=False`** — context DTO niet immutable | `mcp_server/schemas/contexts/commit.py` | §8 Frozen Models | Nergens in planning of archives vermeld. Intentioneel of omissie — niet geverifieerd. |

---

## Prioritering ongedekte gaps

| Prioriteit | Gap | Risico |
|------------|-----|--------|
| 🔴 Hoog | **C1** — QAManager schrijft state.json naast StateRepository | Twee klassen bezitten hetzelfde bestand; state.json kan inconsistent raken bij gelijktijdige writes |
| 🟠 Middel | **C2** — milestone_tools inline GitHubManager() | DIP-overtreding, maar functioneel geïsoleerd; pas zichtbaar na C_LOADER.5 grep-closure |
| 🟠 Middel | **C3** — ScopeDecoder zonder path-injectie | Breekt unit-testbaarheid; cwd-afhankelijkheid maskeert fouten in CI |
| 🟡 Laag | **C4** — PCR hardcoded "implementation" | OCP-overtreding maar klein; pas relevant als fase-namen in config wijzigen |
| 🟡 Laag | **C5** — EnforcementRunner hardcoded "implementation" | Zelfde als C4 |
| 🔵 Onbekend | **C6** — commit.py frozen=False | Intentioneel vs. omissie vereist verificatie bij de auteur |

## Open Questions

- ❓ C1: Moet QAManager op IStateRepository worden gezet in een aparte sub-cyclus binnen C_CLEANUP, of verdient het een eigen cyclus?
- ❓ C2: Moet milestone_tools.py worden toegevoegd aan de C_LOADER.3 blast-radius lijst (retroactief planning update)?
- ❓ C3: Is ScopeDecoder workspace_root injectie onderdeel van PSE Cycle 2 (IStateReader) of een apart item?
- ❓ C6: Is commit.py frozen=False intentioneel (muterend context object) of een omissie?


## Related Documentation
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md — bindende wet][related-1]**
- **[docs/development/issue257/planning.md v3.0 — Config Layer SRP planning][related-2]**
- **[docs/development/issue257/#archive/planning_pse_v1.0_archived.md — PSE Refactor planning][related-3]**
- **[docs/development/issue257/GAP_ANALYSE_ISSUE257.md — eerdere KPI gap analyse][related-4]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md — bindende wet
[related-2]: docs/development/issue257/planning.md v3.0 — Config Layer SRP planning
[related-3]: docs/development/issue257/#archive/planning_pse_v1.0_archived.md — PSE Refactor planning
[related-4]: docs/development/issue257/GAP_ANALYSE_ISSUE257.md — eerdere KPI gap analyse

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |