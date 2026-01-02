"""Tests for concurrent queue operations."""

import asyncio

import pytest

from leasedkeyq import LeasedKeyQueue


@pytest.mark.asyncio
async def test_concurrent_producers() -> None:
    """Test multiple producers adding items concurrently."""
    queue = LeasedKeyQueue[str, int]()

    async def producer(start: int, count: int) -> None:
        for i in range(start, start + count):
            await queue.put(f"key-{i}", i)
            await asyncio.sleep(0.001)

    # Run multiple producers
    await asyncio.gather(
        producer(0, 10),
        producer(100, 10),
        producer(200, 10),
    )

    assert await queue.qsize() == 30


@pytest.mark.asyncio
async def test_concurrent_consumers() -> None:
    """Test multiple consumers processing items concurrently."""
    queue = LeasedKeyQueue[str, int]()

    # Add items
    for i in range(20):
        await queue.put(f"key-{i}", i)

    results = []

    async def consumer(name: str) -> None:
        while True:
            try:
                key, value, lease = await queue.get(timeout=0.1)
                results.append((name, key, value))
                await queue.ack(lease)
            except asyncio.TimeoutError:
                break

    # Run multiple consumers
    await asyncio.gather(
        consumer("c1"),
        consumer("c2"),
        consumer("c3"),
    )

    # All items should be processed
    assert len(results) == 20
    keys = {r[1] for r in results}
    assert len(keys) == 20


@pytest.mark.asyncio
async def test_concurrent_take_different_keys() -> None:
    """Test concurrent take() operations on different keys."""
    queue = LeasedKeyQueue[str, int]()

    results = []

    async def taker(key: str) -> None:
        _, value, lease = await queue.take(key, timeout=1.0)
        results.append((key, value))
        await queue.ack(lease)

    # Start takers before items exist
    tasks = [
        asyncio.create_task(taker("key-a")),
        asyncio.create_task(taker("key-b")),
        asyncio.create_task(taker("key-c")),
    ]

    await asyncio.sleep(0.01)

    # Add items in different order
    await queue.put("key-c", 3)
    await queue.put("key-a", 1)
    await queue.put("key-b", 2)

    await asyncio.gather(*tasks)

    assert len(results) == 3
    assert set(results) == {("key-a", 1), ("key-b", 2), ("key-c", 3)}


@pytest.mark.asyncio
async def test_producer_consumer_pipeline() -> None:
    """Test producer-consumer pipeline with concurrent workers."""
    queue = LeasedKeyQueue[str, int]()
    processed = []

    async def producer() -> None:
        for i in range(50):
            await queue.put(f"task-{i}", i)
            await asyncio.sleep(0.001)

    async def consumer(name: str) -> None:
        while True:
            try:
                key, value, lease = await queue.get(timeout=0.2)
                # Simulate work
                await asyncio.sleep(0.001)
                processed.append((name, key, value))
                await queue.ack(lease)
            except asyncio.TimeoutError:
                break

    # Run producer and consumers concurrently
    await asyncio.gather(
        producer(),
        consumer("c1"),
        consumer("c2"),
        consumer("c3"),
    )

    assert len(processed) == 50


@pytest.mark.asyncio
async def test_concurrent_put_same_key() -> None:
    """Test concurrent put operations on the same key."""
    queue = LeasedKeyQueue[str, int]()

    async def putter(value: int) -> None:
        await queue.put("shared-key", value)

    # Try to put same key concurrently (last one wins)
    await asyncio.gather(
        putter(1),
        putter(2),
        putter(3),
    )

    # Should only have one item
    assert await queue.qsize() == 1

    _, value, _ = await queue.get()
    # Value should be one of them
    assert value in {1, 2, 3}


@pytest.mark.asyncio
async def test_race_between_release_and_take() -> None:
    """Test race condition between release and take."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)

    key, value, lease = await queue.get()

    results = []

    async def taker() -> None:
        k, v, l = await queue.take("key1", timeout=1.0)
        results.append(v)
        await queue.ack(l)

    # Start taker (will block)
    task = asyncio.create_task(taker())
    await asyncio.sleep(0.01)

    # Release the lease
    await queue.release(lease)

    await task

    # Taker should have gotten the released item
    assert results == [100]


@pytest.mark.asyncio
async def test_stress_test_many_items() -> None:
    """Stress test with many items and workers."""
    queue = LeasedKeyQueue[str, int]()
    num_items = 100
    num_consumers = 5

    # Add all items
    for i in range(num_items):
        await queue.put(f"item-{i}", i)

    processed = []

    async def consumer() -> None:
        while True:
            try:
                key, value, lease = await queue.get(timeout=0.1)
                await asyncio.sleep(0.001)  # Simulate work
                processed.append(value)
                await queue.ack(lease)
            except asyncio.TimeoutError:
                break

    # Process with multiple consumers
    tasks = [asyncio.create_task(consumer()) for _ in range(num_consumers)]
    await asyncio.gather(*tasks)

    # All items should be processed exactly once
    assert len(processed) == num_items
    assert set(processed) == set(range(num_items))


@pytest.mark.asyncio
async def test_concurrent_ack_release() -> None:
    """Test concurrent ack/release operations."""
    queue = LeasedKeyQueue[str, int]()

    for i in range(10):
        await queue.put(f"key-{i}", i)

    leases = []
    for _ in range(10):
        _, _, lease = await queue.get()
        leases.append(lease)

    async def ack_some() -> None:
        for i in range(0, 5):
            await queue.ack(leases[i])

    async def release_some() -> None:
        for i in range(5, 10):
            await queue.release(leases[i])

    await asyncio.gather(ack_some(), release_some())

    assert await queue.inflight_size() == 0
    assert await queue.qsize() == 5  # 5 released


@pytest.mark.asyncio
async def test_no_lost_items_under_contention() -> None:
    """Test that no items are lost under high contention."""
    queue = LeasedKeyQueue[str, int]()
    total_items = 50

    async def producer() -> None:
        for i in range(total_items):
            await queue.put(f"item-{i}", i)

    processed = set()
    lock = asyncio.Lock()

    async def consumer() -> None:
        while len(processed) < total_items:
            try:
                key, value, lease = await queue.get(timeout=0.5)
                # Randomly ack or release
                if value % 2 == 0:
                    await queue.ack(lease)
                    async with lock:
                        processed.add(value)
                else:
                    await queue.release(lease)
                    # Will be processed again
            except asyncio.TimeoutError:
                pass

    # Run producer and aggressive consumers
    await asyncio.gather(
        producer(),
        consumer(),
        consumer(),
        consumer(),
    )

    # All even items should be processed
    expected = {i for i in range(total_items) if i % 2 == 0}
    assert processed == expected
