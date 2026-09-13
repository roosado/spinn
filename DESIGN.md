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
    fontSize: "clamp(1.25rem, 2vw, 1.42rem)"
    fontWeight: 600
    lineHeight: 1.2
  body:
    fontFamily: "ui-sans-serif,-apple-system,BlinkMacSystemFont,\"Segoe UI\",Roboto,\"Helvetica Neue\",Arial,sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.65
  standfirst:
    fontFamily: "{typography.body.fontFamily}"
    fontSize: "1.16rem"
    lineHeight: 1.65
  caption:
    fontFamily: "{typography.body.fontFamily}"
    fontSize: ".9375rem"
    fontWeight: 400
    lineHeight: 1.5
  note:
    fontFamily: "{typography.body.fontFamily}"
    fontSize: ".8125rem"
    fontWeight: 400
    lineHeight: 1.5
  datum:
    fontFamily: "{typography.label.fontFamily}"
    fontSize: ".8125rem"
    fontWeight: 400
    fontFeature: "tabular-nums"
  label:
    fontFamily: "ui-monospace,\"Cascadia Code\",\"SF Mono\",Consolas,\"Liberation Mono\",Menlo,monospace"
    fontSize: ".75rem"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: ".12em"
  label-title:
    fontFamily: "{typography.label.fontFamily}"
    fontSize: ".75rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: ".16em"
  readout-small:
    fontFamily: "{typography.label.fontFamily}"
    fontSize: ".95rem"
    fontFeature: "tabular-nums"
  readout:
    fontFamily: "{typography.label.fontFamily}"
    fontSize: "clamp(1.25rem, 2vw, 1.42rem)"
    fontWeight: 600
    letterSpacing: "-.01em"
    fontFeature: "tabular-nums"
  readout-large:
    fontFamily: "{typography.label.fontFamily}"
    fontSize: "2.9rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-.02em"
    fontFeature: "tabular-nums"
  answer:
    fontFamily: "{typography.display.fontFamily}"
    fontSize: "4.2rem"
    fontWeight: 600
    lineHeight: 0.86
    fontFeature: "tabular-nums"
  answer-compact:
    fontFamily: "{typography.display.fontFamily}"
    fontSize: "3.2rem"
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

**The Paper Rule.** Print is always the light palette. Both dark blocks are scoped to
`screen`, and for the length of a print the page script sets `data-theme="light"` so every
canvas redraws through `onThemeChange` — a canvas is pixels in whichever theme was live, and
dark-theme ink on white paper is pale grey on white. `afterprint` puts the reader's own
choice back. Controls a sheet of paper cannot operate (the hero's, the bench's and the pad's
tool rows, the toggle, the skip link) are left off it.

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
  h1, styled through `.machine-say h1`. Its emphasised word is italic in amber ink.
- **Headline** (600, `clamp(1.55rem, 2.8vw, 2.05rem)`, 1.14): section headings, always
  inside a `.phase-head` beside a monospace section number.
- **Title** (600, `clamp(1.25rem, 2vw, 1.42rem)`, 1.2): sub-headings inside a section. The
  floor was 1.15rem, which on a phone put a heading below the standfirst it follows.
- **Standfirst** (1.16rem, dim ink, max 60ch): the single paragraph under the h1.
- **Body** (1.0625rem/1.65, dim ink, max `--measure` = 60ch): running prose. Bolded runs step
  up to full ink rather than changing colour. In rem, not px, so it follows a reader's own
  default size along with everything else; at `17px` it was the one thing that did not.
- **Caption** (sans, .9375rem/1.5, dim ink): instrument captions, the readout's sentence,
  the bench's verdict, the comparison record's values, the next-work notes, the footer.
- **Note** (sans, .8125rem/1.5, muted): the reference list, widget footnotes, the spec
  strip's labels. **Datum** is the same size in mono, tabular: deltas, the ladder's
  brackets, the colophon, the column keys.
- **Label** (mono, 400, .75rem, .12em, uppercase, muted): every legend, field label, axis
  title and record key. **Label title** is the same at 600 and .16em in teal or rust ink:
  instrument titles, the ladder's panel names, the finding's tag, footer headings. Tool
  buttons keep their own .10em.
- **Readout** (mono, 600, tabular-nums): every measured number, in ink, at three sizes that
  rank the numbers rather than the layout — small (.95rem: slider values, section numbers),
  medium (`clamp(1.25rem, 2vw, 1.42rem)`: the spec strip, the device's outputs) and large
  (2.9rem: the bench's accuracy).
- **Answer** (serif, 600, 4.2rem, 3.2rem below 720px, tabular-nums, teal ink; amber ink
  when wrong): the digit the array is claiming — in the hero, and for the reader's own
  drawing.

### Named Rules
**The One Micro-Size Rule.** There is one small-label size: `.75rem`. It replaced six
near-identical sizes that were all doing the same job, four of them under 12px. A new
caption, legend or control label uses `.75rem` and earns its rank from tracking, case and
colour — never from a fractional size step. The same discipline holds one level up: prose
smaller than body is a Caption or a Note, and nothing else; twelve sizes between 12 and
15px once did those two jobs. Type drawn on a canvas is one size, 11px, through
`SpinnView.font()`, which reads `--mono` from the stylesheet — the densest axes have no room
for 12.

**The Tabular Rule.** Any number a reader might compare or watch change is monospace with
`font-variant-numeric: tabular-nums`. A readout that reflows its own width as it counts is
a readout that has been made harder to read.

**The Two-Voice Rule.** Serif claims, monospace measurements. There is no third voice; if a
piece of text is neither a claim nor a measurement, it is body sans.

**The Outline Rule.** Anything that titles what follows it is a heading element, whatever it
looks like: the rank comes from the outline and the look from the class. Instrument titles are
`<h3>` in the Label-title style, the budget's three panel names `<h4>`, the two sub-headings
`<h3 class="sub-h">`, the footer's column heads `<h2>`. The instrument titles and sub-headings
were paragraphs styled as headings, and heading navigation — how a screen reader skims —
skipped all seven.

## Layout

One centred column, `max-width: 1120px` with 24px gutters, and a hard reading measure of
`--measure: 60ch` on prose, which the standfirst and the instrument captions share.
Instruments are allowed to break the measure and use the full 1120px; prose never does.

The first viewport is a two-column band at ≥980px — the claim on the left at roughly 38%,
the running machine on the right at 62%, with the live readout beneath the claim — laid out
on named grid areas so that below 980px it restacks as headline, machine, readout,
standfirst: the machine comes *before* the paragraph describing it, because the page's
promise is "watch this thing work". The standfirst shares `.machine-say` with the headline,
so below 980px that wrapper is `display: contents` and its children take rows of their own.
Only the picture moves; the markup, and so the order a screen reader hears, stays headline,
standfirst, machine. Those rows are spaced by a 22px gap alone, their margins zeroed,
because grid rows do not collapse margins and two systems of spacing would fight.

Sections are separated by a 1px top border and 52px of padding, each opening with a
monospace section number in a soft-teal box beside its serif heading. The in-page contents
is one element with two presentations: a bordered card in the flow, and at ≥1500px the same
list pinned in the right margin as a border-left rail — 1500px being where a 176px rail and
its gap clear the 1120px wrap on both sides without moving the content off centre.

Instrument-internal grids collapse at their own breakpoints, close to the content:
980px (hero), 860px (the three tolerance panels), 800px (the bench goes to one column),
720px (device, draw, the four-cell spec strip), 640px (topbar padding, hero padding, the
bench's three rails), 560px (the comparison record, the next-work list, and the column keys
on a touch screen), and 380px (the drawing pad stacks: its pad, tile and gap need 306px,
and a 320px screen has 272). Rhythm is a loose 4/8/14/20/26px scale; sections at 52px. Anchor
targets carry `scroll-margin-top: 78px` to clear the sticky topbar.

On a narrow screen an instrument is ordered for the thumb that operates it. A finger covers
whatever is below the control it is dragging, so the bench puts its accuracy and meter
*above* its sliders, and puts the verdict — which grows and shrinks by a line or three as
it updates — *below* them, where a reflow cannot move a slider under the finger. The array
it corrupts comes last, because it is looked at rather than operated.

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
a `2px solid var(--accent)` outline applied through `:focus-visible` on every interactive
element without exception, at a 2–4px offset — 0 on a range input on a touch screen, whose
enlarged box would otherwise put the ring through its label. Controls are drawn as *rules
and handles*: a range input is a 1px track with an 11×16px square running along it — a
scale with a marker on it — rather than a pill with a bead in it. Canvas geometry follows
the same logic: array cells are drawn with no gap between rows, because a crossbar is a
continuous sheet of wiring and separating every cell into its own tile reads as a
spreadsheet.

**The Hit-Area Rule.** A control is drawn at the size its meaning needs and hit at the size
a finger needs, and those are different numbers. On any device that can be touched
(`any-pointer: coarse`, so a touchscreen laptop counts) every hit area grows to 44px and no
drawing changes: tool buttons and the topbar's pills gain an invisible `::after` margin, a
range input grows its own box around a track that stays one pixel thick and centred, and
the contents list's rows gain height. The one control that visibly grows is the column key,
because ten of them sit 4px apart and an invisible margin would land on the neighbour.

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
  On a touch screen the key itself is 44×44px, and below 560px the ten become two rows of
  five across the full width.
- **Touch:** every other button keeps its drawing and gains an invisible 44px hit area
  through `::after` (the Hit-Area Rule, under Shapes).
- **Device:** instrument 01's diagram is itself a `<button>`, drawn as the diagram — no
  border, no ground — whose track rule goes teal on hover. Pressed, it steps the device to
  its next state and says which in a polite status ("Wall at position 3 of 6.").

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
- **Touch:** the input's own box grows to 44px around the unchanged track; the label and
  value close up to meet it, and the focus ring hugs the box at 0 offset.
- **Caret:** `caret-color: var(--accent)` on every input, button, select and textarea.
- **Spoken value:** every range input carries `aria-valuetext` written from the same label
  as its `<output>`, units spelled out and the bracket appended ("100 ohms, last that
  holds"). The input's own value is a rung index, and without this a screen reader says "5".
- **Forced colours:** track and handle are drawn from backgrounds, which Windows high
  contrast replaces; there they are redrawn in `CanvasText` and `Highlight`. Keys that are
  their colour — the legend swatches, the bench's track marks — opt out of the forcing.

### Navigation
Monospace .75rem pills in a sticky, blurred topbar over an 82% page-ground mix with a
hairline bottom border. Links are muted and borderless at rest; hover tints them
`--accent-soft`; only `aria-current="page"` gets teal ink plus a 45% teal border. The brand
is monospace dim ink with a teal-ink wordmark and a descriptive tail that disappears below
900px. The theme toggle sits at the right as a pill with a drawn SVG mark and the word
"theme", and persists its choice to `localStorage` under `spinn-theme`.
Its accessible name says what a press will do ("Switch to dark theme"). It needs a script,
so without one it is not drawn; the saved theme is applied in `<head>`, before the first
paint, which is also what marks the page as scripted. Ahead of the bar, the first focusable
element is a **skip link** — "Skip to content", a mono label on `--surface` with a hairline
and the focus ring — held above the viewport until it has focus.

### The Instrument Panel (signature)
The page's structural unit. `.inst` is a 1px top rule and 20px of padding; `.inst-h` is a
baseline-aligned row holding `.inst-t` (mono .75rem uppercase, teal ink, 600) at the left and
`.inst-n` (mono muted) at the right; `.inst-d` is a dim-ink caption capped at 60ch; the
instrument follows at full available width. Five of these carry the whole page. No panel has
a background, a border box or a radius.

An instrument is never a silent gap. Without a script, each host is followed by a
`<noscript>` caption saying what would be there, and the budget's gives its recorded brackets
as a ruled list, which a test holds to `data.js`. A widget that throws while mounting leaves
a Caption in amber ink in its host, naming the error — amber being the page's mark for an
absence. A written state never relies on colour: the device's accuracy says "below the pass
mark of 0.6978" as well as turning amber.

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

### The Drawing Pad
A 168px `--surface` box at a 10px radius, its 24 cells ruled into the six the array sees. It
takes a keyboard as well as a pointer: arrow keys move a pen a cell at a time, a whole ruled
square with Shift; Space puts it down or lifts it; Delete clears. The pen is drawn — a teal ring
the size of the brush, with a dot in it when down — only while the pad has keyboard focus, and
the key hint shows only then as well; a screen reader has the hint as the pad's description.
The verdict is spoken once the pad has been still for 700ms, because every dab reclassifies;
the visible line under the numeral is not live.

## Do's and Don'ts

### Do:
- **Do** put every colour in a CSS custom property in the four theme blocks (`:root`, the
  `screen and (prefers-color-scheme:dark)` query, and the two `data-theme` overrides — both
  dark blocks screen-only, under the Paper Rule), and let both
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
  and leaving autoplay off. A loop that is off screen stops drawing until it is back.
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
