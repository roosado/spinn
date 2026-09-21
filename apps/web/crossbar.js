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
 * `g_min` and `g_max` -- a design point, which a thinner-barrier junction would
 * move. The slow path therefore reconstitutes real conductances and a real drive,
 * and the page states the dependence rather than hiding it behind a widget that
 * looks equally confident either way.
 *
 * ---------------------------------------------------------------------------
 * Two wire models, and why the exact one is also fast
 *
 * `err.ir_drop` is first order: it computes the drops from the currents the
 * *ideal* voltages would draw, which overstates them, and past a certain drop it
 * lets a column node rise above its own driver and reverses a cell's current --
 * an accuracy below chance, which no resistor network produces. `err.ir_drop_exact`
 * solves the network instead. Both are here, because the recorded budget, the
 * published row and the main page are all first order, and the "Go larger" page
 * draws the two together.
 *
 * The solved model turns out not to be a second forward pass at all. The array is
 * linear, so the current into amplifier j per volt on driver i is a fixed matrix
 * `Geff`, and
 *
 *     logits = (V Geff+ - V Geff-) / (V_read span) . gain
 *            = x . (Geff+ - Geff-)/span . gain
 *
 * which is the first equation in this header with `g+ - g-` replaced by
 * `(Geff+ - Geff-)/span`. So the solve produces *an effective-weight matrix*, the
 * fast path runs unchanged over it, and every widget that draws `mach.weights`
 * draws the array as the wires present it rather than as it was programmed.
 * `Geff / G` per cell -- how much of each device survives -- comes out of the same
 * solve, and is what the starvation map on that page draws.
 */
