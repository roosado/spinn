/*
 * bench.js -- the machine, built badly on purpose.
 *
 * Everything above this widget on the page describes an ideal array: exact
 * conductances, infinitely resolvable states, perfect wires. None of those exist.
 * This is where the reader gets to take them away one at a time and watch what
 * happens to the answer -- which is the actual subject of the repository, and the
 * one thing a static chart of somebody else's sweep cannot make them feel.
 *
 * Three sliders, and each one lands only on magnitudes the Monte Carlo actually
 * swept. That is not a UI convenience: this project publishes tolerance *edges* as
 * brackets -- "holds at 0.035, fails at 0.05" -- and never interpolates between
 * them, because the data contains no crossing point. A slider that glided smoothly
 * through unmeasured values would be inviting the reader to read off a number the
 * measurement does not support.
 *
 * Every number here is computed from the real weights over all two thousand frozen
 * test images, on the spot. Two honest differences from the recorded budget, both
 * stated in the widget's own footnote rather than buried:
 *
 *   - The conductance draw uses a different random generator from MATLAB's, so a
 *     single realisation here is not a realisation from the recorded sweep. The
 *     distribution is the same; the stream is not. Re-roll a few times and the
 *     spread is the spread the budget reports.
 *   - At coarse quantisation some samples produce two exactly equal column
 *     currents, and which one wins is then decided by the order the additions
 *     happened in. That moves the accuracy by one sample in two thousand against
 *     the recorded figure, in three places on the states ladder.
 */
