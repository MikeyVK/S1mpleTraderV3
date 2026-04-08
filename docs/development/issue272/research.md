<!-- docs\development\issue272\research.md -->
<!-- template=research version=8b7bb3ab created=2026-04-08T17:48Z updated= -->
# ScopeDecoder wrong phase on child branches with inherited commits

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-08

---

## Purpose

Root-cause analyse en fix-aanbeveling voor issue #272

## Scope

**In Scope:**
ScopeDecoder.detect_phase(), GitAdapter.get_recent_commits(), project_manager._get_project_plan(), discovery_tools._detect_workflow_phase()

**Out of Scope:**
get_state() state-reconstructie (#231), SSOT phase_contracts.yaml (#271), uitbreiding workflow-fasedefinitie

## Prerequisites

Read these first:
1. Issue #272 gelezen
2. Broncode phase_detection.py volledig gelezen
3. Alle callers van detect_phase geïdentificeerd
---

## Problem Statement

Op een verse child-branch (geen eigen commits) rapporteert ScopeDecoder.detect_phase() de fase van de parent-branch in plaats van de fase in state.json. Oorzaak: commit-scope heeft hogere prioriteit dan state.json; de laatste commit in git-history is geïrfd van de parent en draagt diens fase-scope.

## Research Goals

- Bevestig de exacte code-paden die de onjuiste fase veroorzaken
- Identificeer alle callers die geraakt worden
- Evalueer minimale fix-opties (geen grote refactor)
- Kies de aanbevolen fix met laagste risico
- Definieer test-strategie voor de fix

---

## Background

ScopeDecoder gebruikt de precedentie commit-scope > state.json. Dit is gedocumenteerd als intentioneel in phase_detection.py. De design-aanname is dat de meest recente commit op de branch altijd door die branch zelf is aangemaakt. Dit breekt op child-branches vvóór hun eerste eigen commit.

---

## Findings

## Root Cause

`GitAdapter.get_recent_commits(limit=N)` gebruikt `self.repo.iter_commits(max_count=limit)` wat ALLE commits van HEAD itereert, inclusief geërfde parent-commits. Op een verse child-branch is de meest recente commit de laatste parent-commit (bijv. `docs(P_DOCUMENTATION): ...`). `detect_phase()` leest hieruit `documentation` en bereikt nooit de state.json-fallback.

## Affected Callers

1. `discovery_tools.py:141,269` — `get_recent_commits(limit=5)` → `detect_phase(commits[0])`
2. `project_manager.py:448` — `get_recent_commits(limit=1)` → `detect_phase(recent_commits[0])`

## Fix Options

**Optie A — Branch-own commits filter (Aanbevolen):**
Voeg optionele `base` parameter toe aan `get_recent_commits(limit, base=None)`. Wanneer `base` opgegeven, gebruik `repo.iter_commits(f"{base}..HEAD")` zodat alleen branch-eigen commits worden teruggegeven. Bij nul eigen commits retourneert de methode een lege lijst → `detect_phase` valt dan automatisch terug op state.json (bestaand gedrag).

Implementatie:
```python
def get_recent_commits(self, limit: int = 5, base: str | None = None) -> list[str]:
    rev = f"{base}..HEAD" if base else None
    commits = list(self.repo.iter_commits(rev=rev, max_count=limit))
    return [str(c.message).split("\n", 1)[0] for c in commits]
```

Callers updaten:
- `project_manager.py`: `get_recent_commits(limit=1, base="main")` of dynamisch via merge-base
- `discovery_tools.py`: `get_recent_commits(limit=5, base="main")` of dynamisch

**Optie B — Consistency check in detect_phase:**
Na commit-scope detectie, vergelijk met state.json. Als ze afwijken, vertrouw state.json. Nadeel: verandert de semantiek van detect_phase fundamenteel en kan bestaande gedrag breken.

**Optie C — Geen wijziging in detect_phase, wel in callers:**
Callers vragen zelf eerst `state_json.current_phase` op en geven dat door als hint. Nadeel: elke caller moet de logica dupliceren.

## Aanbeveling

Optie A. Minimaal, gerichte change: 1 nieuwe parameter op `get_recent_commits`, 2 caller-updates. Bestaand gedrag blijft intact (geen base-parameter = huidig gedrag). Branch `main` als default base is acceptabel; voor edge-cases (epic-branches) accepteren we dit als known limitation.

## Open Questions

- ❓ Wat is de juiste `base` voor epic child-branches (base is epic/NN, niet main)?
- ❓ Moet `base` dynamisch bepaald worden via merge-base of is hard-coded `main` voldoende?


## Related Documentation
- **[mcp_server/core/phase_detection.py][related-1]**
- **[mcp_server/adapters/git_adapter.py][related-2]**
- **[mcp_server/managers/project_manager.py:440-475][related-3]**
- **[mcp_server/tools/discovery_tools.py:240-270][related-4]**

<!-- Link definitions -->

[related-1]: mcp_server/core/phase_detection.py
[related-2]: mcp_server/adapters/git_adapter.py
[related-3]: mcp_server/managers/project_manager.py:440-475
[related-4]: mcp_server/tools/discovery_tools.py:240-270

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |