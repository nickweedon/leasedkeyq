# Claude Development Guide

Quick reference for Claude (or AI assistants) working on the leasedkeyq project.

## Project Overview

**leasedkeyq** is an asyncio-friendly in-memory queue combining FIFO semantics, dictionary-style keyed access, and lease-based exclusive processing with **O(1) operations**.

**Core Value Proposition**: Prevent duplicate processing in async workflows while maintaining FIFO ordering and supporting targeted key-based consumption.

## Architecture

### Key Components

1. **[DoublyLinkedList](src/leasedkeyq/linkedlist.py)** - Intrusive doubly-linked list with sentinel nodes
   - Direct node references enable O(1) removal by key
   - FIFO ordering maintained

2. **[LeasedKeyQueue](src/leasedkeyq/core.py)** - Main queue implementation
   - `_available: dict[K, Node[K, V]]` - Maps keys to list nodes
   - `_in_flight: dict[str, LeaseRecord]` - Active leases by token
   - `_leases_by_key: dict[K, str]` - Reverse index for O(1) key lookup
   - `_list: DoublyLinkedList[K, V]` - FIFO order

3. **[Lease Management](src/leasedkeyq/lease.py)** - Immutable lease tokens
   - Timeout tracking via `created_at` + `timeout`
   - Background reaper task auto-releases expired leases

### State Machine

Each key is in exactly one state:
- **ABSENT** → not in queue
- **AVAILABLE** → in queue, ready for consumption
- **IN_FLIGHT** → leased to consumer, temporarily inaccessible

### Critical Invariants

```python
# Must ALWAYS hold true
assert not (set(self._available.keys()) & set(self._leases_by_key.keys()))
assert len(self._in_flight) == len(self._leases_by_key)
assert all(key in self._available for key in self._available)
```

## Common Operations

### Producer API
```python
# Add/update item
await queue.put(key, value)

# Handle in-flight conflicts
await queue.put(key, value, if_in_flight="update")   # Update in-flight value
await queue.put(key, value, if_in_flight="reject")   # Raise error
await queue.put(key, value, if_in_flight="buffer")   # Enqueue duplicate
```

### Consumer API
```python
# FIFO consumption
key, value, lease = await queue.get(timeout=10.0, lease_timeout=30.0)

# Targeted consumption (waits for specific key)
key, value, lease = await queue.take("important-key", timeout=10.0)

# Lease control
await queue.ack(lease)                              # Permanent removal
await queue.release(lease, requeue_front=True)      # Retry (front of queue)
```

### Lifecycle
```python
# Recommended: use context manager
async with LeasedKeyQueue[str, dict](default_lease_timeout=30.0) as queue:
    # Queue automatically started and cleaned up
    pass

# Manual lifecycle
queue = LeasedKeyQueue[str, dict](default_lease_timeout=30.0)
await queue.start()  # Starts reaper task if timeout configured
# ... use queue ...
await queue.close()  # Returns in-flight items to available, cancels reaper
```

## Implementation Notes

### Timeout Reaper
- Runs every **0.1 seconds** (see `_REAPER_INTERVAL`)
- Only starts if `default_lease_timeout` set OR per-lease timeout used
- Auto-requeues expired leases to **front** for immediate retry
- Gracefully handles concurrent ack/release during expiration

### Concurrency
- All mutations under single `asyncio.Lock`
- State changes notify `asyncio.Condition` (wakes waiters)
- Cancellation-safe blocking in `get()` and `take()`
- Thread-unsafe: use within single event loop only

### Performance
- **O(1)**: put, get, take, ack, release, peek, contains
- Memory: ~100 bytes per available item, ~150 bytes per in-flight item
- Lock contention: Minimize work under lock; reaper holds lock briefly

## Testing Strategy

See [Testing Guide](docs/TESTING.md) for comprehensive test patterns.

**Quick test categories:**
- `test_linkedlist.py` - Data structure correctness
- `test_core_basic.py` - Put/get/ack operations
- `test_core_blocking.py` - Async waiting behavior
- `test_core_inflight.py` - Lease management
- `test_timeout.py` - Reaper task and expiration
- `test_concurrency.py` - Race conditions

## Common Modification Patterns