(function () {
  "use strict";

  var P = window.SpinnPlot, V = window.SpinnView, C = window.SpinnCrossbar;

  var CSS = ""
    + ".bn-rails{display:grid;grid-template-columns:repeat(3,1fr);gap:22px 30px;"
    + "border-top:1px solid var(--border);padding-top:18px;}"
    + "@media (max-width:800px){.bn-rails{grid-template-columns:1fr;gap:18px;}}"
    + ".bn-body{display:grid;grid-template-columns:minmax(200px,0.9fr) minmax(240px,1.1fr);"
    + "gap:26px 34px;margin-top:28px;align-items:start;}"
    + "@media (max-width:800px){.bn-body{grid-template-columns:1fr;}}"
    + ".bn-body canvas{display:block;width:100%;}"
    + ".bn-acc{font-family:var(--mono);font-size:2.9rem;font-weight:600;line-height:1;"
    + "color:var(--ink);font-variant-numeric:tabular-nums;letter-spacing:-.02em;}"
    + ".bn-acc.fail{color:var(--bad);}"
    + ".bn-accl{font-family:var(--mono);font-size:.75rem;letter-spacing:.16em;"
    + "text-transform:uppercase;color:var(--muted);margin:0 0 8px;}"
    + ".bn-delta{font-family:var(--mono);font-size:.86rem;color:var(--muted);"
    + "margin-left:10px;font-variant-numeric:tabular-nums;}"
    + ".bn-verdict{margin:14px 0 0;font-size:.92rem;color:var(--ink-dim);line-height:1.5;}"
    + ".bn-verdict b{color:var(--ink);font-weight:600;}"
    + ".bn-verdict .fail{color:var(--bad-ink);font-weight:600;}"
    + ".bn-verdict .pass{color:var(--good-ink);font-weight:600;}"
    + ".bn-tools{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px;align-items:center;}"
    + ".bn-btn{font-family:var(--mono);font-size:.75rem;letter-spacing:.1em;"
    + "text-transform:uppercase;background:transparent;color:var(--ink-dim);"
    + "border:1px solid var(--border);border-radius:7px;padding:6px 12px;cursor:pointer;"
    + "transition:color .15s,border-color .15s,background .15s;}"
    + ".bn-btn:hover{color:var(--ink);border-color:var(--accent);background:var(--accent-soft);}"
    + ".bn-btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}"
    + ".bn-note{font-size:.8rem;color:var(--muted);margin:20px 0 0;line-height:1.55;"
    + "border-top:1px solid var(--border);padding-top:12px;max-width:64ch;}"
    + ".bn-cap{font-family:var(--mono);font-size:.75rem;letter-spacing:.12em;"
    + "text-transform:uppercase;color:var(--muted);margin:8px 0 0;}";

  var MONO = 'ui-monospace,"Cascadia Code","SF Mono",Consolas,monospace';

  //: The swept ladders, with a leading "off". Values, and their labels, come from
  //: exports/error_budget.json by way of apps/web/data.js -- so a re-run of the
  //: budget that changes a magnitude changes this control too, rather than leaving
  //: a widget quietly offering a setting nobody measured.
  function ladderOf(entry, zeroLabel, fmt) {
    var vals = [0].concat(entry.magnitudes);
    return {
      values: vals,
      label: function (i) { return i === 0 ? zeroLabel : fmt(vals[i]); },
    };
  }

  function mount(el) {
    P.injectStyle("spinn-bench-style", CSS);
    var model = C.load(window.SpinnData);
    var b = model.budget;

    var sigma = ladderOf(b.sigma, "none", function (v) { return "σ = " + v; });
    var states = {
      // The states ladder runs the other way -- more states is less error -- so it
      // is presented from "unlimited" downwards, which is also how it degrades.
      values: [0].concat(b.states.magnitudes),
      label: function (i) {
        return i === 0 ? "unlimited" : b.states.magnitudes[i - 1] + " states";
      },
    };
    var wire = ladderOf(b.wire, "ideal wires", function (v) {
      return v >= 1000 ? (v / 1000) + " kΩ" : v + " Ω";
    });

    var rails = P.el("div", "bn-rails");
    function field(id, name, ladder, start) {
      var f = P.el("div", "sp-field",
        '<label for="' + id + '">' + name + "</label>"
        + '<input id="' + id + '" type="range" min="0" max="' + (ladder.values.length - 1)
        + '" step="1" value="' + start + '">'
        + '<output for="' + id + '"></output>');
      rails.appendChild(f);
      return f.querySelector("input");
    }
    var sIn = field("bn-sigma", "Conductance variation", sigma, 0);
    var qIn = field("bn-states", "Resolvable states", states, 0);
    var rIn = field("bn-wire", "Wire resistance", wire, 0);

    var body = P.el("div", "bn-body");
    var leftCol = P.el("div", "",
      '<p class="bn-accl">The array, as built</p>');
    var arrayCanvas = document.createElement("canvas");
    arrayCanvas.setAttribute("role", "img");
    leftCol.appendChild(arrayCanvas);
    leftCol.appendChild(P.el("p", "bn-cap",
      "360 differential pairs &middot; teal positive, amber negative"));

    var rightCol = P.el("div", "",
      '<p class="bn-accl">Accuracy, all 2,000 frozen test digits</p>'
      + '<div><span class="bn-acc"></span><span class="bn-delta"></span></div>');
    var meter = document.createElement("canvas");
    meter.setAttribute("role", "img");
    rightCol.appendChild(meter);
    var verdict = P.el("p", "bn-verdict", "");
    verdict.setAttribute("role", "status");
    verdict.setAttribute("aria-live", "off");
    rightCol.appendChild(verdict);

    body.appendChild(leftCol);
    body.appendChild(rightCol);

    var tools = P.el("div", "bn-tools");
    var rollBtn = P.el("button", "bn-btn", "Re-roll the devices");
    rollBtn.type = "button";
    var resetBtn = P.el("button", "bn-btn", "Back to ideal");
    resetBtn.type = "button";
    var railBtn = P.el("button", "bn-btn", "Show both rails");
    railBtn.type = "button";
    railBtn.setAttribute("aria-pressed", "false");
    tools.appendChild(rollBtn);
    tools.appendChild(railBtn);
    tools.appendChild(resetBtn);

    var note = P.el("p", "bn-note",
      "Computed here, now, from the trained weights over the whole frozen test set. "
      + "Two honest gaps against the recorded budget: the conductance draw uses a "
      + "different random generator from MATLAB's, so one realisation here is not one "
      + "of the recorded realisations &mdash; re-roll a few times to see the spread. "
      + "And at coarse quantisation a few digits produce two exactly equal column "
      + "currents, where the winner is decided by the order the additions happened "
      + "in; that moves the accuracy by one digit in two thousand.");

    el.appendChild(rails);
    el.appendChild(body);
    el.appendChild(tools);
    el.appendChild(note);

    var accEl = rightCol.querySelector(".bn-acc");
    var deltaEl = rightCol.querySelector(".bn-delta");
    var mode = "effective";
    var seed = 20260908;
    var queued = false, current = null;

    function settings() {
      return {
        sigma: sigma.values[Number(sIn.value)],
        states: states.values[Number(qIn.value)] || null,
        wireOhm: wire.values[Number(rIn.value)],
        seed: seed,
      };
    }

    function drawArray(res) {
      var colours = V.ink(document.documentElement);
      var W = Math.max(180, Math.round(arrayCanvas.getBoundingClientRect().width || 320));
      var H = Math.round(Math.min(420, Math.max(240, W * 1.25)));
      var ctx = P.fitTo(arrayCanvas, W, H).ctx;
      ctx.clearRect(0, 0, W, H);
      V.drawArray(ctx, colours,
        { x: 0, y: 0, w: W, h: H, rows: model.rows, cols: model.cols },
        { mode: mode, rails: current.mach.rails, weights: current.mach.weights });
      arrayCanvas.setAttribute("aria-label",
        "The 36 by 10 weight array as built, at " + describeSettings() + ".");
    }

    function drawMeter(res) {
      var colours = V.ink(document.documentElement);
      var W = Math.max(200, Math.round(meter.getBoundingClientRect().width || 340));
      var H = 126;
      var ctx = P.fitTo(meter, W, H).ctx;
      ctx.clearRect(0, 0, W, H);

      var lo = 0, hi = 0.78;
      var xOf = function (a) { return ((a - lo) / (hi - lo)) * W; };

      // The bar. Kept slim: it is a position on a scale, not a quantity worth a
      // slab, and the two reference lines above are the part being read.
      ctx.fillStyle = colours.surface2;
      ctx.fillRect(0, 10, W, 9);
      ctx.fillStyle = res.accuracy < model.threshold ? colours.bad : colours.accent;
      ctx.fillRect(0, 10, Math.max(1, xOf(res.accuracy)), 9);

      // The two lines that make the number mean something. They sit four hundredths
      // apart on a scale that is 0.78 wide, so their labels would collide if both
      // were placed against their own line: the pass mark keeps the line and the
      // ideal is labelled at the end of the axis, where there is room.
      var xPass = xOf(model.threshold), xIdeal = xOf(model.ideal);
      ctx.font = "9px " + MONO;

      ctx.strokeStyle = colours.muted;
      ctx.setLineDash([3, 3]);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(xIdeal + 0.5, 2);
      ctx.lineTo(xIdeal + 0.5, 26);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.strokeStyle = colours.ink;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(xPass + 0.5, 0);
      ctx.lineTo(xPass + 0.5, 30);
      ctx.stroke();

      ctx.fillStyle = colours.ink;
      ctx.textAlign = "right";
      ctx.fillText("PASS MARK " + model.threshold.toFixed(4), xPass - 5, 39);
      // The ideal sits at 0.7345 of a 0.78 scale, so its label runs off the right
      // edge if it is placed after its own line. Flip it to the inside there.
      var idealText = "IDEAL " + model.ideal.toFixed(4);
      var fits = xIdeal + 5 + ctx.measureText(idealText).width <= W;
      ctx.fillStyle = colours.muted;
      ctx.textAlign = fits ? "left" : "right";
      ctx.fillText(idealText, xIdeal + (fits ? 5 : -5), 51);

      // per-digit, because "accuracy fell four points" hides whether the machine
      // lost a little of everything or stopped recognising one digit entirely
      var barW = W / 10, base = H - 15, span = 46;
      ctx.font = "9px " + MONO;
      for (var d = 0; d < 10; d++) {
        var h = res.perDigit[d] * span;
        ctx.fillStyle = res.perDigit[d] < 0.5 ? colours.accent2 : colours.accent;
        ctx.fillRect(d * barW + 1, base - h, barW - 3, h);
        ctx.fillStyle = colours.muted;
        ctx.textAlign = "center";
        ctx.fillText(String(d), d * barW + barW / 2 - 1, H - 3);
      }
      ctx.textAlign = "left";
      ctx.fillStyle = colours.muted;
      ctx.fillText("PER DIGIT", 0, base - span - 5);
      meter.setAttribute("aria-label",
        "Accuracy " + res.accuracy.toFixed(4) + " against a pass mark of "
        + model.threshold.toFixed(4) + ".");
    }

    function describeSettings() {
      var s = settings(), bits = [];
      if (s.sigma) bits.push("sigma " + s.sigma);
      if (s.states) bits.push(s.states + " states");
      if (s.wireOhm) bits.push(s.wireOhm + " ohm wires");
      return bits.length ? bits.join(", ") : "no error sources";
    }

    /** The recorded mean and spread at this magnitude, when there is one. */
    function recorded(entry, magnitude) {
      var i = entry.magnitudes.indexOf(magnitude);
      return i < 0 ? null : { mean: entry.accMean[i], sd: entry.accStd[i] };
    }

    function verdictText(res) {
      var s = settings();
      var drop = model.ideal - res.accuracy;
      var passed = res.accuracy >= model.threshold;
      var live = [s.sigma && "conductance variation", s.states && "finite states",
        s.wireOhm && "wire resistance"].filter(Boolean);
      if (!live.length) {
        return "Nothing is wrong with this array. Every device holds exactly the "
          + "conductance it was programmed to, and the wires are perfect.";
      }

      var text = "This realisation loses <b>" + (drop * 100).toFixed(1)
        + " points</b> against ideal and "
        + (passed
          ? '<span class="pass">clears</span>'
          : '<span class="fail">misses</span>')
        + " the 95%-of-ideal mark, with " + live.join(", ") + " in play.";

      // The honest qualifier, and the reason it is not optional: with only sigma
      // set, this widget draws once where the budget averaged twenty, and at the
      // holding edge the recorded mean clears the pass mark by a quarter of a
      // standard deviation. A single draw landing under it is the sweep's own
      // spread, not a different answer -- and without this line the page would
      // appear to contradict the bracket it publishes two sections down.
      if (s.sigma && !s.states && !s.wireOhm) {
        var rec = recorded(b.sigma, s.sigma);
        if (rec) {
          text += " The budget recorded <b>" + rec.mean.toFixed(4) + " &plusmn; "
            + rec.sd.toFixed(4) + "</b> here, over twenty realisations; one draw "
            + "lands anywhere in that spread, so the bracket is the mean and this "
            + "number is not.";
        }
      }
      return text;
    }

    function recompute() {
      var mach = C.machine(model, settings());
      var res = C.evaluate(model, mach);
      current = { mach: mach, res: res };
      // Three figures, not four: the fourth is one digit of two thousand, and on a
      // single realisation of a random draw it is noise being reported as signal.
      accEl.textContent = settings().sigma
        ? res.accuracy.toFixed(3)
        : res.accuracy.toFixed(4);
      accEl.classList.toggle("fail", res.accuracy < model.threshold);
      deltaEl.textContent = (res.accuracy >= model.ideal ? "+" : "−")
        + Math.abs(res.accuracy - model.ideal).toFixed(4) + " vs ideal";
      verdict.innerHTML = verdictText(res);
      drawArray(res);
      drawMeter(res);
    }

    function labels() {
      sIn.parentNode.querySelector("output").textContent = sigma.label(Number(sIn.value));
      qIn.parentNode.querySelector("output").textContent = states.label(Number(qIn.value));
      rIn.parentNode.querySelector("output").textContent = wire.label(Number(rIn.value));
    }

    function schedule() {
      labels();
      if (queued) return;
      queued = true;
      // One evaluation per frame at most. A full pass over two thousand images is
      // about ten milliseconds without wire resistance and thirty with it, so a
      // drag stays responsive as long as it never queues two.
      window.requestAnimationFrame(function () { queued = false; recompute(); });
    }

    [sIn, qIn, rIn].forEach(function (input) {
      // `input` fires on every step of a drag and rewrites the verdict each time;
      // a polite live region would then read the whole sentence out again per
      // frame. It is announced on `change`, which fires once, when the reader has
      // finished choosing.
      input.addEventListener("input", function () {
        verdict.setAttribute("aria-live", "off");
        schedule();
      });
      input.addEventListener("change", function () {
        verdict.setAttribute("aria-live", "polite");
        schedule();
      });
    });
    rollBtn.addEventListener("click", function () {
      seed = (seed + 1) | 0;
      verdict.setAttribute("aria-live", "polite");
      recompute();
    });
    resetBtn.addEventListener("click", function () {
      sIn.value = qIn.value = rIn.value = "0";
      schedule();
    });
    railBtn.addEventListener("click", function () {
      mode = mode === "rails" ? "effective" : "rails";
      railBtn.textContent = mode === "rails" ? "Show the weight" : "Show both rails";
      railBtn.setAttribute("aria-pressed", mode === "rails" ? "true" : "false");
      drawArray(current.res);
    });

    P.onWidthChange(el, function () {
      if (current) { drawArray(current.res); drawMeter(current.res); }
    });
    P.onThemeChange(function () {
      if (current) { drawArray(current.res); drawMeter(current.res); }
    });

    labels();
    recompute();
  }

  if (typeof window !== "undefined") window.SpinnBench = { mount: mount };
})();
