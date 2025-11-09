# CausalityChain Lifecycle - Van Geboorte tot Terminatie

**Status:** Architecture Analysis  
**Datum:** 2025-11-07  
**Doel:** Complete traceability van CausalityChain door pipeline met focus op trade_id multipliciteit

---

## Executive Summary

Dit document beschrijft de volledige lifecycle van CausalityChain van het moment van "geboorte" (tick/news/schedule event) tot terminatie (FlowTerminator journaling). Het analyseert waar en wanneer trade_id(s) worden toegevoegd, met speciale aandacht voor **multipliciteit** (1 directive → N trades).

**Kernbevinding voor Issue #5:**
> Trade_id(s) worden toegevoegd in **PlanningAggregator fase**, niet eerder. De CausalityChain moet trade_id als **optional field** krijgen om beide scenario's te ondersteunen: NEW_TRADE (None) en MODIFY_EXISTING (set).

---

## 1. FASE 0: GEBOORTE (Birth ID Creation)

### Verantwoordelijkheid: DataProvider

**Waar gebeurt dit:** `backend/core/data_provider.py` (nog niet geïmplementeerd)

**Wat gebeurt er:**
```python
class CandleDataProvider:
    def on_candle_complete(self, raw_candle: RawCandle) -> None:
        """
        DataProvider creates the BIRTH ID.
        
        This is the ORIGIN of the strategy run - the "birth event".
        """
        # 1. Generate birth ID
        tick_id = generate_tick_id()  # "TCK_20251107_100000_abc123"
        
        # 2. Create provider DTO (CandleWindow, NewsEvent, etc.)
        candle_window = CandleWindow(
            symbol="BTCUSDT",
            timeframe="1h",
            candles=[...]
        )
        
        # 3. Wrap in PlatformDataDTO
        platform_dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=raw_candle.timestamp,
            payload=candle_window
        )
        
        # 4. Publish to FlowInitiator (per strategy)
        for strategy_id in self._registered_strategies:
            self._event_bus.publish(
                event_name=f"_candle_ready_{strategy_id}",
                payload=platform_dto,
                metadata={"tick_id": tick_id}  # ← Birth ID in metadata
            )
```

**Output:**
- ✅ Birth ID created: `tick_id` (or `news_id` / `schedule_id`)
- ✅ PlatformDataDTO published to FlowInitiator
- ❌ **GEEN CausalityChain DTO yet** (PlatformDataDTO heeft geen causality field)

**Design Rationale:**
- PlatformDataDTO is **minimal envelope** (zie DATA_PROVIDER_DESIGN.md)
- Birth ID zit in **event metadata**, niet in DTO
- CausalityChain wordt pas gecreëerd door eerste **pipeline worker**

---

## 2. FASE 1: FLOW INITIATION (Cache Initialization)

### Verantwoordelijkheid: FlowInitiator

**Waar gebeurt dit:** `backend/core/flow_initiator.py` (✅ geïmplementeerd)

**Wat gebeurt er:**
```python
class FlowInitiator(IWorker, IWorkerLifecycle):
    def on_data_ready(self, data: PlatformDataDTO) -> DispositionEnvelope:
        """
        FlowInitiator initializes cache but does NOT create CausalityChain.
        
        Why? FlowInitiator has no causality field in PlatformDataDTO to propagate.
        First pipeline worker creates the chain.
        """
        # 1. Initialize StrategyCache with timestamp
        self._cache.start_new_strategy_run({}, data.timestamp)
        
        # 2. Store payload in cache (by TYPE)
        self._cache.set_result_dto(data.payload)  # CandleWindow
        
        # 3. Return CONTINUE (EventAdapter publishes next event)
        return DispositionEnvelope(disposition="CONTINUE")
```

**Output:**
- ✅ StrategyCache initialized (RunAnchor created)
- ✅ Provider DTO stored in cache (CandleWindow, etc.)
- ❌ **GEEN CausalityChain created** (FlowInitiator heeft geen access tot birth ID uit metadata)

