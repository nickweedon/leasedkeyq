This will be a python pip package. Look at ../mcp_mapped_resource_lib for examples on how this project should be packaged and set up to work with Google workflow. Also use a similar devcontainer setup as in this project.

# leasedkeyq — Async Keyed Leased Queue (Design Specification)

## Overview

`leasedkeyq` is an asyncio-friendly in-memory data structure combining:

- FIFO queue semantics
- Dictionary-style keyed access
- Leasing (in-flight) semantics with explicit `ack` / `release`
- Blocking `take(key)` that waits until a specific key becomes available
- **O(1)** removal and reinsertion using a hand-written intrusive doubly-linked list

This design avoids the O(n) penalty of `deque.remove(key)` by maintaining direct node references.

---

## Goals

1. FIFO ordering for general consumers
2. Key-based access for targeted consumers
3. Exclusive leasing to prevent concurrent access
4. Blocking behavior for both FIFO and key-based consumers
5. O(1) operations for enqueue, dequeue, take-by-key, release

Non-goals:
- Cross-process persistence
- Distributed coordination
- Hard real-time guarantees

---

## Core States

Each key is always in exactly one state:

- **ABSENT** – not present in the queue
- **AVAILABLE** – present and eligible for consumption
- **IN_FLIGHT** – leased to a consumer and temporarily inaccessible

---

## Internal Data Structures

### 1. Available Map

```text
available: dict[key, Node]
```

Maps keys to linked-list nodes representing available items.

### 2. In-Flight Map

```text
in_flight: dict[lease_token, LeaseRecord]
```

Tracks active leases.

### 3. Optional Reverse Lease Index

```text
leases_by_key: dict[key, lease_token]
```

Allows O(1) lookup of whether a key is in-flight.

### 4. Intrusive Doubly-Linked List

Maintains FIFO order of available items.

Each `Node` contains:
- key
- value
- prev pointer
- next pointer

Sentinel head and tail nodes simplify edge cases.

### 5. Synchronization

- `asyncio.Lock`
- `asyncio.Condition` (`cond_changed`) for blocking waiters

---

## Linked List Operations (O(1))

- append(node)
- appendleft(node)
- remove(node)
- popleft()

Because `available[key]` points directly to the node, removals are constant time.

---

## Public API

### Producer

```python
await put(key, value, *, if_in_flight="update|reject|buffer")
```

Behavior:
- ABSENT → enqueue
- AVAILABLE → update value
- IN_FLIGHT → policy-based handling

---

### Consumers

#### FIFO

```python
await get(timeout=None) -> (key, value, lease)
```

#### Keyed

```python
await take(key, timeout=None) -> (key, value, lease)
```

Blocks while the key is in-flight or absent.

---

### Lease Control

```python
await ack(lease)
await release(lease, requeue_front=False)
```

- `ack` permanently removes the item
- `release` re-enqueues it

---

### Introspection (Available Only)

```python
await peek(key)
await contains(key)
await available_keys()
await inflight_keys()
await qsize()
await inflight_size()
```

---

## Blocking Semantics

- `get()` waits until the linked list is non-empty
- `take(key)` waits until the key is present in `available`
- All state changes call `cond_changed.notify_all()`

---

## Concurrency Guarantees

- All mutations occur under a single asyncio lock
- No partial state transitions
- Cancellation-safe waiting
- No lost wakeups

---

## Complexity Guarantees

| Operation        | Complexity |
|------------------|------------|
| put (new key)    | O(1)       |
| put (update)     | O(1)       |
| get              | O(1)       |
| take(key)        | O(1)       |
| release          | O(1)       |
| ack              | O(1)       |

---

## Optional Extensions

- Lease timeouts with background reaper task
- Per-key conditions for reduced wakeups
- Priority queues
- Retry counters and backoff
- Metrics hooks

---

## Suggested Package Layout

```text
leasedkeyq/
├── core.py          # main queue + lease logic
├── linkedlist.py    # Node + DoublyLinkedList
├── errors.py
├── typing.py
├── __init__.py
└── tests/
```

---

## Invariants (Must Always Hold)

- Each available key has exactly one node in the list
- No key is both available and in-flight
- Each lease token maps to exactly one key
- Linked list contains only available nodes

---

## Summary

`leasedkeyq` provides a clean, efficient abstraction for async workflows that need:
- FIFO scheduling
- Key-level exclusivity
- Safe retries
- High performance under contention

It fills a gap not currently addressed by existing asyncio queue libraries.
