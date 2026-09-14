export function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

export function button(text) {
  const node = element("button", "pg-button", text);
  node.type = "button";
  return node;
}

export function field(parent, text, input) {
  const label = element("label", "pg-field");
  const caption = element("span", "", text);
  label.append(caption, input);
  parent.append(label);
  return caption;
}

export function choices(parent, text, rows) {
  const select = element("select");
  select.setAttribute("aria-label", text);
  for (const row of rows) {
    const option = element("option", "", row.title || row.alt || row.id);
    option.value = row.id;
    select.append(option);
  }
  const wrapper = element("span", "photo-select");
  wrapper.append(select);
  field(parent, text, wrapper);
  select.disabled = !rows.length;
  return select;
}

export function slider(parent, text, min, max, step, value, format = String) {
  const input = element("input");
  input.type = "range";
  input.min = min;
  input.max = max;
  input.step = step;
  input.value = value;
  input.setAttribute("aria-label", text);
  const caption = field(parent, text, input);
  const output = element("output");
  caption.append(output);
  const update = () => {
    const value = Math.min(max, Math.max(min, Number(input.value)));
    input.value = value;
    output.value = format(value);
    input.setAttribute("aria-valuetext", format(value));
    return value;
  };
  update();
  return {input, update};
}

export function context2d(canvas, options) {
  const context = canvas.getContext("2d", options);
  if (!context) throw new Error("This browser could not open a 2D canvas.");
  return context;
}

export function fitSize(width, height, maximumWidth, maximumHeight, dpr = 1) {
  const scale = Math.min(
    Math.max(1, maximumWidth) * Math.min(2, Math.max(1, dpr)) / width,
    Math.max(1, maximumHeight) * Math.min(2, Math.max(1, dpr)) / height,
    Math.sqrt(1000000 / (width * height)), 1,
  );
  return {width: Math.max(1, Math.floor(width * scale)), height: Math.max(1, Math.floor(height * scale))};
}

export function randomFor(seed) {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let n = Math.imul(state ^ state >>> 15, 1 | state);
    n ^= n + Math.imul(n ^ n >>> 7, 61 | n);
    return ((n ^ n >>> 14) >>> 0) / 4294967296;
  };
}

