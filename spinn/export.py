"""One-directional design -> as-built handoff (Python writes, MATLAB reads).

Serialises the trained ideal crossbar, its array geometry, its operating point and
the frozen test set into a single HDF5 file. MATLAB (``spinn-hw/+io/read_handoff.m``)
reads this file and **never writes back**. The boundary between the ideal design
model and the as-built error model is one-directional by design: a design that can
be quietly adjusted to flatter its own error budget is not a measurement of
anything.

This module is the authoritative writer and validator, and it is deliberately the
most defensive code in the repo. The seam is where a wrong number becomes an
invisible wrong number.

Inherited from photonn, whose optical schema this replaces. What was kept is the
**mechanism** -- :class:`OperatingPointField`, :func:`_check_operating_point`, the
write/validate pair -- because it is entirely generic and it was earned the hard
way. photonn's note on why is worth restating: the seam used to be enforced at one
end and depended on at six, so renaming ``pixel_pitch_m`` produced a file the
writer accepted, the validator passed, and MATLAB read as ``NaN``; renaming
``readout_gain`` made MATLAB substitute 1.0 for 10.0, rescaling every logit tenfold
with no error anywhere, into a published tolerance number.

The schema version restarts at 0.1.0. This is a new contract, not a continuation of
photonn's 0.3.0, and carrying their number forward would imply a compatibility that
does not exist.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import NamedTuple

import h5py
import numpy as np

#: Handoff schema version. Bump on any breaking change to the layout below.
#: The MATLAB reader checks against its own copy of this string.
SCHEMA_VERSION = "0.1.0"

#: Versions a reader accepts. One, so far.
SUPPORTED_SCHEMAS = ("0.1.0",)

#: Supported model kinds. One: this repo builds one machine.
MODEL_TYPES = ("crossbar",)

#: How a signed weight is represented, as an integer code on the operating point.
#:
#: A code rather than a string because HDF5 attributes here are numeric and photonn
#: set the precedent with ``encoding_code``. It **must** cross the seam: the scheme
#: changes how conductances are programmed, how many devices exist, and how the
#: column current decodes, so a reader that assumed one while the writer used the
#: other would reconstruct a plausible, wrong array.
SIGNED_SCHEMES = {"differential": 0, "offset": 1}
SIGNED_SCHEME_NAMES = {code: name for name, code in SIGNED_SCHEMES.items()}


class OperatingPointField(NamedTuple):
    """One scalar constant the handoff may carry."""

    required_for: tuple
    doc: str


#: Every scalar ``/operating_point`` is allowed to hold, which model kinds require
#: it, and -- the part that matters -- **what goes wrong downstream if it is absent**.
#:
#: An unknown key fails at write time and a missing one fails before the file
#: exists, so what a reader receives is correct by construction. Adding a constant
#: means adding a row here; that is the whole cost.
OPERATING_POINT = {
    "g_min_s": OperatingPointField(
        ("crossbar",),
        "Low conductance state, siemens. With g_max_s it fixes the window every "
        "weight and every noise margin has to fit inside. UNSOURCED."),
    "g_max_s": OperatingPointField(
        ("crossbar",),
        "High conductance state, siemens. The ratio to g_min_s is this platform's "
        "characteristic constraint. UNSOURCED."),
    "read_voltage_v": OperatingPointField(
        ("crossbar",),
        "Row drive at the largest input in a sample. Sets the current, so it sets "
        "energy and the shot-noise floor; it cancels out of the ideal accuracy."),
    "readout_gain": OperatingPointField(
        ("crossbar",),
        "Factor restoring the trained logit scale, because training fits "
        "unconstrained and the weights are then divided by max|w| to fit the "
        "window. Wrong value still classifies -- argmax is scale-invariant -- so "
        "nothing downstream notices until a margin is computed from it."),
    "signed_scheme_code": OperatingPointField(
        ("crossbar",),
        "0 differential (two devices per weight, currents subtract), 1 offset "
        "(one device, zero at mid-scale, pedestal subtracted downstream). "
        "Reconstructing under the wrong scheme gives a valid array that is not "
        "the trained one."),
}


def _check_operating_point(operating_point, model_type):
    """Reject an operating point the manifest does not recognise or does not cover."""
    unknown = sorted(set(operating_point) - set(OPERATING_POINT))
    if unknown:
        raise ValueError(
            f"operating_point has unrecognised key(s) {unknown}. Add them to "
            "spinn.export.OPERATING_POINT (and to the MATLAB reader) rather than "
            "writing a scalar no reader knows to look for."
        )
    missing = sorted(
        key for key, spec in OPERATING_POINT.items()
        if model_type in spec.required_for and key not in operating_point
    )
    if missing:
        raise ValueError(
            f"operating_point is missing {missing} for model_type={model_type!r}. "
            "Every one of these is read downstream; absent, MATLAB substitutes a "
            "default and produces a plausible wrong answer."
        )


#: Array geometry attributes, all required. Device count is not derivable from the
#: weights alone -- it depends on the signed-weight scheme -- and IR drop and energy
#: are both counted per device, so it crosses explicitly.
GEOMETRY_ATTRS = ("n_rows", "n_cols", "devices_per_weight")


def _as_str(value):
    """Decode an HDF5 attribute that may come back as bytes into ``str``."""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _weight_array(parameters, geometry):
    """Coerce and cross-check the weight matrix against the declared geometry."""
    if "weights" not in parameters:
        raise ValueError("parameters is missing required key 'weights'.")
    w = np.asarray(parameters["weights"], dtype="f8")
    shape = (int(geometry["n_rows"]), int(geometry["n_cols"]))
    if w.shape != shape:
        raise ValueError(
            f"'weights' must be [n_rows, n_cols]={shape}; got {w.shape}."
        )
    if not np.all(np.abs(w) <= 1.0 + 1e-12):
        raise ValueError(
            "weights must lie in [-1, 1] -- they index the conductance window, and "
            f"a value outside it is not one the array can hold. Got "
            f"[{w.min():.6g}, {w.max():.6g}]. Divide by max|w| and carry the factor "
            "as readout_gain."
        )
    return w


def write_handoff(
    path,
    *,
    model_type,
    parameters,
    geometry,
    operating_point,
    test_images,
    test_labels,
    description="",
    test_acc=None,
):
    """Write a handoff HDF5 file.

    Parameters
    ----------
    path : str or os.PathLike
        Output ``.h5`` path (overwritten if it exists).
    model_type : {"crossbar"}
    parameters : dict
        ``{"weights": float[n_rows, n_cols]}``, each in ``[-1, 1]``, indexing the
        conductance window rather than being conductances themselves. The mapping
        is the scheme's job and is done on both sides from the operating point, so
        the file stays independent of the window it was trained against.
    geometry : dict
        ``{"n_rows": int, "n_cols": int, "devices_per_weight": int}``.
    operating_point : dict
        Scalar constants; the manifest in :data:`OPERATING_POINT` is enforced.
    test_images, test_labels : array_like
        The frozen test set, written as ``float32[n, g, g]`` and ``int32[n]``.
    description : str, optional
    test_acc : float, optional
        Ideal accuracy, as a real attribute rather than a token in free text.
    """
    if model_type not in MODEL_TYPES:
        raise ValueError(
            f"model_type must be one of {MODEL_TYPES}; got {model_type!r}."
        )
    _check_operating_point(operating_point, model_type)
    for key in GEOMETRY_ATTRS:
        if key not in geometry:
            raise ValueError(f"geometry is missing required key {key!r}.")

    code = int(operating_point["signed_scheme_code"])
    if code not in SIGNED_SCHEME_NAMES:
        raise ValueError(
            f"signed_scheme_code must be one of {sorted(SIGNED_SCHEME_NAMES)}; got {code}."
        )
    expected_devices = 2 if code == SIGNED_SCHEMES["differential"] else 1
    if int(geometry["devices_per_weight"]) != expected_devices:
        raise ValueError(
            f"devices_per_weight={geometry['devices_per_weight']} disagrees with "
            f"signed_scheme_code={code} ({SIGNED_SCHEME_NAMES[code]}, "
            f"{expected_devices} per weight). The two would be read by different "
            "parts of the as-built model and one of them would be wrong."
        )
    if not operating_point["g_max_s"] > operating_point["g_min_s"] > 0:
        raise ValueError(
            f"need 0 < g_min_s < g_max_s; got {operating_point['g_min_s']} and "
            f"{operating_point['g_max_s']}."
        )

    weights = _weight_array(parameters, geometry)

    with h5py.File(path, "w") as f:
        f.attrs["schema_version"] = SCHEMA_VERSION
        f.attrs["created"] = datetime.now(timezone.utc).isoformat()
        f.attrs["description"] = description
        if test_acc is not None:
            f.attrs["test_acc"] = float(test_acc)

        geo = f.create_group("geometry")
        for key in GEOMETRY_ATTRS:
            geo.attrs[key] = int(geometry[key])

        op = f.create_group("operating_point")
        for key, val in operating_point.items():
            op.attrs[key] = float(val)

        p = f.create_group("parameters")
        p.attrs["model_type"] = model_type
        p.create_dataset("weights", data=weights)

        ts = f.create_group("test_set")
        ts.create_dataset("images", data=np.asarray(test_images, dtype="f4"))
        ts.create_dataset("labels", data=np.asarray(test_labels, dtype="i4"))


def validate_handoff(path):
    """Validate that ``path`` conforms to the handoff schema.

    Reads the file back and asserts the schema version is supported and that every
    required group, attribute and dataset is present. Raises :class:`ValueError` on
    the first violation; returns ``None`` on success.

    Re-checking the manifest against the bytes is not redundant with the writer's
    check. A file can reach here without having gone through :func:`write_handoff`
    -- hand-edited, or written by an older exporter -- and no reader can tell.
    """
    with h5py.File(path, "r") as f:
        if "schema_version" not in f.attrs:
            raise ValueError("Missing root attribute 'schema_version'.")
        version = _as_str(f.attrs["schema_version"])
        if version not in SUPPORTED_SCHEMAS:
            raise ValueError(
                f"Schema version mismatch: file {version!r}, supported {SUPPORTED_SCHEMAS!r}."
            )

        for group in ("geometry", "operating_point", "parameters", "test_set"):
            if group not in f:
                raise ValueError(f"Missing group '/{group}'.")

        geo = f["geometry"]
        for attr in GEOMETRY_ATTRS:
            if attr not in geo.attrs:
                raise ValueError(f"Missing attribute '/geometry.{attr}'.")

        params = f["parameters"]
        if "model_type" not in params.attrs:
            raise ValueError("Missing attribute '/parameters.model_type'.")
        model_type = _as_str(params.attrs["model_type"])
        if model_type not in MODEL_TYPES:
            raise ValueError(
                f"'/parameters.model_type' must be one of {MODEL_TYPES}; got {model_type!r}."
            )
        if "weights" not in params:
            raise ValueError("Missing dataset '/parameters/weights'.")

        op_attrs = f["operating_point"].attrs
        missing = sorted(
            key for key, spec in OPERATING_POINT.items()
            if model_type in spec.required_for and key not in op_attrs
        )
        if missing:
            raise ValueError(
                f"Missing '/operating_point' attribute(s) {missing} for "
                f"model_type={model_type!r}. See spinn.export.OPERATING_POINT."
            )

        _weight_array(
            {"weights": params["weights"][...]},
            {"n_rows": geo.attrs["n_rows"], "n_cols": geo.attrs["n_cols"]},
        )

        test_set = f["test_set"]
        for dset in ("images", "labels"):
            if dset not in test_set:
                raise ValueError(f"Missing dataset '/test_set/{dset}'.")
        if len(test_set["images"]) != len(test_set["labels"]):
            raise ValueError(
                f"test_set has {len(test_set['images'])} images and "
                f"{len(test_set['labels'])} labels."
            )
