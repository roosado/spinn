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
