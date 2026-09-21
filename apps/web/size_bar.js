/*
 * size_bar.js -- the one control the size page has, and the state it owns.
 *
 * Five rungs: 6, 8, 12, 18 and 26 per side, so 36 to 676 rows and ten columns
 * throughout. Every instrument below reads the size from here and re-mounts when it
 * changes, which is the whole of the page's argument -- the same six instruments,
 * the same arithmetic, one axis.
 *
 * It opens at 6x6, which is the array the main page is about. A reader arriving on
 * the "Go larger" link lands on the machine they have just read, and the first move
 * larger is theirs.
 *
 * The bar is sticky under the topbar because eight instruments is more than a screen
 * and a control you have to scroll back to is a control you stop using. It is not
 * an instrument and has no panel: the design system's `.sp-field` is the control,
 * and `.sizebar` is chrome.
 *
 * Being sticky is what makes it expensive. Every line it carries is subtracted from
 * every screenful of the page below it, so it carries two: a label row with the
 * chosen size in it, and the track. The array's rows, devices, ideal and pass mark
 * used to sit here too and are in the instruments that use them.
 *
 * On the input's value being a rung index
 * ---------------------------------------
 * The five sizes are not evenly spaced and the slider's own value is 0-4, so a
 * screen reader left to itself announces "3". `aria-valuetext` carries what the
 * `<output>` says, which is the site's convention for every range input it has.
 *
 * On notifying
 * ------------
 * Subscribers are told about the size the reader stopped on, not about every rung
 * the handle passed over. A frame would be the usual unit and is the wrong one
 * here: one recompute at 676 rows is a few hundred milliseconds, so a drag from
 * 6x6 to 26x26 would queue four of those and the page would stop answering while
 * it worked through sizes nobody asked to see. The bar's own label still moves with
 * the handle, because that costs nothing.
 */
(function () {
  "use strict";

  var P = window.SpinnPlot;

  // Everything the bar draws inside its own host. The chrome around it -- the
  // sticky band, its ground, the grid it sits in -- is the stylesheet's, because
  // that is markup the page body carries and this file never sees.
  //
  // Nothing sits below the track. This bar is fixed to the top of a page the reader
  // scrolls through eight instruments of, so every line it carries is a line taken
  // off every screenful of the page underneath -- it had four (rung labels, the
  // value, and two of array facts) and now has none. The label row carries the
  // value instead, which costs no height at all: the label was always there.
  var CSS = ""
    + ".sz-wrap{display:block;}"
    // The value sits beside its own label, not at the far end of the bar. Spread to
    // opposite edges of 1100px they are two separate things a reader has to pair up;
    // together they read as one caption for the track below them.
    + ".sz-head{display:flex;align-items:baseline;gap:4px 14px;flex-wrap:wrap;}";

  /** Every size the generated module carries, ascending. */
  function grids() {
    var d = window.SpinnSizes;
    return (d && d.grids) || [];
  }

  function dataFor(grid) {
    var d = window.SpinnSizes;
    return (d && d.sizes && d.sizes[String(grid)]) || null;
  }

  /**
   * One loaded model per size, shared by every instrument on the page.
   *
   * `C.load` expands the sparse image block into a Float64Array: 500 digits at
   * 26x26 is 2.7 MB of it. Seven widgets each loading their own copy would be
   * seven copies of that, decoded seven times, on every size change -- so the
   * model is loaded once here and handed out. They are read-only to a widget; the
   * one thing that varies per widget is the machine it builds over them.
   */
  var models = {};

  function modelFor(grid) {
    var key = String(grid);
    if (!models[key]) {
      var d = dataFor(grid);
      if (!d) throw new Error("no array at " + grid + "x" + grid);
      models[key] = window.SpinnCrossbar.load(d);
    }
    return models[key];
  }

  //: How long the handle has to be still before the instruments are told. Short
  //: enough that a keyboard press feels immediate, long enough that a drag across
  //: the track is one recompute rather than four.
  var SETTLE_MS = 90;

  var current = grids()[0] || 6;
  var subs = [];

  function notify() {
    for (var i = 0; i < subs.length; i++) {
      try {
        subs[i](current);
      } catch (e) {
        // One instrument that throws on a size change must not take the other
        // five with it, and the page has no console a reader would read.
        if (window.console && window.console.error) window.console.error(e);
      }
    }
  }

  var announce = P.debounce(notify, SETTLE_MS);

  function subscribe(fn) {
    subs.push(fn);
    return function () {
      var at = subs.indexOf(fn);
      if (at >= 0) subs.splice(at, 1);
    };
  }

  function setGrid(g) {
    if (g === current) return;
    current = g;
    announce();
  }

  /**
   * "12x12, 144 rows" -- what the output prints and a screen reader says.
   *
   * The input's own value is a rung index, so without this a screen reader
   * announces "2". It is the same string either way: one description, so the
   * spoken value and the printed one cannot drift.
   */
  function describe(g) {
    return g + "\u00d7" + g + ", " + (g * g).toLocaleString("en-GB") + " rows";
  }

  function mount(el) {
    P.injectStyle("spinn-sizebar-style", CSS);
    var gs = grids();
    if (!gs.length) throw new Error("size_data.js did not load; there is nothing to size");

    var field = P.el("div", "sp-field sz-wrap");
    var label = P.el("label", "", "Array size");
    var input = document.createElement("input");
    input.type = "range";
    input.min = "0";
    input.max = String(gs.length - 1);
    input.step = "1";
    input.value = String(gs.indexOf(current) >= 0 ? gs.indexOf(current) : 0);
    input.id = "sizeRange";
    label.setAttribute("for", input.id);
    // Above the track, beside its own label, rather than under it. Still an
    // <output for> pointing at the input, which is what it is.
    var out = document.createElement("output");
    out.setAttribute("for", input.id);

    var head = P.el("div", "sz-head");
    head.appendChild(label);
    head.appendChild(out);
    field.appendChild(head);
    field.appendChild(input);

    el.appendChild(field);

    function paint() {
      var g = gs[Number(input.value)];
      out.textContent = describe(g);
      input.setAttribute("aria-valuetext", describe(g));
    }

    function change() {
      paint();
      setGrid(gs[Number(input.value)]);
    }

    input.addEventListener("input", change);
    input.addEventListener("change", change);
    paint();
    // The bar is mounted before the instruments below it, so nothing is listening
    // yet; whatever mounts later reads `current()` for itself.
    setGrid(gs[Number(input.value)]);

    return {
      destroy: function () {
        input.removeEventListener("input", change);
        input.removeEventListener("change", change);
        el.innerHTML = "";
      },
    };
  }

  if (typeof window !== "undefined") {
    window.SpinnSizeBar = {
      mount: mount,
      grids: grids,
      current: function () { return current; },
      dataFor: dataFor,
      data: function () { return dataFor(current); },
      modelFor: modelFor,
      model: function () { return modelFor(current); },
      subscribe: subscribe,
      describe: describe,
    };
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { mount: mount, subscribe: subscribe, describe: describe };
  }
})();
