# SimpleTraderV3 - TODO List

## 🏗️ PLATFORM IMPLEMENTATIE ROADMAP (PRIORITEIT)

### Phase 1: Contracten & Interfaces (Foundation)

**Status:** In Progress (Data Contracts: 14/14 Complete ✅, IStrategyCache: 1/3 Complete ✅)
**Prioriteit:** CRITICAL - Blocking voor alle verdere werk#### 1.1 Data Contracts (DTOs) - ✅ COMPLETE

**Shared Layer:**
- [x] **DispositionEnvelope** - 16/16 tests ✅
- [x] **CausalityChain** - 13/13 tests ✅

**Strategy SWOT Layer:**
- [x] **ContextFactor** - 12/12 tests ✅
- [x] **AggregatedContextAssessment** - 12/12 tests ✅
- [x] **OpportunitySignal** - 37/37 tests ✅
- [x] **ThreatSignal** - 38/38 tests ✅

**Strategy Planning Layer:**
- [x] **StrategyDirective** - 7/7 tests ✅
- [x] **EntryPlan** - 13/13 tests ✅
- [x] **SizePlan** - 20/20 tests ✅
- [x] **ExitPlan** - 15/15 tests ✅
- [x] **ExecutionPlan** - 19/19 tests ✅ (universal trade-offs, replaces RoutingPlan)

**Execution Layer:**
- [x] **ExecutionDirective** - 11/11 tests ✅
- [x] **ExecutionDirectiveBatch** - 15/15 tests ✅
- [x] **ExecutionGroup** - 25/25 tests ✅

**Total:** 252 tests passing across 14 DTOs ✅

**Build Specs Layer** (Pending - niet blocking voor Fase 1):
- [ ] ConnectorExecutionSpec (base ABC)
- [ ] CEXExecutionSpec
- [ ] DEXExecutionSpec  
- [ ] BacktestExecutionSpec

> **Note:** Build Specs zijn output van ExecutionTranslator (Fase 4c) en niet nodig voor worker contracts.

#### 1.2 Interface Protocols (PARTIAL - StrategyCache DONE)
- [x] **IStrategyCache** (protocol) ✅ COMPLETE
  - `start_new_strategy_run(cache, timestamp) -> None`
  - `get_run_anchor() -> RunAnchor`
  - `get_required_dtos(worker) -> Dict[Type[BaseModel], BaseModel]`
  - `set_result_dto(worker, dto) -> None`
  - `has_dto(dto_type) -> bool`
  - `clear_cache() -> None`
  - Tests: 20/20 passing ✅
  - Implementation: `backend/core/strategy_cache.py` ✅

- [ ] **IEventBus** (protocol)
  - `publish(event_name: str, payload: BaseModel) -> None`
  - `subscribe(event_name: str, handler: Callable) -> str`
  - `unsubscribe(subscription_id: str) -> None`
  - Tests: Mock implementatie + pub/sub scenarios

- [ ] **IWorkerLifecycle** (protocol)
  - `initialize(strategy_cache, event_bus) -> None`
  - `shutdown() -> None`
  - Tests: Lifecycle state verification

#### 1.3 Base Worker Classes (TODO)
- [ ] **BaseWorker** (abstract foundation)
  - Implements: IWorkerLifecycle
  - Dependencies: ITradingContextProvider, IEventBus (via constructor)
  - Methods: `process()`, `validate_inputs()`, `handle_error()`
  - Tests: Abstract class instantiation prevention + contract validation

- [ ] **ContextWorker** (extends BaseWorker)
  - Input: TradingContext (raw OHLCV + enriched_df)
  - Output: ContextFactor DTO
  - Tests: Input validation, DTO production

- [ ] **OpportunityWorker** (extends BaseWorker)
  - Input: AggregatedContextAssessment
  - Output: OpportunitySignal DTO
  - Tests: Confidence ranges, signal_type validation

- [ ] **ThreatWorker** (extends BaseWorker)
  - Input: AggregatedContextAssessment
  - Output: ThreatSignal DTO
  - Tests: Severity ranges, threat_type validation

- [ ] **StrategyPlanner** (extends BaseWorker)
  - Input: AggregatedContextAssessment + OpportunitySignal + ThreatSignal
  - Output: StrategyDirective DTO
  - Tests: SWOT confrontation, scope validation

- [ ] **PlanningWorker** (extends BaseWorker)
  - Subtypes: EntryPlanner, SizePlanner, ExitPlanner, ExecutionPlanner
  - Input: StrategyDirective (SWOT mode) OR OpportunitySignal (direct mode)
  - Output: EntryPlan/SizePlan/ExitPlan/ExecutionPlan DTOs
  - Tests: Mode-agnostic processing, role-based filtering

#### 1.4 Platform Data Structures (PARTIAL - RunAnchor DONE)
- [x] **RunAnchor** (Pydantic model) ✅ COMPLETE
  - Frozen timestamp for point-in-time validation
  - Part of IStrategyCache interface
  - Located: `backend/core/interfaces/strategy_cache.py`

- [x] **StrategyCacheType** (type alias) ✅ COMPLETE
  - Type alias: `Dict[Type[BaseModel], BaseModel]`
  - Used by IStrategyCache protocol
  - Located: `backend/core/interfaces/strategy_cache.py`

- [ ] **TickCacheManager** (singleton) - TODO
  - Orchestrates strategy run lifecycle
  - Methods: `start_run()`, `end_run()`, event listeners
  - Tests: Multi-run management, cleanup

