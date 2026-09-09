"""Build the spinn site.

One page today. The generator is sized for several, because that is where this is
going and because the mechanisms that make several pages cheap -- navigation
generated from :data:`PAGES`, an in-page index derived from the markup, link
tokens resolved once at the end -- are the same mechanisms that make one page
correct.

  site/index.html            the page
  site/_artifact_body.html   body-only variant for publishing as an Artifact,
                             which supplies its own <head>/<body> and has no
                             sibling files, so its links must be absolute

Everything is inlined: the pages make no external requests, so they are CSP-safe,
offline, theme-aware and openable from ``file://``.

This file is a trimmed extraction of photonn's ``apps/build_site.py``, which is
1192 lines built for five pages, a figure pipeline, a MathML compiler and nine
widgets. What was dropped, and where each block can be recovered from, is listed
in ``docs/history.md``. The rule applied throughout: a file earns its place by
what this repo needs, never by what photonn had.

Run: python -m apps.build_site
"""
from __future__ import annotations

import html as _html
import json
import os
import re
from typing import NamedTuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(REPO, "site")
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
PAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")

#: Where the site deploys. Only the Artifact variant needs it: it is a single
#: standalone body with no sibling pages, so its links must be absolute.
SITE_URL = "https://roosado.github.io/spinn/"


class Page(NamedTuple):
    """One page of the site, and everything the chrome needs to know about it."""

    key: str      # link token (@@HREF_key@@) and the stem of the filename
    file: str     # name written into site/
    nav: str      # topbar label
    title: str    # <title>
    head: str     # human name, used by the "next" hand-off card
    desc: str     # <meta name="description">
    blurb: str    # one sentence on the hand-off card
    #: Host container ids this page carries, in document order.
    #:
    #: Declared rather than inferred so the two can be checked against each other.
    #: ``mount_queue.js`` deliberately skips a container it cannot find, so a
    #: mistyped id gives a page that silently lacks a widget and passes every test.
    widgets: tuple = ()


#: Reading order. One page, so the topbar has one entry and the sequential
#: hand-off has nowhere to go -- see :func:`_hand_off`.
PAGES = (
    Page(
        "index", "index.html", "The machine",
        "spinn &middot; a neural network made of magnets",
        "A neural network made of magnets",
        "A weight is the magnetic state of a device and the sum is performed by "
        "Kirchhoff's law on a wire. How precisely would such a thing have to be built?",
        "A weight is a magnetic state; the sum is performed by a wire.",
        widgets=("heroMachine", "deviceExplorer", "wireColumn",
                 "errorBench", "budgetLadder", "drawPad"),
    ),
)

PAGE_BY_KEY = {p.key: p for p in PAGES}


