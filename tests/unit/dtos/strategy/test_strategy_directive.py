"""
Unit tests for StrategyDirective DTO.

Tests creation, validation, and edge cases for strategy planning directives.
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
# Suppress Pydantic FieldInfo false positives - Pylance can't narrow types after isinstance()/cast()

from datetime import datetime, timezone
from decimal import Decimal
from typing import cast

import pytest
from pydantic import ValidationError

from backend.core.enums import BatchExecutionMode, DirectiveScope
from backend.dtos.causality import CausalityChain
from backend.dtos.shared import Origin, OriginType
from backend.dtos.strategy.strategy_directive import (
    StrategyDirective,
    EntryDirective,
    SizeDirective,
    ExitDirective,
    ExecutionDirective,
    ExecutionPolicy,
)


def create_test_origin() -> Origin:
    """Helper to create test Origin instance."""
    return Origin(id="TCK_20251026_100000_a1b2c3d4", type=OriginType.TICK)


class TestStrategyDirectiveCreation:
    """Test StrategyDirective instantiation."""

    def test_minimal_new_trade_directive(self):
        """Can create minimal new trade directive with only required fields."""
        directive = StrategyDirective(
            strategy_planner_id="signal_risk_planner_v1",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.75")
        )

        assert directive.strategy_planner_id == "signal_risk_planner_v1"
        assert directive.scope == DirectiveScope.NEW_TRADE
        assert directive.confidence == Decimal("0.75")
        # Auto-generated fields
        directive_id = str(directive.directive_id)
        assert directive_id.startswith("STR_")
        assert isinstance(directive.decision_timestamp, datetime)

    def test_complete_directive_with_all_sub_directives(self):
        """Can create complete directive with all 4 sub-directives."""
        directive = StrategyDirective(
            strategy_planner_id="signal_risk_planner_v1",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.85"),
            entry_directive=EntryDirective(
                symbol="BTCUSDT",
                direction="BUY",
                timing_preference=Decimal("0.8"),
                max_acceptable_slippage=Decimal("0.001")
            ),
            size_directive=SizeDirective(
                aggressiveness=Decimal("0.6"),
                max_risk_amount=Decimal("100.00"),
                account_risk_pct=Decimal("0.02")
            ),
            exit_directive=ExitDirective(
                profit_taking_preference=Decimal("0.7"),
                risk_reward_ratio=Decimal("2.5"),
                stop_loss_tolerance=Decimal("0.015")
            ),
            routing_directive=ExecutionDirective(
                execution_urgency=Decimal("0.9"),
                max_total_slippage_pct=Decimal("0.002")
            )
        )

        assert directive.entry_directive is not None
        assert directive.size_directive is not None
        assert directive.exit_directive is not None
        assert directive.routing_directive is not None
        # Extract values to intermediate variables (Pydantic FieldInfo workaround)
        entry_dir = cast(EntryDirective, directive.entry_directive)
        size_dir = cast(SizeDirective, directive.size_directive)
        assert entry_dir is not None
        assert size_dir is not None
        entry_symbol = str(getattr(entry_dir, "symbol"))
        size_agg = getattr(size_dir, "aggressiveness")
        assert entry_symbol == "BTCUSDT"
        assert size_agg == Decimal("0.6")


class TestStrategyDirectiveValidation:
    """Test StrategyDirective field validation."""

    def test_requires_strategy_planner_id(self):
        """strategy_planner_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            StrategyDirective(
                causality=CausalityChain(origin=create_test_origin()),
                scope=DirectiveScope.NEW_TRADE,
                confidence=Decimal("0.5")
            )
        assert "strategy_planner_id" in str(exc_info.value)

    def test_confidence_must_be_in_range(self):
        """confidence must be between 0.0 and 1.0."""
        with pytest.raises(ValidationError):
            StrategyDirective(
                strategy_planner_id="test_planner",
                causality=CausalityChain(origin=create_test_origin()),
                scope=DirectiveScope.NEW_TRADE,
                confidence=Decimal("1.5")  # Invalid: > 1.0
            )

    def test_scope_must_be_valid_enum(self):
        """scope must be valid DirectiveScope enum."""
        with pytest.raises(ValidationError):
            # Pylance limitation: cannot type narrow string literal for Enum
            StrategyDirective(  # type: ignore[call-overload]
                strategy_planner_id="test_planner",
                causality=CausalityChain(origin=create_test_origin()),
                scope="INVALID_SCOPE",  # type: ignore[arg-type]
                confidence=Decimal("0.5")
            )


