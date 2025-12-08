# S1mpleTrader V3 - Workflow Automation MCP Server Design

**Status:** DESIGN PROMPT v2.0
**Purpose:** Gestructureerde context gathering en specificatie voor de ST3 Workflow MCP Server
**Created:** 2025-12-08
**Revised:** 2025-12-08

---

## Meta-Instructies

### Persona

Je bent een **Senior Software Architect & MCP Specialist** met expertise in:
- Model Context Protocol (MCP) server design
- Development workflow automation
- Python ecosystems (het ST3 project is 100% Python)
- GitHub API integratie

### Interactief Protocol

Deze prompt is te groot om in één keer uit te voeren. Volg dit **gefaseerde protocol**:

| Fase | Actie | Wacht op |
|------|-------|----------|
| **Fase A** | Context Verificatie | Automatisch |
| **Fase B** | Document Analyse & Regels Extractie | `GO FASE B` |
| **Fase C** | MCP Architecture Beslissingen | `GO FASE C` |
| **Fase D** | Deliverable 1: ARCHITECTURE.md | `GO FASE D` |
| **Fase E** | Deliverable 2: TOOLS_AND_RESOURCES.md | `GO FASE E` |
| **Fase F** | Deliverable 3: GITHUB_SETUP.md | `GO FASE F` |
| **Fase G** | Deliverable 4: PHASE_WORKFLOWS.md | `GO FASE G` |
| **Fase H** | Deliverable 5: IMPLEMENTATION_PLAN.md | `GO FASE H` |

**STOP na elke fase en wacht op expliciete `GO` instructie van de gebruiker.**

### Output Formaat

- Gebruik **YAML** voor specificaties en configuraties
- Gebruik **Mermaid** voor diagrammen waar nuttig
- Houd elk deliverable document onder **500 regels**
- Als een deliverable te groot wordt, splits in logische sub-documenten

---

## Fase A: Context Verificatie (VERPLICHT EERST)

### A.1 Verificeer Bestandstoegang

Voordat je verdergaat, **lees en bevestig** dat je toegang hebt tot de volgende kritieke bestanden. Gebruik je file-reading tools om elk bestand te openen.

**Coding Standards (KRITIEK):**
```
□ docs/coding_standards/TDD_WORKFLOW.md
□ docs/coding_standards/QUALITY_GATES.md
□ docs/coding_standards/CODE_STYLE.md
□ docs/coding_standards/GIT_WORKFLOW.md
```

**Documentation Standards:**
```
□ docs/DOCUMENTATION_MAINTENANCE.md
□ docs/reference/templates/README.md
□ docs/reference/templates/BASE_TEMPLATE.md
□ docs/reference/templates/ARCHITECTURE_TEMPLATE.md
□ docs/reference/templates/DESIGN_TEMPLATE.md
□ docs/reference/templates/REFERENCE_TEMPLATE.md
□ docs/reference/templates/TRACKING_TEMPLATE.md
```

**Architecture (KRITIEK):**
```
□ docs/architecture/CORE_PRINCIPLES.md
□ docs/architecture/ARCHITECTURAL_SHIFTS.md
□ docs/architecture/WORKER_TAXONOMY.md
□ docs/architecture/POINT_IN_TIME_MODEL.md
```

**Implementation Tracking:**
```
□ docs/implementation/IMPLEMENTATION_STATUS.md
□ docs/TODO.md
```

**Project Configuration:**
```
□ pyproject.toml
□ pyrightconfig.json
□ pytest.ini
□ requirements.txt
□ requirements-dev.txt
```

### A.2 Stopconditie

**Als een of meer bestanden NIET leesbaar zijn:**

1. **STOP ONMIDDELLIJK**
2. Rapporteer welke bestanden ontbreken
3. Vraag de gebruiker om:
   - De bestanden toe te voegen aan de context, OF
   - Te bevestigen dat het bestand niet bestaat (en dus genegeerd kan worden)

