// Two visible scenes, at most two transform tracks per scene.
// No frame loop, DOM geometry reads, storage, or network work.
const toggle = document.querySelector("[data-motion-toggle]");
const fields = [...document.querySelectorAll("[data-motion-scene]")];
if (toggle && fields.length && !toggle.dataset.initialized &&
    "IntersectionObserver" in window && typeof Element.prototype.animate === "function") {
  toggle.dataset.initialized = "true";
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const forced = matchMedia("(forced-colors: active)");
  const print = matchMedia("print");
  let manualPause = false;
  let away = false;
  const scenes = fields.map(field => ({field, visible: false, animations: []}));
  const poses = {
    depth: ["translate(-10px, 4px) rotate(-4deg) scale(.96, 1.03)",
      "translate(10px, -4px) rotate(4deg) scale(1.04, .97)",
      "translate(-10px, 4px) rotate(-4deg) scale(.96, 1.03)"],
    orbit: ["rotate(-12deg) translateY(-6px)", "rotate(12deg) translateY(6px)", "rotate(-12deg) translateY(-6px)"],
  };
  function sync() {
    const staticMode = reduced.matches || forced.matches || print.matches;
    toggle.hidden = staticMode;
    toggle.setAttribute("aria-pressed", String(manualPause));
    toggle.setAttribute("aria-label", manualPause ? "Resume decorative motion" : "Pause decorative motion");
    toggle.querySelector("[data-motion-label]").textContent = manualPause ? "Resume" : "Pause";
    let active = 0;
    for (const scene of scenes) {
      if (staticMode) {
        scene.animations.forEach(animation => animation.cancel());
        scene.animations = [];
      }
      const running = !staticMode && !manualPause && !away && !document.hidden && scene.visible && active < 2;
      if (running) {
        active++;
        if (!scene.animations.length) {
          scene.animations = [...scene.field.querySelectorAll("[data-motion-track]")].slice(0, 2).map(track => {
            const animation = track.animate(poses[track.dataset.motionTrack].map(transform => ({transform})),
              {duration: track.dataset.motionTrack === "depth" ? 24000 : 18000, iterations: Infinity, easing: "ease-in-out"});
            return animation;
          });
        }
      }
      scene.animations.forEach(animation => running ? animation.play() : animation.pause());
      scene.field.dataset.motionState = staticMode ? "static" : running ? "running" : "suspended";
    }
  }
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) scenes.find(scene => scene.field === entry.target).visible = entry.isIntersecting;
    sync();
  }, {threshold: 0});
  scenes.forEach(scene => observer.observe(scene.field));
  toggle.addEventListener("click", () => { manualPause = !manualPause; sync(); });
  document.addEventListener("visibilitychange", sync);
  for (const query of [reduced, forced, print]) query.addEventListener("change", sync);
  window.addEventListener("pagehide", () => { away = true; sync(); });
  window.addEventListener("pageshow", () => { away = false; sync(); });
  window.addEventListener("beforeprint", () => { away = true; sync(); });
  window.addEventListener("afterprint", () => { away = false; sync(); });
  sync();
}
