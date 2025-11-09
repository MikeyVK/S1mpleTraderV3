# DTO Architecture - S1mpleTraderV3

**Status:** Architectural Foundation  
**Last Updated:** 2025-11-09  
**Version:** 1.0

---

## Executive Summary

This document describes **WHY each DTO exists** and **WHY each field exists**.

**Purpose:**
- Pure architectural rationale (no code, no examples)
- Field-level justification for every DTO
- Lifecycle tracking (Created → Consumed → Persisted/Discarded)
- Design decision documentation

**This document does NOT contain:**
- Code examples
- Implementation details
- Usage patterns (see WORKER_DATA_ACCESS.md)
- Pipeline sequencing (see PIPELINE_FLOW.md)

**Cross-references:**
- [PIPELINE_FLOW.md](PIPELINE_FLOW.md) - Phase sequencing (WHAT happens WHEN)
- [EXECUTION_FLOW.md](EXECUTION_FLOW.md) - Sync/async flows + SRP responsibilities
- [WORKER_DATA_ACCESS.md](WORKER_DATA_ACCESS.md) - Data access patterns

---

## DTO Taxonomy

### Platform DTOs (Origin Tracking & Data Ingestion)
1. **Origin** - Type-safe platform data source identification
2. **PlatformDataDTO** - Minimal envelope for platform data ingestion

### Analysis DTOs (Detection → Decision)
3. **Signal** - Trading opportunity detection output
4. **Risk** - Threat/risk detection output  
5. **StrategyDirective** - Strategy planning decision output

### Planning DTOs (Decision → Execution Intent)
6. **EntryPlan** - Entry execution specifications
7. **SizePlan** - Position sizing specifications
8. **ExitPlan** - Exit/stop-loss specifications
9. **ExecutionPlan** - Execution trade-offs (urgency, slippage, visibility)

### Execution DTOs (Orders & Coordination)
10. **ExecutionDirective** - Aggregated execution instruction
11. **ExecutionDirectiveBatch** - Multi-directive atomic coordination
12. **ExecutionGroup** - Multi-order relationship tracking

### Cross-Cutting DTOs (Infrastructure)
13. **CausalityChain** - ID-only causality tracking
14. **DispositionEnvelope** - Worker output routing control

---

## Platform DTOs

### Origin

**Purpose:** Type-safe platform data source identification

**WHY this DTO exists:**
- Platform data arrives from fundamentally different sources (TICK/NEWS/SCHEDULE/ETC)
- Each source has distinct characteristics requiring different handling:
  - TICK: Real-time market data (high frequency, time-sensitive)
  - NEWS: Event-driven data (irregular, context-rich)
  - SCHEDULE: Time-triggered data (predictable, no external dependency)
- Type-safe discrimination prevents category errors (treating news as tick data)
- Immutable origin provides audit trail foundation
- Prefix validation (TCK_/NWS_/SCH_) enforces ID discipline

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | DataProvider | Creates Origin from exchange ticks, news feeds, or scheduler events |
| **Consumers** | PlatformDataDTO | Embeds origin for envelope routing |
| | CausalityChain | Foundation for causal ID chain (origin → signal_id → ...) |
| | FlowInitiator | Validates origin type matches payload structure |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `id` | str | Yes | Unique identifier with source-specific prefix (TCK_/NWS_/SCH_). Enables unambiguous origin reference throughout pipeline. Validated format prevents ID pollution. |
| `type` | OriginType | Yes | Discriminator enum (TICK/NEWS/SCHEDULE). Enables type-safe routing without string parsing. Compiler-enforced correctness. |

**WHY frozen:**
- Origin is immutable fact - platform data source cannot retroactively change
- Prevents accidental modification during pipeline flow
- Enables safe sharing across workers without defensive copying
- Causality chain integrity depends on immutable origin reference

**WHY NOT included:**
- ❌ `timestamp` - Belongs to PlatformDataDTO (origin is timeless identifier, not point-in-time)
- ❌ `metadata` - Origin is pure identity, not enrichment (metadata belongs in payload)
- ❌ `priority` - Scheduling concern, not identity concern

