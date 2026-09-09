# History

Chronological record of what was done and why. Newest entries at the bottom.

---

## Why this repo exists

**It is the second platform in the physical-AI series: a spintronic crossbar, where a
weight is a magnetic state and the sum is performed by Kirchhoff's law on a wire rather
than by interference.** It exists so the series' claim rests on more than one instance —
one example is an anecdote. Its output is one row in the hub's comparison table.

It is **not** a second `photonn`. photonn is about two months of work with a
browser-resident forward pass, a 3D stage and a five-page site; treating that as the entry
requirement for a platform is how a third platform never happens. A **comparable core** is
defined instead — the minimum that fills a row — with everything beyond it optional.

---

## 2026-09-07 — the repo was created and given photonn's harness

The series was redesigned in a long interview (see `physical-ai/docs/history.md` for the
shape and why). Spintronics was chosen as the second platform, and the scope of this repo
was settled in the same session.

### What this repo will build

- **An MTJ / domain-wall crossbar**, which are *one model with a knob*: they differ in how
  many stable states a weight holds, which is a quantisation parameter and maps directly
  onto photonn's error source #2.
- **A spin-torque oscillator model**, complementary. It **does not enter the comparison
  table** — "how precisely must this be built to classify MNIST" is not a question you ask
  of a reservoir. Keeping it out is a decision, not an oversight.
- **The shared task is photonn's MNIST protocol at 36 channels**, matching the MZI mesh.
  A crossbar is an N×N matrix engine, so the mesh is its like-for-like counterpart, not
  the D²NN.

### MATLAB was chosen on evidence, not habit

The initial recommendation was Python for both halves. Inspecting `photonn-hw` reversed
it. The Monte Carlo harness there is **already multi-model by design**: `mc.sweep` takes a
driver handle and requires only `(handoff, errorConfig, nRealizations, baseSeed) →
{.acc, .mean}`, and `mc.validate_config(cfg, "d2nn")` dispatches on a model *kind*, so a
third kind is an established extension point. `sweep` carries a comment saying it was
lifted out of the D²NN driver to stop two drivers drifting apart on seeding, *"which is
the thing that would quietly make their tolerance tables incomparable."*

That is exactly what cross-platform comparison needs, already solved one repo early.
Reimplementing it risks a difference that would not announce itself — it would just make
the comparison quietly wrong.

### What was committed

| | |
|---|---|
| `16cf2cf` | `.gitignore` and the commit template. Landed **before any content**, because `plans/` is never published and a planning note is easiest to leak before the rule exists. |
| `9dddf01` | `.gitattributes` from photonn, pinning line endings to LF |
| `2c81668` | **20 files inherited from photonn**, separated into three tiers of confidence |

### The inheritance, in three tiers

Copying was cheaper than re-deriving, and for the Monte Carlo harness also safer. The
tiers exist because "inherited" is not one thing:

- **Tier 1 — verbatim, byte-identical** (verified with `diff`): `dom_stub.js`,
  `built_site.py`, `plot_runner.js`, `+mc/sweep.m`, `+mc/pack.m`, `+mc/validate_config.m`,
  `+err/detector_noise.m`. No photonic coupling. `validate_config.m` was the good
  surprise — its typo-catching mechanism is entirely generic; only the registry it
  consults is platform-specific.
- **Tier 2 — copied, globals renamed, nothing else touched**: `mount_queue.js`,
  `plot.js`, `mount_queue_runner.js`, `preview.py`. A `diff` against photonn stays a
  handful of lines, so future drift remains auditable. Provenance comments were left in
  place deliberately.
- **Tier 3 — a base to edit, will not run as-is**: `build_site.py` (61 photonn-specific
  lines), `export.py` (63), `conftest.py` (23), `read_handoff.m` (21), `web_bundle.py`
  (16), `handoff.py` (9), `error_sources.m` (5).

**Two files were deliberately not copied**, and the reason matters more than the omission:
`err/quantize.m` wraps to `[0, 2π)` and iterates phase fields, and `err/thermal_crosstalk.m`
is a `conv2` blur over phase masks. Both are phase-specific in implementation even though
the idea transfers — a crossbar quantises over a conductance range, and IR drop is a
position-dependent systematic rather than a convolution.

### Known state, stated honestly

**Nothing inherited has been executed in this repo.** The tiers come from `grep` and
`diff`, which establish what *should* work, not what does. `pytest` will currently fail on
the inherited `conftest.py`. There is no crossbar model, no `CLAUDE.md`, and no site. The
local plan 02 is the audit that fixes this, and it runs before any model is built.

### One finding worth carrying forward

A parallel learning workspace (`learning/`, gitignored) was started against the primary
literature. Its anchor source — Grollier et al., *Neuromorphic Spintronics*, Nature
Electronics 3, 360–370 (2020) — states that an MTJ's **maximum-to-minimum conductance
ratio is "typically around three, whereas it can reach thousands for other resistive
switching memories,"** and names this in its abstract as a central obstacle to scaling.

That is this platform's counterpart to photonn's `2π` phase range, and it is very small.
Every distinguishable weight state and every noise margin must fit inside a factor of
three. It makes **error source 1 (conductance variation) the one most likely to bind**, and
it is the first real prediction this repo has about its own results.

Its magnitude, however, is `UNSOURCED`: device-to-device variation is established as a
real problem — Borders et al.'s 36-device network failed to recall its patterns from
"insufficient linearity and uniformity" — but no distribution is given. Finding one is the
largest open sourcing gap.

