"""Focused WebKit tests for the two contract-v1 code/model modules.

Generates a disposable mount harness in --artifacts, never in the published site.
Serves source modules at their real /assets/playground/ URLs on a loopback port.
Run with the repository's Playwright-enabled Python; no build or host is required.
"""
import argparse
import gzip
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PALETTE = {"forest": "#1B2915", "green": "#305831", "stone": "#D7CDB8",
           "paper": "#EFEDE6", "white": "#FFFFFF", "ink": "#191919"}

HARNESS = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Code / models contract harness</title>
<link rel="stylesheet" href="/assets/journal.css">
__SHARED_CSS__
<link rel="stylesheet" href="/assets/playground/scratch-terminal.css">
<link rel="stylesheet" href="/assets/playground/assumption-lab.css">
<style>
body { margin:0; background:#D7CDB8; padding:12px 0; }
main { width:min(900px, 100%); margin:auto; }
.pg-shell.harness { position:relative; display:block; padding:0; overflow:visible; background:var(--pg-world-bg); }
.harness-label { color:var(--pg-world-muted); font:12px var(--font-technical); padding:12px; }
#root { height:400px; }
#status, #error { color:var(--pg-world-ink); padding:6px 12px; font:12px var(--font-technical); }
</style></head><body><main id="cover-playground" class="pg-shell harness"><p class="harness-label">SUFF SYED / EPHEMERAL STUDIES</p>
<div id="root"></div><p id="status" role="status"></p><p id="error"></p></main>
<script type="module">
const modules = {
  "scratch-terminal": await import("/assets/playground/scratch-terminal.js"),
  "assumption-lab": await import("/assets/playground/assumption-lab.js")
};
window.errors = []; window.statuses = [];
window.loadExperience = async (id, active = true) => {
  window.abort?.abort(); window.controller?.destroy();
  const root = document.querySelector("#root");
  const [width,height] = innerWidth === 320 ? [280,320] : innerWidth === 390 ? [350,310] : [900,400];
  root.style.width = `${width}px`; root.style.height = `${height}px`;
  root.style.margin = "auto"; root.dataset.testHeight = height;
  root.dataset.experience = id;
  document.querySelector("#cover-playground").dataset.world = id;
  window.abort = new AbortController();
  const signal = window.abort.signal;
  document.querySelector("#error").textContent = "";
  document.querySelector("#status").textContent = "";
  window.ctx = {
    signal, seed: 12345, random: () => 0.5,
    preferences: {reducedMotion:false, forcedColors:false},
    palette: __PALETTE__,
    data: {signature:{src:"/assets/suff-syed-signature.svg",viewBox:[0,0,350,148]},photos:[],passages:[]},
    setStatus(message) { statuses.push(message); document.querySelector("#status").textContent = message; },
    reportError(message, error) { errors.push({message, detail:error?.message}); document.querySelector("#error").textContent = message; }
  };
  window.controller = await modules[id].mount(root, window.ctx);
  if (signal.aborted) return;
  controller.resize({width:root.clientWidth,height:root.clientHeight,dpr:devicePixelRatio});
  controller.setActive(active);
};
await loadExperience("scratch-terminal", false);
window.ready = true;
</script></body></html>"""

PROBE = """(() => {
  const NativeWorker = window.Worker;
  const probe = window.codeProbe = {started:0, terminated:0, live:new Set(), timers:new Set(), paints:0};
  window.Worker = class extends NativeWorker {
    constructor(...args) { super(...args); probe.started++; probe.live.add(this); }
    terminate() { if (probe.live.delete(this)) probe.terminated++; super.terminate(); }
  };
  const schedule = window.setTimeout, cancel = window.clearTimeout;
  window.setTimeout = (fn, delay, ...args) => {
    if (delay !== 1500) return schedule(fn, delay, ...args);
    const id = schedule(() => {probe.timers.delete(id); fn(...args);}, delay);
    probe.timers.add(id); return id;
  };
  window.clearTimeout = id => {probe.timers.delete(id); return cancel(id);};
  const fill = CanvasRenderingContext2D.prototype.fillRect;
  CanvasRenderingContext2D.prototype.fillRect = function(...args) {
    if (this.canvas.classList.contains("code-canvas")) probe.paints++;
    return fill.apply(this, args);
  };
  for (const method of ["getItem","setItem","removeItem","clear"]) {
    Storage.prototype[method] = () => { throw new Error("Forbidden storage access"); };
  }
})();"""


def resources(page):
    return page.evaluate("""() => ({
      live:codeProbe.live.size, timers:codeProbe.timers.size,
      started:codeProbe.started, terminated:codeProbe.terminated, paints:codeProbe.paints
    })""")


def assert_stopped(page):
    snapshot = resources(page)
    assert snapshot["live"] == 0 and snapshot["timers"] == 0, snapshot
    page.wait_for_timeout(100)
    assert resources(page) == snapshot, "Inactive resources continued working"


def fit(page):
    bounds = page.evaluate("""() => {
      const root = document.querySelector("#root"), shell = root.firstElementChild;
      const targets = [...root.querySelectorAll("button,select,input,summary")];
      return {
        pageFits:document.documentElement.scrollWidth <= innerWidth,
        rootHeight:root.getBoundingClientRect().height,
        expectedHeight:Number(root.dataset.testHeight),
        rootFits:root.scrollWidth <= root.clientWidth,
        shellFits:shell.scrollWidth <= shell.clientWidth,
        overflow:[...shell.children].map(x=>({class:x.className,width:x.getBoundingClientRect().width,scroll:x.scrollWidth})),
        targets:targets.filter(x => x.getClientRects().length && (!x.closest("details") || x.tagName === "SUMMARY"))
          .map(x => ({tag:x.tagName,height:x.getBoundingClientRect().height}))
      };
    }""")
    assert bounds["pageFits"] and bounds["rootFits"] and bounds["shellFits"], bounds
    assert bounds["rootHeight"] == bounds["expectedHeight"], bounds
    assert all(target["height"] >= 44 for target in bounds["targets"]), bounds


def pixels(page):
    return page.evaluate("""() => {
      const canvas = document.querySelector(".code-canvas"), ctx = canvas.getContext("2d");
      const data = ctx.getImageData(0,0,canvas.width,canvas.height).data;
      const colors = new Set();
      for (let i=0;i<data.length;i+=16) colors.add(`${data[i]},${data[i+1]},${data[i+2]}`);
      return {colors:colors.size, pixels:canvas.width*canvas.height, bitmap:canvas.toDataURL()};
    }""")


def run(page, code=None):
    if code is not None:
        choose_view(page, "Code")
        page.locator("textarea").fill(code)
    page.get_by_role("button", name="Run", exact=True).click()
    page.wait_for_function("codeProbe.live.size === 0 && !document.querySelector('[data-action=run]').disabled")


def choose_view(page, name):
    button = page.get_by_role("button", name=name, exact=True)
    if button.is_visible():
        button.click()


def world_checks(page, expected_bg):
    return page.evaluate("""expected => {
      const root = document.querySelector("#root"), style = getComputedStyle(root);
      const values = name => style.getPropertyValue(`--pg-world-${name}`).trim();
      if(values("bg").toUpperCase() !== expected.toUpperCase()) throw new Error("Wrong world palette");
      const rgb = hex => hex.replace("#","").match(/../g).map(x => parseInt(x,16)/255)
        .map(x => x <= .04045 ? x/12.92 : ((x+.055)/1.055)**2.4);
      const light = color => rgb(color).reduce((sum,x,i)=>sum+x*[.2126,.7152,.0722][i],0);
      const contrast = (a,b) => (Math.max(light(a),light(b))+.05)/(Math.min(light(a),light(b))+.05);
      const ratios = Object.fromEntries(["ink","muted","accent"].map(name => [name,contrast(values(name),values("bg"))]));
      if(Object.values(ratios).some(value=>value<4.5)) throw new Error("World text contrast below 4.5:1");
      if(getComputedStyle(root.firstElementChild).backgroundColor !== "rgba(0, 0, 0, 0)") throw new Error("Opaque module shell hides signature");
      if(style.getPropertyValue("--forest").trim() !== "#1B2915") throw new Error("Semantic drawing palette changed");
      if(getComputedStyle(root.querySelector("h3")).fontFamily.includes("Newsreader")) throw new Error("World heading fell back to journal typography");
      return ratios;
    }""", expected_bg)


def language_checks(page):
    report = page.evaluate("""async () => {
      const {executeDrawing, LIMITS} = await import("/assets/playground/code-language.js");
      const assert = (condition, message) => {if (!condition) throw new Error(message);};
      const cases = [
        ["print 2 + 3 * 4", ["14"]],
        ["print (2 + 3) * 4; print 20 / 2 / 2; print 8 - 3 - 2", ["20","5","3"]],
        ["let x = -2; print +x; print abs(x); print sqrt(16); print sin(90); print cos(0)", ["-2","2","4","1","1"]],
        ["let x = 3; repeat 3 as i { let x = i; print x }; print x", ["0","1","2","3"]],
        ["# hello\\nclear forest; color paper; width 0.2; line 0,0,400,400; circle 10,20,0; rect 4,5,-2,3; print .5e2", ["50"]],
        ["repeat 0 as i { print i }; print 5", ["5"]],
        ["let constructor = 3; let __proto__ = 4; print constructor + __proto__", ["7"]],
      ];
      for (const [source, logs] of cases) assert(JSON.stringify(executeDrawing(source).logs) === JSON.stringify(logs), source);
      const bad = [
        ["", "Write a drawing"], ["line 1, 2", 'Expected ","'],
        ["let x = 1\\nline x, 0, unknown, 4", 'Line 2, column 12'],
        ["while true {}", "Unknown command"], ["fetch(1)", "Unknown command"],
        ["print Math.sin(1)", "Expected a number"], ["print constructor(1)", "Unknown function"],
        ["print 1 / 0", "finite"], ["print sqrt(-1)", "finite"], ["print 1e999", "finite"],
        ["print 1000001", "finite"], ["repeat 513 as i {}", "0 to 512"],
        ["repeat -1 as i {}", "0 to 512"], ["repeat 1.5 as i {}", "0 to 512"],
        ["circle 1, 1, -2", "radius"], ["width 0", "width"], ["clear pink", "Choose forest"],
        ["repeat 1 as i {", 'Expected "}"'], ["}", 'Unexpected "}"'],
        ["color green circle 2,2,2", "new line"],
        ["repeat 41 as i { print i }", "Log budget"],
        ["repeat 512 as i {" + "circle 1,1,1;".repeat(12) + "}", "Drawing budget"],
        ["repeat 512 as i { repeat 512 as j {} }", "Execution budget"],
        ["print " + "(".repeat(34) + "1" + ")".repeat(34), "nesting"],
        ["print " + Array(50).fill("1").join("+"), "too long"],
        ["repeat 1 as i {".repeat(9) + "}".repeat(9), "nesting"],
        [Array(257).fill(0).map((_,i) => `let x${i} = 1`).join(";"), "256 variables"],
        [" ".repeat(LIMITS.source + 1), "characters"],
        ["print 1;".repeat(2100), "characters"],
        [";;;;".repeat(3100), "tokens"],
        ["print 1+1;".repeat(1400), "too complex"],
      ];
      for (const [source, contains] of bad) {
        let failure;
        try { executeDrawing(source); } catch (error) { failure = error; }
        assert(failure && failure.message.includes(contains), `${source.slice(0,80)} => ${failure?.message}, expected ${contains}`);
        assert(Number.isInteger(failure.line) && Number.isInteger(failure.column), "Missing source position");
      }
      let clock = 0, timedOut = false;
      try { executeDrawing("circle 1,1,1", {now:() => clock += 121}); }
      catch(error) { timedOut = error.message.includes("Time budget"); }
      assert(timedOut, "Interpreter time budget did not fire");
      return {valid:cases.length, rejected:bad.length, timedOut};
    }""")
    return report


def model_checks(page):
    return page.evaluate("""async () => {
      const {calculateModel, SCENARIOS} = await import("/assets/playground/code-model.js");
      const assert = (value, message) => {if (!value) throw new Error(message);};
      const close = (a,b) => Math.abs(a-b) < 1e-9;
      const initial = calculateModel(SCENARIOS[0]);
      assert(close(initial.totalCost,59.5) && close(initial.defects,7.2) && close(initial.humanHours,47.5), "Default model");
      let corners = 0;
      for (const cost of [1,20,100]) for (const automation of [0,60,100]) for (const supervision of [0,50,100]) {
        const result = calculateModel({cost,automation,supervision}); corners++;
        assert(Object.values(result).every(Number.isFinite), "Nonfinite model");
        assert(close(result.manual+result.automated,100), "Task conservation");
        assert(close(result.reviewed+result.unreviewed,automation), "Review conservation");
        assert(result.totalCost >= 0 && result.totalCost <= 125, "Cost range");
        assert(result.defects >= 0 && result.defects <= 20, "Defect range");
      }
      const manual = calculateModel({cost:100,automation:0,supervision:100});
      assert(manual.totalCost === 100 && manual.defects === 0, "Manual reference");
      const expensive = calculateModel({cost:100,automation:100,supervision:100});
      assert(expensive.totalCost === 125 && expensive.savings === -25, "Competing tradeoff");
      const cheap = calculateModel({...SCENARIOS[0],cost:1});
      assert(cheap.totalCost < initial.totalCost && cheap.defects === initial.defects, "Price does not create quality");
      const reviewed = calculateModel({...SCENARIOS[0],supervision:100});
      assert(reviewed.humanHours > initial.humanHours && reviewed.defects < initial.defects, "Review tradeoff");
      for (const input of [{cost:0,automation:0,supervision:0},{cost:1,automation:101,supervision:0},
        {cost:1,automation:0,supervision:NaN},{cost:Infinity,automation:0,supervision:0},
        {cost:"1",automation:0,supervision:0}]) {
        let rejected=false; try {calculateModel(input);} catch {rejected=true;}
        assert(rejected,"Invalid model input accepted");
      }
      return {corners, initial};
    }""")


def cancellation_checks(page):
    return page.evaluate("""async () => {
      const before = codeProbe.paints;
      for (const id of ["scratch-terminal","assumption-lab"]) {
        const {mount} = await import(`/assets/playground/${id}.js`);
        let resolveReady;
        const pending = new Promise(resolve => {resolveReady=resolve;});
        const previous = Object.getOwnPropertyDescriptor(document.fonts,"ready");
        Object.defineProperty(document.fonts,"ready",{configurable:true,get:()=>pending});
        const root = document.createElement("div"); root.dataset.experience=id;
        root.style.cssText="width:280px;height:320px"; document.body.append(root);
        const abort = new AbortController();
        const mounted = mount(root,{...ctx,signal:abort.signal});
        abort.abort(); resolveReady();
        const controller = await mounted;
        if(previous) Object.defineProperty(document.fonts,"ready",previous); else delete document.fonts.ready;
        controller.setActive(true); controller.resize({width:280,height:320,dpr:2});
        controller.setPreferences({forcedColors:true,reducedMotion:true}); controller.destroy();
        if(root.childNodes.length) throw new Error("Mount continued after abort during font readiness");
        const alreadyAborted = await mount(root,{...ctx,signal:abort.signal});
        alreadyAborted.destroy();
        if(root.childNodes.length) throw new Error("Already-aborted mount mutated root");
        root.remove();
      }
      if(codeProbe.paints !== before || codeProbe.live.size || codeProbe.timers.size) throw new Error("Late resources after aborted mount");
      return {delayedFonts:2, alreadyAborted:2};
    }""")


def browser_checks(base, folder):
    report, failures, requests = {}, [], []
    with sync_playwright() as playwright:
        browser = playwright.webkit.launch(timeout=20000)
        for width in [900, 390, 320]:
            context = browser.new_context(viewport={"width": width, "height": 900}, device_scale_factor=2)
            context.add_init_script(PROBE)
            page = context.new_page()
            page.on("pageerror", lambda error: failures.append(str(error)))
            page.on("request", lambda request: requests.append(request.url) if not request.url.startswith(base) else None)
            page.goto(base)
            page.wait_for_function("window.ready === true")
            assert resources(page)["started"] == 0, "Worker created at inactive mount"
            assert page.get_by_role("button", name="Run", exact=True).is_disabled()
            fit(page)
            assert pixels(page)["colors"] > 20, "Initial meaningful drawing missing"
            page.evaluate("controller.setActive(true)")
            report[f"scratchContrast-{width}"] = world_checks(page, "#101713")
            art_bounds = page.locator("canvas").bounding_box()
            assert art_bounds["width"] >= 160 and art_bounds["height"] >= 160, art_bounds
            assert art_bounds["y"] + art_bounds["height"] <= page.locator("#root").bounding_box()["y"] + page.locator("#root").bounding_box()["height"], art_bounds
            choose_view(page, "Code")
            page.screenshot(path=str(folder / f"scratch-editor-{width}.png"))
            if width == 900:
                report["language"] = language_checks(page)
                report["math"] = model_checks(page)
                report["cancellation"] = cancellation_checks(page)
            run(page)
            assert "50 shapes" in page.locator(".code-log").inner_text()
            assert "> 48" in page.locator(".code-log").inner_text()
            orbit = pixels(page)
            assert orbit["colors"] > 20 and orbit["pixels"] <= 1000000
            assert_stopped(page)
            page.screenshot(path=str(folder / f"scratch-{width}.png"))
            page.screenshot(path=str(folder / f"scratch-art-{width}.png"))
            page.get_by_role("combobox", name="Drawing example").select_option("1")
            run(page)
            assert "131 shapes" in page.locator(".code-log").inner_text()
            assert pixels(page)["bitmap"] != orbit["bitmap"]
            page.get_by_role("combobox", name="Drawing example").select_option("2")
            run(page)
            assert "98 shapes" in page.locator(".code-log").inner_text()
            good = pixels(page)["bitmap"]
            run(page, "let x = 1\nline 1, 2")
            assert page.locator(".code-error").is_visible()
            assert "Line 2" in page.locator(".code-error").inner_text()
            assert len(page.evaluate("errors")) == 1
            assert pixels(page)["bitmap"] == good, "Failure discarded last good drawing"
            run(page, "repeat 512 as i { repeat 512 as j {} }")
            assert "budget" in page.locator(".code-error").inner_text()
            assert_stopped(page)
            if width == 900:
                page.route("**/code-worker.js", lambda route: route.fulfill(status=200, content_type="application/javascript", body="self.onmessage = () => {};"))
                run(page, "circle 200,200,80")
                assert "1.5 seconds" in page.locator(".code-error").inner_text()
                assert_stopped(page)
                page.unroute("**/code-worker.js")
                page.evaluate("""() => {window.WorkingWorker=Worker; window.Worker=class {constructor(){throw new Error("Injected startup failure");}};}""")
                run(page)
                assert "could not start" in page.locator(".code-error").inner_text()
                page.evaluate("window.Worker=window.WorkingWorker; delete window.WorkingWorker")
                page.locator("textarea").evaluate("(node) => node.value=' '.repeat(16001)")
                run(page)
                assert "characters" in page.locator(".code-error").inner_text()
                report["workerFailures"] = ["watchdog", "startup", "huge input"]
            page.get_by_role("button", name="Reset", exact=True).click()
            assert page.locator("textarea").input_value().startswith("# A quiet rosette.")
            for action in ["stop", "inactive", "abort", "destroy"]:
                if action in ["abort", "destroy"]:
                    page.evaluate('loadExperience("scratch-terminal")')
                page.evaluate("""action => {
                  document.querySelector("[data-action=run]").click();
                  if(action==="stop") document.querySelector("[data-action=stop]").click();
                  if(action==="inactive") controller.setActive(false);
                  if(action==="abort") abort.abort();
                  if(action==="destroy") controller.destroy();
                }""", action)
                assert_stopped(page)
                if action == "inactive":
                    page.evaluate("controller.setActive(true)")
                    assert_stopped(page)
            page.evaluate('loadExperience("scratch-terminal")')
            page.evaluate("""() => {
              controller.resize({width:320,height:400,dpr:20});
              controller.setPreferences({reducedMotion:true,forcedColors:true});
            }""")
            assert pixels(page)["pixels"] <= 1000000
            assert page.locator("#root").get_attribute("data-code-forced") == "true"
            assert page.evaluate("getComputedStyle(document.querySelector('#root')).color !== getComputedStyle(document.querySelector('#root')).backgroundColor")
            fit(page)
            page.screenshot(path=str(folder / f"scratch-forced-controller-{width}.png"))
            page.evaluate('loadExperience("assumption-lab")')
            fit(page)
            report[f"modelContrast-{width}"] = world_checks(page, "#F4F7FD")
            assert page.locator("[data-metric=humanHours]").inner_text() == "47.5"
            page.screenshot(path=str(folder / f"model-{width}.png"))
            page.locator(".code-model-results").evaluate("(node) => node.scrollTop = node.scrollHeight")
            page.screenshot(path=str(folder / f"model-results-{width}.png"))
            choose_view(page, "Adjust")
            page.screenshot(path=str(folder / f"model-adjust-{width}.png"))
            before = page.locator(".code-model-machine").get_attribute("width")
            page.locator("[data-assumption=cost]").evaluate("(node) => {node.value='1'; node.dispatchEvent(new Event('input',{bubbles:true}));}")
            assert page.locator(".code-model-machine").get_attribute("width") != before
            assert page.locator("[data-metric=defects]").inner_text() == "7.2"
            assert page.locator(".code-model-pocket-cost").inner_text() == "48.1"
            assert "cost units / 7.2 toy defects" in page.locator(".code-model-pocket").inner_text()
            page.locator("[data-assumption=supervision]").evaluate("(node) => {node.value='100'; node.dispatchEvent(new Event('input',{bubbles:true}));}")
            assert page.locator("[data-metric=humanHours]").inner_text() == "55.0"
            assert page.locator("[data-metric=defects]").inner_text() == "2.4"
            page.locator("[data-assumption=automation]").evaluate("(node) => {node.value='0'; node.dispatchEvent(new Event('input',{bubbles:true}));}")
            assert "All work stays human" in page.locator(".code-model-interpretation").inner_text()
            page.get_by_role("combobox", name="Assumption example").select_option("3")
            assert "above" in page.locator(".code-model-headline").inner_text()
            page.get_by_role("button", name="Reset", exact=True).click()
            assert page.locator("[data-assumption=cost]").input_value() == "20"
            page.locator("[data-assumption=cost]").focus()
            page.keyboard.press("ArrowRight")
            assert page.locator("[data-assumption=cost]").input_value() == "21"
            page.evaluate("controller.resize({width:320,height:200,dpr:2})")
            assert page.locator("[data-assumption=cost]").input_value() == "21"
            page.evaluate("controller.setPreferences({reducedMotion:true,forcedColors:true})")
            page.screenshot(path=str(folder / f"model-forced-controller-{width}.png"))
            fit(page)
            page.evaluate("controller.setActive(false)")
            assert page.locator("[data-assumption=cost]").is_disabled()
            assert_stopped(page)
            page.evaluate("controller.destroy(); controller.destroy(); abort.abort()")
            assert page.locator("#root").inner_html() == ""
            page.evaluate('loadExperience("assumption-lab")')
            assert page.locator("[data-assumption=cost]").input_value() == "20"
            assert_stopped(page)
            report[str(width)] = {"resources": resources(page), "rootHeight": page.locator("#root").bounding_box()["height"], "fits": True}
            context.close()
        browser.close()
    assert not failures, failures
    assert not requests, requests
    return report


def host_checks(url, folder):
    """Overlay only this team's source responses; never change the live host files."""
    owned = {
        name: ROOT / "site/playground" / name for name in [
            "scratch-terminal.js", "scratch-terminal.css", "assumption-lab.js", "assumption-lab.css",
            "code-dom.js", "code-language.js", "code-worker.js", "code-model.js",
        ]
    }
    results = []
    with sync_playwright() as playwright:
        browser = playwright.webkit.launch(timeout=20000)
        for width, height in [(320, 740), (390, 844), (1028, 900), (1600, 1000)]:
            context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=2,
                                          has_touch=width < 900)
            context.add_init_script(PROBE)

            def overlay(route):
                source = owned.get(urlsplit(route.request.url).path.rsplit("/", 1)[-1])
                if source:
                    route.fulfill(path=str(source), content_type="text/css" if source.suffix == ".css" else "text/javascript")
                else:
                    route.continue_()

            context.route("**/assets/playground/*", overlay)
            page = context.new_page()
            errors, external = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: external.append(request.url) if not request.url.startswith(url) else None)
            page.goto(url, wait_until="networkidle")
            cover = page.locator(".home-cover")
            cover_height = cover.bounding_box()["height"]
            page.get_by_role("button", name="Open cover experiments").click()
            for identifier in ["scratch-terminal", "assumption-lab"]:
                page.get_by_role("combobox", name="Choose experiment").select_option(identifier)
                page.wait_for_function("document.querySelector('.pg-shell').dataset.state === 'ready'")
                root = page.locator(f'[data-experience="{identifier}"]')
                root.wait_for(state="visible")
                page.evaluate("document.fonts.ready")
                heading_font = root.locator("h3").evaluate("node => getComputedStyle(node).fontFamily")
                assert "Newsreader" not in heading_font and "Kyoto" not in heading_font, heading_font
                page.wait_for_timeout(1200)
                if identifier == "scratch-terminal":
                    canvas = root.locator("canvas")
                    assert canvas.bounding_box()["height"] >= 160
                    run(page)
                    assert "50 shapes" in root.locator(".code-log").inner_text()
                    assert pixels(page)["colors"] > 20
                    art = pixels(page)["bitmap"]
                    run(page, "circle nope")
                    assert root.locator(".code-error").is_visible()
                    assert page.locator(".pg-shell").get_attribute("data-state") == "ready"
                    assert pixels(page)["bitmap"] == art
                    choose_view(page, "Drawing")
                    page.screenshot(path=str(folder / f"host-{width}-scratch-last-good.png"), clip=cover.bounding_box())
                    root.get_by_role("button", name="Reset", exact=True).click()
                    run(page)
                    page.wait_for_timeout(1200)
                    page.screenshot(path=str(folder / f"host-{width}-scratch-drawing.png"), clip=cover.bounding_box())
                    choose_view(page, "Code")
                    page.screenshot(path=str(folder / f"host-{width}-scratch-code.png"), clip=cover.bounding_box())
                    choose_view(page, "Drawing")
                    assert_stopped(page)
                else:
                    page.screenshot(path=str(folder / f"host-{width}-model-readout.png"), clip=cover.bounding_box())
                    choose_view(page, "Adjust")
                    root.get_by_role("combobox", name="Assumption example").select_option("3")
                    assert "above" in root.locator(".code-model-headline").inner_text()
                    slider = root.get_by_role("slider", name="Human supervision")
                    slider.focus()
                    page.keyboard.press("Home")
                    assert slider.input_value() == "0"
                    root.get_by_role("button", name="Reset", exact=True).click()
                    root.get_by_role("slider", name="Cost of intelligence").focus()
                    page.keyboard.press("ArrowRight")
                    assert root.locator(".code-model-pocket-cost").inner_text() == "60.1"
                    page.wait_for_timeout(1200)
                    page.screenshot(path=str(folder / f"host-{width}-model-adjust.png"), clip=cover.bounding_box())
                    choose_view(page, "Readout")
                geometry = root.evaluate("""root => {
                  const box = root.getBoundingClientRect();
                  const canvas = root.querySelector("canvas")?.getBoundingClientRect();
                  return {width:box.width,height:box.height,
                    artifact:canvas ? {width:canvas.width,height:canvas.height} : null,
                    fits:root.scrollWidth <= root.clientWidth};
                }""")
                assert geometry["fits"], geometry
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert cover.bounding_box()["height"] == cover_height
                results.append({"viewportWidth": width, "id": identifier, "headingFont": heading_font, **geometry})
            page.emulate_media(reduced_motion="reduce")
            page.get_by_role("combobox", name="Choose experiment").select_option("scratch-terminal")
            page.wait_for_function("document.querySelector('[data-experience=scratch-terminal]')?.dataset.codeReduced === 'true'")
            run(page)
            assert_stopped(page)
            page.evaluate("""() => {
              document.querySelector('[data-experience=scratch-terminal] [data-action=run]').click();
              document.querySelector('[aria-label="Close experiment"]').click();
            }""")
            assert_stopped(page)
            assert not page.locator(".pg-instance").count()
            assert not errors, errors
            assert not external, external
            context.close()
        browser.close()
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--shared-css", type=Path, help="Read-only host playground.css, if integration is ready.")
    parser.add_argument("--host-url", help="Also check the real loopback host with owned source-response overlays.")
    parser.add_argument("--port", type=int, default=0, help="0 chooses an unused loopback port; never use 8766.")
    args = parser.parse_args()
    if args.port == 8766:
        parser.error("Port 8766 belongs to the integration preview.")
    if args.host_url and urlsplit(args.host_url).hostname != "127.0.0.1":
        parser.error("Host checks require the loopback integration preview.")
    artifacts = args.artifacts.resolve()
    if artifacts == ROOT or ROOT in artifacts.parents:
        parser.error("Keep the generated harness and screenshots outside the worktree.")
    artifacts.mkdir(parents=True, exist_ok=True)
    palette = PALETTE
    if args.contract:
        contract = json.loads(args.contract.read_text())
        assert contract["version"] == 1
        palette = contract["moduleInterface"]["context"]["palette"]
    harness = artifacts / "code-models-harness.html"
    shared_css = args.shared_css.resolve() if args.shared_css else None
    harness.write_text(HARNESS.replace("__PALETTE__", json.dumps(palette))
                       .replace("__SHARED_CSS__", '<link rel="stylesheet" href="/__shared.css">' if shared_css else ""))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route = unquote(urlsplit(self.path).path)
            if route == "/":
                target = harness
            elif route == "/__shared.css" and shared_css:
                target = shared_css
            elif route.startswith("/assets/"):
                target = (ROOT / "site" / route.removeprefix("/assets/")).resolve()
                if ROOT / "site" not in target.parents:
                    self.send_error(403)
                    return
            else:
                self.send_error(404)
                return
            if not target.is_file():
                self.send_error(404)
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(target)[0] or "application/octet-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert urlopen(base).status == 200
        report = browser_checks(base, artifacts)
        if args.host_url:
            report["host"] = host_checks(args.host_url.rstrip("/"), artifacts)
        report["payloadGzipBytes"] = {
            file.name: len(gzip.compress(file.read_bytes(), mtime=0))
            for file in sorted((ROOT / "site/playground").glob("*"))
            if file.name.startswith(("code-", "scratch-terminal.", "assumption-lab."))
        }
        (artifacts / "code-models-results.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


if __name__ == "__main__":
    main()
