"""Freeze the array-size sweep into ``apps/web/size_data.js``, for the second page.

``apps/export_web_data.py`` does this for one array -- 36 rows, the full 2,000 frozen
test digits -- and the page it feeds is the argument. This does it for five arrays, 36
to 676 rows, and the page it feeds is the same six instruments with the size as a knob.

What is different, and why
--------------------------
**A 500-digit sample, not the full 2,000.** Five sizes of the whole test set is about
3.4 MB of digits at 26x26 alone. The sample is the first 50 of each class in the frozen
order -- the same 500 indices at every grid, so one index means one digit at every size
-- and it is chosen by ``spinn-hw/run_size_sweep.m``, not here. This module *reads* the
index list out of the recorded budget rather than recomputing it, which is what makes
the digits the page ships provably the digits MATLAB measured.

The cost is stated on the page: a live number here is computed over 500 digits and a
recorded one over 2,000, so they do not agree to the digit. Every ladder point is
therefore recorded twice, once over each, and ``size.sample`` is the twin -- same
realizations, same seeds, 500 digits. A verdict still rests only on a recorded
full-set number; the pass mark is 95% of the *full* ideal.

**Weights cross as base64 float64.** ``data.js`` writes its 360 weights as nested JSON
arrays, which is legible and costs nothing at one size. At five sizes the same choice is
243 kB against 130 kB packed, for 12,440 numbers nobody reads by eye. The browser's
``load()`` takes either form.

**The solved wire model travels too.** ``exports/size/g<gg>/error_budget.json`` carries
``exact``: the same ladder with the resistive network solved rather than expanded to
first order, and the fraction of its programmed conductance the worst and the mean cell
keep. The worst-cell fractions are what ``tests/size_runner.js`` pins the browser's own
solver against, 75 of them, at 1e-9.

Regenerating
------------
``python -m apps.export_size_data``, after ``spinn-hw/run_size_sweep.m``. The output is
committed, and ``tests/test_web_size.py`` fails when it drifts from the exports it was
built from -- the same bargain ``export_web_data.py`` and ``build_site.py`` make.
"""
from __future__ import annotations

import base64
import json
import os

import numpy as np

from apps.export_web_data import _b64, _ladder, normalise, pack_images
from apps.report_row import array_read_power
from spinn.handoff import read_handoff, read_test_set, read_weights

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
SIZE_DIR = os.path.join(REPO, "exports", "size")
FIXTURES = os.path.join(REPO, "tests", "fixtures")
OUT = os.path.join(WEB, "size_data.js")

#: The grids swept, as ``apps/report_size.py`` and ``run_size_sweep.m`` have them.
#: Rows are ``g * g``; the ten columns are the ten classes at every size.
GRIDS = (6, 8, 12, 18, 26)

#: Where each grid's frozen test split lives. 6x6 is the shared task and came from
#: photonn under its own name; the rest were cut from the same 2,000 digits by
#: ``tools/import_shared_task.py`` and are committed beside it.
def _task_path(grid: int) -> str:
    if grid == 6:
        return os.path.join(FIXTURES, "shared_task_6x6.npz")
    return os.path.join(FIXTURES, f"shared_task_{grid}x{grid}_test.npz")


def _size_path(grid: int, name: str) -> str:
    return os.path.join(SIZE_DIR, f"g{grid:02d}", name)


def _arr(x) -> list:
    """MATLAB's ``jsonencode`` writes a one-element array as a scalar."""
    return [x] if not isinstance(x, list) else x


def sample_indices(budget: dict) -> list:
    """The 500 sample indices MATLAB chose, 0-based, as a list.

    Read rather than recomputed. If this module picked its own 50-per-class the two
    would agree today and diverge the first time either side changed how it breaks a
    tie -- and the symptom would be a page whose live numbers sit a little away from
    its recorded ones for a reason nobody could see.
    """
    idx = [int(i) for i in _arr(budget["sample"]["indices"])]
    assert len(idx) == int(budget["sample"]["n"]), "the recorded sample lost an index"
    return idx