---

## 2026-09-08 — the harness was executed for the first time

The inheritance was sorted into three tiers by `grep` and `diff` on the day it arrived,
which establishes what *should* work. This is the entry that closes that: **35 tests, zero
skips**, with the Node and MATLAB checks actually running rather than being skipped past.

Ran against **Python 3.12.0** in a repo-local `.venv`, with **pytest 9.1.1** and **numpy
2.5.3** — the only two dependencies installed. `torch`, `h5py`, `scipy` and `matplotlib`
stay out until something imports them; whether a single crossbar layer needs `torch` at all
is a question for the plan that writes one.

### What is now proven by execution

- **Tier 1** — `+mc/validate_config` (rejects a misspelled field *and* names the nearest
  key), `+mc/sweep`, `+mc/pack`, `+err/detector_noise`, and `dom_stub.js` through the two
  runners that import it.
- **Tier 2** — `mount_queue.js`, `plot.js` and both runners, with the renamed globals
  asserted by name.

The seed partitioning is the one worth naming. `mc.sweep` handed its stub driver seeds
`[107, 207, 307, 407]` for `baseSeed = 7` — `baseSeed + 100*i`, exactly as its own comment
documents. That comment says the function was lifted out of the D²NN driver to stop two
drivers drifting apart on seeding, *"which is the thing that would quietly make their
tolerance tables incomparable."* Cross-platform comparability is the reason this repo
exists, and nothing in either repo had ever checked it.

### Five things execution found that inspection had not

1. **`tests/built_site.py` was misfiled as Tier 1.** It is byte-identical to photonn's, but
   its `pages()` helper calls `from apps.build_site import render` — photonn's five-page
   build. The coupling is to a *file*, not to optics, so a `grep` for photonic terms found
   nothing. It cannot pass until `build_site.py` is trimmed, and moved to that plan.

2. **`spinn/handoff.py` is not the lightest of Tier 3.** It was recorded at 9
   photonn-specific lines; line 27 is `from photonn.export import (...)`, a hard cross-repo
   import that cannot be satisfied here at all. Both it and `export.py` also fail earlier on
   `h5py`.

3. **`pyproject.toml` promises a README that does not exist.** `readme = "README.md"` at
   line 9, no such file — so `pip install -e .`, which is how photonn puts its package on
   the path, fails outright. The suite uses pytest's own `pythonpath = ["."]` instead, which
   also reaches `apps/` (not a declared package). Writing the README belongs with `CLAUDE.md`.

4. **`plot_runner.js` cannot see the rename it was inherited to protect.** It pulls the
   module in with `require` and never touches `window.SpinnPlot`, so that assignment could
   say anything and every assertion in `test_plot.py` would still pass — while a browser
   showed a page whose widgets never start, silently. `tests/test_web_globals.py` was added
   to check the export surface statically.

5. **`mc.sweep`'s default driver does not exist here.** `sweep.m:16` falls back to
   `@mc.run_montecarlo`; the drivers stayed in photonn. Every call site must pass `mcFn`
   explicitly, which is what the stub test does, and `sweep.m` stays byte-identical as a
   result. The crossbar driver is later work.

That is three files out of three where the tier metric understated the coupling — it counted
mentions of "photonn", not dependence on it. **Treat the tier counts as a lower bound.**

### Corrections to what was recorded before

- **MATLAB `-batch` startup is ~27 s cold and ~6.6 s warm**, not 27 s flat. The whole suite
  runs in about 7 s. One batch invocation per session is still the right shape — four would
  be four startups — but the margin is smaller than the cold figure implied.

### What changed in the tree

| | |
|---|---|
| `tests/conftest.py` | stripped to a seeded `rng` fixture and a shared `json_runner`. photonn's `d2nn_payload`, `mesh_payload`, `_OPERATING_POINT`, `_geometry` and `_test_set` were **deleted, not adapted** — they describe a schema this repo does not have. Their shape is a note for the handoff plan, not a fixture to keep. |
| `tests/test_harness.py` | new. The first test that ever ran here. |
| `tests/test_plot.py`, `tests/test_mount_queue.py` | ported from photonn. The runners were inherited; **their drivers were not**, so `mount_queue_runner.js`'s header referred to a file that did not exist. |
| `tests/test_web_globals.py` | new, for finding 4. |
| `tests/matlab_runner.m`, `tests/test_matlab_harness.py` | new. One `matlab -batch` per session printing a delimited JSON payload — `mc.sweep` prints a progress line per magnitude and there is no suppressing it without editing an inherited file. |
| `pyproject.toml` | `pythonpath = ["."]` under the pytest options, for finding 3. |
| `spinn/__init__.py` | re-pointed at the current plan filename and corrected: `handoff.py` is not merely awaiting a schema, it is unimportable. |

Nothing inherited was modified. `sweep.m`, `pack.m`, `validate_config.m`, `detector_noise.m`,
`mount_queue.js`, `plot.js` and both JS runners are untouched, so a `diff` against photonn
stays clean and any future drift remains auditable.

---

## 2026-09-08 — the web layer was cut to a spine, and the repo described itself

`apps/build_site.py` came across whole: **1192 lines, 59 KB**, written for five
pages, a figure pipeline, a MathML compiler and nine widgets. This repo has one page
and no figures. It is now **711 lines**, most of that CSS, and it builds.

