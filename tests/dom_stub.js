/*
 * The DOM stand-in the widget runners mount against.
 *
 * There is no jsdom here, and the driven Chrome tab cannot stand in for one --
 * that tab is always hidden, so it delivers no observer callbacks and screenshots
 * as a blank field. What the widgets in apps/web/ actually touch is small and
 * boring: create an element, set a class, append a child, measure a width. So the
 * runners hand-build that much.
 *
 * The two parts that genuinely differ per widget are parameters, not copies:
 *
 *   layoutWidth(node)  the layout model. errors.js needs a mini-flexbox that
 *                      parses its own stylesheet; interfere.js needs one capped
 *                      pane. This is the part each runner is really testing.
 *   ctxStub()          the canvas 2D methods that widget calls. Deliberately not
 *                      a union of everything: a widget reaching for a method its
 *                      runner did not declare should throw, not silently no-op.
 *
 * Everything else -- the element factory, the document, the window -- was
 * duplicated line for line between tests/error_widget_runner.js and
 * tests/interference_runner.js before this file existed.
 *
 * ## innerHTML
 *
 * Assigning `innerHTML` *parses*. It has to: six of the ten widgets build a block
 * of controls as a markup string and then query the pieces back out of it, so a
 * stub that stored the string and built no nodes made `querySelector` return null
 * and the widget threw on the next line. That was the single reason most of them
 * could not be mounted here, and why they were tested by grepping their own
 * source instead.
 *
 * The parser below is deliberately small -- tags, attributes, text, void
 * elements, comments -- because that is all these widgets write. It is not an
 * HTML5 parser and does not try to be: no implied tags, no table fixups, no
 * entity decoding beyond leaving text alone. If a widget ever needs more, the
 * failure is a thrown error in a test rather than a silently wrong page.
 */

//: Elements that never have children, so the parser must not look for a close tag.
const VOID_ELEMENTS = new Set([
  "area", "base", "br", "col", "embed", "hr", "img", "input",
  "link", "meta", "param", "source", "track", "wbr",
]);

