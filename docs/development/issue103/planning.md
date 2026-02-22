<!-- docs\development\issue103\planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-22T12:56Z updated=2026-02-22 -->
# Enhance run_tests tool for large test suites

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-02-22

---

## Purpose

Concretiseer de TDD-cycles voor issue #103 op basis van de research-conclusies in
[docs/development/issue103/research.md](research.md).

## Scope

**In Scope:**
`RunTestsTool` output-formaat en parameters, pytest marker cleanup (`integration`
afschaffen + `slow` definitie), `test_create_issue_e2e.py` refactor, `pyproject.toml`
addopts.

**Out of Scope:**
pytest-xdist parallellisatie, changed-files based running, test suite SOLID clean-up
(issue #250), CI/CD integratie.

## Prerequisites

1. Issue #247 afgerond — `tests/backend/` en `tests/mcp_server/` gescheiden
2. Research afgerond — [docs/development/issue103/research.md](research.md)

---

## Summary

Verbeter de `RunTestsTool` op drie fronten:

1. **Gestructureerde JSON-response inline** — `output_mode` parameter
   (minimal / failures / full), geen temp-file meer
2. **`last_failed_only` parameter** — wraps `pytest --lf` voor snelle re-runs
3. **Afschaffen `integration` marker** — inclusief refactor van
   `test_create_issue_e2e.py` (2 API-tests → gemockte `GitHubManager`)

Doel: agent-bruikbare output bij elke testrun, geen grep-workaround op temp file meer.

---

## TDD Cycles

### Cycle 1: output_mode parameter + JSON-response

**Goal:**  
`RunTestsTool` retourneert een gestructureerde JSON-response inline. Bij `failures`
(default) bevat de response een summary-object en een lijst van gefailde tests met
locatie en failureregel. Bij `minimal` alleen de summary. Bij `full` het huidige
gedrag als text-fallback. Geen temp-file indirectie meer.

**Betrokken bestanden:**
- `mcp_server/tools/test_tools.py` — `RunTestsInput`, `RunTestsTool.execute()`
- `tests/mcp_server/unit/tools/test_run_tests_tool.py` — nieuw testbestand (of
  uitbreiding van bestaand)

**RED — wat de test controleert:**
- Response bij 0 failures: `content[0]["type"] == "json"`, `summary.failed == 0`,
  geen `failures`-lijst
- Response bij ≥1 failure: `content[0]["type"] == "json"`, `summary.failed >= 1`,
  `failures[0]` bevat `test_id`, `short_reason`, `location`
- `output_mode="minimal"` retourneert alleen summary, geen `failures`-key
- `output_mode="full"` retourneert `content[0]["type"] == "text"` (huidig gedrag)
- Default `output_mode` is `failures`

**GREEN — minimale implementatie:**
- `RunTestsInput` uitbreiden met `output_mode: Literal["minimal", "failures", "full"]`
- Pytest output parsen: extract summary-regel (`N passed, M failed`) en
  `FAILED path::test_name — reden` regels
- `ToolResult` retourneren met JSON primair + text-fallback (analoog aan
  `RunQualityGatesTool`)

**REFACTOR:**
- Parser extraheren naar private functie `_parse_pytest_output(stdout: str) -> dict`
- Warnings-filtering: deduplicate `DeprecationWarning` naar maximaal één per uniek
  bericht

**Acceptatiecriteria C1:**
- [ ] `pytest tests/mcp_server/unit/tools/test_run_tests_tool.py` slaagt
- [ ] Agent kan `result["summary"]["failed"]` direct lezen zonder extra tool call
- [ ] `output_mode="full"` gedraagt zich identiek aan huidige implementatie
  (backward compatible)
- [ ] Geen temp-file bij geen van de drie modi

---

### Cycle 2: last_failed_only parameter

**Goal:**  
`RunTestsTool` ondersteunt `last_failed_only=True`, dat `pytest --lf` toevoegt aan de
subprocess-aanroep. Hiermee hervoert de agent alleen de tests die bij de vorige run
faalden — nuttig bij iteratief debuggen zonder de hele suite opnieuw te draaien.

**Betrokken bestanden:**
- `mcp_server/tools/test_tools.py` — `RunTestsInput`, cmd-builder in `execute()`
- Bestaand(e) testbestand(en) voor `RunTestsTool`

**RED — wat de test controleert:**
- Bij `last_failed_only=True` bevat de subprocess-cmd het argument `--lf`
- Bij `last_failed_only=False` (default) is `--lf` afwezig
- Combinatie met `output_mode` werkt correct

**GREEN — minimale implementatie:**
- `RunTestsInput` uitbreiden met `last_failed_only: bool = False`
- Cmd-builder: `if params.last_failed_only: cmd.append("--lf")`

**REFACTOR:**
- Cmd-builder logica extraheren naar private methode `_build_cmd(params) -> list[str]`
  zodat `execute()` leesbaar blijft

**Acceptatiecriteria C2:**
- [ ] `pytest tests/mcp_server/unit/tools/test_run_tests_tool.py` slaagt
- [ ] `last_failed_only=True` voegt `--lf` toe aan de cmd
- [ ] Backward compatible: `last_failed_only=False` (default) — gedrag onveranderd

---

### Cycle 3: integration marker afschaffen + test_create_issue_e2e.py refactor

**Goal:**  
De `integration` marker verdwijnt volledig uit de suite. De 2 live API-tests in
`test_create_issue_e2e.py` worden herschreven met een gemockte `GitHubManager` zodat
ze standaard meedraaien. De 5 pure validatietests in hetzelfde bestand verliezen
alleen de `pytestmark`-regel. `pyproject.toml` verliest de `integration`-filter uit
`addopts` en de markerdefinitie.

**Betrokken bestanden:**
- `tests/mcp_server/integration/test_create_issue_e2e.py`
- `pyproject.toml`
- `tests/mcp_server/unit/mcp_server/integration/test_qa.py` — optioneel: `slow` marker
  toevoegen (3 tests > 2s elk)

**RED — wat de test controleert:**
- Nieuwe test: `test_pytest_config.py` uitbreiden met assertion dat `integration`
  marker **niet** in `pyproject.toml` markers staat
- Nieuwe test: assertion dat `addopts` de string `"not integration"` niet bevat
- Bestaande tests in `test_create_issue_e2e.py` slagen zonder live GitHub-verbinding
  (mock-gebaseerd)

**GREEN — minimale implementatie:**
1. `test_create_issue_e2e.py`:
   - `pytestmark` verwijderen
   - `test_minimal_input_creates_issue_with_correct_labels`: mock `GitHubManager` via
     `unittest.mock.patch`, assert op de argumenten waarmee `create_issue` aangeroepen
     wordt + retourneer een mock-issue met de juiste label-namen
   - `test_all_options_creates_issue_with_full_label_set`: idem
2. `pyproject.toml`: `"-m", "not integration"` uit `addopts`, `integration`-definitie
   uit `markers`
3. Optioneel: `@pytest.mark.slow` op de 3 tests in `test_qa.py`

**REFACTOR:**
- ruff format op gewijzigde bestanden
- Controleer: `pytest tests/mcp_server/ -q` — telcount onveranderd of hoger
  (de 7 voorheen geskipte tests draaien nu mee)

**Acceptatiecriteria C3:**
- [ ] `pytest tests/mcp_server/` — geen `deselected` meer door `integration` filter
- [ ] `test_pytest_config.py` assertion slaagt: geen `integration` in markers of
  addopts
- [ ] `test_create_issue_e2e.py` — alle 7 tests slagen zonder live GitHub-verbinding
- [ ] `pyproject.toml` bevat geen verwijzing naar `integration` marker meer

---

## Risks & Mitigation

- **Risico:** Mock van `GitHubManager` in C3 dekt label assembly niet volledig —
  test wordt triviaal groen terwijl de echte label-logica niet getest wordt.
  - **Mitigatie:** Mock retourneert een echte `IssueBody`-structuur; assertions
    controleren de argumenten van de `create_issue`-aanroep (welke labels worden
    meegegeven), niet alleen de retourwaarde.

- **Risico:** Pytest output-format parser in C1 is fragiel bij andere pytest-versies of
  onverwachte output-layout.
  - **Mitigatie:** Parser werkt op de gestandaardiseerde samenvattingsregel
    (`N passed, M failed in Xs`) die stabiel is across pytest versies; fallback naar
    `summary.total = -1` bij parse-fout met foutmelding in de response.

---

## Dependencies

- C3 is onafhankelijk van C1 en C2 — volgorde is flexibel
- C1 levert direct waarde voor de agent en wordt als eerste uitgevoerd
- C2 bouwt voort op de cmd-builder die in C1-refactor is geëxtraheerd

---

## Milestones

- **Na C1:** agent kan test output lezen zonder grep op temp file; response altijd
  inline
- **Na C3:** `integration` marker volledig weg, alle tests draaien standaard mee

---

## Related Documentation

- [docs/development/issue103/research.md](research.md)
- [Issue #250](https://github.com/MikeyVK/S1mpleTraderV3/issues/250) — test suite
  clean-up (uit scope van #103)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-22 | Agent | Scaffold aangemaakt |
| 1.1 | 2026-02-22 | Agent | TDD cycles uitgewerkt op basis van research |
