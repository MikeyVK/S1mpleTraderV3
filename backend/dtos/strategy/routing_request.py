# backend/dtos/strategy/routing_request.py
"""
RoutingRequest DTO - Aggregated input for RoutingPlanner.

Type-safe container for all 3 parallel plans (Entry, Size, Exit) plus
StrategyDirective context, ensuring router has complete trade picture for
multi-dimensional execution optimization.

**Architectural Foundation:**
- Almgren-Chriss Market Impact Model (2000): Optimal execution strategy
  requires simultaneous optimization over entry price, exit target, and position size
- Industry Practice: Bloomberg EMSX, Goldman REDI smart order routing uses
  order type, size, and price levels for venue selection

**Router Dependencies (Why All 3 Plans Required):**
1. Entry Plan:
   - order_type → TIF selection (MARKET=IOC, LIMIT=GTC, STOP_LIMIT=FOK)
   - limit_price → Spread-based slippage tolerance calculation
   
2. Size Plan:
   - position_size → TWAP chunking decision (large orders split)
   - position_value → Venue capacity checks
   - leverage → Margin route selection (spot vs futures)
   
3. Exit Plan:
   - take_profit_price - entry.limit_price → Profit margin urgency (scalp vs swing)
   - stop_loss_price → Risk per unit for iceberg visibility calculation

@layer: DTOs (Strategy Planning Input)
@dependencies: [pydantic, backend.dtos.strategy.*]
"""

# Third-party imports
from pydantic import BaseModel, Field

# Application imports - avoid circular imports with TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.dtos.strategy import (
        EntryPlan,
        ExitPlan,
        SizePlan,
        StrategyDirective,
    )
else:
    # Runtime imports
    from backend.dtos.strategy.entry_plan import EntryPlan
    from backend.dtos.strategy.exit_plan import ExitPlan
    from backend.dtos.strategy.size_plan import SizePlan
    from backend.dtos.strategy.strategy_directive import StrategyDirective


class RoutingRequest(BaseModel):
    """
    Aggregated input for RoutingPlanner - Type-safe router dependency enforcement.
    
    Contains all 3 parallel plans (Entry, Size, Exit) plus StrategyDirective
    context. Ensures router has complete trade characteristics for optimal
    execution strategy decision.
    
    **Why Router Needs All 3 Plans:**
    Routing is a multi-dimensional optimization that depends on:
    - Entry characteristics (WHAT/WHERE) → timing, TIF
    - Size characteristics (HOW MUCH) → chunking, visibility
    - Exit characteristics (WHERE OUT) → urgency, slippage tolerance
    
    **Type Safety:**
    All fields required (not Optional). Compiler enforces that router cannot
    execute without complete trade picture. This prevents sub-optimal routing
    decisions based on incomplete information.
    
    Fields:
        strategy_directive: SWOT context with confidence score and hints/constraints
        entry_plan: Entry characteristics (symbol, direction, order type, prices)
        size_plan: Position sizing (quantity, value, risk, leverage)
        exit_plan: Exit targets (stop loss, take profit)
    
    Examples:
        >>> # Standard limit order with medium size
        >>> request = RoutingRequest(
        ...     strategy_directive=directive,  # Confidence 0.75
        ...     entry_plan=EntryPlan(...),     # LIMIT @ 100k
        ...     size_plan=SizePlan(...),       # 1.0 BTC
        ...     exit_plan=ExitPlan(...)        # SL 95k, TP 105k
        ... )
        >>> # Router uses: limit order → GTC, medium size → no TWAP,
        >>> #               5% profit margin → moderate slippage tolerance
        
        >>> # Large position with market entry (high urgency)
        >>> request = RoutingRequest(
        ...     strategy_directive=directive,  # Confidence 0.90
        ...     entry_plan=EntryPlan(...),     # MARKET order
        ...     size_plan=SizePlan(...),       # 15.0 BTC (large!)
        ...     exit_plan=ExitPlan(...)        # SL 97k, TP 102k
        ... )
        >>> # Router uses: market → IOC, large size → TWAP + iceberg,
        >>> #               tight margin → strict slippage limit
    """

    strategy_directive: StrategyDirective = Field(
        description=(
            "Strategic context with SWOT analysis, confidence score, "
            "and hints/constraints for routing decisions"
        )
    )

    entry_plan: EntryPlan = Field(
        description=(
            "Entry characteristics (WHAT/WHERE): symbol, direction, "
            "order type, price levels - Required for TIF and timing decisions"
        )
    )

    size_plan: SizePlan = Field(
        description=(
            "Position sizing (HOW MUCH): quantity, value, risk, leverage - "
            "Required for TWAP chunking, iceberg visibility, venue selection"
        )
    )

    exit_plan: ExitPlan = Field(
        description=(
            "Exit targets (WHERE OUT): stop loss, take profit - "
            "Required for profit margin urgency and slippage tolerance calculation"
        )
    )

    model_config = {
        "frozen": True,  # Immutable - routing decision snapshot
        "extra": "forbid",  # No additional fields
        "str_strip_whitespace": True,
    }