const TAG = /<(\/)?([a-zA-Z][\w-]*)((?:"[^"]*"|'[^']*'|[^>])*?)(\/)?>/g;
const ATTR = /([\w:-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
const COMMENT = /<!--[\s\S]*?-->/g;

/** Parse an attribute string into a plain object. */
function parseAttrs(text) {
  const out = {};
  if (!text) return out;
  ATTR.lastIndex = 0;
  let m;
  while ((m = ATTR.exec(text)) !== null) {
    const value = m[2] !== undefined ? m[2] : m[3] !== undefined ? m[3] : m[4];
    out[m[1].toLowerCase()] = value === undefined ? "" : value;
  }
  return out;
}

/**
 * Build stub nodes from a markup string.
 *
 * Returns the top-level nodes; `makeEl` supplies elements so parsed nodes are
 * indistinguishable from `document.createElement` ones.
 */
function parseHTML(html, makeEl, makeText) {
  const src = String(html).replace(COMMENT, "");
  const root = { children: [] };
  const stack = [root];
  let last = 0;
  TAG.lastIndex = 0;
  let m;

  const addText = (text) => {
    if (!text || !text.trim()) return;
    stack[stack.length - 1].children.push(makeText(text));
  };

  while ((m = TAG.exec(src)) !== null) {
    addText(src.slice(last, m.index));
    last = TAG.lastIndex;

    const [, closing, rawTag, attrText, selfClosing] = m;
    const tag = rawTag.toLowerCase();

    if (closing) {
      // Close the nearest matching open element; ignore a stray close tag rather
      // than unwinding the whole stack on it.
      for (let i = stack.length - 1; i > 0; i--) {
        if (stack[i].tagName === tag.toUpperCase()) { stack.length = i; break; }
      }
      continue;
    }

    const node = makeEl(tag);
    applyAttrs(node, parseAttrs(attrText));
    const parent = stack[stack.length - 1];
    if (parent.appendChild) parent.appendChild(node);
    else { node.parentNode = null; parent.children.push(node); }
    if (!selfClosing && !VOID_ELEMENTS.has(tag)) stack.push(node);
  }
  addText(src.slice(last));

  for (const c of root.children) c.parentNode = null;
  return root.children;
}

/** Put parsed attributes onto a stub node the way a browser would. */
function applyAttrs(node, attrs) {
  for (const [name, value] of Object.entries(attrs)) {
    node.setAttribute(name, value);
  }
}

/** Match a stub node against the simple selectors the widgets use. */
function matches(node, sel) {
  const s = String(sel).trim();
  if (!s || !node.tagName) return false;
  // One level of compounding is enough for these widgets: "button.foo",
  // ".a.b", "input[type=range]".
  const attr = s.match(/^([^\[]*)\[([\w-]+)(?:=["']?([^\]"']*)["']?)?\]$/);
  if (attr) {
    const [, head, name, want] = attr;
    const got = node.getAttribute(name);
    if (got === null) return false;
    if (want !== undefined && got !== want) return false;
    return head ? matches(node, head) : true;
  }
  const classes = String(node.className).split(/\s+/).filter(Boolean);
  const parts = s.split(".");
  const tag = parts.shift();
  if (tag && tag.startsWith("#")) return node.id === tag.slice(1);
  if (tag && node.tagName !== tag.toUpperCase()) return false;
  return parts.every((c) => classes.includes(c));
}

/** Depth-first collect of descendants matching any comma-separated selector. */
function query(root, sel) {
  const parts = String(sel).split(",").map((x) => x.trim()).filter(Boolean);
  const out = [];
  (function walk(n) {
    for (const c of n.children || []) {
      if (parts.some((p) => matches(c, p))) out.push(c);
      walk(c);
    }
  })(root);
  return out;
}

/** Concatenated text of a subtree, for the textContent getter. */
function textOf(node) {
  if (node.nodeType === 3) return node.nodeValue;
  return (node.children || []).map(textOf).join("");
}

function makeEnv(opts) {
  const styles = {};

  function makeText(text) {
    return { nodeType: 3, nodeValue: text, tagName: null, children: [], parentNode: null };
  }

  function makeEl(tag) {
    const attrs = {};
    const listeners = {};
    let ownText = null;              // set by textContent, cleared by children

    const node = {
      nodeType: 1,
      tagName: String(tag).toUpperCase(),
      className: "",
      id: "",
      children: [],
      parentNode: null,
      style: {},
      dataset: {},
      value: "",
      checked: false,
      disabled: false,

      appendChild(c) { ownText = null; c.parentNode = node; node.children.push(c); return c; },
      insertBefore(c, ref) {
        ownText = null;
        const i = node.children.indexOf(ref);
        c.parentNode = node;
        node.children.splice(i < 0 ? node.children.length : i, 0, c);
        return c;
      },
      removeChild(c) {
        const i = node.children.indexOf(c);
        if (i >= 0) node.children.splice(i, 1);
        c.parentNode = null;
        return c;
      },
      remove() { if (node.parentNode) node.parentNode.removeChild(node); },
      replaceChildren(...kids) {
        node.children.length = 0;
        ownText = null;
        for (const k of kids) node.appendChild(k);
      },

      setAttribute(name, value) {
        attrs[String(name).toLowerCase()] = String(value);
        if (name === "class") node.className = String(value);
        else if (name === "id") node.id = String(value);
        else if (name === "value") node.value = String(value);
        else if (String(name).startsWith("data-")) {
          const key = String(name).slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
          node.dataset[key] = String(value);
        }
      },
      getAttribute(name) {
        const key = String(name).toLowerCase();
        if (key === "class") return node.className || null;
        if (key === "id") return node.id || null;
        return key in attrs ? attrs[key] : null;
      },
      hasAttribute(name) { return node.getAttribute(name) !== null; },
      removeAttribute(name) { delete attrs[String(name).toLowerCase()]; },

      addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
      removeEventListener(type, fn) {
        const list = listeners[type] || [];
        const i = list.indexOf(fn);
        if (i >= 0) list.splice(i, 1);
      },
      /** Fire the handlers registered for `type`; the runners drive widgets with this. */
      dispatch(type, event) {
        for (const fn of listeners[type] || []) fn(Object.assign({
          type, preventDefault() {}, stopPropagation() {}, target: node,
        }, event || {}));
      },
      listenerCount(type) { return (listeners[type] || []).length; },

      classList: {
        add(...cs) {
          const set = new Set(String(node.className).split(/\s+/).filter(Boolean));
          cs.forEach((c) => set.add(c));
          node.className = [...set].join(" ");
        },
        remove(...cs) {
          const set = new Set(String(node.className).split(/\s+/).filter(Boolean));
          cs.forEach((c) => set.delete(c));
          node.className = [...set].join(" ");
        },
        toggle(c, force) {
          const has = node.classList.contains(c);
          const want = force === undefined ? !has : !!force;
          if (want) node.classList.add(c); else node.classList.remove(c);
          return want;
        },
        contains(c) { return String(node.className).split(/\s+/).includes(c); },
      },

      querySelector(sel) { return query(node, sel)[0] || null; },
      querySelectorAll(sel) { return query(node, sel); },
      closest(sel) {
        let n = node;
        while (n) { if (matches(n, sel)) return n; n = n.parentNode; }
        return null;
      },
      contains(other) {
        let n = other;
        while (n) { if (n === node) return true; n = n.parentNode; }
        return false;
      },

      getBoundingClientRect() {
        const width = opts.layoutWidth(node);
        return { width, height: 0, top: 0, left: 0, right: width, bottom: 0, x: 0, y: 0 };
      },
      focus() {}, blur() {}, click() { node.dispatch("click"); },
      setPointerCapture() {}, releasePointerCapture() {},
      scrollIntoView() {},
      appendTo(p) { p.appendChild(node); return node; },
    };

    Object.defineProperty(node, "innerHTML", {
      get() { return node.children.map(serialize).join(""); },
      set(html) {
        node.children.length = 0;
        ownText = null;
        for (const child of parseHTML(html, makeEl, makeText)) node.appendChild(child);
      },
    });

    Object.defineProperty(node, "textContent", {
      get() { return ownText !== null ? ownText : textOf(node); },
      set(text) { node.children.length = 0; ownText = String(text); },
    });

    Object.defineProperty(node, "firstChild", { get() { return node.children[0] || null; } });
    Object.defineProperty(node, "lastChild", {
      get() { return node.children[node.children.length - 1] || null; },
    });
    Object.defineProperty(node, "parentElement", { get() { return node.parentNode; } });
    Object.defineProperty(node, "childNodes", { get() { return node.children; } });
    Object.defineProperty(node, "clientWidth", { get() { return opts.layoutWidth(node); } });
    Object.defineProperty(node, "offsetWidth", { get() { return opts.layoutWidth(node); } });

    if (node.tagName === "CANVAS") {
      node.width = 300; node.height = 150;
      // Memoised, as a real canvas is: getContext("2d") returns the *same*
      // context every time, and a runner that inspects what was drawn has to be
      // looking at the object the widget drew on.
      let ctx = null;
      node.getContext = () => (ctx || (ctx = opts.ctxStub()));
      node.toDataURL = () => "data:,";
    }
    return node;
  }

  /** Enough serialization for the innerHTML getter; the widgets only round-trip. */
  function serialize(node) {
    if (node.nodeType === 3) return node.nodeValue;
    const cls = node.className ? ` class="${node.className}"` : "";
    const id = node.id ? ` id="${node.id}"` : "";
    const inner = node.children.map(serialize).join("");
    const tag = node.tagName.toLowerCase();
    if (VOID_ELEMENTS.has(tag)) return `<${tag}${id}${cls}>`;
    return `<${tag}${id}${cls}>${inner}</${tag}>`;
  }

  const root = makeEl("html");
  const body = makeEl("body");
  root.appendChild(body);

  const doc = {
    documentElement: root,
    body,
    getElementById(id) {
      if (styles[id]) return styles[id];
      return query(root, `#${id}`)[0] || null;
    },
    createElement: (tag) => makeEl(tag),
    createElementNS: (_ns, tag) => makeEl(tag),
    createTextNode: (text) => makeText(text),
    createDocumentFragment: () => makeEl("fragment"),
    querySelector: (sel) => query(root, sel)[0] || null,
    querySelectorAll: (sel) => query(root, sel),
    addEventListener() {},
    removeEventListener() {},
    head: { appendChild(s) { if (s.id) styles[s.id] = s; return s; } },
  };

  // Everything a widget can leave behind, counted.
  //
  // Until the size page there was nothing to count: a widget was mounted once and
  // lived as long as the document, so an observer it never gave back cost nothing
  // and no test could tell the difference. Now each one is mounted again on every
  // size change, and "did `destroy` give everything back" is a question with a
  // right answer -- which needs a window that remembers what it handed out.
  //
  // `live` is what a test asserts on. Every stub increments on creation and
  // decrements on the matching disposal, so a leak is a number that does not
  // return to where it started.
  const live = { resize: 0, mutation: 0, intersection: 0, media: 0, interval: 0,
                 frame: 0, winListener: 0, docListener: 0 };
  const made = { resize: 0, mutation: 0, intersection: 0, media: 0, interval: 0,
                 frame: 0 };

  function tracker(kind) {
    return class {
      constructor(fn) { this.fn = fn; this.observing = false; }
      observe() {
        if (this.observing) return;
        this.observing = true;
        live[kind] += 1;
        made[kind] += 1;
      }
      disconnect() {
        if (!this.observing) return;
        this.observing = false;
        live[kind] -= 1;
      }
      takeRecords() { return []; }
    };
  }

  const timers = new Map();
  let nextTimer = 1;

  const win = {
    document: doc,
    devicePixelRatio: opts.dpr,
    addEventListener() { live.winListener += 1; },
    removeEventListener() { live.winListener -= 1; },
    // Opt in per runner: `plot.js` has a documented fallback for a browser with no
    // ResizeObserver, and a stub that always supplied one would stop exercising it.
    ResizeObserver: opts.observers ? tracker("resize") : undefined,
    MutationObserver: opts.observers ? tracker("mutation") : undefined,
    // The hero watches its own canvas with one of these, to stop animating when it
    // is scrolled past. It is constructed inline and was never held, which is
    // exactly the shape of leak this window exists to notice.
    IntersectionObserver: opts.observers ? tracker("intersection") : undefined,
    matchMedia: opts.observers
      ? function (query) {
        return {
          // A runner asks for reduced motion when it wants the hero's *other*
          // animation path: the one that steps between stills on an interval
          // rather than animating on a frame.
          matches: !!opts.reduceMotion && /reduced-motion/.test(String(query)),
          addEventListener() { live.media += 1; made.media += 1; },
          removeEventListener() { live.media -= 1; },
        };
      }
      : undefined,
    setInterval(fn, ms) {
      const id = nextTimer++;
      timers.set(id, { fn, ms, kind: "interval" });
      live.interval += 1;
      made.interval += 1;
      return id;
    },
    clearInterval(id) { if (timers.delete(id)) live.interval -= 1; },
    setTimeout(fn, ms) {
      const id = nextTimer++;
      timers.set(id, { fn, ms, kind: "timeout" });
      return id;
    },
    clearTimeout(id) { timers.delete(id); },
    requestAnimationFrame(fn) {
      const id = nextTimer++;
      timers.set(id, { fn, kind: "frame" });
      live.frame += 1;
      made.frame += 1;
      return id;
    },
    cancelAnimationFrame(id) { if (timers.delete(id)) live.frame -= 1; },
    //: What is still outstanding, and what was ever handed out. A runner reads
    //: `live` before and after `destroy`; `made` is what says the widget used the
    //: thing at all, so a disposer cannot pass by never having been needed.
    _live: live,
    _made: made,
    _timers: timers,
  };
  if (!opts.observers) {
    delete win.ResizeObserver;
    delete win.MutationObserver;
    delete win.IntersectionObserver;
    delete win.matchMedia;
  }
  // MutationObserver is read off the global rather than off `window` by plot.js,
  // which is what a browser does too.
  if (opts.observers) win.MutationObserver.prototype.constructor = win.MutationObserver;
  doc.addEventListener = function () { live.docListener += 1; };
  doc.removeEventListener = function () { live.docListener -= 1; };
  return { win, doc, makeEl, makeText, body, live, made };
}

/**
 * Evaluate a widget source against one of these environments.
 *
 * The widgets are IIFEs that publish onto `window` and, when running under Node,
 * onto `module.exports`; `new Function` gives each one its own `window` and
 * `document` without a global. `extras` binds any further name the source expects
 * (errors.js wants `atob`).
 */
function loadWidget(src, env, extras) {
  const names = Object.keys(extras || {});
  const mod = { exports: {} };
  const fn = new Function("window", "document", "module", ...names, src);
  fn(env.win, env.doc, mod, ...names.map((k) => extras[k]));
  return mod.exports;
}

module.exports = { makeEnv, loadWidget, parseHTML, matches, query };
