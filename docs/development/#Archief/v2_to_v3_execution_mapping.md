# V2 ExecutionWorker → V3 Architecture Mapping

**Document Purpose**: Systematische analyse van V2 ExecutionWorker subtypes om te bepalen wat PLATFORM ORCHESTRATION is en wat QUANT PLUGIN LOGIC blijft in V3.

**Datum**: 2025-10-26  
**Status**: Architecture Analysis

---

## Executive Summary

### Kernbevinding
**ExecutionWorker als plugin categorie VERDWIJNT in V3**. Functionaliteit splitst in 2 tracks:
1. **Platform Orchestration**: Configureerbare infrastructure (geen quant logic)
2. **Position Lifecycle Workers**: Quant plugins die StrategyDirective produceren

---

## V2 ExecutionWorker Analysis

### V2 Architecture Pattern
```
RoutingPlanner → RoutedTradePlan → [ExecutionOperator] 
                                   ↓
                          ExecutionWorker (Plugin!)
                                   ↓
                          ExecutionEnvironment → IAPIConnector
```

**V2 Assumption**: ExecutionWorker is plugin category tussen planning en broker execution.

---

## Subtype Analysis

### 1. TRADE_INITIATION

**V2 Implementatie**: `DefaultPlanExecutor`

**V2 Verantwoordelijkheden**:
```python
class DefaultPlanExecutor(BaseWorker):
    """Voert trade plannen uit."""
    
    def on_plan_ready(self, plan: RoutedTradePlan) -> DispositionEnvelope:
        # 1. Execute via provider
        result = self.execution_provider.place_order(
            asset=plan.asset,
            order_type=plan.order_type,
            price=plan.entry_price,
            size=plan.position_size
        )
        
        # 2. Update ledger
        self.ledger_provider.add_position(...)
        
        # 3. Log causality in journal
        self.journal_writer.log_entry({
            'event_type': 'TRADE_OPENED',
            'trade_id': plan.trade_id,
            'opportunity_id': plan.opportunity_id
        })
        
        return DispositionEnvelope(
            disposition="PUBLISH",
            event_name="TRADE_EXECUTED",
            payload=TradeExecutedDTO(...)
        )
```

**Analyse**:
- ❌ **GEEN quant logic** - pure orchestratie van platform services
- ✅ **PLATFORM RESPONSIBILITY**: IAPIConnector.place_order() aanroepen
- ✅ **PLATFORM RESPONSIBILITY**: Ledger updates
- ✅ **PLATFORM RESPONSIBILITY**: Causality logging
- ✅ **PLATFORM RESPONSIBILITY**: Event publicatie (TRADE_EXECUTED)

**V3 Besluit**: ❌ **NIET een plugin** - Dit is platform orchestration!

**V3 Vervanger**: `PlanExecutionOrchestrator` (platform component)

---

### 2. POSITION_MANAGEMENT

**V2 Implementaties**:
- `TrailingStopManager`
- `PartialProfitTaker`
- `ScaleInManager`
- `BreakevenMover`

**V2 Verantwoordelijkheden** (TrailingStopManager voorbeeld):
```python
class TrailingStopManager(BaseStatefulWorker):
    """Beheert trailing stops voor open posities."""
    
    def process(self, 
                context: TradingContext,
                ledger: StrategyLedger) -> None:
        
        for position in ledger.open_positions:
            current_price = context.current_price
            
            # Lees state (high water mark)
            hwm_key = f"hwm_{position.trade_id}"
            hwm = self.state.get(hwm_key, position.entry_price)
            
            # QUANT LOGIC: Bepaal nieuwe stop
            if current_price > hwm * (1 + self.params.trigger_threshold):
                new_stop = current_price * (1 - self.params.trail_distance)
                
                # Modify position
                self.execution_provider.modify_position(
                    trade_id=position.trade_id,
                    new_stop_price=new_stop
                )
                
                # Update state
                self.state.set(hwm_key, current_price)
```

**Analyse**:
- ✅ **QUANT LOGIC**: Trailing stop logica (trigger threshold, trail distance)
- ✅ **QUANT LOGIC**: High water mark tracking (stateful!)
- ✅ **QUANT LOGIC**: "Bij 2% winst, trail met 1%" = strategy decision
- ❓ **Vraag**: Hoe past dit in V3 event-driven flow?

**V3 Oplossing**: Deze workers produceren StrategyDirective!