### It was not a trim, because it could not be run

The plan assumed a trim-and-check loop. There was none available: the file could not
be **imported**, for three independent reasons. `from PIL import Image` — Pillow is
not a declared dependency. `from apps.compare_demo import ...`, `apps.d2nn_demo` and
`apps.diffraction_explorer` — 383 lines that were never copied. And
`BODY = page_body("index")` executing at import time against `apps/pages/`, which
existed and was **empty**.

So the spine was **extracted into a new file** rather than deleted down to, importing
after each move. The CSS was lifted by script rather than retyped, so nothing was lost
in transcription.

Two things the structural map had not shown, and only reading end to end did:

- **`_chrome()` depends on three helpers that live outside the file** —
  `read_web_asset`, `mount_queue_bundle` and `mount_script`, all generic, all in
  photonn's `apps/diffraction_explorer.py`, a module built around an optical widget
  and never copied. They are re-homed in `build_site.py` rather than dragged in with
  the explorer they happened to sit beside.
- **`mount_script` emits `window.PhotonnMount`**, and `PAGE_SCRIPT` persists the theme
  under `localStorage['photonn-theme']`. Two more sites the Tier 2 rename had to reach,
  one of them in a file nobody had copied. A `PhotonnMount` call against a `SpinnMount`
  global is undefined at mount time and silent in a browser.

### What was thrown away, and where to get it back

Everything below is recoverable from `D:\Python\Photonn\apps\build_site.py`, which is
**byte-identical** to the copy that arrived here — so these are exact coordinates, and
recovery is a copy rather than a rediscovery.

| block | photonn lines | why it went |
|---|---|---|
| `FIGURES` | 143–180 | seventeen optical figures; this repo has none |
| figure size and quality constants | 182–202 | measured against those figures |
| `_encodings`, `encode_figure` | 205–265 | the five-way encode-and-keep-smallest pipeline. Needs Pillow, an undeclared dependency, to encode nothing |
| `_FIGN`, `_FIG_KEY`, `figure_index` | 717–747 | caption numbering, with no captions |
| `_figures` | 1051–1064 | the token substitution for the above |
| the MathML compiler and table | 750–873 | 124 lines: `_MATH_OPS`, `_mtok`, `mrow`, `mfrac`, `msqrt`, `mathml`, `MATH`, `_math`. Thirty-odd optical expressions and the machinery to render them, serving zero equations here |
| `error_mask_bundle` | 876–903 | slices a trained phase mask out of the weights bundle |
| `error_mount`, `interference_mount` | 922–939 | mount photonn's widgets |
| four `PAGES` entries | 94–137 | physics, chip, tolerance, optics |
| four page-body constants | 1012–1035 | and the `render()` body that filled them, 1097–1175 |
| the explorer CSS host | 497–504 | `.explorer-band`, `.pe-host .pe-root` |
| **`apps/web_bundle.py`** | whole file, 202 lines | recorded as "16 photonn-specific lines"; it mentions photonn twice and carries 41 lines of phase-mask encoding — `wrap_phase` to `[-π, π)`, `quantise_phase`, `encode_masks`. Only the tail from `b64` at line 124 is the generic bundle mechanism, and nothing here writes a bundle |

**Correction to the plan that scheduled this.** It offered "the hub's *trimmed* copy of
`build_site.py`" as an alternative base. There is no such thing: `physical-ai` has no
`apps/` directory at all. From-scratch was the only fallback, and extraction landed
between the two.

### The palette was renamed, and a test now holds it

`--beam`, `--beam-soft`, `--fringe` and `--spectral` became `--accent`,
`--accent-soft`, `--accent-2` and `--rule-gradient`; `.spectral-rule` became
`.topline`. A spintronics repo has no beam and no fringe, and a name kept only because
photonn had it is the residue this pass exists to remove. **The colours themselves are
unchanged** — the hub's nav contract wants the spokes to share chrome.

An undefined CSS custom property is not an error; the declaration is silently dropped.
So `test_site_build.py` asserts every `var(--x)` used is also defined, which is the
only thing that would catch a half-finished rename.

### Numbers that moved

| | before | after |
|---|---|---|
| `apps/build_site.py` | 1192 lines | 711 |
| `apps/` Python | 3 files, 1483 lines | 2 files, 800 |
| tests | 35 | 53 |
| `site/index.html` | did not exist | 31 KB, self-contained |

### Left undone, deliberately

`tests/built_site.py` is now working against this repo's `render()`, which closes the
Tier 1 item the previous entry retiered. The `Page.widgets` field and the `plot.js`
inlining it gates are kept with no widget to gate — the mechanism is three lines and
the alternative is rediscovering it. `next_link` is kept but returns nothing: photonn
wraps the last page back to the first, which on a one-page site invites the reader to
go where they already are.

---

## 2026-09-08 — the ideal crossbar, trained, and one wrong constraint found

The first physics in this repo. `spinn/crossbar.py` is the ideal forward pass,
`spinn/task.py` loads the frozen shared task, `apps/train_crossbar.py` trains it.

**Ideal accuracy on the shared task: `0.7345`**, seed `20260908`, on a 36×10
differential array — **720 devices**, since a differential pair costs two per weight.
Test count 53 → 92.

### The shared task is frozen, not regenerated

`tools/import_shared_task.py` runs **once, in photonn's interpreter**, and is not
imported by anything here:

    D:/Python/Photonn/.venv/Scripts/python.exe tools/import_shared_task.py

