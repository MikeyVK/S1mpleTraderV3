# Backlog Inventory — Issue #288
**Bijgewerkt:** 2026-04-24  
**Aanleiding:** Merge van PR #283 + backlog-sanering: 17 issues gesloten, 2 nieuwe epics aangemaakt, epic-mapping uitgevoerd

---

## 1. Epic-overzicht

| Epic | Titel | # Issues | Sprint |
|------|-------|----------|--------|
| #91 | Restore clean tests + consistent ToolResult contract | 12 | Focus A |
| #72 | Template Library Management | 14 | Focus B |
| #49 | MCP Platform Configurability | 6 | — |
| #18 | Enforce TDD & Coverage via Hard Tooling | 5 | — |
| #289 | Installable Wheel / Standalone MCP Server | 2 + nieuw | Focus C |
| #290 | Workflow Intelligence / Agent UX | 7 | — |

Elke open issue staat in exact één epic of in §3 (standalone) of §4 (deferred).

---

## 2. Issues per epic

### Epic #91 — Restore clean tests + consistent ToolResult contract

Focus A: #282, #253, #237 zijn de eerste te leveren issues (~1 sprint).

| # | Titel | Prio |
|---|-------|------|
| #282 | Isolate test suite van real workflows.yaml (prod-config fallback) | **Nu** |
| #253 | run_tests: sync bug + fail-fast + coverage support | **Nu** |
| #237 | Exclude integration marker from default pytest run | **Nu** |
| #136 | Normalise error handling (ToolResult contract) | Snel |
| #147 | Standardize Tool I/O Schema Validation + graceful degradation | Snel |
| #118 | Post-#56: herstel test discovery + lint suppressions | Snel |
| #47 | Audit over-broad exception handling + lint suppressions | Snel |
| #250 | Test suite clean-up: SOLID audit, deprecated tests | Later |
| #62 | Make phase workflow tests phase-agnostic | Later |
| #128 | V2→V3 Infrastructure Migration: tests & integration | Later |
| #140 | Test coverage 82% → 90% | Later |
| #102 | TEST: Project Initialization Tool Validation | Later |

### Epic #72 — Template Library Management

Focus B: #286, #74, #58, #225 zijn de eerste te leveren issues (~2 sprints).

| # | Titel | Prio |
|---|-------|------|
| #286 | generic template: methods schema mismatch (list[str] vs object access) | **Nu** |
| #74 | Fix DTO en Tool template validation failures | **Nu** |
| #58 | scaffold_design_doc: sections parameter type mismatch | **Nu** |
| #225 | Remove V1 pipeline, consolidate naar Pydantic scaffold path | **Nu** |
| #107 | DRY violations in scaffolding (optioneel na #225) | Nu/Later |
| #187 | Decouple create_issue van Jinja2 field contract | Snel |
| #178 | unit_test template: add test_cases field voor echte testmethoden | Snel |
| #238 | Three-unity architecture voor create_issue | Later |
| #245 | Shared ArtifactBodyRenderer: auto-render PR body + commit message | Later |
| #259 | ArtifactManager sections injection + workflow-aware rendering | Later |
| #258 | sections.yaml + phase_contracts + PSE content_contract gate | Later |
| #132 | Shared File Formatting Service for auto-format on write | Later |
| #106 | ScaffoldComponentTool SRP Refactoring | Later |
| #37 | Design test_*.py Jinja2 template met safe_edit diff-integratie | Later |

### Epic #49 — MCP Platform Configurability

| # | Titel | Prio |
|---|-------|------|
| #271 | phase_contracts.yaml SSOT voor workflow-fase membership | Snel |
| #262 | Config layer: GitConfig/QualityConfig → YAML-backed (niet hardcoded) | Snel |
| #141 | Move ephemeral artifacts van .st3/temp/ naar temp/ | Snel |
| #122 | Move path resolution van ArtifactManager naar tool layer | Later |
| #109 | File Operations Consolidation (PathResolver Utility) | Later |
| #57 | Config: Constants Configuration (constants.yaml) | Later |

### Epic #18 — Enforce TDD & Coverage via Hard Tooling

| # | Titel | Prio |
|---|-------|------|
| #41 | TransitionPhaseTool met phase-specific focus/guidance | Snel |
| #46 | Enforce pre-push/post-pull validation bij fase-transities | Snel |
| #61 | Label Validation Enforcement via Tool Hooks | Snel |
| #60 | Automatic Label Application op basis van issue type/branch/fase | Later |
| #40 | Enforce hierarchical issue-specific documentatiestructuur | Later |

### Epic #289 — Installable Wheel / Standalone MCP Server

Focus C: #285 en #260 zijn de kerndependencies (~3–4 sprints totaal).

