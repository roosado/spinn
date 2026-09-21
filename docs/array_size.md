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

## The arrays

| grid | rows | devices | ideal | pass mark | array read power |
|---|---|---|---|---|---|
| 6×6 | 36 | 720 | 0.7345 | 0.6978 | 1.58 µW |
| 8×8 | 64 | 1,280 | 0.8440 | 0.8018 | 2.76 µW |
| 12×12 | 144 | 2,880 | 0.8975 | 0.8526 | 6.07 µW |
| 18×18 | 324 | 6,480 | 0.9040 | 0.8588 | 13.59 µW |
| 26×26 | 676 | 13,520 | 0.9070 | 0.8617 | 27.88 µW |

Differential pairs throughout, so devices are twice rows times ten. The pass
mark rises with the ideal because it is 95% of it. Read power is array only — no
sense amplifiers, no converters — and grows with the array, as it must.

## Sources 1 and 2

| rows | 1. conductance variation holds → fails | in bits | 2. states per device holds → fails | in bits | binds, of the two |
|---|---|---|---|---|---|
| 36 | σ = 0.035 → 0.05 | 4.84 → 4.32 | 7 → 5 | 3.70 → 3.17 | conductance variation |
| 64 | σ = 0.035 → 0.05 | 4.84 → 4.32 | 7 → 5 | 3.70 → 3.17 | conductance variation |
| 144 | σ = 0.05 → 0.075 | 4.32 → 3.74 | 5 → 4 | 3.17 → 2.81 | conductance variation |
| 324 | σ = 0.075 → 0.1 | 3.74 → 3.32 | 4 → 3 | 2.81 → 2.32 | conductance variation |
| 676 | σ = 0.1 → 0.15 | 3.32 → 2.74 | 4 → 3 | 2.81 → 2.32 | conductance variation |

Across sizes the σ that holds loosens from 0.035 of the window at 36 rows to 0.1 at 676, while the wire edge below tightens. They run in opposite
directions, and neither is explained here.

Read against each size's own ideal, as bracket ends on the row's ladders — not
interpolated. The states ladder wobbles by a sample or two at fine quantisation, as
the row records. These are what the device must deliver at that size; the delivered
spread is `UNSOURCED`, so **no verdict is drawn between them and the wire**.

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
| 36 | 200 → 431 | **431 → 928** | 0.7345 / 0.7345 | 0.7345 / 0.7345 |
| 64 | 92.8 → 200 | **200 → 431** | 0.8440 / 0.8440 | 0.8400 / 0.8400 |
| 144 | 20 → 43.1 | **92.8 → 200** | 0.8975 / 0.8975 | 0.8860 / 0.8960 |
| 324 | 4.31 → 9.28 | **20 → 43.1** | 0.9000 / 0.9025 | 0.0005 / 0.8655 |
| 676 | 0.928 → 2 | **4.31 → 9.28** | 0.6785 / 0.8990 | 0.0000 / 0.7190 |

Cells are accuracy against that size's pass mark. The bracket is the ladder point
either side of where the mean crosses the mark.

At every size the solved edge sits above first order's: the last magnitude that holds is 2.2× to 4.6× higher.

**The row's own array is the first line.** At 36×10 first order puts the edge between 200 and 431 Ω on this ladder — the row, on its coarser one, records holding at 100 Ω and failing at 300 Ω. The solved network holds at 431 Ω and fails at 928 Ω. **The row's “fails at 300 Ω” is a property of the first-order model and not of the array**; its “holds at 100 Ω” is unaffected. Nothing in the row has been changed.

## The size limit

Judged on **cited wiring only**: 2 Ω per cell at 65 nm (Agrawal et al. 2019) and
20 Ω at 7 nm (Victor et al. 2024). Both are ladder points, so each is read off directly.

| cited wiring | solved network | first order |
|---|---|---|
| 2 Ω per segment | holds at every size swept, up to 676 rows: no edge in this range | holds at 324 rows, fails at 676 |
| 20 Ω per segment | holds at 324 rows, fails at 676 | holds at 144 rows, fails at 324 |

**What that says about the question the page asks.** The device spread has no
delivered value, so nothing here is a margin against it. Wire resistance does, so
wiring can be judged: at the sizes where both cited values hold, the wire is inside
its edge and, of the sources judged, conductance variation is the one that binds, as
in the row; where cited wiring fails, the wire is a delivered failure that no
amount of device precision removes.