class TestStrategyDirectiveDefaultValues:
    """Test StrategyDirective auto-generated and default values."""

    def test_auto_generates_directive_id(self):
        """directive_id is auto-generated with STR_ prefix."""
        directive1 = StrategyDirective(
            strategy_planner_id="test",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.5")
        )
        directive2 = StrategyDirective(
            strategy_planner_id="test",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.5")
        )

        # Check unique directive IDs
        dir1_id = str(directive1.directive_id)
        dir2_id = str(directive2.directive_id)
        assert dir1_id.startswith("STR_")
        assert dir2_id.startswith("STR_")
        assert dir1_id != dir2_id

    def test_auto_sets_decision_timestamp(self):
        """decision_timestamp is auto-set to current UTC time."""
        before = datetime.now(timezone.utc)
        directive = StrategyDirective(
            strategy_planner_id="test",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.5")
        )
        after = datetime.now(timezone.utc)

        assert before <= directive.decision_timestamp <= after
        # Verify timezone-aware datetime
        assert isinstance(directive.decision_timestamp, datetime)
        # Pylance limitation: FieldInfo doesn't narrow to datetime after isinstance()
        # Runtime works perfectly. See agent.md section 6.6.5 "Bekende acceptable warnings #2"
        dt = cast(datetime, directive.decision_timestamp)
        assert getattr(dt, "tzinfo") is not None

    def test_sub_directives_default_to_none(self):
        """All sub-directives are optional and default to None."""
        directive = StrategyDirective(
            strategy_planner_id="test",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.5")
        )

        assert directive.entry_directive is None
        assert directive.size_directive is None
        assert directive.exit_directive is None
        assert directive.routing_directive is None

    def test_target_plan_ids_defaults_to_empty_list(self):
        """target_plan_ids defaults to empty list for NEW_TRADE."""
        directive = StrategyDirective(
            strategy_planner_id="test",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.5")
        )

        assert not directive.target_plan_ids

    def test_causality_enable_journal_causality(self):
        """causality contain all IDs for Journal causality tracking."""
        directive = StrategyDirective(
            strategy_planner_id="test",
            causality=CausalityChain(
                origin=create_test_origin(),
                signal_ids=["SIG_20251026_100001_b2c3d4e5",
                                        "SIG_20251026_100002_c3d4e5f6"],
                risk_ids=["RSK_20251026_100003_d4e5f6a7"]
            ),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.75")
        )

        # CausalityChain enable Journal causality reconstruction
        causality = cast(CausalityChain, directive.causality)
        assert len(getattr(causality, "signal_ids")) == 2
        assert len(getattr(causality, "risk_ids")) == 1


class TestStrategyDirectiveSerialization:
    """Test StrategyDirective serialization."""

    def test_can_serialize_to_dict(self):
        """Can serialize to dict."""
        directive = StrategyDirective(
            strategy_planner_id="test",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.75")
        )

        data = directive.model_dump()
        assert data["strategy_planner_id"] == "test"
        assert data["scope"] == "NEW_TRADE"
        assert "directive_id" in data
        assert "decision_timestamp" in data

    def test_can_serialize_to_json(self):
        """Can serialize to JSON."""
        directive = StrategyDirective(
            strategy_planner_id="test",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.MODIFY_EXISTING,
            target_plan_ids=["TPL_001"],
            confidence=Decimal("0.6")
        )

        json_str = directive.model_dump_json()
        assert "strategy_planner_id" in json_str
        assert "MODIFY_EXISTING" in json_str
        assert "TPL_001" in json_str

    def test_can_deserialize_from_dict(self):
        """Can deserialize from dict."""
        data: dict[str, object] = {
            "strategy_planner_id": "test",
            "causality": {
                "origin": {
                    "id": "TCK_20251026_100000_a1b2c3d4",
                    "type": "TICK"
                },
                "signal_ids": [],
                "risk_ids": []
            },
            "scope": "NEW_TRADE",
            "confidence": "0.5"
        }

        directive = StrategyDirective(**data)  # type: ignore[arg-type]
        assert directive.strategy_planner_id == "test"
        assert directive.scope == DirectiveScope.NEW_TRADE


