<!-- docs\development\issue103\research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-22T08:16Z updated=2026-02-22 -->
# Enhance run_tests tool for large test suites

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-02-22

---

## Purpose

Onderzoek bottlenecks in de run_tests tool en test suite, identificeer verbeterkansen op
het gebied van output-filtering, performance-isolatie en test-code kwaliteit (SOLID).
Bevindingen vormen de basis voor de planning fase.

## Scope

**In Scope:**
run_tests tool output-formaat, pytest marker-strategie, performance-profiel per submap,
test-code kwaliteit (DRY/SRP/SSOT), test suite clean-up aanpak

**Out of Scope:**
Implementatiedetails, concrete TDD-cycles, CI/CD pipeline integratie, pytest-xdist configuratie

## Prerequisites

1. Issue #247 afgerond — `tests/backend/` (483) en `tests/mcp_server/` (1836) gescheiden
2. Baseline timing: `pytest tests/mcp_server/` = **73s** voor 1836 tests

---

## Problem Statement

De run_tests tool retourneert volledige pytest output (~285KB voor 1836 tests), schrijft
deze naar een temp file in plaats van inline te retourneren, en heeft geen mechanisme om
trage of extern-afhankelijke tests te isoleren van standaard TDD-runs. Dit maakt de tool
onschaalbaar voor grote test suites en dwingt de agent tot extra tool calls (grep op temp
file) om het resultaat te interpreteren.

## Research Goals

1. Doorgronden welke informatie een agent feitelijk nodig heeft uit test output
2. Identificeren van performance bottlenecks in de huidige test suite (73s baseline)
3. Onderzoeken van risico's en randvoorwaarden voor marker-gebaseerde test isolatie
4. Onderzoeken hoe SOLID principes in testcode de blast radius van productie-wijzigingen
   reduceert
5. Formuleren van randvragen voor een mogelijke test suite clean-up slag

## Related Documentation

- [docs/development/issue247/research.md](../../issue247/research.md) — vorige test-structuur research
- [docs/coding_standards/README.md](../../../coding_standards/README.md) — test placement guardrails

---

## Bevinding 1: Performance profiel huidige test suite

Meting via `pytest tests/mcp_server/ --durations=20` op 2026-02-22.

### Totaalverdeling per submap

| Submap | Tests | Tijd | Gem/test | Opmerking |
|---|---|---|---|---|
| `tests/mcp_server/unit/` | ~1712 | ~56s | ~33ms | Bulk van de suite |
| `tests/mcp_server/integration/` | 124 | ~14s | ~113ms | Geen echte externe deps |
| Overig (tier0-2, acceptance, regression, root) | ~118 | <5s | ~42ms | — |
| **Totaal** | **1836** | **73s** | — | — |

### Top-20 langzaamste tests (top 5 weergegeven)

| Tijd | Test | Oorzaak |
|---|---|---|
| 2.40s | `test_qa.py::test_qa_manager_run_gates_with_real_file` | Spawnt echte ruff/mypy subprocessen |
| 2.21s | `test_qa.py::test_quality_tool_output_format` | Idem |
| 1.96s | `test_workflow_cycle_e2e.py::test_full_workflow_cycle_with_scope_detection` | Git repo + subprocess in tmp_path |
| 1.16s | `test_discovery_tools.py::TestGetWorkContextTool::test_get_context_with_github_integration` | GitHub API call |
| 1.13s | `test_issue39_cross_machine.py::TestIssue39CrossMachine::test_complete_cross_machine_flow` | Subprocess git + tmp_path |

De drie `test_qa.py` tests vertegenwoordigen samen **~6.5s** van de 73s totaal (~9% van de
looptijd) voor 3 van de 1836 tests.

### Diagnose van de 56s unit-subtotaal

De 56s voor ~1712 unit tests @ gemiddeld 33ms is geen alarmerend getal per individuele
test, maar het cumulatieve effect van:

- `asyncio_mode = "auto"` — elke async test start een event loop
- `reset_config_singletons` autouse fixture — draait bij alle 1836 tests (twee maal per
  test: setup + teardown)
- Verborgen I/O in "unit" tests die bestanden of git operaties uitvoeren
  (zie bottleneck-sectie hieronder)

---

## Bevinding 2: Marker-discipline — risico's en randvoorwaarden

### Huidig marker-gebruik

