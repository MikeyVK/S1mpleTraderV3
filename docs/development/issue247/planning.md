<!-- docs\development\issue247\planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-21T20:46Z updated= -->
# Test Structure Separation: backend/ vs mcp_server/

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-21

---

## Purpose

Een schone test-structuur die één op één correspondeert met de productie-packages. Doel: `pytest tests/backend/` isoleert zuivere backend-tests zonder enige MCP-import, `pytest tests/mcp_server/` dekt alle MCP-tooling. Geen cross-ownership meer.

## Scope

**In Scope:**
Verplaatsen van test files naar tests/backend/ of tests/mcp_server/. Verplaatsen van scope_encoder.py en phase_detection.py naar mcp_server/core/. Updaten van alle import-sites (6 stuks). Verwijderen van backend-koppelingen uit 4 test files. Splitsen van conftest.py. Updaten van pyproject.toml testpaths. Verwijderen van lege directories.

**Out of Scope:**
Inhoudelijke wijzigingen aan productie-code anders dan de module-verplaatsing. Wijzigingen aan test-logica (alleen koppelingen verwijderen). Issue #103 (run_tests tool). CI/CD pipeline aanpassingen. Renaming van mcp_server/tools/test_tools.py (tracked in #103).

## Prerequisites

Read these first:
1. Research fase compleet (cc45096d) — alle open vragen beantwoord
2. Main branch clean op 54b42c2, 2318 tests passing
3. Exacte blast-radius scope_encoder/phase_detection: 6 importsites gedocumenteerd in research.md
---

## Summary

Reorganiseer tests/ van een gevlochten structuur naar twee strikte trees: tests/backend/ (27 files) en tests/mcp_server/ (~169 files). Verwijder alle backend-koppelingen uit MIXED test files. Verplaats scope_encoder.py en phase_detection.py van backend/core/ naar mcp_server/core/ waar ze architectureel thuishoren. Split conftest.py zodat MCP-singleton reset niet langer op backend-tests draait.

---

## Dependencies

- Cycle 2 blokkeert op Cycle 1 (importpaden moeten bestaan voor test-update)
- Cycle 4 en 5 mogen parallel maar conftest-split (Cycle 6) kan pas na beide
- Cycle 3 is onafhankelijk — mag voor of na Cycle 1/2

---

## TDD Cycles


### Cycle 1: Verplaats scope_encoder.py + phase_detection.py naar mcp_server/core/

**Goal:** Beide modules uit `backend/core/` verwijderen en toevoegen aan `mcp_server/core/`. Drie productie-importsites bijwerken. SCAFFOLD-header path-comment corrigeren.

**RED:** Schrijf importtest op `mcp_server.core.scope_encoder` en `mcp_server.core.phase_detection` — beide falen (bestanden bestaan nog niet op nieuw pad).

**GREEN:**
- Verplaats `backend/core/scope_encoder.py` → `mcp_server/core/scope_encoder.py`
- Verplaats `backend/core/phase_detection.py` → `mcp_server/core/phase_detection.py`
- Update SCAFFOLD-header in beide files (path-comment)
- Update productie-importsites:
  - `mcp_server/managers/git_manager.py:8`
  - `mcp_server/managers/project_manager.py:26`
  - `mcp_server/tools/discovery_tools.py:10`

**REFACTOR:** Verifieer `backend/core/__init__.py` — als scope_encoder/phase_detection daar geëxporteerd worden, verwijder die exports. Verifieer geen andere `backend.core.scope_encoder` of `backend.core.phase_detection` imports aanwezig.

**Exit Criteria:** `pytest tests/ -k "scope_encoder or phase_detection"` groen; `grep -r "from backend.core.scope_encoder\|from backend.core.phase_detection" .` geeft 0 resultaten buiten verwijderde originelen.

---

### Cycle 2: Update test-importsites voor verplaatste modules

**Goal:** De 3 test-files die nog importeren op `backend.core.*` bijwerken naar `mcp_server.core.*`.

**RED:** `tests/unit/backend/core/test_scope_encoder.py` en `test_phase_detection.py` falen op import-fout (bronbestand verdwenen in Cycle 1).

**GREEN:**
- Update `tests/unit/backend/core/test_scope_encoder.py`: `from backend.core.scope_encoder` → `from mcp_server.core.scope_encoder`
- Update `tests/unit/backend/core/test_phase_detection.py`: `from backend.core.phase_detection` → `from mcp_server.core.phase_detection`
- Update `tests/integration/test_workflow_cycle_e2e.py:13`: zelfde wijziging

