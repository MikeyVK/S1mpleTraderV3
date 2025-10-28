# tests/unit/dtos/strategy/test_routing_request.py
"""
Tests for RoutingRequest DTO.

RoutingRequest aggregates Entry+Size+Exit plans + StrategyDirective context
for type-safe router input. Ensures router has all required trade characteristics
for multi-dimensional execution optimization.
"""

from decimal import Decimal

import pytest

from backend.dtos.causality import CausalityChain
from backend.dtos.strategy import (
    EntryPlan,
    ExitPlan,
    RoutingRequest,
    SizePlan,
    StrategyDirective,
)
from backend.dtos.strategy.strategy_directive import (
    EntryDirective,
    ExitDirective,
    RoutingDirective,
    SizeDirective,
)


# === STAP 1: Creation Tests ===


def test_create_routing_request_with_all_fields():
    """Test creating RoutingRequest with all required fields."""
    # Arrange
    causality = CausalityChain(tick_id="TCK_20251028_100000_abc123")
    directive = StrategyDirective(
        causality=causality,
        confidence=Decimal("0.75"),
        entry_directive=EntryDirective(symbol="BTCUSDT", direction="BUY"),
        size_directive=SizeDirective(),
        exit_directive=ExitDirective(),
        routing_directive=RoutingDirective(),
    )
    entry = EntryPlan(
        symbol="BTCUSDT", direction="BUY", order_type="LIMIT", limit_price=Decimal("100000.00")
    )
    size = SizePlan(
        position_size=Decimal("0.5"),
        position_value=Decimal("50000.00"),
        risk_amount=Decimal("500.00"),
    )
    exit_plan = ExitPlan(
        stop_loss_price=Decimal("95000.00"), take_profit_price=Decimal("105000.00")
    )

    # Act
    request = RoutingRequest(
        strategy_directive=directive, entry_plan=entry, size_plan=size, exit_plan=exit_plan
    )

    # Assert
    assert request.strategy_directive == directive
    assert request.entry_plan == entry
    assert request.size_plan == size
    assert request.exit_plan == exit_plan


def test_create_routing_request_with_market_order():
    """Test RoutingRequest with MARKET order entry (high urgency scenario)."""
    # Arrange
    causality = CausalityChain(tick_id="TCK_20251028_100100_def456")
    directive = StrategyDirective(
        causality=causality,
        confidence=Decimal("0.90"),
        entry_directive=EntryDirective(symbol="ETHUSDT", direction="SELL"),
        size_directive=SizeDirective(aggressiveness=Decimal("0.8")),
        exit_directive=ExitDirective(),
        routing_directive=RoutingDirective(execution_urgency=Decimal("0.95")),
    )
    entry = EntryPlan(symbol="ETHUSDT", direction="SELL", order_type="MARKET")
    size = SizePlan(
        position_size=Decimal("10.0"),
        position_value=Decimal("35000.00"),
        risk_amount=Decimal("700.00"),
    )
    exit_plan = ExitPlan(stop_loss_price=Decimal("3600.00"))

    # Act
    request = RoutingRequest(
        strategy_directive=directive, entry_plan=entry, size_plan=size, exit_plan=exit_plan
    )

    # Assert - Router can check order_type for TIF decision
    assert getattr(request.entry_plan, "order_type") == "MARKET"
    assert getattr(request.strategy_directive.routing_directive, "execution_urgency") == Decimal(
        "0.95"
    )


def test_create_routing_request_with_large_position():
    """Test RoutingRequest with large position (TWAP + iceberg scenario)."""
    # Arrange
    causality = CausalityChain(tick_id="TCK_20251028_100200_ghi789")
    directive = StrategyDirective(
        causality=causality,
        confidence=Decimal("0.65"),
        entry_directive=EntryDirective(symbol="BTCUSDT", direction="BUY"),
        size_directive=SizeDirective(aggressiveness=Decimal("0.4")),
        exit_directive=ExitDirective(),
        routing_directive=RoutingDirective(execution_urgency=Decimal("0.3")),
    )
    entry = EntryPlan(
        symbol="BTCUSDT",
        direction="BUY",
        order_type="LIMIT",
        limit_price=Decimal("98000.00"),
    )
    size = SizePlan(
        position_size=Decimal("15.0"),  # Large position
        position_value=Decimal("1470000.00"),
        risk_amount=Decimal("14700.00"),
    )
    exit_plan = ExitPlan(
        stop_loss_price=Decimal("97000.00"), take_profit_price=Decimal("102000.00")
    )

    # Act
    request = RoutingRequest(
        strategy_directive=directive, entry_plan=entry, size_plan=size, exit_plan=exit_plan
    )

    # Assert - Router can check position_size for TWAP decision
    assert getattr(request.size_plan, "position_size") > Decimal("10.0")
    assert getattr(request.entry_plan, "order_type") == "LIMIT"


