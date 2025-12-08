# MCP Server Ontwerp - Definitieve Beoordeling

**Status:** DEFINITIEF  
**Datum:** 2025-12-08  
**Doel:** Objectieve evaluatie van drie analyse-documenten, getoetst aan projectdoelen

---

## 1. De Drie Analyses - Wat Zeggen Ze?

| Document | Conclusie | Winnaar |
|----------|-----------|---------|
| `MCP_SERVER_DESIGN_REVIEW.md` | Beide hebben sterke punten, consolideer | Geen duidelijke |
| `mcp_server/DESIGN_COMPARISON.md` | Design B (dev_tooling) is significant beter | **dev_tooling** |
| `dev_tooling/DESIGN_COMPARISON_ANALYSIS.md` | Design A (mcp_server) is beter, verrijk met B | **mcp_server** |

**Het probleem:** De analyses spreken elkaar tegen. Dit is geen toeval - elke analyse lijkt geschreven vanuit het perspectief van het "eigen" ontwerp.

---

## 2. Objectieve Toetsing aan Projectdoelen

### 2.1 Wat zegt `agent.md`?

De agent.md is duidelijk over de prioriteiten:

1. **Core Principles zijn heilig** - Plugin First, Separation of Concerns, Config-Driven, Contract-Driven
2. **TDD is verplicht** - RED → GREEN → REFACTOR
3. **Quality Gates 10/10** - Geen uitzonderingen
4. **Status Updates zijn kritiek** - IMPLEMENTATION_STATUS.md na elke feature
5. **Architectuur-documenten zijn leading** - Lees ARCHITECTURAL_SHIFTS.md EERST

### 2.2 Wat zegt `DOCUMENTATION_MAINTENANCE.md`?

- Max 300 lines per document (standaard), 1000 voor architectuur
- Single Source of Truth - link, don't duplicate
- Index-driven navigation
- Templates uit `docs/reference/templates/`

### 2.3 Wat zegt `LAYERED_ARCHITECTURE.md`?

ST3 volgt een **strikte 3-laags architectuur**:
- Frontend Layer (presentation)
- Service Layer (orchestration)
- Backend Layer (engine)

**Dit is cruciaal voor de MCP Server beoordeling.**

---

## 3. Kritische Toetsing: Welk Ontwerp Aligned met ST3?

### 3.1 Architectuur Alignment

| Criterium | mcp_server/ | dev_tooling/ | ST3 Requirement |
|-----------|------------|--------------|-----------------|
| **Layered Architecture** | ✅ Core → Managers → Adapters (3 lagen) | ⚠️ Flatter (resources/tools) | ST3 = 3-laags |
| **Separation of Concerns** | ✅ Managers = logic, Adapters = I/O | ⚠️ Logic in tools | ST3 = strict gescheiden |
| **Contract-Driven** | ✅ Pydantic schemas | ✅ Pydantic models | Beide OK |
| **Config-Driven** | ✅ mcp_config.yaml | ✅ YAML config | Beide OK |

**Verdict:** `mcp_server/` volgt de ST3 layered architecture beter.

### 3.2 TDD Workflow Alignment

| Criterium | mcp_server/ | dev_tooling/ | ST3 Requirement |
|-----------|------------|--------------|-----------------|
| **TDD Phase Tracking** | ⚠️ Niet expliciet | ✅ PHASE_WORKFLOWS.md | ST3 = TDD verplicht |
| **RED→GREEN→REFACTOR** | ⚠️ Impliciet | ✅ Expliciet in labels | ST3 = expliciet |
| **Quality Gates** | ⚠️ Beperkt | ✅ Uitgebreider | ST3 = 10/10 |

**Verdict:** `dev_tooling/` alignt beter met ST3's TDD workflow.

### 3.3 Documentation Standards Alignment

| Criterium | mcp_server/ | dev_tooling/ | ST3 Requirement |
|-----------|------------|--------------|-----------------|
| **Document Length** | ✅ Compacter | ⚠️ 1500+ lines (GITHUB_SETUP) | Max 300/1000 lines |
| **Templates** | ⚠️ Geen template refs | ⚠️ Geen template refs | Gebruik templates |
| **Single Source of Truth** | ⚠️ Overlap met dev_tooling | ⚠️ Overlap met mcp_server | Niet OK |

**Verdict:** Beide falen op documentation standards - er zijn twee bronnen.

### 3.4 Project Focus Alignment

Uit `TODO.md`:
> **Current Focus:** Week 1: Configuration Schemas (CRITICAL PATH - blocker for all subsequent work)

De MCP Server is **niet** de huidige prioriteit. Het project is bezig met:
- Week 0: Foundation DTOs (93% complete)
- Week 1: Config Schemas (not started)
- Week 2-4: Bootstrap, Factories, Platform

**Vraag:** Past een MCP Server in deze roadmap?

**Antwoord uit agent.md:** De MCP Server is **niet** genoemd in de critical reading order of implementation workflow. Het is een **tooling project**, geen **core ST3 component**.

---

## 4. De Echte Vraag: Wat Willen We Bereiken?

### 4.1 Wat is het Doel van de MCP Server?