| # | Titel | Prio |
|---|-------|------|
| #285 | Separate MCPServer composition root van runtime dispatch | **Nu** |
| #260 | Configureerbare MCP root directory (.st3 → instelbaar pad) | **Nu** |
| *(nieuw)* | Entry point in pyproject.toml (`console_scripts: st3-mcp`) | Aanmaken |
| *(nieuw)* | Bootstrap: default .st3/ structuur aanmaken bij first run | Aanmaken |

### Epic #290 — Workflow Intelligence / Agent UX

| # | Titel | Prio |
|---|-------|------|
| #139 | Bug: get_project_plan geeft current_phase niet terug uit state.json | **Nu** |
| #117 | get_work_context detecteert alleen TDD-fase, niet volledige workflow | **Nu** |
| #230 | TDD cycle counter reset bij re-entry na planning/design detour | **Nu** |
| #231 | State reconciliation get_state: cycle/subphase awareness | Snel |
| #45 | PhaseStateEngine state.json structuurinconsistentie docs vs impl | Snel |
| #268 | MCP-tool-first orchestration: get_work_context + create_handover | Later |
| #278 | Fix critical gaps en stale claims in agent.md | Later |

---

## 3. Standalone issues (actief, geen epic)

| # | Titel | Noot |
|---|-------|------|
| #22 | Analyze SRP Compliance and Coding Standards Adherence | Bewust open — follow-up issues uit archief nog aanmaken |
| #269 | Align phase/cycle transition base class + API contracts | Tech debt, scoped, zelfstandig |
| #228 | Add issue number to commit message encoding | Kleine enhancement |
| #150 | Align get_issue/list_issues met nieuwe conventions | Onderhoud |
| #116 | create_branch accepteert issue_number parameter | Kleine enhancement |

---

## 4. Deferred issues (bewust geparkeerd)

| # | Titel | Heropenen wanneer |
|---|-------|-------------------|
| #255 | Unify scope-aware rerun optimization | Na Focus A |
| #261 | SHA-256 tamper detection deliverables.json | Na deployment epic (#289) |
| #242 | save_planning_deliverables validates TDD deliverables op planning exit | Na Focus B |
| #236 | Backfill existing issues: titles, labels, bodies | Onderhoud — laag prio |
| #121 | Content-Aware Edit Tool: VS Code Position/Range API | Toekomst |
| #110 | Project Scaffolding Tool (Empty Dir → Full Project) | Toekomst |
| #59 | Enforce Git Branching & Merging Strategy | Herbeoordelen: grotendeels gerealiseerd via #56/#229/#283 |

---

## 5. Sprint planning

### Focus A — run_tests (~1 sprint, Epic #91)
**Issues:** #282, #253, #237  
**Scope:** `-m not integration` in addopts; summary_line sync fix; exit code 4 detection als ToolResult.error; coverage flag + Gate 6 output

### Focus B — Template pass (~2 sprints, Epic #72)
**Issues:** #286, #74, #58, #225, optioneel #107  
**Scope:** methods schema fix; DTO/Tool template fixes; scaffold_design_doc fix; V1 pipeline removal

### Focus C — Wheel/distribution (~3–4 sprints, Epic #289)
**Issues:** #285, #260 + 2 nieuw aan te maken  
**Scope:** composition root; configurable .st3/; CLI entry point; bootstrap

---

## 6. Beslissingslog

| Beslissing | Motivatie |
|-----------|-----------|
| 17 issues gesloten (§7) | Allemaal superseded, duplicate of buiten scope — zie §7 |
| #22 bewust open | Analyse in archief aanwezig; follow-up issues nog niet gecreëerd |
| #59 herbeoordelen | Grotendeels gerealiseerd via #56, #229, #283 |
| #255 deferred | Geldig maar niet blokkerend; na Focus A |
| #107 optioneel Focus B | V1-removal (#225) kan DRY-violations verminderen; herbeoordelen na #225 |
| #60/#61 → Epic #18 | Label enforcement is tooling-gedreven handhaving, past bij #18 |
| #45/#278 → Epic #290 | Symptomatische bugs van hetzelfde model |
| #141 → Epic #49 | Locatie ephemeral artifacts is een pad/configuratie-issue |
| #128/#147 → Epic #91 | Test infra en I/O contract zijn kern van #91 |
| #132/#178 → Epic #72 | Template-gerelateerde output rendering |
| Nieuwe epics #289, #290 | Expliciet eigenaarschap voor deployment en dagelijkse navigatiepijn |

---

## 7. Acties uitgevoerd (2026-04-24)

| Issues | Actie |
|--------|-------|
| #30, #31, #32, #33 | scaffold → update body → close |
| #42, #48, #274, #89 | scaffold → update body → close |
| #254, #73, #36, #35 | scaffold → update body → close |
| #34, #24, #16, #15, #14 | scaffold → update body → close |
| #22, #260 | scaffold → update body (bewust open) |
| #289, #290 | Nieuwe epics aangemaakt |
| docs/development/archive/ | 242 bestanden gecommit; 3 SRP-docs issue257 → issue22 |
