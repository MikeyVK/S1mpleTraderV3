# Gap Analyse — Issue #257 Config-First PSE Architecture

**Datum:** 2026-03-13  
**Branch:** `feature/257-reorder-workflow-phases`  
**Status:** QA-bevindingen geconsolideerd — herstelplan opgesteld  
**KPI-score:** 10/20 groen · 10/20 rood  
**Testbaseline:** 2132 passed, 11 skipped, 2 xfailed

---

## 1. Root Cause Analyse

### Hoe zijn de gaps ontstaan?

De implementatie heeft **systematisch nieuwe componenten correct gebouwd en getest, maar de integratie van die componenten in het bestaande systeem overgeslagen**. Dit patroon herhaalt zich over alle Cycles.

#### RC-1 — Stop/Go criteria werden niet geëvalueerd als gate

Planning.md bevat exacte verificatiecommando's per Cycle. Cycle 1 Stop/Go vereiste onder andere:
> "projects.json does not exist — all references removed"

`.st3/projects.json` **bestaat nog steeds fysiek**. Dit bewijst dat de implementatie-agent door is gegaan naar Cycle 2 zonder de Stop/Go-gate van Cycle 1 te have gevalideerd. Elke volgende Cycle bouwt op de veronderstelling dat vorige volledig zijn afgerond.

**Effect:** Technische schuld accumuleert onzichtbaar. Cycle 7 wordt als "done" gemeld, maar 10 van 20 KPIs zijn rood.

#### RC-2 — "Component bouwen" wél gedaan, "component indraden" systematisch overgeslagen

| Nieuw component | Gebouwd? | Geïntegreerd in bestaand systeem? |
|---|---|---|
| `PhaseContractResolver` | ✅ klasse aanwezig, getest | ❌ PSE exit-hooks negeren het volledig |
| `StateRepository` | ✅ aanwezig, DI in PSE | ⚠️ PSE gebruikt het maar 3× directe `DeliverableChecker()`-instantiaties in PSE blijven |
| `EnforcementRunner` | ✅ gebouwd, post-hooks actief | ❌ `delete_file` handler ontbreekt, geen post-merge rule |
| `AtomicJsonWriter` | ✅ aanwezig | ✅ gebruikt voor state.json en deliverables.json |

Het meest treffende voorbeeld: `PhaseContractResolver` bestáát, heeft werkende `.resolve()` methode, is volledig getest — maar `on_exit_planning_phase()` in de PSE doet nog steeds directe `project_plan["tdd_cycles"]["cycles"]` dict-traversal. De class staat op 10 meter afstand en wordt nergens aangeroepen vanuit de exit-hooks.

#### RC-3 — Geen structurele tests voor SOLID-eigenschappen

De testsuite is groen (2132 passed) terwijl 10 KPIs rood zijn. Dat kan alleen als de tests uitsluitend *gedrag* testen, niet *structuur*. Geen enkele test verifieert:

- *Roept `PSE.transition()` de `_exit_hooks` registry aan i.p.v. een if-chain?*
- *Wordt `DeliverableChecker` max 1× geïnstantieerd?*
- *Gebruikt `on_exit_design_phase()` de `PhaseContractResolver`?*
- *Bevat `phase_state_engine.py` geen f-string logging?*

Een `grep`-verificatie was de voorgeschreven Stop/Go check. Die is nooit uitgevoerd.

#### RC-4 — PSE was het hoogste-risico refactorobject en is systematisch vermeden

PSE is 869+ regels, de meest complexe file, met de hoogste testdekking. Het indraden van exit-hooks via de PCR vereist gelijktijdige wijzigingen in `__init__` (registry dict), `transition()` (dispatch), en 5+ `on_exit_*` methoden plus al hun unit tests. Dit is het hoogste-risico werk van de gehele refactoring.

De TDD-discipline werd consequent toegepast op nieuwe, geïsoleerde code (laag risico, eenvoudig isoleerbaar). De TDD-discipline voor refactoring van *bestaande, sterk geteste code* is systematisch uitgesteld.

#### RC-5 — `.st3/` directory-migratie: half work is erger dan no work

De huidige staat van `.st3/`:
```
.st3/
  config/              ← aangemaakt ✅
    enforcement.yaml
    phase_contracts.yaml
  deliverables.json    ← moet naar registries/ ❌
  state.json           ← moet naar registries/ ❌
  projects.json        ← moet verwijderd worden ❌
  workflows.yaml       ← moet naar config/ ❌
  workphases.yaml      ← moet naar config/ ❌
  [12 andere YAML-configs in root] ❌
  [registries/ submap bestaat niet] ❌
```