De marker `integration` is gedefinieerd in `pyproject.toml` en standaard uitgefilterd via
`addopts = ["-m", "not integration"]`. Maar de daadwerkelijke toepassing is minimaal:

| Locatie | Gebruik van `integration` marker |
|---|---|
| `tests/mcp_server/integration/test_create_issue_e2e.py` | `pytestmark = pytest.mark.integration` ✓ |
| `tests/mcp_server/core/test_proxy.py` | `@pytest.mark.integration` ✓ (1 test) |
| Alle overige 117 tests in `tests/mcp_server/integration/` | **Geen marker** |
| `tests/mcp_server/unit/mcp_server/integration/test_qa.py` | **Geen marker** (3 trage tests) |

De marker `slow` bestaat in `pyproject.toml` maar wordt **nergens gebruik**.

### Drie betekenissen van "integration" — broncode van verwarring

Het woord "integration" heeft in de huidige codebase drie onverenigbare betekenissen:

1. **Map-naam** (`tests/mcp_server/integration/`) — werd historisch gebruikt als "niet-unit"
2. **pytest marker** `integration` — bedoeld als "raakt echte externe service"
3. **Bestandsnaam in unit/mcp_server/** — `unit/mcp_server/integration/` bevat tests die
   echte subprocessen spawnen, maar in de unit-boom zitten

Zolang deze drie betekenissen door elkaar lopen is marker-discipline onbetrouwbaar.

### Risico's bij invoeren van marker-gebaseerd skippen

**Risico A — Vals groen bij agent-TDD-cyclus**  
Als `test_qa.py` als `slow` of `integration` gemarked en standaard geskipt wordt, kan
een agent de volledige TDD cyclus succesvol afronden en "green" committen, terwijl de
QAManager (die in `run_quality_gates` zit — een kerncomponent) kapot is. De failure
verschijnt pas bij een full run.

**Risico B — Semantische drift naar de toekomst**  
Zonder een expliciete definitie per marker zullen toekomstige tests worden gemarked op
basis van directorycontext in plaats van gedrag. Een test die in `integration/` staat
krijgt dan automatisch het label "mag geskipt worden", ook als het een kritische smoke
test is.

**Risico C — Vrijwillig systeem zonder afdwinging**  
Markers werken als afspraak op eer. Nieuwe tests in `tests/mcp_server/integration/`
zonder marker draaien altijd mee en bouwen de looptijd onzichtbaar op. Er is nu geen
kwaliteitsgate of lint-regel die dit signaleert.

### Randvoorwaarden voor veilige marker-discipline

Voordat markers als isolatiemechanisme kunnen worden ingevoerd, moeten twee vragen
beantwoord zijn:

1. **Definitie per marker:**
   - `integration` = raakt echte externe service (GitHub API, live git remote, filesystem
     buiten tmp_path). Mag geskipt worden in standaard TDD-run.
   - `slow` = hermetisch maar >500ms (bv. subprocess git in tmp_path). Geskipt in snelle
     dev-run, draait bij pre-commit of merge.
   - _(geen marker)_ = volledig gemocked of in-memory. Draait altijd.

2. **Expliciete "altijd-draait" lijst:**  
   Trage tests die kritische productie-paden dekken (bv. `test_qa.py`) moeten expliciet
   als "altijd draaien" worden aangemerkt, ongeacht hun snelheid. Dit is een inhoudelijke
   beslissing die niet volledig te automatiseren is.

3. **Afdwinging via kwaliteitsgate (wenselijk):**  
   Een gate die controleert of bestanden in `tests/mcp_server/integration/` een expliciete
   marker hebben. Hierdoor wordt de afspraak structureel afdwingbaar.

---

## Bevinding 3: Tool output — wat heeft een agent nodig?

### Analyse van de huidige output

Bij 1836 tests retourneert `RunTestsTool.execute()` de ruwe pytest stdout (~285KB). Dit
bevat:

- **Voortgangsbalk:** 1836 regels met `.`, `F`, `s` — voor een agent waardeloos
- **155 DeprecationWarnings:** telkens herhaald per testbestand dat de offending import
  bevat — voor een agent ruis die ruimte inneemt
- **Platform/systeem header:** Python-versie, OS, rootdir, datum — niet relevant voor een
  agent die al weet in welke omgeving hij werkt
- **Volledige traceback bij failures:** meerdere frames — waarvan de agent doorgaans alleen
  de laatste assertieregel nodig heeft om te begrijpen wat er misgaat

Van de ~285KB draagt minder dan 1KB bij aan de twee vragen die een agent daadwerkelijk
stelt.

### Wat een agent feitelijk vraagt

Een agent in een TDD-cyclus heeft twee vragen:

1. Zijn alle tests groen? → één bevestigingszin volstaat
2. Zo niet: welke tests falen, op welke regel, met welke fout?

### Gewenst output-formaat

**Primaire response (altijd):**

```json
{
  "summary": {
    "total": 1836,
    "passed": 1833,
    "failed": 2,
    "skipped": 10,
    "errors": 0,
    "xfailed": 2,
    "duration_s": 73.4,
    "path": "tests/mcp_server/"
  },
  "failures": [
    {
      "test_id": "tests/mcp_server/unit/tools/test_discovery_tools.py::TestGetWorkContextTool::test_x",
      "short_reason": "AssertionError: expected 'active' but got None",
      "location": "tests/mcp_server/unit/tools/test_discovery_tools.py:142"
    }
  ]
}
```

**Secundaire response (text, als fallback voor legacy clients):**

```
✅ 1836 passed (73.4s) — tests/mcp_server/
```

of bij failures:

```
❌ 2 failed / 1836 (73.4s)
  FAILED tests/.../test_x.py::test_x — AssertionError: expected 'active' but got None
  FAILED tests/.../test_y.py::test_y — KeyError: 'workflow_name'
```

### Wat er nooit in moet

- Passing test output (voortgangsbalk, `PASSED` regels bij verbose)
- DeprecationWarning spam (hooguit één keer per unieke warning, niet per testbestand)
- Platform/systeem header
- Volledige multi-frame tracebacks — alleen de bestandslocatie + failureregel

### Relatie tot de temp-file situatie

De temp-file situatie is een gevolg van MCP server response-size limieten. De fix zit
aan de `ToolResult`-kant: een gestructureerde JSON-response met summary + failures past
altijd binnen de limieten ongeacht de test suite grootte. Dezelfde aanpak is al
toegepast in `RunQualityGatesTool` (JSON primair, text als fallback) — dat is het model
om te volgen.

---

## Bevinding 4: SOLID principes in testcode — blast radius probleem

### Observatie

Relatief kleine wijzigingen in productiecode veroorzaken soms een disproportioneel grote
hoeveelheid falende tests. De oorzaak is te herleiden naar dezelfde SOLID-schendingen
die ook in productiecode worden vermeden, maar in testcode minder consequent worden
aangesproken.

### DRY-schending: gedupliceerde setup-logica

Wanneer dezelfde setup (bv. een manager instantiëren met specifieke config, een mock
opzetten voor een service) in meerdere testbestanden los wordt herhaald, dan breekt een
signatuurwijziging in de constructor of een config-naam-wijziging op tientallen plaatsen
tegelijkertijd. Dit is het blast radius probleem: de wijziging zelf is klein, maar de
test-aanpassingen zijn tijdrovend.

**Principe:** Setup-logica die meer dan één keer voorkomt hoort in een fixture, niet
inline in de test.

### SRP-schending: één testklasse test meerdere verantwoordelijkheden

Een `TestPhaseStateEngine` klasse met 60+ test methods die zowel persistence, recovery,
phase transitions als cycle validation test, is moeilijk te onderhouden. Als de
persistence-laag wijzigt, zijn méér tests geraakt dan nodig omdat ze allemaal via
dezelfde klasse het systeem benaderen.

**Principe:** Eén testklasse, één verantwoordelijkheid. Splits op gedragsdomein, niet op
de klasse die getest wordt.

### SSOT-schending: hardcoded waarden in tests

Wanneer tests hardcoded strings, paden of verwachte outputs bevatten die ook in
productie-config staan (bv. marker-namen, phase-namen, artifact-typen), dan breekt een
config-wijziging zowel de productiecode als de tests. De test wordt een tweede bron van
waarheid.

**Principe:** Tests lezen verwachte waarden via dezelfde config-objecten die de
productiecode ook gebruikt. Niet: `assert result == "research"`, maar:
`assert result == WorkflowConfig.phases[0].name`.

### Tight coupling: tests die interne implementatiedetails testen

Tests die controleren of een private methode een bepaald pad bewandelt (bv. via
`unittest.mock.patch` op een private methode), zijn direct gekoppeld aan de
implementatiestructuur. Elke refactor — zelfs als het zichtbare gedrag gelijkblijft —
breekt zulke tests.

**Principe:** Test gedrag, niet implementatie. Patch op de grens van het systeem
(externe services, filesystem, klok), niet op interne methoden.

### Overstimulatie van mocking

Overmatig gebruik van mocks maskert de werkelijke integratie van componenten. Een test
die alles mockt behalve de klasse-zelf test in feite niets over hoe componenten samen
werken. Dit resulteert in tests die groen zijn terwijl de echte integratie kapot is.

**Tegengewicht:** Het risico van te weinig mocking is trage of fragiele tests. De balans
zit in mocking op de infrastructuurgrens (netwerk, filesystem, klok) en vertrouwen op
echte instanties voor de domeinkoppelingen.

---

## Bevinding 5: Test suite clean-up — wanneer en hoe

### Wanneer is een clean-up run zinvol?

Een gerichte clean-up run is zinvol wanneer:

- De test suite structureel is gereorganiseerd (zoals net gedaan in issue #247) en er
  tests zijn die het nieuwe ontwerp nog niet volgen
- De blast radius van een kleine productie-wijziging structureel groter is dan verwacht
- De looptijd van de suite stijgt zonder proportioneel meer coverage te bieden

Een algemeen moment: **vóór** het starten van nieuwe feature-development op een module,
niet na afloop — anders stapelen verouderde tests zich op.

### Wat een clean-up run inhoudt

1. **Deprecated tests verwijderen:** Tests die meten wat in de productiecode al verwijderd
   is. Te identificeren via `pytest --collect-only` gecombineerd met coverage-analyse:
   als een test coverage genereert voor code die niet meer bestaat, is hij kandidaat.

2. **Setup-duplicaten consolideren:** Testbestanden die dezelfde fixture-logica herhalen
   → verplaatsen naar een shared `conftest.py` op het juiste niveau.

3. **Tight-coupling tests refactoren:** Tests die private methoden patchen → herschrijven
   naar gedragsgerichte tests.

4. **Marker-audit:** Elk bestand in `tests/mcp_server/integration/` krijgt een expliciete
   marker op basis van de definitie uit Bevinding 2.

### Voorkomen is beter dan genezen

Afdwinging van SOLID in testcode kan op twee niveaus:

**Niveau 1 — Review criterium (nu toepasbaar):**  
In code review (of agent-TDD-protocol): een PR mag geen nieuwe test introduceren die
dezelfde fixture-logica herhaalt die al in een conftest beschikbaar is. Controleer op
hardcoded config-waarden die ook via een config-object beschikbaar zijn.

**Niveau 2 — Tooling-gebaseerd (toekomstig):**  
- `ruff` kan DRY-schendingen niet detecteren, maar een custom pytest plugin of
  `flake8`-extensie kan herhalende patroontjes signaleren
- Coverage gecombineerd met code-complexiteit: als een test methode `> X` mocks heeft,
  is dat een signaal voor overmatige koppeling
- Mutatietesten (`mutmut`) onthult tests die niets echts meten: als een mutatie in
  productiecode geen test rood maakt, test die test niet wat hij beweert te testen

---

## Bevinding 6: `test_create_issue_e2e.py` — de enige `integration` marker is onnodig

### Situatie

`tests/mcp_server/integration/test_create_issue_e2e.py` is het enige bestand in de
gehele suite met `pytestmark = pytest.mark.integration`. Dit maakt het de enige reden
dat de `integration` marker überhaupt actief is. Bij nader inzien bestaat het bestand
uit twee categorieën die fundamenteel verschillen:

**2 tests die écht de live GitHub API raken:**
- `test_minimal_input_creates_issue_with_correct_labels` — maakt een echt issue aan,
  haalt het terug om labels te verifiëren
- `test_all_options_creates_issue_with_full_label_set` — idem met epic + parent-label

**5 tests die de GitHub API nooit aanraken:**
- `test_invalid_issue_type_is_refused_before_api_call`
- `test_invalid_scope_is_refused_before_api_call`
- `test_invalid_priority_is_refused_before_api_call`
- `test_title_too_long_is_refused_before_api_call`
- `test_milestone_accepted_when_milestones_yaml_is_empty`

Die laatste 5 zijn pure Pydantic-validatietests. Ze testen of `CreateIssueInput` ongeldige
input weigert vóórdat er iets naar GitHub gaat. Ze dragen de `integration` marker omdat
ze toevallig in hetzelfde bestand staan als de 2 echte API-tests — niet op inhoudelijke
gronden.

### Conclusie

De 2 API-tests horen te worden herschreven met een gemockte `GitHubManager`. Wat je
bij mocking verliest is de verificatie dat het label daadwerkelijk op het GitHub issue
staat — maar dat is precies wat de **validatiefase** van iedere issue-cyclus structureel
dekt. Wat je wint:

- De test draait standaard mee en bewaakt label assembly-logica continu
- Geen echte issues als bijwerking van een testrun
- De `integration` marker verdwijnt volledig uit de suite — er is dan geen uitzondering
  meer, wat Bevinding 2 structureel oplost

De 5 validatietests hoeven alleen de `pytestmark`-regel te verliezen — geen verdere
aanpassing nodig.

---

## Conclusies — open vragen beantwoord

### 1. Outputformaat: JSON primair, text als fallback

Beslissing: zelfde patroon als `RunQualityGatesTool`. De primaire response is een
gestructureerd JSON-object; een mensleesbare textsamenvatting als tweede content-item
voor legacy clients. Motivatie: een agent kan `response["summary"]["failed"]` direct
lezen zonder parsing. Geen temp-file indirectie mogelijk met een respons die altijd klein
is (summary + failures-lijst, geen volledige output).

### 2. output_mode default: `failures`

Beslissing: `failures` als default. Rationale: in een TDD-cyclus wil de agent bij een
rode run direct de fout zien zonder te zoeken in volledige output; bij een groene run
volstaat de samenvattingsregel. `full` is beschikbaar maar enkel op expliciete aanvraag.
Drie modi:
- `minimal` — alleen summary counts
- `failures` — summary + gefailde tests met locatie en failureregel **(default)**
- `full` — huidige gedrag

### 3. Marker-strategie: `integration` afschaffen, alleen `slow` behouden

Beslissing: de `integration` marker wordt afgeschaft. Bevinding 6 toont dat de enige
gebruiker (test_create_issue_e2e.py) herschreven wordt met een gemockte GitHubManager,
waarna er geen tests meer zijn die de marker rechtvaardigen. Echte externe calls worden
uitsluitend gedekt door de **validatiefase** van iedere issue-cyclus.

De `slow` marker blijft als opt-out voor subprocess-zware hermetische tests (>500ms).
Definitie: `slow` = volledig hermetisch maar spawnt echte subprocessen of git-operaties
op tmp_path. Standaard ingeschakeld; bij expliciete snelle dev-run te skippen via
`pytest -m "not slow"`.

Gevolg voor `pyproject.toml`:
- `addopts` verliest `"-m", "not integration"` — alle niet-slow tests draaien standaard
- Markerdefinitie `integration` wordt verwijderd
- Markerdefinitie `slow` blijft en wordt uitgebreid met bovenstaande definitie

### 4. Test suite clean-up: apart issue

Beslissing: clean-up (deprecated tests verwijderen, setup-duplicaten naar conftest,
SOLID-audit van bestaande testbestanden) wordt een apart issue. Issue #103 blijft
gefocust op de run_tests tool verbetering. Motivatie: mix van scope maakt #103
moeilijker te sluiten en de clean-up verdient eigen TDD-cycles.

### 5. Blast radius afdwinging: review-criterium nu, tooling later

Beslissing: begin met review-criterium als PR-check, geen tooling-investering in deze
cyclus. Motivatie: review-criterium pakt schendingen op het moment van introductie,
voorkomt ophoping, en vereist nul infrastructuur. Twee concrete criteria om nu te
handhaven:

1. Een nieuwe test mag geen fixture-setup herhalen die al in een conftest op hetzelfde
   of hoger niveau beschikbaar is.
2. Een test mag geen hardcoded verwachte waarde bevatten voor een waarde die ook via
   een config-object (`WorkflowConfig`, `ScopeConfig`, etc.) beschikbaar is.

Mutatietesten (`mutmut`) staat op de agenda als de suite schoon genoeg is voor een
zinvolle baseline — niet nu.

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-22 | Agent | Scaffold aangemaakt |
| 1.1 | 2026-02-22 | Agent | Bevindingen research-sessie verwerkt |
