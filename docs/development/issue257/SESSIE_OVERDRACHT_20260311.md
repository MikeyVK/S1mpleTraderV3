# Sessie Overdracht — Issue #257 — 2026-03-11

> Historisch document. Niet meer gebruiken als actuele issue-map; zie `SESSIE_OVERDRACHT_QA_20260312.md` voor de bijgewerkte status en backlog.

**Branch:** `feature/257-reorder-workflow-phases`  
**Issue:** #257 — Config-First PSE architecture  
**Fase:** `research` (nog niet overgegaan naar design)  
**Machine:** Windows / D:\dev\SimpleTraderV3  

---

## Waar we staan

De research-fase is volledig afgerond. Twee research-documenten zijn geschreven en gevuld:

1. **`docs/development/issue257/research.md`** — Origineel, smalle scope (fasevolgorde wisselen). Bevat KPIs 1–8 en `## Expected Results`. Dient als exit-gate artefact voor de research-fase (file_glob gate).
2. **`docs/development/issue257/research_config_first_pse.md`** — Nieuw, brede scope. Bevat F1–F19, een volledige per-file schendingsscan (44 schendingen), en de per-file schendingstabel.

De scope is aanzienlijk uitgebreid: het gaat niet meer alleen om "fasevolgorde wisselen" maar om een volledige Config-First architectuurrefactoring van de PSE-infrastructuur.

**Nog niet gedaan:**
- Phase transition: research → design (bewust uitgesteld tot start volgende sessie)
- Hernoemen issue op GitHub
- Hernoemen branch
- Enige code-implementatie

---

## Beslissingen die vaststaan (niet heropenen)

| Beslissing | Detail |
|---|---|
| **Optie A** | Config-first is leidend; issue-specifieke deliverables zijn additief |
| **`.st3/` split** | `config/` (YAML, statisch) + `registries/` (JSON, runtime) |
| **`phase_deliverables.yaml`** | Nieuw config: `contracts[workflow][phase]` → lijst check-specs |
| **`deliverables.json`** | Nieuw register: issue-specifieke aanvullende deliverables per fase |
| **`projects.json` abolishment** | Metadata → `state.json`; Mode 2 via git + GitHub API only |
| **Mode 2 op git only** | Vereist: issue-nummer in branchnaam (enforced), branch_types SSOT |
| **`PhaseDeliverableResolver`** | Nieuwe SRP-class: combineert config-laag + registry-laag → check-spec lijst |
| **`StateRepository`** | Extraheert atomische schrijfverantwoordelijkheid uit PSE en ProjectManager |
| **`branch_name_pattern`** | Vereist issue-nummer prefix: `"^[0-9]+-[a-z][a-z0-9-]*$"` |
| **`branch_types` SSOT** | `git.yaml` is de enige bron; PSE extractie-regex leest uit `GitConfig.branch_types` |
| **Fasevolgorde** | `research → design → planning → tdd` (in `workflows.yaml` feature + bug) |

---

## Scope (vastgesteld, 11 items)

1. `.st3/config/` + `.st3/registries/` mapstructuur
2. `phase_deliverables.yaml` (nieuw config-bestand)
3. `deliverables.json` register (nieuw runtime-bestand)
4. `projects.json` abolishment + `state.json` verrijking
5. `PhaseDeliverableResolver` (nieuwe SRP-class)
6. PSE OCP hook-registry
7. PSE DIP (DeliverableChecker injectie)
8. PSE SRP + DRY + logging refactor
9. `StateRepository` extractie
10. `branch_name_pattern` enforcement in `git.yaml` + `create_branch`
11. `branch_types` SSOT unificatie (`git.yaml` → PSE regex)

**Out of Scope:** #258 (sections.yaml + phase_contracts), #259 (ArtifactManager template-integratie)

---

## Consumer-violations (F19) — vastgesteld

| Bestand | Schending | Oplossing |
|---|---|---|
| `workflows.yaml` | Twee `WorkflowConfig` klassen: `config/workflows.py` (PSE+PM) + `config/workflow_config.py` (issue_tools) | Consolideren naar `workflows.py`; `workflow_config.py` verwijderen |
| `workphases.yaml` | 4 consumers: PSE(3×), ScopeEncoder, ScopeDecoder | `WorkphasesConfig` singleton; ScopeEncoder/ScopeDecoder via gefacadeerde interface |
| `state.json` | 2 consumers: PSE (writer+reader) + ScopeDecoder (fallback reader) | ScopeDecoder leest via `StateRepository`, niet direct van schijf |

