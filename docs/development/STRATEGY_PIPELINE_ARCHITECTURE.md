# Strategy Pipeline Architecture - S1mpleTraderV3

**Status:** Definitief - Leidend Document  
**Versie:** 3.0  
**Laatst Bijgewerkt:** 2025-10-27

---

## Executive Summary

Dit document beschrijft de **volledige strategie pipeline** van S1mpleTraderV3 - van market tick tot trade execution. Het is het **enige leidende document** voor pipeline architectuur discussies.

**Kernprincipes:**
1. **Confidence-Driven Specialization** - Hyper-gefocuste planners filteren op confidence scores
2. **Plugin-First** - Alle quant logica in configureerbare plugins
3. **Bus-Agnostic Workers** - Geen EventBus dependency, pure DispositionEnvelope pattern
4. **SRP Overal** - Elke component één verantwoordelijkheid, dynamiek via aparte workers
5. **Platform = Framework** - Quant plugt specialisten in via YAML, geen code wijzigingen

---

## Pipeline Overzicht - De 6+1 Fases

```
┌─────────────────────────────────────────────────────────────────┐
│ Fase 0: BOOTSTRAPPING                                           │
│ - Build rolling window voor alle timeframes                     │
│ - Initialiseer workers en event wirings                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Fase 1a: CONTEXT ANALYSE (Sequential)                           │
│ Workers: ContextWorker (7 subtypes)                             │
│ Doel: Markt "kaart" - Sterktes & Zwaktes ontdekken             │
│ Output: Verrijkte TradingContext (enriched_df)                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Fase 1b: CONTEXT AGGREGATIE (Platform Component)                │
│ Component: ContextAggregator                                     │
│ Doel: Compleet zicht op markt binnen deze tick                  │
│ Output: AggregatedContextAssessment (strength/weakness scores)   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ↓                                           ↓
┌──────────────────────┐                 ┌──────────────────────┐
│ Fase 2a: OPPORTUNITY │  (Parallel)     │ Fase 2b: THREATS     │
│ Detectie             │                 │ Detectie             │
│                      │                 │                      │
│ Workers: 7 subtypes  │                 │ Workers: 5 subtypes  │
│ Output: Opportunity  │                 │ Output: ThreatSignal │
│ Signal (confidence)  │                 │ (severity)           │
└──────────────────────┘                 └──────────────────────┘
        │                                           │
        └─────────────────────┬─────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Fase 3: STRATEGY PLANNING (Confrontatie)                        │
│ Worker: StrategyPlanner (1-op-1 met strategie)                  │
│ Input: SWOT Quadranten (Context + Opportunity + Threat)         │
│ Logica: Confrontatie matrix, gekwantificeerde beslissing        │
│ Output: StrategyDirective (confidence + 4 sub-directives)        │
│                                                                  │
│ KNOOPPUNT voor iteratieve strategieën:                          │
│ - Scheduled (DCA, rebalancing)                                  │
│ - Position management (trailing stops, partial exits)           │
│ - Risk control (emergency exits, drawdown limiters)             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Fase 4a: TRADE PLANNING (Parallel + Sequential)                 │
│                                                                  │
│ PARALLEL PHASE: (confidence-filtered specialisten)              │
│ ├─ EntryPlanner   → EntryPlan   (WHAT/WHERE trade)             │
│ ├─ SizePlanner    → SizePlan    (HOW MUCH)                     │
│ └─ ExitPlanner    → ExitPlan    (WHERE OUT)                    │
│                                                                  │
│ SEQUENTIAL PHASE: (krijgt context van eerdere plannen)          │
│ └─ RoutingPlanner → RoutingPlan (HOW/WHEN execute)             │
│                                                                  │
│ Config-driven filtering: Quant definieert confidence ranges     │
│ - AggressiveMarketEntry: confidence [0.8-1.0]                   │
│ - PatientLimitEntry:     confidence [0.3-0.7]                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Fase 4b: TRADE PLAN AGGREGATIE (Platform Component)             │
│ Component: PlanningAggregator                                    │
│ Input: 4 Plan DTOs (Entry, Size, Exit, Routing)                │
│ Output: ExecutionDirective (complete execution package)         │
│ Event: EXECUTION_DIRECTIVE_READY                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Fase 5: EXECUTION (Environment-dependent)                       │
│ Component: ExecutionHandler (interface)                         │
│ Implementations:                                                 │
│ - BacktestHandler   → Direct ledger registration                │
│ - PaperHandler      → Paper trading simulation                  │
│ - LiveHandler       → Exchange API connector                    │
│ Output: DispositionEnvelope (STOP → _flow_stop event)          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Fase 6: RUN FINALE (Cleanup & Logging)                          │
│ Component: FlowTerminator                                        │
│ Responsibilities:                                                │
│ - Causality reconstruction (Journal queries via TriggerContext) │
│ - Logging & metrics                                             │
│ - Component cleanup & garbage collection                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Fase 0: Bootstrapping

**Doel:** Voorbereiden van de pipeline voor eerste "echte" tick

**Verantwoordelijkheden:**
1. **Rolling Window Opbouw**
   - Verzamel historische data voor alle timeframes
   - Vul indicators voor correcte initialisatie
   - Wacht tot minimum window size bereikt

2. **Worker Initialisatie**
   - Instantieer alle workers volgens workforce config
   - Inject capabilities (state, events, journaling)
   - Valideer dependencies

3. **Event Wiring**
   - Assembleer EventAdapters volgens wiring_map.yaml
   - Koppel event listeners aan publishers
   - Valideer event chain (geen circulaire refs)

**Output:** Klaar-voor-tick systeem

**Zie ook:** Bootstrap Workflow in `agent.md`

---

## Fase 1a: Context Analyse - "De Cartograaf"

**Rol:** Objectief en beschrijvend - "Dit is wat er is"

**Verantwoordelijkheid:**
- Verrijk micro market data (tick) met objectieve informatie
- Ontdek **Sterktes** en **Zwaktes** in de markt
- Geen filtering, geen oordelen - pure data verrijking

**Worker Type:** `ContextWorker` (7 subtypes)

**Execution:** Sequential chain-through
- Workers bouwen op elkaars output
- EventAdapters bedraad volgens wiring_map.yaml
- Laatste worker output = verrijkte TradingContext

**Input:** Raw OHLCV data (current tick + historical window)

**Process:**
```python
# Voorbeeld: ICT/SMC Strategie
context_workers:
  - MarketStructureDetector  # → adds: trend_direction, is_bos, is_choch
  - EMADetector              # → adds: ema_20, ema_50, ema_200
  - ADXRegimeClassifier      # → adds: regime ('trending'/'ranging')