**Lifecycle:**
```
Created:    DataProvider (from exchange/scheduler/news feed)
Copied:     FlowInitiator → PlatformDataDTO → CausalityChain
Propagated: Through entire pipeline via CausalityChain
Persisted:  StrategyJournal (causality reconstruction)
Never:      Modified (frozen model)
```

**Design Decisions:**
- **Decision 1:** Enum over string for `type`
  - Rationale: Compiler-enforced correctness, no typos, IDE autocomplete
  - Alternative rejected: String literals (error-prone, no type safety)
  
- **Decision 2:** Prefix validation in ID
  - Rationale: Self-documenting IDs, prevents ID pollution, enables visual debugging
  - Alternative rejected: Separate prefix field (redundant with type enum)

- **Decision 3:** Frozen model
  - Rationale: Origin is immutable fact, prevents accidental mutation
  - Alternative rejected: Mutable (breaks causality chain integrity)

---

### PlatformDataDTO

**Purpose:** Minimal envelope for heterogeneous platform data ingestion

**WHY this DTO exists:**
- Platform data arrives in vastly different shapes (CandleWindow, NewsEvent, ScheduleEvent, etc.)
- Need uniform interface for FlowInitiator without coupling to payload structure
- Separates "envelope" concern (routing metadata) from "payload" concern (actual data) - SRP
- Enables type-safe routing based on origin WITHOUT payload inspection
- Minimal coupling principle (only 3 fields - KISS)
- Point-in-time model enforcement (every data snapshot has explicit timestamp)

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | DataProvider | Wraps platform-specific payloads (CandleWindow, NewsEvent, etc.) with origin + timestamp |
| **Consumers** | FlowInitiator | Unwraps envelope, validates origin, stores payload in StrategyCache |
| | CausalityChain | Copies origin field as causal chain foundation |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `origin` | Origin | Yes | Platform source discrimination. Enables FlowInitiator to route/validate without inspecting payload. Type-safe origin tracking prevents category errors. |
| `timestamp` | datetime | Yes | Point-in-time anchor. ALL strategy decisions reference THIS moment. RunAnchor foundation. Enables tick boundary detection and stale data prevention. UTC-enforced for consistency. |
| `payload` | BaseModel | Yes | Actual platform data (CandleWindow, NewsEvent, etc). Plugin-specific structure. FlowInitiator stores in StrategyCache without interpretation. Type remains abstract (loose coupling). |

**WHY frozen:**
- Platform data is immutable snapshot of reality at specific moment
- Cannot change after creation (data integrity principle)
- Prevents accidental mutation during pipeline flow
- Payload immutability cascades (payload DTOs should also be frozen)

**WHY NOT included:**
- ❌ `source_type: str` - String-based type identification lacks compiler enforcement, error-prone
- ❌ `payload_type: Type` - Python type system handles this (unnecessary runtime metadata)
- ❌ `metadata: dict` - Belongs in payload, not envelope (SRP violation)
- ❌ `strategy_id` - Routing concern, not data concern (handled by EventAdapter)
- ❌ `validation_status` - Processing concern, not data concern (handle via exceptions)

**Lifecycle:**
```
Created:    DataProvider (wraps platform-specific data from exchange/scheduler/news)
Validated:  FlowInitiator (timestamp check, origin validation)
Consumed:   FlowInitiator (unwraps payload → stores in StrategyCache)
Propagated: Origin field copied to CausalityChain
Discarded:  After FlowInitiator completes (envelope purpose fulfilled)
Never:      Stored long-term (only payload persists in StrategyCache)
```

**Design Decisions:**
- **Decision 1:** Origin over source_type string
  - Rationale: Type safety, compiler-enforced correctness, no string parsing
  - Alternative rejected: `source_type: str` (error-prone, lacks type safety)
  
- **Decision 2:** Abstract BaseModel payload
  - Rationale: Loose coupling - FlowInitiator doesn't need payload knowledge
  - Alternative rejected: Generic[T] (unnecessary complexity, runtime type erasure anyway)

