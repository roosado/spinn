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

Three rules this file exists to keep:

**No margin without a source.** Delivered precision is `UNSOURCED`, so the margin
column is *omitted* rather than estimated. photonn's mesh budget set the precedent.

**Edges are brackets, never interpolated.** "Holds at X, fails at Y." ``mc.pack``
deliberately stores no fitted crossing point, and neither does this.

**A design is checked, not sourced.** The operating point is this project's own
choice. What the row owes it is the check that a junction can physically be it --
:func:`design_check` -- with every outside number in that check cited below.

Run::

    .venv/Scripts/python.exe -m apps.report_row
"""
from __future__ import annotations

import json
import math
import os
import textwrap

import numpy as np

from apps.train_crossbar import ratio_dir, scale_dir
from spinn.handoff import read_handoff, read_test_set, read_weights

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUDGET = os.path.join(REPO, "exports", "error_budget.json")
HANDOFF = os.path.join(REPO, "exports", "crossbar_handoff.h5")
OUT = os.path.join(REPO, "docs", "comparison_row.md")

# -- numbers from outside this project ----------------------------------------
#
# Cited, not designed. The design is the operating point in the handoff; these are
# what show a magnetic tunnel junction can physically be it, and what else has been
# built. The row's "Sources" section says where each comes from.

#: Resistance-area product of a 2.0 nm MgO barrier, ohm um^2, at TMR 200-260%.
#: Hayakawa et al., Jpn. J. Appl. Phys. 44, L587 (2005).
RA_2NM_MGO_OHM_UM2 = 3.4e3

#: Current density at which spin transfer displaced domain walls, A/cm^2 -- "of the
#: order of" this. Lequeux et al., Sci. Rep. 6, 31510 (2016).
WALL_MOTION_A_PER_CM2 = 1.0e6

#: A commodity MRAM crossbar cell, low- then high-resistance state, ohms, access
#: transistor included; and the spread of each over 8,192 cells, as a fraction.
#: Jung et al., Nature 601, 211 (2022).
COMMODITY_CELL_OHM = (13e3, 26e3)
COMMODITY_SIGMA_REL = (1.6e3 / 13e3, 2.0e3 / 26e3)

#: imec's current-summing SOT-MRAM junction, on-state ohms. Doevenspeck et al.,
#: VLSI 2020, Table I.
IMEC_R_ON_OHM = 6e6

#: The measured spread of this device class: sigma/mu of R_P at the two electrical
#: CDs either side of this design's pillar, nm -> (RA 5, 20, 50 kOhm um^2). Read by
#: pixel off Fig. 8b of Doevenspeck et al., VLSI 2020 -- to 0.001, except the 50k
#: value at 127 nm, which is mostly hidden and good to 0.002 (docs/history.md,
#: 2026-10-04). Their own words: set by "process-induced area variations", and
#: "does not increase for increasing RA products".
IMEC_SIGMA_MU = {90: (0.049, 0.056, 0.063), 127: (0.033, 0.040, 0.031)}

#: The delivered precision: the envelope of both rows, and nothing interpolated
#: between them. Both ends are rungs of run_error_budget's area ladder.
DELIVERED_SIGMA_AREA = (
    min(v for row in IMEC_SIGMA_MU.values() for v in row),
    max(v for row in IMEC_SIGMA_MU.values() for v in row),
)

#: The chance one write attempt to an intermediate level misses: 1 minus the per-attempt
#: switching probability, as the median over 80 devices at each device's own best
#: current. The best intermediate level (G2) switches at 0.611 and the worst (G3) at
#: 0.505. Fig. 11(a) of Doevenspeck et al., VLSI 2021 (docs/history.md, 2026-10-06);
#: read by pixel, and the same two numbers as run_error_budget.m's FAIL_BEST/FAIL_WORST.
WRITE_FAIL_BEST = 0.389
WRITE_FAIL_WORST = 0.495
#: Verified attempts the bracket is reported at.
WRITE_ATTEMPTS = range(1, 7)

#: Conductance levels per device delivered by the four-pillar SOT track (five levels,
#: nine per differential pair, Fig. 7), and by the two-pillar track, reported beside it.
#: Set by the number of pillars on the track, not by their size.
DELIVERED_LEVELS = 5
DELIVERED_LEVELS_TWO_PILLAR = 3


def write_bracket(m: int) -> tuple[float, float]:
    """The write-error rates after ``m`` verified attempts: ``(best, worst)``.

    A write that misses is retried and checked, so ``m`` attempts leave
    ``p_fail ** m`` of the writes wrong at each level. Rounded to six places, as the
    ladder in run_error_budget.m is, so both ends are rungs of it exactly.
    """
    return (round(WRITE_FAIL_BEST**m, 6), round(WRITE_FAIL_WORST**m, 6))


# What imec measured on the four-pillar SOT track: Doevenspeck et al., "Multi-pillar
# SOT-MRAM for Accurate Analog in-Memory DNN Inference", VLSI Symposium (2021). All of
# it read by pixel off the figures (docs/history.md, 2026-10-06).

#: The five levels, from all four pillars antiparallel (the lowest conductance) to all
#: four parallel, and the median conductance of each over 80 devices, in microsiemens,
#: good to the reading error below. Fig. 16.
IMEC_LEVEL_LABELS = ("4AP", "3AP/1P", "2AP/2P", "1AP/3P", "4P")
IMEC_LEVELS_US = (37.84, 47.57, 57.29, 67.41, 76.95)
IMEC_LEVELS_READ_US = 0.07

#: Per-attempt maximum switching probability to each level, the median over 80 devices,
#: each device at its own best write current. Fig. 11(a). G1 and G5 are the end levels.
IMEC_P_SW_MEDIANS = {"G1": 0.99, "G2": 0.611, "G3": 0.505, "G4": 0.525, "G5": 1.00}

#: One mean switching probability over all five levels, from which the paper's Fig. 14 is
#: exactly ``(1 - mean) ** n`` to a pixel, and its headline read from that curve: "5 write
#: attempts are needed to reach a bit-error rate of 1e-3".
IMEC_P_SW_MEAN = 0.74
IMEC_HEADLINE = (5, 1e-3)

#: The smallest electrical CD in Fig. 8b of imec's 2020 paper (Doevenspeck et al., VLSI
#: 2020), nm: the smallest pillar anyone's spread has been measured on. The delivered
#: bracket uses the two sizes either side of this design's pillar, not this one.
IMEC_SMALLEST_CD_NM = 65

#: The calibrated-scale variant: the row's own weights with full scale at c * max|w|, at
#: DELIVERED_LEVELS states (apps.train_crossbar --calibrate-states). A sensitivity, like
#: the ratio variants; the row itself keeps max|w|.
SCALE_BUDGET = os.path.join(scale_dir(DELIVERED_LEVELS), "error_budget.json")
SCALE_NPZ = os.path.join(scale_dir(DELIVERED_LEVELS), "crossbar_ideal.npz")


#: The window ratios measured on integrated three-terminal junctions, and where they
#: were read; the delivered spread is judged at each beside the design's own. TMR by
#: RA at 80 nm nominal, imec 2020 Fig. 6, for the operating-point section.
MEASURED_RATIOS = {
    2.03: "imec 2021, four pillars, medians over 80 devices (Fig. 16)",
    1.85: "imec 2020, RA 5 kΩ·µm² (Fig. 6)",
}
IMEC_TMR_BY_RA = {5: 0.85, 20: 0.81, 50: 0.68}
IMEC_TMR_2021 = 1.03
#: The TMR imec's 2020 analysis assumed (its Fig. 11 and Table I).
IMEC_TMR_ASSUMED = 1.50

#: The area source run on the same array at each measured ratio.
RATIO_BUDGETS = {r: os.path.join(ratio_dir(r), "error_budget.json") for r in MEASURED_RATIOS}

#: Crossbar wiring per cell, ohms, from 65 nm (Agrawal et al., arXiv:1907.00285)
#: to 7 nm (Victor et al., arXiv:2406.14706); and the 7 nm line itself, ohms per
#: micron (Wang, Victor & Gupta, arXiv:2307.04261).
WIRE_OHM_PER_CELL = (2.0, 20.0)
WIRE_7NM_OHM_PER_UM = 182.0


def bits_from_sigma(sigma_rel: float) -> float:
    """``log2(range / sigma)`` where sigma is already a fraction of the range.

    This is why the config key is ``sigma_g_rel`` and not a value in siemens: the
    conversion needs no conductance window, so it does not depend on which window
    the design chose.
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


