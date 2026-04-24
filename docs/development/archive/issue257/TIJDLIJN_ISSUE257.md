<!-- docs\development\issue257\TIJDLIJN_ISSUE257.md -->
<!-- template=research version=8b7bb3ab created=2026-03-27T06:52Z updated=2026-03-27 -->
# Issue #257 — Chronologische tijdlijn van concept tot voltooiing

**Status:** DOCUMENTATION CLOSE-OUT
**Version:** 1.1
**Last Updated:** 2026-04-06

---

## Samenvatting

Issue #257 doorliep een lange en meervoudig-pivoterende ontwikkeling van 2026-03-03 t/m 2026-04-06. Wat begon als een smalle `workflows.yaml`-volgordewijziging
(design voor planning) groeide eerst uit tot een volledige refactoring van de
`mcp_server/config/`-architectuur en eindigde daarna in een gerichte Threshold B close-out voor de MCP workflow-orchestratie.

**Vijf grote fases:**

| Fase | Periode | Kern-resultaat |
|------|---------|----------------|
| **PSE-architectuur** | 03-03 t/m 03-13 | Config-First PSE met StateRepository, PhaseContractResolver, EnforcementRunner — 7 TDD-cycli |
| **Gap-analyse + Recovery** | 03-13 | 10/20 KPIs rood; 8 root-causes gevonden; recovery research |
| **Config Layer SRP** | 03-14 t/m 03-26 | Volledig nieuwe scope: ConfigLoader centralisatie, singleton-eliminatie, 10 cycli (C_SETTINGS.1/2 + C_LOADER.1-5 + opschoon) |
| **Threshold B close-out** | 04-04 t/m 04-05 | QA blockers weggewerkt; cycle-based overgangspad config-driven; MCP-verify groen; server restart OK |
| **Documentatie + follow-ups** | 04-06 | Tijdlijn, issue-body close-out, en follow-up context voor issues #269 en #270 voorbereid |

**Eindtoestand op 2026-04-06:** De oorspronkelijke config-pivot was al afgerond, maar issue #257 kreeg daarna nog een gerichte MCP-close-out. `get_state()` is nu een pure query, cycle-overgangen zijn config-driven via `cycle_based`, de relevante MCP-validatie is groen, en resterende niet-blokkerende restschuld is expliciet doorgeschoven naar follow-up issues #269 en #270.

---

## Tijdlijn — Overzicht

