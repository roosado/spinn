# Array size

The row's IR-drop bracket is one point on a curve: the drop grows with array size,
and the row says so and stops. This is the same measurement at five sizes, so the
size is the axis instead of a footnote. Produced by `spinn-hw/run_size_sweep.m`
from `exports/size/`, seeds from `baseSeed = 20260908` at every size, and assembled
by `apps/report_size.py`.

The site shows the same sweep with the size as a control, and draws both wire
models together: **[Go larger](https://roosado.github.io/spinn/larger.html)**.
Every number there is one of these; nothing on it is computed from anything this
document does not record.

**What varies.** The image grid `g`: rows are `g×g` and the ten columns are the ten
classes, so **only the column wire lengthens** — the row wire stays ten cells. It is
one axis. Each size is trained fresh on the same 2,000 test digits at that
resolution, with the learning rate scaled as `0.5 · 36 / rows` so that no size is an
optimiser artefact. **Only 6×6 is the shared task**; the others are the same digits at
another resolution, spinn-internal, and nothing here is compared to a photonn row.
Everything was declared in `docs/history.md` (2026-09-19) before any size was run:
the sizes, the ladder, the seeds, and that each size's pass mark is 95% of *its own*
ideal.

Held fixed: the window (1–3 µS), the read voltage, the cell pitch — so a wire segment
is the same resistance at every size — and the differential pair.

**Rerun on 2026-10-04**, when the pair began storing a zero weight as two devices off
rather than two half-switched, and area variation was added. Every number below is
from that run; `docs/history.md` has what moved and by how much.

## The arrays

| grid | rows | devices | ideal | pass mark | array read power |
|---|---|---|---|---|---|
| 6×6 | 36 | 720 | 0.7345 | 0.6978 | 0.99 µW |
| 8×8 | 64 | 1,280 | 0.8440 | 0.8018 | 1.68 µW |
| 12×12 | 144 | 2,880 | 0.8975 | 0.8526 | 3.67 µW |
| 18×18 | 324 | 6,480 | 0.9040 | 0.8588 | 8.03 µW |
| 26×26 | 676 | 13,520 | 0.9070 | 0.8617 | 16.56 µW |

Differential pairs throughout, so devices are twice rows times ten. The pass
mark rises with the ideal because it is 95% of it. Read power is array only — no
sense amplifiers, no converters — and grows with the array, as it must.

## Sources 1 and 2

| rows | 1. conductance variation holds → fails | in bits | 2. states per device holds → fails | in bits | binds, of the two |
|---|---|---|---|---|---|
| 36 | σ = 0.035 → 0.05 | 4.84 → 4.32 | 7 → 5 | 3.70 → 3.17 | conductance variation |
| 64 | σ = 0.05 → 0.075 | 4.32 → 3.74 | 7 → 5 | 3.70 → 3.17 | conductance variation |
| 144 | σ = 0.075 → 0.1 | 3.74 → 3.32 | 5 → 4 | 3.17 → 2.81 | conductance variation |
| 324 | σ = 0.075 → 0.1 | 3.74 → 3.32 | 4 → 3 | 2.81 → 2.32 | conductance variation |
| 676 | σ = 0.1 → 0.15 | 3.32 → 2.74 | 4 → 3 | 2.81 → 2.32 | conductance variation |

Across sizes the σ that holds loosens from 0.035 of the window at 36 rows to 0.1 at 676, while the wire edge below tightens. They run in opposite
directions, and neither is explained here.

Read against each size's own ideal, as bracket ends on the row's ladders — not
interpolated. The states ladder wobbles by a sample or two at fine quantisation, as
the row records. These are what the device must deliver at that size, in the hub's
unit, and in bits they are compared to nothing: the delivered spread is judged with its
own source, next, and the delivered levels against the states ladder after that.

## The delivered spread

imec measured σ/μ between **0.031 and 0.063** on the two pillar sizes either side of
this design's (Doevenspeck et al. 2020; the row has the readings). The pillar is the
same at every size, so the delivered bracket is too. It is judged with area variation —
each device's whole conductance times `a ~ N(1, σ)` — by the row's rule: it holds if
the worse end holds, fails if the better end fails, and is otherwise undetermined.

| rows | area variation holds → fails (σ/μ) | at 0.031 | at 0.063 | verdict |
|---|---|---|---|---|
| 36 | 0.05 → 0.063 | 0.7211 | 0.6929 | **undetermined** |
| 64 | 0.063 → 0.075 | 0.8327 | 0.8138 | **holds**, by 0.00–0.25 bits |
| 144 | 0.075 → 0.1 | 0.8959 | 0.8835 | **holds**, by 0.25–0.67 bits |
| 324 | 0.1 → 0.15 | 0.9046 | 0.8989 | **holds**, by 0.67–1.25 bits |
| 676 | holds at every rung to 0.15 | 0.9069 | 0.9056 | **holds**, by at least 1.25 bits |

At the design window's ratio of 3. The row adds the two ratios imec measured on
integrated junctions, at 36 rows only; the larger arrays here are not rerun at them.

**The delivered spread holds at 64, 144, 324 and 676 rows**, and the margin widens with the array, as the required σ above loosens. It is undetermined at 36 rows.

## Delivered levels and write errors

imec's four-pillar track delivers five conductance levels per device and its
two-pillar track three (Doevenspeck et al. 2021; the row has the readings). A count
is one rung of the states ladder, so each is read off directly, as holds or fails
and never undetermined. It is set by the pillars on the track and not by their size,
so it is the same at every size here. It is judged at the max|w| scale the row uses:
the row's calibrated scale is a sensitivity of its own 36×10 array and is not rerun
here.

Write errors run at 5 states at every size, and are judged by the row's rule against
[0.389^m, 0.495^m] after m verified attempts. Where five levels fail, the array
fails before a write can matter, so the table says so and judges no attempts there.

| rows | five levels | three levels | write errors at 5 states, holds → fails | fewest verified attempts that hold |
|---|---|---|---|---|
| 36 | **fails** (0.6615) | **fails** (0.5020) | levels fail first | levels fail first |
| 64 | **fails** (0.7615) | **fails** (0.6880) | levels fail first | levels fail first |
| 144 | **holds** (0.8745) | **fails** (0.8380) | 0.121287 → 0.151321 | 3 |
| 324 | **holds** (0.8915) | **fails** (0.7450) | 0.245025 → 0.3 | 2 |
| 676 | **holds** (0.9045) | **fails** (0.8175) | holds at every rung to 0.495 | 1 |

The levels cells give the verdict and, in brackets, the accuracy against that size's
pass mark. The write ladder is read at the ladder points either side of where the
mean crosses it, and a verdict within a sample or two of its mark can move between
runs.

**Five levels per device hold at 144, 324 and 676 rows and fail at 36 and 64 rows.**
Three levels hold at no size swept. Where five levels hold, the fewest verified
attempts that hold are 3 at 144 rows, 2 at 324 rows and 1 at 676 rows.

## IR drop, first order and solved

`err.ir_drop` is first order: the drops come from the currents the *ideal* voltages
would draw, so one pass overstates them. `err.ir_drop_exact` solves the same resistive
network exactly. Both are measured at every ladder point, at every size.

The declaration asked for the solved check at each size's bracket. It is done at every
ladder point because a bracket cannot be carried without the points either side of it,
and a first version that iterated the first-order model to a fixed point was replaced
by a direct solve: it agreed with it wherever it converged and stopped converging at
the resistances the edge sits between.

| rows | first order: holds → fails (Ω) | **solved: holds → fails (Ω)** | 2 Ω first / solved | 20 Ω first / solved |
|---|---|---|---|---|
| 36 | 200 → 431 | **928 → —** | 0.7350 / 0.7350 | 0.7350 / 0.7350 |
| 64 | 200 → 431 | **431 → 928** | 0.8440 / 0.8440 | 0.8425 / 0.8425 |
| 144 | 43.1 → 92.8 | **92.8 → 200** | 0.8975 / 0.8975 | 0.8950 / 0.8960 |
| 324 | 9.28 → 20 | **20 → 43.1** | 0.9025 / 0.9025 | 0.3160 / 0.8895 |
| 676 | 2 → 4.31 | **4.31 → 9.28** | 0.8905 / 0.9020 | 0.0000 / 0.7925 |

Cells are accuracy against that size's pass mark. The bracket is the ladder point
either side of where the mean crosses the mark.

At every size the solved edge sits above first order's: the last magnitude that holds is 2.2× to 4.6× higher.

**The row's own array is the first line.** At 36×10 first order puts the edge between 200 and 431 Ω on this ladder — the row, on its coarser one, records holding at 300 Ω and failing at 1000 Ω. The solved network holds at 928 Ω, the top of this ladder, and fails nowhere on it.
Whether the network fails at the row's 1000 Ω is beyond this ladder, so the row's failing side is neither confirmed nor contradicted here; its holding side is.
Nothing in the row rests on the solved model; moving it there is an open decision.

## The size limit

Judged on **cited wiring and the measured spread**: 2 Ω per cell at 65 nm (Agrawal
et al. 2019) and 20 Ω at 7 nm (Victor et al. 2024), and the delivered bracket above.
Every one of them is a ladder point, so each is read off directly.

| cited wiring | solved network | first order |
|---|---|---|
| 2 Ω per segment | holds at every size swept, up to 676 rows: no edge in this range | holds at every size swept, up to 676 rows: no edge in this range |
| 20 Ω per segment | holds at 324 rows, fails at 676 | holds at 144 rows, fails at 324 |

| rows | delivered spread | 2 Ω, solved | 20 Ω, solved | what fails |
|---|---|---|---|---|
| 36 | undetermined | holds | holds | nothing judged fails; the spread is undetermined |
| 64 | holds | holds | holds | nothing judged |
| 144 | holds | holds | holds | nothing judged |
| 324 | holds | holds | holds | nothing judged |
| 676 | holds | holds | fails | 20 Ω wiring |

On the solved network, 7 nm wiring (20 Ω) holds at 324 rows, fails at 676; 65 nm wiring (2 Ω) holds at every size swept, up to 676 rows: no edge in this range.

**So with 7 nm wiring the wire is what fails, between 324 and 676 rows**, at a size where the measured spread still holds. That is a bracket in size, five sizes wide, and is not interpolated. Where a cited wire
fails, no amount of device precision removes it.

## The first-order model, checked

The row and the recorded budget are first order, and the source's own header calls it
the safe direction. Here it is measured.

**The two disagree on holds/fails at ladder points at 36, 64, 144, 324 and 676 rows.** Where they do, first order says the array fails and the network says it holds.

First order also reaches accuracies below the 0.1 of chance at 64, 144, 324 and 676 rows. That is not a harder failure but an impossible one: past its
range it lets a column node rise above the driver that feeds it and reverses the sign
of a cell's current. The network cannot, and the solved model's lowest accuracy at any size on this ladder is 0.3355.

| rows | worst cell keeps, at 2 Ω | at 20 Ω | at the last magnitude that holds |
|---|---|---|---|
| 36 | 99.8% | 98.0% | 48.2% at 928 Ω |
| 64 | 99.5% | 95.1% | 43.3% at 431 Ω |
| 144 | 97.6% | 80.0% | 42.8% at 92.8 Ω |
| 324 | 89.2% | 41.0% | 41.0% at 20 Ω |
| 676 | 63.8% | 8.0% | 42.6% at 4.31 Ω |

*Worst cell keeps* is the smallest ratio of effective to programmed conductance over
every cell of both rails, from the solved network: the cell furthest from both edges.
At the last magnitude that holds it is between 41% and 48% at every size. That is a property of these trained, differential, sparse-input arrays, and
says the accuracy tolerates a large loss at the corner; it is not a rule about crossbars.

## The expectation on record

Declared before the run, and not a thesis: for a uniform array the first-order far
corner loses `R·G·(N(N+1) + M(M+1))/2` of the drive, so a fixed fraction gives an edge
that falls as `1/N²`. From the row's 100 Ω at 36 rows that put 20 Ω failing between 64
and 144 rows and 2 Ω between 144 and 324. The trained arrays are sparse and
differential, and the declaration said the exponent might differ.

It was declared for the centred pair. The arrays below store zero as two devices
off, which draws less current, so every measured edge sits higher than the one the
expectation was made against; the comparison is kept as it was declared.

| cited wiring | declared | first order | solved |
|---|---|---|---|
| 2 Ω | fails between 144 and 324 rows | holds at every size swept, up to 676 rows: no edge in this range | holds at every size swept, up to 676 rows: no edge in this range |
| 20 Ω | fails between 64 and 144 rows | holds at 144 rows, fails at 324 | holds at 324 rows, fails at 676 |

`edge × rows²`, at both ends of each bracket, so the scaling can be read without a fit:

| rows | first order (holds, fails) | solved (holds, fails) |
|---|---|---|
| 36 | 259,200, 558,429 | 1,203,100, — |
| 64 | 819,200, 1,764,913 | 1,764,913, 3,802,390 |
| 144 | 893,487, 1,924,960 | 1,924,960, 4,147,200 |
| 324 | 974,511, 2,099,520 | 2,099,520, 4,523,279 |
| 676 | 913,952, 1,969,050 | 1,969,050, 4,242,189 |

A constant column would be `1/N²`. From 144 rows up the solved products sit within 9% of each other at the holding end and 9% at the failing
end, so over that range the solved edge is consistent with `1/N²`; below it the
products are smaller and the edge falls less steeply. Both are properties of these
five brackets and neither is extrapolated past them.

## The window

The row says the IR-drop bracket is conditional on the conductance window. It is
conditional on exactly one number: accuracy under IR drop depends on `R·G` alone, and
a test holds that. Scale every conductance by α and every wire resistance by 1/α and
each drop, and so each argmax, is unchanged. So an edge in ohms is the same edge in
`R·g_max`, and a window `k` times more conductive at the same ratio of 3 divides every
edge in ohms in this document by `k`.

| rows | solved edge × g_max (holds, fails) |
|---|---|
| 36 | 2.78e-03, — |
| 64 | 1.29e-03, 2.78e-03 |
| 144 | 2.78e-04, 6.00e-04 |
| 324 | 6.00e-05, 1.29e-04 |
| 676 | 1.29e-05, 2.78e-05 |

Dimensionless. It holds at a fixed ratio of 3 only; a different ratio changes the
weights' mapping onto the window and is not covered.

## What this does not say

- **Five sizes, one axis.** Rows vary; columns are fixed at ten by the task, so the
  row wire never lengthens. Nothing here is a claim about a larger layer split across
  tiles, which is a different study.
- **One window, one pitch.** A segment is resistance per length times the cell pitch,
  and both are held, so a different cell would change the ohm axis.
- **The delivered spread is a bracket, for the device class.** imec's test vehicle,
  at pillar sizes either side of this design's, judged here at one window ratio; the
  row says what it is and is not. In bits, sources 1 and 2 are compared to nothing.
- **The delivered levels and writes are for the device class, at the row's scale.** Five
  levels are judged at the max|w| scale the row uses, and the row's calibrated scale is a
  36×10 sensitivity, not rerun here. Fig. 11 is each device's own best write current, and
  one current shared across an array would do worse: `UNSOURCED`.
- **The other sizes are not the shared task.** Ideal accuracy rises with the grid
  because the task gets easier, and each size's pass mark rises with it.
- **The row's IR-drop bracket is first order.** The solved network at the same size
  is in the table above. Whether to move the row onto it is a separate decision.

## Sources

The two wire resistances, the delivered spread, the delivered levels and the switching
probabilities are cited here; everything else is this project's own model or
measurement.

- Doevenspeck et al., “SOT-MRAM based Analog in-Memory Computing for DNN inference”,
  IEEE Symposium on VLSI Technology (2020),
  <https://ieeexplore.ieee.org/document/9265099> — σ/μ of R_P against electrical CD,
  set by area and not by RA (Fig. 8).
- Doevenspeck et al., “Multi-pillar SOT-MRAM for Accurate Analog in-Memory DNN
  Inference”, IEEE Symposium on VLSI Technology (2021),
  <https://ieeexplore.ieee.org/document/9508714> — five levels per device from four
  pillars, three from two (Fig. 7); per-level switching probabilities (Fig. 11).
- Agrawal, Lee & Roy, “X-CHANGR” (2019), <https://arxiv.org/abs/1907.00285> —
  2 Ω per crossbar node at 65 nm.
- Victor, Kim, Wang, Roy & Gupta, “WAGONN” (2024),
  <https://arxiv.org/abs/2406.14706> — 2–10 Ω per bit-cell at 45–65 nm, up to
  20 Ω at 7 nm.
