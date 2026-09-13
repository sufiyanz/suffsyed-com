/** @typedef {import("./playground-api.js").PlaygroundContext} PlaygroundContext */
/** @typedef {import("./playground-api.js").PlaygroundController} PlaygroundController */

export const experiences = Object.freeze([
  ["scratch-terminal", "Scratch terminal"], ["ink-studio", "Ink studio"],
  ["pocket-darkroom", "Pocket darkroom"], ["type-garden", "Type garden"],
  ["blackout-poetry", "Blackout poetry"], ["agent-terrarium", "Agent terrarium"],
  ["assumption-lab", "Assumption lab"], ["sound-loom", "Sound loom"],
  ["generative-postcard", "Generative postcard"], ["signal-noise", "Signal / noise"],
].map(([id, title]) => Object.freeze({ id, title })));

const cover = document.querySelector(".home-cover");
if (cover) setupPlayground(cover);

function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}

function randomFrom(seed) {
  let value = seed || 1;
  return () => {
    value ^= value << 13; value ^= value >>> 17; value ^= value << 5;
    return (value >>> 0) / 4294967296;
  };
}

function freeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}

function abortable(promise, signal) {
  return new Promise((resolve, reject) => {
    const abort = () => reject(signal.reason || new DOMException("Cancelled", "AbortError"));
    if (signal.aborted) return abort();
    signal.addEventListener("abort", abort, { once: true });
    promise.then(resolve, reject).finally(() => signal.removeEventListener("abort", abort));
  });
}

const styles = new Map();
const modules = new Map();
const importAttempts = new Map();
function loadModule(id) {
  if (modules.has(id)) return modules.get(id);
  const attempt = importAttempts.get(id) || 0;
  const suffix = attempt ? `?retry=${attempt}` : "";
  const promise = import(`/assets/playground/${id}.js${suffix}`).catch(error => {
    modules.delete(id);
    importAttempts.set(id, attempt + 1);
    throw error;
  });
  modules.set(id, promise);
  return promise;
}

function loadStyle(id, signal) {
  if (styles.has(id)) return abortable(styles.get(id), signal);
  const link = node("link");
  link.rel = "stylesheet";
  link.href = `/assets/playground/${id}.css`;
  const promise = new Promise((resolve, reject) => {
    const cancel = () => {
      link.remove();
      styles.delete(id);
      reject(signal.reason);
    };
    signal.addEventListener("abort", cancel, { once: true });
    link.onload = () => {
      signal.removeEventListener("abort", cancel);
      resolve();
    };
    link.onerror = () => {
      signal.removeEventListener("abort", cancel);
      link.remove();
      styles.delete(id);
      reject(new Error(`The ${id} stylesheet could not load.`));
    };
    document.head.append(link);
  });
  styles.set(id, promise);
  return promise;
}

async function loadData(signal) {
  const response = await fetch("/assets/playground-data.json", { signal });
  if (!response.ok) throw new Error(`Experiment material could not load (${response.status}).`);
  const data = await response.json();
  const local = value => typeof value === "string" && value.startsWith("/") && !value.startsWith("//");
  if (data.signature?.src !== "/assets/suff-syed-signature.svg"
    || JSON.stringify(data.signature.viewBox) !== "[0,0,350,148]"
    || !Array.isArray(data.photos) || !data.photos.length || !Array.isArray(data.passages) || !data.passages.length
    || data.photos.some(photo => !local(photo.src) || !photo.id || typeof photo.alt !== "string"
      || typeof photo.title !== "string" || !(photo.width > 0 && photo.height > 0))
    || data.passages.some(passage => !local(passage.href) || !passage.href.includes("#")
      || !passage.id || typeof passage.title !== "string" || typeof passage.text !== "string" || !passage.text)) {
    throw new Error("Experiment material does not match the local content contract.");
  }
  return freeze(data);
}

function setupPlayground(cover) {
  const entry = cover.querySelector(".signature-entry");
  const image = cover.querySelector(".cover-signature");
  if (!entry || !image) return;
  if (!window.ResizeObserver || !window.IntersectionObserver || !window.AbortController) {
    console.warn("Cover experiments unavailable: visibility, resize and cancellation support are required.");
    return;
  }
  const underlay = [...cover.children];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const forced = matchMedia("(forced-colors: active)");
  const printing = matchMedia("print");
  const preferences = () => ({ reducedMotion: reduced.matches, forcedColors: forced.matches });
  const shell = node("section", undefined, "pg-shell");
  shell.id = "cover-playground";
  shell.setAttribute("aria-labelledby", "pg-title");
  shell.hidden = true;
  const header = node("div", undefined, "pg-heading");
  const heading = node("h2", "A little room to play");
  heading.id = "pg-title";
  heading.tabIndex = -1;
  const close = node("button", "Close", "pg-button");
  close.type = "button";
  close.setAttribute("aria-label", "Close experiment");
  header.append(heading, close);
  const toolbar = node("div", undefined, "pg-toolbar");
  const choose = node("select");
  choose.setAttribute("aria-label", "Choose experiment");
  const choice = node("div", undefined, "pg-choice");
  const chevron = node("span", "⌄");
  chevron.setAttribute("aria-hidden", "true");
  choice.append(choose, chevron);
  for (const experience of experiences) {
    const option = node("option", experience.title);
    option.value = experience.id;
    choose.append(option);
  }
  const another = node("button", "Another experiment", "pg-button");
  another.type = "button";
  toolbar.append(choice, another);
  const viewport = node("div", undefined, "pg-viewport");
  const feedback = node("div", undefined, "pg-feedback");
  const feedbackText = node("p");
  const retry = node("button", "Retry", "pg-button");
  retry.type = "button";
  feedback.append(feedbackText, retry);
  viewport.append(feedback);
  const footer = node("div", undefined, "pg-footer");
  const status = node("p", "", "pg-status");
  status.setAttribute("role", "status");
  const ephemeral = node("p", "Not saved. Close or switch to start fresh.", "pg-ephemeral");
  footer.append(status, ephemeral);
  shell.append(header, toolbar, viewport, footer);
  cover.append(shell);
  let selected = experiences[0].id, bag = [], current = null, open = false, away = false;
  let inView = cover.getBoundingClientRect().bottom > 0;
  let dimensions = { width: 0, height: 0, dpr: 1 };
  const shuffle = randomFrom(crypto.getRandomValues(new Uint32Array(1))[0]);
  const palette = freeze(Object.fromEntries(["forest", "green", "stone", "paper", "white", "ink"]
    .map(name => [name, getComputedStyle(cover).getPropertyValue(`--${name}`).trim()])));

  function stillCurrent(record) {
    return open && current === record && !record.abort.signal.aborted;
  }

  function cleanupError(error) {
    console.warn("Cover experiment cleanup failed.", error);
    const message = "Closed, but cleanup reported a problem. Reload before continuing.";
    status.textContent = message;
    entry.querySelector("span").textContent = message;
  }

  function disposeController(controller) {
    try { controller.setActive?.(false); } catch (error) { cleanupError(error); }
    try { Promise.resolve(controller.destroy?.()).catch(cleanupError); } catch (error) { cleanupError(error); }
  }

  function teardown() {
    const record = current;
    current = null;
    if (!record) return;
    clearTimeout(record.deadline);
    if (record.controller) disposeController(record.controller);
    record.abort.abort();
    record.root.remove();
  }

  function fail(record, message, error) {
    if (!stillCurrent(record)) return;
    console.warn("Cover experiment unavailable.", message, error);
    const hadFocus = record.root.contains(document.activeElement);
    teardown();
    shell.dataset.state = "error";
    viewport.setAttribute("aria-busy", "false");
    feedback.hidden = false;
    feedbackText.textContent = message;
    retry.hidden = false;
    status.textContent = "Your experiment could not continue. Retry or close.";
    if (hadFocus) retry.focus({ preventScroll: true });
  }

  function updateActive() {
    const record = current;
    if (!record?.controller) return;
    const active = open && inView && !away && !document.hidden && !printing.matches;
    if (record.active === active) return;
    record.active = active;
    try { record.controller.setActive(active); } catch (error) { fail(record, "The experiment could not change its activity state.", error); }
  }

  async function select(id) {
    const experience = experiences.find(item => item.id === id);
    if (!experience || !open) return;
    const focusWasInside = current?.root.contains(document.activeElement) || document.activeElement === retry;
    teardown();
    selected = id;
    bag = bag.filter(item => item !== id);
    choose.value = id;
    heading.textContent = experience.title;
    if (focusWasInside) heading.focus({ preventScroll: true });
    shell.dataset.state = "loading";
    viewport.setAttribute("aria-busy", "true");
    status.textContent = `Opening ${experience.title.toLowerCase()}.`;
    feedback.hidden = false;
    feedbackText.textContent = `Opening ${experience.title.toLowerCase()}…`;
    retry.hidden = true;
    const root = node("div", undefined, "pg-instance");
    root.dataset.experience = id;
    root.hidden = true;
    viewport.prepend(root);
    const record = { root, abort: new AbortController(), controller: null, active: false, deadline: null };
    current = record;
    record.deadline = setTimeout(() => fail(record, "This experiment is taking too long to open. Try again.", new Error("Mount timeout")), 15000);
    try {
      const signal = record.abort.signal;
      const [module, , data] = await abortable(Promise.all([
        loadModule(id), loadStyle(id, signal), loadData(signal),
      ]), signal);
      if (!stillCurrent(record)) return;
      if (typeof module.mount !== "function") throw new Error("Experiment has no mount function.");
      root.hidden = false;
      root.inert = true;
      const seed = crypto.getRandomValues(new Uint32Array(1))[0];
      /** @type {PlaygroundContext} */
      const context = {
        signal, seed, random: randomFrom(seed), preferences: preferences(), palette, data,
        setStatus(message) { if (stillCurrent(record)) status.textContent = String(message); },
        reportError(message, error) { fail(record, String(message), error); },
      };
      const mounting = Promise.resolve(module.mount(root, context)).then(controller => {
        if (!stillCurrent(record)) {
          if (controller) disposeController(controller);
          return null;
        }
        return controller;
      });
      const controller = await abortable(mounting, signal);
      if (!stillCurrent(record)) return;
      if (!controller || ["setActive", "resize", "setPreferences", "destroy"].some(method => typeof controller[method] !== "function")) {
        if (controller?.destroy) disposeController(controller);
        throw new Error("Experiment controller does not match contract v1.");
      }
      record.controller = controller;
      controller.setActive(false);
      if (!stillCurrent(record)) return;
      controller.setPreferences(preferences());
      if (!stillCurrent(record)) return;
      controller.resize(dimensions);
      if (!stillCurrent(record)) return;
      clearTimeout(record.deadline);
      root.inert = false;
      feedback.hidden = true;
      shell.dataset.state = "ready";
      viewport.setAttribute("aria-busy", "false");
      if (status.textContent === `Opening ${experience.title.toLowerCase()}.`) {
        status.textContent = `${experience.title} is ready.`;
      }
      updateActive();
    } catch (error) {
      if (stillCurrent(record)) fail(record, `Could not open ${experience.title.toLowerCase()}. Retry or choose another experiment.`, error);
    }
  }

  function enter() {
    if (open) return;
    open = true;
    underlay.forEach(el => { el.inert = true; });
    cover.setAttribute("data-playground-open", "");
    cover.dispatchEvent(new CustomEvent("playgroundchange", { detail: { open: true } }));
    shell.hidden = false;
    entry.setAttribute("aria-expanded", "true");
    measure();
    heading.focus({ preventScroll: true });
    void select(selected);
  }

  function exit() {
    if (!open) return;
    teardown();
    open = false;
    shell.hidden = true;
    status.textContent = "";
    cover.removeAttribute("data-playground-open");
    underlay.forEach(el => { el.inert = false; });
    entry.setAttribute("aria-expanded", "false");
    cover.dispatchEvent(new CustomEvent("playgroundchange", { detail: { open: false } }));
    entry.focus({ preventScroll: true });
  }

  function measure() {
    const bounds = image.getBoundingClientRect();
    entry.style.width = `${bounds.width}px`;
    entry.style.height = `${bounds.height}px`;
    if (!open) return;
    const box = viewport.getBoundingClientRect();
    dimensions = { width: box.width, height: box.height, dpr: Math.min(devicePixelRatio || 1, 2) };
    const record = current;
    if (record?.controller) {
      try { record.controller.resize(dimensions); } catch (error) { fail(record, "The experiment could not resize.", error); }
    }
  }

  entry.addEventListener("click", enter);
  close.addEventListener("click", exit);
  retry.addEventListener("click", () => void select(selected));
  choose.addEventListener("change", () => void select(choose.value));
  another.addEventListener("click", () => {
    if (!bag.length) {
      bag = experiences.map(item => item.id).filter(id => id !== selected);
      for (let i = bag.length - 1; i > 0; i -= 1) {
        const j = Math.floor(shuffle() * (i + 1));
        [bag[i], bag[j]] = [bag[j], bag[i]];
      }
    }
    void select(bag[bag.length - 1]);
  });
  shell.addEventListener("keydown", event => {
    if (event.key === "Escape" && !event.isComposing && event.keyCode !== 229) {
      event.preventDefault();
      exit();
    }
  });
  for (const preference of [reduced, forced]) preference.addEventListener("change", () => {
    const record = current;
    if (!record?.controller) return;
    try { record.controller.setPreferences(preferences()); } catch (error) { fail(record, "The experiment could not apply your preferences.", error); }
  });
  printing.addEventListener("change", updateActive);
  document.addEventListener("visibilitychange", updateActive);
  window.addEventListener("pagehide", () => { away = true; updateActive(); });
  window.addEventListener("pageshow", () => { away = false; updateActive(); measure(); });
  window.addEventListener("resize", measure);
  const sizes = new ResizeObserver(measure);
  sizes.observe(image);
  sizes.observe(viewport);
  new IntersectionObserver(entries => {
    inView = entries[0].isIntersecting && entries[0].intersectionRatio > 0;
    updateActive();
  }, { threshold: 0 }).observe(cover);
  measure();
  entry.hidden = false;
}