```

**Output:**
- `TradingContext.enriched_df` - DataFrame met alle toegevoegde kolommen
- Event: `CONTEXT_READY` (trigger voor Fase 2)

**SWOT Mapping:** Dit is waar **Strengths** & **Weaknesses** worden verzameld

---

## Fase 1b: Context Aggregatie

**Component:** `ContextAggregator` (Platform worker, bus-agnostic)

**Verantwoordelijkheid:**
- Aggregeer atomaire context outputs → AggregatedContextAssessment
- Produceer **strength** en **weakness** scores (0.0-1.0)
- Symmetrie met Opportunity.confidence en Threat.severity
- Wired via EventAdapter: luistert naar laatste ContextWorker output

**Configuratie:** `aggregation_policy.yaml` (platform config)
```yaml
aggregation:
  method: "weighted_average"  # of "max", "consensus"
  weights:
    trend_strength: 0.4
    regime_clarity: 0.3
    structure_quality: 0.3
```

**Output:**
```python
AggregatedContextAssessment(
    assessment_id="CTX_20251027_143022_a8f3c",
    strength: Decimal("0.75"),  # Sterke trend, goede structuur
    weakness: Decimal("0.20"),  # Lage volatiliteit
    contributing_factors=[...]  # Welke context workers bijdroegen
)
```

**Event:** `CONTEXT_ASSESSMENT_READY`

---

## Fase 2a: Opportunity Detection - "De Verkenner"

**Rol:** Probabilistisch en creatief - "Ik zie een mogelijkheid"

**Verantwoordelijkheid:**
- Herken handelskansen op basis van patronen/theorieën
- Genereer "handelsideeën" zonder concrete plannen
- Filter op basis van strategische criteria

**Worker Type:** `OpportunityWorker` (7 subtypes)

**Execution:** Parallel
- Alle workers ontvangen dezelfde TradingContext
- EventAdapters fire workers simultaan
- Genereren onafhankelijke signalen

**Input:** Verrijkte TradingContext (uit Fase 1)

**Process:**
```python
# Meerdere opportunity detectors parallel
opportunity_workers:
  - FVGEntryDetector        # → FVG pattern na structure break
  - VolumeSpikeRefiner      # → Validates volume confirmation
  - DivergenceScanner       # → RSI divergence signals
