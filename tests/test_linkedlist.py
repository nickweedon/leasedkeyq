"""Tests for the intrusive doubly-linked list implementation."""

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


def test_remove_from_middle_of_long_list() -> None:
    """Test removing nodes from various positions in a longer list."""
    lst = DoublyLinkedList[str, int]()
    nodes = [Node(f"key{i}", i) for i in range(10)]

    # Build a list of 10 nodes
    for node in nodes:
        lst.append(node)
    assert len(lst) == 10

    # Remove from middle (index 5)
    lst.remove(nodes[5])
    assert len(lst) == 9

    # Remove from position 2
    lst.remove(nodes[2])
    assert len(lst) == 8

    # Remove from position 7
    lst.remove(nodes[7])
    assert len(lst) == 7

    # Verify remaining nodes are in correct order
    expected_order = [0, 1, 3, 4, 6, 8, 9]
    for expected_idx in expected_order:
        popped = lst.popleft()
        assert popped is nodes[expected_idx]

    assert len(lst) == 0


def test_interleaved_append_remove_operations() -> None:
    """Test complex interleaved append and remove operations."""
    lst = DoublyLinkedList[str, int]()
    nodes = [Node(f"key{i}", i) for i in range(6)]

    # Add first 3 nodes
    lst.append(nodes[0])
    lst.append(nodes[1])
    lst.append(nodes[2])
    assert len(lst) == 3

    # Remove middle, then add more
    lst.remove(nodes[1])
    assert len(lst) == 2

    lst.append(nodes[3])
    lst.appendleft(nodes[4])
    assert len(lst) == 4

    # Remove from ends
    lst.remove(nodes[4])  # Was at front
    lst.remove(nodes[3])  # Was at back
    assert len(lst) == 2

    # Add more and verify order
    lst.appendleft(nodes[5])
    assert len(lst) == 3

    # Expected order: nodes[5], nodes[0], nodes[2]
    assert lst.popleft() is nodes[5]
    assert lst.popleft() is nodes[0]
    assert lst.popleft() is nodes[2]
    assert len(lst) == 0


def test_popleft_after_mixed_append_operations() -> None:
    """Test popleft behavior with mixed append and appendleft operations."""
    lst = DoublyLinkedList[str, int]()
    nodes = [Node(f"key{i}", i) for i in range(5)]

    # Build list with mixed operations: append, appendleft pattern
    lst.append(nodes[0])      # [0]
    lst.appendleft(nodes[1])  # [1, 0]
    lst.append(nodes[2])      # [1, 0, 2]
    lst.appendleft(nodes[3])  # [3, 1, 0, 2]
    lst.append(nodes[4])      # [3, 1, 0, 2, 4]

    assert len(lst) == 5

    # Pop and verify correct FIFO order based on mixed operations
    assert lst.popleft() is nodes[3]
    assert len(lst) == 4
    assert lst.popleft() is nodes[1]
    assert len(lst) == 3
    assert lst.popleft() is nodes[0]
    assert len(lst) == 2
    assert lst.popleft() is nodes[2]
    assert len(lst) == 1
    assert lst.popleft() is nodes[4]
    assert len(lst) == 0

    # Verify empty list behavior
    assert lst.popleft() is None
    assert len(lst) == 0


def test_stress_rapid_insertions_and_removals() -> None:
    """Test rapid insertions and removals maintaining consistency."""
    lst = DoublyLinkedList[str, int]()

    # Create a larger set of nodes
    nodes = [Node(f"key{i}", i) for i in range(50)]

    # Rapidly add first 30 nodes
    for i in range(30):
        if i % 2 == 0:
            lst.append(nodes[i])
        else:
            lst.appendleft(nodes[i])

    assert len(lst) == 30

    # Remove every third node
    for i in range(0, 30, 3):
        lst.remove(nodes[i])

    assert len(lst) == 20  # 30 - 10 = 20

    # Add 20 more nodes
    for i in range(30, 50):
        lst.append(nodes[i])

    assert len(lst) == 40

    # Pop 15 from the front
    for _ in range(15):
        result = lst.popleft()
        assert result is not None

    assert len(lst) == 25

    # Remove 5 specific nodes that weren't removed yet
    removable_indices = [2, 5, 8, 11, 14]
    for idx in removable_indices:
        if nodes[idx].prev is not None or nodes[idx].next is not None:
            lst.remove(nodes[idx])

    # Final count should reflect all operations
    # Started with 40 after additions, popped 15, potentially removed up to 5 more
    assert len(lst) <= 25
    assert len(lst) >= 20

    # Verify we can still pop all remaining items
    remaining = len(lst)
    for _ in range(remaining):
        assert lst.popleft() is not None

    assert len(lst) == 0
    assert not lst