---

## Per-File Schendingstelling (samenvatting)

| File | 🔴 Kritiek | 🟠 Significant | 🟡 Minor |
|---|---|---|---|
| `phase_state_engine.py` | PSE-1,2,3,4,6,7 | PSE-9,10,11 | PSE-8 |
| `project_manager.py` | PM-1,3,8 | PM-2,5,6,7 | PM-4 |
| `git_manager.py` | GM-1,2,4,5 | GM-3 | — |
| `config/git_config.py` | GC-1,2 | — | GC-3,4 |
| `config/workflows.py` | WF-2 | WF-1 | WF-3 |
| `config/workflow_config.py` | WFC-1,3 | — | WFC-2 |
| `config/workphases_config.py` | — | WPC-1,2 | — |
| `core/scope_encoder.py` | SE-1 | SE-2 | — |
| `core/phase_detection.py` | PD-1,2 | — | PD-3,4 |
| `managers/deliverable_checker.py` | — | — | DC-2 |
| **Totaal** | **22** | **14** | **8** |

Volledig detail in [research_config_first_pse.md — Per-File Schendingsscan](./research_config_first_pse.md).

---

## Historische vervolgstappen van die sessie

### Stap 1 — Branch + issue hernoemen

```powershell
git branch -m feature/257-reorder-workflow-phases feature/257-config-first-pse-architecture
git push origin -u feature/257-config-first-pse-architecture
git push origin --delete feature/257-reorder-workflow-phases
```

GitHub issue #257 hernoemen naar:
`"Config-First PSE architecture: phase_deliverables.yaml, deliverables register, .st3 structural refactor, projects.json abolishment"`

### Stap 2 — Phase transition research → design

Via workflow tooling: `transition_phase(to_phase="design")`

### Stap 3 — Design scaffold

Ontwerp de interfaces voor:
- `PhaseDeliverableResolver` (input: workflow_name + phase + issue_number → list[CheckSpec])
- `StateRepository` (read_state, save_state, atomic write)
- `phase_deliverables.yaml` schema (YAML-structuur: contracts → workflow → phase → list)
- `deliverables.json` schema (per issue: phase → additieve lijst check-specs)
- Consolidated `WorkflowConfig` (één class, één bestand, `workflow_config.py` verwijderd)
- `WorkphasesConfig` singleton + facade voor ScopeEncoder/ScopeDecoder

### Stap 4 — `git.yaml` quick-wins (config-only, geen code)

- Zet `branch_name_pattern` op `"^[0-9]+-[a-z][a-z0-9-]*$"`
- Voeg `bug` en `hotfix` toe aan `branch_types`

---

## Relevante bestanden

| Bestand | Status | Rol |
|---|---|---|
| `docs/development/issue257/research_config_first_pse.md` | ✅ Nieuw, DRAFT | Hoofdresearch: F1–F19 + per-file scan |
| `docs/development/issue257/research.md` | ✅ Bestaand, compleet | Exit-gate artefact research-fase (file_glob) |
| `mcp_server/managers/phase_state_engine.py` | ❌ Ongewijzigd | God Class — primair doelwit refactoring |
| `mcp_server/managers/project_manager.py` | ❌ Ongewijzigd | projects.json beheer — vervalt |
| `mcp_server/config/workflows.py` | ❌ Ongewijzigd | WorkflowConfig SSOT na consolidatie |
| `mcp_server/config/workflow_config.py` | ❌ Ongewijzigd | Duplicate — verwijderen na consolidatie |
| `.st3/workflows.yaml` | ❌ Ongewijzigd | Fasevolgorde wisselen + comment cleanup |
| `.st3/git.yaml` | ❌ Ongewijzigd | branch_name_pattern + branch_types aanpassen |

---

## State.json op dit moment

```json
{
  "branch": "feature/257-reorder-workflow-phases",
  "issue_number": 257,
  "workflow_name": "feature",
  "current_phase": "research",
  "parent_branch": "main",
  "reconstructed": true
}
```