```

**Output:**
```python
OpportunitySignal(
    signal_id="OPP_20251027_143022_a8f3c",
    timestamp=datetime.now(UTC),
    asset="BTCUSDT",
    direction="BUY",
    signal_type="fvg_entry",
    confidence=Decimal("0.85"),  # ← Cruciaal voor Fase 4 filtering!
    metadata={"gap_size": 8.5, "volume_percentile": 85}
)
```

**Event:** `OPPORTUNITY_DETECTED` (per signaal)

**SWOT Mapping:** Dit is waar **Opportunities** worden ontdekt

---

## Fase 2b: Threat Detection - "De Waakhond"

**Rol:** Vigilant en defensief - "Let op gevaar!"

**Verantwoordelijkheid:**
- Monitor risico's, bedreigingen, afwijkingen
- Publiceert waarschuwingen (handelt NOOIT zelf)
- Parallel aan Opportunity Detection

**Worker Type:** `ThreatWorker` (5 subtypes)

**Execution:** Event-Driven
- EventAdapters wired volgens manifest triggers
- Sommige op `TICK_RECEIVED`, sommige op `LEDGER_UPDATE`
- Parallel aan Opportunity Detection

**Input:**
- TradingContext (market data)
- StrategyLedger (open positions, P&L)

**Process:**
```python
threat_workers:
  - MaxDrawdownMonitor      # → Watches portfolio drawdown
  - CorrelationBreachDetector  # → Market correlation anomalies
  - LiquidityCrisisDetector    # → Order book depth issues
```

**Output:**
```python
ThreatSignal(
    threat_id="THR_20251027_143025_b7c4d",
    timestamp=datetime.now(UTC),
    threat_type="MAX_DRAWDOWN_BREACH",
    severity=Decimal("0.90"),  # 0.0-1.0 (CRITICAL)
    source_worker_id="max_drawdown_monitor",
    metadata={"current_dd": 0.08, "max_allowed": 0.05}
)
```

**Event:** `THREAT_DETECTED`

**SWOT Mapping:** Dit is waar **Threats** worden ontdekt

---

## Fase 3: Strategy Planning - "De Confrontatiematrix"

**Rol:** Strategisch en kwantitatief - "Hier is mijn cijfermatige beslissing"

**Verantwoordelijkheid:**
- **SWOT Confrontatie** - Combineer alle 4 quadranten
- Produceer **confidence score** voor trade planners
- **Knooppunt** voor iteratieve strategieën (scheduled, position management)

**Worker Type:** `StrategyPlanner` (1-op-1 met strategie)

**Subtypes (documentatie only, niet enforced):**
- SWOT Entry Strategies (nieuwe trades)
- Position Management (trailing stops, partial exits)
- Risk Control (emergency exits, drawdown limiters)
- Scheduled Operations (DCA, rebalancing)

**Input:**
```python
# SWOT Quadranten
context_assessment: AggregatedContextAssessment  # S & W
opportunity_signals: list[OpportunitySignal]     # O
threat_signals: list[ThreatSignal]               # T
```

**Confrontatie Logica (quant-specifiek):**
```python
class AdaptiveMomentumPlanner(BaseStrategyPlanner):
    def confront(self, swot: SWOTInputs) -> StrategyDirective:
        # Voorbeeld SWOT formule
        confidence = (
            swot.context.strength * 0.3 +
            swot.opportunity.confidence * 0.5 -
            swot.threat.severity * 0.2
        )
        
        return StrategyDirective(
            confidence=confidence,  # ← Kern output!
            entry_directive=EntryDirective(
                timing_preference=confidence,  # High conf = urgent
                symbol="BTCUSDT",
                direction="BUY"
            ),
            size_directive=SizeDirective(
                aggressiveness=confidence * 0.8,
                max_risk_amount=Decimal("1000.00")
            ),
            # ... exit & routing directives
        )