### Phase 2: Pydantic Config Schemas

**Status:** Planning  
**Prioriteit:** HIGH - Required for config-driven assembly

#### 2.1 Worker Manifest Schema
- [ ] **WorkerManifestDTO**
  ```python
  class WorkerManifestDTO(BaseModel):
      worker_id: str
      worker_type: Literal["context", "signal", "threat", "planning", "execution"]
      produces_dtos: list[str]  # DTO class names
      requires_dtos: list[str]  # DTO class names
      capabilities: list[str]   # ["state_persistence", "events", "journaling"]
      config_schema: dict[str, Any]  # Optional runtime config
  ```
  - Tests: Validation, type checking, required fields

#### 2.2 Wiring Configuration Schema
- [ ] **WiringConfigDTO**
  ```python
  class EventWiringDTO(BaseModel):
      event_name: str
      subscriber_worker_id: str
      handler_method: str  # "on_opportunity_detected"
  
  class WiringConfigDTO(BaseModel):
      sequential_workers: list[str]  # Execution order
      event_wirings: list[EventWiringDTO]
  ```
  - Tests: Circular dependency detection, valid worker references

#### 2.3 Strategy Blueprint Schema
- [ ] **StrategyBlueprintDTO**
  ```python
  class WorkforceDTO(BaseModel):
      context_workers: list[str]
      signal_workers: list[str]
      threat_workers: list[str]
      planning_workers: list[str]
      execution_workers: list[str]
  
  class StrategyBlueprintDTO(BaseModel):
      strategy_id: str
      workforce: WorkforceDTO
      wiring: WiringConfigDTO
  ```
  - Tests: Complete strategy validation

### Phase 3: Singletons & Factories

**Status:** Planning  
**Prioriteit:** HIGH - Core infrastructure

#### 3.1 Core Singletons
- [x] **StrategyCache** (implements IStrategyCache) ✅ COMPLETE
  - Manages current TickCache per strategy run
  - DTO storage and retrieval
  - Tests: 20/20 passing
  - Location: `backend/core/strategy_cache.py`

- [ ] **EventBus** (implements IEventBus)
  - N-to-N broadcast semantics
  - Subscription management
  - Tests: Pub/sub, unsubscribe, error handling

- [ ] **PluginRegistry** (singleton)
  - Discovery: `plugins/**/*_manifest.yaml`
  - Worker class loading
  - Manifest validation
  - Tests: Discovery, registration, retrieval

#### 3.2 Assembly Factories
- [ ] **WorkerFactory**
  - Input: WorkerManifestDTO + runtime config
  - Output: Instantiated worker (BaseWorker subclass)
  - Dependency injection: strategy_cache, event_bus
  - Tests: Worker instantiation, capability injection

- [ ] **EventWiringFactory**
  - Input: WiringConfigDTO + WorkerFactory
  - Output: EventAdapter instances with pre-configured dependencies
  - Assembly-time manifest parsing (NOT runtime)
  - Tests: Event subscription creation, dependency validation

- [ ] **StrategyFactory**
  - Input: StrategyBlueprintDTO
  - Output: Complete assembled strategy (all workers + wirings)
  - Orchestrates: WorkerFactory + EventWiringFactory
  - Tests: End-to-end strategy assembly

### Phase 4: Orchestration & Execution

**Status:** Planning  
**Prioriteit:** MEDIUM - Requires Phase 1-3 complete

#### 4.1 Execution Components
- [ ] **EventAdapter**
  - Wraps worker method calls
  - Pre-configured dependency validation (no runtime manifest parsing!)
  - Error handling & disposition routing
  - Tests: Execution, missing dependencies, error propagation

- [ ] **SequentialExecutor**
  - Executes workers in configured order
  - TickCache population
  - Disposition handling (CONTINUE/PUBLISH/HALT)
  - Tests: Sequential flow, early termination, cache state

#### 4.2 Strategy Runner
- [ ] **StrategyRunner**
  - Main tick processing loop
  - SequentialExecutor orchestration
  - EventBus coordination
  - Tests: Multi-tick execution, event propagation

### Phase 5: Bootstrap & Configuration

**Status:** Planning  
**Prioriteit:** MEDIUM - Integration layer

#### 5.1 Configuration Loading
- [ ] **ConfigLoader**
  - Loads: platform.yaml, operation.yaml, strategy_blueprint.yaml
  - YAML parsing + Pydantic validation
  - Tests: Valid/invalid configs, missing files

- [ ] **ConfigTranslator**
  - YAML → Pydantic DTOs (BuildSpecs)
  - Validation layer
  - Tests: Translation accuracy, error handling

#### 5.2 Bootstrap Orchestration
- [ ] **OperationService**
  - Strategy lifecycle: start/stop/restart
  - ConfigLoader + StrategyFactory orchestration
  - Tests: Multi-strategy management, error recovery

---

## 📐 IMPLEMENTATIE VOLGORDE

### Week 1: Foundation (Phase 1) - Interface Contracts
1. **Data Contracts:** ✅ COMPLETE (14 DTOs, 252 tests passing)
2. **IStrategyCache Protocol + Implementation:** ✅ COMPLETE (20 tests passing)
3. **Next:** IEventBus protocol + tests
4. **Then:** IWorkerLifecycle protocol + tests
5. BaseWorker + subclasses (ContextWorker, OpportunityWorker, ThreatWorker, StrategyPlanner, PlanningWorker)
6. **Milestone:** All interface contracts + tests passing