- **Decision 3:** Three fields only (minimalism)
  - Rationale: KISS principle, SRP (envelope ≠ payload), reduce coupling surface
  - Alternative rejected: Rich envelope with metadata (violates SRP, tight coupling)

- **Decision 4:** Frozen model
  - Rationale: Immutable snapshots, data integrity, safe concurrent access
  - Alternative rejected: Mutable (breaks point-in-time model guarantees)

**Validation Strategy:**
- Origin ID prefix matches origin type (TCK_ for TICK, etc.)
- Timestamp is timezone-aware (UTC enforced)
- Payload is frozen BaseModel subclass (immutability cascade)
- No cross-field business validation (payload responsibility)

---

## Analysis DTOs

### Signal

**Purpose:** Trading opportunity detection output from SignalDetectors

**WHY this DTO exists:**
- SignalDetectors produce objective pattern detection events (entry/exit opportunities)
- Separates "pattern detected" from "trade decision" (SRP - StrategyPlanner decides)
- Confidence scoring enables multi-signal confluence analysis
- Time-stamped events enable historical pattern analysis
- Immutable snapshots prevent accidental signal mutation during pipeline
- Pure detection facts - no causality yet (causality starts at StrategyPlanner decision)

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | SignalDetector (any subtype) | Emits Signal when pattern detected (FVG, MSS, breakout, etc.) |
| **Consumers** | StrategyPlanner | Decision input (combines Signal + Risk + Context) |
| | Journal | Persistence (historical pattern analysis) |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `signal_id` | str | Yes (auto) | Unique signal identifier (SIG_ prefix). Foundation for causality chain created by StrategyPlanner. Enables correlation: signal → strategy decision → execution → orders. |
| `timestamp` | datetime | Yes | Exact moment of pattern detection (UTC). Point-in-time model enforcement. Enables temporal analysis (signal clustering, timing patterns). |
| `symbol` | str | Yes | Trading pair (BASE_QUOTE format). Identifies which market signal applies to. Validated format prevents typos (BTC_USD not BTCUSD). |
| `direction` | Literal["long", "short"] | Yes | Intended trading direction. Discriminates entry vs exit signals. Type-safe (no "buy"/"sell" confusion). |
| `signal_type` | str | Yes | Pattern identifier (UPPER_SNAKE_CASE). Plugin-specific classification (FVG_ENTRY, MSS_REVERSAL, etc). Enables signal taxonomy analysis. Runtime flexibility for plugin-based detectors. |
| `confidence` | float \| None | No | Signal strength [0.0-1.0]. Optional because not all detectors quantify confidence. Enables weighted confluence analysis. Mirrors Risk.severity for balanced decision-making. |

**WHY frozen:**
- Signals are immutable facts ("pattern detected at T") - cannot retroactively change
- Prevents accidental mutation during multi-worker pipeline flow
- Safe concurrent access across workers
- Enables caching without defensive copying

**WHY NOT included:**
- ❌ `causality` - Signal is pre-causality (pure detection fact). CausalityChain only starts when StrategyPlanner makes decision (signal_id → strategy_directive_id). No causal chain exists yet at signal emission.
- ❌ `entry_price` - Planning concern, not detection concern (handled by EntryPlanner)
- ❌ `stop_loss` - Risk management concern, not signal concern (handled by ExitPlanner)
- ❌ `position_size` - Sizing concern, not detection concern (handled by SizePlanner)
- ❌ `trade_id` - Trade is post-hoc quant concept, not runtime entity (no trade exists yet at signal stage)
- ❌ `strategy_id` - Routing metadata, not signal data (handled by EventAdapter)
- ❌ `approved` - Decision concern, not detection concern (StrategyPlanner decides)

**Lifecycle:**
```
Created:    SignalDetector (pattern recognition worker)
Consumed:   StrategyPlanner (combines with Risk + Context for decision)
            → StrategyPlanner creates FIRST causal link (signal_id → strategy_directive_id)
Persisted:  StrategyJournal (signal as standalone detection fact)
Referenced: Via CausalityChain after StrategyPlanner decision
Never:      Modified after creation (frozen)
            Contains causality field (Signal is pre-causality)
```

