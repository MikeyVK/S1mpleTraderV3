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
10. **ExecutionCommand** - Aggregated execution instruction
11. **ExecutionCommandBatch** - Multi-command atomic coordination (combined in execution_command.py)
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
| | ExecutionPlanner | Reads execution_directive for execution constraints |
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
| `execution_directive` | ExecutionDirective \| None | No | Execution constraints for ExecutionPlanner. Optional - planner uses defaults if missing. All scopes may include this. |

**WHY NOT frozen:**
- StrategyDirective is enriched post-execution (order_ids added after orders placed)
- Mutable enables downstream tracking without creating new DTO versions
- Causality chain extended as directive flows through pipeline

**WHY NOT included:**
- ❌ `entry_price` - EntryPlanner calculates this (tactical detail, not strategic constraint)
- ❌ `position_size` - SizePlanner calculates this (tactical detail, not strategic constraint)
- ❌ `stop_loss_price` - ExitPlanner calculates this (tactical detail, not strategic constraint)
- ❌ `order_type` - ExecutionPlanner decides this (tactical detail, not strategic constraint)
- ❌ `approved` - Directive IS the approval (StrategyPlanner already decided to act)
- ❌ `rejected_reason` - If rejected, no directive emitted (rejection = absence of directive)

**Lifecycle:**
```
Created:    StrategyPlanner (combines Signal + Risk + Context → decision)
Extended:   causality.strategy_directive_id = directive_id by StrategyPlanner
Consumed:   Role-based planners (EntryPlanner, SizePlanner, ExitPlanner, ExecutionPlanner)
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
  - Rationale: Flexibility - not all directives need all constraints. Planners have defaults. CLOSE_ORDER may only need execution_directive.
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

- **Decision 8:** ExecutionDirective name (sub-directive in StrategyDirective)
  - Rationale: Clarifies purpose (execution constraints/hints for ExecutionPlanner). Sub-directive within StrategyDirective.
  - Note: Execution layer output uses ExecutionCommand (in execution_command.py)

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
| ExecutionDirective | ExecutionPlanner | execution_urgency, iceberg_preference, max_total_slippage_pct |

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
        - execution_directive: urgency=0.8
          → EntryPlanner → EntryPlan (exact entry price)
          → SizePlanner → SizePlan (exact position size)
          → ExitPlanner → ExitPlan (exact stop/target prices)
          → ExecutionPlanner → ExecutionPlan (execution trade-offs)
            → ExecutionCommand (aggregated execution instruction)
```

StrategyDirective is the strategic decision - planners handle tactical execution.

---

## Planning DTOs

Planning DTOs represent tactical execution plans created by specialized planners.
Each DTO translates strategic constraints from StrategyDirective into concrete execution parameters.

**Architectural Pattern:**
```
StrategyDirective (strategic constraints)
  → EntryPlanner → EntryPlan (WHAT/WHERE to enter)
  → SizePlanner → SizePlan (HOW MUCH)
  → ExitPlanner → ExitPlan (WHERE OUT)
  → ExecutionPlanner → ExecutionPlan (HOW/WHEN - trade-offs)
    → PlanningAggregator → ExecutionCommand (aggregated)
```

**Key Design Principles:**
- **Lean Specs:** Only execution-critical parameters (no metadata/timestamps)
- **No Causality:** Sub-planners receive StrategyDirective (has causality), plans inherit via aggregation
- **Immutable (mostly):** EntryPlan/SizePlan mutable for updates, ExitPlan/ExecutionPlan frozen
- **Universal:** Connector-agnostic (translation happens downstream)

---

### EntryPlan

**Purpose:** Entry execution specification (WHAT/WHERE to enter)

**WHY this DTO exists:**
- EntryPlanner translates entry constraints into concrete order specifications
- Separates "entry decision" from "entry execution" (SRP)
- Defines WHAT order type and WHERE (price levels)
- Pure execution parameters without timing/routing (those → ExecutionPlan)
- Lean spec - no metadata, timestamps, or causality (parent StrategyDirective has those)

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | EntryPlanner | Translates StrategyDirective.entry_directive → concrete order spec |
| **Consumers** | PlanningAggregator | Combines with Size/Exit/ExecutionPlan → ExecutionCommand |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `plan_id` | str | Yes (auto) | Unique entry plan identifier (ENT_ prefix). Enables tracking entry plan → order correlation. |
| `symbol` | str | Yes | Trading pair (BASE_QUOTE format). Identifies which market to enter. |
| `direction` | Literal["BUY", "SELL"] | Yes | Trade direction. Type-safe (BUY/SELL, not long/short). Explicit execution instruction. |
| `order_type` | Literal["MARKET", "LIMIT", "STOP_LIMIT"] | Yes | Order execution type. Determines how entry executes. MARKET=immediate, LIMIT=patient, STOP_LIMIT=breakout. |
| `limit_price` | Decimal \| None | No | Limit price for LIMIT/STOP_LIMIT orders. WHERE to enter. Optional (only for non-MARKET orders). |
| `stop_price` | Decimal \| None | No | Stop trigger price for STOP_LIMIT orders. Breakout entry trigger. Optional (only for STOP_LIMIT). |

**WHY NOT frozen:**
- EntryPlan may be updated pre-execution (price adjustments, order type changes)
- Mutable enables plan refinement without creating new versions
- Frozen after execution starts (immutability via external control)