### Week 2: Configuration (Phase 2)
1. WorkerManifestDTO + tests
2. WiringConfigDTO + tests
3. StrategyBlueprintDTO + tests
4. **Milestone:** Config validation working

### Week 3: Factories (Phase 3)
1. PluginRegistry + worker discovery
2. TradingContextProvider singleton
3. EventBus singleton
4. WorkerFactory + EventWiringFactory
5. **Milestone:** Single worker assembly working

### Week 4: Orchestration (Phase 4)
1. EventAdapter implementation
2. SequentialExecutor
3. StrategyRunner
4. **Milestone:** End-to-end tick processing

### Week 5: Integration (Phase 5)
1. ConfigLoader + ConfigTranslator
2. OperationService
3. **Milestone:** Full bootstrap from YAML to execution

---

## 📋 Architectuur & Design Beslissingen

### 🔄 Plugin Documentatie Framework

**Prioriteit:** Medium  
**Status:** Pending  
**Besluit Datum:** 2025-10-24

**Context:**
Tijdens de implementatie van System DTOs (OpportunitySignal, ThreatSignal) kwam
naar voren dat beschrijvende teksten (descriptions) niet in de DTOs thuishoren,
maar wel essentieel zijn voor begrip van de plugin functionaliteit.

**Actie Items:**
- [ ] Ontwerp plugin documentatie structuur
  - Waar wordt plugin-specifieke uitleg opgeslagen?
  - `plugins/[category]/[plugin_name]/README.md`?
  - Centraal `docs/plugins/` register?
  - Of beide (README.md + centraal overzicht)?

- [ ] Definieer documentatie template voor plugins
  - Beschrijving van signal_type / threat_type betekenis
  - Uitleg van confidence / severity interpretatie
  - Voorbeelden van gebruik
  - Configuratie opties

- [ ] Integreer met UI/tooling
  - Hoe toont "Data Integrity Explorer" deze docs?
  - Developer console access?
  - API documentation generation?

**Gerelateerde Discussie:**
Uit conversatie over ThreatSignal DTO - beschrijvende teksten horen niet in
System DTOs maar moeten wel ergens gedocumenteerd worden voor developers.

---

### ⚙️ EventAdapter Runtime Dependency Validation

**Prioriteit:** Medium  
**Status:** Pending Implementation  
**Besluit Datum:** 2025-10-24

**Context:**
TickCache gebruikt Type-Safe Dependency Resolution waarbij workers via
`manifest.requires_dtos` declareren welke DTOs ze nodig hebben. Momenteel
wordt dit alleen tijdens **bootstrap** gevalideerd door `DependencyValidator`.

**Probleem:**
Runtime enforcement ontbreekt - EventAdapter roept workers aan zonder te
valideren of alle vereiste DTOs daadwerkelijk in de TickCache aanwezig zijn.

**Oplossing:**
EventAdapter moet tijdens **assembly-time** (niet runtime) geconfigureerd
worden met dependency checks:

**Assembly-Time Configuratie:**
```python
# Bij bouwen van EventAdapter (in EventWiringFactory)
adapter = EventAdapter(
    component=worker,
    required_dto_types=[EMAOutputDTO, RSIOutputDTO],  # Uit manifest
    context_provider=context_provider
)
```

**Runtime Validatie (geen manifest inspectie):**
```python
# EventAdapter._on_event() gebruikt pre-configured lijst
def _validate_dependencies(self) -> None:
    cache = self._context_provider.get_current_cache()
    for dto_type in self._required_dto_types:  # Pre-configured!
        if dto_type not in cache:
            raise MissingDependencyError(...)
```

**Architecturaal Principe:**
- ✅ Manifest parsing gebeurt bij **assembly** (WorkerBuilder/EventWiringFactory)
- ✅ Runtime validatie gebruikt **pre-configured** dependency lijst
- ❌ **NOOIT** manifest inspection tijdens runtime

**Actie Items:**
- [ ] Update EventAdapter constructor om `required_dto_types` te accepteren
- [ ] Update EventWiringFactory om manifest.requires_dtos te lezen
- [ ] Implementeer `_validate_dependencies()` check vóór worker aanroep
- [ ] Voeg integration tests toe voor missing dependency scenario

**Gerelateerde Componenten:**
- `EventAdapter` (runtime executor)
- `EventWiringFactory` (assembly-time configurator)
- `DependencyValidator` (bootstrap-time validator)
- `ITradingContextProvider.get_required_dtos()` (worker-side access)

**Design Constraint:**
EventAdapter mag **GEEN** runtime manifest parsing doen - alle configuratie
komt uit assembly-time preparation.

---

### 🌍 i18n Policy voor Field Descriptions

**Prioriteit:** Medium  
**Status:** Pending Architectural Decision  
**Besluit Datum:** 2025-10-24

**Context:**
Field descriptions in Pydantic DTOs worden gebruikt door:
- API Documentation (OpenAPI/Swagger)
- Web Frontend Introspection ("Data Integrity Explorer")
- JSON Schema generation
- Developer Console / Admin Panel
- Error Messages (Pydantic validation)

**Huidige Aanpak:**
Field descriptions zijn technisch Engels, bedoeld voor developers/admins.
Dit is consistent met "technical documentation" principe.

**Mogelijke Alternatieven:**

**Optie A: Descriptions blijven technisch (Engels)**
- ✅ Voor developers/admins
- ✅ Niet user-facing
- ✅ Blijft in Pydantic schema
- ✅ **HUIDIGE KEUZE**

**Optie B: i18n Keys in Descriptions**
- Lookup via i18n systeem
- User-facing mogelijk
- Complexer