def margin(sweep: dict, delivered: tuple[float, float]) -> dict:
    """The delivered spread against a measured source's ladder, by the declared rule.

    It **holds** if the worse end of the delivered bracket holds, **fails** if the
    better end fails, and is otherwise **undetermined** at this resolution -- the
    rule declared in ``docs/history.md`` (2026-10-04) before the run. Both ends must
    be rungs of the ladder; an end between rungs is refused, because reading it
    would be an interpolation.

    Where it holds, the margin is itself a bracket in bits: ``log2(X/B)`` to
    ``log2(Y/B)``, X the last rung that holds and Y the first that fails, because the
    edge is only known to lie between two rungs. An edge beyond the ladder gives an
    open upper end. Where it fails, ``short_bits`` is the same bracket from the other
    side, against the better end.
    """
    best, worst = delivered
    mags, holds = list(sweep["magnitudes"]), list(sweep["holds"])

    def rung(value):
        hits = [i for i, m in enumerate(mags) if math.isclose(m, value, rel_tol=1e-9)]
        if not hits:
            raise ValueError(
                f"{value:g} is not on the ladder {mags}: the delivered bracket has to "
                "be, or the verdict would be an interpolation")
        return hits[0]

    ib, iw = rung(best), rung(worst)
    holds_best, holds_worst = bool(holds[ib]), bool(holds[iw])
    if holds_worst and not holds_best:
        raise ValueError(
            "the worse delivered end holds where the better one fails: the ladder is "
            "not monotone between them, and no verdict follows from it")

    # jsonencode writes NaN as null: an edge beyond the ladder arrives as None.
    x, y = (math.nan if v is None else v for v in (sweep["lastHolding"], sweep["firstFailing"]))
    out = {
        "at_best": sweep["accMean"][ib], "at_worst": sweep["accMean"][iw],
        "holds_at_best": holds_best, "holds_at_worst": holds_worst,
        "edge": (x, y),
    }
    if holds_worst:
        out["verdict"] = "holds"
        out["bits"] = (math.log2(x / worst),
                       math.inf if math.isnan(y) else math.log2(y / worst))
    elif not holds_best:
        out["verdict"] = "fails"
        out["short_bits"] = (math.log2(best / y),
                             math.inf if math.isnan(x) else math.log2(best / x))
    else:
        out["verdict"] = "undetermined"
    return out


def ohms(v: float) -> str:
    return f"{v / 1e3:g} kΩ" if v >= 1e3 else f"{v:g} Ω"


def edge_text(edge: tuple[float, float]) -> str:
    x, y = edge
    if math.isnan(y):
        return f"holds at every rung to {x:g}"
    if math.isnan(x):
        return f"fails at every rung from {y:g}"
    return f"{x:g} → {y:g}"


def verdict_text(m: dict) -> str:
    """One margin, as a table cell. Brackets stay brackets."""
    if m["verdict"] == "holds":
        lo, hi = m["bits"]
        if math.isinf(hi):
            return f"**holds**, by at least {lo:.2f} bits"
        return f"**holds**, by {lo:.2f}–{hi:.2f} bits"
    if m["verdict"] == "fails":
        lo, hi = m["short_bits"]
        return f"**fails**, short by up to {hi:.2f} bits" if not math.isinf(hi) else "**fails**"
    return "**undetermined**"


def margin_cell(verdicts: list) -> str:
    """The row's Margin cell: the design's verdict first, then the measured ratios."""
    (r0, _, _, m0), *rest = verdicts
    others = "; ".join(f"{m['verdict']} at the measured {r:g}" for r, _, _, m in rest)
    return f"{verdict_text(m0)} at the design ratio of {r0:g}; {others} — see below"


def said(m: dict) -> str:
    return "is undetermined" if m["verdict"] == "undetermined" else m["verdict"]


def design_verdict_prose(m: dict, pillar_nm: float) -> str:
    """What the design ratio's verdict means, in the words that fit it."""
    x, y = m["edge"]
    if m["verdict"] == "undetermined":
        return ("**At the design ratio the margin is undetermined, which is not the same as "
                f"missing.** This array's edge lies between σ/μ = {x:g} and {y:g}, inside "
                "the delivered bracket: it holds at the spread imec measured on pillars "
                "larger than this one and fails at the spread they measured on smaller "
                f"ones. Which side of {pillar_nm:.0f} nm a fabricated junction falls on "
                "decides it, and the test vehicle cannot.")
    if m["verdict"] == "holds":
        return ("**At the design ratio the margin holds**: the worse end of the delivered "
                f"bracket is inside this array's edge, which lies between σ/μ = {x:g} and "
                f"{y:g} — {verdict_text(m).removeprefix('**holds**, ')}.")
    return ("**At the design ratio the margin fails**: even the better end of the "
            "delivered bracket is past this array's edge.")


def level_verdict(sweep: dict, levels: int) -> dict:
    """One delivered level count, read off the states ladder: holds or fails.

    A count is a single value, not a bracket, so unlike :func:`margin` the verdict can
    never be undetermined. ``levels`` has to be a rung of the ladder -- a count between
    rungs would be an interpolation, which is refused here as it is there.
    """
    mags = list(sweep["magnitudes"])
    hits = [i for i, m in enumerate(mags) if math.isclose(m, levels, rel_tol=1e-9)]
    if not hits:
        raise ValueError(
            f"{levels} levels is not on the states ladder {mags}: a delivered count has "
            "to be a rung, or the verdict would be an interpolation")
    i = hits[0]
    return {"levels": levels, "acc": sweep["accMean"][i],
            "verdict": "holds" if sweep["holds"][i] else "fails"}


def attempts_verdicts(sweep: dict) -> list[dict]:
    """The write source judged at every number of verified attempts, by :func:`margin`.

    Each entry is ``margin(sweep, write_bracket(m))`` with ``m`` and the bracket beside
    it. The rule is the declared one and works unchanged on a write ladder, because a
    larger rate is worse, as a larger sigma is. Both ends of every bracket have to be
    rungs, or :func:`margin` refuses.
    """
    return [{"m": m, "bracket": write_bracket(m), **margin(sweep, write_bracket(m))}
            for m in WRITE_ATTEMPTS]


