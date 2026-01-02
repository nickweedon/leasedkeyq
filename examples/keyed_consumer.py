"""Example demonstrating keyed/targeted consumption with take()."""

import asyncio

from leasedkeyq import LeasedKeyQueue


async def priority_handler(queue: LeasedKeyQueue[str, dict]) -> None:
    """Handler that specifically waits for priority tasks."""
    print("[Priority Handler] Waiting for priority tasks...")

    for i in range(3):
        key, value, lease = await queue.take(f"priority-{i}", timeout=5.0)
        print(f"[Priority Handler] Processing {key}: {value}")
        await asyncio.sleep(0.2)
        await queue.ack(lease)
        print(f"[Priority Handler] ✓ Completed {key}")


async def regular_handler(queue: LeasedKeyQueue[str, dict], handler_id: str) -> None:
    """Handler that processes any available task (FIFO)."""
    print(f"[{handler_id}] Processing regular tasks...")

    processed = 0
    while True:
        try:
            key, value, lease = await queue.get(timeout=1.0)
            if key.startswith("priority-"):
                # Skip priority tasks (let priority handler get them)
                await queue.release(lease, requeue_front=False)
                continue

            print(f"[{handler_id}] Processing {key}: {value}")
            await asyncio.sleep(0.1)
            await queue.ack(lease)
            processed += 1

        except asyncio.TimeoutError:
            break

    print(f"[{handler_id}] Finished - processed {processed} items")


async def task_producer(queue: LeasedKeyQueue[str, dict]) -> None:
    """Producer that adds both regular and priority tasks."""
    print("[Producer] Adding tasks...\n")

    # Add mixed tasks
    await queue.put("regular-1", {"type": "normal", "data": "A"})
    await queue.put("regular-2", {"type": "normal", "data": "B"})
    await queue.put("priority-0", {"type": "urgent", "data": "X"})
    await queue.put("regular-3", {"type": "normal", "data": "C"})
    await queue.put("regular-4", {"type": "normal", "data": "D"})

    await asyncio.sleep(0.5)

    await queue.put("priority-1", {"type": "urgent", "data": "Y"})
    await queue.put("regular-5", {"type": "normal", "data": "E"})

    await asyncio.sleep(0.5)

    await queue.put("priority-2", {"type": "urgent", "data": "Z"})
    await queue.put("regular-6", {"type": "normal", "data": "F"})

    print("[Producer] Done adding tasks\n")


async def main() -> None:
    """Demonstrate targeted consumption with take()."""
    print("=== Keyed/Targeted Consumption Example ===\n")

    queue = LeasedKeyQueue[str, dict]()

    # Run producer and consumers concurrently
    await asyncio.gather(
        task_producer(queue),
        priority_handler(queue),
        regular_handler(queue, "Regular-A"),
        regular_handler(queue, "Regular-B"),
    )

    print(f"\n=== Final Status ===")
    print(f"Queue size: {await queue.qsize()}")
    print(f"In-flight: {await queue.inflight_size()}")

    await queue.close()


if __name__ == "__main__":
    asyncio.run(main())
