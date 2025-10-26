# Platform Execution Orchestration - V3 Design

**Document Purpose**: Definitieve architectuur voor platform execution orchestration in V3, ter vervanging van V2 TRADE_INITIATION ExecutionWorker plugins.

**Datum**: 2025-10-26  
**Status**: Architecture Approved, Ready for Implementation

---

## Executive Summary

### Core Principle
**ExecutionDirective → IAPIConnector is PLATFORM RESPONSIBILITY**

V2 had dit patroon correct geïdentificeerd maar verkeerd geïmplementeerd als plugin (DefaultPlanExecutor). V3 corrigeert dit: execution orchestration is configureerbare platform code, GEEN quant plugin logic.

---

## Component Architecture

### 1. PlanExecutionOrchestrator

**Type**: Platform Component (backend/core/orchestration/)  
**Configuration**: `platform.yaml`  
**NOT**: Plugin in plugins/ directory

#### Responsibilities

**Primary**: Bridge tussen Planning Layer en Broker Execution
- Input: ExecutionDirective (from PlanningAggregator)
- Output: Trade execution via IAPIConnector + system state updates

**Detailed Responsibilities**:
1. **Listen**: EXECUTION_DIRECTIVE_READY event
2. **Validate**: ExecutionDirective completeness (all required plans present)
3. **Execute**: IAPIConnector.place_order(directive)
4. **Update Ledger**: Record new position/modification in StrategyLedger
5. **Log Causality**: Complete flow trace in StrategyJournal
6. **Publish Events**: TRADE_EXECUTED (success), EXECUTION_FAILED (error)
7. **Flow Termination**: Fire STOP disposition (_flow_stop_success or _flow_stop_error)
8. **Trigger Cleanup**: Signal FlowTerminationHandler for component cleanup

#### Interface Design