def collect_size(grid: int) -> dict:
    """One array: everything ``window.SpinnData`` carries, plus what the size adds."""
    with open(_size_path(grid, "error_budget.json"), encoding="utf-8") as fh:
        budget = json.load(fh)
    ideal = np.load(_size_path(grid, "crossbar_ideal.npz"))
    handoff_path = _size_path(grid, "crossbar_handoff.h5")
    handoff = read_handoff(handoff_path)
    images, labels = read_test_set(handoff_path)

    rows = grid * grid
    assert int(budget["nRows"]) == rows, f"g{grid:02d} records {budget['nRows']} rows"
    weights = np.asarray(ideal["weights"], dtype="f8")
    assert weights.shape == (rows, 10), f"g{grid:02d} weights are {weights.shape}"

    idx = sample_indices(budget)
    x = normalise(images)[idx]

    exact = budget["exact"]
    sample = budget["sample"]
    return {
        "schema": "web-size-data 1",
        "grid": grid,
        "weights": _b64(weights),
        "readoutGain": float(ideal["readout_gain"]),
        "scheme": str(ideal["scheme"]),
        "seed": int(ideal["seed"]),
        # The full-set ideal and pass mark. The digits below are a sample of the set
        # these were measured on, which is the whole of what the page has to say
        # plainly: a verdict comes from here, a live number comes from those.
        "idealAccuracy": float(budget["ideal"]),
        "threshold": float(budget["threshold"]),
        "baseSeed": int(budget["baseSeed"]),
        "geometry": {"rows": rows, "cols": 10, "side": grid,
                     "devices": rows * 10 * handoff.devices_per_weight},
        # Identical at every size -- the window is held fixed across the sweep -- and
        # carried per size anyway, because error source 3 reads it off the model it is
        # running on and a shared copy would be a second place for it to be wrong.
        "operatingPoint": {
            "gMinS": handoff.constant("g_min_s"),
            "gMaxS": handoff.constant("g_max_s"),
            "readVoltageV": handoff.constant("read_voltage_v"),
        },
        "power": array_read_power(handoff, read_weights(handoff_path), images),
        "images": pack_images(x),
        "labels": _b64(np.asarray(labels, dtype="u1")[idx]),
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
            # Source 3 with the network solved. Both models, always -- the page draws
            # them together, because "fails at 200 ohm" and "holds at 431 ohm" are
            # both true and of different models.
            "exact": {
                "magnitudes": _arr(exact["magnitudes"]),
                "firstOrderAcc": _arr(exact["firstOrderAcc"]),
                "exactAcc": _arr(exact["exactAcc"]),
                "worstCellFraction": _arr(exact["worstCellFraction"]),
                "meanCellFraction": _arr(exact["meanCellFraction"]),
                "lastHolding": exact["lastHolding"],
                "firstFailing": exact["firstFailing"],
            },
        },
        # The twin of every ladder above, on the 500 digits this file ships. What a
        # widget compares its own live number against.
        "sample": {
            "n": int(sample["n"]),
            "ideal": float(sample["ideal"]),
            "sigma": {"magnitudes": _arr(sample["sigma_g_rel"]["magnitudes"]),
                      "accMean": _arr(sample["sigma_g_rel"]["accMean"]),
                      "accStd": _arr(sample["sigma_g_rel"]["accStd"])},
            "states": {"magnitudes": _arr(sample["states_per_device"]["magnitudes"]),
                       "accMean": _arr(sample["states_per_device"]["accMean"])},
            "wire": {"magnitudes": _arr(sample["wire_resistance_ohm"]["magnitudes"]),
                     "accMean": _arr(sample["wire_resistance_ohm"]["accMean"])},
            "exact": {"magnitudes": _arr(sample["exact"]["magnitudes"]),
                      "exactAcc": _arr(sample["exact"]["exactAcc"])},
        },
    }


def collect() -> dict:
    sizes = [collect_size(g) for g in GRIDS]

    # One index list for the whole file. Asserted rather than assumed: the grids were
    # cut from the same 2,000 digits, so the same 50-per-class rule must land on the
    # same 500 of them, and the page's "same digit at each size" strip is exactly that
    # claim.
    lists = []
    for g in GRIDS:
        with open(_size_path(g, "error_budget.json"), encoding="utf-8") as fh:
            lists.append(sample_indices(json.load(fh)))
    assert all(l == lists[0] for l in lists), (
        "the sample is not the same 500 digits at every grid, so one index does not "
        "mean one digit across sizes"
    )

    with open(_size_path(6, "error_budget.json"), encoding="utf-8") as fh:
        first = json.load(fh)
    return {
        "schema": "web-size-data 1",
        "grids": list(GRIDS),
        "samplePerClass": int(first["sample"]["perClass"]),
        "sampleIndices": lists[0],
        #: Per-cell wiring, ohms: 2 at 65 nm and about 20 at 7 nm. Both are ladder
        #: points, so the page marks them rather than interpolating to them.
        "citedWireOhm": _arr(first["citedWireOhm"]),
        "sizes": {str(s["grid"]): s for s in sizes},
    }


def render() -> str:
    """The generated module, as bytes-on-disk."""
    payload = json.dumps(collect(), separators=(",", ":"), sort_keys=False)
    return (
        "/* Generated by apps/export_size_data.py. Do not edit.\n"
        " *\n"
        " * The array-size sweep, frozen for the browser: five trained arrays from 36 to\n"
        " * 676 rows, a 500-digit sample of the frozen test set at each grid, and every\n"
        " * ladder recorded twice -- once over the full 2,000 digits and once over those\n"
        " * 500. Regenerate with `python -m apps.export_size_data`; tests/test_web_size.py\n"
        " * fails when this file drifts from exports/size/.\n"
        " */\n"
        "(function () {\n"
        '  "use strict";\n'
        "  var SIZES = " + payload + ";\n"
        "  if (typeof module !== \"undefined\" && module.exports) module.exports = SIZES;\n"
        "  if (typeof window !== \"undefined\") window.SpinnSizes = SIZES;\n"
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