(function () {
  "use strict";

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
   * Read a little-endian unsigned integer of `w` bytes at element `k`.
   *
   * Assembled by hand rather than through a Uint16Array view: a view needs its
   * byte offset to be even, and a sparse stream gives no such promise.
   */
  function le(buf, k, w) {
    return w === 1 ? buf[k] : (buf[k * 2] | (buf[k * 2 + 1] << 8));
  }

  /**
   * Expand the sparse image block written by apps/export_web_data.py.
   *
   * Three quarters of the pixels in a 6x6 MNIST digit are zero, so the file
   * carries a per-sample count, one or two index bytes per non-zero and two value
   * bytes. The two halves of that format have to be read together; the exporter's
   * docstring is the other half of this comment.
   *
   * The widths are read, never assumed. At 6x6 both are one byte; at 18x18 and
   * 26x26 an index runs past 255 and so does the fattest digit's non-zero count,
   * and a decoder that assumed a byte would not fail -- it would return a
   * different picture, classified with perfect confidence.
   */
  function unpackImages(block) {
    var counts = bytes(block.counts);
    var idx = bytes(block.idx);
    var raw = bytes(block.val);
    var n = block.n, dim = block.dim, full = block.full;
    var iw = block.idxBytes, cw = block.cntBytes;
    if (!(iw === 1 || iw === 2) || !(cw === 1 || cw === 2)) {
      throw new Error("image block does not state its index and count widths");
    }
    var x = new Float64Array(n * dim);
    var at = 0;
    for (var s = 0; s < n; s++) {
      var c = le(counts, s, cw), base = s * dim;
      for (var k = 0; k < c; k++, at++) {
        x[base + le(idx, at, iw)] = le(raw, at, 2) / full;
      }
    }
    return x;
  }

  /**
   * The trained weights, however the module that carried them wrote them down.
   *
   * `data.js` writes 360 numbers as nested JSON arrays, which is legible and costs
   * nothing at one size. `size_data.js` writes 12,440 as base64 float64, because
   * legible JSON decimals for five arrays are 243 kB against 130 kB packed. Both
   * forms are exact; neither is a default for the other, so which one is in hand is
   * decided by looking rather than by guessing.
   */
  function weightsOf(data, rows, cols) {
    var w = new Float64Array(rows * cols), i, j;
    if (typeof data.weights === "string") {
      var b = bytes(data.weights);
      if (b.length !== rows * cols * 8) {
        throw new Error("packed weights are " + b.length + " bytes, not "
          + (rows * cols * 8) + " for a " + rows + "x" + cols + " array");
      }
      var view = new DataView(b.buffer, b.byteOffset, b.byteLength);
      for (i = 0; i < rows * cols; i++) w[i] = view.getFloat64(i * 8, true);
      return w;
    }
    for (i = 0; i < rows; i++) {
      for (j = 0; j < cols; j++) w[i * cols + j] = data.weights[i][j];
    }
    return w;
  }

  /** Identity for the solved-network cache. One per loaded array, never reused. */
  var nextModelId = 1;

  /**
   * Turn the generated data module into everything the widgets read.
   *
   * `x` holds the L-infinity normalised inputs, which is what the row drivers
   * deliver once the read voltage is divided back out.
   *
   * `ideal` and `threshold` are the *recorded* numbers, measured over the whole
   * frozen test set. On the size page the images below are a 500-digit sample of
   * that set, so `n` is not the number those were measured over and the two must
   * not be compared without saying so: `sample` carries the twin of every recorded
   * ladder, computed on exactly the digits this model holds.
   */
  function load(data) {
    var g = data.geometry;
    return {
      id: nextModelId++,
      rows: g.rows, cols: g.cols, side: g.side, devices: g.devices,
      n: data.images.n,
      x: unpackImages(data.images),
      labels: bytes(data.labels),
      weights: weightsOf(data, g.rows, g.cols),
      gain: data.readoutGain,
      ideal: data.idealAccuracy,
      threshold: data.threshold,
      op: data.operatingPoint,
      budget: data.budget,
      sample: data.sample || null,
      power: typeof data.power === "number" ? data.power : null,
      grid: data.grid || g.side,
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
    return { G: G, A: A,
             rev: new Float64Array(rows * cols), colDrop: new Float64Array(cols) };
  }

  function irColumnCurrents(ctx, v, rows, cols, R, out) {
    var G = ctx.G, A = ctx.A;
    var i, j, idx;
    // Reverse cumulative sum down each column of I0 = V * G, then a forward
    // cumulative sum of that: the drop delivered to row i of column j.
    //
    // The two scratch arrays belong to the context rather than to the call. This
    // runs once per rail per digit -- two thousand times over the frozen set, and
    // at 676 rows `rev` is 54 kB a time, which is fifty megabytes of garbage for
    // one accuracy. Every entry of both is written before it is read below.
    var rev = ctx.rev, colDrop = ctx.colDrop;
    for (j = 0; j < cols; j++) {
      var run = 0;
      for (i = rows - 1; i >= 0; i--) {
        idx = i * cols + j;
        run += v[i] * G[idx];
        rev[idx] = run;
      }
    }
    for (j = 0; j < cols; j++) { out[j] = 0; colDrop[j] = 0; }
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

  /* -------------------------------------------------- the network, solved */

  /**
   * Dense LU with partial pivoting, in place on the `n` by `n` block at `at`.
   *
   * The offset rather than a `subarray` view because this runs once per row of the
   * array: 676 views per solve, twice per machine, and allocating them costs more
   * than the arithmetic they wrap. Swaps are written into `swap` at `sAt` in the
   * order they were made, which is what `luSolve` replays onto a right-hand side.
   */
  function luFactor(a, at, n, swap, sAt) {
    var i, j, k;
    for (k = 0; k < n; k++) {
      var best = k, mag = Math.abs(a[at + k * n + k]);
      for (i = k + 1; i < n; i++) {
        var m = Math.abs(a[at + i * n + k]);
        if (m > mag) { mag = m; best = i; }
      }
      if (!(mag > 0)) throw new Error("the nodal matrix is singular at pivot " + k);
      swap[sAt + k] = best;
      if (best !== k) {
        for (j = 0; j < n; j++) {
          var t = a[at + k * n + j];
          a[at + k * n + j] = a[at + best * n + j];
          a[at + best * n + j] = t;
        }
      }
      var d = a[at + k * n + k];
      for (i = k + 1; i < n; i++) {
        var f = a[at + i * n + k] / d;
        a[at + i * n + k] = f;
        if (f === 0) continue;
        for (j = k + 1; j < n; j++) a[at + i * n + j] -= f * a[at + k * n + j];
      }
    }
  }

  /** Solve `LU x = b` in place. `b` is `n` by `nrhs`, row-major, at `bAt`. */
  function luSolve(a, at, swap, sAt, n, b, bAt, nrhs) {
    var i, j, k, f;
    for (k = 0; k < n; k++) {
      var p = swap[sAt + k];
      if (p === k) continue;
      for (j = 0; j < nrhs; j++) {
        var t = b[bAt + k * nrhs + j];
        b[bAt + k * nrhs + j] = b[bAt + p * nrhs + j];
        b[bAt + p * nrhs + j] = t;
      }
    }
    for (k = 0; k < n; k++) {
      for (i = k + 1; i < n; i++) {
        f = a[at + i * n + k];
        if (f === 0) continue;
        for (j = 0; j < nrhs; j++) b[bAt + i * nrhs + j] -= f * b[bAt + k * nrhs + j];
      }
    }
    for (k = n - 1; k >= 0; k--) {
      var d = a[at + k * n + k];
      for (j = 0; j < nrhs; j++) b[bAt + k * nrhs + j] /= d;
      for (i = 0; i < k; i++) {
        f = a[at + i * n + k];
        if (f === 0) continue;
        for (j = 0; j < nrhs; j++) b[bAt + i * nrhs + j] -= f * b[bAt + k * nrhs + j];
      }
    }
  }

  /**
   * Error source 3, solved: what the array actually multiplies by.
   *
   * The same network `err.ir_drop` expands to first order -- drivers at the
   * column-1 edge, amplifiers at the row-1 edge, a segment of `R` between
   * neighbouring cells both ways, each cell a conductance between its two wires.
   * Written out, Kirchhoff at every node is a linear system in 2*rows*cols
   * unknowns, and the current into amplifier j per volt on driver i is a fixed
   * matrix `Geff`: it depends on the programmed conductances and on `R`, and not
   * on the image. So it is solved once and applied to every digit.
   *
   * **Ordering the nodes by row makes the matrix block-tridiagonal.** A row wire
   * couples cells within one row; a device couples the two wires of one cell; only
   * a column wire reaches the next row. So each block is the 2*cols nodes of one
   * row, the coupling to the next row is the identity on the column-wire half, and
   * a block Thomas sweep solves it in `rows` steps of 20-by-20 arithmetic rather
   * than one factorisation of a 13,520-square matrix.
   *
   * Everything is scaled so that a wire segment is 1 and a device is `R*G`, as
   * `err.ir_drop_exact` does, which keeps every entry of order one however large
   * the ratio of the two. A one-cell array gives `G / (1 + 2RG)`.
   */
  function effectiveConductance(g, rows, cols, gMin, span, R) {
    var N = rows, M = cols, nb = 2 * M, i, j, k, at;
    var G = new Float64Array(N * M);
    for (i = 0; i < N * M; i++) G[i] = gMin + g[i] * span;

    var lu = new Float64Array(N * nb * nb);     // the factored diagonal blocks
    var swaps = new Int32Array(N * nb);
    var C = new Float64Array(N * nb * M);       // the reduced right-hand sides
    // [ D^-1 P | D^-1 C ] for the block just factored: the first half reduces the
    // next block's diagonal, the second its right-hand side.
    var X = new Float64Array(nb * 2 * M);
    var B = new Float64Array(nb * nb);

    for (i = 0; i < N; i++) {
      B.fill(0);
      for (j = 0; j < M; j++) {
        var dev = R * G[i * M + j];
        // The row wire: the segment behind (to the driver, or to column j-1), the
        // one ahead where there is one, and the device across to the column wire.
        B[j * nb + j] = 1 + (j < M - 1 ? 1 : 0) + dev;
        if (j < M - 1) { B[j * nb + j + 1] = -1; B[(j + 1) * nb + j] = -1; }
        B[j * nb + M + j] = -dev;
        B[(M + j) * nb + j] = -dev;
        // The column wire: the segment toward the amplifier, the one on to row i+1
        // where there is one, and the same device.
        B[(M + j) * nb + M + j] = 1 + (i < N - 1 ? 1 : 0) + dev;
      }

      var cAt = i * nb * M;
      if (i === 0) {
        // One unit of current at each amplifier's node. Geff is then read off the
        // drivers' nodes: the matrix is symmetric, so ten solves from the output
        // side give what `rows` solves from the input side would.
        for (j = 0; j < M; j++) C[cAt + (M + j) * M + j] = 1;
      } else {
        // Eliminate the previous row. Its coupling to this one is the identity on
        // the column-wire half, so the correction is exactly the column-wire block
        // of the previous solve -- subtracted from this diagonal, added to this
        // right-hand side.
        for (j = 0; j < M; j++) {
          for (k = 0; k < M; k++) {
            B[(M + j) * nb + M + k] -= X[(M + j) * 2 * M + k];
            C[cAt + (M + j) * M + k] = X[(M + j) * 2 * M + M + k];
          }
        }
      }

      var luAt = i * nb * nb;
      lu.set(B, luAt);
      luFactor(lu, luAt, nb, swaps, i * nb);

      X.fill(0);
      for (j = 0; j < M; j++) X[(M + j) * 2 * M + j] = 1;
      for (at = 0; at < nb; at++) {
        for (k = 0; k < M; k++) X[at * 2 * M + M + k] = C[cAt + at * M + k];
      }
      luSolve(lu, luAt, swaps, i * nb, nb, X, 0, 2 * M);
    }

    // Back substitution. Only the last block's solve is already in hand; each
    // earlier row takes the column-wire half of the row below it.
    var Geff = new Float64Array(N * M);
    var Y = new Float64Array(nb * M), rhs = new Float64Array(nb * M);
    for (at = 0; at < nb; at++) {
      for (k = 0; k < M; k++) Y[at * M + k] = X[at * 2 * M + M + k];
    }
    for (k = 0; k < M; k++) Geff[(N - 1) * M + k] = Y[k] / R;

    for (i = N - 2; i >= 0; i--) {
      var cAt2 = i * nb * M, luAt2 = i * nb * nb;
      rhs.set(C.subarray(cAt2, cAt2 + nb * M));
      for (j = 0; j < M; j++) {
        for (k = 0; k < M; k++) rhs[(M + j) * M + k] += Y[(M + j) * M + k];
      }
      luSolve(lu, luAt2, swaps, i * nb, nb, rhs, 0, M);
      Y.set(rhs);
      for (k = 0; k < M; k++) Geff[i * M + k] = Y[k] / R;
    }
    return { Geff: Geff, G: G };
  }

  /**
   * The effective weights the solved network presents, and what each cell keeps.
   *
   * See the header: `(Geff+ - Geff-)/span` is an effective-weight matrix, so the
   * result drops straight into the fast path. `frac` is `Geff/G` per cell per rail
   * -- the fraction of its programmed conductance that survives the wires, which is
   * what the starvation map draws and what `run_size_sweep.m` records the smallest
   * and the mean of.
   */
  function solveWires(model, rails, R) {
    var op = model.op, span = op.gMaxS - op.gMinS;
    var p = effectiveConductance(rails.gp, model.rows, model.cols, op.gMinS, span, R);
    var n = effectiveConductance(rails.gn, model.rows, model.cols, op.gMinS, span, R);
    var len = model.rows * model.cols;
    var w = new Float64Array(len);
    var fracP = new Float64Array(len), fracN = new Float64Array(len);
    var worst = Infinity, total = 0;
    for (var i = 0; i < len; i++) {
      w[i] = (p.Geff[i] - n.Geff[i]) / span;
      fracP[i] = p.Geff[i] / p.G[i];
      fracN[i] = n.Geff[i] / n.G[i];
      if (fracP[i] < worst) worst = fracP[i];
      if (fracN[i] < worst) worst = fracN[i];
      total += fracP[i] + fracN[i];
    }
    return { weights: w, fracP: fracP, fracN: fracN,
             worstFraction: worst, meanFraction: total / (2 * len) };
  }

  /**
   * The last few solves, kept.
   *
   * A solve is ~11 million operations at 676 rows and `machine()` is rebuilt on
   * every slider tick -- including the sigma and states sliders, which change the
   * rails the solve is over. Cached on exactly what the rails are a function of, so
   * a hit is the same answer and not a nearly-the-same one. Small, because each
   * entry is three arrays the size of the array itself.
   */
  var SOLVE_CACHE = 8;
  var solved = new Map();

  function solveCached(model, rails, R, key) {
    if (solved.has(key)) return solved.get(key);
    var out = solveWires(model, rails, R);
    solved.set(key, out);
    while (solved.size > SOLVE_CACHE) solved.delete(solved.keys().next().value);
    return out;
  }

  /* -------------------------------------------------------------- evaluation */

  /**
   * Build a callable that turns one sample index into ten logits.
   *
   * `opts`: `states`, `sigma`, `seed`, `wireOhm`, `wireModel`. The returned object
   * also carries the effective weights it is using, because every widget that
   * evaluates also draws the array it evaluated with, and re-deriving them would be
   * a second chance to disagree.
   *
   * `wireModel` is `"firstOrder"` by default, and the default is load bearing: it
   * is the model the recorded budget, the published row and the main page's numbers
   * are. `"solved"` is the network itself, which the size page draws beside it.
   */
  function machine(model, opts) {
    var o = opts || {};
    var rows = model.rows, cols = model.cols, gain = model.gain;
    var rails = vary(program(model.weights, o.states), o.sigma || 0, o.seed || 1);
    var w = effective(rails);
    var R = o.wireOhm || 0;

    if (!(R > 0)) {
      return {
        weights: w, rails: rails, wire: 0, wireModel: o.wireModel || "firstOrder",
        logits: function (s, out) {
          return logitsOne(model.x, s * rows, w, gain, rows, cols, out);
        },
      };
    }

    if (o.wireModel === "solved") {
      // Keyed on everything the rails are a function of, plus the resistance.
      var key = [model.id, R, o.states || 0, o.sigma || 0, o.seed || 1].join("|");
      var sol = solveCached(model, rails, R, key);
      return {
        weights: sol.weights, rails: rails, wire: R, wireModel: "solved",
        fracP: sol.fracP, fracN: sol.fracN,
        worstFraction: sol.worstFraction, meanFraction: sol.meanFraction,
        logits: function (s, out) {
          return logitsOne(model.x, s * rows, sol.weights, gain, rows, cols, out);
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
      weights: w, rails: rails, wire: R, wireModel: "firstOrder",
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
    load: load, unpackImages: unpackImages, bytes: bytes,
    roundHalfAway: roundHalfAway, quantise: quantise, program: program,
    vary: vary, effective: effective, rng: rng, normals: normals,
    logitsOne: logitsOne, argmax: argmax, machine: machine, evaluate: evaluate,
    effectiveConductance: effectiveConductance, solveWires: solveWires,
  };

  if (typeof module !== "undefined" && module.exports) module.exports = API;
  if (typeof window !== "undefined") window.SpinnCrossbar = API;
})();
