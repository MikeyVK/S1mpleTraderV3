<!-- docs\development\issue257\SESSIE_OVERDRACHT_QA_20260316.md -->
<!-- template=planning version=130ac5ea created=2026-03-16T00:00Z updated= -->
# Issue257 Sessieoverdracht QA (2026-03-16)

**Status:** ACTIVE  
**Version:** 1.0  
**Last Updated:** 2026-03-16

---

## Purpose

Read-only QA-overdracht voor issue #257 na hercontrole van Cycle 2c (`C_LOADER.3`).
Doel van dit document:
- vastleggen waarom de huidige hand-over nog **NOGO** is;
- expliciet scheiden van functionele groenstatus versus structurele cycle-closure;
- een concrete input geven voor de volgende implementatiesessie.

---

## QA-oordeel op dit moment

### Cycle 2c — C_LOADER.3
**Oordeel:** NOGO

### Bevestigd groen

De implementatieclaim over functionele status is bevestigd:
- branch-scope quality gates: **6/6 active passed, 1 skipped**;
- volledige MCP-testsuite: **2136 passed, 11 skipped, 2 xfailed, 24 warnings**;
- composition root in `server.py` is aantoonbaar verder richting expliciete DI bewogen;
- brede productie- en testoppervlakte is daadwerkelijk aangepast.

### Waarom toch NOGO

De cycle sluit zijn eigen expliciete structural stop-go nog niet.
Volgens `planning.md` en `.st3/projects.json` moet C_LOADER.3 niet alleen functioneel groen zijn, maar ook verboden self-loading en manager-config imports verwijderen uit de in-scope productieoppervlakte.

Die closure is nog niet gehaald.

---

## In-scope blockers die NOGO veroorzaken

### 1. Managers bevatten nog verboden fallback/self-loading
Bevestigd in productiecode:
- `mcp_server/managers/artifact_manager.py` bevat nog `reset_instance()` en `from_file()` fallback-logica
- managers/import-closure is nog niet nulmatches

Gevolg:
- deliverable `c_loader_3.managers_rewired` is nog niet materieel gesloten
- exit-criterium `from mcp_server\.config` in `mcp_server/managers` is nog niet gehaald

### 2. Core bevat nog legacy loading buiten toegestane eindtoestand
Bevestigd in productiecode:
- `mcp_server/core/policy_engine.py` bevat nog `from_file()` fallback-paden
- `mcp_server/core/directory_policy_resolver.py` bevat nog legacy `from_file()` fallback

Gevolg:
- deliverable `c_loader_3.core_rewired` is nog niet materieel gesloten
- de cycle blijft afhankelijk van verboden fallbackgedrag buiten de finale config-first vorm

### 3. Scaffolding-oppervlak bevat nog verboden fallback/self-loading
Bevestigd in productiecode:
- `mcp_server/scaffolding/metadata.py` bevat nog `from_file()` fallback
- `mcp_server/scaffolders/template_scaffolder.py` bevat nog `from_file()` fallback

Gevolg:
- deliverable `c_loader_3.scaffolding_rewired` is nog niet materieel gesloten
- de expliciete stop-go voor scaffolding/scaffolders is nog niet gehaald

### 4. Toollaag bevat nog legacy singleton/from_file fallback
Bevestigd in productiecode:
- `mcp_server/tools/issue_tools.py` bevat nog fallback naar `from_file()` / `load()` in validator-config paden
- `mcp_server/tools/git_tools.py` bevat nog fallback naar `from_file()`
- `mcp_server/tools/pr_tools.py` bevat nog default/fallback pad via `from_file()`

Gevolg:
- deliverable `c_loader_3.tools_rewired` is nog niet materieel gesloten
- functioneel groen maskeert hier nog resterende architectural debt die juist in deze cycle verwijderd had moeten zijn

---

## Kernonderscheid: groen maar niet gesloten

Deze cycle is nu in de volgende toestand:
- **Functioneel groen:** ja
- **Branch quality groen:** ja
- **Volledige testsuite groen:** ja
- **Structurele cycle-closure conform planning:** nee

Dat betekent:
- de hand-over is geen fake vooruitgang;
- maar wel een te vroege GO-claim;
- QA mag deze cycle nog niet afsluiten zolang de expliciete structural grep/import-closure faalt.

---

## Testrefactor-oordeel binnen deze cycle

QA-standpunt voor vervolgsessies:
- noodzakelijke testrefactor binnen de blast radius van deze refactor hoort **wel** bij C_LOADER.3;
- groene tests zijn niet voldoende als tests nog steeds architectonisch leunen op verborgen singleton state, fallback-loading of andere legacy aannames die door deze cycle juist verwijderd worden;
- testrefactor moet binnen blast radius kritisch worden uitgelijnd op `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md`, maar zonder uit te waaieren naar ongerelateerde latere testschuld.

Concreet betekent dit voor de implementatie-agent:
- niet alleen productie-self-loading verwijderen;
- ook de meegetrokken tests, fixtures en helpers rechtzetten waar zij nog legacy coupling veronderstellen;
- geen beroep doen op "tests zijn mee veranderd dus buiten scope".

---

## Concrete vervolgopdracht voor implementatie

Volgende implementatiesessie moet minimaal deze punten sluiten:
- verwijder resterende `from_file()`, `reset_instance()` en `.reset()` uit de C_LOADER.3 productieoppervlakte waar planning dat expliciet eist;
- haal manager import-closure naar echte nulmatches voor `from mcp_server.config` binnen `mcp_server/managers`;
- refactor tests binnen de blast radius zodat zij niet langer op verboden fallback/singleton gedrag steunen;
- lever daarna opnieuw bewijs voor:
  - branch quality gates groen;
  - volledige `pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q` groen;
  - structural grep/import closure groen.

---

## Related Documentation
- [planning.md](planning.md)
- [research.md](research.md)
- [GAP_ANALYSE_ISSUE257.md](GAP_ANALYSE_ISSUE257.md)
- [SESSIE_OVERDRACHT_QA_20260312.md](#archive/SESSIE_OVERDRACHT_QA_20260312.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-16 | QA Agent | Nieuwe QA-overdracht voor C_LOADER.3: functioneel groen bevestigd, maar cycle blijft NOGO wegens open structural stop-go violations |
