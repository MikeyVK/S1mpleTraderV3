# docs/architecture/DTO_PIPELINE.md
# DTO Pipeline - S1mpleTraderV3

**Status:** PRELIMINARY
**Version:** 1.0
**Last Updated:** 2025-11-29

---

## Purpose

This document defines the **analysis and strategic DTOs** that flow through the detection-to-decision pipeline.

**Target audience:** Developers implementing Detectors or StrategyPlanner.

## Scope

**In Scope:**
- Signal - Trading opportunity detection output
- Risk - Threat/risk detection output
- StrategyDirective - Strategy planning decision output
- TradePlan - Execution Anchor & State Container

**Out of Scope:**
- DTO taxonomy overview → See [DTO_ARCHITECTURE.md](DTO_ARCHITECTURE.md)
- Core DTOs → See [DTO_CORE.md](DTO_CORE.md)
- Execution DTOs → See [DTO_EXECUTION.md](DTO_EXECUTION.md)

---

## 1. Analysis DTOs

### Signal

**Purpose:** Trading opportunity detection output from SignalDetectors

**WHY this DTO exists:**
- SignalDetectors produce objective pattern detection events (entry/exit opportunities)
- Separates "pattern detected" from "trade decision" (SRP - StrategyPlanner decides)
- Confidence scoring enables multi-signal confluence analysis
- Immutable snapshots prevent accidental signal mutation during pipeline
- Pure detection facts - no causality yet (causality starts at StrategyPlanner decision)

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | SignalDetector (any subtype) | Emits Signal when pattern detected |
| **Consumers** | StrategyPlanner | Decision input (combines Signal + Risk + Context) |
| | Journal | Persistence (historical pattern analysis) |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `signal_id` | str | Yes (auto) | Unique identifier (SIG_ prefix). Foundation for causality chain. |
| `timestamp` | datetime | Yes | Exact moment of pattern detection (UTC). Point-in-time model. |
| `symbol` | str | Yes | Trading pair (BASE_QUOTE format). Which market signal applies to. |
| `direction` | Literal["long", "short"] | Yes | Intended trading direction. Type-safe. |
| `signal_type` | str | Yes | Pattern identifier (UPPER_SNAKE_CASE). Plugin-specific. |
| `confidence` | float \| None | No | Signal strength [0.0-1.0]. Optional (not all detectors quantify). |

**WHY frozen:** Signals are immutable facts ("pattern detected at T").

**WHY NOT included:**
- ❌ `causality` - Signal is pre-causality (pure detection fact)
- ❌ `entry_price` - Planning concern (EntryPlanner)
- ❌ `stop_loss` - Risk management concern (ExitPlanner)
- ❌ `position_size` - Sizing concern (SizePlanner)
- ❌ `trade_id` - Trade is post-hoc quant concept, not runtime entity

**Lifecycle:**
```
Created:    SignalDetector (pattern recognition)
Consumed:   StrategyPlanner (combines with Risk + Context)
            → StrategyPlanner creates FIRST causal link (signal_id → strategy_directive_id)
Persisted:  StrategyJournal (signal as standalone detection fact)
Never:      Modified after creation (frozen)
            Contains causality (Signal is pre-causality)
```

**Design Decisions:**
- **Decision 1:** signal_type as string (not enum)
  - Rationale: Runtime flexibility for plugin-based SignalDetectors. New detector = no core code change.

- **Decision 2:** Optional confidence field
  - Rationale: Not all pattern detectors quantify confidence (some are binary).

- **Decision 3:** UPPER_SNAKE_CASE convention
  - Rationale: Consistent naming (FVG_ENTRY, MSS_REVERSAL), grep-friendly.

- **Decision 4:** No causality field
  - Rationale: Signal is pre-causality. CausalityChain starts at StrategyPlanner decision.

---

### Risk

**Purpose:** Threat detection output from RiskMonitors

**WHY this DTO exists:**
- RiskMonitors produce objective threat detection events (portfolio/position/systemic risks)
- Separates "threat detected" from "risk decision" (SRP - StrategyPlanner decides action)
- Severity scoring enables risk-weighted decision making
- Pure detection facts - no causality yet (causality starts at StrategyPlanner decision)
- System-wide scope (no trade_id) - risks are portfolio-level or market-level concerns

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | RiskMonitor (any subtype) | Emits Risk when threat detected |
| **Consumers** | StrategyPlanner | Decision input (combines Signal + Risk + Context) |
| | Journal | Persistence (historical risk analysis) |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `risk_id` | str | Yes (auto) | Unique identifier (RSK_ prefix). Foundation for causality chain. |
| `timestamp` | datetime | Yes | Exact moment of threat detection (UTC). Point-in-time model. |
| `risk_type` | str | Yes | Threat identifier (UPPER_SNAKE_CASE). Plugin-specific. |
| `severity` | float | Yes | Risk severity [0.0-1.0]. Always required (all risks quantify threat level). |
| `affected_symbol` | str \| None | No | Asset identifier or None for system-wide risks. |

