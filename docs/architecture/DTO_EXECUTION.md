# docs/architecture/DTO_EXECUTION.md
# DTO Execution - S1mpleTraderV3

**Status:** PRELIMINARY
**Version:** 1.0
**Last Updated:** 2025-11-29

---

## Purpose

This document defines the **planning and execution DTOs** that translate strategic decisions into executable instructions.

**Target audience:** Developers implementing Planners or ExecutionBridge.

## Scope

**In Scope:**
- Planning DTOs: EntryPlan, SizePlan, ExitPlan, ExecutionPlan
- Execution DTOs: ExecutionDirective, ExecutionDirectiveBatch, ExecutionGroup

**Out of Scope:**
- DTO taxonomy overview → See [DTO_ARCHITECTURE.md](DTO_ARCHITECTURE.md)
- Core DTOs → See [DTO_CORE.md](DTO_CORE.md)
- Pipeline DTOs → See [DTO_PIPELINE.md](DTO_PIPELINE.md)

---

## 1. Planning DTOs

Planning DTOs represent tactical execution plans created by specialized planners.
Each DTO translates strategic constraints from StrategyDirective into concrete execution parameters.

**Architectural Pattern:**
```
StrategyDirective (strategic constraints)
  → EntryPlanner → EntryPlan (WHAT/WHERE to enter)
  → SizePlanner → SizePlan (HOW MUCH)
  → ExitPlanner → ExitPlan (WHERE OUT)
  → RoutingPlanner → ExecutionPlan (HOW/WHEN - trade-offs)
    → PlanningAggregator → ExecutionDirective (aggregated)
```

**Key Design Principles:**
- **Lean Specs:** Only execution-critical parameters (no metadata/timestamps)
- **No Causality:** Sub-planners receive StrategyDirective (has causality), plans inherit via aggregation
- **Universal:** Connector-agnostic (translation happens downstream)

---

### EntryPlan

**Purpose:** Entry execution specification (WHAT/WHERE to enter)

**WHY this DTO exists:**
- EntryPlanner translates entry constraints into concrete order specifications
- Separates "entry decision" from "entry execution" (SRP)
- Defines WHAT order type and WHERE (price levels)
- Lean spec - no metadata, timestamps, or causality

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `plan_id` | str | Yes (auto) | Unique identifier (ENT_ prefix). |
| `symbol` | str | Yes | Trading pair (BASE_QUOTE format). |
| `direction` | Literal["BUY", "SELL"] | Yes | Trade direction. Execution-layer terminology. |
| `order_type` | Literal["MARKET", "LIMIT", "STOP_LIMIT"] | Yes | Order execution type. |
| `limit_price` | Decimal \| None | No | Limit price for LIMIT/STOP_LIMIT orders. |
| `stop_price` | Decimal \| None | No | Stop trigger price for STOP_LIMIT orders. |

**WHY NOT frozen:** May be updated pre-execution (price adjustments).

**Design Decisions:**
- **Decision 1:** BUY/SELL over long/short - Execution-layer terminology.
- **Decision 2:** Three order types - Covers 90% of strategies.
- **Decision 3:** No causality field - Inherited via aggregation.

**Validation:**
- MARKET: limit_price/stop_price should be None
- LIMIT: limit_price required, stop_price None
- STOP_LIMIT: both required

---

### SizePlan

**Purpose:** Position sizing specification (HOW MUCH)

**WHY this DTO exists:**
- SizePlanner translates sizing constraints into absolute position size
- Account risk % → SizePlanner input, absolute size → SizePlan output
- Lean spec - only execution parameters

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `plan_id` | str | Yes (auto) | Unique identifier (SIZ_ prefix). |
| `position_size` | Decimal | Yes | Absolute size in base asset (e.g., 0.5 BTC). |
| `position_value` | Decimal | Yes | Value in quote asset (e.g., 50000 USDT). |
| `risk_amount` | Decimal | Yes | Absolute risk in quote (stop distance × size). |
| `leverage` | Decimal | Yes | Leverage multiplier (1.0 = no leverage). |

**WHY NOT frozen:** May be adjusted pre-execution (risk recalculations).

**Design Decisions:**
- **Decision 1:** Absolute values only - DTOs = execution parameters.
- **Decision 2:** position_value explicit - Enables risk calculations without price lookup.
- **Decision 3:** Leverage field included - Common in crypto/futures.

---

### ExitPlan

**Purpose:** Exit execution specification (WHERE OUT)

