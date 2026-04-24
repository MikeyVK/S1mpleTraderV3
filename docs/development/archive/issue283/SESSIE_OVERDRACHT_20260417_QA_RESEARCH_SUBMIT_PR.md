# SESSIE_OVERDRACHT 2026-04-17 — QA review research submit_pr (Issue #283)

**Datum:** 2026-04-17  
**Branch:** `refactor/283-ready-phase-enforcement`  
**Issue:** #283  
**Rol:** QA (`@qa`)  
**Fase tijdens review:** `research`  
**Primaire bron:** `docs/development/issue283/research-submit-pr-impact-analysis.md` v1.0

---

## Doel van deze overdracht

Deze overdracht legt de QA-analyse vast van de nieuwe researchronde rond het voorgestelde `submit_pr` atomic tool ontwerp. Doel is verder werken op een andere machine zonder contextverlies.

---

## Gereviewde bron

De actuele source of truth voor deze ronde is:

- `docs/development/issue283/research-submit-pr-impact-analysis.md`

Tijdens de review is expliciet vastgesteld dat eerdere issue-283 research/design/planning docs door dit document als **SUPERSEDED** worden gepositioneerd.

---

## Kern van het nieuwe voorstel

De research stelt dat het huidige sequentiele pad:

- `git_add_or_commit(workflow_phase="ready")`
- daarna `create_pr(...)`

een chicken-and-egg probleem veroorzaakt, omdat `neutralize_to_base()` `.st3/state.json` terugzet naar merge-base, waarna een latere `create_pr`-controle de verkeerde phase leest.

Voorgestelde oplossing:

- een nieuw atomair MCP tool: `submit_pr`
- in een enkele tool call: phase check, net-diff check, neutralize, commit, push, PR create

---

## QA-bevindingen

### 1. CRITIEK — bekende phase-guard bypass wordt bewust geaccepteerd

De research documenteert een echte guard-bypass en accepteert die daarna als out-of-scope restschuld.

Onderbouwende bronregels:

- `research-submit-pr-impact-analysis.md` §6a beschrijft de bypass
- `research-submit-pr-impact-analysis.md` §6c kwalificeert dit als medium risk
- `research-submit-pr-impact-analysis.md` §6d schuift de echte fix naar een separaat issue
- `research-submit-pr-impact-analysis.md` D6 kiest expliciet: post-PR gap enforcement **niet** in scope

Concrete productiecode die dit bevestigt:

- `mcp_server/tools/git_tools.py` in `build_phase_guard()`:
  - `if data.get("branch") != branch:`
  - `return  # state.json belongs to a different branch — skip`

QA-oordeel hierover:

- dit is geen acceptabele documentrestschuld voor design readiness
- het voorstel creëert of behoudt bewust een toestand waarin phase-validatie wegvalt
- “agent instructions” en “PR review” zijn hiervoor geen geldige technische mitigatie

### 2. HOOG — enforcement-boundary is nog niet ontwerpvast

De research laat een wezenlijke architectuurkeuze onbeslist of intern tegenstrijdig:

- enerzijds: `check_merge_readiness` blijft bestaan en wordt “intern” door `SubmitPRTool.execute()` aangeroepen
- anderzijds: D1 adviseert om enforcement juist uit yaml te halen en internal in `execute()` te doen

Dat levert nog geen stabiele boundary op tussen:

- declaratieve enforcement via `enforcement_event` + `EnforcementRunner`
- versus tool-internal domeinchecks in `SubmitPRTool.execute()`

Relevante actuele architectuur:

- `server.py` voert enforcement generiek uit op basis van `tool.enforcement_event`
- `CreatePRTool` gebruikt nu ook al zo’n boundary via `enforcement_event = "create_pr"`

QA-oordeel hierover:

- zolang niet expliciet gekozen is voor één patroon, is de research nog niet design-ready
- een volgende designronde moet deze boundary eerst vastzetten

### 3. MATIG — test-impactinventaris is niet overal feitelijk scherp

