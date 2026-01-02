# leasedkeyq API Documentation

Complete API reference for the leasedkeyq async keyed leased queue library.

## Table of Contents

- [LeasedKeyQueue](#leasedkeyqueue)
- [Lease](#lease)
- [Exceptions](#exceptions)
- [Type Definitions](#type-definitions)
- [Usage Patterns](#usage-patterns)

## LeasedKeyQueue

The main queue class providing FIFO semantics with keyed access and lease-based exclusive processing.

### Constructor

```python
LeasedKeyQueue[K, V](*, default_lease_timeout: float | None = None)
```

**Parameters:**
- `default_lease_timeout`: Optional default timeout in seconds for all leases. If set, a background reaper task will automatically release expired leases.

**Type Parameters:**
- `K`: Key type (must be hashable)
- `V`: Value type

**Example:**
```python
# No timeout
queue = LeasedKeyQueue[str, dict]()

# With 30-second default timeout
queue = LeasedKeyQueue[str, dict](default_lease_timeout=30.0)
```

### Lifecycle Methods

#### start()
```python
async def start() -> None
```

Start background tasks (lease timeout reaper if needed). Automatically called when using as context manager.

#### close()
```python
async def close() -> None
```

Stop background tasks and cleanup. Returns all in-flight items to available queue. Automatically called when exiting context manager.

#### Context Manager
```python
async with LeasedKeyQueue[K, V](...) as queue:
    # Use queue
    ...
# Automatically closed
```

### Producer API

#### put()
```python
async def put(
    key: K,
    value: V,
    *,
    if_in_flight: InFlightPolicy = "update"
) -> None
```

Put a key-value pair into the queue.

**Parameters:**
- `key`: Unique key for the item
- `value`: Value to store
- `if_in_flight`: Policy when key is currently in-flight:
  - `"update"` (default): Update the in-flight value
  - `"reject"`: Raise `KeyAlreadyInFlightError`
  - `"buffer"`: Enqueue a second copy to available

**Raises:**
- `KeyAlreadyInFlightError`: If key is in-flight and `if_in_flight="reject"`
- `QueueClosedError`: If queue is closed

**Behavior:**
- If key is **absent**: Adds to available queue
- If key is **available**: Updates the value
- If key is **in-flight**: Follows `if_in_flight` policy

### Consumer API

#### get()
```python
async def get(
    timeout: float | None = None,
    *,
    lease_timeout: float | None = None
) -> tuple[K, V, Lease[K]]
```

Get the next item from the queue (FIFO order). Blocks until an item is available.

**Parameters:**
- `timeout`: Maximum time to wait for an item (None = wait forever)
- `lease_timeout`: Timeout for this specific lease (overrides `default_lease_timeout`)

**Returns:**
- Tuple of `(key, value, lease)`

**Raises:**
- `asyncio.TimeoutError`: If timeout expires before item available
- `QueueClosedError`: If queue is closed

#### take()
```python
async def take(
    key: K,
    timeout: float | None = None,
    *,
    lease_timeout: float | None = None
) -> tuple[K, V, Lease[K]]
```

Take a specific key from the queue. Blocks until the key is available (not in-flight).

**Parameters:**
- `key`: The specific key to retrieve
- `timeout`: Maximum time to wait for the key (None = wait forever)
- `lease_timeout`: Timeout for this specific lease (overrides `default_lease_timeout`)

**Returns:**
- Tuple of `(key, value, lease)`

**Raises:**
- `asyncio.TimeoutError`: If timeout expires before key available
- `QueueClosedError`: If queue is closed

### Lease Control

#### ack()
```python
async def ack(lease: Lease[K]) -> None
```

Acknowledge a lease, permanently removing the item from the queue.

**Parameters:**
- `lease`: The lease to acknowledge

**Raises:**
- `InvalidLeaseError`: If lease is unknown
- `LeaseAlreadyAcknowledgedError`: If lease was already acknowledged
- `QueueClosedError`: If queue is closed

#### release()
```python
async def release(lease: Lease[K], *, requeue_front: bool = False) -> None
```

Release a lease, returning the item to the queue.

**Parameters:**
- `lease`: The lease to release
- `requeue_front`: If `True`, add to front of queue; otherwise add to back

**Raises:**
- `InvalidLeaseError`: If lease is unknown
- `LeaseAlreadyAcknowledgedError`: If lease was already acknowledged
- `QueueClosedError`: If queue is closed

**Note:** If the key was buffered while in-flight, release does not duplicate the item.

### Introspection Methods

#### peek()
```python
async def peek(key: K) -> V | None
```

Peek at the value for a key in the available queue without removing it.

**Returns:** The value if key is available, `None` otherwise

#### contains()
```python
async def contains(key: K) -> bool
```

Check if a key is in the available queue.

**Returns:** `True` if key is available, `False` otherwise

#### available_keys()
```python
async def available_keys() -> set[K]
```

Return a set of all keys currently available (not in-flight).

#### inflight_keys()
```python
async def inflight_keys() -> set[K]
```

Return a set of all keys currently in-flight.

#### qsize()
```python
async def qsize() -> int
```

Return the number of items currently available (not in-flight).

#### inflight_size()
```python
async def inflight_size() -> int
```

Return the number of items currently in-flight.

## Lease

Immutable lease token representing exclusive access to a keyed item.

```python
@dataclass(frozen=True)
class Lease(Generic[K]):
    token: str  # UUID-based unique identifier
    key: K
```

Leases are created automatically by `get()` and `take()`. You should not create them manually.

## Exceptions

### LeasedKeyQError
Base exception for all leasedkeyq errors.

### KeyAlreadyInFlightError
Raised when attempting to put a key that is currently in-flight with `if_in_flight='reject'`.

### InvalidLeaseError
Raised when an invalid or unknown lease token is provided.

### LeaseAlreadyAcknowledgedError
Raised when attempting to ack or release a lease that was already acknowledged.

### QueueClosedError
Raised when operations are attempted on a closed queue.

## Type Definitions

### InFlightPolicy
```python
InFlightPolicy = Literal["update", "reject", "buffer"]
```

Policy for handling `put()` when a key is currently in-flight.

## Usage Patterns

### Basic Producer-Consumer

```python
async with LeasedKeyQueue[str, dict]() as queue:
    # Producer
    await queue.put("task-1", {"action": "process"})

    # Consumer
    key, value, lease = await queue.get()
    try:
        await process(value)
        await queue.ack(lease)
    except Exception:
        await queue.release(lease, requeue_front=True)
```

### Targeted Consumption

```python
# Wait for specific key
key, value, lease = await queue.take("important-task")
await process_important(value)
await queue.ack(lease)
```

### Lease Timeouts

```python
# Queue with default 30s timeout
async with LeasedKeyQueue[str, int](default_lease_timeout=30.0) as queue:
    await queue.put("task", 123)

    # Get with custom 60s timeout for this lease
    key, value, lease = await queue.get(lease_timeout=60.0)

    # If not acked within timeout, automatically re-queued to front
```

### Multiple Consumers

```python
async def worker(queue: LeasedKeyQueue[str, dict], name: str) -> None:
    while True:
        try:
            key, value, lease = await queue.get(timeout=1.0)
            print(f"Worker {name} processing {key}")
            await process(value)
            await queue.ack(lease)
        except asyncio.TimeoutError:
            break

# Run multiple workers
async with LeasedKeyQueue[str, dict]() as queue:
    # Add work
    for i in range(100):
        await queue.put(f"task-{i}", {"id": i})

    # Process with workers
    await asyncio.gather(
        worker(queue, "A"),
        worker(queue, "B"),
        worker(queue, "C"),
    )
```

### In-Flight Policies

```python
# Update in-flight value
await queue.put("key", old_value)
_, _, lease = await queue.get()
await queue.put("key", new_value, if_in_flight="update")
await queue.release(lease)
_, updated, _ = await queue.get()  # Gets new_value

# Reject if in-flight
await queue.put("key", value)
_, _, lease = await queue.get()
try:
    await queue.put("key", value, if_in_flight="reject")
except KeyAlreadyInFlightError:
    print("Key is being processed")

# Buffer second copy
await queue.put("key", 1)
_, _, lease = await queue.get()
await queue.put("key", 2, if_in_flight="buffer")
# Now both copies exist: one in-flight, one available
```

### Error Handling

```python
async def safe_process(queue: LeasedKeyQueue[str, dict]) -> None:
    key, value, lease = await queue.get()

    try:
        result = await risky_operation(value)
        await queue.ack(lease)
    except TemporaryError:
        # Retry later
        await queue.release(lease, requeue_front=False)
    except PermanentError:
        # Don't retry, but log
        await queue.ack(lease)
        log_error(key, value)
```

## Performance Characteristics

All operations are **O(1)**:
- `put()`: O(1)
- `get()`: O(1)
- `take(key)`: O(1) - achieved through direct node references
- `ack()`: O(1)
- `release()`: O(1)
- `peek()`: O(1)
- `contains()`: O(1)

The queue uses an intrusive doubly-linked list internally, allowing constant-time removal even for keyed access.

## Thread Safety

The queue is **not thread-safe** and should only be used within a single asyncio event loop. For multi-threaded access, use appropriate synchronization primitives.

## Best Practices

1. **Always use context manager** to ensure proper cleanup
2. **Set appropriate timeouts** to prevent stuck items
3. **Use `requeue_front=True`** for transient failures
4. **Use `if_in_flight="reject"`** when duplicates are unacceptable
5. **Monitor `inflight_size()`** to detect processing bottlenecks
6. **Avoid very short timeouts** (reaper runs every 1 second)
