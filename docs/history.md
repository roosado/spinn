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