**WHY frozen:** Risks are immutable facts ("threat detected at T").

**WHY NOT included:**
- ❌ `causality` - Risk is pre-causality (pure detection fact)
- ❌ `mitigation_plan` - Planning concern (StrategyPlanner/ExitPlanner)
- ❌ `trade_id` - Trade is post-hoc quant concept
- ❌ `action_taken` - Outcome tracking, not detection data

**Lifecycle:**
```
Created:    RiskMonitor (threat recognition)
Consumed:   StrategyPlanner (combines with Signal + Context)
            → StrategyPlanner creates FIRST causal link (risk_id → strategy_directive_id)
Persisted:  StrategyJournal (risk as standalone detection fact)
Never:      Modified after creation (frozen)
            Contains causality (Risk is pre-causality)
```

**Design Decisions:**
- **Decision 1:** Required severity (unlike optional Signal.confidence)
  - Rationale: All risks quantify threat level. Risk without severity is meaningless.

- **Decision 2:** Optional affected_symbol for system-wide risks
  - Rationale: Some risks are portfolio-wide (flash crash, exchange down).

- **Decision 3:** Severity mirrors Signal.confidence scale
  - Rationale: Symmetric scoring enables balanced decision algebra.

---

## 3. Strategic DTOs

### StrategyDirective

**Purpose:** Strategy planning decision output from StrategyPlanner to role-based planners

**WHY this DTO exists:**
- StrategyPlanner produces high-level trade decisions (NEW_TRADE, MODIFY_ORDER, CLOSE_ORDER)
- Separates "strategic decision" from "tactical planning" (SRP)
- Contains 4 sub-directives (Entry, Size, Exit, Routing) as constraints/hints for specialized planners
- Bridge between Analysis DTOs (Signal/Risk) and Planning DTOs (EntryPlan/SizePlan/etc)
- Mutable for downstream enrichment (order_ids tracking after execution)

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | StrategyPlanner | Combines Signal + Risk + Context → trade decision |
| **Consumers** | EntryPlanner | Reads entry_directive for entry constraints |
| | ExitPlanner | Reads exit_directive for exit constraints |
| | SizePlanner | Reads size_directive for sizing constraints |
| | RoutingPlanner | Reads routing_directive for routing constraints |
| | Journal | Persistence (decision audit trail) |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `directive_id` | str | Yes (auto) | Unique identifier (STR_ prefix). Added to causality chain. |
| `strategy_planner_id` | str | Yes | Which StrategyPlanner produced directive. |
| `decision_timestamp` | datetime | Yes (auto) | Exact moment of decision (UTC). |
| `causality` | CausalityChain | Yes | Complete ID chain from origin. |
| `scope` | DirectiveScope | Yes | Decision type: NEW_TRADE, MODIFY_ORDER, CLOSE_ORDER. |
| `confidence` | Decimal | Yes | Decision confidence [0.0-1.0]. |
| `target_order_ids` | list[str] | No | Existing order IDs for MODIFY/CLOSE. Empty for NEW_TRADE. |
| `entry_directive` | EntryDirective \| None | No | Entry constraints for EntryPlanner. |
| `size_directive` | SizeDirective \| None | No | Sizing constraints for SizePlanner. |
| `exit_directive` | ExitDirective \| None | No | Exit constraints for ExitPlanner. |
| `routing_directive` | RoutingDirective \| None | No | Routing constraints for RoutingPlanner. |

**WHY NOT frozen:** Enriched post-execution (order_ids added after orders placed).

**WHY NOT included:**
- ❌ `entry_price` - EntryPlanner calculates (tactical detail)
- ❌ `position_size` - SizePlanner calculates (tactical detail)
- ❌ `stop_loss_price` - ExitPlanner calculates (tactical detail)
- ❌ `approved` - Directive IS the approval

**Lifecycle:**
```
Created:    StrategyPlanner (combines Signal + Risk + Context)
Extended:   causality.strategy_directive_id = directive_id
Consumed:   Role-based planners read sub-directives
Enriched:   order_ids added after ExecutionHandler places orders
Persisted:  StrategyJournal (complete decision audit trail)
Modified:   Post-creation (order_ids tracking)
```

**Scope Semantics:**

| Scope | target_order_ids | Typical Sub-directives |
|-------|------------------|------------------------|
| NEW_TRADE | Empty | entry, size, exit, routing |
| MODIFY_ORDER | Not empty | size, exit, routing |
| CLOSE_ORDER | Not empty | routing (exit urgency) |

