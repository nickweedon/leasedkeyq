"""Tests for basic LeasedKeyQueue operations."""

import pytest

from leasedkeyq import (
    KeyAlreadyInFlightError,
    LeasedKeyQueue,
    QueueClosedError,
)


@pytest.mark.asyncio
async def test_queue_creation() -> None:
    """Test creating a queue."""
    queue = LeasedKeyQueue[str, int]()
    assert await queue.qsize() == 0
    assert await queue.inflight_size() == 0


@pytest.mark.asyncio
async def test_put_and_get() -> None:
    """Test basic put and get operations."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)
    await queue.put("key2", 200)

    assert await queue.qsize() == 2

    key, value, lease = await queue.get()
    assert key == "key1"
    assert value == 100
    assert lease.key == "key1"

    assert await queue.qsize() == 1
    assert await queue.inflight_size() == 1


@pytest.mark.asyncio
async def test_put_update_available() -> None:
    """Test updating an available key."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)
    await queue.put("key1", 200)  # Update

    assert await queue.qsize() == 1

    key, value, lease = await queue.get()
    assert key == "key1"
    assert value == 200  # Updated value


@pytest.mark.asyncio
async def test_put_update_inflight() -> None:
    """Test updating an in-flight key (default policy)."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)

    key, value, lease = await queue.get()
    assert value == 100

    # Update while in-flight (default: update policy)
    await queue.put("key1", 200)

    # Release and get again
    await queue.release(lease)
    key, value, lease2 = await queue.get()
    assert value == 200  # Updated value


@pytest.mark.asyncio
async def test_put_reject_inflight() -> None:
    """Test reject policy for in-flight keys."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)

    key, value, lease = await queue.get()

    # Try to put with reject policy
    with pytest.raises(KeyAlreadyInFlightError):
        await queue.put("key1", 200, if_in_flight="reject")


@pytest.mark.asyncio
async def test_put_buffer_inflight() -> None:
    """Test buffer policy for in-flight keys."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)

    key, value, lease = await queue.get()
    assert await queue.qsize() == 0

    # Buffer a second copy
    await queue.put("key1", 200, if_in_flight="buffer")
    assert await queue.qsize() == 1

    # Ack the first lease
    await queue.ack(lease)

    # Get the buffered copy
    key, value, lease2 = await queue.get()
    assert value == 200


@pytest.mark.asyncio
async def test_peek() -> None:
    """Test peeking at values."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)
    await queue.put("key2", 200)

    assert await queue.peek("key1") == 100
    assert await queue.peek("key2") == 200
    assert await queue.peek("nonexistent") is None

    # Peek doesn't remove items
    assert await queue.qsize() == 2


@pytest.mark.asyncio
async def test_contains() -> None:
    """Test checking if key is available."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)

    assert await queue.contains("key1")
    assert not await queue.contains("key2")

    # Get makes it not available
    key, value, lease = await queue.get()
    assert not await queue.contains("key1")


@pytest.mark.asyncio
async def test_available_keys() -> None:
    """Test getting available keys."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)
    await queue.put("key2", 200)
    await queue.put("key3", 300)

    keys = await queue.available_keys()
    assert keys == {"key1", "key2", "key3"}

    # Get one
    _, _, lease = await queue.get()
    keys = await queue.available_keys()
    assert len(keys) == 2


@pytest.mark.asyncio
async def test_inflight_keys() -> None:
    """Test getting in-flight keys."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)
    await queue.put("key2", 200)

    assert await queue.inflight_keys() == set()

    key1, _, lease1 = await queue.get()
    assert await queue.inflight_keys() == {key1}

    key2, _, lease2 = await queue.get()
    assert await queue.inflight_keys() == {key1, key2}

    await queue.ack(lease1)
    assert await queue.inflight_keys() == {key2}


@pytest.mark.asyncio
async def test_qsize() -> None:
    """Test queue size tracking."""
    queue = LeasedKeyQueue[str, int]()
    assert await queue.qsize() == 0

    await queue.put("key1", 100)
    assert await queue.qsize() == 1

    await queue.put("key2", 200)
    assert await queue.qsize() == 2

    await queue.get()
    assert await queue.qsize() == 1


@pytest.mark.asyncio
async def test_inflight_size() -> None:
    """Test in-flight size tracking."""
    queue = LeasedKeyQueue[str, int]()
    assert await queue.inflight_size() == 0

    await queue.put("key1", 100)
    await queue.put("key2", 200)

    await queue.get()
    assert await queue.inflight_size() == 1

    await queue.get()
    assert await queue.inflight_size() == 2


@pytest.mark.asyncio
async def test_fifo_order() -> None:
    """Test FIFO ordering."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("first", 1)
    await queue.put("second", 2)
    await queue.put("third", 3)

    key1, _, _ = await queue.get()
    key2, _, _ = await queue.get()
    key3, _, _ = await queue.get()

    assert key1 == "first"
    assert key2 == "second"
    assert key3 == "third"


@pytest.mark.asyncio
async def test_close_empty_queue() -> None:
    """Test closing an empty queue."""
    queue = LeasedKeyQueue[str, int]()
    await queue.close()

    with pytest.raises(QueueClosedError):
        await queue.put("key", 1)

    with pytest.raises(QueueClosedError):
        await queue.get()


@pytest.mark.asyncio
async def test_close_with_items() -> None:
    """Test closing a queue with in-flight items."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)
    await queue.put("key2", 200)

    _, _, lease1 = await queue.get()
    _, _, lease2 = await queue.get()

    assert await queue.inflight_size() == 2
    assert await queue.qsize() == 0

    # Close should return items to available
    await queue.close()

    # Can't operate on closed queue
    with pytest.raises(QueueClosedError):
        await queue.get()


@pytest.mark.asyncio
async def test_context_manager() -> None:
    """Test using queue as context manager."""
    async with LeasedKeyQueue[str, int]() as queue:
        await queue.put("key", 100)
        assert await queue.qsize() == 1

    # Queue should be closed after context exit
    with pytest.raises(QueueClosedError):
        await queue.put("key2", 200)


@pytest.mark.asyncio
async def test_close_with_mixed_state() -> None:
    """Test closing queue with reaper active, available items, and mixed in-flight items."""
    queue = LeasedKeyQueue[str, int](default_lease_timeout=10.0)
    await queue.start()

    # Add items in different states
    await queue.put("available1", 100)
    await queue.put("available2", 200)
    await queue.put("inflight1", 300)
    await queue.put("inflight2", 400)
    await queue.put("acknowledged", 500)

    # Get some items (in-flight)
    _, _, lease1 = await queue.get()  # inflight1
    _, _, lease2 = await queue.get()  # inflight2
    _, _, lease3 = await queue.get()  # acknowledged

    # Acknowledge one lease
    await queue.ack(lease3)

    # Verify state before close
    assert await queue.qsize() == 2  # available1, available2
    assert await queue.inflight_size() == 2  # inflight1, inflight2
    assert queue._reaper_task is not None
    assert not queue._reaper_task.done()

    # Close should return in-flight items to available and stop reaper
    await queue.close()

    # Verify reaper stopped
    assert queue._reaper_task.done()

    # Queue should be closed
    assert queue._closed

    # Operations should raise QueueClosedError
    with pytest.raises(QueueClosedError):
        await queue.get()

    with pytest.raises(QueueClosedError):
        await queue.put("new", 999)