**REFACTOR:**
- Verplaats `tests/unit/backend/core/test_scope_encoder.py` → `tests/mcp_server/unit/core/test_scope_encoder.py`
- Verplaats `tests/unit/backend/core/test_phase_detection.py` → `tests/mcp_server/unit/core/test_phase_detection.py`
- Maak `tests/mcp_server/unit/core/__init__.py` aan als die nog niet bestaat

**Exit Criteria:** `pytest tests/ -k "scope_encoder or phase_detection or workflow_cycle_e2e"` volledig groen; geen bestanden meer in `tests/unit/backend/core/`.

---

### Cycle 3: Verwijder backend-koppelingen uit 4 test files

**Goal:** De 4 test-files die `backend.*` string-literals of echte imports bevatten ontkoppelen zonder hun semantiek te veranderen.

**GREEN (geen RED nodig — huidige tests zijn al groen, dit is een refactor):**
- `tests/test_tier1_templates.py` regels 84+91: vervang `"from backend.core import Worker"` door `"from myproject.core import Worker"` (neutraal, geen productie-koppeling)
- `tests/integration/test_concrete_templates.py` regel 207: vervang `"from backend.core import Something"` door `"from myproject.core import Something"`
- `tests/integration/test_concrete_templates.py` regels 257–267: vervang hardcoded `backend.core.interfaces.*` pad-assertions door patroon-assertions op symboolnaam (`"IWorkerLifecycle"`, `"IStrategyCache"`, `"BuildSpec"`)
- `tests/integration/mcp_server/validation/test_safe_edit_validation_integration.py` regels 211+245: vervang `BaseWorker` multiline fixture door generieke `ABC`-subclass die dezelfde validatielogica triggert

**REFACTOR:** Voer importscanner uit op alle 4 files — verwacht resultaat: 0 `backend.*` matches.

**Exit Criteria:** `grep -n "from backend\.\|import backend\." tests/test_tier1_templates.py tests/integration/test_concrete_templates.py tests/integration/mcp_server/validation/test_safe_edit_validation_integration.py` geeft 0 resultaten; alle betreffende tests groen.

---

### Cycle 4: Hoofdmigratie backend-tests naar tests/backend/

**Goal:** Maak `tests/backend/` directory-tree aan en verplaats alle 27 backend-eigendom test-files.

**GREEN:**
- Maak aan: `tests/backend/__init__.py`, `tests/backend/unit/__init__.py`, `tests/backend/unit/core/__init__.py`, `tests/backend/unit/core/interfaces/__init__.py`, `tests/backend/unit/dtos/__init__.py`, `tests/backend/unit/services/__init__.py`, `tests/backend/unit/utils/__init__.py`, `tests/backend/parity/__init__.py`
- Verplaats 27 backend-files (zie research.md Findings: BACKEND sectie) naar corresponderende `tests/backend/` subpaden
- Verplaats `tests/parity/normalization.py` → `tests/backend/parity/normalization.py`
- Update import van `tests.parity.normalization` in `test_normalizer.py` naar `tests.backend.parity.normalization`

**REFACTOR:** Verwijder lege dirs: `tests/unit/assembly/`, `tests/unit/dtos/build_specs/`

**Exit Criteria:** `pytest tests/backend/ -v` → ±27 tests groen, geen imports op MCP-modules.

---

### Cycle 5: Migratie MCP-files naar tests/mcp_server/

**Goal:** Alle ~169 MCP-eigendom test-files consolideren onder `tests/mcp_server/`. Supporting files meeverplaatsen.

**GREEN:**
- Verplaats `tests/fixtures/` → `tests/mcp_server/fixtures/`
- Verplaats `tests/baselines/` → `tests/mcp_server/baselines/`
- Verplaats `tests/regression/` → `tests/mcp_server/regression/`
- Verplaats `tests/acceptance/` → `tests/mcp_server/acceptance/`
- Verplaats `tests/integration/` → `tests/mcp_server/integration/`
- Verplaats alle MCP-eigendom files in `tests/unit/` naar `tests/mcp_server/unit/` (inclusief subdirs: tools/, config/, scaffolders/, managers/, scaffolding/, validation/, templates/, mcp_server/)
- Verplaats `tests/mcp_server/` (huidige legacy taskXX-files) intern naar correcte subdirs
- Update alle `pytest_plugins` en relatieve import-paden die verwijzen naar `tests.fixtures.*` → `tests.mcp_server.fixtures.*`, `tests.baselines.*` → `tests.mcp_server.baselines.*`
- Verplaats `tests/ root` tier0/tier1/tier2/cycle/etc. files → `tests/mcp_server/`

