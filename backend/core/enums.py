# backend/core/enums.py
"""
Central enumeration definitions.

All Literal types and enums used across DTOs and platform components.
Single source of truth for categorical values.

@layer: Core
@dependencies: []
@responsibilities: [enum definitions, type safety, documentation]
"""

# Standard Library Imports
from enum import Enum


# =============================================================================
# ORIGIN ENUMS
# =============================================================================

class OriginType(str, Enum):
    """Platform data origin types.
    
    Used in Origin DTO and CausalityChain for data source tracking.
    """
    TICK = "TICK"
    NEWS = "NEWS"
    SCHEDULE = "SCHEDULE"


# =============================================================================
# WORKER TYPE ENUMS
# =============================================================================

class ContextType(str, Enum):
    """
    Context worker categorization by analysis domain.

    Maps to worker subtypes for context enrichment.
    """
    REGIME_CLASSIFICATION = "REGIME_CLASSIFICATION"
    STRUCTURAL_ANALYSIS = "STRUCTURAL_ANALYSIS"
    INDICATOR_CALCULATION = "INDICATOR_CALCULATION"
    MICROSTRUCTURE_ANALYSIS = "MICROSTRUCTURE_ANALYSIS"
    TEMPORAL_CONTEXT = "TEMPORAL_CONTEXT"
    SENTIMENT_ENRICHMENT = "SENTIMENT_ENRICHMENT"
    FUNDAMENTAL_ENRICHMENT = "FUNDAMENTAL_ENRICHMENT"


class SignalType(str, Enum):
    """Signal detector categorization by pattern type."""
    BREAKOUT_DETECTION = "BREAKOUT_DETECTION"
    PULLBACK_DETECTION = "PULLBACK_DETECTION"
    REVERSAL_DETECTION = "REVERSAL_DETECTION"
    CONTINUATION_DETECTION = "CONTINUATION_DETECTION"
    ARBITRAGE_DETECTION = "ARBITRAGE_DETECTION"
    STATISTICAL_EDGE = "STATISTICAL_EDGE"
    SENTIMENT_EXTREME = "SENTIMENT_EXTREME"


class RiskType(str, Enum):
    """Risk monitor categorization by risk domain."""
    RISK_LIMIT_MONITORING = "RISK_LIMIT_MONITORING"
    DRAWDOWN_MONITORING = "DRAWDOWN_MONITORING"
    VOLATILITY_MONITORING = "VOLATILITY_MONITORING"
    CORRELATION_MONITORING = "CORRELATION_MONITORING"
    SYSTEMIC_RISK_DETECTION = "SYSTEMIC_RISK_DETECTION"


class PlanningPhase(str, Enum):
    """Planning worker categorization by planning stage."""
    ENTRY_PLANNING = "ENTRY_PLANNING"
    RISK_SIZING = "RISK_SIZING"
    EXIT_PLANNING = "EXIT_PLANNING"
    EXECUTION_ROUTING = "EXECUTION_ROUTING"


class ExecutionType(str, Enum):
    """Execution worker categorization by action type."""
    ORDER_PLACEMENT = "ORDER_PLACEMENT"
    ORDER_MANAGEMENT = "ORDER_MANAGEMENT"
    POSITION_MANAGEMENT = "POSITION_MANAGEMENT"
    REPORTING = "REPORTING"


# =============================================================================
# STRATEGY ENUMS
# =============================================================================

class DirectiveScope(str, Enum):
    """
    Scope of strategy directive.

    Determines what type of action the directive instructs:
    - NEW_TRADE: Open new position
    - MODIFY_EXISTING: Adjust existing position (stops, targets, size)
    - CLOSE_EXISTING: Close existing position(s)
    """
    NEW_TRADE = "NEW_TRADE"
    MODIFY_EXISTING = "MODIFY_EXISTING"
    CLOSE_EXISTING = "CLOSE_EXISTING"


class ExecutionAction(str, Enum):
    """
    Execution action types.

    Distinguishes between trade execution and order management operations.

    Values:
        EXECUTE_TRADE: Execute new trade (default)
        CANCEL_ORDER: Cancel specific order
        MODIFY_ORDER: Modify existing order
        CANCEL_GROUP: Cancel entire execution group (e.g., TWAP)
    """
    EXECUTE_TRADE = "EXECUTE_TRADE"
    CANCEL_ORDER = "CANCEL_ORDER"
    MODIFY_ORDER = "MODIFY_ORDER"
    CANCEL_GROUP = "CANCEL_GROUP"


