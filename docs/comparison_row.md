# The row

One row in the physical-AI comparison table, stated once here. The hub refers
to this rather than copying it.

Produced by `spinn-hw/run_error_budget.m` from `exports/crossbar_handoff.h5`,
seeds from `baseSeed = 20260908`, and assembled by `apps/report_row.py`.

| column | value |
|---|---|
| Platform | spintronic crossbar (MTJ / domain-wall) |
| What a weight physically is | a magnetic state, read as a conductance |
| What performs the sum | Kirchhoff current summing on a wire |
| Ideal accuracy | **0.7345** on the shared task (MNIST, 36 channels) |
| Which source binds | **conductance variation** (device-to-device sigma) |
| Required precision | **4.84 effective bits** on the binding source |
| Delivered precision | `UNSOURCED` |
| Margin | *omitted — delivered precision is not sourced* |
| Energy per inference | `UNSOURCED`; array read power **1.577 µW** |
| Latency per inference | `UNSOURCED` |

Array **36×10**, 720 devices, differential pairs.
Pass mark **0.6978** = 95% of ideal, declared before the sweeps were run.
Operating point **1–3 µS at 0.1 V**, a design checked against device physics — see below.

## The edges, as brackets

Read off the magnitude ladder. Nothing is interpolated: `mc.pack` stores mean
and standard deviation and no fitted crossing point, deliberately.

| source | holds at | fails at | in effective bits |
|---|---|---|---|
| 1. conductance variation | σ = 0.035 of the window (0.7003) | σ = 0.05 (0.6671) | **holds at 4.84, fails at 4.32** |
| 2. resolvable states | 7 states/device | 5 states/device | holds at 3.70, fails at 3.17 |
| 3. IR drop | 100 Ω per segment | 300 Ω per segment | *not a bit depth — see below* |

**Conductance variation binds.** It demands 4.84 bits where the states knob demands 3.70, and both are
expressed against the same conductance window, so the comparison is like for
like. That was the prediction on record before any of this ran.

**IR drop is deliberately not converted to bits.** It is a position-dependent
systematic, not a spread on a stored value, so `log2(range/σ)` has no σ to take.
Forcing it into the unit would be a category error. The statement that means
something is the one in the table: at this array size the design tolerates
100 Ω per wire segment and fails by 300 Ω.
**That number is meaningless without the array size beside it**, which is why
the size is fixed and reported.

**It is equally conditional on the conductance window.** A wire drop is `R·I`,
and `I` is set by the absolute conductance of the devices — so unlike sources 1
and 2, this bracket does not cancel the window. Holding the ratio at 3 and
moving the window by a decade either way moves the edge past both ends of the
swept ladder: at a tenth of this window even 1 kΩ holds, and at ten times it
100 Ω has already failed.

**At this size and in this window, IR drop does not bind.** Published crossbar
wiring runs from 2 Ω per cell at 65 nm (Agrawal et al. 2019),
through 2–10 Ω across 45–65 nm, to about 20 Ω at 7 nm (Victor
et al. 2024; Wang et al. 2023). The design holds to 100 Ω, so the wiring
would have to be 5 times worse than the most scaled of those before this
source bound. A segment is resistance per length times the cell pitch — on
7 nm minimum-pitch wiring, 182 Ω/µm, 100 Ω is a 0.55 µm pitch — so
a cell that large is wired wider than minimum.

What keeps the wires out of this budget is the window. A thin-barrier memory
cell is 26–38 times more conductive than this design (Jung et al.
2022 measured 13 and 26 kΩ, access transistor included), past the tenfold at
which 100 Ω already fails.

## The joint run

All three sources at the last magnitude each individually held: mean **0.6819** ± 0.0119, which is **below** the pass mark.

The joint drop is 0.0526 against 0.0772
for the sum of the independent drops — **sub-additive**, not additive. That is a
property of accuracy as a metric rather than a finding about the crossbar: a
sample already misclassified by one source cannot be misclassified again by the
next, so degradations saturate. No conclusion is drawn from it.

What it does say practically is that budgeting each source to its own edge
leaves nothing over. A design meeting all three at once needs each source
comfortably inside its individual bracket.

