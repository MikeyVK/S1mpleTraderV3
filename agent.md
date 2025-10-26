# S1mpleTrader V2 - AI Assistent Instructies

Hallo! Ik ben een AI-assistent die je helpt met het ontwikkelen van de S1mpleTrader V2 applicatie. Dit document geeft me de nodige context over de architectuur, de belangrijkste ontwerpprincipes en de codeerstandaarden.

## 1. Visie & Kernprincipes

Mijn primaire doel is om je te helpen bij het bouwen en onderhouden van een uniforme, plugin-gedreven architectuur die de volledige levenscyclus van een handelsstrategie ondersteunt. Ik houd me aan de volgende **vier fundamentele kernprincipes**:

* **Plugin First**: Alle strategische logica is ingekapseld in zelfstandige, onafhankelijk testbare plugins. Dit is de kern van het systeem.
* **Scheiding van Zorgen (Separation of Concerns)**: Er is een strikte scheiding tussen de `Workers` (de wat), de `ExecutionEnvironment` (de waar), de `Factories` (de hoe) en `EventBus` (waarmee).
* **Configuratie-gedreven**: Het gedrag van de applicatie wordt volledig bestuurd door mens-leesbare `YAML`-bestanden. De code is de motor, de configuratie is de bestuurder.
* **Contract-gedreven**: Alle data-uitwisseling wordt gevalideerd door strikte Pydantic-schema's (backend) en TypeScript-interfaces (frontend). Dit zorgt voor voorspelbaarheid en type-veiligheid.

### 1.1. Fundamentele Architecturale Verschuivingen (KRITIEK!)

**BELANGRIJKE NOTITIE:** De architectuur heeft **drie fundamentele verschuivingen** ondergaan die essentieel zijn voor correct begrip:

#### **Verschuiving 1: Platgeslagen Orkestratie (Geen Operators Meer)**
- **Was:** Operators (ContextOperator, OpportunityOperator, etc.) orkestreerden workers
- **Nu:** **OPERATORS BESTAAN NIET MEER**. Workers worden direct bedraad via expliciete `wiring_map.yaml`
- **Impact:** De EventAdapter is nu het **enige** orkestratieconcept - één adapter per component
- **Configuratie:** UI genereert `strategy_wiring_map.yaml` op basis van `base_wiring.yaml` templates

#### **Verschuiving 2: Point-in-Time Data Model**
- **Was:** Een groeiende `enriched_df` werd doorgegeven tussen workers
- **Nu:** **DTO-Centric** model met `TickCache` voor één tick en `ITradingContextProvider`
- **Impact:** Workers vragen data expliciet op en produceren specifieke DTOs
- **Communicatie:** Twee gescheiden paden - TickCache (sync flow) en EventBus (async signals)

#### **Verschuiving 3: BuildSpec-Gedreven Bootstrap**
- **Was:** ComponentBuilder las direct YAML en assembleerde
- **Nu:** **ConfigTranslator** vertaalt YAML → BuildSpecs → Factories bouwen
- **Impact:** OperationService is pure lifecycle manager, ConfigTranslator is de enige "denker"
- **Validatie:** Fail-fast validatie tijdens bootstrap via DependencyValidator

## 2. Architectuur Overzicht

De applicatie heeft een strikt gelaagde architectuur met een eenrichtingsverkeer van afhankelijkheden.

```
+-------------------------------------------------------------+
|  Frontend (CLI, Web API, Web UI)                            |
+--------------------------+----------------------------------+
                           |
                           v
+--------------------------+----------------------------------+
|  Service (Orchestratie & Business Workflows)                |
|  - OperationService (Lifecycle Manager)                     |
|  - OptimizationService, ParallelRunService                  |
+--------------------------+----------------------------------+
                           |
                           v
+--------------------------+----------------------------------+
|  Backend (Engine)                                           |
|  - ConfigTranslator (YAML -> BuildSpecs)                    |
|  - Factories (BuildSpecs -> Components)                     |
|  - Workers, Singletons, EventBus                            |
+-------------------------------------------------------------+
```

### 2.1. De Drie Configuratielagen (Addendum 3.8)

**KRITIEK CONCEPT:** Configuratie is strikt gescheiden in drie lagen:

1. **PlatformConfig** (`platform.yaml`)
   - Globale, statische platform instellingen
   - Geladen bij OperationService start
   - Bevat: logging, paths, locale settings
   - **BEVAT GEEN** connectors, environments of schedules

2. **OperationConfig** (`operation.yaml` + referenties)
   - Specifieke "werkruimte" of "campagne"
   - Groepeert: connectors, data_sources, environments, schedule
   - Geladen per operatie
   - Bevat lijst van `strategy_links`

3. **StrategyConfig** (`strategy_blueprint.yaml`)
   - Volledige gebruikersintentie voor één strategie
   - Just-in-time geladen per strategy_link
   - Bevat: workforce, strategy-specifieke wiring

### 2.2. De Bootstrap Workflow (BuildSpec-Gedreven)

```
User Start Command
    ↓
OperationService.start_all_strategies()
    ↓
Voor elke strategy_link:
    ↓
1. ConfigLoader → Laadt PlatformConfig, OperationConfig, StrategyConfig
    ↓
2. ConfigValidator → Valideert alle drie lagen
    ↓
3. ConfigTranslator → Vertaalt naar BuildSpecs
   - connector_spec
   - data_source_spec
   - environment_spec
   - workforce_spec
   - wiring_spec (NIEUW - vervangt operator_spec)
   - persistor_spec
    ↓
4. Factory Chain (in volgorde):
   A. ConnectorFactory.build_from_spec()
   B. DataSourceFactory.build_from_spec()
   C. EnvironmentFactory.build_from_spec()
   D. PersistorFactory.build_from_spec()
   E. WorkerFactory.build_from_spec()
   F. EventWiringFactory.wire_all_from_spec() ← KRITIEK!
    ↓
5. Environment.start()
    ↓
6. OperationService registreert StrategieInstantie
```

### 2.3. Platgeslagen Orkestratie (GEEN OPERATORS!)

**OUDE ARCHITECTUUR (ACHTERHAALD):**
```
ExecutionEnvironment → Operator → Workers → Output
```

**NIEUWE ARCHITECTUUR:**
```
ExecutionEnvironment → EventBus → EventAdapters → Workers → DispositionEnvelope → EventAdapters → EventBus
```

**Kernconcepten:**
- **Elke component** (worker of singleton) krijgt zijn eigen EventAdapter
- Adapters configureren via `wiring_spec` uit BuildSpecs
- Wiring wordt gedefinieerd in `strategy_wiring_map.yaml` (UI-gegenereerd)
- Geen operator-logica meer - pure event-gedreven communicatie

## 3. Worker Taxonomie & Data Model

### 3.1. De 5 Worker Categorieën

**BELANGRIJK:** Workers zijn NIET meer gegroepeerd onder Operators. Ze worden direct bedraad via EventAdapters.

1. **ContextWorker - "De Cartograaf"**
   - Verrijkt marktdata met objectieve context
   - Output: `set_result_dto()` met plugin-specifieke DTO naar TickCache
   - Publiceert NOOIT events op EventBus
   - 7 Sub-types: REGIME_CLASSIFICATION, STRUCTURAL_ANALYSIS, INDICATOR_CALCULATION, etc.

2. **OpportunityWorker - "De Verkenner"**
   - Detecteert subjectieve handelskansen
   - Output: `DispositionEnvelope(PUBLISH)` met `OpportunitySignalDTO` (Systeem DTO)
   - Kan ook intermediaire scores produceren voor TickCache
   - 7 Sub-types: TECHNICAL_PATTERN, MOMENTUM_SIGNAL, MEAN_REVERSION, etc.

3. **ThreatWorker - "De Waakhond"**
   - Detecteert risico's en gevaren
   - Output: `DispositionEnvelope(PUBLISH)` met `ThreatSignalDTO` (Systeem DTO)
   - 5 Sub-types: PORTFOLIO_RISK, MARKET_RISK, SYSTEM_HEALTH, etc.