**WHY this DTO exists:**
- ExitPlanner translates exit constraints into price levels
- Static price targets - NO dynamic logic (trailing stops → PositionMonitor)
- Lean spec - only price levels

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `plan_id` | str | Yes (auto) | Unique identifier (EXT_ prefix). |
| `stop_loss_price` | Decimal | Yes | Stop loss price. Required (risk protection). |
| `take_profit_price` | Decimal \| None | No | Take profit price. Optional (let winners run). |

**WHY frozen:** Immutable after creation (static price targets).

**Design Decisions:**
- **Decision 1:** stop_loss_price required - Risk protection mandatory.
- **Decision 2:** take_profit_price optional - "Let winners run" strategy valid.
- **Decision 3:** No trailing stop fields - Trailing = dynamic (creates new ExitPlan).

---

### ExecutionPlan

**Purpose:** Execution trade-offs specification (HOW/WHEN - universal)

**WHY this DTO exists:**
- RoutingPlanner translates routing constraints into universal trade-offs
- Connector-agnostic (not CEX/DEX/Backtest-specific)
- Expresses WHAT strategy wants (urgency, visibility, slippage)
- Translation layer converts ExecutionPlan → connector-specific specs

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `plan_id` | str | Yes (auto) | Unique identifier (EXP_ prefix). |
| `action` | ExecutionAction | Yes | Action type: EXECUTE_TRADE, CANCEL_ORDER, MODIFY_ORDER, CANCEL_GROUP. |
| `execution_urgency` | Decimal | Yes | Patience vs speed (0.0=patient, 1.0=urgent). |
| `visibility_preference` | Decimal | Yes | Stealth vs transparency (0.0=stealth, 1.0=visible). |
| `max_slippage_pct` | Decimal | Yes | Hard price limit (0.0-1.0 = 0-100%). Constraint. |
| `must_complete_immediately` | bool | No | Force immediate execution. Constraint. |
| `max_execution_window_minutes` | int \| None | No | Maximum time window. Constraint. |
| `preferred_execution_style` | str \| None | No | Hint (e.g., "TWAP", "VWAP", "ICEBERG"). |
| `chunk_count_hint` | int \| None | No | Hint for execution chunks. |
| `min_fill_ratio` | Decimal \| None | No | Minimum fill ratio to accept. Constraint. |

**WHY frozen:** Execution decisions frozen at plan creation.

**Trade-off Types:**
- **Constraints (MUST respect):** max_slippage_pct, must_complete_immediately, max_execution_window_minutes, min_fill_ratio
- **Hints (MAY interpret):** preferred_execution_style, chunk_count_hint

**Universal → Connector Translation:**

| Universal | CEX | DEX | Backtest |
|-----------|-----|-----|----------|
| urgency=0.9, visibility=0.7 | MARKET order | MEV-protected swap | Instant fill |
| urgency=0.2, window=30min | TWAP 30min | Split orders | Simulated TWAP |
| style="ICEBERG" | ICEBERG order | Split orders | Single fill |

---

## 3. Execution DTOs

Execution DTOs represent final executable instructions and execution tracking.

**Architectural Pattern:**
```
PlanningAggregator
  → ExecutionDirective (single executable instruction)
    → ExecutionDirectiveBatch (atomic multi-directive coordination)
      → ExecutionGroup (multi-order execution tracking)
```

---

### ExecutionDirective

**Purpose:** Final aggregated execution instruction (single trade setup)

**WHY this DTO exists:**
- PlanningAggregator combines 4 plans → single executable instruction
- Clean separation: Strategy planning → Execution doing
- Supports partial updates (NEW_TRADE vs MODIFY vs scale-in)
- All plans optional enables flexibility

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `directive_id` | str | Yes (auto) | Unique identifier (EXE_ prefix). |
| `causality` | CausalityChain | Yes | Complete ID chain. Full traceability. |
| `entry_plan` | EntryPlan \| None | No | WHERE IN specification. |
| `size_plan` | SizePlan \| None | No | HOW MUCH specification. |
| `exit_plan` | ExitPlan \| None | No | WHERE OUT specification. |
| `execution_plan` | ExecutionPlan \| None | No | HOW/WHEN specification. |

**WHY frozen:** Immutable instruction snapshot.

**Validation:** At least 1 plan required (cannot be empty directive).

**Use Cases:**

| Use Case | Plans Present |
|----------|---------------|
| NEW_TRADE | Entry + Size + Exit + Execution |
| Trailing stop | Exit only |
| Urgency change | Execution only |
| Scale in | Entry + Size |
| Close position | Exit + Execution |

---

### ExecutionDirectiveBatch

**Purpose:** Atomic multi-directive execution coordination

