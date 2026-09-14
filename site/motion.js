// Two visible carriers (WAAPI) and three ribbon followers (one native SVG clock).
// No frame loop, DOM geometry reads, storage, or network work.
const toggle = document.querySelector("[data-motion-toggle]");
const fields = [...document.querySelectorAll("[data-motion-scene]")];
if (toggle && fields.length && !toggle.dataset.initialized &&
    "IntersectionObserver" in window && typeof Element.prototype.animate === "function" &&
    typeof SVGSVGElement.prototype.pauseAnimations === "function") {
  toggle.dataset.initialized = "true";
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const forced = matchMedia("(forced-colors: active)");
  const print = matchMedia("print");
  let manualPause = false;
  let away = false;
  const scenes = fields.map(field => {
    const svg = field.querySelector("svg");
    svg.pauseAnimations();
    svg.setCurrentTime(0);
    const followers = [...svg.querySelectorAll("[data-motion-follower]")].map(marker => {
      const motion = marker.querySelector("animateMotion");
      return {marker, motion, template: motion.cloneNode(true)};
    });
    return {field, svg, followers, nativeStarted: false, visible: false, animations: []};
  });
  const poses = ["translate(-10px, 4px) rotate(-4deg) scale(.96, 1.03)",
    "translate(10px, -4px) rotate(4deg) scale(1.04, .97)",
    "translate(-10px, 4px) rotate(-4deg) scale(.96, 1.03)"];
  function staticFollowers(scene) {
    if (!scene.nativeStarted) return;
    // Remove SMIL intervals as well as their effect: a later media round trip
    // must not replay old begin/end events when the SVG clock restarts at zero.
    for (const follower of scene.followers) {
      const replacement = follower.template.cloneNode(true);
      follower.motion.replaceWith(replacement);
      follower.motion = replacement;
      follower.marker.setAttribute("transform", `translate(${follower.marker.dataset.motionStart})`);
    }
    scene.svg.setCurrentTime(0);
    scene.nativeStarted = false;
  }
  function sync() {
    const staticMode = reduced.matches || forced.matches || print.matches;
    toggle.hidden = staticMode;
    toggle.setAttribute("aria-pressed", String(manualPause));
    toggle.setAttribute("aria-label", manualPause ? "Resume decorative motion" : "Pause decorative motion");
    toggle.querySelector("[data-motion-label]").textContent = manualPause ? "Resume" : "Pause";
    let active = 0;
    for (const scene of scenes) {
      scene.svg.pauseAnimations();
      if (staticMode) {
        scene.animations.forEach(animation => animation.cancel());
        scene.animations = [];
        staticFollowers(scene);
      }
      const running = !staticMode && !manualPause && !away && !document.hidden && scene.visible && active < 2;
      if (running) {
        active++;
        if (!scene.animations.length) {
          scene.animations = [...scene.field.querySelectorAll("[data-motion-track]")].map(track => {
            const animation = track.animate(poses.map(transform => ({transform})),
              {duration: 24000, iterations: Infinity, easing: "ease-in-out"});
            return animation;
          });
        }
        if (scene.followers.length) {
          if (!scene.nativeStarted) {
            scene.followers.forEach(({marker, motion}) => {
              marker.removeAttribute("transform");
              motion.beginElement();
            });
            scene.nativeStarted = true;
          }
          scene.svg.unpauseAnimations();
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