**Als ALLE bestanden leesbaar zijn:**

1. Bevestig met een checklist: "✅ Alle [X] bestanden geverifieerd"
2. Geef een korte samenvatting van wat je hebt gevonden
3. Wacht op `GO FASE B`

---

## Fase B: Document Analyse & Regels Extractie

### B.1 Coding Standards Analyse

Lees elk bestand volledig en extraheer in tabelvorm:

| Document | Regel ID | Regel Beschrijving | Enforcement Type | Automatiseerbaar? |
|----------|----------|-------------------|------------------|-------------------|
| TDD_WORKFLOW.md | TDD-001 | RED commit bevat alleen test code | Pre-commit hook | ✅ |
| ... | ... | ... | ... | ... |

**Enforcement Types:**
- `pre-commit` - Moet vóór elke commit gecheckt worden
- `pre-push` - Moet vóór push naar remote gecheckt worden
- `pre-pr` - Moet vóór PR creatie gecheckt worden
- `pre-merge` - Moet vóór merge gecheckt worden
- `documentation` - Beïnvloedt alleen documentatie, niet code
- `advisory` - Best practice, niet strikt enforced

### B.2 Documentatie Templates Analyse

Extraheer voor elk template:

```yaml
template_name: string
use_case: wanneer gebruiken
required_sections:
  - section_name: string
    required: true|false
    max_lines: number|null
optional_sections:
  - section_name: string
validation_rules:
  - regel beschrijving
```

### B.3 Architecturale Constraints

Extraheer patronen en anti-patronen die bij code review gedetecteerd moeten worden:

```yaml
patterns:
  - name: string
    description: string
    detection: hoe te detecteren

anti_patterns:
  - name: string
    description: string
    detection: hoe te detecteren
    remediation: hoe te fixen
```

### B.4 Commands & Tools Inventaris

Maak een complete lijst van alle commands die in de documentatie genoemd worden:

| Command | Bron Document | Doel | Parameters |
|---------|---------------|------|------------|
| `pytest tests/ -v` | QUALITY_GATES.md | Run all tests | --tb=short |
| `pylint {file} --disable=all --enable=trailing-whitespace` | QUALITY_GATES.md | Check whitespace | file path |
| ... | ... | ... | ... |

### B.5 Output voor Fase B

Produceer:
1. **Regels Tabel** (alle geëxtraheerde regels)
2. **Templates Inventaris** (alle templates met structuur)
3. **Commands Inventaris** (alle commands met parameters)
4. **Architecturale Constraints** (patterns & anti-patterns)

**Wacht daarna op `GO FASE C`**

---

## Fase C: MCP Architecture Beslissingen

### C.1 Tech Stack Evaluatie (VERPLICHT)

Het ST3 project is **100% Python**. Evalueer expliciet:

| Optie | Voordelen | Nadelen |
|-------|-----------|---------|
| **TypeScript MCP** (standaard) | Rijpere MCP SDK, meer voorbeelden | Tweede taal in project, extra toolchain |
| **Python MCP** (`mcp` package) | Consistentie met project, team maintainability | Nieuwere SDK, minder voorbeelden |

**Geef een expliciet advies** met onderbouwing welke stack het beste past bij:
- Team maintainability (solo developer, Python expertise)
- Project consistentie
- Toekomstige uitbreidbaarheid

### C.2 Resources vs. Tools Analyse

MCP kent twee mechanismen:
- **Tools**: Acties die state wijzigen (create, update, delete)
- **Resources**: Read-only data streams (status, configuratie, logs)

Analyseer voor elke geïdentificeerde functionaliteit:

```yaml
functionaliteit: string
type: tool|resource
rationale: waarom deze keuze

# Voor Resources:
resource_uri: string  # bijv. "st3://status/implementation"
data_format: json|markdown|yaml

# Voor Tools:
tool_name: string
side_effects: [lijst van wijzigingen]
```

**Categoriseer minimaal:**

