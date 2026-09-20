"""GraphPulse-R: Certificate-Driven, Budgeted Reoptimization for Dynamic Delivery Routing."""

from graphpulse.dijkstra import dijkstra
from graphpulse.graph import DiGraph
from graphpulse.opcount import CountedHeap, OpCounter, OpSnapshot
from graphpulse.verify import InvariantViolation, check_spt

__version__ = "0.1.0"
__all__ = [
    "DiGraph",
    "OpCounter",
    "OpSnapshot",
    "CountedHeap",
    "dijkstra",
    "check_spt",
    "InvariantViolation",
    "__version__",
]