```python
# backend/core/orchestration/plan_execution_orchestrator.py
from typing import Protocol
from backend.core.interfaces.connectors import IAPIConnector
from backend.core.interfaces.providers import ILedgerProvider, IJournalWriter
from backend.core.interfaces.events import IEventBus
from backend.dtos.planning.execution_directive import ExecutionDirective
from backend.dtos.execution.trade_executed import TradeExecutedDTO
from backend.dtos.shared.disposition_envelope import DispositionEnvelope

class PlanExecutionOrchestrator:
    """
    Platform component for executing ExecutionDirectives.
    
    This is NOT quant plugin logic - it's configureerbare infrastructure
    that orchestrates platform services (API, Ledger, Journal, EventBus).
    
    Replaces V2 TRADE_INITIATION ExecutionWorker plugins.
    """
    
    def __init__(
        self,
        api_connector: IAPIConnector,
        ledger_provider: ILedgerProvider,
        journal_writer: IJournalWriter,
        event_bus: IEventBus,
        config: PlanExecutionConfig
    ):
        """
        Initialize orchestrator with injected platform dependencies.
        
        Args:
            api_connector: Interface to broker/exchange
            ledger_provider: Position tracking service
            journal_writer: Causality logging service
            event_bus: Event publication service
            config: Platform configuration (from platform.yaml)
        """
        self._api_connector = api_connector
        self._ledger = ledger_provider
        self._journal = journal_writer
        self._event_bus = event_bus
        self._config = config
        
        # Register event handler
        self._event_bus.subscribe(
            event_name="EXECUTION_DIRECTIVE_READY",
            handler=self.on_execution_directive_ready
        )
    
    def on_execution_directive_ready(
        self, 
        directive: ExecutionDirective
    ) -> None:
        """
        Event handler: Execute directive and update system state.
        
        This method orchestrates the following platform services:
        1. Validation (directive completeness)
        2. Broker execution (IAPIConnector)
        3. Ledger updates (position tracking)
        4. Causality logging (journal)
        5. Event publication (TRADE_EXECUTED)
        6. Flow termination (STOP disposition)
        
        Args:
            directive: Complete execution plan from PlanningAggregator
        
        Raises:
            ValidationError: If directive is incomplete
            ExecutionError: If broker execution fails
            LedgerError: If ledger update fails
        """
        try:
            # 1. Validate directive completeness
            self._validate_directive(directive)
            
            # 2. Execute via API connector
            order_result = self._execute_order(directive)
            
            # 3. Update ledger (position tracking)
            position = self._update_ledger(directive, order_result)
            
            # 4. Log causality (complete flow trace)
            self._log_execution(directive, order_result, position)
            
            # 5. Publish TRADE_EXECUTED event
            self._publish_success(directive, order_result)
            
            # 6. Fire STOP disposition (flow termination)
            self._terminate_flow_success(directive)
            
        except Exception as error:
            # Error handling: Rollback + publish failure event
            self._handle_execution_error(directive, error)
            self._terminate_flow_error(directive, error)
    
    def _validate_directive(self, directive: ExecutionDirective) -> None:
        """
        Validate ExecutionDirective completeness.
        
        Ensures all required plans are present and valid.
        Scope-specific validation:
        - NEW_TRADE: Requires entry_plan, size_plan, routing_plan
        - MODIFY_EXISTING: At least one plan (entry/size/exit/routing)
        - CLOSE_EXISTING: Routing plan for exit execution
        
        Args:
            directive: ExecutionDirective to validate
        
        Raises:
            ValidationError: If directive is incomplete or invalid
        """
        if directive.scope == "NEW_TRADE":
            # NEW_TRADE requires minimum: entry, size, routing
            if not directive.entry_plan:
                raise ValidationError("NEW_TRADE requires entry_plan")
            if not directive.size_plan:
                raise ValidationError("NEW_TRADE requires size_plan")
            if not directive.routing_plan:
                raise ValidationError("NEW_TRADE requires routing_plan")
        
        elif directive.scope == "MODIFY_EXISTING":
            # MODIFY requires at least one plan
            if not any([
                directive.entry_plan,
                directive.size_plan,
                directive.exit_plan,
                directive.routing_plan
            ]):
                raise ValidationError(
                    "MODIFY_EXISTING requires at least one plan"
                )
            
            # MODIFY requires target_trade_ids
            if not directive.target_trade_ids:
                raise ValidationError(
                    "MODIFY_EXISTING requires target_trade_ids"
                )
        
        elif directive.scope == "CLOSE_EXISTING":
            # CLOSE requires target_trade_ids + routing plan
            if not directive.target_trade_ids:
                raise ValidationError(
                    "CLOSE_EXISTING requires target_trade_ids"
                )
            if not directive.routing_plan:
                raise ValidationError(
                    "CLOSE_EXISTING requires routing_plan"
                )
    
    def _execute_order(
        self, 
        directive: ExecutionDirective
    ) -> dict[str, Any]:
        """
        Execute order via IAPIConnector.
        
        Translates ExecutionDirective to broker API call.
        Respects retry policy from platform configuration.
        
        Args:
            directive: Complete execution plan
        
        Returns:
            API response with order details (order_id, fill_price, etc.)
        
        Raises:
            ExecutionError: If broker execution fails after retries
        """
        # Implement retry logic from config
        max_retries = self._config.retry_policy.max_retries
        backoff_strategy = self._config.retry_policy.backoff_strategy
        
        for attempt in range(max_retries + 1):
            try:
                # Call IAPIConnector.place_order()
                return self._api_connector.place_order(directive)
            
            except APIError as error:
                if attempt == max_retries:
                    raise ExecutionError(
                        f"Order execution failed after {max_retries} retries"
                    ) from error
                
                # Backoff before retry
                self._apply_backoff(backoff_strategy, attempt)
    
    def _update_ledger(
        self,
        directive: ExecutionDirective,
        order_result: dict[str, Any]
    ) -> Position:
        """
        Update StrategyLedger with new/modified position.
        
        Scope-specific updates:
        - NEW_TRADE: Add new position
        - MODIFY_EXISTING: Update existing position(s)
        - CLOSE_EXISTING: Close existing position(s)
        
        Args:
            directive: Execution directive
            order_result: Broker API response
        
        Returns:
            Updated position object
        
        Raises:
            LedgerError: If ledger update fails
        """
        if directive.scope == "NEW_TRADE":
            return self._ledger.add_position(
                trade_id=directive.directive_id,  # Use directive_id as trade_id
                strategy_id=directive.strategy_id,
                symbol=directive.entry_plan.symbol,
                direction=directive.entry_plan.direction,
                entry_price=order_result['fill_price'],
                position_size=directive.size_plan.position_size,
                stop_loss=directive.exit_plan.stop_loss_price if directive.exit_plan else None,
                take_profit=directive.exit_plan.take_profit_price if directive.exit_plan else None
            )
        
        elif directive.scope == "MODIFY_EXISTING":
            # Update each target position
            positions = []
            for trade_id in directive.target_trade_ids:
                position = self._ledger.modify_position(
                    trade_id=trade_id,
                    new_stop=directive.exit_plan.stop_loss_price if directive.exit_plan else None,
                    new_target=directive.exit_plan.take_profit_price if directive.exit_plan else None,
                    size_adjustment=directive.size_plan.position_size if directive.size_plan else None
                )
                positions.append(position)
            return positions
        
        elif directive.scope == "CLOSE_EXISTING":
            # Close each target position
            positions = []
            for trade_id in directive.target_trade_ids:
                position = self._ledger.close_position(
                    trade_id=trade_id,
                    exit_price=order_result['fill_price'],
                    close_reason=directive.rationale
                )
                positions.append(position)
            return positions
    
    def _log_execution(
        self,
        directive: ExecutionDirective,
        order_result: dict[str, Any],
        position: Position | list[Position]
    ) -> None:
        """
        Log complete causality chain in StrategyJournal.
        
        Captures:
        - Directive details (scope, plans, rationale)
        - Trigger context (opportunity_id, threat_ids, etc.)
        - Order execution details (fill_price, order_id)
        - Position state (entry, size, stops)
        - Timestamp chain
        
        Args:
            directive: Execution directive
            order_result: Broker API response
            position: Updated position(s)
        """
        journal_entry = {
            'event_type': self._get_event_type(directive.scope),
            'directive_id': str(directive.directive_id),
            'strategy_id': directive.strategy_id,
            'timestamp': directive.timestamp.isoformat(),
            
            # Trigger context (causality)
            'trigger_context': directive.trigger_context,
            
            # Plans (what was decided)
            'entry_plan': directive.entry_plan.model_dump() if directive.entry_plan else None,
            'size_plan': directive.size_plan.model_dump() if directive.size_plan else None,
            'exit_plan': directive.exit_plan.model_dump() if directive.exit_plan else None,
            'routing_plan': directive.routing_plan.model_dump() if directive.routing_plan else None,
            
            # Execution details (what happened)
            'order_result': order_result,
            'fill_price': order_result.get('fill_price'),
            'order_id': order_result.get('order_id'),
            
            # Position state
            'position': position.model_dump() if isinstance(position, Position) else [p.model_dump() for p in position],
            
            # Rationale
            'rationale': directive.rationale
        }
        
        self._journal.log_entry(journal_entry)
    
    def _get_event_type(self, scope: str) -> str:
        """Map directive scope to journal event type."""
        return {
            "NEW_TRADE": "TRADE_OPENED",
            "MODIFY_EXISTING": "POSITION_MODIFIED",
            "CLOSE_EXISTING": "TRADE_CLOSED"
        }[scope]
    
    def _publish_success(
        self,
        directive: ExecutionDirective,
        order_result: dict[str, Any]
    ) -> None:
        """
        Publish TRADE_EXECUTED event.
        
        Notifies system of successful execution.
        Other components (UI, monitoring, etc.) can listen to this event.
        
        Args:
            directive: Execution directive
            order_result: Broker API response
        """
        self._event_bus.publish(
            event_name="TRADE_EXECUTED",
            payload=TradeExecutedDTO(
                directive_id=directive.directive_id,
                strategy_id=directive.strategy_id,
                scope=directive.scope,
                execution_time=datetime.now(),
                fill_price=Decimal(str(order_result['fill_price'])),
                order_id=order_result['order_id'],
                target_trade_ids=directive.target_trade_ids
            )
        )
    
    def _terminate_flow_success(self, directive: ExecutionDirective) -> None:
        """
        Fire STOP disposition for successful flow completion.
        
        Triggers FlowTerminationHandler for cleanup:
        - Component instance termination
        - Garbage collection
        - UI updates
        - Metrics recording
        
        Args:
            directive: Completed execution directive
        """
        self._event_bus.publish(
            event_name="_flow_stop_success",
            payload=FlowCompletionDTO(
                flow_id=str(directive.directive_id),
                completion_time=datetime.now(),
                reason="Execution completed successfully",
                final_state="SUCCESS"
            )
        )
    
    def _handle_execution_error(
        self,
        directive: ExecutionDirective,
        error: Exception
    ) -> None:
        """
        Handle execution errors with rollback policy.
        
        Rollback actions (from config):
        - on_api_failure: "rollback_ledger" (undo ledger changes)
        - on_ledger_failure: "alert_admin" (notify but don't rollback)
        
        Args:
            directive: Failed execution directive
            error: Exception that occurred
        """
        # Log error
        self._journal.log_error({
            'event_type': 'EXECUTION_FAILED',
            'directive_id': str(directive.directive_id),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now().isoformat()
        })
        
        # Apply rollback policy
        if isinstance(error, APIError):
            if self._config.error_handling.on_api_failure == "rollback_ledger":
                self._rollback_ledger_changes(directive)
        
        # Publish failure event
        self._event_bus.publish(
            event_name="EXECUTION_FAILED",
            payload=ExecutionFailedDTO(
                directive_id=directive.directive_id,
                error_type=type(error).__name__,
                error_message=str(error),
                timestamp=datetime.now()
            )
        )
    
    def _terminate_flow_error(
        self,
        directive: ExecutionDirective,
        error: Exception
    ) -> None:
        """
        Fire STOP disposition for failed flow.
        
        Triggers FlowTerminationHandler for cleanup + error handling.
        
        Args:
            directive: Failed execution directive
            error: Exception that occurred
        """
        self._event_bus.publish(
            event_name="_flow_stop_error",
            payload=FlowCompletionDTO(
                flow_id=str(directive.directive_id),
                completion_time=datetime.now(),
                reason=f"Execution failed: {str(error)}",
                final_state="ERROR",
                error_details={
                    'error_type': type(error).__name__,
                    'error_message': str(error)
                }
            )
        )
```