4. **PlanningWorker - "De Strateeg"**
   - Transformeert signalen naar concrete plannen
   - Output: Intermediair: `set_result_dto()` met plan DTOs, Finaal: `DispositionEnvelope(PUBLISH)` met `RoutedTradePlanDTO`
   - 4 Sub-types: ENTRY_PLANNING, EXIT_PLANNING, SIZE_PLANNING, ORDER_ROUTING

5. **StrategyPlanner - "De Beslisser"**
   - Produceert StrategyDirective op basis van triggers (SWOT, tick, threat, schedule)
   - Output: `DispositionEnvelope(PUBLISH)` met `StrategyDirective`
   - **1-op-1 relatie**: Elke strategie heeft precies 1 StrategyPlanner
   - **Geen enforced subtypes** - categorisatie voor documentatie only:
     - Entry Strategies (scope: NEW_TRADE, trigger: SWOT/Opportunity)
     - Position Management (scope: MODIFY_EXISTING, trigger: tick)
     - Risk Control (scope: CLOSE_EXISTING, trigger: threat)
     - Scheduled Operations (scope: NEW_TRADE, trigger: schedule)
   - Examples: SWOTMomentumPlanner, TrailingStopPlanner, EmergencyExitPlanner, DCAPlanner

**Note**: V2 ExecutionWorker category is VERWIJDERD. TRADE_INITIATION is platform orchestration (ExecutionHandler + EventAdapter), andere subtypes zijn StrategyPlanners.

### 3.2. Point-in-Time Data Model (KRITIEK!)

**Concept:** Alle data-uitwisseling is gebaseerd op één specifiek moment (tick), NIET op een groeiende dataset.

#### 3.2.1. De Twee Communicatiepaden

1. **TickCache (Sync, Flow-Data)**
   - Via `ITradingContextProvider`
   - Voor directe worker-naar-worker data doorgifte
   - Bevat **alleen plugin-specifieke DTOs**
   - Levensduur: één tick/flow
   - Worker gebruikt: `self.context_provider.set_result_dto(self, my_dto)`

2. **EventBus (Async, Signals)**
   - Via `DispositionEnvelope` retourneren
   - Voor externe signalen, alerts, resultaten
   - Bevat **alleen standaard Systeem DTOs**
   - Worker retourneert: `DispositionEnvelope(PUBLISH, event_name="...", event_payload=system_dto)`

#### 3.2.2. Worker Data Toegang Pattern

```python
class MyWorker(StandardWorker):
    # Providers worden geïnjecteerd door WorkerFactory
    context_provider: ITradingContextProvider
    ohlcv_provider: IOhlcvProvider
    state_provider: Optional[IStateProvider]
    
    def process(self) -> DispositionEnvelope:
        # 1. Haal basis context
        base_ctx = self.context_provider.get_base_context()  # timestamp, price
        
        # 2. Haal benodigde DTOs uit TickCache
        required_dtos = self.context_provider.get_required_dtos(self)
        ema_dto = required_dtos[EMAOutputDTO]  # Type-safe lookup
        
        # 3. Haal platform data
        df = self.ohlcv_provider.get_window(base_ctx.timestamp, lookback=100)
        
        # 4. Bereken
        result = my_calculation(ema_dto, df)
        
        # 5A. Voor flow: Plaats in TickCache
        self.context_provider.set_result_dto(self, MyOutputDTO(value=result))
        return DispositionEnvelope(disposition="CONTINUE")
        
        # 5B. OF voor signaal: Publiceer event
        return DispositionEnvelope(
            disposition="PUBLISH",
            event_name="SIGNAL_GENERATED",
            event_payload=OpportunitySignalDTO(...)  # Systeem DTO!
        )
```

#### 3.2.3. DTO Deling via Enrollment Exposure

**Plugin-specifieke DTOs** worden gedeeld via centraal register:

1. **Definitie:** Developer definieert DTO in plugin's `dtos/` folder
2. **Manifest:** Plugin declareert `produces_dtos` in manifest.yaml
3. **Enrollment:** Platform kopieert naar `backend/dto_reg/<vendor>/<plugin>/<version>/`
4. **Consumptie:** Andere plugins importeren van centrale locatie:
   ```python
   from backend.dto_reg.s1mple.ema_detector.v1_0_0.ema_output_dto import EMAOutputDTO
   ```

### 3.3. DispositionEnvelope (Worker → Adapter Contract)

**KRITIEK:** Workers retourneren DispositionEnvelope om intentie aan te geven:

```python
@dataclass
class DispositionEnvelope:
    disposition: Literal["CONTINUE", "PUBLISH", "STOP"]
    event_name: Optional[str] = None  # Bij PUBLISH
    event_payload: Optional[BaseModel] = None  # Bij PUBLISH (Systeem DTO!)
```

**Adapter gedrag:**
- **CONTINUE:** Trigger volgende worker(s) volgens wiring_map, publiceert intern system event
- **PUBLISH:** Valideer & publiceer custom event op EventBus (payload MOET Systeem DTO zijn)
- **STOP:** Publiceer flow-stop event voor cleanup

### 3.4. Platform "Toolbox" (Capabilities)

Workers vragen capabilities aan via `manifest.yaml`:

```yaml
capabilities:
  # Standaard (altijd beschikbaar)
  context_access:
    enabled: true  # ITradingContextProvider (NIET configureerbaar)
  
  # Opt-in capabilities
  ohlcv_window:
    enabled: true  # IOhlcvProvider
  multi_timeframe:
    enabled: true  # IMtfProvider
  state_persistence:
    enabled: true  # IStateProvider
  market_depth:
    enabled: true  # IDepthProvider
  ledger_state:
    enabled: true  # ILedgerProvider
  journaling:
    enabled: true  # IJournalWriter
```

WorkerFactory injecteert gevraagde providers bij instantiatie.

## 4. Plugin Anatomie

### 4.1. Fundamentele Mappenstructuur

Elke plugin is een opzichzelfstaande Python package:

```
plugins/[category]/[plugin_naam]/
├── manifest.yaml           # ID-kaart + Capability declaraties
├── worker.py               # De businesslogica
├── schema.py               # Pydantic config model
├── context_schema.py       # Visualisatie contract (opt.)
├── dtos/                   # Plugin-specifieke DTOs (opt.)
│   ├── __init__.py
│   └── my_output_dto.py
└── test/
    └── test_worker.py      # Verplichte unit tests
```

**Wanneer `dtos/` map nodig is:**
- ALLEEN als plugin DTOs produceert voor TickCache
- NIET nodig als plugin alleen Systeem DTOs publiceert (OpportunitySignalDTO, etc.)
- 95% van plugins heeft GEEN dtos/ folder

### 4.2. manifest.yaml Structuur (KRITIEK!)

```yaml
identification:
  name: "my_worker"
  display_name: "My Worker"
  type: "context_worker"  # OF opportunity_worker, threat_worker, etc.
  subtype: "indicator_calculation"  # Zie taxonomie
  version: "1.0.0"
  description: "Beschrijving"
  author: "Name"

dependencies:
  # OUDE AANPAK (ACHTERHAALD - voor DataFrame kolommen):
  # requires: ['close', 'volume']
  # provides: ['ema_20']
  
  # NIEUWE AANPAK (Point-in-Time DTOs):
  requires_dtos:
    - source: "backend.dto_reg.s1mple.another_worker.v1_0_0.input_dto"
      dto_class: "InputDTO"
  
  produces_dtos:
    - dto_class: "MyOutputDTO"
      local_path: "dtos/my_output_dto.py"

capabilities:
  # Standaard capability (ALTIJD aanwezig, NIET configureerbaar)
  context_access:
    enabled: true  # ITradingContextProvider
  
  # Opt-in capabilities
  ohlcv_window:
    enabled: true
  
  state_persistence:
    enabled: true
    scope: "strategy"  # OF "global"
  
  # Event capability (voor EventDrivenWorker)
  events:
    enabled: true
    publishes:
      - event_name: "MY_CUSTOM_EVENT"
        description: "Beschrijving"
    wirings:
      - listens_to: "SOME_TRIGGER_EVENT"
        invokes:
          method: "on_trigger"
          requires_payload: true
```

### 4.3. Worker Implementation Patterns

