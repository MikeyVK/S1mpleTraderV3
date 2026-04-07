<!-- docs\development\issue257\test_suite_architectuur_analyse.md -->
<!-- template=research version=8b7bb3ab created=2026-03-26T14:32Z updated= -->
# MCP Server Test Suite — Architectuuranalyse & Verbeterplan

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-26

---

## Purpose

Grondige analyse van de MCP server test suite op twee assen: (1) locatie-naleving en (2) architectuurkwaliteit (ARCHITECTURE_PRINCIPLES.md toegepast op test code). Doel: blast radius van productie refactors minimaliseren.

## Scope

**In Scope:**
Alle bestanden onder tests/ die mcp_server testen. Conftest hiërarchie, fixture organisatie, import patronen, privé-methode koppeling, filesystem koppeling.

**Out of Scope:**
tests/backend/, tests/copilot_orchestration/, pytest.ini configuratie, CI pipeline inrichting.

## Prerequisites

Read these first:
1. Pylint gap-analyse voltooid (pylint_kwaliteitsgap_ruff_dekking.md)
2. C_VALIDATOR (cycle 8) in progress
3. ARCHITECTURE_PRINCIPLES.md gelezen
---

## Problem Statement

De MCP server test suite heeft een groeipijn opgebouwd: tests zijn verspreid over meerdere locaties, koppelen aan private implementatie-details, en handhaven ARCHITECTURE_PRINCIPLES.md niet consistent binnen de test code. Dit vergroot de blast radius van productie refactors disproportioneel.

## Research Goals

- Vastleggen of alle MCP server tests correct in tests/mcp_server/ staan
- Identificeren van ghost pycache residue uit de migratiefase
- Inventariseren van ARCHITECTURE_PRINCIPLES.md schendingen in de test suite (DIP, ISP, SRP, DRY)
- Bepalen welke test-koppeling aan private methoden de grootste blast radius veroorzaakt
- Opstellen van een geprioriteerd verbeterplan

---

## Findings

## Bevinding A — Ghost pycache residue

**Status:** Cleanup (geen architectuurovertreding, wel ruis)

Drie ghost trees bevatten uitsluitend `__pycache__/` mappen zonder bronbestanden:
- `tests/unit/mcp_server/` (oude migratie-oorsprong)
- `tests/integration/mcp_server/` (oude migratie-oorsprong)
- `tests/mcp_server/unit/mcp_server/` (dubbele nesting uit overgangsfase)

De bronbestanden zijn correct verplaatst. Pycache artefacten beïnvloeden testuitvoering niet maar creëren phantom namespace packages. **Fix:** Remove-Item -Recurse op de drie paden.

---

## Bevinding B — MCP server tests buiten tests/mcp_server/

**Status:** Structuurovertreding, twee bronbestanden

- `tests/unit/config/test_c_loader_structural.py` → correct: `tests/mcp_server/unit/config/`
- `tests/unit/config/test_c_settings_structural.py` → correct: `tests/mcp_server/unit/config/`

Beide zijn structural tests voor C_LOADER/C_SETTINGS cycli en testen uitsluitend `mcp_server.*` modules.

---

## Bevinding C — Structurele map-hiërarchie problemen

### C.1 — 16 template tests op root-niveau tests/mcp_server/

Tests als `test_tier0_template.py`, `test_tier1_templates.py`, `test_design_template_cycle5.py` e.a. staan direct in `tests/mcp_server/` root. Ze horen in `tests/mcp_server/unit/scaffolding/` of `tests/mcp_server/unit/templates/`.

### C.2 — Losse component-mappen buiten unit/integration

- `tests/mcp_server/tools/` (3 bestanden) en `tests/mcp_server/managers/` (2 bestanden) bestaan naast het `unit/` tree maar horen erin.

### C.3 — Semantische contradictie: unit/integration/

`tests/mcp_server/unit/integration/` bevat tests die zichzelf beschrijven als 'Integration tests... full flow from Tool -> Manager -> Adapter'. Dit is een semantische contradictie: integration tests die multi-component samenwerking testen horen in `tests/mcp_server/integration/tools/`.

---

## Bevinding D — Naming: test_support.py als helper module

**Status:** Naming schending

`tests/mcp_server/test_support.py` is een helper-module met DI factory functies (geen enkele test). Door de `test_` prefix pikt pytest het op als potentieel test bestand en geeft misleidende '0 tests collected' signalen. **Fix:** Hernoem naar `tests/mcp_server/fixtures/support.py`, update alle imports (~15 bestanden).

---

## Bevinding E — Privé-methode koppeling (W0212, blast radius HOOG)

**Status:** Architectuurovertreding — ISP schending

