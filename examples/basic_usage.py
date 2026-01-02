"""Basic usage example for leasedkeyq."""

import asyncio

from leasedkeyq import LeasedKeyQueue


async def main() -> None:
    """Demonstrate basic queue operations."""
    # Create a queue without timeout
    queue = LeasedKeyQueue[str, dict]()

    print("=== Basic Producer-Consumer Example ===\n")

    # Producer: Add some tasks
    print("Producer: Adding tasks...")
    await queue.put("task-1", {"action": "send_email", "to": "user@example.com"})
    await queue.put("task-2", {"action": "process_data", "records": 100})
    await queue.put("task-3", {"action": "generate_report", "format": "pdf"})

    print(f"Queue size: {await queue.qsize()}")
    print(f"Available keys: {await queue.available_keys()}\n")

    # Consumer: Process tasks in FIFO order
    print("Consumer: Processing tasks...")
    while await queue.qsize() > 0:
        key, value, lease = await queue.get()
        print(f"  Processing {key}: {value}")

        # Simulate work
        await asyncio.sleep(0.1)

        # Acknowledge completion
        await queue.ack(lease)
        print(f"  ✓ Completed {key}\n")

    print(f"Final queue size: {await queue.qsize()}")
    print(f"Final in-flight: {await queue.inflight_size()}\n")

    # Clean up
    await queue.close()


if __name__ == "__main__":
    asyncio.run(main())
