/* Local, opt-in marks and a fixed authored study. This module makes no requests. */
(() => {
  "use strict";

  const MARKS_KEY = "suff-journal-reader-marks-v1";
  const STAGE_MS = 2200;
  const emptyMarks = () => [null, null, null];
  const validMarks = (value) => Array.isArray(value) && value.length === 3
    && value.every((mark) => mark === null
      || (Number.isInteger(mark) && mark >= 0 && mark <= 100));

  function enhanceMargin(root) {
    if (root.dataset.marginReady) return;
    const axes = [...root.querySelectorAll("[data-margin-axis]")];
    const notice = root.querySelector("[data-margin-notice]");
    const reset = root.querySelector("[data-margin-reset]");
    const fallback = root.querySelector("[data-margin-fallback]");
    const parts = axes.map((axis) => ({
      axis,
      input: axis.querySelector("input[type=range]"),
      output: axis.querySelector("[data-margin-output]"),
      middle: axis.querySelector("[data-margin-middle]"),
      clear: axis.querySelector("[data-margin-clear]"),
    }));
    if (axes.length !== 3 || !notice || !reset || !fallback
      || parts.some((part) => !part.input || !part.output || !part.middle || !part.clear)) return;

    let marks = emptyMarks();

    function report(message, problem = false) {
      notice.textContent = message;
      root.dataset.storageProblem = String(problem);
    }

    function markText(index) {
      const value = marks[index];
      if (value === null) return "No mark placed";
      if (value === 50) return "Your mark: between the two (50 of 100)";
      const pole = value > 50 ? axes[index].dataset.top : axes[index].dataset.bottom;
      return `Your mark: ${value === 0 || value === 100 ? "at" : "toward"} ${pole.toLowerCase()} (${value} of 100)`;
    }

    function render() {
      parts.forEach(({ axis, input, output, middle, clear }, index) => {
        const placed = marks[index] !== null;
        axis.dataset.marked = String(placed);
        input.value = String(placed ? marks[index] : 50);
        input.setAttribute("aria-valuetext", markText(index));
        output.textContent = markText(index);
        middle.textContent = placed ? "Move to the middle" : "Place a middle mark";
        clear.disabled = !placed;
      });
    }

    function clearStoredMarks() {
      try {
        window.localStorage.removeItem(MARKS_KEY);
        report("Your marks are cleared. This browser only, not a live poll. Nothing was uploaded.");
      } catch {
        // Some storage implementations permit replacement but not removal.
        try {
          window.localStorage.setItem(MARKS_KEY, JSON.stringify(emptyMarks()));
          report("Your marks are cleared. An empty local record remains because this browser could not remove it.", true);
        } catch {
          report("Visible marks are cleared, but browser storage could not be cleared. Old marks may return on reload. Clear this site’s storage in your browser settings to remove them. Nothing was uploaded.", true);
        }
      }
    }

    function save() {
      if (marks.every((mark) => mark === null)) {
        clearStoredMarks();
        return;
      }
      try {
        window.localStorage.setItem(MARKS_KEY, JSON.stringify(marks));
        report("Your marks are saved in this browser only, not a live poll. Nothing is uploaded; clear them whenever you like.");
      } catch {
        // Do not silently restore an older position on the next visit.
        try {
          window.localStorage.removeItem(MARKS_KEY);
          report("Browser storage could not save your marks. They work for this visit only; older saved marks were cleared. Nothing is uploaded.", true);
        } catch {
          report("Browser storage is unavailable. Your new marks work for this visit only. Older saved marks could not be removed and may return on reload. Nothing is uploaded.", true);
        }
      }
    }

    function place(index, value) {
      if (!Number.isInteger(value) || value < 0 || value > 100) {
        report("That position was not a whole number from 0 to 100. It was not saved. Choose a position on the axis or clear your marks.", true);
        return;
      }
      marks[index] = value;
      render();
      save();
    }

    // Reading an existing opt-in record is allowed; no probe or default is written.
    try {
      const stored = window.localStorage.getItem(MARKS_KEY);
      if (stored !== null) {
        let parsed;
        try {
          parsed = JSON.parse(stored);
        } catch {
          report("Saved marks contain unreadable JSON and were not restored. Clear all my marks to remove them, or place a new mark to replace them. Nothing is uploaded.", true);
        }
        if (parsed !== undefined) {
          if (validMarks(parsed)) {
            marks = parsed;
            report(marks.some((mark) => mark !== null)
              ? "Your saved marks are restored in this browser only, not a live poll. Nothing is uploaded."
              : "No marks are saved. This browser only, not a live poll. Nothing is uploaded.");
          } else {
            report("Saved marks have an invalid format: expected exactly three entries, each null or a whole number from 0 to 100. Nothing was restored. Clear all my marks, or place a new mark to replace them.", true);
          }
        }
      }
    } catch {
      report("Browser storage could not be read. Marks still work for this visit; saving may be unavailable. Nothing is uploaded. Clear all my marks can retry removing a saved record.", true);
    }

    parts.forEach(({ input, middle, clear }, index) => {
      input.addEventListener("input", () => place(index, Number(input.value)));
      input.addEventListener("pointerup", () => {
        if (marks[index] === null) place(index, Number(input.value));
      });
      input.addEventListener("keydown", (event) => {
        const current = Number(input.value);
        const positions = {
          ArrowUp: current + 1, ArrowRight: current + 1,
          ArrowDown: current - 1, ArrowLeft: current - 1,
          PageUp: current + 10, PageDown: current - 10,
          Home: 0, End: 100,
        };
        if (!Object.prototype.hasOwnProperty.call(positions, event.key)) return;
        event.preventDefault();
        place(index, Math.min(100, Math.max(0, positions[event.key])));
      });
      middle.addEventListener("click", () => {
        place(index, 50);
        input.focus({ preventScroll: true });
      });
      clear.addEventListener("click", () => {
        marks[index] = null;
        render();
        save();
        middle.focus({ preventScroll: true });
      });
    });
    reset.addEventListener("click", () => {
      marks = emptyMarks();
      render();
      clearStoredMarks();
    });
    render();
    root.dataset.marginReady = "true";
    root.querySelectorAll("[data-margin-control]").forEach((control) => { control.hidden = false; });
    fallback.hidden = true;
  }

  function enhanceResearch(root) {
    if (root.dataset.researchReady) return;
    const get = (name) => root.querySelector(`[data-research-${name}]`);
    const controls = get("controls");
    const start = get("start"), pause = get("pause"), resume = get("resume");
    const stepButton = get("step"), reset = get("reset");
    const status = get("status"), empty = get("empty"), artifact = get("artifact");
    const fallback = get("fallback"), playback = get("playback"), resultLink = get("result-link");
    const roles = [...root.querySelectorAll("[data-research-role]")];
    const milestones = [...root.querySelectorAll("[data-research-milestone]")];
    const entries = [...root.querySelectorAll("[data-research-log]")];
    if ([controls, start, pause, resume, stepButton, reset, status, empty, artifact,
      fallback, playback, resultLink].some((element) => !element)
      || roles.length !== 3 || milestones.length !== 3 || entries.length !== 3
      || milestones.some((milestone) => !milestone.querySelector("[data-milestone-state]"))) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let completed = 0;
    let state = "idle";
    let timer = null;
    let deadline = 0;
    let remaining = STAGE_MS;

    function render() {
      root.dataset.researchState = state;
      start.disabled = state !== "idle";
      pause.disabled = state !== "running";
      resume.disabled = state !== "paused";
      stepButton.disabled = state === "running" || state === "complete";
      empty.hidden = completed !== 0;
      artifact.hidden = state !== "complete";
      resultLink.hidden = state !== "complete";
      playback.textContent = reducedMotion.matches
        ? "Reduced motion: Start, Resume, and Next step each reveal one authored stage. Nothing advances automatically."
        : "Three predetermined stages, about two seconds each. No network requests. Next step works without timed playback; switching away pauses until you resume.";
      roles.forEach((role, index) => {
        role.dataset.active = String(state === "running" && completed === index);
        role.dataset.complete = String(index < completed);
      });
      milestones.forEach((milestone, index) => {
        milestone.dataset.complete = String(index < completed);
        const current = index === completed;
        const label = index < completed ? "Complete"
          : current && state === "running" ? "Reading this stage"
            : current && state === "paused" ? "Next · paused" : "Not started";
        milestone.querySelector("[data-milestone-state]").textContent = label;
        if (current && (state === "running" || state === "paused")) {
          milestone.setAttribute("aria-current", "step");
        } else {
          milestone.removeAttribute("aria-current");
        }
      });
      entries.forEach((entry, index) => { entry.hidden = index >= completed; });
    }

    function cancelTimer() {
      window.clearTimeout(timer);
      timer = null;
    }

    function pauseCycle(reason) {
      if (state !== "running") return;
      remaining = Math.max(0, deadline - performance.now());
      cancelTimer();
      state = "paused";
      status.textContent = `${reason} ${completed} of 3 stages complete. Resume or choose Next step.`;
      render();
    }

    function schedule() {
      if (state !== "running") return;
      if (document.hidden) {
        deadline = performance.now() + remaining;
        pauseCycle("Paused because this page is hidden.");
        return;
      }
      deadline = performance.now() + remaining;
      timer = window.setTimeout(() => {
        timer = null;
        if (state !== "running") return;
        if (document.hidden) {
          pauseCycle("Paused because this page is hidden.");
          return;
        }
        advance();
        if (state === "running") schedule();
      }, remaining);
    }

    function advance() {
      if (completed >= entries.length) return;
      const entry = entries[completed];
      completed += 1;
      remaining = STAGE_MS;
      if (completed === entries.length) {
        state = "complete";
        cancelTimer();
        status.textContent = "3 of 3 stages complete. The resulting sample artifact is below: an authored, unreviewed proposal, not a research finding.";
      } else {
        status.textContent = `${completed} of 3 stages complete. ${entry.dataset.summary}`;
      }
      render();
    }

    function run() {
      if (state === "running" || state === "complete") return;
      if (reducedMotion.matches) {
        state = "paused";
        advance();
        return;
      }
      state = "running";
      status.textContent = `${completed} of 3 stages complete. Reading the ${["scout", "skeptic", "synthesist"][completed]}’s authored stage.`;
      render();
      schedule();
    }

    start.addEventListener("click", run);
    resume.addEventListener("click", run);
    pause.addEventListener("click", () => pauseCycle("Paused at your request."));
    stepButton.addEventListener("click", () => {
      if (state === "running" || state === "complete") return;
      cancelTimer();
      state = "paused";
      advance();
    });
    reset.addEventListener("click", () => {
      cancelTimer();
      completed = 0;
      state = "idle";
      remaining = STAGE_MS;
      status.textContent = "Reset. The demonstration has not started; no evidence has been collected.";
      render();
    });
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) pauseCycle("Paused because you left this page.");
    });
    window.addEventListener("pagehide", () => pauseCycle("Paused because you left this page."));
    reducedMotion.addEventListener("change", () => {
      if (reducedMotion.matches) pauseCycle("Paused for your reduced-motion preference.");
      render();
    });
    render();
    root.dataset.researchReady = "true";
    controls.hidden = false;
    fallback.hidden = true;
  }

  function init() {
    document.querySelectorAll("[data-reader-margin]").forEach(enhanceMargin);
    document.querySelectorAll("[data-research-study]").forEach(enhanceResearch);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
