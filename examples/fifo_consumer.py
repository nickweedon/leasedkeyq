"""Example with multiple FIFO consumers and error handling."""

import asyncio
import random

from leasedkeyq import LeasedKeyQueue


async def worker(
    queue: LeasedKeyQueue[str, dict],
    worker_id: str,
    fail_rate: float = 0.2,
) -> None:
    """
    Worker that processes items from queue with potential failures.

    Args:
        queue: The queue to process from
        worker_id: Identifier for this worker
        fail_rate: Probability of simulated failure (0.0 to 1.0)
    """
    processed = 0

    while True:
        try:
            # Get next item (timeout after 1 second of no work)
            key, value, lease = await queue.get(timeout=1.0)

            print(f"[{worker_id}] Processing {key}...")

            # Simulate work with potential failure
            await asyncio.sleep(random.uniform(0.1, 0.3))

            if random.random() < fail_rate:
                # Simulated failure - release for retry
                print(f"[{worker_id}] ✗ Failed {key} - will retry")
                await queue.release(lease, requeue_front=True)
            else:
                # Success - acknowledge
                print(f"[{worker_id}] ✓ Completed {key}")
                await queue.ack(lease)
                processed += 1

        except asyncio.TimeoutError:
            # No more work available
            break

    print(f"[{worker_id}] Finished - processed {processed} items")


async def main() -> None:
    """Run multiple workers processing from a shared queue."""
    print("=== Multiple FIFO Consumers with Error Handling ===\n")

    queue = LeasedKeyQueue[str, dict]()

    # Add tasks
    num_tasks = 20
    print(f"Adding {num_tasks} tasks to queue...\n")
    for i in range(num_tasks):
        await queue.put(
            f"task-{i:02d}",
            {"task_id": i, "data": f"payload-{i}"},
        )

    print(f"Queue size: {await queue.qsize()}\n")

    # Run multiple workers concurrently
    print("Starting 3 workers...\n")
    await asyncio.gather(
        worker(queue, "Worker-A", fail_rate=0.3),
        worker(queue, "Worker-B", fail_rate=0.2),
        worker(queue, "Worker-C", fail_rate=0.1),
    )

    print(f"\n=== Final Status ===")
    print(f"Available: {await queue.qsize()}")
    print(f"In-flight: {await queue.inflight_size()}")

    if await queue.qsize() > 0:
        print(f"\nRetrying {await queue.qsize()} remaining tasks...")
        # Retry with no failures
        await worker(queue, "Retry-Worker", fail_rate=0.0)

    print(f"\nAll tasks completed!")
    print(f"Final queue size: {await queue.qsize()}")

    await queue.close()


if __name__ == "__main__":
    asyncio.run(main())
