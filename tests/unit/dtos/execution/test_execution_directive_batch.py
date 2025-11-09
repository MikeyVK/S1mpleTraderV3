"""
Unit tests for ExecutionDirectiveBatch DTO.

STAP 1 RED: Write 15+ FAILING tests based on EXECUTION_DIRECTIVE_BATCH_DESIGN.md
Expected: ALL RED until DTO implementation (STAP 2)

Test Categories:
- Creation Tests (3): minimal, full, with metadata
- Validation Tests (6): batch_id format, empty directives, duplicates, atomic rollback, timeout
- Execution Mode Tests (3): SEQUENTIAL, PARALLEL, ATOMIC
- Immutability Tests (1): frozen model
- Serialization Tests (1): roundtrip
- Edge Cases (1): single directive batch
"""
# pylint: disable=unsubscriptable-object,no-member

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.dtos.causality import CausalityChain
from backend.dtos.shared import Origin, OriginType
from backend.dtos.execution.execution_directive import ExecutionDirective
from backend.dtos.execution.execution_directive_batch import (
    ExecutionDirectiveBatch,
    ExecutionMode
)
from backend.dtos.strategy.entry_plan import EntryPlan


def create_test_origin() -> Origin:
    """Helper to create test Origin instance."""
    return Origin(id="TCK_20251028_143000_test", type=OriginType.TICK)


# Helper function to create minimal ExecutionDirective for testing
def create_test_directive(directive_id: str) -> ExecutionDirective:
    """Create ExecutionDirective with minimal valid fields for testing."""
    causality = CausalityChain(
        origin=create_test_origin(),
        strategy_directive_id="STR_20251028_143010_test"
    )
    # Create minimal EntryPlan (at least 1 plan required)
    entry_plan = EntryPlan(
        symbol="BTCUSDT",
        direction="BUY",
        order_type="MARKET"
    )
    return ExecutionDirective(
        directive_id=directive_id,
        causality=causality,
        entry_plan=entry_plan,
        size_plan=None,
        exit_plan=None,
        execution_plan=None
    )


class TestExecutionDirectiveBatchCreation:
    """Test ExecutionDirectiveBatch creation with various field combinations."""

    def test_create_batch_minimal(self):
        """Test creation with only required fields."""
        directive1 = create_test_directive("EXE_20251028_143020_b7c4d890")
        directive2 = create_test_directive("EXE_20251028_143021_c8e9f123")

        batch = ExecutionDirectiveBatch(
            batch_id="BAT_20251028_143022_a8f3c",
            directives=[directive1, directive2],
            execution_mode=ExecutionMode.SEQUENTIAL,
            created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc)
        )

        assert batch.batch_id == "BAT_20251028_143022_a8f3c"
        assert len(batch.directives) == 2
        assert batch.execution_mode == ExecutionMode.SEQUENTIAL
        assert batch.created_at == datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc)

        # Optional fields should have defaults
        assert batch.rollback_on_failure is True  # Default
        assert batch.timeout_seconds is None
        assert batch.metadata is None

    def test_create_batch_full(self):
        """Test creation with all fields populated."""
        directives = [
            create_test_directive(f"EXE_20251028_14302{i}_test{i}")
            for i in range(3)
        ]

        batch = ExecutionDirectiveBatch(
            batch_id="BAT_20251028_143025_b7c4d",
            directives=directives,
            execution_mode=ExecutionMode.ATOMIC,
            created_at=datetime(2025, 10, 28, 14, 30, 25, tzinfo=timezone.utc),
            rollback_on_failure=True,
            timeout_seconds=30,
            metadata={"reason": "FLASH_CRASH", "risk_threshold": 0.05}
        )

        assert batch.batch_id == "BAT_20251028_143025_b7c4d"
        assert len(batch.directives) == 3
        assert batch.execution_mode == ExecutionMode.ATOMIC
        assert batch.rollback_on_failure is True
        assert batch.timeout_seconds == 30
        assert batch.metadata is not None
        assert batch.metadata["reason"] == "FLASH_CRASH"

    def test_create_batch_with_metadata(self):
        """Test creation with custom metadata."""
        directive = create_test_directive("EXE_20251028_150000_single")

        metadata = {
            "action": "BULK_CANCEL",
            "count": 20,
            "trigger": "USER_REQUEST"
        }

        batch = ExecutionDirectiveBatch(
            batch_id="BAT_20251028_150000_c9e7f",
            directives=[directive],
            execution_mode=ExecutionMode.PARALLEL,
            created_at=datetime(2025, 10, 28, 15, 0, 0, tzinfo=timezone.utc),
            metadata=metadata
        )

        assert batch.metadata is not None
        assert batch.metadata["action"] == "BULK_CANCEL"
        assert batch.metadata["count"] == 20


