"""Shared pytest fixtures and the runner boilerplate.

photonn's version of this file supplied ready-made, schema-valid handoff payloads
-- ``d2nn_payload`` and ``mesh_payload``, a complete operating point per optical
model kind. Those were deleted here rather than adapted: they describe a schema
this repo does not have, and a fixture written before the contract it stands in
for is a fixture that has to be rewritten twice.

Their *shape* is worth carrying to plan 04, where the crossbar handoff is
written. photonn's note on them records why they grew: the fixtures once carried
``wavelength_m`` alone, which was all ``validate_handoff`` checked, so
"schema-valid payload" meant valid against a check covering one field of eleven.
A payload fixture has to be as complete as the thing it stands in for.
"""
from __future__ import annotations

import json
import subprocess

import numpy as np
import pytest

#: Fixed seeds are a project convention, and this one is inherited from photonn
#: unchanged -- there is no reason for the two repos' fixtures to diverge on it.
RNG_SEED = 20260723


@pytest.fixture
def rng():
    """A seeded NumPy Generator (seeds fixed and recorded per project convention)."""
    return np.random.default_rng(RNG_SEED)


def json_runner(*cmd: str, marker: str | None = None) -> dict:
    """Run a subprocess that prints one JSON object on stdout; return it parsed.

    Every out-of-process check in this suite has the same shape -- the runner
    exercises the code and reports facts, the assertions live in Python where a
    failure names something. photonn keeps a private copy of this boilerplate in
    each of its runner wrappers; this repo has three call sites already, which is
    one more than is worth duplicating.

    ``marker`` takes the JSON to be whatever follows that string, for a runner
    that does not own its stdout. The MATLAB harness needs it: ``mc.sweep``
    prints a progress line per magnitude and there is no suppressing it without
    editing an inherited file.
    """
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, (
        f"runner exited {proc.returncode}: {' '.join(cmd)}\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )
    payload = proc.stdout
    if marker is not None:
        _, seen, payload = payload.partition(marker)
        assert seen, (
            f"runner printed no {marker!r} marker, so it failed before reporting:\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )
    return json.loads(payload)
