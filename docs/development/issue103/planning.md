<!-- docs\development\issue103\planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-22T12:56Z updated=2026-02-22 -->
# Enhance run_tests tool for large test suites

**Status:** IN PROGRESS  
**Version:** 2.0  
**Last Updated:** 2026-02-22

---

## Purpose

Concretiseer de TDD-cycles voor issue #103 op basis van de research-conclusies in
[docs/development/issue103/research.md](research.md).

## Scope

**In Scope:**
`RunTestsTool` output-formaat, `last_failed_only` parameter, `integration`/`slow`
marker sanering (definitie + test-verplaatsing), `scope` parameter op `RunTestsTool`
die markers benut.

**Out of Scope:**
test suite SOLID clean-up (issue #250), CI/CD integratie, `output_mode` parameter
(minimal/failures/full — bewust niet geïmplementeerd), pytest-xdist als doel op zich.

## Prerequisites

1. Issue #247 afgerond — `tests/backend/` en `tests/mcp_server/` gescheiden ✅
2. Research afgerond — [docs/development/issue103/research.md](research.md) ✅

---

## Voortgang

| Cycle | Doel | Status |
|-------|------|--------|
| C1 | Unix-style JSON output, `_parse_pytest_output` | ✅ DONE |
| C2 | `last_failed_only`, `_build_cmd` | ✅ DONE |
| C3 | Marker sanering — definitie + test-verplaatsing | ⚠️ INCOMPLETE |
| C4 | Marker sanering — afmaken + `slow` marker op hermetic tests | 🔜 TODO |
| C5 | `scope` parameter op `RunTestsTool` | 🔜 TODO |
| C6 | Output verbetering: `summary_line` + traceback in failures | 🔜 TODO |

**C3 wat WEL gedaan is:**
- `test_qa.py` verplaatst naar `tests/mcp_server/integration/` met `@pytest.mark.integration`
- `pyproject.toml` markerdefinities formeel vastgelegd (`integration`, `slow`)
- `asyncio_mode = "strict"` doorgevoerd
- `xdist_group` marker gedefinieerd (als bijvangst van C4-vooruit-lopen)
- `pytest-xdist` en `-n auto` toegevoegd (als bijvangst — niet gepland maar niet schadelijk)

**C3 wat NIET gedaan is (blokkeert C4/C5):**
- `test_create_issue_e2e.py` — 2 API-tests nog steeds live GitHub; 5 validatietests hebben nog `pytestmark = pytest.mark.integration`
- `test_workflow_cycle_e2e.py` — hermetisch (lokale git op tmp_path), maar géén `@pytest.mark.slow`
- `test_issue39_cross_machine.py` — hermetisch, maar géén `@pytest.mark.slow`

---

## TDD Cycles

### Cycle 1 ✅ — Unix-style JSON output

**Wat geïmplementeerd:**
- `_parse_pytest_output(stdout) -> dict` — parseert failures + summary
- `verbose` veld verwijderd uit `RunTestsInput`
- `execute()` retourneert `ToolResult.json_data(parsed)` — JSON primair, text fallback

**Bekende tekortkoming (aangepakt in C6):**
- `summary_line` ontbreekt in response (de mensleesbare "3 failed, 45 passed in 2.3s")
- `failures[].short_reason` bevat alleen de `FAILED path::test - reason` regel,
  niet de `--tb=short` traceback-regels

---

### Cycle 2 ✅ — last_failed_only parameter

**Wat geïmplementeerd:**
- `last_failed_only: bool = Field(default=False)` in `RunTestsInput`
- `_build_cmd(params)` private methode op `RunTestsTool`
- `--lf` flag in cmd bij `last_failed_only=True`

---

### Cycle 4: Marker sanering — afmaken

**Goal:**  
De drie overgeslagen acties uit C3 alsnog uitvoeren. Na deze cycle klopt de
marker-situatie in de suite volledig:
- Hermetic subprocess-tests dragen `@pytest.mark.slow`
- `test_create_issue_e2e.py` slaagt zonder live GitHub-verbinding

**Concrete acties:**

| Bestand | Actie |
|---|---|
| `tests/mcp_server/integration/test_create_issue_e2e.py` | 2 API-tests: `GitHubManager` mocken; 5 validatietests: `pytestmark` verwijderen |
| `tests/mcp_server/integration/test_workflow_cycle_e2e.py` | Inspecteren → als hermetisch: `@pytest.mark.slow` toevoegen |
| `tests/mcp_server/integration/test_issue39_cross_machine.py` | Inspecteren → als hermetisch: `@pytest.mark.slow` toevoegen |

**Betrokken bestanden:**
- Bovenstaande drie testbestanden

**RED — wat de test controleert:**
- `test_pytest_config.py`: `tests/mcp_server/integration/test_workflow_cycle_e2e.py`
  draagt `slow` marker (bestandsinhoud bevat `pytest.mark.slow`)
- `test_pytest_config.py`: `tests/mcp_server/integration/test_issue39_cross_machine.py`
  idem
- `test_create_issue_e2e.py` zelf: alle 7 tests slagen zonder live verbinding
  (geslaagd wanneer `GH_TOKEN` afwezig is)

**GREEN — minimale implementatie:**
Bovenstaande concrete acties uitvoeren.

**REFACTOR:**
- `run_quality_gates` op gewijzigde bestanden
- `pytest tests/mcp_server/ -q` — controleer: `slow`-tests draaien mee; integration-tests geskipt

**Acceptatiecriteria C4:**
- [ ] `test_workflow_cycle_e2e.py` draagt `@pytest.mark.slow`
- [ ] `test_issue39_cross_machine.py` draagt `@pytest.mark.slow`
- [ ] `test_create_issue_e2e.py` — alle tests slagen zonder `GH_TOKEN`
- [ ] Default suite draait exclusief de 5 (nu unmarked) validatietests uit test_create_issue_e2e

---

### Cycle 5: `scope` parameter op `RunTestsTool`

**Goal:**  
`RunTestsTool` krijgt een `scope` parameter die direct koppelt aan de marker-structuur.
Dit geeft de markers hun concrete nut: de agent kiest expliciet welke laag te draaien.

**Parameter definitie:**
```python
scope: Literal["unit", "all"] = Field(
    default="unit",
    description="'unit' skips slow tests (fast TDD loop); 'all' includes slow tests"
)
```

**Gedrag:**
- `scope="unit"` (default) → `-m "not slow"` — snelle TDD-loop, <5s
- `scope="all"` → geen extra markerfilter — inclusief `slow` subprocess-tests

**Betrokken bestanden:**
- `mcp_server/tools/test_tools.py` — `RunTestsInput`, `_build_cmd()`
- `tests/mcp_server/unit/tools/test_test_tools.py` — uitbreiden

**RED — wat de test controleert:**
- `scope="unit"` → cmd bevat `-m "not slow"`
- `scope="all"` → cmd bevat géén `-m "not slow"`
- Combinatie `scope="unit"` + `markers="foo"` → cmd bevat `-m "not slow and foo"`
- Default `scope` is `"unit"`

**GREEN — minimale implementatie:**
- `scope` veld toevoegen aan `RunTestsInput`
- `_build_cmd()` uitbreiden: scope-naar-markerfilter logica

**REFACTOR:**
- `run_quality_gates` op `test_tools.py`
- Tool description bijwerken met scope-uitleg

**Acceptatiecriteria C5:**
- [ ] `scope="unit"` slaat `slow` tests over
- [ ] `scope="all"` draait alles
- [ ] Combinatie met bestaande `markers` parameter werkt correct

---

### Cycle 6: Output verbetering

**Goal:**  
De JSON-response bevat een mensleesbare `summary_line` en de failure-details bevatten
de volledige `--tb=short` traceback, niet alleen de `FAILED`-regel.

**Concrete wijzigingen:**

1. **`summary_line`** — de ruwe pytest-samenvatting toegevoegd aan JSON:
   ```json
   {"summary_line": "3 failed, 45 passed in 2.31s", "summary": {...}, "failures": [...]}
   ```

2. **`text` content item** — wordt `summary_line` i.p.v. `json.dumps(data)`:
   - Groen: `"45 passed in 2.31s"`
   - Rood: `"3 failed, 45 passed in 2.31s"`

3. **failure `traceback`** — `--tb=short` blokken geparsed per test:
   ```json
   {"test_id": "test_foo", "location": "tests/foo.py::test_foo",
    "traceback": "tests/foo.py:15: in test_foo\n    assert result == 2\nE   AssertionError: assert 1 == 2"}
   ```

**Betrokken bestanden:**
- `mcp_server/tools/test_tools.py` — `_parse_pytest_output()`
- `tests/mcp_server/unit/tools/test_test_tools.py` — uitbreiden

**RED — wat de test controleert:**
- Response bevat `summary_line` key met de ruwe pytest-samenvatting
- `content[1]["text"]` == `summary_line` (niet json.dumps)
- Bij failure: `failures[0]` bevat `traceback` key met de `--tb=short` regels

**GREEN — minimale implementatie:**
- `_parse_pytest_output()` uitbreiden: `summary_line` extraheren + `--tb=short`
  blokken per test parsen
- `ToolResult` constructie aanpassen: text fallback = `summary_line`

**REFACTOR:**
- `run_quality_gates` op `test_tools.py`
- Edge cases: geen summary_line gevonden → `summary_line = ""`

**Acceptatiecriteria C6:**
- [ ] Response bevat `summary_line` bij zowel groene als rode run
- [ ] `content[1]["text"]` is de mensleesbare summary, niet een JSON-dump
- [ ] Failures bevatten traceback-regels van `--tb=short`

---

## Risks & Mitigation

- **Risico C4:** Mock van `GitHubManager` dekt label assembly niet volledig.
  - **Mitigatie:** Mock retourneert echte structuren; assertions controleren de
    argumenten van de `create_issue` aanroep (welke labels worden meegegeven).

- **Risico C5:** Combinatie `scope` + `markers` levert onverwachte markerexpressie op.
  - **Mitigatie:** Unit tests dekken alle combinaties expliciet.

- **Risico C6:** `--tb=short` output-formaat verschilt tussen pytest-versies.
  - **Mitigatie:** Parser is defensief; bij parse-fout valt `traceback` terug op
    lege string zonder crash.

---

## Dependencies

- C4 heeft geen code-afhankelijkheden van C1/C2 — puur testbestanden + pyproject
- C5 bouwt voort op `_build_cmd()` uit C2
- C6 bouwt voort op `_parse_pytest_output()` uit C1
- C5 vereist C4 (markers moeten kloppen vóór tool ze benut)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-22 | Scaffold aangemaakt |
| 1.1 | 2026-02-22 | TDD cycles uitgewerkt op basis van research |
| 1.2 | 2026-02-22 | C1 unix-style, C3 integration-sanering, C4 xdist |
| 1.3 | 2026-02-22 | asyncio_mode strict aan C3 REFACTOR + C4 prereq |
| 2.0 | 2026-02-22 | Volledige herziening: C1/C2 completed, C3 incomplete → C4 continuation, nieuwe C5 (scope parameter), nieuwe C6 (output verbetering), xdist buiten scope |