#### 4.3.1. StandardWorker (90% van plugins)

```python
# plugins/context_workers/ema_detector/worker.py
from backend.core.base_worker import StandardWorker
from backend.shared_dtos.disposition_envelope import DispositionEnvelope
from .dtos.ema_output_dto import EMAOutputDTO

class EMADetector(StandardWorker):
    """Berekent EMA en plaatst in TickCache."""
    
    def process(self) -> DispositionEnvelope:
        # 1. Haal data
        base_ctx = self.context_provider.get_base_context()
        df = self.ohlcv_provider.get_window(base_ctx.timestamp, lookback=100)
        
        # 2. Bereken
        ema_value = df['close'].ewm(span=20).mean().iloc[-1]
        
        # 3. Produceer DTO voor TickCache
        output_dto = EMAOutputDTO(ema_20=ema_value, timestamp=base_ctx.timestamp)
        self.context_provider.set_result_dto(self, output_dto)
        
        # 4. Signaleer "ga door"
        return DispositionEnvelope(disposition="CONTINUE")
```

#### 4.3.2. EventDrivenWorker (Voor complexe workflows)

```python
# plugins/execution_workers/dca_executor/worker.py
from backend.core.base_worker import EventDrivenWorker
from backend.shared_dtos.disposition_envelope import DispositionEnvelope

class DCAExecutor(EventDrivenWorker):
    """Voert wekelijkse DCA uit, getriggerd door scheduler."""
    
    # Event handler (methode naam komt uit manifest.wirings)
    def on_weekly_tick(self, payload: dict) -> DispositionEnvelope:
        # 1. Check condities
        portfolio = self.ledger_provider.get_current_state()
        
        # 2. Voer uit
        if portfolio.cash_available > 100:
            self.execution_provider.place_order(...)
        
        # 3. Optioneel publiceren
        return DispositionEnvelope(
            disposition="PUBLISH",
            event_name="DCA_ORDER_PLACED",
            event_payload=TradeExecutedDTO(...)
        )
```

### 4.4. CAPABILITIES (Manifest-Gedreven Model)

1. **STANDAARD CAPABILITIE**:
   - ITradingContextProvider
2. **CAPABILITIES** (aangevraagd in manifest):
   - `state_persistence`: Krijgt `self.state_provider`
   - `events`: Krijgt event wiring via adapter
   - `journaling`: Krijgt `self.journal_writer`
   - etc.

WorkerFactory leest manifest, valideert contract, injecteert dependencies.

## 5. Event-Driven Architectuur & Wiring

### 5.1. EventBus als Pure N-N Broadcast

**KRITIEK:** EventBus is een pure broadcast-bus, GEEN point-to-point router.

**Twee types events:**
1. **Systeem Events** (intern, flow control)
   - Gegenereerd door adapters voor CONTINUE disposition
   - Unieke namen: `_worker_A_output_uuid`, `_tick_flow_start_uuid`
   - **Bevatten Systeem DTO payloads** voor flow continuïteit

2. **Custom Events** (publiek, signals)
   - Gedeclareerd in manifest.publishes
   - Gepubliceerd via PUBLISH disposition
   - **Bevatten GEEN payload** (data zit in TickCache)

### 5.2. EventAdapter (De Uitvoerder)

**Elke component** (worker of singleton) krijgt zijn eigen EventAdapter.

**Adapter verantwoordelijkheden:**
1. **Luisteren:** Subscribed op events uit wiring_spec
2. **Aanroepen:** Roept component methode aan met payload
3. **Interpreteren:** Verwerkt DispositionEnvelope
4. **Publiceren:** Voert publicatie-instructies uit:
   - **CONTINUE:** Publiceert intern systeem event (met Systeem DTO)
   - **PUBLISH:** Publiceert custom event (ZONDER payload)
   - **STOP:** Publiceert flow-stop event

**Adapter configuratie** (via EventWiringFactory uit BuildSpecs):
```python
adapter_config = {
    'component_ref': worker_instance,
    'eventbus_ref': eventbus,
    'subscriptions': ['EVENT_A', 'EVENT_B'],
    'handler_mapping': {
        'EVENT_A': 'process',
        'EVENT_B': 'on_custom_event'
    },
    'publication_config': {
        'system_events': {
            'CONTINUE': {
                'event_name': '_worker_X_output_abc123',
                'payload_dto_type': 'SomeSystemDTO'
            }
        },
        'custom_events': ['MY_CUSTOM_EVENT'],
        'stop_event': '_flow_stop_abc123'
    }
}
```

### 5.3. Wiring Configuration (UI-Gegenereerd)

**Base Wiring Template** (`base_wiring.yaml`):
```yaml
base_wiring_id: "standard_trading_flow_v1"
wiring_rules:
  - wiring_id: "ctx_to_opp"
    source:
      component_id: "ContextWorker"  # Categorie
      event_name: "ContextOutput"
      event_type: "SystemEvent"
    target:
      component_id: "OpportunityWorker"
      handler_method: "process"
```

**Strategy Wiring Map** (`strategy_wiring_map.yaml`, UI-gegenereerd):
```yaml
strategy_wiring_id: "my_btc_strategy_wiring"
wiring_rules:
  # Concrete instanties, gegenereerd door UI
  - wiring_id: "ema_to_cross_detector"
    source:
      component_id: "ema_detector_instance_1"  # Specifiek!
      event_name: "_ema_output_uuid123"
      event_type: "SystemEvent"
    target:
      component_id: "ema_cross_detector_instance_1"
      handler_method: "process"
  
  # Custom events uit manifesten
  - wiring_id: "news_to_halt"
    source:
      component_id: "news_monitor_instance_1"
      event_name: "EMERGENCY_HALT"
      event_type: "CustomEvent"
    target:
      component_id: "emergency_executor_instance_1"
      handler_method: "on_emergency"
```

### 5.4. TickCacheManager (Flow Initiator)

**Singleton** die flow lifecycle beheert:

1. **Luistert naar initiërende events:**
   - `RAW_TICK` (van ExecutionEnvironment)
   - `SCHEDULED_TASK:weekly_dca` (van Scheduler)
   - `NEWS_RECEIVED` (van external adapter)

2. **Bij ontvangst:**
   - Creëert nieuwe TickCache: `cache = {}`
   - Configureert ITradingContextProvider: `provider.start_new_tick(cache, timestamp, price)`
   - Publiceert `TICK_FLOW_START` event

3. **Workers starten:**
   - Eerste workers in chain luisteren naar `TICK_FLOW_START`
   - Gebruiken ITradingContextProvider voor data access
   - Flow verloopt via wiring_map

4. **Cleanup:**
   - Luistert naar `TICK_FLOW_COMPLETE` of timeout
   - Roept `release_cache(cache)` aan

## 6. Codeerstandaarden & Best Practices

### 6.1. Code Stijl

* **PEP 8 Compliant:** Alle Python-code volgt strict PEP 8
* **Volledige Type Hinting:** Verplicht voor alle functies en methodes
* **Engels:** Alle commentaar, docstrings en variabelnamen in Engels
* **Google Style Docstrings:** Voor alle publieke functies en klassen

### 6.2. Contract-Gedreven Ontwikkeling

**KRITIEK PRINCIPE:** Alle data-uitwisseling via strikte Pydantic contracts.

```python
# ✅ GOED - Expliciete DTO
from pydantic import BaseModel

class MyOutputDTO(BaseModel):
    value: float
    confidence: float
    timestamp: datetime

def my_function() -> MyOutputDTO:
    return MyOutputDTO(value=1.23, confidence=0.85, timestamp=datetime.now())

# ❌ FOUT - Primitieve types of dicts
def bad_function() -> dict:
    return {'value': 1.23}  # Geen type safety!
```

### 6.3. File Header Convention

**VERPLICHT:** Alle Python modules beginnen met een standaard header die de
architecturale positie documenteert.

**Template:**
```python
# {relatief_pad_vanaf_project_root}
"""
{Korte titel - Functionaliteit}.

{Uitgebreide beschrijving van wat deze module doet}

@layer: {Backend/Tests/Service/Frontend}
@dependencies: [{lijst, van, dependencies}]
@responsibilities:
    - {Verantwoordelijkheid 1}
    - {Verantwoordelijkheid 2}
"""
```