**WHY this DTO exists:**
- PlanningAggregator ALWAYS produces ExecutionDirectiveBatch (even for 1 directive)
- Coordinates execution of 1-N ExecutionDirectives as single unit
- Enables atomic transactions (all succeed or all rollback)
- Supports execution modes (SEQUENTIAL, PARALLEL, ATOMIC)

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `batch_id` | str | Yes | Unique identifier (BAT_ prefix). |
| `directives` | List[ExecutionDirective] | Yes | Directives to execute (min 1). |
| `execution_mode` | ExecutionMode | Yes | SEQUENTIAL, PARALLEL, ATOMIC. |
| `created_at` | datetime | Yes | Batch creation timestamp. |
| `rollback_on_failure` | bool | Yes | Rollback all on any failure. MUST be True for ATOMIC. |
| `timeout_seconds` | int \| None | No | Max execution time. |
| `metadata` | Dict \| None | No | Batch context for debugging. |

**WHY frozen:** Coordination contract frozen at creation.

**Execution Modes:**

| Mode | Behavior | Use Case |
|------|----------|----------|
| SEQUENTIAL | Execute 1-by-1 | Ordered operations (hedge → main) |
| PARALLEL | Execute all simultaneously | Independent operations |
| ATOMIC | All succeed or all rollback | Critical coordination |

---

### ExecutionGroup

**Purpose:** Multi-order execution tracking for advanced strategies

**WHY this DTO exists:**
- Tracks lifecycle of multi-order strategies (TWAP, ICEBERG, DCA, LAYERED, POV)
- Groups orders spawned from single ExecutionDirective
- Mutable status tracking (PENDING → ACTIVE → COMPLETED/CANCELLED/FAILED/PARTIAL)
- Enables atomic group operations (cancel all TWAP chunks)

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `group_id` | str | Yes | Unique identifier (EXG_ prefix). |
| `parent_directive_id` | str | Yes | ExecutionDirective that spawned group. |
| `execution_strategy` | ExecutionStrategyType | Yes | SINGLE, TWAP, VWAP, ICEBERG, DCA, LAYERED, POV. |
| `order_ids` | List[str] | Yes | Connector order IDs (grows during execution). |
| `status` | GroupStatus | Yes | PENDING, ACTIVE, COMPLETED, CANCELLED, FAILED, PARTIAL. |
| `created_at` | datetime | Yes | Group creation timestamp. |
| `updated_at` | datetime | Yes | Last update timestamp. |
| `target_quantity` | Decimal \| None | No | Planned total quantity. |
| `filled_quantity` | Decimal \| None | No | Actual filled so far. |
| `cancelled_at` | datetime \| None | No | Cancellation timestamp. |
| `completed_at` | datetime \| None | No | Completion timestamp. |
| `metadata` | Dict \| None | No | Strategy-specific parameters. |

**WHY NOT frozen:** Tracking entity - status, order_ids, filled_quantity evolve.

**Execution Strategy Types:**

| Strategy | Orders | Use Case |
|----------|--------|----------|
| SINGLE | 1 | Simple market/limit order |
| TWAP | 5-20 | Spread over time, minimize impact |
| VWAP | Variable | Match market volume profile |
| ICEBERG | 2-10 | Hide large order intent |
| DCA | 10-50 | Systematic accumulation |
| LAYERED | 3-10 | Multiple entry points |
| POV | Variable | Maintain % of market volume |

**Status Transitions:**

```
PENDING ────→ ACTIVE ────→ COMPLETED (all filled)
                │
                ├──────→ CANCELLED (cancel request)
                │
                ├──────→ FAILED (execution error)
                │
                └──────→ PARTIAL (some filled, stopped)
```

**Validation:**
- order_ids: All unique (no duplicates)
- filled_quantity <= target_quantity
- cancelled_at XOR completed_at (mutually exclusive)

---

## 4. Layer Separation

| Layer | DTOs | Concern |
|-------|------|---------|
| Strategy | StrategyDirective | Strategic decisions, constraints |
| Planning | EntryPlan, SizePlan, ExitPlan, ExecutionPlan | Tactical specifications |
| Execution | ExecutionDirective, ExecutionDirectiveBatch | Final instructions |
| Tracking | ExecutionGroup | Multi-order lifecycle |

**Key Insight:** No strategy metadata in execution DTOs (causality provides traceability).

---

## 5. Related Documents

- [DTO Architecture](DTO_ARCHITECTURE.md) - Overview and design principles
- [DTO Core](DTO_CORE.md) - Platform and infrastructure DTOs
- [DTO Pipeline](DTO_PIPELINE.md) - Analysis and strategic DTOs
- [Execution Flow](EXECUTION_FLOW.md) - Sync/async flows
- [Event Persistence](EVENT_PERSISTENCE.md) - Event durability

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-29 | AI Assistant | Split from DTO_ARCHITECTURE.md |
