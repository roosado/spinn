"""Freeze everything the page's widgets compute from into ``apps/web/data.js``.

The widgets on this site run the **real** forward pass: the trained 36x10 weights,
the frozen 2000-image test set, and the same arithmetic ``spinn/crossbar.py`` and
``spinn-hw/+err/*.m`` perform. That is a deliberate cost. A demonstration that is a
cartoon of the result would undo the one-directional seam that makes the result
worth showing -- a reader who drags a slider and watches an accuracy fall is
entitled to have watched the accuracy that was actually measured.

So the data has to cross into the browser exactly, and it has to be small enough
to inline in a page that makes no external request.

Precision
---------
**uint16, not uint8.** The images are L-infinity normalised into ``[0, 1]`` and
then quantised. At 8 bits the ideal accuracy comes out 0.7340 rather than 0.7345 --
one sample of two thousand, moved by a rounding error in the fifth pixel of some
digit sitting on a knife edge between two columns. That is a small error and it is
the wrong one to accept: the page's whole claim is that these are the recorded
numbers. At 16 bits every magnitude in ``exports/error_budget.json`` that does not
involve a random draw reproduces exactly, which ``tests/test_web_data.py`` asserts.

Size
----
**Sparse, because the digits are.** Three quarters of the 72,000 pixels are zero,
so a dense uint16 block spends 144 kB carrying mostly nothing. Per sample: a count,
then one index byte and two value bytes per non-zero pixel. About 57 kB, ~76 kB
once base64'd, against 192 kB for the dense form -- and exact either way. The
decoder in ``apps/web/data_decode.js`` is the other half of this format; the two
must be read together.

Regenerating
------------
``python -m apps.export_web_data``. The output is committed, and
``tests/test_web_data.py`` fails when it drifts from the exports it was built
from -- the same bargain ``tests/test_site_build.py`` makes for the built page.
"""
from __future__ import annotations

import base64
import json
import os

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

IDEAL = os.path.join(REPO, "exports", "crossbar_ideal.npz")
BUDGET = os.path.join(REPO, "exports", "error_budget.json")
TASK = os.path.join(REPO, "tests", "fixtures", "shared_task_6x6.npz")
OUT = os.path.join(WEB, "data.js")

#: Full scale for the quantised pixel. See the module docstring: 8 bits loses a
#: sample, 16 loses nothing measurable by any number this page prints.
FULL = 65535


def _b64(a: np.ndarray) -> str:
    return base64.b64encode(a.tobytes()).decode("ascii")


def normalise(images: np.ndarray) -> np.ndarray:
    """Flatten to rows and divide by each sample's own peak.

    This is exactly ``Crossbar.encode`` with ``read_voltage`` divided back out --
    the drive scales out of the decode, so the browser carries the dimensionless
    form and never has to know a voltage it would only cancel again.
    """
    v = np.asarray(images, dtype="f8").reshape(len(images), -1)
    peak = np.max(np.abs(v), axis=1, keepdims=True)
    return v / np.where(peak > 0, peak, 1.0)


def pack_images(x: np.ndarray) -> dict:
    """Sparse-encode normalised images, one record per sample.

    Returns the three arrays the decoder needs, base64'd: a per-sample non-zero
    count, the pixel index of each non-zero, and its quantised value.
    """
    q = np.rint(x * FULL).astype("u2")
    counts, idx, val = [], [], []
    for row in q:
        nz = np.nonzero(row)[0]
        counts.append(len(nz))
        idx.append(nz.astype("u1"))
        val.append(row[nz])
    return {
        "n": int(len(q)),
        "dim": int(q.shape[1]),
        "full": FULL,
        "counts": _b64(np.asarray(counts, dtype="u1")),
        "idx": _b64(np.concatenate(idx) if idx else np.empty(0, "u1")),
        "val": _b64(np.concatenate(val) if val else np.empty(0, "u2")),
    }


def _ladder(entry: dict) -> dict:
    """One error source's sweep, trimmed to what the chart draws."""
    return {
        "magnitudes": entry["magnitudes"],
        "accMean": entry["accMean"],
        "accStd": entry["accStd"],
        "holds": entry["holds"],
        "lastHolding": entry["lastHolding"],
        "firstFailing": entry["firstFailing"],
    }


def collect() -> dict:
    ideal = np.load(IDEAL)
    task = np.load(TASK)
    with open(BUDGET, encoding="utf-8") as fh:
        budget = json.load(fh)

    x = normalise(task["test_images"])
    return {
        "schema": "web-data 1",
        "weights": [[float(v) for v in row] for row in ideal["weights"]],
        "readoutGain": float(ideal["readout_gain"]),
        "scheme": str(ideal["scheme"]),
        "seed": int(ideal["seed"]),
        "idealAccuracy": float(ideal["ideal_accuracy"]),
        "geometry": {"rows": 36, "cols": 10, "side": 6, "devices": 720},
        # The design point, not a measurement, and carried only because error
        # source 3 needs an absolute conductance -- sources 1 and 2 cancel it exactly.
        "operatingPoint": {"gMinS": 1.0e-6, "gMaxS": 3.0e-6, "readVoltageV": 0.1},
        "threshold": float(budget["threshold"]),
        "baseSeed": int(budget["baseSeed"]),
        "images": pack_images(x),
        "labels": _b64(np.asarray(task["test_labels"], dtype="u1")),
        "budget": {
            "sigma": _ladder(budget["sigma_g_rel"]),
            "states": _ladder(budget["states_per_device"]),
            "wire": _ladder(budget["wire_resistance_ohm"]),
            "joint": {
                "config": budget["joint"]["config"],
                "mean": budget["joint"]["mean"],
                "std": budget["joint"]["std"],
                "drop": budget["joint"]["drop"],
                "sumOfIndependentDrops": budget["joint"]["sumOfIndependentDrops"],
            },
        },
    }


def render() -> str:
    """The generated module, as bytes-on-disk."""
    payload = json.dumps(collect(), separators=(",", ":"), sort_keys=False)
    return (
        "/* Generated by apps/export_web_data.py. Do not edit.\n"
        " *\n"
        " * The trained weights, the frozen test set and the measured error budget,\n"
        " * frozen for the browser. Regenerate with `python -m apps.export_web_data`;\n"
        " * tests/test_web_data.py fails when this file drifts from exports/.\n"
        " */\n"
        "(function () {\n"
        '  "use strict";\n'
        "  var DATA = " + payload + ";\n"
        "  if (typeof module !== \"undefined\" && module.exports) module.exports = DATA;\n"
        "  if (typeof window !== \"undefined\") window.SpinnData = DATA;\n"
        "})();\n"
    )


def main() -> str:
    text = render()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"wrote {OUT}  ({len(text) / 1024:.1f} kB)")
    return OUT


if __name__ == "__main__":
    main()