class TestExecutionDirectiveBatchValidation:
    """Test ExecutionDirectiveBatch validation rules."""

    def test_batch_id_format_validation(self):
        """Test batch_id format validation."""
        directive = create_test_directive("EXE_20251028_143020_b7c4d890")

        # Invalid format should raise ValidationError
        with pytest.raises(ValidationError, match="batch_id must match pattern"):
            ExecutionDirectiveBatch(
                batch_id="INVALID_FORMAT",
                directives=[directive],
                execution_mode=ExecutionMode.SEQUENTIAL,
                created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc)
            )

    def test_empty_directives_rejected(self):
        """Test that empty directives list is rejected."""
        with pytest.raises(ValidationError, match="at least 1 item"):
            ExecutionDirectiveBatch(
                batch_id="BAT_20251028_143022_a8f3c",
                directives=[],  # Empty list - should fail
                execution_mode=ExecutionMode.SEQUENTIAL,
                created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc)
            )

    def test_duplicate_directive_ids_rejected(self):
        """Test that duplicate directive IDs are rejected."""
        # Create 2 directives with SAME ID (invalid)
        directive1 = create_test_directive("EXE_20251028_143020_DUPLICATE")
        directive2 = create_test_directive("EXE_20251028_143020_DUPLICATE")

        with pytest.raises(ValidationError, match="directive_ids must be unique"):
            ExecutionDirectiveBatch(
                batch_id="BAT_20251028_143022_a8f3c",
                directives=[directive1, directive2],
                execution_mode=ExecutionMode.SEQUENTIAL,
                created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc)
            )

    def test_atomic_requires_rollback(self):
        """Test that ATOMIC mode requires rollback_on_failure=True."""
        directive = create_test_directive("EXE_20251028_143020_b7c4d890")

        # ATOMIC mode with rollback_on_failure=False should fail
        with pytest.raises(ValidationError, match="rollback_on_failure must be True for.*ATOMIC"):
            ExecutionDirectiveBatch(
                batch_id="BAT_20251028_143022_a8f3c",
                directives=[directive],
                execution_mode=ExecutionMode.ATOMIC,
                created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc),
                rollback_on_failure=False  # Invalid for ATOMIC
            )

    def test_timeout_positive_validation(self):
        """Test that timeout_seconds must be positive."""
        directive = create_test_directive("EXE_20251028_143020_b7c4d890")

        # Negative timeout should fail
        with pytest.raises(ValidationError, match="timeout_seconds must be positive"):
            ExecutionDirectiveBatch(
                batch_id="BAT_20251028_143022_a8f3c",
                directives=[directive],
                execution_mode=ExecutionMode.SEQUENTIAL,
                created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc),
                timeout_seconds=-10  # Invalid
            )

    def test_zero_timeout_rejected(self):
        """Test that timeout_seconds=0 is rejected."""
        directive = create_test_directive("EXE_20251028_143020_b7c4d890")

        # Zero timeout should fail
        with pytest.raises(ValidationError, match="timeout_seconds must be positive"):
            ExecutionDirectiveBatch(
                batch_id="BAT_20251028_143022_a8f3c",
                directives=[directive],
                execution_mode=ExecutionMode.SEQUENTIAL,
                created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc),
                timeout_seconds=0  # Invalid
            )