**WHY NOT included:**
- ❌ `timing` - Execution timing → ExecutionPlan (execution_urgency)
- ❌ `slippage_tolerance` - Slippage → ExecutionPlan (max_slippage_pct)
- ❌ `position_size` - Sizing → SizePlan (separate concern)
- ❌ `created_at`/`planner_id` - Metadata → worker context (not execution params)
- ❌ `causality` - Parent StrategyDirective has causality, inherited via aggregation
- ❌ `valid_until` - Execution window → ExecutionPlan (max_execution_window_minutes)

**Lifecycle:**
```
Created:    EntryPlanner (from StrategyDirective.entry_directive constraints)
Validated:  PlanningAggregator (checks order_type vs price consistency)
Consumed:   ExecutionHandler (places order based on plan)
Aggregated: PlanningAggregator adds plan_id to ExecutionCommand
Never:      Modified after execution starts
```

**Design Decisions:**
- **Decision 1:** BUY/SELL over long/short
  - Rationale: Execution-layer terminology. Clear direction for order placement.
  - Alternative rejected: long/short (signal-layer terminology, confusing at execution)

- **Decision 2:** Three order types (MARKET, LIMIT, STOP_LIMIT)
  - Rationale: Covers 90% of entry strategies. Simple spec, complex strategies via combinations.
  - Alternative rejected: Rich order types (POST_ONLY, IOC, FOK) - connector-specific, defeats universal design

- **Decision 3:** Optional limit_price/stop_price
  - Rationale: MARKET orders don't need prices. Type-safe (can't provide limit_price for MARKET).
  - Alternative rejected: Required prices with sentinel values (misleading, null object pattern overkill)

- **Decision 4:** No causality field
  - Rationale: Sub-planners receive StrategyDirective (has causality). PlanningAggregator inherits causality when creating ExecutionCommand.
  - Alternative rejected: Duplicate causality in every plan (redundant, violates DRY)

- **Decision 5:** Mutable (not frozen)
  - Rationale: Pre-execution adjustments common (market conditions change). Frozen after execution starts.
  - Alternative rejected: Frozen (forces new plan versions for minor adjustments, complexity)

**Validation Strategy:**
- plan_id format: `ENT_YYYYMMDD_HHMMSS_hash` (military datetime)
- symbol: BASE_QUOTE format (e.g., BTC_USD)
- order_type consistency:
  - MARKET: limit_price/stop_price should be None
  - LIMIT: limit_price required, stop_price None
  - STOP_LIMIT: both limit_price and stop_price required
- direction: BUY or SELL only

---

### SizePlan

**Purpose:** Position sizing specification (HOW MUCH)

**WHY this DTO exists:**
- SizePlanner translates sizing constraints into absolute position size
- Separates "sizing decision" from "sizing execution" (SRP)
- Defines HOW MUCH to trade (absolute values)
- Lean spec - only execution parameters (no account percentages or constraints)
- Account risk % → SizePlanner input, absolute size → SizePlan output

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | SizePlanner | Translates StrategyDirective.size_directive + account constraints → absolute size |
| **Consumers** | PlanningAggregator | Combines with Entry/Exit/ExecutionPlan → ExecutionCommand |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `plan_id` | str | Yes (auto) | Unique sizing plan identifier (SIZ_ prefix). Enables tracking size plan → order correlation. |
| `position_size` | Decimal | Yes | Absolute position size in base asset (e.g., 0.5 BTC). WHAT quantity to trade. Must be > 0. |
| `position_value` | Decimal | Yes | Position value in quote asset (e.g., 50000 USDT). Total position cost. Enables risk calculations. Must be > 0. |
| `risk_amount` | Decimal | Yes | Absolute risk in quote asset (e.g., 1000 USDT). Stop loss distance × position size. Enables R-multiple tracking. Must be > 0. |
| `leverage` | Decimal | Yes | Leverage multiplier (1.0 = no leverage, 2.0 = 2x). Enables leveraged position sizing. Default 1.0. Must be >= 1.0. |

**WHY NOT frozen:**
- SizePlan may be adjusted pre-execution (risk recalculations, leverage changes)
- Mutable enables size refinement based on entry price updates
- Frozen after execution starts

**WHY NOT included:**
- ❌ `account_risk_pct` - Input constraint (e.g., 2%), not execution parameter. SizePlanner uses this to CALCULATE position_size.
- ❌ `max_position_value` - Planner constraint, not execution output. SizePlanner uses this as limit.
- ❌ `confidence_multiplier` - Worker logic (confidence-driven sizing), not DTO field.
- ❌ `causality` - Inherited from StrategyDirective via aggregation.
- ❌ `created_at`/`planner_id` - Metadata → worker context.

**Lifecycle:**
```
Created:    SizePlanner (from StrategyDirective.size_directive + account state)
Validated:  RiskManager (checks against account limits)
Consumed:   ExecutionHandler (places order with position_size)
Aggregated: PlanningAggregator adds plan_id to ExecutionCommand
Never:      Modified after execution starts
```

**Design Decisions:**
- **Decision 1:** Absolute values only (no percentages)
  - Rationale: DTOs = execution parameters. SizePlanner calculates absolutes from percentages. Clean separation.
  - Alternative rejected: Include account_risk_pct (blurs input vs output, violates SRP)

