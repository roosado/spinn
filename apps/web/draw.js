/*
 * draw.js -- your handwriting, through the array.
 *
 * The last thing the page asks of the reader is to write a digit themselves and
 * watch 720 magnets decide what it was. Nothing about this widget is a
 * simulation of the demonstration: it is the same weights, the same encode, the
 * same ten columns, and the same argmax that produced 0.7345 on the frozen set.
 *
 * What it must not do is flatter the machine. This is a 36-pixel linear
 * classifier -- one matrix, no hidden layer, no convolution -- and the task was
 * deliberately kept that small so that all the complexity in this project sits in
 * the device physics. It gets a bit under three quarters of MNIST right, and a
 * mouse-drawn digit is not MNIST: it is thicker, off-centre, and drawn by an adult
 * with a trackpad. So the widget shows the six-by-six the array actually sees,
 * shows the runner-up as well as the winner, and says plainly what it is that the
 * reader is looking at when it gets one wrong.
 *
 * The pad is 24x24 and box-averaged down to 6x6. That is the same shape of
 * operation the frozen task went through, and doing it in the open -- with the
 * downsampled tile drawn beside the pad -- is the point: most of what a reader
 * needs to understand about why 36 pixels is hard, they get from watching their 4
 * turn into nine grey squares.
 */