export function rgb(hex) {
  if (!/^#[0-9a-f]{6}$/i.test(hex)) throw new Error("The photograph palette is invalid.");
  return [1, 3, 5].map(index => parseInt(hex.slice(index, index + 2), 16));
}

export function localURL(value) {
  const url = new URL(value, location.href);
  if (url.origin !== location.origin || !["http:", "https:"].includes(url.protocol)) {
    throw new Error("Only the site's local photograph and passage sources are supported.");
  }
  return url.href;
}

export async function loadPhoto(photo, signal) {
  const response = await fetch(localURL(photo.src), {signal, credentials: "same-origin"});
  if (!response.ok) throw new Error(`Photograph request failed (${response.status}).`);
  const blob = await response.blob();
  signal.throwIfAborted();
  if (!blob.type.startsWith("image/")) throw new Error("The photograph response was not an image.");
  const url = URL.createObjectURL(blob);
  const image = new Image();
  image.decoding = "async";
  try {
    await new Promise((resolve, reject) => {
      const clean = () => {
        image.onload = image.onerror = null;
        signal.removeEventListener("abort", abort);
      };
      const abort = () => { clean(); image.removeAttribute("src"); reject(new DOMException("Cancelled", "AbortError")); };
      image.onload = () => { clean(); resolve(); };
      image.onerror = () => { clean(); reject(new Error("The photograph could not be decoded.")); };
      signal.addEventListener("abort", abort, {once: true});
      image.src = url;
    });
    signal.throwIfAborted();
    if (!image.naturalWidth || !image.naturalHeight) throw new Error("The photograph has no drawable pixels.");
    return image;
  } finally {
    URL.revokeObjectURL(url);
  }
}

export async function loadFonts(signal) {
  let timeout;
  let abort;
  try {
    const fonts = await Promise.race([
      Promise.all([document.fonts.load('400 24px "Newsreader"'), document.fonts.load('400 12px "DM Mono"')]),
      new Promise((resolve, reject) => {
        abort = () => reject(new DOMException("Cancelled", "AbortError"));
        signal.addEventListener("abort", abort, {once: true});
        timeout = setTimeout(() => reject(new Error("Local font loading timed out.")), 4000);
      }),
    ]);
    signal.throwIfAborted();
    if (fonts.some(rows => !rows.length)) throw new Error("The local editorial fonts were not available.");
  } finally {
    clearTimeout(timeout);
    signal.removeEventListener("abort", abort);
  }
}

export function runtime(root, ctx) {
  const events = new AbortController();
  let work = new AbortController();
  let timer = 0;
  let active = false;
  let destroyed = false;
  let revision = 0;
  let exporting = false;
  const cleanups = [];
  const error = element("p", "photo-error");
  error.hidden = true;
  root.append(error);
  const cancel = () => {
    clearTimeout(timer);
    timer = 0;
    revision++;
    exporting = false;
    work.abort();
  };
  const destroy = () => {
    if (destroyed) return;
    destroyed = true;
    active = false;
    cancel();
    events.abort();
    ctx.signal.removeEventListener("abort", destroy);
    cleanups.forEach(clean => clean());
    root.replaceChildren();
  };
  ctx.signal.addEventListener("abort", destroy, {once: true});
  if (ctx.signal.aborted) destroy();
  return {
    get live() { return !destroyed && !ctx.signal.aborted; },
    get active() { return active; },
    on(node, type, fn) { node.addEventListener(type, fn, {signal: events.signal}); },
    cleanup(fn) { if (destroyed) fn(); else cleanups.push(fn); },
    begin() {
      cancel();
      work = new AbortController();
      const current = revision;
      return {signal: work.signal, valid: () => !destroyed && !work.signal.aborted && current === revision};
    },
    cancel,
    setActive(value) { active = Boolean(value) && !destroyed; if (!active) cancel(); },
    queue(fn) {
      clearTimeout(timer);
      timer = 0;
      if (active && !destroyed) timer = setTimeout(() => { timer = 0; if (active && !destroyed) fn(); }, 40);
    },
    status(message) { if (!destroyed) ctx.setStatus(message); },
    clearError() { if (!destroyed) { error.hidden = true; error.textContent = ""; } },
    fail(message, cause) {
      if (destroyed || cause?.name === "AbortError") return;
      error.textContent = message;
      error.hidden = false;
      ctx.reportError(message, cause);
    },
    preferences(value) {
      if (!destroyed) {
        root.dataset.photoContrast = value.forcedColors ? "forced" : "normal";
        root.dataset.photoMotion = value.reducedMotion ? "reduced" : "normal";
      }
    },
    download(canvas, name, control) {
      if (!active || destroyed || control.disabled || exporting) return;
      const current = revision;
      exporting = true;
      try {
        canvas.toBlob(blob => {
          if (destroyed || current !== revision) return;
          exporting = false;
          if (!active) return;
          if (!blob || blob.type !== "image/png") {
            this.fail("PNG export was unavailable. You can keep editing or retry.");
            return;
          }
          const url = URL.createObjectURL(blob);
          const link = element("a");
          link.download = name;
          link.href = url;
          root.append(link);
          try {
            link.click();
            this.status(`Downloaded ${canvas.width} by ${canvas.height} PNG. Your source stays unchanged.`);
          } finally {
            link.remove();
            URL.revokeObjectURL(url);
          }
        }, "image/png");
      } catch (cause) {
        exporting = false;
        this.fail("PNG export failed. Your original photograph has not changed.", cause);
      }
    },
    destroy,
  };
}