**Optie C: Dual System**
- Technical description voor devs (Engels in schema)
- i18n key voor user-facing features (aparte layer)
- Beste van beide werelden
- Meer overhead

**Actie Items:**
- [ ] Formeel besluit nemen over i18n strategie
- [ ] Documenteren in agent.md als coding standard
- [ ] Bij keuze voor Optie B of C: implementatie guide maken

**Notities:**
- User-facing text hoort primair in `locales/` YAML files
- Field descriptions zijn primair voor developers
- Frontend kan altijd eigen i18n layer toevoegen bovenop schema

---

### 🎯 SWOT Decision Framework

**Prioriteit:** High  
**Status:** Architecture Approved, Pending Implementation  
**Besluit Datum:** 2025-10-24

**Context:**
De strategie implementeert een SWOT-analyse framework waarbij verschillende
worker categorieën verschillende rollen vervullen in het decision-making proces.

**SWOT Mapping:**
- **Strengths & Weaknesses:** ContextWorker → ContextAssessment (via aggregatie)
- **Opportunities:** OpportunityWorker → OpportunitySignal (confidence 0.0-1.0)
- **Threats:** ThreatWorker → ThreatSignal (severity 0.0-1.0)
- **Confrontation Matrix:** PlanningWorker → combineert alle quadranten

**Architecturale Componenten:**

1. **ContextAggregator** (Platform component)
   - Aggregeert atomaire context DTOs → ContextAssessment
   - Platform verantwoordelijkheid (configureerbaar via policy)
   - Draait na laatste ContextWorker in sequential chain
   - Output: `strength` en `weakness` scores (0.0-1.0)

2. **ContextAssessment DTO** (System DTO)
   - Bevat aggregated strength/weakness duiding
   - Analoog aan OpportunitySignal.confidence en ThreatSignal.severity
   - Symmetrie: alle SWOT quadranten hebben 0.0-1.0 scores

3. **SWOT Confrontation Worker** (PlanningWorker)
   - Input: ContextAssessment + OpportunitySignal + ThreatSignal
   - Logic: Mathematische confrontatie matrix
   - Output: TradePlan met execution decisie

**Actie Items:**
- [ ] Design ContextAssessment DTO
- [ ] Implement ContextAggregator platform component
- [ ] Design AggregationPolicy interface
- [ ] Implement SWOT Confrontation PlanningWorker
- [ ] Update worker taxonomie documentatie

**Zie ook:** [`development/decision_framework.md`](development/decision_framework.md) (gedetailleerde architectuur)

**Gerelateerde DTOs:**
- OpportunitySignal (confidence field)
- ThreatSignal (severity field)
- ContextAssessment (strength/weakness fields) - pending

---

### 🎯 STRATEGY PLANNING ARCHITECTUUR

**Prioriteit:** HIGH - Critical Path  
**Status:** Architecture Designed, Ready for Implementation  
**Besluit Datum:** 2025-10-25

**Context:**
De planning fase transformeert input (SWOT of direct Opportunity) naar actionable 
trade plannen via een flexibel multi-mode systeem. Ondersteunt zowel eenvoudige 
als complexe strategieën met dezelfde DTOs en planners.

#### Strategy Modes (Complexity Scaling)

**Mode 1: Direct Planning** (⭐ Beginner)
```yaml
strategy:
  mode: "direct_planning"
  trigger:
    event: "OPPORTUNITY_DETECTED"
    filter: {signal_type: "BREAKOUT", min_confidence: 0.7}
  planning:
    entry: {plugin: "ImmediateMarketEntryPlanner"}
    size: {plugin: "FixedRiskSizer", config: {risk_percentage: 0.01}}
    exit: {plugin: "FixedRRExitPlanner", config: {risk_reward_ratio: 2.0}}
    routing: {plugin: "MarketOrderRouter"}
```
- **Flow**: Opportunity → [OpportunityTrigger] → 4 Fixed Planners → ExecutionDirective
- **Gebruik**: Eenvoudige strategieën zonder SWOT
- **Complexity**: Geen StrategyPlanner, geen role-based selectie

**Mode 2: SWOT Planning** (⭐⭐⭐⭐ Expert)
```yaml
strategy:
  mode: "swot_planning"
  strategy_planner: {plugin: "AdaptiveMomentumPlanner"}
  planning:
    entry:
      - plugin: "ImmediateMarketEntryPlanner"
        triggers: {timing_preference: [0.8, 1.0]}
      - plugin: "LayeredLimitEntryPlanner"
        triggers: {timing_preference: [0.3, 0.7]}
    # ... role-based voor size/exit/routing
```
- **Flow**: SWOT → [StrategyPlanner] → StrategyDirective → Role-Based Planners → ExecutionDirective
- **Gebruik**: Complexe strategieën met SWOT confrontatie
- **Complexity**: Volledige StrategyDirective, PlannerMatcher, dynamische selectie

#### Kern Principes (Mode-Agnostic)

1. **4 Planning Sub-Categorieën** (uit V2 architectuur)
   - `ENTRY_PLANNING`: Entry timing & price selection
   - `SIZE_PLANNING`: Position sizing
   - `EXIT_PLANNING`: Stop loss & take profit
   - `ORDER_ROUTING`: Execution tactics

2. **Final Output: ExecutionDirective** (beide modes)
   - Aggregatie van EntryPlan + SizePlan + ExitPlan + RoutingPlan
   - Ready for execution
   - Event: `EXECUTION_DIRECTIVE_READY`

