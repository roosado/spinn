/*
 * crossbar.js -- the forward pass, and the three error sources, in the browser.
 *
 * This is a third implementation of arithmetic that already exists twice: in
 * `spinn/crossbar.py` (the ideal design) and in `spinn-hw/+model/` plus
 * `spinn-hw/+err/` (the as-built measurement). A third copy is normally the point
 * at which you stop and share one, and that is not available here -- the seam
 * between the two existing copies is one-directional on purpose, and neither
 * Python nor MATLAB runs in a reader's browser.
 *
 * So it is a copy, and the way a copy stays honest is that it is checked against
 * the other two rather than trusted. `tests/test_web_crossbar.py` runs this file
 * under Node and asserts it reproduces every magnitude in
 * `exports/error_budget.json` that does not involve a random draw -- nine
 * quantisation levels and nine wire resistances, to the sample. If this file ever
 * drifts from the physics it is drawing, that test says so.
 *
 * What is NOT reproducible sample-for-sample is error source 1. MATLAB draws from
 * a Mersenne Twister seeded by `mc.sweep`'s partitioning; this draws from a small
 * PRNG. Same distribution, different stream, so a sigma sweep here agrees with the
 * recorded one in mean and spread and not in any individual realisation. The page
 * says so where it matters, and the seed is exposed so a reader can at least
 * repeat their own run.
 *
 * ---------------------------------------------------------------------------
 * Two paths, and why the fast one is exact rather than approximate
 *
 * With ideal wires the conductance window and the read voltage cancel in the
 * decode, exactly:
 *
 *     logits = (I+ - I-) / (V_read * span)
 *            = V (G+ - G-) / (V_read * span)          [Kirchhoff]
 *            = (V / V_read) . (g+ - g-)               [g = (G - g_min) / span]
 *
 * so the browser can carry dimensionless inputs and rail *occupancies* in [0, 1]
 * and never mention a siemens. That is the fast path, and it is the whole reason
 * a slider can re-classify two thousand images between two frames.
 *
 * Error source 3 breaks it. A wire drop is `R * I`, and `I` is an absolute
 * current, so IR drop is the one source whose result depends on the value of
 * `g_min` and `g_max` -- which are UNSOURCED placeholders. The slow path
 * therefore reconstitutes real conductances and a real drive, and the page states
 * the dependence rather than hiding it behind a widget that looks equally
 * confident either way.
 */
