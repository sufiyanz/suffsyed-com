import { element, control, applyPreferences } from "./code-dom.js";

export const EXAMPLES = Object.freeze([
  { name: "Orbit studies", source: `# A quiet rosette. Angles are in degrees.
clear paper
color green
width 0.8
repeat 48 as i {
  let a = i * 7.5
  circle 200 + cos(a) * 73, 200 + sin(a) * 73, 88
}
color forest
width 1.5
circle 200, 200, 168
circle 200, 200, 12
print 48` },
  { name: "Woven light", source: `# Straight lines, curved impressions.
clear forest
color stone
width 0.8
repeat 65 as i {
  let t = i * 5
  line 40, 40 + t, 40 + t, 360
  line 360, 360 - t, 360 - t, 40
}
color paper
rect 40, 40, 320, 320
print 130` },
  { name: "Small architectures", source: `# Each repeat gets its own local variables.
clear paper
color forest
width 1
repeat 7 as row {
  repeat 7 as col {
    let x = 44 + col * 46
    let y = 44 + row * 46
    let r = 5 + (sin(row * 30 + col * 20) + 1) * 7
    rect x - 19, y - 19, 38, 38
    circle x, y, r
  }
}
print 49` },
]);

function initialDrawing() {
  const operations = [{ command: "clear", color: "paper" }, { command: "color", color: "green" }, { command: "width", args: [0.8] }];
  for (let i = 0; i < 48; i++) {
    const angle = i * Math.PI / 24;
    operations.push({ command: "circle", args: [200 + Math.cos(angle) * 73, 200 + Math.sin(angle) * 73, 88] });
  }
  return [...operations, { command: "color", color: "forest" }, { command: "width", args: [1.5] },
    { command: "circle", args: [200, 200, 168] }, { command: "circle", args: [200, 200, 12] }];
}

