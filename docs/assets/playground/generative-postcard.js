import {element, button, choices, slider, context2d, fitSize, randomFor, localURL, loadPhoto, loadFonts, runtime} from "./photo-tools.js";

function excerpt(text) {
  if (typeof Intl.Segmenter === "function") {
    const segments = [...new Intl.Segmenter("en", {granularity: "sentence"}).segment(text)];
    const candidates = segments.filter(row => row.segment.trim().length >= 12 && row.segment.trim().length <= 320);
    const short = candidates.find(row => row.segment.trim().length <= 180) || candidates[0];
    if (short) return short.segment.trim();
  }
  // Keep an exact source substring, including case and punctuation.
  return text.trim();
}

function linesFor(context, text, width) {
  const words = text.split(/\s+/);
  const lines = [];
  let line = "";
  for (const word of words) {
    if (context.measureText(word).width > width) {
      if (line) { lines.push(line); line = ""; }
      for (const character of word) {
        if (context.measureText(line + character).width > width) { lines.push(line); line = ""; }
        line += character;
      }
    } else if (line && context.measureText(`${line} ${word}`).width > width) {
      lines.push(line);
      line = word;
    } else line += `${line ? " " : ""}${word}`;
  }
  if (line) lines.push(line);
  return lines;
}

export async function mount(root, ctx) {
  const life = runtime(root, ctx);
  const controller = {setActive, resize, setPreferences: value => life.preferences(value), destroy: () => life.destroy()};
  if (!life.live) return controller;
  const layout = element("div", "photo-layout");
  const stage = element("figure", "pg-stage photo-preview");
  const canvas = element("canvas", "", "A visitor-composed postcard combining a site photograph with an exact sentence from the journal.");
  canvas.setAttribute("role", "img");
  const caption = element("figcaption", "pg-help", "Generative composition / your arrangement, Suff Syed's photograph and words.");
  stage.append(canvas, caption);
  const controls = element("div", "pg-controls photo-controls");
  const photoSelect = choices(controls, "Photograph", ctx.data.photos);
  const quoteSelect = choices(controls, "Passage", ctx.data.passages);
  const quote = element("blockquote", "photo-quote");
  const source = element("a", "photo-source");
  controls.append(quote, source);
  const adjustments = element("fieldset", "photo-adjustments");
  adjustments.append(element("legend", "", "Compose the card"));
  const balance = slider(adjustments, "Photo balance", 32, 65, 1, 50, n => `${n}%`);
  const crop = slider(adjustments, "Crop position", 0, 100, 1, 50, n => `${n}%`);
  const accent = choices(adjustments, "Accent", [
    {id: "forest", title: "Forest"}, {id: "green", title: "Green"}, {id: "ink", title: "Ink"},
  ]);
  controls.append(adjustments);
  const actions = element("div", "photo-actions");
  const variation = button("New variation");
  const save = button("Download PNG");
  const retry = button("Reload image & fonts");
  actions.append(variation, save, retry);
  controls.append(actions, element("p", "pg-help", "A seeded editorial arrangement, not a new essay. No automatic changes; no saved state."));
  layout.append(stage, controls);
  root.append(layout);
  let image = null;
  let imageId = null;
  let loading = false;
  let dirty = true;
  let fontChecked = false;
  let fontFallback = false;
  let generation = 0;
  let seed = ctx.seed >>> 0;
  let size = {width: root.clientWidth || 720, height: root.clientHeight || 400, dpr: devicePixelRatio || 1};
  root.dataset.photoLayout = size.width >= 620 ? "wide" : "narrow";
  const photo = () => ctx.data.photos.find(row => row.id === photoSelect.value);
  const passage = () => ctx.data.passages.find(row => row.id === quoteSelect.value);
  const enabled = ready => { adjustments.disabled = !ready; variation.disabled = save.disabled = !ready; };
  enabled(false);
  life.preferences(ctx.preferences);
  life.cleanup(() => { image = null; canvas.width = canvas.height = 1; });

  function render() {
    if (!life.live || !image || imageId !== photoSelect.value || !passage()) return false;
    try {
      const selected = passage();
      const text = excerpt(selected.text);
      if (!text || text.length > 1600) throw new Error("Choose a shorter passage for a legible postcard.");
      source.href = localURL(selected.href);
      source.textContent = `Suff Syed / ${selected.title} / read source`;
      quote.textContent = text;
      const wide = size.width >= 620;
      const width = Math.max(180, Math.min(wide ? Math.max(220, size.height) : 440, wide ? size.width - 265 : size.width - 24));
      const random = randomFor(seed);
      const style = Math.floor(random() * 3);
      const margin = Math.round(width * (.055 + random() * .018));
      const photoHeight = Math.round(width * Number(balance.input.value) / 100);
      const reading = fontFallback ? "Georgia, serif" : getComputedStyle(root).getPropertyValue("--font-reading").trim() || '"Newsreader", Georgia, serif';
      const technical = fontFallback ? "monospace" : getComputedStyle(root).getPropertyValue("--font-technical").trim() || '"DM Mono", monospace';
      const fontSize = width < 340 ? 19 : 23;
      let context = context2d(canvas);
      context.font = `400 ${fontSize}px ${reading}`;
      const lines = linesFor(context, text, width - margin * 2);
      const lineHeight = fontSize * 1.22;
      const height = Math.ceil(margin * 3 + 20 + photoHeight + lines.length * lineHeight + 36);
      const bounds = fitSize(width * 2, height * 2, width, height, size.dpr);
      canvas.width = bounds.width;
      canvas.height = bounds.height;
      context = context2d(canvas);
      context.scale(bounds.width / width, bounds.height / height);
      const pigment = ctx.palette[accent.value];
      context.fillStyle = ctx.palette.paper;
      context.fillRect(0, 0, width, height);
      context.fillStyle = pigment;
      context.fillRect(style === 1 ? width - 6 : 0, 0, 6, height);
      context.font = `400 10px ${technical}`;
      context.fillText("A MOMENT / RECOMPOSED", margin, margin + 8);
      const inset = style === 2 ? margin : 0;
      const x = margin + inset;
      const y = margin + 22;
      const imageWidth = width - margin * 2 - inset;
      const scale = Math.max(imageWidth / image.naturalWidth, photoHeight / image.naturalHeight);
      const sw = imageWidth / scale;
      const sh = photoHeight / scale;
      const focal = Number(crop.input.value) / 100;
      context.drawImage(image, (image.naturalWidth - sw) * focal, (image.naturalHeight - sh) * focal,
        sw, sh, x, y, imageWidth, photoHeight);
      context.strokeStyle = pigment;
      context.lineWidth = 1;
      const ruleY = y + photoHeight + margin * .55;
      context.beginPath();
      context.moveTo(margin, ruleY);
      context.lineTo(style === 0 ? width - margin : margin + width * .28, ruleY);
      context.stroke();
      context.fillStyle = ctx.palette.ink;
      context.font = `400 ${fontSize}px ${reading}`;
      context.textBaseline = "top";
      const textY = y + photoHeight + margin;
      lines.forEach((line, index) => context.fillText(line, margin, textY + index * lineHeight));
      context.font = `400 9px ${technical}`;
      context.fillStyle = pigment;
      context.fillText("WORDS & PHOTOGRAPH / SUFF SYED", margin, height - 31);
      context.fillText(`VISITOR COMPOSITION / ${seed.toString(16).padStart(8, "0")}`, margin, height - 17);
      // Readback verifies both the image and local export are canvas-safe.
      context.getImageData(0, 0, 1, 1);
      canvas.setAttribute("aria-label", `Visitor-composed postcard. ${photo()?.alt || photo()?.title}. ${text} Words by Suff Syed, from ${selected.title}.`);
      caption.textContent = `Generative composition / your arrangement / ${canvas.width} × ${canvas.height}${fontFallback ? " / fallback typography" : ""}`;
      dirty = false;
      enabled(true);
      return true;
    } catch (cause) {
      enabled(false);
      life.fail("The postcard could not be composed. Try another passage or reload the image and fonts.", cause);
      return false;
    }
  }

  async function selectPhoto() {
    if (!life.live) return;
    const selected = photo();
    if (!selected || !passage()) {
      enabled(false);
      retry.disabled = true;
      life.fail(!selected ? "No photographs are available for postcards." : "No original passages are available for postcards.");
      return;
    }
    const task = life.begin();
    loading = true;
    enabled(false);
    life.clearError();
    caption.textContent = "Preparing photograph and local typography...";
    try {
      const loaded = await loadPhoto(selected, task.signal);
      if (!task.valid()) return;
      if (!fontChecked) {
        try {
          await loadFonts(task.signal);
          fontFallback = false;
        } catch (cause) {
          if (!task.valid()) return;
          fontFallback = true;
          life.fail("Local editorial fonts could not load. The card uses a readable fallback; Reload image & fonts retries.", cause);
        }
        if (!task.valid()) return;
        fontChecked = true;
      }
      image = loaded;
      imageId = selected.id;
      if (render()) life.status("Postcard ready. Its words link to the original essay; the arrangement is yours.");
    } catch (cause) {
      if (!task.valid()) return;
      image = null;
      imageId = null;
      canvas.width = canvas.height = 1;
      caption.textContent = "Photograph unavailable. Choose another or reload.";
      life.fail("The photograph could not be opened. Choose another photograph or reload.", cause);
    } finally {
      if (task.valid()) loading = false;
    }
  }

  function setActive(value) {
    life.setActive(value);
    if (!life.live) return;
    if (!value) { loading = false; return; }
    if (!image || imageId !== photoSelect.value) void selectPhoto();
    else if (dirty) life.queue(render);
  }

  function resize(next) {
    if (!life.live) return;
    size = {...size, ...next};
    root.dataset.photoLayout = size.width >= 620 ? "wide" : "narrow";
    life.cancel();
    dirty = true;
    if (loading) { loading = false; if (life.active) void selectPhoto(); }
    else life.queue(render);
  }

  life.on(photoSelect, "change", () => { dirty = true; if (life.active) void selectPhoto(); });
  life.on(quoteSelect, "change", () => {
    dirty = true;
    life.clearError();
    if (!image && life.active) void selectPhoto();
    else life.queue(render);
  });
  for (const control of [balance, crop]) {
    life.on(control.input, "input", () => { control.update(); dirty = true; life.queue(render); });
  }
  life.on(accent, "change", () => { dirty = true; life.queue(render); });
  life.on(variation, "click", () => {
    generation++;
    seed = (ctx.seed + Math.imul(generation, 0x9e3779b9)) >>> 0;
    dirty = true;
    life.queue(render);
    life.status(`New editorial arrangement ${generation + 1}. The photograph and original words are unchanged.`);
  });
  life.on(retry, "click", () => { fontChecked = false; if (life.active) void selectPhoto(); });
  life.on(save, "click", () => { if (dirty && life.active) render(); life.download(canvas, "generative-postcard.png", save); });
  await selectPhoto();
  if (!life.live) return controller;
  return controller;
}
