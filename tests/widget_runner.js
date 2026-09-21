/*
 * Mount every widget, at every array size, and check what `destroy` gives back.
 *
 * The size page rebuilds each instrument whenever the reader changes the array
 * size. That is only safe if a mount can be undone, and until this page existed
 * nothing could tell: a widget was mounted once and lived as long as the document,
 * so an observer it never disconnected cost nothing and left no trace.
 *
 * So this runs each widget against `tests/dom_stub.js` with the counting window --
 * one that remembers every ResizeObserver, MutationObserver, media listener,
 * interval and animation frame it hands out -- mounts, tears down, and reports the
 * numbers. A leak is a count that does not come back to where it started.
 *
 * The hero is the one that matters most: it holds an interval, a frame *and* its
 * own IntersectionObserver, and an interval left running repaints a canvas that is
 * no longer in the document, on a loop, for as long as the page is open.
 *
 * It also mounts each widget at all five sizes, which is the other half of Stage 3:
 * a widget that still carries a hard-coded 36 in its markup shows up here as text
 * that did not change when the array did.
 *
 * Reports facts; the assertions live in tests/test_web_widgets.py.
 */
const path = require("path");
const fs = require("fs");

const { makeEnv, loadWidget } = require("./dom_stub.js");

const WEB = path.join(__dirname, "..", "apps", "web");
const DATA = require(path.join(WEB, "data.js"));
const SIZES = require(path.join(WEB, "size_data.js"));

/** Everything the widgets call on a 2D context, and nothing more. */
function ctxStub() {
  const calls = [];
  const rec = (name) => function (...a) { calls.push([name, ...a]); };
  return {
    _calls: calls,
    fillStyle: "", strokeStyle: "", font: "", textAlign: "",
    lineWidth: 1, imageSmoothingEnabled: true,
    arc: rec("arc"), beginPath: rec("beginPath"), clearRect: rec("clearRect"),
    closePath: rec("closePath"), drawImage: rec("drawImage"), fill: rec("fill"),
    fillRect: rec("fillRect"), fillText: rec("fillText"), lineTo: rec("lineTo"),
    moveTo: rec("moveTo"), putImageData: rec("putImageData"), restore: rec("restore"),
    rotate: rec("rotate"), save: rec("save"), setLineDash: rec("setLineDash"),
    setTransform: rec("setTransform"), stroke: rec("stroke"),
    strokeRect: rec("strokeRect"), translate: rec("translate"),
    createImageData: (w, h) => ({ width: w, height: h,
                                  data: new Uint8ClampedArray(w * h * 4) }),
    // Every label this site draws is monospace at one size, so a width per
    // character is as good a model as measuring would be, and it keeps the
    // collision-avoidance in ladder.js exercised rather than trivial.
    measureText: (t) => ({ width: String(t).length * 6.6 }),
  };
}

/** A plausible instrument column: wide enough that nothing hits a minimum. */
function makeStub(reduceMotion) {
  const env = makeEnv({
    dpr: 2,
    layoutWidth: () => 900,
    ctxStub,
    observers: true,
    reduceMotion: !!reduceMotion,
  });
  // `plot.js` reads MutationObserver off the global, as a browser does, so it is
  // bound rather than reached for.
  env.extras = { MutationObserver: env.win.MutationObserver, atob: (b) =>
    Buffer.from(b, "base64").toString("binary") };
  return env;
}

const ORDER = ["plot.js", "xbar_view.js", "crossbar.js"];
const WIDGETS = [
  { host: "heroMachine", asset: "hero.js", global: "SpinnHero", readout: true },
  { host: "deviceExplorer", asset: "device.js", global: "SpinnDevice" },
  { host: "wireColumn", asset: "wire.js", global: "SpinnWire" },
  { host: "errorBench", asset: "bench.js", global: "SpinnBench" },
  { host: "budgetLadder", asset: "ladder.js", global: "SpinnLadder" },
  { host: "drawPad", asset: "draw.js", global: "SpinnDraw" },
  { host: "sizeArray", asset: "size.js", global: "SpinnSizeArray", needsBar: true },
];