**Design Question:**
> **Moet FlowInitiator de CausalityChain creëren?**
> 
> **Option A:** EventAdapter passes event metadata to handler
> ```python
> def on_data_ready(
>     self, 
>     data: PlatformDataDTO,
>     event_metadata: dict  # ← NEW parameter
> ) -> DispositionEnvelope:
>     tick_id = event_metadata.get("tick_id")
>     
>     # Store birth ID in cache for workers
>     self._cache.set_birth_context(tick_id=tick_id)
> ```
>
> **Option B:** First worker creates CausalityChain
> ```python
> class ContextWorker:
>     def process(self) -> DispositionEnvelope:
>         # Extract birth ID from... where?
>         # Problem: Birth ID lost after FlowInitiator!
> ```

**CURRENT DESIGN GAP:** Birth ID propagation mechanism onduidelijk.

---

## 3. FASE 2: CONTEXT ANALYSIS (First CausalityChain Creation)

### Verantwoordelijkheid: ContextWorkers (via ContextAggregator?)

**Probleem:** ContextWorkers produceren **geen DTOs met causality**

Van OBJECTIVE_DATA_PHILOSOPHY.md:
```python
class EMADetector(StandardWorker):
    def process(self) -> DispositionEnvelope:
        # Produces EMAOutputDTO (no causality field)
        self._cache.set_result_dto(EMAOutputDTO(ema_20=50100.50))
        return DispositionEnvelope(disposition="CONTINUE")
```

**Design Implication:**
- ContextWorkers produceren **objective facts** zonder causality
- **GEEN worker in Context Analysis fase creëert CausalityChain**

**Where DOES it start?**

---

## 4. FASE 3: SIGNAL DETECTION (CausalityChain Birth)

### Verantwoordelijkheid: SignalDetector

**Waar gebeurt dit:** `backend/dtos/strategy/signal.py` (✅ geïmplementeerd)

**Wat gebeurt er:**
```python
class SignalDetector(StandardWorker):
    def process(self) -> DispositionEnvelope:
        """
        SignalDetector is the FIRST worker to create CausalityChain.
        
        Question: Where does tick_id come from?
        """
        # Get context facts from cache
        dtos = self._cache.get_required_dtos()
        ema_data = dtos[EMAOutputDTO]
        
        # Apply interpretation
        if self._is_signal_detected(ema_data):
            # CREATE CAUSALITY CHAIN
            causality = CausalityChain(
                tick_id=???  # ← WHERE DOES THIS COME FROM?
                # signal_ids will be added after signal creation
            )
            
            signal = Signal(
                signal_id=generate_signal_id(),
                causality=causality,  # ← NEW chain
                signal_type="FVG_ENTRY",
                direction="long",
                confidence=0.8
            )
            
            # Extend chain with own ID
            signal.causality = signal.causality.model_copy(update={
                "signal_ids": [signal.signal_id]
            })
            
            self._cache.set_result_dto(signal)
            return DispositionEnvelope(
                disposition="PUBLISH",
                connector_id="signal_output",
                payload=signal
            )
        
        return DispositionEnvelope(disposition="CONTINUE")
```

**CRITICAL DESIGN GAP:**
> **Hoe komt SignalDetector aan tick_id?**
> 
> **Option 1:** StrategyCache bewaart birth context
> ```python
> # FlowInitiator stores it
> self._cache.set_birth_context(tick_id=event_metadata["tick_id"])
> 
> # SignalDetector retrieves it
> birth_context = self._cache.get_birth_context()
> causality = CausalityChain(tick_id=birth_context.tick_id)
> ```
>
> **Option 2:** RunAnchor bevat birth ID
> ```python
> class RunAnchor:
>     timestamp: datetime
>     birth_id: str  # ← NEW field (tick_id/news_id/schedule_id)
>     birth_type: str  # "tick" | "news" | "schedule"
> ```

**Output:**
- ✅ CausalityChain CREATED with birth ID
- ✅ Signal ID added to chain
- ✅ Signal DTO has causality field
- ❌ **Trade ID is None** (no trade exists yet)

---

## 5. FASE 4: RISK MONITORING (Chain Propagation)

### Verantwoordelijkheid: RiskMonitor

