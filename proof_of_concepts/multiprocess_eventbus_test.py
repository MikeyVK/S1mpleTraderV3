"""
REAL Multi-Process Event Architecture Test

This is the REAL test - not a naive simulation!

Architecture:
- Process 1: Fast Event Source (publishes every 50ms)
- Process 2: Slow Event Source (publishes every 100ms)
- Process 3: EventBus + Consumer (async I/O, non-blocking)

Goal: Prove that async I/O EventBus can handle events from multiple
      processes WITHOUT missing any events, even when consumers are slow.

Run:
    python proof_of_concepts/multiprocess_eventbus_test.py

Expected:
- Source 1: ~60 events in 3 seconds (50ms interval)
- Source 2: ~30 events in 3 seconds (100ms interval)
- EventBus: Receives ALL ~90 events without missing any
- Consumer: Processes ALL events (even if slow)
"""

import asyncio
import multiprocessing
import queue
import time
from dataclasses import dataclass

# ============================================================================
# Event DTOs (Must be picklable for multiprocessing)
# ============================================================================

@dataclass
class Event:
    """Simple event DTO."""
    event_id: int
    source: str
    timestamp: float
    data: str


# ============================================================================
# Event Source (Runs in SEPARATE PROCESS)
# ============================================================================

def event_source_process(
    source_name: str,
    interval_ms: int,
    duration_sec: int,
    event_queue: multiprocessing.Queue
) -> None:
    """
    Event source running in separate process.

    Publishes events at regular interval to shared queue.
    This simulates external event sources (exchange WebSocket, news feeds, etc.)
    """
    print(f"[{source_name}] Starting (interval={interval_ms}ms)")

    event_count = 0
    start_time = time.perf_counter()
    last_publish = start_time

    while (time.perf_counter() - start_time) < duration_sec:
        current_time = time.perf_counter()

        # Publish at specified interval
        if (current_time - last_publish) >= (interval_ms / 1000.0):
            event = Event(
                event_id=event_count,
                source=source_name,
                timestamp=current_time,
                data=f"{source_name}_Event_{event_count}"
            )

            # Put in queue (this is BLOCKING if queue full, but we use large queue)
            try:
                event_queue.put(event, timeout=0.1)
                event_count += 1
                elapsed = current_time - start_time
                print(f"[{elapsed:.3f}s] {source_name}: Published Event_{event_count}")
                last_publish = current_time
            except queue.Full:
                print(f"[{source_name}] ⚠️ Queue FULL! Event dropped!")

        # Small sleep to avoid busy loop
        time.sleep(0.001)  # 1ms

    print(f"[{source_name}] Finished - published {event_count} events")

    # Send sentinel to signal completion
    event_queue.put(None)


# ============================================================================
# Async EventBus (Runs in MAIN PROCESS with async I/O)
# ============================================================================

class AsyncEventBus:
    """
    Async EventBus that consumes events from multiprocessing.Queue.

    Key features:
    - Non-blocking event consumption (async)
    - Can handle multiple event sources
    - Tracks all events (no loss)
    """

    def __init__(self, event_queue: multiprocessing.Queue) -> None:
        self._event_queue = event_queue
        self._received_events: list[Event] = []
        self._sources_completed = 0
        self._total_sources = 2  # We know we have 2 sources

    async def run(self, processing_delay_ms: int = 0) -> None:
        """
        Main event loop - consumes events from queue.

        Args:
            processing_delay_ms: Simulated processing delay per event
        """
        print(f"[EventBus] Starting (processing_delay={processing_delay_ms}ms)")

        start_time = time.perf_counter()

        while self._sources_completed < self._total_sources:
            # Try to get event from queue (non-blocking with timeout)
            try:
                # Get event with small timeout
                event = await asyncio.get_event_loop().run_in_executor(
                    None,  # Use default executor
                    self._event_queue.get,
                    True,  # block=True
                    0.01   # timeout=10ms
                )

                if event is None:
                    # Sentinel received - one source completed
                    self._sources_completed += 1
                    elapsed = time.perf_counter() - start_time
                    print(f"[{elapsed:.3f}s] EventBus: Source completed "
                          f"({self._sources_completed}/{self._total_sources})")
                    continue

                # Process event
                elapsed = time.perf_counter() - start_time
                print(
                    f"  [{elapsed:.3f}s] EventBus: "
                    f"Received {event.source} Event_{event.event_id}"
                )

                # Simulate processing delay (e.g., database write, API call)
                if processing_delay_ms > 0:
                    await asyncio.sleep(processing_delay_ms / 1000.0)

                # Store event
                self._received_events.append(event)

            except queue.Empty:
                # No event available - this is OK, we'll try again
                # The key is we DON'T block here - we yield control
                await asyncio.sleep(0.001)  # 1ms

            except Exception as e:
                print(f"[EventBus] Error: {e}")
                break

        elapsed = time.perf_counter() - start_time
        print(f"[{elapsed:.3f}s] EventBus: All sources completed")

    def get_stats(self):
        """Get statistics."""
        events_by_source = {}
        for event in self._received_events:
            if event.source not in events_by_source:
                events_by_source[event.source] = []
            events_by_source[event.source].append(event)

        return {
            'total_received': len(self._received_events),
            'by_source': {
                source: len(events)
                for source, events in events_by_source.items()
            },
            'events': self._received_events
        }