#### Configuration Schema

```yaml
# platform.yaml
orchestration:
  plan_execution:
    enabled: true
    
    # Timeout for order execution
    timeout_seconds: 30
    
    # Retry policy for API failures
    retry_policy:
      max_retries: 3
      backoff_strategy: "exponential"  # "linear", "exponential", "constant"
      initial_delay_ms: 100
      max_delay_ms: 5000
    
    # Error handling policies
    error_handling:
      on_api_failure: "rollback_ledger"  # "rollback_ledger", "alert_only", "continue"
      on_ledger_failure: "alert_admin"   # "alert_admin", "rollback_api", "continue"
      on_journal_failure: "continue"     # "continue", "alert_admin", "fail_execution"
    
    # Monitoring
    monitoring:
      log_all_executions: true
      alert_on_slow_execution_ms: 1000
      metrics_enabled: true
```

---

### 2. FlowTerminationHandler

**Type**: Platform Component  
**Configuration**: `platform.yaml`

#### Responsibilities

**Primary**: Cleanup and finalization after flow completion/failure

**Detailed Responsibilities**:
1. **Listen**: _flow_stop_success, _flow_stop_error events
2. **Component Cleanup**: Terminate worker instances, clear caches
3. **Garbage Collection**: Free resources, clear temporary data
4. **UI Updates**: Notify frontend of flow completion
5. **Metrics Recording**: Record flow duration, success/failure rates
6. **State Persistence**: Save final state for post-mortem analysis

