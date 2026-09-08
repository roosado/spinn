# spinn — Project Context

Spintronic neural network simulator. Two codebases, one project.

- `spinn/` — Python. Ideal crossbar physics, training, the handoff writer.
- `spinn-hw/` — MATLAB. Device error modelling, Monte Carlo, tolerance budgets.

**Central question:** how precisely must a spintronic crossbar be built before it stops
computing what it was trained to compute?

This is the **second platform** in the physical-AI series. The first, `photonn`, computes
with light. One example of computation-by-physics is an anecdote; a second, in an
unrelated medium, is what makes it a class. The deliverable is therefore **one row in the
hub's comparison table** — not a second photonn.

The machine learning content is intentionally minimal. Do not expand it. All complexity
belongs in the device physics and the error model.

---

## Environment

- Laptop-only. No cluster, no GPU, no fabrication, no measurement. Everything is
  simulation against sourced parameters.
- Python 3.12 in a repo-local `.venv`: `pytest`, `numpy`, `h5py`. `matplotlib` is
  declared in `pyproject.toml` and not installed, because nothing draws a figure yet;
  `torch` and `scipy` were removed rather than deferred. A dependency goes in when
  something imports it.
- MATLAB base, no toolboxes. Flag it if one becomes necessary. `-batch` startup is ~27 s
  cold and ~6.6 s warm, which is why the whole MATLAB suite is one invocation.
- Node, for the two web runners.
- Run the suite with `.venv/Scripts/python.exe -m pytest`. Build the page with
  `python -m apps.build_site`.

---

## Architecture

```
spinn/
├── crossbar.py       # the ideal forward pass: program, read, decode
├── task.py           # the frozen shared task, MNIST at 6x6
├── export.py         # the one handoff writer
└── handoff.py        # the one Python reader

spinn-hw/
├── +mc/              # sweep, pack, validate_config, error_sources + the crossbar driver
├── +model/           # program, encode, crossbar — the as-built forward pass
├── +err/             # conductance_variation, quantize, ir_drop (+ inherited detector_noise)
└── +io/read_handoff.m  # the one MATLAB reader

apps/
├── train_crossbar.py # trains the ideal array; NumPy, no autograd
├── build_site.py     # the site generator, trimmed to a spine
├── preview.py        # standalone shell for previewing one widget
├── pages/index.html  # page prose lives here, never in the generator
└── web/              # mount_queue.js, plot.js

tools/
└── import_shared_task.py  # one-off, runs in PHOTONN's venv, never imported here

tests/                # pytest drives everything, including Node and MATLAB
└── fixtures/shared_task_6x6.npz   # the frozen task, committed
```

### The model, and the row it produced

36 inputs × 10 columns, **differential pairs**, so 720 devices. Ideal accuracy on the
shared task is **0.7345** (seed `20260908`), with `readout_gain = 5.4271`.

The comparable core is complete. **Conductance variation binds, at 4.84 effective
bits**; the full row and its brackets are in `docs/comparison_row.md`, and that is the
single statement of it — the hub refers to it rather than copying it. Delivered
precision, energy per inference and latency are all `UNSOURCED`, so no margin is
claimed and that column is omitted.

`g_min`, `g_max` and `read_voltage` are `UNSOURCED` placeholders and **cancel exactly**
in the decode — a test asserts the ideal accuracy is unchanged across unrelated windows.
They are carried because the error model needs them.

### Inherited from photonn

Twenty files were copied in rather than re-derived, and for the Monte Carlo harness that
was also the safer choice. **Inherited code is a starting point, not a constraint**: keep
a file because this repo needs it, never because photonn had it — and equally, do not
re-derive one that already works.

`mc/sweep.m` is the one to protect. Its seed partitioning (`baseSeed + 100*i`) is what
keeps two platforms' tolerance tables comparable, and its own comment says so. It is
byte-identical to photonn's and should stay that way. **Its default driver handle points
at `mc.run_montecarlo`, which this repo does not have** — pass `mcFn` explicitly at every
call site.

