/*
 * wire.js -- one column, opened up, so the sum stops being a claim.
 *
 * "Kirchhoff's law does the arithmetic" is the sentence this project rests on, and
 * a sentence is a poor place for it. So: pick a column, pick a digit, and watch
 * the wire fill up. Thirty-six devices each pass a current set by their own
 * conductance and the input driving them; they all empty into the same wire; the
 * wire carries the running total; the number at the bottom is the column's logit.
 *
 * Two panels sharing one row axis, rather than one panel with two scales. Left is
 * what each device contributes, signed, because a differential pair can subtract.
 * Right is what the wire is carrying by the time it has passed that device, which
 * is the quantity that actually exists in the hardware -- there is no per-device
 * current anywhere in a crossbar, only the accumulation, and drawing the staircase
 * beside the bars is the honest way to say so.
 *
 * The scale is dimensionless throughout: the read voltage and the conductance
 * window cancel in the decode, exactly, so a current here is reported in the units
 * the logits are in. Putting amps on this axis would be inventing a precision the
 * operating point does not have.
 */
(function () {
  "use strict";

  var P = window.SpinnPlot, C = window.SpinnCrossbar, V = window.SpinnView;

  var CSS = ""
    + ".wr canvas{display:block;width:100%;max-width:620px;}"
    + ".wr-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 18px;"
    + "margin:0 0 14px;}"
    + ".wr-k{font-family:var(--mono);font-size:.75rem;letter-spacing:.16em;"
    + "text-transform:uppercase;color:var(--muted);margin:0;}"
    + ".wr-cols{display:flex;gap:4px;flex-wrap:wrap;}"
    + ".wr-col{font-family:var(--mono);font-size:.8rem;width:30px;height:30px;"
    + "border:1px solid var(--border);border-radius:7px;background:transparent;"
    + "color:var(--muted);cursor:pointer;font-variant-numeric:tabular-nums;"
    + "transition:color .12s,border-color .12s,background .12s;}"
    + ".wr-col:hover{color:var(--ink);border-color:var(--accent);}"
    + ".wr-col[aria-pressed=\"true\"]{color:var(--accent-ink);border-color:var(--accent);"
    + "background:var(--accent-soft);font-weight:600;}"
    + ".wr-col:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}"
    + ".wr-foot{margin-top:12px;color:var(--ink-dim);font-size:.9rem;line-height:1.5;}"
    + ".wr-foot b{color:var(--ink);font-weight:600;font-family:var(--mono);"
    + "font-variant-numeric:tabular-nums;}"
    + ".wr-btn{font-family:var(--mono);font-size:.75rem;letter-spacing:.1em;"
    + "text-transform:uppercase;background:transparent;color:var(--ink-dim);"
    + "border:1px solid var(--border);border-radius:7px;padding:6px 12px;cursor:pointer;}"
    + ".wr-btn:hover{color:var(--ink);border-color:var(--accent);background:var(--accent-soft);}"
    + ".wr-btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}";

  var MONO = 'ui-monospace,"Cascadia Code","SF Mono",Consolas,monospace';

  function mount(el) {
    P.injectStyle("spinn-wire-style", CSS);
    var model = C.load(window.SpinnData);
    var mach = C.machine(model, {});
    var logits = new Float64Array(model.cols);

    var head = P.el("div", "wr-head", '<p class="wr-k">Sense this column</p>');
    var cols = P.el("div", "wr-cols");
    var buttons = [];
    for (var j = 0; j < model.cols; j++) {
      (function (col) {
        var b = P.el("button", "wr-col", String(col));
        b.type = "button";
        b.setAttribute("aria-label", "Show the wire for column " + col);
        b.addEventListener("click", function () { pick(col); });
        buttons.push(b);
        cols.appendChild(b);
      })(j);
    }
    head.appendChild(cols);
    var nextBtn = P.el("button", "wr-btn", "Another digit");
    nextBtn.type = "button";
    head.appendChild(nextBtn);

    var canvas = document.createElement("canvas");
    canvas.setAttribute("role", "img");
    var foot = P.el("p", "wr-foot", "");

    var wrap = P.el("div", "wr");
    wrap.appendChild(head);
    wrap.appendChild(canvas);
    wrap.appendChild(foot);
    el.appendChild(wrap);

    var order = [];
    var r = C.rng(4242);
    for (var s = 0; s < model.n; s++) order.push(s);
    for (var k = order.length - 1; k > 0; k--) {
      var t = Math.floor(r() * (k + 1)), tmp = order[k];
      order[k] = order[t]; order[t] = tmp;
    }
    var at = 0, column = 0, sample = order[0];

    function draw() {
      var c = V.ink(document.documentElement);
      var ink = c.ink, muted = c.muted, border = c.border;
      var accent = c.accent, accent2 = c.accent2, dim = c.dim;

      // Capped. Both panels plot one small signed number per row, and given a
      // 1300 px instrument each would be 600 px wide: a bar chart whose bars are
      // longer than the figure is tall, and an accumulation whose excursions run
      // out of their own panel and across the bars beside them.
      var W = Math.min(620, Math.max(280,
        Math.round(canvas.getBoundingClientRect().width || 620)));
      var rows = model.rows;
      var rowH = W < 520 ? 9 : 11;
      var top = 30, H = top + rows * rowH + 34;
      var f = P.fitTo(canvas, W, H), ctx = f.ctx;
      ctx.clearRect(0, 0, W, H);

      var driveW = W < 520 ? 30 : 44;
      var gap = 18;
      var rest = W - driveW - gap * 2;
      var contribW = rest * 0.46, accW = rest * 0.54;
      var barMid = driveW + gap + contribW / 2;
      // Centred, not left-edged. The wire carries a signed current and spends most
      // of a typical digit below zero, so an axis at the panel's edge sends the
      // trace out of its own panel and straight across the bars.
      var accMid = driveW + gap + contribW + gap + accW / 2;

      var base = sample * rows;
      var contrib = new Float64Array(rows), cum = new Float64Array(rows);
      var run = 0, peakC = 1e-12, peakA = 1e-12, i;
      for (i = 0; i < rows; i++) {
        contrib[i] = model.x[base + i] * mach.weights[i * model.cols + column] * model.gain;
        run += contrib[i];
        cum[i] = run;
        peakC = Math.max(peakC, Math.abs(contrib[i]));
        peakA = Math.max(peakA, Math.abs(run));
      }

      ctx.font = "9px " + MONO;
      ctx.fillStyle = muted;
      ctx.textAlign = "left";
      ctx.fillText("DRIVE", 0, 12);
      ctx.textAlign = "center";
      ctx.fillText("EACH DEVICE ADDS", barMid, 12);
      ctx.fillText("THE WIRE IS CARRYING", accMid, 12);

      // zero rule for the signed contribution panel
      ctx.strokeStyle = border;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(barMid + 0.5, top);
      ctx.lineTo(barMid + 0.5, top + rows * rowH);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(Math.round(accMid) + 0.5, top);
      ctx.lineTo(Math.round(accMid) + 0.5, top + rows * rowH);
      ctx.stroke();

      for (i = 0; i < rows; i++) {
        var y = top + i * rowH;
        var v = model.x[base + i];

        if (v > 0) {
          ctx.fillStyle = V.mix(border, ink, 0.35 + 0.65 * v);
          ctx.fillRect(0, y + 1, driveW * Math.max(0.16, v), rowH - 2);
        } else {
          // An unlit pixel still has a row and a wire; it just drives nothing.
          ctx.fillStyle = border;
          ctx.fillRect(0, y + rowH / 2 - 0.5, driveW, 1);
        }

        var w = (contrib[i] / peakC) * (contribW / 2 - 3);
        ctx.fillStyle = contrib[i] >= 0 ? accent : accent2;
        if (Math.abs(w) > 0.4) {
          if (w >= 0) ctx.fillRect(barMid + 1, y + 1.5, w, rowH - 3);
          else ctx.fillRect(barMid + w, y + 1.5, -w, rowH - 3);
        }
      }

      // The accumulation, drawn as a staircase: it changes only where a device is.
      ctx.strokeStyle = dim;
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      for (i = 0; i < rows; i++) {
        var yy = top + i * rowH + rowH / 2;
        var xx = accMid + (cum[i] / peakA) * (accW / 2 - 4);
        if (i === 0) { ctx.moveTo(accMid, top); ctx.lineTo(xx, yy); }
        else ctx.lineTo(xx, yy);
      }
      ctx.stroke();

      var finalX = accMid + (cum[rows - 1] / peakA) * (accW / 2 - 4);
      var finalY = top + rows * rowH - rowH / 2;
      ctx.fillStyle = accent;
      ctx.beginPath();
      ctx.arc(finalX, finalY, 3.6, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = c.accentInk;
      ctx.font = "600 11px " + MONO;
      ctx.textAlign = finalX > accMid ? "left" : "right";
      ctx.fillText(cum[rows - 1].toFixed(2),
        finalX + (finalX > accMid ? 8 : -8), top + rows * rowH + 16);

      ctx.font = "9px " + MONO;
      ctx.fillStyle = muted;
      ctx.textAlign = "left";
      ctx.fillText("36 devices, top to bottom", 0, top + rows * rowH + 16);
    }

    function describe() {
      mach.logits(sample, logits);
      var win = C.argmax(logits);
      var label = model.labels[sample];
      buttons.forEach(function (b, j) {
        b.setAttribute("aria-pressed", j === column ? "true" : "false");
      });
      foot.innerHTML = "Column <b>" + column + "</b> ends up carrying <b>"
        + logits[column].toFixed(2) + "</b> for this digit, which is a <b>" + label
        + "</b>. The largest of the ten columns is <b>" + win + "</b> at <b>"
        + logits[win].toFixed(2) + "</b>, so that is the answer"
        + (win === label ? "." : ", and it is wrong.");
      canvas.setAttribute("aria-label",
        "Column " + column + " accumulating current from 36 devices for a handwritten "
        + label + ", reaching " + logits[column].toFixed(2) + ".");
    }

    function pick(col) { column = col; describe(); draw(); }

    nextBtn.addEventListener("click", function () {
      at = (at + 1) % order.length;
      sample = order[at];
      describe();
      draw();
    });

    P.onWidthChange(el, draw);
    P.onThemeChange(draw);
    describe();
    draw();
  }

  if (typeof window !== "undefined") window.SpinnWire = { mount: mount };
})();
