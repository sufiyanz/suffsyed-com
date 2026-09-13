const MAX_CHARACTERS = 60000;
const MAX_WORDS = 2500;

function node(tag, className, text) {
  const element = document.createElement(tag);
  element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

export async function mount(root, context) {
  const listeners = new AbortController();
  let destroyed = false, active = false, captured = null, lastPosition = null;
  let tokens = [], words = [], kept = [], current = null, index = 0, focused = 0;
  let reading, passage, brush, reset, clear, next, copy;
  const on = (target, event, handler) => target.addEventListener(event, handler, { signal: listeners.signal });
  const controller = { setActive, resize, setPreferences, destroy };
  context.signal.addEventListener("abort", destroy, { once: true });
  if (context.signal.aborted) {
    destroy();
    return controller;
  }
  root.inert = true;
  for (const [name, color] of Object.entries(context.palette)) root.style.setProperty(`--poetry-${name}`, color);
  const intro = node("p", "poetry-invitation", "A poem between the lines.");
  const controls = node("div", "pg-controls poetry-controls");
  const label = node("label", "pg-field poetry-field");
  label.append(node("span", "", "Brush"));
  brush = node("select", "");
  brush.setAttribute("aria-label", "Poetry brush");
  for (const [value, text] of [["tap", "Tap / scroll"], ["remove", "Black out"], ["restore", "Restore"]]) {
    const option = node("option", "", text);
    option.value = value;
    brush.append(option);
  }
  label.append(brush);
  controls.append(label);
  function button(text, handler) {
    const input = node("button", "pg-button", text);
    input.type = "button";
    on(input, "click", () => { if (active && !destroyed) handler(); });
    controls.append(input);
    return input;
  }
  reset = button("Reset", () => selectAll(true, "All source words restored."));
  clear = button("Clear", () => selectAll(false, "All words blacked out. Choose words to keep."));
  next = button("New passage", () => {
    stopBrush();
    index = (index + 1) % passages.length;
    showPassage();
    context.setStatus("New source paragraph. All words restored.");
  });
  copy = button("Copy poem", copyPoem);
  const help = node("p", "pg-help poetry-help", "Tap words, or use arrows + Space.");
  help.append(node("span", "poetry-hidden",
    " Arrows move between words; Space or Enter toggles them. Choose a brush to paint; Tap / scroll enables touch scrolling. Closing discards the remix."));
  help.id = `poetry-help-${context.seed}`;
  reading = node("div", "pg-stage poetry-reading");
  reading.setAttribute("role", "region");
  reading.setAttribute("aria-label", "Source paragraph and your remix");
  reading.tabIndex = 0;
  const source = node("details", "poetry-source");
  const attribution = node("summary", "poetry-attribution", "Source paragraph by Suff Syed");
  const sourceLink = node("a", "poetry-source-link");
  sourceLink.target = "_blank";
  sourceLink.rel = "noopener noreferrer";
  source.append(attribution, sourceLink);
  passage = node("div", "poetry-passage");
  passage.setAttribute("role", "group");
  passage.setAttribute("aria-label", "Choose words to keep in your poem");
  passage.setAttribute("aria-describedby", help.id);
  const remix = node("section", "poetry-remix");
  remix.setAttribute("aria-label", "Your visitor remix");
  const heading = node("h3", "", "Your visitor remix");
  const disclaimer = node("p", "poetry-disclaimer", "A selection by you, not an original quotation. Words stay in source order.");
  const poem = node("p", "poetry-poem");
  const empty = node("p", "poetry-empty", "No words kept yet. Restore a few and see what remains.");
  empty.hidden = true;
  remix.append(heading, disclaimer, poem, empty);
  reading.append(passage, source, remix);
  const footer = node("p", "poetry-count");
  const errorBox = node("p", "poetry-error");
  errorBox.hidden = true;
  root.append(intro, controls, help, reading, footer, errorBox);
  const passages = Array.isArray(context.data.passages) ? context.data.passages : [];
  index = passages.length ? Math.floor(context.random() * passages.length) % passages.length : 0;

  function fail(message, error) {
    errorBox.textContent = message;
    errorBox.hidden = false;
    context.reportError(message, error);
  }

  function showPassage() {
    stopBrush();
    current = null;
    tokens = [];
    words = [];
    kept = [];
    focused = 0;
    passage.replaceChildren();
    poem.textContent = "";
    sourceLink.textContent = "";
    sourceLink.removeAttribute("href");
    errorBox.hidden = true;
    source.open = false;
    next.disabled = passages.length <= 1;
    reset.disabled = clear.disabled = copy.disabled = brush.disabled = true;
    if (!passages.length) {
      fail("No source paragraphs are available. You can close this experiment and choose another.", new Error("Empty passages array."));
      footer.textContent = "No paragraph loaded.";
      return;
    }
    try {
      const candidate = passages[index];
      if (!candidate || typeof candidate.text !== "string" || !candidate.text.trim()
        || typeof candidate.title !== "string" || !candidate.title.trim()
        || typeof candidate.href !== "string" || !candidate.href.trim()) {
        throw new Error("A complete text, title and source link are required.");
      }
      const url = new URL(candidate.href, document.baseURI);
      if (!["https:", "http:"].includes(url.protocol)) throw new Error("The source URL is not an HTTP(S) link.");
      if (candidate.text.length > MAX_CHARACTERS) throw new Error("This paragraph exceeds the 60,000-character reading budget.");
      const split = candidate.text.match(/\s+|\S+/gu) || [];
      if (split.filter(text => !/^\s+$/u.test(text)).length > MAX_WORDS) {
        throw new Error("This paragraph exceeds the 2,500-word reading budget.");
      }
      current = candidate;
      sourceLink.textContent = candidate.title;
      sourceLink.href = url.href;
      const fragment = document.createDocumentFragment();
      tokens = split.map(text => {
        if (/^\s+$/u.test(text)) {
          fragment.append(document.createTextNode(text));
          return { text, word: null };
        }
        const word = words.length;
        const input = node("button", "poetry-word", text);
        input.type = "button";
        input.dataset.word = String(word);
        input.setAttribute("aria-pressed", "true");
        input.setAttribute("aria-label", `Word ${word + 1}: ${text}`);
        input.tabIndex = word === 0 ? 0 : -1;
        words.push(input);
        kept.push(true);
        fragment.append(input);
        return { text, word };
      });
      passage.append(fragment);
      reset.disabled = clear.disabled = brush.disabled = false;
      reading.scrollTop = 0;
      update();
    } catch (error) {
      current = null;
      fail(`This source paragraph cannot be opened. ${error.message} Try New passage or Close.`, error);
      footer.textContent = "Source unavailable; no text was shortened or replaced.";
    }
  }

  function output() {
    // Keep the exact separator preceding each retained word, including tabs/newlines.
    // With every word selected this reconstructs the entire source byte-for-byte.
    let result = "", separator = "";
    for (const token of tokens) {
      if (token.word === null) {
        separator = token.text;
      } else {
        if (kept[token.word]) result += separator + token.text;
        separator = "";
      }
    }
    if (kept.at(-1)) result += separator;
    return result;
  }

  function update() {
    if (!current) return;
    const count = kept.filter(Boolean).length;
    poem.textContent = output();
    poem.hidden = count === 0;
    empty.hidden = count !== 0;
    copy.disabled = count === 0;
    footer.textContent = `${count}/${words.length} kept · Underlines stay; bars hide.`;
  }

  function selectWord(word, value) {
    if (kept[word] === value) return;
    kept[word] = value;
    words[word].setAttribute("aria-pressed", String(value));
  }

  function selectAll(value, message) {
    stopBrush();
    kept.forEach((_, word) => selectWord(word, value));
    update();
    context.setStatus(message);
  }

  function wordAt(target) {
    const input = target instanceof Element ? target.closest(".poetry-word") : null;
    return input && passage.contains(input) ? Number(input.dataset.word) : null;
  }

  function focusWord(word) {
    words[focused].tabIndex = -1;
    focused = word;
    words[focused].tabIndex = 0;
    words[focused].focus({ preventScroll: true });
    const rect = words[focused].getBoundingClientRect(), box = reading.getBoundingClientRect();
    if (rect.top < box.top + 6) reading.scrollTop -= box.top + 6 - rect.top;
    else if (rect.bottom > box.bottom - 6) reading.scrollTop += rect.bottom - box.bottom + 6;
  }

  on(passage, "click", event => {
    if (!active || (brush.value !== "tap" && event.detail > 0)) return;
    const word = wordAt(event.target);
    if (word === null) return;
    selectWord(word, !kept[word]);
    update();
    context.setStatus(`${kept.filter(Boolean).length} of ${words.length} words kept.`);
  });
  on(passage, "focusin", event => {
    const word = wordAt(event.target);
    if (word === null) return;
    words[focused].tabIndex = -1;
    focused = word;
    words[word].tabIndex = 0;
  });
  on(passage, "keydown", event => {
    if (!active || event.altKey || event.ctrlKey || event.metaKey) return;
    const word = wordAt(event.target);
    if (word === null) return;
    let destination = word;
    if (event.key === "ArrowRight") destination = Math.min(words.length - 1, word + 1);
    else if (event.key === "ArrowLeft") destination = Math.max(0, word - 1);
    else if (event.key === "Home") destination = 0;
    else if (event.key === "End") destination = words.length - 1;
    else if (event.key === "ArrowUp" || event.key === "ArrowDown") {
      const origin = words[word].getBoundingClientRect();
      const down = event.key === "ArrowDown";
      let best = Infinity;
      words.forEach((input, candidate) => {
        const box = input.getBoundingClientRect();
        const dy = box.top - origin.top;
        if (down ? dy <= 2 : dy >= -2) return;
        const score = Math.abs(dy) * 10 + Math.abs(box.left + box.width / 2 - origin.left - origin.width / 2);
        if (score < best) { best = score; destination = candidate; }
      });
    } else return;
    event.preventDefault();
    focusWord(destination);
  });
  on(brush, "change", () => {
    stopBrush();
    passage.dataset.brushing = String(brush.value !== "tap");
    context.setStatus(brush.value === "tap" ? "Tap words to toggle. Touch scrolling is enabled."
      : `${brush.selectedOptions[0].textContent} brush ready. Drag across words; scroll in the reading margins.`);
  });
  on(passage, "pointerdown", event => {
    if (!active || brush.value === "tap" || !event.isPrimary || event.button !== 0 || captured !== null) return;
    const word = wordAt(event.target);
    if (word === null) return;
    event.preventDefault();
    selectWord(word, brush.value === "restore");
    update();
    try {
      passage.setPointerCapture(event.pointerId);
      captured = event.pointerId;
      lastPosition = { x: event.clientX, y: event.clientY };
    } catch (error) {
      stopBrush();
      fail("The brush could not capture the pointer. Use Tap / scroll or the keyboard.", error);
    }
  });
  on(passage, "pointermove", event => {
    if (!active || event.pointerId !== captured || !lastPosition) return;
    const steps = Math.min(128, Math.max(1, Math.ceil(Math.hypot(event.clientX - lastPosition.x, event.clientY - lastPosition.y) / 4)));
    for (let step = 1; step <= steps; step += 1) {
      const x = lastPosition.x + (event.clientX - lastPosition.x) * step / steps;
      const y = lastPosition.y + (event.clientY - lastPosition.y) * step / steps;
      const word = wordAt(document.elementFromPoint(x, y));
      if (word !== null) selectWord(word, brush.value === "restore");
    }
    lastPosition = { x: event.clientX, y: event.clientY };
    update();
  });
  on(passage, "pointerup", event => {
    if (event.pointerId !== captured) return;
    stopBrush();
    context.setStatus(`${kept.filter(Boolean).length} of ${words.length} words kept.`);
  });
  on(passage, "pointercancel", event => { if (event.pointerId === captured) stopBrush(); });
  on(passage, "lostpointercapture", event => { if (event.pointerId === captured) stopBrush(); });

  function stopBrush() {
    const pointer = captured;
    captured = lastPosition = null;
    if (pointer !== null && passage?.hasPointerCapture(pointer)) passage.releasePointerCapture(pointer);
  }

  async function copyPoem() {
    if (!current) return;
    const text = `Visitor remix (not an original quotation)\n\n${output()}\n\nSource: ${current.title} by Suff Syed\n${sourceLink.href}`;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard access is unavailable in this browser.");
      await navigator.clipboard.writeText(text);
      if (!destroyed && active && !context.signal.aborted) context.setStatus("Visitor remix and source attribution copied.");
    } catch (error) {
      if (!destroyed) fail("Copy was not permitted. You can select the remix text and copy it manually.", error);
    }
  }

  function setActive(value) {
    if (destroyed) return;
    active = Boolean(value);
    root.inert = !active;
    if (!active) stopBrush();
  }

  function resize() {
    if (!destroyed) stopBrush();
  }

  function setPreferences(value) {
    if (!destroyed) root.dataset.poetryForced = String(value.forcedColors);
  }

  function destroy() {
    if (destroyed) return;
    destroyed = true;
    active = false;
    stopBrush();
    listeners.abort();
    context.signal.removeEventListener("abort", destroy);
    current = null;
    tokens = [];
    words = [];
    kept = [];
    if (passage) {
      passage.replaceChildren();
      poem.textContent = "";
    }
    root.replaceChildren();
    root.inert = false;
    delete root.dataset.poetryForced;
    for (const name of Object.keys(context.palette)) root.style.removeProperty(`--poetry-${name}`);
  }

  setPreferences(context.preferences);
  showPassage();
  return controller;
}
