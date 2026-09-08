# spinn

A spintronic crossbar simulator and its device-error model. **A weight is a magnetic
state, and the sum is performed by Kirchhoff's law on a wire** — not by interference, and
not by a processor.

The question it exists to answer: *how precisely would such a thing have to be built
before it stops computing what it was trained to compute?*

This is the second platform in a physical-AI series. The first,
[photonn](https://github.com/roosado/photonn), computes with light. One example of
computation-by-physics is an anecdote; a second, in an unrelated medium, is what makes it
a class — so this repository owes exactly one row in a table that compares the two.

## Layout

| | |
|---|---|
| `spinn/` | Python — ideal crossbar physics, training, the handoff writer |
| `spinn-hw/` | MATLAB — device error modelling, Monte Carlo, tolerance budgets |
| `apps/` | the site generator and its page prose |
| `tests/` | one `pytest` run, which drives the Node and MATLAB checks too |

The Python and MATLAB halves are joined by a **one-directional** HDF5 handoff: Python
designs, MATLAB measures, and nothing crosses back. That boundary is what makes the
numbers trustworthy — a design that can be quietly adjusted to flatter its own error
budget is not a measurement of anything.

## Running it

```sh
py -3 -m venv .venv
.venv/Scripts/python.exe -m pip install pytest numpy h5py
.venv/Scripts/python.exe -m pytest        # Node and MATLAB checks skip if absent
.venv/Scripts/python.exe -m apps.build_site
```

`pytest`, `numpy` and `h5py` are installed. `matplotlib` is declared in `pyproject.toml`
and not installed, because nothing draws a figure yet; the remaining dependencies go in
when something imports them.

Regenerating the result end to end also needs MATLAB (base, no toolboxes):

```sh
.venv/Scripts/python.exe -m apps.train_crossbar     # writes exports/crossbar_handoff.h5
matlab -batch "addpath('spinn-hw'); run_error_budget('exports/crossbar_handoff.h5')"
.venv/Scripts/python.exe -m apps.report_row         # writes docs/comparison_row.md
```

Run from the repo root; `run_error_budget` writes `exports/error_budget.json`, which
`apps.report_row` reads. `exports/` is gitignored — the numbers that matter are copied
into `docs/`, the raw run output is not versioned.

## State

**The comparable core is done, and the row is in `docs/comparison_row.md`.** The ideal
array scores **0.7345** on the shared task; under device error, **conductance variation
binds, at 4.84 effective bits**, ahead of resolvable states and IR drop. Delivered
precision, energy per inference and latency are `UNSOURCED`, so no margin is claimed and
that column is omitted rather than estimated.

The array is 36×10 logical, 720 devices in differential pairs, and that size is fixed and
stated because IR drop grows with it. `docs/history.md` is the full record, newest last.

Not built, deliberately: error sources beyond the first three, an array-size sweep, the
site pages past the placeholder, and the spin-torque oscillator — which is complementary
and stays out of the comparison table on purpose. `CLAUDE.md` says why for each.

## How numbers are treated

Every as-built magnitude is either cited or marked `UNSOURCED` and shown as such. Where a
value cannot be sourced, no margin is claimed against it and the column is left out rather
than estimated. Spintronic device parameters are spread across a literature that mixes
measurements with roadmap projections, so this binds harder here than it might elsewhere.

See `CLAUDE.md` for the working conventions and the open decisions.
