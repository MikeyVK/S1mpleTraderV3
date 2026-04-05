# QA Overdracht — 5 april 2026

## Branch
`feature/257-reorder-workflow-phases`

## Issue
#257

## Aanleiding
QA-review van cycles 1–5 (Threshold B Minimal Refactor) heeft drie blokkerende bevindingen
opgeleverd. Dit document bevat de precieze instructies om deze op te lossen. Geen verdere
scope-uitbreiding.

---

## Overzicht bevindingen

| # | Ernst | Bestand | Kernprobleem |
|---|---|---|---|
| B1 | Blocker | `test_issue39_cross_machine.py` | 4 integratie tests roepen `get_state()` aan met de verwachting van auto-reconstructie, die door C3 expliciet verwijderd is |
| M1a | Middel | `phase_state_engine.py` | 5 dead-code methoden nooit meer aangeroepen na C2, bevatten fossiele phasenaam-dispatch |
| M1b/c | Middel | `phase_state_engine.py` | `"implementation"` hardgecodeerd in transitie-logica en cycle-scope validatie terwijl de `cycle_based` flag al beschikbaar is in `phase_contracts.yaml` |

---

## B1 — `test_issue39_cross_machine.py`: 4 tests bijwerken

### Oorzaak

C3 (C_STATE_RECOVERY) heeft `PhaseStateEngine.get_state()` expliciet een **pure query** gemaakt.
De C3 RED-tests documenteren dit contract precies:

- `test_get_state_does_not_reconstruct_or_save_on_load_failure` (L265 `test_phase_state_engine_c3_issue257.py`)
- `test_get_state_raises_when_repository_load_fails` (L290)

Het contract is: `get_state()` geeft een `FileNotFoundError` als de state file niet bestaat.
Reconstructie gebeurt **uitsluitend** via `_load_state_or_reconstruct()` op het transitie-pad.

De 4 falende tests in `test_issue39_cross_machine.py` gaan ervan uit dat `get_state()` nog
steeds auto-reconstruct na het verwijderen van `state.json`. Dat is het oude gedrag.

### Exacte fout

Alle 4 tests:
```
FileNotFoundError: [Errno 2] No such file or directory: '.../workspace/.st3/state.json'
```

### Wat te fixen

De vier tests testen elk een eigen scenario van cross-machine recovery. Na C3 is het
juiste entry point voor recovery **niet** `get_state()`, maar `transition()` of
`force_transition()` — die intern `_load_state_or_reconstruct()` aanroepen.

**Per test de vereiste wijziging:**

#### 1. `test_complete_cross_machine_flow`

Dit is de hoofdscenario-test. Na het verwijderen van `state.json` roept de test:
```python
recovered_state = state_engine.get_state("fix/42-cross-machine-test")
```
Dit moet worden:
- Roep een transitie aan die reconstructie triggert, bijv. via `transition()` of
  `force_transition()` met een geldige `to_phase`.
- Daarna pas `get_state()` aanroepen om de teruggeschreven state te lezen.

Alternatief als een transitie te complex is om te wiren in deze integratie-test:
- Verwijder de verwachting van live reconstructie via `get_state()`.
- Vervang door: assert dat `get_state()` een `FileNotFoundError` gooit wanneer `state.json`
  ontbreekt, en dat reconstructie werkt via een transitie-aanroep.

#### 2. `test_recovery_with_no_phase_commits`

Patroon gelijk aan test 1. Verwijdert `state.json`, roept dan `get_state()`.
Zelfde fix: recovery gaat via transitie, daarna `get_state()` voor de lees-assert.
Of: verifieer het nieuwe contract direct (zie alternatief boven).

#### 3. `test_recovery_respects_workflow_phases`

Patroon gelijk. `state.json` verwijderd, dan `get_state("docs/44-documentation")`.
Zelfde fix.

#### 4. `test_recovery_with_invalid_branch_name`

Dit is anders. De test verwacht:
```python
with pytest.raises(ValueError, match="Cannot extract issue number"):
    state_engine.get_state("invalid-branch-name")
```
Na C3 gooit `get_state()` nooit een `ValueError` — het leest alleen de repository.
Die `ValueError` komt uit `StateReconstructor` en is dus alleen bereikbaar via
`_load_state_or_reconstruct()` op het transitiepad.

Correcte fix: verander de assert naar het werkelijke nieuwe contract:
```python
with pytest.raises(FileNotFoundError):
    state_engine.get_state("invalid-branch-name")
```
En test de `ValueError("Cannot extract issue number")` apart op het transitiepad, als je
de invalid-branch guard wil dekken op integratie-niveau.

### Verificatie na fix

```
run_tests(path="tests/mcp_server/integration/test_issue39_cross_machine.py")
# → 4 passed
run_tests(scope="full")
# → 0 failed
```

---

## M1a — Dead code verwijderen uit `phase_state_engine.py`

### Welke methoden

De volgende 5 methoden zijn nooit meer aangeroepen na C2 (C_GATE_WIRING). Ze bevatten
de pre-C2 gate-dispatch logica die door `WorkflowGateRunner` is overgenomen.

