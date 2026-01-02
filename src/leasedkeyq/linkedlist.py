"""Intrusive doubly-linked list implementation for O(1) operations."""

from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class Node(Generic[K, V]):
    """A node in the doubly-linked list."""

    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: K, value: V) -> None:
        self.key = key
        self.value = value
        self.prev: Node[K, V] | None = None
        self.next: Node[K, V] | None = None


class DoublyLinkedList(Generic[K, V]):
    """Intrusive doubly-linked list with sentinel nodes for O(1) operations."""

    def __init__(self) -> None:
        # Sentinel nodes simplify edge cases
        self._head: Node[K, V] = Node(None, None)  # type: ignore[arg-type]
        self._tail: Node[K, V] = Node(None, None)  # type: ignore[arg-type]
        self._head.next = self._tail
        self._tail.prev = self._head
        self._size = 0

    def append(self, node: Node[K, V]) -> None:
        """Append node to the end of the list (before tail sentinel). O(1)."""
        node.prev = self._tail.prev
        node.next = self._tail
        if self._tail.prev is not None:
            self._tail.prev.next = node
        self._tail.prev = node
        self._size += 1

    def appendleft(self, node: Node[K, V]) -> None:
        """Prepend node to the beginning of the list (after head sentinel). O(1)."""
        node.prev = self._head
        node.next = self._head.next
        if self._head.next is not None:
            self._head.next.prev = node
        self._head.next = node
        self._size += 1

    def remove(self, node: Node[K, V]) -> None:
        """Remove a node from the list. O(1)."""
        if node.prev is not None:
            node.prev.next = node.next
        if node.next is not None:
            node.next.prev = node.prev
        node.prev = None
        node.next = None
        self._size -= 1

    def popleft(self) -> Node[K, V] | None:
        """Remove and return the first node (after head sentinel). O(1)."""
        if self._head.next == self._tail:
            return None
        node = self._head.next
        if node is not None:
            self.remove(node)
        return node

    def __len__(self) -> int:
        """Return the number of nodes in the list."""
        return self._size

    def __bool__(self) -> bool:
        """Return True if the list is non-empty."""
        return self._size > 0