The test split (2000 × 6×6) is lifted **verbatim** from `photonn/exports/mesh_phase3.h5`
— the artefact photonn's own mesh was scored on, so it cannot drift from what they
used. The train split (20000) is recomputed, because the handoff carries no training
data, but computed *there*, through photonn's own `encode_modes`, so the preprocessing
is theirs rather than a reimplementation of theirs. Output is committed at
`tests/fixtures/shared_task_6x6.npz`, 895 KB.

**Correction to the plan.** It called for freezing the 6×6 grid *before* photonn's L2
normalisation, on the grounds that unit-L2 is an optical convention — power at the
entrance — and a crossbar is bounded by a read voltage instead. The pre-normalisation
grid is not in the handoff, and it is also **not needed**. The samples are non-negative
and the normalisation is a *scale*, so dividing by the per-sample maximum recovers
exactly the L-infinity normalisation of the raw grid: `s/max(s) == d/max(d)`. A scale is
recoverable; an offset would not have been. The plan's concern was real for the wrong
transform.

### Decisions taken, with their reasons

**Signed weights: the differential pair.** Two devices per weight, wired so their
currents subtract.

| | differential | offset |
|---|---|---|
| devices per weight | two | one |
| signed range from the window | ±(g_max−g_min) | ±(g_max−g_min)/2 |
| conductance-variation draws | two, independent | one |
| the column pedestal | cancels in hardware | subtracted downstream |

The conductance window is this platform's binding physical constraint, so doubling the
signed range it yields is worth real devices. Two independent draws raise the effective
weight's σ by √2 against a range that doubles — net √2 in signal-to-noise — before
counting the pedestal, which under an offset scheme is a real input-dependent current
whose *mean* can be subtracted downstream and whose *noise* cannot.

Both schemes are implemented, because the scheme has to cross the handoff rather than be
assumed independently on each side. Ideally they are **identical** — an analytic test
asserts both reduce exactly to `normalised_input @ W` — so the choice is invisible in the
ideal accuracy and shows up only under error, in plan 05.

**Quantisation applies to devices, not to weights.** A device is the object with a finite
number of states. Under a differential pair the effective weight is a *difference* of two
quantised conductances and so resolves more finely than either device: two-state devices
give three distinguishable weights. Quantising the weight instead would understate the
scheme and make error source 2 look worse than it is.

**NumPy, not PyTorch.** The model is one 36×10 linear map and the gradient of softmax
cross-entropy through it is `X.T @ (p − Y)`. Autograd for one line of calculus is not
worth the largest dependency in the project. `torch` was **removed** from
`pyproject.toml` rather than installed, and `scipy` with it — nothing imported either.

### The wrong constraint, and what it cost

The first trainer used **projected** gradient descent, clipping weights onto `[-1, 1]`
after every step. It sounds more physical than training freely and rescaling at the end.
It is not, and it was wrong twice over:

- It clips *inside* the descent, so it distorts the search direction rather than the
  reachable set.
- The window does not bound what it appeared to bound. A positive global factor on every
  column current cannot change an argmax, so the window constrains the weight pattern's
  **shape**, not its **scale**.

| | test accuracy | weights at the window edge |
|---|---|---|
| projected each step | 0.6775 | 27.2% |
| unconstrained, then rescaled | **0.7345** | 0.3% |

**5.7 points**, and the projected run's saturation read exactly like evidence that the
window was binding. It was the optimiser. The trainer now fits unconstrained and divides
by `max|w|`, carrying `readout_gain = 5.4271` so the logits stay reconstructible — a gain
that must cross the handoff, or MATLAB rebuilds correctly-classified but wrongly-scaled
logits, which is invisible in an accuracy and wrong in anything derived from a margin.

photonn does the same thing on its side of the series: its handoff records `sigma`
passivized to ≤ 1 with an external gain of 3.9068, logit-preserving. The pattern was
already there to be copied.

Note the gain amplifies noise along with signal. It buys no signal-to-noise; it only
removes a constraint that was never physical.

### On the two platforms scoring alike

photonn's mesh scored `0.7355` on this identical frozen set; the crossbar scores `0.7345`
— one sample in 2000. **No conclusion is drawn from that, and none should be.** Both are
essentially linear maps over the same 36 channels, so comparable accuracy is what you
would expect rather than a finding. What it does buy is a cleaner comparison: neither row
in the table will be confounded by one platform simply having the better classifier.
Whether the platforms differ is a question for the error budget.

### UNSOURCED, and provably harmless here

`g_min = 1e-6 S`, `g_max = 3e-6 S`, `read_voltage = 0.1 V` are all `UNSOURCED`
placeholders. They **cancel exactly** in the decode, and a test asserts the ideal
accuracy is unchanged across two unrelated windows and drives — so the ideal number does
not rest on them. They are carried because the error model needs them, and because a
conductance window with no numbers in it invites someone to invent some.

The ratio `g_max/g_min` is the one that matters and is the platform's characteristic
constraint. The value here is a placeholder standing in the right region; sourcing it is
still open.

### Left undone, deliberately

No bias row. A crossbar column sums the currents on its wire; a bias would be an extra
row of devices at a fixed voltage, and that is device count spent outside the thing being
measured. No quantisation-aware training — the states knob exists and defaults off, and
it is error source 2, which belongs behind the handoff. The trained weights land in
`exports/`, which is gitignored: they are regenerable from the recorded seed.

