const PITCHES = [
  { name: "A4", hz: 440 },
  { name: "G4", hz: 391.995 },
  { name: "E4", hz: 329.628 },
  { name: "D4", hz: 293.665 },
  { name: "C4", hz: 261.626 },
];
const STEPS = 8;
const MAX_CHORD = 3;
const MAX_VOICES = 6;
const LOOKAHEAD = .1;

export async function mount(root, context) {
  const listeners = new AbortController();
  let active = false, destroyed = false, playing = false, starting = false;
  let preferences = { ...context.preferences };
  let audio = null, master = null, timer = 0, generation = 0, closePromise = Promise.resolve();
  let nextStep = 0, nextTime = 0, tempo = 96, timbre = "sine", focused = 0, marked = -1;
  let cues = [];
  const voices = new Set();
  const pattern = Array.from({ length: PITCHES.length }, () => Array(STEPS).fill(false));
  const cells = [];
  const headers = [];

  function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  const housing = element("div", "loom-housing");
  const header = element("div", "loom-header");
  const brand = element("div", "loom-brand");
  brand.append(element("span", "loom-name", "sound loom"), element("span", "loom-model", "SL-08 / RHYTHM MACHINE"));
  const display = element("div", "loom-display");
  display.setAttribute("aria-hidden", "true");
  const tempoReadout = element("span", "loom-bpm", "96");
  const beatReadout = element("span", "loom-beat", "--");
  display.append(tempoReadout, element("span", "loom-unit", "BPM"), beatReadout);
  header.append(brand, display);
  const help = element("p", "pg-help loom-help", "Tap keys to weave. Play to listen. Swipe for all eight steps; arrow keys and Space work too.");
  const stage = element("div", "pg-stage loom-scroll");
  const grid = element("div", "loom-grid");
  grid.setAttribute("role", "grid");
  grid.setAttribute("aria-label", "Eight-step pentatonic loom. Arrow keys move; Space toggles a note. Up to three notes per step.");
  grid.setAttribute("aria-rowcount", "6");
  grid.setAttribute("aria-colcount", "9");
  const headerRow = element("div", "loom-row loom-headings");
  headerRow.setAttribute("role", "row");
  const corner = element("span", "loom-pitch", "NOTE");
  corner.setAttribute("role", "columnheader");
  headerRow.append(corner);
  for (let step = 0; step < STEPS; step++) {
    const header = element("span", "loom-step", String(step + 1).padStart(2, "0"));
    header.setAttribute("role", "columnheader");
    header.setAttribute("aria-label", `Step ${step + 1}`);
    headers.push(header);
    headerRow.append(header);
  }
  grid.append(headerRow);
  for (let row = 0; row < PITCHES.length; row++) {
    const line = element("div", "loom-row");
    line.setAttribute("role", "row");
    const pitch = element("span", "loom-pitch", PITCHES[row].name);
    pitch.setAttribute("role", "rowheader");
    line.append(pitch);
    for (let step = 0; step < STEPS; step++) {
      const holder = element("div", "loom-cell");
      holder.setAttribute("role", "gridcell");
      const cell = element("button", "loom-note");
      cell.type = "button";
      cell.tabIndex = cells.length ? -1 : 0;
      cell.dataset.row = String(row);
      cell.dataset.step = String(step);
      cell.dataset.stepNumber = String(step + 1);
      cell.setAttribute("aria-label", `${PITCHES[row].name}, step ${step + 1}`);
      cell.setAttribute("aria-pressed", "false");
      const knot = element("span", "loom-knot", "+");
      knot.setAttribute("aria-hidden", "true");
      cell.append(knot);
      cells.push(cell);
      holder.append(cell);
      line.append(holder);
    }
    grid.append(line);
  }
  stage.append(grid);
  const controls = element("div", "pg-controls loom-controls");
  const transport = element("div", "loom-transport");
  const play = element("button", "pg-button loom-play", "Play");
  const clear = element("button", "pg-button", "Clear");
  const reset = element("button", "pg-button", "Reset");
  play.type = clear.type = reset.type = "button";
  transport.append(play, clear, reset);
  const tuning = element("details", "loom-tuning");
  const tune = element("summary", "pg-button", "Tune");
  tune.title = "Adjust tempo and timbre";
  const settings = element("div", "loom-settings");
  const tempoLabel = element("label", "loom-setting");
  const tempoText = element("span", "", "Tempo 96");
  const tempoInput = element("input", "pg-field loom-tempo");
  tempoInput.type = "range";
  tempoInput.min = "64";
  tempoInput.max = "144";
  tempoInput.step = "4";
  tempoInput.value = String(tempo);
  tempoInput.setAttribute("aria-label", "Tempo");
  tempoInput.setAttribute("aria-valuetext", "96 beats per minute");
  tempoLabel.append(tempoText, tempoInput);
  const timbreLabel = element("label", "loom-setting");
  const timbreText = element("span", "", "Voice");
  const timbreInput = element("select", "pg-field");
  timbreInput.setAttribute("aria-label", "Timbre");
  for (const [value, title] of [["sine", "Soft"], ["triangle", "Reed"]]) {
    const option = element("option", "", title);
    option.value = value;
    timbreInput.append(option);
  }
  timbreLabel.append(timbreText, timbreInput);
  const tuningNote = element("p", "loom-tuning-note", "Five pitches. Eight steps.\nA small machine for a passing melody.");
  settings.append(tempoLabel, timbreLabel, tuningNote);
  tuning.append(tune, settings);
  controls.append(transport, tuning);
  const summary = element("p", "loom-summary");
  const error = element("p", "loom-error");
  error.hidden = true;
  housing.append(header, help, stage, controls, summary, error);
  root.append(housing);

  function count() {
    return pattern.reduce((total, row) => total + row.filter(Boolean).length, 0);
  }

  function say(message) {
    if (destroyed) return;
    summary.textContent = message;
    context.setStatus(message);
  }

  function updateControls() {
    if (destroyed) return;
    play.textContent = starting ? "Cancel" : playing ? "Stop" : "Play";
    play.setAttribute("aria-label", starting ? "Cancel audio start" : playing ? "Stop loom" : "Play loom");
    play.setAttribute("aria-pressed", String(playing));
    for (const control of [play, clear, reset, tempoInput, timbreInput, ...cells]) control.disabled = !active;
    root.dataset.state = !active ? "inactive" : starting ? "starting" : playing ? "playing" : error.hidden ? "ready" : "error";
    root.dataset.reducedMotion = String(preferences.reducedMotion);
    root.dataset.forcedColors = String(preferences.forcedColors);
    display.dataset.transport = starting ? "starting" : playing ? "playing" : "stopped";
  }

  function renderPattern() {
    for (const cell of cells) {
      const selected = pattern[Number(cell.dataset.row)][Number(cell.dataset.step)];
      cell.setAttribute("aria-pressed", String(selected));
    }
  }

  function mark(step) {
    if (marked === step) return;
    if (marked >= 0) {
      headers[marked].removeAttribute("aria-current");
      for (let row = 0; row < PITCHES.length; row++) cells[row * STEPS + marked].removeAttribute("data-current");
    }
    marked = step;
    beatReadout.textContent = marked < 0 ? "--" : String(marked + 1).padStart(2, "0");
    if (marked >= 0) {
      headers[marked].setAttribute("aria-current", "step");
      for (let row = 0; row < PITCHES.length; row++) cells[row * STEPS + marked].dataset.current = "true";
      if (playing && active && !destroyed && !document.hidden) context.pulseSignature?.();
    }
  }

  function releaseVoice(voice) {
    voice.oscillator.onended = null;
    voice.oscillator.disconnect();
    voice.envelope.disconnect();
    voices.delete(voice);
  }

  function stop() {
    generation++;
    playing = starting = false;
    clearTimeout(timer);
    timer = 0;
    cues = [];
    mark(-1);
    const closing = audio;
    audio = null;
    if (master) {
      master.gain.value = 0;
      master.disconnect();
      master = null;
    }
    for (const voice of [...voices]) {
      voice.oscillator.stop();
      releaseVoice(voice);
    }
    if (closing && closing.state !== "closed") {
      closing.onstatechange = null;
      // WebKit can finish close() before its pending hardware start; suspend orders the teardown.
      closePromise = closing.suspend().then(() => closing.close()).catch(cause => {
        context.reportError("Sound loom could not close its audio context.", cause);
      });
    }
    updateControls();
    return closePromise;
  }

  function fail(cause) {
    if (destroyed) return;
    stop();
    error.hidden = false;
    error.textContent = "Audio could not start or was interrupted. Check your browser's sound permission, then press Play to try again.";
    say("The loom is silent. Your pattern is preserved.");
    updateControls();
    context.reportError("Sound loom audio is unavailable.", cause);
  }

  function destroy() {
    if (destroyed) return closePromise;
    destroyed = true;
    active = false;
    stop();
    listeners.abort();
    context.signal.removeEventListener("abort", destroy);
    for (const row of pattern) row.fill(false);
    root.replaceChildren();
    return closePromise;
  }
  context.signal.addEventListener("abort", destroy, { once: true });
  if (context.signal.aborted) {
    destroy();
    return { setActive() {}, resize() {}, setPreferences() {}, destroy };
  }

  function note(pitch, time, duration) {
    if (voices.size >= MAX_VOICES) throw new Error("The loom exceeded its six-node voice budget.");
    const oscillator = audio.createOscillator();
    const envelope = audio.createGain();
    const voice = { oscillator, envelope };
    voices.add(voice);
    oscillator.type = timbre;
    oscillator.frequency.setValueAtTime(pitch.hz, time);
    envelope.gain.setValueAtTime(0, time);
    envelope.gain.linearRampToValueAtTime(.18, time + .009);
    envelope.gain.exponentialRampToValueAtTime(.0001, time + duration);
    oscillator.connect(envelope);
    envelope.connect(master);
    oscillator.onended = () => releaseVoice(voice);
    oscillator.start(time);
    oscillator.stop(time + duration + .012);
  }

  function loomTick() {
    timer = 0;
    if (!playing || !active || destroyed || document.hidden || !audio) return;
    try {
      if (audio.state !== "running") throw new Error(`Audio context is ${audio.state}.`);
      const now = audio.currentTime;
      if (nextTime < now - .1) nextTime = now + .025;
      let scheduled = 0;
      while (nextTime < now + LOOKAHEAD && scheduled < 2) {
        const duration = 60 / tempo / 2;
        for (let row = 0; row < PITCHES.length; row++) {
          if (pattern[row][nextStep]) note(PITCHES[row], nextTime, duration * .65);
        }
        cues.push({ step: nextStep, time: nextTime });
        nextStep = (nextStep + 1) % STEPS;
        nextTime += duration;
        scheduled++;
      }
      while (cues.length && cues[0].time <= now) mark(cues.shift().step);
      timer = setTimeout(loomTick, 40);
    } catch (cause) {
      fail(cause);
    }
  }

  async function playFromGesture() {
    if (!active || destroyed || document.hidden) return;
    if (playing || starting) {
      stop();
      say("Loom stopped. Press Play when you want to listen again.");
      return;
    }
    if (!count()) {
      say("The loom is empty. Select a note before pressing Play.");
      return;
    }
    const token = ++generation;
    starting = true;
    error.hidden = true;
    updateControls();
    say("Starting audio. Cancel keeps the loom silent and preserves your pattern.");
    try {
      const Audio = window.AudioContext || window.webkitAudioContext;
      if (!Audio) throw new Error("Web Audio is not supported by this browser.");
      // Construction and resume both remain in the explicit Play gesture, before any await.
      const opened = new Audio();
      audio = opened;
      const resumed = opened.resume();
      master = opened.createGain();
      master.gain.value = .24;
      master.connect(opened.destination);
      await resumed;
      if (destroyed || !active || document.hidden || token !== generation) return;
      if (opened.state !== "running") throw new Error(`Audio context is ${opened.state}.`);
      starting = false;
      playing = true;
      nextStep = 0;
      nextTime = opened.currentTime + .03;
      opened.onstatechange = () => {
        if (playing && opened.state !== "running") fail(new Error("The browser suspended loom audio."));
      };
      updateControls();
      say(`Playing your ${count()}-knot weave. Stop silences it; leaving also stops playback.`);
      loomTick();
    } catch (cause) {
      if (!destroyed && token === generation) fail(cause);
    }
  }

  function resetPattern() {
    for (const row of pattern) row.fill(false);
    for (const [row, step] of [[4, 0], [2, 1], [3, 2], [1, 3], [4, 4], [2, 5], [0, 6], [1, 7], [2, 0]]) {
      pattern[row][step] = true;
    }
    renderPattern();
  }

  function toggle(cell) {
    if (!active || destroyed) return;
    const row = Number(cell.dataset.row), step = Number(cell.dataset.step);
    const selected = pattern[row][step];
    if (!selected && pattern.filter(notes => notes[step]).length >= MAX_CHORD) {
      say(`Step ${step + 1} already has three notes. Remove one knot before adding another.`);
      return;
    }
    pattern[row][step] = !selected;
    renderPattern();
    if (!count() && (playing || starting)) stop();
    say(`${PITCHES[row].name}, step ${step + 1}: ${selected ? "removed" : "woven"}. ${count()} knots in the pattern.`);
  }

  const options = { signal: listeners.signal };
  play.addEventListener("click", playFromGesture, options);
  clear.addEventListener("click", () => {
    stop();
    for (const row of pattern) row.fill(false);
    renderPattern();
    say("All knots cleared. Weave a new pattern, then press Play.");
  }, options);
  reset.addEventListener("click", () => {
    stop();
    resetPattern();
    say("The original nine-knot weave is restored. Press Play to listen.");
  }, options);
  tempoInput.addEventListener("input", () => {
    tempo = Number(tempoInput.value);
    tempoText.textContent = `Tempo ${tempo}`;
    tempoReadout.textContent = String(tempo);
    tempoInput.setAttribute("aria-valuetext", `${tempo} beats per minute`);
  }, options);
  tempoInput.addEventListener("change", () => say(`Tempo set to ${tempo} beats per minute.`), options);
  timbreInput.addEventListener("change", () => {
    timbre = timbreInput.value;
    say(`${timbreInput.selectedOptions[0].textContent} thread selected for the next notes.`);
  }, options);
  tuning.addEventListener("toggle", () => {
    root.dataset.view = tuning.open ? "tune" : "keys";
    stage.hidden = tuning.open;
    tune.textContent = tuning.open ? "Keys" : "Tune";
    tune.title = tuning.open ? "Return to the step keys" : "Adjust tempo and timbre";
  }, options);
  cells.forEach((cell, index) => {
    cell.addEventListener("click", () => toggle(cell), options);
    cell.addEventListener("focus", () => {
      cells[focused].tabIndex = -1;
      focused = index;
      cell.tabIndex = 0;
    }, options);
    cell.addEventListener("keydown", event => {
      const row = Math.floor(index / STEPS), step = index % STEPS;
      let target = index;
      if (event.key === "ArrowLeft") target = row * STEPS + (step + STEPS - 1) % STEPS;
      else if (event.key === "ArrowRight") target = row * STEPS + (step + 1) % STEPS;
      else if (event.key === "ArrowUp") target = ((row + PITCHES.length - 1) % PITCHES.length) * STEPS + step;
      else if (event.key === "ArrowDown") target = ((row + 1) % PITCHES.length) * STEPS + step;
      else if (event.key === "Home") target = event.ctrlKey ? 0 : row * STEPS;
      else if (event.key === "End") target = event.ctrlKey ? cells.length - 1 : row * STEPS + STEPS - 1;
      else return;
      event.preventDefault();
      cells[target].focus({ preventScroll: true });
      const targetBounds = cells[target].getBoundingClientRect(), bounds = stage.getBoundingClientRect();
      if (targetBounds.left < bounds.left + 36) stage.scrollLeft -= bounds.left + 36 - targetBounds.left;
      if (targetBounds.right > bounds.right - 4) stage.scrollLeft += targetBounds.right - bounds.right + 4;
      if (targetBounds.top < bounds.top) stage.scrollTop -= bounds.top - targetBounds.top;
      if (targetBounds.bottom > bounds.bottom) stage.scrollTop += targetBounds.bottom - bounds.bottom;
    }, options);
  });

  function setActive(value) {
    if (destroyed) return;
    const wasPlaying = playing || starting;
    active = Boolean(value);
    if (!active) {
      stop();
      if (wasPlaying) say("Loom stopped while away. Press Play to listen again.");
    }
    updateControls();
  }

  function resize() {
    // The CSS grid reflows without rebuilding the ephemeral pattern or starting audio.
  }

  function setPreferences(value) {
    if (destroyed) return;
    preferences = { ...value };
    updateControls();
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden && (playing || starting)) {
      stop();
      say("Loom stopped while hidden. Press Play to listen again.");
    }
  }, options);
  window.addEventListener("pagehide", () => setActive(false), options);
  resetPattern();
  updateControls();
  say("Nine knots, five pitches, eight steps. Press Play to hear this local, temporary weave.");
  return { setActive, resize, setPreferences, destroy };
}
