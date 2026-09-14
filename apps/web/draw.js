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
 *
 * The pad takes a keyboard as well as a pointer. Arrow keys move a pen over the
 * 24-grid, a whole ruled square of the six at a time with Shift, and Space puts it
 * down or lifts it; with the pen down, every cell it passes over is dabbed with the
 * same brush a pointer uses. Before, the pad was a tab stop that ignored every key,
 * and "Load a test digit" was the only way in -- which lets a reader watch the
 * machine, but never write for it.
 */
(function () {
  "use strict";

  var P = window.SpinnPlot, V = window.SpinnView, C = window.SpinnCrossbar;

  var CSS = ""
    + ".dw{display:grid;grid-template-columns:auto auto minmax(200px,340px);"
    + "gap:20px 30px;align-items:start;justify-content:start;}"
    + "@media (max-width:720px){.dw{grid-template-columns:1fr 1fr;}"
    + ".dw-out{grid-column:1 / -1;}}"
    // The 168px pad, the 108px tile and the gap between them need 306px, and a 320px
    // screen has 272 inside its gutters. One column, rather than a sideways scroll.
    + "@media (max-width:380px){.dw{grid-template-columns:1fr;}}"
    + ".dw-k{font-family:var(--mono);font-size:.75rem;letter-spacing:.12em;"
    + "text-transform:uppercase;color:var(--muted);margin:0 0 8px;}"
    + ".dw-pad{border:1px solid var(--border);border-radius:10px;background:var(--surface);"
    + "touch-action:none;cursor:crosshair;display:block;}"
    + ".dw-pad:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}"
    + ".dw-seen{border:1px solid var(--border);border-radius:10px;display:block;}"
    + ".dw-guess{font-family:var(--serif);font-size:4.2rem;line-height:.86;font-weight:600;"
    + "color:var(--accent-ink);font-variant-numeric:tabular-nums;}"
    + ".dw-guess.none{color:var(--muted);}"
    + "@media (max-width:720px){.dw-guess{font-size:3.2rem;}}"
    + ".dw-second{font-family:var(--mono);font-size:.8125rem;color:var(--muted);"
    + "margin:6px 0 0;font-variant-numeric:tabular-nums;}"
    + ".dw-bars{display:block;width:100%;max-width:330px;margin-top:12px;}"
    + ".dw-tools{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap;}"
    + ".dw-btn{font-family:var(--mono);font-size:.75rem;letter-spacing:.1em;"
    + "text-transform:uppercase;background:transparent;color:var(--ink-dim);"
    + "border:1px solid var(--border);border-radius:7px;padding:6px 12px;cursor:pointer;"
    + "transition:color .15s,border-color .15s,background .15s;}"
    + ".dw-btn:hover{color:var(--ink);border-color:var(--accent);background:var(--accent-soft);}"
    + ".dw-btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}"
    + ".dw-hint{font-size:.8125rem;color:var(--muted);margin:12px 0 0;line-height:1.5;}"
    // The keys, shown to whoever is pressing them: on keyboard focus, and not to a
    // reader who drew with a mouse. A screen reader has them as the pad's description
    // either way. Capped at the pad's width, or the sentence would widen its column.
    + ".dw-keys{display:none;max-width:168px;}"
    + ".dw-pad:focus-visible~.dw-keys{display:block;}"
    + ".dw-vh{position:absolute;width:1px;height:1px;margin:-1px;padding:0;border:0;"
    + "overflow:hidden;clip-path:inset(50%);white-space:nowrap;}";

  var PAD = 24;        // the pad's own grid
  var PAD_PX = 168;    // its drawn size, 7 screen pixels per cell
  var TILE_PX = 108;
  var BRUSH = 1.7;     // the brush's radius, in pad cells
  //: How long the pad has to be still before the verdict is read out. Every pointer
  //: event reclassifies, and a live region that spoke each one would be reading out
  //: numbers faster than anyone can hear them.
  var SPEAK_MS = 700;
  //: The arrow keys, as one cell's step.
  var MOVES = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };

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
    // An application because it behaves as one: it takes the arrow keys for itself,
    // which a screen reader left in browse mode would otherwise keep.
    pad.setAttribute("role", "application");
    pad.setAttribute("aria-roledescription", "drawing pad");
    pad.setAttribute("aria-label", "Draw a digit");
    pad.setAttribute("aria-describedby", "dw-keys");
    padBox.appendChild(pad);
    var tools = P.el("div", "dw-tools");
    var clearBtn = P.el("button", "dw-btn", "Clear");
    clearBtn.type = "button";
    var loadBtn = P.el("button", "dw-btn", "Load a test digit");
    loadBtn.type = "button";
    tools.appendChild(clearBtn);
    tools.appendChild(loadBtn);
    padBox.appendChild(tools);
    var keys = P.el("p", "dw-hint dw-keys",
      "Arrow keys move the pen, a whole square at a time with Shift. Space puts it "
      + "down or lifts it; Delete clears the pad.");
    keys.id = "dw-keys";
    padBox.appendChild(keys);

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
    var bars = document.createElement("canvas");
    bars.setAttribute("role", "img");
    bars.className = "dw-bars";
    // The verdict for a screen reader, spoken once the pad goes still. The visible
    // line under the numeral changes with every dab, and is deliberately not live.
    var status = P.el("p", "dw-vh");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    outBox.appendChild(guess);
    outBox.appendChild(second);
    outBox.appendChild(bars);
    outBox.appendChild(status);

    grid.appendChild(padBox);
    grid.appendChild(seenBox);
    grid.appendChild(outBox);
    el.appendChild(grid);

    var cells = new Float64Array(PAD * PAD);
    var small = new Float64Array(side * side);
    var logits = new Float64Array(model.cols);
    var drawing = false, testIdx = -1;
    // The keyboard's pen: where it is, whether it is down, and whether it is drawn.
    // It is drawn only while the pad has keyboard focus.
    var pen = { x: PAD / 2 - 0.5, y: PAD / 2 - 0.5, down: false, shown: false };
    var speakTimer = 0;

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
      // The keyboard's pen: a ring the size of the brush, with a dot in it when down.
      if (pen.shown && document.activeElement === pad) {
        var px = pen.x * cell, py = pen.y * cell;
        ctx.strokeStyle = c.accent;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(px, py, BRUSH * cell, 0, Math.PI * 2);
        ctx.stroke();
        if (pen.down) {
          ctx.fillStyle = c.accent;
          ctx.beginPath();
          ctx.arc(px, py, 2.5, 0, Math.PI * 2);
          ctx.fill();
        }
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
      ctx.font = V.font();
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

    /**
     * Say `text` now: the answer to a key, not a running commentary. A verdict that
     * is already waiting is left to follow it -- lifting the pen at the end of a
     * stroke must not swallow what the stroke drew.
     */
    function say(text) {
      status.textContent = text;
    }

    /** Classify the pad; with `speak`, read the verdict out once the pad is still. */
    function classify(speak) {
      var has = reduce(), spoken;
      if (has) {
        C.logitsOne(small, 0, mach.weights, model.gain, model.rows, model.cols, logits);
        var top = C.argmax(logits);
        var order = [];
        for (var j = 0; j < 10; j++) order.push(j);
        order.sort(function (a, b) { return logits[b] - logits[a]; });
        var really = testIdx < 0 ? ""
          : (model.labels[testIdx] === 8 ? "an " : "a ") + model.labels[testIdx];
        guess.textContent = String(top);
        guess.classList.remove("none");
        second.textContent = "runner-up " + order[1] + " · margin "
          + (logits[order[0]] - logits[order[1]]).toFixed(2)
          + (really ? " · this one is really " + really : "");
        spoken = "The array says " + top + ", runner-up " + order[1]
          + (really ? ". This one is really " + really : "") + ".";
      } else {
        guess.textContent = "—";
        guess.classList.add("none");
        second.textContent = "Nothing on the pad yet.";
        spoken = "Nothing on the pad yet.";
      }
      paintSeen();
      paintBars(has);
      if (speak) {
        window.clearTimeout(speakTimer);
        speakTimer = window.setTimeout(function () { status.textContent = spoken; }, SPEAK_MS);
      }
    }

    /** One dab of a soft round brush, centred at (x, y) in pad cells. */
    function stamp(x, y) {
      // Soft and round: a one-cell hard stamp on a 24-grid gives a stroke too thin
      // to survive the box-average down to six.
      for (var i = Math.floor(y - BRUSH); i <= Math.ceil(y + BRUSH); i++) {
        for (var j = Math.floor(x - BRUSH); j <= Math.ceil(x + BRUSH); j++) {
          if (i < 0 || j < 0 || i >= PAD || j >= PAD) continue;
          var d = Math.sqrt((i + 0.5 - y) * (i + 0.5 - y) + (j + 0.5 - x) * (j + 0.5 - x));
          if (d > BRUSH) continue;
          var at = i * PAD + j;
          cells[at] = Math.min(1, cells[at] + (1 - d / BRUSH) * 0.85);
        }
      }
      testIdx = -1;
    }

    //: Where the pointer's stroke was at its last event, in pad cells; null between
    //: strokes.
    var last = null;

    function stroke(ev) {
      var rect = pad.getBoundingClientRect();
      var x = (ev.clientX - rect.left) / rect.width * PAD;
      var y = (ev.clientY - rect.top) / rect.height * PAD;
      if (last) {
        // Joined, half a cell at a time. A fast stroke delivers its pointer events
        // cells apart, and a dab at each of them alone drew a row of dots where the
        // hand drew a line.
        var dx = x - last[0], dy = y - last[1];
        var n = Math.ceil(Math.sqrt(dx * dx + dy * dy) / 0.5);
        for (var k = 1; k <= n; k++) stamp(last[0] + dx * k / n, last[1] + dy * k / n);
      } else {
        stamp(x, y);
      }
      last = [x, y];
      paintPad();
      classify(true);
    }

    pad.addEventListener("pointerdown", function (ev) {
      drawing = true;
      last = null;
      // A pointer takes over from the keyboard: the keyboard's pen lifts and hides.
      pen.shown = false;
      pen.down = false;
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

    pad.addEventListener("keydown", function (ev) {
      if (ev.altKey || ev.ctrlKey || ev.metaKey) return;
      var move = MOVES[ev.key], changed = false;
      if (move) {
        // With the pen down every cell passed over is dabbed, so a Shift move is
        // still a line and not two dots a square apart.
        for (var n = ev.shiftKey ? PAD / side : 1; n > 0; n--) {
          pen.x = Math.max(0.5, Math.min(PAD - 0.5, pen.x + move[0]));
          pen.y = Math.max(0.5, Math.min(PAD - 0.5, pen.y + move[1]));
          if (pen.down) { stamp(pen.x, pen.y); changed = true; }
        }
      } else if (ev.key === " " || ev.key === "Enter") {
        pen.down = !pen.down;
        if (pen.down) { stamp(pen.x, pen.y); changed = true; }
        say(pen.down ? "Pen down." : "Pen up.");
      } else if (ev.key === "Escape" && pen.down) {
        pen.down = false;
        say("Pen up.");
      } else if (ev.key === "Delete" || ev.key === "Backspace") {
        cells.fill(0);
        testIdx = -1;
        changed = true;
      } else {
        return;
      }
      ev.preventDefault();
      pen.shown = true;
      paintPad();
      // A pen moved while up changed nothing, and re-reading an unchanged verdict at
      // every step would bury the one that did change.
      if (changed) classify(true);
    });
    pad.addEventListener("focus", function () {
      // Tabbed to, the pen shows at once; clicked, it waits for a key.
      var keyed = false;
      try { keyed = pad.matches(":focus-visible"); } catch (e) { keyed = false; }
      if (keyed) { pen.shown = true; paintPad(); }
    });
    pad.addEventListener("blur", function () {
      pen.down = false;
      paintPad();
    });

    function clear() {
      cells.fill(0);
      testIdx = -1;
      paintPad();
      classify(true);
    }
    clearBtn.addEventListener("click", clear);

    var pick = C.rng(77);
    loadBtn.addEventListener("click", function () {
      // Upsampling a frozen test digit onto the pad gives every reader a reference
      // for how unforgiving six-by-six is once you have tried to draw one by hand.
      testIdx = Math.floor(pick() * model.n);
      var base = testIdx * model.rows, per = PAD / side;
      for (var i = 0; i < PAD; i++) {
        for (var j = 0; j < PAD; j++) {
          cells[i * PAD + j] =
            model.x[base + Math.floor(i / per) * side + Math.floor(j / per)];
        }
      }
      paintPad();
      classify(true);
    });

    P.onWidthChange(el, function () { paintBars(reduce()); });
    P.onThemeChange(function () { paintPad(); classify(); });

    paintPad();
    classify();
  }

  if (typeof window !== "undefined") window.SpinnDraw = { mount: mount };
})();