## The operating point

The window and the drive are a **design point, not a measurement** — this
project's own choice, held to one rule: a magnetic tunnel junction must be able
to physically be it, and every step of that check is cited. The sources back
the claim; none of their numbers is copied into the design.

| | design | what makes it buildable |
|---|---|---|
| `g_max_s`, `g_min_s` | 3 µS and 1 µS: 333 kΩ and 1 MΩ | a ratio of 3 is a TMR of 200%. A CoFeB/MgO junction with a 2.0 nm barrier measures 200–260% at RA = 3.4 kΩ·µm² (Hayakawa et al. 2005), which puts 333 kΩ at a pillar about 114 nm across |
| the write path | three-terminal | spin transfer moves a domain wall at ~10⁶ A/cm² (Lequeux et al. 2016); through that barrier the same density needs 34 V across 2 nm of oxide. So the cell is written along a low-impedance line — a spin-Hall strip (Liu et al. 2012) or the domain-wall track (Alamdar et al. 2021) — and read through the junction |
| `read_voltage_v` | 0.1 V | at most 0.3 µA per device, about 340 times below the density at which walls move: a read does not write |

A ratio of about three is what Grollier et al. (2020) call typical, and
perpendicular junctions reach 249% (Wang et al. 2018). Thin barriers give the
ratio up — TMR falls from 165% at RA = 2.9 Ω·µm² to 27% at 0.8 (Ikeda et al.
2005) — and memory cells accept that because their write current has to cross
the barrier: Jung et al. (2022) note that a thicker insulator “would demand a
higher write voltage or current”. A read-only junction carries no write
current, and at this resistance a series access transistor is a small fraction
of the cell.

**Other work chose other windows, for other machines.** Jung et al. (2022) built
a 64×64 MRAM crossbar at 13 and 26 kΩ and summed *resistances* rather than
currents, because a current-summing array of cells that conductive would draw
too much power. imec's current-summing SOT-MRAM arrays went the other way, to
R_on = 6 MΩ (Doevenspeck et al. 2020, as reported by Cai et al. 2021). A 7 nm
simulation study used SOT junctions of 8–20 kΩ against 28–100 kΩ (Wang et al.
2023), and domain-wall junctions have been made at 95% (Lequeux et al. 2016)
and 164% TMR (Alamdar et al. 2021). This design sits between the two built
extremes: 26–38 times less conductive than the commodity cell, 18 times more than imec's.

## Delivered precision

Still `UNSOURCED`: nobody has measured the device-to-device spread of this
design. The one MTJ crossbar with a published spread is the commodity cell
above — σ/R of 7.7% on its high-resistance state and 12.3% on its low,
over 8,192 cells with the access transistor included (Jung et al. 2022). It is
a different device, so it is not this design's delivered precision and **no
margin is computed from it**. For scale only: the same relative spreads against
this window's span are 0.038 and 0.18 — past the 0.035 that holds on both
states, and past the 0.05 that fails on the low-resistance one. The binding source
is the one to measure first.

## Energy and latency

Both are `UNSOURCED`, and the arithmetic is given so a reader can substitute.

Array read power is **1.577 µW** at the design operating point,
computed exactly as `mean_over_samples( sum_ij V_i² · G_ij )` over all 720
devices at the operating point in the handoff.

That is **array only**: it excludes the sense amplifiers, the ADC and every
digital stage after them. The periphery frequently dominates an analog
accelerator's energy, and a figure that quietly omits it is not comparable to
one that does not — so the boundary is stated rather than implied.

**Energy per inference needs a read time, and a read time belongs to the sense
amplifier**, which this model does not include. Energy = power × t_read. For
scale: MRAM macros read in 4 ns counting sensing alone (Wei et al. 2019) and
9 ns for a full access (Shih et al. 2020), and the commodity crossbar's columns
settle in 13–29 ns through a time-domain readout (Jung et al. 2022). Latency is
the settling of the lines into that amplifier: 2–20 Ω of wire per cell (above)
and, in the commodity crossbar, 2.1 fF of line per cell (Jung et al. 2022; the
textbook rule is about 0.2 fF/µm, Harris 1997).

