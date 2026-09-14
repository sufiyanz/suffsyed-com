import { SignalGame } from "./sim-core.js";
import { button, canvasSurface, colors, element, lifecycle, readyFont } from "./sim-ui.js";

const directions = {
  ArrowLeft: { x: -1, y: 0 }, a: { x: -1, y: 0 },
  ArrowRight: { x: 1, y: 0 }, d: { x: 1, y: 0 },
  ArrowUp: { x: 0, y: -1 }, w: { x: 0, y: -1 },
  ArrowDown: { x: 0, y: 1 }, s: { x: 0, y: 1 },
};

export async function mount(root, context) {
  const life = lifecycle(root, context);
  if (life.destroyed) return life.controller;
  try {
    let game = new SignalGame(context.seed);
    let paused = false, manual = life.preferences.reducedMotion, target = null;
    let dpr = 1, lastSecond = 60;
    let palette = colors(root, life.preferences);
    const held = new Set();
    const heading = element("header", "sim-heading");
    heading.append(element("h2", "", "Signal / Noise"), element("p", "sim-kicker", "Pocket arcade"));
    const instructions = element("p", "pg-help",
      "Steer the ring to 8 + fragments. Avoid x noise: -3 seconds and back to center.");
    const controls = element("div", "pg-controls sim-controls");
    const start = button("Start 60 s", () => {
      if (!life.active) return;
      if (["won", "lost"].includes(game.state)) resetGame();
      if (game.state === "ready") {
        game.start();
        paused = false;
        context.setStatus(manual ? "Game started. Each arrow move uses half a second; take your time between moves." :
          "Game started. Collect plus signs and avoid crosses. You have sixty seconds.");
        canvas.focus({ preventScroll: true });
      } else {
        paused = !paused;
        clearInput();
        context.setStatus(paused ? "Game paused. The clock is stopped." : "Game resumed.");
      }
      sync();
    }, life, "sim-primary");
    const restart = button("Restart", () => {
      if (!life.active) return;
      resetGame();
      sync();
      context.setStatus("Same seed, fresh game. Choose Start when ready.");
    }, life);
    const modeLabel = element("label", "sim-mode-choice");
    const modeInput = element("input");
    modeInput.type = "checkbox";
    modeInput.checked = manual;
    modeLabel.append(modeInput, element("span", "", "Turn-based"));
    life.listen(modeInput, "change", () => {
      manual = modeInput.checked;
      if (game.state === "playing") paused = true;
      clearInput();
      sync();
      context.setStatus(`Turn-based play ${manual ? "on" : "off"}. ${game.state === "playing" ? "Choose Resume to continue." : "Choose Start when ready."}`);
    });
    controls.append(start, restart, modeLabel);
    const layout = element("div", "sim-layout");
    const playfield = element("div", "sim-playfield");
    const metrics = element("div", "sim-metrics");
    metrics.setAttribute("aria-live", "off");
    const score = element("span", "sim-score");
    const time = element("span", "sim-time");
    const hits = element("span", "sim-hits");
    const scoreValue = element("strong", "sim-score-value");
    const timeValue = element("strong", "sim-time-value");
    score.append(scoreValue, element("small", "", " / 8 signal"));
    time.append(timeValue, element("small", "", " s"));
    const canvas = element("canvas", "pg-stage sim-canvas");
    canvas.width = 650;
    canvas.height = 450;
    canvas.tabIndex = 0;
    canvas.setAttribute("role", "application");
    canvas.setAttribute("aria-roledescription", "signal collection game");
    canvas.setAttribute("aria-label", "Signal/noise playfield. Arrow keys or W A S D steer; Space pauses.");
    const surface = canvasSurface(canvas);
    const guidance = element("p", "sim-guidance");
    const position = element("p", "sim-position");
    const pad = element("div", "sim-pad");
    pad.setAttribute("role", "group");
    pad.setAttribute("aria-label", "Steer the signal");
    for (const [key, glyph, label] of [
      ["ArrowLeft", "\u2190", "Left"], ["ArrowUp", "\u2191", "Up"],
      ["ArrowDown", "\u2193", "Down"], ["ArrowRight", "\u2192", "Right"],
    ]) {
      const control = button(glyph, event => {
        if (!playable()) return;
        if (manual) move(directions[key]);
        else if (event.detail === 0) target = {
          x: Math.max(0, Math.min(12, game.player.x + directions[key].x)),
          y: Math.max(0, Math.min(8, game.player.y + directions[key].y)),
        };
      }, life);
      control.setAttribute("aria-label", label);
      life.listen(control, "pointerdown", event => {
        if (!playable() || manual || event.button !== 0) return;
        target = null;
        held.add(key);
        control.setPointerCapture(event.pointerId);
        control.dataset.pointerId = String(event.pointerId);
      });
      for (const name of ["pointerup", "pointercancel", "lostpointercapture", "blur"]) {
        life.listen(control, name, () => {
          held.delete(key);
          if (control.dataset.pointerId) {
            const pointer = Number(control.dataset.pointerId);
            if (control.hasPointerCapture(pointer)) control.releasePointerCapture(pointer);
            delete control.dataset.pointerId;
          }
        });
      }
      pad.append(control);
    }
    playfield.append(canvas);
    const aside = element("aside", "sim-reveal");
    const signatureFrame = element("div", "sim-signature-frame");
    const signature = element("img", "sim-signature");
    const source = new URL(context.data.signature.src, location.href);
    if (source.origin !== location.origin) throw new Error("The signature must be an existing same-origin asset.");
    const [, , signatureWidth, signatureHeight] = context.data.signature.viewBox;
    if (!(signatureWidth > 0 && signatureHeight > 0)) throw new Error("Invalid signature viewBox.");
    signature.alt = "";
    signature.width = signatureWidth;
    signature.height = signatureHeight;
    signature.src = source.href;
    const mask = element("span", "sim-signature-mask");
    mask.style.maskImage = `url("${source.href}")`;
    mask.style.webkitMaskImage = `url("${source.href}")`;
    mask.setAttribute("aria-hidden", "true");
    signatureFrame.append(signature, mask);
    metrics.append(score, signatureFrame, time);
    const segments = element("div", "sim-segments");
    segments.setAttribute("aria-hidden", "true");
    for (let i = 0; i < 8; i++) segments.append(element("span"));
    const message = element("p", "sim-result", "Eight fragments. One familiar mark.");
    const note = element("p", "sim-note", "A small exercise in choosing what deserves your attention. Everything stays in this tab.");
    aside.append(instructions, hits, guidance, position, note);
    const result = element("div", "sim-feedback");
    result.append(segments, message);
    layout.append(metrics, playfield, result, pad, controls);
    root.append(heading, layout, aside);

    function playable() {
      return life.active && game.state === "playing" && !paused;
    }

    function clearInput() {
      held.clear();
      target = null;
      for (const node of root.querySelectorAll("[data-pointer-id]")) {
        const pointer = Number(node.dataset.pointerId);
        if (node.hasPointerCapture(pointer)) node.releasePointerCapture(pointer);
        delete node.dataset.pointerId;
      }
    }

    function resetGame() {
      game = new SignalGame(context.seed);
      paused = false;
      lastSecond = 60;
      clearInput();
    }

    function metricsUpdate() {
      scoreValue.textContent = String(game.collected);
      timeValue.textContent = String(Math.ceil(game.remaining));
      hits.textContent = `${game.hits} noise`;
      const fraction = game.collected / 8;
      signature.style.clipPath = mask.style.clipPath = `inset(0 ${(1 - fraction) * 100}% 0 0)`;
      for (const [i, segment] of [...segments.children].entries()) {
        segment.dataset.found = String(i < game.collected);
      }
      position.textContent = `Ring: ${Math.round(game.player.x) + 1}, ${Math.round(game.player.y) + 1}.${
        game.target ? ` Next +: ${game.target.x + 1}, ${game.target.y + 1}.` : ""}`;
      if (game.state === "won") {
        message.textContent = `Signal found. ${Math.ceil(game.remaining)} seconds to spare.`;
      } else if (game.state === "lost") {
        message.textContent = `Time, not attention, ran out. ${game.collected} of 8 fragments found.`;
      } else {
        message.textContent = game.collected === 0 ? "Eight fragments. One familiar mark." :
          `${game.collected} fragments gathered. A signature takes shape.`;
      }
    }

    function draw() {
      surface.begin();
      const g = surface.drawing, p = palette;
      const cellWidth = surface.width / game.columns, cellHeight = surface.height / game.rows;
      const unit = Math.min(cellWidth, cellHeight);
      const point = item => [(item.x + 0.5) * cellWidth, (item.y + 0.5) * cellHeight];
      g.fillStyle = p.surface;
      g.fillRect(0, 0, surface.width, surface.height);
      g.fillStyle = p.line;
      for (let y = 0; y < game.rows; y++) for (let x = 0; x < game.columns; x++) {
        g.globalAlpha = 0.65;
        g.fillRect((x + 0.5) * cellWidth - 0.7, (y + 0.5) * cellHeight - 0.7, 1.4, 1.4);
      }
      g.globalAlpha = 1;
      g.font = `400 ${Math.max(13, unit * 0.62)}px "DM Mono", monospace`;
      g.textAlign = "center";
      g.textBaseline = "middle";
      for (const noise of game.noise) {
        const [x, y] = point(noise);
        g.strokeStyle = p.muted;
        g.lineWidth = Math.max(1.8, unit * 0.12);
        const arm = Math.max(3, unit * 0.22);
        g.beginPath();
        g.moveTo(x - arm, y - arm);
        g.lineTo(x + arm, y + arm);
        g.moveTo(x + arm, y - arm);
        g.lineTo(x - arm, y + arm);
        g.stroke();
      }
      if (game.target) {
        const [x, y] = point(game.target);
        g.fillStyle = p.accent;
        g.beginPath();
        g.moveTo(x, y - unit * 0.42);
        g.lineTo(x + unit * 0.42, y);
        g.lineTo(x, y + unit * 0.42);
        g.lineTo(x - unit * 0.42, y);
        g.closePath();
        g.fill();
        g.fillStyle = p.background;
        g.fillText("+", x, y);
      }
      const [x, y] = point(game.player);
      g.strokeStyle = p.accent;
      g.lineWidth = Math.max(2, unit * 0.09);
      g.beginPath();
      g.arc(x, y, unit * 0.29, 0, Math.PI * 2);
      g.stroke();
      g.fillStyle = p.ink;
      g.beginPath();
      g.arc(x, y, unit * 0.07, 0, Math.PI * 2);
      g.fill();
      if (game.cooldown > 0) {
        g.lineWidth = 1;
        g.beginPath();
        g.arc(x, y, unit * 0.43, 0, Math.PI * 2);
        g.stroke();
      }
      if (game.state !== "playing" || paused || !life.active) {
        const title = game.state === "ready" ? "COLLECT 8 +" :
          game.state === "won" ? "SIGNAL FOUND" : game.state === "lost" ? "TIME'S UP" : "PAUSED";
        const fontSize = Math.max(14, Math.min(26, surface.width / 17));
        g.font = `500 ${fontSize}px "DM Mono", monospace`;
        const textWidth = g.measureText(title).width;
        const bannerY = surface.height * 0.63;
        g.fillStyle = p.background;
        g.fillRect(surface.width / 2 - textWidth / 2 - 10, bannerY - fontSize, textWidth + 20, fontSize * 2.2);
        g.fillStyle = p.ink;
        g.fillText(title, surface.width / 2, bannerY);
        g.font = `400 ${Math.max(8, Math.min(11, unit * 0.7))}px "DM Mono", monospace`;
        g.fillStyle = p.accent;
        g.fillText(game.state === "ready" ? "x: -3s + center" : "YOUR PACE. YOUR SIGNAL.", surface.width / 2, bannerY + fontSize * 0.85);
      }
    }

    function sync() {
      palette = colors(root, life.preferences);
      if (life.preferences.reducedMotion && !manual) {
        manual = true;
        if (game.state === "playing") paused = true;
      }
      modeInput.checked = manual;
      modeInput.disabled = life.preferences.reducedMotion;
      if (manual) for (const noise of game.noise) {
        noise.x = noise.baseX;
        noise.y = noise.baseY;
      }
      life.setRunning(playable() && !manual);
      start.textContent = game.state === "ready" ? "Start 60 s" :
        ["won", "lost"].includes(game.state) ? "Play again" : paused ? "Resume" : "Pause";
      start.disabled = restart.disabled = !life.active;
      root.dataset.state = game.state === "playing" ? playable() ? "playing" : "paused" : game.state;
      guidance.textContent = manual
        ? "Turn-based: arrows / WASD or buttons. Each move uses 0.5 s; noise stays still. Space pauses."
        : "Arrows / WASD, hold a direction button, or drag the ring. Space pauses.";
      metricsUpdate();
      draw();
    }

    function advance(dt, direction, turnBased) {
      const before = { hits: game.hits, collected: game.collected, state: game.state };
      game.update(dt, direction, turnBased);
      const changed = before.hits !== game.hits || before.collected !== game.collected;
      const second = Math.ceil(game.remaining);
      if (game.state !== before.state) {
        clearInput();
        sync();
        context.setStatus(game.state === "won" ?
          `Signal found. All eight fragments recovered with ${second} seconds left.` :
          `Minute complete. ${game.collected} of eight fragments found. Choose Play again to restart.`);
        if (game.state === "won") context.pulseSignature?.();
      } else {
        if (changed || lastSecond !== second || turnBased) metricsUpdate();
        if (before.hits !== game.hits) {
          target = null;
          context.setStatus(`Noise hit. Three seconds lost; back at the center. ${second} seconds left.`);
        } else if (before.collected !== game.collected) {
          context.setStatus(`Fragment ${game.collected} of eight found. ${second} seconds left.`);
          context.pulseSignature?.();
        } else if ([30, 10].includes(second) && lastSecond !== second) {
          context.setStatus(`${second} seconds left. ${game.collected} of eight fragments found.`);
        } else if (turnBased) {
          context.setStatus(position.textContent + ` ${second} seconds left.`);
        }
        draw();
      }
      lastSecond = second;
    }

    function move(direction) {
      if (playable()) advance(0.5, direction, true);
    }

    life.listen(canvas, "keydown", event => {
      const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
      if (!directions[key] && event.code !== "Space") return;
      event.preventDefault();
      if (event.code === "Space") {
        if (!event.repeat && life.active && game.state === "playing") start.click();
        return;
      }
      if (!playable()) return;
      if (manual) {
        if (!event.repeat) move(directions[key]);
      } else {
        target = null;
        held.add(key);
      }
    });
    life.listen(root, "keyup", event => held.delete(event.key.length === 1 ? event.key.toLowerCase() : event.key));
    life.listen(canvas, "blur", clearInput);
    life.listen(window, "blur", () => {
      if (!playable()) return;
      paused = true;
      clearInput();
      sync();
      context.setStatus("Game paused while focus is elsewhere. Choose Resume when ready.");
    });
    function steer(event) {
      const bounds = canvas.getBoundingClientRect();
      target = {
        x: Math.max(0, Math.min(12, (event.clientX - bounds.left) / bounds.width * game.columns - 0.5)),
        y: Math.max(0, Math.min(8, (event.clientY - bounds.top) / bounds.height * game.rows - 0.5)),
      };
    }
    life.listen(canvas, "pointerdown", event => {
      if (!playable() || manual || event.button !== 0) return;
      event.preventDefault();
      canvas.focus({ preventScroll: true });
      held.clear();
      canvas.setPointerCapture(event.pointerId);
      canvas.dataset.pointerId = String(event.pointerId);
      steer(event);
    });
    life.listen(canvas, "pointermove", event => {
      if (playable() && canvas.hasPointerCapture(event.pointerId)) steer(event);
    });
    for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) {
      life.listen(canvas, name, event => {
        target = null;
        if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
        delete canvas.dataset.pointerId;
      });
    }
    life.listen(canvas, "contextlost", () => { throw new Error("Signal/noise canvas context was lost."); });
    life.configure({
      sync,
      cleanup: clearInput,
      frame(dt) {
        let direction = { x: 0, y: 0 };
        for (const key of held) {
          direction.x += directions[key].x;
          direction.y += directions[key].y;
        }
        if (target) {
          direction = { x: target.x - game.player.x, y: target.y - game.player.y };
          if (Math.hypot(direction.x, direction.y) < 5 * dt) {
            game.player.x = target.x;
            game.player.y = target.y;
            direction = { x: 0, y: 0 };
            target = null;
          }
        }
        advance(dt, direction, false);
      },
    });
    life.onResize = size => {
      dpr = size.dpr;
      surface.resize(dpr);
      draw();
    };
    await Promise.all([readyFont(context.signal), signature.decode()]);
    if (life.destroyed || context.signal.aborted) return life.controller;
    surface.resize(dpr);
    life.prepared();
    return life.controller;
  } catch (error) {
    life.controller.destroy();
    if (!context.signal.aborted) {
      context.reportError("Signal/noise could not open.", error);
      throw error;
    }
    return life.controller;
  }
}