---

## 2026-09-08 — the seam, and a differential pair reduced to a sign bit

Python designs, MATLAB measures, and the handoff crosses one way. That boundary now
exists for the crossbar: `spinn/export.py` writes it, `spinn/handoff.py` and
`spinn-hw/+io/read_handoff.m` are the two readers, `+model/crossbar.m` is the as-built
forward pass, and `+err` sources 1–3 sit behind it. Tests 92 → 120.

**MATLAB reproduces the accuracy Python recorded, exactly.** That single comparison is
the whole point of the plan: every way of getting the seam wrong yields a *valid* array
that is not the trained one — a transposed weight matrix, an image flattened
column-major, the signed scheme assumed rather than read, `readout_gain` defaulted to
1.0. None of them raise. The accuracy is the only detector, and it only detects with
trained weights, so the round-trip fixture trains briefly and a companion assertion
checks the transposed-input variant really does score differently. Otherwise the
headline check passes for free.

### The config API, named once

`+mc/error_sources.m` gained a `"crossbar"` arch with three keys, deliberately and
**not earlier**. Plan 02 had scheduled this for the audit; it was moved here because the
names encode a parameterisation that did not exist then, and a recorded Monte Carlo
result is keyed to them.

| key | source | why the name |
|---|---|---|
| `sigma_g_rel` | conductance variation | **relative to the window span, not siemens.** The reporting unit is `log2(range/σ)`, so `bits = -log2(sigma_g_rel)` directly, with no `UNSOURCED` window in the conversion |
| `states_per_device` | resolvable states | levels per *device*, not per weight |
| `wire_resistance_ohm` | IR drop | ohms per segment between adjacent cells |

Sources 4–7 get their keys when they get their implementations. Each key is tested
against its own plausible typo, because one passing check does not cover three keys.

### The error I made, and what caught it

Plan 03 recorded the rule "quantisation applies to devices, not to weights", reasoning
that a device is the object with finite states. That is true about the *constraint* and
wrong about the *operation*, and the difference is not small.

Rounding each rail independently, two-state devices, target `w = 0.3`: the positive rail
rounds up, the negative rounds down, and the pair lands on `+1` — where the nearest
representable weight is `0`. **The differential pair collapses to a sign bit, at twice
the device count of an offset.** Every argument for choosing it in plan 03 is voided,
silently, and the only symptom is a lattice with two values in it instead of three.

A real programmer knows the target weight and picks the pair of states that best
represents it. Quantisation therefore applies to the **effective weight**, over the set
a legal combination of device states can reach — `states` levels for an offset,
`2·states − 1` for a pair. Both sides were rewritten; `err.quantize` now takes weights
rather than conductances, and `model.program` gained the states argument, because
choosing which states represent a weight is part of programming rather than a
perturbation of it.

The round-trip test found it: MATLAB reported two effective weights where a Python probe
had reported three. The probe included an exact zero and the trained matrix did not, so
each side was right about what it measured and the model underneath was wrong.

### A second cross-language trap, found while fixing the first

`np.round` rounds half to **even**; MATLAB's `round` rounds half **away from zero**. They
differ only on exact halves — which is exactly where a weight sits between two device
states. Left alone the two sides would quantise such a weight differently, agree on
everything else, and disagree on an accuracy by a sample or two with nothing to point at.
Both sides now round half away from zero, with the Python side using an explicit helper.

### What crosses, and what does not

The operating point is a closed set of five: `g_min_s`, `g_max_s`, `read_voltage_v`,
`readout_gain`, `signed_scheme_code`. An unknown key fails at write time and a missing
one before the file exists; there is a test per field, so adding a field adds its guard.
`requiredAttr` on the MATLAB side keeps photonn's discipline of having **no default** — a
default is indistinguishable from a correct value downstream.

Two fields describe one fact — `devices_per_weight` and `signed_scheme_code` — and the
writer checks them against each other, because they are read by different parts of the
as-built model and one of them would be wrong.

`states_per_device` deliberately does **not** cross. How many levels a device resolves is
an as-built property and belongs in the error config, not in the ideal design the handoff
records.

The schema restarts at **0.1.0**. This is spinn's contract, not a continuation of
photonn's 0.3.0, and reusing their numbering would imply a compatibility that does not
exist.

### IR drop, and the approximation in it

Error source 3 is the crossbar's characteristic failure and has no photonic counterpart.
Row drivers sit at the column-1 edge and sense amplifiers at the row-1 edge; the segment
of wire before a cell carries the current every cell beyond it will draw, so the far
corner is starved worst, and **the effect grows with array size** — which is why the size
is fixed and reported beside any number derived from it.

It is computed **first order and deliberately not iterated**: the drops come from the
currents the ideal voltages would draw, rather than from a self-consistent solve. A
reduced voltage draws less current and so less drop, meaning one pass *overstates* the
effect. That is the safe direction for a tolerance study and it is not the same as being
right; iterating is the obvious refinement if this source turns out to bind.

photonn's `err.thermal_crosstalk` transfers conceptually and not at all in
implementation: that is a `conv2` blur over a phase mask, this is an accumulation along a
wire.

### The driver, and a zero that is not a bug

