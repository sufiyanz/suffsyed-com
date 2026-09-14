import {element, button, choices, slider, context2d, fitSize, rgb, loadPhoto, runtime} from "./photo-tools.js";

export async function mount(root, ctx) {
  const life = runtime(root, ctx);
  const controller = {
    setActive, resize,
    setPreferences: value => life.preferences(value),
    destroy: () => life.destroy(),
  };
  if (!life.live) return controller;
  const layout = element("div", "photo-layout");
  const stage = element("figure", "pg-stage photo-preview");
  const canvas = element("canvas", "", "An editable photograph. Use the labelled controls to change the image.");
  canvas.setAttribute("role", "img");
  const caption = element("figcaption", "pg-help");
  stage.append(canvas, caption);
  const controls = element("div", "pg-controls photo-controls");
  const photoSelect = choices(controls, "Photograph", ctx.data.photos);
  const adjustments = element("fieldset", "photo-adjustments");
  adjustments.append(element("legend", "", "Light & texture"));
  const exposure = slider(adjustments, "Exposure", -2, 2, .1, 0, n => `${n > 0 ? "+" : ""}${n.toFixed(1)} EV`);
  const contrast = slider(adjustments, "Contrast", -50, 50, 1, 0, n => `${n > 0 ? "+" : ""}${n}%`);
  const grain = slider(adjustments, "Grain", 0, 50, 1, 0, n => `${n}%`);
  const duotone = slider(adjustments, "Forest duotone", 0, 100, 1, 0, n => `${n}%`);
  controls.append(adjustments);
  const actions = element("div", "photo-actions");
  const before = button("Show original");
  before.setAttribute("aria-pressed", "false");
  const reset = button("Reset to original");
  const save = button("Download PNG");
  const retry = button("Reload photograph");
  actions.append(before, reset, save, retry);
  controls.append(actions, element("p", "pg-help", "A pocket-size print, not a saved edit. Grain stays fixed; nothing leaves this browser."));
  layout.append(stage, controls);
  root.append(layout);
  let image = null;
  let imageId = null;
  let source = null;
  let showingBefore = false;
  let loading = false;
  let dirty = true;
  let size = {width: root.clientWidth || 720, height: root.clientHeight || 400, dpr: devicePixelRatio || 1};
  root.dataset.photoLayout = size.width >= 620 ? "wide" : "narrow";
  const sliders = {exposure, contrast, grain, duotone};
  const values = {exposure: 0, contrast: 0, grain: 0, duotone: 0};
  const photo = () => ctx.data.photos.find(row => row.id === photoSelect.value);
  const enabled = ready => {
    adjustments.disabled = !ready;
    before.disabled = reset.disabled = save.disabled = !ready;
  };
  enabled(false);
  life.preferences(ctx.preferences);
  life.cleanup(() => { image = source = null; canvas.width = canvas.height = 1; });

  function prepare() {
    const wide = size.width >= 620;
    const bounds = fitSize(image.naturalWidth, image.naturalHeight,
      wide ? size.width - 265 : size.width - 24, wide ? Math.max(180, size.height - 55) : 240, size.dpr);
    canvas.width = bounds.width;
    canvas.height = bounds.height;
    const context = context2d(canvas, {willReadFrequently: true});
    context.drawImage(image, 0, 0, bounds.width, bounds.height);
    source = context.getImageData(0, 0, bounds.width, bounds.height);
  }

  function render() {
    if (!life.live || !image || imageId !== photoSelect.value) return false;
    try {
      if (!source) prepare();
      const context = context2d(canvas);
      if (showingBefore) {
        context.putImageData(source, 0, 0);
      } else {
        const output = new ImageData(new Uint8ClampedArray(source.data), source.width, source.height);
        const gain = 2 ** values.exposure;
        const slope = (100 + values.contrast) / (100 - values.contrast);
        const mix = values.duotone / 100;
        const dark = rgb(ctx.palette.forest);
        const light = rgb(ctx.palette.paper);
        const pixels = output.data;
        for (let i = 0; i < pixels.length; i += 4) {
          // Coordinate hash fixes each grain sample across slider changes and idle time.
          let noise = Math.imul((i / 4) ^ ctx.seed, 0x45d9f3b);
          noise = Math.imul(noise ^ noise >>> 16, 0x45d9f3b);
          const amount = (((noise ^ noise >>> 16) >>> 0) / 4294967296 - .5) * values.grain * 1.5;
          let r = Math.min(255, Math.max(0, (pixels[i] * gain - 128) * slope + 128));
          let g = Math.min(255, Math.max(0, (pixels[i + 1] * gain - 128) * slope + 128));
          let b = Math.min(255, Math.max(0, (pixels[i + 2] * gain - 128) * slope + 128));
          const luminance = (r * .2126 + g * .7152 + b * .0722) / 255;
          r = r * (1 - mix) + (dark[0] + (light[0] - dark[0]) * luminance) * mix;
          g = g * (1 - mix) + (dark[1] + (light[1] - dark[1]) * luminance) * mix;
          b = b * (1 - mix) + (dark[2] + (light[2] - dark[2]) * luminance) * mix;
          pixels[i] = r + amount;
          pixels[i + 1] = g + amount;
          pixels[i + 2] = b + amount;
        }
        context.putImageData(output, 0, 0);
      }
      caption.textContent = `${showingBefore ? "Original" : "Your print"} / ${photo()?.title || "Photograph"} / ${canvas.width} × ${canvas.height}`;
      canvas.setAttribute("aria-label", `${showingBefore ? "Original" : "Edited preview"}: ${photo()?.alt || photo()?.title || "Photograph"}`);
      dirty = false;
      enabled(true);
      return true;
    } catch (cause) {
      enabled(false);
      life.fail("The preview could not be processed. Reload the photograph to try again.", cause);
      return false;
    }
  }

  async function selectPhoto() {
    if (!life.live) return;
    const selected = photo();
    if (!selected) {
      enabled(false);
      retry.disabled = true;
      life.fail("No photographs are available for the darkroom.");
      return;
    }
    const task = life.begin();
    loading = true;
    enabled(false);
    life.clearError();
    caption.textContent = "Preparing the photograph...";
    try {
      const loaded = await loadPhoto(selected, task.signal);
      if (!task.valid()) return;
      image = loaded;
      imageId = selected.id;
      prepare();
      if (render()) life.status("Photograph ready. Adjust the light, or compare with the original.");
    } catch (cause) {
      if (!task.valid()) return;
      image = source = null;
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
    if (loading) { loading = false; if (life.active) void selectPhoto(); return; }
    if (image) {
      source = null;
      if (life.active) life.queue(() => {
        try { prepare(); render(); }
        catch (cause) { enabled(false); life.fail("The resized preview could not be drawn. Reload to retry.", cause); }
      });
    }
  }

  life.on(photoSelect, "change", () => {
    dirty = true;
    if (life.active) void selectPhoto();
  });
  for (const [name, control] of Object.entries(sliders)) {
    life.on(control.input, "input", () => {
      values[name] = control.update();
      showingBefore = false;
      before.setAttribute("aria-pressed", "false");
      before.textContent = "Show original";
      dirty = true;
      life.queue(render);
    });
  }
  life.on(before, "click", () => {
    showingBefore = !showingBefore;
    before.setAttribute("aria-pressed", String(showingBefore));
    before.textContent = showingBefore ? "Show edited print" : "Show original";
    dirty = true;
    life.queue(render);
    life.status(showingBefore ? "Showing the untouched original." : "Showing your edited print.");
  });
  life.on(reset, "click", () => {
    for (const [name, control] of Object.entries(sliders)) {
      control.input.value = 0;
      values[name] = control.update();
    }
    showingBefore = false;
    before.setAttribute("aria-pressed", "false");
    before.textContent = "Show original";
    dirty = true;
    life.queue(render);
    life.status("All adjustments reset to the original photograph.");
  });
  life.on(retry, "click", () => { if (life.active) void selectPhoto(); });
  life.on(save, "click", () => {
    if (dirty && life.active) render();
    life.download(canvas, "pocket-darkroom.png", save);
  });
  await selectPhoto();
  if (!life.live) return controller;
  return controller;
}