CSS = r"""
:root{
  color-scheme: light dark;
  --bg:#f4f7fb; --surface:#ffffff; --surface-2:#eef2f8;
  --border:#d8e0ec; --ink:#141b26; --ink-dim:#3f4c60; --muted:#64707f;
  --accent:#0f9e8f; --accent-2:#c9701f; --good:#2f8f52; --bad:#c14a34;
  --accent-soft:rgba(15,158,143,.10);
  /* Text variants. The fill values above are the identity and stay; these carry
     type, because the same teal cannot be both a 1px rule and legible 12px copy on
     a near-white ground.

     Measured on the ground each one actually sits on, not on --bg alone: several of
     these labels sit on an 8-10% wash of their own hue (--accent-soft behind a
     current-state label, the .hole chip behind UNSOURCED), which lifts the
     background and costs about half a point of contrast. On the tint: 4.99 and
     4.85. On plain --bg: 5.56, 5.29 and 4.97. */
  --accent-ink:#0a7064; --accent-2-ink:#9c5411; --good-ink:#237a41;
  --bad-ink:#ba4530;
  --rule-gradient:linear-gradient(90deg,#39d1a0,#4fc6e6,#f2c14e,#ef7d5a,#c05aa8);
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,"Times New Roman",serif;
  --sans:ui-sans-serif,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,"Cascadia Code","SF Mono",Consolas,"Liberation Mono",Menlo,monospace;
  --measure:68ch;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#0a0d12; --surface:#111826; --surface-2:#0e131d;
    --border:#243149; --ink:#e8edf4; --ink-dim:#b7c2d2; --muted:#7787a0;
    --accent:#2ec9b8; --accent-2:#f2994a; --good:#57c07a; --bad:#e0705f;
    --accent-soft:rgba(46,201,184,.14);
    /* Dark clears the floor on the fill values themselves (5.34 / 9.42 / 8.74),
       so the text variants are the same colour rather than a second palette. */
    --accent-ink:#2ec9b8; --accent-2-ink:#f2994a; --good-ink:#57c07a;
    --bad-ink:#e0705f;
  }
}
:root[data-theme="light"]{
  --bg:#f4f7fb; --surface:#ffffff; --surface-2:#eef2f8;
  --border:#d8e0ec; --ink:#141b26; --ink-dim:#3f4c60; --muted:#64707f;
  --accent:#0f9e8f; --accent-2:#c9701f; --good:#2f8f52; --bad:#c14a34; --accent-soft:rgba(15,158,143,.10);
  --accent-ink:#0a7064; --accent-2-ink:#9c5411; --good-ink:#237a41;
  --bad-ink:#ba4530;
}
:root[data-theme="dark"]{
  --bg:#0a0d12; --surface:#111826; --surface-2:#0e131d;
  --border:#243149; --ink:#e8edf4; --ink-dim:#b7c2d2; --muted:#7787a0;
  --accent:#2ec9b8; --accent-2:#f2994a; --good:#57c07a; --bad:#e0705f; --accent-soft:rgba(46,201,184,.14);
  --accent-ink:#2ec9b8; --accent-2-ink:#f2994a; --good-ink:#57c07a; --bad-ink:#e0705f;
}

*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:var(--sans);font-size:17px;line-height:1.65;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}
.topline{height:3px;background:var(--rule-gradient);}

.topbar{position:sticky;top:0;z-index:20;backdrop-filter:blur(8px);
  background:color-mix(in srgb,var(--bg) 82%,transparent);
  border-bottom:1px solid var(--border);}
.topbar-in{max-width:1120px;margin:0 auto;padding:9px 24px;
  display:flex;align-items:center;justify-content:space-between;gap:6px 16px;flex-wrap:wrap;}
.brand{font-family:var(--mono);font-size:.82rem;letter-spacing:.02em;color:var(--ink-dim);}
.brand b{color:var(--accent-ink);font-weight:600;}
.theme-toggle{font-family:var(--mono);font-size:.75rem;letter-spacing:.04em;
  background:transparent;border:1px solid var(--border);color:var(--muted);
  border-radius:999px;padding:5px 13px;cursor:pointer;transition:color .15s,border-color .15s;
  display:inline-flex;align-items:center;gap:6px;line-height:1;}
.theme-toggle .tm{flex:none;}
.theme-toggle:hover{color:var(--ink);border-color:var(--accent);}
.theme-toggle:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
.topbar-right{display:flex;align-items:center;gap:6px 10px;flex-wrap:wrap;}
/* The nav is quieter than a row of pills: only the page you are on is drawn as
   one. Sized for several pages sharing a row, which is where this is going. */
.topbar-nav{display:flex;align-items:center;gap:2px;flex-wrap:wrap;}
.topbar-nav a{font-family:var(--mono);font-size:.75rem;letter-spacing:.03em;text-decoration:none;
  color:var(--muted);border:1px solid transparent;border-radius:999px;padding:5px 11px;
  white-space:nowrap;transition:color .15s,background .15s,border-color .15s;}
.topbar-nav a:hover{color:var(--ink);background:var(--accent-soft);}
.topbar-nav a[aria-current="page"]{color:var(--accent-ink);background:var(--accent-soft);
  border-color:color-mix(in srgb,var(--accent) 45%,transparent);}
.topbar-nav a:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
@media (max-width:900px){.brand span.brand-tail{display:none;}}
@media (max-width:640px){.topbar-nav a{padding:5px 8px;font-size:.75rem;}}

/* sequential hand-off at the foot of every page */
.pagenext{display:block;text-decoration:none;background:var(--surface);
  border:1px solid var(--border);border-radius:12px;
  padding:19px 22px;margin:46px 0 6px;transition:background .15s,border-color .15s;}
.pagenext:hover{background:var(--surface-2);border-color:var(--accent);}
.pagenext:focus-visible{outline:2px solid var(--accent);outline-offset:3px;}
.pagenext .k{display:block;font-family:var(--mono);font-size:.75rem;letter-spacing:.18em;
  text-transform:uppercase;color:var(--muted);}
.pagenext .t{display:block;font-family:var(--serif);font-weight:600;color:var(--ink);
  font-size:clamp(1.12rem,2vw,1.38rem);line-height:1.2;margin:.32rem 0 .28rem;}
.pagenext .b{display:block;color:var(--ink-dim);font-size:.94rem;max-width:64ch;}

/* In-page contents. One element, two presentations: a card in the flow of the page,
   and at >=1500px the same list pinned in the right margin. 1500 is where a 176 px
   rail plus its gap clears the 1120 px wrap on both sides -- narrower than that and
   the content would have to come off centre to make room, which costs more than the
   rail is worth. Below it the card is the whole feature and nothing is missing. */
.toc{background:var(--surface);border:1px solid var(--border);border-radius:12px;
  padding:15px 18px 17px;margin:30px 0 4px;max-width:var(--measure);}
.toc-k{font-family:var(--mono);font-size:.75rem;letter-spacing:.18em;text-transform:uppercase;
  color:var(--muted);margin:0 0 .55rem;}
.toc-list{list-style:none;margin:0;padding:0;}
.toc-list li{margin:1px 0;}
.toc-list a{display:flex;gap:9px;text-decoration:none;color:var(--ink-dim);
  font-size:.88rem;line-height:1.35;border-radius:6px;padding:3px 7px;
  border-left:1px solid transparent;transition:color .15s,background .15s,border-color .15s;}
.toc-list a:hover{color:var(--ink);background:var(--accent-soft);}
.toc-list a:focus-visible{outline:2px solid var(--accent);outline-offset:1px;}
.toc-list a[aria-current="location"]{color:var(--accent-ink);background:var(--accent-soft);
  border-left-color:var(--accent);}
.toc-n{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--accent-ink);
  min-width:1.1em;flex:none;}
.toc-g{margin-top:.5rem;}
.toc-s a{padding-left:18px;}
.toc-g a{font-family:var(--mono);font-size:.75rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted);}
.toc-g a:hover{color:var(--ink);}
@media (min-width:1500px){
  .toc{position:fixed;top:78px;left:calc(50% + 580px);width:176px;margin:0;padding:0 0 0 13px;
    max-height:calc(100vh - 120px);overflow:auto;background:transparent;border:0;
    border-left:1px solid var(--border);border-radius:0;}
  .toc-list a{font-size:.82rem;}
}
/* Anchor jumps have to clear the sticky topbar, which is 42-46 px and taller once
   the nav wraps. */
.phase-head h2[id],.phase-head h3[id],.band-h[id]{scroll-margin-top:78px;}

/* A family of error sources, and what the family is. Used by a page that groups
   its sections; everywhere else a section is a section. */
.band{padding:44px 0 0;}
.band-k{font-family:var(--mono);font-size:.75rem;letter-spacing:.18em;text-transform:uppercase;
  color:var(--muted);margin:0 0 .3rem;}
.band-h{font-family:var(--mono);font-size:1.02rem;font-weight:600;letter-spacing:.06em;
  text-transform:uppercase;color:var(--accent-ink);margin:0;}
.band-b{color:var(--ink-dim);font-size:.95rem;margin:.4rem 0 0;max-width:58ch;}

.wrap{max-width:1120px;margin:0 auto;padding:0 24px;}
.col{max-width:var(--measure);}

/* hero */
.hero{padding:76px 0 30px;}
.hero h1{font-family:var(--serif);font-weight:600;text-wrap:balance;
  font-size:clamp(2.1rem,4.6vw,3.35rem);line-height:1.08;letter-spacing:-.01em;
  margin:.2rem 0 .1rem;}
.hero h1 em{font-style:italic;color:var(--accent-2-ink);}
.hero .underbar{width:132px;height:3px;background:var(--rule-gradient);margin:20px 0 22px;border-radius:2px;}
.standfirst{font-size:1.16rem;color:var(--ink-dim);max-width:60ch;}
.standfirst b{color:var(--ink);font-weight:600;}

.stat-strip{display:flex;flex-wrap:wrap;gap:14px;margin:34px 0 8px;}
.stat{flex:1 1 150px;background:var(--surface);border:1px solid var(--border);
  border-radius:12px;padding:15px 17px;}
.stat .v{font-family:var(--mono);font-size:1.5rem;font-weight:600;color:var(--ink);
  font-variant-numeric:tabular-nums;display:block;letter-spacing:-.01em;}
.stat .v small{font-size:.9rem;color:var(--muted);font-weight:500;}
.stat .l{font-size:.8rem;color:var(--muted);display:block;margin-top:3px;line-height:1.35;}

/* phase sections */
.phase{padding:52px 0;border-top:1px solid var(--border);}
.phase-head{display:flex;gap:20px;align-items:flex-start;margin-bottom:10px;}
.ph-num{font-family:var(--mono);font-size:.95rem;font-weight:600;color:var(--accent-ink);
  border:1px solid var(--border);border-radius:9px;padding:7px 11px;line-height:1;
  background:var(--accent-soft);white-space:nowrap;margin-top:4px;}
.ph-num.next{color:var(--muted);background:transparent;border-style:dashed;}
.phase-head h2,.phase-head h3{font-family:var(--serif);font-weight:600;text-wrap:balance;
  font-size:clamp(1.55rem,2.8vw,2.05rem);line-height:1.14;margin:.1rem 0 0;}
.prose{color:var(--ink-dim);}
.prose p{margin:.85rem 0;max-width:var(--measure);}
.prose strong{color:var(--ink);font-weight:600;}
.sub-h{font-family:var(--serif);font-weight:600;color:var(--ink);
  font-size:clamp(1.15rem,2vw,1.42rem);line-height:1.2;margin:2.1rem 0 .2rem;}
.q{font-family:var(--mono);font-size:.92em;background:var(--surface-2);
  border:1px solid var(--border);border-radius:5px;padding:.05em .38em;color:var(--ink);
  white-space:nowrap;}
/* Mathematics is MathML, rendered by the browser itself. Inline expressions sit in
   the run of the sentence; display ones get their own centred line and a rule-free
   band so a long operator product is not competing with the prose around it.

   Identifier styling is left to the browser on purpose: MathML already italicises a
   single-letter <mi> and leaves a multi-letter one upright, which is exactly the
   convention wanted here (M is a matrix, exp is a function name).

   NEVER set `display` on a <math> element. MathML lays out as `display: math` (or
   `block math`), and overriding it with plain `block` drops the element back into CSS
   block layout, which puts every child on its own line -- a nine-term operator product
   becomes nine stacked rows. The scroll container therefore lives on a wrapper. */
math{font-size:1.06em;color:var(--ink);}
.eq{margin:1.15rem 0;text-align:center;overflow-x:auto;overflow-y:hidden;max-width:100%;
  padding:.1rem 0;}
.eq math{font-size:1.2em;}
a.link{color:var(--accent-ink);text-decoration:none;border-bottom:1px solid color-mix(in srgb,var(--accent) 40%,transparent);}
a.link:hover{border-bottom-color:var(--accent);}
a.link:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:2px;}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:24px 0;}
.stats .s{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:13px 15px;}
.stats .s .v{font-family:var(--mono);font-size:1.15rem;font-weight:600;color:var(--ink);
  font-variant-numeric:tabular-nums;}
.stats .s .l{font-size:.76rem;color:var(--muted);margin-top:2px;line-height:1.35;}

/* figure plates -- always light, since the figures are light-background */
.plate{background:#fff;border:1px solid var(--border);border-radius:12px;
  padding:12px;margin:26px 0;overflow-x:auto;}
.plate img{display:block;width:100%;height:auto;border-radius:6px;}
.plate figcaption{font-family:var(--sans);font-size:.83rem;color:#5b6675;
  margin-top:10px;padding:0 4px;line-height:1.5;}
.plate figcaption .fign{font-family:var(--mono);color:var(--accent-ink);font-weight:600;
  letter-spacing:.02em;margin-right:.5em;}
.plate-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));
  gap:16px;margin:26px 0;}
.plate-grid .plate{margin:0;}

/* tables -- wide content scrolls inside its own box, never the page */
.tbl-wrap{overflow-x:auto;margin:24px 0;-webkit-overflow-scrolling:touch;}
.tbl{border-collapse:collapse;font-size:.92rem;min-width:min(100%,540px);}
.tbl th,.tbl td{border-bottom:1px solid var(--border);padding:9px 14px 9px 0;
  text-align:left;vertical-align:top;color:var(--ink-dim);}
.tbl th{font-family:var(--mono);font-size:.75rem;letter-spacing:.09em;text-transform:uppercase;
  color:var(--muted);font-weight:600;white-space:nowrap;}
.tbl td strong{color:var(--ink);font-weight:600;}
.tbl tr:last-child td{border-bottom:0;}

/* inline reference list, for the sections sourced from outside this project */
.refs{list-style:none;padding:0;margin:1.6rem 0 0;max-width:var(--measure);
  border-top:1px solid var(--border);padding-top:.9rem;}
.refs li{font-size:.84rem;color:var(--muted);margin:.42rem 0;line-height:1.5;}
.refs li b{font-family:var(--mono);color:var(--accent-ink);font-weight:600;margin-right:.45em;}
.refs a{color:inherit;text-decoration:none;
  border-bottom:1px solid color-mix(in srgb,var(--muted) 40%,transparent);}
.refs a:hover{color:var(--ink);border-bottom-color:var(--accent);}
.refs a:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:2px;}
sup.r{font-family:var(--mono);font-size:.66em;color:var(--accent-ink);font-weight:600;
  padding-left:.12em;}

/* finding callout */
.finding{background:var(--surface-2);border:1px solid var(--border);
  border-radius:10px;padding:18px 20px;margin:26px 0;}
.finding .tag{font-family:var(--mono);font-size:.75rem;letter-spacing:.16em;text-transform:uppercase;
  color:var(--bad-ink);margin:0 0 .4rem;font-weight:600;}
.finding p.body{margin:0;color:var(--ink);}
.finding p.body strong{color:var(--ink);}

/* planned cards */
.planned{opacity:.96;}
.planned .phase-head h2{color:var(--ink-dim);}
.badge-next{font-family:var(--mono);font-size:.75rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted);border:1px dashed var(--border);border-radius:999px;padding:3px 10px;
  display:inline-block;margin-bottom:6px;}

/* footer */
footer{border-top:1px solid var(--border);margin-top:20px;padding:44px 0 70px;}
.foot-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:26px;}
footer h3{font-family:var(--mono);font-size:.75rem;letter-spacing:.16em;text-transform:uppercase;
  color:var(--accent-ink);margin:0 0 .6rem;font-weight:600;}
footer p{margin:.3rem 0;color:var(--ink-dim);font-size:.92rem;max-width:42ch;}
footer .colophon{margin-top:30px;font-family:var(--mono);font-size:.76rem;color:var(--muted);
  border-top:1px solid var(--border);padding-top:18px;}

/* ------------------------------------------------------------------ instruments
   The vocabulary the widgets are drawn in. Two rules hold it together.

   Panels are *ruled*, not carded: a hairline above, a monospace title, and the
   instrument itself. A card inside a card is what a dashboard becomes when nobody
   decides, and on a page whose whole subject is one continuous machine, boxing
   each view of it into its own tile argues the opposite of the content.

   Controls are rules and handles. A range input is a hairline track with a small
   square running along it -- the shape of a scale with a marker on it, which is
   what these controls are, rather than a pill with a bead in it. */

.inst{margin:30px 0 0;border-top:1px solid var(--border);padding-top:20px;}
.inst-h{display:flex;justify-content:space-between;align-items:baseline;
  gap:8px 18px;flex-wrap:wrap;margin:0 0 3px;}
.inst-t{font-family:var(--mono);font-size:.75rem;letter-spacing:.16em;
  text-transform:uppercase;color:var(--accent-ink);font-weight:600;margin:0;}
.inst-n{font-family:var(--mono);font-size:.75rem;color:var(--muted);}
.inst-d{color:var(--ink-dim);font-size:.93rem;margin:.4rem 0 20px;max-width:64ch;}

.sp-field label{display:block;font-family:var(--mono);font-size:.75rem;
  letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin:0 0 10px;}
.sp-field output{display:block;font-family:var(--mono);font-size:.95rem;color:var(--ink);
  font-variant-numeric:tabular-nums;margin-top:9px;letter-spacing:.01em;}
.sp-field input[type="range"]{-webkit-appearance:none;appearance:none;width:100%;
  background:transparent;height:16px;margin:0;cursor:pointer;display:block;}
.sp-field input[type="range"]::-webkit-slider-runnable-track{height:1px;
  background:var(--border);}
.sp-field input[type="range"]::-moz-range-track{height:1px;background:var(--border);}
.sp-field input[type="range"]::-webkit-slider-thumb{-webkit-appearance:none;
  appearance:none;width:11px;height:16px;margin-top:-8px;border-radius:2px;
  background:var(--accent);border:0;transition:transform .12s ease;}
.sp-field input[type="range"]::-moz-range-thumb{width:11px;height:16px;border-radius:2px;
  background:var(--accent);border:0;}
.sp-field input[type="range"]:hover::-webkit-slider-thumb{transform:scaleY(1.18);}
.sp-field input[type="range"]:focus-visible{outline:2px solid var(--accent);
  outline-offset:4px;border-radius:2px;}

/* --------------------------------------------------------------------- the hero
   Not a header with a picture beside it. The left column carries the claim and the
   right column carries the machine making it, and on a phone the machine goes
   first below the headline rather than after the whole argument. */
.machine{display:grid;grid-template-columns:minmax(290px,.85fr) minmax(320px,1.15fr);
  grid-template-areas:"say do" "read do";grid-template-rows:auto 1fr;
  gap:20px 48px;align-items:start;padding:64px 0 18px;}
.machine-say{grid-area:say;min-width:0;}
.machine-do{grid-area:do;min-width:0;}
.machine-read{grid-area:read;min-width:0;}
/* On a phone the machine follows the headline immediately, ahead of the readout
   that describes it: the claim is "watch this thing work", and a reader who has to
   scroll past a paragraph and a number to reach the thing has been told instead. */
@media (max-width:980px){
  .machine{grid-template-columns:1fr;grid-template-rows:none;
    grid-template-areas:"say" "do" "read";gap:24px;padding:44px 0 14px;}
}

/* Four facts, separated by rules rather than boxed into tiles. */
.spec{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--border);
  margin:34px 0 6px;}
.spec>div{padding:15px 22px 15px 0;border-right:1px solid var(--border);min-width:0;}
.spec>div+div{padding-left:22px;}
.spec>div:last-child{border-right:0;}
.spec .v{display:block;font-family:var(--mono);font-size:clamp(1.05rem,2vw,1.42rem);
  font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums;letter-spacing:-.01em;}
.spec .l{display:block;font-size:.78rem;color:var(--muted);margin-top:4px;line-height:1.4;}
@media (max-width:720px){
  .spec{grid-template-columns:1fr 1fr;}
  .spec>div{border-bottom:1px solid var(--border);}
  .spec>div:nth-child(2n){border-right:0;}
  .spec>div:nth-last-child(-n+2){border-bottom:0;}
}

/* An unsourced value is drawn as a hole, not as a value. */
.q.hole{color:var(--accent-2-ink);border-color:color-mix(in srgb,var(--accent-2) 40%,transparent);
  background:color-mix(in srgb,var(--accent-2) 8%,transparent);}

/* The comparison row, which is the deliverable. Given its own presentation rather
   than sharing .tbl: it is a two-column record, read down, not a data table. */
.row-rec{border-top:1px solid var(--border);margin:24px 0 0;max-width:var(--measure);}
.row-rec>div{display:grid;grid-template-columns:minmax(130px,.5fr) 1fr;gap:6px 22px;
  padding:11px 0;border-bottom:1px solid var(--border);}
.row-rec dt,.row-rec .k{font-family:var(--mono);font-size:.75rem;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted);margin:0;padding-top:.18em;}
.row-rec dd,.row-rec .v{margin:0;color:var(--ink-dim);font-size:.95rem;line-height:1.5;}
.row-rec .v b{color:var(--ink);font-weight:600;font-family:var(--mono);
  font-variant-numeric:tabular-nums;}
@media (max-width:560px){.row-rec>div{grid-template-columns:1fr;gap:2px;}}

/* What is next: a list of open work, ruled like everything else. */
.next-list{list-style:none;padding:0;margin:20px 0 0;max-width:var(--measure);
  border-top:1px solid var(--border);}
.next-list li{padding:14px 0;border-bottom:1px solid var(--border);
  display:grid;grid-template-columns:minmax(150px,.44fr) 1fr;gap:4px 22px;}
.next-list b{font-family:var(--mono);font-size:.78rem;color:var(--ink);font-weight:600;}
.next-list span{color:var(--ink-dim);font-size:.92rem;line-height:1.5;}
@media (max-width:560px){.next-list li{grid-template-columns:1fr;}}

/* ------------------------------------------------------- surfaces we did not draw
   Selection, caret, focus and scrollbars ship with defaults that belong to no
   design system. They are part of the page. */
::selection{background:color-mix(in srgb,var(--accent) 24%,transparent);color:var(--ink);}
:root{scrollbar-color:var(--border) transparent;scrollbar-width:thin;}
::-webkit-scrollbar{width:11px;height:11px;}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:6px;
  border:3px solid transparent;background-clip:padding-box;}
::-webkit-scrollbar-thumb:hover{background:var(--muted);background-clip:padding-box;
  border:3px solid transparent;}
::-webkit-scrollbar-track{background:transparent;}
input,button,select,textarea{caret-color:var(--accent);font:inherit;}

/* motion */
.reveal{opacity:0;transform:translateY(14px);transition:opacity .6s ease,transform .6s ease;}
.reveal.in{opacity:1;transform:none;}
@media (prefers-reduced-motion:reduce){.reveal{opacity:1;transform:none;transition:none;}}

@media (max-width:640px){
  .phase-head{gap:13px;}
  .hero{padding:52px 0 22px;}
}
"""

