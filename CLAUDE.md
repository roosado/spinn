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
- Python 3.12 in a repo-local `.venv`. **Currently only `pytest` and `numpy` are
  installed** — `torch`, `h5py`, `scipy` and `matplotlib` are declared in
  `pyproject.toml` but deliberately not installed until something imports them.
- MATLAB base, no toolboxes. Flag it if one becomes necessary. `-batch` startup is ~27 s
  cold and ~6.6 s warm, which is why the whole MATLAB suite is one invocation.
- Node, for the two web runners.
- Run the suite with `.venv/Scripts/python.exe -m pytest`. Build the page with
  `python -m apps.build_site`.

---

## Architecture

```
spinn/
├── __init__.py       # version only; nothing is exported yet
├── export.py         # handoff writer          — INHERITED, optical, not yet adapted
└── handoff.py        # the single Python reader — INHERITED, does not import

spinn-hw/
├── +mc/              # sweep, pack, validate_config, error_sources — the shared harness
├── +err/             # detector_noise only, so far
└── +io/read_handoff.m  # the single MATLAB reader — INHERITED, optical

apps/
├── build_site.py     # the site generator, trimmed to a spine
├── preview.py        # standalone shell for previewing one widget
├── pages/index.html  # page prose lives here, never in the generator
└── web/              # mount_queue.js, plot.js

tests/                # pytest drives everything, including Node and MATLAB
```

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

**Unsettled.** `export.py`, `handoff.py` and `+io/read_handoff.m` still describe photonn's
optical schema, and the last of these will not even import. The operating point cannot be
closed before there is a model to operate, so this is owned by `plans/04-the-seam.md`.

What is already decided: the boundary is **one-directional** — Python designs, MATLAB
measures — with **one writer and one reader on each side**, and a **closed** operating
point that refuses both an unknown key and a missing required one. A default is
indistinguishable from a correct value downstream, which is how a renamed field becomes a
plausible wrong answer instead of a stack trace.

---

## Plan of work

Five plans in `plans/` (gitignored), in order. Each has a deliverable that can be checked
by running something.

| | | state |
|---|---|---|
| 01 | prove the harness | **done** — 53 tests, Tier 1 and 2 executed |
| 02 | trim the inheritance | **done** — the web layer cut to a spine, this file |
| 03 | the ideal crossbar | Python forward pass, signed-weight decision, ideal accuracy |
| 04 | the seam | closed handoff, `+model/crossbar`, `+err` sources 1–3, the config API |
| 05 | the budget and the row | binding source, its edge in effective bits, energy, latency |

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
- `torch`. Whether a single crossbar layer needs it is decided in plan 03, on evidence.

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

1. **Signed weights: differential pair or offset.** A pair doubles the device count and
   gives each weight two independent error draws; an offset needs the column pedestal
   subtracted downstream. Plan 03 decides it and writes the reason down.
2. **The array size for the comparable core.** Must be fixed and stated in the row.
3. **`torch` or plain NumPy** for training. Plan 03, on evidence.

### Resolved

Kept so a later session does not reopen a question already answered.

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