```

**Output:**
```python
StrategyDirective(
    directive_id="STR_20251027_143030_c8e6f",
    causality=CausalityChain(...),  # All SWOT IDs
    
    # De kern: Confidence score voor planners
    confidence=Decimal("0.82"),
    
    # Hints (geen orders!) voor trade planners
    entry_directive=EntryDirective(
        timing_preference=Decimal("0.82"),
        preferred_price_zone=PriceZone(...)
    ),
    size_directive=SizeDirective(
        aggressiveness=Decimal("0.66"),
        max_risk_amount=Decimal("1000")
    ),
    exit_directive=ExitDirective(
        profit_taking_preference=Decimal("0.75"),
        risk_reward_ratio=Decimal("2.5")
    ),
    routing_directive=RoutingDirective(
        execution_urgency=Decimal("0.82")
    ),
    
    # Scope (voor position management planners)
    scope="NEW_TRADE",  # of MODIFY_EXISTING, CLOSE_EXISTING
    target_trade_ids=[]
)
```

**Event:** `STRATEGY_DIRECTIVE_ISSUED`

**Iteratieve Strategieën:**
- **Scheduled triggers:** DCAPlanner luistert naar `WEEKLY_DCA_TICK`
- **Position updates:** TrailingStopPlanner luistert naar `POSITION_UPDATE`
- **Output:** Allemaal StrategyDirective (zelfde DTO, andere scope)

---

## Fase 4a: Trade Planning - "Hyper-Gefocuste Specialisten"

**Rol:** Dom en gespecialiseerd - "Ik doe dit ene ding perfect"

**Verantwoordelijkheid:**
- **Geen filtering logica** - dat doet de config
- **Pure specialisatie** - één execution strategie
- **Statische output** - geen dynamische beslissingen

**Planners zijn DOM - Config is SLIM:**

### Config-Driven Filtering

```yaml
# strategy_blueprint.yaml
planning:
  entry:
    - plugin: "AggressiveMarketEntryPlanner"
      triggers:
        confidence: [0.8, 1.0]        # Alleen bij hoge confidence
        timing_preference: [0.8, 1.0] # En hoge urgency
    
    - plugin: "PatientLimitEntryPlanner"
      triggers:
        confidence: [0.3, 0.7]        # Bij medium confidence
        timing_preference: [0.0, 0.3] # En lage urgency
```

**WorkerFactory injecteert PlannerMatcher tijdens assembly:**
```python
class BaseEntryPlanner:
    # Injected by platform during assembly
    matcher: PlannerMatcher
    
    def should_handle(self, directive: StrategyDirective) -> bool:
        """Config-driven filtering - NO quant logic here."""
        return self.matcher.matches(
            confidence=directive.confidence,
            timing_pref=directive.entry_directive.timing_preference
        )
    
    def plan(self, directive: StrategyDirective) -> EntryPlan:
        """Pure specialization - quant logic here."""
        return EntryPlan(
            symbol=directive.entry_directive.symbol,
            direction=directive.entry_directive.direction,
            order_type="MARKET",  # Dit is mijn specialisme!
            limit_price=None
        )