`mc.run_montecarlo_crossbar` satisfies `mc.sweep`'s contract and is passed to it
**explicitly**, because `sweep.m:16` still defaults to `@mc.run_montecarlo` — which this
repo does not have. Leaving `sweep.m` byte-identical is worth the inconvenience: its seed
partitioning is what keeps the two platforms' tolerance tables comparable.

Only source 1 is stochastic. A configuration carrying just sources 2 and 3 therefore has
**zero spread across realizations**, and `mc.pack` reports a standard deviation of
exactly zero. That is correct rather than broken, and it is pinned by a test so nobody
reads it later as a run that failed to vary.

### One guard retired on schedule

Plan 01 left a test asserting that `mc.error_sources("crossbar")` *raises*, with a note
saying that if it ever failed, plan 04 had happened and it should be replaced rather than
deleted. It failed today, and was replaced — by an assertion that the arch exists, plus a
new one that a genuinely unknown arch is still rejected.

---

## 2026-09-08 — the error budget: threshold and array size, declared first

**Written before any sweep was run.** Choosing what counts as "fails" after seeing the
curves is how a tolerance study quietly becomes an argument, so the pass mark and the
array size are fixed here and this entry is committed before the driver produces a
number.

| | |
|---|---|
| **Pass mark** | **95% of ideal accuracy**, i.e. **0.6978** against the recorded ideal of 0.7345. photonn's own convention — its `/tolerance` page carries a `>= 0.7591` bar against an ideal of 0.799, which is the same 95%. Using a different rule would make the two rows incomparable on the one axis the table exists for. |
| **Array size** | **36 × 10 logical, 720 devices** (differential pairs). Fixed for the comparable core and reported in the row, because IR drop grows with array size and a tolerance number for source 3 is meaningless without it. |
| **Edges** | Read off the magnitude ladder as a **bracket** — "holds at X, fails at Y" — never interpolated. `mc.pack` stores mean and standard deviation only, and no fitted crossing point, deliberately. |
| **Realizations** | 20 for the stochastic source. Deterministic sources are run at 3, which is enough to show the variance really is zero and not enough to waste time proving it. |
| **Seeds** | `baseSeed = 20260908`, partitioned by `mc.sweep` as `baseSeed + 100*i` per magnitude and by the driver as `+ i - 1` per realization. Recorded with the results. |

A ladder that never fails has not found an edge; it has found a too-narrow ladder. Each
source is swept over a range wide enough to bracket its edge from both sides, and if one
does not, the ladder is widened and the run repeated — that is a property of the ladder,
not a result.

---

## 2026-09-08 — the budget, and the row

The sweeps were run against the pass mark declared in the entry above, which was
committed at `3c97a6b` before the driver had produced a number. Results in
`docs/comparison_row.md`; raw output in `exports/error_budget.json`, gitignored and
regenerable. Tests 120 → 142.

### The row

| | |
|---|---|
| Ideal accuracy | **0.7345** on the shared task |
| Which source binds | **conductance variation** |
| Required precision | **4.84 effective bits** on the binding source |
| Delivered precision | `UNSOURCED` |
| Margin | *omitted* |
| Energy per inference | `UNSOURCED`; array read power **1.577 µW** |
| Latency per inference | `UNSOURCED` |

Array 36×10, 720 devices, differential pairs. Pass mark 0.6978.

### The edges, as brackets

| source | holds at | fails at | bits |
|---|---|---|---|
| 1. conductance variation | σ = 0.035 of the window → 0.7003 | σ = 0.05 → 0.6671 | **4.84 / 4.32** |
| 2. resolvable states | 7 states/device → 0.7010 | 5 states → 0.6615 | 3.70 / 3.17 |
| 3. IR drop | 100 Ω per segment → 0.7250 | 300 Ω → 0.6845 | *not a bit depth* |

**Conductance variation binds, as predicted before any of this was written.** It
demands 4.84 bits where the states knob demands 3.70, and both are expressed against
the same conductance window, so that is like for like rather than two numbers sharing
a column.

**IR drop is deliberately not converted to bits.** It is a position-dependent
systematic, not a spread on a stored value, so `log2(range/σ)` has no σ to take.
Forcing it into the unit would be a category error. Its cliff is also unusually
sharp: 100 Ω holds at 0.7250, 300 Ω fails at 0.6845, and 1 kΩ collapses to 0.12 —
roughly chance. Whatever the sourced wire resistance turns out to be, this source
either barely matters or destroys the array, with little in between at this size.
That behaviour is what "grows with array size" looks like from the inside, and it is
the strongest argument for the size sweep being the sequel.

### The joint run, and a check that was the wrong instrument

All three sources at the last magnitude each individually held: **0.6819 ± 0.0119**,
which is **below** the pass mark. Budgeting every source to its own edge leaves
nothing over.

The joint drop is 0.0526 against 0.0772 for the sum of the independent drops —
**sub-additive**. Plan 05 proposed checking "a joint run is the sum of the
independent ones" and treating agreement as evidence the seeding is sound. That is
the wrong instrument: accuracy saturates, because a sample already misclassified by
one source cannot be misclassified again by the next, so drops are sub-additive even
when the seeding is perfect. A sum-check would have failed for reasons unrelated to
what it was testing.

The property the per-source seed offsets actually exist for is that **adding a source
cannot change the draw another source gets**, and that is now tested directly: the
same seed must produce the same perturbation whatever base conductances it is applied
to. It does, on every device not clamped at a window edge.

### Two things in the data worth stating rather than smoothing

