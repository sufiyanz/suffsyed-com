const MAX_POINTS = 12000;
const MAX_STROKE_POINTS = 900;
const MAX_STROKES = 96;
const MAX_PIXELS = 1000000;

function node(tag, className, text) {
  const element = document.createElement(tag);
  element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

export async function mount(root, context) {
  const listeners = new AbortController();
  let destroyed = false, active = false;
  let strokes = [], current = null, pointCount = 0, captured = null;
  let width = 0, height = 0, requestedDpr = 1, keyboardDown = false;
  let keyboard = { x: .5, y: .5 }, previousInput = null;
  let preferences = context.preferences;
  let exporting = false;
  let observer = null;
  const urls = new Set();
  const on = (target, event, handler) => target.addEventListener(event, handler, { signal: listeners.signal });
  const controller = { setActive, resize, setPreferences, destroy };
  context.signal.addEventListener("abort", destroy, { once: true });
  if (context.signal.aborted) {
    destroy();
    return controller;
  }

  root.inert = true;
  for (const [name, color] of Object.entries(context.palette)) root.style.setProperty(`--ink-${name}`, color);
  const intro = node("div", "ink-inscription");
  intro.append(node("span", "ink-folio", "01 / FIELD NOTES"), node("p", "ink-invitation", "Take your time."));
  const controls = node("div", "pg-controls ink-controls");
  const toolbox = node("section", "ink-toolbox");
  toolbox.id = `ink-tools-${context.seed}`;
  toolbox.setAttribute("aria-label", "Drawing tools");
  toolbox.hidden = true;
  const toolHeading = node("div", "ink-tool-heading");
  toolHeading.append(node("h3", "", "Choose your materials"));
  const fields = node("div", "ink-fields");
  const actions = node("div", "ink-actions");
  const toolActions = node("div", "ink-tool-actions");
  const stage = node("div", "pg-stage ink-stage");
  const canvas = node("canvas", "ink-paper");
  const invitation = node("span", "ink-paper-invitation", "Start anywhere.");
  invitation.setAttribute("aria-hidden", "true");
  const cursor = node("span", "ink-cursor");
  cursor.setAttribute("aria-hidden", "true");
  canvas.tabIndex = 0;
  canvas.setAttribute("role", "application");
  canvas.setAttribute("aria-label", "Fountain pen drawing surface");
  const help = node("p", "pg-help ink-help", "Draw · arrows + Space");
  help.append(node("span", "ink-hidden",
    " Pen, mouse and touch are supported. Arrows move the nib; Enter or Space lifts/lowers it. Shift + arrows takes a larger step. Closing discards the sheet."));
  help.id = `ink-help-${context.seed}`;
  canvas.setAttribute("aria-describedby", help.id);
  const budget = node("p", "ink-budget");
  const footer = node("div", "ink-footer");
  const sheetCount = node("span", "ink-sheet-count", "BLANK SHEET");
  footer.append(help, sheetCount);
  const notice = node("p", "ink-notice");
  notice.hidden = true;
  toolbox.append(toolHeading, fields, toolActions, budget,
    node("p", "ink-tool-note", "Pen pressure shapes the line. Mouse and touch respond to speed. Nothing is saved unless you choose Save PNG."));
  controls.append(actions);
  stage.append(canvas, invitation, cursor);
  root.append(intro, stage, controls, footer, toolbox, notice);

  function select(labelText, options) {
    const label = node("label", "pg-field ink-field");
    const title = node("span", "", labelText);
    const input = node("select", "");
    input.setAttribute("aria-label", labelText);
    for (const [value, text] of options) {
      const option = node("option", "", text);
      option.value = value;
      input.append(option);
    }
    label.append(title, input);
    fields.append(label);
    on(input, "change", () => {
      finish();
      updateMaterial();
      context.setStatus(`${labelText}: ${input.selectedOptions[0].textContent}.`);
    });
    return input;
  }

  function button(text, handler, parent = actions) {
    const input = node("button", "pg-button", text);
    input.type = "button";
    on(input, "click", () => { if (active && !destroyed) handler(); });
    parent.append(input);
    return input;
  }

  const tools = button("Tools", () => showTools(toolbox.hidden));
  tools.classList.add("ink-nib-button");
  tools.setAttribute("aria-controls", toolbox.id);
  tools.setAttribute("aria-expanded", "false");
  const nibMark = node("span", "ink-nib-mark");
  nibMark.setAttribute("aria-hidden", "true");
  tools.prepend(nibMark);
  button("Done", () => showTools(false), toolHeading);
  const nib = select("Nib", [["fountain", "Fountain"], ["round", "Round"]]);
  const size = select("Size", [["5", "Medium"], ["2", "Fine"], ["10", "Broad"]]);
  const color = select("Ink", [
    ["forest", "Forest"], ["green", "Green"], ["ink", "Ink"],
    ["stone", "Stone"], ["paper", "Paper"], ["white", "White"],
  ]);
  let erasing = false;
  const eraser = button("Eraser", () => {
    finish();
    erasing = !erasing;
    eraser.setAttribute("aria-pressed", String(erasing));
    context.setStatus(erasing ? "Eraser selected. Draw over ink to remove it." : "Pen selected.");
  });
  eraser.setAttribute("aria-pressed", "false");
  const undo = button("Undo", () => {
    finish();
    const stroke = strokes.pop();
    if (!stroke) return;
    pointCount -= stroke.points.length;
    notice.hidden = true;
    render();
    updateTools();
    context.setStatus("Last stroke undone.");
  });
  const clear = button("Clear", () => {
    finish();
    strokes = [];
    pointCount = 0;
    notice.hidden = true;
    render();
    updateTools();
    context.setStatus("A fresh sheet. All strokes cleared.");
  }, toolActions);
  const download = button("Save PNG", save);
  download.classList.add("ink-save");
  const drawing = canvas.getContext("2d");
  if (!drawing) {
    context.reportError("This browser cannot open the drawing surface.", new Error("Canvas 2D is unavailable."));
    destroy();
    return controller;
  }

  function updateTools() {
    undo.disabled = clear.disabled = strokes.length === 0;
    download.disabled = exporting || strokes.length === 0;
    budget.textContent = `${strokes.length}/96 strokes · ${pointCount.toLocaleString("en-US")}/12,000 points`;
    sheetCount.textContent = strokes.length ? `${strokes.length} MARK${strokes.length === 1 ? "" : "S"}` : "BLANK SHEET";
    invitation.hidden = strokes.length > 0;
  }

  function updateMaterial() {
    nibMark.style.setProperty("--ink-selected", context.palette[color.value]);
    nibMark.dataset.nib = nib.value;
    tools.title = `Tools: ${nib.selectedOptions[0].textContent}, ${size.selectedOptions[0].textContent}, ${color.selectedOptions[0].textContent}`;
  }

  function showTools(visible, returnFocus = true) {
    finish();
    toolbox.hidden = !visible;
    tools.setAttribute("aria-expanded", String(visible));
    if (visible) nib.focus();
    else if (returnFocus) tools.focus({ preventScroll: true });
  }

  on(root, "keydown", event => {
    if (event.key === "Escape" && !toolbox.hidden) {
      event.preventDefault();
      showTools(false);
    }
  });

  function showLimit(message) {
    notice.textContent = message;
    notice.hidden = false;
    context.setStatus(message);
    finish();
  }

  function start(point, pressure, time, type) {
    if (!active || destroyed || !width || !height) return false;
    if (strokes.length >= MAX_STROKES || pointCount >= MAX_POINTS) {
      showLimit("This sheet is full. Save PNG, Undo or Clear to make room.");
      return false;
    }
    const base = Math.min(width, height);
    current = {
      points: [], color: color.value, nib: nib.value, erase: erasing,
      size: (erasing ? 26 : Number(size.value)) / base,
    };
    strokes.push(current);
    previousInput = { ...point, time, pressure: .5 };
    addPoint(point, pressure, time, type, true);
    return true;
  }

  function addPoint(point, pressure, time, type, first = false) {
    if (!current) return;
    const points = current.points;
    const previous = points.at(-1);
    const dx = (point.x - previousInput.x) * width;
    const dy = (point.y - previousInput.y) * height;
    const distance = Math.hypot(dx, dy);
    if (!first && distance < .7) return;
    if (points.length >= MAX_STROKE_POINTS || pointCount >= MAX_POINTS) {
      showLimit(points.length >= MAX_STROKE_POINTS
        ? "This stroke reached 900 points. Lift and draw another, or Save PNG."
        : "This sheet reached 12,000 points. Save PNG, Undo or Clear to make room.");
      return;
    }
    const velocity = distance / Math.max(8, time - previousInput.time);
    const measured = type === "pen" && pressure > 0
      ? Math.max(.05, Math.min(1, pressure))
      : .22 + .7 / (1 + velocity * 1.8);
    const force = first ? measured : previousInput.pressure * .35 + measured * .65;
    const filtered = previous && !current.erase
      ? { x: previous.x * .25 + point.x * .75, y: previous.y * .25 + point.y * .75 }
      : point;
    points.push({ ...filtered, pressure: force });
    pointCount += 1;
    previousInput = { ...point, time, pressure: force };
    render();
    updateTools();
  }

  function releaseCapture() {
    const pointer = captured;
    captured = null;
    if (pointer !== null && canvas.hasPointerCapture(pointer)) canvas.releasePointerCapture(pointer);
  }

  function finish() {
    const wasDrawing = Boolean(current);
    current = null;
    previousInput = null;
    keyboardDown = false;
    cursor.dataset.down = "false";
    releaseCapture();
    if (wasDrawing && !destroyed) {
      render();
      canvas.setAttribute("aria-label", `Fountain pen drawing surface, ${strokes.length} strokes. Pen lifted.`);
    }
  }

  function eventPoint(event) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
    };
  }

  on(canvas, "pointerdown", event => {
    if (!active || current || !event.isPrimary || event.button !== 0) return;
    event.preventDefault();
    if (!toolbox.hidden) showTools(false, false);
    canvas.focus({ preventScroll: true });
    cursor.hidden = true;
    if (start(eventPoint(event), event.pressure, event.timeStamp, event.pointerType)) {
      try {
        canvas.setPointerCapture(event.pointerId);
        captured = event.pointerId;
      } catch (error) {
        finish();
        context.reportError("Pointer capture failed; use keyboard drawing or start a new stroke.", error);
      }
    }
  });
  on(canvas, "pointermove", event => {
    if (!active || event.pointerId !== captured || !current) return;
    const events = event.getCoalescedEvents?.() || [];
    for (const sample of events.length ? events : [event]) {
      if (!current) break;
      addPoint(eventPoint(sample), sample.pressure, sample.timeStamp, sample.pointerType);
    }
  });
  on(canvas, "pointerup", event => {
    if (event.pointerId !== captured) return;
    addPoint(eventPoint(event), event.pressure, event.timeStamp, event.pointerType);
    finish();
    context.setStatus(`${strokes.length} strokes on this sheet.`);
  });
  on(canvas, "pointercancel", event => { if (event.pointerId === captured) finish(); });
  on(canvas, "lostpointercapture", event => { if (event.pointerId === captured) finish(); });
  on(canvas, "blur", finish);
  on(canvas, "focus", () => {
    cursor.hidden = false;
    positionCursor();
  });
  on(canvas, "keydown", event => {
    if (!active || event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (event.repeat || captured !== null) return;
      if (keyboardDown) {
        finish();
        context.setStatus("Pen lifted.");
      } else {
        keyboardDown = start(keyboard, .5, event.timeStamp, "keyboard");
        cursor.dataset.down = String(keyboardDown);
        if (keyboardDown) context.setStatus("Pen down. Arrow keys draw; Enter or Space lifts.");
      }
    } else if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
      event.preventDefault();
      if (captured !== null) return;
      const step = event.shiftKey ? 20 : 5;
      keyboard = {
        x: Math.max(0, Math.min(1, keyboard.x + (event.key === "ArrowRight" ? step / width : event.key === "ArrowLeft" ? -step / width : 0))),
        y: Math.max(0, Math.min(1, keyboard.y + (event.key === "ArrowDown" ? step / height : event.key === "ArrowUp" ? -step / height : 0))),
      };
      if (keyboardDown) addPoint(keyboard, .5, event.timeStamp, "keyboard");
    } else if (event.key === "Escape") {
      finish();
    } else return;
    cursor.hidden = false;
    positionCursor();
  });

  function positionCursor() {
    cursor.style.left = `${keyboard.x * 100}%`;
    cursor.style.top = `${keyboard.y * 100}%`;
  }

  function paintStroke(stroke) {
    const points = stroke.points;
    if (!points.length) return;
    drawing.globalCompositeOperation = stroke.erase ? "destination-out" : "source-over";
    drawing.fillStyle = preferences.forcedColors ? getComputedStyle(canvas).color : context.palette[stroke.color];
    const scale = Math.min(width, height) * stroke.size;
    const sides = [[], []];
    for (let index = 0; index < points.length; index += 1) {
      const p = points[index], before = points[Math.max(0, index - 1)], after = points[Math.min(points.length - 1, index + 1)];
      const angle = Math.atan2((after.y - before.y) * height, (after.x - before.x) * width);
      const taper = stroke.erase ? 1 : Math.min(1, .35 + index * .22, .35 + (points.length - 1 - index) * .22);
      const nibFactor = stroke.nib === "fountain" ? .45 + .55 * Math.abs(Math.sin(angle - Math.PI / 4)) : 1;
      const radius = stroke.erase ? scale / 2 : Math.max(.35, scale * (.22 + p.pressure * 1.5) * nibFactor * taper / 2);
      const x = p.x * width, y = p.y * height;
      for (let side = 0; side < 2; side += 1) {
        const direction = side === 0 ? 1 : -1;
        sides[side].push({ x: x - Math.sin(angle) * radius * direction, y: y + Math.cos(angle) * radius * direction });
      }
      if (index === 0 || index === points.length - 1) {
        drawing.beginPath();
        drawing.arc(x, y, radius, 0, Math.PI * 2);
        drawing.fill();
      }
    }
    const outline = [...sides[0], ...sides[1].reverse()];
    drawing.beginPath();
    const last = outline.at(-1), first = outline[0];
    drawing.moveTo((last.x + first.x) / 2, (last.y + first.y) / 2);
    for (let index = 0; index < outline.length; index += 1) {
      const point = outline[index], next = outline[(index + 1) % outline.length];
      drawing.quadraticCurveTo(point.x, point.y, (point.x + next.x) / 2, (point.y + next.y) / 2);
    }
    drawing.closePath();
    drawing.fill();
  }

  function render() {
    if (destroyed || !width || !height) return;
    drawing.setTransform(1, 0, 0, 1, 0, 0);
    drawing.clearRect(0, 0, canvas.width, canvas.height);
    drawing.setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);
    for (const stroke of strokes) paintStroke(stroke);
    drawing.globalCompositeOperation = "source-over";
  }

  function resize(dimensions) {
    if (destroyed) return;
    const nextDpr = Math.max(.25, Math.min(2, dimensions.dpr || requestedDpr));
    const rect = canvas.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    if (rect.width === width && rect.height === height && nextDpr === requestedDpr) return;
    finish();
    requestedDpr = nextDpr;
    width = rect.width;
    height = rect.height;
    const ratio = Math.min(requestedDpr, Math.sqrt(MAX_PIXELS / (width * height)));
    canvas.width = Math.max(1, Math.floor(width * ratio));
    canvas.height = Math.max(1, Math.floor(height * ratio));
    render();
    positionCursor();
  }

  function setActive(value) {
    if (destroyed) return;
    active = Boolean(value);
    root.inert = !active;
    if (!active) {
      finish();
      showTools(false, false);
    }
  }

  function setPreferences(value) {
    if (destroyed) return;
    preferences = value;
    root.dataset.inkForced = String(value.forcedColors);
    render();
  }

  async function save() {
    if (exporting) return;
    finish();
    exporting = true;
    updateTools();
    const output = document.createElement("canvas");
    output.width = canvas.width;
    output.height = canvas.height;
    try {
      const paint = output.getContext("2d");
      if (!paint) throw new Error("PNG canvas is unavailable.");
      paint.fillStyle = preferences.forcedColors ? getComputedStyle(stage).backgroundColor : context.palette.paper;
      paint.fillRect(0, 0, output.width, output.height);
      paint.drawImage(canvas, 0, 0);
      const blob = await new Promise((resolve, reject) => output.toBlob(result =>
        result ? resolve(result) : reject(new Error("PNG encoding failed.")), "image/png"));
      if (destroyed || !active || context.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      urls.add(url);
      try {
        const link = node("a", "");
        link.href = url;
        link.download = "suffsyed-ink-studio.png";
        root.append(link);
        link.click();
        link.remove();
        context.setStatus("PNG download requested. Nothing was uploaded.");
      } finally {
        URL.revokeObjectURL(url);
        urls.delete(url);
      }
    } catch (error) {
      if (!destroyed) context.reportError("The PNG could not be saved. Your drawing is still here.", error);
    } finally {
      output.width = output.height = 0;
      exporting = false;
      if (!destroyed) updateTools();
    }
  }

  function destroy() {
    if (destroyed) return;
    destroyed = true;
    active = false;
    listeners.abort();
    observer?.disconnect();
    context.signal.removeEventListener("abort", destroy);
    // The signal can already be aborted before the canvas is constructed.
    if (root.querySelector(".ink-paper")) {
      releaseCapture();
      canvas.width = canvas.height = 0;
    }
    strokes = [];
    current = previousInput = null;
    pointCount = 0;
    for (const url of urls) URL.revokeObjectURL(url);
    urls.clear();
    root.replaceChildren();
    root.inert = false;
    delete root.dataset.inkForced;
    for (const name of Object.keys(context.palette)) root.style.removeProperty(`--ink-${name}`);
  }

  setPreferences(preferences);
  updateTools();
  updateMaterial();
  await document.fonts.ready;
  if (destroyed || context.signal.aborted) return controller;
  observer = new ResizeObserver(() => resize({ dpr: requestedDpr }));
  observer.observe(canvas);
  resize({ dpr: 1 });
  return controller;
}
