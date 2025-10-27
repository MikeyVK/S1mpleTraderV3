"""
SizePlan DTO - Position Sizing Output.

LEAN SPEC: Represents HOW MUCH (absolute position sizing only).
NO account_risk_pct (was input constraint, not execution output).
NO max_position_value (was planner constraint, not execution param).

Per STRATEGY_PIPELINE_ARCHITECTURE.md:
- SizePlan = pure execution parameters (HOW MUCH)
- Account constraints → SizePlanner worker input, not DTO
- Confidence-driven sizing → worker logic, not DTO fields
"""

# Standard Library Imports
from decimal import Decimal

# Third-Party Imports
from pydantic import BaseModel, Field, field_validator

# Our Application Imports
from backend.utils.id_generators import generate_size_plan_id


class SizePlan(BaseModel):
    """
    Position sizing output from SizePlanner.
    
    LEAN PHILOSOPHY:
    - Contains ONLY absolute sizing values for execution
    - NO account percentages (input constraints, not execution params)
    - NO max limits (planner constraints, not execution values)
    
    SizePlanner workers use account_risk_pct/max_position_value as INPUTS
    to calculate these OUTPUTS (position_size, position_value, risk_amount).
    
    Fields:
        plan_id: Unique identifier (SIZ_YYYYMMDD_HHMMSS_hash)
        position_size: Absolute position size in base asset (e.g., 0.5 BTC)
        position_value: Position value in quote asset (e.g., 50000 USDT)
        risk_amount: Absolute risk in quote asset (e.g., 1000 USDT)
        leverage: Leverage multiplier (default 1.0 = no leverage)
    
    Examples:
        Fixed 1% risk:
        >>> plan = SizePlan(
        ...     position_size=Decimal("0.25"),
        ...     position_value=Decimal("25000.00"),
        ...     risk_amount=Decimal("1000.00")  # 1% of 100k account
        ... )
        
        With leverage:
        >>> plan = SizePlan(
        ...     position_size=Decimal("1.0"),
        ...     position_value=Decimal("100000.00"),
        ...     risk_amount=Decimal("2000.00"),
        ...     leverage=Decimal("2.0")
        ... )
    """

    # Auto-generated ID
    plan_id: str = Field(
        default_factory=generate_size_plan_id,
        description="Unique plan ID (SIZ_YYYYMMDD_HHMMSS_hash)"
    )

    # Position sizing (absolute values)
    position_size: Decimal = Field(
        ...,
        description="Absolute position size in base asset (e.g., 0.5 BTC)",
        gt=0
    )

    position_value: Decimal = Field(
        ...,
        description="Position value in quote asset (e.g., 50000 USDT)",
        gt=0
    )

    risk_amount: Decimal = Field(
        ...,
        description="Absolute risk in quote asset (e.g., 1000 USDT)",
        gt=0
    )

    leverage: Decimal = Field(
        default=Decimal("1.0"),
        description="Leverage multiplier (1.0 = no leverage)",
        ge=1.0
    )

    @field_validator("plan_id")
    @classmethod
    def validate_plan_id(cls, v: str) -> str:
        """Validate plan_id has SIZ_ prefix and correct format."""
        if not v.startswith("SIZ_"):
            raise ValueError("plan_id must start with 'SIZ_'")

        parts = v.split("_")
        if len(parts) != 4:  # SIZ_YYYYMMDD_HHMMSS_hash
            raise ValueError(
                "plan_id must follow format: SIZ_YYYYMMDD_HHMMSS_hash"
            )

        return v

    model_config = {
        "frozen": False,  # Mutable for updates
        "str_strip_whitespace": True,
        "validate_assignment": True,
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Fixed 1% risk sizing (HOW MUCH only)",
                    "plan_id": "SIZ_20251027_143052_a1b2c3d4",
                    "position_size": "0.25",
                    "position_value": "25000.00",
                    "risk_amount": "1000.00",
                    "leverage": "1.0"
                },
                {
                    "description": "Leveraged position (2x)",
                    "plan_id": "SIZ_20251027_143053_e5f6g7h8",
                    "position_size": "1.0",
                    "position_value": "100000.00",
                    "risk_amount": "2000.00",
                    "leverage": "2.0"
                }
            ]
        }
    }