**Waar gebeurt dit:** `backend/dtos/strategy/risk.py` (✅ geïmplementeerd)

**Wat gebeurt er:**
```python
class RiskMonitor(StandardWorker):
    def process(self) -> DispositionEnvelope:
        """
        RiskMonitor extends existing CausalityChain.
        """
        # Get context (including any signals)
        signals = self._cache.get_result_dtos_by_type(Signal)
        
        if self._is_risk_detected():
            # Get existing causality from signal (if exists)
            if signals:
                base_causality = signals[0].causality
            else:
                # No signal? Create new chain
                birth_context = self._cache.get_birth_context()
                base_causality = CausalityChain(tick_id=birth_context.tick_id)
            
            risk_id = generate_risk_id()
            
            # EXTEND chain (not replace!)
            risk_causality = base_causality.model_copy(update={
                "risk_ids": base_causality.risk_ids + [risk_id]
            })
            
            risk = Risk(
                risk_id=risk_id,
                causality=risk_causality,
                risk_type="STOP_LOSS_HIT",
                severity=0.9
            )
            
            self._cache.set_result_dto(risk)
            return DispositionEnvelope(
                disposition="PUBLISH",
                connector_id="risk_output",
                payload=risk
            )
        
        return DispositionEnvelope(disposition="CONTINUE")
```

**Output:**
- ✅ CausalityChain EXTENDED with risk_id
- ✅ Chain now has: tick_id, signal_ids (from signal), risk_ids (new)
- ❌ **Trade ID still None** (no trade planned yet)

**Key Pattern:**
```python
# ALWAYS extend, never replace
extended = base_causality.model_copy(update={
    "risk_ids": base_causality.risk_ids + [new_risk_id]
})
```

---

## 6. FASE 5: STRATEGY PLANNING (Directive Creation)

### Verantwoordelijkheid: StrategyPlanner

**Waar gebeurt dit:** `backend/dtos/strategy/strategy_directive.py` (✅ geïmplementeerd)

**Wat gebeurt er:**
```python
class StrategyPlanner(StandardWorker):
    def process(self) -> DispositionEnvelope:
        """
        StrategyPlanner creates StrategyDirective with causality.
        
        CRITICAL: This is where trade_id COULD be known (for MODIFY_EXISTING).
        For NEW_TRADE, trade_id is still None.
        """
        # Get signals and risks
        signals = self._cache.get_result_dtos_by_type(Signal)
        risks = self._cache.get_result_dtos_by_type(Risk)
        
        # Start with signal causality (or risk causality if no signal)
        if signals:
            base_causality = signals[0].causality
        elif risks:
            base_causality = risks[0].causality
        else:
            # No signal/risk? Use birth only
            birth_context = self._cache.get_birth_context()
            base_causality = CausalityChain(tick_id=birth_context.tick_id)
        
        # Generate directive ID
        directive_id = generate_strategy_directive_id()
        
        # EXTEND chain
        directive_causality = base_causality.model_copy(update={
            "strategy_directive_id": directive_id
        })
        
        # Create directive
        directive = StrategyDirective(
            directive_id=directive_id,
            causality=directive_causality,
            scope=DirectiveScope.NEW_TRADE,  # or MODIFY_EXISTING
            target_trade_ids=[],  # Empty for NEW_TRADE
            confidence=0.85,
            entry_directive=EntryDirective(...),
            size_directive=SizeDirective(...),
            exit_directive=ExitDirective(...),
            routing_directive=ExecutionDirective(...)
        )
        
        self._cache.set_result_dto(directive)
        return DispositionEnvelope(
            disposition="PUBLISH",
            connector_id="directive_output",
            payload=directive
        )
```

**Output:**
- ✅ CausalityChain has: tick_id, signal_ids, risk_ids, strategy_directive_id
- ✅ StrategyDirective has target_trade_ids (empty for NEW_TRADE, populated for MODIFY_EXISTING)
- ❌ **CausalityChain.trade_id still None** (trade not created yet)

