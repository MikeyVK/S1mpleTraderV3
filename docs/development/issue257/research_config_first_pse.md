<!-- docs\development\issue257\research_config_first_pse.md -->
<!-- template=research version=8b7bb3ab created=2026-03-11T13:44Z updated= -->
# Config-First PSE architecture: phase_deliverables.yaml, deliverables register, .st3 structural refactor, projects.json abolishment

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-11

---

## Purpose

Grondige architecturele refactoring van de PSE-infrastructuur zodat werkfase-deliverables volledig Config-First configureerbaar zijn per workflow, de .st3 map een heldere config/registry scheiding heeft, en de PSE geen hardcoded kennis meer bevat van phases, workflows of specifieke deliverables.

## Scope

**In Scope:**
phase_deliverables.yaml (nieuw), deliverables.json register (nieuw), .st3/config/ + .st3/registries/ mapstructuur, projects.json abolishment + state.json verrijking, PhaseDeliverableResolver (nieuw), PSE OCP registry + DIP + SRP + DRY + logging refactor, StateRepository (atomische write extraheren), branch_name_pattern enforcement in git.yaml + create_branch, branch_types SSOT unificatie, fasevolgorde research→design→planning→tdd in workflows.yaml

**Out of Scope:**
sections.yaml + phase_contracts + content_contract gate type (issue #258 / Epic #49), ArtifactManager template-integratie workflow-aware sectie rendering (issue #259 / Epic #73), TDD subphase mechanics, MCP tool signatures (geen wijzigingen)

---

## Problem Statement

The current PhaseStateEngine, ProjectManager en .st3 directory hebben een aantal fundamentele architecturele problemen: (1) .st3/ mixt configs (statisch, YAML) en registries (runtime, JSON) zonder scheiding; (2) deliverable-contracten per werkfase zijn niet configureerbaar per workflow — er is geen phase_deliverables.yaml; (3) projects.json is een groeiend register zonder cleanup dat DRY-schendingen introduceert t.o.v. state.json; (4) de PSE bevat hardcoded phase-namen, hardcoded if-chains (OCP-schending), directe DeliverableChecker-instantiaties (DIP-schending) en gedupliceerde hook bodies (DRY-schending); (5) branch-naam conventie (issue-nummer verplicht) wordt niet machine-afgedwongen door create_branch, wat Mode 2 reconstructie breekbaar maakt; (6) branch_types in git.yaml en PSE extractie-regex zijn twee aparte definities van dezelfde waarheid (DRY).

## Research Goals

- Scheiden van .st3/ in config/ (YAML, statisch, versioned) en registries/ (JSON, runtime)
- Ontwerpen van phase_deliverables.yaml als Config-First workflow×phase deliverable-contract
- Ontwerpen van deliverables.json als issue-specifiek additief register (Optie A: config is leidend, issue-specifiek is aanvullend)
- Afschaffen van projects.json: issue-metadata velden verhuizen naar state.json; Mode 2 leunt volledig op git + GitHub API
- Ontwerpen van PhaseDeliverableResolver (SRP): combineert config-laag + registry-laag tot check-spec lijst zonder zelf checks uit te voeren
- Refactoren van PSE naar volledig config-driven: OCP hook-registry, DIP DeliverableChecker injection, SRP extractie, geen hardcoded phase-namen
- Valideren en hardmaken van branch-naam conventie: issue-nummer afdwingen in create_branch via git.yaml branch_name_pattern
- Unificeren van branch_types definitie: git.yaml is SSOT, PSE extractie-regex leest uit config

---

## Background

Voortgekomen uit issue #257 (fasevolgorde wisselen), uitgegroeid via grondige SOLID/Config-First analyse in research-sessie 2026-03-11. De PSE is 869 regels met minimaal 5 verantwoordelijkheden (God Class). projects.json bevat 40+ entries zonder cleanup. DeliverableChecker wordt 4x direct geïnstantieerd. Exit-hooks zijn een if-chain (OCP). branch_name_pattern valideert geen issue-nummer. branch_types in git.yaml en PSE-regex zijn inconsistent.

---

## Findings

### F1 — Transition ordering is volledig config-driven *(overgenomen uit origineel #257)*

`WorkflowConfig.validate_transition()` gebruikt `phases.index()` — geen hardcoded fasenamen. Fasevolgorde wisselen (research → design → planning → tdd) is uitsluitend een config-wijziging in `workflows.yaml`. Geen code-aanpassing nodig voor de volgorde zelf.

### F2 — Exit-hooks worden gefired op phase-name, niet op positie *(overgenomen, uitgebreid)*

De huidige `if from_phase == "planning": ... if from_phase == "research": ...` if-chain in `transition()` overleeft een volgorde-wissel inhoudelijk, maar is structureel gesloten voor uitbreiding (zie F6). De geplande OCP-registry lost dit op: hooks worden geregistreerd op naam, niet op index. Fasevolgorde en hook-dispatch zijn daarna volledig ontkoppeld.

### F3 — `planning_deliverables` is een God-object in `projects.json` *(origineel finding 3, uitgebreid)*

`planning_deliverables` bevat conceptueel twee totaal verschillende dingen: (a) TDD-cycle breakdown — issue-specifiek, output van de planning-fase; (b) per-fase deliverable checklists (`design.deliverables`, `validation.deliverables`, `documentation.deliverables`) — dit zijn workflow-level contracten die ten onrechte als issue-specifieke planningsoutput worden opgeslagen. Na de refactoring: (a) blijft in `deliverables.json` als issue-specifiek TDD-register; (b) verdwijnt en wordt vervangen door `phase_deliverables.yaml` (config-laag).

### F4 — `research.md` exit-gate: `file_glob` is onvoldoende *(overgenomen, aangepast)*

Huidige gate controleert alleen bestandsaanwezigheid. Een `heading_present`-gate op `## Expected Results` creëert een semantische brug van research naar design. In het nieuwe model wordt deze gate geconfigureerd in `phase_deliverables.yaml[feature][research]`, niet hardcoded in `workphases.yaml`. Geldt unconditionally voor alle workflows met een research-fase (feature, bug, refactor, epic); hotfix en docs hebben geen research-fase.

### F5 — `design` exit-gate ontbreekt *(overgenomen, mechanism aangepast)*

Huidige `on_exit_design_phase()` leest `planning_deliverables.design.deliverables` — dit is de backwards-dependency die verdwijnt. Vervangen door een `file_glob`-gate op `docs/development/issue{issue_number}/design.md` in `phase_deliverables.yaml[feature][design]`. De gate is nu config-driven per workflow, niet hardcoded per hook-methode.

### F6 — OCP-schending: `transition()` if-chain *(overgenomen)*

De if-chain in `transition()` (`if from_phase == "planning": ... if from_phase == "research": ...`) is gesloten voor uitbreiding. Een nieuwe fase vereist een code-aanpassing in deze methode. Oplossing: `_exit_hooks: dict[str, Callable]` registry op class-niveau, gevuld bij initialisatie. Toevoegen van een fase-hook = één entry in de registry, geen methodaanpassing.

### F7 — SRP-schending: God Class `PhaseStateEngine` (869 regels) *(overgenomen)*

De PSE heeft minimaal 5 aaneengegroeide verantwoordelijkheden:
- (a) State persistentie — atomische JSON-write (`_save_state`, `__state.tmp` rename)
- (b) Transitie-validatie + hook-dispatch (`transition()`, `force_transition()`)
- (c) Exit/entry hook implementaties (~150 regels, 6+ methoden)
- (d) State-reconstructie vanuit git (Mode 2, `_reconstruct_branch_state`)
- (e) TDD-cycle lifecycle management (`on_enter_tdd_phase`, `on_exit_tdd_phase`, cycle-validaties)

Na refactoring wordt (a) extracted naar `StateRepository`; (c) gedelegeerd aan `PhaseDeliverableResolver` + `DeliverableChecker`; (d) behoudt zijn plek maar leunt niet meer op `projects.json`.

### F8 — DIP-schending: `DeliverableChecker` 4× direct geïnstantieerd *(overgenomen)*

`checker = DeliverableChecker(workspace_root=self.workspace_root)` komt voor in `on_exit_planning_phase()`, `on_exit_design_phase()`, `on_exit_validation_phase()`, en `on_exit_documentation_phase()`. Oplossing: `DeliverableChecker` als constructor-injectie op `PhaseStateEngine` (of via `PhaseDeliverableResolver`); instantiatie buiten de hook-methoden.

### F9 — DRY-schending: gedupliceerde hook-bodies *(overgenomen, mechanism aangepast)*

`on_exit_validation_phase()`, `on_exit_documentation_phase()`, en `on_exit_design_phase()` zijn structureel identiek: initialiseer checker, lees `planning_deliverables.<phase>.deliverables`, loop + check. Na de refactoring vervalt het directe lezen van `planning_deliverables` volledig; de drie methoden worden vervangen door één generieke `_run_exit_gate(phase_name)` die via de OCP-registry wordt aangeroepen en de check-specs ontvangt van `PhaseDeliverableResolver`.

### F10 — f-string logging door de gehele PSE *(overgenomen)*

`logger.info(f"...")` en `logger.warning(f"...")` worden overal gebruikt. Python logging best practices en de project CODE_STYLE vereisen `logger.info("msg %s", var)` voor lazy evaluation. Alle f-string logging in `phase_state_engine.py` en aangrenzende managers moet worden omgezet.

### F11 — `.st3/` mixt configs en registries zonder structurele scheiding *(nieuw)*

De `.st3/`-map bevat 14 bestanden van twee fundamenteel verschillende typen:
- **Configs** (statisch, YAML, versioned, workflow-wet): `workflows.yaml`, `workphases.yaml`, `artifacts.yaml`, `policies.yaml`, `labels.yaml`, `scopes.yaml`, `git.yaml`, `issues.yaml`, `milestones.yaml`, `contributors.yaml`, `quality.yaml`, `project_structure.yaml`, `scaffold_metadata.yaml`
- **Registries** (dynamisch, runtime, groeien): `state.json`, `projects.json`, `template_registry.json`, `temp/`

Dit mixing bemoeilijkt gesprekken ("is dit een config-beslissing of een runtime-feit?"), maakt tooling-onderscheid noodzakelijk voor elke consumer, en zorgt dat config-wijzigingen en registry-updates in dezelfde directory-context plaatsvinden. Oplossing: `.st3/config/` voor alle YAML-configs, `.st3/registries/` voor alle runtime-bestanden.

### F12 — `phase_deliverables.yaml` ontbreekt als Config-First contract *(nieuw)*

Er bestaat geen configureerbaar workflow×phase deliverable-contract. Gevolg: elke nieuwe fase-eis (bv. een verplicht `design.md`) vereist code-aanpassingen in `workphases.yaml` én in PSE-hook methoden. Dit schending van het Config-First principe: gedragswijzigingen horen alleen te vereisen dat config-bestanden worden aangepast, niet dat code wordt herschreven.

Het nieuwe `phase_deliverables.yaml` definieert per `workflow × phase` een lijst van verplichte check-specs:
```yaml
contracts:
  feature:
    research:
      - id: research_doc
        type: file_glob
        file: "docs/development/issue{issue_number}/*research*.md"
      - id: expected_results_heading
        type: heading_present
        file: "docs/development/issue{issue_number}/*research*.md"
        heading: "## Expected Results"
    design:
      - id: design_doc
        type: file_glob
        file: "docs/development/issue{issue_number}/design.md"
```
Workflow-specifieke en workflow-agnostische contracten zijn beide uitdrukbaar. Issue-specifieke deliverables (Optie A, additief) worden opgeslagen in `deliverables.json`.

### F13 — `projects.json` is een groeiend register met DRY-schendingen en geen cleanup *(nieuw)*

`projects.json` bevat op dit moment 40+ issues (18 t/m 257) zonder cleanup-mechanisme. Problemen:

1. **DRY**: `workflow_name` en `parent_branch` staan zowel in `projects.json` als in `state.json` (gedocumenteerd als *"cache for performance"* — geen formeel caching-contract). Bij divergentie is onduidelijk welke SSOT is.
2. **Groeiend zonder waarde**: afgesloten issues in `projects.json` worden nooit gelezen na afsluiting, maar groeien de file op.
3. **Dubbele verantwoordelijkheid**: bevat zowel workflow-metadata (statisch, hoort in state) als planning-deliverables (runtime, hoort in `deliverables.json`).

Oplossing: `projects.json` verdwijnt volledig. Workflow-metadata (`workflow_name`, `required_phases`, `execution_mode`, `skip_reason`, `issue_title`, `parent_branch`, `created_at`) verhuist naar `state.json`. Mode 2-reconstructie leunt op git-branchnaam + GitHub API (issue type label) + `workflows.yaml` config — geen lokaal historisch register nodig.

### F14 — `DeliverableChecker` voert onterecht config/registry-merges uit *(nieuw)*

Huidige exit-hooks (bv. `on_exit_planning_phase()`) doen zelf de lookup in `projects.json`, de merge van key-gates (workphases) met deliverable-specs (planning_deliverables), en geven het resultaat door aan de checker. De checker zelf is puur structural, maar de aanroeper voert de merge uit — dit is een SRP-schending op het niveau van de hook-methode.

Na refactoring is de verantwoordelijkheidsverdeling:
- **`PhaseDeliverableResolver`**: leest `phase_deliverables.yaml[workflow][phase]` (config-laag) + `deliverables.json[issue][phase]` (registry-laag), merged tot één lijst van check-specs. Doet geen filesystem-checks.
- **`DeliverableChecker`**: ontvangt uitsluitend check-specs, voert filesystem-checks uit. Heeft geen kennis van `projects.json`, `phase_deliverables.yaml` of `state.json`.
- **PSE exit-hook (generiek)**: vraagt resolver om specs, geeft door aan checker. Bevat geen lifecycle-logica van deliverables.

### F15 — `StateRepository` ontbreekt: atomisch schrijven is ingebed in PSE *(nieuw)*

`_save_state()` in `PhaseStateEngine` (atomisch via temp-file + rename, Windows-compatible) is een infrastructure-verantwoordelijkheid die niet thuishoort in een workflow-engine. Hetzelfde geldt voor `ProjectManager._save_project_plan()` en de identieke write-patronen. Oplossing: `StateRepository` class met atomische read/write, Python-typing, en een clean interface. PSE en ProjectManager worden consumers, geen writers.

### F16 — `branch_name_pattern` dwingt issue-nummer niet af; Mode 2 is breekbaar *(nieuw)*

Huidige `git.yaml`:
```yaml
branch_name_pattern: "^[a-z0-9-]+$"
```
Dit valideert alleen kebab-case van het name-gedeelte, niet de aanwezigheid van een issue-nummer. `create_branch(name="my-feature", branch_type="feature")` → `feature/my-feature` → Mode 2 `_extract_issue_from_branch()` gooit `ValueError`. De conventie is een stilzwijgende protocolverplichting, geen machine-afgedwongen contract.

Oplossing: `branch_name_pattern` aanpassen naar `"^[0-9]+-[a-z][a-z0-9-]*$"` (name-gedeelte begint verplicht met `N-`). `CreateBranchInput` of `GitManager.create_branch()` valideert hierop zodat branchnamen zonder issue-nummer worden geweigerd bij aanmaak.

### F17 — `branch_types` in `git.yaml` en PSE extractie-regex zijn inconsistent (DRY) *(nieuw)*

Twee definities van dezelfde waarheid:

| Locatie | Branch types |
|---|---|
| `git.yaml` branch_types | `feature`, `fix`, `refactor`, `docs`, `epic` |
| PSE `_extract_issue_from_branch()` regex | `feature`, `fix`, `bug`, `docs`, `refactor`, `hotfix`, `epic` |

`bug` en `hotfix` bestaan in de PSE-regex maar niet in `git.yaml`. `fix` bestaat in `git.yaml` maar niet consistent in alle PSE-regex varianten. Gevolg: branches van type `bug` of `hotfix` kunnen door Mode 2 worden herkend, maar niet worden aangemaakt via `create_branch`.

Oplossing: `git.yaml` is SSOT voor toegestane branch-types. PSE leest `GitConfig.branch_types` bij reconstructie; de hardcoded regex-alternation verdwijnt. `bug` en `hotfix` worden expliciet toegevoegd aan `git.yaml` als gewenste types, of verwijderd uit de PSE regex — afhankelijk van de workflow-definitie.

### F19 — Eén bestand, meerdere directe consumers: consumers-contract ontbreekt *(nieuw)*

Principe: per `.st3/`-bestand hoort één reader-class als enige directe consumer. Drie bestanden schenden dit:

**`workflows.yaml` — twee concurrerende reader-classes:**
- `mcp_server/config/workflows.py` → `WorkflowConfig` (module-level singleton `workflow_config`)
- `mcp_server/config/workflow_config.py` → óók `WorkflowConfig` (ander bestand, andere klasse)

`issue_tools.py` importeert uit `workflow_config.py`; `project_manager.py` en `phase_state_engine.py` importeren uit `workflows.py`. Twee klassen met dezelfde naam lezen hetzelfde config-bestand — harde DRY-schending en bron van onderhoudsdivergentie.

**`workphases.yaml` — vier directe consumers, drie verschillende redenen:**
- `PhaseStateEngine` (3 methoden): `WorkphasesConfig(workphases_path)` — exit-gate lezen
- `GitManager`: `ScopeEncoder(self._workphases_path)` — subphase-whitelist voor commit-validatie
- `ScopeDecoder`: leest subphases als phase-fallback

`WorkphasesConfig` is de bedoelde reader maar heeft geen singleton en wordt 3× inline geconstrueerd. `ScopeEncoder` en `ScopeDecoder` lezen voor een ander concern (subphase-validatie / phase-detectie) — dat is een verborgen koppeling.

**`state.json` — twee onafhankelijke lezers zonder contractuele interface:**
- `PhaseStateEngine._save_state()` / `get_state()` — primaire schrijver én lezer (via `StateRepository` na refactoring)
- `ScopeDecoder` — secundaire lezer: leest `current_phase` direct van schijf als commit-scope ontbreekt

`ScopeDecoder` bypast de `PhaseStateEngine` en heeft geen garantie dat het schema klopt. Na de `StateRepository`-extractie moet `ScopeDecoder` via die interface lezen, niet direct op het JSON-bestand.

**Oplossing (algemeen):** één reader-class per bestand, singleton-patroon consistent toegepast, en consumers die hetzelfde bestand om een ander concern lezen krijgen een gefacadeerde interface (of het bestand wordt gesplitst op concern).

### F18 — Issue-boundary: scope vs. opvolgers *(overgenomen, bijgewerkt)*

| Scope | Issue | Epic |
|---|---|---|
| `.st3/config/` + `.st3/registries/` structuur | **dit issue** | — |
| `phase_deliverables.yaml` + `PhaseDeliverableResolver` | **dit issue** | — |
| `deliverables.json` register + project-init aanpassing | **dit issue** | — |
| `projects.json` abolishment + `state.json` verrijking + `StateRepository` | **dit issue** | — |
| PSE OCP registry + DIP + SRP + DRY + logging refactor | **dit issue** | — |
| `branch_name_pattern` enforcement + `branch_types` SSOT | **dit issue** | — |
| Fasevolgorde research → design → planning → tdd | **dit issue** | — |
| `sections.yaml` + `phase_contracts` + `content_contract` gate type | **#258** | Epic #49 |
| `ArtifactManager` template-integratie + workflow-aware rendering | **#259** | Epic #73 |

### F20 — `tdd_plan` is een planning artifact, niet execution state — split ontbreekt *(nieuw)*

`planning_deliverables` in `projects.json` mixt twee fundamenteel verschillende dingen:

| Onderdeel | Aard | Na planning immutable? |
|---|---|---|
| `tdd_cycles.total`, `cycles[].exit_criteria`, `cycles[].deliverables` | Planning artifact — besloten bij planning exit | ✅ Ja |
| `current_tdd_cycle`, `last_tdd_cycle`, `tdd_cycle_history` | Execution state — bijgehouden tijdens TDD | ❌ Nee, mutabel |

De **planning artifact** hoort in `deliverables.json` onder een geneste `tdd_plan`-sleutel. De **execution state** (`current_cycle`, `cycle_history`) hoort in `state.json` — beheerd door `StateRepository`.

`PhaseDeliverableResolver` leest bij TDD-gate-check de cyclusnummering uit `deliverables.json` en de huidige positie uit `state.json` (via `StateRepository` interface), zodat hij de juiste cycle-slice kan selecteren zonder zelf state te schrijven.

De vraag of `tdd_plan` na `save_planning_deliverables` nog muteerbaar is (via een apart `update_tdd_plan` endpoint) is een expliciete ontwerpbeslissing: immutabel maakt de invariant sterk; muteerbaar heeft praktische waarde als cycles herontworpen moeten worden.

### F21 — `tdd` is een hardcoded werkwijze-aanname, niet een generieke implementatiefase *(nieuw)*

De huidige architectuur bakt de aanname `implementatie = TDD` op zes lagen in:

| Laag | Hardcoding |
|---|---|
| `workflows.yaml` | Fase heet letterlijk `tdd` |
| `workphases.yaml` | Subphases hardcoded `red / green / refactor` |
| `state.json` | Sleutels `current_tdd_cycle`, `last_tdd_cycle`, `tdd_cycle_history` |
| `PSE` | `on_enter_tdd_phase`, `on_exit_tdd_phase`, `_validate_cycle_number_range` |
| `git_manager.py` GM-1 | `if sub_phase == "red": commit_type = "test"` etc. |
| `ScopeEncoder / PSE` | TDD-labels `{"red", "green", "refactor"}` hardcoded |

Dit is fout voor drie van de vier primaire workflows:
- **feature** → TDD cycles (red/green/refactor) ✅
- **bug** → reproduce → fix → verify (geen cycle-structuur, andere subphases)
- **refactor** → strangler-fig iteraties, geen red/green semantiek
- **docs** → heeft überhaupt geen implementatie-fase in deze zin

**Correcte opzet:** de fase heet `implementation` in `workflows.yaml`. De *werkwijze* (subphases, cycle_based, commit_type_map) wordt per workflow geconfigureerd in `phase_deliverables.yaml`:

```yaml
contracts:
  feature:
    implementation:
      subphases: [red, green, refactor]
      cycle_based: true
      commit_type_map: { red: test, green: feat, refactor: refactor }

  bug:
    implementation:
      subphases: [reproduce, fix, verify]
      cycle_based: false
      commit_type_map: { reproduce: test, fix: fix, verify: test }

  refactor:
    implementation:
      subphases: [identify, extract, verify]
      cycle_based: true
      commit_type_map: { identify: chore, extract: refactor, verify: test }
```

Dit maakt ook **design cycles** mogelijk: als een workflow in de design-fase iteratieve verfijning vereist, kan `cycle_based: true` ook daar worden geconfigureerd. Dezelfde resolver-logica herbruikt voor elke fase.

`state.json` gebruikt dan generieke sleutels (`current_cycle`, `cycle_history`) in plaats van `current_tdd_cycle`. `ScopeEncoder` leest de geldige subphases en commit_type_map uit `phase_deliverables.yaml` i.p.v. hardcoded sets.

**Impact:** fase `tdd` wordt hernoemd naar `implementation` in `workflows.yaml`, `workphases.yaml`, en alle PSE hook-methoden. State-sleutels worden gemigreerd. `ScopeEncoder`, `GitManager.commit_with_scope()`, en PSE TDD-specifieke methoden worden vervangen door generieke varianten.

### F22 — `git_tools.py` bevat hardcodings geraakt door F21 en bredere SOLID-schendingen *(nieuw)*

Nu `git_tools.py` in scope is geraakt door F21 (fase-hernoem + `commit_type_map`), is het bestand breed gescand op SOLID, DRY, SRP en Config-First schendingen.

**Config-First / DRY (direct F21-gevolg):**
- `build_phase_guard()` bevat `if workflow_phase == "tdd"` als cycle-guard trigger. De vraag "is deze fase cycle-based?" is een config-vraag (`phase_deliverables.yaml::cycle_based`), geen hardcoded string-vergelijking.
- `build_phase_guard()` leest `data.get("current_tdd_cycle")` direct uit state.json. Na F20/F13 wijzigt deze sleutel naar `current_cycle`.
- `GitCommitTool.execute()` bevat `if effective_phase == "tdd"` als trigger voor cycle-nummer-verplichting. Na F21 is het resultaat altijd `False` — de beveiliging verdwijnt stil zonder fout.
- De legacy path `mapped_workflow_phase = "tdd"` in `execute()` breekt volledig na het fase-hernoemen.

**Nieuw ontwerpprobleem — `commit_type_map` beschikbaarheid (GT-5):**
Na F21 staat de `commit_type_map` (`red → test`, `green → feat`, etc.) per workflow in `phase_deliverables.yaml`. De huidige tool-laag resolveert `commit_type` niet zelf — dat doet de hardcoded if-chain in `git_manager.py`. Na het verwijderen van die if-chain heeft de tool-laag géén `workflow_name` beschikbaar om de juiste map op te zoeken. Wie resolveert de `commit_type_map` na de refactoring, en op welke laag? Zie open vraag J.

**SRP / DIP:**
- `GitCommitTool.execute()` heeft 5 aaneengegroeide verantwoordelijkheden: (a) auto-detectie `workflow_phase`, (b) cycle-enforcement, (c) phase-guard, (d) legacy-normalisatie, (e) commit-aanroep.
- `GitCommitTool`, `GitCheckoutTool`, en `GetParentBranchTool` instantiëren `ProjectManager` en `PhaseStateEngine` inline in `execute()` — geen injectie, testbaarheid geblokkeerd.
- `build_phase_guard()` leest `state.json` direct van schijf via `json.loads(state_file.read_text(...))`. Na `StateRepository`-extractie (F15) bypast dit de contractuele interface.

### F23 — `workflow_phase` parameter kan vereenvoudigd worden naar `phase` na verwijdering deprecated pad *(nieuw)*

De parameter `workflow_phase` in `GitCommitInput` en `commit_with_scope()` heette zo om te onderscheiden van de deprecated `phase`-parameter (die een TDD-subphase betekende: `red`, `green`, `refactor`). Zodra de deprecated `phase`-parameter volledig verwijderd is, bestaat de ambiguïteit niet meer.

**Beslissing (vastgesteld in research):** deprecated `phase`-parameter wordt volledig verwijderd (geen backward-compat mapping). `workflow_phase` wordt hernoemd naar `phase`. `sub_phase` blijft ongewijzigd. Resulterende API: `git_add_or_commit(phase="implementation", sub_phase="red", message="...")`.

**Impact:**
- `GitCommitInput`: veld `workflow_phase` → `phase`; veld `phase` (deprecated) verwijderd inclusief `validate_phase()` validator en `model_validator`
- `GitCommitTool.execute()`: alle `workflow_phase`-referenties → `phase`; legacy-pad volledig verwijderd
- `git_manager.commit_with_scope()`: parameter `workflow_phase` → `phase`
- `GitCommitTool.description`: `"test(P_TDD_SP_RED): message"` → `"test(P_IMPLEMENTATION_SP_RED): message"`
- Alle tests die `workflow_phase=` gebruiken worden bijgewerkt

### F24 — Backward compatibility: flag-day aanpak, geen migratiecode *(nieuw, beslissingen vastgesteld)*

De refactoring raakt vijf backward compatibility dimensies. Alle beslissingen zijn bewust genomen — geen migratiecode die later opgeruimd moet worden.

| # | Dimensie | Beslissing | Rationale |
|---|---|---|---|
| BC-1 | Historische `P_TDD_SP_*` scope strings in git-log | Accepteren — niet meer decodeerbaar via ScopeDecoder | Commits zijn historisch en niet actief; ScopeDecoder valt terug op state.json |
| BC-2 | `current_tdd_cycle` / `last_tdd_cycle` / `tdd_cycle_history` in bestaande `state.json` bestanden | Geen migratiecode; handmatige fix indien nodig | Geen actieve branches van betekenis; fix is triviaal |
| BC-3 | `.st3/` padlocaties (alle consumers) | Flag-day: alle paden tegelijk migreren naar `.st3/config/` en `.st3/registries/` | Geen fallback-loader; directorynaam configurabel maken is apart issue #260 |
| BC-4 | `projects.json` abolishment | Accepteren: bestaande `projects.json` entries vervallen; tests worden herschreven | Geen backward-compat leeslaag; cross-machine scenario wordt opnieuw gedefinieerd op `state.json + git` |
| BC-5 | Deprecated `phase`-parameter in `git_add_or_commit` | Volledig verwijderen (geen mapping naar `"implementation"`) | Parameter staat al als `DEPRECATED`; callers gebruiken al `workflow_phase` (wordt `phase`) |

**Teststrategie bij flag-day:**
- Tests die `projects.json`-structuren aanmaken worden volledig herschreven op `deliverables.json` + `state.json`
- Tests die `"tdd"` als fase gebruiken worden bijgewerkt naar `"implementation"`
- Tests die `P_TDD_SP_*` scope-strings asserteren worden bijgewerkt naar `P_IMPLEMENTATION_SP_*`
- Tests die `current_tdd_cycle` in state asserteren worden bijgewerkt naar `current_cycle`
- `test_issue39_cross_machine.py`: scenario volledig herschreven op `state.json + git` zonder `projects.json`
- `GitConfig.tdd_phases` en `GitConfig.tdd_phase_map` (DEPRECATED velden in `git_config.py`, GC-3) worden verwijderd

### F25 — `.st3` directorynaam is projectspecifiek, niet configureerbaar *(nieuw, gedefereerd naar #260)*

De naam `.st3` is hardcoded als string-literal door de gehele MCP server codebase en is ontstaan tijdens de ontwikkeling van SimpleTraderV3. Dit maakt de server niet distribueerbaar als zelfstandig pakket. Aanpak: configureerbaar via startup-config met fallback naar `.MyMCP`. **Gedefereerd naar issue #260** — blokkeert #257 niet. In #257 migreren we de interne structuur maar behouden we voorlopig de `.st3`-naam.

## Per-File Schendingsscan

Alle bestanden die geraakt worden door F1–F25 zijn hieronder per file gescand op SOLID, DRY, SRP en Config-First schendingen. Elke tabel toont: schending, principe, ernst (🔴 blokkerend / 🟠 significant / 🟡 minor), en de gekoppelde finding.

---

### `mcp_server/managers/phase_state_engine.py` (869 regels)

| # | Schending | Principe | Ernst | Finding |
|---|---|---|---|---|
| PSE-1 | 5 verantwoordelijkheden in één klasse: state-init, sequentieel transitie, geforceerde transitie, exit-gate orchestratie, TDD-cycle management | SRP | 🔴 | F7 |
| PSE-2 | `transition()` bevat een cascade van `if from_phase == "planning"`, `if from_phase == "research"`, etc. Elke nieuwe fase = code-wijziging | OCP | 🔴 | F6 |
| PSE-3 | `WorkphasesConfig(workphases_path)` wordt 3× inline geconstrueerd (force_transition ln ~231, on_exit_planning ln ~657, on_exit_research ln ~722). Geen singleton, geen injectie | DIP + DRY | 🔴 | F8 + F19 |
| PSE-4 | `DeliverableChecker(workspace_root=...)` wordt 4× geïnstantieerd (on_exit_planning, on_exit_design, on_exit_validation, on_exit_documentation). Geen injectie | DIP + DRY | 🔴 | F8 |
| PSE-5 | `on_exit_design_phase`, `on_exit_validation_phase`, `on_exit_documentation_phase` zijn nagenoeg identiek: lees `planning_deliverables.[phase].deliverables`, itereer, run checker. 3× gedupliceerde body | DRY | 🔴 | F9 |
| PSE-6 | `_extract_issue_from_branch()` bevat hardcoded regex `r"^(?:feature\|fix\|bug\|docs\|refactor\|hotfix\|epic)/(\d+)-"`. Branch-types zijn een duplicaat van `git.yaml:branch_types` | Config-First + DRY | 🔴 | F17 |
| PSE-7 | Exit-gate methoden per fase zijn hardcoded (`on_exit_planning`, `on_exit_research`, etc.). De koppeling fase-naam → hook-methode staat niet in config; toevoegen van een nieuwe fase vereist een nieuwe methode | Config-First + OCP | 🔴 | F2 + F6 |
| PSE-8 | 12 f-string log calls (bijv. `logger.info(f"Planning exit gate passed for branch {branch}...")`). Python logging vereist lazy `%s`-formaat om evaluatie bij uitgeschakeld log-niveau te vermijden | DRY | 🟡 | F10 |
| PSE-9 | `_reconstruct_branch_state()` leest `project.get("parent_branch")` uit `projects.json`. Na abolishment van `projects.json` moet dit via `state.json` of GitHub API komen | Config-First | 🟠 | F13 |
| PSE-10 | `_save_state()` bevat directe atomische schrijflogica (temp-file + rename). Deze verantwoordelijkheid behoort in `StateRepository` | SRP | 🟠 | F15 |
| PSE-11 | `on_exit_planning_phase()` verwerkt geneste `tdd_cycles.cycles[].deliverables[].validates` en `design/validation/documentation.deliverables[].validates` — PSE kent de interne structuur van `planning_deliverables`. Dit is een lekkende abstractie | SRP | 🟠 | F3 |

---

### `mcp_server/managers/project_manager.py`

| # | Schending | Principe | Ernst | Finding |
|---|---|---|---|---|
| PM-1 | `get_project_plan()` combineert drie concerns: JSON-lezen, live phase-detectie via `ScopeDecoder`, en `GitManager` instantiatie. Responsi­biliteiten zijn versnipperd in één methode | SRP | 🔴 | F7 |
| PM-2 | `GitManager()` en `ScopeDecoder()` worden inline geconstrueerd in `get_project_plan()`. Geen injectie; test­baarheid geblokkeerd | DIP | 🔴 | — |
| PM-3 | `_known_phase_keys: frozenset = frozenset({"tdd_cycles", "design", "validation", "documentation", "validates"})` — module-level hardcoded set. Moet komen uit `workphases.yaml` (of `phase_deliverables.yaml` post-refactor) | Config-First + DRY | 🔴 | F3 + F12 |
| PM-4 | `_phase_entry_keys = {"design", "validation", "documentation"}` in `save_planning_deliverables()` is opnieuw hardcoded. Overlapping met `_known_phase_keys` maar niet identiek — stille divergentie mogelijk | DRY + Config-First | 🟠 | F3 |
| PM-5 | `save_planning_deliverables()` bevat uitgebreide schema-validatielogica (cycle-nummering, lege arrays, exit_criteria) die niet thuishoort in een manager; scheiding van validatie en opslag ontbreekt | SRP | 🟠 | F3 |
| PM-6 | `update_planning_deliverables()` bevat identieke merge-logica voor `tdd_cycles.cycles` en voor fase-keys (`design`, `validation`, `documentation`). De merge-strategie is inline gedupliceerd | DRY | 🟠 | F9 |
| PM-7 | `_save_project_plan()` schrijft direct naar `projects.json`. Na abolishment wordt dit `StateRepository`; huidige directe I/O is niet geabstraheerd | SRP | 🟠 | F15 |
| PM-8 | `projects.json` groeit onbeperkt (40+ entries, nooit cleanup). Workflow-naam en parent_branch zijn zowel hier als in `state.json` opgeslagen — data-duplicatie | DRY | 🔴 | F13 |

---

### `mcp_server/managers/deliverable_checker.py`

| # | Schending | Principe | Ernst | Finding |
|---|---|---|---|---|
| DC-1 | Geen structurele schendingen. Klasse heeft één verantwoordelijkheid, OCP via dispatch-dict, geen hardcoded paths, geen externe afhankelijkheden. | — | ✅ Clean | — |
| DC-2 | (Aangrenzend): `on_exit_research_phase` in PSE roept NIET `checker.check()` aan voor `file_glob`-type maar doet de glob-check zelf inline via `workspace_root.glob()`. De `_check_file_glob` methode in `DeliverableChecker` gebruikt `spec['dir'] + spec['pattern']`, maar PSE bouwt anders. Interface-inconsistentie tussen caller en checker | Interface-DRY | 🟡 | F4 |

---

### `mcp_server/managers/git_manager.py`

| # | Schending | Principe | Ernst | Finding |
|---|---|---|---|---|
| GM-1 | `commit_with_scope()` bevat hardcoded TDD commit-type mapping: `if sub_phase == "red": commit_type = "test"`, `elif sub_phase == "green": commit_type = "feat"`, etc. Dit is een duplicaat van wat `workphases.yaml` per subphase zou moeten declareren | Config-First + DRY | 🔴 | F9 + F17 |
| GM-2 | `commit_with_scope()` laadt `workphases.yaml` direct inline via `open(self._workphases_path)` voor `commit_type_hint` lookup — tweede directe consumer van workphases.yaml buiten `WorkphasesConfig` | Config-First + DRY | 🔴 | F19 |
| GM-3 | `ScopeEncoder(self._workphases_path)` wordt twee keer inline geconstrueerd in `commit_with_scope()` (één keer voor fallback-validatie, één keer voor scope-generatie). Geen injectie | DIP + DRY | 🟠 | F8 |
| GM-4 | `create_branch()` valideert branch-naam tegen `branch_name_pattern` maar dat patroon vereist momenteel GEEN issue-nummer prefix — de afdwinging is incompleet | Config-First | 🔴 | F16 |
| GM-5 | `create_branch()` valideert branch-type via `GitConfig.branch_types` maar `branch_types` mist "bug" en "hotfix" die PSE's extractie-regex wél verwacht — PSE en GitManager zijn er niet over eens wat geldige types zijn | DRY + Config-First | 🔴 | F17 |

---

### `mcp_server/config/workflows.py`

| # | Schending | Principe | Ernst | Finding |
|---|---|---|---|---|
| WF-1 | Module-level singleton `workflow_config = WorkflowConfig.load()` laadt bij import. Gooit `FileNotFoundError` als `.st3/workflows.yaml` ontbreekt — ook buiten workspace context (bijv. unit tests zonder fixture) | DIP | 🟠 | — |
| WF-2 | Duplicate class: `WorkflowConfig` bestaat ook in `workflow_config.py` met een andere API. Twee klassen lezen hetzelfde bestand | DRY + SRP | 🔴 | F19 |
| WF-3 | `load()` gebruikt hardcoded default-pad `Path(".st3/workflows.yaml")` relatief aan CWD — pad is niet workspace-root-aware | Config-First | 🟡 | — |

---

### `mcp_server/config/workflow_config.py`

| # | Schending | Principe | Ernst | Finding |
|---|---|---|---|---|
| WFC-1 | Volledig dubbel bestand: `WorkflowConfig` klasse met andere interface (heeft `get_first_phase()`, `has_workflow()`) dan `workflows.py::WorkflowConfig` (heeft `get_workflow()`, `validate_transition()`). Beide lezen `.st3/workflows.yaml` | DRY + SRP | 🔴 | F19 |
| WFC-2 | `from_file()` gebruikt hardcoded string `".st3/workflows.yaml"` relatief aan CWD. Singleton `class_var` heeft geen thread-safety garantie bij parallel gebruik | DIP + Config-First | 🟡 | — |
| WFC-3 | Enige consumer is `issue_tools.py` voor `get_first_phase()`. Na consolidatie met `workflows.py` valt dit bestand weg | — | 🔴 (te verwijderen) | F19 |

---

### `mcp_server/config/workphases_config.py`

| # | Schending | Principe | Ernst | Finding |
|---|---|---|---|---|
| WPC-1 | Geen singleton: `WorkphasesConfig(path)` wordt bij elke instantiatie opnieuw van schijf gelezen. Drie callers in PSE + ScopeEncoder + ScopeDecoder → min. 5 disk-reads per operatie | DIP + DRY | 🟠 | F19 |
| WPC-2 | `ScopeDecoder` en `ScopeEncoder` lezen `workphases.yaml` rechtstreeks (niet via `WorkphasesConfig`) — de reader-class is niet de enige consumer. Werkelijke consumer-count is daarmee hoger dan de class zelf suggereert | DRY | 🟠 | F19 |
| WPC-3 | Geen schendingen op SRP: klasse heeft één verantwoordelijkheid. Typed accessors zijn clean. | — | ✅ structureel clean | — |

---

### `mcp_server/config/git_config.py`

| # | Schending | Principe | Ernst | Finding |
|---|---|---|---|---|
| GC-1 | `branch_name_pattern: default=r"^[a-z0-9-]+$"` dwingt geen issue-nummer prefix af. Mode 2 staat of valt met issue-extractability uit branchnaam | Config-First | 🔴 | F16 |
| GC-2 | `branch_types: default=["feature", "fix", "refactor", "docs", "epic"]` — ontbreekt "bug" en "hotfix". PSE regex en sommige tools verwachten deze types wél. Twee definities van dezelfde waarheid | DRY + Config-First | 🔴 | F17 |
| GC-3 | `tdd_phases`, `commit_prefix_map`, `get_prefix()`, `has_phase()`, `get_all_prefixes()` zijn allemaal `DEPRECATED` maar blijven bestaan. Dead code que divergeert stil van `workphases.yaml` definitie | DRY | 🟡 | F10 (indirect) |
| GC-4 | `from_file()` met hardcoded default `".st3/git.yaml"` — pad relatief aan CWD; niet workspace-root-aware | Config-First | 🟡 | — |

---

### `mcp_server/core/scope_encoder.py`

| # | Schending | Principe | Ernst | Finding |
|---|---|---|---|---|
| SE-1 | `ScopeEncoder.__init__(workphases_path: Path)` accepteert een pad en leest het bestand direct. Is daarmee een tweede directe consumer van `workphases.yaml` naast `WorkphasesConfig` | DIP + Config-First | 🔴 | F19 |
| SE-2 | Wordt 2× inline geconstrueerd in `git_manager.commit_with_scope()` (validatie-fallback + scope-generatie). Geen injectie vanuit GitManager | DIP | 🟠 | F8 |
| SE-3 | Geen structurele SRP-schendingen: encoder doet één ding. Lazy-load cache `_config` is correct geïmplementeerd | — | ✅ structureel clean | — |

---

### `mcp_server/core/phase_detection.py` (ScopeDecoder)

| # | Schending | Principe | Ernst | Finding |
|---|---|---|---|---|
| PD-1 | `_read_state_json()` leest `state.json` rechtstreeks van schijf — tweede directe consumer van `state.json` naast `PhaseStateEngine`. Bypast de toekomstige `StateRepository` interface | DIP + Config-First | 🔴 | F15 + F19 |
| PD-2 | `_load_valid_phases()` leest `workphases.yaml` opnieuw direct — derde consumer van `workphases.yaml` naast `WorkphasesConfig` en `ScopeEncoder` | DIP + DRY | 🔴 | F19 |
| PD-3 | `_unknown_fallback()` bevat hardcoded fase-lijst in error message: `"Valid phases: research, planning, design, tdd, integration, documentation, coordination"`. Divergeert stil van `workphases.yaml` | Config-First + DRY | 🟠 | F6 |
| PD-4 | Klasse heeft 3 verantwoordelijkheden: commit-scope parsen, state.json lezen, workphases valideren. Gescheiden interfaces zouden testbaarheid vergroten, maar cohesie is verdedigbaar als "detectie-unit" | SRP | 🟡 | — |

---

### `mcp_server/tools/git_tools.py`

| # | Schending | Principe | Ernst | Finding |
|---|---|---|---|---|
| GT-1 | `build_phase_guard()` bevat `if workflow_phase == "tdd"` als cycle-guard trigger. Na F21 is `"tdd"` niet meer geldig — de guard valt stil zonder fout. De vraag "is deze fase cycle-based?" is een config-vraag (`phase_deliverables.yaml::cycle_based`), geen hardcoded string-vergelijking | Config-First + DRY | 🔴 | F21 + F22 |
| GT-2 | `build_phase_guard()` leest `data.get("current_tdd_cycle")` hardcoded uit state.json. Na F20 wijzigt de sleutelnaam naar `current_cycle`. Tevens directe schijflezing die `StateRepository` bypast (F15) | DRY + DIP | 🔴 | F20 + F22 |
| GT-3 | `GitCommitTool.execute()` bevat `if effective_phase == "tdd"` als trigger voor cycle-nummer-verplichting. Na F21 altijd `False` — de invariant verdwijnt stil zonder testfalen of compileerfout | Config-First + DRY | 🔴 | F21 + F22 |
| GT-4 | Legacy path in `execute()`: `mapped_workflow_phase = "tdd"` breekt volledig na fase-hernoem. Geen compilatiefout, wel runtime-fout op de eerste legacy commit na de refactoring | DRY | 🔴 | F21 + F22 |
| GT-5 | `commit_type_map` beschikbaarheidsprobleem: tool-laag heeft géén `workflow_name` bij de commit-aanroep. Na verwijdering van de hardcoded if-chain in `git_manager.py` (GM-1) weet geen enkele laag meer welk type bij `red` hoort voor een bug-workflow vs. een feature-workflow. Expliciete ontwerpkeuze vereist. Zie open vraag J | Config-First + SRP | 🔴 | F21 + F22 |
| GT-6 | `GitCommitTool.execute()` heeft 5 aaneengegroeide verantwoordelijkheden: (a) auto-detectie `workflow_phase` uit state.json, (b) cycle-enforcer, (c) phase-guard aanroep, (d) legacy-normalisatie, (e) commit-aanroep via manager. Elke verantwoordelijkheid is apart testbaar als private helper | SRP | 🟠 | F22 |
| GT-7 | `GitCommitTool`, `GitCheckoutTool`, en `GetParentBranchTool` instantiëren `ProjectManager` en `PhaseStateEngine` inline in `execute()`. Koppeling aan concrete klassen blokkeert unit-testbaarheid | DIP | 🟠 | F22 |
| GT-8 | `build_phase_guard()` is een module-level functie die `state.json` direct leest via `json.loads(state_file.read_text(...))`. Na `StateRepository`-extractie (F15) bypast dit de contractuele interface — dezelfde schending als PD-1 | DIP | 🟠 | F15 + F22 |
| GT-9 | `GitCommitInput.workflow_phase` description bevat hardcoded fase-opsomming `"research\|planning\|design\|tdd\|..."`. Divergeert stil van `workphases.yaml` na fase-hernoem | Config-First + DRY | 🟡 | F22 |
| GT-10 | `GitCommitInput.validate_phase()` valideerde deprecated `GitConfig.tdd_phases`. Dit veld is al `DEPRECATED` in `git_config.py` (GC-3) maar wordt hier nog als validator gebruikt | DRY | 🟡 | F22 |

---

### Overzicht: Schendingen per principe

| Principe | Betrokken bestanden | Kritiek (🔴) | Significant (🟠) | Minor (🟡) |
|---|---|---|---|---|
| **SRP** | PSE, PM, GM, GT, PD | PSE-1, PM-1 | PSE-10, PSE-11, PM-5, PM-7, GT-6 | PD-4 |
| **OCP** | PSE | PSE-2, PSE-7 | — | — |
| **DIP** | PSE, PM, GM, WF, WFC, SE, GT, PD | PSE-3, PSE-4, PM-2, GM-3, WF-2, WFC-1, SE-1, PD-1 | WF-1, SE-2, GT-7, GT-8 | WFC-2, GC-4 |
| **DRY** | PSE, PM, GM, WF, WFC, WPC, GC, SE, GT, PD | PSE-3 (3×), PSE-6, GM-1, GM-2, WF-2, WFC-1, GC-2, PD-2, GT-2, GT-4 | PSE-5, PM-6, GM-3, WPC-1, WPC-2 | PSE-8, DC-2, GC-3, GT-10 |
| **Config-First** | PSE, PM, GM, WF, WFC, GC, SE, GT, PD | PSE-6, PSE-7, PM-3, GM-1, GM-4, GM-5, GC-1, GC-2, SE-1, PD-1, GT-1, GT-3, GT-5 | PSE-9, PM-4 | WF-3, WFC-2, GC-4, PD-3, GT-9 |

**Totaal kritieke schendingen (🔴): 27** *(+5 t.o.v. vorige versie)*  
**Totaal significante schendingen (🟠): 18** *(+4 t.o.v. vorige versie)*  
**Totaal minor schendingen (🟡): 10** *(+2 t.o.v. vorige versie)*

---

## Expected Results

> Meetbare uitkomsten die "done" definiëren voor dit issue. Gebruikt als input voor design (interfaces), planning (TDD-cycle indeling) en validatie (verificatiescripts).
>
> **Leeswijzer:** Elke KPI heeft een verificatiemethode die onafhankelijk van de gekozen implementatie geldig is. KPIs gemarkeerd met *[design-input]* kunnen pas volledig gespecificeerd worden na design, maar de uitkomst zelf is al vastgesteld.

---

### KPI 1 — Fasevolgorde correct in alle workflows

- `feature`-workflow: `design` verschijnt vóór `planning`, `planning` vóór `implementation` in de fasenlijst
- `bug`-workflow: zelfde volgorde
- `refactor`-workflow: geen `design`-fase; `planning` vóór `implementation`
- `epic`-workflow: zelfde als `feature`
- `hotfix`- en `docs`-workflow: ongewijzigd
- **Verificatie:** `grep -A15 "feature:" .st3/workflows.yaml` toont `design` voor `planning` voor `implementation`
- **Owner:** config-wijziging; geen design-input vereist

### KPI 2 — `.st3/` mapstructuur gesplitst in config/ en registries/

- `.st3/config/` bestaat en bevat alle YAML-configs (workflows.yaml, workphases.yaml, git.yaml, etc.)
- `.st3/registries/` bestaat en bevat alle runtime-bestanden (state.json, deliverables.json, template_registry.json)
- Geen YAML-configs meer in `.st3/` root; geen JSON-registers meer in `.st3/` root
- **Verificatie:** `Get-ChildItem .st3\ -File` retourneert 0 bestanden (alleen submappen)
- **Owner:** config-wijziging + consumer path-updates; geen design-input vereist

### KPI 3 — `phase_deliverables.yaml` bestaat en drijft fase-gates

- `.st3/config/phase_deliverables.yaml` bestaat
- Bevat minimaal de `feature`- en `bug`-workflows met `research`, `design`, en `implementation`-entries
- PSE exit-hooks lezen gate-specs uitsluitend uit dit bestand — geen hardcoded deliverable-logica meer in PSE-broncode
- **Verificatie:** `grep "planning_deliverables" mcp_server/managers/phase_state_engine.py` retourneert 0 matches
- **Owner:** *[design-input]* — schema-structuur bepaald in design (open vraag A1, A5)

### KPI 4 — `deliverables.json` register vervangt `planning_deliverables` in `projects.json`

- `.st3/registries/deliverables.json` bestaat na eerste `save_planning_deliverables` aanroep
- `tdd_plan` (cyclusindeling) opgeslagen onder `deliverables.json[issue_number]`
- `current_cycle` en `cycle_history` opgeslagen in `state.json`, niet in `deliverables.json`
- **Verificatie:** `save_planning_deliverables` schrijft naar `deliverables.json`; `state.json` bevat `current_cycle`
- **Owner:** *[design-input]* — JSON-schema bepaald in design (open vraag B1, B2)

### KPI 5 — `projects.json` afgeschaft

- `.st3/registries/projects.json` bestaat niet meer
- `workflow_name`, `parent_branch`, `required_phases` staan in `state.json`
- Mode 2-reconstructie (`_reconstruct_branch_state`) gebruikt git-branchnaam + `state.json` (geen `projects.json`)
- **Verificatie:** `Test-Path .st3\registries\projects.json` retourneert `False` na migratie
- **Owner:** *[design-input]* — migratiestrategie bepaald in design (open vraag C1, C4)

### KPI 6 — `PhaseDeliverableResolver` bestaat als geïsoleerde SRP-class

- Nieuwe class `PhaseDeliverableResolver` in `mcp_server/managers/`
- Invoer: `workflow_name`, `phase`, `issue_number` → uitvoer: `list[CheckSpec]`
- Doet geen filesystem-checks; combineert uitsluitend config-laag + registry-laag
- PSE exit-hooks aanroepen de resolver en delegeren checks aan `DeliverableChecker`
- **Verificatie:** `PhaseDeliverableResolver` heeft geen `import pathlib` of `glob`-aanroepen in zijn broncode
- **Owner:** *[design-input]* — interface exact bepaald in design (open vraag D1, D2)

### KPI 7 — `StateRepository` bestaat als geïsoleerde SRP-class

- Nieuwe class `StateRepository` in `mcp_server/managers/`
- Atomisch schrijven (temp-file + rename) geëxtraheerd uit PSE en ProjectManager
- PSE, ProjectManager, `ScopeDecoder`, en `build_phase_guard` in `git_tools.py` lezen/schrijven `state.json` uitsluitend via `StateRepository`
- **Verificatie:** `grep -r "state\.json" mcp_server/ --include="*.py" -l` toont alleen `state_repository.py` als directe opener
- **Owner:** *[design-input]* — interface (abstract/concreet, typed return) bepaald in design (open vraag E1, E2)

### KPI 8 — PSE OCP: geen if-chain op fasenamen in `transition()`

- `transition()` bevat geen `if from_phase ==` vergelijkingen
- Een `_exit_hooks: dict[str, Callable]` registry (of equivalent) mapt fasenamen op hook-callables
- Een nieuwe fase toevoegen vereist uitsluitend een entry in de registry, geen wijziging van `transition()`
- **Verificatie:** `grep "if from_phase" mcp_server/managers/phase_state_engine.py` retourneert 0 matches

### KPI 9 — PSE DIP: `DeliverableChecker` maximaal één keer geïnstantieerd per PSE-instantie

- `DeliverableChecker(workspace_root=...)` komt maximaal 1× voor in `phase_state_engine.py` (constructor-injectie of lazy property)
- **Verificatie:** `grep -c "DeliverableChecker(" mcp_server/managers/phase_state_engine.py` retourneert `≤ 1`

### KPI 10 — PSE DRY: geen gedupliceerde hook-bodies

- `on_exit_validation_phase`, `on_exit_documentation_phase`, `on_exit_design_phase` bestaan niet meer als drie aparte methoden met identieke structuur
- Vervangen door één generieke `_run_exit_gate(phase_name)` of equivalent dat via de OCP-registry wordt aangeroepen
- **Verificatie:** `grep -c "def on_exit_.*_phase" mcp_server/managers/phase_state_engine.py` retourneert `≤ 2`

### KPI 11 — f-string logging vervangen door parameterized logging in PSE

- Geen `logger.info(f"...")` of `logger.warning(f"...")` aanroepen in `phase_state_engine.py`
- **Verificatie:** `grep "logger\.\(info\|warning\|error\)(f\"" mcp_server/managers/phase_state_engine.py` retourneert 0 matches

### KPI 12 — Fase `tdd` hernoemd naar `implementation` door de gehele stack

- `.st3/config/workflows.yaml`: geen `tdd`-entry meer in fasenlijsten
- `.st3/config/workphases.yaml`: fase heet `implementation`, subphases per workflow in `phase_deliverables.yaml`
- `state.json`: sleutels `current_cycle`, `last_cycle`, `cycle_history` (geen `*_tdd_*`)
- `phase_state_engine.py`: geen `on_enter_tdd_phase`, `on_exit_tdd_phase`, `current_tdd_cycle`-referenties
- `git_tools.py`: geen `"tdd"` string-literals in `build_phase_guard` of `GitCommitTool.execute()`
- **Verificatie:** `grep -r '"tdd"' mcp_server/ --include="*.py"` retourneert 0 matches; `grep "tdd" .st3/config/workflows.yaml` retourneert 0 matches

### KPI 13 — `commit_type_map` config-driven via `phase_deliverables.yaml`

- `git_manager.py` bevat geen `if sub_phase == "red": commit_type = "test"` if-chain
- `commit_type` wordt bepaald door de config-laag op basis van `workflow_name` + `sub_phase`
- **Verificatie:** `grep "sub_phase == " mcp_server/managers/git_manager.py` retourneert 0 matches
- **Owner:** *[design-input]* — resolutie-laag (tool/manager/encoder) bepaald in design (open vraag J1)

### KPI 14 — `branch_name_pattern` dwingt issue-nummer af in `create_branch`

- `.st3/config/git.yaml`: `branch_name_pattern: "^[0-9]+-[a-z][a-z0-9-]*$"`
- `create_branch(name="my-feature", branch_type="feature")` gooit `ValidationError` zonder issue-nummer prefix
- `create_branch(name="257-config-first-pse", branch_type="feature")` slaagt
- **Verificatie:** unit test op `GitManager.create_branch` met naam zonder cijfer-prefix faalt met `ValidationError`

### KPI 15 — `branch_types` SSOT: PSE extractie-regex bouwt vanuit `GitConfig`

- `git.yaml` bevat `branch_types: [feature, fix, bug, hotfix, refactor, docs, epic]`
- `_extract_issue_from_branch()` in PSE bevat geen hardcoded alternation-regex met type-namen
- PSE bouwt de regex dynamisch vanuit `GitConfig.branch_types`
- **Verificatie:** `grep "feature.*fix.*bug" mcp_server/managers/phase_state_engine.py` retourneert 0 matches

### KPI 16 — `WorkflowConfig` geconsolideerd: één class, één bestand

- `mcp_server/config/workflow_config.py` bestaat niet meer
- `mcp_server/config/workflows.py` bevat één `WorkflowConfig` class met de gecombineerde API (`get_workflow`, `validate_transition`, `get_first_phase`, `has_workflow`)
- `issue_tools.py` importeert uit `workflows.py`, niet uit `workflow_config.py`
- **Verificatie:** `Test-Path mcp_server/config/workflow_config.py` retourneert `False`

### KPI 17 — Geen regressie: volledige testsuite slaagt

- Alle bestaande tests slagen na de refactoring
- Tests die `"tdd"` als literal bevatten zijn bijgewerkt naar `"implementation"` of worden verwijderd als ze backward-compat dekten
- Quality gates (ruff, mypy, pylint) slagen op branch-scope
- **Verificatie:** `run_tests(path="tests/")` retourneert 0 failures, 0 errors

---

### Handover-matrix richting design en planning

| KPI | Owner fase | Design-input vereist? | Planning-input |
|---|---|---|---|
| KPI 1 (fasevolgorde) | config-wijziging | Nee | Cycle: workflows.yaml aanpassen |
| KPI 2 (.st3 structuur) | config + consumer-updates | Nee | Cycle: pad-migratie per consumer |
| KPI 3 (phase_deliverables.yaml) | design → planning | Schema (A1, A5) | Cycle: YAML schrijven + PSE koppelen |
| KPI 4 (deliverables.json) | design → planning | Schema (B1, B2) | Cycle: PM refactor |
| KPI 5 (projects.json abolishment) | design → planning | Migratiestrategie (C1, C4) | Cycle: state.json verrijking |
| KPI 6 (PhaseDeliverableResolver) | design → planning | Interface (D1, D2) | Cycle: class implementeren + tests |
| KPI 7 (StateRepository) | design → planning | Interface (E1, E2) | Cycle: class implementeren + consumers migreren |
| KPI 8 (OCP registry) | planning | Nee | Cycle: PSE refactor |
| KPI 9 (DIP checker) | planning | Nee | Cycle: PSE refactor |
| KPI 10 (DRY hooks) | planning | Nee | Cycle: PSE refactor |
| KPI 11 (f-string logging) | planning | Nee | Cycle: PSE refactor (samen met KPI 8–10) |
| KPI 12 (tdd → implementation) | design → planning | State-migratie (H1), legacy-pad (J3) | Cycle: rename door gehele stack |
| KPI 13 (commit_type_map) | design → planning | Resolutie-laag (J1, J2) | Cycle: git_manager + git_tools refactor |
| KPI 14 (branch_name_pattern) | planning | Nee | Cycle: git.yaml + GitManager validatie |
| KPI 15 (branch_types SSOT) | planning | Nee | Cycle: samen met KPI 14 |
| KPI 16 (WorkflowConfig consolidatie) | planning | Nee | Cycle: consolidatie + consumers updaten |
| KPI 17 (geen regressie) | planning → tdd/implementation | Nee | Laatste cycle: regressiecheck |

---

## Open Questions

Kritische vragen die voor of tijdens de design-fase beantwoord moeten zijn, gegroepeerd per domein. Onbeantwoorde vragen vertalen direct naar risico's in de implementatie.

---

### A — `phase_deliverables.yaml` schema (F1, F2, F6, F12, F21)

**A1.** Wat is de minimale set verplichte sleutels per fase-entry? Zijn `subphases`, `commit_type_map` en `cycle_based` altijd aanwezig, of optioneel? Hoe valideert de loader ontbrekende velden?

> **✅ Beslissing (11-03-2026):** Optioneel met defaults: `subphases: []`, `commit_type_map: {}`, `cycle_based: false`. De loader vult ontbrekende velden aan met deze defaults zonder error.

**A2.** Hoe worden meervoudige check-types per deliverable gemodelleerd? (`file_exists` + `contains_text` op hetzelfde bestand — één `validates`-spec of geneste lijst?)

**A3.** Is `cycle_based` een boolean, of een object dat ook `max_cycles` en `cycle_deliverable_schema` bevat? Als max open is, mist de resolver een rangecheck.

> **✅ Beslissing (11-03-2026):** `cycle_based` is een boolean. `max_cycles` is een planning-artefact dat in `deliverables.json` opgeslagen wordt, niet in config. Geen rangecheck op config-niveau.

**A4.** Hoe wordt `commit_type_map` geladen door `ScopeEncoder`? Laadt `ScopeEncoder` zelf `phase_deliverables.yaml`, of krijgt hij de map geïnjecteerd? (DIP-risico als hij zelf laadt)

**A5.** De huidige `workphases.yaml` heeft `exit_requires` per fase. Wordt dat bestand samengevoegd met `phase_deliverables.yaml`, of blijven ze bestaan als twee afzonderlijke verantwoordelijkheden? (Overlap-risico: twee configs die hetzelfde beschrijven)

> **✅ Beslissing (11-03-2026):** Twee bestanden, twee verantwoordelijkheden. `workphases.yaml` = puur fase-metadata (display_name, description, subphases whitelist). `phase_contracts.yaml` (hernoemd van `phase_deliverables.yaml`) = workflow×fase contracten (exit_requires, commit_type_map, cycle_based per workflow per fase). Geen overlap.

**A6.** Hoe worden issue-specifieke additieve deliverables (`deliverables.json`) samengevoegd met de config-laag? Volgorde: config eerst, issue-additief daarna — maar wat als een issue-additief een config-entry wil *overschrijven*? Is dat toegestaan?

> **✅ Beslissing (11-03-2026):** Issue-specifiek mag config overschrijven. `PhaseContractResolver` merge-volgorde: config = default, `deliverables.json` = override. Additieve én overschrijvende overrides toegestaan.

---

### B — `deliverables.json` schema en lifecycle (F12, F13, F20)

**B1.** Wat is de exacte JSON-structuur? Per issue: `{ "257": { "phases": { "design": [...], "implementation": { "tdd_plan": {...} } } } }` of platter? Keuze beïnvloedt de `PhaseDeliverableResolver` lookup-logica direct.

> **✅ Beslissing (12-03-2026):** Genest: `{ "257": { "phases": { "design": [...], "implementation": {...} }, "created_at": "...", "workflow_name": "feature" } }`. Geneste structuur biedt ruimte voor issue-level metadata naast fase-entries, wat flat niet biedt zonder pollutie.

**B2.** Is `tdd_plan` na `save_planning_deliverables` immutable of muteerbaar via een apart `update_tdd_plan` endpoint? Als immutable: hoe gaan we om met het praktische geval dat een team halverwege TDD een extra cycle wil toevoegen?

> **✅ Beslissing (12-03-2026):** Mutable. `save_planning_deliverables` maakt aan, `update_planning_deliverables` wijzigt. Praktische noodzaak: extra cycle toevoegen halverwege implementatie moet mogelijk zijn.

**B3.** Wie schrijft naar `deliverables.json`? Alleen `save_planning_deliverables` en `update_planning_deliverables`? Of ook andere tools? De schrijver moet eenduidig zijn (1-writer principe analoog aan 1-reader).

> **✅ Beslissing (12-03-2026):** 1-writer principe: alleen `save_planning_deliverables` en `update_planning_deliverables`. Schrijven en wijzigen zijn gescheiden (SRP). Gedeelde private `AtomicJsonWriter` utility voor alle JSON-writes (inclusief `state.json`), zodat atomisch schrijven op één plek geïmplementeerd is.

**B4.** Wat is de lifecycle van een `deliverables.json` entry? Wordt hij gearchiveerd bij PR-merge, of simpelweg leeg gelaten? Wat gebeurt er als een issue opnieuw wordt geopend?

> **✅ Beslissing (12-03-2026):** Optie C — verwijderen bij PR merge. Config over code: cleanup is een `post_merge` lifecycle hook in `lifecycle.yaml`, niet hardcoded in Python. Git-history is de ultimate source of truth na merge. Cleanup-logica is een nieuwe deliverable van dit issue.

**B5.** Cycle-state (`current_cycle`, `cycle_history`) gaat naar `state.json`. Maar `state.json` bevat nu één issue tegelijk (single-branch). Als een ontwikkelaar van branch wisselt, gaat de cycle-state verloren. Moet cycle-state per issue opgeslagen worden (in `deliverables.json` of apart), of is het altijd gekoppeld aan de actieve branch?

> **✅ Beslissing (12-03-2026):** Probleem vervalt als `state.json` git-tracked is per branch. Nieuwe deliverable van dit issue: `state.json` verwijderen uit `.gitignore` zodat het per branch in git wordt bijgehouden. Bij branch-wissel is `state.json` van die branch beschikbaar via git checkout.

---

### C — `projects.json` abolishment en `state.json` verrijking (F13, F15, F20)

**C1.** Welke velden van `projects.json` gaan naar `state.json`, en welke worden bij Mode 2 opgebouwd uit git + GitHub API? Kandidaten: `issue_title` (GitHub API), `workflow_name` (branch-prefix → git.yaml lookup), `parent_branch` (git log). Is er een veld dat niet reconstructeerbaar is?

**C2.** `state.json` bevat nu één branch tegelijk. Bij abolishment van `projects.json` is er géén andere bron meer voor issues die niet de actieve branch zijn. Is dat acceptabel, of moet `state.json` een multi-branch register worden?

> **✅ Beslissing (12-03-2026):** Single-branch blijft. GitHub issues + lokale git branches zijn single source of truth. `projects.json` als multi-branch register wordt geabolished.

**C3.** `Mode 2 reconstructie` in PSE `_reconstruct_branch_state()` leest nu uit `projects.json`. Na abolishment leest hij uit git + GitHub API. Wat is de fallback als GitHub API onbereikbaar is (offline scenario)? Faalt hard, of graceful degradation naar `unknown`?

> **✅ Beslissing (12-03-2026):** Graceful degradation: `workflow_name: "unknown"` als GitHub API onbereikbaar is. Offline scenario niet prioriteit (MCP is een tool voor agentic coding, geen lokale LLM).

**C4.** Wat wordt de migratiepad voor bestaande 40+ entries in `projects.json`? One-time migration script, of backward-compat leeslaag tijdens transitieperiode?

> **✅ Beslissing (12-03-2026):** Flag-day. `projects.json` wordt verwijderd. Bestaande entries worden niet gemigreerd — niet meer relevant na abolishment. Consistent met BC-aanpak.

---

### D — `PhaseDeliverableResolver` interface (F3, F6, F12, F14, F20, F21)

**D1.** Exacte signatuur: `resolve(workflow_name: str, phase: str, issue_number: int, cycle_number: int | None) -> list[CheckSpec]`? Of wordt `cycle_number` impliciet uit `state.json` gelezen via `StateRepository`?

> **✅ Beslissing (11-03-2026):** DIP — `cycle_number` als expliciete parameter (zelfde patroon als J1). Signatuur: `resolve(workflow_name: str, phase: str, cycle_number: int | None) -> list[CheckSpec]`. Tool-laag leest `cycle_number` uit `StateRepository` en geeft het expliciet door. `PhaseContractResolver` heeft geen dependency op `StateRepository`.

**D2.** Wat is `CheckSpec`? Een TypedDict, dataclass, of Pydantic model? Welke velden zijn verplicht, welke optioneel? Dit bepaalt de interface met `DeliverableChecker`.

> **✅ Beslissing (12-03-2026):** Pydantic model. Pydantic zit al in de stack (`pydantic>=2.5.0`). Geeft runtime-validatie bij laden van `phase_contracts.yaml`-entries en type-safe interface met `DeliverableChecker`.

**D3.** Mag een fase géén deliverables hebben (lege lijst teruggeven)? Of is een lege resolver-output een configuratiefout die een warning/error verdient?

> **✅ Beslissing (12-03-2026):** Lege lijst is normaal en geen fout. Voorbeeld: `docs`-workflow heeft geen `implementation`-fase in `phase_contracts.yaml` — resolver geeft `[]` terug zonder error.

**D4.** Foutafhandeling: als `phase_deliverables.yaml` een fase niet definieert voor de gevraagde workflow, gooit de resolver een `ValueError` of een `ConfigurationError`? Wie vangt dat op — PSE of de caller van PSE?

> **✅ Beslissing (12-03-2026):** `ConfigError` met `file_path=".st3/config/phase_contracts.yaml"`. `ConfigError` is subklasse van `MCPError` en wordt gevangen door `@tool_error_handler` op de tool-laag, die het converteert naar `ToolResult.error()`. Geen try/except nodig in PSE of manager.

**D5.** Heeft `PhaseDeliverableResolver` kennis van de huidige cycle (via `StateRepository`), of krijgt de caller altijd een cycle-nummer mee? Als de resolver state leest, is hij geen pure functie meer — trade-off testbaarheid vs. API-eenvoud.

> **✅ Beslissing (12-03-2026):** Zie D1 — expliciet via parameter. `PhaseContractResolver` heeft geen dependency op `StateRepository`.

---

### E — `StateRepository` interface (F15, F20)

**E1.** Moet `StateRepository` een abstracte base class zijn (voor testability/mocking), of een concrete klasse die direct geïnjecteerd wordt?

> **✅ Beslissing (11-03-2026):** ABC (`abc.ABC` + `@abstractmethod`). Productie: `FileStateRepository(StateRepository)`. Tests: `InMemoryStateRepository(StateRepository)`. Injectie via constructor. Python gooit `TypeError` bij instantiatie van subklasse die niet alle abstracte methoden implementeert — dat is de vangst.

**E2.** Levert `StateRepository.read_state()` een getypte dataclass terug (`BranchState`) of een plain `dict`? Typed is beter voor Pyright strict, maar vereist migratie-aandacht bij schema-uitbreidingen.

> **✅ Beslissing (12-03-2026):** Getypte Pydantic model `BranchState`. Consistent met D2 (CheckSpec is ook Pydantic). Pyright strict-compatibel, runtime-validatie bij lezen van `state.json`.

**E3.** Atomic write is nu geïmplementeerd als temp-file + rename in PSE. Verhuist die logica 1-op-1 naar `StateRepository`, of is er een betere primitieve voor Windows (bijv. `filelock` library)?

> **✅ Beslissing (12-03-2026):** Temp-file + rename verhuist naar gedeelde `AtomicJsonWriter` utility (zie B3). Geen nieuwe dependency op `filelock`. Bestaande aanpak werkt aantoonbaar op Windows (Issue #85).

**E4.** `ScopeDecoder` moet na de refactoring `state.json` lezen via `StateRepository`. Maar `ScopeDecoder` zit in `mcp_server/core/` en `StateRepository` zit (vermoedelijk) in `mcp_server/managers/`. Is die afhankelijkheidsrichting acceptabel, of moet er een interface in `core/` komen?

> **✅ Beslissing (12-03-2026):** `IStateRepository` als `Protocol` in `mcp_server/core/` (structural subtyping). `FileStateRepository` in `managers/` implementeert het protocol zonder expliciete overerving. `ScopeDecoder` importeert alleen `IStateRepository` uit `core/` — geen dependency op `managers/`.

---

### F — PSE OCP hook-registry (F2, F6, F7, F21)

**F1.** Wat is de registry-structuur? `dict[str, Callable]` waarbij key de fase-naam is? Of een lijst van `HookSpec(phase: str, hook: Callable)` objecten? Wat als een fase twee hooks heeft (enter + exit)?

> **✅ Beslissing (12-03-2026):** YAML in `.st3/lifecycle.yaml` — niet Python dict-objecten. Event-keys zijn `"PHASE:enter"` / `"PHASE:exit"` / `"post_merge"` / `"post_checkout"`. Één event kan meerdere hook-entries hebben. Structuur:
> ```yaml
> hooks:
>   planning:exit:
>     - action: check_deliverable
>       source: workphases
>   implementation:enter:
>     - action: state_mutation
>       operation: initialize_cycle
>   post_merge:
>     - action: delete_file
>       path: .st3/state.json
>     - action: delete_file
>       path: .st3/deliverables.json
> ```
> Geïdentificeerde actietypes: `check_deliverable`, `state_mutation`, `delete_file`.

**F2.** Wie registreert hooks? Worden ze geconfigureerd in `phase_deliverables.yaml` (config-driven), of registreren modules zichzelf bij startup (plugin-patroon)?

> **✅ Beslissing (12-03-2026):** Plugin-patroon (module-registratie bij startup) + fail fast. Bij server startup registreert elke module zijn action-handler. De `lifecycle.yaml` loader valideert bij opstart dat elke `action`-naam een geregistreerde handler heeft — `ConfigError` als dat niet zo is. Fail fast voorkomt stille fouten bij runtime. Config-driven (YAML) bepaalt *welke* hooks actief zijn; plugin-registratie bepaalt de Python-implementatie.

**F3.** Blijft de PSE verantwoordelijk voor het aanroepen van hooks, of delegeert hij naar een `HookRunner`? Als PSE de runner blijft, lost het alleen het OCP-probleem op maar niet het SRP-probleem volledig.

> **✅ Beslissing (12-03-2026):** `HookRunner` als aparte service, geïnjecteerd in PSE. PSE's verantwoordelijkheid: state-overgangen valideren en opslaan. `HookRunner` orchestreert hooks zonder zelf worker-logica te bevatten — hij delegeert aan SRP-helpers per actietype (`DeliverableCheckAction`, `StateMutationAction`, `FileDeleteAction`). PSE roept alleen `self._hook_runner.run(event, context)` aan.

**F4.** Hoe worden hooks getest in isolatie? Als hooks geconfigureerd zijn als Python callables, zijn ze niet serialiseerbaar. Als ze geregistreerd zijn via naam (string → callable), is er een registry-lookup nodig bij test-setup.

> **✅ Beslissing (12-03-2026):** Triviaal via constructor-injectie van een fake `HookRegistry` met no-op action-handlers. `HookRunner` zelf is onafhankelijk van PSE testbaar. Elke action-helper (`DeliverableCheckAction`, etc.) is onafhankelijk testbaar met eigen unit tests.

**F5 — Aanvulling (12-03-2026): `transition` vs `force_transition` hook-afhandeling**

Code-analyse toont een implementatiegat: `transition()` roept de volledige `on_exit_*` methoden aan (DeliverableChecker, file_glob, etc.), `force_transition()` doet een vereenvoudigde key-presence check via `wp_config.get_exit_requires()` zonder DeliverableChecker. Ze delen de check-logica **niet** — een DRY-schending die dit issue oplost.

Onderzochte opties voor het blocking/warn onderscheid:

| Optie | Beschrijving | Config-first | DRY | SRP |
|---|---|---|---|---|
| **A — RunMode parameter** | PSE geeft `RunMode.BLOCKING`/`WARN` mee aan HookRunner | ❌ hardcoded in Python | ✅ | ⚠️ |
| **B — `blocking` vlag in lifecycle.yaml** | YAML bepaalt per event of het blokkeert | ✅ | ❌ actions gedupliceerd | ✅ |
| **C — PSE vangt exceptions op bij force** | Force transition roept zelfde hooks aan, vangt exceptions als warnings | ✅ | ✅ | ✅ |

> **✅ Beslissing (12-03-2026): Optie C.** `force_transition()` roept dezelfde hooks aan als `transition()`. Exceptions (`DeliverableCheckError`, `ConfigError`) worden door PSE gevangen en als actieve warnings teruggegeven in de ToolResult — niet geblokkeerd, niet stil genegeerd. PSE orchestreert transitie-gedrag; dat is zijn verantwoordelijkheid.
>
> Het blocking/warn onderscheid is geen hook-eigenschap maar een transitie-mechanisme-eigenschap. "Of een geforceerde transitie blokkeert" is geen configurabele keuze — fail-fast zegt: codeer dat niet als config.
>
> **Architecturele rechtsvaardiging voor tool-scheiding:** `transition` en `force_transition` zijn bewust aparte tools. `transition` kan in een agentic flow auto-accepted worden. `force_transition` vereist altijd expliciete human-approval. Het samenvoegen tot één generieke tool met een `force`-parameter zou dit onderscheid tenietdoen en de agent in staat stellen om stilletjes gates te omzeilen. De tool-scheiding is de enforce-mechanisme, niet alleen een UX-keuze.

---

### G — Consumer consolidatie (F19, WF-2, WFC-1, WPC-1)

**G1.** `workflow_config.py` heeft `get_first_phase()` en `has_workflow()` die `workflows.py::WorkflowConfig` niet heeft. Worden deze methoden toegevoegd aan de gecombineerde klasse, of zijn de consumers die ze gebruiken (`issue_tools.py`) herschrijfbaar om de bestaande API te gebruiken?

> **✅ Beslissing (12-03-2026):** Methoden worden toegevoegd aan de gecombineerde klasse én consumers worden gerefactored. Code-analyse toont twee `WorkflowConfig` klassen (`workflows.py` en `workflow_config.py`) met overlappende verantwoordelijkheid en inconsistent aanroeppatroon:
> - `project_tools.py` roept `WorkflowConfig.load()` aan per request — maakt elke keer een nieuwe instantie (bug + DRY-schending)
> - `issue_tools.py` importeert uit `workflow_config.py` (andere klasse, andere singleton)
> - PSE/ProjectManager/OperationPolicies gebruiken module-level singleton uit `workflows.py`
>
> Oplossing: `workflow_config.py` wordt verwijderd. Alle methoden (`get_workflow`, `validate_transition`, `get_first_phase`, `has_workflow`) komen in één `WorkflowConfig` in `workflows.py`. Alle callers migreren naar dit ene import-pad. Refactor van callers is vereist — niet optioneel.

**G2.** Na consolidatie: wordt de module-level singleton `workflow_config = WorkflowConfig.load()` in `workflows.py` behouden, of wordt het singleton-patroon gemigreerd naar `ClassVar` (zoals in `workflow_config.py` en `git_config.py`)?

> **✅ Beslissing (12-03-2026):** `ClassVar` patroon — module-level singleton verwijderd. Reden: module-level `workflow_config = WorkflowConfig.load()` laadt het YAML-bestand bij elke import, ook in tests zonder het bestand. `ClassVar` met lazy init is testbaar, consistent met `GitConfig`, en voorkomt import-time side effects. Uniform aanroeppatroon na refactor:
> ```python
> from mcp_server.config.workflows import WorkflowConfig
> cfg = WorkflowConfig.load()   # cached singleton, lazy init
> ```
> Geraakte callers die gerefactored worden: `issue_tools.py`, `project_tools.py`, `conftest.py`, `tests/fixtures/workflow_fixtures.py`.

**G3.** `ScopeEncoder` en `ScopeDecoder` lezen `workphases.yaml` elk direct. Na F21 lezen ze ook `phase_deliverables.yaml` (voor subphase-validatie en commit_type_map). Hoe wordt de afhankelijkheid geïnjecteerd zonder dat beide klassen een lange constructor-parameter-lijst krijgen? Config facade/context object?

> **✅ Beslissing (12-03-2026):** `PhaseConfigContext` facade (dataclass met `workphases: WorkphasesConfig` + `phase_contracts: PhaseContractsConfig`). Geïnjecteerd via constructor. Uitbreidbaar zonder API-breuk. Tests injecteren één mock-object. Consistent met het principe dat config-kennis geïsoleerd blijft.

---

### H — Naamgeving en migratie `tdd` → `implementation` (F21)

**H1.** Worden bestaande `state.json` bestanden met `current_tdd_cycle` automatisch gemigreerd, of wordt backward-compat leescode toegevoegd? Hoeveel actieve branches zijn er per vandaag die geraakt worden?

> **✅ Beslissing (11-03-2026):** Handmatige fix indien nodig. Consistent met BC-2. Geen automatische migratie bij opstart, geen backward-compat leescode.

**H2.** Wordt `tdd` als fase-naam volledig verwijderd, of blijft hij als alias in `workphases.yaml` voor backward-compat? Als alias: hoe lang, en wie beheert de deprecation?

> **✅ Beslissing (12-03-2026):** Volledig verwijderd. Consistent met flag-day BC-aanpak. Geen alias, geen deprecation-periode.

**H3.** Labels in GitHub (`phase:tdd`, `phase:red`, `phase:green`, `phase:refactor`) zijn extern en niet zomaar hernoembaar. Worden die labels behouden naast de nieuwe (`phase:implementation`, `phase:red` blijft als sub-label), of is er een label-migratie nodig?

> **✅ Beslissing (12-03-2026):** GitHub labels behouden zoals ze zijn. Extern systeem, label-migratie is overkill. `phase:red`, `phase:green`, `phase:refactor` blijven geldig als sub-labels van `implementation`. Historische commits met `phase:tdd` zijn acceptabel (BC-1).

**H4.** `docs`-workflow heeft geen implementatiefase in de huidige config. Na F21 heeft ook `docs` een `implementation`-fase — of juist expliciet niet? Hoe modelleert `phase_deliverables.yaml` een workflow zonder implementatie (lege fase, of fase ontbreekt in config)?

> **✅ Beslissing (12-03-2026):** Fase ontbreekt in `phase_contracts.yaml` voor de `docs`-workflow (niet aanwezig = niet van toepassing). Resolver geeft `[]` terug (D3). Een lege entry aanmaken zou impliceren dat `docs` *weet* van implementatie maar niets vereist — conceptueel onjuist.

---

### I — `branch_name_pattern` en `branch_types` (F16, F17)

**I1.** `branch_name_pattern: "^[0-9]+-[a-z][a-z0-9-]*$"` valideert alleen het naam-gedeelte na het slash. Is dat correct? Of moet het patroon de volledige naam inclusief type-prefix valideren, en zo ja, wie genereert dan het gecombineerde patroon?

> **✅ Beslissing (12-03-2026):** Correct — `branch_name_pattern` valideert alleen het naam-gedeelte na de slash. `branch_types` valideert het type-prefix. Bewuste scheiding van verantwoordelijkheden: `GitConfig` combineert beide dynamisch via `build_branch_type_regex()` (methode bestaat al). Gecombineerd patroon voor volledige branch-validatie: `f"^{git_config.build_branch_type_regex()}/{branch_name_pattern.lstrip('^')}"`. Geen wijziging aan dit ontwerp nodig.

**I2.** Bij toevoeging van `bug` en `hotfix` aan `branch_types`: hebben die types bestaande beschermde branches of merge-strategieën die hiervan afhangen (bijv. in `operation_policies.yaml`)?

> **✅ Beslissing (12-03-2026):** Geen `operation_policies.yaml` met beschermde branches of merge-strategieën afhankelijk van branch-types. Toevoeging van `bug`/`hotfix` aan `branch_types` is een puur additieve config-wijziging in `git.yaml` — geen cascade-effecten.

**I3.** `_extract_issue_from_branch()` in PSE wordt vervangen door een lookup via `GitConfig.branch_types`. Maar die methode gebruikt `re.match` met een hardcoded pattern. Wordt de regex dynamisch gebouwd vanuit `GitConfig.build_branch_type_regex()` (die methode bestaat al), of is er een directere aanpak?

> **✅ Beslissing (12-03-2026):** Dynamisch via `GitConfig.build_branch_type_regex()` (bestaat al). Hardcoded `re.match(r"^(?:feature|fix|bug|...)/(\d+)-", branch)` vervangen door `re.match(rf"^{git_config.build_branch_type_regex()}/(\d+)-", branch)`. DRY en Config-first: `branch_types` in `git.yaml` is de enige bron van waarheid voor welke types geldig zijn.

---

### J — `commit_type_map` beschikbaarheid in de tool-laag (F21, F22, GT-5)

Het hernoemen van `tdd` naar `implementation` en het verplaatsen van de `commit_type_map` naar `phase_deliverables.yaml` creëert een architectureel hiaat: op geen enkele laag is meer duidelijk wie verantwoordelijk is voor het opzoeken van `commit_type = "test"` bij `sub_phase = "red"` voor een feature-workflow versus `commit_type = "test"` bij `sub_phase = "reproduce"` voor een bug-workflow.

**J1.** Welke laag resolveert de `commit_type_map` na de refactoring? Drie opties:

| Optie | Beschrijving | Voordeel | Nadeel |
|---|---|---|---|
| **A — Tool-laag** | `GitCommitTool.execute()` leest `phase_deliverables.yaml` + `workflow_name` uit `state.json`, bepaalt `commit_type`, geeft het als expliciete override door aan `commit_with_scope()` | `GitManager` blijft puur; commit_type altijd expliciet | Tool-laag heeft config-kennis; `workflow_name` moet beschikbaar zijn in state |
| **B — Manager-laag** | `commit_with_scope()` krijgt `workflow_name` als extra parameter en resolveert via `PhaseDeliverableResolver` | Enkelvoudig resolverpad; manager kent zijn eigen context | `GitManager` koppelt aan `PhaseDeliverableResolver`; API-uitbreiding |
| **C — ScopeEncoder** | `ScopeEncoder` krijgt `phase_deliverables_path` + `workflow_name` en levert ook `commit_type` terug | Één class weet alles over de commit | ScopeEncoder krijgt een tweede verantwoordelijkheid (validatie + type-lookup) |

> **✅ Beslissing (11-03-2026):** Optie A — tool-laag is composition root. `GitManager.commit_with_scope()` ontvangt `commit_type` als expliciete parameter. `PhaseContractResolver` zit in de tool-laag. `GitManager` blijft puur en heeft geen dependency op `PhaseContractResolver`.

**J2.** Hoe weet de tool-laag de `workflow_name`? Na F13 (`projects.json` abolishment) staat `workflow_name` in `state.json`. Bij auto-detectie van `workflow_phase` leest `execute()` al uit `state.json` via `PhaseStateEngine.get_current_phase()`. Mag diezelfde aanroep ook `workflow_name` retourneren, of vereist dat een aparte `StateRepository.read_state()` aanroep?

> **✅ Beslissing (12-03-2026):** `StateRepository.load(branch)` geeft de volledige `BranchState` terug inclusief `workflow_name` — één aanroep. `get_current_phase()` wordt een convenience-wrapper die intern `StateRepository.load()` aanroept en enkel `current_phase` retourneert. Tool-laag roept `StateRepository.load()` direct aan wanneer meer dan alleen de phase nodig is.

**J3.** Backward-compatibel legacy `phase`-pad: na F21 bestaat `"tdd"` niet meer als fase. `mapped_workflow_phase = "tdd"` in de legacy path breekt onmiddellijk. Twee keuzes:
- **(a) Verwijderen:** legacy `phase`-parameter volledig droppen. Breaking change, maar alle gebruik is expliciet `DEPRECATED`.
- **(b) Migreren:** legacy path mapt naar `"implementation"`, `sub_phase` ongewijzigd (`red`, `green`, `refactor` zijn immers subphases van de feature-implementatie-werkwijze).
Keuze beïnvloedt of we backward-compat tests behouden of verwijderen.

> **✅ Beslissing (12-03-2026):** (a) — Legacy `phase`-parameter volledig droppen. Consistent met BC-5 en F23. `mapped_workflow_phase = "tdd"` breaking is gewenst: dwingt alle callers te migreren naar `phase="implementation"`. Backward-compat tests verwijderen, geen migratie-pad.

**J4.** Wat is de foutmelding als `commit_type_map` voor een workflow geen entry heeft voor de opgegeven `sub_phase`? Gooit de resolver een `ConfigurationError` (mis-configuratie) of een `ValueError` (gebruikersfout)? Wie vangt dit op  — `GitManager`, tool-laag of `PhaseDeliverableResolver`?

> **✅ Beslissing (12-03-2026):** Zie D4 — `ConfigError` met `file_path=".st3/config/phase_contracts.yaml"`. Gevangen door `@tool_error_handler` op de tool-laag. `PhaseContractResolver` gooit, decorator vangt, geen try/except in manager of PSE.

---

### K — Testsuite scope en aanpak (F23, F24)

De flag-day aanpak (F24) raakt een significant deel van de testsuite. De volgende testbestanden vereisen herschrijving of verwijdering — geen backward-compat patches.

**K1.** Geraakte testbestanden geïdentificeerd in research:

| Bestand | Reden | Aanpak |
|---|---|---|
| `tests/mcp_server/core/test_scope_encoder.py` | `phase="tdd"`, `P_TDD_SP_*` assertions | Bijwerken naar `"implementation"` + `P_IMPLEMENTATION_SP_*` |
| `tests/mcp_server/core/test_phase_detection.py` | `workflow_phase == "tdd"`, `P_TDD_SP_RED` in fixtures | Bijwerken naar `"implementation"` |
| `tests/mcp_server/managers/test_git_manager_config.py` | `P_TDD_SP_RED`, `P_TDD_SP_GREEN` assertions | Bijwerken scope strings |
| `tests/mcp_server/unit/tools/test_transition_tools.py` | `planning_deliverables`, `current_tdd_cycle`, `tdd_cycle_history`, `initial_phase="tdd"` | Volledig herschrijven op `deliverables.json` + `current_cycle` |
| `tests/mcp_server/unit/tools/test_project_tools.py` | Alle `projects.json` read-asserts (8+ testcases) | Herschrijven op `deliverables.json` |
| `tests/mcp_server/unit/tools/test_initialize_project_tool.py` | `projects.json` aanmaak- en structuurtests | Herschrijven: `deliverables.json` + verrijkte `state.json` |
| `tests/mcp_server/unit/managers/test_phase_state_engine.py` | `projects.json`-injectie in fixtures | Herschrijven fixtures |
| `tests/mcp_server/unit/managers/test_phase_state_engine_recovery.py` | `projects.json` als bron voor reconstructie | Herschrijven op `state.json + git` |
| `tests/mcp_server/integration/test_issue39_cross_machine.py` | `projects.json` commit naar git, volledige flow | Scenario herschrijven op nieuwe architectuur |
| `tests/mcp_server/unit/tools/test_force_phase_transition_tool.py` | `projects.json` path assertions | Bijwerken |
| `tests/mcp_server/integration/test_workflow_cycle_e2e.py` | `"tdd"` fase in e2e-flow, `workflow_phase="tdd"` commits | Bijwerken naar `"implementation"` |
| `tests/mcp_server/conftest.py` | `from mcp_server.config.workflow_config import WorkflowConfig` | Bijwerken na consolidatie (F19/KPI 16) |

**K2.** Wordt de testsuite voor de geraakte bestanden volledig herschreven in de TDD-fase van dit issue (RED first), of worden bestaande tests als basis genomen en incrementeel bijgewerkt? Aanbeveling: RED-first voor de herschreven scenarios (transition_tools, project_tools, initialize_project, cross_machine); incrementele update voor de scope/phase string aanpassingen.

> **✅ Beslissing (11-03-2026):** Akkoord met aanbeveling. RED-first voor herschreven scenarios (transition_tools, project_tools, initialize_project, cross_machine); incrementele update voor scope/phase string aanpassingen.

**K3.** Worden de tests gegroepeerd per TDD-cycle in planning, of per bestand? Aanbeveling: per architectuurlaag, niet per bestand — zodat de TDD-cycles overeenkomen met de implementatievolgorde in de KPI-handover-matrix.

> **✅ Beslissing (11-03-2026):** Akkoord met aanbeveling. Tests gegroepeerd per architectuurlaag, niet per bestand. TDD-cycles corresponderen met de implementatievolgorde in de KPI-handover-matrix.

---

## Related Documentation
- **[docs/development/issue257/research.md][related-1]**
- **[docs/development/issue257/research_sections_config_architecture.md][related-2]**
- **[mcp_server/managers/phase_state_engine.py][related-3]**
- **[mcp_server/managers/project_manager.py][related-4]**
- **[mcp_server/managers/deliverable_checker.py][related-5]**
- **[mcp_server/managers/git_manager.py][related-6]**
- **[mcp_server/config/git_config.py][related-7]**
- **[mcp_server/tools/git_tools.py][related-11]**
- **[.st3/workflows.yaml][related-8]**
- **[.st3/workphases.yaml][related-9]**
- **[.st3/git.yaml][related-10]**

<!-- Link definitions -->

[related-1]: docs/development/issue257/research.md
[related-2]: docs/development/issue257/research_sections_config_architecture.md
[related-3]: mcp_server/managers/phase_state_engine.py
[related-4]: mcp_server/managers/project_manager.py
[related-5]: mcp_server/managers/deliverable_checker.py
[related-6]: mcp_server/managers/git_manager.py
[related-7]: mcp_server/config/git_config.py
[related-8]: .st3/workflows.yaml
[related-9]: .st3/workphases.yaml
[related-10]: .st3/git.yaml
[related-11]: mcp_server/tools/git_tools.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |