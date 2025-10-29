# backend/core/eventbus.py
"""
EventBus - Thread-safe platform-wide event system.

Implements the IEventBus protocol with thread-safe N-to-N event communication,
flexible scoping, and critical error handling.

@layer: Core (Singletons)
@dependencies: [threading, logging, uuid, pydantic, backend.core.interfaces.eventbus]
"""

# Standard Library Imports
import logging
import threading
import uuid
from dataclasses import dataclass
from typing import Dict, List, Callable, Optional

# Third-Party Imports
from pydantic import BaseModel

# Our Application Imports
from backend.core.interfaces.eventbus import IEventBus, SubscriptionScope, ScopeLevel

# Configure logging
logger = logging.getLogger(__name__)


class CriticalEventHandlerError(Exception):
    """
    Raised when a critical event handler fails.

    Critical handlers (is_critical=True) are platform singletons whose
    failure should crash the entire system.

    Attributes:
        message: Error description
        original_error: The original exception from handler
        subscription_id: ID of failed subscription
    """

    def __init__(
        self,
        message: str,
        original_error: Exception,
        subscription_id: str
    ):
        super().__init__(message)
        self.original_error = original_error
        self.subscription_id = subscription_id


@dataclass
class Subscription:
    """
    Internal subscription record.

    Attributes:
        subscription_id: Unique identifier
        event_name: Event to listen for
        handler: Callback function
        scope: Filtering rules
        is_critical: Error handling mode
    """

    subscription_id: str
    event_name: str
    handler: Callable[[BaseModel], None]
    scope: SubscriptionScope
    is_critical: bool