def fewest_attempts(verdicts: list[dict]) -> int | None:
    """The smallest number of attempts whose verdict is *holds*, or None if none does."""
    return next((v["m"] for v in verdicts if v["verdict"] == "holds"), None)


def attempts_monotone(verdicts: list[dict]) -> bool:
    """Whether every number of attempts above the fewest that holds holds too.

    More attempts leave a smaller rate, so a verdict that stops holding as they grow is
    not an edge but noise in the sweep, and the report says so rather than hides it.
    True when nothing holds, because there is nothing to contradict.
    """
    fewest = fewest_attempts(verdicts)
    return fewest is None or all(v["verdict"] == "holds" for v in verdicts if v["m"] > fewest)


def verdict_runs(verdicts: list[dict]) -> str:
    """The verdicts by attempts, runs collapsed: ``fails at m = 1–3, holds at m = 4–6``."""
    runs: list[list] = []
    for v in verdicts:
        if runs and runs[-1][0] == v["verdict"]:
            runs[-1][2] = v["m"]
        else:
            runs.append([v["verdict"], v["m"], v["m"]])
    return ", ".join(
        f"{'is undetermined' if name == 'undetermined' else name} at m = "
        + (f"{lo}" if lo == hi else f"{lo}–{hi}")
        for name, lo, hi in runs)


def write_verdict_text(v) -> str:
    """One write verdict, as a table cell: no bits, because a rate is not a bit depth.

    Takes a margin (or an entry of :func:`attempts_verdicts`), or the verdict string.
    """
    name = v["verdict"] if isinstance(v, dict) else v
    if name not in ("holds", "fails", "undetermined"):
        raise ValueError(f"{name!r} is not a verdict")
    return f"**{name}**"


def _absent(v) -> bool:
    """jsonencode writes NaN as null: an edge beyond the ladder arrives as None."""
    return v is None or (isinstance(v, float) and math.isnan(v))


def _acc_at(sweep: dict, magnitude: float) -> float:
    for m, a in zip(sweep["magnitudes"], sweep["accMean"]):
        if math.isclose(m, magnitude, rel_tol=1e-9):
            return a
    raise ValueError(f"{magnitude:g} is not on the ladder {list(sweep['magnitudes'])}")


def write_edge_cells(sweep: dict) -> tuple[str, str]:
    """A ladder's two edges as the "holds at" and "fails at" cells of the bracket table.

    With the accuracy at each rung. An edge beyond the ladder is said as
    :func:`edge_text` says it, and not given a value it does not have.
    """
    x, y = (None if _absent(sweep[k]) else sweep[k] for k in ("lastHolding", "firstFailing"))
    holds = f"r = {x:g} ({_acc_at(sweep, x):.4f})" if x is not None else "—"
    if y is not None:
        fails = (f"r = {y:g} ({_acc_at(sweep, y):.4f})" if x is not None
                 else f"{edge_text((math.nan, y))} ({_acc_at(sweep, y):.4f})")
    else:
        fails = edge_text((x, math.nan))
    return holds, fails


def write_edge_phrase(sweep: dict) -> str:
    """The same two edges as a clause: ``holds at r = X and fails at r = Y``."""
    x, y = (math.nan if _absent(sweep[k]) else sweep[k] for k in ("lastHolding", "firstFailing"))
    if math.isnan(x) or math.isnan(y):
        return edge_text((x, y))
    return f"holds at r = {x:g} and fails at r = {y:g}"


def rounds_to_zero(weights, levels: int) -> tuple[int, int]:
    """How many weights land on zero when the lattice has ``levels`` steps per device.

    A differential pair stores ``round(w * (levels - 1)) / (levels - 1)``, half away
    from zero, so a weight is zero below ``1 / (2 * (levels - 1))`` of full scale and
    not at it. Returns ``(count, total)``.
    """
    small = np.abs(np.asarray(weights)) < 1.0 / (2.0 * (levels - 1))
    return int(small.sum()), int(small.size)


def para(text: str, width: int = 84) -> list[str]:
    """A paragraph of generated prose, wrapped like the hand-written lines around it."""
    return textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)


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


def design_check(g_min: float, g_max: float, read_voltage: float) -> dict:
    """The operating point as a device -- the check that it can be built.

    The window is designed rather than measured, and the rule it answers to is
    that a magnetic tunnel junction must be able to physically be it.

    - The resistances follow from the conductances, and the ratio is the TMR.
    - The pillar follows from the resistance-area product of a 2.0 nm MgO
      barrier: ``A = RA / R_P``, taken as a disc.
    - The read current density, set against the density at which spin transfer
      moved a domain wall, says whether a read can disturb the state it reads.
    - That same density pushed *through* the barrier says why the cell cannot be
      written that way, and so has to be three-terminal.
    """
    r_p, r_ap = 1.0 / g_max, 1.0 / g_min
    area_um2 = RA_2NM_MGO_OHM_UM2 / r_p
    i_read = read_voltage / r_p
    j_read = i_read / (area_um2 * 1e-8)                       # 1 um^2 = 1e-8 cm^2
    return {
        "r_p": r_p,
        "r_ap": r_ap,
        "tmr": (r_ap - r_p) / r_p,
        "pillar_nm": 2.0 * math.sqrt(area_um2 / math.pi) * 1e3,
        "i_read": i_read,
        "read_below_wall_motion": WALL_MOTION_A_PER_CM2 / j_read,
        # A/cm^2 -> A/m^2 is 1e4; ohm um^2 -> ohm m^2 is 1e-12.
        "write_through_barrier_v": WALL_MOTION_A_PER_CM2 * 1e4 * RA_2NM_MGO_OHM_UM2 * 1e-12,
    }


_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
          8: "eight", 9: "nine"}


def number_word(n: int) -> str:
    return _WORDS.get(n, str(n))


def load_scale() -> tuple[dict, dict]:
    """The calibrated variant's budget and its ideal file.

    Raises if either is missing, or if the budget predates the write source. The section
    on delivered levels is built on it, and a document that quietly left it out would
    look complete.
    """
    for path in (SCALE_BUDGET, SCALE_NPZ):
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"{path} is missing. The section on delivered levels needs the calibrated "
                f"variant: `python -m apps.train_crossbar --calibrate-states {DELIVERED_LEVELS}`, "
                "then spinn-hw/run_error_budget.m")
    with open(SCALE_BUDGET, encoding="utf-8") as fh:
        budget = json.load(fh)
    if "write_error_rate" not in budget:
        raise KeyError(f"{SCALE_BUDGET} has no write_error_rate: it predates the write source; "
                       "re-run spinn-hw/run_error_budget.m")
    with np.load(SCALE_NPZ) as z:
        ideal = {k: z[k] for k in z.files}
    if int(ideal["calibrated_states"]) != DELIVERED_LEVELS:
        raise ValueError(f"{SCALE_NPZ} was calibrated at {int(ideal['calibrated_states'])} "
                         f"states, not {DELIVERED_LEVELS}")
    return budget, ideal