**Key Observation:**
```python
# StrategyDirective knows target_trade_ids (business level)
directive.target_trade_ids = ["TRD_123", "TRD_456"]

# But CausalityChain does NOT (audit trail level)
directive.causality.trade_id = None  # ← Still None!
```

**Why the separation?**
- `target_trade_ids` = Business instruction ("modify these trades")
- `causality.trade_id` = Audit trail ("which trade does THIS execution target")

---

## 7. FASE 6: SUB-PLANNING (Plans WITHOUT Causality)

### Verantwoordelijkheid: EntryPlanner, SizePlanner, ExitPlanner, ExecutionIntentPlanner

**Waar gebeurt dit:** `backend/dtos/strategy/*.py` (✅ geïmplementeerd)

**CRITICAL DESIGN:** Sub-planners **NIET** hebben causality field!

Van `entry_plan.py`:
```python
"""
**Causality Propagation:**
Sub-planners receive StrategyDirective as input (has causality).
PlanningAggregator extracts causality from StrategyDirective and
adds plan IDs to create ExecutionDirective with complete chain.
"""

class EntryPlan(BaseModel):
    plan_id: str
    symbol: str
    direction: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP_LIMIT"]
    # NO causality field!
```

**What happens:**
```python
class EntryPlanner(StandardWorker):
    def process(self) -> DispositionEnvelope:
        """
        EntryPlanner creates plan WITHOUT causality.
        
        It reads StrategyDirective (which HAS causality) but
        does NOT propagate it to EntryPlan.
        """
        # Get directive
        directive = self._cache.get_result_dto(StrategyDirective)
        
        # Create plan (NO causality!)
        plan = EntryPlan(
            plan_id=generate_entry_plan_id(),
            symbol=directive.entry_directive.symbol,
            direction=directive.entry_directive.direction,
            order_type="LIMIT",
            limit_price=self._calculate_entry_price()
        )
        
        self._cache.set_result_dto(plan)
        return DispositionEnvelope(
            disposition="PUBLISH",
            connector_id="entry_plan_output",
            payload=plan
        )
```

**Output:**
- ✅ EntryPlan, SizePlan, ExitPlan, ExecutionPlan created
- ❌ **Plans have NO causality field** (by design)
- ❌ **Plans have NO trade_id field** (by design)

**Why?**
- Plans are **pure execution parameters** (WHAT/WHERE/HOW)
- PlanningAggregator is responsible for **causality propagation**
- Keeps plans simple and focused on their SRP

---

## 8. FASE 7: PLANNING AGGREGATION (Trade ID Assignment) ← **CRITICAL FOR ISSUE #5**

### Verantwoordelijkheid: PlanningAggregator

**Waar gebeurt dit:** `backend/core/planning_aggregator.py` (PENDING implementation)

**THIS IS WHERE TRADE_ID IS ADDED TO CAUSALITYCHAIN!**

```python
class PlanningAggregator:
    def on_strategy_directive(self, directive: StrategyDirective) -> DispositionEnvelope:
        """
        Initialize aggregator state with trade IDs.
        
        THIS IS WHERE WE KNOW WHICH TRADES ARE BEING PLANNED.
        """
        # Reset state
        self._strategy_directive = directive
        
        # Determine expected trades
        if directive.scope == DirectiveScope.NEW_TRADE:
            # NEW_TRADE: Generate new trade ID
            new_trade_id = generate_trade_id()
            self._expected_trade_ids = {new_trade_id}
        else:
            # MODIFY_EXISTING: Use target_trade_ids
            self._expected_trade_ids = set(directive.target_trade_ids)
        
        # Initialize per-trade tracking
        self._plans_by_trade = {tid: {} for tid in self._expected_trade_ids}
        
        return DispositionEnvelope(disposition="CONTINUE")
    
    def _check_batch_completion(self) -> DispositionEnvelope:
        """
        Create ExecutionDirectiveBatch when all plans received.
        
        THIS IS WHERE TRADE_ID IS ADDED TO CAUSALITYCHAIN!
        """
        # All trades complete - assemble batch
        directives = []
        
        for trade_id in self._expected_trade_ids:
            plans = self._plans_by_trade[trade_id]
            
            # EXTEND causality with plan IDs AND trade_id
            directive_causality = self._strategy_directive.causality.model_copy(update={
                "entry_plan_id": plans["entry"].plan_id,
                "size_plan_id": plans["size"].plan_id,
                "exit_plan_id": plans["exit"].plan_id,
                "execution_plan_id": plans["execution"].plan_id,
                "trade_id": trade_id  # ← FINALLY! Trade ID added!
            })
            
            # Generate execution directive ID
            directive_id = generate_execution_directive_id()
            
            # EXTEND again with directive ID
            final_causality = directive_causality.model_copy(update={
                "execution_directive_id": directive_id
            })
            
            # Create ExecutionDirective
            directive = ExecutionDirective(
                directive_id=directive_id,
                causality=final_causality,  # ← Complete chain with trade_id!
                entry_plan=plans["entry"],
                size_plan=plans["size"],
                exit_plan=plans["exit"],
                execution_plan=plans["execution"]
            )
            
            directives.append(directive)
        
        # Create batch
        batch = ExecutionDirectiveBatch(
            batch_id=generate_batch_id(),
            directives=directives
        )
        
        return DispositionEnvelope(
            disposition="PUBLISH",
            connector_id="execution_directive_batch_output",
            payload=batch
        )
```

