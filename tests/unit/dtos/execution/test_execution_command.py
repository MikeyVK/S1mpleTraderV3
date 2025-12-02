# tests/unit/dtos/execution/test_execution_command.py
"""
Unit tests for ExecutionCommand DTO - Final execution instruction.

Tests the ExecutionCommand DTO which aggregates all planning outputs
(Entry, Size, Exit, Execution) into single executable command.

**Clean Execution Contract:**
- No strategy metadata (clean separation)
- Causality chain with complete ID lineage
- At least 1 plan required (validation)

@layer: Tests (Unit - Execution DTOs)
@dependencies: [
    pytest, backend.dtos.execution.execution_command,
    backend.dtos.strategy.*, backend.dtos.causality
]
"""

import re
from decimal import Decimal
import pytest

from backend.dtos.causality import CausalityChain
from backend.dtos.shared import Origin, OriginType
from backend.dtos.strategy import (
    EntryPlan,
    SizePlan,
    ExitPlan,
    ExecutionPlan,
)
from backend.dtos.execution.execution_command import ExecutionCommand


def create_test_origin(origin_type: OriginType = OriginType.TICK) -> Origin:
    """Helper function to create test Origin instances."""
    type_map = {
        OriginType.TICK: "TCK_20251027_100000_abc123",
        OriginType.NEWS: "NWS_20251027_100000_def456",
        OriginType.SCHEDULE: "SCH_20251027_100000_ghi789"
    }
    return Origin(id=type_map[origin_type], type=origin_type)


class TestExecutionCommandCreation:
    """Test ExecutionCommand creation with valid data."""

    def test_create_command_all_plans(self):
        """Test creating command with all 4 plans (NEW_TRADE scenario)."""
        causality = CausalityChain(origin=create_test_origin())

        entry = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="LIMIT",
            limit_price=Decimal("100000.00")
        )
        size = SizePlan(
            position_size=Decimal("0.5"),
            position_value=Decimal("50000.00"),
            risk_amount=Decimal("500.00")
        )
        exit_plan = ExitPlan(
            stop_loss_price=Decimal("95000.00"),
            take_profit_price=Decimal("105000.00")
        )
        execution_plan = ExecutionPlan(
            execution_urgency=Decimal("0.80"),
            visibility_preference=Decimal("0.50"),
            max_slippage_pct=Decimal("0.0050"),
            must_complete_immediately=False
        )

        command = ExecutionCommand(
            causality=causality,
            entry_plan=entry,
            size_plan=size,
            exit_plan=exit_plan,
            execution_plan=execution_plan
        )

        assert command.command_id.startswith("EXC_")
        assert command.causality == causality
        assert command.entry_plan == entry
        assert command.size_plan == size
        assert command.exit_plan == exit_plan
        assert command.execution_plan == execution_plan
        # Verify ExecutionPlan fields are preserved
        assert command.execution_plan is not None  # Type narrowing for type checker
        assert command.execution_plan.execution_urgency == Decimal("0.80")
        assert command.execution_plan.visibility_preference == Decimal("0.50")
        assert command.execution_plan.max_slippage_pct == Decimal("0.0050")
        assert command.execution_plan.must_complete_immediately is False

    def test_create_command_partial_plans_modify_scenario(self):
        """Test creating command with partial plans (MODIFY_EXISTING - trailing stop)."""
        causality = CausalityChain(origin=create_test_origin())

        # Only exit plan - trailing stop adjustment
        exit_plan = ExitPlan(
            stop_loss_price=Decimal("98000.00")
        )

        command = ExecutionCommand(
            causality=causality,
            exit_plan=exit_plan
        )

        assert command.command_id.startswith("EXC_")
        assert command.entry_plan is None
        assert command.size_plan is None
        assert command.exit_plan == exit_plan
        assert command.execution_plan is None

    def test_create_command_execution_plan_only(self):
        """Test creating command with ExecutionPlan only (CANCEL_ORDER scenario)."""
        causality = CausalityChain(origin=create_test_origin())

        # Only execution plan - for non-trade actions like CANCEL_ORDER
        execution_plan = ExecutionPlan(
            action="CANCEL_ORDER",
            execution_urgency=Decimal("1.0"),
            visibility_preference=Decimal("0.50"),
            max_slippage_pct=Decimal("0.0"),
            must_complete_immediately=True
        )

        command = ExecutionCommand(
            causality=causality,
            execution_plan=execution_plan
        )

        assert command.command_id.startswith("EXC_")
        assert command.entry_plan is None
        assert command.size_plan is None
        assert command.exit_plan is None
        assert command.execution_plan == execution_plan
        assert command.execution_plan is not None  # Type narrowing
        assert command.execution_plan.action == "CANCEL_ORDER"
        assert command.execution_plan.must_complete_immediately is True

    def test_command_id_auto_generated(self):
        """Test that command_id is auto-generated with correct format."""
        causality = CausalityChain(origin=create_test_origin())
        entry = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET"
        )

        command = ExecutionCommand(
            causality=causality,
            entry_plan=entry
        )

        # EXC_YYYYMMDD_HHMMSS_hash format
        assert command.command_id.startswith("EXC_")
        assert len(command.command_id) == 28