**Voorbeelden:**

```python
# backend/dtos/shared/disposition_envelope.py
"""
Disposition Envelope - Worker Output Flow Control Contract.

This module defines the DispositionEnvelope, the standardized return
type for all workers to communicate their execution outcome and
next-step intentions to the EventAdapter.

@layer: Backend (DTOs)
@dependencies: [pydantic, typing, re]
@responsibilities:
    - Define worker output contract (CONTINUE, PUBLISH, STOP)
    - Enable event-driven flow control without coupling workers to EventBus
    - Validate event publication payloads at type level
"""
```

```python
# backend/utils/id_generators.py
"""
Typed ID generation utilities.

Provides standardized ID generation with type prefixes for causal
traceability across the trading system.

@layer: Backend (Utils)
@dependencies: [uuid]
@responsibilities:
    - Generate typed IDs with consistent prefixes
    - Extract ID type from typed ID string
    - Maintain ID format consistency
"""
```

```python
# tests/unit/dtos/shared/test_disposition_envelope.py
"""
Unit tests for DispositionEnvelope DTO.

Tests the worker output flow control contract according to TDD principles.

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, backend.dtos.shared.disposition_envelope]
"""
```

**Waarom deze conventie:**
- Snelle navigatie: direct zien waar je bent in de architectuur
- Documentatie: expliciete dependencies en verantwoordelijkheden
- Consistentie: alle modules volgen hetzelfde patroon
- IDE-vriendelijk: file path als eerste regel helpt met context

### 6.4. Logging & Traceability

* **Gestructureerd Logging:** Primair `run.log.json` voor analyse
* **Causale Traceerbaarheid:** Gebruik getypeerde IDs:
  - `TradeID` - Ankerpunt van trade
  - `OpportunityID` - Waarom geopend?
  - `ThreatID` - Waarom gesloten?
  - `ScheduledID` - Waarom nu?
* **IJournalWriter:** Voor significante events, NIET voor flow-data

### 6.5. Code Quality Standards

**VERPLICHT voor alle code:**

* **Max lijnlengte:** 100 karakters
* **Geen trailing whitespace:** Alle regels eindigen zonder spaties/tabs
* **Pylance/Lint clean:** Alle code moet zonder warnings compileren
* **Compacte docstrings:** Method docstrings kort en to-the-point
* **Uitgebreide module docs:** Gedetailleerde uitleg in module header

**Voorbeeld:**
```python
# backend/dtos/strategy/opportunity_signal.py
"""
OpportunitySignal - Trading opportunity detection output.

This module defines the OpportunitySignal DTO, which represents the
output of OpportunityWorkers when a trading opportunity is detected.
It forms the first link in the causal traceability chain.

[... uitgebreide module documentatie ...]

@layer: Backend (DTOs)
@dependencies: [pydantic, datetime, backend.utils.id_generators]
@responsibilities:
    - Define opportunity detection output contract
    - Enforce typed ID prefix validation
    - Ensure UTC timestamp consistency
"""

class OpportunitySignal(BaseModel):
    """System DTO for opportunity detection output."""  # ← Compact!

    @field_validator('timestamp')
    @classmethod
    def ensure_utc_timezone(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware and in UTC."""  # ← Compact!
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)
```

### 6.6. Strikt Validatie & Test Regime (KRITIEK!)

**PRINCIPE:** Alle code moet voldoen aan strikte kwaliteitsnormen VOORDAT het als "compleet" wordt beschouwd.

#### 6.6.1. Verplichte Pre-Commit Validatie

**Voor elke nieuwe module of wijziging MOET je:**

1. **Pylint validatie voor code kwaliteit:**
   ```powershell
   python -m pylint <file_path> --disable=all --enable=trailing-whitespace,superfluous-parens
   ```
   - **Target:** 10.00/10 score
   - **Focus:** Trailing whitespace, onnodige haakjes
   - **Fix automatisch:** `(Get-Content <file>) | ForEach-Object { $_.TrimEnd() } | Set-Content <file>`

2. **Pylint validatie voor imports:**
   ```powershell
   python -m pylint <file_path> --disable=all --enable=import-outside-toplevel
   ```
   - **Target:** 10.00/10 score
   - **Fix:** Verplaats alle imports naar top-level (buiten functies/methods)

3. **VS Code Problems verificatie:**
   - Open VS Code Problems panel (Ctrl+Shift+M)
   - **Target:** 0 ECHTE errors
   - **ACCEPTABEL (kan NIET onderdrukt worden):**
     - Pydantic FieldInfo warnings: "Instance of 'FieldInfo' has no 'X' member"
     - Deze zijn runtime-correct maar Pylance kan Pydantic type narrowing niet begrijpen
     - **Bewijs:** Tests slagen 100%, runtime gedrag correct
     - **Reden:** Pydantic gebruikt dynamische FieldInfo descriptors die Pylance niet kan infereren
     - **Status:** Gedocumenteerd in agent.md sectie 6.6.5 "Bekende acceptable warnings"
   - **Workspace settings zijn aanwezig maar ineffectief** (Pylance limitation):
     ```json
     {
       "python.analysis.diagnosticSeverityOverrides": {
         "reportAttributeAccessIssue": "none",  // Ineffectief voor FieldInfo
         "reportCallIssue": "none",
         "reportArgumentType": "none"
       }
     }
     ```
   - **VERPLICHT OP TE LOSSEN:**
     - Import errors ("could not be resolved")
     - Echte type errors (verkeerde types meegegeven)
     - Undefined variables
     - Missing required parameters (buiten Pydantic Field() defaults)

4. **Test suite verificatie:**
   ```powershell
   pytest tests/unit/ -q --tb=line
   ```
   - **Target:** 100% tests passing
   - **NO regression:** Bestaande tests blijven groen

#### 6.6.2. Test-Driven Development Discipline with Git Integration

**VERPLICHTE TDD + GIT WORKFLOW:**

**0. Feature Branch Setup:**
   ```powershell
   # Create feature branch from main
   git checkout -b feature/size-plan-dto
   ```

**1. Red Phase:** Schrijf failing tests EERST
   ```python
   def test_new_feature():
       """Test that new feature works correctly."""
       result = my_new_function(input_data)
       assert result == expected_output  # FAILS - function not implemented
   ```
   ```powershell
   # Commit failing tests (documents intent)
   git add tests/unit/dtos/strategy/test_size_plan.py
   git commit -m "test: add failing tests for SizePlan DTO

   - Test creation with valid fields
   - Test validation rules
   - Test edge cases
   
   Status: RED - tests fail (implementation pending)"
   ```

**2. Green Phase:** Implementeer minimale code om test groen te maken
   ```python
   def my_new_function(data):
       """Implement minimal working solution."""
       return process(data)  # Test now PASSES
   ```
   ```powershell
   # Commit working implementation
   git add backend/dtos/strategy/size_plan.py
   git commit -m "feat: implement SizePlan DTO

   - Add quantity, risk_amount, position_value fields
   - Add validation for positive values
   - All tests passing (20/20)
   
   Status: GREEN"
   ```

**3. Refactor Phase:** Verbeter code terwijl tests groen blijven
   - Trailing whitespace cleanup
   - Type hints toevoegen
   - Docstrings verbeteren
   - **Verify:** Tests blijven 100% groen
   ```powershell
   # Commit refactoring separately
   git add backend/dtos/strategy/size_plan.py tests/unit/dtos/strategy/test_size_plan.py
   git commit -m "refactor: improve SizePlan DTO code quality

   - Add comprehensive docstrings
   - Fix line length violations
   - Add type hints for all fields
   - Clean up whitespace
   
   Quality gates: All 10/10
   Status: GREEN (tests still 20/20)"
   ```

**4. Quality Gates:** Run complete checklist
   ```powershell
   # Run all quality checks (see section 6.6.1)
   # If all pass, commit quality metrics update
   git add agent.md
   git commit -m "docs: update Quality Metrics Dashboard for SizePlan

   - Added SizePlan row: 10/10 all gates
   - Test coverage: 20/20 passing"
   ```

