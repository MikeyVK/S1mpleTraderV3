# tests/unit/core/test_eventbus.py
"""
Unit tests for EventBus singleton implementation.

Tests the concrete thread-safe event bus implementation including
publishing, subscription management, filtering, and error handling.

@layer: Tests (Unit)
@dependencies: [pytest, backend.core.eventbus, backend.core.interfaces.eventbus]
"""

# Standard Library Imports
import threading
import time

# Third-Party Imports
import pytest
from pydantic import BaseModel

# Our Application Imports
from backend.core.eventbus import EventBus, CriticalEventHandlerError
from backend.core.interfaces.eventbus import SubscriptionScope, ScopeLevel


class EventPayloadDTO(BaseModel):
    """Test DTO for event payloads."""

    message: str
    value: int


class TestEventBusInitialization:
    """Test EventBus singleton initialization."""

    def test_create_eventbus(self):
        """Test creating EventBus instance."""
        bus = EventBus()
        assert bus is not None

    def test_eventbus_starts_empty(self):
        """Test that EventBus has no subscriptions initially."""
        bus = EventBus()
        # Should publish without errors (no subscribers)
        bus.publish(
            "TEST_EVENT",
            EventPayloadDTO(message="test", value=1),
            ScopeLevel.PLATFORM
        )


class TestBasicPublishSubscribe:
    """Test basic publish/subscribe functionality."""

    def test_subscribe_and_publish(self):
        """Test basic subscription and event reception."""
        bus = EventBus()
        received_events = []

        def handler(payload):
            received_events.append(payload)

        # Subscribe
        sub_id = bus.subscribe(
            event_name="TEST_EVENT",
            handler=handler,
            scope=SubscriptionScope(
                level=ScopeLevel.PLATFORM,
                target_strategy_ids=None
            )
        )

        assert sub_id is not None

        # Publish
        payload = EventPayloadDTO(message="test", value=42)
        bus.publish("TEST_EVENT", payload, ScopeLevel.PLATFORM)

        # Verify received
        assert len(received_events) == 1
        assert received_events[0] == payload

    def test_unsubscribe_stops_receiving(self):
        """Test that unsubscribe stops handler from receiving events."""
        bus = EventBus()
        received_events = []

        def handler(payload):
            received_events.append(payload)

        # Subscribe and unsubscribe
        sub_id = bus.subscribe(
            "TEST_EVENT",
            handler,
            SubscriptionScope(ScopeLevel.PLATFORM, target_strategy_ids=None)
        )
        bus.unsubscribe(sub_id)

        # Publish after unsubscribe
        bus.publish(
            "TEST_EVENT",
            EventPayloadDTO(message="test", value=1),
            ScopeLevel.PLATFORM
        )

        # Should not receive
        assert len(received_events) == 0

    def test_multiple_subscribers_same_event(self):
        """Test multiple handlers for same event."""
        bus = EventBus()
        received_a = []
        received_b = []

        bus.subscribe(
            "TEST_EVENT",
            received_a.append,
            SubscriptionScope(ScopeLevel.PLATFORM, target_strategy_ids=None)
        )
        bus.subscribe(
            "TEST_EVENT",
            received_b.append,
            SubscriptionScope(ScopeLevel.PLATFORM, target_strategy_ids=None)
        )

        payload = EventPayloadDTO(message="test", value=1)
        bus.publish("TEST_EVENT", payload, ScopeLevel.PLATFORM)

        # Both should receive
        assert len(received_a) == 1
        assert len(received_b) == 1

    def test_different_events_isolated(self):
        """Test that different events are isolated."""
        bus = EventBus()
        received_a = []
        received_b = []

        bus.subscribe(
            "EVENT_A",
            received_a.append,
            SubscriptionScope(ScopeLevel.PLATFORM, target_strategy_ids=None)
        )
        bus.subscribe(
            "EVENT_B",
            received_b.append,
            SubscriptionScope(ScopeLevel.PLATFORM, target_strategy_ids=None)
        )

        # Publish to EVENT_A
        bus.publish(
            "EVENT_A",
            EventPayloadDTO(message="a", value=1),
            ScopeLevel.PLATFORM
        )

        # Only EVENT_A handler should receive
        assert len(received_a) == 1
        assert len(received_b) == 0


