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
| `apps/` | the site generator, its page prose, and the browser-side widgets |
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

The site is two pages, both self-contained: no external request, no webfont, no
analytics, and both open from `file://`.

`site/index.html` is the argument — one 36×10 array, and how precisely it would have to
be built. `site/larger.html` is the same instruments with the array size as a knob, 36 to
676 rows, where the wire starves the far corner of a large array and the first-order model
parts company with the network it approximates.

The widgets on both run the **real** forward pass, in the browser, with the same
arithmetic `spinn/crossbar.py` and `spinn-hw/+err/` run. The index carries the trained
36×10 weights and the whole frozen 2,000-image test set (`apps/web/data.js`, 86 kB); the
size page carries five trained arrays and a 500-digit sample of that same test set at each
grid (`apps/web/size_data.js`, 957 kB), which is why it is 1.3 MB against the index's
332 kB. Everything is inlined, so that weight is the price of fetching nothing.

Three tests hold the browser's copy of the physics to what MATLAB measured.
`tests/test_web_crossbar.py` recomputes every quantisation level and every wire resistance
in `exports/error_budget.json` under Node. `tests/test_web_size.py` does the same at five
array sizes, and additionally pins the browser's own solve of the wire network — a block
Thomas sweep over the same nodal system `err.ir_drop_exact` factors — to the 150 cell
fractions the sweep recorded, at 1e-9. `tests/test_web_widgets.py` mounts every widget at
every size and proves that tearing it down gives back every observer, timer and frame it
took, which is what makes the size page's rebuild-on-change safe.

`pytest`, `numpy` and `h5py` are installed. `matplotlib` is declared in `pyproject.toml`
and not installed, because nothing draws a figure yet; the remaining dependencies go in
when something imports them.

Regenerating the result end to end also needs MATLAB (base, no toolboxes):

```sh
.venv/Scripts/python.exe -m apps.train_crossbar     # writes exports/crossbar_handoff.h5
matlab -batch "addpath('spinn-hw'); run_error_budget('exports/crossbar_handoff.h5')"
.venv/Scripts/python.exe -m apps.report_row         # writes docs/comparison_row.md
.venv/Scripts/python.exe -m apps.export_web_data    # writes apps/web/data.js
.venv/Scripts/python.exe -m apps.build_site         # writes site/*.html
```

The size page has its own chain, one level up from that one — five arrays instead of one:

```sh
matlab -batch "addpath('spinn-hw'); run_size_sweep"   # writes exports/size/g*/
.venv/Scripts/python.exe -m apps.report_size          # writes docs/array_size.md
.venv/Scripts/python.exe -m apps.export_size_data     # writes apps/web/size_data.js
.venv/Scripts/python.exe -m apps.build_site           # writes site/*.html
```

Run from the repo root; `run_error_budget` writes `exports/error_budget.json`, which
`apps.report_row` and `apps.export_web_data` both read. `exports/` is gitignored — the
numbers that matter are copied into `docs/` and into `apps/web/data.js`, and the raw run
output is not versioned. Both of those copies are committed and both have a test that
fails when they drift from what regenerates them, so a stale one says so rather than
quietly publishing a previous run's numbers.

## Publishing

The site is at **<https://roosado.github.io/spinn/>**, and it is **not served from
`main`**. GitHub Pages is set to the `gh-pages` branch, root path, and that branch holds
the *contents* of `site/` — `index.html` and `larger.html`, since `_artifact_body.html` is
gitignored. So `main` carries the source and the built pages, and `gh-pages` carries only
what a visitor is served.

Publishing is therefore a second push, after the build and the commit:

```sh
.venv/Scripts/python.exe -m apps.build_site         # writes site/*.html
git add site && git commit                          # the committed bytes are the pages
git push origin main                                # the source, first
git subtree push --prefix site origin gh-pages      # then publish
```

**A push to `main` alone changes nothing a visitor sees.** That is the whole trap here,
and it is a quiet one: the build is green, the test asserting the committed bytes match
the generator passes, the commit lands, and the live page is still the previous one.

**The reverse is a worse trap, and it has happened.** `git subtree push` reads `site/`
from whatever branch it is run on and neither knows nor cares whether that branch exists
on the remote. On 2026-09-21 the size page went live from a local branch that had not been
merged or pushed, so for about an hour the published page existed and the source that
generated it existed in exactly one working tree. Push the source first, then publish.

If `git subtree push` refuses because the histories have diverged, the reliable form is
to split and force:

```sh
git push origin "$(git subtree split --prefix site main)":gh-pages --force
```

That is safe here in a way it usually is not: `gh-pages` is a build artifact with no
history worth keeping, and every commit on it is reproducible from `main` by running the
build.

## State

**The comparable core is done, and the row is in `docs/comparison_row.md`.** The ideal
array scores **0.7345** on the shared task; under device error, **conductance variation
binds, at 4.84 effective bits**, ahead of resolvable states and IR drop. Delivered
precision, energy per inference and latency are `UNSOURCED`, so no margin is claimed and
that column is omitted rather than estimated.

The operating point is a design — a thick-barrier magnetic tunnel junction, read through
and written beside — checked against cited device physics rather than copied from a
device. In it, published wiring resistances sit five times inside IR drop's edge.

The array is 36×10 logical, 720 devices in differential pairs, and that size is fixed and
stated because IR drop grows with it. `docs/array_size.md` sweeps it, from 36 to 676 rows,
and says where cited wiring stops holding. `docs/history.md` is the full record, newest last.

`site/index.html` carries all of it: what a weight physically is, the sum performed on a
wire, the array classifying frozen digits and one you draw yourself, the three error
sources taken apart on a live bench, the measured budget with its brackets, and the row.
`site/larger.html` then puts the array size on a control and runs the same instruments
from 36 to 676 rows.

Not built, deliberately: error sources beyond the first three and the spin-torque
oscillator — which is complementary and stays out of the comparison table on purpose.
`CLAUDE.md` says why for each, and the last section of the page states what each would
take. Open, and a decision rather than work: whether the row's IR-drop source moves onto
the solved network the size sweep used.

## How numbers are treated

Every as-built magnitude is either cited or marked `UNSOURCED` and shown as such. Where a
value cannot be sourced, no margin is claimed against it and the column is left out rather
than estimated. Design values — the conductance window and the read voltage — are this
project's own choice, held to being something the device can physically be; the sources
that show it are cited, and none of their numbers is copied. Spintronic device parameters are spread across a literature that mixes
measurements with roadmap projections, so this binds harder here than it might elsewhere.

See `CLAUDE.md` for the working conventions and the open decisions.