- **Decision 2:** position_value explicit field
  - Rationale: Enables risk calculations without knowing current price. Pre-calculated by SizePlanner.
  - Alternative rejected: Calculate on-the-fly (forces price lookup, coupling to market data)

- **Decision 3:** risk_amount explicit field
  - Rationale: Pre-calculates R-multiple for trade. Stop loss distance × position size. Enables simple risk tracking.
  - Alternative rejected: Calculate from exit plan (coupling between plans, violates independence)

- **Decision 4:** Mutable (not frozen)
  - Rationale: Size adjustments common (entry price changes → position_size recalculated). Frozen after execution.
  - Alternative rejected: Frozen (forces new plan for recalculations)

- **Decision 5:** Leverage field included
  - Rationale: Leveraged position sizing common in crypto/futures. Explicit field prevents implicit calculations.
  - Alternative rejected: Embed in position_size (ambiguous, requires external leverage tracking)

**Validation Strategy:**
- plan_id format: `SIZ_YYYYMMDD_HHMMSS_hash` (military datetime)
- position_size: Must be > 0
- position_value: Must be > 0
- risk_amount: Must be > 0
- leverage: Must be >= 1.0
- Consistency: position_value ≈ position_size × entry_price (validated at aggregation)

---

### ExitPlan

**Purpose:** Exit execution specification (WHERE OUT)

**WHY this DTO exists:**
- ExitPlanner translates exit constraints into price levels
- Separates "exit decision" from "exit execution" (SRP)
- Defines WHERE to exit (stop loss, take profit)
- Static price targets - NO dynamic logic (trailing stops → PositionMonitor)
- Lean spec - only price levels (no execution timing or metadata)

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | ExitPlanner | Translates StrategyDirective.exit_directive + risk/reward → price levels |
| **Consumers** | PlanningAggregator | Combines with Entry/Size/ExecutionPlan → ExecutionCommand |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `plan_id` | str | Yes (auto) | Unique exit plan identifier (EXT_ prefix). Enables tracking exit plan → order correlation. |
| `stop_loss_price` | Decimal | Yes | Stop loss price level. WHERE to cut losses. Required (risk protection). Must be > 0. |
| `take_profit_price` | Decimal \| None | No | Take profit price level. WHERE to take profits. Optional (let winners run strategy). Must be > 0 if provided. |

**WHY frozen:**
- ExitPlan is immutable after creation (static price targets)
- Dynamic exit logic creates new Signal → StrategyDirective → ExitPlan (not direct ExitPlan updates)
- Frozen enables safe concurrent access and audit trail

**WHY NOT included:**
- ❌ `trailing_stop_distance` - Dynamic logic → PositionMonitor emits Signal → new StrategyDirective → new ExitPlan
- ❌ `breakeven_trigger` - Dynamic logic → PositionMonitor (adjusts stop_loss_price)
- ❌ `exit_strategy` - Execution timing → ExecutionPlan (how/when to exit)
- ❌ `causality` - Inherited from StrategyDirective via aggregation
- ❌ `created_at`/`planner_id` - Metadata → worker context
- ❌ `risk_reward_ratio` - Input constraint (ExitPlanner calculates prices FROM ratio), not output

**Lifecycle:**
```
Created:    ExitPlanner (from StrategyDirective.exit_directive + entry price + risk tolerance)
Validated:  PlanningAggregator (checks stop_loss_price vs entry_price consistency)
Aggregated: PlanningAggregator adds plan_id to ExecutionCommand
Consumed:   ExecutionCommand → ExecutionHandler (places stop loss/take profit orders)
Finalized:  ExitPlan "dies" when exit orders are created (immutable, no updates)
Never:      Modified after creation (frozen - dynamic logic creates new StrategyDirective)
```

**Design Decisions:**
- **Decision 1:** stop_loss_price required
  - Rationale: Risk protection mandatory. No position without stop loss.
  - Alternative rejected: Optional stop_loss (violates risk management principles)

- **Decision 2:** take_profit_price optional
  - Rationale: "Let winners run" strategy valid. Not all exits target fixed profit.
  - Alternative rejected: Required take_profit (forces artificial targets)

- **Decision 3:** No trailing stop fields
  - Rationale: Trailing stops = dynamic behavior (PositionMonitor emits new Signal → new StrategyDirective → new ExitPlan). ExitPlan = static snapshot.
  - Alternative rejected: Include trailing_distance (blurs static vs dynamic, violates SRP)

- **Decision 4:** Frozen (immutable)
  - Rationale: Exit levels are facts at plan creation. Dynamic adjustments = new plan (audit trail).
  - Alternative rejected: Mutable (loses audit trail, concurrent access issues)

- **Decision 5:** Price-only (no percentage offsets)
  - Rationale: Absolute prices clear and unambiguous. ExitPlanner calculates from percentages.
  - Alternative rejected: Store percentage offset (requires entry price lookup, coupling)

**Validation Strategy:**
- plan_id format: `EXT_YYYYMMDD_HHMMSS_hash` (military datetime)
- stop_loss_price: Must be > 0
- take_profit_price: Must be > 0 if provided
- Consistency (validated at aggregation):
  - Long: stop_loss_price < entry_price < take_profit_price
  - Short: take_profit_price < entry_price < stop_loss_price

---

### ExecutionPlan

**Purpose:** Execution trade-offs specification (HOW/WHEN - universal)