**5. Merge to Main:**
   ```powershell
   # Switch back to main
   git checkout main
   
   # Merge feature (squash or regular based on preference)
   git merge feature/size-plan-dto
   
   # Push to GitHub
   git push origin main
   
   # Delete feature branch
   git branch -d feature/size-plan-dto
   ```

**COMMIT MESSAGE CONVENTIONS:**
- `test:` - Tests only (Red phase)
- `feat:` - New feature implementation (Green phase)
- `refactor:` - Code quality improvements (Refactor phase)
- `docs:` - Documentation updates (agent.md, README)
- `fix:` - Bug fixes
- `chore:` - Build/tooling changes

**BRANCHING STRATEGY:**
- `main` - Always stable, all tests passing, all quality gates met
- `feature/*` - Development branches for new DTOs/features
- Commit early, commit often on feature branches
- Only merge to main when ALL quality gates pass

#### 6.6.3. DTO Implementation Checklist

**Voor elke nieuwe DTO MOET je:**

1. **Tests EERST schrijven** (20-30 tests typisch):
   - Creation tests (valid instantiation)
   - Field validation tests (ranges, formats, types)
   - Edge cases (boundaries, None handling)
   - Immutability tests (frozen models)
   - Cross-field validation (XOR, dependencies)

2. **Implementation volgt tests:**
   - Start met failing tests (Red)
   - Implementeer validators één voor één (Green)
   - Refactor voor leesbaarheid (Refactor)

3. **Quality gates VOOR merge:**
   ```powershell
   # Gate 1: Pylint whitespace check
   python -m pylint backend/dtos/strategy/my_dto.py --disable=all --enable=trailing-whitespace,superfluous-parens
   # Expected: 10.00/10

   # Gate 2: Pylint import check
   python -m pylint backend/dtos/strategy/my_dto.py --disable=all --enable=import-outside-toplevel
   # Expected: 10.00/10

   # Gate 3: Tests still passing
   pytest tests/unit/dtos/strategy/test_my_dto.py -q --tb=line
   # Expected: All tests passing

   # Gate 4: Type checking (DTO only)
   python -m mypy backend/dtos/strategy/my_dto.py --strict --no-error-summary
   # Expected: 0 errors (tests may have Pydantic false positives - see section 6.6.5)

   # Gate 5: Line length check
   python -m pylint backend/dtos/strategy/my_dto.py --disable=all --enable=line-too-long --max-line-length=100
   python -m pylint tests/unit/dtos/strategy/test_my_dto.py --disable=all --enable=line-too-long --max-line-length=100
   # Expected: 10.00/10 for both files
   ```

4. **Post-implementation cleanup workflow:**
   ```powershell
   # Step 1: Auto-fix trailing whitespace (DTO + tests)
   (Get-Content backend/dtos/strategy/my_dto.py) | ForEach-Object { $_.TrimEnd() } | Set-Content backend/dtos/strategy/my_dto.py
   (Get-Content tests/unit/dtos/strategy/test_my_dto.py) | ForEach-Object { $_.TrimEnd() } | Set-Content tests/unit/dtos/strategy/test_my_dto.py

   # Step 2: Run all 5 gates for DTO
   python -m pylint backend/dtos/strategy/my_dto.py --disable=all --enable=trailing-whitespace,superfluous-parens
   python -m pylint backend/dtos/strategy/my_dto.py --disable=all --enable=import-outside-toplevel
   python -m pylint backend/dtos/strategy/my_dto.py --disable=all --enable=line-too-long --max-line-length=100
   python -m mypy backend/dtos/strategy/my_dto.py --strict --no-error-summary

   # Step 3: Run all 5 gates for tests
   python -m pylint tests/unit/dtos/strategy/test_my_dto.py --disable=all --enable=trailing-whitespace,superfluous-parens
   python -m pylint tests/unit/dtos/strategy/test_my_dto.py --disable=all --enable=import-outside-toplevel
   python -m pylint tests/unit/dtos/strategy/test_my_dto.py --disable=all --enable=line-too-long --max-line-length=100
   pytest tests/unit/dtos/strategy/test_my_dto.py -q --tb=line

   # Step 4: Verify 0 problems in VS Code (except accepted Pydantic warnings - see 6.6.5)
   # Check Problems panel - only acceptable warnings should remain
   ```

#### 6.6.4. Code Review Standards

**ELKE pull request/commit MOET:**

- ✅ Alle pylint checks op 10.00/10
- ✅ Alle tests groen (geen skips)
- ✅ Type hints compleet
- ✅ Docstrings aanwezig (module + public methods)
- ✅ Geen trailing whitespace
- ✅ Imports op top-level (NOOIT in functies/methods)
- ✅ Max line length 100 chars (gebruik variabelen om lange asserts te splitsen)
- ✅ Import grouping volgens Chapter 10 (3 groepen met comments)

**REJECT als:**

- ❌ Pylint score < 10.00 voor whitespace/parens/imports
- ❌ Failing tests
- ❌ Missing type hints
- ❌ Imports inside functions (altijd top-level!)
- ❌ Code zonder tests (bij nieuwe features)
- ❌ Lines > 100 characters
- ❌ Import grouping violations

#### 6.6.5. Automated Quality Tools

**Gebruik PowerShell helpers:**

```powershell
# Cleanup trailing whitespace in bulk
Get-ChildItem -Recurse -Filter "*.py" | ForEach-Object {
    (Get-Content $_.FullName) | ForEach-Object { $_.TrimEnd() } | Set-Content $_.FullName
}

# Check all modified files for common issues
git diff --name-only | Where-Object { $_ -like "*.py" } | ForEach-Object {
    python -m pylint $_ --disable=all --enable=trailing-whitespace,superfluous-parens,import-outside-toplevel,line-too-long --max-line-length=100
}

# Check specific quality rules
python -m pylint <file> --disable=all --enable=trailing-whitespace
python -m pylint <file> --disable=all --enable=import-outside-toplevel
python -m pylint <file> --disable=all --enable=line-too-long --max-line-length=100
```

**VS Code settings.json (aanbevolen):**

```json
{
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true,
    "editor.rulers": [100],
    "python.linting.pylintEnabled": true,
    "python.linting.enabled": true,
    "python.analysis.typeCheckingMode": "basic"
}
```

**pyrightconfig.json (type checking):**

Project heeft `pyrightconfig.json` voor consistente type checking:
- Python 3.13 target
- Basic type checking mode (pragmatisch, niet strict)
- `reportUnknownMemberType: false` → Pydantic generics false positives
- `reportUnknownVariableType: false` → DTO field inference issues
- Wel enabled: unused imports, duplicate imports, undefined variables

**Bekende acceptable warnings:**

1. **Pydantic `Field()` met generics:** `list[ContextFactor]` → "partially unknown"
   - **Fix:** `# type: ignore[valid-type]` inline comment in DTO

2. **Pydantic FieldInfo in tests:** `assessment.field.method()` triggers "no member 'method'"
   - **Fix:** Intermediate variabele: `value = str(assessment.field)` then assert on `value`
   - **Pattern:**
     ```python
     # Instead of: assert signal.initiator_id.startswith("TCK_")
     # Use:
     initiator_id = str(signal.initiator_id)
     assert initiator_id.startswith("TCK_")
     ```
   - **Exception:** Datetime attributes like `.tzinfo` CANNOT be suppressed
     - Pylance ignores ALL inline suppressions: `# type: ignore`, `# pyright: ignore`
     - Global pyrightconfig suppressions (reportAttributeAccessIssue: false) also ineffective
     - Runtime werkt perfect, tests slagen
     - **Workaround:** Add explanatory comment boven de regel:
       ```python
       # Pylance limitation: FieldInfo doesn't narrow to datetime after isinstance()
       # Runtime works perfectly. See agent.md section 6.6.5 "Bekende acceptable warnings #2"
       tzinfo = created_at.tzinfo  # type: ignore[attr-defined]
       assert tzinfo is not None
       ```
     - **Status:** ACCEPTED - 1 warning per DTO acceptabel voor datetime.tzinfo checks

