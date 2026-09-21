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
    + ".ld-h{font-family:var(--mono);font-size:.75rem;letter-spacing:.16em;"
    + "text-transform:uppercase;color:var(--accent-ink);margin:0 0 2px;font-weight:600;}"
    + ".ld-binds{color:var(--ink);}"
    + ".ld-s{font-size:.8125rem;color:var(--ink-dim);margin:0 0 12px;line-height:1.45;}"
    + ".ld-b{font-family:var(--mono);font-size:.8125rem;color:var(--muted);margin:10px 0 0;"
    + "line-height:1.6;}"
    + ".ld-b b{color:var(--ink);font-weight:600;}"
    + ".ld-b .hold{color:var(--good-ink);}"
    + ".ld-b .fail{color:var(--bad-ink);}";

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
      // The row's ladder is round numbers and the size sweep's is 2*10^(k/3),
      // whose rungs have seventeen significant figures. One formatter for both.
      fmt: function (v) { return V.ohms(v); },
      bits: null,
      unit: "Ω per segment",
    },
  ];

  /**
   * The solved counterpart of a first-order ladder, where the data has one.
   *
   * Only source 3 has two models, and only the size page's module carries the
   * solved one -- the index's `data.js` does not, because the recorded row and
   * every number on that page are first order. So this returns null there, and the
   * panel draws exactly what it drew before.
   *
   * The rungs are checked rather than assumed to line up: the two series are
   * recorded on the same ladder by `run_size_sweep.m`, and a panel that drew one
   * model's accuracy at another model's magnitudes would look perfectly reasonable.
   */
  function solvedSeries(model, entry, panel) {
    if (panel.key !== "wire") return null;
    var ex = model.budget && model.budget.exact;
    if (!ex || ex.magnitudes.length !== entry.magnitudes.length) return null;
    for (var i = 0; i < ex.magnitudes.length; i++) {
      if (ex.magnitudes[i] !== entry.magnitudes[i]) return null;
    }
    return {
      exactAcc: ex.exactAcc,
      exactHolds: ex.exactAcc.map(function (a) { return a >= model.threshold; }),
      lastHolding: ex.lastHolding,
      firstFailing: ex.firstFailing,
    };
  }


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
    // The top of the scale follows the array's own ideal rather than sitting at
    // the 0.78 that suited a 36-row machine. At 676 rows the ideal is 0.9070 and a
    // fixed 0.78 would draw the whole curve off the top of the panel.
    var yLo = 0, yHi = Math.max(0.5, Math.ceil((model.ideal + 0.05) * 20) / 20);
    var yOf = function (a) { return padT + ph - ((a - yLo) / (yHi - yLo)) * ph; };

    // axes
    ctx.strokeStyle = c.border;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padL - 0.5, padT);
    ctx.lineTo(padL - 0.5, padT + ph + 0.5);
    ctx.lineTo(padL + pw, padT + ph + 0.5);
    ctx.stroke();

    ctx.font = V.font();
    ctx.fillStyle = c.muted;
    ctx.textAlign = "right";
    [0, 0.25, 0.5, 0.75, 1].filter(function (a) { return a <= yHi; })
      .forEach(function (a) {
        ctx.fillText(a.toFixed(2), padL - 6, yOf(a) + 3);
      });

    // The pass mark, and the ideal it is 95% of. Both are labelled: unlabelled,
    // they are two horizontal rules four hundredths apart and a reader has no way
    // to tell which one a curve had to stay above.
    ctx.font = V.font();
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

    // Source 3, where the sweep recorded both models on the same rungs: the
    // network solved, and the same network expanded to first order. Drawn together
    // and never one without the other -- they disagree by a factor that matters,
    // and the recorded row and the main page are the first-order one.
    var solved = solvedSeries(model, entry, panel);
    if (solved) {
      ctx.strokeStyle = c.accent2;
      ctx.lineWidth = 1.3;
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      for (i = 0; i < n; i++) {
        var fx = xOf(i), fy = yOf(mean[i]);
        if (i === 0) ctx.moveTo(fx, fy); else ctx.lineTo(fx, fy);
      }
      ctx.stroke();
      ctx.setLineDash([]);
      mean = solved.exactAcc;
    }

    ctx.strokeStyle = c.ink;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    for (i = 0; i < n; i++) {
      var x = xOf(i), y = yOf(mean[i]);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // The dots, the edge marks and the labels all follow the solid curve, so where
    // both models are drawn they are the solved one's -- which is the model the
    // bracket under the panel then quotes first.
    var holdsAt = solved ? solved.exactHolds : entry.holds;
    var lastHolding = solved ? solved.lastHolding : entry.lastHolding;
    var firstFailing = solved ? solved.firstFailing : entry.firstFailing;

    for (i = 0; i < n; i++) {
      var holds = holdsAt[i];
      var isEdge = mags[i] === lastHolding || mags[i] === firstFailing;
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
    ctx.font = V.font();
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

    var hold = mags.indexOf(lastHolding), fail = mags.indexOf(firstFailing);
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
      + lastHolding + " and fails at " + firstFailing + " " + panel.unit
      + (solved
        ? ", with the wire network solved. Expanded to first order the same array "
          + "holds at " + entry.lastHolding + " and fails at " + entry.firstFailing + "."
        : "."));
  }

  /**
   * `opts.data` is the generated module to run over; the default is the one the
   * index page carries. The size page passes a different array on every change, so
   * everything below reads the model rather than a constant, and `destroy` gives
   * back the observers -- an instrument mounted five times leaves five of them
   * otherwise, each holding a detached canvas.
   */
  function mount(el, opts) {
    P.injectStyle("spinn-ladder-style", CSS);
    var model = C.load((opts && opts.data) || window.SpinnData);
    var grid = P.el("div", "ld");
    var made = [];

    // The source that binds is the one whose holding edge needs the most bits, and
    // its panel says so. The section heading promised "one binds" and no panel said
    // which. IR drop has no bit depth, so it is not in the running; the prose says
    // why it does not bind at this size.
    var need = PANELS.map(function (p) {
      return p.bits ? p.bits(model.budget[p.key].lastHolding) : -Infinity;
    });
    var binding = need.indexOf(Math.max.apply(null, need));

    PANELS.forEach(function (panel, i) {
      var entry = model.budget[panel.key];
      var box = P.el("div", "ld-p",
        '<h4 class="ld-h">' + panel.head
        + (i === binding ? ' <span class="ld-binds">&middot; binds</span>' : "") + "</h4>"
        + '<p class="ld-s">' + panel.sub + "</p>");
      var canvas = document.createElement("canvas");
      canvas.setAttribute("role", "img");
      box.appendChild(canvas);

      var solved = solvedSeries(model, entry, panel);
      var quoted = solved || entry;
      var holdBits = panel.bits ? panel.bits(entry.lastHolding) : null;
      var failBits = panel.bits ? panel.bits(entry.firstFailing) : null;
      box.appendChild(P.el("p", "ld-b",
        '<span class="hold">holds</span> at <b>' + panel.fmt(quoted.lastHolding)
        + "</b> &nbsp;·&nbsp; " + '<span class="fail">fails</span> at <b>'
        + panel.fmt(quoted.firstFailing) + "</b><br>"
        + (panel.bits
          ? "= <b>" + holdBits.toFixed(2) + " bits</b> held, "
            + failBits.toFixed(2) + " failed"
          : solved
            // Both, always: the solid curve is the network and the dashed one is
            // the first-order expansion the recorded row was measured with.
            ? "solved &mdash; first order holds at <b>" + panel.fmt(entry.lastHolding)
              + "</b>, fails at <b>" + panel.fmt(entry.firstFailing) + "</b>"
            : "not a bit depth &mdash; a systematic, not a spread")));

      grid.appendChild(box);
      made.push({ canvas: canvas, entry: entry, panel: panel });
    });

    el.appendChild(grid);

    function redraw() {
      made.forEach(function (m) { drawPanel(m.canvas, model, m.entry, m.panel); });
    }
    var stopWidth = P.onWidthChange(el, redraw);
    var stopTheme = P.onThemeChange(redraw);
    redraw();

    return {
      destroy: function () {
        stopWidth();
        stopTheme();
        el.innerHTML = "";
      },
    };
  }

  if (typeof window !== "undefined") window.SpinnLadder = { mount: mount };
})();