3. **Hybrid Execution Model** (beide modes)
   - **Parallel Phase**: Entry, Size, Exit (onafhankelijk)
   - **Sequential Phase**: Routing (krijgt context van eerdere plannen)
   - Rationale: Routing kan afhankelijk zijn van size (bijv. iceberg orders)

#### DTO Structuur

**Core Planning DTOs** (beide modes):
```python
# Planning outputs (altijd nodig)
class EntryPlan(BaseModel):
    symbol: str
    direction: Literal["BUY", "SELL"]
    order_type: str  # "MARKET", "LIMIT", etc.
    timing: str
    reference_price: Decimal | None

class SizePlan(BaseModel):
    position_size: Decimal
    position_value: Decimal
    risk_amount: Decimal

class ExitPlan(BaseModel):
    stop_loss_price: Decimal
    take_profit_price: Decimal | None
    exit_strategy_type: str

class RoutingPlan(BaseModel):
    order_type: str
    execution_style: str
    slippage_tolerance: Decimal

# Final aggregation (beide modes)
class ExecutionDirective(BaseModel):
    directive_id: str
    timestamp: datetime
    
    # Planning results
    entry_plan: EntryPlan | None
    size_plan: SizePlan | None
    exit_plan: ExitPlan | None
    routing_plan: RoutingPlan | None
    
    # Context
    strategy_id: str
    trigger_context: dict[str, Any]  # OpportunitySignal of StrategyDirective
```

**SWOT Mode Only** (optioneel voor Mode 2):
```python
class StrategyDirective(BaseModel):
    """Output van StrategyPlanner (alleen SWOT mode)."""
    strategy_planner_id: str
    strategy_id: str
    decision_timestamp: datetime
    
    # Causaliteit
    trigger: TriggerInfo
    contributing_signals: ContributingSignals
    
    # Scope
    scope: DirectiveScope  # NEW_TRADE, MODIFY_EXISTING, CLOSE_EXISTING
    target_trade_ids: list[str]
    
    # 4 Planning Directives (optioneel - bepaalt welke planners draaien)
    entry_directive: EntryDirective | None
    size_directive: SizeDirective | None
    exit_directive: ExitDirective | None
    routing_directive: RoutingDirective | None
    
    confidence: Decimal
    rationale: str

# Sub-directives (hints/constraints voor role-based selectie)
class EntryDirective(BaseModel):
    symbol: str
    direction: Literal["BUY", "SELL"]
    timing_preference: Decimal  # 0.0-1.0
    preferred_price_zone: PriceZone | None
    max_acceptable_slippage: Decimal | None

class SizeDirective(BaseModel):
    aggressiveness: Decimal  # 0.0-1.0
    max_risk_amount: Decimal
    account_risk_pct: Decimal

class ExitDirective(BaseModel):
    profit_taking_preference: Decimal  # 0.0-1.0
    risk_reward_ratio: Decimal
    stop_loss_tolerance: Decimal

class RoutingDirective(BaseModel):
    execution_urgency: Decimal  # 0.0-1.0
    iceberg_preference: Decimal
    max_total_slippage_pct: Decimal
```

#### Platform Components

**Mode 1: Direct Planning Components**
1. **OpportunityTrigger** (Platform component)
   - Luistert naar `OPPORTUNITY_DETECTED` 
   - Filtert op basis van strategy config (signal_type, min_confidence)
   - Triggert direct: `PLAN_ENTRY_REQUESTED`, `PLAN_SIZE_REQUESTED`, etc.
   - Output: OpportunitySignal direct naar planners

2. **Base Planner Classes** (simplified)
   - `BaseEntryPlanner.on_opportunity_signal()` 
   - `BaseSizePlanner.on_opportunity_signal()`
   - `BaseExitPlanner.on_opportunity_signal()`
   - `BaseRoutingPlanner.on_routing_context()` (sequential)

**Mode 2: SWOT Planning Components** (additional)
3. **StrategyPlanner** (Worker)
   - Input: ContextAssessment + OpportunitySignal + ThreatSignal
   - Logic: SWOT confrontatie
   - Output: StrategyDirective (met sub-directives)

4. **PlannerMatcher** (Injected in Base Classes)
   - Laadt trigger-configuratie uit strategy YAML
   - Biedt `should_handle(planner_id, directive)` method
   - Strategy-agnostic filtering logic
   - Alleen actief in SWOT mode

5. **Base Planner Classes** (extended)
   - `BaseEntryPlanner.on_strategy_directive()` (extra method)
   - Gebruikt PlannerMatcher voor role-based filtering
   - `should_handle()` check voor trigger ranges

**Shared Components** (beide modes)
6. **PlanningAggregator** (Event-Driven Coordinator)
   - Mode-aware: detecteert Direct vs SWOT op basis van trigger event
   - Tracks welke plannen verwacht worden
   - Parallel phase: Entry, Size, Exit
   - Sequential phase: Routing (krijgt context)
   - Publiceert: `EXECUTION_DIRECTIVE_READY`

#### Event Flows