```python
# V3 Pattern: PositionLifecycleWorker
class TrailingStopManager(EventDrivenWorker):
    """Luistert naar tick events, produceert StrategyDirective."""
    
    def on_tick(self, tick: TickData) -> DispositionEnvelope:
        # QUANT LOGIC: Bepaal of trailing stop nodig is
        for position in self.ledger.open_positions:
            if self._should_trail(position, tick.price):
                # Produceer MODIFY_EXISTING directive
                directive = StrategyDirective(
                    strategy_planner_id="trailing_stop_manager",
                    scope=DirectiveScope.MODIFY_EXISTING,
                    target_trade_ids=[position.trade_id],
                    exit_directive=ExitDirective(
                        stop_loss_tolerance=Decimal("0.01")  # Trail met 1%
                    ),
                    confidence=Decimal("1.0"),
                    rationale="Trailing stop triggered at +2% profit"
                )
                
                return DispositionEnvelope(
                    disposition="PUBLISH",
                    event_name="STRATEGY_DIRECTIVE_ISSUED",
                    payload=directive
                )
        
        return DispositionEnvelope.CONTINUE()
```

**Flow in V3**:
```
[TrailingStopManager] → StrategyDirective (MODIFY_EXISTING)
    ↓
[EventAdapter] → STRATEGY_DIRECTIVE_ISSUED event
    ↓
[ExitPlanner] reads directive.exit_directive → ExitPlan (updated stop)
    ↓
[PlanningAggregator] → ExecutionDirective
    ↓
[PlanExecutionOrchestrator] → IAPIConnector.modify_order()
```

**V3 Besluit**: ✅ **WEL een plugin** - Dit is quant logic!

**V3 Category**: `PositionLifecycleWorker` (nieuwe categorie)

---

### 3. RISK_SAFETY

**V2 Implementaties**:
- `EmergencyExitAgent`
- `CircuitBreaker`
- `CorrelationMonitor`
- `DrawdownLimiter`

**V2 Verantwoordelijkheden** (EmergencyExitAgent):
```python
class EmergencyExitAgent(EventDrivenWorker):
    """Forceert exits bij kritieke threats."""
    
    def on_threat_detected(self, threat: CriticalEvent) -> DispositionEnvelope:
        # QUANT LOGIC: Severity threshold
        if threat.severity >= self.params.exit_threshold:
            # Close all positions
            for position in self.ledger.open_positions:
                self.execution_provider.close_position(
                    trade_id=position.trade_id,
                    reason=f"Emergency exit: {threat.threat_type}"
                )
            
            return DispositionEnvelope(
                disposition="PUBLISH",
                event_name="EMERGENCY_EXIT_EXECUTED"
            )
```

**Analyse**:
- ✅ **QUANT LOGIC**: Severity threshold beslissing
- ✅ **QUANT LOGIC**: "Bij welk threat level exit ik alles?" = strategy decision
- ❓ **Vraag**: Is dit fundamenteel anders dan TrailingStopManager?

**V3 Oplossing**: Zelfde pattern! Produceer StrategyDirective!

```python
# V3 Pattern: PositionLifecycleWorker
class EmergencyExitAgent(EventDrivenWorker):
    """Luistert naar threat events, produceert CLOSE directives."""
    
    def on_threat_detected(self, threat: CriticalEvent) -> DispositionEnvelope:
        # QUANT LOGIC: Severity threshold
        if threat.severity >= self.params.exit_threshold:
            # Produceer CLOSE_EXISTING directive
            directive = StrategyDirective(
                strategy_planner_id="emergency_exit_agent",
                scope=DirectiveScope.CLOSE_EXISTING,
                target_trade_ids=[p.trade_id for p in self.ledger.open_positions],
                contributing_signals=ContributingSignals(
                    threat_ids=[threat.threat_id]
                ),
                confidence=Decimal("1.0"),
                rationale=f"Emergency exit: {threat.threat_type}"
            )
            
            return DispositionEnvelope(
                disposition="PUBLISH",
                event_name="STRATEGY_DIRECTIVE_ISSUED",
                payload=directive
            )
```

**V3 Besluit**: ✅ **WEL een plugin** - Dit is quant logic!

**V3 Category**: `PositionLifecycleWorker` (subcategorie RISK_CONTROL)

---

### 4. OPERATIONAL

**V2 Implementaties**:
- `DCAExecutor` (weekly/daily scheduled DCA)
- `RebalancingAgent` (portfolio rebalancing)
- `HedgeManager` (correlation-based hedging)

