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
 * The array, the meter and the per-digit bars are computed from the real weights
 * over all two thousand frozen test images, on the spot. The headline number is not
 * always: with one source switched on it is the recorded budget's, for the reason
 * `headline()` gives. Two honest differences between the two, both stated in the
 * widget's own footnote rather than buried:
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
    // One grid for the whole instrument, so the result can change places without the
    // markup changing. Wide: the rails across the top, and the array and its result
    // side by side beneath them.
    + ".bn{display:grid;grid-template-columns:minmax(200px,0.9fr) minmax(240px,1.1fr);"
    + "grid-template-areas:'rails rails' 'array result' 'tools tools' 'note note';"
    + "column-gap:34px;align-items:start;}"
    + ".bn-rails{grid-area:rails;display:grid;grid-template-columns:repeat(3,1fr);"
    + "gap:22px 30px;align-items:end;border-top:1px solid var(--border);padding-top:18px;}"
    + ".bn-array{grid-area:array;min-width:0;margin-top:28px;}"
    + ".bn-result{grid-area:result;min-width:0;margin-top:28px;}"
    + ".bn-tools{grid-area:tools;}.bn-note{grid-area:note;}"
    + ".bn canvas{display:block;width:100%;}"
    // Narrow. A thumb dragging a slider covers everything below it, and stacked in
    // the wide order a 420px array would sit between the sliders and the number they
    // move. So the number and its meter, which hold still, go above the sliders; the
    // verdict, which grows and shrinks by a line or three as it updates, goes below
    // them, where a reflow cannot move a slider under the finger; and the array,
    // which is looked at rather than operated, goes last. The result's wrapper steps
    // aside so its two halves can take separate rows.
    + "@media (max-width:800px){"
    + ".bn{grid-template-columns:minmax(0,1fr);"
    + "grid-template-areas:'read' 'rails' 'verdict' 'tools' 'array' 'note';}"
    + ".bn .bn-result{display:contents;}"
    + ".bn .bn-read{grid-area:read;}"
    + ".bn .bn-verdict{grid-area:verdict;margin-top:18px;}"
    + ".bn .bn-rails{margin-top:22px;}}"
    + "@media (max-width:640px){.bn .bn-rails{grid-template-columns:1fr;gap:18px;}}"
    + ".bn-acc{font-family:var(--mono);font-size:2.9rem;font-weight:600;line-height:1;"
    + "color:var(--ink);font-variant-numeric:tabular-nums;letter-spacing:-.02em;}"
    + ".bn-acc.fail{color:var(--bad);}"
    + ".bn-accl{font-family:var(--mono);font-size:.75rem;letter-spacing:.12em;"
    + "text-transform:uppercase;color:var(--muted);margin:0 0 8px;}"
    + ".bn-delta{font-family:var(--mono);font-size:.8125rem;color:var(--muted);"
    + "margin-left:10px;font-variant-numeric:tabular-nums;}"
    + ".bn-verdict{margin:14px 0 0;font-size:.9375rem;color:var(--ink-dim);line-height:1.5;}"
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
    + ".bn-note{font-size:.8125rem;color:var(--muted);margin:20px 0 0;line-height:1.55;"
    + "border-top:1px solid var(--border);padding-top:12px;max-width:64ch;}"
    + ".bn-cap{font-family:var(--mono);font-size:.75rem;letter-spacing:.12em;"
    + "text-transform:uppercase;color:var(--muted);margin:8px 0 0;}"
    // The bracket, on the control itself: the last rung that held and the first that
    // failed. Drawn beneath the handle, which covers them when it sits on one.
    + ".bn-track{position:relative;display:block;}"
    + ".bn-track input{position:relative;}"
    + ".bn-mark{forced-color-adjust:none;position:absolute;top:50%;width:2px;height:7px;margin:3px 0 0 -1px;"
    + "pointer-events:none;}"
    + ".bn-mark.hold{background:var(--good);}"
    + ".bn-mark.fail{background:var(--bad);}";

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
    /** A slider over one ladder, with that source's bracket marked on its track. */
    function field(id, name, ladder, entry) {
      var max = ladder.values.length - 1;
      function mark(cls, magnitude) {
        var i = ladder.values.indexOf(magnitude);
        if (i < 0) return "";
        // The handle's centre runs from half its 11px width in to half its width
        // short of the far end, so a rung sits at its fraction of what is left.
        return '<i class="bn-mark ' + cls + '" style="left:calc(5.5px + (100% - 11px) * '
          + (i / max) + ')"></i>';
      }
      var f = P.el("div", "sp-field",
        '<label for="' + id + '">' + name + "</label>"
        + '<span class="bn-track">' + mark("hold", entry.lastHolding)
        + mark("fail", entry.firstFailing)
        + '<input id="' + id + '" type="range" min="0" max="' + max
        + '" step="1" value="0"></span>'
        + '<output for="' + id + '"></output>');
      rails.appendChild(f);
      return f.querySelector("input");
    }
    var sIn = field("bn-sigma", "Conductance variation", sigma, b.sigma);
    var qIn = field("bn-states", "Resolvable states", states, b.states);
    var rIn = field("bn-wire", "Wire resistance", wire, b.wire);

    var leftCol = P.el("div", "bn-array",
      '<p class="bn-accl">The array, as built</p>');
    var arrayCanvas = document.createElement("canvas");
    arrayCanvas.setAttribute("role", "img");
    leftCol.appendChild(arrayCanvas);
    leftCol.appendChild(P.el("p", "bn-cap",
      "360 differential pairs &middot; teal positive, amber negative"));

    // The result in two pieces: the number and its meter, which hold still, and the
    // verdict, which reflows. A narrow screen puts them on either side of the sliders.
    var rightCol = P.el("div", "bn-result");
    var readout = P.el("div", "bn-read",
      '<p class="bn-accl">Accuracy, all 2,000 frozen test digits</p>'
      + '<div><span class="bn-acc"></span><span class="bn-delta"></span></div>');
    var meter = document.createElement("canvas");
    meter.setAttribute("role", "img");
    readout.appendChild(meter);
    rightCol.appendChild(readout);
    var verdict = P.el("p", "bn-verdict", "");
    verdict.setAttribute("role", "status");
    verdict.setAttribute("aria-live", "off");
    rightCol.appendChild(verdict);

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
      "The array, the pointer on the meter and the per-digit bars are computed here, "
      + "now, from the trained weights over the whole frozen test set; with one source "
      + "switched on, the number above them is the recorded budget's. Two honest gaps "
      + "between the two: the conductance draw uses a "
      + "different random generator from MATLAB's, so one realisation here is not one "
      + "of the recorded realisations &mdash; re-roll a few times to see the spread. "
      + "And at coarse quantisation a few digits produce two exactly equal column "
      + "currents, where the winner is decided by the order the additions happened "
      + "in; that moves the accuracy by one digit in two thousand.");

    // Markup order is reading order -- controls, then what they did -- whatever
    // order the grid draws them in.
    var bench = P.el("div", "bn");
    bench.appendChild(rails);
    bench.appendChild(leftCol);
    bench.appendChild(rightCol);
    bench.appendChild(tools);
    bench.appendChild(note);
    el.appendChild(bench);

    var accEl = rightCol.querySelector(".bn-acc");
    var deltaEl = rightCol.querySelector(".bn-delta");
    var accLabel = rightCol.querySelector(".bn-accl");
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

    function drawMeter(res, hl) {
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
      ctx.fillStyle = hl.value < model.threshold ? colours.bad : colours.accent;
      ctx.fillRect(0, 10, Math.max(1, xOf(hl.value)), 9);

      // The two lines that make the number mean something. They sit four hundredths
      // apart on a scale that is 0.78 wide, so their labels would collide if both
      // were placed against their own line: the pass mark keeps the line and the
      // ideal is labelled at the end of the axis, where there is room.
      var xPass = xOf(model.threshold), xIdeal = xOf(model.ideal);
      ctx.font = V.font();

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

      // The recorded spread as a whisker under the bar, and the draw computed here as
      // a pointer above it. At the holding edge the pass mark sits inside the
      // whisker, which is what "holds, by a quarter of a standard deviation" looks
      // like; one rung further out, the whole whisker is below it.
      if (hl.sd > 0) {
        var x0 = xOf(Math.max(lo, hl.value - hl.sd)), x1 = xOf(Math.min(hi, hl.value + hl.sd));
        ctx.strokeStyle = colours.dim;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x0, 23.5); ctx.lineTo(x1, 23.5);
        ctx.moveTo(x0 + 0.5, 21); ctx.lineTo(x0 + 0.5, 26);
        ctx.moveTo(x1 - 0.5, 21); ctx.lineTo(x1 - 0.5, 26);
        ctx.stroke();
      }
      var drawn = hl.recorded && Math.abs(res.accuracy - hl.value) > 1e-9;
      if (drawn) {
        var xt = xOf(res.accuracy);
        ctx.fillStyle = colours.ink;
        ctx.beginPath();
        ctx.moveTo(xt - 4, 1); ctx.lineTo(xt + 4, 1); ctx.lineTo(xt, 8);
        ctx.closePath();
        ctx.fill();
      }

      // per-digit, because "accuracy fell four points" hides whether the machine
      // lost a little of everything or stopped recognising one digit entirely
      var barW = W / 10, base = H - 15, span = 46;
      ctx.font = V.font();
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
      ctx.fillText(drawn ? "PER DIGIT, THIS DRAW" : "PER DIGIT", 0, base - span - 5);
      meter.setAttribute("aria-label",
        (hl.recorded ? "Recorded accuracy " : "Accuracy ") + hl.value.toFixed(4)
        + (hl.sd > 0 ? " plus or minus " + hl.sd.toFixed(4) : "")
        + " against a pass mark of " + model.threshold.toFixed(4)
        + (drawn ? "; this realisation " + res.accuracy.toFixed(3) : "") + ".");
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

    //: The three sources, by the names their sliders carry.
    var NAMES = { sigma: "conductance variation", states: "resolvable states",
      wire: "wire resistance" };

    /** The sources switched on, as [key, magnitude] pairs. */
    function active() {
      var s = settings();
      return [["sigma", s.sigma], ["states", s.states], ["wire", s.wireOhm]]
        .filter(function (p) { return p[1]; });
    }

    /**
     * What the bench's number and verdict report, and on whose authority.
     *
     * With one source switched on, the budget has a recorded figure for exactly this
     * setting, so that leads: the mean over twenty realisations, and its spread. The
     * draw computed here is one realisation, shown as a pointer against it rather
     * than as the answer. At the holding edge the recorded mean clears the pass mark
     * by a quarter of a standard deviation, so a single draw lands under it about two
     * times in five -- and a headline built on one draw would contradict, that
     * often, the bracket the page publishes two sections down.
     *
     * With two or three on, nothing was recorded for the combination except the one
     * point where all three sit at their holding edges. Everywhere else the live
     * draw is all there is, and the widget says so.
     */
    function headline(res) {
      var on = active(), s = settings(), j = b.joint && b.joint.config;
      if (on.length === 1) {
        var rec = recorded(b[on[0][0]], on[0][1]);
        if (rec) {
          return { value: rec.mean, sd: rec.sd, recorded: true,
            label: rec.sd > 0 ? "Recorded, mean of twenty realisations" : "Recorded accuracy" };
        }
      }
      if (on.length === 3 && j && s.sigma === j.sigma_g_rel
          && s.states === j.states_per_device && s.wireOhm === j.wire_resistance_ohm) {
        return { value: b.joint.mean, sd: b.joint.std, recorded: true, joint: true,
          label: "Recorded, all three at their edges" };
      }
      return { value: res.accuracy, sd: 0, recorded: false,
        label: on.length ? "Accuracy of this realisation"
          : "Accuracy, all 2,000 frozen test digits" };
    }

    /** "a", "a and b", "a, b and c". */
    function list(words) {
      return words.length < 3 ? words.join(" and ")
        : words.slice(0, -1).join(", ") + " and " + words[words.length - 1];
    }

    function verdictText(res, hl) {
      var on = active();
      if (!on.length) {
        return "Nothing is wrong with this array. Every device holds exactly the "
          + "conductance it was programmed to, and the wires are perfect.";
      }
      var passed = hl.value >= model.threshold;
      var mark = "the 95%-of-ideal mark of " + model.threshold.toFixed(4);
      var lead = passed ? '<span class="pass">Holds.</span> '
        : '<span class="fail">Fails.</span> ';
      var draw = res.accuracy.toFixed(3);

      if (hl.joint) {
        return lead + "This is the one combination the budget measured: each source at "
          + "the last magnitude it held on its own. Twenty realisations recorded <b>"
          + hl.value.toFixed(4) + " &plusmn; " + hl.sd.toFixed(4) + "</b>, "
          + (passed ? "clearing " : "under ") + mark + " &mdash; budgeting each source "
          + "to its own edge leaves nothing over. The draw computed here, <b>" + draw
          + "</b>, is the pointer above the bar.";
      }
      if (hl.recorded && hl.sd > 0) {
        return lead + "The budget recorded <b>" + hl.value.toFixed(4) + " &plusmn; "
          + hl.sd.toFixed(4) + "</b> here, over twenty realisations, which "
          + (passed ? "clears " : "misses ") + mark + ". The draw computed in front of "
          + "you is one more realisation, <b>" + draw + "</b>, the pointer above the "
          + "bar: re-roll and it moves, and the recorded mean does not.";
      }
      if (hl.recorded) {
        var same = Math.abs(res.accuracy - hl.value) < 1e-9;
        return lead + "The budget recorded <b>" + hl.value.toFixed(4) + "</b> here, "
          + (passed ? "clearing " : "missing ") + mark + ". This source involves no "
          + "random draw, so "
          + (same ? "the array computed here gives exactly that."
            : "the array computed here should give the same, and gives <b>"
              + res.accuracy.toFixed(4) + "</b>: two columns tie on a few digits, "
              + "and which one wins depends on the order of the additions.");
      }
      return "One realisation, with " + list(on.map(function (p) { return NAMES[p[0]]; }))
        + " in play, " + (passed ? '<span class="pass">clears</span> '
          : '<span class="fail">misses</span> ') + mark + ". The budget measured each "
        + "source on its own, so nothing was recorded for this combination to set it "
        + "against.";
    }

    function recompute() {
      var mach = C.machine(model, settings());
      var res = C.evaluate(model, mach);
      var hl = headline(res);
      current = { mach: mach, res: res, hl: hl };
      // Three figures, not four, for a live draw with a random source in it: the
      // fourth is one digit of two thousand, and on a single realisation of a random
      // draw it is noise being reported as signal. A recorded mean earns all four.
      accEl.textContent = !hl.recorded && settings().sigma
        ? hl.value.toFixed(3)
        : hl.value.toFixed(4);
      accEl.classList.toggle("fail", hl.value < model.threshold);
      accLabel.textContent = hl.label;
      deltaEl.textContent = (hl.sd > 0 ? "± " + hl.sd.toFixed(4) + " · " : "")
        + (hl.value >= model.ideal ? "+" : "−")
        + Math.abs(hl.value - model.ideal).toFixed(4) + " vs ideal";
      verdict.innerHTML = verdictText(res, hl);
      drawArray(res);
      drawMeter(res, hl);
    }

    /** A ladder label as a screen reader should say it: "Ω" is read as "omega", or not at all. */
    function spoken(text) {
      return text.replace(/(\d+(?:\.\d+)?) (k?)Ω/, function (m, n, k) {
        return n + " " + (k ? "kil" : "") + (n === "1" ? "ohm" : "ohms");
      });
    }

    /** Each slider's value, and in words where it sits on that source's bracket. */
    function labels() {
      [[sIn, sigma, b.sigma], [qIn, states, b.states], [rIn, wire, b.wire]]
        .forEach(function (f) {
          var i = Number(f[0].value), v = f[1].values[i];
          var where = v === f[2].lastHolding ? "last that holds"
            : v === f[2].firstFailing ? "first that fails" : "";
          f[0].closest(".sp-field").querySelector("output").textContent = f[1].label(i)
            + (where ? " · " + where : "");
          // The input's own value is a rung index, so without this a screen reader
          // announces "5" for sigma = 0.035.
          f[0].setAttribute("aria-valuetext",
            spoken(f[1].label(i)) + (where ? ", " + where : ""));
        });
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
      // Back to the bench as it opened: no error, and the weight view. It used to
      // leave the rails showing, which was half of the opening state left behind.
      sIn.value = qIn.value = rIn.value = "0";
      mode = "effective";
      railBtn.textContent = "Show both rails";
      railBtn.setAttribute("aria-pressed", "false");
      schedule();
    });
    railBtn.addEventListener("click", function () {
      mode = mode === "rails" ? "effective" : "rails";
      railBtn.textContent = mode === "rails" ? "Show the weight" : "Show both rails";
      railBtn.setAttribute("aria-pressed", mode === "rails" ? "true" : "false");
      drawArray(current.res);
    });

    P.onWidthChange(el, function () {
      if (current) { drawArray(current.res); drawMeter(current.res, current.hl); }
    });
    P.onThemeChange(function () {
      if (current) { drawArray(current.res); drawMeter(current.res, current.hl); }
    });

    labels();
    recompute();
  }

  if (typeof window !== "undefined") window.SpinnBench = { mount: mount };
})();
