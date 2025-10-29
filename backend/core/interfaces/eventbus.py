# backend/core/interfaces/eventbus.py
"""
IEventBus Protocol - Platform-wide event system interface.

Defines the contract for the thread-safe event bus singleton that enables
N-to-N communication between strategies and platform services.

@layer: Core (Interfaces)
@dependencies: [typing, pydantic, backend.core.enums]
"""

# Standard Library Imports
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Callable, Optional, Set

# Third-Party Imports
from pydantic import BaseModel


class ScopeLevel(Enum):
    """
    Event scope level.

    Determines visibility and filtering of events across the platform.
    """

    PLATFORM = "platform"  # Platform-wide visibility
    STRATEGY = "strategy"  # Strategy-isolated


@dataclass(frozen=True)
class SubscriptionScope:
    """
    Defines what events a subscription should receive.

    Supports three filtering modes:

    1. **STRATEGY scope** (most restrictive):
       - Receives: Own strategy events + platform events
       - Filters out: Other strategy events

    2. **PLATFORM scope - unrestricted**:
       - target_strategy_ids=None
       - Receives: ALL events (all strategies + platform)
       - Use case: AggregatedLedger, ComplianceValidator

    3. **PLATFORM scope - selective**:
       - target_strategy_ids={specific strategies}
       - Receives: Specified strategy events + platform events
       - Filters out: Other strategy events
       - Use case: DebugMonitor, strategy-specific platform services

    **Examples:**
        >>> # Strategy worker - only own events
        >>> SubscriptionScope(
        ...     level=ScopeLevel.STRATEGY,
        ...     strategy_instance_id="STR_A"
        ... )

        >>> # Platform singleton - all strategies
        >>> SubscriptionScope(
        ...     level=ScopeLevel.PLATFORM,
        ...     target_strategy_ids=None
        ... )

        >>> # Platform singleton - specific strategies only
        >>> SubscriptionScope(
        ...     level=ScopeLevel.PLATFORM,
        ...     target_strategy_ids={"STR_A", "STR_B"}
        ... )

    Attributes:
        level: Base scope level (PLATFORM or STRATEGY)
        strategy_instance_id: Required for STRATEGY level
        target_strategy_ids: Optional filter for PLATFORM level
            - None = unrestricted (all strategies)
            - Set = selective (only specified strategies)
    """

    level: ScopeLevel
    strategy_instance_id: Optional[str] = None
    target_strategy_ids: Optional[Set[str]] = None

    def should_receive_event(
        self,
        publish_scope: ScopeLevel,
        publish_strategy_id: Optional[str]
    ) -> bool:
        """
        Determine if subscription should receive event.

        Filtering Rules:
        - Platform-scoped events → everyone receives
        - Strategy-scoped events:
          - STRATEGY subscription: only own strategy
          - PLATFORM subscription (unrestricted): all strategies
          - PLATFORM subscription (selective): only matching strategies

        Args:
            publish_scope: Scope of published event
            publish_strategy_id: Strategy that published (None for platform)

        Returns:
            True if subscription should receive event

        Examples:
            >>> scope = SubscriptionScope(ScopeLevel.STRATEGY, "STR_A")
            >>> scope.should_receive_event(ScopeLevel.PLATFORM, None)
            True  # Platform events always received

            >>> scope.should_receive_event(ScopeLevel.STRATEGY, "STR_A")
            True  # Own strategy events received

            >>> scope.should_receive_event(ScopeLevel.STRATEGY, "STR_B")
            False  # Other strategy events filtered
        """
        # Platform-scoped events → everyone receives
        if publish_scope == ScopeLevel.PLATFORM:
            return True

        # Strategy-scoped events
        if self.level == ScopeLevel.STRATEGY:
            # Only receive own strategy events
            return self.strategy_instance_id == publish_strategy_id

        if self.level == ScopeLevel.PLATFORM:
            # Unrestricted → receive all
            if self.target_strategy_ids is None:
                return True

            # Selective → only matching strategies
            return publish_strategy_id in self.target_strategy_ids

        return False


