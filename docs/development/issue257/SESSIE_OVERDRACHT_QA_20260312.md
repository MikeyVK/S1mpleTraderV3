<!-- docs\development\issue257\SESSIE_OVERDRACHT_QA_20260312.md -->
<!-- template=planning version=130ac5ea created=2026-03-12T00:00Z updated= -->
# Issue257 Sessieoverdracht QA (2026-03-12)

**Status:** ACTIVE  
**Version:** 1.4  
**Last Updated:** 2026-03-13

---

## Purpose

Read-only QA-log voor issue #257 na hercontrole van Cycle 1, Cycle 2 en Cycle 3.
Doel van dit document:
- vastleggen welke punten nu `GO` zijn;
- vastleggen welke restschuld bewust niet blockend is;
- een concrete input geven voor een eventuele extra schuld-cycle.

---

## QA-oordeel op dit moment

### Cycle 1
**Oordeel:** GO

Bevestigd:
- `tdd` is vervangen door `implementation` in `.st3/workflows.yaml`
- `GitConfig.extract_issue_number()` bestaat en wordt gebruikt
- `_extract_issue_from_branch` is verwijderd uit PSE
- `workflow_config.py` is verwijderd
- broncode-PSE bevat geen blocking `projects.json`-afhankelijkheid meer voor Cycle 1-doelen

### Cycle 2
**Oordeel:** GO

Bevestigd:
- `StateRepository`-laag bestaat met `FileStateRepository` en `InMemoryStateRepository`
- `BranchState` is frozen en gebruikt de design-richting met `current_cycle`, `last_cycle`, `cycle_history`
- `PhaseStateEngine.get_state()` retourneert `BranchState`
- `PhaseStateEngine._save_state()` werkt op `BranchState`
- PSE unit tests gebruiken repository-injectie met `InMemoryStateRepository`
- onderzochte Cycle 2-files passeren quality gates en typechecks

### Cycle 3
**Oordeel:** GO

Bevestigd:
- `phase_contracts.yaml` bestaat als aparte contractlaag naast `workphases.yaml`
- `PhaseContractsConfig`, `PhaseConfigContext`, `CheckSpec` en `PhaseContractResolver` bestaan
- Fail-Fast validatie op `cycle_based=true` zonder `commit_type_map` is aanwezig
- resolver heeft geen dependency op `StateRepository` en gebruikt geen `glob`
- A6 merge-semantiek is aanwezig: required config-gates blijven immutabel, issue-specifieke checks kunnen recommended gedrag uitbreiden of overschrijven
- `commit_type_map` voor `implementation` gebruikt `red: test`, `green: feat`, `refactor: refactor`
- gerichte resolver-tests en quality gates zijn groen

### Cycle 4
**Oordeel:** GO

Full test suite (hercheck na fix): **2123 passed, 0 failed, 11 skipped, 2 xfailed** (2026-03-13). Suite volledig groen.

Bevestigd (J1–J4):
- **J1:** `build_commit_type_resolver(workspace_root)` bestaat als composition root in `git_tools.py`; `GitCommitTool.execute()` keert PSE.get_state() → PCR.resolve_commit_type() → GitManager.commit_with_scope() op; `GitManager` heeft geen PCR-dependency
- **J2:** `PhaseStateEngine.get_state(branch) -> BranchState` is publieke methode (lijn 304); `get_current_phase()` is convenience-wrapper eromheen
- **J3:** `GitCommitInput(model_config=ConfigDict(extra="forbid"))` — legacy `phase=` kwarg gooit `ValidationError`; geen enkele `phase=` kwarg meer in `mcp_server/tools/`; backward-compat tests voor `phase=` weigering zijn aanwezig en groen
- **J4:** `PhaseContractResolver` gooit `ConfigError` met `file_path=".st3/config/phase_contracts.yaml"` wanneer config ontbreekt

Pyright check (scope: `git_tools.py`, `phase_state_engine.py`, `git_manager.py`): **0 errors, 0 warnings** (exit 0)

De 2 resterende testsuite-failures zijn **pre-existing** — niet veroorzaakt door Cycle 4:
- `test_raises_filenotfound_when_default_path_missing`: test geschreven voor oudere versie van `get_template_root()` zonder package-fallback; bronbestand `template_config.py` aangeraakt in commit `2ee9228` (tier-templates GREEN, vóór PSE-refactor), testbestand aangeraakt in `0e78bfb` (ruff format); geen Cycle 4 commit raakte deze bestanden
- `test_atomic_creation_both_files`: assertie-bug; test checkt `"reconstructed" not in state` (key aanwezigheid) terwijl `BranchState.model_dump(mode="json")` altijd `reconstructed=False` serialiseert; `BranchState.reconstructed` field toegevoegd in C2 (`68b767e`); test-bestand aangeraakt in `dbe8c15` (C1_REFACTOR); geen Cycle 4 commit raakte dit bestand

