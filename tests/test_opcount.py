"""Tests for operation counting and counted heap (Milestone 1.1)."""

import pytest
from hypothesis import given, settings, strategies as st

from graphpulse.opcount import CountedHeap, OpCounter, OpSnapshot


def test_t11_01_initial_state():
    """T1.1-01: Initial state of OpCounter has all fields set to zero."""
    counter = OpCounter()
    assert counter.scan == 0
    assert counter.push == 0
    assert counter.pop == 0
    assert counter.queue == 0
    assert counter.dijkstra_work == 0
    assert counter.work == 0


def test_t11_02_push_and_pop_counting():
    """T1.1-02: CountedHeap tracks push and pop operations accurately."""
    counter = OpCounter()
    heap = CountedHeap[tuple[int, int]](counter)

    for i in range(5):
        heap.push((i, i))
    assert counter.push == 5
    assert counter.pop == 0

    popped = [heap.pop() for _ in range(3)]
    assert counter.push == 5
    assert counter.pop == 3
    assert len(heap) == 2
    assert popped == [(0, 0), (1, 1), (2, 2)]


@settings(max_examples=200)
@given(st.lists(st.tuples(st.integers(), st.integers()), min_size=0, max_size=100))
def test_t11_03_heap_order(items):
    """T1.1-03: Property test with 200 random lists ensuring min-heap ordering."""
    counter = OpCounter()
    heap = CountedHeap[tuple[int, int]](counter)

    for item in items:
        heap.push(item)

    assert counter.push == len(items)

    result = []
    while heap:
        result.append(heap.pop())

    assert counter.pop == len(items)
    # Check that popped items are in non-decreasing order
    assert result == sorted(items)


def test_t11_04_pop_from_empty():
    """T1.1-04: Popping from empty heap raises IndexError and leaves counters unchanged."""
    counter = OpCounter()
    heap = CountedHeap[int](counter)

    with pytest.raises(IndexError, match="empty"):
        heap.pop()

    assert counter.push == 0
    assert counter.pop == 0


def test_t11_05_equal_keys():
    """T1.1-05: Equal key tuples (5, 1) and (5, 2) can be pushed and popped without error."""
    counter = OpCounter()
    heap = CountedHeap[tuple[int, int]](counter)

    heap.push((5, 2))
    heap.push((5, 1))

    first = heap.pop()
    second = heap.pop()

    assert first == (5, 1)
    assert second == (5, 2)
    assert counter.push == 2
    assert counter.pop == 2


def test_t11_06_snapshot_delta():
    """T1.1-06: Snapshot delta captures only operations executed since the snapshot."""
    counter = OpCounter(scan=10, push=5, pop=4, queue=2)
    s1 = counter.snapshot()

    assert s1.scan == 10
    assert s1.push == 5
    assert s1.pop == 4
    assert s1.queue == 2
    assert s1.dijkstra_work == 19
    assert s1.work == 21

    # Incur additional operations
    counter.scan += 7
    counter.push += 3
    counter.pop += 2
    counter.queue += 5

    delta = counter.since(s1)
    assert delta.scan == 7
    assert delta.push == 3
    assert delta.pop == 2
    assert delta.queue == 5
    assert delta.dijkstra_work == 12
    assert delta.work == 17


def test_t11_07_counter_independence():
    """T1.1-07: Independent counter instances do not share state."""
    c1 = OpCounter()
    c2 = OpCounter()

    c1.scan += 10
    c1.push += 5
    c1.pop += 2
    c1.queue += 1

    assert c2.scan == 0
    assert c2.push == 0
    assert c2.pop == 0
    assert c2.queue == 0
    assert c2.work == 0


def test_t11_08_work_definitions():
    """T1.1-08: Verify work definitions match SPEC.md (work - dijkstra_work == queue)."""
    counter = OpCounter(scan=12, push=8, pop=7, queue=15)
    assert counter.dijkstra_work == 12 + 8 + 7
    assert counter.work == 12 + 8 + 7 + 15
    assert counter.work - counter.dijkstra_work == counter.queue