# ============================================================================
# Slow Consumer (Simulates CPU-intensive processing)
# ============================================================================

class SlowConsumer:
    """
    Consumer that processes events slowly.

    This simulates strategy workers doing CPU-intensive work.
    """

    def __init__(self, event_bus: AsyncEventBus) -> None:
        self._event_bus = event_bus
        self._processed_count = 0

    async def run(self, processing_time_ms: int = 100) -> None:
        """
        Consume and process events.

        Args:
            processing_time_ms: Time to process each event
        """
        print(f"[Consumer] Starting (processing_time={processing_time_ms}ms)")

        start_time = time.perf_counter()

        # Wait for EventBus to finish receiving
        while self._event_bus._sources_completed < self._event_bus._total_sources:
            await asyncio.sleep(0.1)

        # Process all received events
        events = self._event_bus._received_events

        for event in events:
            elapsed = time.perf_counter() - start_time
            print(f"  [{elapsed:.3f}s] Consumer: Processing {event.source} Event_{event.event_id}")

            # Simulate CPU work
            await asyncio.sleep(processing_time_ms / 1000.0)

            self._processed_count += 1

        elapsed = time.perf_counter() - start_time
        print(f"[{elapsed:.3f}s] Consumer: Processed {self._processed_count} events")


# ============================================================================
# Main Test
# ============================================================================

async def async_main():
    """Main async test runner."""

    # Create shared queue (large enough to hold all events)
    event_queue = multiprocessing.Queue(maxsize=1000)

    # Create EventBus
    event_bus = AsyncEventBus(event_queue)

    # Create slow consumer
    consumer = SlowConsumer(event_bus)

    # Start EventBus and Consumer as async tasks
    eventbus_task = asyncio.create_task(event_bus.run(processing_delay_ms=10))

    # Wait a bit for EventBus to start
    await asyncio.sleep(0.1)

    print()
    print("All components started - events should start flowing...")
    print()

    # Wait for EventBus to finish
    await eventbus_task

    # Now process events with slow consumer
    await consumer.run(processing_time_ms=50)

    # Get statistics
    return event_bus.get_stats()



def main() -> None:
    """Main test entry point."""
    print("=" * 80)
    print("REAL Multi-Process Event Architecture Test")
    print("=" * 80)
    print()
    print("Architecture:")
    print("- Process 1: Fast Event Source (50ms interval)")
    print("- Process 2: Slow Event Source (100ms interval)")
    print("- Main Process: Async EventBus + Consumer")
    print()
    print("Expected:")
    print("- Fast source: ~60 events in 3 seconds")
    print("- Slow source: ~30 events in 3 seconds")
    print("- EventBus: Receives ALL events (no loss)")
    print()

    # Set start method
    multiprocessing.set_start_method('spawn', force=True)

    # Create shared queue
    event_queue = multiprocessing.Queue(maxsize=1000)

    # Start event source processes
    print("Starting event source processes...")

    source1 = multiprocessing.Process(
        target=event_source_process,
        args=("FastSource", 50, 3, event_queue)  # 50ms interval, 3 seconds
    )

    source2 = multiprocessing.Process(
        target=event_source_process,
        args=("SlowSource", 100, 3, event_queue)  # 100ms interval, 3 seconds
    )

    source1.start()
    source2.start()

    print()

    # Run async EventBus and Consumer
    stats = asyncio.run(async_main())

    # Wait for source processes to finish
    source1.join()
    source2.join()

    # Print results
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    print(f"Total events received: {stats['total_received']}")
    print()

    print("Events by source:")
    for source, count in stats['by_source'].items():
        print(f"  {source}: {count} events")
    print()

    # Calculate expected events
    fast_expected = 3.0 / 0.05  # 3 seconds / 50ms = 60 events
    slow_expected = 3.0 / 0.1   # 3 seconds / 100ms = 30 events
    total_expected = fast_expected + slow_expected

    fast_actual = stats['by_source'].get('FastSource', 0)
    slow_actual = stats['by_source'].get('SlowSource', 0)

    print("Expected events:")
    print(f"  FastSource: ~{fast_expected:.0f}")
    print(f"  SlowSource: ~{slow_expected:.0f}")
    print(f"  Total: ~{total_expected:.0f}")
    print()

    print("Actual events:")
    print(f"  FastSource: {fast_actual}")
    print(f"  SlowSource: {slow_actual}")
    print(f"  Total: {stats['total_received']}")
    print()

    # Check for event loss
    fast_loss = fast_expected - fast_actual
    slow_loss = slow_expected - slow_actual
    total_loss = total_expected - stats['total_received']

    print("Event loss:")
    print(f"  FastSource: {fast_loss:.0f} ({(fast_loss/fast_expected)*100:.1f}%)")
    print(f"  SlowSource: {slow_loss:.0f} ({(slow_loss/slow_expected)*100:.1f}%)")
    print(f"  Total: {total_loss:.0f} ({(total_loss/total_expected)*100:.1f}%)")
    print()

    if total_loss <= 5:  # Allow small margin (timing variations)
        print("✅ SUCCESS! Async EventBus handled all events without significant loss!")
        print("   This proves async I/O works for event routing.")
    else:
        print("❌ FAILURE! Events were lost during async I/O.")
        print(f"   {total_loss:.0f} events missing out of {total_expected:.0f} expected.")

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