#### Interface Design

```python
# backend/core/orchestration/flow_termination_handler.py
class FlowTerminationHandler:
    """
    Platform component for flow cleanup and finalization.
    
    Listens to flow termination events and orchestrates cleanup.
    """
    
    def __init__(
        self,
        event_bus: IEventBus,
        component_registry: IComponentRegistry,
        metrics_collector: IMetricsCollector,
        config: FlowTerminationConfig
    ):
        self._event_bus = event_bus
        self._components = component_registry
        self._metrics = metrics_collector
        self._config = config
        
        # Register event handlers
        self._event_bus.subscribe(
            event_name="_flow_stop_success",
            handler=self.on_flow_success
        )
        self._event_bus.subscribe(
            event_name="_flow_stop_error",
            handler=self.on_flow_error
        )
    
    def on_flow_success(self, completion: FlowCompletionDTO) -> None:
        """Handle successful flow completion."""
        # 1. Terminate component instances
        self._terminate_flow_components(completion.flow_id)
        
        # 2. Garbage collection
        self._cleanup_flow_resources(completion.flow_id)
        
        # 3. UI updates
        self._notify_ui(completion)
        
        # 4. Metrics recording
        self._record_success_metrics(completion)
    
    def on_flow_error(self, completion: FlowCompletionDTO) -> None:
        """Handle failed flow completion."""
        # 1. Terminate component instances
        self._terminate_flow_components(completion.flow_id)
        
        # 2. Garbage collection
        self._cleanup_flow_resources(completion.flow_id)
        
        # 3. UI updates (error notification)
        self._notify_ui_error(completion)
        
        # 4. Metrics recording
        self._record_error_metrics(completion)
        
        # 5. Error alerting (if configured)
        if self._config.alert_on_error:
            self._send_error_alert(completion)
```

