import { normalize, tokenPattern } from "./text.js";

const embedded = document.getElementById("essay-data");
if (embedded) initializeReader(JSON.parse(embedded.textContent));

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function initializeReader(essay) {
  const byId = new Map(essay.passages.map(passage => [passage.id, passage]));
  const lens = document.getElementById("reading-lens");
  const query = document.getElementById("term-query");
  const scope = document.getElementById("term-scope");
  const status = document.getElementById("term-status");
  const results = document.getElementById("term-results");
  const inspector = document.getElementById("passage-inspector");
  let lastOpener = null;
  let selectedTerm = "";

  function readingPosition() {
    const passages = [...document.querySelectorAll("#essay-body [data-passage]")];
    const visible = passage => {
      const rect = passage.getBoundingClientRect();
      return rect.bottom > 0 && rect.top < innerHeight;
    };
    const node = passages.find(passage => `#${passage.id}` === location.hash && visible(passage))
      || passages.find(passage => visible(passage) && passage.getBoundingClientRect().top >= 0)
      || passages.find(visible);
    return node ? { node, offset: node.getBoundingClientRect().top } : null;
  }

  function restorePosition(position) {
    if (document.querySelector(".reader-composition")) return;
    if (position) requestAnimationFrame(() => {
      window.scrollBy({ top: position.node.getBoundingClientRect().top - position.offset, behavior: "instant" });
    });
  }

  function openLens(opener, focus = true) {
    const position = lens.hidden ? readingPosition() : null;
    if (opener) lastOpener = opener;
    lens.hidden = false;
    document.body.classList.add("lens-open");
    restorePosition(position);
    if (focus) query.focus({ preventScroll: true });
  }

  function clearHighlights() {
    document.querySelectorAll(".passage-text mark").forEach(mark => mark.replaceWith(...mark.childNodes));
    document.querySelectorAll(".passage-text").forEach(passage => passage.normalize());
  }

  function clearTerm(updateUrl = true) {
    selectedTerm = "";
    query.value = "";
    clearHighlights();
    results.replaceChildren();
    status.textContent = "";
    document.querySelectorAll("[data-term]").forEach(button => button.setAttribute("aria-pressed", "false"));
    if (updateUrl) {
      const url = new URL(location.href);
      url.searchParams.delete("term");
      url.searchParams.delete("section");
      history.replaceState(null, "", url);
    }
  }

  function jump(id) {
    const destination = document.getElementById(id);
    if (!destination) return;
    history.replaceState(null, "", `${location.pathname}${location.search}#${encodeURIComponent(id)}`);
    destination.scrollIntoView({ block: "start", behavior: "instant" });
    destination.focus({ preventScroll: true });
  }

  function highlightPassage(id, term) {
    const root = document.getElementById(id).querySelector(".passage-text");
    const pieces = [];
    let text = "";
    function visit(node) {
      if (node.nodeType === Node.TEXT_NODE) {
        pieces.push({ node, start: text.length, end: text.length + node.textContent.length });
        text += node.textContent;
      } else if (node.nodeName === "BR") {
        text += "\n";
      } else {
        const boundary = ["TABLE", "THEAD", "TBODY", "TR", "TD", "TH", "CAPTION"].includes(node.nodeName);
        if (boundary) text += "\n";
        node.childNodes.forEach(visit);
        if (boundary) text += "\n";
      }
    }
    visit(root);
    const matches = [...text.matchAll(tokenPattern())].filter(match => normalize(match[0]) === term);
    for (const match of matches.reverse()) {
      const start = match.index, end = start + match[0].length;
      for (const piece of [...pieces].reverse()) {
        if (piece.end <= start || piece.start >= end) continue;
        const localStart = Math.max(start, piece.start) - piece.start;
        const localEnd = Math.min(end, piece.end) - piece.start;
        const tail = piece.node.splitText(localEnd);
        const middle = piece.node.splitText(localStart);
        const mark = element("mark");
        middle.replaceWith(mark);
        mark.append(middle);
        if (!tail.textContent) tail.remove();
      }
    }
    return matches.length;
  }

  function inspect(id, opener) {
    const passage = byId.get(id);
    if (!passage) return;
    openLens(opener, false);
    inspector.hidden = false;
    document.getElementById("inspected-text").textContent = passage.kind === "table" ? `Table / ${passage.label}. Read its original rows and columns in the essay.` : passage.text;
    document.getElementById("inspector-title").textContent = passage.kind === "table" ? "A structured comparison." : "A thought in company.";
    document.getElementById("inspected-source").textContent =
      `Passage ${passage.no} / ${essay.sections.find(section => section.id === passage.section).title}`;
    const link = document.getElementById("inspected-link");
    link.href = `#${id}`;
    link.onclick = event => { event.preventDefault(); jump(id); };
    const list = document.getElementById("related-passages");
    list.replaceChildren();
    for (const match of passage.related) {
      const item = element("li");
      const title = element("a", match.title);
      title.href = match.url;
      const reason = element("small", `Shared words: ${match.shared.join(" · ")}`);
      const excerpt = element("p", match.excerpt);
      item.append(title, reason, excerpt);
      list.append(item);
    }
    if (!passage.related.length) {
      const nonProse = !["p", "li", "blockquote"].includes(passage.kind);
      list.append(element("li", nonProse ? "This is a structured passage, not continuous prose. Its words remain searchable, but it is not used for prose-neighbor suggestions." : passage.words < 20 ? "This passage is too short for a reliable vocabulary comparison. Try a longer paragraph." : "No other essay shares enough distinctive vocabulary with this passage. Not every thought needs a neighbor."));
    }
    const fixedHeaderHeight = lens.querySelector(".lens-heading").getBoundingClientRect().height;
    lens.scrollTop = Math.max(0, inspector.offsetTop - fixedHeaderHeight - 12);
    const heading = document.getElementById("inspector-title");
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
  }

  function search(updateUrl = true) {
    clearHighlights();
    results.replaceChildren();
    inspector.hidden = true;
    const term = normalize(query.value.trim());
    const pieces = [...term.matchAll(tokenPattern())];
    if (pieces.length !== 1 || pieces[0][0] !== term) {
      selectedTerm = "";
      document.querySelectorAll("[data-term]").forEach(button => button.setAttribute("aria-pressed", "false"));
      if (updateUrl) {
        const url = new URL(location.href);
        url.searchParams.delete("term");
        url.searchParams.delete("section");
        history.replaceState(null, "", url);
      }
      status.textContent = term ? "Use one complete word, including its apostrophe or hyphen if it has one. For a phrase, use the writing archive." : "Choose a word to see where it returns.";
      return;
    }
    selectedTerm = term;
    const chosenSection = essay.sections.find(section => section.id === scope.value);
    const passages = essay.passages.filter(passage => !chosenSection || passage.section === chosenSection.id);
    let total = 0, matching = 0, highlighted = 0;
    for (const passage of passages) {
      const count = passage.terms[term] || 0;
      if (!count) continue;
      total += count;
      matching++;
      highlighted += highlightPassage(passage.id, term);
      const item = element("li");
      const label = essay.sections.find(section => section.id === passage.section).title;
      const meta = element("small", `${passage.kind === "table" ? "Table p" : "P"}assage ${passage.no} · ${label} · ${count} ${count === 1 ? "occurrence" : "occurrences"}`);
      const link = element("a", passage.kind === "table" ? `${passage.label}. Open the original rows and columns ↗` : passage.text);
      link.href = `#${passage.id}`;
      link.addEventListener("click", event => { event.preventDefault(); jump(passage.id); });
      const related = element("button", "Follow this passage’s connections ↗");
      related.type = "button";
      related.addEventListener("click", () => inspect(passage.id, related));
      item.append(meta, link, related);
      results.append(item);
    }
    status.textContent = `${total} ${total === 1 ? "occurrence" : "occurrences"} of “${term}” in ${matching} ${matching === 1 ? "passage" : "passages"}${chosenSection ? ` within “${chosenSection.title}”` : " across the whole essay"}.`;
    if (highlighted !== total) {
      status.textContent += " The highlighting does not match the text index; the source counts above remain visible.";
      console.error("Text/index mismatch", { term, total, highlighted });
    }
    document.querySelectorAll("[data-term]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.term === term)));
    if (updateUrl) {
      const url = new URL(location.href);
      url.searchParams.set("term", term);
      if (chosenSection) url.searchParams.set("section", chosenSection.id);
      else url.searchParams.delete("section");
      history.replaceState(null, "", url);
    }
  }

  document.querySelectorAll(".open-lens").forEach(button => button.addEventListener("click", () => openLens(button)));
  document.querySelectorAll('a[href="#reading-lens"]').forEach(link => link.addEventListener("click", event => { event.preventDefault(); openLens(link); }));
  document.getElementById("close-lens").addEventListener("click", () => {
    const position = readingPosition();
    clearTerm();
    inspector.hidden = true;
    lens.hidden = true;
    document.body.classList.remove("lens-open");
    restorePosition(position);
    const focusTarget = lastOpener?.closest("#essay-body [data-passage]") || lastOpener;
    focusTarget?.focus({ preventScroll: true });
  });
  document.getElementById("clear-term").addEventListener("click", () => clearTerm());
  document.getElementById("term-form").addEventListener("submit", event => { event.preventDefault(); search(); });
  scope.addEventListener("change", () => { if (selectedTerm || query.value) search(); });
  document.querySelectorAll("[data-term]").forEach(button => button.addEventListener("click", () => {
    query.value = button.dataset.term;
    scope.value = "";
    search();
  }));
  document.querySelectorAll("[data-inspect]").forEach(button => button.addEventListener("click", () => inspect(button.dataset.inspect, button)));
  if (matchMedia("(max-width: 760px)").matches) document.querySelector(".contents").open = false;

  const params = new URLSearchParams(location.search);
  if (params.has("term")) {
    query.value = params.get("term").slice(0, 80);
    const section = params.get("section");
    if (essay.sections.some(item => item.id === section)) scope.value = section;
    openLens(null, false);
    search(false);
  }
  if (location.hash === "#reading-lens") openLens(null, false);
  if (document.getElementById("ai-reading-guide")) {
    initializeCompanion(essay);
    return;
  }
  const sectionNodes = essay.sections.map(section => document.getElementById(section.id)).filter(Boolean);
  const contentsLinks = [...document.querySelectorAll(".contents a")];
  let orientationQueued = false;
  function updateOrientation() {
    orientationQueued = false;
    let current = sectionNodes[0];
    for (const node of sectionNodes) {
      if (node.getBoundingClientRect().top > Math.min(140, innerHeight * .2)) break;
      current = node;
    }
    contentsLinks.forEach(link => {
      if (link.hash === `#${current.id}`) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }
  // A jump can skip every heading; font and lens reflow can also move them.
  function scheduleOrientation() {
    if (orientationQueued) return;
    orientationQueued = true;
    requestAnimationFrame(updateOrientation);
  }
  window.addEventListener("scroll", scheduleOrientation, { passive: true });
  window.addEventListener("resize", scheduleOrientation);
  new ResizeObserver(scheduleOrientation).observe(document.getElementById("essay-body"));
  scheduleOrientation();
}

function initializeCompanion(essay) {
  const body = document.getElementById("essay-body");
  const guide = document.getElementById("ai-reading-guide");
  const notes = document.getElementById("ai-reading-notes");
  const tools = document.getElementById("reader-tools");
  const composition = document.querySelector(".reader-composition");
  const panel = tools.querySelector(".reader-tools-content");
  const rails = [guide.closest(".reader-guide"), notes.closest(".reader-notes")];
  const compactProgress = tools.querySelector("[data-compact-progress]");
  const wide = matchMedia("(min-width: 1280px)");
  const sections = [...guide.querySelectorAll("[data-guide-section]")].map(item => ({
    item, link: item.querySelector("[data-guide-anchor]"), points: item.querySelector(".guide-points"),
    anchor: document.getElementById(item.querySelector("[data-guide-anchor]").dataset.guideAnchor),
  }));
  const noteNodes = [...notes.querySelectorAll("[data-note-section]")];
  const position = document.querySelector(".reading-position");
  const progress = position.querySelector("progress");
  const percent = position.querySelector("[data-reading-percent]");
  const allNotes = notes.querySelector("[data-all-notes]");
  const originalLinks = [...document.querySelectorAll(".contents a")];
  const originalSections = essay.sections.map(section => document.getElementById(section.id)).filter(Boolean);
  const manualPoints = new Map();
  let current = null;
  let showAll = false;
  let frame = null;
  let away = false;
  let restorationFrame = null;
  let interaction = 0;

  function responsive() {
    const focused = document.activeElement;
    const movedFocus = rails.some(rail => rail.contains(focused));
    for (const rail of rails) {
      if (wide.matches && rail.parentElement !== composition) composition.insertBefore(rail, body);
      else if (!wide.matches && rail.parentElement !== panel) panel.append(rail);
    }
    tools.open = false;
    guide.open = notes.open = wide.matches;
    if (movedFocus) (wide.matches ? focused : tools.querySelector(":scope > summary")).focus({ preventScroll: true });
    current = null;
    schedule();
  }
  function update() {
    frame = null;
    if (away || document.hidden) return;
    const clearance = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop);
    const rect = body.getBoundingClientRect();
    const travel = rect.height - (innerHeight - clearance);
    const value = Math.round(travel > 0 ? Math.max(0, Math.min(1, (clearance - rect.top) / travel)) * 100
      : rect.top <= clearance ? 100 : 0);
    if (progress.value !== value) progress.value = value;
    const label = `${value}%`;
    if (percent.textContent !== label) percent.textContent = label;
    if (compactProgress.textContent !== label) {
      compactProgress.textContent = label;
      compactProgress.setAttribute("aria-label", `Reading progress: ${label} through the article body`);
    }
    position.hidden = false;
    const reached = node => node.getBoundingClientRect().top <=
      clearance + parseFloat(getComputedStyle(node).scrollMarginTop) + 1;
    let selected = sections[0];
    for (const section of sections) {
      if (!reached(section.anchor)) break;
      selected = section;
    }
    if (current !== selected) {
      current = selected;
      sections.forEach(section => {
        const active = section === selected;
        section.item.dataset.active = String(active);
        if (active) section.link.setAttribute("aria-current", "location");
        else section.link.removeAttribute("aria-current");
        if (wide.matches && !manualPoints.has(section.points) && !section.points.contains(document.activeElement))
          section.points.open = active;
      });
      renderNotes();
    }
    let original = originalSections[0];
    for (const node of originalSections) {
      if (!reached(node)) break;
      original = node;
    }
    originalLinks.forEach(link => {
      if (link.hash === `#${original.id}`) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }
  function renderNotes() {
    notes.dataset.noteMode = showAll ? "all" : "current";
    const id = current.item.dataset.guideSection;
    let count = 0;
    noteNodes.forEach(note => {
      note.hidden = !showAll && note.dataset.noteSection !== id;
      if (!note.hidden) count++;
    });
    notes.querySelector("[data-current-section]").textContent = showAll ? "All sections" : current.link.textContent.trim().replace(/^\d+\s*/, "");
    notes.querySelector(".reader-note-empty").hidden = count > 0;
    allNotes.setAttribute("aria-pressed", String(showAll));
    allNotes.textContent = showAll ? "Follow the current section" : "Show all AI notes";
  }
  function schedule() {
    if (frame !== null || away || document.hidden) return;
    frame = requestAnimationFrame(update);
  }
  function suspend() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
  }
  function cancelRestoration() {
    if (restorationFrame !== null) cancelAnimationFrame(restorationFrame);
    restorationFrame = null;
  }
  function rememberPosition() {
    const state = history.state && typeof history.state === "object" ? history.state : {};
    history.replaceState({ ...state, readerPosition: { url: location.href, y: scrollY } }, "");
  }
  function restoreHistory(event) {
    cancelRestoration();
    const intent = ++interaction;
    away = false;
    schedule();
    const saved = history.state?.readerPosition;
    const returning = event.persisted || performance.getEntriesByType("navigation")[0]?.type === "back_forward";
    if (!returning || saved?.url !== location.href || !Number.isFinite(saved.y) || saved.y < 0) return;
    // WebKit can restore scroll, then reapply the old fragment during load.
    // Restore once after fonts and the browser's return frame, unless the user acts.
    document.fonts.ready.then(() => {
      if (away || document.hidden || interaction !== intent) return;
      restorationFrame = requestAnimationFrame(() => {
        restorationFrame = requestAnimationFrame(() => {
          restorationFrame = null;
          if (!away && !document.hidden && interaction === intent && Math.abs(scrollY - saved.y) > 1)
            window.scrollTo({ top: saved.y, behavior: "instant" });
        });
      });
    });
  }
  sections.forEach(section => section.points.querySelector("summary").addEventListener("click", () => {
    manualPoints.set(section.points, !section.points.open);
  }));
  allNotes.addEventListener("click", () => {
    showAll = !showAll;
    if (current) renderNotes();
  });
  document.querySelector("[data-passage-toggle]").addEventListener("change", event => {
    document.body.classList.toggle("show-passage-tools", event.target.checked);
  });
  for (const rail of [guide, notes]) {
    rail.addEventListener("toggle", schedule, true);
    rail.addEventListener("click", event => {
      const link = event.target.closest('a[href^="#"]');
      if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      if (!wide.matches) tools.open = false;
      document.getElementById(link.hash.slice(1))?.focus({ preventScroll: true });
    });
  }
  tools.addEventListener("keydown", event => {
    if (event.key === "Escape" && !wide.matches && tools.open) {
      tools.open = false;
      tools.querySelector(":scope > summary").focus({ preventScroll: true });
    }
  });
  document.querySelector(".open-lens").addEventListener("click", () => {
    if (!wide.matches) tools.open = false;
  });
  window.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", schedule);
  window.addEventListener("hashchange", schedule);
  window.addEventListener("popstate", schedule);
  window.addEventListener("pagehide", () => { rememberPosition(); interaction++; away = true; suspend(); cancelRestoration(); });
  window.addEventListener("pageshow", restoreHistory);
  for (const type of ["pointerdown", "keydown", "wheel", "touchstart"]) {
    window.addEventListener(type, () => { interaction++; cancelRestoration(); }, { passive: true });
  }
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { interaction++; suspend(); cancelRestoration(); }
    else schedule();
  });
  wide.addEventListener("change", responsive);
  new ResizeObserver(schedule).observe(body);
  document.fonts.ready.then(schedule);
  responsive();
}