**Design Decisions:**
- **Decision 1:** Literal["long", "short"] over enum
  - Rationale: Simple two-value discriminator, enum overhead unnecessary
  - Alternative rejected: Enum (overkill for binary choice)

- **Decision 2:** Optional confidence field
  - Rationale: Not all pattern detectors quantify confidence (some are binary: detected or not)
  - Alternative rejected: Required with default 1.0 (misleading - implies certainty when undefined)

- **Decision 3:** signal_type as Literal[str] (not enum)
  - Rationale: Runtime flexibility for plugin-based SignalDetectors. New detector = no core code change.
  - Alternative rejected: Enum in backend/core/enums.py (forces code change per new detector, defeats plugin architecture)

- **Decision 4:** UPPER_SNAKE_CASE signal_type convention
  - Rationale: Consistent naming prevents typos, enables taxonomy, grep-friendly
  - Alternative rejected: Free-form strings (inconsistent, error-prone)

- **Decision 5:** No entry/exit planning fields
  - Rationale: SRP - signal detects pattern, planners decide execution details
  - Alternative rejected: Rich signal with price/stops (violates SRP, tight coupling)

- **Decision 6:** Confidence mirrors Risk.severity scale
  - Rationale: Symmetric scoring (high signal confidence vs high risk severity) enables balanced decision algebra
  - Alternative rejected: Asymmetric scales (complex decision logic)

- **Decision 7:** No causality field (pre-causality)
  - Rationale: Signal is pure detection fact. CausalityChain starts at StrategyPlanner decision point (signal_id → strategy_directive_id first link)
  - Alternative rejected: Signal contains causality (premature - no decision made yet, violates causality semantics)

**Validation Strategy:**
- signal_id format: `SIG_YYYYMMDD_HHMMSS_hash` (military datetime)
- signal_type: UPPER_SNAKE_CASE, 3-25 chars, no reserved prefixes (SYSTEM_, INTERNAL_, _)
- symbol: BASE_QUOTE format (e.g., BTC_USD, not BTCUSD or BTC/USD)
- timestamp: UTC-enforced (timezone-aware)
- confidence: [0.0, 1.0] if provided
- Reserved prefix prevention: Avoids namespace pollution

**Signal Framework Context:**
```
ContextWorkers → Objective facts (EMA=50100, regime=BULLISH)
       ↓
SignalDetectors → Patterns (FVG detected at 50000, confidence 0.85)
       ↓
RiskMonitors → Threats (drawdown approaching, severity 0.7)
       ↓
StrategyPlanner → Decision (combine signals + risks → StrategyDirective)
```

Signal is pure detection output - no decisions, no planning, no execution details.

---

### Risk

**Purpose:** Threat detection output from RiskMonitors

**WHY this DTO exists:**
- RiskMonitors produce objective threat detection events (portfolio/position/systemic risks)
- Separates "threat detected" from "risk decision" (SRP - StrategyPlanner decides action)
- Severity scoring enables risk-weighted decision making
- Time-stamped events enable risk timeline analysis
- Immutable snapshots prevent accidental risk mutation during pipeline
- Pure detection facts - no causality yet (causality starts at StrategyPlanner decision)
- System-wide scope (no trade_id) - risks are portfolio-level or market-level concerns

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | RiskMonitor (any subtype) | Emits Risk when threat detected (drawdown, volatility spike, correlation break, etc.) |
| **Consumers** | StrategyPlanner | Decision input (combines Signal + Risk + Context) |
| | Journal | Persistence (historical risk analysis) |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `risk_id` | str | Yes (auto) | Unique risk identifier (RSK_ prefix). Foundation for causality chain created by StrategyPlanner. Enables correlation: risk → strategy decision → defensive action. |
| `timestamp` | datetime | Yes | Exact moment of threat detection (UTC). Point-in-time model enforcement. Enables temporal analysis (risk clustering, timing patterns). |
| `risk_type` | str | Yes | Threat identifier (UPPER_SNAKE_CASE). Plugin-specific classification (STOP_LOSS_HIT, DRAWDOWN_BREACH, etc). Enables risk taxonomy analysis. Runtime flexibility for plugin-based monitors. |
| `severity` | float | Yes | Risk severity [0.0-1.0]. Always required (all risks quantify threat level). Enables weighted decision analysis. Mirrors Signal.confidence for balanced decision-making. |
| `affected_symbol` | str \| None | No | Asset identifier (BASE_QUOTE format) or None for system-wide risks. Discriminates asset-specific vs portfolio-wide threats. None = exchange down, flash crash, etc. |

