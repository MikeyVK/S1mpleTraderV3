# backend/dtos/state/order.py
"""
Order DTO - Exchange order lifecycle tracking.

Represents a single order sent to an exchange. Part of the State layer,
owned exclusively by StrategyLedger.

**Architectural Role (per TRADE_LIFECYCLE.md):**
- Level 3 container: TradePlan → ExecutionGroup → **Order** → Fill
- Represents **exchange intent** (what we want to happen)
- May differ from Fill (execution reality) - partial fills, rejections

**Mutability Contract:**
- frozen=False (status, connector_order_id, updated_at evolve during lifecycle)
- Immutable identifiers: order_id, parent_group_id never change after creation

@layer: DTOs (State)
@dependencies: [
    pydantic, backend.core.enums, backend.utils.id_generators
]
"""

from datetime import datetime
from decimal import Decimal
from re import match
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.core.enums import OrderStatus, OrderType
from backend.utils.id_generators import generate_order_id


class Order(BaseModel):
    """
    Exchange order lifecycle tracking.

    Tracks a single order from creation through completion. Mutable to
    reflect status updates from exchange.

    **Fields:**
    - order_id: Auto-generated unique identifier (ORD_YYYYMMDD_HHMMSS_hash)
    - parent_group_id: Reference to parent ExecutionGroup
    - connector_order_id: Exchange-assigned order ID (set after submission)
    - symbol: Trading pair (e.g., BTC_USDT)
    - side: Order direction (BUY/SELL)
    - order_type: Order type (MARKET, LIMIT, STOP_LIMIT)
    - quantity: Order size (always positive)
    - price: Limit price (required for LIMIT orders)
    - stop_price: Stop trigger price (required for STOP_LIMIT orders)
    - status: Order lifecycle status
    - created_at: Order creation timestamp (UTC)
    - updated_at: Last update timestamp (UTC)

    **Lifecycle:**
    PENDING → OPEN → FILLED
    PENDING → OPEN → PARTIALLY_FILLED → FILLED
    PENDING → OPEN → CANCELLED
    PENDING → REJECTED
    """

    order_id: str = Field(
        default_factory=generate_order_id,
        description="Auto-generated unique order ID (ORD_YYYYMMDD_HHMMSS_hash)",
    )
    parent_group_id: str = Field(
        ...,
        description="Reference to parent ExecutionGroup (EXG_ prefix)",
    )
    connector_order_id: str | None = Field(
        default=None,
        description="Exchange-assigned order ID (set after submission)",
    )
    symbol: str = Field(
        ...,
        description="Trading pair (e.g., BTC_USDT)",
    )
    side: Literal["BUY", "SELL"] = Field(
        ...,
        description="Order direction",
    )
    order_type: OrderType = Field(
        ...,
        description="Order type (MARKET, LIMIT, STOP_LIMIT)",
    )
    quantity: Decimal = Field(
        ...,
        gt=0,
        description="Order size (must be positive)",
    )
    price: Decimal | None = Field(
        default=None,
        description="Limit price (required for LIMIT orders)",
    )
    stop_price: Decimal | None = Field(
        default=None,
        description="Stop trigger price (required for STOP_LIMIT orders)",
    )
    status: OrderStatus = Field(
        ...,
        description="Order lifecycle status",
    )
    created_at: datetime = Field(
        ...,
        description="Order creation timestamp (UTC)",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp (UTC)",
    )

    model_config = {
        "frozen": False,  # Mutable for status updates
        "extra": "forbid",
        "str_strip_whitespace": True,
        "validate_assignment": True,
        "json_schema_extra": {
            "examples": [
                {
                    "description": "New limit buy order",
                    "order_id": "ORD_20251201_150000_a1b2c3d4",
                    "parent_group_id": "EXG_20251201_145955_xyz789",
                    "connector_order_id": None,
                    "symbol": "BTC_USDT",
                    "side": "BUY",
                    "order_type": "LIMIT",
                    "quantity": "0.5",
                    "price": "95000.00",
                    "stop_price": None,
                    "status": "PENDING",
                    "created_at": "2025-12-01T15:00:00Z",
                    "updated_at": "2025-12-01T15:00:00Z",
                },
                {
                    "description": "Filled market sell order",
                    "order_id": "ORD_20251201_150100_b2c3d4e5",
                    "parent_group_id": "EXG_20251201_150055_abc123",
                    "connector_order_id": "binance_order_12345678",
                    "symbol": "ETH_USDT",
                    "side": "SELL",
                    "order_type": "MARKET",
                    "quantity": "2.0",
                    "price": None,
                    "stop_price": None,
                    "status": "FILLED",
                    "created_at": "2025-12-01T15:01:00Z",
                    "updated_at": "2025-12-01T15:01:02Z",
                },
            ]
        },
    }

    @field_validator("parent_group_id")
    @classmethod
    def validate_parent_group_id_prefix(cls, v: str) -> str:
        """Ensure parent_group_id has EXG_ prefix.

        Args:
            v: Parent group ID value

        Returns:
            Validated parent_group_id

        Raises:
            ValueError: If prefix is not EXG_
        """
        if not v.startswith("EXG_"):
            raise ValueError(
                f"parent_group_id must start with 'EXG_', got: {v[:10]}..."
            )
        return v

    @field_validator("symbol")
    @classmethod
    def validate_symbol_format(cls, v: str) -> str:
        """Ensure symbol matches BASE_QUOTE format.

        Args:
            v: Symbol value

        Returns:
            Validated symbol

        Raises:
            ValueError: If format is invalid
        """
        pattern = r"^[A-Z]+_[A-Z]+$"
        if not match(pattern, v):
            raise ValueError(
                f"symbol must match pattern BASE_QUOTE (e.g., BTC_USDT), got: {v}"
            )
        return v

    @model_validator(mode="after")
    def validate_price_requirements(self) -> "Order":
        """Validate price requirements based on order_type.

        - LIMIT orders require price
        - STOP_LIMIT orders require both price and stop_price
        - MARKET orders don't require price

        Returns:
            Validated Order instance

        Raises:
            ValueError: If price requirements not met
        """
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("LIMIT orders require price to be set")

        if self.order_type == OrderType.STOP_LIMIT:
            if self.price is None:
                raise ValueError("STOP_LIMIT orders require price to be set")
            if self.stop_price is None:
                raise ValueError("STOP_LIMIT orders require stop_price to be set")

        return self