---

## Event Flow Diagram

### Successful Execution Flow

```
[PlanningAggregator] 
    ↓ aggregates 4 plans
ExecutionDirective
    ↓ publishes event
EXECUTION_DIRECTIVE_READY
    ↓
[PlanExecutionOrchestrator]
    ├─→ IAPIConnector.place_order()
    ├─→ ILedgerProvider.add_position()
    ├─→ IJournalWriter.log_entry()
    ├─→ IEventBus.publish(TRADE_EXECUTED)
    └─→ IEventBus.publish(_flow_stop_success)
         ↓
[FlowTerminationHandler]
    ├─→ Terminate components
    ├─→ Garbage collection
    ├─→ UI updates
    └─→ Metrics recording
```

### Error Handling Flow

```
[PlanExecutionOrchestrator]
    ↓ API error
IAPIConnector.place_order() → APIError
    ↓ retry logic (max 3x)
STILL FAILS
    ↓
[PlanExecutionOrchestrator._handle_execution_error]
    ├─→ Rollback ledger (if policy = "rollback_ledger")
    ├─→ IJournalWriter.log_error()
    ├─→ IEventBus.publish(EXECUTION_FAILED)
    └─→ IEventBus.publish(_flow_stop_error)
         ↓
[FlowTerminationHandler.on_flow_error]
    ├─→ Terminate components
    ├─→ Garbage collection
    ├─→ UI error notification
    ├─→ Error metrics
    └─→ Admin alert (if configured)
```

---

## Key Architectural Decisions