### Adding New Queue Method
1. Add method signature to `LeasedKeyQueue` class
2. Acquire lock: `async with self._lock:`
3. Check if closed: `if self._closed: raise QueueClosedError(...)`
4. Perform operation maintaining invariants
5. Notify waiters if state changed: `self._cond_changed.notify_all()`
6. Add tests in appropriate `test_core_*.py` file

### Modifying Timeout Behavior
1. Change `_REAPER_INTERVAL` constant (currently 0.1s)
2. Update `_reaper_loop()` logic in [core.py:392](src/leasedkeyq/core.py#L392)
3. Update tests in `test_timeout.py` with new timing assumptions
4. Update docs mentioning timeout precision

### Changing In-Flight Policies
1. Update `InFlightPolicy` type in [types.py](src/leasedkeyq/types.py)
2. Modify `put()` method's in-flight handling in [core.py:91](src/leasedkeyq/core.py#L91)
3. Add tests in `test_core_basic.py`
4. Update API docs in [docs/README.md](docs/README.md)

## Development Workflow

### Claude Code Commands (Recommended)
```bash
# Complete build process (lint, typecheck, test, build package)
/build

# Create release (auto-increment patch version)
/release

# Create release with specific version
/release 1.2.3
```

### Manual Commands
```bash
# Setup
pip install -e ".[dev]"

# Run all checks (recommended before commit)
make all  # Runs lint, typecheck, test

# Individual checks
make lint       # ruff check src/ tests/
make typecheck  # mypy src/
make test       # pytest with coverage

# Release
./release.sh [VERSION]  # Auto-increments if VERSION omitted
```

See [.claude/commands/README.md](.claude/commands/README.md) for command details.

## Code Style Guidelines

- **Type hints**: 100% coverage, strict mypy mode
- **Docstrings**: All public methods with Args/Returns/Raises
- **Line length**: 100 characters (ruff enforced)
- **Naming**:
  - Public: `snake_case`
  - Private: `_snake_case`
  - Internal state: `self._lock`, `self._available`, etc.
- **Async**: Always use `async def` for I/O, even if just acquiring lock
- **Error handling**: Specific exceptions over generic `Exception`

## Critical Files

- [src/leasedkeyq/core.py](src/leasedkeyq/core.py) - Main implementation (437 lines)
- [src/leasedkeyq/linkedlist.py](src/leasedkeyq/linkedlist.py) - O(1) data structure
- [pyproject.toml](pyproject.toml) - Dependencies, build config, tool settings
- [.github/workflows/test.yml](.github/workflows/test.yml) - CI pipeline

## Additional Resources

- **[API Documentation](docs/README.md)** - Complete API reference with examples
- **[Design Specification](docs/DESIGN.md)** - Original design rationale
- **[Testing Guide](docs/TESTING.md)** - Test patterns and fixtures
- **[Contributing Guide](docs/CONTRIBUTING.md)** - PR process and conventions
- **[Examples](examples/)** - Working code examples

## Quick Debugging

```python
# Check queue state
print(f"Available: {await queue.qsize()}")
print(f"In-flight: {await queue.inflight_size()}")
print(f"Available keys: {await queue.available_keys()}")
print(f"In-flight keys: {await queue.inflight_keys()}")

# Check reaper status
print(f"Reaper running: {queue._reaper_task is not None}")
print(f"Queue closed: {queue._closed}")

# Verify invariants (internal)
async with queue._lock:
    assert not (set(queue._available.keys()) & set(queue._leases_by_key.keys()))
    assert len(queue._in_flight) == len(queue._leases_by_key)
```

## Known Limitations

1. **Not thread-safe** - Use within single asyncio event loop
2. **In-memory only** - No persistence across restarts
3. **Timeout precision** - ±0.1 seconds (reaper interval)
4. **No priority levels** - Pure FIFO (use multiple queues for priorities)
5. **No metrics/observability** - Add via custom wrapper

## When to Update This Guide

- New public API method added
- Architecture change (new data structure, threading model)
- Common debugging pattern discovered
- Breaking change to internal APIs
- New development tool or workflow

---

**Last Updated**: 2026-01-02 | **Version**: 0.1.0
