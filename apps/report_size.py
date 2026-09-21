"""The array-size sweep, reported: ``docs/array_size.md``.

Reads ``exports/size/g<gg>/error_budget.json`` for each grid (written by
``spinn-hw/run_size_sweep.m``) and the handoff beside it, and writes one document.

The row (``docs/comparison_row.md``) is one array, 36 rows by 10 columns, and says of
its IR-drop bracket that it is meaningless without the array size beside it. This is
the same measurement at five sizes, so the size is the axis rather than a footnote.

What varies is the image grid ``g``: rows are ``g*g`` and the ten columns are the ten
classes, so **only the column wire lengthens**. Each size is trained fresh on the same
2,000 test digits at that resolution. Only 6x6 is the shared task the comparison table
rests on; nothing here is compared to a photonn row.

Rules this file keeps, all declared in ``docs/history.md`` (2026-09-19) before any
size was run:

**Every pass mark is 95% of that size's own ideal.** No size is graded on another's
curve.

**The size limit is judged on cited wiring only.** Wire resistance is cited (2 ohm per
cell at 65 nm, 20 ohm at 7 nm), so IR drop can be judged against it. The device spread
is ``UNSOURCED``, so source 1 gets no verdict against the wire: its edge is reported at
each size and nothing is compared to it.

**Edges are brackets, never interpolated.** No fitted crossing and no fitted exponent.
``edge x rows^2`` is shown at both ends of each bracket instead, so a reader can see how
far the scaling is from a power law without one being assumed.

Run::

    .venv/Scripts/python.exe -m apps.report_size
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

from apps.report_row import array_read_power, bits_from_sigma, bits_from_states
from spinn.handoff import read_handoff, read_test_set, read_weights

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE_DIR = os.path.join(REPO, "exports", "size")
OUT = os.path.join(REPO, "docs", "array_size.md")

#: The image grids swept. Rows are ``g * g``; columns stay ten. 6 is the row's own.
GRIDS = (6, 8, 12, 18, 26)

#: Source 3's ladder, ohms per segment: ``2 * 10^(k/3)`` for k = -6..8. It contains
#: both cited wire values exactly, so "does cited wiring hold at this size" is read off
#: a ladder point. Declared in docs/history.md; ``spinn-hw/run_size_sweep.m`` builds the
#: same list.
WIRE_LADDER = tuple(2.0 * 10.0 ** (k / 3.0) for k in range(-6, 9))

#: Per-cell wiring, ohms: 2 at 65 nm (Agrawal, Lee & Roy 2019, arXiv:1907.00285) and
#: about 20 at 7 nm (Victor et al. 2024, arXiv:2406.14706).
CITED_OHM = (2.0, 20.0)

#: The expectation declared before the run: from a uniform array's closed form the
#: first-order edge goes as ``1/(g*N^2)``, which from the row's 100 ohm at 36 rows put
#: 20 ohm failing between 64 and 144 rows and 2 ohm between 144 and 324.
DECLARED = {20.0: (64, 144), 2.0: (144, 324)}


def _path(grid: int, name: str) -> str:
    return os.path.join(SIZE_DIR, f"g{grid:02d}", name)


def load(grid: int) -> dict:
    """One size's budget, with the fields the report needs alongside it."""
    with open(_path(grid, "error_budget.json"), encoding="utf-8") as fh:
        b = json.load(fh)
    handoff = _path(grid, "crossbar_handoff.h5")
    h = read_handoff(handoff)
    images, _ = read_test_set(handoff)
    b["rows"] = int(b["nRows"])
    b["g_max"] = h.crossbar().g_max
    b["power"] = array_read_power(h, read_weights(handoff), images)
    return b


def _arr(x) -> list:
    """jsonencode writes a one-element array as a scalar and NaN as null."""
    return [x] if not isinstance(x, list) else x