**WHY this DTO exists:**
- ExecutionPlanner translates execution constraints into universal trade-offs
- Connector-agnostic execution preferences (not CEX/DEX/Backtest-specific)
- Expresses WHAT strategy wants (urgency, visibility, slippage) not HOW to execute
- Translation layer converts ExecutionPlan → connector-specific execution specs
- Replaces old RoutingPlan with universal trade-off model

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | ExecutionPlanner | Translates StrategyDirective.execution_directive → universal trade-offs |
| **Consumers** | PlanningAggregator | Combines with Entry/Size/ExitPlan → ExecutionCommand |
| | ExecutionTranslator | Converts ExecutionPlan trade-offs → connector-specific params (CEX/DEX/Backtest) |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `plan_id` | str | Yes (auto) | Unique execution plan identifier (EXP_ prefix). Enables tracking execution plan → execution correlation. |
| `action` | ExecutionAction | Yes | Action type: EXECUTE_TRADE, CANCEL_ORDER, MODIFY_ORDER, CANCEL_GROUP. Discriminates execution vs order management. Default EXECUTE_TRADE. |
| `execution_urgency` | Decimal | Yes | Patience vs speed (0.0=patient, 1.0=urgent). Universal trade-off. Translator maps to connector-specific (LIMIT vs MARKET, TWAP duration, etc). |
| `visibility_preference` | Decimal | Yes | Stealth vs transparency (0.0=stealth, 1.0=visible). Universal trade-off. Translator maps to iceberg, dark pools, private mempool, etc. |
| `max_slippage_pct` | Decimal | Yes | Hard price limit (0.0-1.0 = 0-100%). Constraint (MUST respect). Execution fails if exceeded. |
| `must_complete_immediately` | bool | No | Force immediate execution. Constraint (MUST respect). Overrides execution_urgency. Default False. |
| `max_execution_window_minutes` | int \| None | No | Maximum time window for completion. Constraint (MUST respect). Enables TWAP duration limits. |
| `preferred_execution_style` | str \| None | No | Hint for execution style (e.g., "TWAP", "VWAP", "ICEBERG"). Hint (MAY interpret). Translator decides if feasible. |
| `chunk_count_hint` | int \| None | No | Hint for number of execution chunks. Hint (MAY interpret). TWAP chunking suggestion. |
| `chunk_distribution` | str \| None | No | Hint for chunk distribution (e.g., "UNIFORM", "WEIGHTED"). Hint (MAY interpret). Influences TWAP strategy. |
| `min_fill_ratio` | Decimal \| None | No | Minimum fill ratio to accept (0.0-1.0). Constraint (MUST respect). Partial fill handling. |

**WHY frozen:**
- ExecutionPlan is immutable after creation (trade-off decisions frozen)
- Audit trail integrity - execution decisions preserved
- Safe concurrent access for execution translation

**WHY NOT included:**
- ❌ `time_in_force` - Connector-specific (GTC, IOC, FOK). Translator maps from urgency/window.
- ❌ `iceberg_preference` - Connector-specific. Translator maps from visibility_preference.
- ❌ `twap_duration`/`twap_intervals` - Connector/platform-specific. Translator calculates from execution_urgency + max_execution_window.
- ❌ `routing_venue` - Platform decision (CEX/DEX selection). Not strategy concern.
- ❌ `causality` - Inherited from StrategyDirective via aggregation.
- ❌ `created_at`/`planner_id` - Metadata → worker context.

**Lifecycle:**
```
Created:    ExecutionPlanner (from StrategyDirective.execution_directive)
Validated:  PlanningAggregator (checks trade-off consistency)
Translated: ExecutionTranslator (universal → connector-specific)
Consumed:   ExecutionHandler (executes based on translated spec)
Aggregated: PlanningAggregator adds plan_id to ExecutionCommand
Never:      Modified after creation (frozen)
```

**Design Decisions:**
- **Decision 1:** Universal trade-offs (not connector-specific)
  - Rationale: Strategy layer connector-agnostic. Translator handles CEX/DEX/Backtest specifics.
  - Alternative rejected: CEX-specific params (time_in_force, iceberg) - tight coupling, no DEX/backtest support

- **Decision 2:** Decimal 0.0-1.0 range for trade-offs
  - Rationale: Normalized scale. Clear semantics (0=min, 1=max). Easy interpolation.
  - Alternative rejected: Enum levels (LOW/MEDIUM/HIGH) - loses granularity, hard to interpolate

- **Decision 3:** Constraints (MUST) vs Hints (MAY)
  - Rationale: Clear contract. Constraints fail execution if violated. Hints guide but don't force.
  - Alternative rejected: All fields as hints (unclear which are hard limits)

- **Decision 4:** action field for order management
  - Rationale: ExecutionPlan not just for trades. Cancel/modify operations also need execution specs.
  - Alternative rejected: Separate CancelPlan/ModifyPlan DTOs (proliferation, shared fields)

- **Decision 5:** Frozen (immutable)
  - Rationale: Execution decisions frozen at plan creation. New plan for changes. Audit trail.
  - Alternative rejected: Mutable (loses decision audit trail)

- **Decision 6:** preferred_execution_style as hint
  - Rationale: Strategy suggests, platform decides feasibility (TWAP may not be available).
  - Alternative rejected: Required style (forces platform to support all styles)

