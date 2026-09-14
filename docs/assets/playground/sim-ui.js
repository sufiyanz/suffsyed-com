export function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function button(text, action, lifecycle, className = "") {
  const node = element("button", `pg-button ${className}`, text);
  node.type = "button";
  lifecycle.listen(node, "click", action);
  return node;
}

export async function readyFont(signal) {
  if (signal.aborted) return;
  const faces = await document.fonts.load('400 12px "DM Mono"', "+x./");
  if (signal.aborted) return;
  if (!faces.length || faces.some(face => face.status !== "loaded")) {
    throw new Error("The existing local DM Mono font could not be loaded.");
  }
}

export function colors(context, preferences) {
  const p = context.palette;
  return preferences.forcedColors
    ? { background: "Canvas", ink: "CanvasText", line: "CanvasText", accent: "Highlight", reverse: "HighlightText", muted: "CanvasText" }
    : { background: p.paper, ink: p.forest, line: p.stone, accent: p.green, reverse: p.white, muted: p.green };
}

export function canvasSurface(canvas) {
  const drawing = canvas.getContext("2d");
  if (!drawing) throw new Error("Canvas 2D is unavailable in this browser.");
  let width = 620, height = 380;
  return {
    drawing,
    get width() { return width; },
    get height() { return height; },
    resize(dpr) {
      const bounds = canvas.getBoundingClientRect();
      if (!Number.isFinite(dpr) || dpr <= 0) throw new RangeError("Canvas DPR must be positive.");
      // A hidden/zero-size stage is valid; retain its last meaningful bitmap.
      if (!bounds.width || !bounds.height) return;
      width = bounds.width;
      height = bounds.height;
      const ratio = Math.min(dpr, 2, Math.sqrt(1000000 / (width * height)));
      canvas.width = Math.max(1, Math.floor(width * ratio));
      canvas.height = Math.max(1, Math.floor(height * ratio));
    },
    begin() {
      drawing.setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);
      drawing.clearRect(0, 0, width, height);
      drawing.globalAlpha = 1;
      drawing.lineWidth = 1;
      drawing.setLineDash([]);
    },
  };
}

export function lifecycle(root, context) {
  const events = new AbortController();
  let active = false, ready = false, destroyed = false, requested = false;
  let timer = null, lastTime = null;
  let frame = () => {}, sync = () => {}, cleanup = () => {};
  let preferences = { ...context.preferences };
  const canRun = () => active && ready && requested && !destroyed && !document.hidden;

  function stop() {
    if (timer !== null) clearTimeout(timer);
    timer = null;
    lastTime = null;
  }

  function fail(error) {
    destroy();
    context.reportError("This local experiment stopped. Close it and try again.", error);
  }

  function guard(action) {
    return (...args) => {
      if (destroyed) return;
      try { return action(...args); } catch (error) { fail(error); }
    };
  }

  function schedule() {
    if (timer !== null || !canRun()) return;
    lastTime = performance.now();
    timer = setTimeout(tick, 34);
  }

  function tick() {
    timer = null;
    if (!canRun()) return;
    const now = performance.now();
    const dt = Math.min(0.1, (now - lastTime) / 1000);
    lastTime = now;
    try {
      frame(dt);
      if (canRun()) timer = setTimeout(tick, 34);
    } catch (error) { fail(error); }
  }

  function suspend() {
    stop();
    for (const node of root.querySelectorAll("[data-pointer-id]")) {
      const pointer = Number(node.dataset.pointerId);
      if (node.hasPointerCapture(pointer)) node.releasePointerCapture(pointer);
      delete node.dataset.pointerId;
    }
    cleanup();
  }

  function destroy() {
    if (destroyed) return;
    destroyed = true;
    active = requested = false;
    suspend();
    events.abort();
    context.signal.removeEventListener("abort", destroy);
    frame = sync = cleanup = () => {};
    api.onResize = () => {};
    root.replaceChildren();
  }

  const api = {
    get active() { return active && ready && !destroyed && !document.hidden; },
    get destroyed() { return destroyed; },
    get preferences() { return preferences; },
    listen(target, event, action, options = {}) {
      target.addEventListener(event, guard(action), { ...options, signal: events.signal });
    },
    configure(handlers) {
      frame = handlers.frame;
      sync = handlers.sync;
      cleanup = handlers.cleanup || (() => {});
    },
    setRunning(value) {
      requested = value;
      if (!value) stop();
      else schedule();
    },
    prepared() {
      if (destroyed) return;
      ready = true;
      sync();
      schedule();
    },
    controller: {
      setActive: guard(value => {
        active = Boolean(value);
        if (!active) suspend();
        sync();
        schedule();
      }),
      resize: guard(size => {
        if (![size.width, size.height, size.dpr].every(Number.isFinite) ||
            size.width < 0 || size.height < 0 || size.dpr <= 0) {
          throw new RangeError("The host supplied invalid experiment dimensions.");
        }
        api.onResize(size);
      }),
      setPreferences: guard(value => {
        if (typeof value.reducedMotion !== "boolean" || typeof value.forcedColors !== "boolean") {
          throw new TypeError("The host supplied invalid experiment preferences.");
        }
        preferences = { ...value };
        root.dataset.forcedColors = String(preferences.forcedColors);
        suspend();
        sync();
        schedule();
      }),
      destroy,
    },
    onResize: () => {},
  };
  root.dataset.forcedColors = String(preferences.forcedColors);
  context.signal.addEventListener("abort", destroy, { once: true });
  api.listen(document, "visibilitychange", () => {
    if (document.hidden) suspend();
    sync();
    schedule();
  });
  if (context.signal.aborted) destroy();
  return api;
}
