/*
 * ladder.js -- the measured budget: three sources, three brackets, one pass mark.
 *
 * Unlike every other widget on this page, nothing here is computed in the browser.
 * These are the recorded results of `spinn-hw/run_error_budget.m` -- twenty Monte
 * Carlo realisations per magnitude for the source that has a random draw, seeded
 * by `mc.sweep`'s partitioning so that this platform's table stays comparable with
 * the other one's. The bench above lets a reader move the knobs; this is what the
 * measurement said when it moved them properly.
 *
 * The design decision that matters is what is *not* drawn: there is no fitted
 * crossing point, no interpolated tolerance, and no curve through the points
 * suggesting a value between two magnitudes. `mc.pack` deliberately stores a mean
 * and a standard deviation and no crossing, because the sweep is a ladder of
 * magnitudes and the honest statement is a bracket -- holds here, fails there. So
 * the marks are the measured points, the segments between them are drawn as
 * straight connectors rather than as a model, and the bracket is called out in
 * words underneath.
 *
 * IR drop is on the same axes and deliberately not converted into effective bits.
 * It is a position-dependent systematic, not a spread on a stored value, so
 * log2(range/sigma) has no sigma to take. Forcing it into the unit would make the
 * three panels look more comparable than they are.
 */
(function () {
  "use strict";

  var P = window.SpinnPlot, V = window.SpinnView, C = window.SpinnCrossbar;

  var CSS = ""
    + ".ld{display:grid;grid-template-columns:repeat(3,1fr);gap:26px 30px;}"
    + "@media (max-width:860px){.ld{grid-template-columns:1fr;gap:30px;}}"
    + ".ld-p canvas{display:block;width:100%;}"
    + ".ld-h{font-family:var(--mono);font-size:.75rem;letter-spacing:.14em;"
    + "text-transform:uppercase;color:var(--accent-ink);margin:0 0 2px;font-weight:600;}"
    + ".ld-s{font-size:.86rem;color:var(--ink-dim);margin:0 0 12px;line-height:1.45;}"
    + ".ld-b{font-family:var(--mono);font-size:.76rem;color:var(--muted);margin:10px 0 0;"
    + "line-height:1.6;}"
    + ".ld-b b{color:var(--ink);font-weight:600;}"
    + ".ld-b .hold{color:var(--good-ink);}"
    + ".ld-b .fail{color:var(--bad-ink);}";

  var MONO = 'ui-monospace,"Cascadia Code","SF Mono",Consolas,monospace';

  var PANELS = [
    {
      key: "sigma", head: "1. Conductance variation",
      sub: "Every device misses its programmed state by an independent draw, as a "
        + "fraction of the conductance window.",
      fmt: function (v) { return String(v); },
      bits: function (v) { return -Math.log(v) / Math.LN2; },
      unit: "σ",
    },
    {
      key: "states", head: "2. Resolvable states",
      sub: "A device holds finitely many levels. A pair reaches 2·states − 1 "
        + "effective weights.",
      fmt: function (v) { return String(v); },
      bits: function (v) { return Math.log(2 * v - 1) / Math.LN2; },
      unit: "states",
      reversed: true,
    },
    {
      key: "wire", head: "3. IR drop",
      sub: "The wires are not ideal conductors, so a cell far from both edges is "
        + "starved. This one grows with array size.",
      fmt: function (v) {
        if (v >= 1000000) return (v / 1000000) + "M";
        return v >= 1000 ? (v / 1000) + "k" : String(v);
      },
      bits: null,
      unit: "Ω per segment",
    },
  ];

  function drawPanel(canvas, model, entry, panel) {
    var c = V.ink(document.documentElement);
    var W = Math.max(220, Math.round(canvas.getBoundingClientRect().width || 320));
    var H = 190;
    var ctx = P.fitTo(canvas, W, H).ctx;
    ctx.clearRect(0, 0, W, H);

    var padL = 34, padR = 8, padT = 10, padB = 26;
    var pw = W - padL - padR, ph = H - padT - padB;
    var mags = entry.magnitudes, mean = entry.accMean, sd = entry.accStd;
    var n = mags.length;

    // Magnitudes are a logarithmic ladder, so position is by index rather than by
    // value: the sweep asks about decades, and spacing the marks evenly is the
    // picture of "these are the rungs we climbed", which is what happened.
    var xOf = function (i) { return padL + (n === 1 ? pw / 2 : (i / (n - 1)) * pw); };
    var yLo = 0, yHi = 0.78;
    var yOf = function (a) { return padT + ph - ((a - yLo) / (yHi - yLo)) * ph; };

    // axes
    ctx.strokeStyle = c.border;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padL - 0.5, padT);
    ctx.lineTo(padL - 0.5, padT + ph + 0.5);
    ctx.lineTo(padL + pw, padT + ph + 0.5);
    ctx.stroke();

    ctx.font = "9px " + MONO;
    ctx.fillStyle = c.muted;
    ctx.textAlign = "right";
    [0, 0.25, 0.5, 0.75].forEach(function (a) {
      ctx.fillText(a.toFixed(2), padL - 6, yOf(a) + 3);
    });

    // The pass mark, and the ideal it is 95% of. Both are labelled: unlabelled,
    // they are two horizontal rules four hundredths apart and a reader has no way
    // to tell which one a curve had to stay above.
    ctx.font = "8px " + MONO;
    // One label above its line, one below: the two are 0.037 apart on a 0.78 scale,
    // which is about seven pixels here, so both placed above would sit on top of
    // each other.
    [[model.ideal, c.muted, [3, 3], "IDEAL", -3],
     [model.threshold, c.ink, [], "PASS", 9]].forEach(function (m) {
      var y = yOf(m[0]) + 0.5;
      ctx.strokeStyle = m[1];
      ctx.setLineDash(m[2]);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(padL + pw, y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = m[1];
      ctx.textAlign = "right";
      ctx.fillText(m[3], padL + pw, y + m[4]);
    });

    // spread, where there is one
    var i;
    var hasSpread = sd.some(function (v) { return v > 0; });
    if (hasSpread) {
      ctx.fillStyle = V.mix(c.surface, c.accent, 0.18);
      ctx.beginPath();
      for (i = 0; i < n; i++) ctx.lineTo(xOf(i), yOf(Math.min(yHi, mean[i] + sd[i])));
      for (i = n - 1; i >= 0; i--) ctx.lineTo(xOf(i), yOf(Math.max(0, mean[i] - sd[i])));
      ctx.closePath();
      ctx.fill();
    }

    ctx.strokeStyle = c.ink;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    for (i = 0; i < n; i++) {
      var x = xOf(i), y = yOf(mean[i]);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();

    for (i = 0; i < n; i++) {
      var holds = entry.holds[i];
      var isEdge = mags[i] === entry.lastHolding || mags[i] === entry.firstFailing;
      ctx.fillStyle = holds ? c.accent : c.accent2;
      ctx.beginPath();
      ctx.arc(xOf(i), yOf(mean[i]), isEdge ? 4.2 : 2.4, 0, Math.PI * 2);
      ctx.fill();
      if (isEdge) {
        ctx.strokeStyle = c.surface;
        ctx.lineWidth = 1.4;
        ctx.stroke();
      }
    }

    // x labels: the two bracket rungs always, plus the ends, and nothing else --
    // eleven monospace labels under a 300px panel is a smear. Even four collide:
    // the bracket is by definition two adjacent rungs, and on the sigma ladder
    // "0.035" and "0.05" sit thirty pixels apart. So each label is clamped inside
    // the panel and skipped when it would overlap the one before it, bracket rungs
    // taking precedence over the ends.
    ctx.font = "9px " + MONO;
    ctx.textAlign = "center";
    var placed = [];

    function place(text, at, colour) {
      var half = ctx.measureText(text).width / 2 + 4;
      var x = Math.max(padL + half, Math.min(padL + pw - half, at));
      for (var k = 0; k < placed.length; k++) {
        if (Math.abs(x - placed[k][0]) < half + placed[k][1]) return;
      }
      placed.push([x, half]);
      ctx.fillStyle = colour;
      ctx.fillText(text, x, padT + ph + 15);
    }

    var hold = mags.indexOf(entry.lastHolding), fail = mags.indexOf(entry.firstFailing);
    var holdText = panel.fmt(mags[hold]), failText = panel.fmt(mags[fail]);
    var gap = Math.abs(xOf(fail) - xOf(hold));
    var need = (ctx.measureText(holdText).width + ctx.measureText(failText).width) / 2 + 10;
    if (gap < need) {
      // Adjacent rungs on a narrow panel: one label for the pair rather than
      // dropping the failing edge, which is half of what the bracket says.
      place(holdText + " / " + failText, (xOf(hold) + xOf(fail)) / 2, c.ink);
    } else {
      place(holdText, xOf(hold), c.accentInk);
      place(failText, xOf(fail), c.accent2Ink);
    }
    [0, n - 1].forEach(function (idx) {
      if (idx !== hold && idx !== fail) place(panel.fmt(mags[idx]), xOf(idx), c.muted);
    });
    ctx.textAlign = "left";
    ctx.fillStyle = c.muted;
    ctx.fillText(panel.unit + " →", padL, padT + ph + 25);

    canvas.setAttribute("aria-label", panel.head + ": accuracy holds at "
      + entry.lastHolding + " and fails at " + entry.firstFailing + " "
      + panel.unit + ".");
  }

  function mount(el) {
    P.injectStyle("spinn-ladder-style", CSS);
    var model = C.load(window.SpinnData);
    var grid = P.el("div", "ld");
    var made = [];

    PANELS.forEach(function (panel) {
      var entry = model.budget[panel.key];
      var box = P.el("div", "ld-p",
        '<p class="ld-h">' + panel.head + "</p>"
        + '<p class="ld-s">' + panel.sub + "</p>");
      var canvas = document.createElement("canvas");
      canvas.setAttribute("role", "img");
      box.appendChild(canvas);

      var holdBits = panel.bits ? panel.bits(entry.lastHolding) : null;
      var failBits = panel.bits ? panel.bits(entry.firstFailing) : null;
      box.appendChild(P.el("p", "ld-b",
        '<span class="hold">holds</span> at <b>' + panel.fmt(entry.lastHolding)
        + "</b> &nbsp;·&nbsp; " + '<span class="fail">fails</span> at <b>'
        + panel.fmt(entry.firstFailing) + "</b><br>"
        + (panel.bits
          ? "= <b>" + holdBits.toFixed(2) + " bits</b> held, "
            + failBits.toFixed(2) + " failed"
          : "not a bit depth &mdash; a systematic, not a spread")));

      grid.appendChild(box);
      made.push({ canvas: canvas, entry: entry, panel: panel });
    });

    el.appendChild(grid);

    function redraw() {
      made.forEach(function (m) { drawPanel(m.canvas, model, m.entry, m.panel); });
    }
    P.onWidthChange(el, redraw);
    P.onThemeChange(redraw);
    redraw();
  }

  if (typeof window !== "undefined") window.SpinnLadder = { mount: mount };
})();