### 1. Platform Component vs Plugin
**Decision**: PlanExecutionOrchestrator is platform code, NOT plugin  
**Rationale**: No quant logic - pure orchestration of platform services  
**Impact**: Configured via platform.yaml, not strategy_blueprint.yaml

### 2. Retry Logic Location
**Decision**: Retry logic lives in PlanExecutionOrchestrator  
**Rationale**: Infrastructure concern, not strategy concern  
**Impact**: Quant doesn't configure retries, platform admin does

### 3. Rollback Policy
**Decision**: Configurable rollback (ledger, API, none)  
**Rationale**: Different environments need different policies (backtest vs live)  
**Impact**: Platform.yaml specifies policy per environment

### 4. Flow Termination Signal
**Decision**: EVERY flow ends with STOP disposition  
**Rationale**: Ensures cleanup happens for success AND failure paths  
**Impact**: FlowTerminationHandler triggers on both _flow_stop_success and _flow_stop_error

### 5. Causality Logging Responsibility
**Decision**: PlanExecutionOrchestrator logs complete causality  
**Rationale**: Platform has complete view of execution context  
**Impact**: Workers don't need to implement causality logging

---

## Implementation Checklist

### Phase 1: Core Components
- [ ] Create `backend/core/orchestration/` directory
- [ ] Implement `PlanExecutionOrchestrator` class
- [ ] Implement `FlowTerminationHandler` class
- [ ] Define configuration schemas (PlanExecutionConfig, FlowTerminationConfig)
- [ ] Unit tests (25+ tests per component)

### Phase 2: Integration
- [ ] Integrate with EventBus (EXECUTION_DIRECTIVE_READY subscription)
- [ ] Integrate with IAPIConnector (place_order calls)
- [ ] Integrate with ILedgerProvider (position updates)
- [ ] Integrate with IJournalWriter (causality logging)
- [ ] Integration tests (end-to-end flow)

### Phase 3: Configuration
- [ ] Add orchestration section to platform.yaml
- [ ] Document configuration options
- [ ] Add validation for configuration schema
- [ ] Environment-specific configs (backtest vs live)

### Phase 4: Error Handling
- [ ] Implement retry logic (exponential backoff)
- [ ] Implement rollback policies
- [ ] Implement error alerting
- [ ] Error scenario tests

### Phase 5: Monitoring
- [ ] Metrics collection integration
- [ ] Slow execution alerts
- [ ] Success/failure rate tracking
- [ ] Dashboard integration

---

## Migration from V2

### V2 Pattern (INCORRECT)
```python
# plugins/execution_workers/trade_initiation/default_plan_executor/worker.py
class DefaultPlanExecutor(BaseWorker):  # ❌ Plugin!
    """Voert trade plannen uit."""
    
    def on_plan_ready(self, plan: RoutedTradePlan):
        # Orchestration logic in plugin! ❌
        self.execution_provider.place_order(...)
```

### V3 Pattern (CORRECT)
```python
# backend/core/orchestration/plan_execution_orchestrator.py
class PlanExecutionOrchestrator:  # ✅ Platform component!
    """Platform orchestration - NOT quant plugin."""
    
    def on_execution_directive_ready(self, directive: ExecutionDirective):
        # Platform orchestration ✅
        self._api_connector.place_order(directive)
```

### Migration Steps
1. ❌ DELETE: plugins/execution_workers/trade_initiation/
2. ✅ CREATE: backend/core/orchestration/plan_execution_orchestrator.py
3. ✅ UPDATE: platform.yaml (add orchestration config)
4. ✅ NO CHANGES: Strategy YAML files (platform change, not strategy change)

---

**Documentatie Eigenaar**: Platform Team  
**Laatste Update**: 2025-10-26  
**Review Status**: Ready for Implementation  
**Zie ook**:
- v2_to_v3_execution_mapping.md (volledige ExecutionWorker analyse)
- TODO.md Phase 5 (implementation roadmap)
