/*
 * size_page.js -- what makes six instruments follow one control.
 *
 * Each widget on the size page is mounted through `own()` instead of directly.
 * That does two things: it hands the widget the chosen array's data instead of
 * `window.SpinnData`, and it keeps hold of what `mount` returned, so that when the
 * size changes the instrument can be **destroyed and built again** rather than
 * asked to reconfigure itself.
 *
 * Why destroy and rebuild, rather than a `setData`
 * ------------------------------------------------
 * Because the alternative is six widgets each growing a second entry point that
 * has to put every piece of their own state back to a consistent place -- the
 * wire column's chosen column, the bench's three sliders and its seed, the draw
 * pad's strokes, the hero's animation phase -- and a size change that left any one
 * of them half-converted would look like a rendering bug at one size only. A mount
 * already knows how to produce a correct instrument from nothing. The cost is that
 * `destroy` has to be real, which is why `plot.js`'s observers return disposers and
 * why the hero gives back its interval, its frame and its own observer.
 *
 * What this file is not
 * ---------------------
 * It is not a framework and does not want to be one. It is a list, a loop, and an
 * unsubscribe.
 */
(function () {
  "use strict";

  var owned = [];
  var unsubscribe = null;

  function dataNow() {
    var bar = window.SpinnSizeBar;
    return bar ? bar.data() : window.SpinnData;
  }

  function build(entry) {
    try {
      entry.instance = entry.mounter(entry.el, { data: dataNow() });
    } catch (e) {
      entry.instance = null;
      // One instrument that cannot build must not stop the other five. The reader
      // sees an empty panel under a caption that says what would have been there,
      // which is the same fallback a reader without a script gets.
      if (window.console && window.console.error) window.console.error(e);
    }
  }

  function rebuildAll() {
    for (var i = 0; i < owned.length; i++) {
      var entry = owned[i];
      if (entry.instance && typeof entry.instance.destroy === "function") {
        try {
          entry.instance.destroy();
        } catch (e) {
          if (window.console && window.console.error) window.console.error(e);
        }
      } else {
        // A widget with no disposer still must not be mounted on top of itself.
        // This keeps the page correct and leaks whatever that widget was holding,
        // which is the honest half-measure and not a substitute for a `destroy`.
        entry.el.innerHTML = "";
      }
      entry.instance = null;
      build(entry);
    }
  }

  /**
   * Mount `mounter` into `el` at the current size, and rebuild it on every change.
   *
   * `mounter(el, opts)` is the widget's own mount call, and what it returns is
   * expected to carry `destroy`. A widget that returns nothing still works -- it
   * is simply never torn down, and its host is emptied before the next mount, so
   * the page stays correct and leaks whatever that widget was holding.
   */
  function own(el, mounter) {
    var entry = { el: el, mounter: mounter, instance: null };
    owned.push(entry);
    build(entry);
    if (!unsubscribe && window.SpinnSizeBar) {
      unsubscribe = window.SpinnSizeBar.subscribe(rebuildAll);
    }
    return entry;
  }

  if (typeof window !== "undefined") {
    window.SpinnSizePage = { own: own, rebuildAll: rebuildAll, owned: owned };
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { own: own, rebuildAll: rebuildAll, owned: owned };
  }
})();