**Output:**
- ✅ **CausalityChain NOW HAS trade_id!**
- ✅ ExecutionDirective has complete causality chain
- ✅ Each directive in batch has DIFFERENT trade_id
- ✅ All directives share same birth_id, signal_ids, risk_ids, strategy_directive_id

**Multipliciteit Pattern:**
```python
# 1 StrategyDirective → 3 ExecutionDirectives

# StrategyDirective causality:
CausalityChain(
    tick_id="TCK_...",
    signal_ids=["SIG_..."],
    strategy_directive_id="STR_...",
    trade_id=None  # ← Not yet assigned
)

# ExecutionDirective[0] causality:
CausalityChain(
    tick_id="TCK_...",  # SAME
    signal_ids=["SIG_..."],  # SAME
    strategy_directive_id="STR_...",  # SAME
    entry_plan_id="ENT_..._1",
    size_plan_id="SIZ_..._1",
    exit_plan_id="EXT_..._1",
    execution_plan_id="EXP_..._1",
    execution_directive_id="EXE_..._1",
    trade_id="TRD_123"  # ← UNIQUE
)

# ExecutionDirective[1] causality:
CausalityChain(
    tick_id="TCK_...",  # SAME
    signal_ids=["SIG_..."],  # SAME
    strategy_directive_id="STR_...",  # SAME
    entry_plan_id="ENT_..._2",
    size_plan_id="SIZ_..._2",
    exit_plan_id="EXT_..._2",
    execution_plan_id="EXP_..._2",
    execution_directive_id="EXE_..._2",
    trade_id="TRD_456"  # ← UNIQUE
)
```

**KEY INSIGHT:**
> CausalityChain "branches" bij PlanningAggregator:
> - Upstream delen (tick, signal, risk, directive) = SHARED
> - Downstream delen (plans, trade_id, execution) = UNIQUE per trade

---

## 9. FASE 8: EXECUTION (Chain Preserved)

### Verantwoordelijkheid: ExecutionHandler

**Waar gebeurt dit:** `backend/execution/execution_handler.py` (niet geïmplementeerd)

**Wat gebeurt er:**
```python
class ExecutionHandler:
    def on_execution_directive_batch(
        self,
        batch: ExecutionDirectiveBatch
    ) -> DispositionEnvelope:
        """
        ExecutionHandler executes directives but does NOT modify causality.
        
        Causality is complete at this point - just preserve it.
        """
        for directive in batch.directives:
            # Execute trade
            order_result = self._execute_directive(directive)
            
            # Causality is COMPLETE - no changes needed
            # directive.causality has full chain:
            # - tick_id (birth)
            # - signal_ids (detection)
            # - risk_ids (risk monitoring)
            # - strategy_directive_id (planning decision)
            # - entry/size/exit/execution_plan_ids (tactical planning)
            # - execution_directive_id (execution instruction)
            # - trade_id (which trade this targets)
            
            # Pass causality to journal
            self._journal_execution(directive, order_result)
        
        return DispositionEnvelope(disposition="STOP")
```