**V2 Verantwoordelijkheden** (DCAExecutor):
```python
class DCAExecutor(EventDrivenWorker):
    """Voert wekelijkse DCA uit."""
    
    def on_weekly_tick(self, payload: dict) -> DispositionEnvelope:
        # QUANT LOGIC: DCA strategy
        portfolio = self.ledger_provider.get_current_state()
        
        if portfolio.cash_available > self.params.min_cash:
            # Place DCA order
            self.execution_provider.place_order(
                asset=self.params.target_asset,
                order_type="MARKET",
                size=self.params.dca_amount
            )
        
        return DispositionEnvelope(
            disposition="PUBLISH",
            event_name="DCA_ORDER_PLACED"
        )
```

**Analyse**:
- ✅ **QUANT LOGIC**: DCA schema (weekly, daily, etc.)
- ✅ **QUANT LOGIC**: DCA amount calculation
- ✅ **QUANT LOGIC**: "Koop elke week €100" = strategy decision
- ❓ **Vraag**: Is dit een nieuwe trade of position management?

**V3 Oplossing**: DCA is NEW_TRADE creation! Produceer StrategyDirective!

```python
# V3 Pattern: PositionLifecycleWorker (SCHEDULED subcategorie)
class DCAExecutor(EventDrivenWorker):
    """Luistert naar scheduler events, produceert NEW_TRADE directives."""
    
    def on_weekly_tick(self, tick_event: ScheduledTick) -> DispositionEnvelope:
        # QUANT LOGIC: DCA strategy
        if self._should_execute_dca():
            # Produceer NEW_TRADE directive
            directive = StrategyDirective(
                strategy_planner_id="dca_executor",
                scope=DirectiveScope.NEW_TRADE,
                target_trade_ids=[],
                entry_directive=EntryDirective(
                    symbol=self.params.target_asset,
                    direction="BUY",
                    timing_preference=Decimal("1.0")  # IMMEDIATE
                ),
                size_directive=SizeDirective(
                    max_risk_amount=Decimal(str(self.params.dca_amount))
                ),
                confidence=Decimal("1.0"),
                rationale="Scheduled DCA execution"
            )
            
            return DispositionEnvelope(
                disposition="PUBLISH",
                event_name="STRATEGY_DIRECTIVE_ISSUED",
                payload=directive
            )
```

**V3 Besluit**: ✅ **WEL een plugin** - Dit is quant logic!

**V3 Category**: `PositionLifecycleWorker` (subcategorie SCHEDULED_OPERATIONS)

---

## V3 Architecture Summary

### What DISAPPEARS
❌ **ExecutionWorker plugin category** - Artificial boundary in V2

### What EMERGES

#### 1. Platform Component: `PlanExecutionOrchestrator`

**Type**: Platform component (NIET plugin)  
**Configured via**: `platform.yaml`  
**Responsibilities**:
1. Luistert naar `EXECUTION_DIRECTIVE_READY` event
2. Valideert ExecutionDirective completeness
3. Roept `IAPIConnector.place_order(directive)` aan
4. Updates ledger (position tracking)
5. Logs causality (complete flow trace)
6. Publiceert `TRADE_EXECUTED` event
7. Fired STOP disposition (flow termination)
8. Triggers cleanup (component termination, garbage collection, UI updates)

**NOT Responsible For**:
- ❌ Quant logic (trailing stops, DCA schema, etc.)
- ❌ Strategy decisions (die komen van PositionLifecycleWorkers)

**Code Example** (conceptueel):
```python
# backend/core/orchestration/plan_execution_orchestrator.py
class PlanExecutionOrchestrator:
    """Platform component for executing ExecutionDirectives."""
    
    def __init__(
        self, 
        api_connector: IAPIConnector,
        ledger_provider: ILedgerProvider,
        journal_writer: IJournalWriter,
        event_bus: IEventBus
    ):
        self._api_connector = api_connector
        self._ledger = ledger_provider
        self._journal = journal_writer
        self._event_bus = event_bus
    
    def on_execution_directive_ready(
        self, 
        directive: ExecutionDirective
    ) -> None:
        """
        Platform orchestration: Execute directive via IAPIConnector.
        
        This is NOT quant logic - pure infrastructure orchestration.
        """
        # 1. Validate directive completeness
        self._validate_directive(directive)
        
        # 2. Execute via API connector
        order_result = self._api_connector.place_order(directive)
        
        # 3. Update ledger
        position = self._ledger.add_position(
            trade_id=directive.trade_id,
            symbol=directive.entry_plan.symbol,
            entry_price=directive.entry_plan.reference_price,
            size=directive.size_plan.position_size
        )
        
        # 4. Log causality (complete flow trace)
        self._journal.log_trade_opened({
            'event_type': 'TRADE_OPENED',
            'trade_id': str(directive.trade_id),
            'strategy_id': directive.strategy_id,
            'trigger_context': directive.trigger_context,
            'timestamp': directive.timestamp,
            'order_result': order_result
        })
        
        # 5. Publish TRADE_EXECUTED event
        self._event_bus.publish(
            event_name="TRADE_EXECUTED",
            payload=TradeExecutedDTO(
                trade_id=directive.trade_id,
                execution_time=datetime.now(),
                fill_price=order_result['fill_price']
            )
        )
        
        # 6. Fire STOP disposition (flow termination)
        # This triggers platform cleanup (component termination, 
        # garbage collection, UI updates)
        self._event_bus.publish(
            event_name="_flow_stop_success",
            payload=FlowCompletionDTO(
                flow_id=directive.directive_id,
                reason="Trade execution complete"
            )
        )
```