| Kandidaat | Type | Rationale |
|-----------|------|-----------|
| Implementation Status | Resource | Read-only status data, geen side effects |
| Test Count | Resource | Real-time metric, read-only |
| Current Phase | Resource | Derived from git state, read-only |
| Quality Gates Results | Resource | Output van commands, geen state wijziging |
| Create Issue | Tool | Wijzigt GitHub state |
| Commit Code | Tool | Wijzigt git state |
| ... | ... | ... |

### C.3 State Management Design

Identificeer alle state die de MCP server moet beheren:

```yaml
state_sources:
  - name: git_state
    location: local .git
    examples: [current branch, uncommitted changes, commit history]

  - name: github_state
    location: GitHub API
    examples: [issues, PRs, labels, reviews]

  - name: file_state
    location: local filesystem
    examples: [IMPLEMENTATION_STATUS.md, design docs]

  - name: derived_state
    computed_from: [git_state, github_state, file_state]
    examples: [current phase, blockers, progress percentage]
```

### C.4 Output voor Fase C

Produceer:
1. **Tech Stack Advies** (Python vs TypeScript, met onderbouwing)
2. **Resources vs Tools Matrix** (complete categorisatie)
3. **State Management Diagram** (Mermaid)

**Wacht daarna op `GO FASE D`**

---

## Fase D: Deliverable 1 - ARCHITECTURE.md

### D.1 Document Structuur

Produceer `docs/mcp_server/ARCHITECTURE.md` met:

```markdown
# ST3 Workflow MCP Server - Architecture

## 1. Overview
- Doel van de MCP server
- High-level capabilities

## 2. Tech Stack
[Beslissing uit Fase C met onderbouwing]

## 3. Component Diagram
[Mermaid diagram]

## 4. Resources
[Lijst van alle MCP Resources met URI's]

## 5. Tools
[Lijst van alle MCP Tools per categorie]

## 6. State Management
[Diagram en beschrijving uit Fase C]

## 7. Error Handling Strategy
- Error categorieën
- Recovery procedures
- User messaging

## 8. Security Considerations
- GitHub token handling
- File system access scope
- Audit logging

## 9. Extension Points
- Hoe nieuwe tools toe te voegen
- Hoe nieuwe resources toe te voegen
```

### D.2 Kwaliteitseisen

- Max 400 regels
- Alle diagrammen in Mermaid
- Referenties naar geëxtraheerde regels uit Fase B

**Wacht daarna op `GO FASE E`**

---

## Fase E: Deliverable 2 - TOOLS_AND_RESOURCES.md

### E.1 Resource Specificaties

Voor elke Resource:

```yaml
resource_name: string
uri: "st3://{path}"
description: string
data_format: json|yaml|markdown

schema:
  type: object
  properties:
    field_name:
      type: string
      description: string

refresh_trigger: polling|event|manual
cache_ttl: seconds|null

example_output: |
  {actual example}
```

### E.2 Tool Specificaties

Voor elke Tool:

```yaml
tool_name: snake_case
description: string (voor AI agent)
category: discovery|planning|design|implementation|quality|git

parameters:
  - name: string
    type: string|number|boolean|array
    required: true|false
    description: string
    validation: regex|enum|range

returns:
  success:
    schema: object structure
    example: actual example
  error:
    codes:
      - code: ERROR_CODE
        message: human readable
        resolution: wat te doen

implementation:
  prerequisites: [checks vooraf]
  steps:
    - description: string
      command: shell command if applicable
  side_effects:
    - wat verandert
  rollback: hoe ongedaan te maken (indien mogelijk)

idempotency: true|false
dry_run_support: true|false
offline_capable: true|false
```

### E.3 Document Structuur

Produceer `docs/mcp_server/TOOLS_AND_RESOURCES.md`:

- Sectie 1: Resources (alle resources)
- Sectie 2: Discovery & Planning Tools
- Sectie 3: Design Phase Tools
- Sectie 4: Implementation Tools
- Sectie 5: Quality Tools
- Sectie 6: Git Integration Tools