| Bestand | Privé toegang | Aantal | Fix |
|---|---|---|---|
| `unit/tools/test_create_issue_label_assembly.py` | `._assemble_labels()` | 20× | Optie A: maak publiek; Optie B: test via execute() |
| `conftest.py` | `._git_config = None` | 2× | `reset_for_testing()` classmethod (C_LOADER deliverable) |
| `managers/test_phase_state_engine_async.py` | `._save_state()` | 4× | Test via get_state() publieke API |
| `tools/test_admin_tools.py` | `_get_*` module patches | 5× | Constructor injectie (DIP) |

Elke hernoeming van deze private API's vereist aanpassing van test code -> verhoogde blast radius.

---

## Bevinding F — DIP schending: echte filesystem koppeling

**Status:** Architectuurovertreding

`tests/mcp_server/unit/integration/test_git.py` laadt config via `ConfigLoader(Path('.st3/config'))` van de echte workspace. Meer subtiel: `test_support.load_issue_tool_dependencies()` zonder `workspace_root` valt terug op de echte `.st3/config` via `compat_roots.resolve_config_root()`. Tests in `test_github.py` gebruiken dit patroon.

Gevolg: tests falen als ze buiten de workspace root staan, en zijn gekoppeld aan de actuele YAML-inhoud. **Fix:** Gebruik `tmp_path` gebaseerde config fixtures (patroon al aanwezig in `test_quality_config.py`).

---

## Bevinding G — SRP schending: God Test (test_all_tools.py)

**Status:** Lichte schending

`tests/mcp_server/unit/integration/test_all_tools.py` importeert 15+ tool klassen en 50+ symbolen. Elke toevoeging of wijziging van een tool-module vereist update van dit bestand. **Fix:** Opsplitsen in per-domein integration tests in `tests/mcp_server/integration/tools/`.

---

## Bevinding H — DRY schending: make_mock_*() factory duplicatie

**Status:** DRY overtreding

`make_mock_git_config()`, `make_mock_git_manager()`, `make_mock_label_config()`, `make_mock_qa_manager()` zijn inline gedefinieerd in `test_all_tools.py`. Vergelijkbare factories zijn ook aanwezig in `test_support.py`. **Fix:** Centraliseer in `tests/mcp_server/fixtures/builders.py`.

---

## Bevinding I — Conftest hiërarchie gaten

**Status:** Structuurovertreding

Actuele conftest bestanden:
- `tests/conftest.py` (root)
- `tests/backend/conftest.py`
- `tests/mcp_server/conftest.py` (autouse reset_config_singletons)
- `tests/mcp_server/unit/conftest.py` (mock_env_vars)
- `tests/mcp_server/parity/conftest.py`
- `tests/mcp_server/integration/mcp_server/conftest.py` (server fixture)

Ontbrekend: `tests/mcp_server/integration/conftest.py` (geen gedeeld integration-niveau fixture bestand), en per-component conftest bestanden voor `unit/tools/` en `unit/managers/`.

---

## Prioriteringsmatrix

| ID | Bevinding | Blast radius | Prioriteit |
|---|---|---|---|
| E | Privé-methode koppeling (W0212) | HOOG | P1 |
| F | Echte filesystem koppeling | HOOG | P1 |
| C.3 | unit/integration/ contradictie | MEDIUM | P2 |
| B | 2 tests buiten mcp_server/ | LAAG | P2 |
| D | test_support.py naming | LAAG | P2 |
| C.1+C.2 | Root-level + losse mappen | LAAG | P3 |
| G | God Test test_all_tools | MEDIUM | P3 |
| H | make_mock_*() duplicatie | LAAG | P3 |
| I | Conftest hiërarchie | LAAG | P3 |
| A | Ghost pycache residue | GEEN | P4 |

## Open Questions

- ❓ Optie A of B voor _assemble_labels: publiek maken of testen via execute()?
- ❓ Moet het P1 werk (E+F) als apart issue worden opgepakt of meelopen met een bestaande C_LOADER cycle?
- ❓ Is test_all_tools.py opsplitsen P2 of P3 gezien het als 'smoke test' dient?
- ❓ Moeten de 2 misplaatste tests uit tests/unit/config/ met een git mv worden verplaatst of zijn er import-reden om ze te laten staan?


## Related Documentation
- **[docs/development/issue257/pylint_kwaliteitsgap_ruff_dekking.md][related-1]**
- **[docs/development/issue257/gap_analyse_architectuur_dekking.md][related-2]**
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-3]**

<!-- Link definitions -->

[related-1]: docs/development/issue257/pylint_kwaliteitsgap_ruff_dekking.md
[related-2]: docs/development/issue257/gap_analyse_architectuur_dekking.md
[related-3]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |