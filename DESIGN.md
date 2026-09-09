---
name: spinn
description: A ruled instrument panel for a spintronic crossbar — serif claim, monospace measurement, no cards.
colors:
  bg: "#f4f7fb"
  surface: "#ffffff"
  surface-2: "#eef2f8"
  border: "#d8e0ec"
  ink: "#141b26"
  ink-dim: "#3f4c60"
  muted: "#64707f"
  accent: "#0f9e8f"
  accent-ink: "#0a7064"
  accent-soft: "rgba(15,158,143,.10)"
  accent-2: "#c9701f"
  accent-2-ink: "#9c5411"
  good: "#2f8f52"
  good-ink: "#237a41"
  bad: "#c14a34"
  bad-ink: "#ba4530"
  rule-gradient: "linear-gradient(90deg,#39d1a0,#4fc6e6,#f2c14e,#ef7d5a,#c05aa8)"
  bg-dark: "#0a0d12"
  surface-dark: "#111826"
  surface-2-dark: "#0e131d"
  border-dark: "#243149"
  ink-dark: "#e8edf4"
  ink-dim-dark: "#b7c2d2"
  muted-dark: "#7787a0"
  accent-dark: "#2ec9b8"
  accent-2-dark: "#f2994a"
  good-dark: "#57c07a"
  bad-dark: "#e0705f"
  accent-soft-dark: "rgba(46,201,184,.14)"
typography:
  display:
    fontFamily: "\"Iowan Old Style\",\"Palatino Linotype\",Palatino,\"Book Antiqua\",Georgia,\"Times New Roman\",serif"
    fontSize: "clamp(2.1rem, 4.6vw, 3.35rem)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-.01em"
  headline:
    fontFamily: "{typography.display.fontFamily}"
    fontSize: "clamp(1.55rem, 2.8vw, 2.05rem)"
    fontWeight: 600
    lineHeight: 1.14
  title:
    fontFamily: "{typography.display.fontFamily}"
    fontSize: "clamp(1.15rem, 2vw, 1.42rem)"
    fontWeight: 600
    lineHeight: 1.2
  body:
    fontFamily: "ui-sans-serif,-apple-system,\"Segoe UI\",Roboto,\"Helvetica Neue\",Arial,sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.65
  standfirst:
    fontFamily: "{typography.body.fontFamily}"
    fontSize: "1.16rem"
    lineHeight: 1.65
  label:
    fontFamily: "ui-monospace,\"Cascadia Code\",\"SF Mono\",Consolas,\"Liberation Mono\",Menlo,monospace"
    fontSize: ".75rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: ".16em"
  readout:
    fontFamily: "{typography.label.fontFamily}"
    fontSize: "clamp(1.05rem, 2vw, 1.42rem)"
    fontWeight: 600
    letterSpacing: "-.01em"
    fontFeature: "tabular-nums"
  answer:
    fontFamily: "{typography.display.fontFamily}"
    fontSize: "4.2rem"
    fontWeight: 600
    lineHeight: 0.86
    fontFeature: "tabular-nums"
rounded:
  hair: "2px"
  chip: "5px"
  list: "6px"
  control: "7px"
  marker: "9px"
  box: "10px"
  card: "12px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  lg: "20px"
  xl: "26px"
  section: "52px"