def at(magnitudes, values, ohm):
    """The value at a ladder magnitude, matched to a relative 1e-9."""
    for m, v in zip(_arr(magnitudes), _arr(values)):
        if math.isclose(m, ohm, rel_tol=1e-9):
            return v
    raise KeyError(f"{ohm:g} ohm is not on the ladder")


def bracket_in_size(sizes, holds) -> dict:
    """The last size at which something holds and the first at which it fails.

    ``sizes`` ascending. A bracket, never interpolated. If it fails at every size or
    holds at every size there is no edge inside the range, and that is reported as a
    property of the range. ``monotone`` is false if it holds again after failing.
    """
    holds = [bool(x) for x in holds]
    if all(holds):
        return {"status": "holds_everywhere", "last": sizes[-1], "first_fail": None,
                "monotone": True}
    f = holds.index(False)
    monotone = not any(holds[f:])
    if f == 0:
        return {"status": "fails_everywhere", "last": None, "first_fail": sizes[0],
                "monotone": monotone}
    return {"status": "bracket", "last": sizes[f - 1], "first_fail": sizes[f],
            "monotone": monotone}


def _f(x, spec: str = ".3g") -> str:
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else format(x, spec)


def _where(br: dict) -> str:
    if br["status"] == "bracket":
        return f"holds at {br['last']} rows, fails at {br['first_fail']}"
    if br["status"] == "holds_everywhere":
        return f"holds at every size swept, up to {br['last']} rows: no edge in this range"
    return f"fails already at {br['first_fail']} rows, the smallest swept"


def _list(xs) -> str:
    xs = [str(x) for x in xs]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _bits_pair(sigma_block: dict) -> tuple[float, float]:
    return bits_from_sigma(sigma_block["lastHolding"]), bits_from_sigma(sigma_block["firstFailing"])


