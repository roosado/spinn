/*
 * hero.js -- the machine, running, as the first thing on the page.
 *
 * The page's claim is that a grid of magnets classifies handwriting, and the
 * cheapest way to lose a reader is to assert that in a sentence over a stock
 * illustration. So the first viewport is the array itself: the real 36x10 trained
 * weights, real frozen MNIST test digits, and the same arithmetic the measurement
 * ran -- classifying, in front of them, before they have read anything.
 *
 * It mounts into two elements: the machine, and a readout that sits beside the
 * headline in the other column of the hero. One widget owning both is deliberate.
 * The number and the picture must never disagree, and the way to guarantee that is
 * for one piece of code to produce both from one evaluation.
 *
 * The settle
 * ----------
 * One authored motion moment, used here and nowhere else on the page: the drive
 * lines fill in down the array, then the column currents grow from zero on an
 * exponential ease-out, then the winning column brightens once. It is a sequence
 * with a meaning -- drive, sum, decide -- rather than an entrance.
 *
 * Under `prefers-reduced-motion` there is no settle and no autoplay: the reader
 * gets a still machine on one digit and a button that steps to the next.
 */
(function () {
  "use strict";

  var P = window.SpinnPlot, V = window.SpinnView, C = window.SpinnCrossbar;

  var CSS = ""
    + ".xh{margin:0;}"
    + ".xh-frame{position:relative;}"
    + ".xh canvas{display:block;width:100%;}"
    + ".xh-legend{display:flex;flex-wrap:wrap;gap:4px 18px;margin-top:14px;"
    + "font-family:var(--mono);font-size:.75rem;letter-spacing:.09em;"
    + "text-transform:uppercase;color:var(--muted);}"
    + ".xh-legend span{display:flex;align-items:center;gap:6px;}"
    + ".xh-legend i{width:9px;height:9px;border-radius:2px;display:block;}"
    + ".xh-controls{display:flex;align-items:center;gap:8px;margin-top:12px;}"
    + ".xh-btn{font-family:var(--mono);font-size:.75rem;letter-spacing:.1em;"
    + "text-transform:uppercase;background:transparent;color:var(--ink-dim);"
    + "border:1px solid var(--border);border-radius:7px;padding:6px 12px;cursor:pointer;"
    + "transition:color .15s,border-color .15s,background .15s;}"
    + ".xh-btn:hover{color:var(--ink);border-color:var(--accent);background:var(--accent-soft);}"
    + ".xh-btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}"
    + ".xh-tally{font-family:var(--mono);font-size:.75rem;color:var(--muted);"
    + "font-variant-numeric:tabular-nums;margin-left:auto;}"
    // The readout in the headline column: one very large numeral, because it is
    // the answer, and the rest of the machine's state in small type beneath it.
    + ".xr{display:flex;align-items:flex-start;gap:18px;margin:26px 0 0;"
    + "border-top:1px solid var(--border);padding-top:18px;max-width:34rem;}"
    + ".xr-digit{font-family:var(--serif);font-size:4.2rem;line-height:.86;font-weight:600;"
    + "color:var(--accent-ink);font-variant-numeric:tabular-nums;min-width:2ch;"
    + "transition:color .25s ease;}"
    + ".xr.miss .xr-digit{color:var(--accent-2-ink);}"
    + ".xr-body{padding-top:5px;}"
    + ".xr-k{font-family:var(--mono);font-size:.75rem;letter-spacing:.16em;"
    + "text-transform:uppercase;color:var(--muted);margin:0;}"
    + ".xr-t{margin:.3rem 0 0;color:var(--ink-dim);font-size:.94rem;line-height:1.45;}"
    + ".xr-t b{color:var(--ink);font-weight:600;}"
    + "@media (max-width:720px){.xr-digit{font-size:3.2rem;}}";

  var HOLD_MS = 1750;

  //: Canvas cannot resolve `var(--mono)`, so the one place a widget draws type it
  //: repeats the stack the stylesheet sets rather than inheriting it.
  var MONO = 'ui-monospace,"Cascadia Code","SF Mono",Consolas,monospace';

  function mount(el, readoutEl) {
    P.injectStyle("spinn-hero-style", CSS);
    var data = window.SpinnData;
    var model = C.load(data);
    var mach = C.machine(model, {});
    var reduce = window.matchMedia
      && window.matchMedia("(prefers-reduced-motion:reduce)").matches;

    var wrap = P.el("div", "xh");
    var frame = P.el("div", "xh-frame");
    var canvas = document.createElement("canvas");
    canvas.setAttribute("role", "img");
    frame.appendChild(canvas);
    wrap.appendChild(frame);

    var controls = P.el("div", "xh-controls");
    var playBtn = P.el("button", "xh-btn", reduce ? "Play" : "Pause");
    playBtn.type = "button";
    var nextBtn = P.el("button", "xh-btn", "Next digit");
    nextBtn.type = "button";
    var tally = P.el("span", "xh-tally", "");
    controls.appendChild(playBtn);
    controls.appendChild(nextBtn);
    controls.appendChild(tally);
    wrap.appendChild(controls);

    var legend = P.el("div", "xh-legend",
      '<span><i style="background:var(--accent)"></i>positive weight</span>'
      + '<span><i style="background:var(--accent-2)"></i>negative weight</span>'
      + "<span>360 weights &middot; 720 devices, two per weight</span>"
      + "<span>the tallest column wins</span>");
    wrap.appendChild(legend);
    el.appendChild(wrap);

    var read = P.el("div", "xr",
      '<span class="xr-digit" aria-hidden="true">&mdash;</span>'
      + '<div class="xr-body"><p class="xr-k">The array answers</p>'
      + '<p class="xr-t" role="status" aria-live="off"></p></div>');
    var digitEl = read.querySelector(".xr-digit");
    var textEl = read.querySelector(".xr-t");
    if (readoutEl) readoutEl.appendChild(read);

    // -- state ---------------------------------------------------------------
    var order = [];
    for (var s = 0; s < model.n; s++) order.push(s);
    // A fixed shuffle, so every reader sees the same digits in the same order --
    // a page whose first impression is a random draw is a page that is sometimes
    // worse than it is, for no gain.
    var r = C.rng(20260908);
    for (var k = order.length - 1; k > 0; k--) {
      var t = Math.floor(r() * (k + 1)), tmp = order[k];
      order[k] = order[t]; order[t] = tmp;
    }

    var at = -1, seen = 0, right = 0;
    var logits = new Float64Array(model.cols);
    var winner = 0, label = 0, sample = 0;
    var playing = !reduce;
    var t0 = 0, raf = 0, timer = 0;

    var arrayBuf = document.createElement("canvas");
    var geom = null, layout = null, colours = null;

    function measure() {
      var W = Math.max(280, Math.round(canvas.getBoundingClientRect().width || 560));
      var tile = W < 460 ? 72 : 96;
      var driveW = W < 460 ? 26 : 44;
      var pad = 2;
      // The rotated row label needs a column of its own between the drive lines and
      // the array, or it overprints them.
      var arrayX = pad + tile + 12 + driveW + 22;
      var arrayW = Math.max(120, W - arrayX - pad);
      var arrayH = Math.round(Math.min(360, Math.max(230, arrayW * 1.24)));
      var barsH = W < 460 ? 84 : 104;
      // Headroom for the annotations: one line above the array, and below the bars
      // the column digits and then the label naming what they measure.
      var H = 18 + arrayH + 14 + barsH + 38;
      layout = {
        W: W, H: H, tile: tile, tileX: pad, tileY: Math.round(18 + (arrayH - tile) / 2),
        driveX: pad + tile + 12, driveW: driveW, barsH: barsH,
      };
      geom = { x: arrayX, y: 18, w: arrayW, h: arrayH, rows: model.rows, cols: model.cols };
      return P.fitTo(canvas, W, H);
    }

    function paintArray() {
      var r2 = P.scale();
      P.resize(arrayBuf, Math.round(geom.w * r2), Math.round(geom.h * r2));
      var bx = arrayBuf.getContext("2d");
      bx.setTransform(r2, 0, 0, r2, 0, 0);
      bx.clearRect(0, 0, geom.w, geom.h);
      V.drawArray(bx, colours,
        { x: 0, y: 0, w: geom.w, h: geom.h, rows: geom.rows, cols: geom.cols },
        // The effective weight, not the two rails. The pair view is the truer
        // picture of 720 devices and it reads as a textile: every cell is part
        // teal and part amber, so the trained pattern -- the thing that actually
        // classifies -- disappears into the weave. Here the ground colour is a
        // zero weight, so what is left on screen is what does the work. The bench
        // below carries the rail view, where two independent error draws per
        // weight are the point being made.
        { mode: "effective", rails: mach.rails, weights: mach.weights });
    }

    function pixels(idx) {
      var out = new Float64Array(model.rows), base = idx * model.rows;
      for (var i = 0; i < model.rows; i++) out[i] = model.x[base + i];
      return out;
    }

    function advance() {
      at = (at + 1) % order.length;
      sample = order[at];
      mach.logits(sample, logits);
      winner = C.argmax(logits);
      label = model.labels[sample];
      seen++;
      if (winner === label) right++;
      t0 = (typeof performance !== "undefined" ? performance.now() : Date.now());
      updateText();
    }

    /** Announce only what the reader asked for; see the aria-live note above. */
    function announce(on) {
      textEl.setAttribute("aria-live", on ? "polite" : "off");
    }

    function updateText() {
      var hit = winner === label;
      digitEl.textContent = String(winner);
      read.classList.toggle("miss", !hit);
      textEl.innerHTML = "This digit is a <b>" + label + "</b>, and the column that drew "
        + "the most current is <b>" + winner + "</b> &mdash; "
        + (hit ? "correct" : "wrong") + ". Over the whole frozen test set the ideal array "
        + "gets <b>73.45%</b> right.";
      tally.textContent = right + " / " + seen + " correct so far";
      canvas.setAttribute("aria-label",
        "A 36 by 10 crossbar classifying a handwritten " + label
        + "; the winning column is " + winner + ".");
    }

    /** The three labels that turn a coloured grid into a mechanism. */
    function annotate(ctx) {
      ctx.font = "10px " + MONO;
      ctx.fillStyle = colours.muted;
      ctx.textAlign = "left";
      ctx.fillText("DIGIT IN", layout.tileX, layout.tileY - 8);
      ctx.fillText("36 VALUES", layout.tileX, layout.tileY + layout.tile + 16);
      ctx.save();
      // Rotated up the left edge of the array, where the drive lines enter it: the
      // rows are the input and the label has to sit on them to say so.
      ctx.translate(geom.x - 7, geom.y + geom.h);
      ctx.rotate(-Math.PI / 2);
      ctx.textAlign = "left";
      ctx.fillText("36 ROWS DRIVEN", 0, 0);
      ctx.restore();
      ctx.textAlign = "right";
      ctx.fillText("10 COLUMNS SUM", geom.x + geom.w, geom.y - 8);
      // Below the column digits, which drawColumns puts 13px under the bar band.
      ctx.textAlign = "left";
      ctx.fillText("COLUMN CURRENT", geom.x, geom.y + geom.h + 14 + layout.barsH + 30);
    }

    function frameNow(now) {
      var ctx = P.fitTo(canvas, layout.W, layout.H).ctx;
      var el2 = reduce ? 1 : Math.min(1, (now - t0) / 170);
      var eg = reduce ? 1 : Math.max(0, Math.min(1, (now - t0 - 150) / 300));
      var grow = 1 - Math.pow(1 - eg, 3);
      var px = pixels(sample);

      ctx.clearRect(0, 0, layout.W, layout.H);
      V.drawInput(ctx, colours, layout.tileX, layout.tileY, layout.tile, px, model.side);
      V.drawDrive(ctx, colours, layout.driveX, geom.x - layout.driveX - 14,
        geom, px, Math.round(el2 * model.rows));
      ctx.drawImage(arrayBuf, geom.x, geom.y, geom.w, geom.h);
      V.drawColumns(ctx, colours, geom, geom.y + geom.h + 14, layout.barsH,
        logits, winner, MONO, grow);
      annotate(ctx);

      if (playing && now - t0 > HOLD_MS) advance();
      if (!reduce) raf = window.requestAnimationFrame(frameNow);
    }

    function still() {
      frameNow(t0 + 10000);
    }

    function start() {
      if (reduce) { still(); return; }
      if (!raf) raf = window.requestAnimationFrame(frameNow);
    }

    function relayout() {
      colours = V.ink(document.documentElement);
      measure();
      paintArray();
      if (reduce) still();
    }

    playBtn.addEventListener("click", function () {
      playing = !playing;
      announce(!playing);
      playBtn.textContent = playing ? "Pause" : "Play";
      if (playing && reduce) {
        // Reduced motion still gets a cycle if it is asked for; it just steps
        // between stills rather than animating between them.
        timer = window.setInterval(function () { advance(); still(); }, HOLD_MS);
      } else if (reduce && timer) {
        window.clearInterval(timer); timer = 0;
      }
      if (playing) t0 = (typeof performance !== "undefined" ? performance.now() : Date.now());
    });
    nextBtn.addEventListener("click", function () {
      announce(true);
      advance();
      if (reduce) still();
    });

    P.onWidthChange(el, relayout);
    P.onThemeChange(function () { relayout(); });

    colours = V.ink(document.documentElement);
    announce(!playing);
    measure();
    advance();
    paintArray();
    start();
  }

  if (typeof window !== "undefined") window.SpinnHero = { mount: mount };
})();
