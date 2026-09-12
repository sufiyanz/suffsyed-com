const archiveForm = document.getElementById("archive-search");
if (archiveForm) initializeArchive();

function initializeArchive() {
  const query = document.getElementById("archive-query");
  const theme = document.getElementById("archive-theme");
  const list = document.getElementById("archive-entries");
  const status = document.getElementById("archive-status");
  const rows = [...list.querySelectorAll(".archive-entry")];
  let index = null;
  let indexPromise = null;
  let revision = 0;
  const normalize = text => text.toLowerCase().replaceAll("’", "'").replace(/\s+/g, " ").trim();

  async function loadIndex() {
    if (index) return index;
    if (!indexPromise) {
      indexPromise = fetch("/assets/search-index.json").then(response => {
        if (!response.ok) throw new Error(`Search index returned ${response.status}`);
        return response.json();
      }).then(data => { index = data; return data; });
    }
    try { return await indexPromise; }
    catch (error) { indexPromise = null; throw error; }
  }

  async function apply() {
    const version = ++revision;
    const phrase = normalize(query.value);
    let data;
    if (phrase) {
      status.textContent = "Opening the local text index…";
      try { data = await loadIndex(); }
      catch (error) {
        if (version !== revision) return;
        status.textContent = "The text index could not be loaded. All essays remain available below. Retry Search when it is available.";
        rows.forEach(row => { row.hidden = false; row.querySelector(".archive-matches").replaceChildren(); });
        console.warn("Archive search unavailable", error);
        return;
      }
    }
    if (version !== revision) return;
    let visible = 0, totalPassages = 0;
    for (const row of rows) {
      const essay = data?.find(item => item.slug === row.dataset.slug);
      const matches = phrase ? essay.passages.filter(passage => normalize(passage.text).includes(phrase)) : [];
      const titleMatch = phrase && normalize(essay.title).includes(phrase);
      const themeMatch = !theme.value || row.dataset.theme === theme.value;
      row.hidden = !themeMatch || (!!phrase && !matches.length && !titleMatch);
      const target = row.querySelector(".archive-matches");
      target.replaceChildren();
      if (row.hidden) continue;
      visible++;
      totalPassages += matches.length;
      if (phrase) {
        const note = document.createElement("small");
        note.textContent = `${matches.length} matching ${matches.length === 1 ? "passage" : "passages"}${titleMatch ? " · Title also matches" : ""}`;
        target.append(note);
        for (const passage of matches.slice(0, 3)) {
          const p = document.createElement("p"), link = document.createElement("a");
          const text = passage.text;
          const at = normalize(text).indexOf(phrase);
          const start = Math.max(0, at - 75), end = Math.min(text.length, at + phrase.length + 145);
          link.textContent = passage.kind === "table" ? `Table / ${passage.label}. Open the original rows and columns ↗` : `${start ? "…" : ""}${text.slice(start, end)}${end < text.length ? "…" : ""} ↗`;
          link.href = `${essay.url}#${passage.id}`;
          p.append(link);
          target.append(p);
        }
        if (matches.length > 3) {
          const more = document.createElement("details"), summary = document.createElement("summary");
          summary.textContent = `Show the other ${matches.length - 3} matching passages`;
          more.append(summary);
          for (const passage of matches.slice(3)) {
            const p = document.createElement("p"), link = document.createElement("a");
            link.textContent = passage.kind === "table" ? `Table / ${passage.label}. Open the original rows and columns ↗` : passage.text;
            link.href = `${essay.url}#${passage.id}`;
            p.append(link); more.append(p);
          }
          target.append(more);
        }
      }
    }
    status.textContent = `${visible} ${visible === 1 ? "essay" : "essays"}${phrase ? ` · ${totalPassages} matching passages for “${query.value.trim()}”` : ""}${theme.value ? ` · ${theme.value}` : ""}.${visible === 0 ? " Try a different phrase or reset the filters." : ""}`;
    const url = new URL(location.href);
    if (query.value.trim()) url.searchParams.set("q", query.value.trim());
    else url.searchParams.delete("q");
    if (theme.value) url.searchParams.set("theme", theme.value);
    else url.searchParams.delete("theme");
    history.replaceState(null, "", url);
  }
  archiveForm.addEventListener("submit", event => { event.preventDefault(); apply(); });
  theme.addEventListener("change", apply);
  query.addEventListener("search", apply);
  document.getElementById("archive-reset").addEventListener("click", () => {
    query.value = theme.value = "";
    apply();
  });
  document.getElementById("archive-list-toggle").addEventListener("click", event => {
    const compact = list.classList.toggle("compact");
    event.currentTarget.setAttribute("aria-pressed", String(compact));
    event.currentTarget.textContent = compact ? "Show the cover illustrations" : "Compact reading list";
  });
  const params = new URLSearchParams(location.search);
  if (params.has("q")) query.value = params.get("q").slice(0, 180);
  if ([...theme.options].some(option => option.value === params.get("theme"))) theme.value = params.get("theme");
  if (query.value || theme.value) apply();
}