# ---------------------------------------------------------------------- navigation
# Every link between pages is written as @@HREF_<key>@@ and resolved once, at the
# end of render(). That is what lets the Artifact -- a lone body with no sibling
# files -- carry absolute URLs while the deployed site carries relative ones,
# without either variant knowing which pages exist.


def href(key: str, absolute: bool = False) -> str:
    """Return the URL of page ``key``, relative to the site or absolute."""
    page = PAGE_BY_KEY[key]
    if absolute:
        return SITE_URL if key == "index" else SITE_URL + page.file
    return "./" if key == "index" else page.file


def resolve_links(html: str, absolute: bool = False) -> str:
    """Substitute every ``@@HREF_<key>@@`` token in ``html``."""
    for page in PAGES:
        html = html.replace(f"@@HREF_{page.key}@@", href(page.key, absolute))
    return html


#: The theme control's mark. Drawn rather than borrowed from Unicode: a glyph
#: standing in for an icon renders at whatever weight the reader's fallback font
#: happens to have, beside a monospace label at 0.74rem, and half the time it is
#: not the same weight twice.
THEME_MARK = (
    '<svg class="tm" viewBox="0 0 16 16" width="11" height="11" aria-hidden="true" '
    'focusable="false"><circle cx="8" cy="8" r="6.3" fill="none" stroke="currentColor" '
    'stroke-width="1.4"/><path d="M8 1.7a6.3 6.3 0 0 0 0 12.6z" fill="currentColor"/>'
    "</svg>"
)


def topbar(current: str) -> str:
    """Return the shared page chrome, with ``current`` marked as the live page."""
    parts = []
    for p in PAGES:
        mark = ' aria-current="page"' if p.key == current else ""
        parts.append(f'<a href="@@HREF_{p.key}@@"{mark}>{p.nav}</a>')
    links = "".join(parts)
    return (
        '<header class="topbar">\n'
        '  <div class="topbar-in">\n'
        '    <span class="brand"><b>spinn</b><span class="brand-tail">'
        " &middot; a device-tolerance study of spintronic neural networks</span></span>\n"
        '    <div class="topbar-right">\n'
        f'      <nav class="topbar-nav" aria-label="Sections">{links}</nav>\n'
        '      <button class="theme-toggle" id="themeToggle" aria-label="Toggle colour theme">'
        f"{THEME_MARK} theme</button>\n"
        "    </div>\n"
        "  </div>\n"
        "</header>"
    )


def _hand_off(key: str):
    """``(next key, kicker)`` for the page after ``key``, or ``None`` if there is none.

    PAGES is the reading order and drives both the topbar and this. photonn wraps
    the last page back to the first, which is right for a five-page reading order
    and wrong for a one-page site: the card would invite the reader to go where
    they already are. Until there is a second page, there is no hand-off.
    """
    keys = [p.key for p in PAGES]
    if len(keys) < 2:
        return None
    i = keys.index(key)
    if i == len(keys) - 1:
        return keys[0], "Back to the start"
    return keys[i + 1], "Next"


def next_link(hand_off) -> str:
    """Return the hand-off card that closes a page, or nothing when there is none."""
    if hand_off is None:
        return ""
    key, kicker = hand_off
    page = PAGE_BY_KEY[key]
    return (
        f'<a class="pagenext reveal" href="@@HREF_{key}@@">'
        f'<span class="k">{kicker}</span>'
        f'<span class="t">{page.head} &rarr;</span>'
        f'<span class="b">{page.blurb}</span></a>'
    )


# ---------------------------------------------------------------- IN-PAGE INDEX
# Section navigation is generated from the markup, never authored twice. Every
# section heading sits inside a `.phase-head`, so one scan finds them all, gives
# each an id derived from its text, and returns the list the contents card is
# rendered from. Adding a
# section therefore adds it to the index, with nothing to remember -- the same
# bargain PAGES makes for the topbar.

#: A section heading, anchored on the ``.phase-head`` block it sits in.
#:
#: This used to match on a ``<p class="eyebrow">`` above the heading, which quietly
#: made a decorative element load bearing: a section that dropped its eyebrow
#: dropped out of the contents card as well. The eyebrow is gone from this site --
#: on the page it was on, six of eight restated the first words of the heading
#: beneath them -- and the anchor is now the markup that actually means "this is a
#: section heading". Anchoring on nothing was tried in between, and put the
#: footer's three ``<h3>`` headings into the card;
#: ``test_the_contents_card_indexes_sections_and_nothing_else`` is that lesson.
#:
#: What the card shows comes from the heading itself through :func:`toc_label`,
#: overridable with ``data-toc``; the number beside it, where a page groups its
#: sections by error source, comes from ``data-num``.
_HEADING = re.compile(
    r'(?P<lead><div class="phase-head">.*?)'
    r'<(?P<tag>h2|h3)(?P<attrs>[^>]*)>(?P<text>.*?)</(?P=tag)>',
    re.S,
)
#: A band heading: the family a run of sections belongs to.
_BAND = re.compile(r'<h2 class="band-h"(?P<attrs>[^>]*)>(?P<text>.*?)</h2>', re.S)
#: An explicit number for the contents card, for a page that groups its sections
#: by error source. An attribute rather than an element: it is a fact about the
#: heading, and the element that used to carry it was a kicker.
_NUM_ATTR = re.compile(r'\s*data-num="([^"]*)"')
_TOC_ATTR = re.compile(r'\s*data-toc="([^"]*)"')


def strip_tags(markup: str) -> str:
    """Plain text of a fragment: inline tags dropped, entities resolved."""
    return _html.unescape(re.sub(r"<[^>]+>", "", markup)).strip()


def slugify(text: str) -> str:
    """A stable id from heading text."""
    slug = re.sub(r"[^a-z0-9]+", "-", strip_tags(text).lower()).strip("-")
    return slug or "section"


def toc_label(text: str) -> str:
    """The short form of a heading, for a 176 px rail.

    Section headings are written as ``Topic: what it does to you`` wherever there is
    a topic to name, so the part before the colon is already the label. Headings with
    no colon are short enough to use whole, and anything that is neither carries an
    explicit ``data-toc``.
    """
    plain = strip_tags(text)
    head = plain.split(":", 1)[0].strip()
    return head if 0 < len(head) < len(plain) else plain


def section_index(body: str):
    """Give every section heading an id; return ``(html, entries)``.

    ``entries`` is in document order, each ``{level, id, label, num}``. ``level`` is
    ``"band"`` for a family heading, and otherwise the heading's own tag -- ``"h2"``
    or ``"h3"`` -- which is what :func:`toc` dispatches on to nest the card by the
    page's outline rather than by sibling order.
    """
    entries, seen = [], {}

    def unique(slug: str) -> str:
        seen[slug] = seen.get(slug, 0) + 1
        return slug if seen[slug] == 1 else f"{slug}-{seen[slug]}"

    def take(text: str, attrs: str, level: str, num=None):
        """Record one entry and return the attribute string its heading should carry."""
        override = _TOC_ATTR.search(attrs)
        label = strip_tags(override.group(1)) if override else toc_label(text)
        numbered = _NUM_ATTR.search(attrs)
        if numbered:
            num = numbered.group(1)
        attrs = _NUM_ATTR.sub("", _TOC_ATTR.sub("", attrs))
        ident = unique(slugify(label))
        entries.append({"level": level, "id": ident, "label": label, "num": num})
        return f' id="{ident}"{attrs}'

    def band(m):
        attrs = take(m.group("text"), m.group("attrs"), "band")
        return f'<h2 class="band-h"{attrs}>{m.group("text")}</h2>'

    def heading(m):
        # `level` is the heading tag, so the card's nesting is the page's own
        # outline: a section written as <h3> belongs to the band above it and is
        # indented under it, and one written as <h2> is not.
        tag = m.group("tag")
        attrs = take(m.group("text"), m.group("attrs"), tag)
        return m.group("lead") + f'<{tag}{attrs}>{m.group("text")}</{tag}>'


    # Bands first: a band heading is an <h2> outside any `.phase-head`, so the two
    # patterns cannot both match the same element, and running bands first keeps the
    # entries in document order for a page that has them.
    body = _BAND.sub(band, body)
    body = _HEADING.sub(heading, body)
    entries.sort(key=lambda e: body.index(f'id="{e["id"]}"'))
    return body, entries


def toc(entries) -> str:
    """Render the contents card. Empty for a page with nothing to index."""
    if not entries:
        return ""
    items = []
    for e in entries:
        cls = {"band": ' class="toc-g"', "h3": ' class="toc-s"'}.get(e["level"], "")
        num = f'<span class="toc-n">{e["num"]}</span>' if e["num"] else ""
        items.append(f'<li{cls}><a href="#{e["id"]}">{num}{e["label"]}</a></li>')
    return (
        # No `reveal` here: this is navigation chrome, like the topbar, not content.
        # `.reveal` starts at opacity 0 and waits for an observer, so a reader
        # landing on a #fragment could arrive at an index they cannot see.
        '<nav class="toc" aria-label="On this page">\n'
        '  <p class="toc-k">On this page</p>\n'
        '  <ol class="toc-list">' + "".join(items) + "</ol>\n"
        "</nav>"
    )


# ---------------------------------------------------------------------- WEB ASSETS
# These three lived in photonn's apps/diffraction_explorer.py, a module built
# around an optical widget that was not copied. They are generic -- inlining an
# asset, and handing a widget to the mount scheduler -- so they are re-homed here
# rather than dragged in with the explorer they happened to sit beside.


def read_web_asset(name: str) -> str:
    """Return the text of an asset under ``apps/web``."""
    with open(os.path.join(WEB_DIR, name), "r", encoding="utf-8") as fh:
        return fh.read()


def mount_queue_bundle() -> str:
    """Return the ``<script>`` holding the page's mount scheduler."""
    return f"<script>\n{read_web_asset('mount_queue.js')}\n</script>\n"


def mount_script(container_id: str, body: str, defer: bool = False) -> str:
    """Wrap widget-mount JavaScript so the page decides when it runs.

    ``body`` is JavaScript that mounts the widget into the local variable ``el``.
    It is handed to ``apps/web/mount_queue.js``, which holds every widget until
    after the first paint and then starts them one at a time -- so a page carrying
    several expensive widgets never blocks the main thread on all of them at once.
    With ``defer``, the widget additionally waits until the reader is approaching
    it. Either way it still starts by itself: nothing here asks for a tap.

    The ``readyState`` check in the fallback matters for nested mounts. A widget
    that schedules another one runs long after DOMContentLoaded, so a fallback that
    only ever added a listener would silently never fire.

    Note the global: ``window.SpinnMount``. photonn's copy of this function names
    ``window.PhotonnMount``, and it sits in a file that was never copied -- so this
    was a rename waiting to be missed, in the one place where missing it is silent.
    """
    ident = json.dumps(container_id)
    opts = ", {defer: true}" if defer else ""
    lines = ["<script>", "  (function () {", "    function boot(el) {"]
    lines += [f"      {line}" for line in body.strip().splitlines()]
    lines += [
        "    }",
        f"    if (window.SpinnMount) window.SpinnMount({ident}, boot{opts});",
        "    else if (document.readyState === 'loading') {",
        f"      window.addEventListener('DOMContentLoaded', function () {{ boot(document.getElementById({ident})); }});",
        "    } else {",
        f"      boot(document.getElementById({ident}));",
        "    }",
        "  })();",
        "</script>",
    ]
    return "\n".join(lines)


def script_tags(*assets: str) -> str:
    """Inline the named ``apps/web`` assets as <script> blocks, in order.

    Order is the argument order, which is the point: where one asset reads another's
    global at module scope, loading them the other way round gives a widget that
    silently falls back to a stand-in rather than one that fails.
    """
    return "\n".join(f"<script>\n{read_web_asset(a)}\n</script>" for a in assets)


# ------------------------------------------------------------------------ WIDGETS
# Every widget on this site runs the real forward pass, against the real trained
# weights and the real frozen test set, both frozen into apps/web/data.js by
# apps/export_web_data.py. That is the expensive choice and it is the only honest
# one: this repository's result is trustworthy because the design half cannot
# quietly flatter the measurement half, and a demonstration that was a cartoon of
# the measurement would spend that credibility on the one page most people read.
#
# Load order is the argument order of `script_tags` and it matters twice: data.js
# and crossbar.js are read at module scope by every widget, and xbar_view.js reads
# plot.js the same way. Getting it wrong gives an undefined global at mount time,
# which in a browser is silent.

#: Shared by every widget, in load order. ``plot.js`` is emitted separately by
#: :func:`_chrome`, ahead of these, as it always was.
WIDGET_CORE = ("data.js", "crossbar.js", "xbar_view.js")


class Widget(NamedTuple):
    """One widget: where it mounts, what it needs, and how it starts."""

    host: str            # container id in the page body
    asset: str           # its module under apps/web
    boot: str            # JavaScript that mounts it into the local ``el``
    defer: bool = True   # hold until the reader is approaching it


#: Declared in document order, which is also the order they are emitted.
WIDGETS = (
    # The hero is the one widget that must not defer: it is the first viewport, and
    # a widget waiting for the reader to approach it has already been walked past.
    Widget("heroMachine", "hero.js",
           "window.SpinnHero.mount(el, document.getElementById('heroReadout'));",
           defer=False),
    Widget("deviceExplorer", "device.js", "window.SpinnDevice.mount(el);"),
    Widget("wireColumn", "wire.js", "window.SpinnWire.mount(el);"),
    Widget("errorBench", "bench.js", "window.SpinnBench.mount(el);"),
    Widget("budgetLadder", "ladder.js", "window.SpinnLadder.mount(el);"),
    Widget("drawPad", "draw.js", "window.SpinnDraw.mount(el);"),
)

WIDGET_BY_HOST = {w.host: w for w in WIDGETS}