class IEventBus(Protocol):
    """
    Thread-safe platform-wide event bus protocol.

    Responsibilities:
    - Event publishing with scope filtering
    - Subscription management with flexible scoping
    - Critical error handling (crash vs log)
    - Thread-safe concurrent access

    Non-Responsibilities:
    - Business logic understanding
    - Component type knowledge (Workers, Operators, etc.)
    - Wiring decisions (handled by EventWiringFactory)

    **Architecture Pattern:**
        Workers are bus-agnostic. They return DispositionEnvelope.
        EventAdapter bridges workers and EventBus.

    **Thread Safety:**
        All methods are thread-safe and can be called concurrently.

    **Error Handling:**
        - is_critical=True handlers: Failure crashes everything
        - is_critical=False handlers: Failure logged, continues
    """

    def publish(
        self,
        event_name: str,
        payload: BaseModel,
        scope: ScopeLevel,
        strategy_instance_id: Optional[str] = None
    ) -> None:
        """
        Broadcast event to matching subscribers.

        Invokes all handlers whose SubscriptionScope.should_receive_event()
        returns True for the given publish scope and strategy ID.

        Args:
            event_name: Event identifier (e.g., "OPPORTUNITY_DETECTED")
            payload: Pydantic DTO (validated contract)
            scope: PLATFORM (all) or STRATEGY (scoped)
            strategy_instance_id: Required if scope=STRATEGY

        Raises:
            CriticalEventHandlerError: If is_critical handler fails
            ValueError: If scope=STRATEGY but strategy_instance_id is None

        Thread-Safety:
            Multiple threads can publish concurrently.
            Handlers are invoked outside the lock to prevent deadlocks.

        Examples:
            >>> # Strategy worker publishes scoped event
            >>> event_bus.publish(
            ...     "OPPORTUNITY_DETECTED",
            ...     OpportunitySignal(...),
            ...     ScopeLevel.STRATEGY,
            ...     strategy_instance_id="STR_A"
            ... )

            >>> # Platform singleton publishes system-wide event
            >>> event_bus.publish(
            ...     "PORTFOLIO_RISK_HIGH",
            ...     RiskAlert(...),
            ...     ScopeLevel.PLATFORM
            ... )
        """
        ...

    def subscribe(
        self,
        event_name: str,
        handler: Callable[[BaseModel], None],
        scope: SubscriptionScope,
        is_critical: bool = False
    ) -> str:
        """
        Register event handler with flexible scoping.

        Creates a subscription that will receive events matching the
        provided SubscriptionScope filtering rules.

        Args:
            event_name: Event to listen for
            handler: Callback function (receives payload)
            scope: Defines filtering behavior:
                - STRATEGY: Own events + platform events
                - PLATFORM (unrestricted): All events
                - PLATFORM (selective): Specific strategies + platform
            is_critical: Error handling mode:
                - True: Handler failure crashes everything
                - False: Handler failure logged, continues

        Returns:
            subscription_id: Unique ID for unsubscribe

        Thread-Safety:
            Can subscribe while events are being published.

        Examples:
            >>> # Strategy worker subscribes to own events
            >>> sub_id = event_bus.subscribe(
            ...     "TICK",
            ...     worker.on_tick,
            ...     SubscriptionScope(
            ...         level=ScopeLevel.STRATEGY,
            ...         strategy_instance_id="STR_A"
            ...     ),
            ...     is_critical=False
            ... )

            >>> # Platform singleton subscribes to all
            >>> sub_id = event_bus.subscribe(
            ...     "LEDGER_STATE_CHANGED",
            ...     aggregated_ledger.on_update,
            ...     SubscriptionScope(
            ...         level=ScopeLevel.PLATFORM,
            ...         target_strategy_ids=None
            ...     ),
            ...     is_critical=True
            ... )
        """
        ...

    def unsubscribe(self, subscription_id: str) -> None:
        """
        Remove subscription.

        Args:
            subscription_id: ID returned from subscribe()

        Raises:
            KeyError: If subscription_id not found

        Thread-Safety:
            Can unsubscribe while events are being published.

        Examples:
            >>> sub_id = event_bus.subscribe(...)
            >>> event_bus.unsubscribe(sub_id)
        """
        ...
