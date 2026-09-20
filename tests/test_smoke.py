"""Smoke tests for GraphPulse-R package initialization (Milestone 0.1)."""

import graphpulse


def test_import_and_version():
    """T0.1-02 / T0.1-03: Verify package imports and exposes __version__."""
    assert hasattr(graphpulse, "__version__")
    assert graphpulse.__version__ == "0.1.0"