**The states ladder is not monotonic.** 33 states scores 0.7350, marginally *above*
the unquantised ideal of 0.7345, and 17 states (0.7170) scores below 9 states
(0.7260). Quantisation at coarse steps perturbs a handful of borderline samples in
whichever direction the rounding happens to fall, and at 2000 samples one flip is
0.0005. The bracket [7 holds, 5 fails] is unaffected, but a reader should not take
the curve as smooth.

**The differential pair's advantage grows with state count, and is smallest where it
is most often argued for.** `log2(2n−1) − log2(n)` approaches 1 bit as `n` grows and
is only `log2(3) − 1 = 0.585` bits at two states. A test asserting the opposite was
written first and failed; the reasoning behind it, not the code, was wrong. The
binary MTJ case gets the least out of the scheme.

### Energy and latency, and what is counted

Array read power is **1.577 µW**, computed exactly as
`mean_over_samples( Σ_ij V_i² · G_ij )` over all 720 devices.

**Array only** — it excludes the sense amplifiers, the ADC and every digital stage
after them. The periphery frequently dominates an analog accelerator's energy, so a
figure that quietly omits it is not comparable to one that does not, and the boundary
is stated rather than implied.

**Energy per inference needs a read time and no read time has been sourced.** Energy
= power × t_read; the arithmetic is published so a reader can substitute. Latency is
the RC settling of the lines and needs a line capacitance and resistance, neither
sourced. Both stay `UNSOURCED` rather than being filled with a plausible number.

The window and read voltage are `UNSOURCED` placeholders too, so the power figure
scales with them and is a worked example rather than a measurement. The accuracy and
bit-depth results do not depend on them — they cancel in the decode, and a test
asserts it.

### What the comparable core does not include

Error sources 4–7 (sneak paths, read noise, ADC quantisation, retention drift), the
array-size sweep, the site pages beyond the placeholder, and the spin-torque
oscillator. None of them blocks the row.

---

## 2026-09-08 — the five plans are closed, and archived

All five plans have been delivered and committed. They were moved to
`plans/finished_plans/` in the same pass, each stamped with the commit that closed it.
`plans/` stays gitignored, so this entry is the published record of that; the archive
itself is working material and is never pushed.

| plan | commit | what closed it |
|---|---|---|
| 01 prove the harness | `d80c2f2` | `pytest` green with the Node and MATLAB checks running rather than skipped; Tiers 1 and 2 proven by execution |
| 02 trim the inheritance | `abfd79c` | the web layer cut to a spine, `apps/web_bundle.py` gone, `CLAUDE.md` written |
| 03 the ideal crossbar | `9c4d9b5` | **0.7345** ideal at seed `20260908`, differential pairs, the frozen task committed |
| 04 the seam | `8b9543c` | schema 0.1.0 closed on both sides, `+model/crossbar.m`, `+err` 1–3, the driver |
| 05 the budget and the row | `3c97a6b`, `5646471` | the pass mark declared before the sweeps, then the row: conductance variation binds at **4.84 effective bits** |

Verified before archiving: `142 passed`, no skips, on `.venv/Scripts/python.exe -m pytest`
— so the MATLAB and Node checks ran rather than being absent.

**The comparable core is complete.** The repo now owes the series exactly what it was
scoped to owe — one row, in `docs/comparison_row.md` — and nothing in `plans/` is open.

### Why the plans are kept rather than deleted

They record what was believed *before* each piece was built, which is the only way to
tell a prediction that held from one written afterwards. Three of the five were wrong
about something that mattered, and in each case the plan text is the evidence:

- **01** classified the inheritance by inspection; execution corrected it. The recorded
  "photonn-specific line counts" counted mentions of the word, not dependence.
- **03** recorded "quantisation applies to devices, not to weights" and argued for the
  differential pair on grounds that rule would have voided. Plan 04's round-trip test
  caught it.
- **05** proposed a joint-equals-sum check as evidence the seeding was sound. Accuracy
  saturates, so that check would have failed for reasons unrelated to seeding.

The archived files are therefore **unedited below their status banner**, including the
`plans/*.md` cross-references that no longer resolve and the future tense they are
written in. Editing them to match what happened would destroy what they are kept for.

### What is not planned

No sixth plan exists, and one should not be written from the archive. The next work is
named in `CLAUDE.md` instead — the two open sourcing questions (a conductance window, a
wire resistance) under "Open decisions", and the deferred items under "Scope boundaries".
The array-size sweep is the strongest candidate among them, because IR drop's cliff at
this size is sharp enough that the row's number is visibly one point on a curve.
---

## 2026-09-09 — the page, and a third implementation of the physics

The comparable core was complete and the row was reported, and none of it was visible.
`site/index.html` was four sections of prose about a machine nobody could watch work.
This entry is the page that shows it: **six live instruments, all running the real
forward pass against the real trained weights and the whole frozen test set**, in the
reader's browser.

### The decision that cost the most, and why it was taken

A demonstration can be a cartoon of a measurement, and nobody would know. The cheap
version of this page draws a plausible crossbar, animates a plausible digit, and prints
0.7345 underneath — and it would look identical to this one in a screenshot.

It would also spend exactly the credibility the one-directional seam was built to earn.
This repository's numbers are worth something because the design half cannot quietly
adjust itself to flatter the measurement half; publishing an illustration of that
measurement on the one page most people read is the same failure in the other direction.

