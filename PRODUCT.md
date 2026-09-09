# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

A **technical reader who does not know spintronics**: physicists outside magnetism, ML
engineers, and technically literate hiring managers. Comfortable with matrices and
probability; not assumed to know what an MTJ, a domain wall, or a crossbar is. They
arrive from the physical-AI hub or from a link, on a laptop or a phone, giving the page
minutes rather than an afternoon.

The page must therefore explain the device, and may assume the mathematics.

## Product Purpose

`spinn` answers one question: **how precisely must a spintronic crossbar be built before
it stops computing what it was trained to compute?** It is the second platform in a
physical-AI series; the first, `photonn`, computes with light. One example of
computation-by-physics is an anecdote; a second, in an unrelated medium, makes it a
class.

The repository's deliverable is **one row in the hub's comparison table**. The site's
job is different and larger: to make a reader *see* the machine compute — a weight as a
magnetic state, a sum performed by a wire, a digit classified — and then see that
machine degrade under real device error until it stops working.

Success is a reader who can say what binds the design, at what precision, and why they
should believe the number.

## Positioning

The mechanism a neighbouring project could not truthfully copy: **a one-directional
Python→MATLAB seam.** Python designs the ideal array; MATLAB measures the as-built one;
nothing crosses back. A design that can be quietly adjusted to flatter its own error
budget is not a measurement of anything. The seam is proven by round trip — MATLAB
rebuilds the array from the handoff file alone and must reproduce the accuracy Python
recorded.

The second: **every number is cited or marked `UNSOURCED` and surfaced.** No margin is
claimed against an uncited value; tolerance edges are published as brackets ("holds at
X, fails at Y") and never interpolated. Where a value is missing, the column is omitted
rather than estimated.

## Operating Context

Read in a browser, often from the hub's comparison table, sometimes offline or from
`file://`. Pages are built by `python -m apps.build_site` into `site/`, deploy to GitHub
Pages, and make **no external requests** — no CDN, no webfont, no analytics. They must
survive a strict CSP and open from a local file.

The reader is scanning first and reading second: the contents card, the topbar and the
section structure are load-bearing.

## Capabilities and Constraints

**The machine.** 36 inputs × 10 columns, differential pairs, 720 devices. Ideal accuracy
**0.7345** on the shared task (MNIST at 6×6, imported frozen from `photonn`), seed
`20260908`, readout gain `5.4271`. Pass mark **0.6978** = 95% of ideal, declared before
the sweeps ran.

**The result.** Conductance variation binds, at **4.84 effective bits** (holds at
σ = 0.035 of the window, fails at 0.05). Resolvable states holds at 7, fails at 5
(3.70 bits). IR drop holds at 100 Ω per segment, fails at 300 Ω, and is deliberately
**not** converted to bits — it is a position-dependent systematic, not a spread on a
stored value. All three at their individual edges together: 0.6819, below the pass mark.

**The holes, which must stay visible.** `g_min`, `g_max`, `read_voltage` and
`wire_resistance_ohm` are `UNSOURCED` placeholders. Delivered precision, energy per
inference and latency are `UNSOURCED`. Array read power is 1.577 µW, **array only** —
it excludes sense amplifiers, ADC and every digital stage after them.

**Technical constraints.** Everything inlined; no external subresource. Theme-aware with
a persisted toggle (`spinn-theme`). Widgets mount through `window.SpinnMount`, draw
through `window.SpinnPlot`, and must not block first paint. Page prose lives in
`apps/pages/*.html`, never in the generator. Site tests assert the committed bytes match
`render()`.

## Brand Commitments

Name `spinn`, lowercase. Voice: precise, plain, and unhedged; states what was done and
what was not. A confident wrong number costs more than an admitted hole. British
spelling in prose.

The incumbent visual system is binding as a starting point: serif display over
monospace metadata, a five-stop spectral rule, teal accent, light and dark.

## Evidence on Hand

Real, and usable directly by the page:

- `exports/crossbar_ideal.npz` — the trained 36×10 weights, readout gain, seed.
- `tests/fixtures/shared_task_6x6.npz` — 2000 frozen test images at 6×6 with labels.
- `exports/error_budget.json` — every sweep magnitude, mean, std and bracket.
- `docs/comparison_row.md` — the row, stated once.
- `spinn/crossbar.py`, `spinn-hw/+err/*.m` — the exact algorithms the widgets reproduce.

**No measured device data exists.** No fabrication, no measurement, no cited conductance
window. Nothing on the page may imply otherwise, and no physical constant may be
invented.

## Product Principles

1. **Show the machine computing, do not assert that it computes.** The reader's own
   digit through the real weights beats any diagram.
2. **A hole is shown as a hole.** `UNSOURCED` is surfaced in the interface, never
   smoothed over or filled with a plausible number.
3. **An edge is a bracket.** Publish "holds at X, fails at Y"; never interpolate a
   crossing point the data does not contain.
4. **The widgets run the real arithmetic**, matching `crossbar.py` and `+err/*.m`, on
   the real weights and the real frozen test set. A demonstration that is a cartoon of
   the result would undo the seam that makes the result trustworthy.
5. **What is not built is future work, not an apology.** Deferred items are named with
   what they would take.

## Accessibility & Inclusion

Keyboard operable throughout, including every widget control. Contrast holds in both
themes. `prefers-reduced-motion` is honoured — the page already disables reveals and
must not animate the crossbar under it. No result may exist only as colour: a value a
reader needs is also written as a number.