**Mode 1: Direct Planning**
```
Opportunity → OPPORTUNITY_DETECTED
    ↓
[OpportunityTrigger] filters & validates
    ↓
PLAN_ENTRY_REQUESTED (payload: OpportunitySignal)
PLAN_SIZE_REQUESTED  (payload: OpportunitySignal)
PLAN_EXIT_REQUESTED  (payload: OpportunitySignal)
    ↓
[Fixed Planners] execute (1 per categorie)
    ↓
ENTRY_PLAN_CREATED, SIZE_PLAN_CREATED, EXIT_PLAN_CREATED
    ↓
[PlanningAggregator] detects completion
    ↓
ROUTING_PLANNING_REQUESTED (with EntryPlan + SizePlan + ExitPlan)
    ↓
[Routing Planner] executes
    ↓
ROUTING_PLAN_CREATED
    ↓
[PlanningAggregator] aggregates
    ↓
EXECUTION_DIRECTIVE_READY
```

**Mode 2: SWOT Planning**
```
Context → ContextAssessment  ┐
Opportunity → OpportunitySignal ├→ [StrategyPlanner] → StrategyDirective
Threat → ThreatSignal       ┘
    ↓
STRATEGY_DIRECTIVE_ISSUED
    ↓
[PlanningAggregator] starts tracking
    ↓
[Multiple Entry Planners] filter via PlannerMatcher → Winner executes
[Multiple Size Planners]  filter via PlannerMatcher → Winner executes
[Multiple Exit Planners]  filter via PlannerMatcher → Winner executes
    ↓
ENTRY_PLAN_CREATED, SIZE_PLAN_CREATED, EXIT_PLAN_CREATED
    ↓
[PlanningAggregator] triggers routing phase
    ↓
ROUTING_PLANNING_REQUESTED
    ↓
[Multiple Routing Planners] filter via PlannerMatcher → Winner executes
    ↓
ROUTING_PLAN_CREATED
    ↓
EXECUTION_DIRECTIVE_READY
```

#### Actie Items

**Phase 1: Core DTOs** (beide modes)
- [ ] `EntryPlan`, `SizePlan`, `ExitPlan`, `RoutingPlan` (planning outputs)
- [ ] `ExecutionDirective` (final aggregation)
- [ ] `RoutingPlanningContext` (voor sequential routing phase)
- [ ] Unit tests (min 20 per DTO)

**Phase 2: Direct Planning Mode** (⭐ Start hier - snelste ROI)
- [ ] `OpportunityTrigger` platform component
- [ ] Base planner classes met `on_opportunity_signal()` method
- [ ] `PlanningAggregator` (mode-agnostic, start met direct mode support)
- [ ] Reference implementations:
  - [ ] `ImmediateMarketEntryPlanner`
  - [ ] `FixedRiskSizer`
  - [ ] `FixedRRExitPlanner`
  - [ ] `MarketOrderRouter`
- [ ] End-to-end test: Opportunity → ExecutionDirective

**Phase 2: SWOT Planning DTOs** (optioneel voor complexe strategieën)
- [x] `StrategyDirective` + sub-directives (Entry/Size/Exit/Routing) ✅ COMPLETE
- [x] `TriggerInfo`, `ContributingSignals` (causaliteit) ✅ COMPLETE
- [x] Unit tests ✅ 17 tests passing

**Phase 4: SWOT Planning Components** (⭐⭐⭐⭐ Expert features)
- [ ] `BaseStrategyPlanner` worker
- [ ] `PlannerMatcher` (trigger filtering)
- [ ] Extend base planner classes met `on_strategy_directive()` method
- [ ] Update `PlanningAggregator` voor SWOT mode support
- [ ] Reference implementation: `AdaptiveMomentumPlanner` (StrategyPlanner)
- [ ] Integration tests voor role-based selection
- [ ] End-to-end test: SWOT → StrategyDirective → Role-based planners → ExecutionDirective

**Phase 5: Platform Execution Components** (CRITICAL - Event-Driven Flow)
- [ ] `DirectiveAssembler` platform worker (bus-agnostic)
  - Aggregates 4 plans (Entry, Size, Exit, Routing) → ExecutionDirective
  - Returns: DispositionEnvelope (PUBLISH "EXECUTION_DIRECTIVE_READY")
  - Wired via EventAdapter to listen: ENTRY_PLAN_CREATED, SIZE_PLAN_CREATED, etc.
  - Copies TriggerContext forward, adds execution_directive_id
- [ ] `ExecutionHandler` interface update
  - Change return type: void → DispositionEnvelope
  - Workers return STOP disposition, EventAdapter handles routing
  - Maintains bus-agnostic pattern (no EventBus dependency)
  - Copies TriggerContext forward (unchanged)
- [ ] `FlowTerminator` platform worker (bus-agnostic) **← JOURNAL CAUSALITY ENDPOINT**
  - Responsibilities: 
    - **Journal causality reconstruction** (uses TriggerContext to query Journal)
    - Component cleanup, garbage collection, metrics
  - Input: ExecutionDirective with complete TriggerContext (all IDs accumulated)
  - Returns: DispositionEnvelope (PUBLISH "UI_FLOW_TERMINATED")
  - Wired via EventAdapter to listen: _flow_stop
  - **THIS IS THE COMPONENT THAT USES TRIGGERCONTEXT FOR JOURNAL RECONSTRUCTION**
- [ ] Event wiring configuration (wiring_map.yaml)
  - DirectiveAssembler → 4 plan events
  - ExecutionHandler → EXECUTION_DIRECTIVE_READY
  - FlowTerminator → _flow_stop
- [ ] End-to-end test: 4 Plans → DirectiveAssembler → ExecutionDirective → ExecutionHandler → FlowTerminator

**Phase 6: StrategyPlanner Reference Implementations**
- [ ] Entry Strategy planners (scope: NEW_TRADE)
  - [ ] `SWOTMomentumPlanner` (SWOT-driven entry decisions)
  - [ ] `BreakoutPlanner` (pattern-based entries)
