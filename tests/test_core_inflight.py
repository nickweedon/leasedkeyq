"""Tests for in-flight lease management."""

import pytest

from leasedkeyq import (
    InvalidLeaseError,
    LeaseAlreadyAcknowledgedError,
    LeasedKeyQueue,
)


@pytest.mark.asyncio
async def test_ack_removes_permanently() -> None:
    """Test that ack() removes item permanently."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)

    key, value, lease = await queue.get()
    assert await queue.inflight_size() == 1

    await queue.ack(lease)

    assert await queue.inflight_size() == 0
    assert await queue.qsize() == 0
    assert not await queue.contains("key1")


@pytest.mark.asyncio
async def test_ack_invalid_lease() -> None:
    """Test acking an invalid lease."""
    from leasedkeyq.lease import Lease

    queue = LeasedKeyQueue[str, int]()
    fake_lease = Lease(token="invalid-token", key="key1")

    with pytest.raises(InvalidLeaseError):
        await queue.ack(fake_lease)


@pytest.mark.asyncio
async def test_ack_already_acknowledged() -> None:
    """Test double-ack raises error."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)

    _, _, lease = await queue.get()
    await queue.ack(lease)

    with pytest.raises(LeaseAlreadyAcknowledgedError):
        await queue.ack(lease)


@pytest.mark.asyncio
async def test_release_requeues_back() -> None:
    """Test release() re-adds to back of queue."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)
    await queue.put("key2", 200)

    _, _, lease1 = await queue.get()
    key2, _, lease2 = await queue.get()

    # Release key1 to back
    await queue.release(lease1, requeue_front=False)

    # key1 should be after key2 was acknowledged
    await queue.ack(lease2)

    # Next item should be key1
    key, value, _ = await queue.get()
    assert key == "key1"


@pytest.mark.asyncio
async def test_release_requeues_front() -> None:
    """Test release() with requeue_front=True."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)
    await queue.put("key2", 200)

    _, _, lease1 = await queue.get()
    _, _, lease2 = await queue.get()

    # Release key1 to front
    await queue.release(lease1, requeue_front=True)

    # key1 should be next
    key, value, _ = await queue.get()
    assert key == "key1"


@pytest.mark.asyncio
async def test_release_invalid_lease() -> None:
    """Test releasing an invalid lease."""
    from leasedkeyq.lease import Lease

    queue = LeasedKeyQueue[str, int]()
    fake_lease = Lease(token="invalid-token", key="key1")

    with pytest.raises(InvalidLeaseError):
        await queue.release(fake_lease)


@pytest.mark.asyncio
async def test_release_already_acknowledged() -> None:
    """Test releasing an already-acked lease."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)

    _, _, lease = await queue.get()
    await queue.ack(lease)

    with pytest.raises(LeaseAlreadyAcknowledgedError):
        await queue.release(lease)


@pytest.mark.asyncio
async def test_release_after_release() -> None:
    """Test double-release is idempotent (doesn't duplicate)."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)

    _, _, lease = await queue.get()
    await queue.release(lease)

    # Second release should fail (lease no longer in-flight)
    with pytest.raises(InvalidLeaseError):
        await queue.release(lease)


@pytest.mark.asyncio
async def test_release_with_buffered_key() -> None:
    """Test release when key was buffered during in-flight."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)

    _, _, lease = await queue.get()

    # Buffer another copy
    await queue.put("key1", 200, if_in_flight="buffer")

    # Release the first
    await queue.release(lease)

    # Should only have one copy (the buffered one)
    assert await queue.qsize() == 1
    _, value, _ = await queue.get()
    assert value == 200


@pytest.mark.asyncio
async def test_lease_preserves_updated_value() -> None:
    """Test that release preserves updated value from in-flight update."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)

    _, value, lease = await queue.get()
    assert value == 100

    # Update while in-flight
    await queue.put("key1", 200, if_in_flight="update")

    # Release
    await queue.release(lease)

    # Should get updated value
    _, value, _ = await queue.get()
    assert value == 200


@pytest.mark.asyncio
async def test_multiple_leases() -> None:
    """Test managing multiple leases."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)
    await queue.put("key2", 200)
    await queue.put("key3", 300)

    _, _, lease1 = await queue.get()
    _, _, lease2 = await queue.get()
    _, _, lease3 = await queue.get()

    assert await queue.inflight_size() == 3

    await queue.ack(lease1)
    assert await queue.inflight_size() == 2

    await queue.release(lease2)
    assert await queue.inflight_size() == 1
    assert await queue.qsize() == 1

    await queue.ack(lease3)
    assert await queue.inflight_size() == 0


@pytest.mark.asyncio
async def test_inflight_keys_tracking() -> None:
    """Test that inflight_keys() correctly tracks in-flight items."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key1", 100)
    await queue.put("key2", 200)

    _, _, lease1 = await queue.get()
    inflight = await queue.inflight_keys()
    assert inflight == {"key1"}

    _, _, lease2 = await queue.get()
    inflight = await queue.inflight_keys()
    assert inflight == {"key1", "key2"}

    await queue.ack(lease1)
    inflight = await queue.inflight_keys()
    assert inflight == {"key2"}

    await queue.release(lease2)
    inflight = await queue.inflight_keys()
    assert inflight == set()