Twee bestanden zijn in `config/` gezet. De `registries/` submap bestaat niet. Alle source-code paden verwijzen nog naar `.st3/*.json`. De structuur suggereert dat de migratie "al gedaan is" terwijl ze slechts 2/15 stappen ver is.

#### RC-6 — `phase_contracts.yaml` fundamenteel misgebruikt *(additionele bevinding)*

De huidige inhoud van `.st3/config/phase_contracts.yaml`:
```yaml
workflows:
  feature:
    planning:
      exit_requires:
        - id: planning-doc
          type: file_exists
          file: docs/development/issue257/planning.md    # ← HARDCODED voor issue 257!
    implementation:
      exit_requires:
        - id: design-doc
          type: file_exists
          file: docs/development/issue257/design.md     # ← HARDCODED voor issue 257!
```

`phase_contracts.yaml` is bedoeld als **workflow-level contract** — geldig voor ALLE issues van type `feature`. De implementatie-agent heeft het gevuld met issue-specifieke paden (`issue257`). Dit betekent:
- Voor issue #257 zelf: werkt toevallig
- Voor elke andere `feature`-branch: de planning-gate controleert `issue257/planning.md` i.p.v. het actuele issue → false positives op elke andere branch

Dit is een fundamenteel conceptmisverstaan van het design: de `{issue_number}` interpolatie (zoals beschreven in F12 van de research) is niet geïmplementeerd.

#### RC-7 — `cycle_tools.py` roept private methode aan via buitenobject *(additionele bevinding)*