3. **Pydantic optional fields:** `Field(None, ...)` → Pylance "missing parameter" warnings
   - **Root cause:** Pylance doesn't recognize `Field(None, default=None)` pattern for optionality
   - **Evidence:** All tests pass, runtime behavior correct
   - **Global suppressie:** pyrightconfig.json heeft deze settings:
     ```json
     {
       "reportCallIssue": false,
       "reportArgumentType": false,
       "reportAttributeAccessIssue": false
     }
     ```
   - **Fix in test files:** Add header comment:
     ```python
     """
     Unit tests for MyDTO.
     """
     # pyright: reportCallIssue=false
     # Suppress Pydantic FieldInfo false positives for optional fields
     ```
   - **Best practice:** Add explanatory comment in test file explaining Pydantic limitation
   - **Status:** Systematically suppressed globally - 0 warnings verwacht voor "missing arguments"

4. **Line length voor comments:** Comments met inline code kunnen >100 chars zijn
   - **Fix:** Split op meerdere regels of verkort comment
   - **Pattern:**
     ```python
     # Too long (107 chars):
     assert plan.limit_price > plan.reference_price  # type: ignore[operator]  # Selling above reference

     # Fixed (split comment):
     # Selling above reference price
     assert plan.limit_price > plan.reference_price  # type: ignore[operator]
     ```

**DOEL: 0 ACTIONABLE PROBLEMS**

Na volledige quality workflow moet VS Code Problems panel ALLEEN tonen:
- ✅ 0-1 warnings voor datetime.tzinfo checks (ACCEPTED per DTO)
- ✅ 0 warnings voor "missing arguments" (globally suppressed)
- ✅ 0 warnings voor trailing whitespace
- ✅ 0 warnings voor line length
- ✅ 0 warnings voor imports

**Als je meer warnings ziet:** Check de 4-step cleanup workflow hierboven.

#### 6.6.6. Quality Metrics Dashboard

**Track per module:**

| Module | Pylint Score | Test Coverage | Line Length | Pylance Warnings | Status |
|--------|--------------|---------------|-------------|------------------|--------|
| aggregated_context_assessment.py | 10.00/10 | 14/14 ✅ | 10.00/10 | 0 | ✅ |
| causality.py | 10.00/10 | 25/25 ✅ | 10.00/10 | 0 | ✅ |
| context_factor.py | 10.00/10 | 28/28 ✅ | 10.00/10 | 0 | ✅ |
| context_factors.py | 10.00/10 | 21/21 ✅ | 10.00/10 | 0 | ✅ |
| enums.py | 10.00/10 | 13/13 ✅ | 10.00/10 | 0 | ✅ |
| entry_plan.py | 10.00/10 | 22/22 ✅ | 10.00/10 | 1 (datetime.tzinfo - accepted) | ✅ |
| id_generators.py | 10.00/10 | 37/37 ✅ | 10.00/10 | 0 | ✅ |
| opportunity_signal.py | 10.00/10 | 26/26 ✅ | 10.00/10 | 0 | ✅ |
| strategy_directive.py | 10.00/10 | 17/17 ✅ | 10.00/10 | 1 (FieldInfo - accepted) | ✅ |
| threat_signal.py | 10.00/10 | 22/22 ✅ | 10.00/10 | 0 | ✅ |

**Acceptance criteria:** 
- ✅ ALLE modules: Pylint 10.00/10 (whitespace, imports, line length)
- ✅ ALLE modules: 100% tests passing
- ✅ ALLE modules: 0 actionable Pylance warnings
  - **ACCEPTED:** Pydantic FieldInfo warnings (Pylance limitation, runtime correct)
  - **ACCEPTED:** datetime.tzinfo warnings (Pylance type narrowing limitation)

**Quality workflow checklist per nieuwe module:**
1. ✅ Create feature branch: `git checkout -b feature/dto-name`
2. ✅ Tests geschreven (min 20) + commit (RED phase)
3. ✅ DTO geïmplementeerd (Pydantic v2) + commit (GREEN phase)
4. ✅ Gate 1: Whitespace (10.00/10)
5. ✅ Gate 2: Imports (10.00/10)
6. ✅ Gate 3: Tests passing (100%)
7. ✅ Gate 4: Type checking DTO (0 errors)
8. ✅ Gate 5: Line length (10.00/10)
9. ✅ Gate 6: Documentation quality (file header + class docstring)
10. ✅ VS Code Problems: Only accepted warnings (FieldInfo/datetime.tzinfo)
11. ✅ Refactor + commit quality improvements
12. ✅ Update Quality Metrics Dashboard (sectie 6.6.6) + commit
13. ✅ Merge to main: `git checkout main && git merge feature/dto-name`
14. ✅ Push to GitHub: `git push origin main`

#### 6.6.7. Quick Reference: Complete Quality Workflow with Git

**COPY-PASTE COMMANDO'S VOOR NIEUWE DTO MODULE:**

```powershell
# === STAP 0: Create Feature Branch ===
git checkout -b feature/size-plan-dto

# === STAP 1: RED Phase - Write Failing Tests ===
# Create tests/unit/dtos/strategy/test_size_plan.py with 20+ tests
git add tests/unit/dtos/strategy/test_size_plan.py
git commit -m "test: add failing tests for SizePlan DTO

- Test creation with valid fields
- Test validation rules  
- Test edge cases

Status: RED - tests fail (implementation pending)"

# === STAP 2: GREEN Phase - Implement DTO ===
# Create backend/dtos/strategy/size_plan.py
git add backend/dtos/strategy/size_plan.py
git commit -m "feat: implement SizePlan DTO

- Add quantity, risk_amount, position_value fields
- Add validation for positive values
- All tests passing (20/20)

Status: GREEN"

# === STAP 3: REFACTOR Phase - Quality Gates ===

# Auto-cleanup whitespace
(Get-Content backend/dtos/strategy/size_plan.py) | ForEach-Object { $_.TrimEnd() } | Set-Content backend/dtos/strategy/size_plan.py
(Get-Content tests/unit/dtos/strategy/test_size_plan.py) | ForEach-Object { $_.TrimEnd() } | Set-Content tests/unit/dtos/strategy/test_size_plan.py

# DTO Quality Gates (5 checks)
python -m pylint backend/dtos/strategy/size_plan.py --disable=all --enable=trailing-whitespace,superfluous-parens
python -m pylint backend/dtos/strategy/size_plan.py --disable=all --enable=import-outside-toplevel
python -m pylint backend/dtos/strategy/size_plan.py --disable=all --enable=line-too-long --max-line-length=100
python -m mypy backend/dtos/strategy/size_plan.py --strict --no-error-summary
pytest tests/unit/dtos/strategy/test_size_plan.py -q --tb=line

# Test Quality Gates (3 checks)
python -m pylint tests/unit/dtos/strategy/test_size_plan.py --disable=all --enable=trailing-whitespace,superfluous-parens
python -m pylint tests/unit/dtos/strategy/test_size_plan.py --disable=all --enable=import-outside-toplevel
python -m pylint tests/unit/dtos/strategy/test_size_plan.py --disable=all --enable=line-too-long --max-line-length=100

# Commit refactoring
git add backend/dtos/strategy/size_plan.py tests/unit/dtos/strategy/test_size_plan.py
git commit -m "refactor: improve SizePlan DTO code quality

- Add comprehensive docstrings
- Fix line length violations
- Clean up whitespace

Quality gates: All 10/10
Status: GREEN (tests still 20/20)"

# === STAP 4: Documentation Quality Check ===
# Manually verify file header and class docstring

# === STAP 5: Update Quality Metrics Dashboard ===
# Add row to agent.md section 6.6.6
git add agent.md
git commit -m "docs: update Quality Metrics Dashboard for SizePlan

- Added SizePlan row: 10/10 all gates
- Test coverage: 20/20 passing"

# === STAP 6: Merge to Main ===
git checkout main
git merge feature/size-plan-dto
git push origin main
git branch -d feature/size-plan-dto
```

**VERWACHTE OUTPUT:**
- Alle 8 pylint checks: `10.00/10`
- Mypy check: `Success: no issues found`
- Pytest check: `XX passed in X.XXs`
- Documentation: File header + comprehensive class docstring present
- VS Code Problems: 0-1 warnings (accepted Pydantic limitation)
- Quality Metrics Dashboard: Updated with new module

