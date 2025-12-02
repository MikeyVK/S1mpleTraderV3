# backend/dtos/execution/execution_command.py
"""
ExecutionCommand and ExecutionCommandBatch - Final execution instructions.

DESIGN DECISION: Combined in single file because:
1. Batch is ALWAYS used (even for n=1) - per DTO_ARCHITECTURE.md
2. ExecutionCommand exists only as batch member
3. Single import: `from backend.dtos.execution import ExecutionCommandBatch`

**Clean Execution Contract:**
- No strategy metadata (clean separation between Strategy and Execution layers)
- Complete causality chain with full ID lineage
- At least 1 plan required (supports both NEW_TRADE and MODIFY_EXISTING scenarios)
- All plans Optional (enables partial updates like trailing stops)

@layer: DTOs (Execution)
@dependencies: [
    pydantic, backend.dtos.causality, backend.dtos.strategy.*,
    backend.utils.id_generators, backend.core.enums
]
"""
from datetime import datetime
from re import match
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from backend.core.enums import ExecutionMode
from backend.dtos.causality import CausalityChain
from backend.dtos.strategy import EntryPlan, ExecutionPlan, ExitPlan, SizePlan
from backend.utils.id_generators import generate_batch_id, generate_execution_command_id

if TYPE_CHECKING:
    from typing import Self