class EventBus(IEventBus):
    """
    Thread-safe platform-wide event bus singleton.

    Provides N-to-N event communication with:
    - Flexible scoping (PLATFORM/STRATEGY, selective filtering)
    - Critical error handling (crash vs log)
    - Thread-safe concurrent access (RLock)

    **Usage:**
        >>> bus = EventBus()
        >>> sub_id = bus.subscribe(
        ...     "TICK",
        ...     handler=worker.on_tick,
        ...     scope=SubscriptionScope(
        ...         level=ScopeLevel.STRATEGY,
        ...         strategy_instance_id="STR_A"
        ...     )
        ... )
        >>> bus.publish(
        ...     "TICK",
        ...     payload=TickData(...),
        ...     scope=ScopeLevel.STRATEGY,
        ...     strategy_instance_id="STR_A"
        ... )

    **Thread Safety:**
        All public methods are thread-safe and can be called concurrently.
        Uses RLock (reentrant lock) to prevent deadlocks in event chains.

    **Error Handling:**
        - Non-critical handlers (is_critical=False): Log + continue
        - Critical handlers (is_critical=True): Raise CriticalEventHandlerError
    """

    def __init__(self):
        """Initialize empty event bus with thread lock."""
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._subscription_index: Dict[str, Subscription] = {}
        self._lock = threading.RLock()  # Reentrant lock for nested calls

    def publish(
        self,
        event_name: str,
        payload: BaseModel,
        scope: ScopeLevel,
        strategy_instance_id: Optional[str] = None
    ) -> None:
        """
        Broadcast event to matching subscribers.

        Acquires lock only for reading subscriptions, then releases before
        invoking handlers to prevent deadlocks.

        Args:
            event_name: Event identifier
            payload: Pydantic DTO
            scope: PLATFORM or STRATEGY
            strategy_instance_id: Required if scope=STRATEGY

        Raises:
            ValueError: If scope=STRATEGY but strategy_instance_id is None
            CriticalEventHandlerError: If critical handler fails

        Thread-Safety:
            Multiple threads can publish concurrently
        """
        # Validate strategy_instance_id requirement
        if scope == ScopeLevel.STRATEGY and strategy_instance_id is None:
            raise ValueError(
                "strategy_instance_id is required when scope=STRATEGY"
            )

        # Lock ONLY for reading subscription list
        with self._lock:
            all_subscriptions = self._subscriptions.get(event_name, [])
            matching_subscriptions = [
                sub for sub in all_subscriptions
                if sub.scope.should_receive_event(scope, strategy_instance_id)
            ]

        # Release lock BEFORE invoking handlers (avoid deadlocks)
        for subscription in matching_subscriptions:
            self._invoke_handler(subscription, payload)

    def subscribe(
        self,
        event_name: str,
        handler: Callable[[BaseModel], None],
        scope: SubscriptionScope,
        is_critical: bool = False
    ) -> str:
        """
        Register event handler with flexible scoping.

        Args:
            event_name: Event to listen for
            handler: Callback function
            scope: Filtering rules
            is_critical: Error handling mode

        Returns:
            subscription_id: Unique ID for unsubscribe

        Thread-Safety:
            Can subscribe while events are being published
        """
        with self._lock:
            # Generate unique subscription ID
            subscription_id = f"SUB_{uuid.uuid4().hex[:12].upper()}"

            # Create subscription record
            subscription = Subscription(
                subscription_id=subscription_id,
                event_name=event_name,
                handler=handler,
                scope=scope,
                is_critical=is_critical
            )

            # Add to event index
            if event_name not in self._subscriptions:
                self._subscriptions[event_name] = []
            self._subscriptions[event_name].append(subscription)

            # Add to ID index for fast unsubscribe
            self._subscription_index[subscription_id] = subscription

            return subscription_id

    def unsubscribe(self, subscription_id: str) -> None:
        """
        Remove subscription.

        Args:
            subscription_id: ID returned from subscribe()

        Raises:
            KeyError: If subscription_id not found

        Thread-Safety:
            Can unsubscribe while events are being published
        """
        with self._lock:
            # Look up subscription
            if subscription_id not in self._subscription_index:
                raise KeyError(f"Subscription ID not found: {subscription_id}")

            subscription = self._subscription_index[subscription_id]

            # Remove from event index
            event_subscriptions = self._subscriptions[subscription.event_name]
            event_subscriptions.remove(subscription)

            # Clean up empty event lists
            if not event_subscriptions:
                del self._subscriptions[subscription.event_name]

            # Remove from ID index
            del self._subscription_index[subscription_id]

    def _invoke_handler(
        self,
        subscription: Subscription,
        payload: BaseModel
    ) -> None:
        """
        Invoke subscription handler with error handling.

        Error Handling Rules:
        - is_critical=True (singleton): Crash everything
        - is_critical=False (strategy): Log + continue

        Args:
            subscription: Subscription to invoke
            payload: Event payload

        Raises:
            CriticalEventHandlerError: If critical handler fails
        """
        try:
            subscription.handler(payload)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # We catch all exceptions for handler isolation - we don't know what handlers throw
            if subscription.is_critical:
                # Platform singleton failure = STOP EVERYTHING
                logger.critical(  # pylint: disable=logging-fstring-interpolation
                    f"Critical handler failed for event {subscription.event_name}",
                    exc_info=e,
                    extra={
                        "subscription_id": subscription.subscription_id,
                        "event_name": subscription.event_name,
                        "handler": subscription.handler.__name__
                    }
                )
                raise CriticalEventHandlerError(
                    f"Critical handler failed for event {subscription.event_name}",
                    original_error=e,
                    subscription_id=subscription.subscription_id
                ) from e
            else:
                # Strategy worker failure = LOG + CONTINUE
                strategy_id = subscription.scope.strategy_instance_id
                logger.error(  # pylint: disable=logging-fstring-interpolation
                    f"Handler failed for strategy {strategy_id}",
                    exc_info=e,
                    extra={
                        "subscription_id": subscription.subscription_id,
                        "event_name": subscription.event_name,
                        "strategy_instance_id": strategy_id,
                        "handler": subscription.handler.__name__
                    }
                )
                # Continue to next handler (no raise)