components:
  panel-instrument:
    backgroundColor: "transparent"
    textColor: "{colors.ink-dim}"
    rounded: "0px"
    padding: "20px 0 0"
  panel-instrument-title:
    textColor: "{colors.accent-ink}"
    typography: "{typography.label}"
  button-tool:
    backgroundColor: "transparent"
    textColor: "{colors.ink-dim}"
    rounded: "{rounded.control}"
    padding: "6px 12px"
    typography: "{typography.label}"
  button-tool-hover:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.ink}"
  button-column:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.control}"
    height: "30px"
    width: "30px"
  button-column-pressed:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent-ink}"
  theme-toggle:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    padding: "5px 13px"
    typography: "{typography.label}"
  nav-link:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    padding: "5px 11px"
  nav-link-current:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent-ink}"
  field-range:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    height: "16px"
  field-range-thumb:
    backgroundColor: "{colors.accent}"
    rounded: "{rounded.hair}"
    width: "11px"
    height: "16px"
  chip-hole:
    backgroundColor: "color-mix(in srgb,#c9701f 8%,transparent)"
    textColor: "{colors.accent-2-ink}"
    rounded: "{rounded.chip}"
    padding: ".05em .38em"
  spec-cell:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "0px"
    padding: "15px 22px 15px 0"
  row-record-row:
    backgroundColor: "transparent"
    textColor: "{colors.ink-dim}"
    rounded: "0px"
    padding: "11px 0"
---

# Design System: spinn

## Overview

**Creative North Star: "The Ruled Instrument Panel"**

This is a laboratory page, not a product page. Its subject is one continuous machine — a
36×10 lattice of magnetic devices — and the page is built as the bench that machine sits
on: a hairline rule, a monospace label naming what is below it, and then the instrument
itself at full width. Nothing is boxed. A card inside a card is what a dashboard becomes
when nobody decides, and on a page whose whole argument is that one array does all of this,
tiling each view of it into its own container argues the opposite of the content.

The palette is inherited whole from a sibling platform and is deliberately unchanged: a
cool paper ground, a teal accent, an amber second, and a five-stop spectral hairline across
the very top of the page. What this build added is a way to draw *signed physical state*.
A weight in this machine is a difference between two devices, so the array is painted on a
two-pole diverging ramp — amber at −1, the page's own second surface at 0, teal at +1 — and
zero weights vanish into the page so the trained pattern is the only thing left visible.
That single decision is why the hero reads as a picture of something rather than a heat map.

Density is high and quiet. Type does the ranking, not colour and not elevation: serif for
every claim, monospace for every measured quantity, one micro-label size for every caption
and legend on the page. Confirmed rejections: no card grid carries structure anywhere; no
research-writeup pattern of prose with a static plot dropped in at the end; no shadows; no
webfont and no external request of any kind.

**Key Characteristics:**
- Ruled, never carded — hairline separators do all the work containers would.
- Serif claims over monospace measurement; nothing in between.
- A two-pole diverging ramp that grounds zero in the page itself.
- Flat: depth comes from tonal surfaces and 1px borders, never from shadow.
- One authored motion moment on the whole page, and it means something.
- Every colour is a custom property, read by CSS and by canvas from the same place.

## Colors

Cool laboratory paper under two working hues, one for each sign of a weight; everything
else is a neutral or a state.