**Output:**
- ✅ Trades executed
- ✅ CausalityChain UNCHANGED (complete vanaf PlanningAggregator)
- ✅ Ready for FlowTerminator

---

## 10. FASE 9: TERMINATION (Journal Reconstruction)

### Verantwoordelijkheid: FlowTerminator

**Waar gebeurt dit:** `backend/core/flow_terminator.py` (niet geïmplementeerd)

**Wat gebeurt er:**
```python
class FlowTerminator:
    def on_flow_stop(self, batch: ExecutionDirectiveBatch) -> DispositionEnvelope:
        """
        FlowTerminator uses CausalityChain for complete audit trail.
        
        This is the ONLY component that READS causality chains for reconstruction.
        """
        for directive in batch.directives:
            chain = directive.causality
            
            # RECONSTRUCT COMPLETE DECISION CHAIN
            
            # 1. Birth event
            if chain.tick_id:
                tick = self._journal.get_tick(chain.tick_id)
                self._log(f"Strategy run born from tick {tick.timestamp}")
            
            # 2. Signal detection
            for signal_id in chain.signal_ids:
                signal = self._journal.get_signal(signal_id)
                self._log(f"Signal detected: {signal.signal_type} @ {signal.confidence}")
            
            # 3. Risk monitoring
            for risk_id in chain.risk_ids:
                risk = self._journal.get_risk(risk_id)
                self._log(f"Risk detected: {risk.risk_type} @ {risk.severity}")
            
            # 4. Strategy decision
            strategy_directive = self._journal.get_strategy_directive(
                chain.strategy_directive_id
            )
            self._log(f"Strategy decided: {strategy_directive.scope}")
            
            # 5. Tactical planning
            entry_plan = self._journal.get_entry_plan(chain.entry_plan_id)
            size_plan = self._journal.get_size_plan(chain.size_plan_id)
            exit_plan = self._journal.get_exit_plan(chain.exit_plan_id)
            execution_plan = self._journal.get_execution_plan(chain.execution_plan_id)
            
            # 6. Trade identification
            self._log(f"Trade executed: {chain.trade_id}")
            
            # 7. Write complete causality chain
            self._journal.write_causality_chain({
                "birth": chain.tick_id,
                "signals": chain.signal_ids,
                "risks": chain.risk_ids,
                "directive": chain.strategy_directive_id,
                "plans": {
                    "entry": chain.entry_plan_id,
                    "size": chain.size_plan_id,
                    "exit": chain.exit_plan_id,
                    "execution": chain.execution_plan_id
                },
                "execution": chain.execution_directive_id,
                "trade": chain.trade_id,
                "timestamp": datetime.now(UTC)
            })
        
        # Cleanup
        self._cleanup_components()
        
        return DispositionEnvelope(
            disposition="PUBLISH",
            connector_id="flow_terminated",
            payload={}
        )
```

**Output:**
- ✅ Complete audit trail in Journal
- ✅ Full traceability: tick → signal → risk → directive → plans → execution → trade
- ✅ Per-trade causality chains logged
- ✅ Components cleaned up

---

## 11. DESIGN IMPLICATIONS FOR ISSUE #5

### CausalityChain Field Requirements

```python
class CausalityChain(BaseModel):
    # Birth IDs (at least 1 required)
    tick_id: str | None = None
    news_id: str | None = None
    schedule_id: str | None = None
    
    # Worker output IDs
    signal_ids: list[str] = Field(default_factory=list)
    risk_ids: list[str] = Field(default_factory=list)
    strategy_directive_id: str | None = None
    
    # Plan IDs (added by PlanningAggregator)
    entry_plan_id: str | None = None
    size_plan_id: str | None = None
    exit_plan_id: str | None = None
    execution_plan_id: str | None = None
    
    # Execution IDs (added by PlanningAggregator)
    execution_directive_id: str | None = None
    
    # Trade tracking (added by PlanningAggregator)
    trade_id: str | None = None  # ← SOLUTION TO ISSUE #5!
```