class TradeStatus(str, Enum):
    """
    Lifecycle status of a TradePlan.

    Defines the high-level state of the strategic container.
    """
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


# =============================================================================
# EXECUTION ENUMS
# =============================================================================

class BatchExecutionMode(str, Enum):
    """Strategic execution coordination mode for command batches.

    Defines the coordination semantics from strategic intent (StrategyDirective).
    This is the strategic "what should happen" - not the technical "how to execute".

    Used in ExecutionPolicy (within StrategyDirective) to express coordination
    requirements that flow unchanged to ExecutionCommandBatch.

    Values:
        INDEPENDENT: Fire all commands, ignore individual failures.
                     Use case: Flash crash exit (close all positions ASAP).
        COORDINATED: Commands are related; cancel pending on failure.
                     Use case: Pair trade (both legs or neither).
        SEQUENTIAL: Execute in order, stop on first failure.
                    Use case: DCA (Dollar Cost Averaging) with dependencies.

    Design Note:
        Maps 1:1 from StrategyDirective.execution_policy → ExecutionCommandBatch.mode.
        No transformation logic - pure passthrough ("dumb pipe").

    See Also:
        - docs/development/backend/dtos/EXECUTION_COMMAND_BATCH_DESIGN.md
        - docs/development/backend/dtos/EXECUTION_COMMAND_DESIGN.md
    """
    INDEPENDENT = "INDEPENDENT"
    COORDINATED = "COORDINATED"
    SEQUENTIAL = "SEQUENTIAL"


class ExecutionMode(str, Enum):
    """Batch execution mode (LEGACY - to be replaced by BatchExecutionMode).

    Values:
        SEQUENTIAL: Execute 1-by-1, stop on first failure
        PARALLEL: Execute all simultaneously (no rollback)
        ATOMIC: All succeed or all rollback (transaction)

    @deprecated: Use BatchExecutionMode instead. This enum will be removed
                 when ExecutionCommandBatch is refactored.
    """
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"
    ATOMIC = "ATOMIC"


class ExecutionStrategyType(str, Enum):
    """Execution strategy types.

    Values:
        SINGLE: Single order (no grouping needed)
        TWAP: Time-Weighted Average Price
        VWAP: Volume-Weighted Average Price
        ICEBERG: Iceberg order (visible/hidden pairs)
        LAYERED: Layered limit orders
        POV: Percentage of Volume
    """
    SINGLE = "SINGLE"
    TWAP = "TWAP"
    VWAP = "VWAP"
    ICEBERG = "ICEBERG"
    LAYERED = "LAYERED"
    POV = "POV"


class GroupStatus(str, Enum):
    """Group lifecycle status.

    State Transitions:
        PENDING → ACTIVE → COMPLETED
        PENDING → ACTIVE → CANCELLED
        PENDING → ACTIVE → FAILED
        PENDING → ACTIVE → PARTIAL
        * → CANCELLED (any state can transition to CANCELLED)

    Values:
        PENDING: Created, no orders yet
        ACTIVE: Orders being executed
        COMPLETED: All orders filled/complete
        CANCELLED: Group cancelled (all orders cancelled)
        FAILED: Execution failed (error state)
        PARTIAL: Some orders filled, group stopped
    """
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


# =============================================================================
# ORDER ENUMS
# =============================================================================


class OrderType(str, Enum):
    """Order type specification.

    Values:
        MARKET: Execute immediately at current market price
        LIMIT: Execute at specified price or better
        STOP_LIMIT: Trigger limit order when stop price is reached
    """
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    """Order lifecycle status.

    State Transitions:
        PENDING → OPEN → FILLED
        PENDING → OPEN → PARTIALLY_FILLED → FILLED
        PENDING → OPEN → CANCELLED
        PENDING → REJECTED
        PENDING → OPEN → EXPIRED

    Values:
        PENDING: Created, not yet sent to exchange
        OPEN: Sent to exchange, awaiting fill
        PARTIALLY_FILLED: Partial execution received
        FILLED: Completely filled
        CANCELLED: Cancelled by user/system
        REJECTED: Rejected by exchange
        EXPIRED: Time-in-force expired
    """
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
