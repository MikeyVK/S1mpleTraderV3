# Architecturele Principes — S1mpleTrader V3

**Status:** Bindend contract voor alle implementatiewerk
**Lezen bij:** Sessie-start — gerefereerd vanuit `.github/.copilot-instructions.md`
**Laatste update:** 2026-03-12

---

## 0. Primaat van dit document

Deze principes zijn **wetten, geen suggesties**. Een code-wijziging die deze principes schendt wordt **REJECTED** bij code review, ook als alle tooling-gates groen zijn. Tooling-gates (ruff, mypy, coverage) toetsen *vorm*. Dit document toetst *architectuur*.

> **Agents:** lees dit document bij elke implementatie-sessie. De vraag "mag ik dit zo schrijven?" wordt beantwoord door dit document, niet door of ruff klaagt.

---

## 1. SOLID

### 1.1 SRP — Single Responsibility Principle

Een klasse heeft precies één reden om te wijzigen.

**Bindende regels:**
- Een klasse met meer dan één logische verantwoordelijkheid is een God Class. Split altijd.
- Methoden die state persisteren, state lezen, én businesslogica uitvoeren behoren niet in dezelfde klasse.
- Test of je de klasse in één zin kunt beschrijven zonder "en" — als dat niet lukt, is er een SRP-schending.

**Anti-patronen:**
```python
# ❌ WRONG — PSE doet state-persistentie + transitie-validatie + hook-uitvoering + reconstructie
class PhaseStateEngine:
    def _save_state(self): ...      # state persistentie
    def transition(self): ...       # validatie + hook-dispatch
    def on_exit_planning(self): ... # hook-implementatie
    def _reconstruct(self): ...     # git-reconstructie

# ✅ CORRECT — elke klasse heeft één verantwoordelijkheid
class StateRepository: ...         # state persistentie
class PhaseStateEngine: ...        # transitie-validatie + dispatch
class EnforcementRunner: ...       # enforcement-orchestratie
class GitStateReconstructor: ...   # git-reconstructie
```

### 1.2 OCP — Open/Closed Principle

Code is open voor uitbreiding, gesloten voor aanpassing.

**Bindende regels:**
- If-chains op fase-namen, workflow-namen of action-types zijn OCP-schendingen. Gebruik een registry of config-driven dispatch.
- Een nieuwe fase of action-type toevoegen mag **nooit** een bestaande methode aanpassen. Het voegt alleen een nieuwe registratie of YAML-entry toe.

**Anti-patroon:**
```python
# ❌ WRONG — elke nieuwe fase = aanpassing van deze methode
def transition(self, from_phase):
    if from_phase == "planning":
        self.on_exit_planning()
    elif from_phase == "research":
        self.on_exit_research()
    # nieuwe fase vereist code-aanpassing hier
```

**Correct patroon:** `enforcement.yaml` + `EnforcementRunner` registry — zie `docs/development/issue257/`.

### 1.3 LSP — Liskov Substitution Principle

Subklassen moeten volledig uitwisselbaar zijn met hun basisklasse.

**Bindende regels:**
- `FileStateRepository` en `InMemoryStateRepository` zijn uitwisselbaar op elke plek die `IStateRepository` accepteert.
- Een subklasse mag de precondities van de basisklasse niet verzwaren en de postcondities niet verzwakken.
- Tests die `InMemoryStateRepository` gebruiken moeten dezelfde contracten valideren als productietests met `FileStateRepository`.

### 1.4 ISP — Interface Segregation Principle

Clients mogen niet gedwongen worden interfaces te implementeren die ze niet gebruiken.

**Bindende regels:**
- Een read-only consumer (bijv. `ScopeDecoder`) krijgt **nooit** een interface met write-methoden.
- Splits interfaces op het smalste bruikbare contract:
  ```python
  # core/interfaces.py
  class IStateReader(Protocol):
      def load(self, branch: str) -> BranchState: ...

  class IStateRepository(IStateReader, Protocol):
      def save(self, state: BranchState) -> None: ...
  ```
- `ScopeDecoder` → injecteert `IStateReader`
- `PhaseStateEngine` → injecteert `IStateRepository`

### 1.5 DIP — Dependency Inversion Principle

High-level modules hangen niet af van low-level modules. Beiden hangen af van abstracties.

**Bindende regels:**
- Directe instantiatie (`SomeManager()`) in `execute()` van een tool is verboden. Alle dependencies via constructor-injectie.
- Interfaces voor externe systemen (bestand, git, GitHub API) leven in `mcp_server/core/interfaces/` — nooit in `managers/`.
- De concrete implementatie mag alleen op de composition root (tool-laag of server-startup) worden geïnstantieerd.

**Anti-patroon:**
```python
# ❌ WRONG — tool instantieert direct
async def execute(self, params):
    pm = ProjectManager(workspace_root=Path.cwd())  # directe instantiatie
    state_engine = PhaseStateEngine(workspace_root=Path.cwd(), project_manager=pm)

# ✅ CORRECT — dependency geïnjecteerd via constructor
class TransitionPhaseTool(BaseTool):
    def __init__(self, pse: IPhaseStateEngine | None = None) -> None:
        self._pse = pse or PhaseStateEngine.create_default()
```