def widget_bundle(page: Page) -> str:
    """Every script one page's widgets need, in load order, inlined."""
    if not page.widgets:
        return ""
    used = [WIDGET_BY_HOST[h] for h in page.widgets]
    parts = [script_tags(*(list(WIDGET_CORE) + [w.asset for w in used]))]
    for w in used:
        parts.append(mount_script(w.host, w.boot, defer=w.defer))
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------- BODY
# Page prose lives in apps/pages/*.html, not in this module. photonn learned this
# the expensive way: 1,565 of that file's 2,652 lines were body literals, which is
# why it appeared in 17 of 30 commits. The token vocabulary (@@TOPBAR@@, @@TOC@@,
# @@NEXT@@, @@HREF_*@@, @@PAGE_SCRIPT@@) was already the interface between the
# prose and the generator, so moving the prose across it costs nothing and makes an
# editorial commit legible as one.


def page_body(key: str) -> str:
    """The raw body of one page, before any token is substituted."""
    with open(os.path.join(PAGES_DIR, f"{key}.html"), encoding="utf-8") as fh:
        return fh.read()


# Shared page chrome: the theme toggle (persisted) and the scroll-reveal observer.
PAGE_SCRIPT = r"""<script>
(function(){
  var root=document.documentElement, btn=document.getElementById('themeToggle');
  try{var saved=localStorage.getItem('spinn-theme'); if(saved){root.setAttribute('data-theme',saved);}}catch(e){}
  function cur(){var a=root.getAttribute('data-theme'); if(a) return a;
    return window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';}
  btn.addEventListener('click',function(){var n=cur()==='dark'?'light':'dark';
    root.setAttribute('data-theme',n); try{localStorage.setItem('spinn-theme',n);}catch(e){}});
})();
(function(){
  var els=document.querySelectorAll('.reveal');
  if(!('IntersectionObserver' in window)||window.matchMedia('(prefers-reduced-motion:reduce)').matches){
    els.forEach(function(el){el.classList.add('in');}); return;}
  var io=new IntersectionObserver(function(es){es.forEach(function(e){
    if(e.isIntersecting){e.target.classList.add('in'); io.unobserve(e.target);}});},{rootMargin:'0px 0px -8% 0px'});
  els.forEach(function(el){io.observe(el);});
})();
(function(){
  var links=document.querySelectorAll('.toc-list a[href^="#"]');
  if(!links.length) return;
  var map={},order=[];
  links.forEach(function(a){var id=a.getAttribute('href').slice(1),el=document.getElementById(id);
    if(el){map[id]=a; order.push(el);}});
  if(!order.length) return;
  function mark(){
    var cur=order[0].id;
    order.forEach(function(el){if(el.getBoundingClientRect().top<=90) cur=el.id;});
    for(var k in map){if(k===cur){map[k].setAttribute('aria-current','location');}
      else{map[k].removeAttribute('aria-current');}}
  }
  // A throttled scroll listener, not an IntersectionObserver. "Which section am I
  // reading" is a question about every heading at once, and an observer answers only
  // about the one that crossed -- and answers nothing at all when a click on this
  // card jumps the page straight over the crossing, which is the commonest way this
  // card is used. The reveal observer above cannot be reused either: it unobserves
  // on first sight.
  var queued=false;
  function ping(){if(queued) return; queued=true;
    setTimeout(function(){queued=false; mark();},100);}
  addEventListener('scroll',ping,{passive:true});
  addEventListener('resize',ping,{passive:true});
  addEventListener('hashchange',mark);
  mark();
})();
</script>"""


def _document(body: str, page: Page) -> str:
    """Wrap a rendered body in the shared document shell."""
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="description" content="{page.desc}">\n'
        f"<title>{page.title}</title>"
        "\n<style>\n" + CSS + "\n</style>\n</head>\n<body>\n"
        + body
        + "\n</body>\n</html>\n"
    )


def _chrome(body: str, key: str) -> str:
    """Fill in everything every page shares: nav, hand-off, page script.

    Link tokens are deliberately left in place -- ``resolve_links`` runs last, so
    one rendered body can be emitted twice, once relative and once absolute. The
    in-page index is filled here because it needs the ids :func:`section_index`
    writes into the headings; its links are ``#fragment`` and never page tokens, so
    it is indifferent to that ordering.
    """
    html, entries = section_index(body)
    html = html.replace("@@TOC@@", toc(entries))
    html = html.replace("@@TOPBAR@@", topbar(key))
    html = html.replace("@@NEXT@@", next_link(_hand_off(key)))
    page = PAGE_BY_KEY[key]
    # plot.js goes in the page-script slot, above every widget bundle, so there is
    # exactly one copy per page before any widget reads window.SpinnPlot at module
    # scope. A page with no widgets does not get it at all -- shipping the shared
    # canvas module to a page that draws nothing is paying for nothing.
    plot = script_tags("plot.js") + "\n" if page.widgets else ""
    # The scheduler is inlined before the widgets that call it. A mount script that
    # runs first finds no window.SpinnMount, falls back to DOMContentLoaded, works --
    # and silently gives up the sequencing the scheduler exists to provide.
    html = html.replace(
        "@@PAGE_SCRIPT@@",
        plot + mount_queue_bundle() + widget_bundle(page) + PAGE_SCRIPT)
    return html


def render() -> dict:
    """Return ``{filename: html}`` for every file the site is made of."""
    out = {}

    body = _chrome(page_body("index"), "index")
    out["index.html"] = _document(resolve_links(body), PAGE_BY_KEY["index"])
    # The Artifact is a standalone body with no sibling pages, so its links must be
    # absolute and it supplies no <head> of its own.
    out["_artifact_body.html"] = ("<style>\n" + CSS + "\n</style>\n"
                                  + resolve_links(body, absolute=True))

    return out


def main():
    os.makedirs(SITE, exist_ok=True)
    for name, text in render().items():
        path = os.path.join(SITE, name)
        # newline="\n" so the file written here is byte-for-byte what `render()`
        # returned. Without it Python translates on Windows, the working tree fills
        # with CRLF that .gitattributes normalises straight back out, and the built
        # page cannot be compared against the render that produced it.
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"wrote {path} ({len(text) // 1024} KB)")


if __name__ == "__main__":
    main()
