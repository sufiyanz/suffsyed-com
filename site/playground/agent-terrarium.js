import { Terrarium } from "./sim-core.js";
import { button, canvasSurface, colors, element, lifecycle, readyFont } from "./sim-ui.js";

export async function mount(root, context) {
  const life = lifecycle(root, context);
  if (life.destroyed) return life.controller;
  try {
    let world = new Terrarium(context.seed);
    let running = false, started = false, accumulator = 0, elapsed = 0;
    let cursor = world.home, tool = "resource", dpr = 1;
    let palette = colors(root, life.preferences);
    const heading = element("header", "sim-heading");
    heading.append(
      element("h2", "", "Habitat"),
      element("p", "sim-kicker", "Local rule-based simulation"),
    );
    const controls = element("div", "pg-controls sim-controls");
    const run = button("Run", () => {
      if (!life.active || life.preferences.reducedMotion) return;
      running = !running;
      started = true;
      sync();
      context.setStatus(running ? "Colony running. Returning agents leave trails." : "Colony paused.");
    }, life, "sim-primary");
    const step = button("Step", () => {
      if (!life.active) return;
      running = false;
      started = true;
      world.step();
      sync();
      context.setStatus(`Step ${world.steps}. ${world.delivered} food returned; ${world.foodRemaining()} remaining.`);
    }, life);
    const reset = button("Reset", () => {
      if (!life.active) return;
      world = new Terrarium(context.seed, world.rules);
      cursor = world.home;
      running = started = false;
      accumulator = 0;
      sync();
      context.setStatus("Same seed, fresh colony. Your current rules are retained.");
    }, life);
    const view = button("Rules", () => {
      const open = root.dataset.view !== "rules";
      if (open) running = false;
      root.dataset.view = open ? "rules" : "world";
      view.textContent = open ? "World" : "Rules";
      view.setAttribute("aria-expanded", String(open));
      panel.hidden = !open;
      figure.hidden = tools.hidden = open;
      sync();
      if (!open) {
        surface.resize(dpr);
        draw();
      }
      context.setStatus(open ? "Rules open. Colony paused; adjust a rule or choose World." : "World view. Choose Run or Step.");
    }, life, "sim-view-button");
    view.setAttribute("aria-expanded", "false");
    controls.append(run, step, reset, view);
    const layout = element("div", "sim-layout");
    const figure = element("figure", "sim-world");
    const canvas = element("canvas", "pg-stage sim-canvas");
    canvas.tabIndex = 0;
    canvas.setAttribute("role", "application");
    canvas.setAttribute("aria-roledescription", "editable terrarium grid");
    canvas.setAttribute("aria-label", "Terrarium. Use arrows to move the cursor; Space places the selected tool.");
    canvas.width = 620;
    canvas.height = 380;
    const surface = canvasSurface(canvas);
    const metrics = element("div", "sim-metrics");
    metrics.setAttribute("aria-live", "off");
    const count = element("span", "sim-delivered");
    const food = element("span", "sim-food");
    const steps = element("span", "sim-steps");
    metrics.append(count, food, steps);
    figure.append(metrics, canvas);
    const panel = element("div", "sim-panel");
    const tools = element("div", "sim-tools");
    tools.setAttribute("role", "group");
    tools.setAttribute("aria-label", "Place in the world");
    const toolButtons = new Map();
    for (const [value, label] of [["resource", "+ Food"], ["obstacle", "# Wall"], ["erase", "/ Erase"]]) {
      const control = button(label, () => {
        tool = value;
        syncTools();
        context.setStatus(`${label.slice(2)} tool selected. Tap the world, or use arrows and Space on the grid.`);
      }, life);
      toolButtons.set(value, control);
      tools.append(control);
    }
    const position = element("p", "sim-position");
    position.setAttribute("aria-live", "polite");
    position.setAttribute("aria-atomic", "true");
    const help = element("p", "pg-help", "Tap to place. Or focus the world, move with arrow keys, and press Space.");
    const details = element("div", "sim-rules");
    details.append(element("h3", "", "Adjust the rules"));
    for (const [name, label, low, high] of [
      ["population", "Agents", 6, 36],
      ["exploration", "Exploration", 0, 100],
      ["persistence", "Trail memory", 0, 100],
    ]) {
      const field = element("label", "pg-field");
      const text = element("span", "", `${label}: ${world.rules[name]}`);
      const input = element("input");
      input.type = "range";
      input.min = String(low);
      input.max = String(high);
      input.step = "1";
      input.value = String(world.rules[name]);
      input.setAttribute("aria-label", label);
      life.listen(input, "input", () => {
        world.setRules({ [name]: Number(input.value) });
        world.rebuildPaths();
        text.textContent = `${label}: ${world.rules[name]}`;
        metricsUpdate();
        draw();
      });
      life.listen(input, "change", () => context.setStatus(`${label} set to ${input.value}.`));
      field.append(text, input);
      details.append(field);
    }
    const explanation = element("p", "sim-explanation",
      "Each agent wanders, senses nearby food, then finds a route home around walls. Return trips leave fading trails. Shared paths emerge from those small rules, not an AI model.");
    const mode = element("p", "sim-mode");
    const key = element("p", "sim-key", "Double ring: home / +: food / square: wall / dot: agent");
    panel.append(details, explanation, help, key, mode);
    panel.hidden = true;
    const dock = element("div", "sim-dock");
    dock.append(tools, controls);
    layout.append(figure, panel);
    root.append(heading, layout, dock, position);
    root.dataset.view = "world";

    function metricsUpdate() {
      count.textContent = `${world.delivered} returned`;
      food.textContent = `${world.foodRemaining()} food`;
      steps.textContent = `t ${world.steps}`;
      const description = `Cursor ${cursor % world.columns + 1}, ${Math.floor(cursor / world.columns) + 1}: ${
        cursor === world.home ? "home" : world.obstacles[cursor] ? "wall" :
          world.resources[cursor] ? `${world.resources[cursor]} food` : "open ground"}.`;
      if (position.textContent !== description) position.textContent = description;
    }

    function syncTools() {
      for (const [name, control] of toolButtons) control.setAttribute("aria-pressed", String(tool === name));
    }

    function draw() {
      if (root.dataset.view === "rules") return;
      surface.begin();
      const g = surface.drawing;
      const cellWidth = surface.width / world.columns, cellHeight = surface.height / world.rows;
      const unit = Math.min(cellWidth, cellHeight);
      const xy = cell => [(cell % world.columns + 0.5) * cellWidth, (Math.floor(cell / world.columns) + 0.5) * cellHeight];
      g.fillStyle = palette.surface;
      g.fillRect(0, 0, surface.width, surface.height);
      for (let cell = 0; cell < world.resources.length; cell++) {
        const [x, y] = xy(cell);
        g.fillStyle = palette.line;
        g.globalAlpha = 0.7;
        g.fillRect(x - 0.6, y - 0.6, 1.2, 1.2);
        g.globalAlpha = 1;
        if (world.trails[cell] > 0.02) {
          g.globalAlpha = life.preferences.forcedColors ? 1 : Math.min(0.75, world.trails[cell] / 8);
          g.fillStyle = palette.accent;
          g.beginPath();
          g.arc(x, y, Math.max(1, unit * 0.28), 0, Math.PI * 2);
          g.fill();
          g.globalAlpha = 1;
        }
        if (world.obstacles[cell]) {
          g.strokeStyle = palette.muted;
          g.lineWidth = 1;
          g.strokeRect(x - unit * 0.39, y - unit * 0.39, unit * 0.78, unit * 0.78);
          g.fillStyle = palette.muted;
          g.globalAlpha = 0.35;
          g.fillRect(x - unit * 0.23, y - unit * 0.23, unit * 0.46, unit * 0.46);
          g.globalAlpha = 1;
        }
        if (world.resources[cell]) {
          g.fillStyle = palette.accent;
          g.globalAlpha = life.preferences.forcedColors ? 1 : 0.09 + world.resources[cell] / 80;
          g.beginPath();
          g.arc(x, y, unit * 0.62, 0, Math.PI * 2);
          g.fill();
          g.globalAlpha = 1;
          g.strokeStyle = palette.accent;
          g.lineWidth = Math.max(1.5, unit * 0.12);
          g.beginPath();
          g.moveTo(x - unit * 0.3, y);
          g.lineTo(x + unit * 0.3, y);
          g.moveTo(x, y - unit * 0.3);
          g.lineTo(x, y + unit * 0.3);
          g.stroke();
        }
      }
      const [hx, hy] = xy(world.home);
      g.strokeStyle = palette.accent;
      g.lineWidth = 1.5;
      for (const radius of [0.52, 0.83]) {
        g.beginPath();
        g.arc(hx, hy, unit * radius, 0, Math.PI * 2);
        g.stroke();
      }
      g.font = `400 ${Math.max(7, Math.min(10, unit * 0.65))}px "DM Mono", monospace`;
      g.textAlign = "center";
      g.fillStyle = palette.muted;
      g.fillText("HOME", hx, hy + unit * 1.8);
      world.agents.forEach((agent, index) => {
        const [x, y] = xy(agent.cell);
        const offset = (index % 3 - 1) * unit * 0.13;
        g.fillStyle = agent.carrying ? palette.accent : palette.ink;
        g.beginPath();
        g.arc(x + offset, y + offset, Math.max(1.6, unit * 0.16), 0, Math.PI * 2);
        g.fill();
        if (agent.carrying) {
          g.strokeStyle = palette.ink;
          g.lineWidth = 1;
          g.strokeRect(x - unit * 0.3, y - unit * 0.3, unit * 0.6, unit * 0.6);
        }
      });
      const [cx, cy] = xy(cursor);
      g.strokeStyle = palette.ink;
      g.lineWidth = 1.5;
      const side = Math.max(3, unit * 0.32);
      for (const [dx, dy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
        const x = cx + dx * (cellWidth / 2 - 1), y = cy + dy * (cellHeight / 2 - 1);
        g.beginPath();
        g.moveTo(x - dx * side, y);
        g.lineTo(x, y);
        g.lineTo(x, y - dy * side);
        g.stroke();
      }
    }

    function sync() {
      palette = colors(root, life.preferences);
      if (life.preferences.reducedMotion) running = false;
      life.setRunning(running && life.active && !life.preferences.reducedMotion);
      run.textContent = running ? "Pause" : started ? "Resume" : "Run";
      run.disabled = life.preferences.reducedMotion || !life.active || root.dataset.view === "rules";
      step.disabled = !life.active || root.dataset.view === "rules";
      reset.disabled = !life.active;
      root.dataset.state = running && life.active ? "running" : "paused";
      mode.textContent = life.preferences.reducedMotion
        ? "Reduced motion: explore one step at a time."
        : "Eight steps per second. Reset repeats this seed.";
      metricsUpdate();
      syncTools();
      draw();
    }

    function place() {
      const result = world.place(cursor, tool);
      metricsUpdate();
      draw();
      context.setStatus(result + ` Column ${cursor % world.columns + 1}, row ${Math.floor(cursor / world.columns) + 1}.`);
      context.pulseSignature?.();
    }

    life.listen(canvas, "pointerdown", event => {
      if (!life.active || event.button !== 0) return;
      const rect = canvas.getBoundingClientRect();
      const x = Math.min(world.columns - 1, Math.max(0, Math.floor((event.clientX - rect.left) / rect.width * world.columns)));
      const y = Math.min(world.rows - 1, Math.max(0, Math.floor((event.clientY - rect.top) / rect.height * world.rows)));
      cursor = y * world.columns + x;
      canvas.focus({ preventScroll: true });
      place();
    });
    life.listen(canvas, "keydown", event => {
      if (!life.active) return;
      const movement = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key];
      if (!movement && event.code !== "Space") return;
      event.preventDefault();
      if (!movement) { place(); return; }
      const x = Math.min(world.columns - 1, Math.max(0, cursor % world.columns + movement[0]));
      const y = Math.min(world.rows - 1, Math.max(0, Math.floor(cursor / world.columns) + movement[1]));
      cursor = y * world.columns + x;
      metricsUpdate();
      draw();
    });
    life.listen(canvas, "contextlost", () => { throw new Error("Terrarium canvas context was lost."); });
    life.configure({
      sync,
      frame(dt) {
        accumulator += dt;
        elapsed += dt;
        if (accumulator >= 0.125) {
          accumulator -= 0.125;
          world.step();
          draw();
        }
        if (elapsed >= 0.5) { elapsed = 0; metricsUpdate(); }
      },
    });
    life.onResize = size => {
      dpr = size.dpr;
      surface.resize(dpr);
      draw();
    };
    await readyFont(context.signal);
    if (life.destroyed || context.signal.aborted) return life.controller;
    surface.resize(dpr);
    life.prepared();
    return life.controller;
  } catch (error) {
    life.controller.destroy();
    if (!context.signal.aborted) {
      context.reportError("The agent terrarium could not open.", error);
      throw error;
    }
    return life.controller;
  }
}