```

### De 4 Trade Planners

**Execution Model:** Hybrid
- **Parallel:** Entry, Size, Exit (EventAdapters fire simultaan)
- **Sequential:** Routing (EventAdapter wacht op 3 plannen → fires Routing)

**Rationale:** Routing kan afhankelijk zijn van size (bijv. iceberg voor grote orders)

**Orchestration:** PlanningAggregator (platform worker) detecteert completion van parallel phase, triggert routing phase

#### 1. EntryPlanner → EntryPlan (WHAT/WHERE)

**Output:**
```python
EntryPlan(
    plan_id="ENT_20251027_143035_d9f7a",
    
    # Trade identiteit
    symbol="BTCUSDT",
    direction="BUY",
    
    # Order spec (statisch)
    order_type="MARKET",  # of LIMIT, STOP_LIMIT
    limit_price=None,
    stop_price=None
)
```

**GEEN:**
- `created_at` (redundant - timestamp in plan_id)
- `timing` (→ RoutingPlan)
- `max_slippage_pct` (→ RoutingPlan)
- `planner_id`, `rationale` (→ StrategyJournal)

**Specialisten:**
- `AggressiveMarketEntryPlanner` - confidence [0.8-1.0]
- `PatientLimitEntryPlanner` - confidence [0.3-0.7]
- `LayeredEntryPlanner` - confidence [0.5-0.9], grote positions

#### 2. SizePlanner → SizePlan (HOW MUCH)

**Output:**
```python
SizePlan(
    plan_id="SIZ_20251027_143036_e2a8b",
    
    # Position sizing (absolute values)
    position_size=Decimal("0.5"),      # BTC
    position_value=Decimal("50000.00"), # USDT
    risk_amount=Decimal("1000.00"),     # USDT risk
    leverage=Decimal("1.0")             # No leverage
)
```

**GEEN:**
- `account_risk_pct` (was input voor planner, niet output)
- `max_position_value` (constraint voor planner, niet execution param)

**Specialisten:**
- `FixedRiskSizer` - altijd 1% account risk
- `KellyCriterionSizer` - optimaal volgens Kelly
- `AggressiveSizer` - confidence [0.8-1.0] → 2% risk

#### 3. ExitPlanner → ExitPlan (WHERE OUT)

**Output:**
```python
ExitPlan(
    plan_id="EXT_20251027_143037_f3b9c",
    
    # Risk boundaries (absolute prices, statisch)
    stop_loss_price=Decimal("49500.00"),
    take_profit_price=Decimal("51000.00")  # Of None
)
```

**GEEN:**
- `trailing_stop_config` - Aparte PositionMonitor worker publiceert nieuwe ExitPlan
- `breakeven_trigger` - Aparte worker, niet in statisch plan
- `partial_exit_levels` - ExecutionHandler splits, niet hier

**Specialisten:**
- `FixedRRExitPlanner` - altijd 2:1 RR
- `StructureBasedExit` - SL onder structure, TP op liquidity
- `AggressiveExitPlanner` - confidence [0.8-1.0] → 3:1 RR

#### 4. RoutingPlanner → RoutingPlan (HOW/WHEN)

**Output:**
```python
RoutingPlan(
    plan_id="ROU_20251027_143038_g4c1d",
    
    # Execution tactics (statisch)
    timing="IMMEDIATE",  # of TWAP, LAYERED, PATIENT
    time_in_force="GTC",
    
    # Risk controls
    max_slippage_pct=Decimal("0.01"),  # 1% hard limit
    
    # Preferences (hints voor execution)
    execution_urgency=Decimal("0.82"),     # 0.0-1.0
    iceberg_preference=Decimal("0.5")      # Of None
)
```

**GEEN:**
- `twap_duration_minutes` - Platform config (uniform algorithm)
- `exchange_preference` - Platform config
- `post_only_flag` - Platform config

**Specialisten:**
- `MarketOrderRouter` - confidence [0.8-1.0] → IMMEDIATE
- `TWAPRouter` - grote orders, lage urgency
- `IcebergRouter` - position_size > threshold

---

## Fase 4b: Trade Plan Aggregatie

**Component:** `PlanningAggregator` (Platform worker, bus-agnostic)

**Verantwoordelijkheid:**
- Track welke plannen verwacht worden (4 stuks)
- Wacht tot alle plannen binnen zijn
- Aggregeer → ExecutionDirective
- Trigger Routing phase (sequential)
- Wired via EventAdapter: luistert naar ENTRY_PLAN_CREATED, SIZE_PLAN_CREATED, etc.

**Mode Detection:**
- Direct Planning: OpportunitySignal → 4 plannen
- SWOT Planning: StrategyDirective → 4 plannen

**Process:**
```
ENTRY_PLAN_CREATED  ┐
SIZE_PLAN_CREATED   ├─→ [Parallel phase complete]
EXIT_PLAN_CREATED   ┘         ↓
                    ROUTING_PLANNING_REQUESTED
                              ↓
                    ROUTING_PLAN_CREATED
                              ↓
                    [All 4 plans ready] → Aggregate
```

**Output:**
```python
ExecutionDirective(
    directive_id="EXE_20251027_143040_h5d2e",
    causality=CausalityChain(...),  # Complete chain met alle plan IDs
    
    # Aggregated plans
    entry_plan=EntryPlan(...),
    size_plan=SizePlan(...),
    exit_plan=ExitPlan(...),
    routing_plan=RoutingPlan(...)
)
```

**Event:** `EXECUTION_DIRECTIVE_READY`

---

## Fase 5: Execution

**Component:** `ExecutionHandler` (interface, environment-dependent)

**Implementations:**
- `BacktestHandler` - Direct ledger registration
- `PaperHandler` - Paper trading simulation
- `LiveHandler` - Exchange API connector

**Input:** ExecutionDirective (complete package)

**Process:**
```python
class BacktestHandler(ExecutionHandler):
    def execute(self, directive: ExecutionDirective) -> DispositionEnvelope:
        # Valideer order
        # Registreer in StrategyLedger
        # Update portfolio state
        
        return DispositionEnvelope(
            disposition=Disposition.STOP,  # Stop flow
            metadata={"trade_id": "TRD_..."}
        )
