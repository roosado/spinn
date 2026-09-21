/*
 * Exercise apps/web/crossbar.js at five array sizes, against the recorded sweep.
 *
 * `tests/crossbar_runner.js` is the same idea at one size: the browser's copy of
 * the physics is allowed to exist because it is pinned to what MATLAB and Python
 * produced, rather than trusted. This adds the two things the size page needs and
 * the main page never did -- the wire network solved rather than expanded, and the
 * arrays at 64, 144, 324 and 676 rows.
 *
 * Two pins, doing different jobs:
 *
 *   `Geff / G` at every ladder point of every size, against the worst and mean cell
 *   fractions `run_size_sweep.m` recorded. Seventy-five points each, and they are
 *   *numbers* -- the browser's block Thomas sweep and MATLAB's sparse LU are
 *   different algorithms on the same matrix, so they agree to floating point and
 *   not beyond it.
 *
 *   Accuracy at every ladder point of every size, against the twins recorded on
 *   exactly the 500 digits this module ships. Those are integers over 500 and agree
 *   exactly -- except where two column currents come out equal and the winner is
 *   decided by summation order, which is the same one-sample slip
 *   `test_web_crossbar.py` documents at 2,000.
 *
 * Reports facts; the assertions live in tests/test_web_size.py, where a failure
 * names something.
 */
const path = require("path");

const C = require(path.join(__dirname, "..", "apps", "web", "crossbar.js"));
const SIZES = require(path.join(__dirname, "..", "apps", "web", "size_data.js"));

const out = { grids: SIZES.grids, sizes: {}, timings: {} };

/* -- the arrays, size by size ---------------------------------------------- */

for (const g of SIZES.grids) {
  const data = SIZES.sizes[String(g)];
  const model = C.load(data);
  const rec = data.sample;
  const exact = data.budget.exact;
  const started = Date.now();

  const accuracy = (opts) => C.evaluate(model, C.machine(model, opts)).accuracy;

  const size = {
    rows: model.rows,
    cols: model.cols,
    side: model.side,
    devices: model.devices,
    n: model.n,
    recordedIdeal: model.ideal,
    threshold: model.threshold,
    sampleIdeal: rec.ideal,
    sampleIdealComputed: accuracy({}),
  };

  // The solved network: what each cell keeps, against MATLAB's two scalars.
  size.fractions = exact.magnitudes.map((R, i) => {
    const m = C.machine(model, { wireOhm: R, wireModel: "solved" });
    return {
      magnitude: R,
      worst: m.worstFraction,
      worstRecorded: exact.worstCellFraction[i],
      mean: m.meanFraction,
      meanRecorded: exact.meanCellFraction[i],
    };
  });

  // Error source 2, which has no random draw.
  size.states = rec.states.magnitudes.map((s, i) => ({
    magnitude: s,
    computed: accuracy({ states: s }),
    recorded: rec.states.accMean[i],
  }));

  // Error source 3, both models, on the same ladder.
  size.wire = rec.wire.magnitudes.map((R, i) => ({
    magnitude: R,
    computed: accuracy({ wireOhm: R }),
    recorded: rec.wire.accMean[i],
  }));
  size.solved = rec.exact.magnitudes.map((R, i) => ({
    magnitude: R,
    computed: accuracy({ wireOhm: R, wireModel: "solved" }),
    recorded: rec.exact.exactAcc[i],
  }));

  // Error source 1: same distribution, different stream. Twenty realisations, as
  // the budget ran, compared in mean rather than sample for sample.
  size.sigma = rec.sigma.magnitudes.map((s, i) => {
    const runs = [];
    for (let k = 0; k < 20; k++) runs.push(accuracy({ sigma: s, seed: 1000 + k }));
    return {
      magnitude: s,
      mean: runs.reduce((a, b) => a + b, 0) / runs.length,
      recorded: rec.sigma.accMean[i],
      recordedStd: rec.sigma.accStd[i],
    };
  });

  // The pictures the page draws come off the same solve as the numbers above, so
  // this records that they are the same length as the array and inside [0, 1].
  {
    const m = C.machine(model, { wireOhm: 20, wireModel: "solved" });
    let lo = Infinity, hi = -Infinity;
    for (let i = 0; i < m.fracP.length; i++) {
      lo = Math.min(lo, m.fracP[i], m.fracN[i]);
      hi = Math.max(hi, m.fracP[i], m.fracN[i]);
    }
    size.map = { length: m.fracP.length, cells: model.rows * model.cols, lo: lo, hi: hi,
                 worst: m.worstFraction };
  }

  // The images decode to something shaped like normalised digits: every sample has
  // a peak of exactly one, and nothing is above it.
  {
    let peakOne = 0, over = 0, nonZero = 0;
    for (let s = 0; s < model.n; s++) {
      let peak = 0;
      for (let i = 0; i < model.rows; i++) {
        const v = model.x[s * model.rows + i];
        if (v > 0) nonZero++;
        if (v > 1) over++;
        if (v > peak) peak = v;
      }
      if (peak === 1) peakOne++;
    }
    size.images = { nonZero, peakExactlyOne: peakOne, aboveOne: over };
  }

  out.sizes[String(g)] = size;
  out.timings[String(g)] = Date.now() - started;
}

/* -- the solver on its own, away from the recorded data -------------------- */

// A one-cell array is a device in series with its two wire segments.
{
  const gMin = 1.0e-6, span = 2.0e-6, R = 1.0e4;
  const occupancy = 0.5;
  const r = C.effectiveConductance(new Float64Array([occupancy]), 1, 1, gMin, span, R);
  const G = gMin + occupancy * span;
  out.oneCell = { geff: r.Geff[0], closedForm: G / (1 + 2 * R * G), G: G };
}

// A small array, for the dense direct solve tests/test_web_size.py builds in NumPy
// from the same description. Deliberately not square and deliberately lopsided in
// its conductances: a transposed index or an off-by-one in the block sweep survives
// a uniform array and does not survive this one.
{
  const rows = 3, cols = 2, gMin = 1.0e-6, span = 2.0e-6, R = 5.0e3;
  const occ = new Float64Array([0.0, 1.0, 0.25, 0.5, 0.75, 0.1]);
  const r = C.effectiveConductance(occ, rows, cols, gMin, span, R);
  out.small = {
    rows, cols, gMin, span, R,
    occupancy: Array.from(occ),
    G: Array.from(r.G),
    Geff: Array.from(r.Geff),
  };
}

// With no wire the solved model is the ideal one: Geff is G itself, so the
// effective weights are the programmed ones. Run just above zero rather than at it,
// because zero takes the fast path and would prove nothing about the solver.
{
  const g = SIZES.grids[0];
  const model = C.load(SIZES.sizes[String(g)]);
  const ideal = C.machine(model, {});
  const thin = C.machine(model, { wireOhm: 1e-9, wireModel: "solved" });
  let worst = 0;
  for (let i = 0; i < ideal.weights.length; i++) {
    worst = Math.max(worst, Math.abs(ideal.weights[i] - thin.weights[i]));
  }
  out.vanishingWire = { grid: g, worstWeightDifference: worst,
                        worstFraction: thin.worstFraction };
}

process.stdout.write(JSON.stringify(out));