**Configuration** (`platform.yaml`):
```yaml
orchestration:
  plan_execution:
    enabled: true
    timeout_seconds: 30
    retry_policy:
      max_retries: 3
      backoff_strategy: "exponential"
    error_handling:
      on_api_failure: "rollback_ledger"
      on_ledger_failure: "alert_admin"
```

---

#### 2. New Plugin Category: `PositionLifecycleWorker`

**Type**: Plugin category (quant logic)  
**Configured via**: `strategy_blueprint.yaml`  
**Responsibilities**:
- Monitor open positions (via ledger)
- Apply quant logic (trailing stops, partials, DCA schema, etc.)
- Produce StrategyDirective (MODIFY_EXISTING, CLOSE_EXISTING, NEW_TRADE)

**Subcategories**:
1. **DYNAMIC_MANAGEMENT** (V2 POSITION_MANAGEMENT)
   - TrailingStopManager
   - PartialProfitTaker
   - ScaleInManager
   - BreakevenMover

2. **RISK_CONTROL** (V2 RISK_SAFETY)
   - EmergencyExitAgent
   - CircuitBreaker
   - DrawdownLimiter
   - CorrelationMonitor

3. **SCHEDULED_OPERATIONS** (V2 OPERATIONAL)
   - DCAExecutor
   - RebalancingAgent
   - HedgeManager

**Output**: StrategyDirective (scope: MODIFY_EXISTING, CLOSE_EXISTING, or NEW_TRADE)

**Event Flow**:
```
[PositionLifecycleWorker] → StrategyDirective
    ↓
STRATEGY_DIRECTIVE_ISSUED event
    ↓
[Planning Layer] → 4 Planners → ExecutionDirective
    ↓
EXECUTION_DIRECTIVE_READY event
    ↓
[PlanExecutionOrchestrator] → IAPIConnector
```

---

## Key Architectural Insights

### 1. IAPIConnector is the PLATFORM BOUNDARY
```python
# V2 had this RIGHT - ExecutionDirective goes DIRECTLY to IAPIConnector
def place_order(self, directive: ExecutionDirective) -> Dict[str, Any]:
    """Platform interface - NO plugin logic between this and planners!"""
```

### 2. StrategyDirective is the UNIVERSAL TRIGGER
Position lifecycle workers don't execute directly - they produce directives:
- TrailingStopManager → StrategyDirective (MODIFY_EXISTING)
- EmergencyExitAgent → StrategyDirective (CLOSE_EXISTING)
- DCAExecutor → StrategyDirective (NEW_TRADE)

ALL go through Planning Layer → ExecutionDirective → PlanExecutionOrchestrator

### 3. ExecutionDirective is ALWAYS the final step
No exceptions:
- New trade from SWOT → ExecutionDirective
- New trade from Opportunity → ExecutionDirective
- Modify position from TrailingStop → ExecutionDirective
- Close position from EmergencyExit → ExecutionDirective

### 4. PlanningAggregator is MODE-AGNOSTIC
```python
class PlanningAggregator:
    """Tracks planning completion, aggregates ExecutionDirective."""
    
    def on_strategy_directive_issued(self, directive: StrategyDirective):
        # SWOT mode - role-based planner selection
        self._track_planning(directive)
    
    def on_plan_entry_requested(self, signal: OpportunitySignal):
        # Direct mode - fixed planner assignment
        self._track_planning(signal)
```

---

## Implementation Roadmap