class ExecutionCommand(BaseModel):
    """
    Final aggregated execution instruction - always nested in ExecutionCommandBatch.

    Aggregates all planning outputs into single executable command.
    Supports both NEW_TRADE (all plans) and MODIFY_EXISTING (partial plans)
    scenarios.

    **NOT intended for standalone use. Always wrap in ExecutionCommandBatch.**

    **Fields:**
    - command_id: Auto-generated unique identifier (EXC_YYYYMMDD_HHMMSS_hash)
    - causality: Complete ID chain from tick through strategy decision
    - entry_plan: WHERE IN specification (optional - for new trades or additions)
    - size_plan: HOW MUCH specification (optional - for new trades or scaling)
    - exit_plan: WHERE OUT specification (optional - for new trades or adjustments)
    - execution_plan: HOW/WHEN specification (optional - execution trade-offs)

    **Validation:**
    - At least 1 plan required (cannot be empty command)
    - Causality required (full traceability)

    **Use Cases:**
    - NEW_TRADE: All 4 plans present (complete trade setup)
    - MODIFY_EXISTING: Partial plans (e.g., only exit_plan for trailing stop)
    - ADD_TO_POSITION: entry_plan + size_plan only
    """

    command_id: str = Field(
        default_factory=generate_execution_command_id,
        description="Auto-generated unique execution command ID (EXC_YYYYMMDD_HHMMSS_hash)"
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
                    "command_id": "EXC_20251027_143500_a1b2c3d4",
                    "causality": {
                        "origin": {"id": "TCK_20251027_143000_abc123", "type": "TICK"},
                        "signal_ids": ["SIG_20251027_143100_abc456"],
                        "strategy_directive_id": "STR_20251027_143110_def789",
                    },
                    "entry_plan": {
                        "plan_id": "ENT_20251027_143300_ghi012",
                        "symbol": "BTC_USDT",
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
                    "command_id": "EXC_20251027_150000_b2c3d4e5",
                    "causality": {
                        "origin": {"id": "TCK_20251027_145900_xyz789", "type": "TICK"},
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
                    "command_id": "EXC_20251027_152000_c3d4e5f6",
                    "causality": {
                        "origin": {"id": "TCK_20251027_151800_def123", "type": "TICK"},
                        "signal_ids": ["SIG_20251027_151920_ghi678"],
                        "strategy_directive_id": "STR_20251027_151925_jkl012",
                    },
                    "entry_plan": {
                        "plan_id": "ENT_20251027_151955_mno234",
                        "symbol": "ETH_USDT",
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
                "ExecutionCommand must contain at least one plan "
                "(entry_plan, size_plan, exit_plan, or execution_plan)"
            )
        return self


class ExecutionCommandBatch(BaseModel):
    """Atomic execution batch - THE interface to ExecutionWorker.

    ALWAYS USE THIS DTO - even for single command (n=1).
    PlanningAggregator is the ONLY producer.

    IMMUTABILITY CONTRACT:
    - frozen=True (batch integrity during execution)
    - Once created, fields CANNOT be modified
    - If changes needed: Create new batch (don't modify existing)

    Fields:
        batch_id: Unique batch identifier (BAT_YYYYMMDD_HHMMSS_xxxxx)
        commands: List of ExecutionCommands to execute (min 1)
        execution_mode: Execution mode (SEQUENTIAL, PARALLEL, ATOMIC)
        created_at: Batch creation timestamp (UTC)
        rollback_on_failure: Rollback all on any failure (default: True)
        timeout_seconds: Max execution time (None = no timeout)
        metadata: Batch-specific metadata (optional)

    Example:
        >>> batch = ExecutionCommandBatch(
        ...     batch_id="BAT_20251028_143022_a8f3c",
        ...     commands=[command1, command2, command3],
        ...     execution_mode=ExecutionMode.ATOMIC,
        ...     created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc),
        ...     rollback_on_failure=True,
        ...     timeout_seconds=30
        ... )
    """

    model_config = {
        "frozen": True,  # IMMUTABLE - batch integrity during execution
        "json_schema_extra": {
            "examples": [
                {
                    "batch_id": "BAT_20251028_143022_a8f3c",
                    "commands": [
                        {
                            "command_id": "EXC_20251028_143020_1a2b3c4d",
                            "causality": {
                                "origin": {"id": "TCK_20251028_143000_abc123", "type": "TICK"}
                            }
                        },
                        {
                            "command_id": "EXC_20251028_143021_2b3c4d5e",
                            "causality": {
                                "origin": {"id": "TCK_20251028_143001_def456", "type": "TICK"}
                            }
                        },
                        {
                            "command_id": "EXC_20251028_143022_3c4d5e6f",
                            "causality": {
                                "origin": {"id": "TCK_20251028_143002_ghi789", "type": "TICK"}
                            }
                        }
                    ],
                    "execution_mode": "ATOMIC",
                    "created_at": "2025-10-28T14:30:22Z",
                    "rollback_on_failure": True,
                    "timeout_seconds": 30,
                    "metadata": {
                        "reason": "FLASH_CRASH",
                        "trigger_price": 45000,
                        "risk_threshold": 0.05
                    }
                },
                {
                    "batch_id": "BAT_20251028_150000_e3f4g",
                    "commands": [
                        {
                            "command_id": "EXC_20251028_150001_4d5e6f7g",
                            "causality": {
                                "origin": {"id": "TCK_20251028_150000_jkl012", "type": "TICK"}
                            }
                        }
                    ],
                    "execution_mode": "PARALLEL",
                    "created_at": "2025-10-28T15:00:00Z",
                    "rollback_on_failure": False,
                    "timeout_seconds": 10,
                    "metadata": {"action": "BULK_CANCEL", "count": 20}
                },
                {
                    "batch_id": "BAT_20251028_160000_h9i0j",
                    "commands": [
                        {
                            "command_id": "EXC_20251028_160001_5e6f7g8h",
                            "causality": {
                                "origin": {"id": "TCK_20251028_160000_mno345", "type": "TICK"}
                            }
                        },
                        {
                            "command_id": "EXC_20251028_160002_6f7g8h9i",
                            "causality": {
                                "origin": {"id": "TCK_20251028_160001_pqr678", "type": "TICK"}
                            }
                        }
                    ],
                    "execution_mode": "SEQUENTIAL",
                    "created_at": "2025-10-28T16:00:00Z",
                    "rollback_on_failure": False,
                    "timeout_seconds": None,
                    "metadata": {"strategy": "HEDGED_EXIT"}
                }
            ]
        }
    }

    batch_id: str = Field(
        default_factory=generate_batch_id,
        description="Unique batch identifier (BAT_YYYYMMDD_HHMMSS_xxxxx)"
    )
    commands: list[ExecutionCommand] = Field(min_length=1)
    execution_mode: ExecutionMode
    created_at: datetime
    rollback_on_failure: bool = True
    timeout_seconds: int | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("batch_id")
    @classmethod
    def validate_batch_id_format(cls, v: str) -> str:
        """Ensure batch_id matches BAT_YYYYMMDD_HHMMSS_xxxxx format.

        Args:
            v: Batch ID string

        Returns:
            Validated batch ID

        Raises:
            ValueError: If format is invalid
        """
        pattern = r"^BAT_\d{8}_\d{6}_[0-9a-z]{5,8}$"
        if not match(pattern, v):
            raise ValueError(
                f"batch_id must match pattern BAT_YYYYMMDD_HHMMSS_xxxxx, got: {v}"
            )
        return v

    @field_validator("commands")
    @classmethod
    def validate_non_empty_commands(cls, v: list[ExecutionCommand]) -> list[ExecutionCommand]:
        """Ensure commands list is not empty.

        Args:
            v: List of commands

        Returns:
            Validated commands list

        Raises:
            ValueError: If list is empty
        """
        if len(v) == 0:
            raise ValueError(
                "commands list cannot be empty (minimum 1 command required)"
            )
        return v

    @field_validator("commands")
    @classmethod
    def validate_unique_command_ids(
        cls, v: list[ExecutionCommand]
    ) -> list[ExecutionCommand]:
        """Ensure all command IDs are unique within batch.

        Args:
            v: List of commands

        Returns:
            Validated commands list

        Raises:
            ValueError: If duplicate command IDs found
        """
        command_ids = [c.command_id for c in v]
        if len(command_ids) != len(set(command_ids)):
            raise ValueError(
                "All command_ids must be unique within batch (duplicates found)"
            )
        return v

    @field_validator("rollback_on_failure")
    @classmethod
    def validate_atomic_rollback(cls, v: bool, info: ValidationInfo) -> bool:
        """Ensure rollback_on_failure=True for ATOMIC mode.

        Args:
            v: rollback_on_failure value
            info: Validation info (contains other field values)

        Returns:
            Validated rollback_on_failure value

        Raises:
            ValueError: If ATOMIC mode with rollback_on_failure=False
        """
        execution_mode: ExecutionMode | None = info.data.get("execution_mode")
        if execution_mode == ExecutionMode.ATOMIC and not v:
            raise ValueError(
                "rollback_on_failure must be True for ExecutionMode.ATOMIC"
            )
        return v

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout_positive(cls, v: int | None) -> int | None:
        """Ensure timeout_seconds is positive if provided.

        Args:
            v: Timeout in seconds

        Returns:
            Validated timeout value

        Raises:
            ValueError: If timeout <= 0
        """
        if v is not None and v <= 0:
            raise ValueError(f"timeout_seconds must be positive, got: {v}")
        return v
