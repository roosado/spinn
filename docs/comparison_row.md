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

**It is equally conditional on the conductance window**, which is `UNSOURCED`.
A wire drop is `R·I`, and `I` is set by the absolute conductance of the
devices — so unlike sources 1 and 2, this bracket does not cancel the window.
Holding the ratio at 3 and moving the window by a decade either way moves the
edge past both ends of the swept ladder: at a tenth of the placeholder even
1 kΩ holds, and at ten times it 100 Ω has already failed. The bracket above is
therefore a statement about this array at this operating point, and sourcing
the window is what would turn it into a statement about the platform.

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

## Energy and latency

Both are `UNSOURCED`, and the arithmetic is given so a reader can substitute.

Array read power is **1.577 µW**, computed exactly as
`mean_over_samples( sum_ij V_i² · G_ij )` over all 720 devices at the operating point in the handoff.

That is **array only**: it excludes the sense amplifiers, the ADC and every
digital stage after them. The periphery frequently dominates an analog
accelerator's energy, and a figure that quietly omits it is not comparable to
one that does not — so the boundary is stated rather than implied.

**Energy per inference needs a read time, and no read time has been sourced.**
Energy = power × t_read; multiply the figure above by whatever t_read a source
supports. Latency is the RC settling of the lines, which needs a line
capacitance and resistance, neither of which is sourced either.

The conductance window itself (`g_min_s`, `g_max_s`) and the read voltage are
also `UNSOURCED` placeholders — so the power figure scales with them and should
be read as an arithmetic worked example, not as a measurement.

**Sources 1 and 2 do not depend on them.** The window and the drive cancel in
the decode, exactly, and a test asserts the ideal accuracy is unchanged across
unrelated windows — so the ideal accuracy and both bit depths stand whatever the
window turns out to be. **Source 3 is the exception**, for the reason given
under its bracket above: a wire drop is `R·I`, and there is no `I` without an
absolute conductance.
