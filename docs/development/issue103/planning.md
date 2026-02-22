<!-- docs\development\issue103\planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-22T12:56Z updated=2026-02-22 -->
# Enhance run_tests tool for large test suites

**Status:** DRAFT  
**Version:** 1.3  
**Last Updated:** 2026-02-22

---

## Purpose

Concretiseer de TDD-cycles voor issue #103 op basis van de research-conclusies in
[docs/development/issue103/research.md](research.md).

## Scope

**In Scope:**
`RunTestsTool` output-formaat, `last_failed_only` parameter, `integration` marker
sanering (definitie + test-verplaatsing), optioneel pytest-xdist.

**Out of Scope:**
test suite SOLID clean-up (issue #250), CI/CD integratie.

## Prerequisites

1. Issue #247 afgerond — `tests/backend/` en `tests/mcp_server/` gescheiden
2. Research afgerond — [docs/development/issue103/research.md](research.md)

---

## Summary

Verbeter de `RunTestsTool` op drie fronten, met een optionele vierde:

1. **Unix-style output** — geen output bij succes, failure-details bij falen. Geen
   output_mode keuze, geen backward compatibility last.
2. **`last_failed_only` parameter** — wraps `pytest --lf` voor snelle re-runs.
3. **`integration` marker saneren** — definitie formaliseren, misgeplaatste tests naar
   de juiste map, marker consequent toepassen op echte e2e tests.
4. **(Optioneel C4) pytest-xdist** — parallelle testuitvoering, afhankelijk van
   compatibiliteitsonderzoek met `asyncio_mode = "auto"`.

**Geldt voor alle cycles:**  
Tijdens de REFACTOR fase van elke cycle: `run_quality_gates` draaien op gewijzigde
bestanden vóór commit.

---

## TDD Cycles

### Cycle 1: Unix-style output — JSON-response inline

**Goal:**  
`RunTestsTool` retourneert een gestructureerde JSON-response, altijd inline (geen
temp-file). Gedrag: bij alle tests groen → alleen summary. Bij failures → summary +
lijst van gefailde tests met locatie en failureregel. Geen `output_mode` parameter.
`full` mode wordt niet geïmplementeerd.

**Betrokken bestanden:**
- `mcp_server/tools/test_tools.py` — `RunTestsInput`, `RunTestsTool.execute()`
- `tests/mcp_server/unit/tools/test_run_tests_tool.py` — nieuw of uitbreiden

**RED — wat de test controleert:**
- Response bij 0 failures: `content[0]["type"] == "json"`, `summary.failed == 0`,
  geen `failures`-key aanwezig (of lege lijst)
- Response bij ≥1 failure: `content[0]["type"] == "json"`, `summary.failed >= 1`,
  `failures[0]` bevat `test_id`, `short_reason`, `location`
- `content[1]["type"] == "text"` als human-readable fallback altijd aanwezig
- Bestaande `path`, `markers`, `timeout` parameters werken onveranderd

**GREEN — minimale implementatie:**
- `RunTestsInput`: `verbose` veld verwijderen (niet meer nodig), rest onveranderd
- Pytest stdout parsen: extract summary-regel (`N passed, M failed`) en
  `FAILED path::test_name — reden` regels
- `ToolResult` retourneren met JSON primair + text-fallback (patroon van
  `RunQualityGatesTool`)

**REFACTOR:**
- Parser extraheren naar private functie `_parse_pytest_output(stdout: str) -> dict`
- `DeprecationWarning` dedupliceren: maximaal één keer per uniek bericht in de
  text-fallback
- `run_quality_gates` draaien op `mcp_server/tools/test_tools.py`

**Acceptatiecriteria C1:**
- [ ] Response bij groene run: alleen summary, geen failures-lijst
- [ ] Response bij rode run: summary + failures met `test_id`, `short_reason`,
  `location`
- [ ] Geen temp-file in geen enkel scenario
- [ ] `path`-parameter werkt onveranderd (gerichte TDD-run op specifiek bestand)

---

### Cycle 2: last_failed_only parameter

**Goal:**  
`RunTestsTool` ondersteunt `last_failed_only=True`, dat `pytest --lf` toevoegt aan de
subprocess-aanroep. Standaard `False` — gedrag onveranderd.

**Betrokken bestanden:**
- `mcp_server/tools/test_tools.py` — `RunTestsInput`, cmd-builder
- Bestaand testbestand voor `RunTestsTool`

**RED — wat de test controleert:**
- Bij `last_failed_only=True`: subprocess-cmd bevat `--lf`
- Bij `last_failed_only=False` (default): `--lf` afwezig
- Combinatie met `path` parameter werkt correct

**GREEN — minimale implementatie:**
- `RunTestsInput`: `last_failed_only: bool = False`
- Cmd-builder: `if params.last_failed_only: cmd.append("--lf")`

**REFACTOR:**
- Cmd-builder logica extraheren naar private methode `_build_cmd(params) -> list[str]`
- `run_quality_gates` draaien op `mcp_server/tools/test_tools.py`

**Acceptatiecriteria C2:**
- [ ] `last_failed_only=True` voegt `--lf` toe aan de cmd
- [ ] Default gedrag onveranderd

---

### Cycle 3: integration marker saneren

**Goal:**  
De `integration` marker krijgt een formele definitie en wordt consequent toegepast.
Tests die echte e2e gedrag over de volledige scope testen (en dus externe dependencies
of het volledige systeem aanroepen) krijgen de marker en verhuizen naar
`tests/mcp_server/integration/`. Tests die misplaatst zijn in de unit-boom worden
gecorrigeerd.

**Definitie `integration` marker (vast te leggen in `pyproject.toml`):**
> Tests die end-to-end gedrag over de volledige scope valideren en daarbij echte
> subprocessen, externe services of het volledige MCP-systeem aanroepen. Worden
> standaard geskipt in TDD-runs; expliciet ingeschakeld in de validatiefase.

**Definitie `slow` marker:**
> Volledig hermetisch maar spawnt echte subprocessen of git-operaties op tmp_path.
> Standaard ingeschakeld; te skippen via `pytest -m "not slow"` voor snelle dev-run.

**Concrete acties:**

| Bestand | Actie |
|---|---|
| `tests/mcp_server/unit/mcp_server/integration/test_qa.py` | Verplaatsen naar `tests/mcp_server/integration/test_qa.py` + `@pytest.mark.integration` |
| `tests/mcp_server/integration/test_create_issue_e2e.py` | 2 API-tests: mock `GitHubManager`; 5 validatietests: `pytestmark` verwijderen |
| `tests/mcp_server/integration/test_workflow_cycle_e2e.py` | Controleren: hermetisch (tmp_path + lokale git) → `@pytest.mark.slow`, géén `integration` |
| `tests/mcp_server/integration/test_issue39_cross_machine.py` | Idem — hermetisch → `@pytest.mark.slow` |
| `pyproject.toml` | Markerdefinities bijwerken met bovenstaande definities |

**Betrokken bestanden:**
- Bovenstaande testbestanden
- `pyproject.toml`
- `tests/mcp_server/unit/mcp_server/integration/` map (leeg na verplaatsing)

**RED — wat de test controleert:**
- `test_pytest_config.py` uitbreiding: marker `integration` aanwezig in pyproject met
  de nieuwe definitie
- `test_pytest_config.py` uitbreiding: marker `slow` aanwezig met definitie
- `test_create_issue_e2e.py` tests slagen zonder live GitHub-verbinding (mock-based)
- `test_qa.py` tests draaien niet standaard mee (gefilterd door `not integration`)

**GREEN — minimale implementatie:**
Bovenstaande concrete acties uitvoeren.

**REFACTOR:**
- `run_quality_gates` draaien op gewijzigde bestanden
- Controleer: `pytest tests/mcp_server/ -q` — alle tests die hermetisch zijn draaien
  standaard mee; `integration`-gemarkte tests worden geskipt
- `asyncio_mode = "auto"` wijzigen naar `"strict"` in `pyproject.toml`:
  elk testbestand met async tests krijgt `pytestmark = pytest.mark.asyncio` op
  module-niveau. Sync tests betalen geen event loop overhead meer. Dit is een
  vereiste prereq voor C4 (xdist heeft bekende edge cases met `asyncio_mode = "auto"`).

**Acceptatiecriteria C3:**
- [ ] `pytest tests/mcp_server/` — QA-tests standaard geskipt (gemarked integration)
- [ ] `pytest tests/mcp_server/ -m integration` — QA-tests draaien
- [ ] `test_create_issue_e2e.py` — alle 7 tests slagen zonder live verbinding
- [ ] Markerdefinities in `pyproject.toml` beschrijven duidelijk wanneer elke marker
  van toepassing is

---

### Cycle 4 (optioneel): pytest-xdist parallelle uitvoering

**Goal:**  
Onderzoek en implementeer parallelle testuitvoering via `pytest-xdist`. Doel: wall
clock tijd van 73s significant reduceren door tests over meerdere CPU-cores te
verdelen.

**Waarom optioneel:**  
Drie afhankelijkheden moeten eerst geverifieerd worden:
1. `asyncio_mode = "strict"` vereist (afgehandeld in C3 REFACTOR) — xdist heeft bekende edge cases met `"auto"`
2. Gedrag van `reset_config_singletons` fixture bij worker-processen
3. Filesystem-contention bij tests die ruff/mypy/git aanroepen op gedeelde bestanden

**Analyse:**

- **Async per test**: xdist elimineert de event-loop overhead niet, maar verdeelt hem
  over workers. Wall clock tijd daalt proportioneel met aantal workers.
- **Singletons**: elk xdist-worker is een apart proces met eigen module-geheugen.
  Cross-worker contaminatie bestaat niet. De `reset_config_singletons` fixture blijft
  nuttig binnen één worker (opeenvolgende tests).
- **Filesystem-touching tests**: `test_qa.py` (ruff/mypy op workspace-bestanden) en
  git-operaties kunnen race conditions veroorzaken bij parallelle workers. Oplossing:
  `@pytest.mark.xdist_group("qa")` en `@pytest.mark.xdist_group("git")` — tests
  binnen een groep draaien altijd op dezelfde worker.
- **Distributiestrategie**: `--dist loadgroup` (ipv `--dist load`) is nodig zodat
  xdist_group-markeringen gerespecteerd worden.

**RED — wat de test controleert:**
- `test_pytest_config.py`: `pytest-xdist` aanwezig als dependency
- Smoke: `pytest tests/mcp_server/ -n auto -q` slaagt zonder failures (zelfde
  resultaat als sequentieel)

**GREEN — minimale implementatie:**
- `pytest-xdist` toevoegen aan `requirements-dev.txt`
- `pyproject.toml addopts`: `-n auto` toevoegen (of separaat `pytest-xdist`-sectie)
- `@pytest.mark.xdist_group` toevoegen aan filesystem-touching tests

**REFACTOR:**
- Timing vergelijken: sequentieel vs. parallel
- `run_quality_gates` draaien
- Baseline in research doc bijwerken met nieuwe timing

**Acceptatiecriteria C4:**
- [ ] `pytest tests/mcp_server/ -n auto` slaagt zonder extra failures
- [ ] Wall clock tijd < 40s (streefwaarde bij 2 workers, afhankelijk van hardware)
- [ ] Geen race conditions op filesystem-touching tests

---

## Risks & Mitigation

- **Risico C1:** Pytest output-format parser fragiel bij andere pytest-versies.
  - **Mitigatie:** Parser werkt op de stabiele samenvattingsregel
    (`N passed, M failed in Xs`); bij parse-fout: `summary.total = -1` met
    foutmelding in response, nooit een crash.

- **Risico C3:** Mock van `GitHubManager` dekt label assembly niet — test wordt
  triviaal groen.
  - **Mitigatie:** Mock retourneert echte structuren; assertions controleren de
    argumenten van de `create_issue` aanroep (welke labels worden meegegeven),
    niet alleen de retourwaarde.

- **Risico C4:** `pytest-asyncio` + `pytest-xdist` incompatibiliteit.
  - **Mitigatie:** Compatibiliteit verifiëren als eerste stap van C4 RED; als niet
    oplosbaar zonder grote refactor → C4 niet implementeren.

---

## Dependencies

- C2 bouwt voort op de cmd-builder die in C1-refactor is geëxtraheerd
- C3 is onafhankelijk van C1 en C2 — kan parallel lopen
- C4 vereist C3 (xdist_group markers voor integration tests)

---

## Milestones

- **Na C1:** agent leest testresultaten direct uit JSON-response; geen grep op
  temp file meer
- **Na C3:** `integration` marker heeft formele definitie en is consequent toegepast;
  validatiefase is de authoritative plek voor echte e2e runs
- **Na C4 (optioneel):** wall clock tijd < 40s

---

## Related Documentation

- [docs/development/issue103/research.md](research.md)
- [Issue #250](https://github.com/MikeyVK/S1mpleTraderV3/issues/250) — test suite
  SOLID clean-up (buiten scope van #103)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-22 | Agent | Scaffold aangemaakt |
| 1.1 | 2026-02-22 | Agent | TDD cycles uitgewerkt op basis van research |
| 1.2 | 2026-02-22 | Agent | C1 unix-style (geen output_mode), C3 integration-sanering ipv afschaffing, C4 xdist + async analyse, quality gates expliciet per cycle |
