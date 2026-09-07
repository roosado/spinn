"""spinn — spintronic neural network simulator (design side).

Second platform in the physical-AI series. A weight is a magnetic state and the
sum is performed by Kirchhoff's law on a wire, where photonn's weight is an
etched phase and the sum is performed by interference.

Pure-NumPy crossbar physics plus thin PyTorch wrappers. Trains an idealized
crossbar classifier and serializes it across the one-directional HDF5 handoff to
the MATLAB as-built device-error model (see ``spinn-hw/``).

Nothing is exported yet: :mod:`spinn.export` and :mod:`spinn.handoff` are
photonn copies awaiting a crossbar operating point, so importing them here would
re-export photonn's optical schema. See ``plans/01-crossbar-comparable-core.md``.
"""
from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
