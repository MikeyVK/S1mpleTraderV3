# PlanningAggregator - Conceptual Design (STAP 0)

**Status:** Architectural Contract  
**Versie:** 1.0  
**Datum:** 2025-11-06  
**Owner:** Platform Architecture Team

---

## Executive Summary

**PlanningAggregator** is de fan-in coordinator die Entry/Size/Exit/Execution plans aggregeert tot ExecutionDirectiveBatch DTOs. Het ondersteunt **multipliciteit** (N trades → N directives → 1 batch) en **dual-phase coordination** (parallel Entry/Size/Exit, sequential ExecutionPlan).

**Kernprincipe:**
> PlanningAggregator is de "plan assembly coordinator" - track incoming plans per trade, detect completion phases, publish aggregated directives.

**Key Design Decisions:**
- ✅ Multi-input worker (5 event handlers via manifest)
- ✅ Per-strategy singleton (zoals FlowInitiator)
- ✅ State tracking via per-trade matrix + RunAnchor guard
- ✅ Non-reentrant (binnen 1 tick, GEEN cross-tick planning)
- ✅ Bus-agnostic (EventAdapter wiring pattern)
- ✅ Altijd EXECUTION_DIRECTIVE_BATCH_READY (ook voor single directive)

---

## 1. Architectural Contract

### 1.1 Responsibility (SRP)

**PlanningAggregator heeft ÉÉN verantwoordelijkheid:**
> "Coordinate multi-plan aggregation per trade and publish ExecutionDirectiveBatch when complete"

