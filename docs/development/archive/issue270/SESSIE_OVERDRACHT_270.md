# Sessie Overdracht — Issue #270
<!-- template=manual version=issue270 -->

## Branch
`refactor/270-remove-dead-config-fields`

## Status
**Alle quality gates groen. 2659 tests passing. Branch klaar voor PR naar epic/257.**

```
Gate 0: Ruff Format   ✅
Gate 1: Ruff Lint     ✅
Gate 2: Imports       ✅
Gate 3: Line Length   ✅
Gate 4: Types (mypy)  ✅
Gate 4b: Pyright      ✅
```

## Wat er gedaan is

### Doelstelling
Verwijderen van dode YAML-velden die nooit gelezen worden door de applicatie na de #257-migratie.

### Gewijzigde bestanden

**`.st3/config/workphases.yaml`**
- `exit_requires` verwijderd uit alle fase-definities (was gemigreerd naar `phase_contracts.yaml`)
- `entry_expects` verwijderd uit alle fase-definities (was gemigreerd naar `phase_contracts.yaml`)

**`.st3/config/policies.yaml`**
- `allowed_prefixes` verwijderd uit alle operatieregels (was superseded door `commit_types` in `git.yaml`)

**`tests/mcp_server/config/test_operation_policies.py`**
- Testregels die `exit_requires`/`entry_expects` verwachtten verwijderd (regels 50-51)
- `test_validate_commit_message_required` gefixed: verwachtte onterecht `allowed_prefixes`-melding

### Wat dit oplost
- Geen verwarring meer over welke config-bron authoratief is
- WorkphasesConfig-schema hoeft geen lege lijsten meer te accepteren
- PolicyEngine leest `allowed_prefixes` al niet meer → veld was dead code

## Follow-up issues

### Issue #273 — commit_prefix_map DRY-violation (child of #257)
`git.yaml:commit_prefix_map` dupliceert `phase_contracts.yaml:commit_type_map`.
PolicyEngine kan `valid_prefixes` deriveren uit `git.yaml:commit_types` (alle conventional types).
Methoden `get_prefix()` en `has_phase()` op `GitConfig` zijn dead code (never called).

### Issue #274 — Terminal-fase exit gates niet gevalideerd (child of #257)
De `documentation`-fase is de terminal fase in alle workflows. `WGR.enforce()` wordt alleen
aangeroepen via `transition_phase`, die voor de terminal fase nooit wordt gecalld.
Oplossing: `CreatePRTool` krijgt `enforcement_event = "create_pr"`, enforcement.yaml krijgt
een `check_terminal_phase_gates` pre-rule, en een closure in server.py roept `WGR.enforce()`
aan als de branch in de terminal fase zit.

## Architectuurnota
Beide follow-ups zijn architectureel onderdeel van de incomplete #257-migratie
(config-driven PSE refactor). Ze zijn bewust apart gehouden om scope-creep te voorkomen.
