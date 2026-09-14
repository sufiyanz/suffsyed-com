"""Real lazy scene engine with route-only control fixtures; not a world-composition test."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
IDS = ["scratch-terminal", "ink-studio", "pocket-darkroom", "blackout-poetry",
       "agent-terrarium", "signal-noise", "sound-loom", "assumption-lab", "generative-postcard"]
FIXTURE = """
export async function mount(root, context) {
  const button=document.createElement('button');
  button.textContent='Pulse signature';
  button.addEventListener('click',()=>context.pulseSignature?.(),{signal:context.signal});
  root.append(button);
  return {setActive(){},resize(){},setPreferences(){},destroy(){}};
}
"""
PROBE = """(() => {
  const probe=window.sceneProbe={paints:0,frames:[],timers:new Set()};
  for(const name of ['clearRect','fillRect','fillText','drawImage']) {
    const original=CanvasRenderingContext2D.prototype[name];
    CanvasRenderingContext2D.prototype[name]=function(...args) {
      if(this.canvas.className.startsWith('pg-scene-')) {
        probe.paints++;
        if(name==='clearRect'&&this.canvas.className==='pg-scene-canvas')probe.frames.push(performance.now());
      }
      return original.apply(this,args);
    };
  }
  const timeout=window.setTimeout,clear=window.clearTimeout;
  window.setTimeout=function(callback,delay,...args) {
    const owned=typeof callback==='function'&&new Error().stack.includes('scene-engine.js');
    if(!owned)return timeout(callback,delay,...args);
    let id=timeout(()=>{probe.timers.delete(id);callback(...args);},delay);
    probe.timers.add(id);return id;
  };
  window.clearTimeout=function(id){probe.timers.delete(id);return clear(id);};
})();"""


def fixture(route):
    name = Path(urlsplit(route.request.url).path).stem
    if name in IDS or name == "type-garden":
        route.fulfill(body=FIXTURE, content_type="text/javascript")
    else:
        route.continue_()


def stable(page, milliseconds=220):
    before = page.evaluate("sceneProbe.paints")
    page.wait_for_timeout(milliseconds)
    assert page.evaluate("sceneProbe.paints") == before
    assert page.evaluate("sceneProbe.timers.size") == 0


def run(args):
    args.artifacts.mkdir(parents=True, exist_ok=True)
    rows = []
    with sync_playwright() as p:
        browser = p.webkit.launch()
        for width in args.widths:
            context = browser.new_context(viewport={"width": width, "height": 844 if width < 900 else 1000},
                                          device_scale_factor=2, has_touch=width < 900)
            context.add_init_script(PROBE)
            context.route("**/assets/playground/*.js*", fixture)
            page = context.new_page()
            errors, requests = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.goto(args.url, wait_until="networkidle")
            assert not [url for url in requests if "/scene-" in url]
            page.get_by_role("button", name="Open cover experiments").click()
            for identifier in IDS:
                print(f"Scene: {identifier} / {width}px", flush=True)
                page.get_by_role("combobox", name="Choose experiment").select_option(identifier)
                page.wait_for_selector(f'[data-world-signature="{identifier}"][data-scene-status="ready"]')
                scene = page.locator(".pg-scene")
                assert scene.count() == 1 and scene.get_attribute("aria-hidden") == "true"
                assert scene.evaluate("el=>getComputedStyle(el).pointerEvents") == "none"
                data = scene.evaluate("""el=>{
                  const canvas=el.querySelector('canvas');
                  const pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
                  return {cells:Number(el.dataset.sceneCells),profile:el.dataset.sceneProfile,
                    width:canvas.width,height:canvas.height,ink:pixels.some((v,i)=>i%4===3&&v>0)};
                }""")
                assert 20 <= data["cells"] <= 3000, data
                assert data["width"] * data["height"] <= 600000, data
                assert data["ink"], data
                page.wait_for_timeout(1200)
                stable(page)
                before = page.evaluate("sceneProbe.frames.length")
                page.get_by_role("button", name="Pulse signature").evaluate("el=>{for(let i=0;i<100;i++)el.click();}")
                page.wait_for_timeout(750)
                pulse_frames = page.evaluate("start=>sceneProbe.frames.slice(start)", before)
                assert 2 <= len(pulse_frames) <= 8, pulse_frames
                assert all(b - a >= 80 for a, b in zip(pulse_frames, pulse_frames[1:])), pulse_frames
                stable(page)
                page.evaluate("scrollTo(0,document.querySelector('.home-cover').offsetHeight+5)")
                page.wait_for_function("document.querySelector('.pg-scene').dataset.sceneActive==='false'")
                stable(page)
                page.get_by_role("button", name="Pulse signature").evaluate("el=>el.click()")
                stable(page)
                page.evaluate("scrollTo(0,0)")
                page.wait_for_function("document.querySelector('.pg-scene').dataset.sceneActive==='true'")
                page.wait_for_timeout(120)
                stable(page)
                if identifier == IDS[0]:
                    page.evaluate("""Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
                      document.dispatchEvent(new Event('visibilitychange'));""")
                    page.wait_for_function("document.querySelector('.pg-scene').dataset.sceneActive==='false'")
                    stable(page)
                    page.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))")
                    page.wait_for_function("document.querySelector('.pg-scene').dataset.sceneActive==='true'")
                    page.wait_for_timeout(120)
                    page.evaluate("dispatchEvent(new Event('pagehide'))")
                    stable(page)
                    page.evaluate("dispatchEvent(new Event('pageshow'))")
                    page.wait_for_timeout(120)
                    stable(page)
                page.emulate_media(reduced_motion="reduce")
                page.wait_for_timeout(120)
                stable(page)
                page.emulate_media(forced_colors="active")
                page.wait_for_selector('.pg-scene[data-scene-state="vector"]')
                assert not scene.locator("canvas").is_visible()
                stable(page)
                page.emulate_media(reduced_motion="no-preference", forced_colors="none")
                page.wait_for_selector('.pg-scene[data-scene-state="glyphs"]')
                page.wait_for_timeout(120)
                stable(page)
                rows.append({"id": identifier, "viewport": width, **data, "pulseFrames": len(pulse_frames)})
            page.get_by_role("combobox", name="Choose experiment").select_option("type-garden")
            page.wait_for_selector('.pg-shell[data-state="ready"] [data-experience="type-garden"]')
            assert not page.locator(".pg-scene").count()
            stable(page)
            page.get_by_role("button", name="Close experiment").click()
            assert not page.locator("[data-world-signature]").count()
            stable(page)
            assert not errors, errors
            assert not [url for url in requests if not url.startswith(args.url)], requests
            context.close()

        context = browser.new_context()
        context.add_init_script(PROBE)
        context.route("**/assets/playground/*.js*", fixture)
        attempts = []
        def recover_scene(route):
            attempts.append(route.request.url)
            if len(attempts) == 1:
                route.fulfill(status=503, body="Temporarily unavailable", content_type="text/plain")
            else:
                route.fulfill(path=str(ROOT / "site/playground/scene-engine.js"), content_type="text/javascript")
        context.route("**/assets/playground/scene-engine.js*", recover_scene)
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle")
        entry = page.get_by_role("button", name="Open cover experiments")
        entry.click()
        page.wait_for_selector('.pg-scene[data-scene-status="failed"]')
        assert page.locator(".pg-shell").get_attribute("data-state") == "ready"
        page.get_by_role("button", name="Close experiment").click()
        entry.click()
        page.wait_for_selector('.pg-scene[data-scene-status="ready"]')
        assert len(attempts) == 2 and "retry=1" in attempts[-1], attempts
        page.get_by_role("button", name="Close experiment").click()
        stable(page)
        context.close()

        context = browser.new_context()
        context.add_init_script(PROBE)
        context.route("**/assets/playground/*.js*", fixture)
        context.route("**/assets/suff-syed-signature.svg", lambda route: route.fulfill(status=503, body="Unavailable"))
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle")
        page.get_by_role("button", name="Open cover experiments").click()
        page.wait_for_selector('.pg-scene[data-scene-status="failed"]')
        assert page.locator(".pg-shell").get_attribute("data-state") == "ready"
        assert page.locator(".cover-signature").evaluate("el=>el.complete&&el.naturalWidth>0")
        assert "suff-syed-signature-reversed.svg" in page.locator(".pg-scene").evaluate("el=>getComputedStyle(el,'::before').maskImage")
        page.screenshot(path=str(args.artifacts / "master-fetch-fallback.png"))
        stable(page)
        page.get_by_role("button", name="Close experiment").click()
        stable(page)
        context.close()

        context = browser.new_context()
        context.add_init_script(PROBE)
        context.route("**/assets/playground/*.js*", fixture)
        held = []
        context.route("**/assets/playground/scene-engine.js", lambda route: held.append(route))
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle")
        page.get_by_role("button", name="Open cover experiments").click()
        page.wait_for_selector('.pg-shell[data-state="ready"]')
        assert len(held) == 1
        page.get_by_role("button", name="Close experiment").click()
        held[0].fulfill(path=str(ROOT / "site/playground/scene-engine.js"), content_type="text/javascript")
        stable(page, 400)
        assert not page.locator(".pg-scene").count()
        context.close()

        context = browser.new_context()
        context.add_init_script(PROBE)
        context.add_init_script("""(() => {
          const get=HTMLCanvasElement.prototype.getContext;
          HTMLCanvasElement.prototype.getContext=function(...args){
            return this.className==='pg-scene-canvas'?null:get.apply(this,args);
          };
        })();""")
        context.route("**/assets/playground/*.js*", fixture)
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle")
        page.get_by_role("button", name="Open cover experiments").click()
        page.wait_for_selector('.pg-scene[data-scene-status="failed"]')
        assert page.locator(".pg-shell").get_attribute("data-state") == "ready"
        assert "original signature" in page.locator(".pg-status").inner_text()
        assert "suff-syed-signature-reversed.svg" in page.locator(".pg-scene").evaluate("el=>getComputedStyle(el,'::before').maskImage")
        stable(page)
        page.get_by_role("button", name="Close experiment").click()
        stable(page)
        context.close()
        browser.close()
    (args.artifacts / "scenes.json").write_text(json.dumps(rows, indent=2) + "\n")
    print("PASS: real nine-profile glyphs, bounded/coalesced pulses, static/inactive cleanup, late disposal and explicit fallback.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--widths", nargs="+", type=int, default=[320, 390, 1600])
    parser.add_argument("--artifacts", type=Path, required=True)
    run(parser.parse_args())
