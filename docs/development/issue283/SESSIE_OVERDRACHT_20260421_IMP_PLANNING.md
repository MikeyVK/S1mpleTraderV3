# Sessie Overdracht — Issue #283 Planning → Implementatie
**Datum:** 2026-04-21  
**Branch:** `refactor/283-ready-phase-enforcement`  
**Fase:** `planning` (klaar voor implementatie)  
**Voor:** `@imp implementer`

---

## Wat is er gedaan

1. Research (`research-submit-pr-impact-analysis.md` v2.0 — FINAL)
2. Design (`design-submit-pr-prstatus-enforcement.md` v1.2 — APPROVED)
3. Planning (`planning.md` v1.0 — READY FOR IMPLEMENTATION)
4. `save_planning_deliverables` → 5 cycli geregistreerd in `.st3/deliverables.json`
5. Fase geforceerd: `design → planning` (menselijke goedkeuring verleend)

---

## ⚠️ FLAG DAY Constraint

**Dit is een clean-break implementatie.** Geen backward-compat shims, geen legacy-code.  
Alle bestaande `create_pr`-aanroepen, legacy enforcement-regels en bijbehorende tests  
worden volledig verwijderd (in C5). Geen deprecated-paden bewaard.

---

## 5-Cyclus Overzicht

| Cyclus | Naam | Kernbestanden | Exit-criteria |
|--------|------|---------------|---------------|
| C1 | Contract Surface | `tools/base.py`, `config/schemas/enforcement_config.py`, `state/pr_status_cache.py`, `tools/pr_tools.py` | ABC + cache + SubmitPRTool-scaffold groen |
| C2 | Enforcement Pipeline | `core/enforcement_runner.py`, `server.py` (composition root) | EnforcementRunner + BranchMutatingTool DI groen |
| C3 | submit_pr Atomic Flow | `tools/pr_tools.py` (volledige implementatie) | Atomische PR-flow incl. status-registratie groen |
| C4 | Branch Lockdown Rollout | 18 tools erven van `BranchMutatingTool` | Alle 18 tools geblokkeerd zonder actieve branch groen |
| C5 | Flag-Day Cleanup | Legacy-regels, tests, `create_pr` verwijderd | Geen legacy-paden meer aanwezig, alle gates groen |

---

## Eerste Stap (C1 — RED)

Schrijf tests voor:
1. `BranchMutatingTool` ABC in `mcp_server/tools/base.py`
2. `EnforcementRule.tool_category` in `mcp_server/config/schemas/enforcement_config.py`
3. `IPRStatusCache` interface in `mcp_server/core/interfaces/__init__.py`
4. `PRStatusCache` implementatie in `mcp_server/state/pr_status_cache.py`
5. `SubmitPRTool` scaffold (skeleton) in `mcp_server/tools/pr_tools.py`

Gebruik `transition_cycle` en `git_add_or_commit(workflow_phase="implementation", sub_phase="red", cycle_number=1, ...)`.

---

## Referentiedocumenten

| Document | Pad |
|----------|-----|
| Planning (actueel) | `docs/development/issue283/planning.md` |
| Design v1.2 | `docs/development/issue283/design-submit-pr-prstatus-enforcement.md` |
| Research v2.0 | `docs/development/issue283/research-submit-pr-impact-analysis.md` |
| Deliverables | `.st3/deliverables.json` → sleutel `planning_deliverables` onder issue 283 |

---

## Bekende Pre-existing Debt

`run_quality_gates(scope="branch")` toont ~353 overtredingen in de repo — **dit is pre-existing debt**, niet geïntroduceerd door deze sessie. Voer quality gates uit op gewijzigde bestanden per cyclus (`scope="files"`), niet op de hele branch.

---

## Startcommando's voor @imp

```
1. get_work_context()                    → bevestig branch + fase
2. get_project_plan(283)                 → laad 5-cyclus plan
3. transition_phase(to_phase="implementation")
4. # Schrijf C1 RED tests
5. git_add_or_commit(workflow_phase="implementation", sub_phase="red", cycle_number=1, message="...")
```