function source(name) {
  return fs.readFileSync(path.join(WEB, name), "utf8");
}

/**
 * One widget, mounted over `data`, then destroyed. Returns what it cost.
 *
 * A fresh environment each time, because a leak is measured as a difference and
 * two widgets sharing a window would each be measuring the other's.
 */
function cycle(widget, data, grid, reduceMotion) {
  const env = makeStub(reduceMotion);
  env.win.SpinnData = DATA;
  env.win.SpinnSizes = SIZES;
  for (const name of ORDER) loadWidget(source(name), env, env.extras);
  if (widget.needsBar) {
    loadWidget(source("size_bar.js"), env, env.extras);
    // The instrument reads the bar for the current grid, so the bar has to be
    // mounted first -- exactly as the page mounts it first.
    const barHost = env.makeEl("div");
    env.body.appendChild(barHost);
    env.win.SpinnSizeBar.mount(barHost);
  }
  loadWidget(source(widget.asset), env, env.extras);

  const host = env.makeEl("div");
  host.id = widget.host;
  env.body.appendChild(host);
  let readout = null;
  if (widget.readout) {
    readout = env.makeEl("div");
    readout.id = "heroReadout";
    env.body.appendChild(readout);
  }

  const before = Object.assign({}, env.win._live);
  const api = env.win[widget.global];
  const instance = widget.readout
    ? api.mount(host, readout, { data })
    : api.mount(host, { data });

  // Under reduced motion the hero schedules nothing until the reader presses
  // Play -- that is the branch that starts an interval, so the press is part of
  // the cycle rather than a separate test. Pressing it is also the only way the
  // interval leak could ever have happened in a browser.
  if (reduceMotion && widget.host === "heroMachine") {
    const play = host.querySelector(".xh-btn");
    if (play) play.dispatch("click");
  }

  const mounted = {
    hostLength: host.innerHTML.length,
    text: host.textContent,
    live: Object.assign({}, env.win._live),
    made: Object.assign({}, env.win._made),
  };

  const hasDestroy = !!(instance && typeof instance.destroy === "function");
  if (hasDestroy) instance.destroy();

  return {
    grid,
    reduceMotion: !!reduceMotion,
    hasDestroy,
    mountedLength: mounted.hostLength,
    text: mounted.text,
    made: mounted.made,
    before,
    afterMount: mounted.live,
    afterDestroy: Object.assign({}, env.win._live),
    hostLeft: host.innerHTML.length,
    readoutLeft: readout ? readout.innerHTML.length : 0,
  };
}

const out = { widgets: {} };

for (const widget of WIDGETS) {
  const runs = {};
  // The index page's own array first, then every size the size page offers.
  if (!widget.needsBar) runs.index = cycle(widget, DATA, 6);
  for (const g of SIZES.grids) {
    runs["g" + g] = cycle(widget, SIZES.sizes[String(g)], g);
  }
  // The hero again, with reduced motion asked for: that is the path where it
  // holds an interval rather than a frame, and an interval is the one leak a
  // reader would actually feel.
  if (widget.host === "heroMachine") {
    runs.reducedMotion = cycle(widget, SIZES.sizes["26"], 26, true);
  }
  out.widgets[widget.host] = runs;
}

/* -- the draw pad's grid, which must stay a whole multiple ------------------ */
{
  const env = makeStub();
  env.win.SpinnData = DATA;
  for (const name of ORDER) loadWidget(source(name), env, env.extras);
  const draw = loadWidget(source("draw.js"), env, env.extras);
  out.padGrid = SIZES.grids.map((g) => {
    const pad = draw.padGrid(g);
    return { grid: g, pad, per: pad / g, whole: pad % g === 0 };
  });
  out.padGridAtSix = draw.padGrid(6);
}

process.stdout.write(JSON.stringify(out));
