"""GraphPulse-R: Certificate-Driven, Budgeted Reoptimization for Dynamic Delivery Routing."""

from graphpulse.dijkstra import dijkstra
from graphpulse.generators import (
    Update,
    apply_update,
    comb_adversarial,
    grid,
    hub_spoke,
    random_sparse,
    random_updates,
)
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
    "grid",
    "random_sparse",
    "hub_spoke",
    "comb_adversarial",
    "Update",
    "apply_update",
    "random_updates",
    "__version__",
]
