"""Tests for the intrusive doubly-linked list implementation."""

import pytest

from leasedkeyq.linkedlist import DoublyLinkedList, Node


def test_node_creation() -> None:
    """Test creating a node."""
    node = Node("key1", "value1")
    assert node.key == "key1"
    assert node.value == "value1"
    assert node.prev is None
    assert node.next is None


def test_empty_list() -> None:
    """Test empty list behavior."""
    lst = DoublyLinkedList[str, int]()
    assert len(lst) == 0
    assert not lst
    assert lst.popleft() is None


def test_append() -> None:
    """Test appending nodes."""
    lst = DoublyLinkedList[str, int]()
    node1 = Node("a", 1)
    node2 = Node("b", 2)

    lst.append(node1)
    assert len(lst) == 1
    assert bool(lst)

    lst.append(node2)
    assert len(lst) == 2

    # Check FIFO order
    popped = lst.popleft()
    assert popped is node1
    popped = lst.popleft()
    assert popped is node2
    assert len(lst) == 0


def test_appendleft() -> None:
    """Test prepending nodes."""
    lst = DoublyLinkedList[str, int]()
    node1 = Node("a", 1)
    node2 = Node("b", 2)

    lst.appendleft(node1)
    lst.appendleft(node2)

    # Should pop in reverse order
    popped = lst.popleft()
    assert popped is node2
    popped = lst.popleft()
    assert popped is node1


def test_remove() -> None:
    """Test removing nodes."""
    lst = DoublyLinkedList[str, int]()
    node1 = Node("a", 1)
    node2 = Node("b", 2)
    node3 = Node("c", 3)

    lst.append(node1)
    lst.append(node2)
    lst.append(node3)

    # Remove middle node
    lst.remove(node2)
    assert len(lst) == 2

    # Check remaining order
    assert lst.popleft() is node1
    assert lst.popleft() is node3

    # Remove from empty-ish list
    lst.append(node1)
    lst.remove(node1)
    assert len(lst) == 0


def test_remove_first() -> None:
    """Test removing the first node."""
    lst = DoublyLinkedList[str, int]()
    node1 = Node("a", 1)
    node2 = Node("b", 2)

    lst.append(node1)
    lst.append(node2)

    lst.remove(node1)
    assert len(lst) == 1
    assert lst.popleft() is node2


def test_remove_last() -> None:
    """Test removing the last node."""
    lst = DoublyLinkedList[str, int]()
    node1 = Node("a", 1)
    node2 = Node("b", 2)

    lst.append(node1)
    lst.append(node2)

    lst.remove(node2)
    assert len(lst) == 1
    assert lst.popleft() is node1


def test_popleft() -> None:
    """Test popping from the left."""
    lst = DoublyLinkedList[str, int]()
    node1 = Node("a", 1)
    node2 = Node("b", 2)

    lst.append(node1)
    lst.append(node2)

    popped = lst.popleft()
    assert popped is node1
    assert len(lst) == 1

    popped = lst.popleft()
    assert popped is node2
    assert len(lst) == 0

    popped = lst.popleft()
    assert popped is None


def test_mixed_operations() -> None:
    """Test mixed append/appendleft/remove operations."""
    lst = DoublyLinkedList[str, int]()
    node1 = Node("a", 1)
    node2 = Node("b", 2)
    node3 = Node("c", 3)
    node4 = Node("d", 4)

    lst.append(node1)
    lst.appendleft(node2)
    lst.append(node3)
    lst.appendleft(node4)

    # Order should be: node4, node2, node1, node3
    assert lst.popleft() is node4
    assert lst.popleft() is node2
    assert lst.popleft() is node1
    assert lst.popleft() is node3


def test_single_node() -> None:
    """Test operations on a single-node list."""
    lst = DoublyLinkedList[str, int]()
    node = Node("a", 1)

    lst.append(node)
    assert len(lst) == 1

    lst.remove(node)
    assert len(lst) == 0
    assert not lst


def test_node_cleanup_after_remove() -> None:
    """Test that removed nodes have their pointers cleared."""
    lst = DoublyLinkedList[str, int]()
    node = Node("a", 1)

    lst.append(node)
    lst.remove(node)

    assert node.prev is None
    assert node.next is None