On the solved network, 7 nm wiring (20 Ω) holds at 324 rows, fails at 676; 65 nm wiring (2 Ω) holds at every size swept, up to 676 rows: no edge in this range.

So for 7 nm wiring the binding source changes from conductance variation to the wire somewhere between 324 and 676 rows. That is a bracket in size, five sizes wide, and is not interpolated.

## The first-order model, checked

The row and the recorded budget are first order, and the source's own header calls it
the safe direction. Here it is measured.

**The two disagree on holds/fails at ladder points at 36, 64, 144, 324 and 676 rows.** Where they do, first order says the array fails and the network says it holds.

First order also reaches accuracies below the 0.1 of chance at 64, 144, 324 and 676 rows. That is not a harder failure but an impossible one: past its
range it lets a column node rise above the driver that feeds it and reverses the sign
of a cell's current. The network cannot, and the solved model's lowest accuracy at any size on this ladder is 0.3215.

| rows | worst cell keeps, at 2 Ω | at 20 Ω | at the last magnitude that holds |
|---|---|---|---|
| 36 | 99.7% | 97.1% | 58.4% at 431 Ω |
| 64 | 99.1% | 91.9% | 50.1% at 200 Ω |
| 144 | 95.9% | 68.6% | 26.9% at 92.8 Ω |
| 324 | 81.9% | 24.9% | 24.9% at 20 Ω |
| 676 | 48.0% | 2.7% | 26.6% at 4.31 Ω |

*Worst cell keeps* is the smallest ratio of effective to programmed conductance over
every cell of both rails, from the solved network: the cell furthest from both edges.
At the last magnitude that holds it is between 25% and 58% at every size. That is a property of these trained, differential, sparse-input arrays, and
says the accuracy tolerates a large loss at the corner; it is not a rule about crossbars.

## The expectation on record

Declared before the run, and not a thesis: for a uniform array the first-order far
corner loses `R·G·(N(N+1) + M(M+1))/2` of the drive, so a fixed fraction gives an edge
that falls as `1/N²`. From the row's 100 Ω at 36 rows that put 20 Ω failing between 64
and 144 rows and 2 Ω between 144 and 324. The trained arrays are sparse and
differential, and the declaration said the exponent might differ.

| cited wiring | declared | first order | solved |
|---|---|---|---|
| 2 Ω | fails between 144 and 324 rows | holds at 324 rows, fails at 676 | holds at every size swept, up to 676 rows: no edge in this range |
| 20 Ω | fails between 64 and 144 rows | holds at 144 rows, fails at 324 | holds at 324 rows, fails at 676 |

`edge × rows²`, at both ends of each bracket, so the scaling can be read without a fit:

| rows | first order (holds, fails) | solved (holds, fails) |
|---|---|---|
| 36 | 259,200, 558,429 | 558,429, 1,203,100 |
| 64 | 380,239, 819,200 | 819,200, 1,764,913 |
| 144 | 414,720, 893,487 | 1,924,960, 4,147,200 |
| 324 | 452,328, 974,511 | 2,099,520, 4,523,279 |
| 676 | 424,219, 913,952 | 1,969,050, 4,242,189 |

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
| 36 | 1.29e-03, 2.78e-03 |
| 64 | 6.00e-04, 1.29e-03 |
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
- **The device spread is still `UNSOURCED`.** Sources 1 and 2 are reported at every
  size and compared to nothing.
- **The other sizes are not the shared task.** Ideal accuracy rises with the grid
  because the task gets easier, and each size's pass mark rises with it.
- **The row itself is unchanged.** Its 6×6 IR-drop bracket is first order, and its
  failing side is first order's; the solved network at the same size is in the table
  above. Whether to move the row onto the solved model is a separate decision.

## Sources

Only the two wire resistances are cited here; everything else is this project's own
model or measurement.

- Agrawal, Lee & Roy, “X-CHANGR” (2019), <https://arxiv.org/abs/1907.00285> —
  2 Ω per crossbar node at 65 nm.
- Victor, Kim, Wang, Roy & Gupta, “WAGONN” (2024),
  <https://arxiv.org/abs/2406.14706> — 2–10 Ω per bit-cell at 45–65 nm, up to
  20 Ω at 7 nm.