- **Decision 7:** WHY "ExecutionPlan" (not "RoutingPlan")?
  - Rationale: Plans **execution trade-offs** (urgency, visibility, slippage). ExecutionPlanner determines execution logic → outputs **ExecutionPlan** (HOW/WHEN to execute). Execution **planning** (strategy layer) vs execution **doing** (execution layer). Action field = ExecutionAction (planned actions: EXECUTE_TRADE, CANCEL_ORDER).
  - Alternative rejected: RoutingPlan (confuses routing logic with execution plan output)

**Validation Strategy:**
- plan_id format: `EXP_YYYYMMDD_HHMMSS_xxxxx` (military datetime, 5-char hash)
- execution_urgency: 0.0-1.0 range, 2 decimal places
- visibility_preference: 0.0-1.0 range, 2 decimal places
- max_slippage_pct: 0.0-1.0 range (0-100%), 4 decimal places
- Trade-off consistency:
  - urgency=1.0 + visibility=1.0 + must_complete_immediately → likely MARKET order
  - urgency=0.2 + max_execution_window=30 → likely TWAP
- Action-specific validation:
  - CANCEL/MODIFY: may have reduced field requirements

**Universal → Connector Translation Examples:**

| Universal Trade-Offs | CEX Translation | DEX Translation | Backtest Translation |
|---------------------|-----------------|-----------------|----------------------|
| urgency=0.9, visibility=0.7, slippage=0.01 | MARKET order, visible | MEV-protected swap, public mempool | Instant fill, realistic slippage |
| urgency=0.2, visibility=0.1, window=30min | TWAP 30min, 6 chunks, LIMIT orders | Private mempool, 5min intervals | Simulated TWAP, spread fills |
| urgency=0.5, visibility=0.3, style="ICEBERG" | ICEBERG order, 20% visible | Split orders, randomized timing | Single fill, average price |

---

## Execution DTOs

Execution DTOs represent final executable instructions and execution tracking.
These DTOs bridge the Strategy layer (planning) and Execution layer (doing).

**Architectural Pattern:**
```
PlanningAggregator
  → ExecutionCommand (single executable instruction)
    → ExecutionCommandBatch (atomic multi-command coordination)
      → ExecutionGroup (multi-order execution tracking)
```

**Key Design Principles:**
- **Clean Layer Separation:** No strategy metadata (causality only for traceability)
- **Flexible Composition:** All plans optional (supports partial updates)
- **Atomic Coordination:** Batch enables transaction-like execution
- **Mutable Tracking:** ExecutionGroup evolves during execution lifecycle

---

### ExecutionCommand

**Purpose:** Final aggregated execution instruction (single trade setup)

**WHY this DTO exists:**
- PlanningAggregator combines 4 plans → single executable instruction
- Clean separation: Strategy planning → Execution doing
- Supports partial updates (NEW_TRADE vs MODIFY_ORDER vs ADD_TO_POSITION)
- Complete causality chain for full traceability
- All plans optional enables flexibility (trailing stop = only exit_plan)

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | PlanningAggregator | Aggregates Entry/Size/Exit/ExecutionPlan → ExecutionCommand |
| **Consumers** | ExecutionCommandBatch | Groups multiple commands for atomic execution |
| | ExecutionTranslator | Translates ExecutionPlan → connector-specific params |
| | ExecutionHandler | Executes single command (places orders) |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `command_id` | str | Yes (auto) | Unique execution command identifier (EXC_ prefix). Enables tracking command → orders. |
| `causality` | CausalityChain | Yes | Complete ID chain from origin through strategy decision. Full traceability for auditing and debugging. |
| `entry_plan` | EntryPlan \| None | No | WHERE IN specification. Optional (only for new trades or scaling in). |
| `size_plan` | SizePlan \| None | No | HOW MUCH specification. Optional (only for new trades or scaling). |
| `exit_plan` | ExitPlan \| None | No | WHERE OUT specification. Optional (only for new trades or exit adjustments like trailing stops). |
| `execution_plan` | ExecutionPlan \| None | No | HOW/WHEN specification. Optional (execution trade-offs, may use defaults). |

**WHY frozen:**
- ExecutionCommand is immutable after creation (instruction snapshot)
- Execution layer consumes immutable facts
- Frozen enables safe concurrent access and audit trail
- Changes require new command (not mutations)

**WHY NOT included:**
- ❌ `strategy_id` - Not execution concern (causality provides traceability without strategy metadata)
- ❌ `planner_metadata` - Strategy layer metadata, not execution parameters
- ❌ `priority` - ExecutionCommandBatch handles priority via ordering
- ❌ `created_at` - Auto-captured from command_id timestamp (military datetime)
- ❌ `status` - Execution state tracking → separate tracking system (not DTO field)

**Lifecycle:**
```
Created:    PlanningAggregator (aggregates 4 plans + causality)
Validated:  At least 1 plan required (cannot be empty command)
Nested in:  Always nested in ExecutionCommandBatch
Consumed:   ExecutionHandler translates → connector orders
Grouped:    ExecutionCommandBatch coordinates atomic execution
Tracked:    ExecutionGroup tracks multi-order execution progress
Modified:   Never modified after creation (frozen - new command for changes)
```

**Design Decisions:**
- **Decision 1:** All plans optional
  - Rationale: Enables partial updates (trailing stop = only exit_plan, scale in = entry+size only). Flexibility without proliferation.
  - Alternative rejected: Required plans (forces full trade spec even for adjustments)

