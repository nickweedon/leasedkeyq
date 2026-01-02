"""Tests for lease timeout functionality."""

import asyncio

import pytest

from leasedkeyq import LeasedKeyQueue


@pytest.mark.asyncio
async def test_lease_timeout_basic() -> None:
    """Test basic lease timeout functionality."""
    async with LeasedKeyQueue[str, int](default_lease_timeout=0.2) as queue:
        await queue.put("key1", 100)

        # Get and don't ack
        key, value, lease = await queue.get()
        assert key == "key1"

        # Wait for timeout
        await asyncio.sleep(0.3)

        # Item should be back in queue
        assert await queue.qsize() == 1
        key2, value2, lease2 = await queue.get(timeout=0.1)
        assert key2 == "key1"
        assert value2 == 100


@pytest.mark.asyncio
async def test_lease_timeout_requeue_front() -> None:
    """Test that expired leases are requeued to front."""
    async with LeasedKeyQueue[str, int](default_lease_timeout=0.2) as queue:
        await queue.put("key1", 1)
        await queue.put("key2", 2)
        await queue.put("key3", 3)

        # Get first item and let it timeout
        _, _, lease1 = await queue.get()

        # Wait for timeout
        await asyncio.sleep(0.3)

        # key1 should be back at front
        key, value, _ = await queue.get()
        assert key == "key1"


@pytest.mark.asyncio
async def test_per_lease_timeout_override() -> None:
    """Test per-lease timeout override."""
    async with LeasedKeyQueue[str, int](default_lease_timeout=10.0) as queue:
        await queue.put("key1", 100)

        # Override with shorter timeout
        key, value, lease = await queue.get(lease_timeout=0.2)

        # Wait for timeout
        await asyncio.sleep(0.3)

        # Should be back in queue
        assert await queue.qsize() == 1


@pytest.mark.asyncio
async def test_no_timeout_never_expires() -> None:
    """Test that leases without timeout never expire."""
    async with LeasedKeyQueue[str, int]() as queue:
        await queue.put("key1", 100)

        key, value, lease = await queue.get()

        # Wait a while
        await asyncio.sleep(0.3)

        # Should still be in-flight
        assert await queue.inflight_size() == 1
        assert await queue.qsize() == 0


@pytest.mark.asyncio
async def test_ack_before_timeout() -> None:
    """Test that acking before timeout prevents re-queue."""
    async with LeasedKeyQueue[str, int](default_lease_timeout=0.5) as queue:
        await queue.put("key1", 100)

        key, value, lease = await queue.get()
        await queue.ack(lease)

        # Wait past timeout
        await asyncio.sleep(0.6)

        # Should not be in queue
        assert await queue.qsize() == 0
        assert await queue.inflight_size() == 0


@pytest.mark.asyncio
async def test_release_before_timeout() -> None:
    """Test that releasing before timeout prevents auto-release."""
    async with LeasedKeyQueue[str, int](default_lease_timeout=0.5) as queue:
        await queue.put("key1", 100)

        key, value, lease = await queue.get()
        await queue.release(lease, requeue_front=True)

        initial_size = await queue.qsize()

        # Wait past timeout
        await asyncio.sleep(0.6)

        # Size should be same (not doubled)
        assert await queue.qsize() == initial_size


@pytest.mark.asyncio
async def test_multiple_leases_different_timeouts() -> None:
    """Test multiple leases with different timeout values."""
    async with LeasedKeyQueue[str, int](default_lease_timeout=1.0) as queue:
        await queue.put("fast", 1)
        await queue.put("slow", 2)
        await queue.put("default", 3)

        # Get with different timeouts
        _, _, lease_fast = await queue.get(lease_timeout=0.1)
        _, _, lease_slow = await queue.get(lease_timeout=0.5)
        _, _, lease_default = await queue.get()

        # After 0.2s, only fast should timeout
        await asyncio.sleep(0.2)
        assert await queue.qsize() >= 1

        # After 0.6s, both fast and slow should timeout
        await asyncio.sleep(0.5)
        assert await queue.qsize() >= 2

        # default should still be in-flight
        assert await queue.inflight_size() >= 1