def render() -> str:
    """The report, assembled from the recorded budgets at every size."""
    data = {g: load(g) for g in GRIDS}
    rows = [data[g]["rows"] for g in GRIDS]
    scheme = data[GRIDS[0]]["scheme"]

    # -- what each size says about the wire, both ways --------------------------
    hold = {"first": {}, "exact": {}}
    for ohm in CITED_OHM:
        hold["first"][ohm] = [at(d["wire_resistance_ohm"]["magnitudes"],
                                 d["wire_resistance_ohm"]["holds"], ohm) for d in data.values()]
        hold["exact"][ohm] = [at(d["exact"]["magnitudes"], d["exact"]["exactHolds"], ohm)
                              for d in data.values()]
    limit = {kind: {ohm: bracket_in_size(rows, hold[kind][ohm]) for ohm in CITED_OHM}
             for kind in hold}

    disagree_sizes = [d["rows"] for d in data.values() if any(_arr(d["exact"]["disagree"]))]
    for d in data.values():
        ex = d["exact"]
        for first, solved in zip(_arr(ex["firstOrderHolds"]), _arr(ex["exactHolds"])):
            if first and not solved:
                # The source's header says one pass overstates the drop. A point where
                # first order holds and the network fails contradicts it, and the prose
                # below would then be wrong; say so rather than write it.
                raise ValueError(
                    f"first order holds where the solved network fails at {d['rows']} rows; "
                    "the report's account of which way they disagree is no longer true"
                )
    first_below_chance = [d["rows"] for d in data.values()
                          if min(_arr(d["exact"]["firstOrderAcc"])) < 0.1]
    exact_min = min(min(_arr(d["exact"]["exactAcc"])) for d in data.values())

    L = []
    w = L.append

    w("# Array size")
    w("")
    w("The row's IR-drop bracket is one point on a curve: the drop grows with array size,")
    w("and the row says so and stops. This is the same measurement at five sizes, so the")
    w("size is the axis instead of a footnote. Produced by `spinn-hw/run_size_sweep.m`")
    w("from `exports/size/`, seeds from `baseSeed = 20260908` at every size, and assembled")
    w("by `apps/report_size.py`.")
    w("")
    # The page is a second presentation of this table, not a second source for it.
    # Said here so a reader who lands on the document knows the interactive form
    # exists, and so that the document stays the thing the page points back to.
    w("The site shows the same sweep with the size as a control, and draws both wire")
    w("models together: **[Go larger](https://roosado.github.io/spinn/larger.html)**.")
    w("Every number there is one of these; nothing on it is computed from anything this")
    w("document does not record.")
    w("")
    w("**What varies.** The image grid `g`: rows are `g×g` and the ten columns are the ten")
    w("classes, so **only the column wire lengthens** — the row wire stays ten cells. It is")
    w("one axis. Each size is trained fresh on the same 2,000 test digits at that")
    w("resolution, with the learning rate scaled as `0.5 · 36 / rows` so that no size is an")
    w("optimiser artefact. **Only 6×6 is the shared task**; the others are the same digits at")
    w("another resolution, spinn-internal, and nothing here is compared to a photonn row.")
    w("Everything was declared in `docs/history.md` (2026-09-19) before any size was run:")
    w("the sizes, the ladder, the seeds, and that each size's pass mark is 95% of *its own*")
    w("ideal.")
    w("")
    w("Held fixed: the window (1–3 µS), the read voltage, the cell pitch — so a wire segment")
    w("is the same resistance at every size — and the differential pair.")
    w("")

    # -- table A ---------------------------------------------------------------
    w("## The arrays")
    w("")
    w("| grid | rows | devices | ideal | pass mark | array read power |")
    w("|---|---|---|---|---|---|")
    for g in GRIDS:
        d = data[g]
        w(f"| {g}×{g} | {d['rows']} | {d['nDevices']:,} | {d['ideal']:.4f} | "
          f"{d['threshold']:.4f} | {d['power'] * 1e6:.2f} µW |")
    w("")
    w(f"{scheme.capitalize()} pairs throughout, so devices are twice rows times ten. The pass")
    w("mark rises with the ideal because it is 95% of it. Read power is array only — no")
    w("sense amplifiers, no converters — and grows with the array, as it must.")
    w("")

    # -- table B ---------------------------------------------------------------
    w("## Sources 1 and 2")
    w("")
    w("| rows | 1. conductance variation holds → fails | in bits | "
      "2. states per device holds → fails | in bits | binds, of the two |")
    w("|---|---|---|---|---|---|")
    for g in GRIDS:
        d = data[g]
        s1, s2 = d["sigma_g_rel"], d["states_per_device"]
        hb, fb = _bits_pair(s1)
        sh = bits_from_states(int(s2["lastHolding"]), scheme)
        sf = bits_from_states(int(s2["firstFailing"]), scheme)
        binds = "conductance variation" if hb > sh else "resolvable states"
        w(f"| {d['rows']} | σ = {s1['lastHolding']:g} → {s1['firstFailing']:g} | "
          f"{hb:.2f} → {fb:.2f} | {int(s2['lastHolding'])} → {int(s2['firstFailing'])} | "
          f"{sh:.2f} → {sf:.2f} | {binds} |")
    w("")
    sig = [data[g]["sigma_g_rel"]["lastHolding"] for g in GRIDS]
    w(f"Across sizes the σ that holds loosens from {sig[0]:g} of the window at {rows[0]} rows to "
      f"{sig[-1]:g} at {rows[-1]}, while the wire edge below tightens. They run in opposite")
    w("directions, and neither is explained here.")
    w("")
    w("Read against each size's own ideal, as bracket ends on the row's ladders — not")
    w("interpolated. The states ladder wobbles by a sample or two at fine quantisation, as")
    w("the row records. These are what the device must deliver at that size; the delivered")
    w("spread is `UNSOURCED`, so **no verdict is drawn between them and the wire**.")
    w("")

    # -- table C ---------------------------------------------------------------
    w("## IR drop, first order and solved")
    w("")
    w("`err.ir_drop` is first order: the drops come from the currents the *ideal* voltages")
    w("would draw, so one pass overstates them. `err.ir_drop_exact` solves the same resistive")
    w("network exactly. Both are measured at every ladder point, at every size.")
    w("")
    w("The declaration asked for the solved check at each size's bracket. It is done at every")
    w("ladder point because a bracket cannot be carried without the points either side of it,")
    w("and a first version that iterated the first-order model to a fixed point was replaced")
    w("by a direct solve: it agreed with it wherever it converged and stopped converging at")
    w("the resistances the edge sits between.")
    w("")
    w("| rows | first order: holds → fails (Ω) | **solved: holds → fails (Ω)** | "
      "2 Ω first / solved | 20 Ω first / solved |")
    w("|---|---|---|---|---|")
    for g in GRIDS:
        d = data[g]
        fo, ex = d["wire_resistance_ohm"], d["exact"]
        cells = []
        for ohm in CITED_OHM:
            a = at(fo["magnitudes"], fo["accMean"], ohm)
            b = at(ex["magnitudes"], ex["exactAcc"], ohm)
            cells.append(f"{a:.4f} / {b:.4f}")
        w(f"| {d['rows']} | {_f(fo['lastHolding'])} → {_f(fo['firstFailing'])} | "
          f"**{_f(ex['lastHolding'])} → {_f(ex['firstFailing'])}** | {cells[0]} | {cells[1]} |")
    w("")
    w("Cells are accuracy against that size's pass mark. The bracket is the ladder point")
    w("either side of where the mean crosses the mark.")
    w("")
    ratios = [d["exact"]["lastHolding"] / d["wire_resistance_ohm"]["lastHolding"]
              for d in data.values()]
    w(f"At every size the solved edge sits above first order's: the last magnitude that holds "
      f"is {min(ratios):.1f}× to {max(ratios):.1f}× higher.")
    w("")
    r6 = data[GRIDS[0]]
    ex6, fo6 = r6["exact"], r6["wire_resistance_ohm"]
    w(f"**The row's own array is the first line.** At {r6['rows']}×10 first order puts the edge "
      f"between {fo6['lastHolding']:.3g} and {fo6['firstFailing']:.3g} Ω on this ladder — "
      "the row, on its coarser one, records holding at 100 Ω and failing at 300 Ω. The solved "
      f"network holds at {ex6['lastHolding']:.3g} Ω and fails at {ex6['firstFailing']:.3g} Ω. "
      "**The row's “fails at 300 Ω” is a property of the first-order model and not of the "
      "array**; its “holds at 100 Ω” is unaffected. Nothing in the row has been changed.")
    w("")

    # -- the size limit ---------------------------------------------------------
    w("## The size limit")
    w("")
    w("Judged on **cited wiring only**: 2 Ω per cell at 65 nm (Agrawal et al. 2019) and")
    w("20 Ω at 7 nm (Victor et al. 2024). Both are ladder points, so each is read off directly.")
    w("")
    w("| cited wiring | solved network | first order |")
    w("|---|---|---|")
    for ohm in CITED_OHM:
        w(f"| {ohm:g} Ω per segment | {_where(limit['exact'][ohm])} | "
          f"{_where(limit['first'][ohm])} |")
    w("")
    for ohm in CITED_OHM:
        for kind in ("exact", "first"):
            if not limit[kind][ohm]["monotone"]:
                w(f"*The {kind} result at {ohm:g} Ω holds again after failing; the bracket is")
                w("the first failure and the range should not be read as monotone.*")
                w("")

    w("**What that says about the question the page asks.** The device spread has no")
    w("delivered value, so nothing here is a margin against it. Wire resistance does, so")
    w("wiring can be judged: at the sizes where both cited values hold, the wire is inside")
    w("its edge and, of the sources judged, conductance variation is the one that binds, as")
    w("in the row; where cited wiring fails, the wire is a delivered failure that no")
    w("amount of device precision removes.")
    w("")
    w(f"On the solved network, 7 nm wiring (20 Ω) {_where(limit['exact'][20.0])}; "
      f"65 nm wiring (2 Ω) {_where(limit['exact'][2.0])}.")
    w("")
    e20 = limit["exact"][20.0]
    if e20["status"] == "bracket":
        w(f"So for 7 nm wiring the binding source changes from conductance variation to the "
          f"wire somewhere between {e20['last']} and {e20['first_fail']} rows. That is a "
          "bracket in size, five sizes wide, and is not interpolated.")
        w("")

    # -- how far first order is off ---------------------------------------------
    w("## The first-order model, checked")
    w("")
    w("The row and the recorded budget are first order, and the source's own header calls it")
    w("the safe direction. Here it is measured.")
    w("")
    if disagree_sizes:
        w(f"**The two disagree on holds/fails at ladder points at {_list(disagree_sizes)} rows.** "
          "Where they do, first order says the array fails and the network says it holds.")
    else:
        w("The two agree on holds/fails at every ladder point at every size.")
    w("")
    if first_below_chance:
        w(f"First order also reaches accuracies below the 0.1 of chance at "
          f"{_list(first_below_chance)} rows. That is not a harder failure but an impossible one: past its")
        w("range it lets a column node rise above the driver that feeds it and reverses the sign")
        w("of a cell's current. The network cannot, and the solved model's lowest accuracy at "
          f"any size on this ladder is {exact_min:.4f}.")
        w("")
    w("| rows | worst cell keeps, at 2 Ω | at 20 Ω | at the last magnitude that holds |")
    w("|---|---|---|---|")
    for g in GRIDS:
        d = data[g]
        ex = d["exact"]
        keeps = [at(ex["magnitudes"], ex["worstCellFraction"], o) for o in CITED_OHM]
        last = ex["lastHolding"]
        kl = at(ex["magnitudes"], ex["worstCellFraction"], last) if last is not None else None
        w(f"| {d['rows']} | {keeps[0]:.1%} | {keeps[1]:.1%} | "
          f"{_f(kl, '.1%')} at {_f(last)} Ω |")
    w("")
    kept = [at(d["exact"]["magnitudes"], d["exact"]["worstCellFraction"], d["exact"]["lastHolding"])
            for d in data.values()]
    w("*Worst cell keeps* is the smallest ratio of effective to programmed conductance over")
    w("every cell of both rails, from the solved network: the cell furthest from both edges.")
    w(f"At the last magnitude that holds it is between {min(kept):.0%} and {max(kept):.0%} at "
      "every size. That is a property of these trained, differential, sparse-input arrays, and")
    w("says the accuracy tolerates a large loss at the corner; it is not a rule about crossbars.")
    w("")

    # -- the expectation ---------------------------------------------------------
    w("## The expectation on record")
    w("")
    w("Declared before the run, and not a thesis: for a uniform array the first-order far")
    w("corner loses `R·G·(N(N+1) + M(M+1))/2` of the drive, so a fixed fraction gives an edge")
    w("that falls as `1/N²`. From the row's 100 Ω at 36 rows that put 20 Ω failing between 64")
    w("and 144 rows and 2 Ω between 144 and 324. The trained arrays are sparse and")
    w("differential, and the declaration said the exponent might differ.")
    w("")
    w("| cited wiring | declared | first order | solved |")
    w("|---|---|---|---|")
    for ohm in CITED_OHM:
        lo, hi = DECLARED[ohm]
        w(f"| {ohm:g} Ω | fails between {lo} and {hi} rows | {_where(limit['first'][ohm])} | "
          f"{_where(limit['exact'][ohm])} |")
    w("")
    w("`edge × rows²`, at both ends of each bracket, so the scaling can be read without a fit:")
    w("")
    w("| rows | first order (holds, fails) | solved (holds, fails) |")
    w("|---|---|---|")
    for g in GRIDS:
        d = data[g]
        n2 = d["rows"] ** 2
        fo, ex = d["wire_resistance_ohm"], d["exact"]
        w(f"| {d['rows']} | {_f(fo['lastHolding'] and fo['lastHolding'] * n2, ',.0f')}, "
          f"{_f(fo['firstFailing'] and fo['firstFailing'] * n2, ',.0f')} | "
          f"{_f(ex['lastHolding'] and ex['lastHolding'] * n2, ',.0f')}, "
          f"{_f(ex['firstFailing'] and ex['firstFailing'] * n2, ',.0f')} |")
    w("")
    big = [d for d in data.values() if d["rows"] >= 144]
    spread = {}
    for key, name in (("lastHolding", "holds"), ("firstFailing", "fails")):
        v = [d["exact"][key] * d["rows"] ** 2 for d in big]
        spread[name] = max(v) / min(v) - 1
    w("A constant column would be `1/N²`. From 144 rows up the solved products sit within "
      f"{spread['holds']:.0%} of each other at the holding end and {spread['fails']:.0%} at the failing")
    w("end, so over that range the solved edge is consistent with `1/N²`; below it the")
    w("products are smaller and the edge falls less steeply. Both are properties of these")
    w("five brackets and neither is extrapolated past them.")
    w("")

    # -- the window ---------------------------------------------------------------
    w("## The window")
    w("")
    w("The row says the IR-drop bracket is conditional on the conductance window. It is")
    w("conditional on exactly one number: accuracy under IR drop depends on `R·G` alone, and")
    w("a test holds that. Scale every conductance by α and every wire resistance by 1/α and")
    w("each drop, and so each argmax, is unchanged. So an edge in ohms is the same edge in")
    w("`R·g_max`, and a window `k` times more conductive at the same ratio of 3 divides every")
    w("edge in ohms in this document by `k`.")
    w("")
    w("| rows | solved edge × g_max (holds, fails) |")
    w("|---|---|")
    for g in GRIDS:
        d = data[g]
        ex, gm = d["exact"], d["g_max"]
        lo = _f(ex["lastHolding"] and ex["lastHolding"] * gm, ".2e")
        hi = _f(ex["firstFailing"] and ex["firstFailing"] * gm, ".2e")
        w(f"| {d['rows']} | {lo}, {hi} |")
    w("")
    w("Dimensionless. It holds at a fixed ratio of 3 only; a different ratio changes the")
    w("weights' mapping onto the window and is not covered.")
    w("")

    # -- limits ---------------------------------------------------------------------
    w("## What this does not say")
    w("")
    w("- **Five sizes, one axis.** Rows vary; columns are fixed at ten by the task, so the")
    w("  row wire never lengthens. Nothing here is a claim about a larger layer split across")
    w("  tiles, which is a different study.")
    w("- **One window, one pitch.** A segment is resistance per length times the cell pitch,")
    w("  and both are held, so a different cell would change the ohm axis.")
    w("- **The device spread is still `UNSOURCED`.** Sources 1 and 2 are reported at every")
    w("  size and compared to nothing.")
    w("- **The other sizes are not the shared task.** Ideal accuracy rises with the grid")
    w("  because the task gets easier, and each size's pass mark rises with it.")
    w("- **The row itself is unchanged.** Its 6×6 IR-drop bracket is first order, and its")
    w("  failing side is first order's; the solved network at the same size is in the table")
    w("  above. Whether to move the row onto the solved model is a separate decision.")
    w("")
    w("## Sources")
    w("")
    w("Only the two wire resistances are cited here; everything else is this project's own")
    w("model or measurement.")
    w("")
    w("- Agrawal, Lee & Roy, “X-CHANGR” (2019), <https://arxiv.org/abs/1907.00285> —")
    w("  2 Ω per crossbar node at 65 nm.")
    w("- Victor, Kim, Wang, Roy & Gupta, “WAGONN” (2024),")
    w("  <https://arxiv.org/abs/2406.14706> — 2–10 Ω per bit-cell at 45–65 nm, up to")
    w("  20 Ω at 7 nm.")

    return "\n".join(L) + "\n"


def main() -> None:
    text = render()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("\n".join(text.splitlines()[:30]))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