Treat the "photonn-specific line counts" recorded for the inherited files as a **lower
bound**. They counted mentions of the word, not dependence: three files out of three
turned out to be more coupled than recorded.

### Handoff contract

Schema **0.1.0** — spinn's own, restarted rather than continuing photonn's 0.3.0.

The boundary is **one-directional**: Python designs, MATLAB measures, one writer and one
reader on each side. The operating point is a **closed set of five** — `g_min_s`,
`g_max_s`, `read_voltage_v`, `readout_gain`, `signed_scheme_code` — and refuses both an
unknown key and a missing required one, on both sides. Neither reader supplies a default:
a default is indistinguishable from a correct value downstream, which is how a renamed
field becomes a plausible wrong answer instead of a stack trace.

`states_per_device` deliberately does **not** cross. How many levels a device resolves is
an as-built property and belongs in the error config, not the ideal design.

The seam is proven by round trip: MATLAB rebuilds the array from the file alone and must
reproduce the accuracy Python recorded. That is the only detector for a transposed weight
matrix, a column-major image flatten, an assumed signed scheme or a defaulted gain — none
of which raise.

---

## Plan of work

Five plans in `plans/` (gitignored), in order. Each has a deliverable that can be checked
by running something.

| | | state |
|---|---|---|
| 01 | prove the harness | **done** — Tier 1 and 2 executed |
| 02 | trim the inheritance | **done** — the web layer cut to a spine, this file |
| 03 | the ideal crossbar | **done** — 0.7345 ideal, differential pairs |
| 04 | the seam | **done** — closed handoff, `+model/crossbar`, `+err` 1–3, 120 tests |
| 05 | the budget and the row | **done** — conductance variation binds at 4.84 bits |

---

## Scope boundaries

### Build

- An **MTJ / domain-wall crossbar**. These are one model with a knob — states per weight
  — not two machines.
- The **shared task**: photonn's MNIST protocol at **36 channels** (6×6). A crossbar is an
  N×N matrix engine, so the MZI mesh is its like-for-like counterpart, not the D²NN.
- Error sources, platform-native and in this order: conductance variation, resolvable
  states, IR drop; then sneak paths, read noise, ADC quantisation, retention drift.
- One row in `/compare`, reported once, here.

### Do not build

- **Do not force photonn's error sources onto a crossbar.** A common list would measure
  the taxonomy rather than the hardware.
- **Do not copy photonn's physics.** `propagate.py`, `fields.py`, `elements.py`, `mzi.py`,
  `models.py`, `layers.py`, `detect.py` and every optical `+err` source stay where they are.
- **Do not implement error modelling in Python, or training in MATLAB.**
- **Do not let the spin-torque oscillator into the comparison table.** It is complementary
  and explanatory; "how precisely must this be built to classify MNIST" is not a question
  you ask of a reservoir. Keeping it out is a decision, not an oversight.
- No micromagnetics, no LLG solving, no p-bits, no materials science.

### Deliberately deferred

- The site pages beyond `index.html`. There is no result to write about yet.
- An array-size sweep. IR drop grows with array size, so the row's number is one point on
  a curve — but the size is fixed and stated first.
- A self-consistent IR-drop solve. Source 3 is first-order and one pass overstates the
  drop; iterating is the refinement if it turns out to bind.
- Error sources 4–7, and the keys that name them.

---

## Working conventions

- **Every number is cited or marked `UNSOURCED` and surfaced.** This binds harder here
  than in photonn: spintronic device parameters are spread across a literature that mixes
  measurements with roadmap projections. A confident wrong number costs more than an
  admitted hole. **Do not invent a physical constant.**
- **No margin against an uncited value.** Publish tolerance *edges* and omit the margin
  column entirely rather than estimating it.
- **Tolerance edges are brackets** — "holds at X, fails at Y" — never interpolated.
- Random seeds fixed and recorded for every Monte Carlo run.
- Physics functions are pure and NumPy-native; any autodiff wrapper stays thin.
- Every physics function gets a corresponding analytic test. A crossbar has exact small
  cases, so this is cheap.
- **Config key names are an API.** Renaming one after a run exists invalidates every
  recorded result keyed to it. Name them when the thing they describe exists.