**Design Decisions:**
- **Decision 1:** 4 optional sub-directives
  - Rationale: Flexibility - not all directives need all constraints.

- **Decision 2:** Sub-directives as constraints (not tactical plans)
  - Rationale: SRP - StrategyPlanner sets strategic constraints, planners calculate details.

- **Decision 3:** Mutable (not frozen)
  - Rationale: Enriched downstream (order_ids tracking).

- **Decision 4:** RoutingDirective name (not ExecutionDirective)
  - Rationale: Avoids naming conflict with Execution layer DTO.

---

### TradePlan

**Purpose:** Execution Anchor and state container for the entire trade lifecycle

**WHY this DTO exists:**
- Serves as the **Root Entity** for a trade's lifecycle (Entry → Execution → Exit)
- **Execution Anchor:** All tactical plans and orders link back to this ID
- **State Container:** Tracks high-level status (ACTIVE, CLOSED)
- **Ledger Integration:** Primary entity managed by StrategyLedger
- **Minimalist Design:** Contains ONLY identity, linkage, and status

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | StrategyPlanner | Creates TradePlan when NEW_TRADE directive issued |
| **Consumers** | StrategyLedger | Persists and updates status |
| | ExecutionHandler | Uses plan_id to tag orders |
| | StrategyJournal | Uses plan_id to correlate events |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `plan_id` | str | Yes | Unique identifier (TPL_ prefix). Anchor for all downstream artifacts. |
| `strategy_instance_id` | str | Yes | Links trade to strategy instance. |
| `status` | TradeStatus | Yes | Lifecycle state (ACTIVE, CLOSED). Mutable. |
| `created_at` | datetime | Yes | Creation timestamp (UTC). |

**WHY NOT frozen:** Status field MUST be mutable for lifecycle changes.

**WHY NOT included:**
- ❌ `asset_symbol` - Belongs to EntryPlan or StrategyDirective
- ❌ `metadata` - History belongs to StrategyJournal
- ❌ `child_lists` (orders, fills) - Children point to Parent, not vice versa

**Lifecycle:**
```
Created:    StrategyPlanner (on NEW_TRADE decision)
Persisted:  StrategyLedger (immediately)
Referenced: EntryPlan, ExitPlan, ExecutionDirective (all link to plan_id)
Updated:    StrategyLedger (status changes to CLOSED)
Archived:   StrategyLedger (historical retention)
```

**Design Decisions:**
- **Decision 1:** "Execution Anchor" pattern
  - Rationale: Decouples "concept of a trade" from "execution of orders".

- **Decision 2:** Minimalist fields
  - Rationale: SRP. TradePlan = State/Identity. StrategyJournal = History/Context.

---

## 4. Pipeline Context

```
ContextWorkers → Objective facts (EMA=50100, regime=BULLISH)
       ↓
SignalDetectors → Patterns (FVG detected, confidence 0.85)
       ↓
RiskMonitors → Threats (drawdown approaching, severity 0.7)
       ↓
StrategyPlanner → Decision (combine signals + risks)
       ↓
StrategyDirective + TradePlan
       ↓
Specialized Planners (Entry, Size, Exit, Routing)
```

**Key Insight:** Signal and Risk are **pre-causality** (pure detection facts). CausalityChain starts at StrategyPlanner decision point.

---

## 5. TODO.md Technical Debt Alignment

The following DTO changes are tracked in TODO.md:

| Item | Status | Impact |
|------|--------|--------|
| Signal DTO: Remove causality field | ✅ Done | Signal is pre-causality |
| Risk DTO: Remove causality field | ✅ Done | Risk is pre-causality |
| Symbol field naming consistency | Pending | BASE_QUOTE format |
| StrategyDirective: target_trade_ids → target_plan_ids | Pending | Align with TradePlan |
| ExecutionGroup: metadata field review | Pending | See DTO_EXECUTION.md |
| ExecutionDirective → RoutingDirective rename | Rejected | Different concerns |
| Asset format: BASE/QUOTE → BASE_QUOTE | Pending | Validation patterns |

---

## 6. Related Documents

- [DTO Architecture](DTO_ARCHITECTURE.md) - Overview and design principles
- [DTO Core](DTO_CORE.md) - Platform and infrastructure DTOs
- [DTO Execution](DTO_EXECUTION.md) - Planning and execution DTOs
- [Pipeline Flow](PIPELINE_FLOW.md) - Phase sequencing
- [Execution Flow](EXECUTION_FLOW.md) - Sync/async flows

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-29 | AI Assistant | Split from DTO_ARCHITECTURE.md |
