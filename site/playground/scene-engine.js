import { profileFor } from "./scene-profiles.js";

function hash(value) {
  value = Math.imul(value ^ (value >>> 16), 0x45d9f3b);
  value = Math.imul(value ^ (value >>> 16), 0x45d9f3b);
  return (value ^ (value >>> 16)) >>> 0;
}

export async function mountScene(root, context) {
  const profile = profileFor(context.id, context.data, context.seed);
  const canvas = document.createElement("canvas");
  canvas.className = "pg-scene-canvas";
  canvas.setAttribute("aria-hidden", "true");
  root.append(canvas);
  const mask = document.createElement("canvas");
  mask.className = "pg-scene-mask";
  const image = new Image();
  let drawing, stencil, cells = [], active = false, destroyed = false, failed = false;
  let preferences = { ...context.preferences }, dimensions = { width: 0, height: 0, dpr: 1 };
  let dirty = true, ready = false, arrived = false, timer = null, deadline = null;
  let width = 0, height = 0, color = "", phase = 0, start = 0, nextPulse = 0, lastPaint = -Infinity;
  const family = profile.serif ? "Newsreader" : "DM Mono";

  function stop() {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  }

  function destroy() {
    if (destroyed) return;
    destroyed = true;
    active = false;
    stop();
    clearTimeout(deadline);
    context.signal.removeEventListener("abort", destroy);
    image.onload = image.onerror = null;
    image.removeAttribute("src");
    cells = [];
    canvas.width = canvas.height = mask.width = mask.height = 0;
    canvas.remove();
  }
  context.signal.addEventListener("abort", destroy, { once: true });

  function fail(error) {
    if (destroyed || failed) return;
    failed = true;
    stop();
    root.dataset.sceneState = "fallback";
    root.dataset.sceneStatus = "failed";
    context.reportError("The character background could not render; the original signature is shown.", error);
  }

  function place(x, y, size, angle) {
    stencil.save();
    stencil.translate(x + size / 2, y + size * 148 / 700);
    stencil.rotate(angle);
    stencil.drawImage(image, -size / 2, -size * 148 / 700, size, size * 148 / 350);
    stencil.restore();
  }

  function rebuild() {
    width = Math.max(1, dimensions.width);
    height = Math.max(1, dimensions.height);
    const dpr = Math.min(dimensions.dpr, 2, Math.sqrt(600000 / (width * height)));
    const backingWidth = Math.max(1, Math.floor(width * dpr));
    const backingHeight = Math.max(1, Math.floor(height * dpr));
    canvas.width = mask.width = backingWidth;
    canvas.height = mask.height = backingHeight;
    stencil.setTransform(backingWidth / width, 0, 0, backingHeight / height, 0, 0);
    stencil.clearRect(0, 0, width, height);
    const size = Math.min(width * 1.18, height * 2.8);
    place((width - size) * .48, height * .55 - size * 148 / 700, size, profile.angle);
    const stamp = Math.min(280, width * .62);
    place(width - stamp - Math.min(50, width * .06), height - stamp * 148 / 350 - 6, stamp, profile.angle * -1.5);
    color = getComputedStyle(root).color;
    stencil.globalCompositeOperation = "source-in";
    stencil.fillStyle = color;
    stencil.fillRect(0, 0, width, height);
    stencil.globalCompositeOperation = "source-over";
    const pixels = stencil.getImageData(0, 0, backingWidth, backingHeight).data;
    const unit = Math.max(4, Math.min(8.5, width / 90));
    const cellWidth = unit * profile.cell[0], cellHeight = unit * profile.cell[1];
    const columns = Math.ceil(width / cellWidth);
    const occupied = new Map();
    for (let y = 0; y < backingHeight; y += 2) {
      for (let x = 0; x < backingWidth; x += 2) {
        if (pixels[(y * backingWidth + x) * 4 + 3] < 40) continue;
        const column = Math.floor(x * width / backingWidth / cellWidth);
        const row = Math.floor(y * height / backingHeight / cellHeight);
        const key = row * columns + column;
        if (occupied.has(key)) continue;
        const n = hash(key ^ context.seed);
        occupied.set(key, {
          x: (column + .5 + ((n % 101) / 100 - .5) * profile.jitter) * cellWidth,
          y: (row + .5 + ((n % 137) / 136 - .5) * profile.jitter) * cellHeight,
          glyph: profile.glyphs[n % profile.glyphs.length], n, size: unit * profile.size,
        });
      }
    }
    cells = [...occupied.values()];
    if (cells.length > 3000) {
      const stride = cells.length / 3000;
      cells = Array.from({ length: 3000 }, (_, index) => cells[Math.floor(index * stride)]);
    }
    root.dataset.sceneCells = String(cells.length);
    root.dataset.sceneProfile = profile.reveal;
    dirty = false;
  }

  function paint(progress = 1) {
    if (!active || destroyed || failed || !ready) return;
    try {
      if (preferences.forcedColors) {
        root.dataset.sceneState = "vector";
        root.dataset.sceneStatus = "ready";
        return;
      }
      lastPaint = performance.now();
      if (dirty) rebuild();
      root.dataset.sceneState = "glyphs";
      drawing.setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);
      drawing.clearRect(0, 0, width, height);
      drawing.fillStyle = color;
      drawing.textAlign = "center";
      drawing.textBaseline = "middle";
      for (const cell of cells) {
        let order = (cell.n % 997) / 997;
        if (profile.reveal === "scan") order = cell.y / height;
        if (profile.reveal === "columns") order = cell.x / width;
        if (profile.reveal === "coordinates") order = (cell.x / width + cell.y / height) / 2;
        drawing.globalAlpha = progress >= order ? 1 : .18;
        drawing.font = `${profile.weight} ${cell.size}px "${family}", monospace`;
        let x = cell.x, y = cell.y;
        if (progress < 1 && profile.reveal === "blocks" && cell.n % 7 === phase % 7) x += 3;
        if (profile.reveal === "trails" && cell.n % 3 === 0) {
          drawing.fillRect(x, y, cell.size * 1.6, Math.max(.5, cell.size / 9));
        }
        if (profile.reveal === "stamp" && cell.n % 5 === 0) {
          drawing.save();
          drawing.translate(x, y);
          drawing.rotate(-.12);
          drawing.fillText(cell.glyph, 0, 0);
          drawing.restore();
        } else drawing.fillText(cell.glyph, x, y);
      }
      drawing.globalAlpha = 1;
      drawing.globalCompositeOperation = "destination-in";
      drawing.drawImage(mask, 0, 0, width, height);
      drawing.globalCompositeOperation = "destination-over";
      drawing.globalAlpha = profile.underlay;
      drawing.drawImage(mask, 0, 0, width, height);
      drawing.globalAlpha = 1;
      drawing.globalCompositeOperation = "source-over";
      root.dataset.sceneStatus = "ready";
    } catch (error) { fail(error); }
  }

  function frame() {
    timer = null;
    if (!active || destroyed || failed) return;
    const progress = Math.min(1, (performance.now() - start) / 500);
    paint(progress);
    if (progress < 1 && !preferences.reducedMotion && !preferences.forcedColors) {
      timer = setTimeout(frame, 90);
    }
  }

  function pulse() {
    if (!active || !ready || destroyed || failed || preferences.forcedColors || timer !== null) return;
    const now = performance.now();
    if (now < nextPulse) return;
    nextPulse = now + 1100;
    phase++;
    if (preferences.reducedMotion) {
      requestPaint();
      return;
    }
    const delay = Math.max(0, 90 - (now - lastPaint));
    start = now + delay;
    if (delay) timer = setTimeout(frame, delay);
    else frame();
  }

  function requestPaint() {
    if (!active || timer !== null) return;
    const delay = Math.max(0, 90 - (performance.now() - lastPaint));
    if (delay) timer = setTimeout(() => { timer = null; paint(); }, delay);
    else paint();
  }

  const controller = {
    setActive(value) {
      if (destroyed || active === Boolean(value)) return;
      active = Boolean(value);
      root.dataset.sceneActive = String(active);
      if (!active) { stop(); return; }
      if (ready) {
        if (!arrived && !preferences.forcedColors) { arrived = true; pulse(); }
        else requestPaint();
      }
    },
    resize(value) {
      if (destroyed) return;
      if (![value.width, value.height, value.dpr].every(Number.isFinite)
        || value.width <= 0 || value.height <= 0 || value.dpr <= 0) {
        throw new Error("The signature background received invalid dimensions.");
      }
      if (Object.keys(dimensions).every(key => dimensions[key] === value[key])) return;
      dimensions = { ...value };
      dirty = true;
      requestPaint();
    },
    setPreferences(value) {
      if (destroyed) return;
      preferences = { ...value };
      dirty = true;
      stop();
      requestPaint();
    },
    pulse,
    destroy,
  };

  try {
    if (context.signal.aborted) throw context.signal.reason;
    drawing = canvas.getContext("2d");
    stencil = mask.getContext("2d", { willReadFrequently: true });
    if (!drawing || !stencil) throw new Error("A 2D signature background is unavailable.");
    await new Promise((resolve, reject) => {
      const abort = () => { cleanup(); reject(context.signal.reason); };
      const cleanup = () => {
        clearTimeout(deadline);
        context.signal.removeEventListener("abort", abort);
      };
      const loaded = new Promise((done, failed) => {
        image.onload = done;
        image.onerror = () => failed(new Error("The original signature could not load."));
        image.src = context.data.signature.src;
      });
      context.signal.addEventListener("abort", abort, { once: true });
      deadline = setTimeout(() => {
        cleanup();
        reject(new Error("The signature background took too long to load."));
      }, 8000);
      Promise.all([loaded, document.fonts.load(`12px "${family}"`)]).then(([, fonts]) => {
        cleanup();
        if (!fonts.length) reject(new Error(`The local ${family} scene font could not load.`));
        else resolve();
      }, error => { cleanup(); reject(error); });
    });
    if (context.signal.aborted) throw context.signal.reason;
    ready = true;
    return controller;
  } catch (error) {
    destroy();
    throw error;
  }
}