- [ ] Position Management planners (scope: MODIFY_EXISTING)
  - [ ] `TrailingStopPlanner` → StrategyDirective (MODIFY_EXISTING)
  - [ ] `PartialProfitPlanner` → StrategyDirective (MODIFY_EXISTING)
- [ ] Risk Control planners (scope: CLOSE_EXISTING)
  - [ ] `EmergencyExitPlanner` → StrategyDirective (CLOSE_EXISTING)
  - [ ] `DrawdownLimiter` → StrategyDirective (CLOSE_EXISTING)
- [ ] Scheduled Operation planners (scope: NEW_TRADE)
  - [ ] `DCAPlanner` → StrategyDirective (NEW_TRADE, trigger: schedule)
  - [ ] `RebalancingPlanner` → StrategyDirective (MODIFY_EXISTING, trigger: schedule)
- [ ] Integration tests: StrategyPlanner → StrategyDirective → Planning → Execution

**Note**: All StrategyPlanners have 1-op-1 relationship with strategy. Grouping above is for documentation only (not enforced via subtypes).

**Parkeren:**
- [ ] Timeout handling (wat bij missing plans?)
- [ ] Partial plan completion policy
- [ ] Retry logic voor failed planners
- [ ] Performance monitoring

**Referenties:**
- **STRATEGY PIPELINE ARCHITECTURE**: `docs/development/STRATEGY_PIPELINE_ARCHITECTURE.md` ⭐ **LEIDEND DOCUMENT**
- **ROUTING PLANNER DEEP DIVE**: `docs/development/ROUTING_PLANNER_DEEP_DIVE.md` (execution tactics explained)
- V2 Architectuur: `ST2/docs/system/S1mpleTrader V2 Architectuur.md` (PlanningPhase sub-categorieën)
- SWOT Framework: `docs/development/decision_framework.md`
- V2→V3 Analysis (archived): `docs/development/#Archief/v2_to_v3_execution_mapping.md`
- **TriggerContext Causality**: `backend/dtos/causality.py` (immutable causality chain)

---

### 🔗 Causality Tracking Architecture

**Prioriteit:** CRITICAL - Foundation for Journal Reconstruction  
**Status:** Implemented  
**Besluit Datum:** 2025-10-26

#### TriggerContext: The Immutable Causality Chain

**Core Concept:**
TriggerContext is een immutable DTO die door de **hele pijplijn** vloeit, waarbij elke worker zijn output ID toevoegt. FlowTerminator gebruikt deze IDs om de volledige decision chain in de Strategy Journal te reconstrueren.

**Design Principes:**
1. **Immutability Pattern**: Workers kopiëren + uitbreiden, nooit muteren
2. **Flexible Fields**: Verschillende worker types vullen verschillende fields
3. **Universal Usage**: ALLE pipeline DTOs hebben een `causality: TriggerContext` field
4. **Journal Reconstruction**: FlowTerminator query't Journal met IDs uit TriggerContext

**Pipeline Flow:**
```python
# OpportunityWorker
ctx = TriggerContext(opportunity_ids=["OPP_123"])

# StrategyPlanner
ctx = ctx.model_copy(update={"strategy_directive_id": "STR_456"})

# Planners (copy forward, add plan IDs)
ctx = ctx.model_copy(update={"entry_plan_id": "ENT_789"})
ctx = ctx.model_copy(update={"size_plan_id": "SIZ_012"})
ctx = ctx.model_copy(update={"exit_plan_id": "EXT_345"})
ctx = ctx.model_copy(update={"routing_plan_id": "ROU_678"})

# DirectiveAssembler
ctx = ctx.model_copy(update={"execution_directive_id": "EXE_901"})

# FlowTerminator reconstructs:
# OPP_123 → STR_456 → ENT_789/SIZ_012/EXT_345/ROU_678 → EXE_901
journal.query(opportunity_ids=ctx.opportunity_ids) → OpportunitySignal
journal.query(directive_id=ctx.strategy_directive_id) → StrategyDirective
journal.query(plan_id=ctx.entry_plan_id) → EntryPlan
# Complete decision chain reconstructed!
```

**Worker Type Field Usage:**
- **SWOT Entry**: opportunity_ids, threat_ids, context_assessment_id
- **Position Management**: monitored_position_ids, trigger_tick
- **Risk Control**: threat_ids, trigger_event
- **Scheduled Operations**: schedule_trigger

**Implementation Status:**
- [x] TriggerContext DTO (`backend/dtos/causality.py`) ✅
- [x] 15 unit tests passing ✅
- [x] Extracted from StrategyDirective (previously embedded) ✅
- [ ] Add `causality: TriggerContext` field to all pipeline DTOs:
  - [ ] OpportunitySignal
  - [ ] ThreatSignal
  - [ ] StrategyDirective (already has trigger_context) ✅
  - [ ] EntryPlan, SizePlan, ExitPlan, RoutingPlan
  - [ ] ExecutionDirective
- [ ] FlowTerminator implementation (Journal reconstruction logic)

**Architectural Impact:**
- **FlowTerminator** is het ENIGE component dat TriggerContext gebruikt voor Journal queries
- Alle andere workers kopiëren het alleen door (immutability pattern)
- Journal reconstruction gebeurt centraal in FlowTerminator (single responsibility)

**Zie ook:** `backend/dtos/causality.py` voor volledige documentatie en usage examples.

---

### 🔄 V3 Architecture Decisions - ExecutionWorker Migration