**WHY frozen:**
- Risks are immutable facts ("threat detected at T") - cannot retroactively change
- Prevents accidental mutation during multi-worker pipeline flow
- Safe concurrent access across workers
- Enables caching without defensive copying

**WHY NOT included:**
- ❌ `causality` - Risk is pre-causality (pure detection fact). CausalityChain only starts when StrategyPlanner makes decision (risk_id → strategy_directive_id). No causal chain exists yet at risk emission.
- ❌ `mitigation_plan` - Planning concern, not detection concern (handled by StrategyPlanner/ExitPlanner)
- ❌ `stop_loss` - Execution concern, not detection concern (handled by ExitPlanner)
- ❌ `trade_id` - Trade is post-hoc quant concept, not runtime entity (no trade exists yet at risk stage)
- ❌ `strategy_id` - Routing metadata, not risk data (handled by EventAdapter)
- ❌ `acknowledged` - Decision concern, not detection concern (StrategyPlanner decides)
- ❌ `action_taken` - Outcome tracking, not detection data (handled by execution layer)

**Lifecycle:**
```
Created:    RiskMonitor (threat recognition worker)
Consumed:   StrategyPlanner (combines with Signal + Context for decision)
            → StrategyPlanner creates FIRST causal link (risk_id → strategy_directive_id)
Persisted:  StrategyJournal (risk as standalone detection fact)
Referenced: Via CausalityChain after StrategyPlanner decision
Never:      Modified after creation (frozen)
            Contains causality field (Risk is pre-causality)
```

**Design Decisions:**
- **Decision 1:** risk_type as Literal[str] (not enum)
  - Rationale: Runtime flexibility for plugin-based RiskMonitors. New monitor = no core code change.
  - Alternative rejected: Enum in backend/core/enums.py (forces code change per new monitor, defeats plugin architecture)

- **Decision 2:** UPPER_SNAKE_CASE risk_type convention
  - Rationale: Consistent naming prevents typos, enables taxonomy, grep-friendly
  - Alternative rejected: Free-form strings (inconsistent, error-prone)

- **Decision 3:** Required severity field (unlike Signal.confidence which is optional)
  - Rationale: All risks quantify threat level. Risk without severity is meaningless (how bad is it?).
  - Alternative rejected: Optional severity (conceptually invalid - risk = threat + magnitude)

- **Decision 4:** Optional affected_symbol for system-wide risks
  - Rationale: Some risks are portfolio-wide (flash crash, exchange down). None = system-level threat.
  - Alternative rejected: Required symbol (cannot express system-wide risks)

- **Decision 5:** Severity mirrors Signal.confidence scale
  - Rationale: Symmetric scoring (high signal confidence vs high risk severity) enables balanced decision algebra
  - Alternative rejected: Asymmetric scales (complex decision logic, different scales for opportunity vs threat)

- **Decision 6:** No mitigation/action fields
  - Rationale: SRP - risk detects threat, planners decide response
  - Alternative rejected: Rich risk with mitigation plan (violates SRP, tight coupling)

- **Decision 7:** No causality field (pre-causality)
  - Rationale: Risk is pure detection fact. CausalityChain starts at StrategyPlanner decision point (risk_id → strategy_directive_id first link)
  - Alternative rejected: Risk contains causality (premature - no decision made yet, violates causality semantics)