---

## Afgeronde opschoonpunten

Deze restschuldpunten zijn op 2026-03-13 daadwerkelijk opgeschoond en blijven dus niet langer open staan voor issue #257.

### 1. Cycle-terminologie in testlaag gemigreerd
Afgerond:
- `tests/mcp_server/unit/tools/test_transition_tools.py` gebruikt nu `current_cycle`, `last_cycle` en `cycle_history`
- verwijzingen naar `current_tdd_cycle`, `last_tdd_cycle` en `tdd_cycle_history` zijn uit de actieve workflow-tooltests verwijderd

### 2. Documentatie- en issue-map drift gesloten
Afgerond:
- `SESSIE_OVERDRACHT_20260311.md` is expliciet historisch
- `SESSIE_OVERDRACHT_QA_20260303.md` en `SESSIE_OVERDRACHT_QA_20260304.md` zijn expliciet historisch gemarkeerd
- `SESSIE_OVERDRACHT_QA_20260312.md` blijft het enige actuele overdrachtsdocument voor issue #257

### 3. `BranchState` compatibility helpers verwijderd
Afgerond:
- oude veldaliasen via `AliasChoices` zijn verwijderd
- properties `current_tdd_cycle`, `last_tdd_cycle`, `tdd_cycle_history` zijn verwijderd
- helper-methoden `get`, `__getitem__`, `__contains__` zijn verwijderd
- actieve state gebruikt nu alleen `current_cycle`, `last_cycle`, `cycle_history`

### 4. `phase_contracts` compatibilitylaag verwijderd
Afgerond:
- alias-ondersteuning via `AliasChoices` is verwijderd
- alleen de publieke contracttaal `exit_requires` en `cycle_exit_requires` blijft ondersteund
- contractconvergentie is hiermee afgerond voor issue #257

### 5. Afgerond op 2026-03-13: 2 pre-existing testfailures buiten Cycle 4 scope

**`test_uses_package_template_root_when_workspace_default_missing`** (`tests/mcp_server/unit/config/test_template_config.py`):
- Oplossing: test herschreven naar het actuele contract van `get_template_root()`
- Nieuw gedrag onder test: zonder `TEMPLATE_ROOT` en zonder workspace `.st3/templates` valt de code terug op bundled package templates

**`test_atomic_creation_both_files`** (`tests/mcp_server/unit/tools/test_initialize_project_tool.py`):
- Oplossing: assertie gecorrigeerd naar waardesemantiek
- Nieuw gedrag onder test: `reconstructed` mag aanwezig zijn in `state.json`, maar moet `False` zijn voor verse initialisatie

---

### Validatie
Afgerond en gevalideerd op 2026-03-13:
- grep op legacy cycle-termen en `AliasChoices` in issue257-relevante code/config geeft geen actieve treffers meer
- gerichte tests groen: `test_state_repository.py`, `test_phase_contract_resolver.py`, `test_transition_tools.py` → 34 passed
- actieve branch-state gebruikt nu alleen `current_cycle`, `last_cycle`, `cycle_history`

### Volgende stap
Issue #257 gaat hiermee verder naar **Cycle 5** uit `planning.md`:
- `enforcement.yaml`
- `EnforcementRunner`
- declaratieve `BaseTool.enforcement_event`
- dispatch-level pre/post enforcement
- branch-policy pre-hook en state-file post-hook

---

## Related Documentation
- [planning.md](planning.md)
- [design.md](design.md)
- [research_config_first_pse.md](research_config_first_pse.md)
- [SESSIE_OVERDRACHT_QA_20260304.md](SESSIE_OVERDRACHT_QA_20260304.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.5 | 2026-03-13 | Copilot | Restschuldpunten 1/2/4/5 opgeschoond en gevalideerd; issue257 handover sluit cleanup af en wijst door naar Cycle 5 |
| 1.4 | 2026-03-13 | Copilot | Restschuld punt 6 opgelost: 2 pre-existing testfailures in testlaag gealigneerd met huidig gedrag |
| 1.3 | 2026-03-13 | QA Agent | Cycle 4 GO-oordeel toegevoegd; 2 pre-existing test-failures gedocumenteerd als restschuld punt 6 |
| 1.2 | 2026-03-13 | QA Agent | Verwijderde testschuld verwerkt; open restschuld teruggebracht tot compatibility-helpers, contract-convergentie en actuele issue-map |
| 1.1 | 2026-03-12 | QA Agent | Cycle 3 QA-oordeel en niet-blockerende contract-aliasschuld toegevoegd |
| 1.0 | 2026-03-12 | QA Agent | Nieuwe QA-log met restschuld na hercontrole van Cycle 1 en 2 |
