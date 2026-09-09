/*
 * Exercise apps/web/crossbar.js against the recorded error budget.
 *
 * This file is the reason the browser copy of the physics is allowed to exist.
 * `spinn/crossbar.py` and `spinn-hw/+model` plus `spinn-hw/+err` are the two
 * implementations that matter, and the seam between them is one-directional on
 * purpose -- so the widgets on the site cannot call either one and had to be given
 * a third copy. A third copy is normally where you stop and share one. Since that
 * is not available, the copy is instead pinned to what the other two produced:
 * every deterministic magnitude in exports/error_budget.json, recomputed here.
 *
 * Reports facts; the assertions live in tests/test_web_crossbar.py, where a
 * failure names something.
 */
const path = require("path");

const DATA = require(path.join(__dirname, "..", "apps", "web", "data.js"));
const C = require(path.join(__dirname, "..", "apps", "web", "crossbar.js"));

const model = C.load(DATA);
const out = { n: model.n, rows: model.rows, cols: model.cols, ideal: model.ideal };

function accuracy(opts) {
  return C.evaluate(model, C.machine(model, opts)).accuracy;
}

out.idealComputed = accuracy({});

/* -- error source 2, which has no random draw ------------------------------ */
out.states = model.budget.states.magnitudes.map((s) => ({
  magnitude: s,
  computed: accuracy({ states: s }),
  recorded: model.budget.states.accMean[model.budget.states.magnitudes.indexOf(s)],
}));

/* -- error source 3, likewise ---------------------------------------------- */
out.wire = model.budget.wire.magnitudes.map((r, i) => ({
  magnitude: r,
  computed: accuracy({ wireOhm: r }),
  recorded: model.budget.wire.accMean[i],
}));

/* -- error source 1: same distribution, different stream ------------------- */
// MATLAB draws from a Mersenne Twister seeded by mc.sweep's partitioning; this
// draws from a small PRNG. Sample-for-sample agreement is impossible and would be
// suspicious; what has to hold is that the mean over a comparable number of
// realisations lands inside the spread the budget recorded.
out.sigma = model.budget.sigma.magnitudes.map((s, i) => {
  const runs = [];
  for (let k = 0; k < 20; k++) runs.push(accuracy({ sigma: s, seed: 1000 + k }));
  const mean = runs.reduce((a, b) => a + b, 0) / runs.length;
  return {
    magnitude: s,
    mean: mean,
    recorded: model.budget.sigma.accMean[i],
    recordedStd: model.budget.sigma.accStd[i],
  };
});

/* -- the quantiser's rounding convention ----------------------------------- */
// NumPy rounds half to even and MATLAB rounds half away from zero; JavaScript's
// Math.round rounds half towards positive infinity, which is a third answer. The
// negative halves are the ones that separate all three.
out.rounding = [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5].map(C.roundHalfAway);

/* -- the sparse image block decodes to what the exporter packed ------------ */
{
  const x = model.x;
  let nonZero = 0, peakOne = 0, over = 0;
  for (let s = 0; s < model.n; s++) {
    let peak = 0;
    for (let i = 0; i < model.rows; i++) {
      const v = x[s * model.rows + i];
      if (v > 0) nonZero++;
      if (v > 1) over++;
      if (v > peak) peak = v;
    }
    if (peak === 1) peakOne++;
  }
  out.images = { nonZero: nonZero, peakExactlyOne: peakOne, aboveOne: over };
}

/* -- a differential pair reaches 2*states - 1 effective weights ------------ */
{
  const w = new Float64Array([-1, -0.6, -0.3, 0, 0.3, 0.6, 1]);
  const levels = {};
  [2, 3, 5].forEach((s) => {
    const q = C.quantise(w, s);
    const set = new Set();
    // Every value the lattice can reach, not just the ones this probe hit: sweep
    // the full range, since a probe that misses a level reports a smaller lattice
    // than the one that exists. That is exactly the shape of the bug the round-trip
    // test caught in the Python and MATLAB copies.
    const sweep = new Float64Array(2001);
    for (let i = 0; i <= 2000; i++) sweep[i] = -1 + i / 1000;
    C.quantise(sweep, s).forEach((v) => set.add(Number(v.toFixed(9))));
    levels[s] = { reached: set.size, expected: 2 * s - 1, sample: Array.from(q) };
  });
  out.lattice = levels;
}

process.stdout.write(JSON.stringify(out));