**REFACTOR:** Controleer dat geen conftest.py paden gebroken zijn; alle `__init__.py` aanwezig in nieuwe dirs.

**Exit Criteria:** `pytest tests/mcp_server/ -v` → ±169 tests groen zonder backend-imports.

---

### Cycle 6: conftest.py split + pyproject.toml + cleanup

**Goal:** MCP-singleton reset autouse-fixture isoleren van backend-tests. pyproject.toml testpaths bijwerken. Lege resten opruimen.

**RED:** Schrijf test die bewijst dat `pytest tests/backend/` zonder MCP-singleton reset draait (mock-verificatie dat `IssueConfig.reset()` e.d. niet aangeroepen worden).

**GREEN:**
- Split `tests/conftest.py`:
  - Root `tests/conftest.py`: minimaal, geen MCP-imports
  - `tests/backend/conftest.py`: backend-specifieke fixtures (geen MCP)
  - `tests/mcp_server/conftest.py`: autouse MCP-singleton reset (huidige inhoud)
- Update `pyproject.toml`: `testpaths = ["tests/mcp_server"]`
  - Backend-tests vallen hierdoor buiten de default discovery — `pytest` (geen args) = alleen MCP-tests
  - Backend-tests expliciet aanroepbaar via `pytest tests/backend/`
  - Mechanisme: `testpaths` in `[tool.pytest.ini_options]`, geen conftest.py-aanpassing nodig
- Verplaats `tests/unit/test_pytest_config.py` → `tests/mcp_server/unit/test_pytest_config.py`; update assertions: huidige test bewaakt `not integration` in addopts — voeg assertion toe dat `testpaths == ["tests/mcp_server"]`

**REFACTOR:** Verwijder alle nu-lege `tests/unit/` subdirectories. Verwijder `tests/parity/` als leeg na Cycle 4. Verwijder `tests/fixtures/` en `tests/baselines/` als leeg na Cycle 5.

**Exit Criteria:** `pytest` (geen args) draait alleen MCP-tests en slaagt; `pytest tests/backend/` → 27 backend-tests groen; `pytest tests/backend/ tests/mcp_server/` → 2318 tests totaal; `test_pytest_config.py` slaagt na bijwerken van de testpaths-assertion.

---

## Risks & Mitigation

- **Risk:** `__init__.py` ontbreekt in nieuwe directories → ImportError bij test discovery
  - **Mitigation:** Per cycle expliciet `__init__.py` aanmaken vóór eerste test-run
- **Risk:** `autouse=True` conftest-fixture lekt naar backend-tests als testpaths niet correct gescheiden zijn
  - **Mitigation:** Verificatie via `pytest tests/backend/ -v` na Cycle 6; controle dat geen auto-use fixtures uit `tests/mcp_server/conftest.py` zichtbaar zijn
- **Risk:** `backend/core/__init__.py` exporteert scope_encoder of phase_detection — verwijdering breekt externe consumers
  - **Mitigation:** Check `backend/core/__init__.py` vóór Cycle 1 GREEN stap; als exports aanwezig: verwijder en verifieer geen andere consumers
- **Risk:** SCAFFOLD-header path-comment in verplaatste files verwijst nog naar `backend/core/` pad
  - **Mitigation:** Update header in Cycle 1 GREEN als onderdeel van de verplaatsing

---

## Milestones

- Na Cycle 2: alle production + test imports op nieuwe mcp_server.core.* paden, 0 backend-referenties in MCP tooling
- Na Cycle 3: 0 cross-ownership imports in test files (geen MIXED files meer)
- Na Cycle 5: alle test files in juiste directory, oude tests/unit/ structuur leeg
- Na Cycle 6: `pytest tests/backend/` en `pytest tests/mcp_server/` beide zelfstandig groen, totaal nog steeds 2318 tests

## Related Documentation
- **[docs/development/issue247/research.md][related-1]**

<!-- Link definitions -->

[related-1]: docs/development/issue247/research.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |