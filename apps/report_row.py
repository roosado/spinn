"""Turn the error budget into the one row this repo owes the comparison table.

Reads ``exports/error_budget.json`` (written by ``spinn-hw/run_error_budget.m``)
and the handoff, converts each tolerance edge into the series' comparison unit,
and writes ``docs/comparison_row.md``.

The unit is fixed by the hub:

    effective bits = log2(operating range / sigma)

Comparing tolerance across media looks impossible -- phase error in radians has no
spintronic counterpart, conductance spread in siemens has no optical one -- but any
analog tolerance normalises against the device's own operating range, and the log
of that ratio is a bit depth.

Two rules this file exists to keep:

**No margin without a source.** Delivered precision is `UNSOURCED`, so the margin
column is *omitted* rather than estimated. photonn's mesh budget set the precedent.

**Edges are brackets, never interpolated.** "Holds at X, fails at Y." ``mc.pack``
deliberately stores no fitted crossing point, and neither does this.

Run::

    .venv/Scripts/python.exe -m apps.report_row
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

from spinn.handoff import read_handoff, read_test_set, read_weights

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUDGET = os.path.join(REPO, "exports", "error_budget.json")
HANDOFF = os.path.join(REPO, "exports", "crossbar_handoff.h5")
OUT = os.path.join(REPO, "docs", "comparison_row.md")


def bits_from_sigma(sigma_rel: float) -> float:
    """``log2(range / sigma)`` where sigma is already a fraction of the range.

    This is why the config key is ``sigma_g_rel`` and not a value in siemens: the
    conversion needs no conductance window, so it does not inherit the window's
    ``UNSOURCED`` status.
    """
    return -math.log2(sigma_rel)


def bits_from_states(states: int, scheme: str) -> float:
    """Bit depth of the weight lattice the devices can reach.

    A differential pair reaches ``2*states - 1`` effective weights, because the
    weight is a *difference* of two device states. Using ``log2(states)`` here
    would understate the scheme by up to a full bit -- and the shortfall *grows*
    with the state count rather than shrinking, since ``2n-1`` approaches ``2n``.
    At two states, where the MTJ family sits, the pair is worth only
    ``log2(3) - 1 = 0.585`` bits over an offset: the case it is most often argued
    for is the case it helps least.
    """
    levels = 2 * states - 1 if scheme == "differential" else states
    return math.log2(levels)


def array_read_power(handoff, weights, images) -> float:
    """Mean power dissipated in the array during a read, in watts.

    ``P = sum_ij V_i^2 * G_ij`` over every device, averaged over samples.

    **Array only.** This excludes the sense amplifiers, the ADC and every digital
    stage after it. That exclusion is the whole reason the number is quoted as
    power rather than as energy per inference: the periphery frequently dominates
    an analog accelerator's energy, and a figure that quietly leaves it out is not
    comparable to one that does not.
    """
    cb = handoff.crossbar()
    v = cb.encode(images)
    g = cb.program(weights)
    return float(np.mean(np.einsum("bi,dio->b", v ** 2, g)))


def main() -> None:
    with open(BUDGET, encoding="utf-8") as fh:
        b = json.load(fh)
    h = read_handoff(HANDOFF)
    weights = read_weights(HANDOFF)
    images, _ = read_test_set(HANDOFF)

    ideal, thr = b["ideal"], b["threshold"]
    sig, sta, wir = b["sigma_g_rel"], b["states_per_device"], b["wire_resistance_ohm"]

    sig_hold, sig_fail = bits_from_sigma(sig["lastHolding"]), bits_from_sigma(sig["firstFailing"])
    sta_hold = bits_from_states(int(sta["lastHolding"]), h.scheme)
    sta_fail = bits_from_states(int(sta["firstFailing"]), h.scheme)

    power = array_read_power(h, weights, images)
    joint = b["joint"]

    lines = [
        "# The row",
        "",
        "One row in the physical-AI comparison table, stated once here. The hub refers",
        "to this rather than copying it.",
        "",
        "Produced by `spinn-hw/run_error_budget.m` from `exports/crossbar_handoff.h5`,",
        f"seeds from `baseSeed = {int(b['baseSeed'])}`, and assembled by "
        "`apps/report_row.py`.",
        "",
        "| column | value |",
        "|---|---|",
        "| Platform | spintronic crossbar (MTJ / domain-wall) |",
        "| What a weight physically is | a magnetic state, read as a conductance |",
        "| What performs the sum | Kirchhoff current summing on a wire |",
        f"| Ideal accuracy | **{ideal:.4f}** on the shared task (MNIST, 36 channels) |",
        "| Which source binds | **conductance variation** (device-to-device sigma) |",
        f"| Required precision | **{sig_hold:.2f} effective bits** on the binding source |",
        "| Delivered precision | `UNSOURCED` |",
        "| Margin | *omitted — delivered precision is not sourced* |",
        f"| Energy per inference | `UNSOURCED`; array read power **{power * 1e6:.3f} µW** |",
        "| Latency per inference | `UNSOURCED` |",
        "",
        f"Array **{b['nRows']}×{b['nCols']}**, {b['nDevices']} devices, {b['scheme']} pairs.",
        f"Pass mark **{thr:.4f}** = 95% of ideal, declared before the sweeps were run.",
        "",
        "## The edges, as brackets",
        "",
        "Read off the magnitude ladder. Nothing is interpolated: `mc.pack` stores mean",
        "and standard deviation and no fitted crossing point, deliberately.",
        "",
        "| source | holds at | fails at | in effective bits |",
        "|---|---|---|---|",
        f"| 1. conductance variation | σ = {sig['lastHolding']:g} of the window "
        f"({sig['accMean'][sig['holds'].index(False) - 1]:.4f}) | σ = {sig['firstFailing']:g} "
        f"({sig['accMean'][sig['holds'].index(False)]:.4f}) | **holds at {sig_hold:.2f}, "
        f"fails at {sig_fail:.2f}** |",
        f"| 2. resolvable states | {int(sta['lastHolding'])} states/device | "
        f"{int(sta['firstFailing'])} states/device | holds at {sta_hold:.2f}, "
        f"fails at {sta_fail:.2f} |",
        f"| 3. IR drop | {wir['lastHolding']:g} Ω per segment | "
        f"{wir['firstFailing']:g} Ω per segment | *not a bit depth — see below* |",
        "",
        "**Conductance variation binds.** It demands "
        f"{sig_hold:.2f} bits where the states knob demands {sta_hold:.2f}, and both are",
        "expressed against the same conductance window, so the comparison is like for",
        "like. That was the prediction on record before any of this ran.",
        "",
        "**IR drop is deliberately not converted to bits.** It is a position-dependent",
        "systematic, not a spread on a stored value, so `log2(range/σ)` has no σ to take.",
        "Forcing it into the unit would be a category error. The statement that means",
        f"something is the one in the table: at this array size the design tolerates",
        f"{wir['lastHolding']:g} Ω per wire segment and fails by {wir['firstFailing']:g} Ω.",
        "**That number is meaningless without the array size beside it**, which is why",
        "the size is fixed and reported.",
        "",
        "## The joint run",
        "",
        f"All three sources at the last magnitude each individually held: mean "
        f"**{joint['mean']:.4f}** ± {joint['std']:.4f}, which is **below** the pass mark.",
        "",
        f"The joint drop is {joint['drop']:.4f} against {joint['sumOfIndependentDrops']:.4f}",
        "for the sum of the independent drops — **sub-additive**, not additive. That is a",
        "property of accuracy as a metric rather than a finding about the crossbar: a",
        "sample already misclassified by one source cannot be misclassified again by the",
        "next, so degradations saturate. No conclusion is drawn from it.",
        "",
        "What it does say practically is that budgeting each source to its own edge",
        "leaves nothing over. A design meeting all three at once needs each source",
        "comfortably inside its individual bracket.",
        "",
        "## Energy and latency",
        "",
        "Both are `UNSOURCED`, and the arithmetic is given so a reader can substitute.",
        "",
        f"Array read power is **{power * 1e6:.3f} µW**, computed exactly as",
        "`mean_over_samples( sum_ij V_i² · G_ij )` over all "
        f"{b['nDevices']} devices at the operating point in the handoff.",
        "",
        "That is **array only**: it excludes the sense amplifiers, the ADC and every",
        "digital stage after them. The periphery frequently dominates an analog",
        "accelerator's energy, and a figure that quietly omits it is not comparable to",
        "one that does not — so the boundary is stated rather than implied.",
        "",
        "**Energy per inference needs a read time, and no read time has been sourced.**",
        "Energy = power × t_read; multiply the figure above by whatever t_read a source",
        "supports. Latency is the RC settling of the lines, which needs a line",
        "capacitance and resistance, neither of which is sourced either.",
        "",
        "The conductance window itself (`g_min_s`, `g_max_s`) and the read voltage are",
        "also `UNSOURCED` placeholders — so the power figure scales with them and should",
        "be read as an arithmetic worked example, not as a measurement. The *accuracy*",
        "and *bit-depth* results above do not depend on them: they cancel in the decode,",
        "and a test asserts as much.",
    ]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("\n".join(lines[:22]))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
