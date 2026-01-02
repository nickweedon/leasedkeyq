"""Tests for blocking behavior in LeasedKeyQueue."""

import asyncio

import pytest

from leasedkeyq import LeasedKeyQueue


@pytest.mark.asyncio
async def test_get_blocks_until_available() -> None:
    """Test that get() blocks until an item is available."""
    queue = LeasedKeyQueue[str, int]()

    result = None

    async def consumer() -> None:
        nonlocal result
        key, value, lease = await queue.get()
        result = (key, value)

    # Start consumer (will block)
    task = asyncio.create_task(consumer())
    await asyncio.sleep(0.01)  # Let it block

    assert result is None

    # Add an item
    await queue.put("key1", 100)
    await task

    assert result == ("key1", 100)


@pytest.mark.asyncio
async def test_get_timeout() -> None:
    """Test get() with timeout."""
    queue = LeasedKeyQueue[str, int]()

    with pytest.raises(asyncio.TimeoutError):
        await queue.get(timeout=0.1)


@pytest.mark.asyncio
async def test_get_timeout_success() -> None:
    """Test get() succeeds before timeout."""
    queue = LeasedKeyQueue[str, int]()

    async def delayed_put() -> None:
        await asyncio.sleep(0.05)
        await queue.put("key1", 100)

    task = asyncio.create_task(delayed_put())
    key, value, lease = await queue.get(timeout=1.0)
    await task

    assert key == "key1"
    assert value == 100


@pytest.mark.asyncio
async def test_take_blocks_until_key_available() -> None:
    """Test that take() blocks until specific key is available."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("wrong-key", 999)

    result = None

    async def consumer() -> None:
        nonlocal result
        key, value, lease = await queue.take("target-key")
        result = (key, value)

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0.01)

    assert result is None

    # Add the target key
    await queue.put("target-key", 100)
    await task

    assert result == ("target-key", 100)


@pytest.mark.asyncio
async def test_take_blocks_while_inflight() -> None:
    """Test that take() blocks while key is in-flight."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)

    # Get it (make it in-flight)
    _, _, lease1 = await queue.get()

    result = None

    async def second_consumer() -> None:
        nonlocal result
        key, value, lease = await queue.take("key1")
        result = (key, value)

    task = asyncio.create_task(second_consumer())
    await asyncio.sleep(0.01)

    # Should still be blocked
    assert result is None

    # Release the lease
    await queue.release(lease1)
    await task

    assert result == ("key1", 100)


@pytest.mark.asyncio
async def test_take_timeout() -> None:
    """Test take() with timeout."""
    queue = LeasedKeyQueue[str, int]()

    with pytest.raises(asyncio.TimeoutError):
        await queue.take("nonexistent", timeout=0.1)


@pytest.mark.asyncio
async def test_take_timeout_success() -> None:
    """Test take() succeeds before timeout."""
    queue = LeasedKeyQueue[str, int]()

    async def delayed_put() -> None:
        await asyncio.sleep(0.05)
        await queue.put("key1", 100)

    task = asyncio.create_task(delayed_put())
    key, value, lease = await queue.take("key1", timeout=1.0)
    await task

    assert key == "key1"
    assert value == 100


@pytest.mark.asyncio
async def test_multiple_consumers_waiting() -> None:
    """Test multiple consumers waiting for items."""
    queue = LeasedKeyQueue[str, int]()
    results = []

    async def consumer(name: str) -> None:
        key, value, lease = await queue.get()
        results.append((name, key, value))
        await queue.ack(lease)

    # Start multiple consumers
    tasks = [asyncio.create_task(consumer(f"c{i}")) for i in range(3)]
    await asyncio.sleep(0.01)

    # Add items
    await queue.put("key1", 1)
    await queue.put("key2", 2)
    await queue.put("key3", 3)

    await asyncio.gather(*tasks)

    # All consumers should have gotten an item
    assert len(results) == 3
    keys = {r[1] for r in results}
    assert keys == {"key1", "key2", "key3"}


@pytest.mark.asyncio
async def test_multiple_take_waiters_same_key() -> None:
    """Test multiple consumers waiting for the same key."""
    queue = LeasedKeyQueue[str, int]()
    results = []

    async def consumer(name: str) -> None:
        key, value, lease = await queue.take("target")
        results.append((name, key, value))
        await queue.ack(lease)

    # Start multiple consumers for same key
    tasks = [asyncio.create_task(consumer(f"c{i}")) for i in range(3)]
    await asyncio.sleep(0.01)

    # Add the key multiple times
    await queue.put("target", 1)
    await asyncio.sleep(0.01)
    await queue.put("target", 2)
    await asyncio.sleep(0.01)
    await queue.put("target", 3)

    await asyncio.gather(*tasks)

    # All consumers should have gotten the target key
    assert len(results) == 3
    assert all(r[1] == "target" for r in results)


@pytest.mark.asyncio
async def test_cancellation_during_get() -> None:
    """Test that get() can be cancelled."""
    queue = LeasedKeyQueue[str, int]()

    async def consumer() -> None:
        await queue.get()

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0.01)

    # Cancel the task
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_cancellation_during_take() -> None:
    """Test that take() can be cancelled."""
    queue = LeasedKeyQueue[str, int]()

    async def consumer() -> None:
        await queue.take("key")

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0.01)

    # Cancel the task
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