class TestExecutionCommandValidation:
    """Test ExecutionCommand validation rules."""

    def test_at_least_one_plan_required(self):
        """Test that at least one plan is required."""
        causality = CausalityChain(origin=create_test_origin())

        with pytest.raises(ValueError, match="at least one plan"):
            ExecutionCommand(causality=causality)

    def test_causality_required(self):
        """Test that causality is required."""
        entry = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET"
        )

        with pytest.raises(ValueError):
            ExecutionCommand(entry_plan=entry)  # Missing causality

    def test_multiple_plans_combinations_valid(self):
        """Test various valid plan combinations."""
        causality = CausalityChain(origin=create_test_origin())

        entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")
        size = SizePlan(
            position_size=Decimal("0.5"),
            position_value=Decimal("50000"),
            risk_amount=Decimal("500")
        )

        # Entry + Size only
        command1 = ExecutionCommand(causality=causality, entry_plan=entry, size_plan=size)
        assert command1.exit_plan is None

        # Entry only
        command2 = ExecutionCommand(causality=causality, entry_plan=entry)
        assert command2.size_plan is None


class TestExecutionCommandImmutability:
    """Test ExecutionCommand immutability."""

    def test_command_is_frozen(self):
        """Test that ExecutionCommand is immutable after creation."""
        causality = CausalityChain(origin=create_test_origin())
        entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")

        command = ExecutionCommand(causality=causality, entry_plan=entry)

        with pytest.raises(ValueError, match="frozen"):
            command.entry_plan = None  # type: ignore

    def test_no_extra_fields_allowed(self):
        """Test that extra fields are rejected."""
        causality = CausalityChain(origin=create_test_origin())
        entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")

        with pytest.raises(ValueError):
            ExecutionCommand(
                causality=causality,
                entry_plan=entry,
                strategy_metadata="not allowed"  # Extra field
            )


class TestExecutionCommandIdFormat:
    """Test ExecutionCommand command_id format validation."""

    def test_command_id_matches_pattern(self):
        """Test that generated command_id matches EXC_ pattern."""
        causality = CausalityChain(origin=create_test_origin())
        entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")

        command = ExecutionCommand(causality=causality, entry_plan=entry)

        # Should match: EXC_YYYYMMDD_HHMMSS_hash
        pattern = r'^EXC_\d{8}_\d{6}_[0-9a-f]{8}$'
        assert re.match(pattern, command.command_id)

    def test_command_id_uniqueness(self):
        """Test that command_ids are unique across instances."""
        causality = CausalityChain(origin=create_test_origin())
        entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")

        command1 = ExecutionCommand(causality=causality, entry_plan=entry)
        command2 = ExecutionCommand(causality=causality, entry_plan=entry)

        # Same data, but different IDs (hash ensures uniqueness)
        assert command1.command_id != command2.command_id


class TestExecutionCommandCausalityChain:
    """Test ExecutionCommand causality chain handling."""

    def test_causality_preserved(self):
        """Test that causality chain is preserved in command."""
        causality = CausalityChain(
            origin=create_test_origin(),
            signal_ids=["SIG_20251027_100001_def456"],
            strategy_directive_id="STR_20251027_100002_ghi789"
        )
        entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")

        command = ExecutionCommand(causality=causality, entry_plan=entry)

        assert command.causality.origin.id == "TCK_20251027_100000_abc123"
        assert len(command.causality.signal_ids) == 1
        assert command.causality.strategy_directive_id == "STR_20251027_100002_ghi789"