Uit de ontwerpen:
1. **GitHub workflow automatisering** - Issues, PRs, Project board
2. **Quality gate enforcement** - Pylint, mypy, pytest
3. **Documentation validation** - Template compliance
4. **Git workflow automation** - Branching, commits, TDD phases

**Dit is een Developer Tooling project, geen ST3 Core component.**

### 4.2 Past dit in de ST3 Scope?

| Aspect | ST3 Core | MCP Server |
|--------|----------|------------|
| **Trading Logic** | ✅ Ja | ❌ Nee |
| **Platform Components** | ✅ Ja | ❌ Nee |
| **DTOs** | ✅ Ja | ❌ Nee |
| **Developer Productivity** | ❌ Secundair | ✅ Primair |

**Conclusie:** De MCP Server is een **meta-tool** voor ST3 development, niet een ST3 component.

---

## 5. Definitieve Beoordeling

### 5.1 Analyse van de Analyses

| Document | Bias | Fout |
|----------|------|------|
| `MCP_SERVER_DESIGN_REVIEW.md` | Neutraal | Te diplomatiek, geen duidelijke keuze |
| `mcp_server/DESIGN_COMPARISON.md` | Pro dev_tooling | Onderwaardeert architectuur-kwaliteit |
| `dev_tooling/DESIGN_COMPARISON_ANALYSIS.md` | Pro mcp_server | Onderwaardeert workflow completeness |

**Alle drie hebben gelijk op onderdelen, maar geen geeft het volledige beeld.**

### 5.2 Wat Is Echt Waar?

1. **`mcp_server/` heeft betere architectuur**
   - 3-laags (Core → Managers → Adapters) aligned met ST3's LAYERED_ARCHITECTURE.md
   - Data flow diagrammen maken het begrijpelijk
   - Cache strategy is granulairder

2. **`dev_tooling/` heeft betere workflow documentatie**
   - PHASE_WORKFLOWS.md is essentieel en ontbreekt in mcp_server/
   - Issue templates zijn completer
   - TDD integration is explicieter

3. **Beide falen op ST3 documentation standards**
   - Te lange documenten (1500+ lines)
   - Geen gebruik van project templates
   - Dubbele bronnen = geen Single Source of Truth

4. **De MCP Server is geen prioriteit**
   - TODO.md focust op Config Schemas (Week 1)
   - MCP Server is niet in de critical path

### 5.3 De Juiste Conclusie

**Noch mcp_server/ noch dev_tooling/ is "de winnaar".**

De juiste strategie is:

```
1. PARKEER de MCP Server implementatie
   - Focus op Week 1-4 roadmap (Config Schemas → Platform)
   - MCP Server komt NA core ST3 components

2. Als je WEL doorgaat:
   - Gebruik mcp_server/ ARCHITECTUUR (3-laags, aligned met ST3)
   - Neem dev_tooling/ WORKFLOW documentatie over (PHASE_WORKFLOWS.md)
   - Consolideer naar ONE locatie
   - Splits documenten naar max 300/1000 lines
   - Gebruik docs/reference/templates/

3. Archiveer de andere locatie
   - Voorkom dubbel onderhoud
   - Maak duidelijk welke de "source of truth" is
```

---

## 6. Concrete Aanbeveling

### 6.1 Korte Termijn (Nu)

1. **Maak een beslissing**: Is MCP Server nu prioriteit of niet?
2. **Als NEE**: Parkeer in `docs/archive/mcp_server_design/` en focus op Week 1
3. **Als JA**: Volg sectie 6.2

### 6.2 Als MCP Server WEL Prioriteit Is

```
Stap 1: Consolideer naar docs/mcp_server/ (single source of truth)

Stap 2: Neem over uit dev_tooling/:
        - PHASE_WORKFLOWS.md (essentieel, ontbreekt)
        - Issue templates (completer)
        - Risk assessment (uitgebreider)

Stap 3: Behoud uit mcp_server/:
        - ARCHITECTURE.md (3-laags, aligned met ST3)
        - TOOLS_AND_RESOURCES.md (example JSON, dry-run flags)
        - st3:// URI prefix (consistent)

Stap 4: Split lange documenten:
        - GITHUB_SETUP.md → GITHUB_SETUP.md + ISSUE_TEMPLATES.md + WORKFLOWS.md
        - Max 300 lines per document

Stap 5: Archiveer docs/dev_tooling/ → docs/archive/dev_tooling_v1/

Stap 6: Verwijder de drie analyse-documenten (dit, DESIGN_COMPARISON.md, etc.)
```

### 6.3 Prioriteit Advies

Gegeven de huidige TODO.md status:
- Week 0: 93% complete
- Week 1: Not started (Config Schemas = CRITICAL PATH)

**Mijn advies: Parkeer MCP Server, focus op Config Schemas.**

De MCP Server is tooling. Het helpt pas als de core components bestaan. Nu implementeren is premature optimization.

---

## 7. Samenvatting

| Vraag | Antwoord |
|-------|----------|
| Welke analyse is correct? | **Geen van de drie is volledig correct** |
| Welk ontwerp is beter? | **mcp_server/ voor architectuur, dev_tooling/ voor workflow** |
| Wat moet er gebeuren? | **Consolideren OF parkeren, niet beide houden** |
| Wat is de prioriteit? | **Config Schemas (Week 1), niet MCP Server** |

---

**Einde Definitieve Beoordeling**