- **Decision 2:** At least 1 plan required
  - Rationale: Empty command is meaningless (validation prevents accidents).
  - Alternative rejected: Allow empty (dangerous - silent no-ops)

- **Decision 3:** No strategy metadata
  - Rationale: Clean layer separation. Execution layer doesn't need strategy_id, confidence, etc. Causality provides traceability.
  - Alternative rejected: Include strategy_id (couples layers, violates separation)

- **Decision 4:** Frozen (immutable)
  - Rationale: Execution instructions are facts at creation time. Mutations violate audit trail. New command for changes.
  - Alternative rejected: Mutable (loses audit trail, concurrent access issues)

- **Decision 5:** CausalityChain required
  - Rationale: Full traceability mandatory (debugging, auditing, regulatory). Every execution traces back to origin.
  - Alternative rejected: Optional causality (loses traceability, regulatory risk)

**Validation Strategy:**
- command_id format: `EXC_YYYYMMDD_HHMMSS_hash` (military datetime)
- At least 1 plan: entry_plan OR size_plan OR exit_plan OR execution_plan
- causality: Complete chain validation (all required IDs present)
- Plan consistency: Validated by ExecutionHandler (entry+size for new trade, etc)

**Use Cases:**

| Use Case | Plans Present | Description |
|----------|---------------|-------------|
| NEW_TRADE | Entry + Size + Exit + Execution | Complete new trade setup (all 4 plans) |
| MODIFY_ORDER (trailing stop) | Exit only | Trailing stop adjustment (only exit_plan) |
| MODIFY_ORDER (urgency change) | Execution only | Change execution urgency (only execution_plan) |
| MODIFY_ORDER (size adjust) | Size + Execution | Adjust position size with urgency |
| ADD_TO_POSITION | Entry + Size | Scale in (add to existing position) |
| CLOSE_POSITION | Exit + Execution | Close position with urgency (exit_plan + execution urgency) |

---

### ExecutionCommandBatch

**Purpose:** Atomic multi-command execution coordination

**WHY this DTO exists:**
- PlanningAggregator ALWAYS produces ExecutionCommandBatch (even for single command)
- Coordinates execution of 1-N ExecutionCommands as single unit
- Enables atomic transactions (all succeed or all rollback)
- Supports execution modes (SEQUENTIAL, PARALLEL, ATOMIC)
- Batch-level timeout and rollback control

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | PlanningAggregator | ONLY producer - bundles 1-N commands + sets execution_mode/timeout/etc |
| **Consumers** | ExecutionHandler | Executes batch according to execution_mode |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `batch_id` | str | Yes | Unique batch identifier (BAT_ prefix). PlanningAggregator generates. Enables tracking batch → commands → orders. |
| `commands` | List[ExecutionCommand] | Yes | ExecutionCommands to execute (min 1). PlanningAggregator bundles 1-N commands. Atomic coordination unit. |
| `execution_mode` | ExecutionMode | Yes | Execution mode: SEQUENTIAL (1-by-1), PARALLEL (all at once), ATOMIC (transaction). PlanningAggregator sets based on StrategyDirective scope/count. |
| `created_at` | datetime | Yes | Batch creation timestamp (UTC). PlanningAggregator sets. Audit trail and timeout calculation. |
| `rollback_on_failure` | bool | Yes | Rollback all on any failure. PlanningAggregator sets (default True, MUST True for ATOMIC). MUST be True for ATOMIC mode. |
| `timeout_seconds` | int \| None | No | Max execution time (None = no timeout). PlanningAggregator sets (default 30s). Prevents hanging batch execution. |
| `metadata` | Dict \| None | No | Batch context (strategy_directive_id, trade_count). PlanningAggregator sets for debugging/analysis. Optional. |

**WHY frozen:**
- ExecutionCommandBatch is immutable after creation (coordination contract frozen)
- Execution mode cannot change mid-execution (violates contract)
- Frozen enables safe concurrent access
- Changes require new batch (not mutations)

**WHY NOT included:**
- ❌ `status` - Runtime state tracking → separate tracking system (not DTO field)
- ❌ `progress` - Execution progress → tracking system (not coordination spec)
- ❌ `results` - Execution outcomes → tracking system (not input spec)
- ❌ `priority` - Command ordering within batch determines priority
- ❌ `strategy_id` - In metadata if needed for debugging (not execution parameter)

**Lifecycle:**
```
Created:    PlanningAggregator (when all plans per trade complete)
            - Sets batch_id, execution_mode, created_at, rollback_on_failure, timeout_seconds
            - Bundles 1-N ExecutionCommands
            - Adds metadata (strategy_directive_id, trade_count)
Validated:  Min 1 command, unique command IDs, ATOMIC → rollback_on_failure=True
Consumed:   ExecutionHandler executes commands per execution_mode
Coordinated: ExecutionHandler manages execution coordination (SEQUENTIAL/PARALLEL/ATOMIC)
Finalized:  Batch completes (all succeed) or rolls back (any fail + rollback_on_failure)
Never:      Modified after creation (frozen)
```

**Design Decisions:**
- **Decision 1:** Three execution modes
  - Rationale: Covers 90% use cases. SEQUENTIAL=simple, PARALLEL=fast, ATOMIC=safe. Clear semantics.
  - Alternative rejected: Single mode (loses flexibility), 10+ modes (complexity overkill)

