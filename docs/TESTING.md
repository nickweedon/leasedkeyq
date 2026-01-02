# Testing Guide

Comprehensive guide for testing leasedkeyq.

## Test Organization

### Test Files by Category

1. **test_linkedlist.py** - Data structure correctness
   - Node creation and linking
   - O(1) operations (append, appendleft, remove, popleft)
   - Edge cases: empty list, single node, sentinel integrity

2. **test_lease.py** - Lease management
   - Lease creation and immutability
   - LeaseRecord state tracking
   - Timeout expiration logic

3. **test_core_basic.py** - Basic queue operations
   - put() with different states (absent, available, in-flight)
   - In-flight policies: update, reject, buffer
   - Introspection: peek(), contains(), available_keys()

4. **test_core_blocking.py** - Async blocking behavior
   - get() blocking until items available
   - take(key) blocking until key available
   - Timeout behavior with asyncio.wait_for()
   - Cancellation safety

5. **test_core_inflight.py** - Lease control
   - ack() removing items permanently
   - release() with requeue_front=True/False
   - Double ack/release error handling
   - In-flight tracking

6. **test_timeout.py** - Lease timeouts
   - Lease expiration and auto-release
   - Reaper task lifecycle (start/close)
   - Per-lease timeout overrides
   - Context manager cleanup

7. **test_concurrency.py** - Concurrent access
   - Multiple producers/consumers
   - Race conditions
   - State consistency under load

## Common Test Patterns

### Basic Test Structure
```python
@pytest.mark.asyncio
async def test_operation() -> None:
    """Test description."""
    queue = LeasedKeyQueue[str, int]()

    # Setup
    await queue.put("key", 100)

    # Execute
    key, value, lease = await queue.get()

    # Assert
    assert key == "key"
    assert value == 100

    # Cleanup
    await queue.close()
```

### Context Manager Pattern
```python
@pytest.mark.asyncio
async def test_with_timeout() -> None:
    """Test with automatic cleanup."""
    async with LeasedKeyQueue[str, int](default_lease_timeout=1.0) as queue:
        await queue.put("key", 100)
        # Queue auto-closed on exit
```

### Timeout Testing
```python
@pytest.mark.asyncio
async def test_timeout() -> None:
    """Test operation timeout."""
    queue = LeasedKeyQueue[str, int]()

    with pytest.raises(asyncio.TimeoutError):
        await queue.get(timeout=0.1)
```

### Concurrent Testing
```python
@pytest.mark.asyncio
async def test_concurrent_consumers() -> None:
    """Test multiple consumers."""
    queue = LeasedKeyQueue[str, int]()
    results = []

    async def consumer() -> None:
        while True:
            try:
                key, value, lease = await queue.get(timeout=0.1)
                results.append(value)
                await queue.ack(lease)
            except asyncio.TimeoutError:
                break

    # Add items
    for i in range(10):
        await queue.put(f"key-{i}", i)

    # Run consumers
    await asyncio.gather(consumer(), consumer(), consumer())

    assert len(results) == 10
```

## Test Fixtures

### Queue Fixtures
```python
import pytest
from leasedkeyq import LeasedKeyQueue

@pytest.fixture
async def queue() -> LeasedKeyQueue[str, int]:
    """Provide a clean queue instance."""
    q = LeasedKeyQueue[str, int]()
    yield q
    await q.close()

@pytest.fixture
async def queue_with_timeout() -> LeasedKeyQueue[str, int]:
    """Provide a queue with timeout configured."""
    async with LeasedKeyQueue[str, int](default_lease_timeout=1.0) as q:
        yield q
```

### Data Fixtures
```python
@pytest.fixture
def sample_items() -> list[tuple[str, int]]:
    """Provide sample test data."""
    return [
        ("task-1", 100),
        ("task-2", 200),
        ("task-3", 300),
    ]
```

## Testing Invariants

### Verify State Consistency
```python
async def assert_invariants(queue: LeasedKeyQueue) -> None:
    """Verify queue invariants hold."""
    async with queue._lock:
        # No key in both available and in-flight
        assert not (set(queue._available.keys()) & set(queue._leases_by_key.keys()))

        # In-flight maps are consistent
        assert len(queue._in_flight) == len(queue._leases_by_key)

        # All available keys have nodes
        assert all(key in queue._available for key in queue._available)
```

## Coverage Goals

- **Line coverage**: >95%
- **Branch coverage**: >90%
- **Critical paths**: 100% (lease management, state transitions)

## Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_core_basic.py

# Specific test
pytest tests/test_core_basic.py::test_put_and_get

# With coverage
pytest --cov=leasedkeyq --cov-report=html

# Verbose
pytest -v

# Stop on first failure
pytest -x
```

## Debugging Failed Tests

### Add Debug Output
```python
@pytest.mark.asyncio
async def test_debug() -> None:
    queue = LeasedKeyQueue[str, int]()

    print(f"Before: qsize={await queue.qsize()}")
    await queue.put("key", 100)
    print(f"After put: qsize={await queue.qsize()}")

    # Use pytest -s to see output
```

### Inspect Queue State
```python
# Check internal state
print(f"Available: {queue._available}")
print(f"In-flight: {queue._in_flight}")
print(f"Leases by key: {queue._leases_by_key}")
print(f"List size: {len(queue._list)}")
```

### Timing Issues
```python
# If test is flaky due to timing
await asyncio.sleep(0.01)  # Give event loop time to process
```

## Common Test Scenarios

### Test Release vs Ack
```python
@pytest.mark.asyncio
async def test_release_vs_ack() -> None:
    """Verify release returns item, ack removes it."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key", 100)

    # Test release
    _, _, lease1 = await queue.get()
    await queue.release(lease1)
    assert await queue.qsize() == 1  # Back in queue

    # Test ack
    _, _, lease2 = await queue.get()
    await queue.ack(lease2)
    assert await queue.qsize() == 0  # Removed
```

### Test In-Flight Policies
```python
@pytest.mark.asyncio
async def test_inflight_policies() -> None:
    """Test all three in-flight policies."""
    queue = LeasedKeyQueue[str, int]()
    await queue.put("key", 100)
    _, _, lease = await queue.get()

    # Update
    await queue.put("key", 200, if_in_flight="update")
    await queue.release(lease)
    _, value, _ = await queue.get()
    assert value == 200

    # Reject
    _, _, lease = await queue.get()
    with pytest.raises(KeyAlreadyInFlightError):
        await queue.put("key", 300, if_in_flight="reject")

    # Buffer
    await queue.put("key", 300, if_in_flight="buffer")
    assert await queue.qsize() == 1  # Buffered copy
```

## Performance Testing

```python
import time

@pytest.mark.asyncio
async def test_performance() -> None:
    """Verify O(1) operations scale."""
    queue = LeasedKeyQueue[str, int]()

    # Add 10k items
    start = time.monotonic()
    for i in range(10000):
        await queue.put(f"key-{i}", i)
    duration = time.monotonic() - start

    # Should be fast (< 1 second)
    assert duration < 1.0

    # Take by key should still be O(1)
    start = time.monotonic()
    await queue.take("key-5000")
    duration = time.monotonic() - start

    assert duration < 0.01  # Very fast
```

## Continuous Integration

Tests run automatically on:
- Push to main branch
- Pull requests
- Python versions: 3.10, 3.11, 3.12

See [.github/workflows/test.yml](../.github/workflows/test.yml) for CI configuration.
