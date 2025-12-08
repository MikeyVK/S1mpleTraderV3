# MCP Server Ontwerp Analyse & Aanbevelingen

**Document Type:** Vergelijkende Analyse  
**Datum:** 2025-12-08  
**Status:** DEFINITIEF

---

## 1. Overzicht

Dit document vergelijkt twee ontwerpen voor de ST3 Workflow MCP Server:

| Aspect | Ontwerp A (`docs/mcp_server/`) | Ontwerp B (`docs/dev_tooling/`) |
|--------|-------------------------------|--------------------------------|
| **Focus** | Domain-specifiek voor ST3 | Generiek framework-achtig |
| **Structuur** | Manager/Adapter pattern | Flat tools/resources pattern |
| **GitHub** | Project V2 + Sprints + Velocity | Issues/Milestones/Labels focus |
| **Documenten** | 4 bestanden | 5 bestanden |

---

## 2. Gedetailleerde Vergelijking per Aspect

### 2.1 Architectuur

| Criterium | Ontwerp A | Ontwerp B | Winnaar |
|-----------|-----------|-----------|---------|
| **Layered Design** | ✅ Core → Managers → Adapters (3 lagen) | ⚠️ Flatter structure (resources/tools) | **A** |
| **Separation of Concerns** | ✅ Managers = logic, Adapters = I/O | ⚠️ Logic in tools zelf | **A** |
| **Data Flow Diagrams** | ✅ Mermaid sequence diagrams | ❌ Geen sequence diagrams | **A** |
| **Cache Strategy** | ✅ TTL per resource type | ⚠️ Generiek beschreven | **A** |
| **Extension Points** | ✅ Duidelijke patronen voor toevoegen | ⚠️ Minder expliciet | **A** |

**Conclusie Architectuur:** Ontwerp A is significant sterker met een duidelijke 3-laags architectuur die ST3's eigen LAYERED_ARCHITECTURE.md principes volgt.

---

### 2.2 Tools & Resources

| Criterium | Ontwerp A | Ontwerp B | Winnaar |
|-----------|-----------|-----------|---------|
| **Aantal Resources** | 6 (gefocust) | 15 (breed) | Tie |
| **Aantal Tools** | 15 (gefocust) | 22 (breed) | Tie |
| **Schema Definitie** | ✅ Volledige YAML schemas | ✅ Volledige YAML schemas | Tie |
| **Example Output** | ✅ Concrete JSON voorbeelden | ⚠️ Minder voorbeelden | **A** |
| **Implementation Steps** | ✅ Stap-voor-stap | ⚠️ Minder detail | **A** |
| **Idempotency/Dry-run** | ✅ Expliciet per tool | ❌ Niet gespecificeerd | **A** |
| **Prerequisites** | ✅ Expliciet per tool | ⚠️ Impliciet | **A** |

**Ontwerp A Tools (sterk specifiek):**
- `start_work_on_issue` - One-command workflow
- `update_implementation_status` - IMPLEMENTATION_STATUS.md automation
- `scaffold_design_doc` - Design doc met fase-koppeling

**Ontwerp B Tools (sterk generiek):**
- `architecture_validate` - Pattern validation
- `naming_validate` - Naming convention checks
- `docs_check_coverage` - Documentation gap analysis

**Conclusie Tools:** Ontwerp A heeft betere specificaties, maar Ontwerp B heeft bredere scope. Beide zijn waardevol.

---

### 2.3 GitHub Integratie

| Criterium | Ontwerp A | Ontwerp B | Winnaar |
|-----------|-----------|-----------|---------|
| **Project V2 Integration** | ✅ Volledige spec (Views, Columns, Iterations) | ⚠️ Beperkt | **A** |
| **Sprint/Velocity Tracking** | ✅ Story points, burndown | ❌ Niet aanwezig | **A** |
| **Issue Templates** | ⚠️ 2 templates (Feature, Bug) | ✅ 9 templates (incl. TDD, Docs lifecycle) | **B** |
| **Label Taxonomy** | ✅ Goed gestructureerd | ✅ Uitgebreider (28+ labels) | **B** |
| **Phase Labels** | ⚠️ 5 fases | ✅ 10+ fases (discovery→done) | **B** |
| **Branch Protection** | ✅ Gedetailleerd | ✅ Vergelijkbaar | Tie |
| **PR Template** | ❌ Niet aanwezig | ✅ Aanwezig | **B** |
| **Documentation Issue Types** | ❌ Niet aanwezig | ✅ 5 types (Discussion, Design, etc.) | **B** |

**Conclusie GitHub:** Ontwerp A heeft sterkere Project V2 integratie, Ontwerp B heeft betere issue templates voor de volledige development lifecycle.

---

### 2.4 Development Workflow

