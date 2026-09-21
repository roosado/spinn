/*
 * size.js -- where the wire starves the array, and what the two models disagree about.
 *
 * The one instrument on this page that the main page has no counterpart for. It
 * answers the question the array-size sweep asked: as the array grows, does the
 * wire or the device bind first, and by how much does the first-order model
 * overstate the answer?
 *
 * Recorded numbers lead; the picture is live
 * ------------------------------------------
 * The ladder, the brackets and the pass mark are what `run_size_sweep.m` measured
 * over all 2,000 frozen test digits. The map is solved here, in the browser, from
 * the real trained weights at the chosen size -- the same solve `err.ir_drop_exact`
 * performs, checked against it at 1e-9 by `tests/test_web_size.py`. And the two
 * accuracies under the slider are computed live over the 500-digit sample this page
 * ships, each printed beside the number MATLAB recorded on those same 500 digits.
 *
 * Two models, never one
 * ---------------------
 * `err.ir_drop` expands the drop to first order and overstates it; `err.ir_drop_exact`
 * solves the network. The recorded budget, the published row and the main page are
 * all first order, so both are drawn here and the difference is the point rather
 * than a footnote. At 36 rows first order puts the edge between 200 and 431 ohm and
 * the network puts it between 431 and 928 -- and the row, on its own coarser ladder,
 * records holding at 100 and failing at 300. Three brackets, one array, all true,
 * and the caption under the chart is what says so.
 *
 * Why the chart is normalised
 * ---------------------------
 * Five sizes have five ideals, from 0.7345 to 0.9070, and each one's pass mark is
 * 95% of its own. Plotted raw, five curves would be judged against five invisible
 * lines. Plotted as a fraction of each array's own ideal, the pass mark is one line
 * that means the same thing for every curve -- which is the definition the sweep
 * used. The raw accuracies are printed under the slider, where precision belongs.
 */
