# Trade Lifecycle & Architecture - S1mpleTraderV3

**Status:** Definitive  
**Version:** 1.0  
**Goal:** This document complements `PIPELINE_FLOW.md` and `EXECUTION_FLOW.md`. It defines the data hierarchy, lifecycle scopes, and interaction patterns between strategic plugins and platform components.

---

## 1. Data Hierarchy (Nesting)

The lifecycle of a strategy is not managed by a single "Trade DTO" traveling through the pipeline, but by a strict hierarchy of **Persisted Entities** in the `StrategyLedger`. This ensures a clear separation of concerns.

### 1.1. Container Structure

```mermaid
erDiagram  
    StrategyPlanner ||--o{ TradePlan : "Manages (via StrategyDirectives)"  
    TradePlan ||--|{ ExecutionGroup : "Contains (1-to-N)"  
    ExecutionGroup ||--|{ Order : "Groups (1-to-N)"  
    Order ||--o{ Fill : "Results in (0-to-N)"

    TradePlan {  
        string plan_id "TP_..."  
        string strategy_instance_id "ID of StrategyPlanner (plugin) instance"  
        string asset_symbol "BTC/USDT"  
        string status "ACTIVE | CLOSED"  
        string comments "Optional strategic metadata"  
    }

    ExecutionGroup {  
        string group_id "EXG_..."  
        string parent_plan_id "TP_..."  
        string intent_action "EXECUTE_TRADE, CANCEL_GROUP, etc."  
        datetime created_at  
        string status "OPEN | FILLED | CANCELLED"  
    }

    Order {  
        string order_id "ORD_..."  
        string parent_group_id "EXG_..."  
        string connector_id "Unique ID from exchange (Binance_Spot_...)"  
        string status "OPEN | FILLED | CANCELED | REJECTED"  
    }

    Fill {  
        string fill_id "FILL_..."  
        string parent_order_id "ORD_..."  
        decimal price  
        decimal quantity  
        decimal fee  
    }
```

### 1.2. Ownership Matrix

| Level | Entity | Owner (Write/Manage) | Consumer (Read) | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Strategic** | **TradePlan** | StrategyPlanner (indirect) / StrategyLedger | StrategyPlanner (Self) | The long-lived container encompassing the *entire* strategy (e.g., Grid, DCA). Created by the Ledger upon the *first* ExecutionGroup. |
| **Tactical** | **ExecutionGroup** | ExecutionTranslator | StrategyPlanner (Read-only Ref), StrategyLedger | A logical set of 1-N orders resulting from **one** StrategyDirective. This is the atomic unit of tactical execution (e.g., "one TWAP run"). |
| **Operational** | **Order** | ExecutionHandler | ExchangeConnector | The actual, concrete instruction to the exchange. Contains no strategic context. |
| **Result** | **Fill** | ExchangeConnector (via Async Flow) | StrategyLedger | The immutable, hard reality (truth) from the market. [cite: Async Exchange Reply Flow] |

---

## 2. Access Levels & StrategyLedger API

The `StrategyLedger` is a **"dumb" gateway** to the ledger and ensures SRP. Intelligence resides *outside* the Ledger. Components are granted access based on their role.

### Level 1: High-Level Access (Strategy Domain)

*   **User:** StrategyPlanner (Plugin, the "General").
*   **Rights:** May read *abstract* `TradePlan` and `ExecutionGroup` data.
*   **Forbidden:** Must **never** directly write or modify individual `Order` objects.
*   **Example Methods:**
    *   `ledger.get_active_trade_plan(strategy_instance_id)`: Retrieves the "container".
    *   `ledger.get_execution_groups(plan_id)`: Returns a list of `ExecutionGroup` DTOs (ID, status).
    *   `ledger.get_net_position(plan_id)`: Calculates the *current* exposure for this plan.

### Level 2: Mid-Level Access (Translation Domain)

*   **User:** ExecutionTranslator (Platform, the "Unpacker").
*   **Rights:** Bridges the gap between abstract groups and concrete orders.
*   **Task:** Must know which Order IDs belong to ExecutionGroup X to build a `CANCEL_GROUP` command. [cite: Phase 4c: EXECUTION TRANSLATION]
*   **Example Methods:**
    *   `ledger.get_open_order_ids(group_id)`: Returns list `["ORD_A", "ORD_B"]`.
    *   `ledger.register_execution_group(group_dto)`

### Level 3: Low-Level Access (Execution Domain)

*   **User:** ExecutionHandler (Platform, the "Executor").
*   **Rights:** Writes the *actual* `Order` and `Fill` data.
*   **Example Methods:**
    *   `ledger.register_order(order_dto)`
    *   `ledger.update_order_status(order_id, status)`
    *   `ledger.register_fill(fill_dto)`

---

## 3. ExecutionIntent Command List

The `ExecutionIntent` (DTO) contains **operational commands**, not strategic logic. It is the output of the RoutingPlanner (Plugin) and the input for the ExecutionTranslator (Platform). [cite: ExecutionIntent - Universal Trade-Offs]

A "Grid" is strategy (and thus unknown to the Translator). `EXECUTE_TRADE` is an operation.

