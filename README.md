# leasedkeyq

**Async Keyed Leased Queue** - An asyncio-friendly in-memory queue combining FIFO semantics, dictionary-style keyed access, and lease-based exclusive processing.

[![Python Version](https://img.shields.io/pypi/pyversions/leasedkeyq)](https://pypi.org/project/leasedkeyq/)
[![PyPI Version](https://img.shields.io/pypi/v/leasedkeyq)](https://pypi.org/project/leasedkeyq/)
[![License](https://img.shields.io/github/license/yourusername/leasedkeyq)](LICENSE)

## Features

- **FIFO Queue Semantics**: Process items in order with `get()`
- **Keyed Access**: Target specific items with `take(key)`
- **Lease-Based Processing**: Exclusive access with explicit `ack`/`release`
- **O(1) Operations**: Constant-time enqueue, dequeue, and key-based removal
- **Automatic Timeouts**: Optional lease expiration with auto-retry
- **Blocking Behavior**: Async waiting for items or specific keys
- **Type Safe**: Full type hints with strict mypy compliance
- **Zero Dependencies**: Pure Python stdlib implementation

## Installation

```bash
pip install leasedkeyq
```

## Quick Start

```python
import asyncio
from leasedkeyq import LeasedKeyQueue

async def main():
    # Create queue with 30-second lease timeout
    async with LeasedKeyQueue[str, dict](default_lease_timeout=30.0) as queue:
        # Producer: add items
        await queue.put("task-1", {"action": "process", "data": 123})
        await queue.put("task-2", {"action": "send", "data": 456})

        # Consumer: FIFO consumption
        key, value, lease = await queue.get()
        print(f"Processing {key}: {value}")

        try:
            # Do work...
            await process(value)
            # Success: acknowledge
            await queue.ack(lease)
        except Exception:
            # Failure: release for retry
            await queue.release(lease, requeue_front=True)

        # Targeted consumption
        key, value, lease = await queue.take("task-2")
        print(f"Specifically got {key}: {value}")
        await queue.ack(lease)

asyncio.run(main())
```

## Core Concepts

### States

Each key is in exactly one state:
- **ABSENT**: Not in queue
- **AVAILABLE**: Ready for consumption
- **IN_FLIGHT**: Leased to a consumer

### API Overview

**Producer API**
```python
await queue.put(key, value, if_in_flight="update")  # update|reject|buffer
```

**Consumer API**
```python
# FIFO consumption
key, value, lease = await queue.get(timeout=10.0, lease_timeout=30.0)

# Keyed consumption
key, value, lease = await queue.take("specific-key", timeout=10.0)
```

**Lease Control**
```python
await queue.ack(lease)                              # Permanent removal
await queue.release(lease, requeue_front=True)      # Retry
```

**Introspection**
```python
value = await queue.peek("key")
has_key = await queue.contains("key")
keys = await queue.available_keys()
inflight = await queue.inflight_keys()
size = await queue.qsize()
```

## In-Flight Policies

Control behavior when putting a key that's currently leased:

- **`update`** (default): Update the in-flight value
- **`reject`**: Raise `KeyAlreadyInFlightError`
- **`buffer`**: Enqueue a second copy to available

```python
await queue.put("key", new_value, if_in_flight="update")
```

## Lease Timeouts

Prevent stuck items with automatic lease expiration:

```python
# Queue-wide default timeout
queue = LeasedKeyQueue[str, int](default_lease_timeout=30.0)
await queue.start()

# Per-lease override
key, value, lease = await queue.get(lease_timeout=60.0)
```

Expired leases are automatically released to the front of the queue for retry.

## Complexity Guarantees

| Operation | Time Complexity |
|-----------|----------------|
| `put()`   | O(1)           |
| `get()`   | O(1)           |
| `take(key)` | O(1)         |
| `ack()`   | O(1)           |
| `release()` | O(1)         |

Achieved through intrusive doubly-linked list with direct node references.

## Use Cases

- **Task Queues**: FIFO processing with retry on failure
- **Job Scheduling**: Target specific jobs while maintaining order
- **Rate Limiting**: Lease-based exclusive access prevents double-processing
- **Event Processing**: Handle events by ID with guaranteed exclusivity
- **Workflow Engines**: Track in-flight work with timeout-based recovery

## Documentation

- [API Documentation](docs/README.md)
- [Design Specification](docs/DESIGN.md)
- [Examples](examples/)

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/ tests/
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please open an issue or PR on GitHub.
