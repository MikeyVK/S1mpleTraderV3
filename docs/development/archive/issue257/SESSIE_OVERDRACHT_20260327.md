<!-- docs\development\issue257\SESSIE_OVERDRACHT_20260327.md -->
<!-- template=planning version=130ac5ea created=2026-03-27T00:00Z updated=2026-03-27 -->
# Issue #257 Sessie Overdracht (2026-03-27)

**Status:** ONDERZOEK — geen implementatie gedaan  
**Version:** 1.0  
**Last Updated:** 2026-03-27

---

## Purpose

Vastleggen van onderzoeksbevindingen uit de sessie van 27 maart 2026.
Doel:
- verduidelijken wat de `deliverables_design_doc_v1.json` backup precies is;
- vaststellen wat de huidige staat van de PSE God Class is;
- vaststellen of `EnforcementRunner` en `PhaseContractResolver` ingedraad zijn als phase-transition dispatcher;
- de openstaande schuld expliciet formuleren als input voor de volgende implementatiesessie.

---

## Activiteiten deze sessie

1. Branch `feature/257-reorder-workflow-phases` gecheckt uit na fetch + pull.
2. Workspace opgeschoond (4 untracked orchestratie-runtime bestanden verwijderd).
3. `TIJDLIJN_ISSUE257.md` volledig gelezen en geïnterpreteerd.
4. `deliverables_design_doc_v1.json` geïdentificeerd en vergeleken met huidige `.st3/deliverables.json`.
5. PSE, EnforcementRunner en PhaseContractResolver geïnspecteerd in de broncode.

---

## Bevinding 1 — `deliverables_design_doc_v1.json` zijn de originele PSE-cycles

Het bestand `.st3/deliverables_design_doc_v1.json` bevat de **PSE Config-First Architecture cycles (v1.0)**:
6 cycles (C1-C7) die werden ontworpen in de periode 3-12 maart 2026 en geïmplementeerd tussen
12-13 maart.

Dit zijn **precies de cycles die leidden tot "green tests maar PSE unwired"** — de crisis
die resulteerde in 10/20 KPIs rood. Ze zijn volledig gearchiveerd en vervangen door de
huidige Config Layer SRP cycles in `.st3/deliverables.json`.

De v1-backup is **historisch artefact**, geen actief plan.

---

## Bevinding 2 — Huidige deliverables.json bevat 10 Config Layer SRP cycles

De huidige `.st3/deliverables.json` bevat de 10-cycle Config Layer SRP structuur (planning v3.0):

| Cyclus (deliverables.json nr) | Naam | Status |
|---|---|---|
| 1 | C_SETTINGS.1 | ✅ Gedaan |
| 2 | C_SETTINGS.2 | ✅ Gedaan |
| 3 | C_LOADER.1 | ✅ Gedaan |
| 4 | C_LOADER.2 | ✅ Gedaan |
| 5 | C_LOADER.3 | ✅ Gedaan |
| 6 | C_LOADER.4 | ✅ Gedaan |
| 7 | C_LOADER.5 | ✅ Gedaan |
| 8 | C_VALIDATOR | ✅ Gedaan |
| 9 | C_GITCONFIG | ✅ Gedaan |
| 10 | C_CLEANUP | ✅ Gedaan |

Branch is in `validation`-fase, 2670 tests groen, alle quality gates groen.

---

## Bevinding 3 — PSE is nog steeds een God Class (801 regels)

De PSE (`mcp_server/managers/phase_state_engine.py`) bevat 801 regels en heeft de volgende
methoden direct als instance-methoden:

```
initialize_branch()           # regel 102
transition()                  # regel 160
force_transition()            # regel 231
get_current_phase()           # regel 313
get_state()                   # regel 346
on_enter_implementation_phase()   # regel 568
on_exit_planning_phase()          # regel 590
on_exit_research_phase()          # regel 649
on_exit_design_phase()            # regel 693
on_exit_validation_phase()        # regel 724
on_exit_documentation_phase()     # regel 755
on_exit_implementation_phase()    # regel 786
```

De 7 `on_enter_*` / `on_exit_*` methoden zijn hardcoded phase-hooks direct in de PSE.
Dit is de God Class structuur die het originele design (Config-First PSE) wilde oplossen
via `EnforcementRunner` + `EnforcementRegistry` dispatch.

De PSE constructor ontvangt **geen** `EnforcementRunner` en **geen** `PhaseContractResolver`:

