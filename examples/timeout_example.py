"""Example demonstrating automatic lease timeouts and retry."""

import asyncio

from leasedkeyq import LeasedKeyQueue


async def slow_worker(
    queue: LeasedKeyQueue[str, dict],
    worker_id: str,
    processing_time: float,
) -> None:
    """
    Worker that takes a specific amount of time to process.

    If processing_time exceeds lease timeout, the item will be
    automatically re-queued and picked up by another worker.
    """
    try:
        key, value, lease = await queue.get(timeout=5.0)
        print(f"[{worker_id}] Got {key}, will take {processing_time:.1f}s")

        # Simulate slow processing
        await asyncio.sleep(processing_time)

        # Try to acknowledge (may fail if lease expired)
        try:
            await queue.ack(lease)
            print(f"[{worker_id}] ✓ Completed {key}")
        except Exception as e:
            print(f"[{worker_id}] ✗ Failed to ack {key}: {e.__class__.__name__}")

    except asyncio.TimeoutError:
        print(f"[{worker_id}] No more work")


async def fast_worker(queue: LeasedKeyQueue[str, dict], worker_id: str) -> None:
    """Fast worker that can pick up timed-out tasks."""
    processed = 0
    while True:
        try:
            key, value, lease = await queue.get(timeout=1.0)
            print(f"[{worker_id}] Got {key}")

            # Fast processing
            await asyncio.sleep(0.1)

            await queue.ack(lease)
            print(f"[{worker_id}] ✓ Completed {key}")
            processed += 1

        except asyncio.TimeoutError:
            break

    print(f"[{worker_id}] Finished - processed {processed} items")


async def main() -> None:
    """Demonstrate automatic lease timeout and retry."""
    print("=== Lease Timeout and Automatic Retry Example ===\n")

    # Queue with 1 second lease timeout
    async with LeasedKeyQueue[str, dict](default_lease_timeout=1.0) as queue:
        # Add tasks
        print("Adding tasks to queue...\n")
        for i in range(5):
            await queue.put(f"task-{i}", {"id": i, "data": f"payload-{i}"})

        print(f"Queue size: {await queue.qsize()}\n")

        print("Starting workers...\n")

        # Start a slow worker that will exceed timeout
        slow_task = asyncio.create_task(
            slow_worker(queue, "Slow-Worker", processing_time=2.5)
        )

        # Wait a bit
        await asyncio.sleep(0.5)

        # Start fast workers that will pick up expired leases
        await asyncio.gather(
            slow_task,
            fast_worker(queue, "Fast-Worker-A"),
            fast_worker(queue, "Fast-Worker-B"),
        )

        print(f"\n=== Final Status ===")
        print(f"Queue size: {await queue.qsize()}")
        print(f"In-flight: {await queue.inflight_size()}")


async def custom_timeout_example() -> None:
    """Example with per-lease timeout overrides."""
    print("\n\n=== Per-Lease Timeout Override Example ===\n")

    async with LeasedKeyQueue[str, int](default_lease_timeout=2.0) as queue:
        await queue.put("quick", 1)
        await queue.put("normal", 2)
        await queue.put("long", 3)

        # Get with different timeouts
        print("Getting items with different timeouts...\n")

        # Short timeout (0.5s instead of default 2s)
        key1, val1, lease1 = await queue.get(lease_timeout=0.5)
        print(f"Got {key1} with 0.5s timeout")

        # Use default timeout (2s)
        key2, val2, lease2 = await queue.get()
        print(f"Got {key2} with 2.0s timeout (default)")

        # No timeout (manual ack only)
        key3, val3, lease3 = await queue.get(lease_timeout=None)
        print(f"Got {key3} with no timeout (manual ack only)")

        print(f"\nWaiting 1 second...\n")
        await asyncio.sleep(1.0)

        # First lease should have timed out and be back in queue
        print(f"Queue size after 1s: {await queue.qsize()}")
        print(f"In-flight: {await queue.inflight_size()}")

        # Acknowledge remaining
        await queue.ack(lease2)
        await queue.ack(lease3)

        print(f"\nFinal queue size: {await queue.qsize()}")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(custom_timeout_example())
