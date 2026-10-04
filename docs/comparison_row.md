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
| Delivered precision | **σ/μ = 0.031–0.063**, measured on this device class (Doevenspeck et al. 2020) — a bracket, see below |
| Margin | **undetermined** at the design ratio of 3; undetermined at the measured 2.03; fails at the measured 1.85 — see below |
| Energy per inference | `UNSOURCED`; array read power **0.988 µW** |
| Latency per inference | `UNSOURCED` |

Array **36×10**, 720 devices, differential pairs.
Pass mark **0.6978** = 95% of ideal, declared before the sweeps were run.
Operating point **1–3 µS at 0.1 V**, a design checked against device physics — see below.

## The edges, as brackets

Read off the magnitude ladder. Nothing is interpolated: `mc.pack` stores mean
and standard deviation and no fitted crossing point, deliberately.

| source | holds at | fails at | in effective bits |
|---|---|---|---|
| 1. conductance variation | σ = 0.035 of the window (0.7087) | σ = 0.05 (0.6799) | **holds at 4.84, fails at 4.32** |
| 1, measured: area variation | σ/μ = 0.05 (0.7046) | σ/μ = 0.063 (0.6929) | *judged against the delivered spread — see below* |
| 2. resolvable states | 7 states/device | 5 states/device | holds at 3.70, fails at 3.17 |
| 3. IR drop | 300 Ω per segment | 1000 Ω per segment | *not a bit depth — see below* |

**Conductance variation binds.** It demands 4.84 bits where the states knob demands 3.70, and both are
expressed against the same conductance window, so the comparison is like for
like. That was the prediction on record before any of this ran.

**Source 1 is measured twice, and the two are never combined.** As a uniform σ
against the window it is the required precision, in the hub's unit. As area
variation — each device's whole conductance times `a ~ N(1, σ)`, the form imec
measured — it is what the delivered spread is judged with. They are two models
of one spread, so the joint run below uses the first and not both.

**IR drop is deliberately not converted to bits.** It is a position-dependent
systematic, not a spread on a stored value, so `log2(range/σ)` has no σ to take.
Forcing it into the unit would be a category error. The statement that means
something is the one in the table: at this array size the design tolerates
300 Ω per wire segment and fails by 1000 Ω.
**That number is meaningless without the array size beside it**, which is why
the size is fixed and reported. How it moves with the size — and how far the
first-order model behind its failing side is from the network it approximates —
is measured in `docs/array_size.md`. The failing side above is first order's.

**It is equally conditional on the conductance window.** A wire drop is `R·I`,
and `I` is set by the absolute conductance of the devices — so unlike sources 1
and 2, this bracket does not cancel the window. Accuracy under IR drop depends
on `R·G` alone, so holding the ratio at 3 and moving the window by a decade
moves the edge by a decade: at a tenth of this window 3 kΩ holds, and at ten times it
100 Ω has already failed.

**At this size and in this window, IR drop does not bind.** Published crossbar
wiring runs from 2 Ω per cell at 65 nm (Agrawal et al. 2019),
through 2–10 Ω across 45–65 nm, to about 20 Ω at 7 nm (Victor
et al. 2024; Wang et al. 2023). The design holds to 300 Ω, so the wiring
would have to be 15 times worse than the most scaled of those before this
source bound. A segment is resistance per length times the cell pitch — on
7 nm minimum-pitch wiring, 182 Ω/µm, 300 Ω is a 1.65 µm pitch — so
a cell that large is wired wider than minimum.

What keeps the wires out of this budget is the window. A thin-barrier memory
cell is 26–38 times more conductive than this design (Jung et al.
2022 measured 13 and 26 kΩ, access transistor included), past the tenfold at
which 100 Ω already fails.

## The joint run

All three sources at the last magnitude each individually held: mean **0.6709** ± 0.0120, which is **below** the pass mark.

The joint drop is 0.0636 against 0.0838
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

**The integrated devices come in lower.** The three-terminal junctions with a thick
read barrier that imec integrated and measured run at TMR 85% at RA 5 kΩ·µm²,
falling to 68% at 50 (Doevenspeck et al. 2020, Fig. 6, at 80 nm), and 103% in a
perpendicular four-pillar stack (Doevenspeck et al. 2021, Fig. 16) — against 200%
here, and against the 150% imec's own analysis assumed. The design keeps 200%,
because film-level junctions reach it and a window is a design value. But a
delivered spread arrives as σ/μ and reaches the window through the ratio, so the
margin below is judged at the measured ratios as well as at this one.

**Other work chose other windows, for other machines.** Jung et al. (2022) built
a 64×64 MRAM crossbar at 13 and 26 kΩ and summed *resistances* rather than
currents, because a current-summing array of cells that conductive would draw
too much power. imec's current-summing SOT-MRAM arrays went the other way, to
R_on = 6 MΩ (Doevenspeck et al. 2020, Table I). A 7 nm
simulation study used SOT junctions of 8–20 kΩ against 28–100 kΩ (Wang et al.
2023), and domain-wall junctions have been made at 95% (Lequeux et al. 2016)
and 164% TMR (Alamdar et al. 2021). This design sits between the two built
extremes: 26–38 times less conductive than the commodity cell, 18 times more than imec's.

