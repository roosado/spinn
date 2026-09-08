"""Reading the design -> as-built handoff back, from Python.

:mod:`spinn.export` writes the file and MATLAB reads it. Python reads it too --
for the round-trip test, and so that "what did we hand over?" is answerable without
opening HDF5 by hand -- but it never writes back through this path. There is one
writer and one reader per side, and that is the whole contract.

The reader is deliberately strict in the same way the writer is. Nothing here
supplies a default for a missing field: a default is indistinguishable from a
correct value downstream, which is how a renamed field becomes a plausible wrong
answer instead of a stack trace.
"""
from __future__ import annotations

from dataclasses import dataclass

import h5py
import numpy as np

from spinn.crossbar import Crossbar
from spinn.export import (
    MODEL_TYPES,
    OPERATING_POINT,
    SIGNED_SCHEME_NAMES,
    SUPPORTED_SCHEMAS,
    _as_str,
)


@dataclass(frozen=True)
class Handoff:
    """The metadata half of a handoff file: everything except the big arrays."""

    path: str
    schema_version: str
    model_type: str
    description: str
    test_acc: float | None
    n_rows: int
    n_cols: int
    devices_per_weight: int
    operating_point: dict

    def constant(self, name: str) -> float:
        """One operating-point constant, by manifest name.

        Raises rather than returning a default, and says what the constant is for
        when the name is not one the manifest knows.
        """
        if name not in OPERATING_POINT:
            known = ", ".join(sorted(OPERATING_POINT))
            raise KeyError(f"{name!r} is not an operating-point field. Known: {known}")
        if name not in self.operating_point:
            raise KeyError(
                f"{name!r} is missing from {self.path}. "
                f"{OPERATING_POINT[name].doc}"
            )
        return self.operating_point[name]

    @property
    def scheme(self) -> str:
        """The signed-weight scheme, as a name rather than a code."""
        code = int(self.constant("signed_scheme_code"))
        if code not in SIGNED_SCHEME_NAMES:
            raise ValueError(f"unknown signed_scheme_code {code} in {self.path}")
        return SIGNED_SCHEME_NAMES[code]

    @property
    def n_devices(self) -> int:
        return self.n_rows * self.n_cols * self.devices_per_weight

    def crossbar(self, states: int | None = None) -> Crossbar:
        """Rebuild the array this handoff describes.

        ``states`` is not carried by the file, deliberately: how many levels a
        device resolves is an as-built property and belongs in the error config, not
        in the ideal design the handoff records.
        """
        return Crossbar(
            n_inputs=self.n_rows,
            n_outputs=self.n_cols,
            scheme=self.scheme,
            states=states,
            g_min=self.constant("g_min_s"),
            g_max=self.constant("g_max_s"),
            read_voltage=self.constant("read_voltage_v"),
        )


def read_handoff(path) -> Handoff:
    """Read a handoff's metadata, checking it against the schema on the way in."""
    with h5py.File(path, "r") as f:
        version = _as_str(f.attrs["schema_version"])
        if version not in SUPPORTED_SCHEMAS:
            raise ValueError(
                f"Schema version mismatch: file {version!r}, supported {SUPPORTED_SCHEMAS!r}."
            )
        model_type = _as_str(f["parameters"].attrs["model_type"])
        if model_type not in MODEL_TYPES:
            raise ValueError(f"Unknown model_type {model_type!r} in {path}.")
        geo = f["geometry"].attrs
        return Handoff(
            path=str(path),
            schema_version=version,
            model_type=model_type,
            description=_as_str(f.attrs.get("description", "")),
            test_acc=(float(f.attrs["test_acc"]) if "test_acc" in f.attrs else None),
            n_rows=int(geo["n_rows"]),
            n_cols=int(geo["n_cols"]),
            devices_per_weight=int(geo["devices_per_weight"]),
            operating_point={k: float(v) for k, v in f["operating_point"].attrs.items()},
        )


def read_weights(path) -> np.ndarray:
    """The trained weight matrix, ``[n_rows, n_cols]`` in ``[-1, 1]``."""
    with h5py.File(path, "r") as f:
        return f["parameters"]["weights"][...]


def read_test_set(path):
    """``(images, labels)`` of the frozen test set."""
    with h5py.File(path, "r") as f:
        return f["test_set"]["images"][...], f["test_set"]["labels"][...]