### Why trade_id Belongs in CausalityChain

**✅ Architecturally Consistent:**
- execution_directive_id is in CausalityChain
- trade_id is execution-phase identifier (same level)
- Keeps audit trail complete

**✅ Supports Both Scenarios:**
```python
# NEW_TRADE scenario
causality = CausalityChain(
    tick_id="TCK_...",
    signal_ids=["SIG_..."],
    strategy_directive_id="STR_...",
    trade_id="TRD_NEW_123"  # ← Generated by PlanningAggregator
)

# MODIFY_EXISTING scenario
causality = CausalityChain(
    tick_id="TCK_...",
    risk_ids=["RSK_..."],
    strategy_directive_id="STR_...",
    trade_id="TRD_123"  # ← From directive.target_trade_ids[0]
)
```

**✅ Solves Multipliciteit:**
```python
# 1 StrategyDirective → N ExecutionDirectives
for trade_id in expected_trade_ids:
    causality = base_causality.model_copy(update={
        "trade_id": trade_id,  # ← UNIQUE per directive
        "execution_directive_id": generate_execution_directive_id()
    })
```

**✅ Perfect for FlowTerminator:**
```python
# Query journal by trade_id
def on_flow_stop(self, batch: ExecutionDirectiveBatch):
    for directive in batch.directives:
        # Each directive has unique trade_id in causality
        self._journal.write_trade_execution(
            trade_id=directive.causality.trade_id,
            causality_chain=directive.causality
        )
```

---

## 12. REMAINING DESIGN GAPS

### GAP 1: Birth ID Propagation

**Problem:** Hoe komt birth ID van DataProvider → SignalDetector?

**Solution Options:**

**A) EventAdapter passes metadata to handlers:**
```python
# EventAdapter modification
def on_event_received(self, event: Event):
    result = self._handler(
        event.payload,
        event_metadata=event.metadata  # ← NEW parameter
    )

# SignalDetector signature
def process(self, event_metadata: dict | None = None):
    if event_metadata and "tick_id" in event_metadata:
        tick_id = event_metadata["tick_id"]
```

**B) RunAnchor contains birth ID:**
```python
class RunAnchor:
    timestamp: datetime
    birth_id: str  # tick_id / news_id / schedule_id
    birth_type: Literal["tick", "news", "schedule"]

# FlowInitiator stores it
self._cache.start_new_strategy_run(
    birth_id=event_metadata["tick_id"],
    birth_type="tick",
    timestamp=data.timestamp
)

# SignalDetector retrieves it
anchor = self._cache.get_run_anchor()
causality = CausalityChain(tick_id=anchor.birth_id)
```

**Recommendation:** Option B (cleaner, RunAnchor already exists)

### GAP 2: ExecutionDirectiveBatch Causality

**Problem:** Batch bevat N directives, elk met eigen causality. Heeft batch zelf causality nodig?

**Solution:**
```python
class ExecutionDirectiveBatch:
    batch_id: str
    directives: list[ExecutionDirective]  # Each has own causality
    # NO batch-level causality field needed!
    
# FlowTerminator iterates over directives
for directive in batch.directives:
    # Each directive has complete causality chain
    self._journal.write_chain(directive.causality)
```

**Recommendation:** Batch heeft GEEN eigen causality field (directives hebben het al)

---

## 13. COMPLETE LIFECYCLE SUMMARY

| Fase | Component | CausalityChain Status | Trade ID Status |
|------|-----------|----------------------|-----------------|
| 0. Birth | DataProvider | NOT created | N/A |
| 1. Initiation | FlowInitiator | NOT created | N/A |
| 2. Context | ContextWorkers | NOT created (no causality in output) | N/A |
| 3. Signal | SignalDetector | **CREATED** with birth ID | None |
| 4. Risk | RiskMonitor | EXTENDED with risk_ids | None |
| 5. Strategy | StrategyPlanner | EXTENDED with strategy_directive_id | None |
| 6. Sub-Planning | Entry/Size/Exit/ExecutionPlanner | Plans have NO causality | None |
| 7. Aggregation | **PlanningAggregator** | **EXTENDED with plan IDs + trade_id** | **SET!** |
| 8. Execution | ExecutionHandler | UNCHANGED (complete) | PRESERVED |
| 9. Termination | FlowTerminator | USED for reconstruction | LOGGED |

