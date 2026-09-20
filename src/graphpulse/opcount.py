"""Machine-independent operation counting and counted heap (Milestone 1.1)."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class OpSnapshot:
    """Immutable point-in-time snapshot or delta of an OpCounter."""

    scan: int
    push: int
    pop: int
    queue: int

    @property
    def dijkstra_work(self) -> int:
        """Total operations performed in Dijkstra tree construction (SCAN + PUSH + POP)."""
        return self.scan + self.push + self.pop

    @property
    def work(self) -> int:
        """Total operations performed across all algorithms (SCAN + PUSH + POP + QUEUE)."""
        return self.scan + self.push + self.pop + self.queue


class OpCounter:
    """Explicit machine-independent operation counter.

    Charges are categorized into:
    - scan: adjacency entry inspections and O(1) certificate checks
    - push: heap push operations
    - pop: heap pop operations (including stale entries)
    - queue: FIFO queue enqueues and dequeues during affected-set propagation
    """

    __slots__ = ("scan", "push", "pop", "queue")

    def __init__(self, scan: int = 0, push: int = 0, pop: int = 0, queue: int = 0) -> None:
        self.scan: int = scan
        self.push: int = push
        self.pop: int = pop
        self.queue: int = queue

    @property
    def dijkstra_work(self) -> int:
        """Total operations for Dijkstra rebuild (SCAN + PUSH + POP)."""
        return self.scan + self.push + self.pop

    @property
    def work(self) -> int:
        """Total machine-independent operations (SCAN + PUSH + POP + QUEUE)."""
        return self.scan + self.push + self.pop + self.queue

    def snapshot(self) -> OpSnapshot:
        """Capture an immutable point-in-time snapshot of current operation counts."""
        return OpSnapshot(
            scan=self.scan,
            push=self.push,
            pop=self.pop,
            queue=self.queue,
        )

    def since(self, snapshot: OpSnapshot) -> OpSnapshot:
        """Compute the operational delta incurred since a given snapshot."""
        return OpSnapshot(
            scan=self.scan - snapshot.scan,
            push=self.push - snapshot.push,
            pop=self.pop - snapshot.pop,
            queue=self.queue - snapshot.queue,
        )

    def __repr__(self) -> str:
        return (
            f"OpCounter(scan={self.scan}, push={self.push}, pop={self.pop}, queue={self.queue}, "
            f"work={self.work})"
        )


class CountedHeap(Generic[T]):
    """Min-heap wrapper around heapq that charges every push and pop to an explicit OpCounter."""

    __slots__ = ("_counter", "_data")

    def __init__(self, counter: OpCounter) -> None:
        self._counter: OpCounter = counter
        self._data: list[T] = []

    @property
    def counter(self) -> OpCounter:
        """Reference to the underlying operation counter."""
        return self._counter

    def push(self, item: T) -> None:
        """Push an item onto the heap and charge 1 PUSH."""
        self._counter.push += 1
        heapq.heappush(self._data, item)

    def pop(self) -> T:
        """Pop and return the smallest item from the heap and charge 1 POP.

        Raises IndexError if the heap is empty, without modifying the counter.
        """
        if not self._data:
            raise IndexError("pop from empty CountedHeap")
        self._counter.pop += 1
        return heapq.heappop(self._data)

    def peek(self) -> T:
        """Return the smallest item without popping or charging."""
        if not self._data:
            raise IndexError("peek from empty CountedHeap")
        return self._data[0]

    def __len__(self) -> int:
        return len(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)