## Delivered precision

**Measured, for this device class, and a bracket.** imec has measured the
device-to-device spread of this kind of junction — three-terminal, written along a
spin-orbit-torque track and read through the barrier — on 300 mm wafers (Doevenspeck
et al. 2020). Two of their findings make it usable for a junction they did not
build: the spread “does not increase for increasing RA products”, and it is “mostly
determined by process-induced area variations”. It follows the pillar's size rather
than its barrier, and this design's pillar size is known.

That pillar is 114 nm across, electrically. imec measured either side of it, across
three barriers (their Fig. 8b, read by pixel):

| electrical CD | σ/μ of R_P at RA 5, 20 and 50 kΩ·µm² |
|---|---|
| ≈ 90 nm | 0.049, 0.056, 0.063 |
| ≈ 127 nm | 0.033, 0.040, 0.031 |

So the delivered spread is **σ/μ between 0.031 and 0.063**, the envelope of both
sizes, with nothing interpolated between them. It is adopted as the delivered spread
*of the class* and not presented as more: by its authors' account it comes from a
test vehicle and does “not represent the fundamental lower limit”, its barriers
start at 5 kΩ·µm² against 3.4 here, and its values are read off a figure. imec's
multi-pillar devices a year later agree with it: four pillars in parallel spread by
σ/μ = 3.3–4.1% over 80 devices (Doevenspeck et al. 2021, Fig. 16), a single pillar's
spread averaged over four.

**Judged with the source built for it.** A spread set by area is proportional to
conductance — a pillar that came out small is small in both states — so it is not
source 1's uniform σ, and it is not converted into source 1's bits. Against this
window it is 0.015–0.032 on a device that is off and 0.046–0.095 on one that is on:
not one number. It is put against area variation instead, swept in σ/μ with both
ends of the bracket on the ladder, so the verdict is read off ladder points rather
than interpolated:

| window ratio | area variation holds at → fails at | at σ/μ = 0.031 | at 0.063 | verdict |
|---|---|---|---|---|
| 3, the design | 0.05 → 0.063 | 0.7211 | 0.6929 | **undetermined** |
| 2.03, imec 2021, four pillars, medians over 80 devices (Fig. 16) | 0.035 → 0.05 | 0.7045 | 0.6348 | **undetermined** |
| 1.85, imec 2020, RA 5 kΩ·µm² (Fig. 6) | 0.02 → 0.031 | 0.6952 | 0.6048 | **fails**, short by up to 0.63 bits |

The rule was declared before the run: it holds if the worse end of the bracket
holds, fails if the better end fails, and is otherwise undetermined at this
resolution.

**At the design ratio the margin is undetermined, which is not the same as
missing.** This array's edge lies between σ/μ = 0.05 and 0.063, inside the delivered
bracket: it holds at the spread imec measured on pillars larger than this one and
fails at the spread they measured on smaller ones. Which side of 114 nm a fabricated
junction falls on decides it, and the test vehicle cannot.

**The ratio decides as much as the spread.** At 2.03 the margin is undetermined. At
1.85 the margin fails. A measured σ/μ reaches the window through the ratio, which is
why the integrated TMR in the operating-point section matters to the margin and not
only to the window. How the verdict moves with the array size is in
`docs/array_size.md`.

For scale, and nothing more: the commodity cell's measured spread is larger than
either end — σ/R of 7.7% and 12.3% over 8,192 cells, access transistor included
(Jung et al. 2022) — on a thin-barrier memory cell, a different device.

## Energy and latency

Both are `UNSOURCED`, and the arithmetic is given so a reader can substitute.

Array read power is **0.988 µW** at the design operating point,
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
- Cai et al. (2021), <https://arxiv.org/abs/2110.03937> — lists Shih et al. 2020.
- Doevenspeck et al., “SOT-MRAM based Analog in-Memory Computing for DNN
  inference”, IEEE Symposium on VLSI Technology (2020),
  <https://ieeexplore.ieee.org/document/9265099> — three-terminal SOT junctions
  on 300 mm wafers at RA 5–50 kΩ·µm²; σ/μ of R_P against electrical CD, set by
  area and not by RA (Fig. 8); R-H loops at 80 nm, TMR 68–85% (Fig. 6); R_on =
  6 MΩ and an assumed TMR of 150% (Table I); zero stored as two AP devices.
- Doevenspeck et al., “Multi-pillar SOT-MRAM for Accurate Analog in-Memory DNN
  Inference”, IEEE Symposium on VLSI Technology (2021),
  <https://ieeexplore.ieee.org/document/9508714> — four pillars on one SOT track;
  conductance distributions over 80 devices, a ratio of 2.03 and σ/μ of
  3.3–4.1% per level (Fig. 16).
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