**NIET verantwoordelijk voor:**
- ❌ Plan creation (dat is planner workers' domein)
- ❌ Plan validation (dat is ExecutionIntentPlanner's domein)
- ❌ Batch execution (dat is ExecutionHandler's domein)
- ❌ Trade routing logic (dat is ExecutionTranslator's domein)

### 1.2 Core Use Cases

1. **Single Trade Planning**: 1 StrategyDirective (NEW_TRADE) → 4 plans → 1 ExecutionDirective → Batch(size=1)
2. **Multi-Trade Batch**: 1 StrategyDirective (3 target_trade_ids) → 12 plans (4 per trade) → 3 ExecutionDirectives → Batch(size=3)
3. **Partial Plan Update**: 1 StrategyDirective (MODIFY_EXISTING, 2 trades) → 2 ExitPlans only → 2 ExecutionDirectives → Batch(size=2)
4. **Parallel Phase Coordination**: Detect when Entry/Size/Exit complete → trigger ExecutionIntent phase
5. **Batch Assembly**: All 4 plans per trade received → create ExecutionDirectiveBatch → publish

### 1.3 Multipliciteit Pattern

**StrategyDirective → N Trades → 4N Plans → N Directives → 1 Batch**

```
StrategyDirective(
    target_trade_ids=["TRD_123", "TRD_456", "TRD_789"]  # 3 trades
)
↓
Expected Plans: 3 × 4 = 12 plans total
├─ Trade TRD_123: EntryPlan, SizePlan, ExitPlan, ExecutionPlan
├─ Trade TRD_456: EntryPlan, SizePlan, ExitPlan, ExecutionPlan
└─ Trade TRD_789: EntryPlan, SizePlan, ExitPlan, ExecutionPlan
↓
Output: ExecutionDirectiveBatch(directives=[
    ExecutionDirective(trade_id="TRD_123", ...),
    ExecutionDirective(trade_id="TRD_456", ...),
    ExecutionDirective(trade_id="TRD_789", ...)
])
```

---

## 2. State Tracking Architecture

### 2.1 State Structure

```python
class PlanningAggregator:
    """
    Multi-input aggregator with per-trade state tracking.
    
    Lifecycle: Per-strategy singleton (like FlowInitiator)
    State: Mutable tracking matrix, reset per planning cycle
    Reentry: BLOCKED via RunAnchor guard
    """
    
    # Injected dependencies
    strategy_cache: IStrategyCache
    event_bus: IEventBus  # For publishing output events
    
    # State tracking (mutable)
    _run_anchor: RunAnchor | None = None
    _strategy_directive: StrategyDirective | None = None
    _expected_trade_ids: set[str] = field(default_factory=set)
    _plans_by_trade: dict[str, dict[str, BaseModel]] = field(default_factory=dict)
    
    # Phase tracking
    _parallel_phase_complete: set[str] = field(default_factory=set)  # Trade IDs
```

### 2.2 Per-Trade Plan Matrix

```python
_plans_by_trade = {
    "TRD_123": {
        "entry": EntryPlan(...),
        "size": SizePlan(...),
        "exit": ExitPlan(...),
        "execution": ExecutionPlan(...)  # ← Added after parallel phase
    },
    "TRD_456": {
        "entry": EntryPlan(...),
        "size": None,  # ← Not yet received
        "exit": None,
        "execution": None
    },
    "NEW": {  # ← For NEW_TRADE scenario (no target_trade_ids)
        "entry": EntryPlan(...),
        "size": SizePlan(...),
        "exit": None,
        "execution": None
    }
}
```

### 2.3 RunAnchor Reentry Guard

```python
def on_strategy_directive(self, directive: StrategyDirective) -> DispositionEnvelope:
    """Reset state for new planning cycle."""
    current_anchor = self.strategy_cache.get_run_anchor()
    
    # REENTRY GUARD: Reject if already processing this run
    if self._run_anchor is not None and self._run_anchor == current_anchor:
        raise RuntimeError(
            f"Reentry detected: PlanningAggregator already processing "
            f"run {current_anchor.timestamp}"
        )
    
    # Fresh state for new planning cycle
    self._run_anchor = current_anchor
    self._strategy_directive = directive
    
    # Determine expected trades
    if directive.target_trade_ids:
        self._expected_trade_ids = set(directive.target_trade_ids)
    else:
        self._expected_trade_ids = {"NEW"}  # NEW_TRADE scenario
    
    # Initialize per-trade plan tracking
    self._plans_by_trade = {tid: {} for tid in self._expected_trade_ids}
    self._parallel_phase_complete = set()
    
    return DispositionEnvelope(
        disposition="CONTINUE",
        connector_id="internal"  # No external event needed
    )
```

---

## 3. Event Handler Pattern

### 3.1 Manifest Declaration

```yaml
# backend/core/planning_aggregator/manifest.yaml
plugin_id: "platform/planning_aggregator/v1.0.0"
category: "platform_component"

scope_behavior:
  subscription_mode: "strategy"  # Per-strategy scoped
  publication_scope: "strategy"

capabilities:
  io:
    multi_input: true   # ← KEY: Multiple event handlers
    broadcast_output: false

inputs:
  - connector_id: "strategy_directive_input"
    handler_method: "on_strategy_directive"
  - connector_id: "entry_plan_input"
    handler_method: "on_entry_plan"
  - connector_id: "size_plan_input"
    handler_method: "on_size_plan"
  - connector_id: "exit_plan_input"
    handler_method: "on_exit_plan"
  - connector_id: "execution_plan_input"
    handler_method: "on_execution_plan"

outputs:
  - connector_id: "execution_request_output"
    disposition: "PUBLISH"
    payload_type: "ExecutionRequest"
    payload_source: "backend.dtos.strategy.execution_request.ExecutionRequest"
  - connector_id: "execution_directive_batch_output"
    disposition: "PUBLISH"
    payload_type: "ExecutionDirectiveBatch"
    payload_source: "backend.dtos.execution.execution_directive_batch.ExecutionDirectiveBatch"
```

### 3.2 Wiring Map

```yaml
# strategy_wiring_map.yaml
adapter_configurations:
  plan_aggregator:
    subscriptions:
      - event_name: "STRATEGY_DIRECTIVE_PUBLISHED"
        connector_id: "strategy_directive_input"
      - event_name: "ENTRY_PLAN_CREATED"
        connector_id: "entry_plan_input"
      - event_name: "SIZE_PLAN_CREATED"
        connector_id: "size_plan_input"
      - event_name: "EXIT_PLAN_CREATED"
        connector_id: "exit_plan_input"
      - event_name: "EXECUTION_PLAN_CREATED"
        connector_id: "execution_plan_input"
    publications:
      - connector_id: "execution_request_output"
        event_name: "EXECUTION_INTENT_REQUESTED"
      - connector_id: "execution_directive_batch_output"
        event_name: "EXECUTION_DIRECTIVE_BATCH_READY"
```

### 3.3 Handler Methods

#### Handler 1: on_strategy_directive

```python
def on_strategy_directive(self, directive: StrategyDirective) -> DispositionEnvelope:
    """
    Initialize aggregator state for new planning cycle.
    
    Triggered by: STRATEGY_DIRECTIVE_PUBLISHED event
    Side effects: Resets state, initializes per-trade tracking
    Returns: CONTINUE (no external event)
    """
    # See Section 2.3 for implementation
    # ...
    
    return DispositionEnvelope(
        disposition="CONTINUE",
        connector_id="internal"
    )
```

#### Handler 2-4: on_entry/size/exit_plan

```python
def on_entry_plan(self, plan: EntryPlan) -> DispositionEnvelope:
    """
    Track EntryPlan for specific trade.
    
    Triggered by: ENTRY_PLAN_CREATED event
    Side effects: Updates _plans_by_trade, may trigger parallel phase completion
    Returns: PUBLISH ExecutionRequest OR CONTINUE
    """
    # TODO: Extract trade_id from plan/causality (Issue #5)
    trade_id = self._extract_trade_id(plan)
    
    # Store plan
    self._plans_by_trade[trade_id]["entry"] = plan
    
    # Check parallel phase completion
    return self._check_parallel_phase_completion(trade_id)

def on_size_plan(self, plan: SizePlan) -> DispositionEnvelope:
    """Similar to on_entry_plan, stores SizePlan."""
    trade_id = self._extract_trade_id(plan)
    self._plans_by_trade[trade_id]["size"] = plan
    return self._check_parallel_phase_completion(trade_id)

def on_exit_plan(self, plan: ExitPlan) -> DispositionEnvelope:
    """Similar to on_entry_plan, stores ExitPlan."""
    trade_id = self._extract_trade_id(plan)
    self._plans_by_trade[trade_id]["exit"] = plan
    return self._check_parallel_phase_completion(trade_id)
```

#### Handler 5: on_execution_plan

```python
def on_execution_plan(self, plan: ExecutionPlan) -> DispositionEnvelope:
    """
    Track ExecutionPlan (sequential phase) for specific trade.
    
    Triggered by: EXECUTION_PLAN_CREATED event
    Side effects: Updates _plans_by_trade, may trigger batch assembly
    Returns: PUBLISH ExecutionDirectiveBatch OR CONTINUE
    """
    trade_id = self._extract_trade_id(plan)
    
    # Store execution plan
    self._plans_by_trade[trade_id]["execution"] = plan
    
    # Check if ALL trades have ALL 4 plans
    return self._check_batch_completion()
```

---

## 4. Phase Coordination Logic

### 4.1 Parallel Phase Completion

```python
def _check_parallel_phase_completion(self, trade_id: str) -> DispositionEnvelope:
    """
    Check if parallel phase (Entry/Size/Exit) complete for given trade.
    
    Returns:
        - PUBLISH ExecutionRequest if parallel phase complete for this trade
        - CONTINUE otherwise
    """
    plans = self._plans_by_trade[trade_id]
    
    # Parallel phase = Entry + Size + Exit
    if all(k in plans for k in ["entry", "size", "exit"]):
        # Mark parallel phase complete for this trade
        self._parallel_phase_complete.add(trade_id)
        
        # Publish ExecutionRequest for ExecutionIntentPlanner
        request = ExecutionRequest(
            request_id=generate_execution_request_id(),
            trade_id=trade_id,
            strategy_directive=self._strategy_directive,
            entry_plan=plans["entry"],
            size_plan=plans["size"],
            exit_plan=plans["exit"],
            causality=self._strategy_directive.causality  # Propagate
        )
        
        return DispositionEnvelope(
            disposition="PUBLISH",
            connector_id="execution_request_output",
            payload=request
        )
    
    # Not yet complete - wait for more plans
    return DispositionEnvelope(
        disposition="CONTINUE",
        connector_id="internal"
    )
```

### 4.2 Batch Completion

```python
def _check_batch_completion(self) -> DispositionEnvelope:
    """
    Check if ALL trades have ALL 4 plans (Entry/Size/Exit/Execution).
    
    Returns:
        - PUBLISH ExecutionDirectiveBatch if all complete
        - CONTINUE otherwise
    """
    # Check if all expected trades have all 4 plans
    for trade_id in self._expected_trade_ids:
        plans = self._plans_by_trade[trade_id]
        required = ["entry", "size", "exit", "execution"]
        
        if not all(k in plans for k in required):
            # Still waiting for plans
            return DispositionEnvelope(
                disposition="CONTINUE",
                connector_id="internal"
            )
    
    # All trades complete - assemble batch
    directives = []
    for trade_id in self._expected_trade_ids:
        plans = self._plans_by_trade[trade_id]
        
        # Create ExecutionDirective per trade
        directive = ExecutionDirective(
            directive_id=generate_execution_directive_id(),
            causality=self._build_causality(trade_id),  # TODO: Issue #5
            entry_plan=plans.get("entry"),
            size_plan=plans.get("size"),
            exit_plan=plans.get("exit"),
            execution_plan=plans.get("execution")
        )
        directives.append(directive)
    
    # Create batch (always, even for single directive)
    batch = ExecutionDirectiveBatch(
        batch_id=generate_batch_id(),
        directives=directives,
        execution_mode=ExecutionMode.ATOMIC,  # Default: all-or-nothing
        created_at=datetime.now(timezone.utc),
        rollback_on_failure=True,
        timeout_seconds=30,
        metadata={
            "strategy_directive_id": self._strategy_directive.directive_id,
            "trade_count": len(directives)
        }
    )
    
    # Reset state after publishing (ready for next cycle)
    self._reset_state()
    
    return DispositionEnvelope(
        disposition="PUBLISH",
        connector_id="execution_directive_batch_output",
        payload=batch
    )

def _reset_state(self):
    """Reset aggregator state after batch published."""
    self._run_anchor = None
    self._strategy_directive = None
    self._expected_trade_ids = set()
    self._plans_by_trade = {}
    self._parallel_phase_complete = set()
```

---

## 5. Trade ID Extraction (Issue #5 - BLOCKER)

**OPEN DESIGN ISSUE:** Hoe bepalen we welke plan bij welke trade hoort?

### 5.1 Problem Statement

Plans (EntryPlan, SizePlan, etc.) hebben **GEEN trade_id field**:

```python
@dataclass
class EntryPlan:
    plan_id: str  # "ENT_20251106_100000_abc123"
    symbol: str
    # ... NO trade_id field!
```

**Aggregator moet weten:** EntryPlan met plan_id X hoort bij trade "TRD_123".

### 5.2 Option A: Extract from CausalityChain

**Aanname:** Plans hebben causality field (momenteel niet zo):

```python
@dataclass
class EntryPlan:
    plan_id: str
    causality: CausalityChain  # ← NEW field
    # ...

@dataclass
class CausalityChain:
    tick_id: str
    signal_ids: list[str]
    strategy_directive_id: str
    trade_id: str | None  # ← NEW field (None for NEW_TRADE)
```

**Extraction:**
```python
def _extract_trade_id(self, plan: BaseModel) -> str:
    """Extract trade_id from plan's causality."""
    if hasattr(plan, 'causality') and plan.causality.trade_id:
        return plan.causality.trade_id
    return "NEW"  # NEW_TRADE scenario
```

**Pro:**
- ✅ Causality chain completeness
- ✅ Audit trail per trade

**Con:**
- ❌ Breaking change (plans moeten causality krijgen)
- ❌ Sub-planners moeten causality propageren

### 5.3 Option B: Embed in plan_id

**Pattern:**
```python
plan_id = "ENT_20251106_100000_TRD123_abc"
#                               ^^^^^^^ trade ID embedded
```

**Extraction:**
```python
def _extract_trade_id(self, plan: BaseModel) -> str:
    """Extract trade_id from plan_id pattern."""
    parts = plan.plan_id.split("_")
    if len(parts) >= 5 and parts[3].startswith("TRD"):
        return parts[3]  # "TRD123"
    return "NEW"
```

**Pro:**
- ✅ Geen DTO wijzigingen nodig
- ✅ Simpel te implementeren

**Con:**
- ❌ Fragile (regex parsing)
- ❌ Geen expliciete field

### 5.4 Option C: Separate trade_id Field

**Aanpassing:**
```python
@dataclass
class EntryPlan:
    plan_id: str
    trade_id: str  # ← NEW field
    # ...
```

**Extraction:**
```python
def _extract_trade_id(self, plan: BaseModel) -> str:
    """Extract trade_id from explicit field."""
    if hasattr(plan, 'trade_id'):
        return plan.trade_id
    return "NEW"
```

**Pro:**
- ✅ Explicit field (type-safe)
- ✅ Simpel te lezen

**Con:**
- ❌ Breaking change (alle plan DTOs updaten)

### 5.5 DECISION NEEDED

**TODO in Issue #5:** Beslissen tussen Option A, B, of C.

**Voor nu:** Design document aanneemt **Option A (CausalityChain)** als voorlopig design.

---

## 6. Partial Plan Support

### 6.1 Scenario

```python
# Modify 2 existing trades - only update exit plans
StrategyDirective(
    scope=DirectiveScope.MODIFY_EXISTING,
    target_trade_ids=["TRD_123", "TRD_456"],
    exit_directive=ExitDirective(stop_loss_tolerance=0.01),
    # NO entry_directive, size_directive, routing_directive
)
```

### 6.2 Expected Plans

```
Trade TRD_123: ExitPlan only (no Entry/Size/Execution)
Trade TRD_456: ExitPlan only
```

### 6.3 Aggregator Logic

```python
def _check_batch_completion(self) -> DispositionEnvelope:
    """
    MODIFIED: Support partial plans.
    
    Completion = all EXPECTED plans received (not necessarily all 4).
    """
    # Determine expected plan types from StrategyDirective sub-directives
    expected_plan_types = self._determine_expected_plans()
    # e.g., ["exit"] for exit-only modification
    
    for trade_id in self._expected_trade_ids:
        plans = self._plans_by_trade[trade_id]
        
        # Check only expected plan types
        if not all(k in plans for k in expected_plan_types):
            return DispositionEnvelope(
                disposition="CONTINUE",
                connector_id="internal"
            )
    
    # All expected plans received - assemble batch
    # ...

def _determine_expected_plans(self) -> list[str]:
    """
    Determine which plan types to expect based on StrategyDirective.
    
    Returns:
        List of plan types: ["entry", "size", "exit", "execution"]
    """
    directive = self._strategy_directive
    expected = []
    
    if directive.entry_directive is not None:
        expected.append("entry")
    if directive.size_directive is not None:
        expected.append("size")
    if directive.exit_directive is not None:
        expected.append("exit")
    if directive.routing_directive is not None:
        expected.append("execution")
    
    # NEW_TRADE: default to all 4 if none specified
    if not expected and directive.scope == DirectiveScope.NEW_TRADE:
        expected = ["entry", "size", "exit", "execution"]
    
    return expected
```

---

## 7. Dependencies & Integration

### 7.1 Upstream Dependencies

**Input Events:**
- `STRATEGY_DIRECTIVE_PUBLISHED` (from StrategyPlanner)
- `ENTRY_PLAN_CREATED` (from EntryPlanner)
- `SIZE_PLAN_CREATED` (from SizePlanner)
- `EXIT_PLAN_CREATED` (from ExitPlanner)
- `EXECUTION_PLAN_CREATED` (from ExecutionIntentPlanner)

**Input DTOs:**
- `StrategyDirective` (strategy layer)
- `EntryPlan`, `SizePlan`, `ExitPlan`, `ExecutionPlan` (planning layer)

### 7.2 Downstream Consumers

**Output Events:**
- `EXECUTION_INTENT_REQUESTED` → ExecutionIntentPlanner
- `EXECUTION_DIRECTIVE_BATCH_READY` → ExecutionHandler

**Output DTOs:**
- `ExecutionRequest` (NEW DTO - Issue #4)
- `ExecutionDirectiveBatch` (execution layer)

### 7.3 Injected Dependencies

```python
class PlanningAggregator:
    def __init__(
        self,
        strategy_cache: IStrategyCache,
        event_bus: IEventBus  # For publishing output events
    ):
        self.strategy_cache = strategy_cache
        self.event_bus = event_bus
```

---

## 8. Error Handling

### 8.1 Reentry Detection

```python
# In on_strategy_directive
if self._run_anchor is not None and self._run_anchor == current_anchor:
    raise RuntimeError(
        f"Reentry detected: PlanningAggregator already processing "
        f"run {current_anchor.timestamp}"
    )
```

### 8.2 Stale Plan Detection

```python
def _validate_plan_freshness(self, plan: BaseModel):
    """Ensure plan is from current run (not stale from previous tick)."""
    current_anchor = self.strategy_cache.get_run_anchor()
    
    # Assume plan has timestamp field (validate against run_anchor)
    if hasattr(plan, 'timestamp'):
        if plan.timestamp < current_anchor.timestamp:
            raise ValueError(
                f"Stale plan detected: plan timestamp {plan.timestamp} "
                f"< run anchor {current_anchor.timestamp}"
            )
```

### 8.3 Unexpected Plan

```python
def _validate_trade_id(self, trade_id: str):
    """Ensure plan is for expected trade."""
    if trade_id not in self._expected_trade_ids:
        raise ValueError(
            f"Unexpected plan for trade {trade_id}. "
            f"Expected trades: {self._expected_trade_ids}"
        )
```

### 8.4 Timeout (Tick Boundary)

**NO explicit timeout logic needed** - tick timeout is hard limit.

If plans not received within tick:
- FlowTerminator cleanup triggered
- State reset happens automatically on next StrategyDirective

---

## 9. Test Coverage Requirements

### Minimum 30+ Tests

**State Management (8 tests):**
1. `test_on_strategy_directive_resets_state` - Fresh state per cycle
2. `test_reentry_guard_blocks_duplicate_run` - RunAnchor validation
3. `test_expected_trade_ids_new_trade` - Single NEW trade
4. `test_expected_trade_ids_multi_trade` - N target_trade_ids
5. `test_plans_by_trade_matrix_initialization` - Per-trade tracking
6. `test_state_reset_after_batch_published` - Cleanup
7. `test_stale_plan_rejected` - Old timestamp rejected
8. `test_unexpected_trade_id_rejected` - Unknown trade rejected

**Parallel Phase Coordination (6 tests):**
9. `test_parallel_phase_incomplete_entry_only` - 1/3 plans
10. `test_parallel_phase_incomplete_entry_size` - 2/3 plans
11. `test_parallel_phase_complete_all_three` - 3/3 → ExecutionRequest
12. `test_parallel_phase_multi_trade_independent` - Trade A complete, Trade B incomplete
13. `test_execution_request_published` - EXECUTION_INTENT_REQUESTED event
14. `test_execution_request_payload_structure` - All 3 plans included

**Sequential Phase Coordination (4 tests):**
15. `test_execution_plan_received_before_parallel` - Reject if parallel incomplete
16. `test_execution_plan_completes_trade` - 4/4 plans for 1 trade
17. `test_batch_waiting_for_other_trades` - Trade A done, Trade B pending
18. `test_batch_assembly_all_trades_complete` - N trades → Batch

**Batch Assembly (6 tests):**
19. `test_batch_single_directive` - 1 trade → Batch(size=1)
20. `test_batch_multi_directive` - 3 trades → Batch(size=3)
21. `test_batch_execution_mode_atomic` - Default ATOMIC mode
22. `test_batch_metadata_includes_directive_id` - Metadata populated
23. `test_batch_causality_chain` - Causality propagated (Issue #5 dependent)
24. `test_batch_published_event` - EXECUTION_DIRECTIVE_BATCH_READY

**Partial Plans (4 tests):**
25. `test_partial_exit_only_modification` - Only ExitPlan expected
26. `test_partial_entry_size_only` - Entry + Size, no Exit/Execution
27. `test_partial_expected_plans_determination` - StrategyDirective → expected types
28. `test_partial_batch_completion` - Complete with 2/4 plan types

**Error Handling (2 tests):**
29. `test_reentry_error_raised` - Duplicate run rejected
30. `test_stale_plan_error_raised` - Old timestamp rejected

---

## 10. Implementation Notes

### 10.1 IWorker Compliance

```python
class PlanningAggregator(IWorker, IWorkerLifecycle):
    """Multi-input aggregator implementing IWorker protocol."""
    
    def initialize(
        self,
        strategy_cache: IStrategyCache | None = None,
        **capabilities
    ) -> None:
        """Initialize with strategy_cache (Platform-within-Strategy worker)."""
        assert strategy_cache is not None, "PlanningAggregator requires strategy_cache"
        self.strategy_cache = strategy_cache
        self.event_bus = capabilities.get("event_bus")
        assert self.event_bus is not None, "PlanningAggregator requires event_bus"
    
    def shutdown(self) -> None:
        """Cleanup (if needed)."""
        self._reset_state()
```

### 10.2 EventAdapter Wiring

**Bootstrap creates EventAdapter per input connector:**

```python
# EventWiringFactory bootstrap
for input_connector in manifest.inputs:
    adapter = EventAdapter(
        worker=planning_aggregator,
        handler_method=getattr(planning_aggregator, input_connector.handler_method),
        event_bus=event_bus,
        scope=SubscriptionScope(level=ScopeLevel.STRATEGY, strategy_instance_id=strategy_id)
    )
    
    # Subscribe to event
    event_name = wiring_map.get_event_for_connector(input_connector.connector_id)
    event_bus.subscribe(event_name, adapter.on_event_received, scope)
```

---

## 11. Open Issues (BLOCKERS)

### Issue #4: ExecutionRequest DTO
**Status:** TODO in Week 4  
**Spec:** See Section 7.1  
**Blocker:** Cannot implement `_check_parallel_phase_completion()` without DTO

### Issue #5: Trade ID Propagation
**Status:** TODO - Decision needed  
**Options:** CausalityChain, plan_id embedding, separate field  
**Blocker:** Cannot implement `_extract_trade_id()` without decision  
**Related:** ExecutionDirectiveBatch causality chain representation

---

## 12. Quality Gates

**STAP 1 RED:**
- ✅ 30+ failing tests written
- ✅ `ModuleNotFoundError` confirmed (component doesn't exist yet)

**STAP 2 GREEN:**
- ✅ PlanningAggregator class implemented (all 5 handlers)
- ✅ State tracking logic implemented (per-trade matrix + RunAnchor guard)
- ✅ Phase coordination logic implemented (parallel/sequential detection)
- ✅ Batch assembly logic implemented
- ✅ All 30+ tests PASSING

**STAP 3 REFACTOR:**
- ✅ Pylint 10.00/10
- ✅ 0 Pylance warnings
- ✅ Comprehensive docstrings (class + all handlers)
- ✅ Quality Metrics Dashboard updated

---

## 13. Decision Log

### Decision 1: Always ExecutionDirectiveBatch (Not Dual Output)

**Question:** Single directive → EXECUTION_DIRECTIVE_READY or BATCH_READY?

**Decision:** ALWAYS `EXECUTION_DIRECTIVE_BATCH_READY` (even for single directive)

**Rationale:**
- ✅ Uniform consumer interface (ExecutionHandler always expects batch)
- ✅ No dual output complexity (single output event type)
- ✅ ExecutionDirectiveBatch(directives=[single]) is valid
- ✅ "BATCH" naming acceptable (batch size=1 is still a batch)

**Alternative Rejected:** Dual output (READY for single, BATCH_READY for multi)
- Complexity: 2 output events, conditional routing logic
- Consumer burden: ExecutionHandler needs 2 handlers

### Decision 2: Non-Reentrant (Within 1 Tick)

**Question:** Allow cross-tick planning (state preserved over ticks)?

**Decision:** NO - Planning MUST complete within 1 tick

**Rationale:**
- ✅ Simplicity: State reset per tick (via RunAnchor guard)
- ✅ Predictability: No stale state accumulation
- ✅ YAGNI: Async/syncio complexity NOT needed (explicit design choice)
- ✅ Clear lifecycle: Tick boundary = hard reset

**Alternative Rejected:** Cross-tick planning
- Complexity: State management over time, timeout logic
- Risk: Stale state bugs, race conditions
- Not needed: Planners are simple logic (no ML), execute fast

### Decision 3: Per-Strategy Singleton

**Question:** One global PlanningAggregator or per-strategy instance?

**Decision:** Per-strategy singleton (like FlowInitiator)

**Rationale:**
- ✅ Perfect isolation (strategy A state ≠ strategy B state)
- ✅ Simpler API (no strategy_id parameter needed)
- ✅ Clear lifecycle (created per strategy at bootstrap)
- ✅ Consistent pattern (matches FlowInitiator design)

---

## 14. Next Steps

### Prerequisites (Blockers)
1. ✅ Resolve Issue #4: Create ExecutionRequest DTO
2. ✅ Resolve Issue #5: Decide trade_id propagation mechanism
3. ✅ EventAdapter multi-input support verified

### STAP 1 RED: Write Failing Tests
**File:** `tests/unit/core/test_planning_aggregator.py`  
**Action:** Create 30+ failing test cases based on Section 9  
**Expected:** `ModuleNotFoundError: No module named 'backend.core.planning_aggregator'`

### STAP 2 GREEN: Implement Component
**File:** `backend/core/planning_aggregator.py`  
**Action:**
1. Create PlanningAggregator class (IWorker + IWorkerLifecycle)
2. Implement 5 event handlers (on_strategy_directive, on_entry_plan, etc.)
3. Implement state tracking (per-trade matrix + RunAnchor guard)
4. Implement phase coordination (_check_parallel_phase_completion, _check_batch_completion)
5. Implement batch assembly logic
6. Run tests → ALL GREEN ✅

### STAP 3 REFACTOR: Quality & Documentation
**Action:**
1. Pylint → 10/10 score
2. Add comprehensive docstrings (all public methods)
3. Update Quality Metrics Dashboard in `agent.md`
4. Final test run → 30/30 passing ✅

---

**END OF CONCEPTUAL DESIGN**

**Status:** Ready for Issue #4 & #5 resolution, then STAP 1 (RED)  
**Sign-off:** Architecture Team ✅  
**Date:** 2025-11-06
