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

import numpy as np

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
#: VLSI 2020, as reported by Cai et al., arXiv:2110.03937 (2021).
IMEC_R_ON_OHM = 6e6

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

    ideal, thr = b["ideal"], b["threshold"]
    sig, sta, wir = b["sigma_g_rel"], b["states_per_device"], b["wire_resistance_ohm"]

    sig_hold, sig_fail = bits_from_sigma(sig["lastHolding"]), bits_from_sigma(sig["firstFailing"])
    sta_hold = bits_from_states(int(sta["lastHolding"]), h.scheme)
    sta_fail = bits_from_states(int(sta["firstFailing"]), h.scheme)

    power = array_read_power(h, weights, images)
    joint = b["joint"]

    # The operating point, as a device, and against the windows other work chose.
    cb = h.crossbar()
    d = design_check(cb.g_min, cb.g_max, cb.read_voltage)
    span = cb.g_max - cb.g_min
    thin = (1.0 / COMMODITY_CELL_OHM[0] / cb.g_max, 1.0 / COMMODITY_CELL_OHM[1] / cb.g_min)
    scale = (COMMODITY_SIGMA_REL[0] * cb.g_max / span, COMMODITY_SIGMA_REL[1] * cb.g_min / span)
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
        "| Delivered precision | `UNSOURCED` |",
        "| Margin | *omitted — delivered precision is not sourced* |",
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
        "**It is equally conditional on the conductance window.** A wire drop is `R·I`,",
        "and `I` is set by the absolute conductance of the devices — so unlike sources 1",
        "and 2, this bracket does not cancel the window. Holding the ratio at 3 and",
        "moving the window by a decade either way moves the edge past both ends of the",
        "swept ladder: at a tenth of this window even 1 kΩ holds, and at ten times it",
        "100 Ω has already failed.",
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
        "which 100 Ω already fails.",
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
        "**Other work chose other windows, for other machines.** Jung et al. (2022) built",
        "a 64×64 MRAM crossbar at 13 and 26 kΩ and summed *resistances* rather than",
        "currents, because a current-summing array of cells that conductive would draw",
        "too much power. imec's current-summing SOT-MRAM arrays went the other way, to",
        "R_on = 6 MΩ (Doevenspeck et al. 2020, as reported by Cai et al. 2021). A 7 nm",
        "simulation study used SOT junctions of 8–20 kΩ against 28–100 kΩ (Wang et al.",
        "2023), and domain-wall junctions have been made at 95% (Lequeux et al. 2016)",
        "and 164% TMR (Alamdar et al. 2021). This design sits between the two built",
        f"extremes: {thin[0]:.0f}–{thin[1]:.0f} times less conductive than the commodity "
        f"cell, {imec:.0f} times more than imec's.",
        "",
        "## Delivered precision",
        "",
        "Still `UNSOURCED`: nobody has measured the device-to-device spread of this",
        "design. The one MTJ crossbar with a published spread is the commodity cell",
        f"above — σ/R of {COMMODITY_SIGMA_REL[1]:.1%} on its high-resistance state and "
        f"{COMMODITY_SIGMA_REL[0]:.1%} on its low,",
        "over 8,192 cells with the access transistor included (Jung et al. 2022). It is",
        "a different device, so it is not this design's delivered precision and **no",
        "margin is computed from it**. For scale only: the same relative spreads against",
        f"this window's span are {scale[1]:.3f} and {scale[0]:.2f} — past the "
        f"{sig['lastHolding']:g} that holds on both",
        f"states, and past the {sig['firstFailing']:g} that fails on the low-resistance one. "
        "The binding source",
        "is the one to measure first.",
        "",
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
        "- Cai et al. (2021), <https://arxiv.org/abs/2110.03937> — reports Doevenspeck",
        "  et al. (imec, IEEE Symposium on VLSI Technology 2020) at R_on = 6 MΩ, and",
        "  lists Shih et al. 2020.",
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