### Phase 1: Platform Orchestration (CRITICAL)
- [ ] **PlanExecutionOrchestrator** platform component
  - Replaces V2 TRADE_INITIATION workers
  - Listens: EXECUTION_DIRECTIVE_READY event
  - Calls: IAPIConnector.place_order(directive)
  - Updates: Ledger, Journal
  - Publishes: TRADE_EXECUTED, _flow_stop_success

- [ ] **FlowTerminationHandler** platform component
  - Listens: _flow_stop_success, _flow_stop_error events
  - Responsibilities: Component cleanup, garbage collection, UI updates

- [ ] **PlanningAggregator** enhancement
  - Mode detection (SWOT vs Direct)
  - Parallel tracking (Entry, Size, Exit)
  - Sequential routing phase
  - Publishes: EXECUTION_DIRECTIVE_READY

### Phase 2: Plugin Category Refactoring
- [ ] **Rename**: ExecutionWorker → PositionLifecycleWorker
  - Update manifest schemas
  - Update documentation
  - Update agent.md

- [ ] **Subcategories**:
  - DYNAMIC_MANAGEMENT (trailing stops, partials)
  - RISK_CONTROL (emergency exits, circuit breakers)
  - SCHEDULED_OPERATIONS (DCA, rebalancing)

- [ ] **Reference Implementations**:
  - TrailingStopManager → StrategyDirective (MODIFY_EXISTING)
  - EmergencyExitAgent → StrategyDirective (CLOSE_EXISTING)
  - DCAExecutor → StrategyDirective (NEW_TRADE)

### Phase 3: Documentation Updates
- [ ] Update agent.md worker taxonomy
- [ ] Update TODO.md roadmap
- [ ] Update architecture diagrams
- [ ] Create migration guide (V2 → V3 ExecutionWorker)

---

## Migration Guide (V2 → V3)

### If you have V2 TRADE_INITIATION workers:
❌ **DELETE THEM** - Platform handles this now  
✅ **NO ACTION NEEDED** - PlanExecutionOrchestrator is platform code

### If you have V2 POSITION_MANAGEMENT workers:
✅ **REFACTOR TO**: PositionLifecycleWorker (DYNAMIC_MANAGEMENT)  
✅ **OUTPUT**: StrategyDirective (MODIFY_EXISTING)  
✅ **EXAMPLE**: TrailingStopManager now produces directive instead of calling execution_provider

### If you have V2 RISK_SAFETY workers:
✅ **REFACTOR TO**: PositionLifecycleWorker (RISK_CONTROL)  
✅ **OUTPUT**: StrategyDirective (CLOSE_EXISTING)  
✅ **EXAMPLE**: EmergencyExitAgent produces directive instead of force-closing positions

### If you have V2 OPERATIONAL workers:
✅ **REFACTOR TO**: PositionLifecycleWorker (SCHEDULED_OPERATIONS)  
✅ **OUTPUT**: StrategyDirective (NEW_TRADE or MODIFY_EXISTING)  
✅ **EXAMPLE**: DCAExecutor produces NEW_TRADE directive instead of placing orders

---

## Conclusion

### ExecutionWorker Category Fate: ❌ DISCONTINUED

**Reason**: Artificial boundary between planning and execution. V2 mixed platform orchestration (TRADE_INITIATION) with quant logic (POSITION_MANAGEMENT, RISK_SAFETY, OPERATIONAL).

### V3 Separation of Concerns

**Platform Responsibility** (configureerbaar, GEEN quant logic):
- `PlanExecutionOrchestrator`: ExecutionDirective → IAPIConnector
- `FlowTerminationHandler`: Cleanup after execution
- `PlanningAggregator`: Aggregeert 4 plans → ExecutionDirective

**Plugin Responsibility** (quant logic):
- `PositionLifecycleWorker`: Monitor positions, produce StrategyDirective
- Subtypes: DYNAMIC_MANAGEMENT, RISK_CONTROL, SCHEDULED_OPERATIONS

### Final Architecture
```
[SWOT/Opportunity] → [StrategyPlanner] → StrategyDirective
                                              ↓
                                    [4 Sub-Planners] → Plans
                                              ↓
[PositionLifecycle] → StrategyDirective → [PlanningAggregator] → ExecutionDirective
                                                                         ↓
                                              [PlanExecutionOrchestrator] (PLATFORM)
                                                                         ↓
                                                        IAPIConnector.place_order()
```

**Kracht**: Duidelijke scheiding platform vs plugin, universele StrategyDirective trigger, ExecutionDirective als finale contract.

---

**Documentatie Eigenaar**: Architecture Team  
**Laatste Update**: 2025-10-26  
**Review Status**: Ready for Implementation