class TestExecutionDirectiveBatchExecutionModes:
    """Test different execution mode scenarios."""

    def test_sequential_mode(self):
        """Test SEQUENTIAL execution mode."""
        directives = [
            create_test_directive("EXE_20251028_160001_hedge"),
            create_test_directive("EXE_20251028_160002_close")
        ]

        batch = ExecutionDirectiveBatch(
            batch_id="BAT_20251028_160000_a1b2c3d4",
            directives=directives,
            execution_mode=ExecutionMode.SEQUENTIAL,
            created_at=datetime(2025, 10, 28, 16, 0, 0, tzinfo=timezone.utc),
            rollback_on_failure=False,  # OK for SEQUENTIAL
            metadata={"strategy": "HEDGED_EXIT"}
        )

        assert batch.execution_mode == ExecutionMode.SEQUENTIAL
        assert batch.rollback_on_failure is False
        assert len(batch.directives) == 2

    def test_parallel_mode(self):
        """Test PARALLEL execution mode."""
        directives = [
            create_test_directive(f"EXE_20251028_15000{i}_cancel{i}")
            for i in range(5)
        ]

        batch = ExecutionDirectiveBatch(
            batch_id="BAT_20251028_150000_parallel",
            directives=directives,
            execution_mode=ExecutionMode.PARALLEL,
            created_at=datetime(2025, 10, 28, 15, 0, 0, tzinfo=timezone.utc),
            rollback_on_failure=False,  # Best-effort
            timeout_seconds=10,
            metadata={"action": "BULK_CANCEL", "count": 5}
        )

        assert batch.execution_mode == ExecutionMode.PARALLEL
        assert batch.rollback_on_failure is False
        assert batch.timeout_seconds == 10
        assert len(batch.directives) == 5

    def test_atomic_mode(self):
        """Test ATOMIC execution mode."""
        directives = [
            create_test_directive(f"EXE_20251028_14302{i}_exit{i}")
            for i in range(3)
        ]

        batch = ExecutionDirectiveBatch(
            batch_id="BAT_20251028_143022_atomic",
            directives=directives,
            execution_mode=ExecutionMode.ATOMIC,
            created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc),
            rollback_on_failure=True,  # Required for ATOMIC
            timeout_seconds=30,
            metadata={"reason": "FLASH_CRASH", "trigger_price": 45000}
        )

        assert batch.execution_mode == ExecutionMode.ATOMIC
        assert batch.rollback_on_failure is True
        assert len(batch.directives) == 3


class TestExecutionDirectiveBatchImmutability:
    """Test batch immutability (frozen=True)."""
    # pylint: disable=too-few-public-methods

    def test_batch_immutability(self):
        """Test that batch fields cannot be modified after creation."""
        directive = create_test_directive("EXE_20251028_143020_b7c4d890")

        batch = ExecutionDirectiveBatch(
            batch_id="BAT_20251028_143022_a8f3c",
            directives=[directive],
            execution_mode=ExecutionMode.SEQUENTIAL,
            created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc)
        )

        # Attempt to modify should raise ValidationError (Pydantic frozen model)
        with pytest.raises(ValidationError):
            batch.execution_mode = ExecutionMode.PARALLEL  # type: ignore


class TestExecutionDirectiveBatchSerialization:
    """Test JSON serialization."""
    # pylint: disable=too-few-public-methods

    def test_json_serialization_roundtrip(self):
        """Test model_dump() → model_validate() roundtrip."""
        directives = [
            create_test_directive(f"EXE_20251028_14302{i}_test{i}")
            for i in range(2)
        ]

        original = ExecutionDirectiveBatch(
            batch_id="BAT_20251028_143025_b7c4d",
            directives=directives,
            execution_mode=ExecutionMode.ATOMIC,
            created_at=datetime(2025, 10, 28, 14, 30, 25, tzinfo=timezone.utc),
            rollback_on_failure=True,
            timeout_seconds=30,
            metadata={"reason": "TEST"}
        )

        # Serialize → Deserialize
        dumped = original.model_dump(mode="json")
        restored = ExecutionDirectiveBatch.model_validate(dumped)

        # Verify roundtrip
        assert restored.batch_id == original.batch_id
        assert restored.execution_mode == original.execution_mode
        assert len(restored.directives) == len(original.directives)
        assert restored.rollback_on_failure == original.rollback_on_failure
        assert restored.timeout_seconds == original.timeout_seconds
        assert restored.metadata is not None
        assert restored.metadata["reason"] == "TEST"


class TestExecutionDirectiveBatchEdgeCases:
    """Test edge cases and boundary conditions."""
    # pylint: disable=too-few-public-methods

    def test_single_directive_batch(self):
        """Test batch with only 1 directive (valid - minimum is 1)."""
        directive = create_test_directive("EXE_20251028_143020_single")

        batch = ExecutionDirectiveBatch(
            batch_id="BAT_20251028_143022_single",
            directives=[directive],  # Only 1 directive
            execution_mode=ExecutionMode.SEQUENTIAL,
            created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc)
        )

        assert len(batch.directives) == 1
        assert batch.execution_mode == ExecutionMode.SEQUENTIAL


# Test count: 15 tests total
# - 3 creation tests
# - 6 validation tests
# - 3 execution mode tests
# - 1 immutability test
# - 1 serialization test
# - 1 edge case test