| Criterium | Ontwerp A | Ontwerp B | Winnaar |
|-----------|-----------|-----------|---------|
| **Phase Definitions** | ⚠️ Impliciet in labels | ✅ Volledig document (PHASE_WORKFLOWS.md) | **B** |
| **Entry/Exit Criteria** | ❌ Niet aanwezig | ✅ Per fase | **B** |
| **MCP Tool Mapping per Fase** | ❌ Niet aanwezig | ✅ Expliciet | **B** |
| **Workflow Automation** | ⚠️ Built-in workflows alleen | ✅ GitHub Actions + MCP hooks | **B** |
| **Label Transitions** | ❌ Niet gedefinieerd | ✅ Expliciet | **B** |

**Conclusie Workflow:** Ontwerp B is sterker met een dedicated PHASE_WORKFLOWS.md document.

---

### 2.5 Implementatie Plan

| Criterium | Ontwerp A | Ontwerp B | Winnaar |
|-----------|-----------|-----------|---------|
| **Phased Approach** | ✅ 6 phases (1 dag elk focus) | ✅ 5 milestones (multi-day) | Tie |
| **Build Order** | ✅ Core → Adapters → Managers → Tools | ✅ Layer 0-6 dependency graph | **A** (cleaner) |
| **Definition of Done** | ✅ Per fase | ✅ Per milestone + overall | Tie |
| **Risk Assessment** | ✅ 4 risico's | ✅ 10+ risico's | **B** |
| **Test Strategy** | ✅ Basis beschreven | ✅ Uitgebreider (pyramid, mocking) | **B** |
| **Module Inventory** | ⚠️ Directory structure only | ✅ LOC estimates per module | **B** |
| **GitHub Issues to Create** | ❌ Niet aanwezig | ✅ Concrete issues per milestone | **B** |

**Conclusie Implementatie:** Beide zijn goed, B is uitgebreider maar A heeft een cleaner build order.

---

### 2.6 Resource URI Schema

| Ontwerp A | Ontwerp B |
|-----------|-----------|
| `st3://status/implementation` | `project://structure` |
| `st3://status/phase` | `github://current-phase` |
| `st3://github/issues` | `github://issues` |
| `st3://github/project` | ❌ Geen equivalent |
| `st3://rules/coding_standards` | `standards://coding-standards` |
| `st3://templates/list` | `templates://dto` (per template) |

**Analyse:**
- Ontwerp A: Consistente `st3://` prefix, meer domain-aligned
- Ontwerp B: Categorie-gebaseerd (`github://`, `standards://`, `templates://`)

**Conclusie URI:** Ontwerp A's `st3://` prefix is meer consistent en project-specifiek.

---

## 3. Sterke Punten Samenvatting

### Ontwerp A (`docs/mcp_server/`) - Sterke Punten

| # | Sterk Punt | Waarom Waardevol |
|---|------------|------------------|
| 1 | **Manager/Adapter Architecture** | Volgt ST3's LAYERED_ARCHITECTURE.md |
| 2 | **Data Flow Diagrams** | Visualiseert request/response flows |
| 3 | **Cache TTL per Resource** | Granulaire controle over freshness |
| 4 | **Project V2 Integration** | Sprint velocity, burndown tracking |
| 5 | **Implementation Steps per Tool** | Duidelijk wat elke tool doet |
| 6 | **Idempotency & Dry-run Flags** | Veilige tool-ontwerp |
| 7 | **Prerequisites per Tool** | Voorkomt runtime errors |
| 8 | **Example JSON Output** | Concrete voorbeelden |
| 9 | **st3:// URI Prefix** | Consistente namespace |
| 10 | **Jinja2 Templates** | Powerfulle scaffolding |

### Ontwerp B (`docs/dev_tooling/`) - Sterke Punten

| # | Sterk Punt | Waarom Waardevol |
|---|------------|------------------|
| 1 | **PHASE_WORKFLOWS.md** | Complete lifecycle documentation |
| 2 | **9 Issue Templates** | Covers discussion → documentation |
| 3 | **28+ Labels** | Granulaire tracking |
| 4 | **Entry/Exit Criteria per Fase** | Duidelijke gates |
| 5 | **MCP Tool Mapping per Fase** | Weet welke tools wanneer |
| 6 | **Label Transitions** | Explicit state machine |
| 7 | **Risk Assessment** | 10+ risico's geïdentificeerd |
| 8 | **GitHub Issues per Milestone** | Concrete backlog items |
| 9 | **PR Template** | Consistente PR's |
| 10 | **Validation Tools** | architecture_validate, naming_validate |

---

## 4. Zwakke Punten Samenvatting

### Ontwerp A - Zwakke Punten

