const root = document.querySelector("[data-question-atlas]");
if (root) {
  const disclosure = root.querySelector("[data-atlas-map]");
  const notice = root.querySelector("[data-atlas-notice]");
  const retry = root.querySelector("[data-atlas-retry]");
  const mount = root.querySelector("[data-atlas-mount]");
  let controller = null;
  let loading = false;
  let visible = false;
  let failed = false;
  let attempts = 0;
  const active = () => disclosure.open && visible && !document.hidden;
  const sync = () => controller?.setActive(active());
  notice.textContent = "Five editorial questions, with their original passages. The map loads only when opened.";

  async function load() {
    if (controller || loading || attempts >= 3 || !disclosure.open) return;
    loading = true;
    attempts++;
    failed = false;
    retry.hidden = true;
    root.dataset.atlasState = "loading";
    notice.textContent = "Opening the local question map…";
    try {
      // Browsers cache rejected module imports. A bounded fresh URL makes Retry real.
      const module = await import(attempts === 1 ? "./atlas-map.js" : `./atlas-map.js?attempt=${attempts}`);
      controller = module.mountAtlas(root, mount);
      root.dataset.atlasState = "ready";
      notice.textContent = "Question map ready. Choose a question.";
      sync();
    } catch (error) {
      failed = true;
      mount.replaceChildren();
      root.dataset.atlasState = "failed";
      notice.textContent = "The map could not be opened. All questions and source passages remain in the index below.";
      if (attempts >= 3) notice.textContent += " Reload this page to try again.";
      retry.hidden = attempts >= 3;
      console.warn("Question atlas unavailable", error);
    } finally {
      loading = false;
    }
  }
  disclosure.addEventListener("toggle", () => {
    sync();
    if (disclosure.open && !failed) load();
  });
  retry.addEventListener("click", load);
  document.addEventListener("visibilitychange", sync);
  window.addEventListener("pagehide", () => controller?.setActive(false));
  window.addEventListener("pageshow", sync);
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(entries => {
      visible = entries[0].isIntersecting;
      sync();
    }).observe(disclosure);
  } else {
    visible = true;
  }
  if (disclosure.open) load();
}