**Prioriteit:** CRITICAL - Architectural Foundation  
**Status:** Architecture Finalized  
**Besluit Datum:** 2025-10-26

#### Kernbevindingen

**ExecutionWorker Plugin Category VERDWIJNT**. Reden: Verkeerde scheiding tussen platform orchestratie en quant logic.

**V2 ExecutionWorker Subtypes → V3 Mapping**:

1. **TRADE_INITIATION** → ❌ VERWIJDERD
   - V2: DefaultPlanExecutor (plugin) - uitvoeren van trade plans
   - V3: ExecutionHandler (existing interface) + EventAdapter (generic wiring)
   - ExecutionHandler.execute_plan() returnt DispositionEnvelope (STOP)
   - EventAdapter routes STOP → _flow_stop event → FlowTerminator
   
2. **POSITION_MANAGEMENT/RISK_SAFETY/OPERATIONAL** → ✅ StrategyPlanner
   - V2: Aparte ExecutionWorker categorie
   - V3: StrategyPlanner workers (1-op-1 met strategie)
   - Output: StrategyDirective (scope: MODIFY_EXISTING, CLOSE_EXISTING, NEW_TRADE)
   - Examples: TrailingStopPlanner, EmergencyExitPlanner, DCAPlanner
   - **Geen nieuwe plugin categorie** - gebruik bestaande StrategyPlanner

#### Architecturale Principes

**1. Bus-Agnostic Workers**:
- Workers hebben GEEN EventBus dependency
- Return DispositionEnvelope (CONTINUE/PUBLISH/STOP)
- EventAdapter (generic) handles event routing

**2. StrategyPlanner = 1-op-1 Relationship**:
- Elke strategie heeft precies 1 StrategyPlanner
- Geen enforced subtypes (documentatie only)
- TrailingStopPlanner, EmergencyExitPlanner, DCAPlanner = allemaal StrategyPlanners
- Scope field in StrategyDirective (NEW_TRADE, MODIFY_EXISTING, CLOSE_EXISTING)

**3. Platform Components (Event-Driven)**:
- DirectiveAssembler: Aggregates 4 plans → ExecutionDirective
- ExecutionHandler: Executes directive via Tradable (Portfolio)
- FlowTerminator: Journaling, cleanup, metrics (uniform flow termination)

**4. Event Flow**:
```
StrategyPlanner → StrategyDirective
    ↓
4 Sub-Planners → EntryPlan, SizePlan, ExitPlan, RoutingPlan
    ↓ (via EventAdapter)
DirectiveAssembler → ExecutionDirective → EXECUTION_DIRECTIVE_READY
    ↓ (via EventAdapter)
ExecutionHandler → STOP disposition → _flow_stop
    ↓ (via EventAdapter)
FlowTerminator → Journaling + Cleanup
```

**Zie ook**: `docs/development/#Archief/` voor volledige analyse en verworpen concepten.

---

## 🚀 Implementatie Pipeline

### Foundation DTOs (In Progress)

**Status:** 3/7 Complete

**System DTOs** (SWOT Framework):
- [x] DispositionEnvelope (21 tests passing)
- [x] OpportunitySignal (30 tests passing)
- [x] ThreatSignal (26 tests passing)
- [x] ContextFactor (28 tests passing)
- [x] AggregatedContextAssessment (14 tests passing)

**Planning DTOs** (Strategy Planning):
- [ ] EntryPlan
- [ ] SizePlan
- [ ] ExitPlan
- [ ] RoutingPlan
- [ ] ExecutionDirective

**SWOT Planning DTOs** (Optioneel - voor complexe strategieën):
- [ ] StrategyDirective + sub-directives

**Next Steps:**
1. **START**: Implement EntryPlan, SizePlan, ExitPlan, RoutingPlan, ExecutionDirective
2. Implement OpportunityTrigger + PlanningAggregator (direct mode)
3. Build reference planners (ImmediateMarketEntry, FixedRiskSizer, etc.)
4. End-to-end test: Opportunity → ExecutionDirective
5. **LATER**: Add SWOT mode support (StrategyDirective, PlannerMatcher)

---

## 📚 Documentation Updates Needed

### Agent.md Additions
- [ ] Add SWOT framework section
- [ ] Document severity vs confidence consistency
- [ ] Add plugin documentation guidelines

### Architecture Docs
- [ ] Update worker taxonomie with SWOT mapping
- [ ] Document confrontation matrix concept
- [ ] Add i18n policy decision (when finalized)

---

## 🧪 Testing & Quality

### Test Coverage Goals
- [x] ID Generators: 26/26 tests passing
- [x] DispositionEnvelope: 21/21 tests passing
- [x] OpportunitySignal: 30/30 tests passing
- [x] ThreatSignal: 26/26 tests passing

**Total:** 103/103 current tests passing ✅

### Code Quality Metrics
- [x] Max line length: 100 chars
- [x] No trailing whitespace
- [x] Pylance/lint clean
- [x] File header convention applied

---

## 💡 Future Considerations

### Potential Enhancements
- [ ] Visualization tools for SWOT analysis
- [ ] Confrontation matrix debugging UI
- [ ] Plugin documentation browser
- [ ] i18n layer for user-facing features

### Research Topics
- [ ] Optimal confrontation algorithms
- [ ] Dynamic threshold adjustment
- [ ] Multi-timeframe SWOT analysis
- [ ] Machine learning integration with SWOT scores

---

**Last Updated:** 2025-10-24  
**Maintained By:** Development Team  
**Review Frequency:** Weekly
