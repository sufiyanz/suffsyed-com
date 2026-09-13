const signature = document.querySelector(".home-cover #cover-title > .cover-signature");
if (signature) enhanceSignature(signature);

function enhanceSignature(image) {
  const cover = image.closest(".home-cover");
  const button = cover.querySelector(".signature-motion");
  if (!button) {
    console.warn("Signature animation unavailable; using the original vector.", new Error("The pause control is missing."));
    return;
  }
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const forced = matchMedia("(forced-colors: active)");
  const print = matchMedia("print");
  const canvas = document.createElement("canvas");
  canvas.className = "signature-field";
  canvas.setAttribute("aria-hidden", "true");
  canvas.hidden = true;
  image.after(canvas);

  const glyphs = "/+ :=.#*;\\-".replaceAll(" ", "");
  const introDuration = 1350;
  const introCadence = 150;
  const settledCadence = 320;
  const maxCells = 3000;
  const maxPixels = 600000;
  const listeners = new AbortController();
  let context, mask, maskContext, observer, sizes;
  let ready = false, loading = false, failed = false, paused = false;
  let inView = false, away = false, timer = null, lastTick = 0, elapsed = 0;
  let covered = false;
  let width = 0, height = 0, ratio = 0, color, font, cells = [], mutable = [];
  let seed = 89173;

  function random() {
    seed ^= seed << 13;
    seed ^= seed >>> 17;
    seed ^= seed << 5;
    return (seed >>> 0) / 4294967296;
  }

  function stop() {
    clearTimeout(timer);
    timer = null;
  }

  function disabled() {
    return reduced.matches || forced.matches || print.matches;
  }

  function canTick() {
    return ready && !failed && !disabled() && !paused && !covered && inView && !away && !document.hidden;
  }

  function fail(error) {
    failed = true;
    stop();
    cover.removeAttribute("data-signature-active");
    cover.dataset.signatureState = "failed";
    canvas.hidden = button.hidden = true;
    observer?.disconnect();
    sizes?.disconnect();
    listeners.abort();
    console.warn("Signature animation unavailable; using the original vector.", error);
  }

  function build() {
    const bounds = image.getBoundingClientRect();
    const dpr = Math.min(devicePixelRatio || 1, 2, Math.sqrt(maxPixels / (bounds.width * bounds.height)));
    if (bounds.width === width && bounds.height === height && ratio === dpr) return;
    width = bounds.width;
    height = bounds.height;
    ratio = dpr;
    if (!width || !height) throw new Error("Signature has no drawable dimensions.");
    canvas.width = mask.width = Math.round(width * ratio);
    canvas.height = mask.height = Math.round(height * ratio);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    maskContext.drawImage(image, 0, 0, mask.width, mask.height);
    const alpha = maskContext.getImageData(0, 0, mask.width, mask.height).data;
    const fontSize = width < 340 ? 7 : 9.5;
    const stepX = fontSize * .68;
    const stepY = fontSize;
    const columns = Math.ceil(width / stepX);
    const rows = Math.ceil(height / stepY);
    if (columns * rows > maxCells) throw new Error("Signature grid exceeds its cell budget.");
    const coverage = new Uint32Array(columns * rows);
    for (let y = 0; y < mask.height; y += 1) {
      const row = Math.min(rows - 1, Math.floor(y * height / mask.height / stepY));
      for (let x = 0; x < mask.width; x += 1) {
        if (alpha[(y * mask.width + x) * 4 + 3] > 32) {
          const column = Math.min(columns - 1, Math.floor(x * width / mask.width / stepX));
          coverage[row * columns + column] += 1;
        }
      }
    }
    const previous = new Map(cells.map(cell => [cell.key, cell.glyph]));
    cells = Array.from(coverage, (ink, index) => {
      const column = index % columns, row = Math.floor(index / columns);
      const key = `${column}:${row}`;
      return {
        key, x: (column + .5) * stepX, y: (row + .5) * stepY, ink,
        glyph: previous.get(key) ?? Math.floor(random() * glyphs.length),
        delay: .65 * random() + .35 * column / columns,
        brightness: .8 + random() * .2,
      };
    });
    mutable = cells.filter(cell => cell.ink > stepX * stepY * ratio * ratio * .4);
    if (!mutable.length) throw new Error("Signature mask contains no usable ink.");
    const style = getComputedStyle(canvas);
    color = style.color;
    font = `400 ${fontSize}px ${style.fontFamily}`;
    paint();
  }

  function paint() {
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);
    context.font = font;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillStyle = color;
    const progress = Math.min(1, elapsed / introDuration);
    for (const cell of cells) {
      if (!cell.ink) continue;
      const reveal = Math.max(0, Math.min(1, (progress - cell.delay * .55) / .45));
      context.globalAlpha = (.18 + .82 * reveal * reveal * (3 - 2 * reveal)) * cell.brightness;
      context.fillText(glyphs[cell.glyph], cell.x, cell.y);
    }
    context.globalAlpha = 1;
    context.globalCompositeOperation = "destination-in";
    context.drawImage(mask, 0, 0, width, height);
    context.globalCompositeOperation = "source-over";
    if (progress < 1) {
      context.globalAlpha = .055 * (1 - progress);
      for (const cell of cells) {
        if (!cell.ink) context.fillText(glyphs[cell.glyph], cell.x, cell.y);
      }
    }
    context.globalAlpha = 1;
  }

  function tick() {
    timer = null;
    if (!canTick()) return;
    try {
      const now = performance.now();
      elapsed = Math.min(introDuration, elapsed + now - lastTick);
      lastTick = now;
      for (let index = 0; index < 2; index += 1) {
        const cell = mutable[Math.floor(random() * mutable.length)];
        cell.glyph = (cell.glyph + 1 + Math.floor(random() * (glyphs.length - 1))) % glyphs.length;
      }
      paint();
      timer = setTimeout(tick, elapsed < introDuration ? introCadence : settledCadence);
    } catch (error) {
      fail(error);
    }
  }

  async function prepare() {
    loading = true;
    cover.dataset.signatureState = "loading";
    try {
      context = canvas.getContext("2d");
      mask = document.createElement("canvas");
      maskContext = mask.getContext("2d", { willReadFrequently: true });
      if (!context || !maskContext) throw new Error("Canvas 2D is unavailable.");
      const [, faces] = await Promise.all([image.decode(), document.fonts.load('400 9.5px "DM Mono"', glyphs)]);
      if (!faces.length || faces.some(face => face.status !== "loaded")) {
        throw new Error("The local DM Mono font did not load.");
      }
      ready = true;
      sync();
    } catch (error) {
      fail(error);
    }
  }

  function sync() {
    stop();
    if (failed) return;
    button.textContent = paused ? "Resume" : "Pause";
    button.setAttribute("aria-label", `${button.textContent} signature animation`);
    button.title = button.getAttribute("aria-label");
    if (disabled()) {
      cover.removeAttribute("data-signature-active");
      cover.dataset.signatureState = "static";
      canvas.hidden = button.hidden = true;
      if (document.activeElement === button) button.blur();
      return;
    }
    if (!inView || away || covered || document.hidden) {
      cover.dataset.signatureState = paused ? "paused" : "suspended";
      return;
    }
    if (!ready) {
      if (!loading) void prepare();
      return;
    }
    try {
      build();
      canvas.hidden = button.hidden = false;
      cover.setAttribute("data-signature-active", "");
      cover.dataset.signatureState = paused ? "paused" : canTick() ? "running" : "suspended";
      if (canTick()) {
        lastTick = performance.now();
        timer = setTimeout(tick, elapsed < introDuration ? introCadence : settledCadence);
      }
    } catch (error) {
      fail(error);
    }
  }

  try {
    if (!window.IntersectionObserver || !window.ResizeObserver || !document.fonts) {
      throw new Error("Signature animation requires visibility, resize and font-loading support.");
    }
    const options = { signal: listeners.signal };
    button.addEventListener("click", () => { paused = !paused; sync(); }, options);
    cover.addEventListener("playgroundchange", event => {
      covered = event.detail.open;
      sync();
    }, options);
    for (const preference of [reduced, forced, print]) preference.addEventListener("change", sync, options);
    document.addEventListener("visibilitychange", sync, options);
    window.addEventListener("resize", sync, options);
    window.addEventListener("pagehide", () => { away = true; sync(); }, options);
    window.addEventListener("pageshow", () => { away = false; sync(); }, options);
    canvas.addEventListener("contextlost", () => fail(new Error("Signature canvas context was lost.")), options);
    sizes = new ResizeObserver(sync);
    sizes.observe(image);
    observer = new IntersectionObserver(entries => {
      inView = entries[0].isIntersecting && entries[0].intersectionRatio > 0;
      sync();
    }, { threshold: 0 });
    observer.observe(image);
    sync();
  } catch (error) {
    fail(error);
  }
}