The power figure scales with the window and the drive: a thin-barrier window
26–38 times more conductive would dissipate that much more for the same read voltage.

**Sources 1 and 2 do not depend on the operating point.** The window and the
drive cancel in the decode, exactly, and a test asserts the ideal accuracy is
unchanged across unrelated windows — so the ideal accuracy and both bit depths
stand whichever window a junction is built to. **Source 3 is the exception**,
for the reason given under its bracket above: a wire drop is `R·I`, and there
is no `I` without an absolute conductance.

## Sources

Every number quoted above from outside this project, and what it is cited for.
The design values are this project's own; these are what show they can be built.

- Agrawal, Lee & Roy, “X-CHANGR” (2019), <https://arxiv.org/abs/1907.00285> —
  2 Ω per crossbar node at 65 nm.
- Alamdar et al., *Appl. Phys. Lett.* 118, 112401 (2021),
  <https://arxiv.org/abs/2010.13879> — three-terminal domain-wall MTJs for
  in-memory computing; TMR 164%, RA 31 Ω·µm².
- Cai et al. (2021), <https://arxiv.org/abs/2110.03937> — reports Doevenspeck
  et al. (imec, IEEE Symposium on VLSI Technology 2020) at R_on = 6 MΩ, and
  lists Shih et al. 2020.
- Grollier et al., “Neuromorphic spintronics”, *Nature Electronics* 3, 360–370
  (2020), <https://doi.org/10.1038/s41928-019-0360-9> — a conductance ratio
  “typically around three”.
- Harris, “Interconnect RC”, lecture notes (1997),
  <https://pages.hmc.edu/harris/class/hal/lect4.pdf> — about 0.2 fF/µm of wire
  capacitance.
- Hayakawa, Ikeda, Matsukura, Takahashi & Ohno, *Jpn. J. Appl. Phys.* 44, L587
  (2005), <https://arxiv.org/abs/cond-mat/0504051> — RA 3.4 kΩ·µm² and TMR
  200–260% at 2.0 nm MgO; RA rises exponentially with barrier thickness.
- Ikeda et al., *Jpn. J. Appl. Phys.* 44, L1442 (2005),
  <https://arxiv.org/abs/cond-mat/0510531> — TMR 27% at RA 0.8 Ω·µm² rising to
  165% at 2.9; 355% at room temperature.
- Jung et al., *Nature* 601, 211–216 (2022),
  <https://doi.org/10.1038/s41586-021-04196-6> — 13 kΩ (σ 1.6 kΩ) and 26 kΩ
  (σ 2.0 kΩ) over 8,192 cells, transistor included; resistance summation; 2.1 fF
  of column per cell; 13–29 ns column readout; lists Wei et al. 2019.
- Lequeux et al., *Sci. Rep.* 6, 31510 (2016),
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC4990964/> — domain walls displaced
  at ~10⁶ A/cm²; 15–20 intermediate states; TMR about 95%.
- Liu, Pai, Li, Tseng, Ralph & Buhrman, *Science* 336, 555–558 (2012),
  <https://arxiv.org/abs/1203.2875> — the three-terminal cell: a low-impedance
  write line with a higher-impedance MTJ for read-out.
- Shih et al. (2020) — an 8 Mb STT-MRAM macro with 9 ns read access in 16 nm
  FinFET; known from Cai et al.'s reference list, not read.
- Victor, Kim, Wang, Roy & Gupta, “WAGONN” (2024),
  <https://arxiv.org/abs/2406.14706> — 2–10 Ω per bit-cell at 45–65 nm, up to
  20 Ω at 7 nm.
- C. Wang, Victor & Gupta (2023), <https://arxiv.org/abs/2307.04261> — 182 Ω/µm
  at 7 nm over a 108 nm SOT-MRAM cell; SOT junctions simulated at 8–100 kΩ.
- M. Wang et al., *Nature Communications* 9 (2018),
  <https://arxiv.org/abs/1708.04111> — TMR up to 249% in perpendicular junctions.
- Wei et al., ISSCC (2019) — a 7 Mb STT-MRAM with 4 ns read sensing in 22FFL;
  known from Jung et al.'s reference list, not read.