**Key Takeaway:**
> Trade_id wordt toegevoegd in **FASE 7 (PlanningAggregator)**, samen met plan IDs en execution_directive_id.

---

## 14. AANBEVELING VOOR ISSUE #5

### Implement trade_id in CausalityChain

```python
# backend/dtos/causality.py

class CausalityChain(BaseModel):
    # ... existing fields ...
    
    # Trade tracking (execution phase)
    trade_id: str | None = Field(
        default=None,
        description=(
            "Trade ID - identifies which trade this execution targets. "
            "Set by PlanningAggregator. None for NEW_TRADE until ID generated. "
            "Set from target_trade_ids for MODIFY_EXISTING/CLOSE_EXISTING."
        )
    )
```

### PlanningAggregator Implementation

```python
# backend/core/planning_aggregator.py

class PlanningAggregator:
    def _check_batch_completion(self) -> DispositionEnvelope:
        directives = []
        
        for trade_id in self._expected_trade_ids:
            plans = self._plans_by_trade[trade_id]
            
            # Extend causality with plan IDs AND trade_id
            causality = self._strategy_directive.causality.model_copy(update={
                "entry_plan_id": plans["entry"].plan_id,
                "size_plan_id": plans["size"].plan_id,
                "exit_plan_id": plans["exit"].plan_id,
                "execution_plan_id": plans["execution"].plan_id,
                "execution_directive_id": generate_execution_directive_id(),
                "trade_id": trade_id  # ← SOLUTION!
            })
            
            directive = ExecutionDirective(
                directive_id=causality.execution_directive_id,
                causality=causality,
                entry_plan=plans["entry"],
                size_plan=plans["size"],
                exit_plan=plans["exit"],
                execution_plan=plans["execution"]
            )
            
            directives.append(directive)
        
        return DispositionEnvelope(...)
```

### FlowTerminator Usage

```python
# backend/core/flow_terminator.py

class FlowTerminator:
    def on_flow_stop(self, batch: ExecutionDirectiveBatch):
        for directive in batch.directives:
            # Complete causality chain available
            self._journal.write_execution({
                "trade_id": directive.causality.trade_id,
                "birth_event": directive.causality.tick_id,
                "decision_chain": {
                    "signals": directive.causality.signal_ids,
                    "risks": directive.causality.risk_ids,
                    "directive": directive.causality.strategy_directive_id,
                    "plans": {
                        "entry": directive.causality.entry_plan_id,
                        "size": directive.causality.size_plan_id,
                        "exit": directive.causality.exit_plan_id,
                        "execution": directive.causality.execution_plan_id
                    },
                    "execution": directive.causality.execution_directive_id
                }
            })
```

---

## 15. VOORDELEN VAN DEZE OPLOSSING

**✅ Absolute Traceerbaarheid:**
- Volledige chain van tick → trade in één DTO
- FlowTerminator kan complete audit trail reconstrueren
- Elke trade heeft unieke causality chain

**✅ Eenduidigheid van Structuur:**
- trade_id volgt hetzelfde pattern als execution_directive_id
- Consistent met bestaande architectuur
- Geen nieuwe DTO fields in plans nodig

**✅ Multipliciteit Support:**
- 1 directive → N trades = N unique causality chains
- Shared upstream (tick, signal, risk, directive)
- Unique downstream (plans, trade_id, execution)

**✅ Backward Compatible:**
- Existing DTOs unchanged
- Only CausalityChain gets new optional field
- PlanningAggregator is new component (geen breaking changes)

---

**Document Status:** Architecture Analysis Complete  
**Next Steps:** Implement trade_id in CausalityChain + PlanningAggregator  
**Owner:** Platform Architecture Team  
**Date:** 2025-11-07
