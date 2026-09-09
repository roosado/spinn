---
version: 1
slug: "apps-pages-index-html"
primary_target: "apps/pages/index.html"
related_targets: ["apps/build_site.py","apps/web"]
---

Scope: `apps/pages/index.html` — the one page the site builds, rebuilt around live widgets.
Visitor mode: **Read** (the visitor is here to understand something), with demonstration as
its instrument rather than illustration.

Audience: a technical reader who does not know spintronics — physicists outside magnetism,
ML engineers, technically literate hiring managers. Assumes matrices; explains devices.
Job: understand what this machine is, watch it work, and leave able to say what binds it
and at what precision.

Constraints that bind the surface: everything inlined, no external subresource, opens from
`file://`; theme-aware light/dark with a persisted toggle; widgets mount via
`window.SpinnMount` and draw via `window.SpinnPlot`; page prose lives in this file, never
in the generator; `prefers-reduced-motion` honoured.

## Direction contract

THESIS: The array is the interface. One 36x10 lattice of real devices is drawn at page
scale and every claim the page makes is made by driving it — a digit enters as row
voltages, the columns sum, one column wins — and then by damaging it three ways until the
answer fails. Refused: the research-writeup default (prose sections with a static plot
dropped in at the end) and the landing-page default (hero, then a grid of equal cards).
No card grid carries structure anywhere on this page.

OWN-WORLD: The incumbent world, inherited whole — Iowan Old Style serif display over
monospace metadata, teal accent with amber second, the five-stop spectral rule, light and
dark. Extended only where instruments need vocabulary the page did not have: a device
lattice on canvas in a two-pole diverging ramp (amber = negative rail, teal = positive,
page ground = zero) so a weight's sign reads at a glance; instrument panels ruled rather
than carded — one hairline top rule, mono labels, no nested boxes, no card inside a card;
every readout tabular mono; controls are rules and handles, not pills.

STORY: The reader learns that a weight is a magnetic state read as a conductance, sees
Kirchhoff's law perform the sum on a wire, watches the real trained array classify frozen
MNIST digits and then their own drawn digit, and discovers that accuracy is a function of
build precision — that conductance variation binds first, at 4.84 effective bits, ahead of
resolvable states and IR drop. They believe it because they operated it themselves, on the
real weights and the real test set, and because every unsourced quantity is labelled as a
hole rather than filled.

FIRST VIEWPORT: Topline spectral rule and topbar unchanged. Below it, no standard hero:
a two-column band at >=980px. Left (38%): the h1 "A neural network made of magnets" in
serif at clamp(2.1rem, 4.6vw, 3.35rem), the standfirst, and a live readout naming the
digit the array is currently answering. Right (62%): the machine itself, running from
load — the 6x6 input tile, the 36x10 device lattice, and ten column-current bars with the
winner lit, cycling a new frozen test digit every 1.4 s with a stop/step control. Under
both, a four-cell measurement strip: 720 devices, 0.7345 ideal, 4.84 bits, 36x10. On a
phone the two columns stack, machine first below the h1, lattice at full width.

FORM: Extension of an established surface (new-work section 3, "Extend an existing
surface") — the world is inherited, no concept tournament was run, and DESIGN.md is not
rewritten. Signature interaction: the error bench — three sliders (conductance sigma,
states per device, wire resistance) re-classify all 2000 frozen test images in the browser
on every drag, corrupt the lattice visibly, and move an accuracy needle against the
declared pass mark. Motion grammar, one authored moment: the settle — row voltages sweep
in left to right over ~180 ms and the column bars grow from zero on an exponential
ease-out, with the winning bar brightening once; nothing else on the page moves beyond the
existing scroll reveal, and reduced motion snaps every value and leaves autoplay off.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review,
the verdict, DESIGN.md, and every shipping raster carrying its provenance.