- **Decision 2:** rollback_on_failure required for ATOMIC
  - Rationale: ATOMIC without rollback is misleading (violates transaction semantics).
  - Alternative rejected: Optional rollback for ATOMIC (confusing, violates expectations)

- **Decision 3:** Min 1 directive
  - Rationale: Empty batch is meaningless (validation prevents accidents).
  - Alternative rejected: Allow empty (dangerous - silent no-ops)

- **Decision 4:** Frozen (immutable)
  - Rationale: Batch coordination contract frozen at creation. Changes require new batch.
  - Alternative rejected: Mutable (loses coordination integrity, concurrent issues)

- **Decision 5:** Unique directive IDs
  - Rationale: Duplicate directives dangerous (double execution). Validation prevents accidents.
  - Alternative rejected: Allow duplicates (risk of unintended double orders)

- **Decision 6:** PlanningAggregator fills ALL fields
  - Rationale: Clear responsibility. PlanningAggregator knows StrategyDirective scope → determines execution_mode. Sets sensible defaults (timeout=30s, rollback=True).
  - Alternative rejected: ExecutionHandler decides (duplicates logic, violates SRP)

- **Decision 7:** metadata field
  - Rationale: Debugging aid (strategy_directive_id, trade_count). Minimal (not full strategy context). Optional.
  - Alternative rejected: No metadata (loses debugging context), Rich metadata (couples layers)

**Validation Strategy:**
- batch_id format: `BAT_YYYYMMDD_HHMMSS_xxxxx` (military datetime)
- commands: Min 1, all command_ids unique
- execution_mode: ATOMIC → rollback_on_failure must be True
- timeout_seconds: Must be positive if provided
- Command uniqueness: No duplicate command_ids within batch

**Execution Mode Semantics:**

| Mode | Behavior | Use Case | Rollback |
|------|----------|----------|----------|
| SEQUENTIAL | Execute 1-by-1, stop on first failure | Ordered operations (hedge → main) | Optional |
| PARALLEL | Execute all simultaneously | Independent operations (multiple symbols) | Optional |
| ATOMIC | All succeed or all rollback | Critical coordination (entry+exits together) | Required |

---

### ExecutionGroup

**Purpose:** Multi-order execution tracking for advanced strategies

**WHY this DTO exists:**
- Tracks lifecycle of multi-order strategies (TWAP, ICEBERG, DCA, LAYERED, POV)
- Groups orders spawned from single ExecutionCommand
- Mutable status tracking (PENDING → ACTIVE → COMPLETED/CANCELLED/FAILED/PARTIAL)
- Progress monitoring (filled_quantity vs target_quantity)
- Enables atomic group operations (cancel all TWAP chunks, modify entire group)
- Causal traceability (parent_command_id → order_ids chain)

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | ExecutionHandler | Creates group when spawning multi-order strategy (TWAP, ICEBERG, etc) |
| **Consumers** | ExecutionHandler | Updates group as orders spawn, fill, complete |
| | (Future) PositionTracker | Aggregates fills across group orders |
| | (Future) RiskMonitor | Monitors group exposure and cancels if risk threshold breached |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `group_id` | str | Yes | Unique execution group identifier (EXG_ prefix). ExecutionHandler generates. Enables tracking group → orders. |
| `parent_command_id` | str | Yes | ExecutionCommand that spawned this group. Links group to originating command. Causal traceability. |
| `execution_strategy` | ExecutionStrategyType | Yes | Strategy type: SINGLE, TWAP, VWAP, ICEBERG, DCA, LAYERED, POV. Determines coordination logic. ExecutionHandler sets based on ExecutionPlan hints. |
| `order_ids` | List[str] | Yes | Connector order IDs in this group (unique values). ExecutionHandler appends as orders spawn. Tracks all spawned orders. Empty initially. |
| `status` | GroupStatus | Yes | Lifecycle status: PENDING, ACTIVE, COMPLETED, CANCELLED, FAILED, PARTIAL. ExecutionHandler updates as execution progresses. |
| `created_at` | datetime | Yes | Group creation timestamp (UTC). ExecutionHandler sets. Audit trail. |
| `updated_at` | datetime | Yes | Last update timestamp (UTC). ExecutionHandler refreshes on each update. Tracks freshness. |
| `target_quantity` | Decimal \| None | No | Planned total quantity. From SizePlan. Enables progress calculation (filled/target ratio). Optional (not all strategies have fixed target). |
| `filled_quantity` | Decimal \| None | No | Actual filled quantity so far. ExecutionHandler aggregates from fill events. Tracks execution progress. |
| `cancelled_at` | datetime \| None | No | Cancellation timestamp (mutually exclusive with completed_at). ExecutionHandler sets on cancel. Audit trail. |
| `completed_at` | datetime \| None | No | Completion timestamp (mutually exclusive with cancelled_at). ExecutionHandler sets on completion. Audit trail. |
| `metadata` | Dict \| None | No | Strategy-specific parameters (e.g., TWAP: chunk_size, interval_seconds, chunks_total). ExecutionHandler extracts from ExecutionPlan hints. Debugging and analysis. |