```python
def __init__(
    self,
    workspace_root: Path | str,
    project_manager: ProjectManager,
    git_config: GitConfig,
    workflow_config: WorkflowConfig,
    workphases_config: WorkphasesConfig,
    state_repository: IStateRepository | None = None,
    scope_decoder: ScopeDecoder | None = None,
) -> None:
```

---

## Bevinding 4 — EnforcementRunner en PhaseContractResolver bestaan maar zijn NIET ingedraad in PSE

Beide componenten zijn aanwezig in `mcp_server/managers/`:

**`EnforcementRunner`** (194 regels):
- `EnforcementContext` — event context dataclass
- `EnforcementRegistry` — handler registry
- `EnforcementRunner.run(event, timing, context)` — dispatcher
- `_handle_check_branch_policy()` — branch policy enforcement
- `_handle_commit_state_files()` — atomische state-commit handler

**`PhaseContractResolver`** (aanwezig):
- `PhaseConfigContext` — facade voor workphases + phase_contracts config
- `PhaseContractResolver.resolve()` — geeft `list[CheckSpec]` terug per fase

**Waar ze wél worden gebruikt (`server.py`):**

| Component | Gebruik in server.py |
|---|---|
| `PhaseContractResolver` | Als dependency van `build_commit_type_resolver()` → inject in `GitCommitTool` |
| `EnforcementRunner` | Als tool-enforcement dispatcher (regel 498: `enforcement_runner.run(event, timing, context)`) voor MCP tool-level enforcement |

**De kritieke gap:** `server.py` instantieert `PhaseStateEngine` **zonder** `enforcement_runner`
of `phase_contract_resolver`. Bij `transition()` en `force_transition()` worden de hardcoded
`on_exit_*` / `on_enter_*` methoden in PSE zelf aangeroepen, **niet** via `EnforcementRunner`.

---

## Bevinding 5 — Wat de scope-pivot van 14 maart bewust parkeerde

Uit de tijdlijn:

> "Op 14 maart werd de scope fundamenteel herzien. Uit de recovery research bleek dat de
> root cause dieper lag dan de PSE-implementatie: de gehele `mcp_server/config/`-laag miste
> een centrale ConfigLoader, ConfigValidator, en correcte SRP-scheiding. De PSE-herstelcycli
> werden verlaten ten gunste van een grondiger aanpak."

De PSE God Class refactoring is **bewust geparkeerd** bij de scope-pivot. Dit was een
weloverwogen beslissing op dat moment, maar de schuld staat nog open.

---

## Openstaande schuld

| Component | Probleem | Impact |
|---|---|---|
| `PhaseStateEngine` (801 regels) | God Class: 7 hardcoded `on_exit_*` / `on_enter_*` methoden direct in PSE | Hoog: elke nieuwe fase of regel vereist PSE-wijziging |
| `EnforcementRunner` → PSE | Runner is gebouwd maar niet als dispatcher voor phase-transitions ingedraad | Middel: run() werkt voor tool-enforcement, maar phase-hook dispatch via PSE hardcoding |
| `PhaseContractResolver` → PSE | Resolver is beschikbaar maar PSE roept hem niet aan bij transitions | Middel: contract-validatie bij phase exit/enter is dode code t.o.v. PSE |

---

## Aanbeveling voor volgende sessie

De openstaande PSE-refactoring vormt een duidelijk afgebakend vervolgissue.

**Scope voor een nieuw issue:**
1. PSE ontvangt `EnforcementRunner` via constructor (DI)
2. PSE `transition()` dispatcht naar `enforcement_runner.run()` in plaats van hardcoded `on_exit_*`
3. Hardcoded `on_exit_*` / `on_enter_*` methoden verwijderd uit PSE of vervangen door generieke dispatcher
4. Structural guards die verifiëren dat PSE geen hardcoded phase-namen meer bevat

**Alternatief:** branch #257 alsnog uitbreiden met extra cycles voor PSE-refactoring voordat een PR wordt aangemaakt.

---

## Huidige Branchstaat

| Aspect | Status |
|---|---|
| Branch | `feature/257-reorder-workflow-phases` |
| Fase | `validation` |
| Testresultaat | 2670 passed, 12 skipped, 2 xfailed |
| Quality gates | Alle 6 actief groen |
| Worktree | Clean |
| Openstaande blocker | PSE God Class niet gerefactord (buiten scope Config Layer SRP) |
