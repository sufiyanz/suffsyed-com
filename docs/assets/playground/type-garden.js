const GLYPHS = "TYPE/garden+";
const FRAME_MS = 1000 / 30;
const MAX_PIXELS = 1000000;

export async function mount(root, context) {
  const listeners = new AbortController();
  let active = false, destroyed = false, ready = false, failed = false, paused = false;
  let preferences = { ...context.preferences };
  let raf = 0, lastFrame = 0, pointerId = null, held = false, keyboardHeld = false;
  let width = 0, height = 0, ratio = 1, particles = [], image, drawing, mask, maskDrawing;
  let fontSize = 10, fontFamily = "", color = "", accent = "", mode = "attract";
  const aim = { x: 0, y: 0, visible: false };
  const glyphs = Array.from({ length: 500 }, () => GLYPHS[Math.floor(context.random() * GLYPHS.length)]);

  function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  const help = element("p", "pg-help type-help", "Drag to disturb. Release to return.");
  const controls = element("div", "pg-controls type-controls");
  const modeLabel = element("label", "type-mode");
  const modeSelect = element("select", "pg-field");
  modeSelect.setAttribute("aria-label", "Garden force");
  for (const [value, title] of [["attract", "Attract"], ["repel", "Repel"], ["flow", "Flow"]]) {
    const option = element("option", "", title);
    option.value = value;
    modeSelect.append(option);
  }
  modeLabel.append(modeSelect);
  const pause = element("button", "pg-button", "Pause");
  const reform = element("button", "pg-button type-reform", "Re-form");
  const step = element("button", "pg-button", "Step");
  pause.type = reform.type = step.type = "button";
  step.title = "Apply one nudge at the aiming point without animation";
  controls.append(modeLabel, pause, reform, step);
  const stage = element("div", "pg-stage type-stage");
  const canvas = element("canvas", "type-canvas", "Suff Syed's autograph, composed of bold, individually planted letters. Drag to move them; release to restore the signature.");
  canvas.dataset.worldSignature = "type-garden";
  canvas.tabIndex = 0;
  canvas.setAttribute("role", "application");
  canvas.setAttribute("aria-roledescription", "interactive signature garden");
  canvas.setAttribute("aria-label", "Type garden. Arrow keys aim the force; hold Space or Enter to apply it; release to re-form. Escape releases the tool.");
  const poster = element("div", "type-poster");
  poster.setAttribute("aria-hidden", "true");
  const title = element("span", "type-title", "TYPE");
  const edition = element("span", "type-edition", "LIVING\nLETTERFORMS\nNO. 01");
  const word = element("span", "type-word", "GARDEN");
  const caption = element("span", "type-caption", "250 LETTERS / ONE SIGNATURE");
  poster.append(title, edition, word, caption);
  stage.append(canvas, poster);
  const summary = element("p", "type-summary", "Preparing the original autograph...");
  const error = element("p", "type-error");
  error.hidden = true;
  root.append(stage, help, controls, summary, error);
  root.dataset.state = "loading";

  function say(message) {
    if (destroyed) return;
    summary.textContent = message;
    context.setStatus(message);
  }

  function cancelFrame() {
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    lastFrame = 0;
  }

  function release() {
    held = keyboardHeld = false;
    const captured = pointerId;
    pointerId = null;
    if (captured !== null && canvas.hasPointerCapture(captured)) canvas.releasePointerCapture(captured);
  }

  function destroy() {
    if (destroyed) return;
    destroyed = true;
    active = false;
    cancelFrame();
    release();
    listeners.abort();
    context.signal.removeEventListener("abort", destroy);
    if (image) image.removeAttribute("src");
    particles = [];
    canvas.width = canvas.height = 0;
    if (mask) mask.width = mask.height = 0;
    root.replaceChildren();
  }
  context.signal.addEventListener("abort", destroy, { once: true });
  if (context.signal.aborted) {
    destroy();
    return { setActive() {}, resize() {}, setPreferences() {}, destroy };
  }

  function canWork() {
    return ready && active && !paused && !failed && !destroyed && !document.hidden;
  }

  function unsettled() {
    return particles.some(particle => Math.abs(particle.x - particle.tx) + Math.abs(particle.y - particle.ty) > .15
      || Math.abs(particle.vx) + Math.abs(particle.vy) > .8);
  }

  function updateControls() {
    if (destroyed) return;
    for (const control of [modeSelect, pause, reform, step]) control.disabled = !ready || !active || failed;
    step.disabled ||= paused;
    pause.textContent = paused ? "Resume" : "Pause";
    pause.setAttribute("aria-pressed", String(paused));
    pause.setAttribute("aria-label", `${paused ? "Resume" : "Pause"} garden motion`);
    step.hidden = !preferences.reducedMotion;
    canvas.setAttribute("aria-disabled", String(!canWork()));
    canvas.setAttribute("aria-label", preferences.reducedMotion
      ? "Type garden. Arrow keys aim; Step applies one nudge. Re-form restores the autograph. Dragging also applies the force without animation."
      : "Type garden. Arrow keys aim; hold Space or Enter to apply the force; release to re-form. Escape releases the tool.");
    root.dataset.state = failed ? "failed" : !ready ? "loading" : !active ? "inactive"
      : paused ? "paused" : preferences.reducedMotion ? "manual" : held ? "held" : unsettled() ? "returning" : "resting";
    root.dataset.reducedMotion = String(preferences.reducedMotion);
    root.dataset.forcedColors = String(preferences.forcedColors);
  }

  function fail(cause) {
    if (destroyed) return;
    failed = true;
    cancelFrame();
    release();
    error.hidden = false;
    error.textContent = "The letter garden could not be drawn. The original autograph is still available when you close this experiment.";
    summary.textContent = "Type garden is unavailable.";
    updateControls();
    context.reportError("Type garden could not prepare its local signature and font.", cause);
  }

  function colors() {
    const style = getComputedStyle(canvas);
    color = preferences.forcedColors ? "CanvasText" : style.getPropertyValue("--pg-world-signature").trim();
    accent = preferences.forcedColors ? "CanvasText" : style.getPropertyValue("--pg-world-ink").trim();
    if (!color || !accent) throw new Error("The Type garden world palette is unavailable.");
    fontFamily = style.fontFamily;
  }

  function paint() {
    if (!ready || destroyed || failed || !width || !height) return;
    drawing.setTransform(1, 0, 0, 1, 0, 0);
    drawing.clearRect(0, 0, canvas.width, canvas.height);
    drawing.setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);
    drawing.globalAlpha = preferences.forcedColors ? .2 : .14;
    drawing.drawImage(mask, 0, 0, width, height);
    drawing.globalAlpha = 1;
    drawing.fillStyle = color;
    drawing.font = `900 ${fontSize}px ${fontFamily}`;
    drawing.textAlign = "center";
    drawing.textBaseline = "middle";
    for (const particle of particles) drawing.fillText(particle.glyph, particle.x, particle.y);
    if (aim.visible && active) {
      drawing.strokeStyle = accent;
      drawing.lineWidth = 1;
      drawing.setLineDash(held ? [] : [2, 4]);
      drawing.beginPath();
      drawing.arc(aim.x, aim.y, held ? 13 : 9, 0, Math.PI * 2);
      drawing.stroke();
      drawing.setLineDash([]);
    }
  }

  function build() {
    if (!ready || destroyed || failed) return;
    const bounds = stage.getBoundingClientRect();
    const nextWidth = Math.max(1, Math.floor(bounds.width));
    const nextHeight = Math.max(1, Math.floor(bounds.height));
    const dpr = Math.min(ratio, 2, Math.sqrt(MAX_PIXELS / (nextWidth * nextHeight)));
    const backingWidth = Math.max(1, Math.floor(nextWidth * dpr));
    const backingHeight = Math.max(1, Math.floor(nextHeight * dpr));
    if (width === nextWidth && height === nextHeight && canvas.width === backingWidth && canvas.height === backingHeight) return;
    const oldWidth = width, oldHeight = height, previous = particles;
    width = nextWidth;
    height = nextHeight;
    canvas.width = mask.width = backingWidth;
    canvas.height = mask.height = backingHeight;
    const [, , sourceWidth, sourceHeight] = context.data.signature.viewBox;
    const posterTop = width < 500 ? 58 : 24;
    const posterBottom = width < 500 ? 40 : 24;
    const scale = Math.min((width - 24) / sourceWidth, (height - posterTop - posterBottom) / sourceHeight, 2.65);
    const imageWidth = Math.max(1, sourceWidth * scale), imageHeight = Math.max(1, sourceHeight * scale);
    const left = (width - imageWidth) / 2, top = posterTop + (height - posterTop - posterBottom - imageHeight) / 2;
    maskDrawing.setTransform(backingWidth / width, 0, 0, backingHeight / height, 0, 0);
    maskDrawing.drawImage(image, left, top, imageWidth, imageHeight);
    const pixels = maskDrawing.getImageData(0, 0, mask.width, mask.height).data;
    const budget = width < 500 ? 250 : 500;
    fontSize = width < 500 ? 8.5 : 12;
    // One mask read per resolution; occupied tiles keep the fine autograph hairlines.
    const tile = width < 500 ? 3.8 : 5.5;
    const columns = Math.ceil(width / tile);
    const tiles = new Map();
    for (let y = 0; y < mask.height; y++) {
      for (let x = 0; x < mask.width; x++) {
        if (pixels[(y * mask.width + x) * 4 + 3] < 40) continue;
        const px = (x + .5) * width / mask.width, py = (y + .5) * height / mask.height;
        const key = Math.floor(py / tile) * columns + Math.floor(px / tile);
        const point = tiles.get(key);
        if (point) { point.x += px; point.y += py; point.count++; }
        else tiles.set(key, { x: px, y: py, count: 1 });
      }
    }
    const targets = [...tiles.values()].map(point => ({ x: point.x / point.count, y: point.y / point.count }));
    if (!targets.length) throw new Error("The signature mask contains no drawable points.");
    const count = Math.min(budget, targets.length);
    particles = Array.from({ length: count }, (_, index) => {
      const target = targets[Math.floor(index * targets.length / count)];
      const old = previous[index];
      return {
        tx: target.x, ty: target.y, glyph: glyphs[index], vx: 0, vy: 0,
        x: target.x + (old && oldWidth ? (old.x - old.tx) * width / oldWidth : 0),
        y: target.y + (old && oldHeight ? (old.y - old.ty) * height / oldHeight : 0),
      };
    });
    caption.textContent = `${count} LETTERS / ONE SIGNATURE`;
    aim.x = oldWidth ? aim.x * width / oldWidth : width / 2;
    aim.y = oldHeight ? aim.y * height / oldHeight : top + imageHeight / 2;
    tintMask();
    paint();
  }

  function tintMask() {
    maskDrawing.save();
    maskDrawing.setTransform(1, 0, 0, 1, 0, 0);
    maskDrawing.globalCompositeOperation = "source-in";
    maskDrawing.fillStyle = color;
    maskDrawing.fillRect(0, 0, mask.width, mask.height);
    maskDrawing.restore();
  }

  function force(x, y) {
    const dx = aim.x - x, dy = aim.y - y, distance = Math.hypot(dx, dy);
    const reach = Math.max(65, Math.min(120, width * .24));
    const strength = Math.max(0, 1 - distance / reach);
    const divisor = Math.max(12, distance);
    if (mode === "flow") return { x: -dy / divisor * strength, y: dx / divisor * strength };
    const direction = mode === "repel" ? -1 : 1;
    return { x: dx / divisor * strength * direction, y: dy / divisor * strength * direction };
  }

  function advance(dt) {
    for (const particle of particles) {
      const push = held ? force(particle.x, particle.y) : { x: 0, y: 0 };
      particle.vx += ((particle.tx - particle.x) * 42 + push.x * 2200) * dt;
      particle.vy += ((particle.ty - particle.y) * 42 + push.y * 2200) * dt;
      const damping = Math.exp(-8 * dt);
      particle.vx = Math.max(-360, Math.min(360, particle.vx * damping));
      particle.vy = Math.max(-360, Math.min(360, particle.vy * damping));
      particle.x = Math.max(4, Math.min(width - 4, particle.x + particle.vx * dt));
      particle.y = Math.max(4, Math.min(height - 4, particle.y + particle.vy * dt));
    }
  }

  function snapHome() {
    for (const particle of particles) {
      particle.x = particle.tx; particle.y = particle.ty; particle.vx = particle.vy = 0;
    }
  }

  function gardenFrame(now) {
    raf = 0;
    if (!canWork() || preferences.reducedMotion) return;
    if (now - lastFrame >= FRAME_MS) {
      const dt = Math.min((now - lastFrame) / 1000, 1 / 30);
      lastFrame = now;
      advance(dt);
      if (!held && !unsettled()) {
        snapHome();
        paint();
        updateControls();
        say("The autograph has re-formed. The garden is at rest.");
        return;
      }
      paint();
    }
    raf = requestAnimationFrame(gardenFrame);
  }

  function start() {
    updateControls();
    if (canWork() && !preferences.reducedMotion && !raf && (held || unsettled())) {
      lastFrame = performance.now();
      raf = requestAnimationFrame(gardenFrame);
    }
  }

  function nudge() {
    if (!canWork()) return;
    for (const particle of particles) {
      const push = force(particle.x, particle.y);
      particle.x = Math.max(4, Math.min(width - 4, particle.x + push.x * 24));
      particle.y = Math.max(4, Math.min(height - 4, particle.y + push.y * 24));
      particle.vx = particle.vy = 0;
    }
    paint();
  }

  function finishGesture() {
    if (!held && pointerId === null) return;
    release();
    if (preferences.reducedMotion) snapHome();
    paint();
    start();
    say(preferences.reducedMotion ? "The autograph is re-formed." : "Released. The letters are returning home.");
  }

  function aimAt(event) {
    const bounds = canvas.getBoundingClientRect();
    aim.x = Math.max(8, Math.min(width - 8, event.clientX - bounds.left));
    aim.y = Math.max(8, Math.min(height - 8, event.clientY - bounds.top));
    aim.visible = true;
  }

  const options = { signal: listeners.signal };
  modeSelect.addEventListener("change", () => {
    mode = modeSelect.value;
    say(`${modeSelect.selectedOptions[0].textContent} selected. Drag the garden, or aim with arrow keys.`);
  }, options);
  pause.addEventListener("click", () => {
    paused = !paused;
    cancelFrame();
    release();
    updateControls();
    paint();
    start();
    say(paused ? "Garden paused. Your letter positions are held." : "Garden resumed. Drag to shape the autograph.");
  }, options);
  reform.addEventListener("click", () => {
    cancelFrame();
    release();
    snapHome();
    paint();
    updateControls();
    say("The original autograph is restored.");
  }, options);
  step.addEventListener("click", () => {
    aim.visible = true;
    nudge();
    say(`One ${mode} nudge. Re-form restores the autograph.`);
  }, options);
  canvas.addEventListener("pointerdown", event => {
    if (!canWork() || (event.pointerType === "mouse" && event.button !== 0) || pointerId !== null) return;
    event.preventDefault();
    canvas.focus({ preventScroll: true });
    aimAt(event);
    pointerId = event.pointerId;
    canvas.setPointerCapture(pointerId);
    held = true;
    if (preferences.reducedMotion) nudge();
    start();
    say(`${modeSelect.selectedOptions[0].textContent} engaged. Release to re-form.`);
  }, options);
  canvas.addEventListener("pointermove", event => {
    if (!canWork() || event.pointerId !== pointerId) return;
    aimAt(event);
    if (preferences.reducedMotion) nudge();
  }, options);
  for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) {
    canvas.addEventListener(name, event => {
      if (event.pointerId === pointerId) finishGesture();
    }, options);
  }
  canvas.addEventListener("keydown", event => {
    if (!canWork()) return;
    const directions = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
    if (directions[event.key]) {
      event.preventDefault();
      const [dx, dy] = directions[event.key];
      aim.x = Math.max(8, Math.min(width - 8, aim.x + dx * 16));
      aim.y = Math.max(8, Math.min(height - 8, aim.y + dy * 16));
      aim.visible = true;
      paint();
    } else if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
      if (event.repeat) return;
      aim.visible = true;
      if (preferences.reducedMotion) {
        nudge();
        say(`One ${mode} nudge. Re-form restores the autograph.`);
      } else {
        held = keyboardHeld = true;
        start();
        say(`${modeSelect.selectedOptions[0].textContent} engaged. Release the key to re-form.`);
      }
    } else if (event.key === "Escape") {
      event.preventDefault();
      finishGesture();
    }
  }, options);
  canvas.addEventListener("keyup", event => {
    if (keyboardHeld && (event.key === " " || event.key === "Enter")) {
      event.preventDefault();
      finishGesture();
    }
  }, options);
  canvas.addEventListener("blur", () => { finishGesture(); aim.visible = false; paint(); }, options);
  canvas.addEventListener("contextlost", event => {
    event.preventDefault();
    fail(new Error("The garden canvas context was lost."));
  }, options);

  function setActive(value) {
    if (destroyed) return;
    active = Boolean(value);
    if (!active) {
      cancelFrame();
      release();
      aim.visible = false;
    }
    updateControls();
    paint();
    start();
  }

  function resize(size) {
    if (destroyed || failed) return;
    ratio = Math.min(2, Math.max(.1, size.dpr || 1));
    try { build(); start(); } catch (cause) { fail(cause); }
  }

  function setPreferences(value) {
    if (destroyed) return;
    preferences = { ...value };
    cancelFrame();
    release();
    updateControls();
    if (ready && !failed) {
      if (preferences.reducedMotion) snapHome();
      colors();
      build();
      tintMask();
      paint();
    }
    start();
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { cancelFrame(); release(); }
    else start();
  }, options);
  window.addEventListener("pagehide", () => setActive(false), options);
  updateControls();

  try {
    drawing = canvas.getContext("2d");
    mask = document.createElement("canvas");
    maskDrawing = mask.getContext("2d", { willReadFrequently: true });
    if (!drawing || !maskDrawing || !document.fonts) throw new Error("Canvas 2D and local font loading are required.");
    image = new Image();
    image.src = context.data.signature.src;
    let cancelLoading;
    const cancelled = new Promise(resolve => { cancelLoading = () => resolve(null); });
    listeners.signal.addEventListener("abort", cancelLoading, { once: true });
    let prepared;
    try {
      prepared = await Promise.race([
        Promise.all([image.decode(), document.fonts.load('400 11px "DM Mono"', GLYPHS)]),
        cancelled,
      ]);
    } finally {
      listeners.signal.removeEventListener("abort", cancelLoading);
    }
    if (destroyed || context.signal.aborted) return { setActive, resize, setPreferences, destroy };
    const [, faces] = prepared;
    if (!faces.length || faces.some(face => face.status !== "loaded")) throw new Error("The local DM Mono face did not load.");
    ready = true;
    ratio = Math.min(devicePixelRatio || 1, 2);
    colors();
    build();
    updateControls();
    say("Suff Syed's autograph, planted in letters. Drag to begin; arrows and Space work too.");
  } catch (cause) {
    if (!destroyed && !context.signal.aborted) fail(cause);
  }
  return { setActive, resize, setPreferences, destroy };
}