# === STAP 2: Validation Tests ===


def test_routing_request_requires_strategy_directive():
    """Test that RoutingRequest requires strategy_directive."""
    # Arrange
    entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")
    size = SizePlan(
        position_size=Decimal("1.0"),
        position_value=Decimal("100000.00"),
        risk_amount=Decimal("1000.00"),
    )
    exit_plan = ExitPlan(stop_loss_price=Decimal("95000.00"))

    # Act & Assert
    with pytest.raises(Exception):  # Pydantic validation error
        RoutingRequest(
            strategy_directive=None, entry_plan=entry, size_plan=size, exit_plan=exit_plan
        )


def test_routing_request_requires_entry_plan():
    """Test that RoutingRequest requires entry_plan."""
    # Arrange
    causality = CausalityChain(tick_id="TCK_20251028_100300_jkl012")
    directive = StrategyDirective(
        causality=causality,
        confidence=Decimal("0.75"),
        entry_directive=EntryDirective(symbol="BTCUSDT", direction="BUY"),
        size_directive=SizeDirective(),
        exit_directive=ExitDirective(),
        routing_directive=RoutingDirective(),
    )
    size = SizePlan(
        position_size=Decimal("1.0"),
        position_value=Decimal("100000.00"),
        risk_amount=Decimal("1000.00"),
    )
    exit_plan = ExitPlan(stop_loss_price=Decimal("95000.00"))

    # Act & Assert
    with pytest.raises(Exception):  # Pydantic validation error
        RoutingRequest(
            strategy_directive=directive, entry_plan=None, size_plan=size, exit_plan=exit_plan
        )


def test_routing_request_requires_size_plan():
    """Test that RoutingRequest requires size_plan."""
    # Arrange
    causality = CausalityChain(tick_id="TCK_20251028_100400_mno345")
    directive = StrategyDirective(
        causality=causality,
        confidence=Decimal("0.75"),
        entry_directive=EntryDirective(symbol="BTCUSDT", direction="BUY"),
        size_directive=SizeDirective(),
        exit_directive=ExitDirective(),
        routing_directive=RoutingDirective(),
    )
    entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")
    exit_plan = ExitPlan(stop_loss_price=Decimal("95000.00"))

    # Act & Assert
    with pytest.raises(Exception):  # Pydantic validation error
        RoutingRequest(
            strategy_directive=directive, entry_plan=entry, size_plan=None, exit_plan=exit_plan
        )


def test_routing_request_requires_exit_plan():
    """Test that RoutingRequest requires exit_plan."""
    # Arrange
    causality = CausalityChain(tick_id="TCK_20251028_100500_pqr678")
    directive = StrategyDirective(
        causality=causality,
        confidence=Decimal("0.75"),
        entry_directive=EntryDirective(symbol="BTCUSDT", direction="BUY"),
        size_directive=SizeDirective(),
        exit_directive=ExitDirective(),
        routing_directive=RoutingDirective(),
    )
    entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")
    size = SizePlan(
        position_size=Decimal("1.0"),
        position_value=Decimal("100000.00"),
        risk_amount=Decimal("1000.00"),
    )

    # Act & Assert
    with pytest.raises(Exception):  # Pydantic validation error
        RoutingRequest(
            strategy_directive=directive, entry_plan=entry, size_plan=size, exit_plan=None
        )


# === STAP 3: Immutability Tests ===