**Wacht daarna op `GO FASE F`**

---

## Fase F: Deliverable 3 - GITHUB_SETUP.md

### F.1 Issue Templates

Produceer volledige YAML voor elk issue type:

```yaml
# .github/ISSUE_TEMPLATE/feature_request.yml
name: Feature Request
description: Request a new feature
title: "[Feature]: "
labels: ["type:feature", "phase:discovery"]
body:
  - type: markdown
    attributes:
      value: |
        ## Feature Request
  - type: input
    id: summary
    attributes:
      label: Summary
      description: One-line summary
    validations:
      required: true
  # ... meer velden
```

### F.2 PR Template

Produceer volledige markdown voor `.github/PULL_REQUEST_TEMPLATE.md`

### F.3 Labels

Produceer een script of GitHub CLI commands om alle labels aan te maken:

```bash
# create_labels.sh
gh label create "phase:discovery" --color "f9d0c4" --description "Discovery phase"
# ... meer labels
```

### F.4 Branch Protection

Produceer GitHub CLI commands of settings.yml:

```yaml
# Branch protection for main
branches:
  main:
    protection:
      required_pull_request_reviews:
        required_approving_review_count: 1
      required_status_checks:
        strict: true
        contexts:
          - "quality-gates"
```

### F.5 Document Structuur

Produceer `docs/mcp_server/GITHUB_SETUP.md`:
- Alle templates volledig uitgewerkt
- Setup instructies
- Verificatie stappen

**Wacht daarna op `GO FASE G`**

---

## Fase G: Deliverable 4 - PHASE_WORKFLOWS.md

### G.1 Fase Definitie Template

Voor elke van de 7 fasen:

```yaml
phase_number: 0-6
phase_name: string
goal: string (één zin)
duration_estimate: string

entry_criteria:
  - criterium beschrijving
  - automated_check: true|false

exit_criteria:
  - criterium beschrijving
  - automated_check: true|false

input_artifacts:
  - artifact: naam
    source: waar het vandaan komt
    validation: hoe valideren

output_artifacts:
  - artifact: naam
    destination: waar het heen gaat
    template: welk template te gebruiken

github_workflow:
  labels:
    add: [labels]
    remove: [labels]
  branch:
    create: true|false
    naming: pattern
    source: parent branch
  commits:
    allowed_types: [test, feat, refactor, docs, fix]
    message_template: "{type}({scope}): {description}"
  pr:
    create_at: wanneer
    title_template: string
    auto_labels: [labels]

mcp_tools_used:
  - tool_name: wanneer en waarom

mcp_resources_used:
  - resource_uri: waarom

quality_gates:
  - gate: naam
    when: wanneer uitvoeren
    blocking: true|false

rollback_procedure:
  - stap beschrijving

next_phase:
  condition: wanneer naar volgende fase
  target: fase nummer of naam
```

### G.2 Fase Transitie Diagram

Produceer een Mermaid state diagram dat alle fasen en transities toont.

### G.3 De 7 Fasen

| # | Fase | Focus |
|---|------|-------|
| 0 | Discovery | Requirements → GitHub Issue |
| 1 | Planning | Issue → Epic breakdown |
| 2 | Architectural Design | Epic → Design doc (interfaces) |
| 3 | Component Design | Design → Implementation spec |
| 4 | TDD Implementation | Spec → Code (RED→GREEN→REFACTOR) |
| 5 | Integration | Code → E2E tests |
| 6 | Documentation | Feature → Reference docs |

**Wacht daarna op `GO FASE H`**

---

## Fase H: Deliverable 5 - IMPLEMENTATION_PLAN.md

### H.1 Milestone Definitie

```yaml
milestones:
  - id: M1
    name: "Core Infrastructure"
    goal: "MCP server skeleton met eerste resource"
    deliverables:
      - MCP server project setup
      - Eerste Resource: implementation_status
      - Basic error handling
    estimated_effort: X uur
    dependencies: []

  - id: M2
    name: "Git Integration"
    # ...
```

