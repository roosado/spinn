/*
 * xbar_view.js -- how a crossbar is drawn on this site.
 *
 * Four widgets draw the same three objects: the 6x6 input tile, the lattice of
 * devices, and the ten column currents. Each of those has one drawing here and
 * every widget calls it, for the reason plot.js exists one level down -- five
 * shallow copies of a rasteriser drifted apart in photonn until a bug fixed in
 * two of them survived in the third.
 *
 * The colour decision this module makes, once
 * ---------------------------------------------
 * A weight is a *difference of two device states*, so there are two things worth
 * seeing and they want different pictures.
 *
 *   `rails`      -- 720 devices, each cell split into its positive and negative
 *                   device. Teal fills with the positive rail's occupancy, amber
 *                   with the negative's. This is the view in which the pair is
 *                   visibly two objects, and in which an independent error draw on
 *                   each of them is visibly two draws.
 *   `effective`  -- 360 weights on a diverging ramp through the page ground:
 *                   amber for negative, teal for positive, the background colour
 *                   itself for zero. This is the view in which the trained pattern
 *                   is legible as a pattern.
 *
 * Both ramps are built from the page's own custom properties, so they follow the
 * theme toggle rather than carrying a second palette that would slowly disagree
 * with the first.
 */
(function () {
  "use strict";

  var P = (typeof window !== "undefined" && window.SpinnPlot) || require("./plot.js");

  /* ------------------------------------------------------------------ colour */

  var VARS = {
    ink: ["--ink", "#141b26"],
    dim: ["--ink-dim", "#3f4c60"],
    muted: ["--muted", "#6b7789"],
    border: ["--border", "#d8e0ec"],
    surface: ["--surface", "#ffffff"],
    surface2: ["--surface-2", "#eef2f8"],
    bg: ["--bg", "#f4f7fb"],
    accent: ["--accent", "#0f9e8f"],
    accent2: ["--accent-2", "#c9701f"],
    good: ["--good", "#2f8f52"],
    bad: ["--bad", "#c14a34"],
    // Text variants of the two sign colours. A canvas label is type and has to
    // clear the same contrast floor as type in the DOM; the fill values above are
    // for rules, bars and cells, where the floor does not apply.
    accentInk: ["--accent-ink", "#0b7d70"],
    accent2Ink: ["--accent-2-ink", "#a85a16"],
  };

  /** The site's ink, by this site's own property names. */
  function ink(root) {
    return P.readVars(root || document.documentElement, VARS);
  }

  function rgb(hex) {
    var h = String(hex).trim();
    if (h.charAt(0) === "#") h = h.slice(1);
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var v = parseInt(h, 16);
    if (isNaN(v)) return [0, 0, 0];
    return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
  }

  function mix(a, b, t) {
    var A = rgb(a), B = rgb(b);
    return "rgb(" + Math.round(A[0] + (B[0] - A[0]) * t) + ","
      + Math.round(A[1] + (B[1] - A[1]) * t) + ","
      + Math.round(A[2] + (B[2] - A[2]) * t) + ")";
  }

  /**
   * The diverging weight ramp: amber at -1, the page's own ground at 0, teal at +1.
   *
   * Grounding zero in the surface colour rather than in a third hue is what makes
   * a trained weight matrix readable at a glance: the devices doing nothing
   * disappear, and the pattern that remains is the part that classifies.
   */
  function weightColour(c, w) {
    if (w >= 0) return mix(c.surface2, c.accent, Math.min(1, w));
    return mix(c.surface2, c.accent2, Math.min(1, -w));
  }

  /** One device's own ramp: the fraction of its window it has been programmed to. */
  function railColour(c, occupancy, negative) {
    return mix(c.surface2, negative ? c.accent2 : c.accent, Math.min(1, Math.max(0, occupancy)));
  }

  /* ------------------------------------------------------------------ pieces */

  /** The 6x6 input, drawn as the pixels that become row voltages. */
  function drawInput(ctx, c, x, y, size, pixels, side) {
    var cell = size / side;
    for (var r = 0; r < side; r++) {
      for (var k = 0; k < side; k++) {
        var v = pixels[r * side + k];
        ctx.fillStyle = v > 0 ? mix(c.surface2, c.ink, 0.12 + 0.88 * v) : c.surface2;
        ctx.fillRect(x + k * cell, y + r * cell, cell - 1, cell - 1);
      }
    }
    ctx.strokeStyle = c.border;
    ctx.lineWidth = 1;
    ctx.strokeRect(x - 0.5, y - 0.5, size + 1, size + 1);
  }

  /**
   * The array. `mode` is "rails" or "effective"; see the module comment.
   *
   * Devices are drawn without a gap between rows on purpose. A crossbar is a
   * continuous sheet of wiring and the drawing that separates every cell into its
   * own tile reads as a spreadsheet, which is the wrong mental model for a thing
   * whose defining property is that its cells share a wire.
   */
  function drawArray(ctx, c, geom, state) {
    var rows = geom.rows, cols = geom.cols;
    var cw = geom.w / cols, ch = geom.h / rows;
    var i, j, idx;
    ctx.clearRect(geom.x, geom.y, geom.w, geom.h);
    for (i = 0; i < rows; i++) {
      for (j = 0; j < cols; j++) {
        idx = i * cols + j;
        var px = geom.x + j * cw, py = geom.y + i * ch;
        if (state.mode === "rails") {
          ctx.fillStyle = railColour(c, state.rails.gp[idx], false);
          ctx.fillRect(px, py, cw / 2 - 0.5, ch - 0.5);
          ctx.fillStyle = railColour(c, state.rails.gn[idx], true);
          ctx.fillRect(px + cw / 2, py, cw / 2 - 0.5, ch - 0.5);
        } else {
          ctx.fillStyle = weightColour(c, state.weights[idx]);
          ctx.fillRect(px, py, cw - 0.5, ch - 0.5);
        }
      }
    }
    ctx.strokeStyle = c.border;
    ctx.lineWidth = 1;
    ctx.strokeRect(geom.x - 0.5, geom.y - 0.5, geom.w + 1, geom.h + 1);
  }

  /**
   * The row drive: one mark per input, at the height of its own row of devices.
   *
   * These are the voltages. Drawing them against the array rather than beside it
   * is the point of the figure -- a reader should be able to see that a bright
   * pixel is a driven row, and that a driven row is what a column sums.
   */
  function drawDrive(ctx, c, x, w, geom, v, reveal) {
    var rows = geom.rows, ch = geom.h / rows;
    var shown = reveal === undefined ? rows : reveal;
    for (var i = 0; i < rows; i++) {
      var y = geom.y + i * ch + ch / 2;
      ctx.strokeStyle = c.border;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + w, y);
      ctx.stroke();
      if (i >= shown || !(v[i] > 0)) continue;
      ctx.strokeStyle = mix(c.border, c.ink, 0.25 + 0.75 * v[i]);
      ctx.lineWidth = Math.max(1, 2.4 * v[i]);
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + w, y);
      ctx.stroke();
    }
  }

  /**
   * The ten column currents, as bars hanging below the array they came out of.
   *
   * Signed, because a differential pair produces a signed current and the sign is
   * the whole reason the pair exists: bars grow down for positive and up for
   * negative from a zero rule, and the winning column is the one that reached
   * furthest down.
   */
  function drawColumns(ctx, c, geom, y0, height, logits, winner, label, grow) {
    var cols = geom.cols, cw = geom.w / cols;
    var g = grow === undefined ? 1 : grow;
    var peak = 0, j;
    for (j = 0; j < cols; j++) peak = Math.max(peak, Math.abs(logits[j]));
    if (peak <= 0) peak = 1;
    // The zero rule sits high in the band, not in the middle of it. A column that
    // drew less current than the others is a real and uninteresting outcome; the
    // one the reader is looking for is the largest positive. Splitting the band
    // 24/66 keeps the sign honest and stops a large negative from being the
    // tallest thing on the figure -- which, when the answer is a positive column,
    // reads as the wrong column winning.
    var mid = y0 + height * 0.28;
    var up = height * 0.24, down = height * 0.66;

    ctx.strokeStyle = c.border;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(geom.x, mid + 0.5);
    ctx.lineTo(geom.x + geom.w, mid + 0.5);
    ctx.stroke();

    for (j = 0; j < cols; j++) {
      var x = geom.x + j * cw;
      var pos = logits[j] >= 0;
      var h = (logits[j] / peak) * (pos ? down : up) * g;
      var win = j === winner;
      // Sign is carried twice, by direction and by the page's own sign colours,
      // so neither has to be read on its own.
      ctx.fillStyle = win ? c.accent
        : (pos ? mix(c.border, c.accent, 0.34) : mix(c.border, c.accent2, 0.34));
      if (h >= 0) ctx.fillRect(x, mid, cw - 1.5, h);
      else ctx.fillRect(x, mid + h, cw - 1.5, -h);

      if (label) {
        ctx.fillStyle = win ? c.accentInk : c.muted;
        ctx.font = (win ? "600 " : "") + "11px " + label;
        ctx.textAlign = "center";
        ctx.fillText(String(j), x + cw / 2 - 0.75, y0 + height + 13);
      }
    }
  }

  /* -------------------------------------------------------------------- DOM */

  /** A labelled readout: mono value over a small caption. Used by every widget. */
  function readout(cls, value, label) {
    return P.el("div", cls, '<span class="v">' + value + '</span><span class="l">' + label + "</span>");
  }

  var API = {
    VARS: VARS, ink: ink, rgb: rgb, mix: mix,
    weightColour: weightColour, railColour: railColour,
    drawInput: drawInput, drawArray: drawArray, drawDrive: drawDrive,
    drawColumns: drawColumns, readout: readout,
  };

  if (typeof module !== "undefined" && module.exports) module.exports = API;
  if (typeof window !== "undefined") window.SpinnView = API;
})();
