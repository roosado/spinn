/*
 * device.js -- one device, and what "states per device" costs the machine.
 *
 * The knob this widget exposes is the one that makes an MTJ and a domain-wall
 * device the same model rather than two machines. A magnetic tunnel junction has
 * two stable configurations, parallel and antiparallel, so it stores one bit as a
 * conductance. A domain-wall device stores a wall *position*, and a position is
 * continuous until pinning sites make it discrete -- so it holds a handful of
 * levels instead of two. Same crossbar, same arithmetic, one parameter.
 *
 * Two things are drawn side by side because the reader needs to hold them
 * together: the device, which has `states` levels, and the *weight*, which has
 * `2 * states - 1` of them because a differential pair takes a difference. That
 * asymmetry is the entire argument for spending two devices on one weight, and it
 * is much easier to see as two rows of ticks than to read as a sentence.
 *
 * The accuracy under the slider is computed here and now, over all two thousand
 * frozen test images, with the same quantiser both other implementations use.
 */
(function () {
  "use strict";

  var P = window.SpinnPlot, C = window.SpinnCrossbar;

  var CSS = ""
    + ".dv-grid{display:grid;grid-template-columns:minmax(180px,.62fr) minmax(280px,1fr);"
    + "gap:26px 40px;align-items:start;max-width:940px;}"
    + "@media (max-width:720px){.dv-grid{grid-template-columns:1fr;gap:20px;}}"
    + ".dv-k{font-family:var(--mono);font-size:.75rem;letter-spacing:.16em;"
    + "text-transform:uppercase;color:var(--muted);margin:0 0 10px;}"
    + ".dv-stack{display:block;width:100%;max-width:250px;height:auto;}"
    + ".dv-note{font-size:.86rem;color:var(--muted);margin:10px 0 0;line-height:1.5;}"
    + ".dv-lat{display:block;width:100%;}"
    + ".dv-rowlab{display:flex;justify-content:space-between;align-items:baseline;"
    + "font-family:var(--mono);font-size:.75rem;letter-spacing:.1em;text-transform:uppercase;"
    + "color:var(--muted);margin:16px 0 4px;}"
    + ".dv-rowlab b{color:var(--ink);font-weight:600;font-variant-numeric:tabular-nums;"
    + "letter-spacing:0;}"
    + ".dv-ctl{margin-top:26px;border-top:1px solid var(--border);padding-top:18px;}"
    + ".dv-out{display:flex;flex-wrap:wrap;gap:18px 26px;margin-top:16px;}"
    + ".dv-out div{min-width:104px;}"
    + ".dv-out .v{display:block;font-family:var(--mono);font-size:1.24rem;font-weight:600;"
    + "color:var(--ink);font-variant-numeric:tabular-nums;}"
    + ".dv-out .v.warn{color:var(--accent-2-ink);}"
    + ".dv-out .l{display:block;font-size:.76rem;color:var(--muted);margin-top:2px;}";

  var MONO = 'ui-monospace,"Cascadia Code","SF Mono",Consolas,monospace';

  /**
   * The device itself: two magnetic layers, a barrier, and an arrow that turns.
   *
   * Drawn as SVG rather than canvas because it is a diagram and not a plot -- it
   * has to stay crisp at any zoom, and its parts want to be elements a screen
   * reader can be told about rather than pixels.
   */
  function stack(level, states) {
    var t = states > 1 ? level / (states - 1) : 0;
    // A binary device flips its free layer; a multi-level device slides a wall.
    var binary = states === 2;
    var arrow = binary
      ? (t > 0.5 ? "M 34 34 L 74 34" : "M 74 34 L 34 34")
      : null;
    var wallX = 30 + t * 66;
    var body = binary
      ? '<g stroke="var(--accent)" stroke-width="2.4" fill="none" '
        + 'marker-end="url(#dvhead)"><path d="' + arrow + '"/></g>'
      : '<rect x="30" y="24" width="' + (wallX - 30).toFixed(1) + '" height="20" '
        + 'fill="var(--accent)" opacity=".78"/>'
        + '<rect x="' + wallX.toFixed(1) + '" y="24" width="' + (96 - wallX).toFixed(1)
        + '" height="20" fill="var(--accent-2)" opacity=".5"/>'
        + '<line x1="' + wallX.toFixed(1) + '" y1="20" x2="' + wallX.toFixed(1)
        + '" y2="48" stroke="var(--ink)" stroke-width="1.6"/>';

    return ''
      + '<svg class="dv-stack" viewBox="0 0 126 108" role="img" aria-label="'
      + (binary ? "A magnetic tunnel junction, free layer " + (t > 0.5 ? "parallel" : "antiparallel")
        : "A domain-wall device with the wall at position " + level + " of " + (states - 1))
      + '">'
      + '<defs><marker id="dvhead" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" '
      + 'markerHeight="5" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="var(--accent)"/>'
      + "</marker></defs>"
      // fixed reference layer
      + '<rect x="30" y="62" width="66" height="20" fill="var(--ink-dim)" opacity=".33"/>'
      + '<g stroke="var(--ink-dim)" stroke-width="2" opacity=".8" marker-end="url(#dvhead)">'
      + '<path d="M 44 72 L 82 72"/></g>'
      // barrier
      + '<rect x="30" y="52" width="66" height="8" fill="var(--border)"/>'
      // free layer / track
      + '<rect x="30" y="24" width="66" height="20" fill="var(--surface-2)" '
      + 'stroke="var(--border)"/>'
      + body
      // contacts
      + '<rect x="18" y="16" width="10" height="76" fill="var(--border)"/>'
      + '<rect x="98" y="16" width="10" height="76" fill="var(--border)"/>'
      + '<text x="63" y="14" text-anchor="middle" font-family="' + MONO + '" font-size="8" '
      + 'fill="var(--muted)" letter-spacing="1.4">' + (binary ? "FREE LAYER" : "WALL TRACK")
      + "</text>"
      + '<text x="63" y="98" text-anchor="middle" font-family="' + MONO + '" font-size="8" '
      + 'fill="var(--muted)" letter-spacing="1.4">REFERENCE</text>'
      + "</svg>";
  }

  /** Two rows of ticks: what one device can be, and what one weight can be. */
  function lattice(canvas, states, level) {
    var c = window.SpinnView.ink(document.documentElement);
    var ink = c.ink, muted = c.muted, border = c.border;
    var accent = c.accent, accent2 = c.accent2;

    var W = Math.max(220, Math.round(canvas.getBoundingClientRect().width || 380));
    var H = 96;
    var f = P.fitTo(canvas, W, H), ctx = f.ctx;
    ctx.clearRect(0, 0, W, H);
    var pad = 10, span = W - pad * 2;

    function row(y, n, colourAt, mark) {
      ctx.strokeStyle = border;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad, y + 0.5);
      ctx.lineTo(pad + span, y + 0.5);
      ctx.stroke();
      // Above ~40 ticks the marks merge into a grey band, which is the honest
      // picture of "effectively continuous" and the reason the cap is not lower.
      var thin = n > 40;
      for (var i = 0; i < n; i++) {
        var x = pad + (n === 1 ? span / 2 : (i / (n - 1)) * span);
        ctx.strokeStyle = colourAt(i, n);
        ctx.lineWidth = thin ? 1 : 1.6;
        ctx.beginPath();
        ctx.moveTo(x, y - (thin ? 5 : 8));
        ctx.lineTo(x, y + (thin ? 5 : 8));
        ctx.stroke();
      }
      if (mark >= 0 && n <= 40) {
        var mx = pad + (n === 1 ? span / 2 : (mark / (n - 1)) * span);
        ctx.fillStyle = ink;
        ctx.beginPath();
        ctx.arc(mx, y, 3.6, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    row(26, states, function () { return accent; }, level);
    row(74, 2 * states - 1, function (i, n) {
      var t = n === 1 ? 0 : i / (n - 1) * 2 - 1;
      return t < -0.01 ? accent2 : (t > 0.01 ? accent : muted);
    }, -1);

    ctx.font = "10px " + MONO;
    ctx.fillStyle = muted;
    ctx.textAlign = "left";
    ctx.fillText("g_min", pad, 50);
    ctx.fillText("−1", pad, 96);
    ctx.textAlign = "right";
    ctx.fillText("g_max", pad + span, 50);
    ctx.fillText("+1", pad + span, 96);
  }

  function mount(el) {
    P.injectStyle("spinn-device-style", CSS);
    var model = C.load(window.SpinnData);

    var grid = P.el("div", "dv-grid");
    var left = P.el("div", "", '<p class="dv-k">One device</p><div class="dv-stackwrap"></div>'
      + '<p class="dv-note"></p>');
    var right = P.el("div", "",
      '<div class="dv-rowlab"><span>What one device can hold</span><b class="dv-n"></b></div>'
      + '<canvas class="dv-lat"></canvas>');
    grid.appendChild(left);
    grid.appendChild(right);

    var ctl = P.el("div", "dv-ctl");
    right.appendChild(ctl);
    var slider = P.el("div", "sp-field",
      '<label for="dv-states">States per device</label>'
      + '<input id="dv-states" type="range" min="0" max="7" step="1" value="7">'
      + '<output for="dv-states"></output>');
    var out = P.el("div", "dv-out",
      '<div><span class="v acc"></span><span class="l">accuracy on the frozen test set</span></div>'
      + '<div><span class="v bits"></span><span class="l">effective bits per weight</span></div>'
      + '<div><span class="v pair"></span><span class="l">weights a pair can represent</span></div>');
    ctl.appendChild(slider);
    ctl.appendChild(out);

    el.appendChild(grid);

    // The magnitudes the budget actually swept, so the reader's slider lands on
    // the points that were measured rather than on interpolations between them.
    var LADDER = [2, 3, 4, 5, 7, 9, 17, 33];
    var input = slider.querySelector("input");
    var outEl = slider.querySelector("output");
    var stackWrap = left.querySelector(".dv-stackwrap");
    var note = left.querySelector(".dv-note");
    var canvas = right.querySelector(".dv-lat");
    var nEl = right.querySelector(".dv-n");
    var accEl = out.querySelector(".acc"), bitsEl = out.querySelector(".bits");
    var pairEl = out.querySelector(".pair");

    var level = 1;

    function render() {
      var states = LADDER[Number(input.value)];
      level = Math.min(level, states - 1);
      var res = C.evaluate(model, C.machine(model, { states: states }));
      var bits = Math.log(2 * states - 1) / Math.LN2;

      outEl.textContent = states;
      nEl.textContent = states + " levels";
      stackWrap.innerHTML = stack(level, states);
      note.innerHTML = states === 2
        ? "Two magnetisations, parallel and antiparallel. This is a magnetic tunnel "
          + "junction, and it stores one bit as a conductance."
        : "A domain wall parked at one of " + states + " pinning sites. The wall's "
          + "position sets how much of the track conducts.";
      lattice(canvas, states, level);

      accEl.textContent = res.accuracy.toFixed(4);
      accEl.classList.toggle("warn", res.accuracy < model.threshold);
      bitsEl.textContent = bits.toFixed(2);
      pairEl.textContent = 2 * states - 1;
    }

    input.addEventListener("input", render);
    // Clicking the device steps it through its own states, which is the fastest
    // way to feel what "a state" is without reading a caption about it.
    stackWrap.addEventListener("click", function () {
      var states = LADDER[Number(input.value)];
      level = (level + 1) % states;
      render();
    });
    P.onWidthChange(el, render);
    P.onThemeChange(render);
    render();
  }

  if (typeof window !== "undefined") window.SpinnDevice = { mount: mount };
})();
