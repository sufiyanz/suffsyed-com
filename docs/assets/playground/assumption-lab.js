import { element, control, applyPreferences } from "./code-dom.js";
import { calculateModel, SCENARIOS } from "./code-model.js";

const format = (value) => value.toFixed(1);
const svgElement = (tag, attributes) => {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
  return node;
};

export async function mount(root, context) {
  let active = false, destroyed = false;
  let assumptions = { ...SCENARIOS[0] };
  const listeners = new AbortController();
  const shell = element("section", "code-model-shell");
  const heading = element("header", "code-model-heading");
  heading.append(element("h3", "", "What changes when intelligence becomes cheap?"),
    element("p", "pg-help", "An authored toy model, not a forecast. No AI calls."));
  const pocket = element("div", "code-model-pocket");
  const pocketText = element("p");
  const pocketBar = element("span", "code-model-pocket-bar");
  const pocketFill = element("span");
  pocketBar.setAttribute("aria-hidden", "true");
  pocketBar.append(pocketFill);
  pocket.append(pocketText, pocketBar);
  const body = element("div", "code-model-body");
  const inputs = element("div", "code-model-inputs");
  const controls = element("div", "pg-controls code-model-controls");
  const scenario = element("select", "pg-field");
  scenario.setAttribute("aria-label", "Assumption example");
  for (const [index, preset] of SCENARIOS.entries()) {
    const option = element("option", "", preset.name);
    option.value = String(index); scenario.append(option);
  }
  const custom = element("option", "", "Your assumptions");
  custom.value = "custom"; custom.disabled = true; scenario.append(custom);
  const reset = control("Reset", "reset");
  controls.append(scenario, reset);
  inputs.append(controls);
  const fields = [
    { key: "cost", label: "Cost of intelligence", unit: "% of manual task cost", low: 1, first: "1% of manual cost", last: "Parity" },
    { key: "automation", label: "Tasks automated", unit: "of 100 tasks", low: 0, first: "Human-led", last: "Machine-led" },
    { key: "supervision", label: "Human supervision", unit: "% of automated tasks reviewed", low: 0, first: "Hands off", last: "Every task" },
  ].map((field) => {
    const label = element("label", "code-model-field");
    const row = element("span", "code-model-label");
    const output = element("output");
    row.append(element("span", "", field.label), output);
    const input = element("input", "pg-field");
    input.type = "range"; input.min = String(field.low); input.max = "100"; input.step = "1";
    input.dataset.assumption = field.key;
    input.setAttribute("aria-label", field.label);
    const ends = element("span", "code-model-ends");
    ends.append(element("span", "", field.first), element("span", "", field.last));
    label.append(row, input, ends);
    inputs.append(label);
    return { ...field, input, output };
  });
  const results = element("div", "pg-stage code-model-results");
  results.append(element("p", "code-model-kicker", "ONE BATCH / 100 TASKS"));
  const headline = element("p", "code-model-headline");
  results.append(headline);
  const chart = element("figure", "code-model-chart");
  chart.append(element("figcaption", "", "Cost ledger / human-hour equivalents"));
  const graphic = svgElement("svg", { viewBox: "0 0 300 66", preserveAspectRatio: "none", "aria-hidden": "true", focusable: "false" });
  const track = svgElement("rect", { x: 0, y: 8, width: 300, height: 18, class: "code-model-track" });
  const manualBar = svgElement("rect", { x: 0, y: 8, width: 0, height: 18, class: "code-model-manual" });
  const reviewBar = svgElement("rect", { x: 0, y: 8, width: 0, height: 18, class: "code-model-review" });
  const machineBar = svgElement("rect", { x: 0, y: 8, width: 0, height: 18, class: "code-model-machine" });
  const baseline = svgElement("line", { x1: 240, x2: 240, y1: 1, y2: 35, class: "code-model-baseline" });
  const baselineBar = svgElement("rect", { x: 0, y: 44, width: 240, height: 8, class: "code-model-reference" });
  graphic.append(track, manualBar, reviewBar, machineBar, baseline, baselineBar);
  chart.append(graphic);
  const legend = element("div", "code-model-legend");
  const entries = ["Manual", "Review", "Machine"].map((text, index) => {
    const item = element("span", `code-model-key code-model-key-${index}`);
    const value = element("span"); item.append(element("i"), value); legend.append(item);
    return { text, value };
  });
  chart.append(legend, element("p", "code-model-reference-label", "Reference: all-human batch = 100. Scale: 0-125."));
  results.append(chart);
  const metrics = element("dl", "code-model-metrics");
  const metricFields = [
    ["humanHours", "Human hours", "manual work + review"],
    ["unreviewed", "Unreviewed tasks", "automated, not checked"],
    ["defects", "Defect allowance", "toy expected count, not observed"],
  ].map(([key, label, note]) => {
    const item = element("div");
    const value = element("dd");
    value.dataset.metric = key;
    item.append(element("dt", "", label), value, element("small", "", note));
    metrics.append(item);
    return { key, value };
  });
  results.append(metrics);
  const interpretation = element("p", "code-model-interpretation");
  results.append(interpretation);
  body.append(inputs, results);
  const errorBox = element("p", "code-model-error"); errorBox.hidden = true;
  const guide = element("details", "code-model-guide");
  guide.append(element("summary", "", "Open the model / formulas & caveats"));
  guide.append(element("p", "", "Imagine 100 equal tasks. Each manual task takes 1 hour and costs 1 unit. Machine cost is a percentage of that manual cost, not a measured price. Every reviewed machine task adds 0.25 human hours. Lower machine prices do not automatically raise automation here: move both assumptions yourself."));
  guide.append(element("pre", "", `A = tasks automated (0-100)
S = supervision / 100
C = machine cost / 100 (0.01-1)
Manual hours = 100 - A
Review hours = A * S * 0.25
Machine cost = A * C
Total cost = manual + review + machine
Unreviewed = A * (1 - S)
Defect allowance = A * ((1 - S) * 0.20 + S * 0.04)`));
  guide.append(element("p", "", "The 20% unreviewed and 4% reviewed defect rates are invented constants, not evidence. Manual work is assumed defect-free to keep this particular comparison simple. Fractions are expected counts in this toy arithmetic, not partial real tasks. The cost ledger excludes defect repair, setup, training, demand, wages and displacement. No scientific validation or forecast is implied."));
  guide.append(element("p", "", "What the model makes visible: cheaper machine work lowers its bill, not its errors; more automation frees manual time but increases exposure to the assumed defects; more review reduces that exposure but uses human time. All settings disappear when you leave."));
  shell.append(heading, pocket, body, errorBox, guide);

  function report(error) {
    const message = `The model could not update: ${error.message}`;
    errorBox.textContent = message; errorBox.hidden = false;
    context.reportError(message, error);
  }
  function render() {
    const result = calculateModel(assumptions);
    pocketText.textContent = `${format(result.totalCost)} cost units / ${format(result.defects)} toy defects`;
    pocketFill.style.width = `${result.totalCost / 125 * 100}%`;
    for (const field of fields) {
      field.input.value = String(assumptions[field.key]);
      field.output.textContent = field.key === "automation" ? `${assumptions[field.key]} / 100` : `${assumptions[field.key]}%`;
      field.input.setAttribute("aria-valuetext", `${assumptions[field.key]} ${field.unit}`);
    }
    headline.replaceChildren(element("strong", "", format(result.totalCost)),
      element("span", "", `cost units / ${format(Math.abs(result.savings))}% ${result.savings >= 0 ? "below" : "above"} the all-human reference`));
    const scale = 300 / 125;
    manualBar.setAttribute("width", String(result.manual * scale));
    reviewBar.setAttribute("x", String(result.manual * scale));
    reviewBar.setAttribute("width", String(result.reviewHours * scale));
    machineBar.setAttribute("x", String((result.manual + result.reviewHours) * scale));
    machineBar.setAttribute("width", String(result.machineCost * scale));
    [result.manual, result.reviewHours, result.machineCost].forEach((value, index) => {
      entries[index].value.textContent = `${entries[index].text} ${format(value)}`;
    });
    for (const metric of metricFields) metric.value.textContent = format(result[metric.key]);
    interpretation.textContent = result.automated === 0
      ? "All work stays human in this scenario. Machine cost and review settings have no effect until you automate tasks."
      : `Review uses ${format(result.reviewHours)} hours and reduces the invented defect allowance from ${format(result.automated * 0.20)} to ${format(result.defects)} tasks. Cheaper intelligence alone does not change that allowance.`;
    errorBox.hidden = true;
  }
  function update(next, announce) {
    if (destroyed || !active) return;
    try {
      calculateModel(next);
      assumptions = next;
      render();
      if (announce) context.setStatus(announce);
    } catch (error) { report(error); }
  }
  function destroy() {
    if (destroyed) return;
    destroyed = true; active = false;
    listeners.abort();
    context.signal.removeEventListener("abort", destroy);
    assumptions = null;
    root.replaceChildren();
  }
  const controller = {
    setActive(value) {
      if (destroyed) return;
      active = Boolean(value);
      for (const field of fields) field.input.disabled = !active;
      scenario.disabled = !active; reset.disabled = !active;
    },
    resize(value) {
      if (destroyed) return;
      if (![value.width, value.height, value.dpr].every(Number.isFinite) || value.width < 0 || value.height < 0 || value.dpr <= 0) {
        report(new RangeError("Preview dimensions must be finite and non-negative.")); return;
      }
      root.dataset.codeCompact = String(value.width < 580);
    },
    setPreferences(value) { if (!destroyed) applyPreferences(root, value); },
    destroy,
  };
  context.signal.addEventListener("abort", destroy, { once: true });
  if (context.signal.aborted) { destroy(); return controller; }
  root.replaceChildren(shell);
  root.dataset.codeCompact = String(root.clientWidth < 580);
  applyPreferences(root, context.preferences);
  for (const field of fields) {
    field.input.addEventListener("input", () => {
      if (!active || destroyed) return;
      scenario.value = "custom";
      update({ ...assumptions, [field.key]: Number(field.input.value) });
    }, { signal: listeners.signal });
    field.input.addEventListener("change", () => {
      if (active && !destroyed) context.setStatus(`${field.label}: ${field.input.getAttribute("aria-valuetext")}. Model updated.`);
    }, { signal: listeners.signal });
  }
  scenario.addEventListener("change", () => {
    if (scenario.value !== "custom") update({ ...SCENARIOS[Number(scenario.value)] }, "Assumption example loaded.");
  }, { signal: listeners.signal });
  reset.addEventListener("click", () => {
    if (!active || destroyed) return;
    scenario.value = "0"; update({ ...SCENARIOS[0] }, "Assumptions reset to Shared work.");
  }, { signal: listeners.signal });
  controller.setActive(false);
  try { render(); } catch (error) { report(error); }
  try { await document.fonts.ready; } catch (error) {
    if (!context.signal.aborted && !destroyed) report(error);
    return controller;
  }
  if (context.signal.aborted || destroyed) { destroy(); return controller; }
  return controller;
}
