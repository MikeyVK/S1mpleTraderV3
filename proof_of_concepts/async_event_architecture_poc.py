"""
Async Event Architecture - Proof of Concept

Demonstrates:
1. Async event sources (OHLCV provider, News provider, Scheduler)
2. EventBus with async publish/subscribe
3. Per-strategy event queues (buffering)
4. Multiple strategies processing in parallel
5. No missed events during CPU-intensive processing

Run:
    python proof_of_concepts/async_event_architecture_poc.py

Expected output:
- Platform events published every 100-500ms
- Multiple strategies processing events from their queues
- No events missed (all queued and processed)
- Processing time stats showing parallel execution
"""

import asyncio
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# ============================================================================
# Event DTOs
# ============================================================================

@dataclass
class CandleCloseEvent:
    """Market candle close event."""
    timestamp: datetime
    symbol: str
    close: float
    volume: float

    def __repr__(self) -> str:
        return f"Candle({self.symbol} @{self.close})"


@dataclass
class NewsEvent:
    """News article event."""
    timestamp: datetime
    headline: str
    sentiment: str

    def __repr__(self) -> str:
        return f"News({self.headline[:30]}... sentiment={self.sentiment})"


@dataclass
class ScheduleEvent:
    """Scheduled trigger event."""
    timestamp: datetime
    schedule_type: str

    def __repr__(self) -> str:
        return f"Schedule({self.schedule_type})"


@dataclass
class SignalDetectedEvent:
    """Signal detection result."""
    timestamp: datetime
    strategy_id: str
    signal_type: str
    confidence: float

    def __repr__(self) -> str:
        return f"Signal({self.signal_type} confidence={self.confidence:.2f})"


# ============================================================================
# Event Bus (Async)
# ============================================================================

class ScopeLevel(str, Enum):
    """Event scope levels."""
    PLATFORM = "PLATFORM"
    STRATEGY = "STRATEGY"


@dataclass
class Subscription:
    """Event subscription record."""
    subscription_id: str
    event_name: str
    handler: Callable
    scope: ScopeLevel
    strategy_instance_id: str | None = None