def delivered_levels_lines(b: dict, weights, d: dict, cb) -> list[str]:
    """The section on delivered levels and write errors, from the budgets and the weights.

    Split out of :func:`render` because it reads three things the rest of the row does
    not: the calibrated variant, imec's measured constants, and the row's own write block.
    Where a sentence is only true of one outcome it raises on the other rather than say
    it, as ``apps/report_size.py`` does.
    """
    L, L2 = DELIVERED_LEVELS, DELIVERED_LEVELS_TWO_PILLAR
    thr = b["threshold"]
    sta, wr, wir = b["states_per_device"], b["write_error_rate"], b["wire_resistance_ohm"]
    sb, sz = load_scale()
    sw = sb["write_error_rate"]
    if sb["threshold"] != thr:
        raise ValueError(f"the variant is judged at {sb['threshold']}, not the row's {thr}: "
                         "the section says it is judged against the row's own pass mark")

    plural = {"holds": "hold", "fails": "fail"}
    v5, v3 = level_verdict(sta, L), level_verdict(sta, L2)
    if v5["verdict"] != "fails":
        raise ValueError(f"{L} levels hold at the row's scale; the section's account of why "
                         "write errors are measured at more is no longer true")
    states = int(wr["states"])
    if states in (L, L2):
        raise ValueError(f"the row's write errors ran at {states} states, a delivered count: "
                         "the section says that bracket is compared to nothing")
    if states != int(sta["lastHolding"]):
        raise ValueError(f"the row's write errors ran at {states} states, not at the fewest "
                         f"the row holds at ({int(sta['lastHolding'])}), which the section says")
    cal = level_verdict(sb["states_per_device"], L)
    own = sb["ownPassMark"]

    lines = ["## Delivered levels and write errors", ""]

    # -- what imec measured ----------------------------------------------------------
    steps = np.diff(IMEC_LEVELS_US)
    mean_step = (IMEC_LEVELS_US[-1] - IMEC_LEVELS_US[0]) / (len(IMEC_LEVELS_US) - 1)
    uneven = float(np.max(np.abs(steps - mean_step)) / mean_step)
    lines += para(
        f"**Measured, for this device class.** imec's multi-pillar junctions (Doevenspeck et "
        f"al. 2021) put {number_word(L - 1)} pillars on one spin-orbit-torque track, and the write "
        f"current chooses how many of them switch: {number_word(L)} conductance levels per device "
        f"and {number_word(2 * L - 1)} per differential pair (their Fig. 7). "
        f"{number_word(L2 - 1).capitalize()} pillars give {number_word(L2)}. The count is set by the "
        "pillars on the track and not by their size, so, unlike a spread, it carries to this "
        "design as it stands. The medians over 80 devices, in µS, read off their Fig. 16 "
        f"(each good to ±{IMEC_LEVELS_READ_US:g}):")
    lines += [
        "",
        "| | " + " | ".join(IMEC_LEVEL_LABELS) + " |",
        "|---|" + "---|" * len(IMEC_LEVEL_LABELS),
        "| median conductance, µS | " + " | ".join(f"{g:.2f}" for g in IMEC_LEVELS_US) + " |",
        "",
    ]
    step_text = ", ".join(f"{s:.2f}" for s in steps[:-1]) + f" and {steps[-1]:.2f}"
    lines += para(
        f"The steps between them are {step_text} µS: evenly spaced, to within {uneven:.1%} of "
        f"their mean of {mean_step:.2f} µS. That is the lattice `program()` assumes, so the "
        f"paper's weight table is `program()` at {number_word(L)} states, with zero stored as both "
        f"devices at {IMEC_LEVEL_LABELS[0]}.")
    lines.append("")

    # -- the verdict at this size ----------------------------------------------------
    same = v3["verdict"] == v5["verdict"]
    lines += para(
        f"**At the row's own scale, {number_word(L)} levels per device {plural[v5['verdict']]}:** "
        f"{v5['acc']:.4f} against the pass mark of {thr:.4f}. "
        f"{number_word(L2).capitalize()} levels, the two-pillar device, "
        f"{'also ' if same else ''}**{plural[v3['verdict']]}** at {v3['acc']:.4f}. The row's own "
        f"states bracket, as a required precision, is {int(sta['lastHolding'])} states holding "
        f"and {int(sta['firstFailing'])} failing. A count is one rung of the states ladder, so "
        "this verdict is holds or fails and never undetermined.")
    lines.append("")

    # -- the failure is the scale ----------------------------------------------------
    zero_below = 1.0 / (2.0 * (L - 1))
    k_row, total = rounds_to_zero(weights, L)
    k_cal, _ = rounds_to_zero(sz["weights"], L)
    c = float(sz["scale_c"])
    clipped = float(np.mean(np.abs(weights) > c * np.abs(weights).max()))
    lines += para(
        "**The failure is the scale, not the device.** The row maps max|w| to full scale, so "
        f"one outlier weight sets the lattice for all {total} weights. At {number_word(L)} levels a "
        f"weight rounds to zero below 1/(2·{L - 1}) = {zero_below:g} of full scale, and "
        f"{k_row} of the row's {total} ({k_row / total:.0%}) are that small.")
    lines.append("")
    lines += para(
        f"Put full scale at c·max|w| instead and clip what lies beyond it. The train-set "
        f"accuracy maximiser at {number_word(L)} states is c = {c:g}, which clips {clipped:.1%} of the "
        f"weights and leaves {k_cal} of {total} ({k_cal / total:.0%}) rounding to zero. Its "
        f"continuous ideal is {sb['ideal']:.4f}, against the row's {b['ideal']:.4f}. At "
        f"{number_word(L)} levels it reaches {cal['acc']:.4f}, which **{cal['verdict']}** "
        f"against the row's own pass mark of {thr:.4f}; against 95% of its own ideal, {own:.4f}, "
        f"it {'holds' if cal['acc'] >= own else 'fails'}.")
    lines.append("")
    lines += para(
        "**The row keeps max|w|.** This calibrated scale is a sensitivity, like the measured "
        "ratios, and not a redesign: it moves where the largest weight sits in the window and "
        f"nothing else about the array, and it covers the row's {b['nRows']}×{b['nCols']} array "
        "only. Quantisation-aware training, which would fit the weights to the lattice instead, "
        "was tried and did worse than quantising afterwards (`docs/history.md`, 2026-10-06); "
        "it is machine learning, and stays out of scope.")
    lines.append("")

    # -- writes ----------------------------------------------------------------------
    names = list(IMEC_P_SW_MEDIANS)
    inner = names[1:-1]
    best_key = max(inner, key=IMEC_P_SW_MEDIANS.get)
    worst_key = min(inner, key=IMEC_P_SW_MEDIANS.get)

    def p_text(p: float) -> str:
        s = f"{p:.3f}"
        return s[:-1] if s.endswith("0") else s

    lines += para(
        "**Writing is stochastic.** imec's Fig. 11(a) gives the per-attempt maximum switching "
        "probability to each level, the median over 80 devices, each at its own best write "
        "current:")
    lines += [
        "",
        "| level | " + " | ".join(f"{k} ({lab})" for k, lab in zip(names, IMEC_LEVEL_LABELS)) + " |",
        "|---|" + "---|" * len(names),
        "| median switching probability | "
        + " | ".join(p_text(IMEC_P_SW_MEDIANS[k]) for k in names) + " |",
        "",
    ]
    lines += para(
        "**The model.** With probability r a device programmed to an intermediate level j "
        "lands on j − 1 or j + 1 instead, half each: imec's Fig. 9 shows a missed write going to "
        "the two neighbouring levels about equally. Level 0 is the reset state and takes no write "
        f"pulse, and the top level switches at {p_text(IMEC_P_SW_MEDIANS[names[-1]])} "
        f"({names[-1]}), so neither misses. Every rail of every pair is independent, and the "
        "error is applied to the programmed levels before the spread. It needs a lattice to "
        "miss, so it requires a number of states per device.")
    lines.append("")
    lines += para(
        "A missed write can be read back and retried. Taking each attempt as independent of "
        "the last, as imec's own Fig. 14 does, what is left after m verified attempts is the "
        f"miss probability to the m-th power. The best intermediate level, {best_key}, misses "
        f"{WRITE_FAIL_BEST:g} of the time and the worst, {worst_key}, {WRITE_FAIL_WORST:g}, so "
        f"the delivered rate after m attempts is the bracket "
        f"[{WRITE_FAIL_BEST:g}^m, {WRITE_FAIL_WORST:g}^m]. It is judged by the same rule as "
        "the spread: it holds if the worse end holds, fails if the better end fails, and is "
        "otherwise undetermined at this resolution.")
    lines.append("")

    av = attempts_verdicts(sw)
    fewest = fewest_attempts(av)
    lines += para(
        f"**For the calibrated variant at {number_word(L)} states**, where the levels "
        f"{plural[cal['verdict']]}, the write source {write_edge_phrase(sw)}. Accuracy against the pass mark of {thr:.4f}:")
    lines += [
        "",
        "| attempts | delivered rate | at best end | at worst end | verdict |",
        "|---|---|---|---|---|",
        *[f"| {v['m']} | {v['bracket'][0]:g}–{v['bracket'][1]:g} | {v['at_best']:.4f} | "
          f"{v['at_worst']:.4f} | {write_verdict_text(v)} |" for v in av],
        "",
    ]
    if fewest is None:
        lines += para(f"No number of attempts up to {max(WRITE_ATTEMPTS)} holds: by attempts "
                      f"the write source {verdict_runs(av)}.")
    else:
        tail = (", and every larger number holds too" if attempts_monotone(av) else
                ", but a larger number does not: **the verdict is not monotone in the attempts**, "
                "so the fewest is not an edge")
        again = ""
        if fewest == IMEC_HEADLINE[0]:
            again = (" That is the number imec quote, reached here for a different reason: the "
                     "pass mark, not a bit-error rate.")
        lines += para(f"**The fewest verified attempts at which it holds is m = {fewest}**"
                      f"{tail}. By attempts the write source {verdict_runs(av)}.{again}")
    lines.append("")

    # -- the row at its own scale ---------------------------------------------------
    lines += para(
        f"**The row at its own scale.** {number_word(L).capitalize()} levels fail before a write can "
        f"matter, so the row's write errors are measured at {states} states, the fewest it "
        f"holds at: the write source {write_edge_phrase(wr)}. No delivered device has {states} "
        "levels, so that bracket is a required precision and is compared to nothing.")
    lines.append("")

    # -- the paper's headline ------------------------------------------------------
    n_head, rate_head = IMEC_HEADLINE
    left = (1.0 - IMEC_P_SW_MEAN) ** n_head
    first_n = next(n for n in range(1, 100) if (1.0 - IMEC_P_SW_MEAN) ** n <= rate_head)
    lo5, hi5 = write_bracket(n_head)
    lines += para(
        f"**imec's headline is a mean.** Their Fig. 14 reads {n_head} write attempts to reach a "
        f"rate of {rate_head:g}, and it is (1 − {IMEC_P_SW_MEAN:g})^n: the paper's own mean "
        f"switching probability over all five levels. That mean includes {names[0]} and "
        f"{names[-1]}, which switch at {p_text(IMEC_P_SW_MEDIANS[names[0]])} and "
        f"{p_text(IMEC_P_SW_MEDIANS[names[-1]])}, so it is higher than the switching "
        f"probability of any level a write can miss. At n = {n_head} it leaves {left:.2e} (the rate is strictly first met at "
        f"{first_n} attempts). The intermediate levels' own medians leave {lo5:.2e} to "
        f"{hi5:.2e} at the same n, {lo5 / left:.0f} to {hi5 / left:.0f} times as much.")
    lines.append("")

    # -- what it leaves out ---------------------------------------------------------
    lines += para(
        "**What this leaves out.** Fig. 11 is each device's own best write current, so one "
        "current shared across an array would do worse: by how much is `UNSOURCED`. And the "
        "time and energy the attempts cost are not computed. They are `UNSOURCED` too, beside "
        "the read time below.")
    lines.append("")

    # -- the geometry -----------------------------------------------------------------
    k = L - 1
    edge_x, edge_y = wir["lastHolding"], wir["firstFailing"]
    half = d["pillar_nm"] / math.sqrt(k)
    smaller = "smaller than" if half < IMEC_SMALLEST_CD_NM else "no smaller than"
    lines += para(
        f"**The geometric tension.** {number_word(k).capitalize()} pillars at this design's "
        f"{d['pillar_nm']:.0f} nm multiply the conductance by {k}, so every IR-drop edge in "
        f"ohms divides by {k}: the row's {ohms(edge_x)} holding and {ohms(edge_y)} failing "
        f"(first order) become {ohms(edge_x / k)} and {ohms(edge_y / k)}. Keeping the "
        f"{cb.g_min * 1e6:g}–{cb.g_max * 1e6:g} µS window instead needs pillars about "
        f"{half:.0f} nm across, each 1/{k} of the area — {smaller} the smallest "
        f"pillar in imec's spread measurement, about {IMEC_SMALLEST_CD_NM} nm electrical "
        "(Fig. 8b of the 2020 paper). Neither is modelled.")
    lines.append("")
    return lines


