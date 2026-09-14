const NS = "http://www.w3.org/2000/svg";
const MAPPED_ESSAYS = 5;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function button(text, action, className = "") {
  const node = element("button", className, text);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}

function link(text, href, className = "") {
  const node = element("a", className, text);
  node.href = href;
  return node;
}

export function mountAtlas(root, mount) {
  // The server-rendered index is the only text model; no second corpus payload.
  const questions = [...root.querySelectorAll("[data-atlas-question]")].map(group => ({
    id: group.dataset.atlasQuestion,
    anchor: group.id,
    name: group.querySelector("[data-atlas-theme]").textContent,
    label: group.querySelector("h3").textContent,
    entries: [...group.querySelectorAll("[data-atlas-entry]")].map(entry => ({
      id: entry.dataset.atlasEntry,
      number: entry.dataset.number,
      title: entry.querySelector(".atlas-essay-title").textContent,
      note: entry.querySelector(".atlas-source-note").textContent,
      text: entry.querySelector("blockquote").textContent,
      href: entry.querySelector(".atlas-context").getAttribute("href"),
    })),
  }));
  const bridges = [...root.querySelectorAll("[data-atlas-bridge]")].map(bridge => ({
    id: bridge.dataset.atlasBridge,
    from: bridge.dataset.from,
    to: bridge.dataset.to,
    label: bridge.querySelector("h4").textContent,
    reason: bridge.querySelector(".atlas-reason").textContent,
    sources: [...bridge.querySelectorAll("[data-source-slug]")].map(source => source.dataset.sourceSlug),
  }));
  if (questions.length !== 5 || bridges.length !== 4 || questions.some(q => !q.entries.length)) {
    throw new Error("The question index does not match the bounded atlas model.");
  }
  const questionById = new Map(questions.map(q => [q.id, q]));
  const entryById = new Map(questions.flatMap(q => q.entries.map(entry => [entry.id, entry])));
  if (bridges.some(b => !questionById.has(b.from) || !questionById.has(b.to)
    || b.sources.length !== 2 || b.sources.some(id => !entryById.has(id)))) {
    throw new Error("The atlas is missing a bridge source.");
  }
  const nearby = id => bridges.filter(b => b.from === id || b.to === id);
  if (questions.some(q => nearby(q.id).length > 2)) throw new Error("Too many neighboring questions.");
  const other = (bridge, id) => questionById.get(bridge.from === id ? bridge.to : bridge.from);
  const order = [];
  let current = questions.find(q => nearby(q.id).length === 1);
  while (current && !order.includes(current.id)) {
    order.push(current.id);
    current = nearby(current.id).map(b => other(b, current.id)).find(q => !order.includes(q.id));
  }
  if (order.length !== 5) throw new Error("The four bridges must connect all five questions.");

  const shell = element("div", "atlas-interactive");
  const toolbar = element("div", "atlas-toolbar");
  const overview = button("All five questions", () => showOverview(true), "atlas-overview");
  const textIndex = link("Use the text index ↓", "#theme-1", "atlas-text-link");
  const position = element("span", "label atlas-position", "01—05 / The overview");
  toolbar.append(overview, position, textIndex);
  const legend = element("p", "atlas-legend");
  legend.append(element("span", "atlas-legend-member", "Essay in an editorial theme"),
    element("span", "atlas-legend-bridge", "Curated bridge / two sources"));
  const guide = element("details", "atlas-map-guide");
  guide.append(element("summary", "", "How to read this map"), legend,
    element("p", "", "The questions are editorial index labels, not quotations. Essay groupings come from the archive; bridges are curated comparisons with two source passages, not agreement or evidence. Position, size and distance are not measurements. Quoted claims remain the original essays’ arguments, not newly verified findings."),
    link("Read the full method ↗", "/methods/#question-atlas"));
  const coverage = element("p", "atlas-coverage");
  coverage.hidden = true;
  const graph = element("div", "atlas-graph");
  graph.setAttribute("role", "group");
  graph.setAttribute("aria-label", "Question map. Native buttons also work with Tab and Enter or Space.");
  const lines = document.createElementNS(NS, "svg");
  lines.classList.add("atlas-lines");
  lines.setAttribute("aria-hidden", "true");
  lines.setAttribute("focusable", "false");
  const nodes = element("div", "atlas-nodes");
  graph.append(lines, nodes);
  const detail = element("section", "atlas-detail");
  detail.setAttribute("aria-labelledby", "atlas-detail-title");
  const status = element("p", "sr-only");
  status.setAttribute("role", "status");
  status.setAttribute("aria-atomic", "true");
  shell.append(toolbar, coverage, graph, guide, detail, status);

  let selected = null;
  let active = false;
  let frame = null;
  let edges = [];
  let nodeById = new Map();
  const compact = window.matchMedia("(max-width: 700px)");

  function schedule() {
    if (active && frame === null) frame = requestAnimationFrame(drawLines);
  }

  function drawLines() {
    frame = null;
    if (!active) return;
    const box = graph.getBoundingClientRect();
    if (!box.width || !box.height) return;
    lines.setAttribute("viewBox", `0 0 ${box.width} ${box.height}`);
    const paths = edges.map(edge => {
      const left = nodeById.get(edge.from).getBoundingClientRect();
      const right = nodeById.get(edge.to).getBoundingClientRect();
      const sx = left.x - box.x + left.width / 2;
      const sy = left.y - box.y + left.height / 2;
      const tx = right.x - box.x + right.width / 2;
      const ty = right.y - box.y + right.height / 2;
      const path = document.createElementNS(NS, "path");
      const gutter = compact.matches ? 12 : (sx + tx) / 2;
      path.setAttribute("d", compact.matches
        ? `M${sx},${sy}H${gutter}V${ty}H${tx}`
        : `M${sx},${sy}C${gutter},${sy} ${gutter},${ty} ${tx},${ty}`);
      path.setAttribute("class", edge.kind === "bridge" ? "atlas-edge-bridge" : "atlas-edge-member");
      return path;
    });
    lines.replaceChildren(...paths);
  }

  function graphNode(id, kind, kicker, title, action) {
    const node = button("", action, `atlas-node atlas-node-${kind}`);
    node.dataset.atlasNode = id;
    node.dataset.nodeKind = kind;
    node.append(element("span", "atlas-node-kicker", kicker),
      element("span", "atlas-node-title", title),
      element("span", "atlas-node-arrow", "↗"));
    node.querySelector(".atlas-node-arrow").setAttribute("aria-hidden", "true");
    nodeById.set(id, node);
    return node;
  }

  function resetGraph(mode) {
    graph.dataset.view = mode;
    nodeById = new Map();
    edges = [];
    nodes.replaceChildren();
    lines.replaceChildren();
  }

  function heading(kicker, title) {
    detail.replaceChildren(element("p", "label", kicker));
    const h = element("h3", "", title);
    h.id = "atlas-detail-title";
    h.tabIndex = -1;
    detail.append(h);
    return h;
  }

  function announce(message) {
    status.textContent = message;
  }

  function focusDetail() {
    const title = detail.querySelector("h3");
    title.focus({ preventScroll: true });
    // Align the reading surface, not just its heading; native scroll padding keeps clearance.
    detail.scrollIntoView({ block: "start", behavior: "instant" });
  }

  function focusGraph(node) {
    node.focus({ preventScroll: true });
    graph.scrollIntoView({ block: "start", behavior: "instant" });
  }

  function quote(entry) {
    const section = element("div", "atlas-quoted-source");
    const block = element("blockquote", "", entry.text);
    block.cite = entry.href;
    section.append(element("p", "atlas-source-note", entry.note),
      block, link("Read in the original essay ↗", entry.href, "atlas-context"));
    return section;
  }

  function questionDetail(question, focus = false) {
    for (const node of nodeById.values()) node.removeAttribute("aria-pressed");
    heading("Editorial index question / " + question.name, question.label);
    detail.append(element("p", "atlas-detail-intro",
      `All ${question.entries.length} essays in the archive’s existing ${question.name} grouping. Choose an essay to read a complete source passage, or inspect a bridge below. Map selection does not filter the archive or the text index.`));
    const essayList = element("div", "atlas-detail-essays");
    for (const entry of question.entries) {
      const choice = button(entry.title, () => selectEssay(question, entry, true), "atlas-detail-essay");
      choice.dataset.atlasDetailEntry = entry.id;
      essayList.append(choice);
    }
    detail.append(essayList);
    const connections = element("div", "atlas-nearby");
    connections.append(element("p", "label", "A question in company"));
    for (const bridge of nearby(question.id)) {
      const target = other(bridge, question.id);
      connections.append(button(`${bridge.label} / ${target.name}`, () => bridgeDetail(bridge, true), "atlas-bridge-button"));
    }
    detail.append(connections, link("Read this question in the text index ↓", `#${question.anchor}`, "atlas-context"));
    if (focus) focusDetail();
  }

  function showOverview(focus = false) {
    selected = null;
    coverage.hidden = true;
    overview.disabled = true;
    position.textContent = "01—05 / The overview";
    textIndex.href = "#theme-1";
    resetGraph("overview");
    // An editorial reading route, not a ranking or a force-directed embedding.
    for (const id of order) {
      const question = questionById.get(id);
      const node = graphNode(id, "question", `${question.name} / ${question.entries.length} essays`, question.label,
        () => showQuestion(question, true));
      nodes.append(node);
    }
    edges = bridges.map(b => ({ from: b.from, to: b.to, kind: "bridge" }));
    heading("A reading route, not a verdict", "Where would you begin?");
    detail.append(element("p", "atlas-detail-intro",
      "Five questions recur across the collection. The map offers four deliberately chosen bridges between them. Open a question to see the essays around it; every passage has an address."),
    element("p", "micro", "Position, distance and size do not measure importance, similarity or certainty."));
    announce("Overview. Five editorial questions and four curated bridges.");
    schedule();
    if (focus) focusGraph(nodeById.get(order[0]));
  }

  function showQuestion(question, focus = false) {
    selected = question;
    coverage.hidden = question.entries.length <= MAPPED_ESSAYS;
    coverage.textContent = `${MAPPED_ESSAYS} of ${question.entries.length} essays mapped; all ${question.entries.length} in the index and detail list below.`;
    overview.disabled = false;
    position.textContent = question.name + " / A neighborhood";
    textIndex.href = `#${question.anchor}`;
    resetGraph("question");
    const center = graphNode(question.id, "selected", "The question / editorial index", question.label,
      () => questionDetail(question, true));
    nodes.append(center);
    const essays = element("div", "atlas-essay-nodes");
    for (const entry of question.entries.slice(0, MAPPED_ESSAYS)) {
      essays.append(graphNode(entry.id, "essay", `Essay ${entry.number} / read a passage`, entry.title,
        () => selectEssay(question, entry, true)));
      edges.push({ from: question.id, to: entry.id, kind: "member" });
    }
    nodes.append(essays);
    const neighbors = element("div", "atlas-neighbor-nodes");
    for (const bridge of nearby(question.id)) {
      const target = other(bridge, question.id);
      neighbors.append(graphNode(target.id, "neighbor", `Curated bridge / ${bridge.label}`, target.label,
        () => bridgeDetail(bridge, true)));
      edges.push({ from: question.id, to: target.id, kind: "bridge" });
    }
    nodes.append(neighbors);
    questionDetail(question);
    announce(`${question.name}. ${question.entries.length} essays and ${nearby(question.id).length} curated bridges.${coverage.hidden ? "" : " " + coverage.textContent}`);
    schedule();
    if (focus) focusGraph(center);
  }

  function selectEssay(question, entry, focus = false) {
    for (const node of nodeById.values()) node.removeAttribute("aria-pressed");
    nodeById.get(entry.id)?.setAttribute("aria-pressed", "true");
    heading(`Essay ${entry.number} / ${question.name}`, entry.title);
    const note = "A curated entry point, not a summary. The complete original passage follows."
      + (nodeById.has(entry.id) ? "" : " This essay is in the full index, not one of the five mapped nodes.");
    detail.append(element("p", "atlas-detail-intro", note),
      quote(entry), button("Back to this question", () => questionDetail(question, true), "plain"));
    announce(`${entry.title}. Original source passage selected.`);
    if (focus) focusDetail();
  }

  function bridgeDetail(bridge, focus = false) {
    for (const node of nodeById.values()) node.removeAttribute("aria-pressed");
    heading("Curated bridge / Two source passages", bridge.label);
    detail.append(element("p", "atlas-detail-intro", bridge.reason));
    const pair = element("div", "atlas-source-pair");
    for (const id of bridge.sources) {
      const entry = entryById.get(id);
      const section = element("section");
      section.append(element("h4", "", entry.title), quote(entry));
      pair.append(section);
    }
    detail.append(pair);
    const destination = other(bridge, selected.id);
    const next = button(`Follow to ${destination.name} ↗`, () => showQuestion(destination, true), "atlas-follow");
    next.dataset.atlasFollow = destination.id;
    detail.append(next, button("Back to this question", () => questionDetail(selected, true), "plain"));
    announce(`${bridge.label}. Curated comparison with two original passages.`);
    if (focus) focusDetail();
  }

  const resize = "ResizeObserver" in window ? new ResizeObserver(schedule) : null;
  function setActive(value) {
    if (active === value) return;
    active = value;
    if (active) {
      resize?.observe(graph);
      window.addEventListener("resize", schedule);
      schedule();
    } else {
      resize?.disconnect();
      window.removeEventListener("resize", schedule);
      if (frame !== null) cancelAnimationFrame(frame);
      frame = null;
    }
  }
  mount.replaceChildren(shell);
  showOverview();
  document.fonts?.ready.then(schedule);
  return { setActive };
}