def test_routing_request_is_frozen():
    """Test that RoutingRequest is immutable (frozen)."""
    # Arrange
    causality = CausalityChain(tick_id="TCK_20251028_100600_stu901")
    directive = StrategyDirective(
        causality=causality,
        confidence=Decimal("0.75"),
        entry_directive=EntryDirective(symbol="BTCUSDT", direction="BUY"),
        size_directive=SizeDirective(),
        exit_directive=ExitDirective(),
        routing_directive=RoutingDirective(),
    )
    entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")
    size = SizePlan(
        position_size=Decimal("1.0"),
        position_value=Decimal("100000.00"),
        risk_amount=Decimal("1000.00"),
    )
    exit_plan = ExitPlan(stop_loss_price=Decimal("95000.00"))
    request = RoutingRequest(
        strategy_directive=directive, entry_plan=entry, size_plan=size, exit_plan=exit_plan
    )

    # Act & Assert
    with pytest.raises(Exception):  # ValidationError (frozen model)
        request.entry_plan = EntryPlan(symbol="ETHUSDT", direction="SELL", order_type="LIMIT")


def test_routing_request_no_extra_fields():
    """Test that RoutingRequest forbids extra fields."""
    # Arrange
    causality = CausalityChain(tick_id="TCK_20251028_100700_vwx234")
    directive = StrategyDirective(
        causality=causality,
        confidence=Decimal("0.75"),
        entry_directive=EntryDirective(symbol="BTCUSDT", direction="BUY"),
        size_directive=SizeDirective(),
        exit_directive=ExitDirective(),
        routing_directive=RoutingDirective(),
    )
    entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")
    size = SizePlan(
        position_size=Decimal("1.0"),
        position_value=Decimal("100000.00"),
        risk_amount=Decimal("1000.00"),
    )
    exit_plan = ExitPlan(stop_loss_price=Decimal("95000.00"))

    # Act & Assert
    with pytest.raises(Exception):  # ValidationError (extra='forbid')
        RoutingRequest(
            strategy_directive=directive,
            entry_plan=entry,
            size_plan=size,
            exit_plan=exit_plan,
            extra_field="not_allowed",
        )


# === STAP 4: Router Decision Support Tests ===


def test_routing_request_supports_profit_margin_calculation():
    """Test router can calculate profit margin from entry and exit plans."""
    # Arrange
    causality = CausalityChain(tick_id="TCK_20251028_100800_yzab567")
    directive = StrategyDirective(
        causality=causality,
        confidence=Decimal("0.80"),
        entry_directive=EntryDirective(symbol="BTCUSDT", direction="BUY"),
        size_directive=SizeDirective(),
        exit_directive=ExitDirective(),
        routing_directive=RoutingDirective(),
    )
    entry = EntryPlan(
        symbol="BTCUSDT",
        direction="BUY",
        order_type="LIMIT",
        limit_price=Decimal("100000.00"),
    )
    size = SizePlan(
        position_size=Decimal("1.0"),
        position_value=Decimal("100000.00"),
        risk_amount=Decimal("1000.00"),
    )
    exit_plan = ExitPlan(
        stop_loss_price=Decimal("99000.00"),
        take_profit_price=Decimal("100500.00"),  # Tight 0.5% margin (scalping)
    )

    # Act
    request = RoutingRequest(
        strategy_directive=directive, entry_plan=entry, size_plan=size, exit_plan=exit_plan
    )

    # Assert - Router can calculate profit margin
    entry_price = getattr(request.entry_plan, "limit_price")
    exit_price = getattr(request.exit_plan, "take_profit_price")
    profit_margin = (exit_price - entry_price) / entry_price
    assert profit_margin < Decimal("0.01")  # Less than 1% (scalping scenario)


def test_routing_request_supports_leverage_routing():
    """Test router can access leverage for margin route selection."""
    # Arrange
    causality = CausalityChain(tick_id="TCK_20251028_100900_cdef890")
    directive = StrategyDirective(
        causality=causality,
        confidence=Decimal("0.70"),
        entry_directive=EntryDirective(symbol="BTCUSDT", direction="BUY"),
        size_directive=SizeDirective(),
        exit_directive=ExitDirective(),
        routing_directive=RoutingDirective(),
    )
    entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")
    size = SizePlan(
        position_size=Decimal("2.0"),
        position_value=Decimal("200000.00"),
        risk_amount=Decimal("2000.00"),
        leverage=Decimal("3.0"),  # Leveraged position
    )
    exit_plan = ExitPlan(stop_loss_price=Decimal("95000.00"))

    # Act
    request = RoutingRequest(
        strategy_directive=directive, entry_plan=entry, size_plan=size, exit_plan=exit_plan
    )

    # Assert - Router can check leverage for futures routing
    assert getattr(request.size_plan, "leverage") > Decimal("1.0")