De research classificeert `tests/mcp_server/integration/test_model1_branch_tip_neutralization.py` alsof dat bestand de neutralize→create_pr-sequentie test.

Bij codecontrole bleek:

- het bestand test `GitCommitTool` + `ExclusionNote` + neutralize-commitgedrag
- het test niet de aparte `create_pr` call sequence zelf

QA-oordeel hierover:

- de impactinventaris is bruikbaar als startpunt, maar nog niet betrouwbaar genoeg als planningsbasis
- voor design/planning moet deze inventaris eerst feitelijk worden opgeschoond

---

## Samenvattend oordeel

### Verdict

**Niet design-ready / implementatie-ready.**

Reden:

1. Het voorstel accepteert een bekende enforcement-bypass als out-of-scope.
2. De enforcement-boundary van `submit_pr` is nog niet architectonisch vastgelegd.
3. De impactanalyse is nog niet scherp genoeg om direct planning op te bouwen.

---

## Wat wél klopt in de research

De volgende delen van de research zijn inhoudelijk plausibel en bruikbaar als basis voor een volgende iteratie:

- de kip-ei probleemstelling rond `git_add_or_commit` gevolgd door `create_pr`
- het inzicht dat een atomaire tool het fase-lezen vóór neutralisatie kan uitvoeren
- de observatie dat `NoteContext` niet cross-call gedeeld hoeft te worden
- de algemene impactrichting: nieuwe tool, testherschikking, documentatierewrite

Met andere woorden:

- het probleem is reëel
- de oplossingsrichting kan valide zijn
- maar de huidige researchversie is nog niet strak genoeg om er design op te baseren

---

## QA-aanbevolen vervolgstappen voor research/design

### Verplicht vóór design

1. Trek de post-submit enforcement-gap terug in scope, **of** herdefinieer `submit_pr` zodanig dat deze bypass niet ontstaat.
2. Kies expliciet één enforcement-boundary:
   - of declaratief via `enforcement_event` + `EnforcementRunner`
   - of via een expliciet geëxtraheerde service/facade
   - maar niet impliciet via ad-hoc private-handler hergebruik in de tool.
3. Corrigeer de test-impactinventaris zodat per testbestand feitelijk klopt:
   - wat direct breekt
   - wat surviveert
   - wat herschreven moet worden

### Pas daarna

4. Scaffold nieuwe design doc voor `submit_pr`.
5. Scaffold daarna planning op basis van het gecorrigeerde design.

---

## Relevante bronverwijzingen uit productiecode

### Phase guard bypass

- `mcp_server/tools/git_tools.py` — `build_phase_guard()`
- branch mismatch veroorzaakt early return zonder validatie

### Huidige enforcement boundary

- `mcp_server/server.py` — generieke enforcement dispatch via `tool.enforcement_event`
- `mcp_server/tools/pr_tools.py` — `CreatePRTool.enforcement_event = "create_pr"`

### Bestaande neutralize-commitroute

- `mcp_server/tools/git_tools.py` — terminal route in `GitCommitTool.execute()`
- `mcp_server/managers/enforcement_runner.py` — `_handle_check_merge_readiness()`

---

## Uitdrukkelijk niet gedaan in deze QA-ronde

- geen codewijzigingen uitgevoerd
- geen tests gedraaid voor deze researchreview
- geen commit of workflowtransitie uitgevoerd

Deze review was een research-tegen-code consistentiecontrole.

---

## Korte overdracht voor volgende machine

Als je dit op een andere machine oppakt, begin dan met:

1. Lees `docs/development/issue283/research-submit-pr-impact-analysis.md` volledig.
2. Lees daarna deze overdracht.
3. Behandel het huidige QA-oordeel als **NO GO voor design** totdat:
   - de phase-guard bypass inhoudelijk is opgelost of uit scope-verdediging verdwijnt,
   - de enforcement-boundary expliciet gekozen is,
   - de test-impactinventaris gecorrigeerd is.

Daarna pas nieuwe design/planning review starten.