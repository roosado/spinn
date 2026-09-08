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
.venv/Scripts/python.exe -m pip install pytest numpy
.venv/Scripts/python.exe -m pytest        # Node and MATLAB checks skip if absent
.venv/Scripts/python.exe -m apps.build_site
```

Only `pytest` and `numpy` are installed today. The remaining dependencies in
`pyproject.toml` go in when something imports them.

## State

Early, and stated plainly. The Monte Carlo harness and web layer are inherited from
photonn and **proven by execution**; there is no crossbar model, no handoff and no
measurement yet. The page the build produces says so.

## How numbers are treated

Every as-built magnitude is either cited or marked `UNSOURCED` and shown as such. Where a
value cannot be sourced, no margin is claimed against it and the column is left out rather
than estimated. Spintronic device parameters are spread across a literature that mixes
measurements with roadmap projections, so this binds harder here than it might elsewhere.

See `CLAUDE.md` for the working conventions and the open decisions.