@pytest.mark.asyncio
async def test_reaper_task_starts_and_stops() -> None:
    """Test that reaper task starts and stops correctly."""
    queue = LeasedKeyQueue[str, int](default_lease_timeout=1.0)

    assert queue._reaper_task is None

    await queue.start()
    assert queue._reaper_task is not None
    assert not queue._reaper_task.done()

    await queue.close()
    assert queue._reaper_task.done()


@pytest.mark.asyncio
async def test_reaper_not_started_without_timeout() -> None:
    """Test that reaper doesn't start if no timeout is set."""
    queue = LeasedKeyQueue[str, int]()
    await queue.start()

    assert queue._reaper_task is None

    await queue.close()


@pytest.mark.asyncio
async def test_reaper_starts_on_first_timeout_lease() -> None:
    """Test that reaper starts when first timeout lease is created."""
    queue = LeasedKeyQueue[str, int]()  # No default timeout

    assert queue._reaper_task is None

    await queue.put("key1", 100)

    # Get with timeout should start reaper
    _, _, lease = await queue.get(lease_timeout=1.0)

    await asyncio.sleep(0.01)  # Let reaper start
    assert queue._reaper_task is not None

    await queue.close()


@pytest.mark.asyncio
async def test_context_manager_cleanup() -> None:
    """Test that context manager properly cleans up timeout resources."""
    async with LeasedKeyQueue[str, int](default_lease_timeout=0.2) as queue:
        await queue.put("key1", 100)
        _, _, lease = await queue.get()

        # Don't ack - leave in-flight

    # After context exit, queue should be closed
    # (In-flight items returned to available during close)


@pytest.mark.asyncio
async def test_mixed_timeout_and_no_timeout() -> None:
    """Test mixing leases with and without timeouts."""
    async with LeasedKeyQueue[str, int]() as queue:
        await queue.put("timeout", 1)
        await queue.put("no-timeout", 2)

        # One with timeout, one without
        _, _, lease_timeout = await queue.get(lease_timeout=0.2)
        _, _, lease_no_timeout = await queue.get()

        # Wait for timeout
        await asyncio.sleep(0.3)

        # Timeout one should be back
        assert await queue.qsize() == 1

        # No-timeout should still be in-flight
        assert await queue.inflight_size() == 1


@pytest.mark.asyncio
async def test_timeout_preserves_updated_value() -> None:
    """Test that timeout re-queue preserves updated value."""
    async with LeasedKeyQueue[str, int](default_lease_timeout=0.2) as queue:
        await queue.put("key1", 100)

        key, value, lease = await queue.get()
        assert value == 100

        # Update while in-flight
        await queue.put("key1", 200, if_in_flight="update")

        # Wait for timeout
        await asyncio.sleep(0.3)

        # Should get updated value
        _, value2, _ = await queue.get()
        assert value2 == 200


@pytest.mark.asyncio
async def test_take_waiter_notified_on_timeout() -> None:
    """Test that take() waiters are notified when lease times out."""
    async with LeasedKeyQueue[str, int](default_lease_timeout=0.2) as queue:
        await queue.put("key1", 100)

        # Get it (in-flight)
        _, _, lease = await queue.get()

        result = None

        async def waiter() -> None:
            nonlocal result
            key, value, lease = await queue.take("key1", timeout=1.0)
            result = (key, value)

        # Start waiter
        task = asyncio.create_task(waiter())
        await asyncio.sleep(0.01)

        # Wait for timeout
        await asyncio.sleep(0.3)

        await task

        # Waiter should have gotten it
        assert result == ("key1", 100)


@pytest.mark.asyncio
async def test_stress_many_timeouts() -> None:
    """Stress test with many concurrent timeouts."""
    async with LeasedKeyQueue[str, int](default_lease_timeout=0.1) as queue:
        num_items = 20

        # Add items
        for i in range(num_items):
            await queue.put(f"item-{i}", i)

        # Get all without acking
        leases = []
        for _ in range(num_items):
            _, _, lease = await queue.get()
            leases.append(lease)

        # Wait for all to timeout
        await asyncio.sleep(0.3)

        # All should be back in queue
        assert await queue.qsize() == num_items
        assert await queue.inflight_size() == 0