So the widgets compute. `apps/web/data.js` carries the trained 36×10 weights at full
precision and all 2,000 frozen test images, and `apps/web/crossbar.js` is a **third
implementation** of arithmetic that already exists in `spinn/crossbar.py` and in
`spinn-hw/+model` plus `spinn-hw/+err`. A third copy is normally where you stop and
extract a shared one. That was not available: the seam between the two existing copies is
one-directional by design, and neither Python nor MATLAB runs in a browser.

**A copy that cannot be shared is instead pinned.** `tests/test_web_crossbar.py` runs the
JavaScript under Node and recomputes every magnitude in `exports/error_budget.json` that
has no random draw — nine quantisation levels and nine wire resistances — against what
MATLAB recorded. All nine wire resistances match, which is the strongest single check
available: IR drop is the one source whose result depends on the absolute conductance
window and the read voltage, so reproducing it says the operating point crossed intact as
well as the arithmetic.

Two differences are real and are stated on the page rather than smoothed:

- **The conductance draw uses a different generator.** MATLAB draws from a Mersenne
  Twister seeded by `mc.sweep`'s partitioning; the browser draws from a small PRNG. Same
  distribution, different stream, so one realisation here is not one of the recorded
  realisations. The bench says so, and prints the recorded mean and spread beside the
  live number.
- **Three magnitudes on the states ladder differ by exactly one sample.** At coarse
  quantisation some digits produce two *exactly equal* column currents, and which column
  wins is then decided by the order the additions happened in — a matrix multiply and a
  loop sum associate differently. 0.6620 here against 0.6615 recorded at five states, and
  the same at three and two. Not a difference in the physics, and one sample in two
  thousand either way.

### What the page found that the repository had got slightly wrong

**The IR-drop bracket is conditional on the conductance window, and the row did not say
so.** `docs/comparison_row.md` stated that the accuracy and bit-depth results do not
depend on the `UNSOURCED` window because it cancels in the decode. That is true of
sources 1 and 2 and false of source 3: a wire drop is `R·I`, and `I` is set by the
absolute conductance of the devices. Holding the ratio at 3 and moving the window a
decade either way moves the edge past both ends of the swept ladder — at a tenth of the
placeholder even 1 kΩ holds, and at ten times it 100 Ω has already failed.

The bracket is unchanged and still correct. What was wrong was the scope of one sentence,
which claimed for all three sources what is true of two. Both the row and the page now
carry the condition, next to the array-size condition that was already there.

`apps/report_row.py` also gained the `render()` / `main()` split that
`apps/build_site.py` and `apps/export_web_data.py` already had, and
`tests/test_report_row.py` now asserts the committed row is what the module produces.
That is not tidiness: the row is generated and does **not** look generated — it is prose
with numbers in it — so the natural way to correct a sentence in it is to edit the file,
and the next run would have discarded the edit without a word. Correcting this sentence
is exactly the operation that would have been lost.

### The design work

An **extension** of the incumbent visual world, not a replacement: the serif display over
monospace metadata, the teal-and-amber pair, the five-stop rule and the light/dark toggle
all came from photonn and stay. What the build added is recorded in `DESIGN.md`, written
from the shipped artifact rather than from intentions —

- a **two-pole diverging ramp** for a signed weight: amber at −1, the page's own recessed
  surface at 0, teal at +1, so the devices doing nothing disappear and the trained pattern
  is what remains on screen;
- the **ruled instrument panel** — a hairline, a monospace title, the instrument. No
  cards, no nested boxes, and no card inside a card;
- **the settle**, the page's one authored motion moment: drive lines fill down the array,
  the column currents grow from zero, the winning column brightens once;
- an **ink-and-fill split** of all four signal colours. The fill values are the identity
  and carry rules, bars, cells and canvas geometry; darkened ink variants carry every
  piece of type, in the DOM and on canvas alike, and clear 4.5:1 *on the ground each label
  actually sits on* — which for several is an 8–10% wash of their own hue rather than the
  page. The `UNSOURCED` chip was the worst of them at 4.33:1 and is now 4.86:1.

The eyebrow above each section heading is **gone**. It had become load-bearing by
accident — `section_index` matched on it, so a section that dropped its eyebrow dropped
out of the contents card — and six of the eight restated the first words of the heading
beneath them. The match is anchored on `.phase-head` now, and the card's optional number
comes from a `data-num` attribute rather than from parsing a kicker's text. Anchoring on
nothing was tried in between and put the footer's three `<h3>` headings into the contents
card, which is why `test_the_contents_card_indexes_sections_and_nothing_else` exists.

### Numbers

Tests **142 → 171**, no skips. The page is **256 kB**, of which 86 kB is the frozen data;
it makes no external request, opens from `file://`, and reaches DOMContentLoaded in 83 ms
because `mount_queue.js` holds every widget until after the first paint. Nothing in the
physics changed and no result moved: the ideal is still 0.7345, conductance variation
still binds at 4.84 effective bits, and the row's brackets are the ones `5646471`
measured.

### Left undone

No second page. Error sources 4–7, the array-size sweep and the self-consistent IR-drop
solve are all still deferred, and the page's last section states what each would take
rather than apologising for it. The 17 font sizes the design detector reports against
`DESIGN.md` are pre-existing scatter between `.8rem` and `.95rem` plus three different
"the answer" display sizes in three widgets; they were left uncanonised deliberately,
because writing them into the schema would only make the inconsistency invisible.
