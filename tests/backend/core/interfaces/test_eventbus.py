# tests/unit/core/interfaces/test_eventbus.py
"""
Unit tests for IEventBus Protocol and SubscriptionScope.

Tests the event bus interface definition, scope filtering logic,
and protocol compliance.

@layer: Tests (Unit)
@dependencies: [pytest, backend.core.interfaces.eventbus]
"""

# Standard library
# (none)

# Third-party
import pytest

# Project modules
from backend.core.interfaces.eventbus import (
    IEventBus,
    ScopeLevel,
    SubscriptionScope,
)


class TestSubscriptionScopeCreation:
    """Test SubscriptionScope instantiation."""

    def test_create_strategy_scope(self):
        """Test creating strategy-level scope."""
        scope = SubscriptionScope(level=ScopeLevel.STRATEGY, strategy_instance_id="STR_A")

        assert scope.level == ScopeLevel.STRATEGY
        assert scope.strategy_instance_id == "STR_A"
        assert scope.target_strategy_ids is None

    def test_create_platform_scope_unrestricted(self):
        """Test creating unrestricted platform scope."""
        scope = SubscriptionScope(level=ScopeLevel.PLATFORM, target_strategy_ids=None)

        assert scope.level == ScopeLevel.PLATFORM
        assert scope.strategy_instance_id is None
        assert scope.target_strategy_ids is None

    def test_create_platform_scope_selective(self):
        """Test creating selective platform scope."""
        target_ids = {"STR_A", "STR_C"}
        scope = SubscriptionScope(level=ScopeLevel.PLATFORM, target_strategy_ids=target_ids)

        assert scope.level == ScopeLevel.PLATFORM
        assert scope.target_strategy_ids == target_ids

    def test_subscription_scope_is_frozen(self):
        """Test that SubscriptionScope is immutable."""
        scope = SubscriptionScope(level=ScopeLevel.STRATEGY, strategy_instance_id="STR_A")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            scope.level = ScopeLevel.PLATFORM


class TestSubscriptionScopeFiltering:
    """Test SubscriptionScope.should_receive_event() logic."""

    def test_strategy_scope_receives_platform_events(self):
        """Test that strategy scope receives platform events."""
        scope = SubscriptionScope(level=ScopeLevel.STRATEGY, strategy_instance_id="STR_A")

        # Platform event → should receive
        assert scope.should_receive_event(ScopeLevel.PLATFORM, None) is True

    def test_strategy_scope_receives_own_events(self):
        """Test that strategy scope receives own strategy events."""
        scope = SubscriptionScope(level=ScopeLevel.STRATEGY, strategy_instance_id="STR_A")

        # Own strategy event → should receive
        assert scope.should_receive_event(ScopeLevel.STRATEGY, "STR_A") is True

    def test_strategy_scope_filters_other_strategy_events(self):
        """Test that strategy scope filters other strategy events."""
        scope = SubscriptionScope(level=ScopeLevel.STRATEGY, strategy_instance_id="STR_A")

        # Other strategy event → should filter
        assert scope.should_receive_event(ScopeLevel.STRATEGY, "STR_B") is False

    def test_platform_unrestricted_receives_all(self):
        """Test that unrestricted platform scope receives all events."""
        scope = SubscriptionScope(level=ScopeLevel.PLATFORM, target_strategy_ids=None)

        # Platform event → should receive
        assert scope.should_receive_event(ScopeLevel.PLATFORM, None) is True

        # Any strategy event → should receive
        assert scope.should_receive_event(ScopeLevel.STRATEGY, "STR_A") is True
        assert scope.should_receive_event(ScopeLevel.STRATEGY, "STR_B") is True

    def test_platform_selective_receives_matching_strategies(self):
        """Test that selective platform scope receives only matching strategies."""
        scope = SubscriptionScope(level=ScopeLevel.PLATFORM, target_strategy_ids={"STR_A", "STR_C"})

        # Platform event → should receive
        assert scope.should_receive_event(ScopeLevel.PLATFORM, None) is True

        # Matching strategy events → should receive
        assert scope.should_receive_event(ScopeLevel.STRATEGY, "STR_A") is True
        assert scope.should_receive_event(ScopeLevel.STRATEGY, "STR_C") is True

        # Non-matching strategy events → should filter
        assert scope.should_receive_event(ScopeLevel.STRATEGY, "STR_B") is False
        assert scope.should_receive_event(ScopeLevel.STRATEGY, "STR_D") is False

    def test_platform_selective_empty_set_filters_all_strategies(self):
        """Test that empty target set filters all strategy events."""
        scope = SubscriptionScope(
            level=ScopeLevel.PLATFORM,
            target_strategy_ids=set(),  # Empty set
        )

        # Platform event → should receive
        assert scope.should_receive_event(ScopeLevel.PLATFORM, None) is True

        # Strategy events with empty filter → should filter all
        assert scope.should_receive_event(ScopeLevel.STRATEGY, "STR_A") is False


class TestScopeLevelEnum:
    """Test ScopeLevel enum values."""

    def test_scope_level_values(self):
        """Test that ScopeLevel has correct values."""
        assert ScopeLevel.PLATFORM.value == "platform"
        assert ScopeLevel.STRATEGY.value == "strategy"

    def test_scope_level_comparison(self):
        """Test ScopeLevel enum comparison."""
        assert ScopeLevel.PLATFORM == ScopeLevel.PLATFORM
        assert ScopeLevel.STRATEGY == ScopeLevel.STRATEGY
        assert ScopeLevel.PLATFORM != ScopeLevel.STRATEGY


class TestIEventBusProtocol:
    """Test IEventBus protocol compliance (interface only)."""

    def test_protocol_has_publish_method(self):
        """Test that IEventBus protocol defines publish method."""
        assert hasattr(IEventBus, "publish")

    def test_protocol_has_subscribe_method(self):
        """Test that IEventBus protocol defines subscribe method."""
        assert hasattr(IEventBus, "subscribe")

    def test_protocol_has_unsubscribe_method(self):
        """Test that IEventBus protocol defines unsubscribe method."""
        assert hasattr(IEventBus, "unsubscribe")