class TestStrategyScoping:
    """Test strategy-scoped event filtering."""

    def test_strategy_scope_receives_own_events(self):
        """Test strategy subscriber receives own events."""
        bus = EventBus()
        received = []

        bus.subscribe(
            "TICK",
            received.append,
            SubscriptionScope(
                level=ScopeLevel.STRATEGY,
                strategy_instance_id="STR_A"
            )
        )

        # Publish from STR_A
        bus.publish(
            "TICK",
            EventPayloadDTO(message="tick", value=1),
            ScopeLevel.STRATEGY,
            strategy_instance_id="STR_A"
        )

        assert len(received) == 1

    def test_strategy_scope_filters_other_strategies(self):
        """Test strategy subscriber filters other strategy events."""
        bus = EventBus()
        received = []

        bus.subscribe(
            "TICK",
            received.append,
            SubscriptionScope(
                level=ScopeLevel.STRATEGY,
                strategy_instance_id="STR_A"
            )
        )

        # Publish from STR_B
        bus.publish(
            "TICK",
            EventPayloadDTO(message="tick", value=1),
            ScopeLevel.STRATEGY,
            strategy_instance_id="STR_B"
        )

        # STR_A subscriber should not receive
        assert len(received) == 0

    def test_strategy_scope_receives_platform_events(self):
        """Test strategy subscriber receives platform events."""
        bus = EventBus()
        received = []

        bus.subscribe(
            "RISK_ALERT",
            received.append,
            SubscriptionScope(
                level=ScopeLevel.STRATEGY,
                strategy_instance_id="STR_A"
            )
        )

        # Publish platform event
        bus.publish(
            "RISK_ALERT",
            EventPayloadDTO(message="risk", value=1),
            ScopeLevel.PLATFORM
        )

        # Strategy subscriber should receive platform events
        assert len(received) == 1


class TestPlatformScoping:
    """Test platform-scoped subscription filtering."""

    def test_platform_unrestricted_receives_all_strategies(self):
        """Test unrestricted platform subscriber receives all strategies."""
        bus = EventBus()
        received = []

        bus.subscribe(
            "LEDGER_UPDATE",
            received.append,
            SubscriptionScope(
                level=ScopeLevel.PLATFORM,
                target_strategy_ids=None  # Unrestricted
            )
        )

        # Publish from multiple strategies
        bus.publish(
            "LEDGER_UPDATE",
            EventPayloadDTO(message="a", value=1),
            ScopeLevel.STRATEGY,
            strategy_instance_id="STR_A"
        )
        bus.publish(
            "LEDGER_UPDATE",
            EventPayloadDTO(message="b", value=2),
            ScopeLevel.STRATEGY,
            strategy_instance_id="STR_B"
        )

        # Should receive both
        assert len(received) == 2

    def test_platform_selective_receives_matching_strategies(self):
        """Test selective platform subscriber receives only matching strategies."""
        bus = EventBus()
        received = []

        bus.subscribe(
            "DEBUG_EVENT",
            received.append,
            SubscriptionScope(
                level=ScopeLevel.PLATFORM,
                target_strategy_ids={"STR_A", "STR_C"}
            )
        )

        # Publish from multiple strategies
        bus.publish(
            "DEBUG_EVENT",
            EventPayloadDTO(message="a", value=1),
            ScopeLevel.STRATEGY,
            strategy_instance_id="STR_A"
        )
        bus.publish(
            "DEBUG_EVENT",
            EventPayloadDTO(message="b", value=2),
            ScopeLevel.STRATEGY,
            strategy_instance_id="STR_B"  # Not in target set
        )
        bus.publish(
            "DEBUG_EVENT",
            EventPayloadDTO(message="c", value=3),
            ScopeLevel.STRATEGY,
            strategy_instance_id="STR_C"
        )

        # Should receive STR_A and STR_C, not STR_B
        assert len(received) == 2
        assert received[0].message == "a"
        assert received[1].message == "c"


