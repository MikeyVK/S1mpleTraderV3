"""
Unit tests for StrategyDirective DTO.

Tests creation, validation, and edge cases for strategy planning directives.
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives - Pylance can't narrow types after isinstance()

from datetime import datetime, timezone
from decimal import Decimal
from typing import cast

import pytest
from pydantic import ValidationError

from backend.dtos.causality import CausalityChain
from backend.dtos.shared import Origin, OriginType
from backend.dtos.strategy.strategy_directive import (
    StrategyDirective,
    EntryDirective,
    SizeDirective,
    ExitDirective,
    ExecutionDirective,
    DirectiveScope
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

        assert directive.target_plan_ids == []

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
