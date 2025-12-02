"""ExecutionDirectiveBatch DTO - Atomic multi-directive execution.

ARCHITECTURAL CONTRACT (IMMUTABLE COORDINATOR):
- Coordinates atomic execution of multiple ExecutionDirectives
- IMMUTABLE: frozen=True (batch integrity during execution)
- Single Responsibility: Batch coordination, NOT individual execution
- Validation: Pydantic field_validators enforce business rules

Version: v4.0 (ExecutionIntent Architecture)
Created: 2025-10-28
Design: docs/development/EXECUTION_DIRECTIVE_BATCH_DESIGN.md
Tests: tests/unit/dtos/execution/test_execution_directive_batch.py
"""

from datetime import datetime
from re import match
from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from backend.core.enums import ExecutionMode
from backend.dtos.execution.execution_directive import ExecutionDirective


class ExecutionDirectiveBatch(BaseModel):
    """Atomic execution batch for multiple directives.

    IMMUTABILITY CONTRACT:
    - frozen=True (batch integrity during execution)
    - Once created, fields CANNOT be modified
    - If changes needed: Create new batch (don't modify existing)

    Fields:
        batch_id: Unique batch identifier (BAT_YYYYMMDD_HHMMSS_xxxxx)
        directives: List of ExecutionDirectives to execute (min 1)
        execution_mode: Execution mode (SEQUENTIAL, PARALLEL, ATOMIC)
        created_at: Batch creation timestamp (UTC)
        rollback_on_failure: Rollback all on any failure (default: True)
        timeout_seconds: Max execution time (None = no timeout)
        metadata: Batch-specific metadata (optional)

    Example:
        >>> batch = ExecutionDirectiveBatch(
        ...     batch_id="BAT_20251028_143022_a8f3c",
        ...     directives=[directive1, directive2, directive3],
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
                    "directives": [
                        {"directive_id": "EXE_20251028_143020_1", "causality": None},
                        {"directive_id": "EXE_20251028_143021_2", "causality": None},
                        {"directive_id": "EXE_20251028_143022_3", "causality": None}
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
                    "directives": [
                        {"directive_id": "EXE_20251028_150001_1", "causality": None}
                    ],
                    "execution_mode": "PARALLEL",
                    "created_at": "2025-10-28T15:00:00Z",
                    "rollback_on_failure": False,
                    "timeout_seconds": 10,
                    "metadata": {"action": "BULK_CANCEL", "count": 20}
                },
                {
                    "batch_id": "BAT_20251028_160000_h9i0j",
                    "directives": [
                        {"directive_id": "EXE_20251028_160001_1", "causality": None},
                        {"directive_id": "EXE_20251028_160002_2", "causality": None}
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

    batch_id: str
    directives: list[ExecutionDirective] = Field(min_length=1)
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

    @field_validator("directives")
    @classmethod
    def validate_non_empty_directives(cls, v: list[ExecutionDirective]) -> list[ExecutionDirective]:
        """Ensure directives list is not empty.

        Args:
            v: List of directives

        Returns:
            Validated directives list

        Raises:
            ValueError: If list is empty
        """
        if len(v) == 0:
            raise ValueError(
                "directives list cannot be empty (minimum 1 directive required)"
            )
        return v

    @field_validator("directives")
    @classmethod
    def validate_unique_directive_ids(
        cls, v: list[ExecutionDirective]
    ) -> list[ExecutionDirective]:
        """Ensure all directive IDs are unique within batch.

        Args:
            v: List of directives

        Returns:
            Validated directives list

        Raises:
            ValueError: If duplicate directive IDs found
        """
        directive_ids = [d.directive_id for d in v]
        if len(directive_ids) != len(set(directive_ids)):
            raise ValueError(
                "All directive_ids must be unique within batch (duplicates found)"
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