**GATE 6: DOCUMENTATION QUALITY CHECKLIST**

Verificeer HANDMATIG de volgende elementen in de DTO file:

✅ **File Header (regels 1-10):**
```python
# backend/dtos/strategy/MYDTO.py
"""
MYDTO DTO - [One-line description].

[2-3 lines detailed explanation of purpose and context].

@layer: DTOs (Strategy Planning Output)
@dependencies: [pydantic, backend.utils.id_generators]
"""
```

✅ **Import Grouping (3 secties met comments):**
```python
# Standard Library Imports
from datetime import datetime, timezone
from decimal import Decimal

# Third-Party Imports  
from pydantic import BaseModel, Field

# Our Application Imports
from backend.utils.id_generators import generate_xxx_id
```

✅ **Class Docstring (min 20 regels):**
```python
class MyDTO(BaseModel):
    """
    [One-line summary of what this DTO represents].

    [2-3 lines context: who creates it, when, why].

    **Planning Chain Position:** [If applicable, e.g., "First step (Entry → Size → Exit → Routing)"]

    **Key Responsibilities:**
    - [Responsibility 1]
    - [Responsibility 2]
    - [Responsibility 3]

    **Not Responsible For:**
    - [What this DTO does NOT handle]

    **Usage Example:**
    ```python
    # [Concrete example with real values]
    dto = MyDTO(
        field1="value1",
        field2=Decimal("123.45"),
        rationale="Why this approach"
    )
    ```

    **Attributes:**
        field1: [Description]
        field2: [Description]
        [All fields documented]
    """
```

**REJECT als:**
- ❌ Geen file path comment (regel 1)
- ❌ Geen @layer en @dependencies tags
- ❌ Import grouping violations (missing section comments)
- ❌ Class docstring < 20 regels
- ❌ Geen **Usage Example:** sectie
- ❌ Geen **Attributes:** sectie
- ❌ Attributes sectie incomplete (niet alle velden gedocumenteerd)

**COMMON ISSUES & FIXES:**

| Issue | Command | Expected Fix |
|-------|---------|--------------|
| Trailing whitespace | PowerShell TrimEnd() | Score: 6.XX/10 → 10.00/10 |
| Line too long (>100) | Split asserts, shorten comments | Score: 9.XX/10 → 10.00/10 |
| Import inside function | Move to top-level | Score: X.XX/10 → 10.00/10 |
| Pylance "missing args" | Already suppressed globally | Should be 0 warnings |
| Pylance "no tzinfo member" | Add explanatory comment | 1 warning ACCEPTED |
| Missing documentation | Add file header + docstring | Gate 6 REJECT → PASS |
| Dashboard not updated | Edit agent.md sectie 6.6.6 | Missing tracking → Complete |

**REQUIRED TEST FILE HEADER TEMPLATE:**

```python
"""
Unit tests for MYDTO DTO.

Tests creation, validation, and edge cases for [brief description].
"""
# pyright: reportCallIssue=false
# Suppress Pydantic FieldInfo false positives for optional fields

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.dtos.strategy.MYDTO import MYDTO


class TestMYDTOCreation:
    """Test MYDTO instantiation."""
    
    def test_minimal_creation(self):
        """Can create minimal valid instance."""
        # Implementation...
```

**PYDANTIC V2 DTO TEMPLATE:**

```python
# backend/dtos/strategy/my_dto.py
"""
MyDTO DTO - [One-line description].

[2-3 lines detailed explanation of purpose, context, and usage].

@layer: DTOs (Strategy Planning Output)
@dependencies: [pydantic, backend.utils.id_generators]
"""

# Standard Library Imports
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

# Third-Party Imports
from pydantic import BaseModel, Field

# Our Application Imports
from backend.utils.id_generators import generate_xxx_id


class MyDTO(BaseModel):
    """
    [One-line summary of what this DTO represents].

    [2-3 lines context: who creates it, when, why].

    **Planning Chain Position:** [If applicable]

    **Key Responsibilities:**
    - [Responsibility 1]
    - [Responsibility 2]
    - [Responsibility 3]

    **Not Responsible For:**
    - [What this DTO does NOT handle]

    **Usage Example:**
    ```python
    # [Concrete example]
    dto = MyDTO(
        required_field="value",
        rationale="Explanation"
    )
    ```

    **Attributes:**
        dto_id: Auto-generated unique identifier (XXX_ prefix)
        created_at: Auto-set creation timestamp (timezone-aware UTC)
        required_field: [Description]
        optional_field: [Description] (optional)
    """

    # Auto-generated fields
    dto_id: str = Field(
        default_factory=generate_xxx_id,
        description="Unique identifier"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )

    # Required fields
    required_field: str = Field(
        description="Description"
    )

    # Optional fields (use | None, not Optional[])
    optional_field: Decimal | None = Field(
        None,
        description="Optional description"
    )

    # Pydantic v2 config (NOT class Config!)
    model_config = {
        "json_schema_extra": {
            "example": {
                "dto_id": "XXX_20250125_abc123",
                "created_at": "2025-01-25T10:30:00Z",
                "required_field": "value",
                "optional_field": None
            }
        }
    }
```

### 6.7. Test-Driven Development

**VERPLICHT TDD WORKFLOW:**

**STAP 0: CONCEPTUEEL ONTWERP (VERPLICHT VOORDAT JE CODE SCHRIJFT)**

Voordat je begint met testen of implementatie, moet je het component **volledig conceptueel ontwerpen**:

1. **Architecturale Positie:**
   - Waar past dit component in de pipeline?
   - Welke workers produceren input?
   - Welke workers consumeren output?
   - Is dit een DTO, Worker, Platform Component, of Factory?

2. **Verantwoordelijkheden & Contract:**
   - Wat is de single responsibility?
   - Welke data komt binnen?
   - Welke data gaat eruit?
   - Welke invarianten moeten gehandhaafd worden?

3. **Field Design (voor DTOs):**
   - Welke fields zijn **absoluut noodzakelijk**?
   - Welke fields zijn optioneel en waarom?
   - Welke types maken de intentie duidelijk?
   - Hoe voorkom je feature creep?

4. **Immutability & Flow Pattern:**
   - Is dit een immutable DTO (copy + extend)?
   - Wordt dit doorgegeven door workers?
   - Wie is de eindbestemming (consumer)?

5. **Design Document (optioneel voor complexe componenten):**
   - Maak een `docs/development/design_[component].md`
   - Documenteer: architecturale positie, verantwoordelijkheden, flow, edge cases
   - Review met gebruiker VOORDAT je test/implementatie start

**WAAROM DEZE STAP KRITIEK IS:**
- Voorkomt implementatie van verkeerde abstractions
- Dwingt helderheid over single responsibility
- Voorkomt feature creep (fields die "misschien handig zijn")
- Maakt test-driven development effectiever (je weet wat je test)

**ALLEEN NA CONCEPTUELE GOEDKEURING:**

**STAP 1: RED** - Schrijf test die faalt
**STAP 2: GREEN** - Schrijf minimale code om test te laten slagen  
**STAP 3: REFACTOR** - Verbeter code, tests blijven groen

```python
# test/test_my_worker.py
from unittest.mock import MagicMock
from backend.core.interfaces.context_provider import ITradingContextProvider
from backend.dto_reg.s1mple.input_worker.v1_0_0.input_dto import InputDTO

def test_my_worker_calculation():
    # Arrange
    mock_provider = MagicMock(spec=ITradingContextProvider)
    test_input = InputDTO(value=100)
    mock_provider.get_required_dtos.return_value = {InputDTO: test_input}
    
    worker = MyWorker(params={})
    worker.context_provider = mock_provider
    
    # Act
    result = worker.process()
    
    # Assert
    assert result.disposition == "CONTINUE"
    mock_provider.set_result_dto.assert_called_once()
```

### 6.7. Dependency Injection Pattern

**ALLE dependencies via injectie, NOOIT hardcoded:**