**Validation Strategy:**
- risk_id format: `RSK_YYYYMMDD_HHMMSS_hash` (military datetime)
- risk_type: UPPER_SNAKE_CASE, 3-25 chars, no reserved prefixes (SYSTEM_, INTERNAL_, _)
- affected_symbol: BASE_QUOTE format (e.g., BTC_USD, not BTCUSD or BTC/USD) if provided
- timestamp: UTC-enforced (timezone-aware)
- severity: [0.0, 1.0] required
- Reserved prefix prevention: Avoids namespace pollution

**Risk Framework Context:**
```
ContextWorkers → Objective facts (volatility=0.45, correlation=0.92)
       ↓
SignalDetectors → Opportunities (FVG detected, confidence 0.85)
       ↓
RiskMonitors → Threats (drawdown approaching, severity 0.75)
       ↓
StrategyPlanner → Decision (combine signals + risks → StrategyDirective or reject)
```

Risk is pure threat detection output - no decisions, no mitigation plans, no execution details.

---

### StrategyDirective

**Purpose:** Strategy planning decision output from StrategyPlanner to role-based planners

**WHY this DTO exists:**
- StrategyPlanner produces high-level trade decisions (NEW_TRADE, MODIFY_EXISTING, CLOSE_EXISTING)
- Separates "strategic decision" from "tactical planning" (SRP - planners handle execution details)
- Contains 4 sub-directives (Entry, Size, Exit, Routing) as constraints/hints for specialized planners
- Scope field discriminates directive type (NEW_TRADE vs MODIFY_ORDER vs CLOSE_ORDER)
- Confidence scoring enables directive prioritization/rejection
- Causality tracking from signals/risks through directive to execution
- Bridge between Analysis DTOs (Signal/Risk) and Planning DTOs (EntryPlan/SizePlan/etc)
- Mutable (not frozen) for downstream enrichment (order_ids tracking after execution)

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | StrategyPlanner | Combines Signal + Risk + Context → trade decision with constraints |
| **Consumers** | EntryPlanner | Reads entry_directive for entry constraints |
| | ExitPlanner | Reads exit_directive for exit constraints |
| | SizePlanner | Reads size_directive for sizing constraints |
| | RoutingPlanner | Reads routing_directive for routing constraints |
| | Journal | Persistence (decision audit trail) |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `directive_id` | str | Yes (auto) | Unique directive identifier (STR_ prefix). Added to causality chain. Enables correlation: signal → directive → execution → orders. |
| `strategy_planner_id` | str | Yes | Identifies which StrategyPlanner produced directive. Enables planner-specific analysis (which planners perform best?). |
| `decision_timestamp` | datetime | Yes (auto) | Exact moment of decision (UTC). Point-in-time model. Enables temporal analysis (decision latency, clustering). |
| `causality` | CausalityChain | Yes | Complete ID chain from origin through signals/risks to this directive. Enables journal reconstruction: "Why this decision?". Foundation for causal analysis. |
| `scope` | DirectiveScope | Yes | Decision type: NEW_TRADE, MODIFY_ORDER, or CLOSE_ORDER. Discriminates directive semantics. Type-safe routing. |
| `confidence` | Decimal | Yes | Decision confidence [0.0-1.0]. Enables directive prioritization/rejection. Low confidence = skip or reduce size. |
| `target_order_ids` | list[str] | No | Existing order IDs for MODIFY_ORDER/CLOSE_ORDER. Empty for NEW_TRADE. Validated consistency with scope. |
| `entry_directive` | EntryDirective \| None | No | Entry constraints for EntryPlanner. Optional - planner uses defaults if missing. NEW_TRADE typically includes this. |
| `size_directive` | SizeDirective \| None | No | Sizing constraints for SizePlanner. Optional - planner uses defaults if missing. NEW_TRADE/MODIFY_ORDER typically includes this. |
| `exit_directive` | ExitDirective \| None | No | Exit constraints for ExitPlanner. Optional - planner uses defaults if missing. NEW_TRADE/MODIFY_ORDER typically includes this. |
| `routing_directive` | RoutingDirective \| None | No | Routing constraints for RoutingPlanner. Optional - planner uses defaults if missing. All scopes may include this. |

**WHY NOT frozen:**
- StrategyDirective is enriched post-execution (order_ids added after orders placed)
- Mutable enables downstream tracking without creating new DTO versions
- Causality chain extended as directive flows through pipeline