class TestErrorHandling:
    """Test error handling for critical and non-critical handlers."""

    def test_non_critical_handler_failure_continues(self):
        """Test that non-critical handler failure doesn't stop other handlers."""
        bus = EventBus()
        received = []

        def failing_handler(payload):
            raise ValueError("Handler failed!")

        def success_handler(payload):
            received.append(payload)

        # Subscribe both handlers (non-critical)
        bus.subscribe(
            "TEST_EVENT",
            failing_handler,
            SubscriptionScope(ScopeLevel.PLATFORM, target_strategy_ids=None),
            is_critical=False
        )
        bus.subscribe(
            "TEST_EVENT",
            success_handler,
            SubscriptionScope(ScopeLevel.PLATFORM, target_strategy_ids=None),
            is_critical=False
        )

        # Publish should not crash
        bus.publish(
            "TEST_EVENT",
            EventPayloadDTO(message="test", value=1),
            ScopeLevel.PLATFORM
        )

        # Success handler should still execute
        assert len(received) == 1

    def test_critical_handler_failure_raises(self):
        """Test that critical handler failure raises exception."""
        bus = EventBus()

        def failing_handler(payload):
            raise ValueError("Critical failure!")

        bus.subscribe(
            "TEST_EVENT",
            failing_handler,
            SubscriptionScope(ScopeLevel.PLATFORM, target_strategy_ids=None),
            is_critical=True  # Critical!
        )

        # Should raise CriticalEventHandlerError
        with pytest.raises(CriticalEventHandlerError):
            bus.publish(
                "TEST_EVENT",
                EventPayloadDTO(message="test", value=1),
                ScopeLevel.PLATFORM
            )


class TestThreadSafety:
    """Test thread-safe concurrent operations."""

    def test_concurrent_publish(self):
        """Test multiple threads publishing simultaneously."""
        bus = EventBus()
        received = []
        lock = threading.Lock()

        def handler(payload):
            with lock:
                received.append(payload)

        bus.subscribe(
            "TEST_EVENT",
            handler,
            SubscriptionScope(ScopeLevel.PLATFORM, target_strategy_ids=None)
        )

        # Publish from multiple threads
        def publish_events(thread_id):
            for i in range(10):
                bus.publish(
                    "TEST_EVENT",
                    EventPayloadDTO(message=f"thread_{thread_id}", value=i),
                    ScopeLevel.PLATFORM
                )

        threads = [threading.Thread(target=publish_events, args=(i,))
                   for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All events should be received
        assert len(received) == 50  # 5 threads * 10 events

    def test_concurrent_subscribe_unsubscribe(self):
        """Test subscribing and unsubscribing from multiple threads."""
        bus = EventBus()
        subscription_ids = []
        lock = threading.Lock()

        def subscribe_unsubscribe():
            for _ in range(10):
                sub_id = bus.subscribe(
                    "TEST_EVENT",
                    lambda p: None,
                    SubscriptionScope(ScopeLevel.PLATFORM, target_strategy_ids=None)
                )
                with lock:
                    subscription_ids.append(sub_id)
                time.sleep(0.001)  # Small delay
                bus.unsubscribe(sub_id)

        threads = [threading.Thread(target=subscribe_unsubscribe)
                   for _ in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All subscriptions created successfully
        assert len(subscription_ids) == 30  # 3 threads * 10 subscriptions


class TestSubscriptionIDUniqueness:
    """Test that subscription IDs are unique."""

    def test_subscription_ids_are_unique(self):
        """Test that each subscribe() returns unique ID."""
        bus = EventBus()
        subscription_ids = set()

        for _ in range(100):
            sub_id = bus.subscribe(
                "TEST_EVENT",
                lambda p: None,
                SubscriptionScope(ScopeLevel.PLATFORM, target_strategy_ids=None)
            )
            subscription_ids.add(sub_id)

        # All IDs should be unique
        assert len(subscription_ids) == 100


class TestInvalidOperations:
    """Test error handling for invalid operations."""

    def test_unsubscribe_invalid_id_raises(self):
        """Test that unsubscribing invalid ID raises error."""
        bus = EventBus()

        with pytest.raises(KeyError):
            bus.unsubscribe("INVALID_ID")

    def test_publish_strategy_event_without_id_raises(self):
        """Test that publishing strategy event without ID raises error."""
        bus = EventBus()

        with pytest.raises(ValueError):
            bus.publish(
                "TEST_EVENT",
                EventPayloadDTO(message="test", value=1),
                ScopeLevel.STRATEGY,
                strategy_instance_id=None  # Missing required ID!
            )