(function () {
  "use strict";

  var P = window.SpinnPlot, V = window.SpinnView, C = window.SpinnCrossbar;

  var CSS = ""
    + ".sz{display:grid;grid-template-columns:minmax(220px,340px) minmax(0,1fr);"
    + "gap:26px 32px;align-items:start;}"
    + "@media (max-width:860px){.sz{grid-template-columns:1fr;}}"
    + ".sz-k{font-family:var(--mono);font-size:.75rem;letter-spacing:.12em;"
    + "text-transform:uppercase;color:var(--muted);margin:0 0 9px;}"
    + ".sz-map{display:block;width:100%;border:1px solid var(--border);border-radius:10px;}"
    + ".sz-key{display:flex;align-items:center;gap:8px;margin:9px 0 0;"
    + "font-family:var(--mono);font-size:.75rem;color:var(--muted);}"
    + ".sz-ramp{flex:1 1 auto;height:8px;border-radius:2px;border:1px solid var(--border);}"
    + ".sz-chart{display:block;width:100%;}"
    + ".sz-note{font-size:.8125rem;color:var(--ink-dim);margin:10px 0 0;line-height:1.5;}"
    + ".sz-note b{color:var(--ink);font-weight:600;}"
    + ".sz-read{font-family:var(--mono);font-size:.8125rem;color:var(--muted);"
    + "margin:12px 0 0;line-height:1.7;font-variant-numeric:tabular-nums;}"
    + ".sz-read b{color:var(--ink);font-weight:600;}"
    + ".sz-read .hold{color:var(--good-ink);}"
    + ".sz-read .fail{color:var(--bad-ink);}"
    + ".sz-facts{display:flex;flex-wrap:wrap;gap:8px 34px;margin:24px 0 0;}"
    + ".sz-facts .v{display:block;font-family:var(--mono);font-size:1.05rem;color:var(--ink);"
    + "font-variant-numeric:tabular-nums;}"
    + ".sz-facts .l{display:block;font-size:.8125rem;color:var(--muted);margin-top:2px;}"
    + ".sz-striph{margin-top:28px;}"
    + ".sz-strip{display:flex;align-items:flex-end;gap:14px;flex-wrap:wrap;margin:0;}"
    + ".sz-strip figure{margin:0;}"
    + ".sz-strip canvas{display:block;border:1px solid var(--border);border-radius:6px;}"
    + ".sz-strip figcaption{font-family:var(--mono);font-size:.75rem;color:var(--muted);"
    + "margin-top:6px;text-align:center;}"
    + ".sz-strip figcaption[aria-current]{color:var(--accent-ink);}";

  var MAP_H = 260;          // the map's drawn height, whatever the row count
  var CHART_H = 220;
  var STRIP_PX = 54;

  /* ----------------------------------------------------------------- the map */

  /**
   * What each cell keeps, drawn as the texture it is.
   *
   * One pixel per device pair, put into an offscreen the size of the array and
   * scaled up with smoothing off -- at 676 rows a cell is a third of a pixel tall
   * on screen and there is nothing to draw but the pattern.
   *
   * The value drawn is the **worse of the pair**: two devices sit at the same place
   * in the array and starve almost equally, so one picture is honest, and taking
   * the worse makes the darkest pixel on the map the number `run_size_sweep.m`
   * records as the worst cell.
   *
   * The ramp is fixed from keeping all of it to keeping none, never auto-scaled to
   * the data: an auto-scaled map would make 2 ohm and 20 ohm look identical, and
   * how different they are is the finding.
   */
  function drawMap(canvas, off, mach, model, c) {
    var rows = model.rows, cols = model.cols;
    off.width = cols;
    off.height = rows;
    var octx = off.getContext("2d");
    var img = octx.createImageData(cols, rows);
    var d = img.data;
    var ground = V.rgb(c.surface2), amber = V.rgb(c.accent2);
    for (var i = 0; i < rows * cols; i++) {
      var keeps = Math.min(mach.fracP[i], mach.fracN[i]);
      // Gamma on the loss, not on what survives: at cited wiring the losses are
      // fractions of a percent, and a linear ramp would draw an array that is
      // fine and an array that is starving as the same blank rectangle.
      var t = Math.pow(Math.max(0, Math.min(1, 1 - keeps)), 0.6);
      d[i * 4] = Math.round(ground[0] + (amber[0] - ground[0]) * t);
      d[i * 4 + 1] = Math.round(ground[1] + (amber[1] - ground[1]) * t);
      d[i * 4 + 2] = Math.round(ground[2] + (amber[2] - ground[2]) * t);
      d[i * 4 + 3] = 255;
    }
    octx.putImageData(img, 0, 0);

    var W = Math.max(120, Math.round(canvas.getBoundingClientRect().width || 300));
    var ctx = P.fitTo(canvas, W, MAP_H).ctx;
    ctx.clearRect(0, 0, W, MAP_H);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(off, 0, 0, cols, rows, 0, 0, W, MAP_H);

    canvas.setAttribute("aria-label",
      "The " + rows + " by " + cols + " array, shaded by how much of its programmed "
      + "conductance each cell keeps at " + mach.wire + " ohms per wire segment. The "
      + "worst cell keeps " + (100 * mach.worstFraction).toFixed(1) + " per cent and the "
      + "mean cell " + (100 * mach.meanFraction).toFixed(1) + " per cent. Drivers are at "
      + "the left edge and sense amplifiers at the top, so the bottom right corner "
      + "starves worst.");
  }

  /* --------------------------------------------------------------- the chart */

  /** Accuracy over each array's own ideal, against the fifteen wire rungs. */
  function drawChart(canvas, grid, rung, c) {
    var bar = window.SpinnSizeBar;
    var grids = bar.grids();
    var W = Math.max(260, Math.round(canvas.getBoundingClientRect().width || 460));
    var ctx = P.fitTo(canvas, W, CHART_H).ctx;
    ctx.clearRect(0, 0, W, CHART_H);

    var padL = 40, padR = 10, padT = 12, padB = 30;
    var pw = W - padL - padR, ph = CHART_H - padT - padB;
    var here = bar.dataFor(grid), ex = here.budget.exact;
    var n = ex.magnitudes.length;

    // By index, as ladder.js draws every ladder on this site: the sweep asked about
    // decades, and evenly spaced marks are the picture of the rungs it climbed.
    var xOf = function (i) { return padL + (i / (n - 1)) * pw; };
    var yLo = 0, yHi = 1.08;
    var yOf = function (v) { return padT + ph - ((v - yLo) / (yHi - yLo)) * ph; };

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
    [0.25, 0.5, 0.75, 1].forEach(function (v) {
      ctx.fillText(v.toFixed(2) + "×", padL - 6, yOf(v) + 3);
    });

    // One pass mark for every curve, which is the whole reason the curves are
    // normalised: 95% of its own ideal is what each size was graded on.
    var yPass = yOf(0.95) + 0.5;
    ctx.strokeStyle = c.ink;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padL, yPass);
    ctx.lineTo(padL + pw, yPass);
    ctx.stroke();
    ctx.fillStyle = c.ink;
    ctx.textAlign = "right";
    ctx.fillText("PASS 95%", padL + pw, yPass - 4);

    // The cited wiring, marked rather than interpolated to: both values are rungs.
    var cited = (window.SpinnSizes.citedWireOhm || []).map(function (ohm) {
      var at = -1;
      for (var i = 0; i < n; i++) {
        if (Math.abs(ex.magnitudes[i] - ohm) < 1e-9 * ohm) at = i;
      }
      return { ohm: ohm, at: at };
    }).filter(function (m) { return m.at >= 0; });
    ctx.setLineDash([2, 3]);
    ctx.strokeStyle = c.border;
    cited.forEach(function (m) {
      ctx.beginPath();
      ctx.moveTo(xOf(m.at) + 0.5, padT);
      ctx.lineTo(xOf(m.at) + 0.5, padT + ph);
      ctx.stroke();
    });
    ctx.setLineDash([]);

    function series(values, ideal, colour, width, dash) {
      ctx.strokeStyle = colour;
      ctx.lineWidth = width;
      ctx.setLineDash(dash || []);
      ctx.beginPath();
      for (var i = 0; i < values.length; i++) {
        var x = xOf(i), y = yOf(values[i] / ideal);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // The other four sizes behind, for shape. Same axes, and legitimately so: every
    // curve is a fraction of its own ideal.
    grids.forEach(function (g) {
      if (g === grid) return;
      var other = bar.dataFor(g);
      series(other.budget.exact.exactAcc, other.idealAccuracy,
             V.mix(c.surface, c.muted, 0.45), 1);
    });

    series(ex.firstOrderAcc, here.idealAccuracy, c.accent2, 1.5, [4, 3]);
    series(ex.exactAcc, here.idealAccuracy, c.ink, 1.8);

    var i;
    for (i = 0; i < n; i++) {
      ctx.fillStyle = ex.exactAcc[i] / here.idealAccuracy >= 0.95 ? c.accent : c.accent2;
      ctx.beginPath();
      ctx.arc(xOf(i), yOf(ex.exactAcc[i] / here.idealAccuracy), 2.4, 0, Math.PI * 2);
      ctx.fill();
    }

    // Where the reader is standing.
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(xOf(rung) + 0.5, padT);
    ctx.lineTo(xOf(rung) + 0.5, padT + ph);
    ctx.stroke();

    ctx.font = V.font();
    ctx.textAlign = "center";
    ctx.fillStyle = c.muted;
    cited.forEach(function (m) {
      ctx.fillText(m.ohm + " Ω", xOf(m.at), padT + ph + 14);
    });
    ctx.textAlign = "left";
    ctx.fillText("Ω per segment →", padL, padT + ph + 25);

    canvas.setAttribute("aria-label",
      "Accuracy as a fraction of each array's own ideal, against fifteen wire "
      + "resistances. At " + (grid * grid) + " rows the first-order model holds to "
      + fmtOhm(ex.lastHoldingFirstOrder) + " and the solved network to "
      + fmtOhm(ex.lastHolding) + " ohms per segment. The four fainter curves are the "
      + "other array sizes, solved.");
  }

  /** The site's wire formatter, with this instrument's word for "no edge". */
  function fmtOhm(v) {
    if (v == null || !isFinite(v)) return "none on this ladder";
    return V.ohms(v);
  }

  /* -------------------------------------------------------------- the strip */

  /** The same digit at all five grids: what "36 pixels" costs, seen once. */
  function drawStrip(box, sampleIndex, grid, c) {
    var bar = window.SpinnSizeBar;
    box.innerHTML = "";
    bar.grids().forEach(function (g) {
      var model = bar.modelFor(g);
      var fig = document.createElement("figure");
      var canvas = document.createElement("canvas");
      canvas.width = STRIP_PX;
      canvas.height = STRIP_PX;
      canvas.style.width = STRIP_PX + "px";
      canvas.style.height = STRIP_PX + "px";
      var ctx = canvas.getContext("2d");
      var pixels = model.x.subarray(sampleIndex * model.rows,
                                    (sampleIndex + 1) * model.rows);
      V.drawInput(ctx, c, 0.5, 0.5, STRIP_PX - 1, pixels, model.side);
      var cap = P.el("figcaption", "", g + "&times;" + g);
      if (g === grid) cap.setAttribute("aria-current", "true");
      fig.appendChild(canvas);
      fig.appendChild(cap);
      box.appendChild(fig);
    });
    var label = bar.modelFor(grid).labels[sampleIndex];
    box.setAttribute("aria-label",
      "The same handwritten " + label + " at 6, 8, 12, 18 and 26 pixels per side.");
  }

  /* --------------------------------------------------------------- mounting */

  function mount(el, opts) {
    P.injectStyle("spinn-size-style", CSS);
    var bar = window.SpinnSizeBar;
    if (!bar) throw new Error("the size bar did not mount; there is no size to draw");

    // The grid comes from the data this mount was handed, and falls back to the
    // bar. Two sources of truth would agree on the real page -- `size_page.js`
    // rebuilds with the size the bar just published -- and disagree anywhere else,
    // including in a test that mounts this instrument on its own.
    var grid = (opts && opts.data && opts.data.grid) || bar.current();
    var rung = 0;                 // index into the fifteen-rung wire ladder
    var sampleIndex = 0;
    var off = document.createElement("canvas");

    var wrap = P.el("div", "sz");

    var left = P.el("div", "");
    left.appendChild(P.el("p", "sz-k", "What each cell keeps"));
    var map = document.createElement("canvas");
    map.className = "sz-map";
    map.setAttribute("role", "img");
    left.appendChild(map);
    var key = P.el("div", "sz-key");
    var ramp = P.el("div", "sz-ramp");
    key.appendChild(P.el("span", "", "all"));
    key.appendChild(ramp);
    key.appendChild(P.el("span", "", "none"));
    left.appendChild(key);

    var field = P.el("div", "sp-field");
    field.style.marginTop = "18px";
    var label = P.el("label", "", "Wire resistance");
    var slider = document.createElement("input");
    slider.type = "range";
    slider.min = "0";
    slider.step = "1";
    slider.id = "sizeWire";
    label.setAttribute("for", slider.id);
    var out = document.createElement("output");
    out.setAttribute("for", slider.id);
    field.appendChild(label);
    field.appendChild(slider);
    field.appendChild(out);
    left.appendChild(field);
    var read = P.el("p", "sz-read");
    left.appendChild(read);

    var right = P.el("div", "");
    right.appendChild(P.el("p", "sz-k", "Accuracy against wire resistance"));
    var chart = document.createElement("canvas");
    chart.className = "sz-chart";
    chart.setAttribute("role", "img");
    right.appendChild(chart);
    var note = P.el("p", "sz-note");
    right.appendChild(note);

    wrap.appendChild(left);
    wrap.appendChild(right);

    var facts = P.el("div", "sz-facts");
    var strip = P.el("div", "sz-strip");
    strip.setAttribute("role", "img");

    el.appendChild(wrap);
    el.appendChild(facts);
    el.appendChild(P.el("p", "sz-k sz-striph", "The same digit, at each grid"));
    el.appendChild(strip);

    function bits(v) { return (-Math.log(v) / Math.LN2).toFixed(2); }
    function stateBits(v) { return (Math.log(2 * v - 1) / Math.LN2).toFixed(2); }

    function paintFacts(data) {
      var b = data.budget;
      facts.innerHTML = "";
      [[bits(b.sigma.lastHolding) + " bits",
        "conductance variation holds at σ = " + b.sigma.lastHolding],
       [stateBits(b.states.lastHolding) + " bits",
        "and " + b.states.lastHolding + " states per device"],
       [(data.power * 1e6).toFixed(2) + " µW",
        "array read power, no periphery"],
       [fmtOhm(b.exact.lastHolding) + " Ω",
        "solved wire holds · first order " + fmtOhm(firstOrderLast(b.exact)) + " Ω"],
      ].forEach(function (f) {
        facts.appendChild(V.readout("", f[0], f[1]));
      });
    }

    /** The last rung at which first order still clears this size's pass mark. */
    function firstOrderLast(ex) {
      var data = bar.dataFor(grid), last = null;
      for (var i = 0; i < ex.magnitudes.length; i++) {
        if (ex.firstOrderAcc[i] >= 0.95 * data.idealAccuracy) last = ex.magnitudes[i];
      }
      return last;
    }

    function paint() {
      var c = V.ink(document.documentElement);
      var data = bar.dataFor(grid);
      var model = bar.modelFor(grid);
      var ex = data.budget.exact;
      var ohm = ex.magnitudes[rung];

      ramp.style.background = "linear-gradient(90deg," + c.surface2 + "," + c.accent2 + ")";

      var solved = C.machine(model, { wireOhm: ohm, wireModel: "solved" });
      var first = C.machine(model, { wireOhm: ohm });
      var accSolved = C.evaluate(model, solved).accuracy;
      var accFirst = C.evaluate(model, first).accuracy;

      drawMap(map, off, solved, model, c);
      ex.lastHoldingFirstOrder = firstOrderLast(ex);
      drawChart(chart, grid, rung, c);
      drawStrip(strip, sampleIndex, grid, c);
      paintFacts(data);

      out.textContent = fmtOhm(ohm) + " Ω per segment";
      slider.setAttribute("aria-valuetext", fmtOhm(ohm) + " ohms per segment, rung "
        + (rung + 1) + " of " + ex.magnitudes.length);

      var pass = 0.95 * data.idealAccuracy;
      var verdict = function (a) {
        return '<span class="' + (a >= pass ? "hold" : "fail") + '">'
          + (a >= pass ? "holds" : "fails") + "</span>";
      };
      read.innerHTML = ""
        + "solved <b>" + accSolved.toFixed(4) + "</b> &middot; recorded "
        + data.sample.exact.exactAcc[rung].toFixed(4) + "<br>"
        + "first order <b>" + accFirst.toFixed(4) + "</b> &middot; recorded "
        + data.sample.wire.accMean[rung].toFixed(4) + "<br>"
        + "worst cell keeps <b>" + (100 * solved.worstFraction).toFixed(1) + "%</b>"
        + " &middot; mean " + (100 * solved.meanFraction).toFixed(1) + "%<br>"
        + "on all 2,000 &mdash; solved " + ex.exactAcc[rung].toFixed(4) + " "
        + verdict(ex.exactAcc[rung]) + "<br>"
        + "on all 2,000 &mdash; first order " + ex.firstOrderAcc[rung].toFixed(4) + " "
        + verdict(ex.firstOrderAcc[rung]);

      // Below the 0.1 of chance is not a harder failure, it is an impossible one,
      // and it is the clearest evidence on the page that the two models are two
      // models. Said only where it is happening, so it reads as an observation
      // rather than a disclaimer.
      var impossible = ex.firstOrderAcc[rung] < 0.1
        ? "First order is below the 0.1 of chance here: past its range it lets a "
          + "column node rise above the driver feeding it and reverses a cell&rsquo;s "
          + "current, which no resistor network does. "
        : "";

      note.innerHTML = ""
        + "Live numbers are a <b>500-digit sample</b>; the verdict is the recorded run "
        + "over all 2,000. The fainter curves are the other four sizes. "
        + impossible
        + (grid === 6
          ? "At 6&times;6 the main page records IR drop holding at 100&nbsp;&#937; and "
            + "failing at 300 &mdash; the same first-order model, on the row&rsquo;s "
            + "coarser nine-rung ladder. A finer ladder moves a bracket without moving "
            + "a curve."
          : "Only 6&times;6 is the shared task; this grid is internal to this repository.");
    }

    /** The part of the readout that costs nothing: where the handle is. */
    function paintRung() {
      var ex = bar.dataFor(grid).budget.exact;
      var ohm = ex.magnitudes[rung];
      out.textContent = fmtOhm(ohm) + " Ω per segment";
      slider.setAttribute("aria-valuetext", fmtOhm(ohm) + " ohms per segment, rung "
        + (rung + 1) + " of " + ex.magnitudes.length);
    }

    // Everything else -- two solves and two passes over five hundred digits -- waits
    // for the handle to settle. At 676 rows a paint is a few hundred milliseconds
    // and this track has fifteen rungs on it.
    var repaint = P.debounce(paint, 90);

    function onSlide() {
      rung = Number(slider.value);
      paintRung();
      repaint();
    }

    function resize(grid_) {
      var ex = bar.dataFor(grid_).budget.exact;
      slider.max = String(ex.magnitudes.length - 1);
      if (rung > ex.magnitudes.length - 1) rung = ex.magnitudes.length - 1;
      slider.value = String(rung);
    }

    // Open on the cited 7 nm wiring, which is where the sizes actually differ: at
    // 2 ohm every size holds and the map is blank, and a first view that shows
    // nothing happening is a first view that teaches nothing.
    (function () {
      var ex = bar.dataFor(grid).budget.exact;
      for (var i = 0; i < ex.magnitudes.length; i++) {
        if (Math.abs(ex.magnitudes[i] - 20) < 1e-9) rung = i;
      }
    })();

    resize(grid);
    slider.addEventListener("input", onSlide);
    slider.addEventListener("change", onSlide);

    var stopWidth = P.onWidthChange(el, repaint);
    var stopTheme = P.onThemeChange(repaint);
    var unsubscribe = bar.subscribe(function (g) {
      grid = g;
      resize(g);
      paintRung();
      paint();
    });

    paint();

    return {
      destroy: function () {
        slider.removeEventListener("input", onSlide);
        slider.removeEventListener("change", onSlide);
        repaint.cancel();
        if (stopWidth) stopWidth();
        if (stopTheme) stopTheme();
        unsubscribe();
        el.innerHTML = "";
      },
    };
  }

  if (typeof window !== "undefined") window.SpinnSizeArray = { mount: mount };
  if (typeof module !== "undefined" && module.exports) module.exports = { mount: mount };
})();