**WHY NOT included:**
- ❌ `entry_price` - EntryPlanner calculates this (tactical detail, not strategic constraint)
- ❌ `position_size` - SizePlanner calculates this (tactical detail, not strategic constraint)
- ❌ `stop_loss_price` - ExitPlanner calculates this (tactical detail, not strategic constraint)
- ❌ `order_type` - RoutingPlanner decides this (tactical detail, not strategic constraint)
- ❌ `approved` - Directive IS the approval (StrategyPlanner already decided to act)
- ❌ `rejected_reason` - If rejected, no directive emitted (rejection = absence of directive)

**Lifecycle:**
```
Created:    StrategyPlanner (combines Signal + Risk + Context → decision)
Extended:   causality.strategy_directive_id = directive_id by StrategyPlanner
Consumed:   Role-based planners (EntryPlanner, SizePlanner, ExitPlanner, RoutingPlanner)
            → Each planner reads its corresponding sub-directive
Enriched:   order_ids added after ExecutionHandler places orders
Persisted:  StrategyJournal (complete decision audit trail)
Referenced: Throughout execution pipeline via causality.strategy_directive_id
Modified:   Post-creation (order_ids tracking, not frozen)
```

**Design Decisions:**
- **Decision 1:** Scope enum (NEW_TRADE, MODIFY_ORDER, CLOSE_ORDER)
  - Rationale: Type-safe directive discrimination. Order-level semantics (not position-level). Compiler-enforced correctness.
  - Alternative rejected: String literals (error-prone, no type safety)
  - Alternative rejected: MODIFY_EXISTING/CLOSE_EXISTING (position-level naming, but operations are order-level)

- **Decision 2:** 4 optional sub-directives (not required)
  - Rationale: Flexibility - not all directives need all constraints. Planners have defaults. CLOSE_ORDER may only need routing_directive.
  - Alternative rejected: All sub-directives required (rigid, forces dummy values)

- **Decision 3:** Sub-directives as constraints (not tactical plans)
  - Rationale: SRP - StrategyPlanner sets strategic constraints, specialized planners calculate tactical details
  - Alternative rejected: Rich directive with exact prices/sizes (violates SRP, tight coupling, no planner specialization)

- **Decision 4:** Mutable (not frozen)
  - Rationale: Enriched downstream (order_ids tracking). Avoids creating new DTO versions.
  - Alternative rejected: Frozen + separate tracking DTO (complexity, indirection)

- **Decision 5:** target_order_ids validated with scope
  - Rationale: Prevents invalid states (NEW_TRADE with order IDs, MODIFY_ORDER without IDs)
  - Alternative rejected: No validation (runtime errors, invalid directives)

- **Decision 6:** Confidence required (unlike Signal/Risk optional confidence)
  - Rationale: StrategyPlanner ALWAYS quantifies decision confidence. Enables prioritization/rejection.
  - Alternative rejected: Optional confidence (conceptually invalid - no decision without confidence assessment)

- **Decision 7:** Causality chain continues from Signal/Risk
  - Rationale: StrategyPlanner extends causal chain (signal_id/risk_id → strategy_directive_id). Enables complete audit trail.
  - Alternative rejected: New causality chain (breaks causal continuity, no signal → directive link)

- **Decision 8:** RoutingDirective name (not ExecutionDirective)
  - Rationale: Avoids naming conflict with Execution layer DTO (execution/execution_directive.py). Clarifies purpose (routing constraints, not execution commands).
  - Alternative rejected: Keep ExecutionDirective name (confusing, two DTOs with same name in different layers)

**Validation Strategy:**
- directive_id format: `STR_YYYYMMDD_HHMMSS_hash` (military datetime)
- scope vs target_order_ids consistency:
  - NEW_TRADE: target_order_ids must be empty
  - MODIFY_ORDER/CLOSE_ORDER: target_order_ids must not be empty
- confidence: [0.0, 1.0] required
- decision_timestamp: UTC-enforced (timezone-aware)
- Sub-directives validated internally (decimal ranges, format checks)