| Methode | Regelnummer | Bevat |
|---|---|---|
| `_legacy_planning_exit_gate` | ~L657 | Leest `workphases.yaml`, instantieert `DeliverableChecker` direct |
| `on_exit_research_phase` | ~L716 | `get_exit_requires("research")`, instantieert `DeliverableChecker` |
| `on_exit_design_phase` | ~L760 | Instantieert `DeliverableChecker` direct |
| `on_exit_validation_phase` | ~L791 | Instantieert `DeliverableChecker` direct |
| `on_exit_documentation_phase` | ~L822 | Instantieert `DeliverableChecker` direct |

**Let op:** `on_exit_implementation_phase` (L853) is **niet** dead code. Die wordt nog
aangeroepen op L188 en L252. Niet verwijderen.

### Verificatie na verwijdering

Doe een grep om te bevestigen dat geen van de verwijderde namen nog aangeroepen wordt:
```
grep: on_exit_research_phase|on_exit_design_phase|on_exit_validation_phase|on_exit_documentation_phase|_legacy_planning_exit_gate
→ 0 matches in mcp_server/
```
Daarna:
```
run_quality_gates(scope="files", files=["mcp_server/managers/phase_state_engine.py"])
run_tests(path="tests/mcp_server/unit/managers/")
```

---

## M1b/c — `"implementation"` hardcoding vervangen door `cycle_based` config lookup

### Probleemstelling

`"implementation"` als string verschijnt op vier plaatsen in actieve logica:

**M1b — Transitie-hooks (L187, L205 in `transition()` en L251, L271 in `force_transition()`):**
```python
if from_phase == "implementation":
    self.on_exit_implementation_phase(branch)
...
if to_phase == "implementation":
    self.on_enter_implementation_phase(branch, issue_number)
```
Dit koppelt cycle-state-management hard aan één phasenaam.

**M1c — Cycle-scope validatie (L509 in `_validate_cycle_phase()`):**
```python
if current_phase != "implementation":
    raise ValueError(...)
```

### Beschikbare infra

`phase_contracts.yaml` heeft al:
```yaml
implementation:
  cycle_based: true
```
`PhaseContractPhase` (in `mcp_server/config/schemas/phase_contracts_config.py`) heeft al:
```python
cycle_based: bool = False
```
`PhaseContractResolver` is al geïnjecteerd in PSE via `WorkflowGateRunner`.

### Verwachte aanpak

De PSE heeft toegang tot `WorkflowGateRunner`, die `PhaseContractResolver` bevat.
Via de resolver is de `cycle_based` vlag op te vragen voor de huidige fase.

1. Voeg een query-methode toe (of gebruik de bestaande resolver direct) om te controleren
   of een gegeven fase `cycle_based == True` is voor een gegeven workflow.

2. Vervang in `transition()` en `force_transition()`:
   ```python
   # VOOR
   if from_phase == "implementation":
       self.on_exit_implementation_phase(branch)
   ```
   door een check op de `cycle_based` flag uit config.

3. Vervang in `_validate_cycle_phase()`:
   ```python
   # VOOR
   if current_phase != "implementation":
       raise ValueError(...)
   ```
   door een check of `current_phase` een `cycle_based` fase is voor de workflow van de branch.
   De foutmelding moet ook generiek worden — niet meer `"Not in implementation phase"`.

4. De gate runner aanroepen met `phase=state.current_phase` in plaats van
   `phase="implementation"` hardcoded (L304, L360) volgt vanzelf als de dispatch
   config-driven is.

### RED tests vereist voor M1b/c

Schrijf twee RED tests voordat je de productie-code aanpast:

```python
def test_cycle_transition_is_allowed_in_any_cycle_based_phase(...)
    # Arrange: maak een branch-state met current_phase = een fase die cycle_based=True heeft
    #          maar NIET "implementation" heet (bijv. naam "tdd" in een custom workflow)
    # Act: roep transition_cycle aan
    # Assert: slaagt zonder ValueError
    # Rationale: als er morgen een workflow komt met cycle_based op "tdd", moet dat werken

def test_cycle_transition_is_blocked_in_non_cycle_based_phase(...)
    # Arrange: maak een branch-state met current_phase = een fase met cycle_based=False
    # Act: roep transition_cycle aan
    # Assert: ValueError met boodschap die NIET "implementation" noemt
```

### Verificatie na fix

```
grep: "implementation" in phase_state_engine.py  →  alleen in docstrings en comments
run_tests(path="tests/mcp_server/unit/managers/")
run_quality_gates(scope="files", files=["mcp_server/managers/phase_state_engine.py"])
```

---

## Volgorde van uitvoering

1. **B1 eerst** — dit zijn gebroken tests, suite is rood.
2. **M1a daarna** — dead code cleanup, geen RED tests nodig.
3. **M1b/c als laatste** — vereist RED tests schrijven, dan pas productie-aanpassing.

Na elke stap: full suite groen controleren voor je doorgaat.

## Afsluiting

Na alle drie fixes:
```
run_tests(scope="full")       # → 0 failed
run_quality_gates(scope="branch")  # → overall_pass: true
```
Dan terug naar QA voor eindvonnis.