| # | Zwak Punt | Impact |
|---|-----------|--------|
| 1 | Slechts 2 issue templates | Mist TDD workflow, docs lifecycle |
| 2 | Geen PR template | Inconsistente PR's |
| 3 | Geen PHASE_WORKFLOWS document | Workflow kennis impliciet |
| 4 | Geen entry/exit criteria | Onduidelijk wanneer fase klaar is |
| 5 | Minder validation tools | Mist architecture/naming validation |
| 6 | Geen GitHub Issues voorgedefinieerd | Backlog moet handmatig gemaakt |

### Ontwerp B - Zwakke Punten

| # | Zwak Punt | Impact |
|---|-----------|--------|
| 1 | Geen Manager/Adapter layer | Business logic verspreid |
| 2 | Geen data flow diagrams | Moeilijker te begrijpen |
| 3 | Geen Project V2 integration | Mist sprint/velocity tracking |
| 4 | Minder concrete tool specs | Minder implementation guidance |
| 5 | Geen example JSON output | Abstractere specs |
| 6 | Geen idempotency/dry-run flags | Minder veilig |
| 7 | Inconsistente URI prefixes | `github://` vs `standards://` |

---

## 5. Aanbeveling: Unified Design

### 5.1 Merge Strategie

Neem **Ontwerp A als basis** vanwege de superieure architectuur, en **verrijk met Ontwerp B's sterke punten**.

### 5.2 Concrete Merge Acties

```
ARCHITECTURE.md
├── Behoud: Ontwerp A's 3-layer architecture
├── Behoud: Ontwerp A's data flow diagrams
├── Behoud: Ontwerp A's cache strategy
├── Toevoegen: Ontwerp B's validation tools in Tools section
└── Toevoegen: Reference naar PHASE_WORKFLOWS.md

TOOLS_AND_RESOURCES.md
├── Behoud: Ontwerp A's detailed specs met implementation steps
├── Behoud: Ontwerp A's example JSON output
├── Behoud: Ontwerp A's idempotency/dry-run flags
├── Toevoegen: Ontwerp B's architecture_validate tool
├── Toevoegen: Ontwerp B's naming_validate tool
├── Toevoegen: Ontwerp B's docs_check_coverage tool
└── URI: Gebruik Ontwerp A's st3:// prefix

GITHUB_SETUP.md
├── Behoud: Ontwerp A's Project V2 spec (Views, Iterations, Velocity)
├── Toevoegen: Ontwerp B's 9 issue templates
├── Toevoegen: Ontwerp B's 28+ labels
├── Toevoegen: Ontwerp B's PR template
└── Toevoegen: Ontwerp B's GitHub Actions workflows

PHASE_WORKFLOWS.md
└── Neem: Ontwerp B's document volledig over (bestaat niet in A)

IMPLEMENTATION_PLAN.md
├── Behoud: Ontwerp A's clean build order
├── Toevoegen: Ontwerp B's risk assessment (uitgebreider)
├── Toevoegen: Ontwerp B's concrete GitHub issues per milestone
└── Toevoegen: Ontwerp B's test strategy details
```

### 5.3 Resulterende Bestanden

```
docs/mcp_server/
├── ARCHITECTURE.md           # A's architecture + B's extra tools
├── TOOLS_AND_RESOURCES.md    # A's specs + B's validation tools
├── GITHUB_SETUP.md           # A's Project V2 + B's templates/labels
├── PHASE_WORKFLOWS.md        # B's document (nieuw voor A)
└── IMPLEMENTATION_PLAN.md    # A's build order + B's risk/test strategy
```

---

## 6. Prioriteit van Merge Acties

| Prioriteit | Actie | Bron | Impact |
|------------|-------|------|--------|
| **P1** | Add PHASE_WORKFLOWS.md | B | Critical voor workflow guidance |
| **P1** | Add 9 issue templates | B | Critical voor consistent werk |
| **P1** | Add PR template | B | Critical voor PR quality |
| **P2** | Add validation tools | B | Important voor quality automation |
| **P2** | Extend labels to 28+ | B | Important voor granular tracking |
| **P2** | Add GitHub Actions | B | Important voor automation |
| **P3** | Add concrete issues per milestone | B | Nice-to-have voor planning |
| **P3** | Extend risk assessment | B | Nice-to-have voor risk management |

---

## 7. Conclusie

**Aanbeveling:** Gebruik Ontwerp A (`docs/mcp_server/`) als primaire basis en merge de sterke punten van Ontwerp B.

**Rationale:**
1. Ontwerp A heeft een **superieure architectuur** die aligned is met ST3's eigen LAYERED_ARCHITECTURE.md
2. Ontwerp A heeft **betere tool specifications** met implementation steps en examples
3. Ontwerp B's **workflow documentation** en **issue templates** vullen de gaps perfect aan
4. De merge resulteert in een **complete, well-architected MCP server design**

**Actie:** Voer de merge uit volgens sectie 5.2, prioriteer P1 acties eerst.

---

*Einde Analyse*