class TestStrategyDirectiveUseCases:
    """Test StrategyDirective real-world use cases."""

    def test_new_trade_signal(self):
        """New trade directive from signal detection."""
        directive = StrategyDirective(
            strategy_planner_id="signal_risk_momentum_planner",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.85"),
            entry_directive=EntryDirective(
                symbol="BTCUSDT",
                direction="BUY",
                timing_preference=Decimal("0.9"),
                max_acceptable_slippage=Decimal("0.001")
            ),
            size_directive=SizeDirective(
                aggressiveness=Decimal("0.7"),
                max_risk_amount=Decimal("200.00"),
                account_risk_pct=Decimal("0.02")
            )
        )

        assert directive.scope == DirectiveScope.NEW_TRADE
        # Type narrowing: entry_directive is not None here
        entry_dir = cast(EntryDirective, directive.entry_directive)
        assert entry_dir is not None
        assert getattr(entry_dir, "direction") == "BUY"
        assert directive.confidence == Decimal("0.85")

    def test_modify_existing_trade_on_risk(self):
        """Modify existing trade directive from risk signal."""
        directive = StrategyDirective(
            strategy_planner_id="signal_risk_planner",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.MODIFY_EXISTING,
            target_plan_ids=["TPL_12345678_123456_12345678"],
            confidence=Decimal("0.9"),
            exit_directive=ExitDirective(
                profit_taking_preference=Decimal("0.3"),
                risk_reward_ratio=Decimal("1.5"),
                stop_loss_tolerance=Decimal("0.02")
            )
        )

        assert directive.scope == DirectiveScope.MODIFY_EXISTING
        assert len(directive.target_plan_ids) == 1
        assert directive.exit_directive is not None

    def test_close_existing_trade(self):
        """Close existing trade directive."""
        directive = StrategyDirective(
            strategy_planner_id="signal_risk_exit_planner",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.CLOSE_EXISTING,
            target_plan_ids=["TPL_001", "TPL_002"],
            confidence=Decimal("0.95"),
            routing_directive=ExecutionDirective(
                execution_urgency=Decimal("1.0"),
                max_total_slippage_pct=Decimal("0.005")
            )
        )

        assert directive.scope == DirectiveScope.CLOSE_EXISTING
        assert len(directive.target_plan_ids) == 2
        # Type narrowing: routing_directive is not None here
        routing_dir = cast(ExecutionDirective, directive.routing_directive)
        assert routing_dir is not None
        assert getattr(routing_dir, "execution_urgency") == Decimal("1.0")

    def test_partial_directive_for_entry_only(self):
        """Directive with only entry sub-directive (other planners inactive)."""
        directive = StrategyDirective(
            strategy_planner_id="simple_entry_planner",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.6"),
            entry_directive=EntryDirective(
                symbol="ETHUSDT",
                direction="SELL",
                timing_preference=Decimal("0.5")
            )
        )

        assert directive.entry_directive is not None
        assert directive.size_directive is None
        assert directive.exit_directive is None
        assert directive.routing_directive is None


# =============================================================================
# IMMUTABILITY TESTS (TDD: RED phase - frozen=True)
# =============================================================================

class TestStrategyDirectiveImmutability:
    """Test StrategyDirective immutability (frozen=True)."""

    def test_cannot_modify_strategy_planner_id(self):
        """Cannot modify strategy_planner_id after creation."""
        directive = StrategyDirective(
            strategy_planner_id="original_planner",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.5")
        )

        with pytest.raises(ValidationError):
            directive.strategy_planner_id = "modified_planner"

    def test_cannot_modify_scope(self):
        """Cannot modify scope after creation."""
        directive = StrategyDirective(
            strategy_planner_id="test",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.5")
        )

        with pytest.raises(ValidationError):
            directive.scope = DirectiveScope.MODIFY_EXISTING

    def test_cannot_modify_confidence(self):
        """Cannot modify confidence after creation."""
        directive = StrategyDirective(
            strategy_planner_id="test",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.5")
        )

        with pytest.raises(ValidationError):
            directive.confidence = Decimal("0.9")

    def test_cannot_modify_target_plan_ids(self):
        """Cannot modify target_plan_ids after creation."""
        directive = StrategyDirective(
            strategy_planner_id="test",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.MODIFY_EXISTING,
            target_plan_ids=["TPL_001"],
            confidence=Decimal("0.5")
        )

        with pytest.raises(ValidationError):
            directive.target_plan_ids = ["TPL_002"]


