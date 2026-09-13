const root = document.querySelector("[data-home-root]");
const dataElement = document.getElementById("home-data");

if (root && dataElement) {
  let data;
  try {
    data = JSON.parse(dataElement.textContent);
  } catch {
    // The complete server-rendered reading path remains available.
  }
  if (data && Array.isArray(data.themes) && Array.isArray(data.essays)) {
    enhanceHome(root, data);
  }
}

function enhanceHome(root, data) {
  const find = (name) => root.querySelector(`[data-home-${name}]`);
  const { themes, essays, initial } = data;
  const groups = themes.map((theme) => essays.filter((essay) => essay.theme === theme.name));
  const templates = themes.map((_, index) => document.getElementById(`home-plate-${index}`));
  if (!initial || !groups[initial.theme]?.[initial.essay] || templates.some((template) => !template)) return;

  const svgNamespace = "http://www.w3.org/2000/svg";
  const format = new Intl.NumberFormat("en-US");
  let activeTheme = initial.theme;
  let selectedIndex = initial.essay;
  const remembered = new Map([[activeTheme, selectedIndex]]);
  const themeButtons = [];
  const themeOptions = find("theme-options");
  const themeDisclosure = find("theme-selector");
  const narrowThemes = window.matchMedia("(max-width: 580px)");
  function sizeThemeSelector() {
    themeDisclosure.open = !narrowThemes.matches;
    if (narrowThemes.matches && themeDisclosure.contains(document.activeElement)) {
      themeDisclosure.querySelector("summary").focus({ preventScroll: true });
    }
  }
  sizeThemeSelector();
  narrowThemes.addEventListener("change", sizeThemeSelector);

  themeOptions.setAttribute("role", "group");
  for (const link of themeOptions.querySelectorAll("[data-home-theme]")) {
    const index = Number(link.dataset.homeTheme);
    if (!groups[index].length) continue;
    const button = document.createElement("button");
    button.type = "button";
    button.className = link.className;
    button.dataset.homeTheme = String(index);
    button.style.setProperty("--tone", themes[index].band);
    button.setAttribute("aria-pressed", String(index === activeTheme));
    button.append(...link.childNodes);
    button.addEventListener("click", () => {
      select(index, remembered.get(index) ?? 0, true, true);
      if (narrowThemes.matches) {
        themeDisclosure.open = false;
        themeDisclosure.querySelector("summary").focus({ preventScroll: true });
      }
    });
    link.replaceWith(button);
    themeButtons.push(button);
  }
  find("theme-help").textContent = "Select a pattern. The drawing, artwork, and reading path change together.";

  function updateBars(essay, count) {
    const drawing = find("drawing");
    const bars = Math.ceil(essay.words / 100);
    const spacing = Math.min(11, 190 / Math.max(1, bars - 1));
    const fragment = document.createDocumentFragment();
    for (let index = 0; index < bars; index += 1) {
      const path = document.createElementNS(svgNamespace, "path");
      path.classList.add("word-bar");
      path.setAttribute("d", `M${(190 + index * spacing).toFixed(2)} 47V107`);
      path.setAttribute("stroke", "var(--cp-text)");
      path.setAttribute("stroke-width", index % 5 === 4 ? "2.2" : ".8");
      fragment.append(path);
    }
    drawing.querySelector("[data-word-bars]").replaceChildren(fragment);
    drawing.querySelector("[data-word-label]").textContent = `${format.format(essay.words)} words`;
    drawing.querySelector("[data-drawing-description]").textContent =
      `${count} essays form this theme. The selected essay contains ${format.format(essay.words)} words, ` +
      `represented by ${bars} bars, rounded up to hundreds. The ${count}-lobed face follows the essay count. ` +
      "Fine lines and the gently moving rings are expressive, not measured evidence.";
  }

  function makeIndex(items) {
    const fragment = document.createDocumentFragment();
    items.forEach((essay, index) => {
      const li = document.createElement("li");
      li.dataset.essayIndex = String(index);
      const link = document.createElement("a");
      link.href = essay.url;
      const number = document.createElement("span");
      number.className = "index-number";
      number.textContent = essay.no;
      const title = document.createElement("span");
      title.textContent = essay.title;
      link.append(number, title);
      const preview = document.createElement("button");
      preview.type = "button";
      preview.className = "home-preview";
      preview.dataset.preview = String(index);
      preview.setAttribute("aria-label", `Preview ${essay.title} in the plate`);
      preview.textContent = "Preview";
      li.append(link, preview);
      fragment.append(li);
    });
    find("index").replaceChildren(fragment);
  }

  function updateURL(index) {
    const url = new URL(window.location.href);
    url.searchParams.set("theme", themes[index].id);
    try {
      window.history.replaceState(window.history.state, "", url);
    } catch {
      // Selection also works in file previews with restricted history APIs.
    }
  }

  function select(index, essayIndex = 0, announce = true, changeURL = false) {
    const items = groups[index];
    const essay = items?.[essayIndex];
    if (!essay) return;
    const changedTheme = index !== activeTheme;
    activeTheme = index;
    selectedIndex = essayIndex;
    remembered.set(index, essayIndex);
    const theme = themes[index];
    find("current-theme").textContent = theme.name;

    if (changedTheme) {
      find("drawing").replaceChildren(templates[index].content.cloneNode(true));
      makeIndex(items);
    }
    updateBars(essay, items.length);
    find("plate-label").textContent = `Plate ${String(index + 1).padStart(2, "0")} / ${theme.name}`;
    find("count").textContent = `${format.format(items.reduce((sum, item) => sum + item.words, 0))} words across this theme.`;
    find("position").textContent = `${essayIndex + 1} / ${items.length}`;
    const cover = find("cover");
    const artwork = find("artwork");
    const caption = `Original cover illustration for ${essay.title}`;
    artwork.hidden = !essay.cover;
    artwork.href = essay.cover || "#reading";
    artwork.dataset.artwork = essay.cover;
    artwork.dataset.caption = caption;
    artwork.setAttribute("aria-label", `Inspect original cover illustration for ${essay.title}`);
    cover.alt = essay.coverAlt || caption;
    if (essay.cover) {
      cover.srcset = essay.srcset;
      cover.src = essay.cover;
    } else {
      cover.removeAttribute("src");
      cover.removeAttribute("srcset");
    }
    find("title").textContent = essay.title;
    find("title").href = essay.url;
    find("selection-title").textContent = essay.title;
    root.querySelectorAll("[data-home-selection-link]").forEach((link) => {
      link.href = essay.url;
    });
    find("excerpt").textContent = essay.excerpt;
    find("essay-link").href = essay.url;
    find("length").textContent = `${format.format(essay.words)} words; ${essay.minutes} minute read.`;
    find("browse").hidden = items.length < 2;
    find("index-description").textContent = `${items.length} ${items.length === 1 ? "essay" : "essays"} in ${theme.name}.`;
    find("archive").href = theme.archive;
    themeButtons.forEach((button) => {
      button.setAttribute("aria-pressed", String(Number(button.dataset.homeTheme) === index));
    });
    for (const button of find("index").querySelectorAll("[data-preview]")) {
      button.hidden = false;
      button.setAttribute("aria-pressed", String(Number(button.dataset.preview) === essayIndex));
    }
    const swatches = document.createDocumentFragment();
    for (const color of [theme.band, theme.second, theme.edge]) {
      const swatch = document.createElement("span");
      swatch.style.setProperty("--swatch", color);
      swatches.append(swatch);
    }
    find("swatches").replaceChildren(swatches);
    if (changeURL) updateURL(index);
    if (announce) {
      find("status").textContent =
        `${theme.name}. Essay ${essayIndex + 1} of ${items.length}: ${essay.title}. ` +
        `${format.format(essay.words)} words; ${Math.ceil(essay.words / 100)} length bars.`;
    }
  }

  find("index").addEventListener("click", (event) => {
    const preview = event.target.closest("[data-preview]");
    if (preview) select(activeTheme, Number(preview.dataset.preview));
  });
  find("previous").addEventListener("click", () => {
    const count = groups[activeTheme].length;
    select(activeTheme, (selectedIndex - 1 + count) % count);
  });
  find("next").addEventListener("click", () => {
    select(activeTheme, (selectedIndex + 1) % groups[activeTheme].length);
  });

  function restoreTheme(announce = false) {
    const requested = new URL(window.location.href).searchParams.get("theme");
    const index = themes.findIndex((theme) => theme.id === requested);
    const target = index >= 0 && groups[index].length ? index : initial.theme;
    select(target, remembered.get(target) ?? 0, announce);
  }
  restoreTheme();
  window.addEventListener("popstate", () => restoreTheme(true));

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const motionButton = find("motion");
  const instrument = root.querySelector(".instrument");
  let paused = false;
  let visible = false;
  function updateMotion() {
    root.dataset.motion = !paused && !reducedMotion.matches && !document.hidden && visible ? "running" : "paused";
    motionButton.hidden = reducedMotion.matches;
    motionButton.setAttribute("aria-pressed", String(paused));
    motionButton.textContent = paused ? "Resume the motion" : "Pause the motion";
  }
  motionButton.addEventListener("click", () => {
    paused = !paused;
    updateMotion();
  });
  document.addEventListener("visibilitychange", updateMotion);
  reducedMotion.addEventListener("change", updateMotion);
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      updateMotion();
    }, { threshold: 0.05 });
    observer.observe(instrument);
  } else {
    const measureVisibility = () => {
      const bounds = instrument.getBoundingClientRect();
      visible = bounds.bottom > 0 && bounds.top < window.innerHeight;
      updateMotion();
    };
    window.addEventListener("scroll", measureVisibility, { passive: true });
    window.addEventListener("resize", measureVisibility, { passive: true });
    measureVisibility();
  }
  updateMotion();
}