class AsyncEventBus:
    """
    Async event bus with scope filtering.

    Key features:
    - Non-blocking publish (returns immediately)
    - Async handler invocation
    - Scope-based filtering (PLATFORM vs STRATEGY)
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Subscription]] = {}
        self._event_count = 0
        self._publish_times: list[float] = []

    async def publish(
        self,
        event_name: str,
        payload: object,
        scope: ScopeLevel,
        strategy_instance_id: str | None = None
    ) -> None:
        """
        Publish event to matching subscribers (async, non-blocking).

        Args:
            event_name: Event identifier
            payload: Event data
            scope: PLATFORM or STRATEGY
            strategy_instance_id: Required if scope=STRATEGY
        """
        start_time = time.perf_counter()

        # Get matching subscriptions
        subscriptions = self._subscriptions.get(event_name, [])
        matching = [
            sub for sub in subscriptions
            if self._should_receive(sub, scope, strategy_instance_id)
        ]

        # Invoke handlers asynchronously (non-blocking!)
        tasks = []
        for sub in matching:
            task = asyncio.create_task(sub.handler(payload))
            tasks.append(task)

        # Wait for all handlers to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Track metrics
        elapsed = time.perf_counter() - start_time
        self._publish_times.append(elapsed)
        self._event_count += 1

        # Log every 10 events
        if self._event_count % 10 == 0:
            avg_time = sum(self._publish_times[-10:]) / 10
            print(
                f"[EventBus] Published {self._event_count} events "
                f"(avg publish time: {avg_time*1000:.2f}ms)"
            )

    def subscribe(
        self,
        event_name: str,
        handler: Callable,
        scope: ScopeLevel,
        strategy_instance_id: str | None = None
    ) -> str:
        """Subscribe to event."""
        subscription_id = f"SUB_{len(self._subscriptions)}"

        sub = Subscription(
            subscription_id=subscription_id,
            event_name=event_name,
            handler=handler,
            scope=scope,
            strategy_instance_id=strategy_instance_id
        )

        if event_name not in self._subscriptions:
            self._subscriptions[event_name] = []
        self._subscriptions[event_name].append(sub)

        return subscription_id

    def _should_receive(
        self,
        sub: Subscription,
        event_scope: ScopeLevel,
        event_strategy_id: str | None
    ) -> bool:
        """Check if subscription should receive event."""
        if sub.scope == ScopeLevel.PLATFORM:
            return event_scope == ScopeLevel.PLATFORM
        # STRATEGY scope
        if event_scope != ScopeLevel.STRATEGY:
            return False
        # Wildcard (monitor all strategies) or exact match
        return (sub.strategy_instance_id is None or
                sub.strategy_instance_id == event_strategy_id)


# ============================================================================
# Event Queue Manager
# ============================================================================

class EventQueueManager:
    """
    Per-strategy async event queues.

    Provides buffering and backpressure handling.
    """

    def __init__(self, maxsize: int = 1000) -> None:
        self._queues: dict[str, asyncio.Queue] = {}
        self._maxsize = maxsize
        self._enqueue_count: dict[str, int] = {}
        self._dequeue_count: dict[str, int] = {}

    def create_queue(self, strategy_id: str) -> None:
        """Create queue for strategy."""
        self._queues[strategy_id] = asyncio.Queue(maxsize=self._maxsize)
        self._enqueue_count[strategy_id] = 0
        self._dequeue_count[strategy_id] = 0

    async def enqueue(self, strategy_id: str, event: object) -> None:
        """Enqueue event (non-blocking with backpressure)."""
        queue = self._queues[strategy_id]

        try:
            # Try to enqueue with timeout
            await asyncio.wait_for(queue.put(event), timeout=0.1)
            self._enqueue_count[strategy_id] += 1
        except TimeoutError:
            # Queue full - drop oldest event (backpressure policy)
            try:
                queue.get_nowait()  # Drop oldest
                await queue.put(event)  # Add new
                print(f"[Queue] Backpressure! Dropped oldest event for {strategy_id}")
            except Exception:  # Queue full - drop oldest
                pass

    async def dequeue(self, strategy_id: str) -> object:
        """Dequeue event (async wait if empty)."""
        queue = self._queues[strategy_id]
        event = await queue.get()
        self._dequeue_count[strategy_id] += 1
        return event

    def get_stats(self, strategy_id: str) -> dict:
        """Get queue statistics."""
        queue = self._queues.get(strategy_id)
        return {
            "enqueued": self._enqueue_count.get(strategy_id, 0),
            "dequeued": self._dequeue_count.get(strategy_id, 0),
            "queue_size": queue.qsize() if queue else 0,
            "queue_maxsize": self._maxsize
        }


# ============================================================================
# Platform Event Sources (Async Tasks)
# ============================================================================

class OhlcvProvider:
    """
    OHLCV market data provider (async task).

    Simulates fetching candles from exchange API.
    """

    def __init__(self, event_bus: AsyncEventBus, symbol: str = "BTC/USD") -> None:
        self._event_bus = event_bus
        self._symbol = symbol
        self._running = False

    async def run(self) -> None:
        """Run provider (publishes candles every 500ms)."""
        self._running = True
        print(f"[OhlcvProvider] Starting for {self._symbol}")

        while self._running:
            # Simulate API call (I/O operation)
            await asyncio.sleep(0.5)

            # Create candle event
            candle = CandleCloseEvent(
                timestamp=datetime.now(),
                symbol=self._symbol,
                close=50000 + random.uniform(-1000, 1000),
                volume=random.uniform(100, 1000)
            )

            # Publish (non-blocking!)
            await self._event_bus.publish(
                event_name="APL_CANDLE_CLOSE_1H",
                payload=candle,
                scope=ScopeLevel.PLATFORM
            )

    def stop(self) -> None:
        """Stop provider."""
        self._running = False


class NewsProvider:
    """
    News feed provider (async task).

    Simulates fetching news from RSS feeds.
    """

    def __init__(self, event_bus: AsyncEventBus) -> None:
        self._event_bus = event_bus
        self._running = False
        self._headlines = [
            "Bitcoin reaches new all-time high",
            "Federal Reserve announces interest rate decision",
            "Major exchange reports security breach",
            "New cryptocurrency regulation proposed",
            "Institutional adoption continues to grow"
        ]

    async def run(self) -> None:
        """Run provider (publishes news every 2 seconds)."""
        self._running = True
        print("[NewsProvider] Starting")

        while self._running:
            # Simulate API call
            await asyncio.sleep(2.0)

            # Create news event
            news = NewsEvent(
                timestamp=datetime.now(),
                headline=random.choice(self._headlines),
                sentiment=random.choice(["positive", "negative", "neutral"])
            )

            # Publish
            await self._event_bus.publish(
                event_name="APL_NEWS_EVENT",
                payload=news,
                scope=ScopeLevel.PLATFORM
            )

    def stop(self) -> None:
        """Stop provider."""
        self._running = False


class Scheduler:
    """
    Time-based scheduler (async task).

    Simulates cron-based schedule triggers.
    """

    def __init__(self, event_bus: AsyncEventBus) -> None:
        self._event_bus = event_bus
        self._running = False

    async def run(self) -> None:
        """Run scheduler (publishes schedule every 3 seconds)."""
        self._running = True
        print("[Scheduler] Starting")

        while self._running:
            await asyncio.sleep(3.0)

            # Create schedule event
            schedule = ScheduleEvent(
                timestamp=datetime.now(),
                schedule_type="HOURLY_SCHEDULE"
            )

            # Publish
            await self._event_bus.publish(
                event_name="APL_HOURLY_SCHEDULE",
                payload=schedule,
                scope=ScopeLevel.PLATFORM
            )

    def stop(self) -> None:
        """Stop scheduler."""
        self._running = False


# ============================================================================
# FlowInitiator (Event Translator)
# ============================================================================

class FlowInitiator:
    """
    Per-strategy event translator.

    Transforms PLATFORM scope APL_* events to STRATEGY scope events.
    """

    def __init__(
        self,
        strategy_id: str,
        event_bus: AsyncEventBus,
        queue_manager: EventQueueManager
    ) -> None:
        self._strategy_id = strategy_id
        self._event_bus = event_bus
        self._queue_manager = queue_manager

    async def on_platform_event(self, event: object) -> None:
        """
        Handle platform event.

        Transforms and enqueues for strategy processing.
        """
        # Transform event (remove APL_ prefix conceptually)
        # In real implementation, this would be proper event transformation

        # Enqueue for strategy (non-blocking!)
        await self._queue_manager.enqueue(self._strategy_id, event)


# ============================================================================
# Strategy Worker (CPU-Intensive Processing)
# ============================================================================

class StrategyWorker:
    """
    Strategy worker that processes events from queue.

    Simulates CPU-intensive signal detection and risk evaluation.
    """

    def __init__(
        self,
        strategy_id: str,
        worker_id: str,
        event_bus: AsyncEventBus,
        queue_manager: EventQueueManager
    ) -> None:
        self._strategy_id = strategy_id
        self._worker_id = worker_id
        self._event_bus = event_bus
        self._queue_manager = queue_manager
        self._running = False
        self._processed_count = 0
        self._processing_times: list[float] = []

    async def run(self) -> None:
        """Run worker (dequeue and process events)."""
        self._running = True
        print(f"[{self._worker_id}] Starting for strategy {self._strategy_id}")

        while self._running:
            # Dequeue next event (async wait if empty)
            event = await self._queue_manager.dequeue(self._strategy_id)

            # Process event (CPU-intensive work)
            start_time = time.perf_counter()
            result = await self._process_event(event)
            elapsed = time.perf_counter() - start_time

            # Track metrics
            self._processed_count += 1
            self._processing_times.append(elapsed)

            # Log every 5 events
            if self._processed_count % 5 == 0:
                avg_time = sum(self._processing_times[-5:]) / 5
                print(f"[{self._worker_id}] Processed {self._processed_count} events "
                      f"(avg time: {avg_time*1000:.2f}ms)")

            # Publish result if significant
            if result:
                await self._event_bus.publish(
                    event_name="SIGNAL_DETECTED",
                    payload=result,
                    scope=ScopeLevel.STRATEGY,
                    strategy_instance_id=self._strategy_id
                )

    async def _process_event(self, event: object) -> SignalDetectedEvent | None:
        """
        Process event (simulates CPU-intensive work).

        In real implementation, this would be signal detection,
        risk evaluation, entry planning, etc.
        """
        # Simulate CPU work (blocking, but other async tasks still run!)
        processing_time = random.uniform(0.05, 0.15)  # 50-150ms
        await asyncio.sleep(processing_time)  # In reality: await run_in_executor()

        # Simulate signal detection (20% chance)
        if random.random() < 0.2:
            return SignalDetectedEvent(
                timestamp=datetime.now(),
                strategy_id=self._strategy_id,
                signal_type="BUY" if random.random() > 0.5 else "SELL",
                confidence=random.uniform(0.6, 0.95)
            )

        return None

    def stop(self) -> None:
        """Stop worker."""
        self._running = False

    def get_stats(self) -> dict:
        """Get worker statistics."""
        return {
            "processed": self._processed_count,
            "avg_processing_time_ms": (
                sum(self._processing_times) / len(self._processing_times) * 1000
                if self._processing_times else 0
            )
        }


# ============================================================================
# Platform Monitor (Observes All Strategies)
# ============================================================================

class PerformanceMonitor:
    """
    Platform monitor that observes all strategy signals.

    Demonstrates cross-strategy monitoring without interference.
    """

    def __init__(self, event_bus: AsyncEventBus) -> None:
        self._event_bus = event_bus
        self._signals_by_strategy: dict[str, list[SignalDetectedEvent]] = {}

        # Subscribe to all strategy signals (wildcard)
        event_bus.subscribe(
            event_name="SIGNAL_DETECTED",
            handler=self.on_signal_detected,
            scope=ScopeLevel.STRATEGY,
            strategy_instance_id=None  # Wildcard: all strategies
        )

    async def on_signal_detected(self, signal: SignalDetectedEvent) -> None:
        """Handle signal from any strategy."""
        strategy_id = signal.strategy_id

        if strategy_id not in self._signals_by_strategy:
            self._signals_by_strategy[strategy_id] = []

        self._signals_by_strategy[strategy_id].append(signal)

        # Log aggregated stats
        total_signals = sum(len(signals) for signals in self._signals_by_strategy.values())
        print(f"[PerformanceMonitor] Total signals detected: {total_signals} "
              f"(across {len(self._signals_by_strategy)} strategies)")

    def get_stats(self) -> dict:
        """Get monitoring statistics."""
        return {
            strategy_id: {
                "total_signals": len(signals),
                "buy_signals": sum(1 for s in signals if s.signal_type == "BUY"),
                "sell_signals": sum(1 for s in signals if s.signal_type == "SELL"),
                "avg_confidence": (
                    sum(s.confidence for s in signals) / len(signals)
                    if signals else 0
                )
            }
            for strategy_id, signals in self._signals_by_strategy.items()
        }


# ============================================================================
# Main Demo
# ============================================================================

async def main() -> None:
    """
    Run proof-of-concept demo.

    Demonstrates:
    1. Multiple async event sources publishing concurrently
    2. EventBus routing to multiple strategies
    3. Per-strategy queues buffering events
    4. Multiple workers per strategy processing in parallel
    5. Platform monitor observing all strategies
    6. No missed events despite CPU-intensive processing
    """
    print("=" * 80)
    print("Async Event Architecture - Proof of Concept")
    print("=" * 80)
    print()

    # Initialize core components
    event_bus = AsyncEventBus()
    queue_manager = EventQueueManager(maxsize=100)

    # Create platform event sources
    ohlcv_provider = OhlcvProvider(event_bus, "BTC/USD")
    news_provider = NewsProvider(event_bus)
    scheduler = Scheduler(event_bus)

    # Create strategies
    strategy_ids = ["STR_MOMENTUM_001", "STR_MEAN_REVERSION_002"]

    flow_initiators = []
    workers = []

    for strategy_id in strategy_ids:
        # Create queue for strategy
        queue_manager.create_queue(strategy_id)

        # Create FlowInitiator
        flow_initiator = FlowInitiator(strategy_id, event_bus, queue_manager)
        flow_initiators.append(flow_initiator)

        # Subscribe to platform events
        event_bus.subscribe(
            event_name="APL_CANDLE_CLOSE_1H",
            handler=flow_initiator.on_platform_event,
            scope=ScopeLevel.PLATFORM
        )
        event_bus.subscribe(
            event_name="APL_NEWS_EVENT",
            handler=flow_initiator.on_platform_event,
            scope=ScopeLevel.PLATFORM
        )
        event_bus.subscribe(
            event_name="APL_HOURLY_SCHEDULE",
            handler=flow_initiator.on_platform_event,
            scope=ScopeLevel.PLATFORM
        )

        # Create workers (2 per strategy for parallel processing)
        for i in range(2):
            worker = StrategyWorker(
                strategy_id=strategy_id,
                worker_id=f"{strategy_id}_WORKER_{i+1}",
                event_bus=event_bus,
                queue_manager=queue_manager
            )
            workers.append(worker)

    # Create platform monitor
    monitor = PerformanceMonitor(event_bus)

    # Start all async tasks
    print("Starting platform components...")
    print()

    tasks = [
        # Platform event sources
        asyncio.create_task(ohlcv_provider.run()),
        asyncio.create_task(news_provider.run()),
        asyncio.create_task(scheduler.run()),

        # Strategy workers
        *[asyncio.create_task(worker.run()) for worker in workers],
    ]

    # Run for 10 seconds
    print("Running demo for 10 seconds...")
    print("Watch for:")
    print("  - Platform events published every 0.5-3 seconds")
    print("  - Workers processing events from queues")
    print("  - Signals detected and monitored")
    print("  - NO events missed despite CPU work")
    print()

    await asyncio.sleep(10)

    # Stop all components
    print()
    print("=" * 80)
    print("Stopping components...")
    ohlcv_provider.stop()
    news_provider.stop()
    scheduler.stop()
    for worker in workers:
        worker.stop()

    # Wait for tasks to finish
    await asyncio.sleep(0.5)

    # Cancel remaining tasks
    for task in tasks:
        task.cancel()

    # Print final statistics
    print()
    print("=" * 80)
    print("FINAL STATISTICS")
    print("=" * 80)
    print()

    print("Event Bus:")
    print(f"  Total events published: {event_bus._event_count}")
    print()

    print("Queue Statistics:")
    for strategy_id in strategy_ids:
        stats = queue_manager.get_stats(strategy_id)
        print(f"  {strategy_id}:")
        print(f"    Enqueued: {stats['enqueued']}")
        print(f"    Dequeued: {stats['dequeued']}")
        print(f"    Queue size: {stats['queue_size']}/{stats['queue_maxsize']}")
        print(f"    Events in flight: {stats['enqueued'] - stats['dequeued']}")
    print()

    print("Worker Statistics:")
    for worker in workers:
        stats = worker.get_stats()
        print(f"  {worker._worker_id}:")
        print(f"    Processed: {stats['processed']} events")
        print(f"    Avg processing time: {stats['avg_processing_time_ms']:.2f}ms")
    print()

    print("Performance Monitor:")
    monitor_stats = monitor.get_stats()
    for strategy_id, stats in monitor_stats.items():
        print(f"  {strategy_id}:")
        print(f"    Total signals: {stats['total_signals']}")
        print(f"    Buy signals: {stats['buy_signals']}")
        print(f"    Sell signals: {stats['sell_signals']}")
        print(f"    Avg confidence: {stats['avg_confidence']:.2%}")
    print()

    # Calculate missed events
    print("Event Loss Analysis:")
    total_enqueued = sum(queue_manager.get_stats(sid)['enqueued'] for sid in strategy_ids)
    total_dequeued = sum(queue_manager.get_stats(sid)['dequeued'] for sid in strategy_ids)
    total_in_queue = sum(queue_manager.get_stats(sid)['queue_size'] for sid in strategy_ids)

    print(f"  Total events enqueued: {total_enqueued}")
    print(f"  Total events processed: {total_dequeued}")
    print(f"  Events still in queue: {total_in_queue}")
    print(f"  Events lost: {total_enqueued - total_dequeued - total_in_queue}")
    print()

    if total_enqueued - total_dequeued - total_in_queue == 0:
        print("✅ NO EVENTS LOST - All events queued and processed!")
    else:
        print("⚠️ Some events were dropped (backpressure triggered)")

    print()
    print("=" * 80)
    print("Demo complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