### Exhaustive List of ExecutionAction (Enum)

#### A. Creation Commands

*   **EXECUTE_TRADE**
    *   **Meaning:** "Place new orders according to the attached Entry/Size/Exit plans."
    *   **Context:** Used with `scope=NEW_TRADE` (new entry) or `scope=CLOSE_EXISTING` (new close order).
    *   **Consequence:** Translator creates 1-to-N `ConnectorExecutionSpec(s)` (e.g., for a TWAP).

#### B. Cancellation Commands

*   **CANCEL_GROUP**
    *   **Meaning:** "Cancel all open (unfilled) orders belonging to this TargetGroupID."
    *   **Context:** Used with `scope=MODIFY_EXISTING`. E.g., StrategyPlanner retracts a specific set of grid orders.
    *   **Consequence:** Translator calls `ledger.get_open_order_ids(group_id)` and builds a `ConnectorExecutionSpec` with cancellation requests.
*   **CANCEL_ALL_IN_PLAN**
    *   **Meaning:** "Emergency Stop. Cancel *all* open orders within the TargetPlanID."
    *   **Context:** Used with `scope=CLOSE_EXISTING` (Panic/Crash).
    *   **Consequence:** Translator calls `ledger.get_open_order_ids` for *every active group* in the plan.

#### C. Modification Commands

*   **MODIFY_ORDERS**
    *   **Meaning:** "Adjust parameters (e.g., price, quantity) of existing, open orders in TargetGroupID."
    *   **Context:** Used with `scope=MODIFY_EXISTING` (e.g., Trailing Stop). Requires the ExitPlan (or EntryPlan) to provide the new parameters.
    *   **Consequence:** Translator generates cancel-replace or modify API calls.

---

## 4. The Lifecycle Scopes (The "WHAT")

The `StrategyDirective.scope` is the **imperative command** (the "WHAT") from the StrategyPlanner (the "General"). [cite: Phase 3: STRATEGY PLANNING] This is *not* a hint. It dictates how the downstream TradePlanners (Specialists) must behave.

### Scope 1: NEW_TRADE (Creation)

*   **Command:** Create new exposure.
*   **Planner Reaction:**
    *   Entry/Size/Exit/Routing: All planners are "active" and in their *Core Business*. They determine **HOW** the new position is created.

### Scope 2: MODIFY_EXISTING (Mutation)

*   **Command:** Modify an existing `TradePlan` or `ExecutionGroup`.
*   **Planner Reaction:**
    *   Entry/Size: Usually passive (do nothing).
    *   Exit: Active if the SL/TP is adjusted.
    *   Routing: Active to determine the urgency of the *change*.
*   **Example:** A Trailing Stop StrategyPlanner sends `scope=MODIFY_EXISTING` with an `exit_hint` (new SL). Only the ExitPlanner and RoutingPlanner respond to this.

### Scope 3: CLOSE_EXISTING (Termination)

*   **Command:** Bring exposure to zero and/or cancel open orders.
*   **Planner Reaction:** The planners operate in "Close" mode.
    *   Entry: Often forces `MARKET` type.
    *   Size: Proposes (via Ledger query) 100% of the `netPositionSize`.
    *   Exit: Generates plans to cancel all open SL/TP orders.
    *   Routing: Sets urgency (usually high).

---

## 5. Reusability (The Base Class Pattern)

To prevent an "explosion of specialists" (e.g., NewEntryPlanner, ModifyEntryPlanner, CloseEntryPlanner), reusability is enforced via **Abstract Base Classes** in the platform.

The `TradePlanner` (Specialist Plugin) inherits from a base class and implements only the logic relevant to its specialization.

```python
# Example: Base Class for an EntryPlanner
class BaseEntryPlanner(ABC):

    def plan(self, directive: StrategyDirective) -> Optional[EntryPlan]:
        """
        The Master Method called by the pipeline.
        This logic resides in the platform, NOT in the plugin.
        """
        if directive.scope == StrategyScope.NEW_TRADE:
            # Quant's logic is called
            return self.on_new_trade(directive)
            
        elif directive.scope == StrategyScope.MODIFY_EXISTING:
            # Default: do nothing on 'modify'
            return self.on_modify_trade(directive)
            
        elif directive.scope == StrategyScope.CLOSE_EXISTING:
            # Default: generate a 'Market Sell' plan
            return self.on_close_trade(directive)
            
        return None

    # --- Methods for the Quant to implement ---

    @abstractmethod
    def on_new_trade(self, directive: StrategyDirective) -> EntryPlan:
        """
        Quant implements THIS (Core Business).
        E.g., "Calculate RSI and return a Limit order plan."
        """
        pass

    def on_modify_trade(self, directive: StrategyDirective) -> Optional[EntryPlan]:
        """
        Quant can override this.
        Default (in Base Class): return None
        """
        return None
        
    def on_close_trade(self, directive: StrategyDirective) -> EntryPlan:
        """
        Quant can override this (e.g., for a 'Limit' close).
        Default (in Base Class): return EntryPlan(order_type="MARKET")
        """
        return EntryPlan(order_type="MARKET", direction=...) # Determine 'direction' based on size
```