def render() -> str:
    """The row, assembled from the recorded budget and the handoff.

    Split out from :func:`main` so the committed ``docs/comparison_row.md`` can be
    compared against what this module produces now -- the same bargain
    ``apps/build_site.py`` and ``apps/export_web_data.py`` make for their own
    generated files. This one needs it most: the row reads like prose somebody
    wrote, so the natural way to fix a sentence in it is to edit the file, and the
    next run of this module would discard that silently.
    """
    with open(BUDGET, encoding="utf-8") as fh:
        b = json.load(fh)
    h = read_handoff(HANDOFF)
    weights = read_weights(HANDOFF)
    images, _ = read_test_set(HANDOFF)

    if "write_error_rate" not in b:
        raise KeyError(f"{BUDGET} has no write_error_rate: it predates the write source; "
                       "re-run spinn-hw/run_error_budget.m")
    ideal, thr = b["ideal"], b["threshold"]
    sig, sta, wir = b["sigma_g_rel"], b["states_per_device"], b["wire_resistance_ohm"]
    wr = b["write_error_rate"]
    wr_holds, wr_fails = write_edge_cells(wr)

    sig_hold, sig_fail = bits_from_sigma(sig["lastHolding"]), bits_from_sigma(sig["firstFailing"])
    sta_hold = bits_from_states(int(sta["lastHolding"]), h.scheme)
    sta_fail = bits_from_states(int(sta["firstFailing"]), h.scheme)

    power = array_read_power(h, weights, images)
    joint = b["joint"]

    # The delivered spread, judged at the design's ratio and at each measured one.
    area = b["sigma_area_rel"]
    judged = [(h.crossbar().ratio, "the design", area)]
    for r, where in MEASURED_RATIOS.items():
        with open(RATIO_BUDGETS[r], encoding="utf-8") as fh:
            judged.append((r, where, json.load(fh)["sigma_area_rel"]))
    verdicts = [(r, where, s, margin(s, DELIVERED_SIGMA_AREA)) for r, where, s in judged]
    lo, hi = DELIVERED_SIGMA_AREA

    # The operating point, as a device, and against the windows other work chose.
    cb = h.crossbar()
    d = design_check(cb.g_min, cb.g_max, cb.read_voltage)
    thin = (1.0 / COMMODITY_CELL_OHM[0] / cb.g_max, 1.0 / COMMODITY_CELL_OHM[1] / cb.g_min)
    imec = cb.g_max * IMEC_R_ON_OHM
    edge = wir["lastHolding"]

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
        f"| Delivered precision | **σ/μ = {lo:g}–{hi:g}**, measured on this device class "
        "(Doevenspeck et al. 2020) — a bracket, see below |",
        f"| Margin | {margin_cell(verdicts)} |",
        f"| Energy per inference | `UNSOURCED`; array read power **{power * 1e6:.3f} µW** |",
        "| Latency per inference | `UNSOURCED` |",
        "",
        f"Array **{b['nRows']}×{b['nCols']}**, {b['nDevices']} devices, {b['scheme']} pairs.",
        f"Pass mark **{thr:.4f}** = 95% of ideal, declared before the sweeps were run.",
        f"Operating point **{cb.g_min * 1e6:g}–{cb.g_max * 1e6:g} µS at {cb.read_voltage:g} V**, "
        "a design checked against device physics — see below.",
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
        f"| 1, measured: area variation | σ/μ = {area['lastHolding']:g} "
        f"({area['meanAtLastHolding']:.4f}) | σ/μ = {area['firstFailing']:g} "
        f"({area['accMean'][area['holds'].index(False)]:.4f}) | *judged against the "
        "delivered spread — see below* |",
        f"| 2. resolvable states | {int(sta['lastHolding'])} states/device | "
        f"{int(sta['firstFailing'])} states/device | holds at {sta_hold:.2f}, "
        f"fails at {sta_fail:.2f} |",
        f"| 2, written: write errors, at {int(wr['states'])} states | {wr_holds} | {wr_fails} | "
        "*a rate, not a bit depth — judged against delivered writes below* |",
        f"| 3. IR drop | {wir['lastHolding']:g} Ω per segment | "
        f"{wir['firstFailing']:g} Ω per segment | *not a bit depth — see below* |",
        "",
        "**Conductance variation binds.** It demands "
        f"{sig_hold:.2f} bits where the states knob demands {sta_hold:.2f}, and both are",
        "expressed against the same conductance window, so the comparison is like for",
        "like. That was the prediction on record before any of this ran.",
        "",
        "**Source 1 is measured twice, and the two are never combined.** As a uniform σ",
        "against the window it is the required precision, in the hub's unit. As area",
        "variation — each device's whole conductance times `a ~ N(1, σ)`, the form imec",
        "measured — it is what the delivered spread is judged with. They are two models",
        "of one spread, so the joint run below uses the first and not both.",
        "",
        *para("**Source 2 is measured twice too, and likewise never combined.** As levels "
              "per device it is the required precision in the hub's unit, and it is judged "
              "against the levels imec delivers. As written levels — a device programmed to "
              "one level can land on a neighbour — it is a write error rate, which needs a "
              "lattice to miss, so it runs at "
              f"{int(wr['states'])} states per device, the fewest the row holds at. A rate is "
              "not a bit depth, so it is not converted."),
        "",
        "**IR drop is deliberately not converted to bits.** It is a position-dependent",
        "systematic, not a spread on a stored value, so `log2(range/σ)` has no σ to take.",
        "Forcing it into the unit would be a category error. The statement that means",
        f"something is the one in the table: at this array size the design tolerates",
        f"{wir['lastHolding']:g} Ω per wire segment and fails by {wir['firstFailing']:g} Ω.",
        "**That number is meaningless without the array size beside it**, which is why",
        "the size is fixed and reported. How it moves with the size — and how far the",
        "first-order model behind its failing side is from the network it approximates —",
        "is measured in `docs/array_size.md`. The failing side above is first order's.",
        "",
        "**It is equally conditional on the conductance window.** A wire drop is `R·I`,",
        "and `I` is set by the absolute conductance of the devices — so unlike sources 1",
        "and 2, this bracket does not cancel the window. Accuracy under IR drop depends",
        "on `R·G` alone, so holding the ratio at 3 and moving the window by a decade",
        f"moves the edge by a decade: at a tenth of this window "
        f"{ohms(wir['lastHolding'] * 10)} holds, and at ten times it",
        f"{ohms(wir['firstFailing'] / 10)} has already failed.",
        "",
        "**At this size and in this window, IR drop does not bind.** Published crossbar",
        f"wiring runs from {WIRE_OHM_PER_CELL[0]:g} Ω per cell at 65 nm (Agrawal et al. 2019),",
        f"through 2–10 Ω across 45–65 nm, to about {WIRE_OHM_PER_CELL[1]:g} Ω at 7 nm (Victor",
        f"et al. 2024; Wang et al. 2023). The design holds to {edge:g} Ω, so the wiring",
        f"would have to be {edge / WIRE_OHM_PER_CELL[1]:g} times worse than the most scaled "
        "of those before this",
        "source bound. A segment is resistance per length times the cell pitch — on",
        f"7 nm minimum-pitch wiring, {WIRE_7NM_OHM_PER_UM:g} Ω/µm, {edge:g} Ω is a "
        f"{edge / WIRE_7NM_OHM_PER_UM:.2f} µm pitch — so",
        "a cell that large is wired wider than minimum.",
        "",
        "What keeps the wires out of this budget is the window. A thin-barrier memory",
        f"cell is {thin[0]:.0f}–{thin[1]:.0f} times more conductive than this design (Jung et al.",
        "2022 measured 13 and 26 kΩ, access transistor included), past the tenfold at",
        f"which {ohms(wir['firstFailing'] / 10)} already fails.",
        "",
        "## The joint run",
        "",
        f"All three sources at the last magnitude each individually held: mean "
        f"**{joint['mean']:.4f}** ± {joint['std']:.4f}, which is "
        f"**{'above' if joint['holds'] else 'below'}** the pass mark.",
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
        "## The operating point",
        "",
        "The window and the drive are a **design point, not a measurement** — this",
        "project's own choice, held to one rule: a magnetic tunnel junction must be able",
        "to physically be it, and every step of that check is cited. The sources back",
        "the claim; none of their numbers is copied into the design.",
        "",
        "| | design | what makes it buildable |",
        "|---|---|---|",
        f"| `g_max_s`, `g_min_s` | {cb.g_max * 1e6:g} µS and {cb.g_min * 1e6:g} µS: "
        f"{d['r_p'] / 1e3:.0f} kΩ and {d['r_ap'] / 1e6:g} MΩ | a ratio of "
        f"{cb.g_max / cb.g_min:g} is a TMR of {d['tmr']:.0%}. A CoFeB/MgO junction with a "
        f"2.0 nm barrier measures 200–260% at RA = {RA_2NM_MGO_OHM_UM2 / 1e3:g} kΩ·µm² "
        f"(Hayakawa et al. 2005), which puts {d['r_p'] / 1e3:.0f} kΩ at a pillar about "
        f"{d['pillar_nm']:.0f} nm across |",
        "| the write path | three-terminal | spin transfer moves a domain wall at "
        "~10⁶ A/cm² (Lequeux et al. 2016); through that barrier the same density needs "
        f"{d['write_through_barrier_v']:.0f} V across 2 nm of oxide. So the cell is "
        "written along a low-impedance line — a spin-Hall strip (Liu et al. 2012) or "
        "the domain-wall track (Alamdar et al. 2021) — and read through the junction |",
        f"| `read_voltage_v` | {cb.read_voltage:g} V | at most {d['i_read'] * 1e6:.1f} µA "
        f"per device, about {d['read_below_wall_motion']:.0f} times below the density at "
        "which walls move: a read does not write |",
        "",
        "A ratio of about three is what Grollier et al. (2020) call typical, and",
        "perpendicular junctions reach 249% (Wang et al. 2018). Thin barriers give the",
        "ratio up — TMR falls from 165% at RA = 2.9 Ω·µm² to 27% at 0.8 (Ikeda et al.",
        "2005) — and memory cells accept that because their write current has to cross",
        "the barrier: Jung et al. (2022) note that a thicker insulator “would demand a",
        "higher write voltage or current”. A read-only junction carries no write",
        "current, and at this resistance a series access transistor is a small fraction",
        "of the cell.",
        "",
        *para("**The integrated devices come in lower.** The three-terminal junctions with "
              "a thick read barrier that imec integrated and measured run at TMR "
              f"{IMEC_TMR_BY_RA[5]:.0%} at RA 5 kΩ·µm², falling to {IMEC_TMR_BY_RA[50]:.0%} "
              "at 50 (Doevenspeck et al. 2020, Fig. 6, at 80 nm), and "
              f"{IMEC_TMR_2021:.0%} in a perpendicular four-pillar stack (Doevenspeck et "
              f"al. 2021, Fig. 16) — against {d['tmr']:.0%} here, and against the "
              f"{IMEC_TMR_ASSUMED:.0%} imec's own analysis assumed. The design keeps "
              f"{d['tmr']:.0%}, because film-level junctions reach it and a window is a "
              "design value. But a delivered spread arrives as σ/μ and reaches the window "
              "through the ratio, so the margin below is judged at the measured ratios as "
              "well as at this one."),
        "",
        "**Other work chose other windows, for other machines.** Jung et al. (2022) built",
        "a 64×64 MRAM crossbar at 13 and 26 kΩ and summed *resistances* rather than",
        "currents, because a current-summing array of cells that conductive would draw",
        "too much power. imec's current-summing SOT-MRAM arrays went the other way, to",
        "R_on = 6 MΩ (Doevenspeck et al. 2020, Table I). A 7 nm",
        "simulation study used SOT junctions of 8–20 kΩ against 28–100 kΩ (Wang et al.",
        "2023), and domain-wall junctions have been made at 95% (Lequeux et al. 2016)",
        "and 164% TMR (Alamdar et al. 2021). This design sits between the two built",
        f"extremes: {thin[0]:.0f}–{thin[1]:.0f} times less conductive than the commodity "
        f"cell, {imec:.0f} times more than imec's.",
        "",
        "## Delivered precision",
        "",
        *para("**Measured, for this device class, and a bracket.** imec has measured the "
              "device-to-device spread of this kind of junction — three-terminal, written "
              "along a spin-orbit-torque track and read through the barrier — on 300 mm "
              "wafers (Doevenspeck et al. 2020). Two of their findings make it usable for a "
              "junction they did not build: the spread “does not increase for increasing RA "
              "products”, and it is “mostly determined by process-induced area variations”. "
              "It follows the pillar's size rather than its barrier, and this design's "
              "pillar size is known."),
        "",
        *para(f"That pillar is {d['pillar_nm']:.0f} nm across, electrically. imec measured "
              "either side of it, across three barriers (their Fig. 8b, read by pixel):"),
        "",
        "| electrical CD | σ/μ of R_P at RA 5, 20 and 50 kΩ·µm² |",
        "|---|---|",
        *[f"| ≈ {cd} nm | {', '.join(f'{v:.3f}' for v in row)} |"
          for cd, row in IMEC_SIGMA_MU.items()],
        "",
        *para(f"So the delivered spread is **σ/μ between {lo:.3f} and {hi:.3f}**, the "
              "envelope of both sizes, with nothing interpolated between them. It is "
              "adopted as the delivered spread *of the class* and not presented as more: by "
              "its authors' account it comes from a test vehicle and does “not represent "
              "the fundamental lower limit”, its barriers start at 5 kΩ·µm² against "
              f"{RA_2NM_MGO_OHM_UM2 / 1e3:g} here, and its values are read off a figure. "
              "imec's multi-pillar devices a year later agree with it: four pillars in "
              "parallel spread by σ/μ = 3.3–4.1% over 80 devices (Doevenspeck et al. 2021, "
              "Fig. 16), a single pillar's spread averaged over four."),
        "",
        *para("**Judged with the source built for it.** A spread set by area is "
              "proportional to conductance — a pillar that came out small is small in both "
              "states — so it is not source 1's uniform σ, and it is not converted into "
              "source 1's bits. Against this window it is "
              f"{lo / (cb.ratio - 1):.3f}–{hi / (cb.ratio - 1):.3f} on a device that is off "
              f"and {lo * cb.ratio / (cb.ratio - 1):.3f}–{hi * cb.ratio / (cb.ratio - 1):.3f} "
              "on one that is on: not one number. It is put against area variation "
              "instead, swept in σ/μ with both ends of the bracket on the ladder, so the "
              "verdict is read off ladder points rather than interpolated:"),
        "",
        f"| window ratio | area variation holds at → fails at | at σ/μ = {lo:.3f} | "
        f"at {hi:.3f} | verdict |",
        "|---|---|---|---|---|",
        *[f"| {r:g}, {where} | {edge_text(m['edge'])} | {m['at_best']:.4f} | "
          f"{m['at_worst']:.4f} | {verdict_text(m)} |" for r, where, _, m in verdicts],
        "",
        *para("The rule was declared before the run: it holds if the worse end of the "
              "bracket holds, fails if the better end fails, and is otherwise undetermined "
              "at this resolution."),
        "",
        *para(design_verdict_prose(verdicts[0][3], d["pillar_nm"])),
        "",
        *para("**The ratio decides as much as the spread.** "
              + " ".join(f"At {r:g} the margin {said(m)}." for r, _, _, m in verdicts[1:])
              + " A measured σ/μ reaches the window through the ratio, which is why the "
              "integrated TMR in the operating-point section matters to the margin and not "
              "only to the window. How the verdict moves with the array size is in "
              "`docs/array_size.md`."),
        "",
        *para("For scale, and nothing more: the commodity cell's measured spread is larger "
              f"than either end — σ/R of {COMMODITY_SIGMA_REL[1]:.1%} and "
              f"{COMMODITY_SIGMA_REL[0]:.1%} over 8,192 cells, access transistor included "
              "(Jung et al. 2022) — on a thin-barrier memory cell, a different device."),
        "",
        *delivered_levels_lines(b, weights, d, cb),
        "## Energy and latency",
        "",
        "Both are `UNSOURCED`, and the arithmetic is given so a reader can substitute.",
        "",
        f"Array read power is **{power * 1e6:.3f} µW** at the design operating point,",
        "computed exactly as `mean_over_samples( sum_ij V_i² · G_ij )` over all "
        f"{b['nDevices']}",
        "devices at the operating point in the handoff.",
        "",
        "That is **array only**: it excludes the sense amplifiers, the ADC and every",
        "digital stage after them. The periphery frequently dominates an analog",
        "accelerator's energy, and a figure that quietly omits it is not comparable to",
        "one that does not — so the boundary is stated rather than implied.",
        "",
        "**Energy per inference needs a read time, and a read time belongs to the sense",
        "amplifier**, which this model does not include. Energy = power × t_read. For",
        "scale: MRAM macros read in 4 ns counting sensing alone (Wei et al. 2019) and",
        "9 ns for a full access (Shih et al. 2020), and the commodity crossbar's columns",
        "settle in 13–29 ns through a time-domain readout (Jung et al. 2022). Latency is",
        "the settling of the lines into that amplifier: 2–20 Ω of wire per cell (above)",
        "and, in the commodity crossbar, 2.1 fF of line per cell (Jung et al. 2022; the",
        "textbook rule is about 0.2 fF/µm, Harris 1997).",
        "",
        "The power figure scales with the window and the drive: a thin-barrier window",
        f"{thin[0]:.0f}–{thin[1]:.0f} times more conductive would dissipate that much more "
        "for the same read voltage.",
        "",
        "**Sources 1 and 2 do not depend on the operating point.** The window and the",
        "drive cancel in the decode, exactly, and a test asserts the ideal accuracy is",
        "unchanged across unrelated windows — so the ideal accuracy and both bit depths",
        "stand whichever window a junction is built to. **Source 3 is the exception**,",
        "for the reason given under its bracket above: a wire drop is `R·I`, and there",
        "is no `I` without an absolute conductance.",
        "",
        "## Sources",
        "",
        "Every number quoted above from outside this project, and what it is cited for.",
        "The design values are this project's own; these are what show they can be built.",
        "",
        "- Agrawal, Lee & Roy, “X-CHANGR” (2019), <https://arxiv.org/abs/1907.00285> —",
        "  2 Ω per crossbar node at 65 nm.",
        "- Alamdar et al., *Appl. Phys. Lett.* 118, 112401 (2021),",
        "  <https://arxiv.org/abs/2010.13879> — three-terminal domain-wall MTJs for",
        "  in-memory computing; TMR 164%, RA 31 Ω·µm².",
        "- Cai et al. (2021), <https://arxiv.org/abs/2110.03937> — lists Shih et al. 2020.",
        "- Doevenspeck et al., “SOT-MRAM based Analog in-Memory Computing for DNN",
        "  inference”, IEEE Symposium on VLSI Technology (2020),",
        "  <https://ieeexplore.ieee.org/document/9265099> — three-terminal SOT junctions",
        "  on 300 mm wafers at RA 5–50 kΩ·µm²; σ/μ of R_P against electrical CD, set by",
        "  area and not by RA (Fig. 8); R-H loops at 80 nm, TMR 68–85% (Fig. 6); R_on =",
        "  6 MΩ and an assumed TMR of 150% (Table I); zero stored as two AP devices.",
        "- Doevenspeck et al., “Multi-pillar SOT-MRAM for Accurate Analog in-Memory DNN",
        "  Inference”, IEEE Symposium on VLSI Technology (2021),",
        "  <https://ieeexplore.ieee.org/document/9508714> — four pillars on one SOT track;",
        "  five levels per device and nine per pair (Fig. 7); where a missed write lands",
        "  (Fig. 9); per-level switching probabilities (Fig. 11) and the 0.74 mean behind",
        "  the five-attempt headline (Fig. 14); conductance distributions over 80 devices,",
        "  a ratio of 2.03, the five medians and σ/μ of 3.3–4.1% per level (Fig. 16);",
        "  the weight-noise normalisation (Fig. 17).",
        "- Grollier et al., “Neuromorphic spintronics”, *Nature Electronics* 3, 360–370",
        "  (2020), <https://doi.org/10.1038/s41928-019-0360-9> — a conductance ratio",
        "  “typically around three”.",
        "- Harris, “Interconnect RC”, lecture notes (1997),",
        "  <https://pages.hmc.edu/harris/class/hal/lect4.pdf> — about 0.2 fF/µm of wire",
        "  capacitance.",
        "- Hayakawa, Ikeda, Matsukura, Takahashi & Ohno, *Jpn. J. Appl. Phys.* 44, L587",
        "  (2005), <https://arxiv.org/abs/cond-mat/0504051> — RA 3.4 kΩ·µm² and TMR",
        "  200–260% at 2.0 nm MgO; RA rises exponentially with barrier thickness.",
        "- Ikeda et al., *Jpn. J. Appl. Phys.* 44, L1442 (2005),",
        "  <https://arxiv.org/abs/cond-mat/0510531> — TMR 27% at RA 0.8 Ω·µm² rising to",
        "  165% at 2.9; 355% at room temperature.",
        "- Jung et al., *Nature* 601, 211–216 (2022),",
        "  <https://doi.org/10.1038/s41586-021-04196-6> — 13 kΩ (σ 1.6 kΩ) and 26 kΩ",
        "  (σ 2.0 kΩ) over 8,192 cells, transistor included; resistance summation; 2.1 fF",
        "  of column per cell; 13–29 ns column readout; lists Wei et al. 2019.",
        "- Lequeux et al., *Sci. Rep.* 6, 31510 (2016),",
        "  <https://pmc.ncbi.nlm.nih.gov/articles/PMC4990964/> — domain walls displaced",
        "  at ~10⁶ A/cm²; 15–20 intermediate states; TMR about 95%.",
        "- Liu, Pai, Li, Tseng, Ralph & Buhrman, *Science* 336, 555–558 (2012),",
        "  <https://arxiv.org/abs/1203.2875> — the three-terminal cell: a low-impedance",
        "  write line with a higher-impedance MTJ for read-out.",
        "- Shih et al. (2020) — an 8 Mb STT-MRAM macro with 9 ns read access in 16 nm",
        "  FinFET; known from Cai et al.'s reference list, not read.",
        "- Victor, Kim, Wang, Roy & Gupta, “WAGONN” (2024),",
        "  <https://arxiv.org/abs/2406.14706> — 2–10 Ω per bit-cell at 45–65 nm, up to",
        "  20 Ω at 7 nm.",
        "- C. Wang, Victor & Gupta (2023), <https://arxiv.org/abs/2307.04261> — 182 Ω/µm",
        "  at 7 nm over a 108 nm SOT-MRAM cell; SOT junctions simulated at 8–100 kΩ.",
        "- M. Wang et al., *Nature Communications* 9 (2018),",
        "  <https://arxiv.org/abs/1708.04111> — TMR up to 249% in perpendicular junctions.",
        "- Wei et al., ISSCC (2019) — a 7 Mb STT-MRAM with 4 ns read sensing in 22FFL;",
        "  known from Jung et al.'s reference list, not read.",
    ]

    return "\n".join(lines) + "\n"


def main() -> None:
    text = render()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)

    print("\n".join(text.splitlines()[:22]))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