export async function mount(root, context) {
  let active = false, destroyed = false, worker = null, timeout = null;
  let operations = initialDrawing(), preferences = { ...context.preferences };
  let dimensions = { width: 0, height: 0, dpr: 1 };
  const listeners = new AbortController();
  const shell = element("section", "code-shell");
  const heading = element("header", "code-heading");
  const title = element("h3", "", "A little code. A little wonder.");
  heading.append(title, element("p", "pg-help", "A bounded drawing language, not JavaScript or a shell. Nothing is saved."));
  const controls = element("div", "pg-controls code-controls");
  const exampleLabel = element("label", "code-example-label", "Study");
  const examples = element("select", "pg-field");
  examples.setAttribute("aria-label", "Drawing example");
  for (const [index, example] of EXAMPLES.entries()) {
    const option = element("option", "", example.name);
    option.value = String(index);
    examples.append(option);
  }
  exampleLabel.append(examples);
  const run = control("Run", "run"), stop = control("Stop", "stop"), reset = control("Reset", "reset");
  run.disabled = true; stop.disabled = true; reset.disabled = true; examples.disabled = true;
  controls.append(exampleLabel, run, stop, reset);
  const workspace = element("div", "code-workspace");
  const editorPanel = element("div", "code-editor-panel");
  const editorLabel = element("label", "code-panel-label", "01 / Drawing instructions");
  const editor = element("textarea", "code-editor");
  editor.value = EXAMPLES[0].source;
  editor.maxLength = 16000;
  editor.spellcheck = false;
  editor.autocapitalize = "off";
  editor.setAttribute("autocomplete", "off");
  editor.setAttribute("autocorrect", "off");
  editor.setAttribute("aria-label", "Drawing instructions");
  editorLabel.append(editor);
  const log = element("pre", "code-log", "Ready. The preview is the first study; Run executes your code.");
  log.setAttribute("aria-label", "Drawing log");
  editorPanel.append(editorLabel, log);
  const preview = element("figure", "pg-stage code-preview");
  const canvas = element("canvas", "code-canvas");
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", "Orbit study: 48 overlapping circles form a green rosette.");
  const caption = element("figcaption", "code-caption", "02 / A 400 x 400 imaginary sheet");
  preview.append(canvas, caption);
  workspace.append(editorPanel, preview);
  const help = element("details", "code-guide");
  help.append(element("summary", "", "Language guide & limits"));
  help.append(element("p", "", "One command per line (or use semicolons). Coordinates run from 0 to 400; (0, 0) is the top left. Shapes are outlines. # starts a comment."));
  help.append(element("pre", "", `let x = 200
clear paper
color green
width 1
line 20, 20, x, 300
circle x, 200, 60
rect 40, 40, 80, 120
repeat 12 as i {
  circle 200 + cos(i * 30) * 80, 200, 20
}
print x`));
  help.append(element("p", "", "Use + - * /, parentheses, sin(angle), cos(angle), abs(value), sqrt(value). Angles are degrees. Colors: forest, green, stone, paper, white, ink. Repeat counts: 0-512; the index starts at 0. Variables inside a repeat are local to that iteration. Width: 0.2-20; radius: 0-2,000."));
  help.append(element("p", "", "Limits: 16,000 characters; 12,000 tokens; 4,096 syntax nodes; 32 expression levels; 8 nested repeats; 256 variables; 12,000 steps; 6,000 drawing operations; 40 log lines. Numbers must stay finite within +/-1,000,000. Worker execution has a 120 ms budget plus a 1.5 s startup watchdog. Stop or leaving terminates the Worker. No files, network commands or general-purpose code."));
  const errorBox = element("p", "code-error");
  errorBox.hidden = true;
  shell.append(heading, controls, errorBox, workspace, help);

  function finishWorker() {
    if (timeout !== null) clearTimeout(timeout);
    timeout = null;
    if (worker) {
      worker.onmessage = null; worker.onerror = null; worker.onmessageerror = null;
      worker.terminate();
      worker = null;
    }
    stop.disabled = true;
    run.disabled = !active || destroyed;
    editor.removeAttribute("aria-busy");
  }
  function fail(message, error) {
    finishWorker();
    errorBox.textContent = message; errorBox.hidden = false;
    log.textContent = "Not drawn. The last successful sheet is still visible.";
    context.reportError(message, error);
  }
  function stopDrawing(message) {
    const running = worker !== null;
    finishWorker();
    if (running) {
      log.textContent = message;
      context.setStatus(message);
    }
  }
  function draw() {
    if (destroyed || !canvas.isConnected) return;
    const bounds = canvas.getBoundingClientRect();
    const size = Math.max(1, Math.min(bounds.width || 240, bounds.height || 240, 500));
    const dpr = Math.min(2, Math.max(1, dimensions.dpr));
    const pixels = Math.min(1000, Math.round(size * dpr));
    canvas.width = pixels; canvas.height = pixels;
    const paint = canvas.getContext("2d");
    if (!paint) throw new Error("A 2D canvas is unavailable in this browser.");
    paint.setTransform(pixels / 400, 0, 0, pixels / 400, 0, 0);
    const style = getComputedStyle(root);
    const ink = preferences.forcedColors ? style.color : context.palette.forest;
    const paper = preferences.forcedColors ? style.backgroundColor : context.palette.paper;
    const color = (name, background = false) => preferences.forcedColors
      ? (background ? paper : ink) : context.palette[name];
    paint.fillStyle = paper; paint.fillRect(0, 0, 400, 400);
    paint.strokeStyle = ink; paint.lineWidth = 1;
    for (const operation of operations) {
      const args = operation.args;
      switch (operation.command) {
        case "clear": paint.fillStyle = color(operation.color, true); paint.fillRect(0, 0, 400, 400); break;
        case "color": paint.strokeStyle = color(operation.color); break;
        case "width": paint.lineWidth = args[0]; break;
        case "line": paint.beginPath(); paint.moveTo(args[0], args[1]); paint.lineTo(args[2], args[3]); paint.stroke(); break;
        case "circle": paint.beginPath(); paint.arc(args[0], args[1], args[2], 0, Math.PI * 2); paint.stroke(); break;
        case "rect": paint.strokeRect(...args); break;
      }
    }
  }
  function safeDraw() {
    try { draw(); } catch (error) { fail("The drawing preview could not be painted.", error); }
  }
  function runDrawing() {
    if (!active || destroyed) return;
    finishWorker();
    errorBox.hidden = true;
    log.textContent = "Drawing in an isolated Worker...";
    editor.setAttribute("aria-busy", "true");
    run.disabled = true; stop.disabled = false;
    try {
      worker = new Worker(new URL("./code-worker.js", import.meta.url), { type: "module", name: "scratch-drawing" });
      worker.onmessage = (event) => {
        if (destroyed || !active) return;
        const result = event.data;
        finishWorker();
        if (result.type === "error") {
          fail(result.message, new Error(result.message));
          return;
        }
        if (result.type !== "result" || !Array.isArray(result.operations) || !Array.isArray(result.logs)) {
          fail("The drawing Worker returned an unreadable result.", new Error("Invalid Worker result"));
          return;
        }
        operations = result.operations;
        const shapes = operations.filter((operation) => ["circle", "rect", "line"].includes(operation.command)).length;
        canvas.setAttribute("aria-label", `Your drawing: ${shapes} outline shapes on a 400 by 400 sheet. Drawing instructions and numeric log are alongside.`);
        try { draw(); } catch (error) { fail("The drawing preview could not be painted.", error); return; }
        log.textContent = `${shapes} shapes / ${result.operations.length} operations / ${result.steps} steps\n${result.logs.length ? result.logs.map((entry) => `> ${entry}`).join("\n") : "No printed values."}`;
        if (root.dataset.codeCompact === "true") {
          const overflow = preview.getBoundingClientRect().bottom - shell.getBoundingClientRect().bottom + 8;
          if (overflow > 0) shell.scrollTop += overflow;
        }
        context.setStatus(`Drawing complete: ${shapes} shapes.`);
      };
      worker.onerror = (event) => {
        event.preventDefault();
        fail("The isolated drawing Worker could not run. Try Run again.", new Error(event.message));
      };
      worker.onmessageerror = () => fail("The drawing Worker response could not be read.", new Error("Worker message error"));
      timeout = setTimeout(() => fail("Drawing stopped after 1.5 seconds. Try a smaller example.", new Error("Drawing watchdog timeout")), 1500);
      worker.postMessage({ source: editor.value });
    } catch (error) {
      fail("The isolated drawing Worker could not start in this browser.", error);
    }
  }
  function restore() {
    stopDrawing("Drawing stopped.");
    examples.value = "0"; editor.value = EXAMPLES[0].source;
    operations = initialDrawing();
    canvas.setAttribute("aria-label", "Orbit study: 48 overlapping circles form a green rosette.");
    errorBox.hidden = true;
    log.textContent = "Reset to Orbit studies. Run executes this code.";
    safeDraw();
    context.setStatus("Drawing and code reset to Orbit studies.");
  }
  function destroy() {
    if (destroyed) return;
    destroyed = true; active = false;
    finishWorker();
    listeners.abort();
    context.signal.removeEventListener("abort", destroy);
    operations = [];
    editor.value = ""; log.textContent = ""; canvas.width = 1; canvas.height = 1;
    root.replaceChildren();
  }
  const controller = {
    setActive(value) {
      if (destroyed) return;
      active = Boolean(value);
      if (!active) stopDrawing("Drawing stopped while inactive. Run when you return.");
      run.disabled = !active || worker !== null;
      reset.disabled = !active; examples.disabled = !active; editor.disabled = !active;
    },
    resize(value) {
      if (destroyed) return;
      if (![value.width, value.height, value.dpr].every(Number.isFinite) || value.width < 0 || value.height < 0 || value.dpr <= 0) {
        fail("The drawing received invalid preview dimensions.", new Error("Invalid resize dimensions")); return;
      }
      dimensions = value;
      root.dataset.codeCompact = String(value.width < 580);
      safeDraw();
    },
    setPreferences(value) {
      if (destroyed) return;
      preferences = { ...value }; applyPreferences(root, preferences); safeDraw();
    },
    destroy,
  };
  context.signal.addEventListener("abort", destroy, { once: true });
  if (context.signal.aborted) { destroy(); return controller; }
  root.replaceChildren(shell);
  applyPreferences(root, preferences);
  root.dataset.codeCompact = String(root.clientWidth < 580);
  editor.disabled = true;
  run.addEventListener("click", runDrawing, { signal: listeners.signal });
  stop.addEventListener("click", () => stopDrawing("Drawing stopped. The last successful sheet is still visible."), { signal: listeners.signal });
  reset.addEventListener("click", restore, { signal: listeners.signal });
  examples.addEventListener("change", () => {
    if (!active || destroyed) return;
    stopDrawing("Drawing stopped.");
    editor.value = EXAMPLES[Number(examples.value)].source;
    log.textContent = `${EXAMPLES[Number(examples.value)].name} loaded. Run to draw it.`;
    errorBox.hidden = true;
    context.setStatus("Example loaded. Run to draw it.");
  }, { signal: listeners.signal });
  editor.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); runDrawing(); }
  }, { signal: listeners.signal });
  try { await document.fonts.ready; } catch (error) {
    if (!context.signal.aborted && !destroyed) fail("The drawing fonts could not become ready.", error);
    return controller;
  }
  if (context.signal.aborted || destroyed) { destroy(); return controller; }
  safeDraw();
  return controller;
}
