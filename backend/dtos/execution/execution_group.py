"""ExecutionGroup DTO - Tracks grouped order execution for advanced strategies.

ARCHITECTURAL CONTRACT (MUTABLE TRACKING ENTITY):
- Tracks lifecycle of multi-order execution strategies (TWAP, ICEBERG, DCA, etc.)
- MUTABLE: status/timestamps/filled_quantity evolve during execution
- IMMUTABLE identifiers: group_id, parent_directive_id never change
- Single Responsibility: Group coordination, NOT individual order management
- Validation: Pydantic field_validators enforce business rules

Version: v4.0 (ExecutionIntent Architecture)
Created: 2025-10-28
Design: docs/development/EXECUTION_GROUP_DESIGN.md
Tests: tests/unit/dtos/execution/test_execution_group.py
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from re import match
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class ExecutionStrategyType(str, Enum):
    """Execution strategy types.

    Values:
        SINGLE: Single order (no grouping needed)
        TWAP: Time-Weighted Average Price
        VWAP: Volume-Weighted Average Price
        ICEBERG: Iceberg order (visible/hidden pairs)
        DCA: Dollar-Cost Averaging
        LAYERED: Layered limit orders
        POV: Percentage of Volume
    """

    SINGLE = "SINGLE"
    TWAP = "TWAP"
    VWAP = "VWAP"
    ICEBERG = "ICEBERG"
    DCA = "DCA"
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


class ExecutionGroup(BaseModel):
    """Tracks grouped order execution for advanced strategies.

    MUTABILITY CONTRACT:
    - frozen=False (status/timestamps/filled_quantity change during execution)
    - Immutable identifiers: group_id, parent_directive_id
    - Timestamps: created_at (always), updated_at (always), cancelled_at/completed_at
      (when applicable)

    Fields:
        group_id: Unique execution group identifier (EXG_YYYYMMDD_HHMMSS_xxxxx)
        parent_directive_id: ExecutionDirective that spawned this group
        execution_strategy: Execution strategy type (TWAP, ICEBERG, DCA, etc.)
        order_ids: List of connector order IDs in this group (unique values)
        status: Current lifecycle status
        created_at: Group creation timestamp (UTC)
        updated_at: Last update timestamp (UTC)
        target_quantity: Planned total quantity for this group (optional)
        filled_quantity: Actual filled quantity so far (optional)
        cancelled_at: Cancellation timestamp (optional)
        completed_at: Completion timestamp (optional)
        metadata: Strategy-specific parameters (optional)

    Example:
        >>> group = ExecutionGroup(
        ...     group_id="EXG_20251028_143022_a8f3c",
        ...     parent_directive_id="EXE_20251028_143020_b7c4d",
        ...     execution_strategy=ExecutionStrategyType.TWAP,
        ...     order_ids=[],
        ...     status=GroupStatus.PENDING,
        ...     created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc),
        ...     updated_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc)
        ... )
    """

    model_config = {
        "frozen": False,  # MUTABLE - status/timestamps/filled_quantity evolve
        "json_schema_extra": {
            "examples": [
                {
                    "group_id": "EXG_20251028_143022_a8f3c",
                    "parent_directive_id": "EXE_20251028_143020_b7c4d",
                    "execution_strategy": "TWAP",
                    "order_ids": [
                        "order_20251028_143025_1",
                        "order_20251028_143325_2",
                        "order_20251028_143625_3",
                        "order_20251028_143925_4",
                        "order_20251028_144225_5"
                    ],
                    "status": "ACTIVE",
                    "created_at": "2025-10-28T14:30:22Z",
                    "updated_at": "2025-10-28T14:39:30Z",
                    "target_quantity": "100.0",
                    "filled_quantity": "40.0",
                    "cancelled_at": None,
                    "completed_at": None,
                    "metadata": {
                        "chunk_size": "20.0",
                        "interval_seconds": 180,
                        "chunks_total": 5
                    }
                },
                {
                    "group_id": "EXG_20251028_150015_b9d2e",
                    "parent_directive_id": "EXE_20251028_150010_c3f1g",
                    "execution_strategy": "ICEBERG",
                    "order_ids": [
                        "order_20251028_150018_1",
                        "order_20251028_150045_2"
                    ],
                    "status": "ACTIVE",
                    "created_at": "2025-10-28T15:00:15Z",
                    "updated_at": "2025-10-28T15:00:50Z",
                    "target_quantity": "500.0",
                    "filled_quantity": "100.0",
                    "cancelled_at": None,
                    "completed_at": None,
                    "metadata": {
                        "visible_size": "100.0",
                        "hidden_size": "400.0",
                        "reveal_threshold": 0.8
                    }
                },
                {
                    "group_id": "EXG_20251028_160000_d4e5f",
                    "parent_directive_id": "EXE_20251028_155955_e6g7h",
                    "execution_strategy": "SINGLE",
                    "order_ids": ["order_20251028_160002_1"],
                    "status": "COMPLETED",
                    "created_at": "2025-10-28T16:00:00Z",
                    "updated_at": "2025-10-28T16:00:05Z",
                    "target_quantity": "50.0",
                    "filled_quantity": "50.0",
                    "cancelled_at": None,
                    "completed_at": "2025-10-28T16:00:05Z",
                    "metadata": None
                }
            ]
        }
    }

    group_id: str
    parent_directive_id: str
    execution_strategy: ExecutionStrategyType
    order_ids: List[str] = Field(default_factory=list)
    status: GroupStatus
    created_at: datetime
    updated_at: datetime
    target_quantity: Optional[Decimal] = None
    filled_quantity: Optional[Decimal] = None
    cancelled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("group_id")
    @classmethod
    def validate_group_id_format(cls, v: str) -> str:
        """Ensure group_id matches EXG_YYYYMMDD_HHMMSS_xxxxx format.

        Args:
            v: Group ID string

        Returns:
            Validated group ID

        Raises:
            ValueError: If format is invalid
        """
        pattern = r"^EXG_\d{8}_\d{6}_[0-9a-z]{5,8}$"
        if not match(pattern, v):
            raise ValueError(
                f"group_id must match pattern EXG_YYYYMMDD_HHMMSS_xxxxx, got: {v}"
            )
        return v

    @field_validator("parent_directive_id")
    @classmethod
    def validate_parent_directive_id_format(cls, v: str) -> str:
        """Ensure parent_directive_id matches EXE_YYYYMMDD_HHMMSS_xxxxx format.

        Args:
            v: Parent directive ID string

        Returns:
            Validated parent directive ID

        Raises:
            ValueError: If format is invalid
        """
        pattern = r"^EXE_\d{8}_\d{6}_[0-9a-z]{5,8}$"
        if not match(pattern, v):
            raise ValueError(
                f"parent_directive_id must match pattern EXE_YYYYMMDD_HHMMSS_xxxxx, got: {v}"
            )
        return v

    @field_validator("order_ids")
    @classmethod
    def validate_unique_order_ids(cls, v: List[str]) -> List[str]:
        """Ensure all order IDs are unique.

        Args:
            v: List of order IDs

        Returns:
            Validated list of unique order IDs

        Raises:
            ValueError: If duplicate order IDs found
        """
        if len(v) != len(set(v)):
            raise ValueError("order_ids must contain unique values (duplicates found)")
        return v

    @field_validator("target_quantity")
    @classmethod
    def validate_target_quantity_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure target_quantity is positive if provided.

        Args:
            v: Target quantity

        Returns:
            Validated target quantity

        Raises:
            ValueError: If target_quantity <= 0
        """
        if v is not None and v <= Decimal("0"):
            raise ValueError(f"target_quantity must be positive, got: {v}")
        return v

    @field_validator("filled_quantity")
    @classmethod
    def validate_fill_ratio(cls, v: Optional[Decimal], info: ValidationInfo) -> Optional[Decimal]:
        """Ensure filled_quantity <= target_quantity (if both present).

        Args:
            v: Filled quantity
            info: Validation info (contains other field values)

        Returns:
            Validated filled quantity

        Raises:
            ValueError: If filled_quantity > target_quantity
        """
        if v is None:
            return v

        target_quantity: Optional[Decimal] = info.data.get("target_quantity")
        if target_quantity is not None and v > target_quantity:
            raise ValueError(
                f"filled_quantity ({v}) cannot exceed target_quantity ({target_quantity})"
            )
        return v

    @field_validator("completed_at")
    @classmethod
    def validate_final_state_xor(
        cls, v: Optional[datetime], info: ValidationInfo
    ) -> Optional[datetime]:
        """Ensure cancelled_at and completed_at are mutually exclusive.

        Args:
            v: completed_at timestamp
            info: Validation info (contains other field values)

        Returns:
            Validated completed_at timestamp

        Raises:
            ValueError: If both cancelled_at and completed_at are set
        """
        cancelled_at: Optional[datetime] = info.data.get("cancelled_at")

        if cancelled_at is not None and v is not None:
            raise ValueError(
                "cancelled_at and completed_at are mutually exclusive "
                "(group cannot be both cancelled and completed)"
            )
        return v
