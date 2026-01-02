"""Main LeasedKeyQueue implementation."""

import asyncio
import time
from typing import Generic, TypeVar

from leasedkeyq.errors import (
    InvalidLeaseError,
    KeyAlreadyInFlightError,
    LeaseAlreadyAcknowledgedError,
    QueueClosedError,
)
from leasedkeyq.lease import Lease, LeaseRecord
from leasedkeyq.linkedlist import DoublyLinkedList, Node
from leasedkeyq.types import InFlightPolicy

K = TypeVar("K")
V = TypeVar("V")

# Reaper check interval in seconds
_REAPER_INTERVAL = 0.1


class LeasedKeyQueue(Generic[K, V]):
    """
    Async keyed leased queue with FIFO semantics and O(1) operations.

    Combines dictionary-style keyed access with FIFO queue semantics and
    lease-based exclusive processing. All operations are O(1).
    """

    def __init__(self, *, default_lease_timeout: float | None = None) -> None:
        """
        Initialize the queue.

        Args:
            default_lease_timeout: Default timeout in seconds for leases.
                If set, a background reaper task will automatically release
                expired leases. Can be overridden per-lease in get()/take().
        """
        self._lock = asyncio.Lock()
        self._cond_changed = asyncio.Condition(self._lock)
        self._available: dict[K, Node[K, V]] = {}
        self._in_flight: dict[str, LeaseRecord[K, V]] = {}
        self._leases_by_key: dict[K, str] = {}
        self._acknowledged: set[str] = set()  # Track acknowledged lease tokens
        self._list = DoublyLinkedList[K, V]()
        self._default_lease_timeout = default_lease_timeout
        self._reaper_task: asyncio.Task[None] | None = None
        self._closed = False

    async def start(self) -> None:
        """Start background tasks (lease timeout reaper if needed)."""
        async with self._lock:
            if self._closed:
                raise QueueClosedError("Cannot start a closed queue")
            if self._default_lease_timeout is not None and self._reaper_task is None:
                self._reaper_task = asyncio.create_task(self._reaper_loop())

    async def close(self) -> None:
        """Stop background tasks and cleanup. Returns all in-flight items to available."""
        async with self._lock:
            if self._closed:
                return
            self._closed = True

            # Cancel reaper task
            if self._reaper_task is not None:
                self._reaper_task.cancel()
                try:
                    await self._reaper_task
                except asyncio.CancelledError:
                    pass
                # Keep reference so tests can check task.done()

            # Return all in-flight items to available (front of queue)
            for record in list(self._in_flight.values()):
                if not record.acknowledged:
                    await self._release_internal(record.lease, requeue_front=True)

            self._cond_changed.notify_all()

    async def __aenter__(self) -> "LeasedKeyQueue[K, V]":
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Context manager exit."""
        await self.close()

    async def put(
        self,
        key: K,
        value: V,
        *,
        if_in_flight: InFlightPolicy = "update",
    ) -> None:
        """
        Put a key-value pair into the queue.

        Args:
            key: Unique key for the item
            value: Value to store
            if_in_flight: Policy when key is currently in-flight:
                - "update": Update the in-flight value (default)
                - "reject": Raise KeyAlreadyInFlightError
                - "buffer": Enqueue a second copy to available

        Raises:
            KeyAlreadyInFlightError: If key is in-flight and if_in_flight="reject"
            QueueClosedError: If queue is closed
        """
        async with self._lock:
            if self._closed:
                raise QueueClosedError("Cannot put to a closed queue")

            # Check if key is in-flight
            if key in self._leases_by_key:
                if if_in_flight == "update":
                    # Update the in-flight value
                    lease_token = self._leases_by_key[key]
                    self._in_flight[lease_token].value = value
                    return
                elif if_in_flight == "reject":
                    raise KeyAlreadyInFlightError(f"Key {key!r} is currently in flight")
                elif if_in_flight == "buffer":
                    # Fall through to enqueue to available
                    pass

            # Check if key is already available
            if key in self._available:
                # Update existing value
                self._available[key].value = value
                return

            # Add new key to available
            node = Node(key, value)
            self._list.append(node)
            self._available[key] = node
            self._cond_changed.notify_all()

    async def get(
        self,
        timeout: float | None = None,
        *,
        lease_timeout: float | None = None,
    ) -> tuple[K, V, Lease[K]]:
        """
        Get the next item from the queue (FIFO).

        Blocks until an item is available or timeout expires.

        Args:
            timeout: Maximum time to wait for an item (None = wait forever)
            lease_timeout: Timeout for this lease (overrides default_lease_timeout)

        Returns:
            Tuple of (key, value, lease)

        Raises:
            asyncio.TimeoutError: If timeout expires
            QueueClosedError: If queue is closed
        """
        async with self._lock:
            if self._closed:
                raise QueueClosedError("Cannot get from a closed queue")

            # Wait for items to be available
            while not self._list:
                if self._closed:
                    raise QueueClosedError("Queue was closed while waiting")
                if timeout is not None:
                    await asyncio.wait_for(self._cond_changed.wait(), timeout)
                else:
                    await self._cond_changed.wait()

            # Pop from front (FIFO)
            node = self._list.popleft()
            if node is None:
                raise RuntimeError("Unexpected empty list after checking")

            # Remove from available
            del self._available[node.key]

            # Create lease
            lease = Lease.create(node.key)
            effective_timeout = (
                lease_timeout if lease_timeout is not None else self._default_lease_timeout
            )
            record = LeaseRecord(
                lease=lease,
                key=node.key,
                value=node.value,
                timeout=effective_timeout,
            )

            # Add to in-flight
            self._in_flight[lease.token] = record
            self._leases_by_key[node.key] = lease.token

            # Start reaper if needed and not already running
            if effective_timeout is not None and self._reaper_task is None and not self._closed:
                self._reaper_task = asyncio.create_task(self._reaper_loop())

            return (node.key, node.value, lease)

    async def take(
        self,
        key: K,
        timeout: float | None = None,
        *,
        lease_timeout: float | None = None,
    ) -> tuple[K, V, Lease[K]]:
        """
        Take a specific key from the queue.

        Blocks until the key is available (not in-flight) or timeout expires.

        Args:
            key: The key to take
            timeout: Maximum time to wait for the key (None = wait forever)
            lease_timeout: Timeout for this lease (overrides default_lease_timeout)

        Returns:
            Tuple of (key, value, lease)

        Raises:
            asyncio.TimeoutError: If timeout expires
            QueueClosedError: If queue is closed
        """
        async with self._lock:
            if self._closed:
                raise QueueClosedError("Cannot take from a closed queue")

            # Wait for key to be available
            while key not in self._available:
                if self._closed:
                    raise QueueClosedError("Queue was closed while waiting")
                if timeout is not None:
                    await asyncio.wait_for(self._cond_changed.wait(), timeout)
                else:
                    await self._cond_changed.wait()

            # Get the node
            node = self._available[key]

            # Remove from list and available
            self._list.remove(node)
            del self._available[key]

            # Create lease
            lease = Lease.create(key)
            effective_timeout = (
                lease_timeout if lease_timeout is not None else self._default_lease_timeout
            )
            record = LeaseRecord(
                lease=lease,
                key=key,
                value=node.value,
                timeout=effective_timeout,
            )

            # Add to in-flight
            self._in_flight[lease.token] = record
            self._leases_by_key[key] = lease.token

            # Start reaper if needed and not already running
            if effective_timeout is not None and self._reaper_task is None and not self._closed:
                self._reaper_task = asyncio.create_task(self._reaper_loop())

            return (key, node.value, lease)

    async def ack(self, lease: Lease[K]) -> None:
        """
        Acknowledge a lease, permanently removing the item from the queue.

        Args:
            lease: The lease to acknowledge

        Raises:
            InvalidLeaseError: If lease is unknown
            LeaseAlreadyAcknowledgedError: If lease was already acknowledged
            QueueClosedError: If queue is closed
        """
        async with self._lock:
            if self._closed:
                raise QueueClosedError("Cannot ack in a closed queue")

            if lease.token in self._acknowledged:
                raise LeaseAlreadyAcknowledgedError(f"Lease {lease.token} already acknowledged")

            if lease.token not in self._in_flight:
                raise InvalidLeaseError(f"Unknown lease token: {lease.token}")

            record = self._in_flight[lease.token]
            if record.acknowledged:
                raise LeaseAlreadyAcknowledgedError(f"Lease {lease.token} already acknowledged")

            # Mark as acknowledged and remove
            record.acknowledged = True
            self._acknowledged.add(lease.token)
            del self._in_flight[lease.token]
            del self._leases_by_key[lease.key]

    async def release(self, lease: Lease[K], *, requeue_front: bool = False) -> None:
        """
        Release a lease, returning the item to the queue.

        Args:
            lease: The lease to release
            requeue_front: If True, add to front of queue; otherwise add to back

        Raises:
            InvalidLeaseError: If lease is unknown
            LeaseAlreadyAcknowledgedError: If lease was already acknowledged
            QueueClosedError: If queue is closed
        """
        async with self._lock:
            if self._closed:
                raise QueueClosedError("Cannot release in a closed queue")
            await self._release_internal(lease, requeue_front=requeue_front)

    async def _release_internal(self, lease: Lease[K], *, requeue_front: bool) -> None:
        """Internal release implementation (must be called with lock held)."""
        if lease.token in self._acknowledged:
            raise LeaseAlreadyAcknowledgedError(f"Lease {lease.token} already acknowledged")

        if lease.token not in self._in_flight:
            raise InvalidLeaseError(f"Unknown lease token: {lease.token}")

        record = self._in_flight[lease.token]
        if record.acknowledged:
            raise LeaseAlreadyAcknowledgedError(f"Lease {lease.token} already acknowledged")

        # Remove from in-flight
        del self._in_flight[lease.token]
        del self._leases_by_key[lease.key]

        # Don't re-add if key is already available (from buffer policy)
        if lease.key in self._available:
            return

        # Re-add to queue
        node = Node(lease.key, record.value)
        if requeue_front:
            self._list.appendleft(node)
        else:
            self._list.append(node)
        self._available[lease.key] = node
        self._cond_changed.notify_all()

    async def peek(self, key: K) -> V | None:
        """
        Peek at the value for a key in the available queue.

        Args:
            key: The key to peek at

        Returns:
            The value if key is available, None otherwise
        """
        async with self._lock:
            node = self._available.get(key)
            return node.value if node is not None else None

    async def contains(self, key: K) -> bool:
        """
        Check if a key is in the available queue.

        Args:
            key: The key to check

        Returns:
            True if key is available, False otherwise
        """
        async with self._lock:
            return key in self._available

    async def available_keys(self) -> set[K]:
        """Return a set of all keys currently available (not in-flight)."""
        async with self._lock:
            return set(self._available.keys())

    async def inflight_keys(self) -> set[K]:
        """Return a set of all keys currently in-flight."""
        async with self._lock:
            return set(self._leases_by_key.keys())

    async def qsize(self) -> int:
        """Return the number of items currently available (not in-flight)."""
        async with self._lock:
            return len(self._list)

    async def inflight_size(self) -> int:
        """Return the number of items currently in-flight."""
        async with self._lock:
            return len(self._in_flight)

    async def _reaper_loop(self) -> None:
        """Background task that periodically checks for and releases expired leases."""
        check_count = 0
        while not self._closed:
            try:
                # Check first, then sleep (so we check immediately on start)
                async with self._lock:
                    check_count += 1
                    if self._closed:
                        break

                    now = time.monotonic()
                    expired: list[str] = []

                    # Find expired leases
                    for token, record in self._in_flight.items():
                        # DEBUG
                        # age = now - record.created_at
                        # timeout = record.timeout or 0
                        # print(f"[REAPER check #{check_count}] token={token[:8]}, age={age:.3f}, timeout={timeout:.3f}, expired={record.is_expired(now)}")
                        if record.is_expired(now):
                            expired.append(token)

                    # Release expired leases (requeue to front for retry)
                    for token in expired:
                        record = self._in_flight[token]
                        try:
                            await self._release_internal(record.lease, requeue_front=True)
                        except (InvalidLeaseError, LeaseAlreadyAcknowledgedError):
                            # Lease was already handled, ignore
                            pass

                    if expired:
                        self._cond_changed.notify_all()

                # Sleep before next check
                await asyncio.sleep(_REAPER_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception:
                # Log error and continue (in production, add logging)
                import traceback
                traceback.print_exc()
                pass