---

## 2. DRY + SSOT — Don't Repeat Yourself + Single Source of Truth

**Bindende regels:**
- Elke fact van het systeem heeft precies **één definitieve locatie**. Alle andere locaties verwijzen of lezen.
- `branch_types` in `git.yaml` = SSOT. Regex-alternation in PSE die dezelfde types opsomt = verbod.
- `workflows.yaml` = SSOT voor fase-volgorde. Hardcoded fase-namen in Python = verbod.
- `phase_contracts.yaml` = SSOT voor `commit_type_map`. Hardcoded `if sub_phase == "red": commit_type = "test"` = verbod.
- Twee klassen die hetzelfde config-bestand lezen zonder gemeenschappelijke interface = DRY-schending (zie `WorkflowConfig`-probleem in issue #257).

---

## 3. Config-First

Businesskennis die op meerdere plaatsen nodig is, wordt **altijd** in config vastgelegd, nooit hardcoded.

**Bindende regels:**
- Fase-namen, workflow-namen, subphase-namen, commit-type-mappings, branch-types, deliverable-gates: **altijd in YAML**, nooit als string-literal in Python.
- Een `if fase_naam == "implementation"` in productie-code is een Config-First schending.
- De loader is verantwoordelijk voor fail-fast validatie van de config. Code die de config leest mag nooit vinnig de ontbrekende velden als "normaal" beschouwen.
- **SSOT voor config**: één reader-class per config-bestand. Geen twee klassen die hetzelfde YAML-bestand onafhankelijk lezen.

**Validatieregel bij `cycle_based`:**
Config-loader gooit `ConfigError` als `cycle_based: true` gecombineerd is met `commit_type_map: {}` (lege map). Deze combinatie = onbruikbare config.

---

## 4. Fail-Fast

Fouten worden zo vroeg mogelijk gedetecteerd, zo dicht mogelijk bij de oorzaak.

**Bindende regels:**
- Configuratiefouten (ontbrekende velden, inconsistente waarden) worden gedetecteerd bij **server-opstart**, niet bij runtime van een gebruikersactie.
- Een onbekende `action-type` in `enforcement.yaml` → `ConfigError` op startup. Nooit een `KeyError` bij uitvoering.
- Ontbrekende YAML-bestanden → expliciet `FileNotFoundError` met pad, nooit `None` return.
- Combinatievalidaties (bv. `cycle_based: true` + lege `commit_type_map`) worden in de Pydantic-loader gecheckt via `model_validator`, niet in de consumer.

---

## 5. CQS — Command/Query Separation

Methoden die state wijzigen (commands) en methoden die state lezen (queries) zijn strikt gescheiden.

**Bindende regels:**
- Een methode retourneert **ofwel** een waarde (query) **óf** muteert state (command) — nooit beide.
- Value objects die als query-resultaat teruggegeven worden, zijn **frozen**: `model_config = ConfigDict(frozen=True)`. Het type-systeem afdwingt dat queries niet muteren.
- `BranchState` is frozen. Elke code die probeert een `BranchState` te muteren geeft een `ValidationError`.
- `PSE.get_state()` en `PSE.get_current_phase()` zijn pure queries — ze roepen **nooit** `save()` aan.

```python
# ✅ Frozen value object als query-resultaat
class BranchState(BaseModel):
    model_config = ConfigDict(frozen=True)
    branch: str
    workflow_name: str
    current_phase: str
    # ... alle velden immutabel
```

---

## 6. ISP in de praktijk — Smalle interfaces

Zie ook 1.4. Concrete toepassing voor dit project:

| Consumer | Interface | Reden |
|---|---|---|
| `ScopeDecoder` | `IStateReader` | lees-only |
| `PhaseContractResolver` | `IStateReader` | lees-only |
| `PhaseStateEngine` | `IStateRepository` | schrijft én leest |
| `HookRunner`/`EnforcementRunner` | `IStateRepository` | schrijft cycle-state |

Alle `IStateReader` en `IStateRepository` interfaces leven in `mcp_server/core/interfaces/`. Nooit in `managers/`.

---

## 7. Law of Demeter

Praat met directe vrienden, niet met hun vrienden.

**Bindende regel:**
- `tool.pse.state_repo.load(branch)` = schending. Tool praat met PSE, PSE praat met StateRepository.
- Tool-laag kent: `PSE`, `GitManager`, `WorkflowConfig`. Tool-laag kent **niet**: `StateRepository`, `AtomicJsonWriter`, `DeliverableChecker`.
- Diepte van dependency-chain is maximaal 2 lagen vanuit de tool.

---

## 8. Explicit over Implicit

Geen stille fallbacks, geen impliciete conventies die niet in code zichtbaar zijn.

**Bindende regels:**
- Geen `None` als fallback voor een configuratiewaarde die verplicht is → `ConfigError`.
- Geen `workflow_name: "unknown"` zonder expliciete waarschuwing terug naar de caller.
- Geen stille default die een fout verbergt. Liever een harde fout op het juiste moment dan een stille non-waarde die drie lagen later een `AttributeError` veroorzaakt.
- Code die "verhaal vertelt": class-variabelen, type-annotaties en Pydantic-constraints zijn de primaire communicatiemiddelen. Comments suppleren, zij vertellen het verhaal niet.

---

## 9. YAGNI — You Aren't Gonna Need It

Schrijf geen code voor hypothetische toekomstige behoeften.

**Bindende regels:**
- Geen migratiecode schrijven voor scenario's die nu niet bestaan.
- Geen backward-compat laag voor gedepreceerde parameters langer dan één release-cyclus.
- Geen abstractielaag voor een concern dat vandaag slechts één implementatie heeft (tenzij testbaarheid het vereist).
- Geen configureerbare vlag voor gedrag dat altijd hetzelfde moet zijn.

---

## 10. Cohesion — Methoden bij hun domein

**Bindende regel:**
- Een methode die uitsluitend kennis van domein X nodig heeft, hoort in de klasse die domein X modelleert.
- Voorbeeld: `extract_issue_number(branch)` → hoort in `GitConfig`, niet in `PhaseStateEngine`. De methode antwoord een vraag over git-conventies.
- Geef bij twijfel: "Is dit een vraag over X?" Als het antwoord ja is, hoort de methode bij X.

---

## 11. Dependency Injection als default

**Bindende regels:**
- Constructor-injectie is de default. `execute()` instantieert nooit zelf een dependency.
- Alle productie-dependencies zijn injecteerbaar. Tests injecteren een fake/in-memory variant.
- Composition root: alleen de server-startup en de tool-laag mogen concrete implementaties instantiëren.
- `BaseTool.__init__` accepteert optionele dependencies met `None`-default die via factory-method de concrete implementatie retourneren:
  ```python
  def __init__(self, pse: IPhaseStateEngine | None = None) -> None:
      self._pse = pse or PhaseStateEngine.create_default()
  ```

---

## 12. Geen import-time side effects

**Bindende regel:**
- Module-level code die bestanden leest, netwerkverzoeken doet, of singletons initialiseert = verbod.
- `workflow_config = WorkflowConfig.load()` als module-level statement veroorzaakt FileNotFoundError bij import in tests. Gebruik `ClassVar` met lazy init.
- Alle singletons gebruiken het `ClassVar` patroon: de instantie wordt aangemaakt bij de eerste aanroep van `.load()`, niet bij import.

---

## 13. Enforcement is Config-First

**Bindende regel:**
- Gedrag dat "bij fase X triggert" of "na tool Y uitvoert" wordt geconfigureerd in `enforcement.yaml`, niet hardcoded in Python.
- Elke nieuwe enforcement-actie = één registratie in de `EnforcementRunner` action-registry + één entry in `enforcement.yaml`. Nooit een if-chain in PSE of een tool.
- `BaseTool.enforcement_event: str | None = None` — elke tool declareert declaratief zijn eigen enforcement-event als class-variabele.

---

## Snelreferentie — Verboden patronen

| Patroon | Schending | Alternatief |
|---|---|---|
| `if phase_name == "tdd":` | Config-First, OCP | Config bepaalt, code dispatcht op type |
| `WorkflowConfig()` in `execute()` | DIP, SRP | Constructor-injectie |
| `if sub_phase == "red": commit_type = "test"` | DRY, Config-First | `commit_type_map` in `phase_contracts.yaml` |
| Twee klassen lezen hetzelfde YAML | SSOT, DRY | Één reader-class, singleton |
| `module_level_var = Config.load()` | Fail-Fast (import side effect) | ClassVar + lazy init |
| `ScopeDecoder` injecteert `IStateRepository` | ISP | `ScopeDecoder` injecteert `IStateReader` |
| `get_state()` roept `save()` aan | CQS | Query retourneert, command muteert |
| `BranchState.current_phase = "..."` | CQS (frozen) | Maak nieuwe `BranchState` via PSE command |
| `tool.pse.state_repo.load()` | Law of Demeter | `tool.pse.get_state(branch)` |
| Hardcoded regex `r"^(?:feature\|fix\|..."` | DRY, Config-First | `git_config.build_branch_type_regex()` |
| Lege `commit_type_map` bij `cycle_based: true` | Fail-Fast | `ConfigError` op startup |
| Migratiecode voor gedepreceerde parameter | YAGNI | Flag-day: verwijder direct |

---

## Gerelateerde beslissingen

De patronen in dit document zijn ontleend aan het design-document voor issue #257:
- [docs/development/issue257/research_config_first_pse.md](../development/issue257/research_config_first_pse.md) — volledige redenering en trade-offs per beslissing