(function () {
  "use strict";

  var P = window.SpinnPlot, V = window.SpinnView, C = window.SpinnCrossbar;

  var CSS = ""
    + ".dw{display:grid;grid-template-columns:auto auto minmax(200px,340px);"
    + "gap:20px 30px;align-items:start;justify-content:start;}"
    + "@media (max-width:720px){.dw{grid-template-columns:1fr 1fr;}"
    + ".dw-out{grid-column:1 / -1;}}"
    + ".dw-k{font-family:var(--mono);font-size:.75rem;letter-spacing:.14em;"
    + "text-transform:uppercase;color:var(--muted);margin:0 0 8px;}"
    + ".dw-pad{border:1px solid var(--border);border-radius:10px;background:var(--surface);"
    + "touch-action:none;cursor:crosshair;display:block;}"
    + ".dw-pad:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}"
    + ".dw-seen{border:1px solid var(--border);border-radius:10px;display:block;}"
    + ".dw-guess{font-family:var(--serif);font-size:3.6rem;line-height:1;font-weight:600;"
    + "color:var(--accent-ink);font-variant-numeric:tabular-nums;}"
    + ".dw-guess.none{color:var(--muted);}"
    + ".dw-second{font-family:var(--mono);font-size:.8rem;color:var(--muted);"
    + "margin:6px 0 0;font-variant-numeric:tabular-nums;}"
    + ".dw-bars{display:block;width:100%;max-width:330px;margin-top:12px;}"
    + ".dw-tools{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap;}"
    + ".dw-btn{font-family:var(--mono);font-size:.75rem;letter-spacing:.1em;"
    + "text-transform:uppercase;background:transparent;color:var(--ink-dim);"
    + "border:1px solid var(--border);border-radius:7px;padding:6px 12px;cursor:pointer;"
    + "transition:color .15s,border-color .15s,background .15s;}"
    + ".dw-btn:hover{color:var(--ink);border-color:var(--accent);background:var(--accent-soft);}"
    + ".dw-btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}"
    + ".dw-hint{font-size:.82rem;color:var(--muted);margin:12px 0 0;line-height:1.5;}";

  var MONO = 'ui-monospace,"Cascadia Code","SF Mono",Consolas,monospace';
  var PAD = 24;        // the pad's own grid
  var PAD_PX = 168;    // its drawn size, 7 screen pixels per cell
  var TILE_PX = 108;

  function mount(el) {
    P.injectStyle("spinn-draw-style", CSS);
    var model = C.load(window.SpinnData);
    var mach = C.machine(model, {});
    var side = model.side;

    var grid = P.el("div", "dw");
    var padBox = P.el("div", "", '<p class="dw-k">Draw a digit</p>');
    var pad = document.createElement("canvas");
    pad.className = "dw-pad";
    pad.width = PAD_PX; pad.height = PAD_PX;
    pad.style.width = PAD_PX + "px"; pad.style.height = PAD_PX + "px";
    pad.tabIndex = 0;
    pad.setAttribute("role", "application");
    pad.setAttribute("aria-label",
      "Drawing pad. Draw a digit with the pointer, or use the buttons below to load "
      + "a test digit.");
    padBox.appendChild(pad);
    var tools = P.el("div", "dw-tools");
    var clearBtn = P.el("button", "dw-btn", "Clear");
    clearBtn.type = "button";
    var loadBtn = P.el("button", "dw-btn", "Load a test digit");
    loadBtn.type = "button";
    tools.appendChild(clearBtn);
    tools.appendChild(loadBtn);
    padBox.appendChild(tools);

    var seenBox = P.el("div", "", '<p class="dw-k">What the array sees</p>');
    var seen = document.createElement("canvas");
    seen.className = "dw-seen";
    seen.setAttribute("role", "img");
    seen.setAttribute("aria-label", "The drawing reduced to a 6 by 6 grid.");
    seenBox.appendChild(seen);
    seenBox.appendChild(P.el("p", "dw-hint", "36 pixels. That is the whole input."));

    var outBox = P.el("div", "dw-out", '<p class="dw-k">The array says</p>');
    var guess = P.el("div", "dw-guess none", "—");
    var second = P.el("p", "dw-second", "");
    second.setAttribute("role", "status");
    second.setAttribute("aria-live", "polite");
    var bars = document.createElement("canvas");
    bars.setAttribute("role", "img");
    bars.className = "dw-bars";
    outBox.appendChild(guess);
    outBox.appendChild(second);
    outBox.appendChild(bars);

    grid.appendChild(padBox);
    grid.appendChild(seenBox);
    grid.appendChild(outBox);
    el.appendChild(grid);

    var cells = new Float64Array(PAD * PAD);
    var small = new Float64Array(side * side);
    var logits = new Float64Array(model.cols);
    var drawing = false, testIdx = -1;

    function paintPad() {
      var c = V.ink(document.documentElement);
      var ctx = pad.getContext("2d");
      var r = P.scale();
      P.resize(pad, Math.round(PAD_PX * r), Math.round(PAD_PX * r));
      ctx.setTransform(r, 0, 0, r, 0, 0);
      ctx.clearRect(0, 0, PAD_PX, PAD_PX);
      var cell = PAD_PX / PAD;
      for (var i = 0; i < PAD; i++) {
        for (var j = 0; j < PAD; j++) {
          var v = cells[i * PAD + j];
          if (v <= 0) continue;
          ctx.fillStyle = V.mix(c.surface, c.ink, Math.min(1, v));
          ctx.fillRect(j * cell, i * cell, cell, cell);
        }
      }
      // The six-by-six the array will actually see, ruled over the pad, so the
      // reader can watch their stroke fall into one square or straddle two.
      ctx.strokeStyle = c.border;
      ctx.lineWidth = 1;
      for (var k = 1; k < side; k++) {
        var p = Math.round((k / side) * PAD_PX) + 0.5;
        ctx.beginPath(); ctx.moveTo(p, 0); ctx.lineTo(p, PAD_PX); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0, p); ctx.lineTo(PAD_PX, p); ctx.stroke();
      }
    }

    /** Box-average the pad down to the six-by-six the crossbar is wired for. */
    function reduce() {
      var per = PAD / side, i, j;
      for (i = 0; i < side * side; i++) small[i] = 0;
      for (i = 0; i < PAD; i++) {
        for (j = 0; j < PAD; j++) {
          small[Math.floor(i / per) * side + Math.floor(j / per)] += cells[i * PAD + j];
        }
      }
      var peak = 0;
      for (i = 0; i < small.length; i++) {
        small[i] /= per * per;
        peak = Math.max(peak, small[i]);
      }
      // The encode is per-sample L-infinity: the brightest pixel sits at the read
      // voltage. An empty pad has no peak and must not divide by it.
      if (peak > 0) for (i = 0; i < small.length; i++) small[i] /= peak;
      return peak > 0;
    }

    function paintSeen() {
      var c = V.ink(document.documentElement);
      var ctx = P.fitTo(seen, TILE_PX, TILE_PX).ctx;
      ctx.clearRect(0, 0, TILE_PX, TILE_PX);
      V.drawInput(ctx, c, 0.5, 0.5, TILE_PX - 1, small, side);
    }

    function paintBars(has) {
      var c = V.ink(document.documentElement);
      var W = Math.max(180, Math.round(bars.getBoundingClientRect().width || 260));
      var H = 74;
      var ctx = P.fitTo(bars, W, H).ctx;
      ctx.clearRect(0, 0, W, H);
      var bw = W / 10, base = H - 15, peak = 1e-9, j;
      for (j = 0; j < 10; j++) peak = Math.max(peak, Math.abs(logits[j]));
      var top = has ? C.argmax(logits) : -1;
      ctx.font = "9px " + MONO;
      for (j = 0; j < 10; j++) {
        var h = has ? (Math.max(0, logits[j]) / peak) * (base - 4) : 0;
        ctx.fillStyle = j === top ? c.accent : V.mix(c.border, c.ink, 0.25);
        ctx.fillRect(j * bw + 1, base - h, bw - 3, h);
        ctx.fillStyle = j === top ? c.accentInk : c.muted;
        ctx.textAlign = "center";
        ctx.fillText(String(j), j * bw + bw / 2 - 1, H - 3);
      }
      bars.setAttribute("aria-label", has
        ? "Column currents; column " + top + " is highest."
        : "No digit drawn yet.");
    }

    function classify() {
      var has = reduce();
      if (has) {
        C.logitsOne(small, 0, mach.weights, model.gain, model.rows, model.cols, logits);
        var top = C.argmax(logits);
        var order = [];
        for (var j = 0; j < 10; j++) order.push(j);
        order.sort(function (a, b) { return logits[b] - logits[a]; });
        guess.textContent = String(top);
        guess.classList.remove("none");
        second.textContent = "runner-up " + order[1] + " · margin "
          + (logits[order[0]] - logits[order[1]]).toFixed(2)
          + (testIdx >= 0 ? " · this one is really a " + model.labels[testIdx] : "");
      } else {
        guess.textContent = "—";
        guess.classList.add("none");
        second.textContent = "Nothing on the pad yet.";
      }
      paintSeen();
      paintBars(has);
    }

    function stroke(ev) {
      var rect = pad.getBoundingClientRect();
      var x = (ev.clientX - rect.left) / rect.width * PAD;
      var y = (ev.clientY - rect.top) / rect.height * PAD;
      // A soft round brush: a one-cell hard stamp on a 24-grid gives a stroke too
      // thin to survive the box-average down to six.
      var rad = 1.7;
      for (var i = Math.floor(y - rad); i <= Math.ceil(y + rad); i++) {
        for (var j = Math.floor(x - rad); j <= Math.ceil(x + rad); j++) {
          if (i < 0 || j < 0 || i >= PAD || j >= PAD) continue;
          var d = Math.sqrt((i + 0.5 - y) * (i + 0.5 - y) + (j + 0.5 - x) * (j + 0.5 - x));
          if (d > rad) continue;
          var add = 1 - d / rad;
          var at = i * PAD + j;
          cells[at] = Math.min(1, cells[at] + add * 0.85);
        }
      }
      testIdx = -1;
      paintPad();
      classify();
    }

    pad.addEventListener("pointerdown", function (ev) {
      drawing = true;
      pad.setPointerCapture(ev.pointerId);
      stroke(ev);
      ev.preventDefault();
    });
    pad.addEventListener("pointermove", function (ev) {
      if (drawing) { stroke(ev); ev.preventDefault(); }
    });
    ["pointerup", "pointercancel"].forEach(function (name) {
      pad.addEventListener(name, function () { drawing = false; });
    });

    function clear() {
      cells.fill(0);
      testIdx = -1;
      paintPad();
      classify();
    }
    clearBtn.addEventListener("click", clear);

    var pick = C.rng(77);
    loadBtn.addEventListener("click", function () {
      // Upsampling a frozen test digit onto the pad gives the keyboard-only reader
      // a way to operate this widget, and everyone else a reference for how
      // unforgiving six-by-six is once you have tried to draw one by hand.
      testIdx = Math.floor(pick() * model.n);
      var base = testIdx * model.rows, per = PAD / side;
      for (var i = 0; i < PAD; i++) {
        for (var j = 0; j < PAD; j++) {
          cells[i * PAD + j] =
            model.x[base + Math.floor(i / per) * side + Math.floor(j / per)];
        }
      }
      paintPad();
      classify();
    });

    P.onWidthChange(el, function () { paintBars(reduce()); });
    P.onThemeChange(function () { paintPad(); classify(); });

    paintPad();
    classify();
  }

  if (typeof window !== "undefined") window.SpinnDraw = { mount: mount };
})();