# =============================================================================
# EXECUTION POLICY TESTS (TDD: RED phase - new field)
# =============================================================================

class TestExecutionPolicy:
    """Test ExecutionPolicy creation and validation."""

    def test_create_with_defaults(self):
        """Can create ExecutionPolicy with default values."""
        policy = ExecutionPolicy()

        assert policy.mode == BatchExecutionMode.INDEPENDENT
        assert policy.timeout_seconds is None

    def test_create_with_coordinated_mode(self):
        """Can create ExecutionPolicy with COORDINATED mode."""
        policy = ExecutionPolicy(
            mode=BatchExecutionMode.COORDINATED,
            timeout_seconds=30
        )

        assert policy.mode == BatchExecutionMode.COORDINATED
        assert policy.timeout_seconds == 30

    def test_create_with_sequential_mode(self):
        """Can create ExecutionPolicy with SEQUENTIAL mode."""
        policy = ExecutionPolicy(
            mode=BatchExecutionMode.SEQUENTIAL,
            timeout_seconds=60
        )

        assert policy.mode == BatchExecutionMode.SEQUENTIAL
        assert policy.timeout_seconds == 60

    def test_timeout_must_be_positive(self):
        """timeout_seconds must be positive if provided."""
        with pytest.raises(ValidationError):
            ExecutionPolicy(timeout_seconds=0)

        with pytest.raises(ValidationError):
            ExecutionPolicy(timeout_seconds=-10)

    def test_policy_is_immutable(self):
        """ExecutionPolicy is immutable (frozen=True)."""
        policy = ExecutionPolicy()

        with pytest.raises(ValidationError):
            policy.mode = BatchExecutionMode.COORDINATED


class TestStrategyDirectiveExecutionPolicy:
    """Test ExecutionPolicy field in StrategyDirective."""

    def test_execution_policy_defaults_to_none(self):
        """execution_policy defaults to None."""
        directive = StrategyDirective(
            strategy_planner_id="test",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.5")
        )

        assert directive.execution_policy is None

    def test_can_create_with_execution_policy(self):
        """Can create directive with execution_policy."""
        policy = ExecutionPolicy(
            mode=BatchExecutionMode.COORDINATED,
            timeout_seconds=30
        )
        directive = StrategyDirective(
            strategy_planner_id="pair_trade_planner",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.85"),
            execution_policy=policy
        )

        assert directive.execution_policy is not None
        exec_policy = cast(ExecutionPolicy, directive.execution_policy)
        assert getattr(exec_policy, "mode") == BatchExecutionMode.COORDINATED
        assert getattr(exec_policy, "timeout_seconds") == 30

    def test_flash_crash_scenario_with_independent_policy(self):
        """Flash crash uses INDEPENDENT mode (fire all, ignore failures)."""
        directive = StrategyDirective(
            strategy_planner_id="emergency_exit_planner",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.CLOSE_EXISTING,
            target_plan_ids=["TPL_001", "TPL_002", "TPL_003"],
            confidence=Decimal("0.99"),
            execution_policy=ExecutionPolicy(
                mode=BatchExecutionMode.INDEPENDENT
            ),
            routing_directive=ExecutionDirective(
                execution_urgency=Decimal("1.0")
            )
        )

        exec_policy = cast(ExecutionPolicy, directive.execution_policy)
        assert getattr(exec_policy, "mode") == BatchExecutionMode.INDEPENDENT

    def test_pair_trade_scenario_with_coordinated_policy(self):
        """Pair trade uses COORDINATED mode (cancel others on failure)."""
        directive = StrategyDirective(
            strategy_planner_id="pair_trade_planner",
            causality=CausalityChain(origin=create_test_origin()),
            scope=DirectiveScope.NEW_TRADE,
            confidence=Decimal("0.85"),
            execution_policy=ExecutionPolicy(
                mode=BatchExecutionMode.COORDINATED,
                timeout_seconds=30
            )
        )

        exec_policy = cast(ExecutionPolicy, directive.execution_policy)
        assert getattr(exec_policy, "mode") == BatchExecutionMode.COORDINATED
        assert getattr(exec_policy, "timeout_seconds") == 30