| Datum | Mijlpaal | Kop-commit of document |
|-------|----------|------------------------|
| 2026-03-03 | Origineel issue #257 aangemaakt; `research_legacy.md` geschreven (smalle scope) | `research_legacy.md` v1.0 |
| 2026-03-03 | QA sessie 1: impact analyse, scope-grens #257/#258/#259 vastgesteld | `SESSIE_OVERDRACHT_QA_20260303.md` |
| 2026-03-04 | QA sessie 2: SOLID-richting bevestigd, Expected Results als contract | `SESSIE_OVERDRACHT_QA_20260304.md` |
| 2026-03-11 | Branch-commits starten; alle design-beslissingen A-K vastgelegd in research | `de6cf5d` t/m `8de6f61` |
| 2026-03-12 | Design goedgekeurd, `design.md` gestuurd; `planning.md` v1.0 scaffold; TDD C1-C3 | `2243bf3` t/m `8e72572` |
| 2026-03-13 | TDD C4-C7; gap-analyse: 10/20 KPIs rood; recovery research | `fd48c39` t/m `1cc482b` |
| 2026-03-13 | QA sessie 3: NOGO oordeel; 8 root-causes + 12 gaps gedocumenteerd | `SESSIE_OVERDRACHT_QA_20260312.md` v1.4 |
| 2026-03-14 | **Scope-pivot:** Config Layer SRP research (`research_config_layer_srp.md` v1.0-v1.9) | `2f676b8` t/m `37f9d4a` |
| 2026-03-14 | `planning.md` v1.0 -> v2.0 -> v3.0; 10-cycle structuur vastgesteld | `24a08bf` t/m `25218b1` |
| 2026-03-14 | C_SETTINGS.1: singleton verwijderd, `Settings.from_env()` ingedraad | `158664b` t/m `967647d` |
| 2026-03-14 | C_SETTINGS.2: workflow singleton verwijderd, DI volledig | `42db228`, `37f9d4a` |
| 2026-03-15 | C_LOADER.1-.2: config loader migratie start, docs hersteld | `1b20c67` |
| 2026-03-16 | C_LOADER.3 NOGO: structurele closure nog niet gehaald | `1aeceae`, `074ade8` |
| 2026-03-17 | C_LOADER.4 baseline; PR #264 (feature/263) samengevoegd | `a3475940`, `706910b` |
| 2026-03-17-18 | VS Code orchestratie-documenten (issue #263 artefacten) | `8e797ba` t/m `77d0c21` |
| 2026-03-25 | PR #264 reverts (3 commits) + issue #263-artefacten opgeruimd | `75647674` t/m `d2418798` |
| 2026-03-25 | C_LOADER.5: `GitHubManager.validate_issue_params()` RED + GREEN | `e44ee8e`, `435eca8e` |
| 2026-03-25-26 | Cycles 8-10: flag-day config-wrapper cleanup | `bce01880` t/m `487e905` |
| 2026-03-26 | QA remediation; alle quality gates groen | `408789c` |
| 2026-03-26 | Validatiefase: `pytest_plugins` fix + import-sort fixes | `50ae9cd`, `867bf8c` |
| 2026-03-26 | Branch gepusht naar remote; worktree clean; **2670 tests groen** | `867bf8c` gepusht |
| 2026-04-04 | Threshold B minimal-refactor plan/design opnieuw gekaderd; cycle 5 enforcement cleanup voorbereid | `planning_threshold_b_minimal_refactor.md`, `design_threshold_b_minimal_refactor.md` |
| 2026-04-05 | QA blocker-overdracht verwerkt; B1, M1a, M1b/c en M2 opgelost; focused MCP verify groen | `SESSIE_OVERDRACHT_20260405_QA_BLOCKER.md`, `3605913` |
| 2026-04-05 | Server herstart en health-check groen; branch naar validation en daarna documentation getransitioned | validation/documentation transitions |
| 2026-04-06 | Follow-up issues #269 en #270 expliciet meegenomen in documentatiefase-close-out | issues `#269`, `#270` |

---

## Fase 0 — Aanloop: smal issue, brede implicaties (2026-03-03)

### Context

Issue #257 werd aangemaakt vanuit de observatie dat de huidige workflow-volgorde
`research -> planning -> design -> tdd` epistemisch achteruitloopt: planning voor design betekent
dat deliverables worden vastgesteld **voordat** de architectuur bekend is.
`planning_deliverables.design` als sub-sleutel was een code-niveau symptoom hiervan.

### research_legacy.md — scope v1.0 (2026-03-03)

Het eerste researchdocument (`docs/development/issue257/research_legacy.md`, nu gearchiveerd)
definieerde een smalle scope:

- **KPI 1-8:** fasevolgorde corrigeren in `workflows.yaml`; `heading_present` gate op
  `## Expected Results` in research; `file_glob` gate op design document;
  OCP registry in `PhaseStateEngine`; DIP DeliverableChecker-injectie; DRY per-phase helper;
  logging f-string cleanup
- **Scopegrens vastgesteld:** #257 levert de OCP-infrastructuur die `content_contract` als
  pluggable gate type mogelijk maakt; #258 en #259 bouwen hierop verder

**Scope op dit punt:** enkele werkdagen PSE-refactoring + config-YAML-patches.

### QA-sessies (2026-03-03 en 2026-03-04)

`SESSIE_OVERDRACHT_QA_20260303.md` — eerste QA-analyse:

- Impact van fase-herordening op workflow/workphases/template-keten gedocumenteerd
- Buitenscope #258/#259 helder afgebakend

`SESSIE_OVERDRACHT_QA_20260304.md` — aangescherpte QA-conclusies:

- SOLID-richting bevestigd (OCP registry, DIP checker, SRP/DRY helper, logging)
- Expected Results als formeel research-exitcontract geformuleerd
  (KPI + bewijs + verificatie + eigenaarfase)
- Aanbevolen implementatievolgorde: config-first -> schema-cleanup -> engine refactor -> tests -> QA

---

## Fase 1 — Research & Design: scope-explosie + alle beslissingen (2026-03-11 t/m 2026-03-12)

### Sessie-overdracht 11 maart

Op 11 maart was de branch nog in de research-fase. De research had zich **materieel uitgebreid**
ten opzichte van de smalle scope uit maart 3. Een tweede researchdocument
(`research_config_first_pse.md`) was gecreeerd met een volledige Config-First PSE-scope:
44 SOLID-schendingen, F1-F19, per-file schendingstabel.

De fase-overgang naar design was bewust uitgesteld tot de volgende sessie.

**Kernbeslissingen vastgesteld op 11 maart:**

| Beslissing | Detail |
|-----------|--------|
| Config-First als leidend principe | Alle business rules naar YAML |
| `.st3/` split | `config/` (statisch) + `registries/` (runtime) |
| `phase_deliverables.yaml` | Nieuw config met `contracts[workflow][phase]` |
| `deliverables.json` | Issue-specifiek runtime-register |
| `projects.json` abolished | Metadata naar `state.json`; Mode 2 via git only |
| `PhaseDeliverableResolver` | Nieuwe SRP-class |
| `StateRepository` | Atomische schrijfverantwoordelijkheid uit PSE |
| Fasevolgorde | `research -> design -> planning -> tdd` |

Scope uitgebreid naar 11 items (mapstructuur, YAML-configs, PSE OCP/DIP/SRP, StateRepository,
branch_name_pattern, branch_types SSOT).

### Design-beslissingen vastgelegd (commits 2026-03-11 t/m 2026-03-12)

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `de6cf5d` | 03-11 | docs(P_RESEARCH): Expected Results (KPI 1-17) en handover matrix |
| `1ed9f13` | 03-11 | docs(P_RESEARCH): F23-F25, BC decisions, test suite scope (K), issue #260 ref |
| `8de6f61` | 03-11 | docs(P_DESIGN): beslissingen A1, A3, A5, A6, D1, E1, H1, J1, K2, K3 |
| `75fbf6b` | 03-12 | docs(P_DESIGN): B1-B5, C2-C4, D2-D5, E2-E4, F1-F4, G3, H2-H4 |
| `29f1cac` | 03-12 | docs(P_DESIGN): F5 (transition vs force_transition semantics, Optie C) |
| `9cf35ab` | 03-12 | docs(P_DESIGN): G1-G2, I1-I3, J2-J4 — alle A-K open vragen beantwoord |
| `170ce4a7` | 03-12 | docs(P_DESIGN): I1-I3, J2-J4 corrections (I3->GitConfig.extract_issue_number) |
| `c77374` | 03-12 | docs(P_DESIGN): A1/A6/B2/B5/C3/E1/E4/I2/J2 — volledig met user besproken |
| `f02f58` | 03-12 | docs(P_DESIGN): coding standards update (Gate 7 body + architectural rejection criteria) |
| `e62e539` | 03-12 | docs(P_DESIGN): design.md aangemaakt + research bevroren |
| `47a91aa` | 03-12 | docs(P_DESIGN): design.md gestuurd via template (v5827e841) |
| `2243bf3` | 03-12 | docs(P_DESIGN): design goedgekeurd — Mermaid diagram, lifecycle->enforcement term |

### Wat design.md vastlegde (PSE Config-First Architecture v1.0)

Het goedgekeurde `design.md` (nu gearchiveerd) definieerde:

- **`phase_contracts.yaml`** — workflow-level gate-contracten met Fail-Fast validatie
- **`StateRepository` + `AtomicJsonWriter`** — SRP-extractie uit PSE; atomische JSON-schrijfoperaties
- **`PhaseContractResolver`** — combineert config + registry naar `list[CheckSpec]`
- **`EnforcementRunner`** — vervangt HookRunner voor phase- + tool-enforcement
- **ISP-split:** `IStateReader` (read-only) + `IStateRepository` (read+write)
- **`tdd` -> `implementation`** — flag-day rename, geen alias, geen migratielaag
- **`projects.json` abolished** — `state.json` per branch als SSOT
- **`GitConfig.extract_issue_number(branch)`** — centraal branchnaam-parsing

---

## Fase 2 — Planning + PSE TDD Cycles 1-7 (2026-03-12 t/m 2026-03-13)

### Planning scaffold (2026-03-12)

| Commit | Inhoud |
|--------|--------|
| `5ce5744` | docs(P_PLANNING): scaffold planning.md (template v130ac5ea) met 6 TDD-cycli |
| `66b3952` | docs(P_PLANNING): `save_planning_deliverables` payload appendix |
| `3e996f9` | docs(P_PLANNING): concrete deliverables+validates appendix (D1-D6) |
| `0ced90e` | docs(P_PLANNING): deliverables opgeslagen voor issue #257 — 6 TDD cycles + fases |

### Cycle 1 — Phase rename + deliverables migratie (2026-03-12)

**Doel:** `tdd` -> `implementation` flag-day; `GitConfig.extract_issue_number()` introduceren;
`workflow_config.py` verwijderen (duplicate WorkflowConfig); `projects.json` verdwijnt.

| Commit | Sub-fase |
|--------|----------|
| `dbe8c15` | C1_REFACTOR: cycle 1 afronden (phase rename + deliverables migratie) |

**QA oordeel:** GO — `workflow_config.py` verwijderd, `GitConfig.extract_issue_number()` bestaat.

### Cycle 2 — StateRepository + AtomicJsonWriter (2026-03-12)

**Doel:** `StateRepository`-laag extraheren uit PSE; `BranchState` frozen=True; atomische schrijfoperaties.

| Commit | Sub-fase |
|--------|----------|
| `b5e2972` | C2_RED: state repository contracts + atomic writer tests |
| `f18fc68` | C2_GREEN: state repository + atomic writer primitives geimplementeerd |
| `22ec2ee` | C2_REFACTOR: state repository geinjinjecteerd in PSE |
| `68b767e` | C2_REFACTOR: BranchState API aligned, legacy workflow config verwijderd |

**QA oordeel:** GO — `FileStateRepository` + `InMemoryStateRepository` aanwezig,
`BranchState` frozen, PSE unit tests gebruiken repository-injectie.

### Cycle 3 — PhaseContractResolver + config loader (2026-03-12)

**Doel:** `phase_contracts.yaml` met per-workflow x fase gate-contracten;
`PhaseContractResolver` SRP-class introduceren.

| Commit | Sub-fase |
|--------|----------|
| `a1e5d68` | C3_RED: phase contract resolver red tests |
| `42fa656` | C3_GREEN: phase contract resolver + config loader geimplementeerd |
| `ad066ca` | C3_REFACTOR: typing + formatting verfijnd |
| `8e72572` | C3_REFACTOR: phase contract merge-semantiek + config naming gealigned |

**QA oordeel:** GO — `PhaseContractResolver`, `PhaseConfigContext`, `CheckSpec` aanwezig;
fail-fast validatie op `cycle_based=true` + lege `commit_type_map`; A6 merge-semantiek correct.

### Cycle 4 — Git tool commit-type resolution (2026-03-13)

**Doel:** `build_commit_type_resolver()` composition root in `git_tools.py`;
legacy `phase=` kwarg definitief verboden; `PSE.get_state(branch) -> BranchState` als publieke methode.

| Commit | Sub-fase |
|--------|----------|
| `fd48c39` | C4_RED: cycle 4 git tool commit contract tests |
| `f4f6df4` | C4_GREEN: tool-laag commit type resolution geimplementeerd |
| `b0fbe6a` | C4_REFACTOR: workflow regressions + Windows state writes gealigned |
| `d5d9da5` | C4_REFACTOR: legacy test-schuld verwijderd, handover issue257 bijgewerkt |
| `df3dff8` | C4_REFACTOR: resterende workflow test-schuld gemigreerd |
| `748656f` | C4_REFACTOR: typed BranchState test-callers gemigreerd |

**QA oordeel:** GO — volledige testsuite **2123 passed**; J1-J4 bevestigd.
2 pre-existing test-failures gedocumenteerd (buiten Cycle 4 scope).

### Cycle 5 — EnforcementRunner + dispatch hook (2026-03-13)

**Doel:** `EnforcementRunner` implementeren; dispatch hook integratie.

| Commit | Sub-fase |
|--------|----------|
| `1de388b` | C5_RED: enforcement runner + dispatch hook tests |
| `d2c8872` | C5_GREEN: enforcement runner + dispatch hook integratie |
| `a3d4da6` | C5_REFACTOR: types + dispatch test harness gepolijst |

### Cycle 5.1 / Additionele F6 — cycle_tools refactor (2026-03-13)

**Doel:** `transition_tools.py` hernoemen naar `cycle_tools.py`; shared base; DIP/DRY-verbetering.

| Commit | Inhoud |
|--------|--------|
| `dd7b588` | planning: Cycle 5.1 (F6) toegevoegd aan design, planning, projects.json |
| `f2c7868` | F6.6: file rename (transition_tools -> cycle_tools) in planning + projects.json |
| `9bdb5df` | refactor: cycle enforcement hooks + cycle tool refactor afgerond |
| `e10c60c` | refactor: dead cycle settings export verwijderd; legacy cycle tests hernoemd |

### Cycle 6/7 — Atomic deliverables + branch init (2026-03-13)

| Commit | Inhoud |
|--------|--------|
| `2aa9309` | C7_GREEN: atomic deliverables writes + state file tracking |
| `2600601` | C7_GREEN: warn on uncommitted state during branch init |
| `c0cf3d5` | C7_REFACTOR: cycle 7 state tracking cleanup |
| `fec31d0` | C7_REFACTOR: issue 257 implementation state hersteld |

---

## Fase 3 — Gap Analyse + Recovery Research (2026-03-13)

### Crisis: 10 van 20 KPIs rood

Na 7 TDD-cycli was de testsuite groen (2132 passed), maar een grondige KPI-check toonde
dat **10 van de 20 KPIs rood** stonden. De testsuite controleerde gedrag, niet structuur.

**Cruciaal inzicht:** componenten waren gebouwd en getest in isolatie, maar **nooit ingedraad**
in het bestaande systeem.

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `1a602ce` | 03-13 | docs: QA sessie overdracht — 10/20 KPIs rood, 12 gaps geidentificeerd |
| `89adc38` | 03-13 | docs: gap analysis document aangemaakt (root causes, cycle DoD review, recovery plan) |
| `d5ec756` | 03-13 | docs(P_RESEARCH): architectuur recovery plan + scaffolding/config diagrammen, issue #262 |
| `1cc482b` | 03-13 | docs(P_RESEARCH): originele research hersteld als research_legacy.md |

### GAP_ANALYSE_ISSUE257.md — 8 root-causes (RC-1 t/m RC-8)

| RC | Kern |
|----|------|
| **RC-1** | Stop/Go criteria niet als gate geevalueerd — `.st3/projects.json` bestond nog na Cycle 1 |
| **RC-2** | Componenten gebouwd maar niet ingedraad (`PCR` nooit aangeroepen vanuit PSE exit-hooks) |
| **RC-3** | Geen structurele tests — testsuite controleerde gedrag, niet systeem-structuur |
| **RC-4** | PSE (869+ regels) — hoogste-risico object — systematisch vermeden in TDD |
| **RC-5** | `.st3/` directory-migratie half gedaan: `config/` aangemaakt, `registries/` niet |
| **RC-6** | `phase_contracts.yaml` hardcoded op `issue257/` paden — breekt alle andere branches |
| **RC-7** | `cycle_tools.py` roept private `state_engine._save_state()` aan (encapsulatieschendig) |
| **RC-8** | `planning.md` als architectuurdocument gelezen, niet als executable specification |

### Proposed Recovery Cycles C8-C15

Het recovery-onderzoek definieerde een herstelplan voor de PSE-architectuur.
**Maar dit leidde tot de scope-pivot in Fase 4.**

---

## Fase 4 — Scope-Pivot: Config Layer SRP Research (2026-03-14)

### De grote pivot: PSE-reparatie -> Config-architectuur

Op 14 maart werd de scope fundamenteel herzien. Uit de recovery research bleek dat de
root cause dieper lag dan de PSE-implementatie: **de gehele `mcp_server/config/`-laag miste
een centrale ConfigLoader, ConfigValidator, en correcte SRP-scheiding.** De PSE-herstelcycli
werden verlaten ten gunste van een grondiger aanpak.

`research_config_layer_srp.md` werd geschreven in 9 iteraties.

| Commit | Datum | Versie | Inhoud |
|--------|-------|--------|--------|
| `2f676b8` | 03-14 | v1.0 | Rewrite config-layer-srp research (F1-F9, D1-D7) — volledig in Engels |
| `2d9f5af` | 03-14 | v1.2 | F10 test isolation zones, F11 spec-builders, F2 validator layers |
| `b4d395a` | 03-14 | v1.3 | F12/F13, D9/D10 hard break, design questions resolved |
| `05bf280` | 03-14 | v1.4 | F14 config coverage map, F15 naming audit |
| `d3a5473` | 03-14 | v1.5 | TOC, open questions section, 15-schema count verduidelijkt |
| `f711af5` | 03-14 | v1.6 | OQ1-OQ5 resolved, OQ6 field_validator break |
| `0b1b362` | 03-14 | v1.7 | F16 volledige blast radius, D15 GitHubManager validatie |
| `2d72deb` | 03-14 | v1.8 | §12 conflict gefixed, F16 testinventaris voltooid |
| `24a08bf` | 03-14 | v1.9 | F16 count gecorrigeerd (8->15 test/fixture files) |

### Kernbevindingen (vereenvoudigd)

| Finding | Kern |
|---------|------|
| **F1** | Geen centrale ConfigLoader — elke schema-class laadt zichzelf (SRP-schending) |
| **F2** | Geen ConfigValidator — geen startup-validatie van config-consistentie |
| **F3** | `mcp_config.yaml` verwijst naar een niet-bestaand bestand; `mcp.json` is de standaard |
| **F4** | Python defaults spiegelen YAML exact (DRY-schending, dead code) |
| **F5** | Value conflict in `quality_config.py` vs `quality.yaml` |
| **F7** | Config vs Constants grens niet gedefinieerd |
| **F12** | Module-level singletons met import-time side-effects overal |
| **F16** | Volledige blast radius C_LOADER hard-break: 15+ schema-classes, tools, managers, core, scaffolders |

### Kernbeslissingen (D1-D15)

| Beslissing | Kern |
|-----------|------|
| **D2** | `ConfigLoader` ontvangt `config_root` via constructor (path injection) |
| **D9** | `ClassVar`-singletons op alle schema-classes verwijderd |
| **D10** | Hard break: alle `from_file()` / `load()` / `reset_instance()` direct verboden na C_LOADER |
| **D13** | `MCP_LOG_LEVEL` -> `LOG_LEVEL` env-var rename |
| **D14** | PSE two-step migratie: PSE-wrapper blijft tijdelijk, verwijderd in C_LOADER |
| **D15** | `GitHubManager.validate_issue_params()` als slotcyclus (C_LOADER.5) |

---

## Fase 5 — Planning Rewrites + C_SETTINGS (2026-03-14)

### planning.md: v1.0 -> v2.0 -> v3.0

| Commit | Versie | Kern |
|--------|--------|------|
| `1088c02` | v2.0 | PSE planning gearchiveerd; 12 QA-condities (integration surface, structural RED tests, zone assignments) |
| `1955156` | v3.0 | C_SETTINGS gesplitst in .1/.2; C_LOADER gesplitst in .1-.5; deliverables manifest per cyclus |
| `25218b1` | — | PSE `planning_deliverables` vervangen door 10-cycle config SRP structuur; cycle counter gereset |

**planning.md v3.0** definieerde 7 globale regels (P-1 t/m P-7):

| Regel | Kern |
|-------|------|
| **P-1** | No Partial Migration — flag-day cycles volledig af alvorens de volgende start |
| **P-2** | Forbidden Legacy Patterns — `from_file()`, `load()`, `reset_instance()`, singletons verboden na C_LOADER |
| **P-3** | Generic Config Only — geen issue-specifieke waarden in workflow-level YAML |
| **P-4** | Built and Wired — elk component: bestaat + min. 1 consumer via server.py + grep=0 residuals + min. 1 integratietest |
| **P-5** | Test Zones Enforced — Zone 1 (config), Zone 2 (spec/builder), Zone 3 (managers/tools/core) |
| **P-6** | Env-Var Renames als blast-radius items |
| **P-7** | Single Source of Truth — dit document is de enige planningsreferentie |

### Cycle tabel (10-cycle structuur)

```
C_SETTINGS.1 -> C_SETTINGS.2
                               -> C_LOADER.1 -> C_LOADER.2 -> C_LOADER.3 -> C_LOADER.4 -> C_LOADER.5
                                                                                                -> C_VALIDATOR
                                                                                                -> C_GITCONFIG
                                                                                                -> C_CLEANUP
```

### C_SETTINGS.1 — Settings singleton verwijderd (2026-03-14)

**Doel:** `Settings.load()` singleton vervangen door `Settings.from_env()`; `MCP_LOG_LEVEL -> LOG_LEVEL`;
DI-stub ingedraad in `server.py`.

| Commit | Inhoud |
|--------|--------|
| `158664b` | feat(P_TDD_SP_C1_GREEN): Settings.from_env(), LOG_LEVEL, singleton deleted, DI stub wired |
| `a93c8ff` | chore: quality gates — ruff format, import sort, type annotations, SIM/ARG suppressions |
| `b99dc6e` | chore: scope correctie — cli.py DI uitgesteld naar C_SETTINGS.2 |
| `f3c35bd` | chore: C_SETTINGS.1 CLI DI — cli.py accepteert settings param, MCPServer/main() injectable |
| `fdab131` | chore: regressiefix — test_server mocks TextIOWrapper om pytest stdout-sluiting te vermijden |
| `967647d` | chore: persist state after phase transition |

### C_SETTINGS.2 — Workflow singleton verwijderd (2026-03-14)

**Doel:** workflow-singleton verwijderd; DI volledig voor Settings + WorkflowConfig.

| Commit | Inhoud |
|--------|--------|
| `42db228` | refactor(C2_REFACTOR): complete settings DI rewiring + workflow singleton removed |
| `37f9d4a` | refactor(C2_REFACTOR): quality gate test annotations + imports gefixed |

---

## Fase 6 — C_LOADER.1-3: De grote config-migratie (2026-03-14 t/m 2026-03-16)

### C_LOADER.1-2 (2026-03-14 t/m 2026-03-15)

**Doel:** ConfigLoader introduceren; alle schema-classes verliezen `from_file()`/`ClassVar` singletons;
`config/schemas/` submap formeel; twee ConfigError-classes geconsolideerd tot een.

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `e19d9ce` | 03-14 | docs(P_RESEARCH): archive pre-TDD docs, sections naar issue258, config-layer SRP research |
| `1b20c67` | 03-15 | docs(P_RESEARCH): config loader migratie + agent role guides hersteld |

### C_LOADER.3 — Brede DI-ombouw (2026-03-16)

**Doel:** managers, core, scaffolding, toollaag allemaal ombouwen naar expliciete config-injectie.
Geen enkele `from_file()` fallback meer buiten `mcp_server/config/`.

**NOGO bij overdracht** (QA sessie 2026-03-16):

| Laag | Probleem |
|------|---------|
| `ArtifactManager` | Nog `reset_instance()` + `from_file()` fallback-logica aanwezig |
| `policy_engine.py` / `directory_policy_resolver.py` | Nog legacy `from_file()` fallback-paden |
| `scaffolding/metadata.py` + `template_scaffolder.py` | Nog `from_file()` fallback |
| `issue_tools.py`, `git_tools.py`, `pr_tools.py` | Nog `from_file()` / `load()` fallback-paden |

**Functioneel groen, structureel niet gesloten** — directe herhaling van RC-1 en RC-8.

Wat wel bereikt was in deze sessie (SESSIE_OVERDRACHT_20260316.md):

- Runtime `config_root` expliciet gemaakt via `compat_roots.py`
- `ServerSettings.config_root: str | None = None` geintroduceerd
- `server.py` composeert nu via `resolve_config_root(preferred, explicit, required_files)`
- `tests/mcp_server/test_support.py` uitgebreid met `make_*` builders
- Brede testblast-radius meegetrokken naar expliciete injectie (15+ testbestanden)
- 2136 tests groen

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `1aeceae` | 03-16 | docs(P_RESEARCH): C_LOADER.3 refactor + handover state vastgelegd |
| `074ade8` | 03-16 | chore(issue257): config-root refactor state overdragen |

---

## Fase 7 — C_LOADER.4 + PR #264 Detour (2026-03-17 t/m 2026-03-25)

### C_LOADER.4 baseline (2026-03-17)

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `a3475940` | 03-17 | chore(issue257): baseline vastgelegd voor C_LOADER.4 cleanup |
| `a0b2e7a` | 03-17 | refactor(P_RESEARCH): config schema purity hersteld voor C_LOADER.5 |

### PR #264 — feature/263 orchestratie-merge (2026-03-17)

Tussen C_LOADER.4 en C_LOADER.5 werd **feature/263** (VS Code implementatie-orchestratie)
samengevoegd in branch #257 via mergecommit van PR #264. Dit leverde een reeks VS Code-agent-
orchestratie-artefacten op: hooks, sub-role prompts, agent configs.

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `706910b` | 03-17 | Merge pull request #264 from MikeyVK/feature/263-vscode-implementation-orchestration |
| `875b1a2` | 03-17 | fix: use local .venv python for Windows hook commands |
| `006ca0e` | 03-17 | refactor: split precompact -> workspace per-chat writer + agent dual-write |
| `a417020` | 03-17 | docs: update design + usage docs voor hook split |
| `1f1bd56` | 03-17 | refactor session hooks — split workspace/agent-specific SessionStart |
| `8e797ba` | 03-17 | feat: add lightweight VS Code orchestration flow |
| `c5b2590` | 03-17 | docs(P_RESEARCH): portable setup docs + mcp.json template |
| `17c3194` | 03-17 | docs(P_RESEARCH): design doc v2.0 — phase-aware agent model, 6 phase prompts, roadmap |
| `ccaf0a5` | 03-17 | docs(P_RESEARCH): VS Code agent orchestration design document |

### C_LOADER.4 handover (2026-03-18)

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `7e4ca71` | 03-18 | chore(P_RESEARCH): commit all pending changes |
| `18adde0` | 03-18 | fix(P_RESEARCH): finalize C_LOADER.4 formatter handover |
| `1f3764b` | 03-18 | chore(P_PLANNING): persist state after phase transition |
| `77d0c21` | 03-18 | docs(263): sub-role orchestration design v2 + hook TypedDict fix |

### Revert — PR #264 artefacten verwijderd van branch #257 (2026-03-25)

Na heroverweging werden de feature/263-artefacten als ongepast voor branch #257 beoordeeld
en via 3 revert-commits teruggedraaid. Vervolgens werden agent-config-bestanden op de juiste
manier geintegreerd zonder de hook-referenties.

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `3fb4ea4` | 03-25 | Revert "docs(263): add sub-role orchestration design v2 + hook TypedDict fix" |
| `71a5ea3` | 03-25 | Revert "fix: use local .venv python for Windows hook commands" |
| `75647674` | 03-25 | Revert "Merge pull request #264 from MikeyVK/feature/263-vscode-implementation-orchestration" |
| `d2418798` | 03-25 | docs(P_PLANNING): verwijder alle branch #263 orchestratie-artefacten van branch #257 |
| `660a87f` | 03-25 | docs(P_PLANNING): voeg agent files toe van branch #263 zonder hooks sectie |
| `193a1300` | 03-25 | docs(P_PLANNING): voeg slash prompts toe van branch #263 zonder hook-referentie |

---

## Fase 8 — C_LOADER.5 + Cycles 8-10 + Flag Day (2026-03-25 t/m 2026-03-26)

### State alignment na de reverts (2026-03-25)

Na de revert-operaties moest de branch state opnieuw worden gealigned.

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `496e420a` | 03-25 | chore: deliverables.json + state.json aligned (cycle 6 done, implementation phase) |
| `32a3e2fa` | 03-25 | refactor(C7_REFACTOR): state.json gecorrigeerd naar implementation phase (C_LOADER.5 done) |

### C_LOADER.5 — GitHubManager.validate_issue_params() (2026-03-25)

**Doel:** slotcyclus van de C_LOADER-reeks; `GitHubManager.validate_issue_params()` toevoegen
als DI-ingedraad validatiecomponent in `server.py`.

| Commit | Datum | Sub-fase |
|--------|-------|----------|
| `e44ee8e` | 03-25 | test(C7_RED): structural guards + validate_issue_params RED tests |
| `435eca8e` | 03-25 | feat(C7_GREEN): GitHubManager.validate_issue_params() + config DI wiring in server.py |

### Phase state transitions peri-C_LOADER.5 (2026-03-25)

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `4324449` | 03-25 | chore(P_PLANNING): persist state after phase transition |
| `5adcba7` | 03-25 | chore(P_DESIGN): persist state after phase transition |
| `586f731` | 03-25 | chore(P_PLANNING): persist state after phase transition |
| `179ac47` | 03-25 | chore(P_DESIGN): persist state after phase transition |
| `ebbbcad` | 03-25 | chore(P_PLANNING): persist state after phase transition |

### Cycles 8-10 — Flag Day Cleanup (2026-03-25 t/m 2026-03-26)

**Het moment waarop alle resterende config-compatibility-wrappers werden verwijderd.**

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `bce01880` | 03-26 | chore(P_IMPLEMENTATION): persist state after phase transition |
| `96412e3` | 03-26 | chore(P_IMPLEMENTATION): persist state after phase transition |

### QA Remediation (2026-03-26)

Na de cycli 8-10 waren er nog kwaliteitsgate-failures. De QA-remediatie loste alle
openstaande items op.

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `408789c` | 03-26 | chore(P_IMPLEMENTATION): complete QA remediation for config schema flag-day cleanup |
| `487e905` | 03-26 | chore(P_IMPLEMENTATION): finalize cycle 10 cleanup + quality gate stabilization |
| `71b4c99` | 03-26 | chore(P_IMPLEMENTATION): persist state after cycle transition |
| `fffc8be` | 03-26 | chore(P_IMPLEMENTATION): persist state after cycle transition |

---

## Fase 9 — Validatie + afsluiting (2026-03-26)

### Validatiefase

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `50ae9cd` | 03-26 | chore(P_VALIDATION): persist state after phase transition |

### Laatste Quality Gate fixes

Twee openstaande Ruff I001 (import-sort) problemen en een `pytest_plugins` registratiefout
in een niet-top-level `conftest.py` (nieuw pytest-gedrag in recentere versies).

| Commit | Datum | Inhoud |
|--------|-------|--------|
| `867bf8c` | 03-26 | chore(P_VALIDATION): fix pytest root plugin registration + import ordering |

**Wat gefixeerd werd:**

1. `tests/conftest.py` — `pytest_plugins` verplaatst naar top-level (was in sub-level conftest)
2. `mcp_server/tools/label_tools.py` — import sort fix (GitHubManager voor LabelConfig)
3. `tests/mcp_server/unit/config/test_label_config.py` — import sort (ConfigLoader voor LabelConfig)
4. `tests/mcp_server/conftest.py` — `pytest_plugins` declaratie verwijderd (dubbel)

### Eindresultaat

```
pytest tests/
2670 passed, 12 skipped, 2 xfailed
All 6 active quality gates: PASS
```

Branch `feature/257-reorder-workflow-phases` gepusht naar remote. Worktree clean.

---

## Lessons Learned

De ontwikkeling van issue #257 heeft een reeks inzichten opgeleverd die nu verankerd
zijn als het **Gap Prevention Protocol** (`research_config_layer_srp.md`, sectie §17).

### L-1: Stop/Go als harde gate, niet als suggestie (RC-1 / RC-8)

**Wat fout ging:** Cycles werden afgesloten zonder de verificatiecommando's daadwerkelijk
uit te voeren. `projects.json` bestond nog na Cycle 1, maar niemand controleerde het.

**Gevolg:** 7 cycles met groene tests maar 10/20 KPIs rood.

**Fix:** `planning.md` bevat nu expliciete PowerShell-verificatiecommand's per cycle als
executable specification. Stop/Go is een harde blokkade, geen optioneel advies.

### L-2: Gebouwd en ingedraad (RC-2 / P-4)

**Wat fout ging:** `PhaseContractResolver` gebouwd, getest, maar nooit aangeroepen vanuit PSE
exit-hooks. De class stond op 10 meter afstand en werd nergens gebruikt.

**Gevolg:** kritieke componenten met volledige testdekking maar nul productie-effect.

**Fix:** Regel P-4 (Built and Wired): grep=0 residuals + min. 1 consumer via `server.py` +
min. 1 integratietest die het nieuwe pad exerceert.

### L-3: Structurele tests naast gedragstests (RC-3)

**Wat fout ging:** 2132 tests groen terwijl structurele violations onopgemerkt bleven.
Geen test controleerde "Roept PSE.transition() de exit-hook registry aan?"

**Gevolg:** false sense of security via green testsuite.

**Fix:** Elk RED-fase vereist min. 1 structurele test (grep, ast, isinstance).

### L-4: Hoogste-risico werk eerst (RC-4 / P-1)

**Wat fout ging:** PSE (869+ regels, God Class) werd systematisch vermeden.
Simpele gesoleerde code werd wel TDD-gewijs opgepakt.

**Fix:** Planning plaatst de risicovolste refactoring in cycle 1.

### L-5: Geen issue-specifieke waarden in workflow-level YAML (RC-6 / P-3)

**Wat fout ging:** `phase_contracts.yaml` hardcoded op `issue257/` paden.
Elke andere feature-branch zou een false positive gate-pass krijgen.

**Fix:** Regel P-3: `{issue_number}` interpolatie verplicht; geen issue-specifieke waarden
in workflow-level config.

### L-6: Scope-pivot is soms de enige echte remedie

**Wat gebeurde:** Gap-analyse toonde dat de root cause dieper lag dan de PSE-architectuur.
De config-laag miste een fundamentele structuur.

**Beslissing:** Volledige scope-pivot naar Config Layer SRP; PSE-herstelplan verlaten.

**Resultaat:** Betere architectuur (ConfigLoader centraal, DI overal, singletons weg)
dan het herstelplan had kunnen leveren.

---

## Fase 5 — Threshold B close-out en documentatiefase (2026-04-04 t/m 2026-04-06)

### 2026-04-04 — Scope-herkadering naar minimale MCP-close-out

Na de eerdere config-layer pivot werd issue #257 opnieuw benaderd vanuit een smallere Threshold B-scope:

- `planning_threshold_b_minimal_refactor.md` en `design_threshold_b_minimal_refactor.md` bakenden de resterende MCP-architectuurschuld af
- focus verschoof naar `PhaseStateEngine`, `WorkflowGateRunner`, `StateReconstructor`, cycle-tools en enforcement cleanup
- doel was niet nog een brede config-ombouw, maar het afronden van de resterende God Class- en orchestratieproblemen in de MCP-laag

### 2026-04-05 — QA blockers opgelost en branch opnieuw gevalideerd

Een expliciete QA blocker-overdracht leidde tot drie gerichte remediatiestromen:

- **B1:** cross-machine integratietests aangepast aan het pure-query contract van `get_state()`
- **M1a:** dode legacy gate-dispatch methoden verwijderd uit `PhaseStateEngine`
- **M1b/c:** cycle-overgangen en cycle-validatie config-driven gemaakt via `cycle_based` in `phase_contracts.yaml`
- **M2:** ontbrekende code-style headers/metadata aangevuld op de gevraagde bestanden

Daarna volgde een gerichte MCP-validatie:

- file-scoped quality gates op alle relevante MCP-bestanden: groen
- `tests/mcp_server/`: `2158 passed, 12 skipped, 2 xfailed, 19 warnings`
- server restart + health check: `OK`

De branch werd vervolgens van `implementation` naar `validation` en daarna naar `documentation` getransitioned.

### 2026-04-06 — Follow-up issues expliciet gemaakt in de documentatiefase

Tijdens de documentatiefase zijn de overgebleven niet-blokkerende vervolgpunten expliciet vastgelegd als vervolgwerk:

- **Issue #269:** overgangstools/API-contracten tussen phase- en cycle-tools harmoniseren
- **Issue #270:** dode legacy velden verwijderen uit `workphases.yaml` en `policies.yaml`

Belangrijk: issue #270 hoort inhoudelijk bij eigen vervolgwerk, maar wordt vanaf dit moment wel meegenomen in de issue #257 documentatiecontext zodat het close-out verhaal compleet is.

---

## Huidige Staat (2026-04-06)

| Aspect | Status |
|--------|--------|
| Branch | `feature/257-reorder-workflow-phases` — documentatiefase actief |
| Testresultaat | Focused MCP verify: `2158 passed, 12 skipped, 2 xfailed, 19 warnings` |
| Quality gates | File-scoped gates op alle gewijzigde MCP-bestanden groen |
| Transition state | `get_state()` pure query; cycle-overgangen config-driven via `cycle_based` |
| Server | Herstart uitgevoerd; `health_check()` = `OK` |
| Workflow-fase | `documentation` (`P_DOCUMENTATION`) |
| Follow-up issues | `#269` (transition tool harmonisatie), `#270` (dead config fields) |
| Openstaande blockers | Geen — resterend werk is documentatie en nette close-out |

---

## Related Documentation

- **[docs/development/issue257/research_legacy.md][related-1]** — originele smalle scope (gearchiveerd)
- **[docs/development/issue257/research_config_layer_srp.md][related-2]** — config SRP findings v1.8
- **[docs/development/issue257/planning.md][related-3]** — 10-cycle planning v3.0
- **[docs/development/issue257/GAP_ANALYSE_ISSUE257.md][related-4]** — gap analyse met 8 root-causes
- [docs/development/issue257/#archive/design.md] — PSE Config-First design v1.0 (gearchiveerd)
- [docs/development/issue257/#archive/SESSIE_OVERDRACHT_QA_20260312.md] — QA oordelen C1-C4

[related-1]: docs/development/issue257/research_legacy.md
[related-2]: docs/development/issue257/research_config_layer_srp.md
[related-3]: docs/development/issue257/planning.md
[related-4]: docs/development/issue257/GAP_ANALYSE_ISSUE257.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1 | 2026-04-06 | Copilot | April-close-out toegevoegd: Threshold B blockerremediatie, documentatiefase, en follow-up issues #269/#270 |
| 1.0 | 2026-03-27 | Copilot | Initieel: chronologische tijdlijn op basis van ~100 branch-commits + alle issue257-documenten inclusief #archive/ |
