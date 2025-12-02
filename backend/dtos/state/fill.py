# backend/dtos/state/fill.py
"""
Fill DTO - Exchange execution event tracking.

Represents a single execution event (fill) from an exchange. Part of the
State layer, owned exclusively by StrategyLedger.

**Architectural Role (per TRADE_LIFECYCLE.md):**
- Level 4 container: TradePlan → ExecutionGroup → Order → **Fill**
- Represents **execution reality** (what actually happened)
- May differ from Order (partial fills, price improvement, slippage)

**Immutability Contract:**
- frozen=True (fills are immutable facts from exchange)
- Once created, a Fill never changes - it represents historical execution

**Key Insight:** Fill is REALITY. Order is INTENT. They may differ.

@layer: DTOs (State)
@dependencies: [
    pydantic, backend.utils.id_generators
]
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from backend.utils.id_generators import generate_fill_id


class Fill(BaseModel):
    """
    Exchange execution event tracking.

    Represents a single fill from an exchange. Immutable once created
    as it represents historical execution fact.

    **Fields:**
    - fill_id: Auto-generated unique identifier (FIL_YYYYMMDD_HHMMSS_hash)
    - parent_order_id: Reference to parent Order
    - connector_fill_id: Exchange-assigned fill ID (if provided)
    - filled_quantity: Quantity executed in this fill (always positive)
    - fill_price: Execution price for this fill
    - commission: Trading fee (if provided)
    - commission_asset: Asset used for commission (e.g., "BNB")
    - executed_at: When the exchange executed this fill (UTC)

    **Key Differences from Order:**
    - Order may have multiple Fills (partial fills)
    - Fill price may differ from Order price (slippage, price improvement)
    - Fill is immutable; Order status can change
    """

    fill_id: str = Field(
        default_factory=generate_fill_id,
        description="Auto-generated unique fill ID (FIL_YYYYMMDD_HHMMSS_hash)",
    )
    parent_order_id: str = Field(
        ...,
        description="Reference to parent Order (ORD_ prefix)",
    )
    connector_fill_id: str | None = Field(
        default=None,
        description="Exchange-assigned fill ID (if provided)",
    )
    filled_quantity: Decimal = Field(
        ...,
        gt=0,
        description="Quantity executed in this fill (must be positive)",
    )
    fill_price: Decimal = Field(
        ...,
        gt=0,
        description="Execution price for this fill (must be positive)",
    )
    commission: Decimal | None = Field(
        default=None,
        ge=0,
        description="Trading fee (0 or positive)",
    )
    commission_asset: str | None = Field(
        default=None,
        description="Asset used for commission (e.g., 'BNB', 'USDT')",
    )
    executed_at: datetime = Field(
        ...,
        description="When the exchange executed this fill (UTC)",
    )

    model_config = {
        "frozen": True,  # Immutable - fills are historical facts
        "extra": "forbid",
        "str_strip_whitespace": True,
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Market order fill with commission",
                    "fill_id": "FIL_20251201_150102_a1b2c3d4",
                    "parent_order_id": "ORD_20251201_150100_b2c3d4e5",
                    "connector_fill_id": "binance_fill_987654321",
                    "filled_quantity": "2.0",
                    "fill_price": "3450.25",
                    "commission": "0.003",
                    "commission_asset": "BNB",
                    "executed_at": "2025-12-01T15:01:02Z",
                },
                {
                    "description": "Partial fill (first of many)",
                    "fill_id": "FIL_20251201_151000_c3d4e5f6",
                    "parent_order_id": "ORD_20251201_150955_def123",
                    "connector_fill_id": "binance_fill_111222333",
                    "filled_quantity": "0.2",
                    "fill_price": "95000.50",
                    "commission": "0.00004",
                    "commission_asset": "BTC",
                    "executed_at": "2025-12-01T15:10:00Z",
                },
            ]
        },
    }

    @field_validator("parent_order_id")
    @classmethod
    def validate_parent_order_id_prefix(cls, v: str) -> str:
        """Ensure parent_order_id has ORD_ prefix.

        Args:
            v: Parent order ID value

        Returns:
            Validated parent_order_id

        Raises:
            ValueError: If prefix is not ORD_
        """
        if not v.startswith("ORD_"):
            raise ValueError(
                f"parent_order_id must start with 'ORD_', got: {v[:10]}..."
            )
        return v