### Primary
- **Crossbar Teal** (`--accent`, #0f9e8f light / #2ec9b8 dark): the positive rail. Carries
  the array's positive cells, range-slider thumbs, focus outlines, hover borders and the
  live-page marker. Its 10% wash (`--accent-soft`) is the only tinted background in the
  system.
- **Teal Ink** (`--accent-ink`, #0a7064 light / #2ec9b8 dark): the same identity as type.
  Every teal *word* on the page — instrument titles, section numbers, the answer numeral,
  links, footer headings — is this value, not the fill.

### Secondary
- **Domain Amber** (`--accent-2`, #c9701f light / #f2994a dark): the negative rail, and
  the page's mark for an absence. It fills negative cells and the negative half of a device
  track.
- **Amber Ink** (`--accent-2-ink`, #9c5411 light / #f2994a dark): the italic word in the
  headline, the `UNSOURCED` chip, a missed classification, an out-of-tolerance readout.

### Tertiary
- **Pass Green** (`--good` / `--good-ink`): reserved for one meaning — a tolerance edge
  that still holds, and a bench verdict above the declared pass mark.
- **Fail Rust** (`--bad`, #c14a34 / #e0705f): fill only — the failing bar on the accuracy
  meter, and the 2.9rem accuracy numeral, which is large enough to be exempt.
- **Fail Rust Ink** (`--bad-ink`, #ba4530 / #e0705f): the same identity as type, at any size
  below display: the finding callout's tag, a failing bench verdict, a failed tolerance edge.
- **The Spectral Rule** (`--rule-gradient`, five stops: #39d1a0 → #4fc6e6 → #f2c14e →
  #ef7d5a → #c05aa8): 3px across the top of the page and 132px under the headline. It is
  the platform's signature and appears exactly twice; it is never a background or a fill.

### Neutral
- **Cool Paper** (`--bg`, #f4f7fb / #0a0d12): the page ground.
- **Card White** (`--surface`, #ffffff / #111826): raised neutral for the contents card and
  the drawing pad only.
- **Recessed Paper** (`--surface-2`, #eef2f8 / #0e131d): the *zero point of the weight
  ramp*, and the ground of inline code and the finding callout. It is load-bearing: change
  it and every array in the page repaints.
- **Hairline** (`--border`, #d8e0ec / #243149): every rule, every 1px control edge, every
  scrollbar thumb, every axis drawn on canvas.
- **Ink / Dim Ink / Muted** (`--ink` #141b26, `--ink-dim` #3f4c60, `--muted` #64707f): the
  three-step text ramp. Ink for emphasis and readouts, dim for running prose, muted for
  labels and captions.

### Named Rules
**The Ink-and-Fill Rule.** Each of the four signal hues ships twice: a fill value
(`--accent`, `--accent-2`, `--good`, `--bad`) and an ink value (`--accent-ink`,
`--accent-2-ink`, `--good-ink`, `--bad-ink`). Fills are the identity and carry rules, bars, cells, thumbs and canvas
geometry, where no contrast floor applies. Ink carries *all type*, in the DOM and on canvas
alike, and is darkened in light theme until it clears 4.5:1 **on the ground it actually sits
on** — which for several labels is an 8–10% wash of their own hue, not the page. Measured in
the shipped values: teal ink 5.56 on the page and 5.32 on the recessed surface, amber ink
5.30 / 5.07, green ink 4.97 / 4.75, rust ink 4.91 / 4.69, against fills of 3.10, 3.36 and
4.35-on-the-recessed-surface that would fail. The rust pair was split last, after the first
record, for exactly the ground its one type use sits on. In dark
theme the two are the same value in all four pairs, because the fills already clear the
floor there (9.42, 8.74, 8.55, 6.16). Collapsing ink back into fill "to simplify" is the single easiest way to break
this system.

**The Two-Pole Rule.** A weight is signed, so it is drawn on a diverging ramp with the page
under it: amber at −1, `--surface-2` at 0, teal at +1. Zero is not a colour, it is the
absence of one. Never introduce a third hue for zero and never draw weights on a sequential
ramp.

**The Hole Rule.** An unsourced quantity is drawn as a hole, not as a value: amber ink on an
8% amber wash with an amber hairline, never as ordinary body text. A number the project
cannot cite must be visibly different from one it can.

## Typography

**Display Font:** Iowan Old Style (falling back through Palatino Linotype, Palatino, Book
Antiqua, Georgia, Times New Roman, serif)
**Body Font:** the platform UI sans stack (ui-sans-serif, -apple-system, Segoe UI, Roboto)
**Label/Mono Font:** the platform mono stack (ui-monospace, Cascadia Code, SF Mono, Consolas)

**Character:** A serif that argues and a monospace that measures, with a neutral sans doing
the reading in between. The serif appears only where the page makes a claim — headline,
section headings, and the one enormous numeral that is the array's answer. Everything that
is a quantity, a unit, a legend, an axis or a caption is monospace, tabular, and small.

**Known limitation, not a token:** the page ships no webfont and makes no external request,
which is a hard product constraint. The display face therefore resolves per platform and
will not be Iowan Old Style on most machines; the design depends on *serif-ness* and on the
size ramp, never on that specific face's metrics.

### Hierarchy
- **Display** (600, `clamp(2.1rem, 4.6vw, 3.35rem)`, 1.08, −.01em, balanced wrap): the one
  h1. Its emphasised word is italic in amber ink.
- **Headline** (600, `clamp(1.55rem, 2.8vw, 2.05rem)`, 1.14): section headings, always
  inside a `.phase-head` beside a monospace section number.
- **Title** (600, `clamp(1.15rem, 2vw, 1.42rem)`, 1.2): sub-headings inside a section.
- **Standfirst** (1.16rem, dim ink, max 60ch): the single paragraph under the h1.
- **Body** (17px/1.65, dim ink, max `--measure` = 68ch): running prose. Bolded runs step up
  to full ink rather than changing colour.
- **Label** (mono, 600, .75rem, .10–.18em tracking, uppercase, muted): every caption,
  legend, axis title, control label, table header and instrument title on the page.
- **Readout** (mono, 600, tabular-nums, 1.15rem–2.9rem by importance): every measured
  number, in ink; four sizes exist and they rank the numbers, not the layout.
- **Answer** (serif, 600, 4.2rem, tabular-nums, teal ink; amber ink when wrong): the single
  digit the array is currently claiming.

### Named Rules
**The One Micro-Size Rule.** There is one small-label size: `.75rem`. It replaced six
near-identical sizes that were all doing the same job, four of them under 12px. A new
caption, legend or control label uses `.75rem` and earns its rank from tracking, case and
colour — never from a fractional size step.

**The Tabular Rule.** Any number a reader might compare or watch change is monospace with
`font-variant-numeric: tabular-nums`. A readout that reflows its own width as it counts is
a readout that has been made harder to read.

**The Two-Voice Rule.** Serif claims, monospace measurements. There is no third voice; if a
piece of text is neither a claim nor a measurement, it is body sans.

## Layout

One centred column, `max-width: 1120px` with 24px gutters, and a hard reading measure of
`--measure: 68ch` on prose (60ch for the standfirst, 64ch for instrument captions).
Instruments are allowed to break the measure and use the full 1120px; prose never does.

The first viewport is a two-column band at ≥980px — the claim on the left at roughly 38%,
the running machine on the right at 62%, with the live readout beneath the claim — laid out
on named grid areas so that below 980px it restacks as claim, machine, readout: the machine
comes *before* the paragraph describing it, because the page's promise is "watch this thing
work".

Sections are separated by a 1px top border and 52px of padding, each opening with a
monospace section number in a soft-teal box beside its serif heading. The in-page contents
is one element with two presentations: a bordered card in the flow, and at ≥1500px the same
list pinned in the right margin as a border-left rail — 1500px being where a 176px rail and
its gap clear the 1120px wrap on both sides without moving the content off centre.

Instrument-internal grids collapse at their own breakpoints, close to the content:
980px (hero), 860px (the three tolerance panels), 800px (the bench), 720px (device, draw,
the four-cell spec strip), 640px (topbar padding, hero padding), 560px (the comparison
record and the next-work list). Rhythm is a loose 4/8/14/20/26px scale; sections at 52px.
Anchor targets carry `scroll-margin-top: 78px` to clear the sticky topbar.

## Elevation & Depth

**This system has no shadows at all.** Not one `box-shadow` is declared anywhere in the
stylesheet or in any widget. Depth is entirely tonal and linear: a 1px `--border` hairline,
and at most one step of surface tone (`--surface` above the page, `--surface-2` recessed
below it). The only non-flat treatment in the page is the topbar's `backdrop-filter:
blur(8px)` over an 82% mix of the page ground, which exists so text scrolling underneath a
sticky bar stays readable — not to lift it.

### Named Rules
**The No-Shadow Rule.** Nothing on this page casts one. An element that needs to separate
from its neighbour gets a hairline; an element that needs to sit apart gets one tonal step.
If a surface seems to need a shadow, it is usually a card that should have been a rule.

**The Rule-Not-Card Rule.** An instrument panel is a hairline top rule, a monospace title,
an optional right-aligned note, a caption, then the instrument. It has no background, no
border box and no radius, and nothing inside it is boxed either. The same grammar drives the
four-cell measurement strip (cells divided by vertical rules), the comparison record and the
next-work list. Boxes are reserved for genuinely detached objects: the contents card, the
finding callout, the drawing pad.

## Shapes

Corners are small and functional, and they scale with how much of a *thing* an element is:
2px on the range thumb and the underbar, 5px on inline code, 6px on contents-list rows and
scrollbar thumbs, 7px on tool buttons and column buttons, 9px on the section-number box,
10px on the drawing pad and the finding callout, 12px on the contents card, and full pills
(999px) only on the topbar's two pill-shaped controls — the theme toggle and
the nav links — where the round form marks page-level chrome as distinct from instrument
chrome.

Borders are always exactly 1px and always `--border` at rest, going teal on hover. Focus is
a `2px solid var(--accent)` outline with a 2–4px offset, applied through `:focus-visible` on
every interactive element without exception. Controls are drawn as *rules and handles*: a
range input is a 1px track with an 11×16px square running along it — a scale with a marker
on it — rather than a pill with a bead in it. Canvas geometry follows the same logic: array
cells are drawn with no gap between rows, because a crossbar is a continuous sheet of wiring
and separating every cell into its own tile reads as a spreadsheet.

Icons are drawn as inline SVG with `currentColor`, never as Unicode glyphs or an icon font;
the theme mark is a 16-viewBox half-filled circle at 11px.

## Components

### Buttons
- **Shape:** softly squared (7px radius), 1px hairline border, transparent ground.
- **Tool button** (`.xh-btn` / `.bn-btn` / `.dw-btn` / `.wr-btn`): monospace .75rem
  uppercase at .10em tracking, dim ink, 6px 12px padding. Every widget's controls are this
  one button.
- **Hover / Focus:** border goes teal, text goes full ink, ground goes `--accent-soft`, over
  a 150ms colour/border/background transition. Focus is a 2px teal outline at 2px offset.
- **Toggle state:** `aria-pressed="true"` promotes it to teal ink on `--accent-soft` with a
  teal border and 600 weight; there is no separate "selected" colour.
- **Column button:** the same button squared to 30×30px, used as the ten column selectors.

### Chips
- **Hole chip** (`.q.hole`): the inline-code chip recoloured amber — amber ink, 8% amber
  ground, 40% amber border. Marks a value the project cannot cite.
- **Planned badge** (`.badge-next`): muted mono uppercase on a *dashed* pill border. Dashed
  means "not built yet" throughout the system; the section-number box uses the same dashed
  treatment for a planned section.

### Cards / Containers
Used sparingly and only for detached objects.
- **Corner Style:** 12px (contents card), 10px (finding callout, drawing pad).
- **Background:** `--surface` for the contents card and pad; `--surface-2` for the finding
  callout, which is recessed because it is an aside rather than a control.
- **Shadow Strategy:** none. See Elevation & Depth.
- **Border:** 1px `--border`.
- **Internal Padding:** 15–20px.

### Inputs / Fields
- **Style** (`.sp-field`): a monospace uppercase label above, a 1px `--border` track, an
  11×16px teal square thumb with a 2px radius, and a monospace tabular `<output>` below
  showing the current value. No fill, no pill, no bead.
- **Hover:** the thumb scales 1.18× vertically over 120ms — the handle grows, the track
  never changes.
- **Focus:** 2px teal outline at 4px offset around the whole track.
- **Caret:** `caret-color: var(--accent)` on every input, button, select and textarea.

### Navigation
Monospace .75rem pills in a sticky, blurred topbar over an 82% page-ground mix with a
hairline bottom border. Links are muted and borderless at rest; hover tints them
`--accent-soft`; only `aria-current="page"` gets teal ink plus a 45% teal border. The brand
is monospace dim ink with a teal-ink wordmark and a descriptive tail that disappears below
900px. The theme toggle sits at the right as a pill with a drawn SVG mark and the word
"theme", and persists its choice to `localStorage` under `spinn-theme`.

### The Instrument Panel (signature)
The page's structural unit. `.inst` is a 1px top rule and 20px of padding; `.inst-h` is a
baseline-aligned row holding `.inst-t` (mono .75rem uppercase, teal ink, 600) at the left and
`.inst-n` (mono muted) at the right; `.inst-d` is a dim-ink caption capped at 64ch; the
instrument follows at full available width. Five of these carry the whole page. No panel has
a background, a border box or a radius.

### The Crossbar View (signature)
A shared drawing vocabulary — `apps/web/xbar_view.js` — that all four array widgets call, so
the array is drawn once and looks the same everywhere. Two modes:
- **effective** — 360 weights on the two-pole diverging ramp, `--surface-2` at zero.
- **rails** — 720 devices, each cell split into its positive (teal) and negative (amber)
  device, each filled by that device's own occupancy.
Both ramps are mixed from the page's live custom properties, so they follow the theme rather
than carrying a second palette.

### The Readout (signature)
The hero's answer: a 4.2rem serif tabular numeral (3.2rem below 720px) in teal ink beside a
monospace kicker-free label and a dim-ink sentence, separated from the standfirst by a
hairline. It turns amber ink when the array gets the digit wrong. One widget owns both the
numeral and the picture, so the two can never disagree.

## Do's and Don'ts

### Do:
- **Do** put every colour in a CSS custom property in the four theme blocks (`:root`, the
  `prefers-color-scheme:dark` media query, and the two `data-theme` overrides), and let both
  CSS and canvas read it from there.
- **Do** read canvas colours through `SpinnView.ink()` and redraw on `SpinnPlot.onThemeChange`.
  Two widgets grew private copies of that read and were consolidated; a private copy is a
  second palette waiting to drift.
- **Do** use ink variants (`--accent-ink`, `--accent-2-ink`, `--good-ink`) for every word,
  in the DOM and on canvas, and fill variants for every rule, bar, cell and thumb.
- **Do** build a new panel as a hairline rule plus a monospace title (`.inst`), and a new
  fact list as ruled rows (`.row-rec`, `.next-list`) rather than as tiles.
- **Do** size every small label at `.75rem` and rank it with tracking, case and colour.
- **Do** give every interactive element a `:focus-visible` outline of `2px solid var(--accent)`.
- **Do** honour `prefers-reduced-motion` by snapping every animated value to its end state
  and leaving autoplay off.
- **Do** draw an uncited number as a hole (`.q.hole`) rather than as a value.
- **Do** record both themes' values when a token is added. The palette is two full sets, and
  a token documented in one theme only is a token half the readers never had described.

### Don't:
- **Don't** add a `box-shadow` anywhere. The system has none, and depth is a hairline plus
  one tonal step.
- **Don't** build a card grid, or nest a bordered box inside another bordered box. Panels are
  ruled; boxes are for the contents card, the finding callout and the drawing pad only.
- **Don't** use a fill value as type colour below display size, or "simplify" the ink/fill
  split away. In light theme the fills measure 3.10, 3.36 and 4.35 against the grounds they
  sit on and fail the contrast floor; the ink variants exist for exactly that.
- **Don't** introduce a third hue for a zero weight, or draw signed weights on a sequential
  ramp; zero is `--surface-2` and disappears.
- **Don't** spend the spectral gradient on anything but the 3px topline and the 132px
  headline underbar. It is a signature, not a fill.
- **Don't** add a Unicode glyph as an icon; draw an inline SVG with `currentColor`. A glyph
  renders at whatever weight the reader's fallback font happens to have.
- **Don't** add a kicker or an eyebrow above a heading. The predecessor's `<p class="eyebrow">`
  was removed from this system entirely — six of eight restated the first words of the heading
  beneath them — and section indexing now anchors on `.phase-head` with an optional `data-num`.
- **Don't** animate anything beyond the scroll reveal and the settle. Motion here has to mean
  drive, sum, decide.
- **Don't** introduce a webfont or any external subresource; the page must open from `file://`.
