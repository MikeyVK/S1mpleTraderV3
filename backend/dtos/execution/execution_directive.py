# backend/dtos/execution/execution_directive.py
"""
ExecutionDirective - Final aggregated execution instruction.

Aggregates all planning outputs (Entry, Size, Exit, Routing) into a single
executable directive for the ExecutionHandler.

**Clean Execution Contract:**
- No strategy metadata (clean separation between Strategy and Execution layers)
- Complete causality chain with full ID lineage
- At least 1 plan required (supports both NEW_TRADE and MODIFY_EXISTING scenarios)
- All plans Optional (enables partial updates like trailing stops)

@layer: DTOs (Execution)
@dependencies: [pydantic, backend.dtos.causality, backend.dtos.strategy.*, backend.utils.id_generator]
"""

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
from pydantic import BaseModel, Field, model_validator

# Application imports
from backend.dtos.causality import CausalityChain
from backend.dtos.strategy import EntryPlan, SizePlan, ExitPlan, RoutingPlan
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
    - routing_plan: HOW/WHEN specification (optional - for execution control)
    
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
    routing_plan: RoutingPlan | None = None
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
        "str_strip_whitespace": True,
    }
    
    @model_validator(mode="after")
    def validate_at_least_one_plan(self) -> "Self":
        """Validate that at least one plan is present."""
        if not any([
            self.entry_plan,
            self.size_plan,
            self.exit_plan,
            self.routing_plan
        ]):
            raise ValueError(
                "ExecutionDirective must contain at least one plan "
                "(entry_plan, size_plan, exit_plan, or routing_plan)"
            )
        return self