### H.2 Build Order

Specificeer de volgorde waarin tools/resources gebouwd moeten worden, inclusief dependencies:

```yaml
build_order:
  - item: resource:implementation_status
    rationale: "Geen dependencies, direct testbaar"
    test_strategy: "Unit tests met mock file system"

  - item: tool:run_quality_gates
    rationale: "Foundation voor andere tools"
    dependencies: []
    test_strategy: "Integration tests met echte commands"

  # ...
```

### H.3 Test Strategy voor MCP Server

```yaml
testing:
  unit_tests:
    framework: pytest|jest (afhankelijk van tech stack)
    coverage_target: 90%
    mock_strategy: hoe externe deps te mocken

  integration_tests:
    scope: welke integraties te testen
    fixtures: test repo, mock GitHub API

  e2e_tests:
    scenarios:
      - "Complete feature cycle from discovery to merge"
      - "Error recovery scenarios"
```

### H.4 Risico's en Mitigaties

| Risico | Impact | Mitigatie |
|--------|--------|-----------|
| GitHub API rate limits | Hoog | Caching, conditional requests |
| Git state corruption | Kritiek | Atomic operations, dry-run mode |
| ... | ... | ... |

---

## Constraints

### Technisch

- **Python versie:** 3.11+ (consistent met ST3 project)
- **MCP SDK:** Te bepalen in Fase C (Python of TypeScript)
- **GitHub API:** REST API via Octokit of PyGithub
- **Git:** simple-git (TS) of GitPython (Python)
- **Geen externe services** behalve GitHub API

### Kwaliteit

1. **Idempotency:** Elk tool moet veilig opnieuw uitgevoerd kunnen worden
2. **Actionable Errors:** Foutmeldingen vertellen WAT te doen
3. **Dry-Run Mode:** Alle destructieve operaties ondersteunen --dry-run
4. **Offline Capable:** Git-only tools werken zonder internet
5. **Audit Trail:** Alle acties gelogd met timestamp en context
6. **Graceful Degradation:** Als GitHub faalt, fallback naar lokale operaties

---

## Samenvatting Deliverables

| Fase | Deliverable | Locatie |
|------|-------------|---------|
| B | Regels & Commands Extractie | (in chat) |
| C | Tech Stack Advies + Resources/Tools Matrix | (in chat) |
| D | ARCHITECTURE.md | `docs/mcp_server/ARCHITECTURE.md` |
| E | TOOLS_AND_RESOURCES.md | `docs/mcp_server/TOOLS_AND_RESOURCES.md` |
| F | GITHUB_SETUP.md | `docs/mcp_server/GITHUB_SETUP.md` |
| G | PHASE_WORKFLOWS.md | `docs/mcp_server/PHASE_WORKFLOWS.md` |
| H | IMPLEMENTATION_PLAN.md | `docs/mcp_server/IMPLEMENTATION_PLAN.md` |

---

## Checklist voor Voltooiing

- [ ] Fase A: Alle bestanden geverifieerd
- [ ] Fase B: Regels, templates, commands geëxtraheerd
- [ ] Fase C: Tech stack beslissing + Resources vs Tools matrix
- [ ] Fase D: ARCHITECTURE.md opgeleverd en gereviewd
- [ ] Fase E: TOOLS_AND_RESOURCES.md opgeleverd en gereviewd
- [ ] Fase F: GITHUB_SETUP.md opgeleverd en gereviewd
- [ ] Fase G: PHASE_WORKFLOWS.md opgeleverd en gereviewd
- [ ] Fase H: IMPLEMENTATION_PLAN.md opgeleverd en gereviewd
- [ ] Alle documenten voldoen aan max line limits
- [ ] Alle cross-references correct

---

**Document Status:** Ready for phased execution
**First Step:** Begin met Fase A (Context Verificatie)