```python
# ✅ GOED - Via injectie
class MyWorker(StandardWorker):
    context_provider: ITradingContextProvider
    ohlcv_provider: IOhlcvProvider
    
    def __init__(self, params, **kwargs):
        super().__init__(params)
        self.context_provider = kwargs['context_provider']
        self.ohlcv_provider = kwargs['ohlcv_provider']

# ❌ FOUT - Hardcoded dependencies
class BadWorker:
    def __init__(self):
        self.provider = SomeConcreteProvider()  # Niet testbaar!
```

### 6.8. Error Handling & Validation

**Fail Fast:** Validatie tijdens bootstrap, NIET tijdens runtime.

```python
# In ConfigValidator
def validate_strategy_config(strategy: StrategyConfig, operation: OperationConfig):
    if strategy.execution_environment_id not in operation.environments:
        raise ConfigurationError(
            f"Environment '{strategy.execution_environment_id}' not found"
        )
```

## 7. Kritieke "DO's & DON'Ts"

### ✅ DO's

1. **Lees ALTIJD addenda eerst:**
   - `Addendum 3.8` - ConfigTranslator & BuildSpecs
   - `Addendum 5.1 Data` - Point-in-Time model
   - `Addendum 5.1 Expliciet` - Platgeslagen orkestratie

2. **Gebruik ALTIJD BuildSpec workflow:**
   ```
   YAML → ConfigTranslator → BuildSpecs → Factories → Components
   ```

3. **Onderscheid data communicatiepaden:**
   - TickCache (sync) → `set_result_dto()` met plugin DTOs
   - EventBus (async) → `DispositionEnvelope(PUBLISH)` met systeem DTOs

4. **Valideer tijdens bootstrap:**
   - DependencyValidator voor DTO chains
   - EventChainValidator voor event topology
   - ConfigValidator voor config consistency

5. **Test met mocks:**
   - Mock alle providers (ITradingContextProvider, IOhlcvProvider, etc.)
   - Import DTOs van centrale locatie voor tests

### ❌ DON'Ts

1. **NOOIT Operator-logica implementeren:**
   - Operators bestaan niet meer!
   - Gebruik EventAdapter + wiring_map

2. **NOOIT enriched_df pattern gebruiken:**
   - Gebruik Point-in-Time model met DTOs
   - Geen DataFrame muteren tussen workers

3. **NOOIT hardcoded dependencies:**
   - Gebruik dependency injection
   - Declareer capabilities in manifest

4. **NOOIT payload op custom events:**
   - Custom events zijn signalen zonder payload
   - Data gaat via TickCache

5. **NOOIT runtime validatie van config:**
   - Valideer tijdens bootstrap (fail fast)
   - Runtime moet puur executie zijn

6. **NOOIT code committen met quality issues:**
   - ❌ Trailing whitespace (moet 10.00/10 pylint zijn)
   - ❌ Imports inside functions (altijd top-level)
   - ❌ Onnodige haakjes: `not (a <= b)` → gebruik `not a <= b`
   - ❌ Failing tests (100% groen verplicht)
   - ❌ Missing type hints (alle functies typed)
   - ❌ **Import grouping violations (zie Chapter 10 architectuur)**

7. **NOOIT implementeren zonder tests:**
   - TDD workflow is VERPLICHT (Red → Green → Refactor)
   - Minimaal 20+ tests voor nieuwe DTOs
   - Edge cases MOETEN gedekt zijn

### 6.7. Import Grouping Standard (Chapter 10)

**VERPLICHT PEP 8 Import Grouping:**

Alle Python bestanden MOETEN imports groeperen in EXACT deze volgorde:

```python
# Standard Library Imports
import re
from datetime import datetime
from typing import Any, Dict, Optional

# Third-Party Imports
import pytest
from pydantic import BaseModel, Field, validator

# Our Application Imports
from backend.core.enums import ContextType
from backend.core.context_factors import FactorRegistry
from backend.dtos.strategy.context_factor import ContextFactor
```

**Regels:**
1. **Drie groepen** met lege regel tussen elke groep
2. **Comment headers** voor elke groep (verplicht)
3. **Alfabetisch** binnen elke groep (import statements eerst, from imports daarna)
4. **Absolute imports** vanaf project root
5. **Geen relatieve imports** (geen `from . import`)

**Rationale (Chapter 10):**
- Voorkomt circular import problemen
- Maakt dependencies expliciet zichtbaar
- Verbetert code leesbaarheid
- Standaard in Python community (PEP 8)

**Validatie:**
```powershell
# Check import grouping met pylint
python -m pylint <file> --disable=all --enable=wrong-import-order

# Of handmatig: ALLE imports moeten in 3 groepen met comments
```

**Automated Tools (Optioneel):**
```powershell
# isort configuratie (.isort.cfg)
[settings]
force_single_line = True
line_length = 100
known_third_party = pytest,pydantic,pandas,numpy
known_first_party = backend,tests
sections = STDLIB,THIRDPARTY,FIRSTPARTY
import_heading_stdlib = Standard Library Imports
import_heading_thirdparty = Third-Party Imports
import_heading_firstparty = Our Application Imports
```

## 8. Documentatie Referenties

### Primaire Bronnen (In volgorde van lezen)

1. **S1mpleTrader V2 Architectuur.md** (Hoofddocument - BASIS CONCEPTEN)
   - Hoofdstukken 1-2: Fundamentele concepten
   - Hoofdstuk 3-4: Plugin anatomie
   - **LET OP:** Hoofdstukken 5-10 zijn deels achterhaald!

2. **Addendum 3.8: Configuratie & Vertaal Filosofie** (KRITIEK!)
   - Drie configuratielagen
   - ConfigTranslator & BuildSpecs
   - OperationService als lifecycle manager

3. **Addendum 5.1: Data Landschap & Point-in-Time** (KRITIEK!)
   - DTO-Centric model
   - TickCache vs EventBus
   - ITradingContextProvider
   - DispositionEnvelope

4. **Addendum 5.1: Expliciet Bedraad Netwerk** (KRITIEK!)
   - Eliminatie Operator-laag
   - EventAdapter per component
   - Wiring_map generatie via UI

5. **Addendum 11_6.7: DependencyValidator**
   - DTO dependency validatie
   - Bootstrap-fase checks

### Achterhaalde Secties (Lees met Voorzichtigheid)

**In Architectuur.md:**
- ❌ Paragraaf 2.7: Data-Gedreven Operator (VERVALT)
- ❌ Paragraaf 2.11: Dataflow & Orchestratie (ACHTERHAALD)
- ❌ Hoofdstuk 5: Workflow Orkestratie (ACHTERHAALD)
- ❌ Paragraaf 3.3.2: operators.yaml (BESTAAT NIET MEER)

**Gebruik in plaats daarvan:**
- ✅ Addenda 3.8 + 5.1 voor actuele architectuur
- ✅ Sectie 2.4 voor worker categorieën (nog steeds geldig)
- ✅ Sectie 4 voor plugin anatomie (basis nog geldig)

## 9. Snelle Referentie: Kernterminologie

| Term | Betekenis | Kritieke Details |
|------|-----------|------------------|
| **BuildSpecs** | Machine-instructies voor factories | Gegenereerd door ConfigTranslator uit YAML |
| **DispositionEnvelope** | Worker output contract | CONTINUE, PUBLISH of STOP |
| **TickCache** | Tijdelijke DTO opslag per tick | Levensduur: één tick/flow |
| **ITradingContextProvider** | Data access interface | get_base_context(), get_required_dtos(), set_result_dto() |
| **EventAdapter** | Component ↔ EventBus interface | Één per component, geconfigureerd via wiring_spec |
| **Systeem DTO** | Standaard platform DTOs | OpportunitySignalDTO, ThreatSignalDTO, etc. |
| **Plugin DTO** | Worker-specifieke DTOs | Voor TickCache, gedeeld via enrollment |
| **Wiring Map** | Event routing configuratie | UI-gegenereerd per strategie |
| **Capability** | Opt-in worker functionaliteit | Gedeclareerd in manifest, geïnjecteerd door factory |

Door deze principes en structuren te volgen, help ik je om een consistente, robuuste en onderhoudbare codebase te bouwen. Laten we beginnen!