```

**Bus-Agnostic Pattern:**
- ExecutionHandler returnt STOP disposition
- EventAdapter detecteert STOP → publiceert `_flow_stop` event
- FlowTerminator luistert naar `_flow_stop`

**Output:**
- Trade geregistreerd in StrategyLedger
- DispositionEnvelope (STOP)
- Event: `_flow_stop` (via EventAdapter)

---

## Fase 6: Run Finale - FlowTerminator

**Component:** `FlowTerminator` (Platform worker, bus-agnostic)

**Verantwoordelijkheid:**
- **Causality Reconstruction** - Query StrategyJournal met TriggerContext IDs
- **Logging & Metrics** - Persisteer complete decision chain
- **Cleanup** - Garbage collection, component reset

**Input:** ExecutionDirective met complete CausalityChain

**Causality Reconstruction:**
```python
class FlowTerminator:
    def on_flow_stop(self, directive: ExecutionDirective):
        # TriggerContext bevat alle IDs
        ctx = directive.causality
        
        # Reconstruct decision chain
        opportunity = journal.query(opportunity_id=ctx.opportunity_ids[0])
        directive_obj = journal.query(directive_id=ctx.strategy_directive_id)
        entry = journal.query(plan_id=ctx.entry_plan_id)
        size = journal.query(plan_id=ctx.size_plan_id)
        exit = journal.query(plan_id=ctx.exit_plan_id)
        routing = journal.query(plan_id=ctx.routing_plan_id)
        
        # Log complete chain
        journal.write_decision_chain(...)
        
        # Cleanup
        self.cleanup_components()
```

**Output:**
- Complete causality chain in Journal
- Metrics logged
- Components cleaned
- Event: `UI_FLOW_TERMINATED` (optioneel voor UI updates)

---

## Event Flow Summary

```
TICK_RECEIVED
    ↓
CONTEXT_READY
    ↓
CONTEXT_ASSESSMENT_READY
    ↓ (parallel split)
    ├─→ OPPORTUNITY_DETECTED
    └─→ THREAT_DETECTED
         ↓ (merge)
STRATEGY_DIRECTIVE_ISSUED
    ↓ (parallel split)
    ├─→ ENTRY_PLAN_CREATED
    ├─→ SIZE_PLAN_CREATED
    └─→ EXIT_PLAN_CREATED
         ↓ (merge)
ROUTING_PLANNING_REQUESTED
    ↓
ROUTING_PLAN_CREATED
    ↓
EXECUTION_DIRECTIVE_READY
    ↓
_flow_stop (internal)
    ↓
UI_FLOW_TERMINATED
```

---

## DTO Hierarchy - Data Flow

```
Raw OHLCV
    ↓
TradingContext (enriched_df)
    ↓
AggregatedContextAssessment
    ├─→ OpportunitySignal (confidence)
    └─→ ThreatSignal (severity)
         ↓
StrategyDirective (confidence + 4 sub-directives)
    ↓ (parallel)
    ├─→ EntryPlan
    ├─→ SizePlan
    └─→ ExitPlan
         ↓ (sequential)
         └─→ RoutingPlan
              ↓
ExecutionDirective (aggregated)
    ↓
Trade (in StrategyLedger)
```

---

## Configuration Hierarchy

```
platform.yaml
    ├─ Global settings
    ├─ Logging config
    └─ Default execution params (TWAP duration, etc.)
        ↓
operation.yaml
    ├─ Connectors (exchange APIs)
    ├─ Data sources
    ├─ Environments (backtest/paper/live)
    └─ strategy_links (lijst van strategieën)
        ↓