**Scope Semantics:**

| Scope | target_order_ids | Typical Sub-directives | Purpose |
|-------|------------------|------------------------|---------|
| NEW_TRADE | Empty (new position) | entry, size, exit, routing | Open new position from signal |
| MODIFY_ORDER | Not empty (existing orders) | size, exit, routing | Adjust stops, scale position, change routing |
| CLOSE_ORDER | Not empty (existing orders) | routing (exit urgency) | Close position from exit signal or risk |

**Sub-Directive Semantics:**

| Sub-Directive | Planner | Constraint Examples |
|---------------|---------|---------------------|
| EntryDirective | EntryPlanner | symbol, direction, timing_preference, preferred_price_zone, max_slippage |
| SizeDirective | SizePlanner | aggressiveness, max_risk_amount, account_risk_pct |
| ExitDirective | ExitPlanner | profit_taking_preference, risk_reward_ratio, stop_loss_tolerance |
| RoutingDirective | RoutingPlanner | execution_urgency, iceberg_preference, max_total_slippage_pct |

**StrategyPlanner Types & Directive Patterns:**

| StrategyPlanner Type | Trigger | Scope | Typical Sub-directives |
|---------------------|---------|-------|------------------------|
| Entry Strategy | Signal + Context | NEW_TRADE | entry, size, exit, routing |
| Position Management | Tick + Position | MODIFY_EXISTING | size, exit (trailing stops) |
| Risk Control | Risk event | CLOSE_EXISTING | routing (urgency) |
| Scheduled Operations | Schedule | NEW_TRADE | entry, size (DCA patterns) |

**Directive Flow Example:**
```
Signal (FVG detected, confidence 0.85)
  → StrategyPlanner combines Signal + Risk + Context
    → Decision: NEW_TRADE with confidence 0.80
      → StrategyDirective created:
        - scope=NEW_TRADE
        - entry_directive: BUY BTCUSDT, timing=0.9
        - size_directive: aggressiveness=0.7, risk=2%
        - exit_directive: RR=3.0, stop=1.5%
        - routing_directive: urgency=0.8
          → EntryPlanner → EntryPlan (exact entry price)
          → SizePlanner → SizePlan (exact position size)
          → ExitPlanner → ExitPlan (exact stop/target prices)
          → RoutingPlanner → ExecutionPlan (order routing)
            → ExecutionDirective (aggregated execution instruction)
```

StrategyDirective is the strategic decision - planners handle tactical execution.

---

## Planning DTOs

**Status:** TODO

Planned coverage:
- EntryPlan
- SizePlan
- ExitPlan
- ExecutionPlan

---

## Execution DTOs

**Status:** TODO

Planned coverage:
- ExecutionDirective
- ExecutionDirectiveBatch
- ExecutionGroup

---

## Cross-Cutting DTOs

**Status:** TODO

Planned coverage:
- CausalityChain (ID-only tracking)
- DispositionEnvelope (worker routing)

---

## Appendix A: Rejected DTO Designs

### ExecutionRequest (Rejected - Terminologie Conflict)

**Proposed:** Aggregation DTO for ExecutionIntentPlanner input

**WHY rejected:**
- Term "trade_id" incorrectly implied runtime tracking unit
- "Trade" is post-hoc quant analysis concept, NOT runtime entity
- Tracking unit is actually StrategyDirective → order_ids (via CausalityChain)
- One StrategyDirective can result in 0, 1, or N orders (not 1:1 mapping)
- **Resolution pending:** Architectural clarity needed on directive → order relationship

**Lessons learned:**
- Avoid terms that blur runtime vs analysis boundaries
- Question every field name for conceptual accuracy
- "Trade" = quant concept (orders grouped post-hoc), NOT runtime ID

---

## Document Maintenance

**Update triggers:**
- New DTO created (add rationale before implementation)
- Field added/removed from existing DTO (update rationale)
- Design decision changes (document old vs new rationale)
- Architecture discussions resolve ambiguity (capture in "WHY NOT included")

**Responsible:** Development Team  
**Review frequency:** Per DTO change (living document)