- Prefer explicit, readable physics over vectorised cleverness. This is meant to be read.
- Page prose lives in `apps/pages/*.html`, never in the generator.
- `.gitattributes` pins LF. If something fails oddly on Windows, check line endings before
  logic.
- **A bug found in an inherited file is a bug in photonn too.** Note it; fix it there.
  This repo does not push changes upstream.
- `plans/` and `learning/` are gitignored working material and are never published.
  **`learning/` does not inform the build** — it may inform page prose later, nothing else.

---

## Open decisions

Do not assume an answer; ask.

1. **A source for the conductance window.** `g_max/g_min` is the platform's
   characteristic constraint and the current value is a placeholder. This is the largest
   open sourcing gap.
   Also unsourced, and needed by plan 05: a wire resistance for `wire_resistance_ohm`,
   and the energy and latency constants.
2. **Whether IR drop matters at all**, which cannot be answered without a sourced wire
   resistance. Its cliff is sharp — 100 Ω holds, 1 kΩ is chance — so the sourced value
   decides between "irrelevant" and "fatal" with little in between at this array size.

### Resolved

Kept so a later session does not reopen a question already answered.

- **Signed weights: the differential pair.** Two devices per weight. The window is the
  binding constraint, so doubling the signed range it yields is worth the devices: two
  independent error draws raise σ by √2 against a range that doubles, a net √2 in SNR,
  before counting the pedestal an offset scheme must subtract downstream. Both schemes
  are implemented because the choice crosses the handoff; ideally they are identical.
- **Quantisation applies to the effective weight**, over the lattice a legal combination
  of device states can reach — `states` levels for an offset, `2·states − 1` for a pair.
  The devices are what have finite states, but the programmer picks the pair that best
  represents the target. Rounding each rail independently collapses the pair to a sign
  bit at twice an offset's device count, silently; plan 04's round-trip test caught it.
- **Both sides round half away from zero.** NumPy rounds half to even and MATLAB does
  not, and they differ exactly where a weight sits between two device states.
- **NumPy, not PyTorch.** One 36×10 linear map; the gradient is `X.T @ (p − Y)`. `torch`
  and `scipy` were removed from `pyproject.toml` rather than installed.
- **The window bounds the weight pattern's shape, not its scale.** Train unconstrained,
  then divide by `max|w|` and carry the factor as a readout gain. Projecting onto
  `[-1, 1]` inside the descent cost 5.7 points of accuracy and looked like evidence the
  window was binding. It was the optimiser. photonn does the same thing with `sigma`.
- **The array size is 36×10**, 720 devices. Fixed for the comparable core and stated in
  the row, because IR drop grows with array size.
- **The pass mark is 95% of ideal**, photonn's own convention, declared before the
  sweeps ran (commit `3c97a6b`) so the ordering is checkable rather than asserted.
- **Edges are brackets, never interpolated.** `mc.pack` stores no fitted crossing point.
- **Joint-equals-sum is not a test of the seeding.** Accuracy saturates, so drops are
  sub-additive even when seeding is perfect. The property that matters — a source's
  draw not depending on what else is active — is tested directly instead.

- **MATLAB for the as-built half, and why.** Reversed from an initial "Python for both" on
  inspecting `photonn-hw`: `mc.sweep` takes a driver handle and requires only
  `(handoff, errorConfig, nRealizations, baseSeed) -> {.acc, .mean}`, and
  `mc.validate_config` dispatches on a model *kind*, so a third kind is an established
  extension point. Reimplementing the seeding discipline in Python risked a difference
  that would not announce itself.
- **The comparison unit is effective bits**, `log2(range / sigma)`, plus energy and
  latency. Any analog tolerance normalises against the device's own operating range.
- **The frozen test set is imported from photonn as data.** The one deliberate exception
  to repo independence — regenerating "the same" MNIST subset independently is how two
  platforms end up scored on different data without anyone noticing.
- **No thesis is pre-registered** about linearity, walls, or which platform wins. Measure,
  report, and explore anything interesting *after* it appears.
