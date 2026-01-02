"""Tests for lease management classes."""

import time

import pytest

from leasedkeyq.lease import Lease, LeaseRecord


def test_lease_creation() -> None:
    """Test creating a lease."""
    lease = Lease.create("test-key")
    assert lease.key == "test-key"
    assert lease.token
    assert len(lease.token) == 36  # UUID format


def test_lease_immutability() -> None:
    """Test that leases are immutable."""
    lease = Lease.create("test-key")
    with pytest.raises(AttributeError):  # FrozenInstanceError
        lease.token = "new-token"  # type: ignore[misc]


def test_lease_uniqueness() -> None:
    """Test that each lease gets a unique token."""
    lease1 = Lease.create("key")
    lease2 = Lease.create("key")
    assert lease1.token != lease2.token


def test_lease_record_creation() -> None:
    """Test creating a lease record."""
    lease = Lease.create("test-key")
    record = LeaseRecord(lease=lease, key="test-key", value={"data": 123})

    assert record.lease is lease
    assert record.key == "test-key"
    assert record.value == {"data": 123}
    assert not record.acknowledged
    assert record.created_at > 0
    assert record.timeout is None


def test_lease_record_with_timeout() -> None:
    """Test lease record with timeout."""
    lease = Lease.create("test-key")
    record = LeaseRecord(
        lease=lease,
        key="test-key",
        value=100,
        timeout=30.0,
    )

    assert record.timeout == 30.0
    assert not record.is_expired(time.monotonic())


def test_lease_record_expiration() -> None:
    """Test lease expiration logic."""
    lease = Lease.create("test-key")
    now = time.monotonic()
    record = LeaseRecord(
        lease=lease,
        key="test-key",
        value=100,
        created_at=now - 40.0,  # 40 seconds ago
        timeout=30.0,
    )

    assert record.is_expired(time.monotonic())


def test_lease_record_no_timeout_never_expires() -> None:
    """Test that records without timeout never expire."""
    lease = Lease.create("test-key")
    record = LeaseRecord(
        lease=lease,
        key="test-key",
        value=100,
        created_at=time.monotonic() - 1000.0,  # Very old
        timeout=None,
    )

    assert not record.is_expired(time.monotonic())


def test_lease_record_not_expired_yet() -> None:
    """Test that recent leases are not expired."""
    lease = Lease.create("test-key")
    record = LeaseRecord(
        lease=lease,
        key="test-key",
        value=100,
        timeout=30.0,
    )

    # Just created, should not be expired
    assert not record.is_expired(time.monotonic())


def test_lease_record_acknowledged() -> None:
    """Test acknowledged flag."""
    lease = Lease.create("test-key")
    record = LeaseRecord(lease=lease, key="test-key", value=100)

    assert not record.acknowledged
    record.acknowledged = True
    assert record.acknowledged