strategy_blueprint.yaml (per strategie)
    ├─ workforce (welke workers?)
    │   ├─ context_workers: [...]
    │   ├─ opportunity_workers: [...]
    │   ├─ threat_workers: [...]
    │   ├─ strategy_planner: {...}
    │   └─ planning_workers:
    │       ├─ entry: [{plugin, triggers}, ...]
    │       ├─ size: [{plugin, triggers}, ...]
    │       ├─ exit: [{plugin, triggers}, ...]
    │       └─ routing: [{plugin, triggers}, ...]
    └─ wiring (event connections)
        ↓
plugin_manifest.yaml (per worker)
    ├─ identification (type, subtype)
    ├─ capabilities (events, state, journaling)
    ├─ dependencies (requires_dtos, provides_dtos)
    └─ config_schema (plugin-specific params)
```

---

## Architectural Patterns

### 1. Confidence-Driven Specialization

**Probleem:** Hoe kunnen quants meerdere entry strategieën pluggen zonder code wijzigingen?

**Oplossing:** Config-driven filtering op confidence ranges
```yaml
entry:
  - plugin: "Aggressive"
    triggers: {confidence: [0.8, 1.0]}
  - plugin: "Conservative"
    triggers: {confidence: [0.3, 0.6]}
```

WorkerFactory injecteert `PlannerMatcher` tijdens assembly, workers blijven dom.

### 0. Platgeslagen Orkestratie (Event-Driven)

**Architectuur:** Geen Operators - alleen EventAdapters + explicit wiring

**Pattern:**
```yaml
# wiring_map.yaml (generated from base_wiring.yaml templates)
event_wirings:
  - event: "CONTEXT_READY"
    subscribers:
      - worker: "fvg_detector"
        method: "on_context_ready"
      - worker: "breakout_scanner"
        method: "on_context_ready"
  
  - event: "ENTRY_PLAN_CREATED"
    subscribers:
      - worker: "planning_aggregator"
        method: "on_entry_plan"
```

**Geen orkestratie laag** - workers communiceren direct via events (bedraad door EventAdapters).

### 2. Bus-Agnostic Workers

**Probleem:** Workers moeten testbaar zijn zonder EventBus dependency.

**Oplossing:** DispositionEnvelope pattern
```python
# Worker returnt envelope, geen EventBus.publish()
return DispositionEnvelope(
    disposition=Disposition.PUBLISH,
    event_name="OPPORTUNITY_DETECTED",
    payload=opportunity_signal
)
```

EventAdapter (generic) handles event routing.

### 3. Statische Plan DTOs

**Probleem:** Trailing stops, breakeven rules - waar hoort dynamiek?

**Oplossing:** Aparte monitoring workers
- ExitPlan = statisch snapshot (SL = $49,500)
- TrailingStopWorker (scheduled) publiceert nieuwe ExitPlan bij update
- ExecutionHandler ziet nieuwe plan, update order

**SRP:** Plan DTOs = snapshots, Workers = dynamiek

### 4. Hybrid Execution (Parallel + Sequential)

**Probleem:** Routing kan afhankelijk zijn van size (iceberg voor grote orders).

**Oplossing:**
- Parallel: Entry, Size, Exit (EventAdapters fire simultaan)
- Sequential: Routing (PlanningAggregator wacht op 3 plannen, triggert Routing)

PlanningAggregator (platform worker) detecteert completion, publiceert `ROUTING_PLANNING_REQUESTED` event.

---

## Referenties

**Primaire Bronnen:**
- V2 Architectuur: `ST2/docs/system/S1mpleTrader V2 Architectuur.md` (proven patterns)
- V2 Pipeline: Sectie 5 - Worker Ecosysteem & Workflow

**V3 Documentatie:**
- `agent.md` - Verwijst naar dit document (niet duplicate)
- `TODO.md` - Implementation roadmap
- `backend/dtos/causality.py` - CausalityChain implementation

**Addendums (V2 - Architecturale Verschuivingen):**
- Addendum 5.1 - Expliciet Bedraad Netwerk & Platgeslagen Orkestratie ⭐ **CRITICAL**
- Addendum 3.8 - Configuratie en Vertaal Filosofie
- Point-in-Time Data Model - DTO-Centric met TickCache

---

## Changelog

**2025-10-27 - v3.0 (Definitief)**
- Complete pipeline architectuur gedefinieerd
- Confidence-driven specialization pattern toegevoegd
- Hybrid execution model (parallel + sequential) gedocumenteerd
- Bus-agnostic worker pattern formalized
- Dit is nu het leidende document (agent.md verwijst hiernaar)

---

**Einde Document**
