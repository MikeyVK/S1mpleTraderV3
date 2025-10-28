# backend/dtos/execution/execution_directive.py
"""
ExecutionDirective - Final aggregated execution instruction.

Aggregates all planning outputs (Entry, Size, Exit, Execution) into a single
executable directive for the ExecutionHandler.

**Clean Execution Contract:**
- No strategy metadata (clean separation between Strategy and Execution layers)
- Complete causality chain with full ID lineage
- At least 1 plan required (supports both NEW_TRADE and MODIFY_EXISTING scenarios)
- All plans Optional (enables partial updates like trailing stops)

@layer: DTOs (Execution)
@dependencies: [
    pydantic, backend.dtos.causality, backend.dtos.strategy.*,
    backend.utils.id_generator
]
"""

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
from pydantic import BaseModel, Field, model_validator

# Application imports
from backend.dtos.causality import CausalityChain
from backend.dtos.strategy import EntryPlan, SizePlan, ExitPlan, ExecutionPlan
from backend.utils.id_generators import generate_execution_directive_id

if TYPE_CHECKING:
    from typing_extensions import Self


class ExecutionDirective(BaseModel):
    """
    Final aggregated execution instruction for ExecutionHandler.
    
    Aggregates all planning outputs into single executable directive.
    Supports both NEW_TRADE (all plans) and MODIFY_EXISTING (partial plans)
    scenarios.
    
    **Fields:**
    - directive_id: Auto-generated unique identifier (EXE_YYYYMMDD_HHMMSS_hash)
    - causality: Complete ID chain from tick through strategy decision
    - entry_plan: WHERE IN specification (optional - for new trades or additions)
    - size_plan: HOW MUCH specification (optional - for new trades or scaling)
    - exit_plan: WHERE OUT specification (optional - for new trades or adjustments)
    - execution_plan: HOW/WHEN specification (optional - execution trade-offs)
    
    **Validation:**
    - At least 1 plan required (cannot be empty directive)
    - Causality required (full traceability)
    
    **Use Cases:**
    - NEW_TRADE: All 4 plans present (complete trade setup)
    - MODIFY_EXISTING: Partial plans (e.g., only exit_plan for trailing stop)
    - ADD_TO_POSITION: entry_plan + size_plan only
    """

    directive_id: str = Field(
        default_factory=generate_execution_directive_id,
        description="Auto-generated unique execution directive ID (EXE_YYYYMMDD_HHMMSS_hash)"
    )
    causality: CausalityChain
    entry_plan: EntryPlan | None = None
    size_plan: SizePlan | None = None
    exit_plan: ExitPlan | None = None
    execution_plan: ExecutionPlan | None = None

    model_config = {
        "frozen": True,
        "extra": "forbid",
        "str_strip_whitespace": True,
        "json_schema_extra": {
            "examples": [
                {
                    "description": "NEW_TRADE - Complete setup with all 4 plans",
                    "directive_id": "EXE_20251027_143500_a1b2c3d4",
                    "causality": {
                        "tick_id": "TCK_20251027_143000_xyz123",
                        "opportunity_signal_ids": ["OPP_20251027_143100_abc456"],
                        "strategy_directive_id": "STR_20251027_143200_def789"
                    },
                    "entry_plan": {
                        "plan_id": "ENT_20251027_143300_ghi012",
                        "symbol": "BTCUSDT",
                        "direction": "BUY",
                        "order_type": "LIMIT",
                        "limit_price": "100000.00"
                    },
                    "size_plan": {
                        "plan_id": "SIZ_20251027_143350_jkl345",
                        "position_size": "0.5",
                        "position_value": "50000.00",
                        "risk_amount": "500.00"
                    },
                    "exit_plan": {
                        "plan_id": "EXT_20251027_143400_mno678",
                        "stop_loss_price": "95000.00",
                        "take_profit_price": "105000.00"
                    },
                    "execution_plan": {
                        "plan_id": "EXP_20251027_143450_pqr901",
                        "action": "EXECUTE_TRADE",
                        "execution_urgency": "0.80",
                        "visibility_preference": "0.50",
                        "max_slippage_pct": "0.0050",
                        "must_complete_immediately": False
                    }
                },
                {
                    "description": "MODIFY_EXISTING - Trailing stop adjustment (exit only)",
                    "directive_id": "EXE_20251027_150000_b2c3d4e5",
                    "causality": {
                        "tick_id": "TCK_20251027_145900_xyz789",
                        "strategy_directive_id": "STR_20251027_145950_abc012"
                    },
                    "entry_plan": None,
                    "size_plan": None,
                    "exit_plan": {
                        "plan_id": "EXT_20251027_145955_def345",
                        "stop_loss_price": "98000.00",
                        "take_profit_price": None
                    },
                    "execution_plan": None
                },
                {
                    "description": "ADD_TO_POSITION - Scale in (entry + size only)",
                    "directive_id": "EXE_20251027_152000_c3d4e5f6",
                    "causality": {
                        "tick_id": "TCK_20251027_151900_xyz456",
                        "opportunity_signal_ids": ["OPP_20251027_151920_ghi678"],
                        "strategy_directive_id": "STR_20251027_151950_jkl901"
                    },
                    "entry_plan": {
                        "plan_id": "ENT_20251027_151955_mno234",
                        "symbol": "ETHUSDT",
                        "direction": "BUY",
                        "order_type": "MARKET"
                    },
                    "size_plan": {
                        "plan_id": "SIZ_20251027_151958_pqr567",
                        "position_size": "2.0",
                        "position_value": "7000.00",
                        "risk_amount": "70.00"
                    },
                    "exit_plan": None,
                    "execution_plan": None
                }
            ]
        }
    }

    @model_validator(mode="after")
    def validate_at_least_one_plan(self) -> "Self":
        """Validate that at least one plan is present."""
        if not any([
            self.entry_plan,
            self.size_plan,
            self.exit_plan,
            self.execution_plan
        ]):
            raise ValueError(
                "ExecutionDirective must contain at least one plan "
                "(entry_plan, size_plan, exit_plan, or execution_plan)"
            )
        return self