**WHY NOT frozen:**
- ExecutionGroup is mutable during execution lifecycle (tracking entity, not specification)
- status evolves: PENDING → ACTIVE → COMPLETED/CANCELLED/FAILED/PARTIAL
- order_ids list grows as ExecutionHandler spawns orders
- filled_quantity increases as orders fill
- updated_at refreshed on each state change
- Timestamps set when transitions occur (cancelled_at, completed_at)

**WHY NOT included:**
- ❌ `individual_order_status` - Order-level tracking → separate Order DTO or connector state
- ❌ `slippage` - Analytics concern (computed post-execution from fills)
- ❌ `average_fill_price` - Analytics concern (computed from fills)
- ❌ `remaining_quantity` - Computed field (target_quantity - filled_quantity)
- ❌ `strategy_id` - Not execution concern (parent_command_id provides traceability)

**Lifecycle:**
```
Created:    ExecutionHandler (when spawning multi-order strategy)
            - Status: PENDING, order_ids=[], created_at/updated_at set
            - Based on ExecutionPlan hints (preferred_execution_style, chunk_count_hint)
Spawning:   ExecutionHandler appends order_ids as orders created
            - Status: PENDING → ACTIVE (first order placed)
            - updated_at refreshed
Progress:   ExecutionHandler updates filled_quantity as fill events arrive
            - updated_at refreshed on each update
Finalized:  ExecutionHandler transitions status
            - ACTIVE → COMPLETED (all orders filled)
            - ACTIVE → CANCELLED (group cancelled, cancelled_at set)
            - ACTIVE → FAILED (execution error)
            - ACTIVE → PARTIAL (some filled, execution stopped)
```

**Design Decisions:**
- **Decision 1:** Mutable (not frozen)
  - Rationale: Tracking entity (not specification). Status, order_ids, filled_quantity evolve. Real-time updates essential.
  - Alternative rejected: Frozen (requires new group for every update, impractical for tracking)

- **Decision 2:** Seven execution strategy types
  - Rationale: Covers common advanced strategies. SINGLE for simple cases. Enables strategy-specific coordination.
  - Alternative rejected: Generic "MULTI_ORDER" (loses semantic information for debugging/analysis)

- **Decision 3:** Six group statuses
  - Rationale: Clear lifecycle semantics. PARTIAL status critical (some filled, execution stopped). FAILED vs CANCELLED distinction important.
  - Alternative rejected: Binary complete/incomplete (loses nuance for debugging)

- **Decision 4:** cancelled_at XOR completed_at
  - Rationale: Mutually exclusive final states. Validation prevents impossible states.
  - Alternative rejected: Allow both (confusing, violates state machine)

- **Decision 5:** Unique order_ids
  - Rationale: Duplicate order IDs indicate bug (double spawn). Validation prevents tracking corruption.
  - Alternative rejected: Allow duplicates (risk of incorrect fill aggregation)

- **Decision 6:** filled_quantity <= target_quantity
  - Rationale: Cannot fill more than target (validation prevents data corruption). Over-fills indicate bug.
  - Alternative rejected: No validation (allows impossible states, silent bugs)

- **Decision 7:** ExecutionHandler owns lifecycle
  - Rationale: Single owner prevents race conditions. ExecutionHandler creates, updates, finalizes groups.
  - Alternative rejected: Multiple writers (race conditions, state corruption)

**Validation Strategy:**
- group_id format: `EXG_YYYYMMDD_HHMMSS_xxxxx` (military datetime)
- parent_command_id format: `EXC_YYYYMMDD_HHMMSS_xxxxx`
- order_ids: All unique (no duplicates)
- target_quantity: Must be positive if provided
- filled_quantity: Must be <= target_quantity (if both present)
- cancelled_at XOR completed_at: Mutually exclusive (validation enforced)

**Execution Strategy Types:**

| Strategy | Description | Typical Order Count | Use Case |
|----------|-------------|---------------------|----------|
| SINGLE | Single order (no grouping) | 1 | Simple execution (market/limit order) |
| TWAP | Time-Weighted Average Price | 5-20 | Spread execution over time, minimize market impact |
| VWAP | Volume-Weighted Average Price | Variable | Match market volume profile |
| ICEBERG | Iceberg orders (visible/hidden) | 2-10 | Hide large order intent, prevent front-running |
| DCA | Dollar-Cost Averaging | 10-50 | Systematic accumulation, reduce timing risk |
| LAYERED | Layered limit orders | 3-10 | Capture range-bound moves, multiple entry points |
| POV | Percentage of Volume | Variable | Maintain fixed % of market volume, minimize impact |

**Group Status Transitions:**

```
PENDING ────→ ACTIVE ────→ COMPLETED (all orders filled)
                │
                ├──────→ CANCELLED (emergency cancel / user request)
                │
                ├──────→ FAILED (execution error / connector issue)
                │
                └──────→ PARTIAL (some filled, stopped early)

State Machine Rules:
- PENDING: No orders placed yet (order_ids=[])
- ACTIVE: At least 1 order placed (order_ids not empty)
- COMPLETED: filled_quantity == target_quantity (all orders filled)
- CANCELLED: User/system requested cancellation (cancelled_at set)
- FAILED: Execution error prevented completion
- PARTIAL: filled_quantity < target_quantity, execution stopped

Transition Guards:
- PENDING → ACTIVE: First order placed
- ACTIVE → COMPLETED: All orders filled
- ANY → CANCELLED: Cancel request accepted (atomic group operation)
```

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