(function () {
  "use strict";

  var ROWS = 36, COLS = 10;

  /* --------------------------------------------------------------- decoding */

  function bytes(b64) {
    var bin = typeof atob === "function"
      ? atob(b64)
      : Buffer.from(b64, "base64").toString("binary");
    var out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  /**
   * Expand the sparse image block written by apps/export_web_data.py.
   *
   * Three quarters of the pixels in a 6x6 MNIST digit are zero, so the file
   * carries a per-sample count, one index byte per non-zero and two value bytes.
   * The two halves of that format have to be read together; the exporter's
   * docstring is the other half of this comment.
   */
  function unpackImages(block) {
    var counts = bytes(block.counts);
    var idx = bytes(block.idx);
    var raw = bytes(block.val);
    var n = block.n, dim = block.dim, full = block.full;
    var x = new Float64Array(n * dim);
    var at = 0;
    for (var s = 0; s < n; s++) {
      var c = counts[s], base = s * dim;
      for (var k = 0; k < c; k++, at++) {
        // Little-endian uint16, assembled by hand: a Uint16Array view would need
        // the byte offset to be even, and a sparse stream gives no such promise.
        x[base + idx[at]] = (raw[at * 2] | (raw[at * 2 + 1] << 8)) / full;
      }
    }
    return x;
  }

  /**
   * Turn the generated data module into everything the widgets read.
   *
   * `x` holds the L-infinity normalised inputs, which is what the row drivers
   * deliver once the read voltage is divided back out.
   */
  function load(data) {
    var g = data.geometry;
    var w = new Float64Array(g.rows * g.cols);
    for (var i = 0; i < g.rows; i++) {
      for (var j = 0; j < g.cols; j++) w[i * g.cols + j] = data.weights[i][j];
    }
    return {
      rows: g.rows, cols: g.cols, side: g.side, devices: g.devices,
      n: data.images.n,
      x: unpackImages(data.images),
      labels: bytes(data.labels),
      weights: w,
      gain: data.readoutGain,
      ideal: data.idealAccuracy,
      threshold: data.threshold,
      op: data.operatingPoint,
      budget: data.budget,
    };
  }

  /* ---------------------------------------------------------------- physics */

  /**
   * Round half away from zero, as both existing implementations do.
   *
   * `Math.round` rounds half **up** -- towards positive infinity -- so it gives
   * -2 for -2.5 where Python's and MATLAB's conventions here give -3. A weight
   * sitting exactly between two device states is precisely where that shows up,
   * which makes it precisely the case a quantiser meets.
   */
  function roundHalfAway(v) {
    return v < 0 ? -Math.floor(-v + 0.5) : Math.floor(v + 0.5);
  }

  /**
   * Snap weights to the lattice a legal pair of device states can reach.
   *
   * `states` levels per device gives `2 * states - 1` effective weights under a
   * differential pair, because the effective weight is a *difference*. Rounding
   * each rail on its own instead collapses the pair to a sign bit -- see
   * spinn/crossbar.py, which explains the failure at length because it happened.
   */
  function quantise(weights, states) {
    if (!states) return weights;
    var n = states - 1;
    var out = new Float64Array(weights.length);
    for (var i = 0; i < weights.length; i++) out[i] = roundHalfAway(weights[i] * n) / n;
    return out;
  }

  /**
   * Programmed rail occupancies for every device, in [0, 1] of the window.
   *
   * Returns the positive and negative rails as one interleaved pair of arrays.
   * Under quantisation the pair is `(max(k, 0), max(-k, 0))` for the integer
   * level `k`, which is the representation drawing the least current -- and the
   * one whose zero weight is two devices in the same state.
   */
  function program(weights, states) {
    var len = weights.length;
    var gp = new Float64Array(len), gn = new Float64Array(len);
    if (!states) {
      for (var i = 0; i < len; i++) {
        var w = Math.max(-1, Math.min(1, weights[i]));
        gp[i] = (1 + w) / 2;
        gn[i] = (1 - w) / 2;
      }
      return { gp: gp, gn: gn };
    }
    var n = states - 1;
    for (var j = 0; j < len; j++) {
      var k = roundHalfAway(Math.max(-1, Math.min(1, weights[j])) * n);
      gp[j] = Math.max(k, 0) / n;
      gn[j] = Math.max(-k, 0) / n;
    }
    return { gp: gp, gn: gn };
  }

  /** A small deterministic PRNG, so a reader's run repeats when they repeat it. */
  function rng(seed) {
    var a = (seed >>> 0) || 1;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /** Standard normals, Box-Muller, drawn in pairs and handed out one at a time. */
  function normals(seed) {
    var u = rng(seed), spare = null;
    return function () {
      if (spare !== null) { var s = spare; spare = null; return s; }
      var a = 1 - u(), b = u();
      var r = Math.sqrt(-2 * Math.log(a)), th = 2 * Math.PI * b;
      spare = r * Math.sin(th);
      return r * Math.cos(th);
    };
  }

  /**
   * Error source 1: an independent draw on every device, clamped to the window.
   *
   * `sigma` is a fraction of the conductance span, which is what makes it convert
   * straight into the comparison unit: effective bits = -log2(sigma). Under a
   * differential pair this is two draws per weight, which is the cost side of the
   * scheme -- the effective weight's sigma is larger by sqrt(2), against a signed
   * range that is twice as wide.
   *
   * The clamp is physical, not defensive: a device cannot be programmed outside
   * the states it has, and a weight already near an edge therefore sees an
   * asymmetric error. That is a real effect of the window being small.
   */
  function vary(rails, sigma, seed) {
    if (!(sigma > 0)) return rails;
    var draw = normals(seed);
    var gp = new Float64Array(rails.gp), gn = new Float64Array(rails.gn);
    for (var i = 0; i < gp.length; i++) {
      gp[i] = Math.max(0, Math.min(1, gp[i] + sigma * draw()));
      gn[i] = Math.max(0, Math.min(1, gn[i] + sigma * draw()));
    }
    return { gp: gp, gn: gn };
  }

  /** The effective weight each pair represents: the difference of its two rails. */
  function effective(rails) {
    var w = new Float64Array(rails.gp.length);
    for (var i = 0; i < w.length; i++) w[i] = rails.gp[i] - rails.gn[i];
    return w;
  }

  /* ------------------------------------------------------------- the fast path */

  /** Logits for one sample against an effective-weight matrix. Ohm and Kirchhoff. */
  function logitsOne(x, offset, w, gain, rows, cols, out) {
    var o = out || new Float64Array(cols);
    for (var j = 0; j < cols; j++) o[j] = 0;
    for (var i = 0; i < rows; i++) {
      var v = x[offset + i];
      if (v === 0) continue;              // three quarters of a 6x6 digit
      var base = i * cols;
      for (var k = 0; k < cols; k++) o[k] += v * w[base + k];
    }
    for (var m = 0; m < cols; m++) o[m] *= gain;
    return o;
  }

  function argmax(v) {
    var best = 0;
    for (var i = 1; i < v.length; i++) if (v[i] > v[best]) best = i;
    return best;
  }

  /* ------------------------------------------------------------- the slow path */

  /**
   * Error source 3: finite wire resistance, first order and deliberately not
   * iterated.
   *
   * Row drivers sit at the column-1 edge and column sense amplifiers at the row-1
   * edge. The row-wire segment before column j carries everything every cell from
   * j onward draws, so a cell sees its driver voltage less the accumulated drop of
   * the segments before it; the column wire does the same in the other direction,
   * lifting the far end off the amplifier's virtual ground. Cells furthest from
   * both edges are starved worst, and the effect grows with array size -- which is
   * why the row states the array size beside the number.
   *
   * The row-side drop is precomputed. Substituting the two reverse-cumulative sums
   * gives
   *
   *     dropRow(i,j) = R * V(i) * SUM_j'' G(i,j'') * min(j'' + 1, j + 1)
   *
   * whose second factor does not depend on the sample. Hoisting it out is what
   * lets this run over two thousand images inside a slider drag; the column-side
   * drop genuinely depends on the sample and is computed per image.
   */
  function irContext(g, rows, cols, gMin, span) {
    var G = new Float64Array(rows * cols), A = new Float64Array(rows * cols);
    var i, j, jj;
    for (i = 0; i < rows * cols; i++) G[i] = gMin + g[i] * span;
    for (i = 0; i < rows; i++) {
      for (j = 0; j < cols; j++) {
        var acc = 0;
        for (jj = 0; jj < cols; jj++) acc += G[i * cols + jj] * Math.min(jj + 1, j + 1);
        A[i * cols + j] = acc;
      }
    }
    return { G: G, A: A };
  }

  function irColumnCurrents(ctx, v, rows, cols, R, out) {
    var G = ctx.G, A = ctx.A;
    var i, j, idx;
    // Reverse cumulative sum down each column of I0 = V * G, then a forward
    // cumulative sum of that: the drop delivered to row i of column j.
    var rev = new Float64Array(rows * cols);
    for (j = 0; j < cols; j++) {
      var run = 0;
      for (i = rows - 1; i >= 0; i--) {
        idx = i * cols + j;
        run += v[i] * G[idx];
        rev[idx] = run;
      }
    }
    for (j = 0; j < cols; j++) out[j] = 0;
    var colDrop = new Float64Array(cols);
    for (i = 0; i < rows; i++) {
      for (j = 0; j < cols; j++) {
        idx = i * cols + j;
        colDrop[j] += R * rev[idx];
        var veff = v[i] - R * v[i] * A[idx] - colDrop[j];
        out[j] += veff * G[idx];
      }
    }
    return out;
  }

  /* -------------------------------------------------------------- evaluation */

  /**
   * Build a callable that turns one sample index into ten logits.
   *
   * `opts`: `states`, `sigma`, `seed`, `wireOhm`. The returned object also carries
   * the effective weights it is using, because every widget that evaluates also
   * draws the array it evaluated with, and re-deriving them would be a second
   * chance to disagree.
   */
  function machine(model, opts) {
    var o = opts || {};
    var rows = model.rows, cols = model.cols, gain = model.gain;
    var rails = vary(program(model.weights, o.states), o.sigma || 0, o.seed || 1);
    var w = effective(rails);
    var R = o.wireOhm || 0;

    if (!(R > 0)) {
      return {
        weights: w, rails: rails, wire: 0,
        logits: function (s, out) {
          return logitsOne(model.x, s * rows, w, gain, rows, cols, out);
        },
      };
    }

    var op = model.op, span = op.gMaxS - op.gMinS, vRead = op.readVoltageV;
    var ctxP = irContext(rails.gp, rows, cols, op.gMinS, span);
    var ctxN = irContext(rails.gn, rows, cols, op.gMinS, span);
    var v = new Float64Array(rows);
    var ip = new Float64Array(cols), inn = new Float64Array(cols);
    var scale = vRead * span;

    return {
      weights: w, rails: rails, wire: R,
      logits: function (s, out) {
        var base = s * rows, k;
        for (k = 0; k < rows; k++) v[k] = vRead * model.x[base + k];
        irColumnCurrents(ctxP, v, rows, cols, R, ip);
        irColumnCurrents(ctxN, v, rows, cols, R, inn);
        var res = out || new Float64Array(cols);
        for (k = 0; k < cols; k++) res[k] = (ip[k] - inn[k]) / scale * gain;
        return res;
      },
    };
  }

  /**
   * Accuracy over the whole frozen test set, plus what got confused with what.
   *
   * `perDigit` is what makes a falling number legible: an accuracy that drops four
   * points says nothing about whether the machine lost a little of everything or
   * stopped recognising 8 entirely, and those are different failures.
   */
  function evaluate(model, mach) {
    var cols = model.cols, out = new Float64Array(cols);
    var right = 0;
    var perTotal = new Int32Array(10), perRight = new Int32Array(10);
    var predicted = new Uint8Array(model.n);
    for (var s = 0; s < model.n; s++) {
      var p = argmax(mach.logits(s, out));
      var lab = model.labels[s];
      predicted[s] = p;
      perTotal[lab]++;
      if (p === lab) { right++; perRight[lab]++; }
    }
    var perDigit = new Float64Array(10);
    for (var d = 0; d < 10; d++) perDigit[d] = perTotal[d] ? perRight[d] / perTotal[d] : 0;
    return {
      accuracy: right / model.n,
      correct: right,
      total: model.n,
      perDigit: perDigit,
      predicted: predicted,
    };
  }

  var API = {
    ROWS: ROWS, COLS: COLS,
    load: load, unpackImages: unpackImages, bytes: bytes,
    roundHalfAway: roundHalfAway, quantise: quantise, program: program,
    vary: vary, effective: effective, rng: rng, normals: normals,
    logitsOne: logitsOne, argmax: argmax, machine: machine, evaluate: evaluate,
  };

  if (typeof module !== "undefined" && module.exports) module.exports = API;
  if (typeof window !== "undefined") window.SpinnCrossbar = API;
})();