In [cycle_tools.py regel 129](../../mcp_server/tools/cycle_tools.py#L129):
```python
state_engine._save_state(branch, updated_state)
```

`_save_state` is een private methode van `PhaseStateEngine`. Buitencode mag deze methode niet aanroepen — dit doorbreekt de encapsulatie en bypassed de `IStateRepository`-grens die in Cycle 2 werd opgezet. Correct zou zijn `state_engine._state_repository.save(updated_state)` of een publieke wrapper.

#### RC-8 — planning.md als architectuurdocument, niet als uitvoerbare checklist

planning.md bevat voor elke Cycle precies de verificatiecommando's die als Stop/Go moeten dienen. Het document is blijkbaar één keer gelezen voor architectureel begrip en daarna niet actief geraadpleegd. Het verschil:

- **Design document:** lees → begrijp → implementeer
- **Executable specification:** lees → volg elk punt → toon bewijs van voltooiing (grep-uitvoer, Pyright-output, testresultaat) voordat Cycle N+1 start

---

## 2. Commit Historie per Cycle

```
Cycle 1:  dbe8c15  chore(P_IMPLEMENTATION_SP_C1_REFACTOR): complete cycle 1 phase rename and deliverables migration
Cycle 2:  b5e2972  chore(P_IMPLEMENTATION_SP_C2_RED): add state repository contracts and atomic writer tests
          f18fc68  chore(P_IMPLEMENTATION_SP_C2_GREEN): implement state repository and atomic writer primitives
          22ec2ee  chore(P_IMPLEMENTATION_SP_C2_REFACTOR): inject state repository into phase state engine
          68b767e  chore(P_IMPLEMENTATION_SP_C2_REFACTOR): align BranchState API and remove legacy workflow config
Cycle 3:  a1e5d68  chore(P_IMPLEMENTATION_SP_C3_RED): add phase contract resolver red tests
          42fa656  chore(P_IMPLEMENTATION_SP_C3_GREEN): implement phase contract resolver and config loader
          ad066ca  chore(P_IMPLEMENTATION_SP_C3_REFACTOR): refine phase contract resolver typing and formatting
          8e72572  chore(P_IMPLEMENTATION_SP_C3_REFACTOR): align phase contract merge semantics and config naming
Cycle 4:  fd48c39  chore(P_IMPLEMENTATION_SP_C4_RED): add cycle 4 git tool commit contract tests
          f4f6df4  chore(P_IMPLEMENTATION_SP_C4_GREEN): implement tool-layer commit type resolution
          b0fbe6a  chore(P_IMPLEMENTATION_SP_C4_REFACTOR): align workflow regressions and windows state writes
          d5d9da5  chore(P_IMPLEMENTATION_SP_C4_REFACTOR): remove legacy test debt
          df3dff8  chore(P_IMPLEMENTATION_SP_C4_REFACTOR): migrate remaining workflow test debt and close point 6
          748656f  chore(P_IMPLEMENTATION_SP_C4_REFACTOR): migrate typed BranchState test callers
Cycle 5:  1de388b  chore(P_IMPLEMENTATION_SP_C5_RED): add failing enforcement runner and dispatch hook tests
          d2c8872  chore(P_IMPLEMENTATION_SP_C5_GREEN): implement enforcement runner and dispatch hook integration
          a3d4da6  chore(P_IMPLEMENTATION_SP_C5_REFACTOR): polish enforcement runner types and dispatch test harness
Cycle 5.1 9bdb5df  refactor(P_IMPLEMENTATION_SP_REFACTOR): finalize cycle enforcement hooks and cycle tool refactor
          e10c60c  refactor(P_IMPLEMENTATION_SP_REFACTOR): remove dead cycle settings export and rename legacy cycle tests
Cycle 6:  (geen aparte C6-commits; C6-deliverables zijn direct in C7 geland)
Cycle 7:  2aa9309  chore(P_IMPLEMENTATION_SP_C7_GREEN): use atomic deliverables writes and track state file
          2600601  chore(P_IMPLEMENTATION_SP_C7_GREEN): warn on uncommitted state during branch init
          c0cf3d5  chore(P_IMPLEMENTATION_SP_C7_REFACTOR): clean up cycle 7 state tracking changes
          fec31d0  chore(P_IMPLEMENTATION_SP_C7_REFACTOR): restore issue 257 implementation state
```

**Opvallend:** Cycle 6 bestaat niet als aparte serie commits. C6 (deliverables.json tooling + state.json git-tracked) is deels als C7 ingeboekt. Tevens ontbreekt een Cycle 6 RED-commit volledig, wat betekent dat de TDD-volgorde niet is gevolgd voor C6.

---

## 3. Cycle-by-cycle DoD Review

### Cycle 1 — Foundations & Renames

**Doel:** Elimineer dead code, hernoem alle bewegende delen.

| DoD Item | Verwacht | Werkelijk | Status |
|---|---|---|---|
| `implementation` in workflows.yaml | Ja | Ja (KPI 1) | ✅ |
| `workflow_config.py` verwijderd | Ja | Geen bestand gevonden | ✅ |
| `GitConfig.extract_issue_number()` | Aanwezig | Aanwezig | ✅ |
| `_extract_issue_from_branch` weg uit PSE | Ja | Weg (KPI 15) | ✅ |
| `projects.json` verwijderd (fysiek) | Ja | **Bestand bestaat nog** | ❌ |
| Geen `tdd`-literals in source | Ja | `git_tools.py` beschrijving + foutmelding bevatten nog "tdd"/"TDD" | ❌ |
| `grep projects.json in source` = 0 | 0 matches | Niet verifiëerd bij Stop/Go | ❌ Stop/Go niet uitgevoerd |

**Stop/Go Cycle 1:** ❌ Niet gehaald — `projects.json` nog aanwezig, `tdd`-literals resterend.

---

### Cycle 2 — StateRepository + BranchState + AtomicJsonWriter

**Doel:** State I/O uit PSE extraheren naar SRP-component.

| DoD Item | Verwacht | Werkelijk | Status |
|---|---|---|---|
| `BranchState` frozen Pydantic model | Ja | `model_config = ConfigDict(frozen=True)` | ✅ |
| `FileStateRepository.load/save` | Aanwezig | Aanwezig | ✅ |
| `InMemoryStateRepository` | Aanwezig | Aanwezig | ✅ |
| `AtomicJsonWriter` crash-safe | Aanwezig | Aanwezig, temp+rename | ✅ |
| PSE ontvangt `IStateRepository` via constructor | Ja | `state_repository: IStateRepository \| None = None` in PSE `__init__` | ✅ |
| `IStateReader` / `IStateRepository` in `core/interfaces/` | Aanwezig | Aanwezig | ✅ |
| PSE unit tests via `InMemoryStateRepository` | 0 filesystem-afhankelijkheden | Grotendeels zo; niet volledig geverifieerd | ⚠️ |
| Pyright strict op `core/interfaces/`, `state_repository.py`, PSE | 0 errors | Niet geverifieerd bij Stop/Go | ⚠️ |

**Stop/Go Cycle 2:** ⚠️ Waarschijnlijk gehaald maar Pyright strict niet expliciet aangetoond.

---

### Cycle 3 — phase_contracts.yaml + PhaseContractResolver

**Doel:** Config-laag: phase_contracts.yaml schema, CheckSpec, PhaseContractResolver.resolve().

| DoD Item | Verwacht | Werkelijk | Status |
|---|---|---|---|
| `PhaseContractResolver` klasse | Aanwezig | Aanwezig (KPI 6) | ✅ |
| `CheckSpec` Pydantic model | Aanwezig | Aanwezig | ✅ |
| `PhaseConfigContext` facade | Aanwezig | Aanwezig | ✅ |
| Loader Fail-Fast op `cycle_based=true` + lege `commit_type_map` | `ConfigError` bij startup | `@model_validator` aanwezig | ✅ |
| `phase_contracts.yaml` is generiek (workflow × fase) | `{issue_number}` interpolatie of generieke paden | **Hardcoded `docs/development/issue257/planning.md`** | ❌ |
| `PCR` heeft geen import van `StateRepository` of `pathlib.glob` | Ja | Te verifiëren | ⚠️ |
| Pyright strict op `PhaseContractResolver`, `CheckSpec`, `PhaseConfigContext` | 0 errors | Niet geverifieerd bij Stop/Go | ⚠️ |

**Kritieke bevinding:** De `phase_contracts.yaml` bevat issue-specifieke paden i.p.v. workflow-generieke contracten. Dit is een fundamenteel conceptmisverstaan van het design (zie RC-6). De config-laag werkt per toeval voor issue #257 maar is incorrect voor elke andere branch.

**Stop/Go Cycle 3:** ❌ Niet gehaald — `phase_contracts.yaml` is geen generiek config-laag.

---

### Cycle 4 — Tool layer integration + PSE.get_state() + legacy param drop

**Doel:** Tool layer als composition root; PSE.get_state() → BranchState; legacy `phase=` param weg.

| DoD Item | Verwacht | Werkelijk | Status |
|---|---|---|---|
| `PSE.get_state(branch)` retourneert `BranchState` | Ja | Aanwezig | ✅ |
| `PSE.get_current_phase()` als convenience wrapper | Aanwezig | Aanwezig | ✅ |
| `GitManager.commit_with_scope(commit_type)` explicit parameter | Ja | Aanwezig | ✅ |
| PCR gebruikt in tool layer voor commit-type resolutie | Ja | Aanwezig in `git_tools.py` | ✅ |
| Legacy `phase=` kwarg verwijderd uit `mcp_server/tools/` | 0 matches | Verwijderd per refactor-commits | ✅ |
| Geen `tdd`-literals in `git_tools.py` | 0 matches | **`"research\|planning\|design\|tdd\|..."` in `workflow_phase` description; `"TDD phase commits"` in foutmelding** | ❌ |
| `TransitionPhaseTool` integratietest met `PCR.resolve()` | Aanwezig | Gedeeltelijk (commit-type resolutie ✅; deliverable-check via PCR ❌) | ⚠️ |
| Pyright strict op tool files en PSE public API | 0 errors | Niet geverifieerd bij Stop/Go | ⚠️ |

**Stop/Go Cycle 4:** ⚠️ Gedeeltelijk — PSE↔PCR integratie voor deliverable-checks ontbreekt.

---

### Cycle 5 — enforcement.yaml + EnforcementRunner

**Doel:** Enforcement-laag live; state.json auto-gecommit op phase transition.

| DoD Item | Verwacht | Werkelijk | Status |
|---|---|---|---|
| `EnforcementRunner` klasse | Aanwezig | Aanwezig | ✅ |
| `EnforcementRegistry` klasse | Aanwezig | Aanwezig | ✅ |
| `BaseTool.enforcement_event` class variable | Aanwezig | `enforcement_event: str \| None = None` in `base.py` | ✅ |
| Loader `ConfigError` voor ongeregistreerd action type | Fail-Fast | `_validate_registered_actions()` aanwezig | ✅ |
| `check_branch_policy` pre-hook op `create_branch` | Aanwezig | In `enforcement.yaml` ✅ | ✅ |
| `commit_state_files` post-hook op `transition_phase` | Aanwezig | In `enforcement.yaml` ✅ | ✅ |
| `commit_state_files` post-hook op `transition_cycle` | Aanwezig | In `enforcement.yaml` ✅ | ✅ |
| `delete_file` handler geregistreerd in `_build_default_registry()` | Aanwezig | **Afwezig — alleen `check_branch_policy` + `commit_state_files` geregistreerd** | ❌ |
| Post-merge cleanup rule in `enforcement.yaml` | `event_source: merge` aanwezig | **Afwezig — geen merge-regel** | ❌ |
| `EnforcementRunner` unit tests 0 afhankelijkheid van `FileStateRepository`/PSE | Ja | Niet geverifieerd | ⚠️ |
| E2E test: `transition_phase` → `state.json` gecmmit | Aanwezig | Gedeeltelijk aanwezig | ⚠️ |

**Stop/Go Cycle 5:** ❌ Niet gehaald — `delete_file` handler ontbreekt + geen post-merge rule.

---

### Cycle 5.1 — transition_tools refactor

**Doel:** `cycle_tools.py` ter vervanging van `transition_tools.py`; DIP + DRY fixes; `enforcement_event`.

| DoD Item | Verwacht | Werkelijk | Status |
|---|---|---|---|
| `cycle_tools.py` aanwezig, `transition_tools.py` weg | Ja | ✅ | ✅ |
| Beide tools erven van `_BaseTransitionTool` | Ja | Erft van `_BaseTransitionTool` in `phase_tools.py` | ✅ |
| `workspace_root` als constructor parameter | Ja | Via base class `__init__(self, workspace_root)` | ✅ |
| `settings.server.workspace_root` afwezig in `execute()` | 0 matches | Niet in `cycle_tools.py` aangetroffen | ✅ |
| `_extract_issue_number()` afwezig; `GitConfig.extract_issue_number()` gebruikt | 0 matches | `GitConfig.from_file().extract_issue_number(branch)` aanwezig | ✅ |
| `TransitionCycleTool.enforcement_event == "transition_cycle"` | Aanwezig | Aanwezig | ✅ |
| `ForceCycleTransitionTool.enforcement_event == "transition_cycle"` | Aanwezig | Aanwezig | ✅ |
| `DeliverableCheckError` als `ToolResult` warning (niet raised) | Ja | Aanwezig in `ForceCycleTransitionTool` | ✅ |
| `cycle_tools.py` gebruikt **geen** directe dict-traversal van planning_deliverables | Nee | **Nog steeds direct `planning_deliverables.get("tdd_cycles", {})`** | ❌ |
| `cycle_tools.py` gebruikt **geen** directe `DeliverableChecker()`-instantiatie | Nee | **`checker = DeliverableChecker(workspace_root=...)` op regel ~249** | ❌ |
| `state_engine._save_state()` NIET aangeroepen van buitenaf | 0 calls | **`state_engine._save_state(branch, updated_state)` op regel ~129 — private method call** | ❌ |
| Geen "TDD" in user-facing strings | 0 matches | `"Transition to next TDD cycle"`, `"Transitioned to TDD Cycle N"` | ❌ |
| Pyright strict op `cycle_tools.py` | 0 errors | Niet geverifieerd | ⚠️ |

**Stop/Go Cycle 5.1:** ❌ Niet gehaald — directe dict-traversal, directe DeliverableChecker-instantiatie, private-method call vanuit buitenobject.

---

### Cycle 6/7 — deliverables.json + state.json git-tracked

**Doel:** deliverables.json tooling; state.json git-tracked; post-merge cleanup.

| DoD Item | Verwacht | Werkelijk | Status |
|---|---|---|---|
| `save_planning_deliverables` aanwezig | Ja | Aanwezig | ✅ |
| `update_planning_deliverables` completed-cycle guard | `ValidationError` bij completed cycle | **Guard ontbreekt** (Gap 1) | ❌ |
| Alle `deliverables.json` writes via `AtomicJsonWriter` | Ja | Gebruikt | ✅ |
| `state.json` weg uit `.gitignore` | Ja | Verwijderd (KPI 19) | ✅ |
| PSE startup guard bij uncommitted `state.json` changes | Explicit warning | Aanwezig | ✅ |
| Post-merge cleanup: `delete_file` verwijdert `state.json` + `deliverables.json` | In `enforcement.yaml` | **Afwezig** (Gap 2, KPI 18) | ❌ |
| `deliverables.json` in `.st3/registries/` | In `registries/` submap | **In `.st3/` root** | ❌ |
| `state.json` in `.st3/registries/` | In `registries/` submap | **In `.st3/` root** | ❌ |
| RED-commit voor Cycle 6 | Obligatoir | **Afwezig — geen C6_RED commit** | ❌ TDD-volgorde niet gevolgd |

**Stop/Go Cycle 6/7:** ❌ Niet gehaald.

---

## 4. KPI-matrix (volledige staat)

| # | KPI | Verwacht | Huidig | Status |
|---|-----|----------|--------|--------|
| 1 | `workflows.yaml` gebruikt `"implementation"` | Ja | Ja | ✅ |
| 2 | `.st3/` split: `config/` + `registries/` aanwezig | Beide submappen | `config/` ✅, `registries/` ❌ | ❌ |
| 3a | `phase_contracts.yaml` bestand bestaat | Ja | Ja | ✅ |
| 3b | PSE exit-hooks via `PhaseContractResolver` (code) | PCR gebruikt in PSE | Direct dict-traversal in alle `on_exit_*` methoden | ❌ |
| 4 | `deliverables.json` in `.st3/registries/` | Ja | In `.st3/` root | ❌ |
| 5 | `projects.json` verwijderd | Bestand weg | **Bestand bestaat nog** | ❌ |
| 6 | `PhaseContractResolver` klasse aanwezig | Ja | Aanwezig | ✅ |
| 7 | `StateRepository` klasse aanwezig | Ja | Aanwezig | ✅ |
| 8 | PSE OCP: exit-hook registry i.p.v. if-chain | 0 `if from_phase ==` checks | **6 `if from_phase ==` checks** in `transition()` | ❌ |
| 9 | `DeliverableChecker` max 1× geïnstantieerd | ≤ 1 instantiatie | **3× in PSE + 1× in cycle_tools = 4×** | ❌ |
| 10 | DRY `on_exit_*` methoden (één generieke) | ≤ 1 specifieke hook-methode | **5 separate `on_exit_*_phase` methoden** | ❌ |
| 11 | Geen f-string logging in PSE | 0 f-strings in `logger.*` calls | **Meerdere `logger.info(f"...")` aanwezig** | ❌ |
| 12 | Geen `"tdd"` literals in source + tests | 0 matches | `git_tools.py` beschrijving/fout, `cycle_tools.py` user strings, test-fixtures | ❌ |
| 13 | Geen `sub_phase` if-chain in `git_manager` | 0 if-chains | Geen if-chain | ✅ |
| 14 | `branch_name_pattern` enforceert issue-nummer prefix | Pattern valideert nummer | `"^[a-z0-9-]+$"` — geen issue-nummer vereiste | ❌ |
| 15 | `_extract_issue_from_branch` verwijderd uit PSE | Afwezig | Verwijderd | ✅ |
| 16 | `workflow_config.py` verwijderd | Bestand weg | Verwijderd | ✅ |
| 17 | Volledige testsuite groen | 0 failures | 2132 passed | ✅ |
| 18 | `enforcement.yaml` bevat post-merge cleanup rules | `event_source: merge` aanwezig + `delete_file` handler | **Geen merge-rule; geen `delete_file` handler** | ❌ |
| 19 | `state.json` git-tracked + startup guard | `.gitignore` clean; PSE waarschuwt | Beide aanwezig | ✅ |
| 20 | `AtomicJsonWriter` aanwezig en gebruikt | Ja | Aanwezig, gebruikt | ✅ |

**Score: 10 ✅ / 10 ❌**

---

## 5. Additionele bevindingen (buiten QA-handover)

### A-01 — `phase_contracts.yaml` bevat issue-specifieke paden in plaats van generieke contracten

**Locatie:** `.st3/config/phase_contracts.yaml`  
**Probleem:** De exit-gatefiles zijn hardcoded als `docs/development/issue257/planning.md`. Voor elke andere `feature`-branch faalt de gate verkeerd (te permissief of te strict op verkeerd bestand).  
**Vereiste:** Gebruik `{issue_number}` interpolatie (zoals beschreven in research F12) of generaliseer naar globs. Matcher moet dynamisch interpoleren bij gate-evaluatie.  
**Verificatie:** `.st3/config/phase_contracts.yaml` bevat 0 hardcoded `issue257` paden.

### A-02 — `cycle_tools.py` roept private methode `_save_state()` van buitenobject aan

**Locatie:** [cycle_tools.py ~regel 129](../../mcp_server/tools/cycle_tools.py)  
**Probleem:** `state_engine._save_state(branch, updated_state)` — private methode-aanroep omzeilt de `IStateRepository`-grens die in Cycle 2 bewust is opgezet.  
**Vereiste:** `state_engine._state_repository.save(updated_state)` of via een publieke wrapper.  
**Verificatie:** `Select-String "_save_state" mcp_server/tools/cycle_tools.py` → 0 matches.

### A-03 — `cycle_tools.py` user-facing strings bevatten nog "TDD"

**Locatie:** [cycle_tools.py](../../mcp_server/tools/cycle_tools.py) — description velden en ToolResult-teksten  
**Huidig:** `"Transition to next TDD cycle"`, `"Transitioned to TDD Cycle N/M"`  
**Vereiste:** Vervang door `"implementation cycle"` consistent met KPI 12.

### A-04 — Cycle 6 mist RED-commit — TDD-volgorde niet gevolgd

**Bewijs:** Geen `P_IMPLEMENTATION_SP_C6_RED` commit in git log.  
**Effect:** C6-deliverables zijn direct als C7 geïmplementeerd zonder RED-fase. Dit is een protocol-overtreding (planning.md schrijft RED → GREEN → REFACTOR voor per cycle).

---

## 6. Herstelplan (geordend)

De volgorde is kritisch. Verkeerde volgorde veroorzaakt dubbel werk.

### Stap 1 — Directory structuur (Gap 7 + Gap 8) — EERST

Doe dit vóór alle andere path-aanpassingen, anders moeten paden twee keer worden bijgewerkt.

1. Maak `.st3/registries/` aan
2. Verplaats `deliverables.json` → `.st3/registries/deliverables.json`
3. Verplaats `state.json` → `.st3/registries/state.json`
4. Update `ProjectManager.deliverables_file` → `.st3/registries/deliverables.json`
5. Update `FileStateRepository` pad → `.st3/registries/state.json`
6. Update alle hardcoded `".st3/state.json"` en `".st3/deliverables.json"` refs in source, tests, enforcement.yaml
7. Verwijder `.st3/projects.json` (Gap 8)
8. Update `enforcement.yaml` post-merge cleanup paths naar nieuwe `registries/`-paden (vereist Gap 2B fix)

**Verificatie:** `Test-Path .st3\registries\deliverables.json` → True; `Test-Path .st3\projects.json` → False

---

### Stap 2 — PSE structurele refactor (Gaps 3–6 + 12) — ÉÉN atomische commit

OCP + DIP + DRY + f-string logging en PSE→PCR-wiring zijn zo sterk verweven dat ze tegelijk moeten. Splits dit in twee sub-stappen:

**Stap 2A — Structurele PSE refactor (KPIs 8, 9, 10, 11):**

1. Voeg `_exit_hooks: dict[str, Callable]` registry toe in `__init__`; registreer alle huidige `on_exit_*` methoden
2. Vervang de 6 `if from_phase ==` checks in `transition()` door `_exit_hooks`-dispatch
3. Introduceer lazy-property `_checker: DeliverableChecker` (één instantiatie, DIP)
4. Consolideer `on_exit_design_phase`, `on_exit_validation_phase`, `on_exit_documentation_phase` → één generieke `_run_exit_gate(phase, branch, issue_number)` (DRY)
5. Vervang alle `logger.info(f"...")` door `logger.info("msg %s", var)` (f-string elimination)

**Verificatie:**
- `Select-String "if from_phase ==" mcp_server/managers/phase_state_engine.py` → 0 matches
- `Select-String "DeliverableChecker(" mcp_server/managers/phase_state_engine.py` → max 1 match
- `(Select-String "def on_exit_.*_phase" mcp_server/managers/phase_state_engine.py).Count` ≤ 1
- `Select-String 'logger\.\w+\(f"' mcp_server/managers/phase_state_engine.py` → 0 matches

**Stap 2B — PCR wiring (Gap 12, KPI 3b):**

1. Injecteer `PhaseContractResolver` in PSE constructor (naast `IStateRepository`)
2. Refactor `_run_exit_gate(phase, branch, issue_number)`: roep `PhaseContractResolver.resolve(workflow, phase, issue_number)` aan om `list[CheckSpec]` te verkrijgen; geef door aan `DeliverableChecker` (geen directe dict-traversal meer)
3. Verwijder alle directe `project_plan["tdd_cycles"]`, `project_plan["planning_deliverables"]` lookups uit PSE exit-hooks

**Verificatie:** `Select-String "planning_deliverables" mcp_server/managers/phase_state_engine.py` → 0 matches

---

### Stap 3 — `phase_contracts.yaml` generaliseren (A-01 + Cycle 3 conceptfix)

1. Vervang hardcoded `docs/development/issue257/planning.md` door sjabloon met `{issue_number}` interpolatie
2. Implementeer `{issue_number}` interpolatie in `PhaseContractResolver.resolve()` (of `PhaseConfigContext`)
3. Stel generieke contracten op voor alle `feature`-fases op basis van design F12

**Verificatie:** `.st3/config/phase_contracts.yaml` bevat 0 `issue257`-paden; test met `issue_number=99` interpoleer correct.

---

### Stap 4 — Enforcement post-merge (Gap 2, KPI 18)

**Stap 4A — `delete_file` handler registreren:**
1. Voeg toe in `EnforcementRunner._build_default_registry()`: `registry.register("delete_file", self._handle_delete_file)`
2. Implementeer `_handle_delete_file(action, context, workspace_root)`: verwijder `workspace_root / action.path` idempotent

**Stap 4B — Post-merge rule in `enforcement.yaml`:**
1. Voeg toe:
   ```yaml
   - rule_id: post_merge_cleanup
     event_source: merge
     timing: post
     actions:
       - type: delete_file
         path: .st3/registries/state.json
       - type: delete_file
         path: .st3/registries/deliverables.json
   ```

**Stap 4C — Test:**
- `test_post_merge_enforcement_deletes_state_and_deliverables`

**Verificatie:** KPI 18 volledig groen.

---

### Stap 5 — Completed-cycle guard (Gap 1, Cycle 7 B2)

1. Lees `state.json` via `FileStateRepository` aan begin van `update_planning_deliverables`
2. Bouw `frozenset` van completed cycle-nummers uit `state_data.cycle_history`
3. Raise `ValidationError` bij poging tot update van completed cycle

**Test:** `test_update_planning_deliverables_raises_for_completed_cycle`

---

### Stap 6 — `cycle_tools.py` technische schuld (A-02, A-03, C5.1 resterend)

1. Vervang `state_engine._save_state(branch, updated_state)` door `state_engine._state_repository.save(updated_state)` (A-02)
2. Vervang `"TDD cycle"` en `"TDD Cycle"` door `"implementation cycle"` in alle user-facing strings (A-03, KPI 12)

---

### Stap 7 — String literals + config (Gap 9, Gap 10, Gap 11)

1. **`git_tools.py`** — update `workflow_phase` parameter description: `"tdd"` → `"implementation"`;  foutmelding `"TDD phase commits"` → `"implementation phase commits"` (Gap 9)
2. **`tests/mcp_server/fixtures/workflow_fixtures.py`** — phaselijsten: `"tdd"` → `"implementation"` (Gap 10)
3. **`tests/mcp_server/unit/config/test_workflow_config.py`** — alle `"tdd"`-fixtures → `"implementation"` (Gap 10)
4. **`.st3/git.yaml`** — `branch_name_pattern: "^[a-z0-9-]+$"` → `"^[0-9]+-[a-z][a-z0-9-]*$"` + bijbehorende test (Gap 11)

**Verificatie:** `Select-String "\btdd\b" mcp_server/tools/git_tools.py` → 0 matches; `Select-String "\btdd\b" tests/mcp_server/fixtures/workflow_fixtures.py` → 0 matches

---

### Stap 8 — Pyright strict sweep

Na alle code-aanpassingen: run Pyright strict op alle gewijzigde modules. Minimaal:
- `mcp_server/managers/phase_state_engine.py`
- `mcp_server/managers/enforcement_runner.py`
- `mcp_server/managers/phase_contract_resolver.py`
- `mcp_server/tools/cycle_tools.py`
- `mcp_server/tools/git_tools.py`

---

### Stap 9 — KPI-validatie (research_config_first_pse.md KPIs 1–20)

Loop expliciet alle 20 KPIs af als geautomatiseerde grep/test-verificatie. Toon bewijs van elk groen KPI vóór PR aangemaakt wordt.

---

## 7. Risicomatrix herstelplan

| Stap | Risico | Mitigatie |
|---|---|---|
| Stap 1 (dir-structuur) | Veel path-updates; kans op gemiste referentie | Volledige grep-sweep vóór commit; run tests na elke sub-stap |
| Stap 2A (PSE structuur) | PSE-regressie in 2000+ regels tests | Kleine atomische commits per SOLID-fix; InMemoryStateRepository beschermt unit tests |
| Stap 2B (PCR wiring) | Gedragsverandering in exit-hooks | Aparte commit; volledige test-suite na deze stap verplicht |
| Stap 3 (phase_contracts generalisatie) | Interpolatie kan bestaande tests breken | Backward-compatible default; test met issue 257 + dummy issue |
| Stap 4 (enforcement) | `delete_file` op verkeerd pad verwijdert data | Idempotent implementatie; test na merge op dummy branch |
| Stap 7 (branch_name_pattern) | Bestaande branches voldoen niet aan nieuw pattern | Pattern geldt alleen voor nieuwe branches via `create_branch`; bestaande branches niet geblokkeerd |

---

## 8. Geraadpleegde bronnen

| Bestand | Rol |
|---|---|
| [docs/development/issue257/research_config_first_pse.md](research_config_first_pse.md) | KPIs 1–20, design findings F1–F15 |
| [docs/development/issue257/design.md](design.md) | Design decisions A–J, functiespecs |
| [docs/development/issue257/planning.md](planning.md) | Cycles 1–7, Stop/Go criteria, TDD tests |
| [docs/SESSIE_OVERDRACHT_20260313.md](../../SESSIE_OVERDRACHT_20260313.md) | QA-bevindingen, 12 gaps, aanbevelingen |
| [mcp_server/managers/phase_state_engine.py](../../../mcp_server/managers/phase_state_engine.py) | Huidig PSE—6 if-chains, 3× DeliverableChecker, f-strings |
| [mcp_server/managers/phase_contract_resolver.py](../../../mcp_server/managers/phase_contract_resolver.py) | PCR — aanwezig maar niet ingedraad in PSE |
| [mcp_server/managers/enforcement_runner.py](../../../mcp_server/managers/enforcement_runner.py) | EnforcementRunner — geen delete_file handler |
| [mcp_server/tools/cycle_tools.py](../../../mcp_server/tools/cycle_tools.py) | cycle_tools — private method call, TDD-strings, directe instantiatie |
| [mcp_server/tools/git_tools.py](../../../mcp_server/tools/git_tools.py) | git_tools — tdd-literals in descriptions |
| [.st3/config/phase_contracts.yaml](../../../.st3/config/phase_contracts.yaml) | Hardcoded issue257 paden — conceptueel incorrect |
| [.st3/config/enforcement.yaml](../../../.st3/config/enforcement.yaml) | Geen merge-rule, geen delete_file handler |
