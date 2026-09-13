"""Standalone v1-contract tests; writes its temporary mount harness only to --artifacts.

Run with the existing Playwright environment:
  python tools/test_playground_simulation_game.py --artifacts /path/to/session/files
The loopback server uses a free port and serves only these tests and existing site assets.
"""
import argparse
from collections import deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HARNESS = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Local simulation contract test</title><link rel="stylesheet" href="/assets/journal.css">SHARED_CSS
<style>
body { padding:20px; } main { max-width:980px; margin:auto; }
.pg-shell.test-shell { position:relative;inset:auto;padding:0;display:block;overflow:visible; }
.test-slot { position:relative;height:680px;max-height:calc(100svh - 74px); }
#status { font:12px var(--font-technical); margin-top:12px; }
</style></head><body><main class="pg-shell test-shell"><div class="test-slot"><div id="root" class="pg-instance"></div></div>
<p id="status" role="status"></p></main><script type="module">
const probe = window.probe = {active:new Set(), frames:0, times:[], peak:0, requests:0};
const schedule = window.setTimeout, cancel = window.clearTimeout;
window.setTimeout = (fn, delay, ...args) => {
  const id = schedule(() => { probe.active.delete(id); fn(...args); }, delay);
  probe.active.add(id); probe.peak = Math.max(probe.peak, probe.active.size);
  return id;
};
window.clearTimeout = id => { probe.active.delete(id); cancel(id); };
const frame = window.requestAnimationFrame, cancelFrame = window.cancelAnimationFrame;
window.requestAnimationFrame = fn => {
  const id = frame(t => { probe.active.delete(id); fn(t); });
  probe.active.add(id); return id;
};
window.cancelAnimationFrame = id => { probe.active.delete(id); cancelFrame(id); };
const clear = CanvasRenderingContext2D.prototype.clearRect;
CanvasRenderingContext2D.prototype.clearRect = function(...args) {
  probe.frames++; probe.times.push(performance.now());
  return clear.apply(this,args);
};
window.failures = [];
window.messages = [];
window.testMount = async (id, preferences={reducedMotion:false,forcedColors:false}) => {
  window.controller?.destroy();
  window.abort?.abort();
  window.abort = new AbortController();
  document.querySelectorAll('link[data-test]').forEach(link=>link.remove());
  const link = document.createElement('link');
  link.rel='stylesheet'; link.href='/assets/playground/'+id+'.css'; link.dataset.test='';
  const loaded = new Promise((resolve,reject)=>{link.onload=resolve;link.onerror=reject});
  document.head.append(link);
  await loaded;
  const root=document.getElementById('root'); root.dataset.experience=id;
  const {seededRandom}=await import('/assets/playground/sim-core.js');
  window.testContext = {
    signal:abort.signal,seed:42,random:seededRandom(42),preferences,
    palette:{forest:'#1B2915',green:'#305831',stone:'#D7CDB8',paper:'#EFEDE6',white:'#FFFFFF',ink:'#191919'},
    data:{signature:{src:'/assets/suff-syed-signature.svg',viewBox:[0,0,350,148]},photos:[],passages:[]},
    setStatus:message=>{messages.push(message);document.getElementById('status').textContent=message;},
    reportError:(message,error)=>{failures.push(message+': '+error?.message);document.getElementById('status').textContent=message;}
  };
  const module=await import('/assets/playground/'+id+'.js');
  window.controller=await module.mount(root,testContext);
  window.testResize=()=>controller.resize({width:root.clientWidth,height:root.clientHeight,dpr:devicePixelRatio});
  testResize();
};
window.harnessReady=true;
</script></body></html>"""

MODEL_TESTS = """async () => {
  const {Terrarium, SignalGame, seededRandom} = await import('/assets/playground/sim-core.js');
  const assert=(value,message)=>{if(!value)throw new Error(message)};
  const snapshot=w=>JSON.stringify({
    resources:[...w.resources],obstacles:[...w.obstacles],trails:[...w.trails],
    agents:w.agents,delivered:w.delivered,steps:w.steps,rules:w.rules
  });
  const first=new Terrarium(42), second=new Terrarium(42);
  const initial=snapshot(first);
  for(let i=0;i<1800;i++) {
    first.step(); second.step();
    assert(first.agents.every(a=>!first.obstacles[a.cell]),'Agent crossed an obstacle');
    assert(first.foodRemaining()+first.agents.filter(a=>a.carrying).length+first.delivered===72,'Food was fabricated or lost');
    assert(first.trails.length===589 && first.trails.every(t=>t>=0 && t<=8),'Trail budget exceeded');
  }
  assert(first.delivered===72,'Colony did not return all food');
  assert(snapshot(first)===snapshot(second),'Seeded replay diverged');
  assert(initial===snapshot(new Terrarium(42)),'Reset differs from original seed');
  const barrier=new Terrarium(42), home=barrier.home;
  const neighbors=barrier.neighbors(home);
  for(const cell of neighbors)barrier.place(cell,'obstacle');
  for(let i=0;i<200;i++)barrier.step();
  assert(barrier.agents.every(a=>a.cell===home),'Enclosed agents escaped');
  assert(barrier.delivered===0,'Enclosed agents delivered nonexistent food');
  barrier.place(neighbors[0],'erase');
  for(let i=0;i<100;i++)barrier.step();
  assert(barrier.agents.some(a=>a.cell!==home),'Agents failed to use opened route');
  const changing=new Terrarium(21);
  for(let i=0;i<200;i++)changing.step();
  const conserved=changing.foodRemaining()+changing.agents.filter(a=>a.carrying).length+changing.delivered;
  changing.setRules({population:6,exploration:100,persistence:0});
  assert(changing.agents.length===6,'Population did not change');
  assert(changing.foodRemaining()+changing.agents.filter(a=>a.carrying).length+changing.delivered===conserved,'Population adjustment lost food');
  changing.setRules({population:36});
  assert(changing.agents.length===36,'Population did not increase');
  const faint=new Terrarium(1), lasting=new Terrarium(1);
  faint.trails[0]=lasting.trails[0]=8;
  faint.setRules({persistence:0}); lasting.setRules({persistence:100});
  for(let i=0;i<10;i++){faint.step();lasting.step();}
  assert(lasting.trails[0]>faint.trails[0]*5,'Trail persistence has no effect');
  const wander=new Terrarium(2), follow=new Terrarium(2);
  wander.setRules({exploration:100}); follow.setRules({exploration:0});
  for(let i=0;i<80;i++){wander.step();follow.step();}
  assert(JSON.stringify(wander.agents)!==JSON.stringify(follow.agents),'Exploration has no effect');
  let rejected=0;
  for(const action of [()=>new Terrarium(-1),()=>first.setRules({population:99}),()=>first.place(-1,'resource'),()=>seededRandom(1.1)]) {
    try{action();}catch{rejected++;}
  }
  assert(rejected===4,'Invalid model inputs were silently accepted');
  const capped=new Terrarium(42);
  for(let cell=0;cell<capped.resources.length;cell++) capped.place(cell,'resource');
  assert(capped.foodRemaining()<=192,'Food cap exceeded');
  for(let cell=0;cell<capped.obstacles.length;cell++) capped.place(cell,'obstacle');
  assert(capped.obstacles.reduce((a,b)=>a+b,0)<=128,'Wall cap exceeded');
  const noiseGame=new SignalGame(42);
  assert(noiseGame.noise.length===6 && noiseGame.fragments.length===8,'Game entity budget changed');
  noiseGame.start();
  noiseGame.player={x:2,y:4};
  noiseGame.update(.5,{x:0,y:0},true);
  assert(noiseGame.hits===1 && noiseGame.elapsed===3.5 && noiseGame.player.x===6,'Noise collision has no real consequence');
  for(let i=0;i<700;i++)noiseGame.update(.1,{x:0,y:0});
  assert(noiseGame.state==='lost' && noiseGame.remaining===0,'Minute never ended');
  assert(JSON.stringify(new SignalGame(42))===JSON.stringify(new SignalGame(42)),'Game reset is not seeded');
  const successes=[];
  for(const seed of [0,1,2,42,1234,4294967295]) {
    const game=new SignalGame(seed);game.start();
    const walls=new Set(game.noise.map(n=>n.baseY*13+n.baseX));
    let moves=0;
    while(game.state==='playing') {
      const start=Math.round(game.player.y)*13+Math.round(game.player.x);
      const goal=game.target.y*13+game.target.x;
      const queue=[start],paths=new Map([[start,[]]]);
      for(let i=0;i<queue.length && !paths.has(goal);i++) {
        const cell=queue[i],x=cell%13,y=Math.floor(cell/13);
        for(const [dx,dy] of [[-1,0],[1,0],[0,-1],[0,1]]) {
          const nx=x+dx,ny=y+dy,n=ny*13+nx;
          if(nx<0||nx>12||ny<0||ny>8||walls.has(n)||paths.has(n))continue;
          paths.set(n,[...paths.get(cell),{x:dx,y:dy}]);queue.push(n);
        }
      }
      assert(paths.has(goal),'Signal is unreachable');
      for(const direction of paths.get(goal)){game.update(.5,direction,true);moves++;}
    }
    assert(game.state==='won' && game.collected===8 && game.hits===0,'A seeded manual round is not winnable');
    successes.push({seed,moves,remaining:game.remaining});
  }
  return {returned:first.delivered,steps:first.steps,worldCells:first.resources.length,maxAgents:36,maxWalls:128,maxFood:192,gameEntities:8,successes};
}"""


def frozen(page):
    before = page.evaluate("({frames:probe.frames,active:probe.active.size,text:document.getElementById('root').textContent})")
    page.wait_for_timeout(300)
    after = page.evaluate("({frames:probe.frames,active:probe.active.size,text:document.getElementById('root').textContent})")
    assert before == after and after["active"] == 0, (before, after)


def capture(page, artifacts, name):
    page.locator("#root").evaluate("el=>el.scrollTop=0")
    page.screenshot(path=str(artifacts / name), full_page=True)


def controls_fit(page, selector):
    result = page.locator(selector).evaluate_all("""nodes=>{
      const root=document.getElementById('root').getBoundingClientRect();
      return nodes.map(node=>{const box=node.getBoundingClientRect();
        return {text:node.textContent, width:box.width, height:box.height, bottom:box.bottom, rootBottom:root.bottom,
          valid:box.width>=44 && box.height>=44 && box.left>=root.left &&
          box.right<=root.right+1 && box.top>=root.top && box.bottom<=root.bottom+1};});
    }""")
    assert all(item["valid"] for item in result), result
    return True


def mount(page, experience, reduced=False):
    page.evaluate("([id,reduced])=>testMount(id,{reducedMotion:reduced,forcedColors:false})", [experience, reduced])
    frozen(page)
    page.evaluate("controller.setActive(true)")
    frozen(page)


def route(start, target):
    walls = {(2, 4), (4, 6), (6, 2), (8, 4), (10, 2), (6, 6)}
    queue = deque([(start, [])])
    seen = {start}
    while queue:
        (x, y), path = queue.popleft()
        if (x, y) == target:
            return path
        for dx, dy, key in [(-1, 0, "ArrowLeft"), (1, 0, "ArrowRight"), (0, -1, "ArrowUp"), (0, 1, "ArrowDown")]:
            point = (x + dx, y + dy)
            if 0 <= point[0] <= 12 and 0 <= point[1] <= 8 and point not in seen and point not in walls:
                queue.append((point, path + [key]))
                seen.add(point)
    raise AssertionError("No route to visible signal")


def solve_browser_game(page, captures, prefix, touch=False):
    for fragment in range(8):
        values = page.locator(".sim-position").inner_text()
        x, y, tx, ty = [int(n) - 1 for n in re.findall(r"\d+", values)]
        for key in route((x, y), (tx, ty)):
            if touch:
                page.get_by_role("button", name=key.removeprefix("Arrow"), exact=True).tap()
            else:
                page.locator("canvas").focus()
                page.keyboard.press(key)
        assert page.locator(".sim-score").inner_text().startswith(f"{fragment + 1} / 8"), values
        if fragment == 3:
            capture(page, captures, f"{prefix}-game-mid.png")
            if int(prefix) < 600:
                assert page.locator(".sim-signature-frame").evaluate("""el=>{
                  const box=el.getBoundingClientRect(),root=document.getElementById('root').getBoundingClientRect();
                  return box.top>=root.top && box.bottom<=root.bottom && box.right<=root.right;
                }"""), "Recovered mark is outside the compact view"
    assert page.locator("#root").get_attribute("data-state") == "won"
    assert "Signal found" in page.locator(".sim-result").inner_text()
    assert page.locator(".sim-hits").inner_text() == "0 noise"
    capture(page, captures, f"{prefix}-game-won.png")
    frozen(page)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--shared-css", type=Path, default=ROOT / "site" / "playground.css")
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    harness = args.artifacts / "mount-harness.html"
    shared_css = '<link rel="stylesheet" href="/test-host.css">' if args.shared_css.is_file() else ""
    harness.write_text(HARNESS.replace("SHARED_CSS", shared_css))

    class Handler(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            if path.split("?")[0] == "/":
                return str(harness)
            if path == "/test-host.css" and args.shared_css.is_file():
                return str(args.shared_css)
            if path.startswith("/assets/"):
                requested = (ROOT / "site" / path.split("?", 1)[0].removeprefix("/assets/")).resolve()
                if requested.is_relative_to(ROOT / "site"):
                    return str(requested)
            return str(args.artifacts / "not-found")

        def log_message(self, *unused):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}"
    report = {"url": url, "errors": [], "externalRequests": [], "captures": [], "viewports": []}
    try:
        with sync_playwright() as p:
            browser = p.webkit.launch(timeout=20000)
            for width, height in [(320, 740), (390, 844), (1600, 1000)]:
                print(f"Simulation/game: {width}px", flush=True)
                context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=2,
                                              has_touch=width < 600, is_mobile=width < 600)
                page = context.new_page()
                page.on("pageerror", lambda error: report["errors"].append(str(error)))
                page.on("request", lambda request: report["externalRequests"].append(request.url)
                        if not request.url.startswith(url) else None)
                page.goto(url)
                page.wait_for_function("window.harnessReady")
                if width < 600:
                    page.locator(".test-slot").evaluate("(el,height)=>el.style.height=height+'px'", 320 if width == 320 else 310)
                else:
                    page.locator(".test-slot").evaluate("el=>el.style.height='443px'")
                    page.locator("main").evaluate("el=>el.style.maxWidth='1500px'")
                if width == 320:
                    report["models"] = page.evaluate(MODEL_TESTS)
                mount(page, "agent-terrarium")
                assert page.get_by_text("Local rule-based simulation", exact=True).count() == 1
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
                assert page.locator("canvas").evaluate("el=>el.width*el.height<=1000000")
                canvas_pixels = page.locator("canvas").evaluate("el=>el.width*el.height")
                capture(page, args.artifacts, f"{width}-terrarium-ready.png")
                assert controls_fit(page, ".sim-controls button, .sim-tools button"), "Terrarium controls escape compact stage"
                page.locator("canvas").focus()
                page.keyboard.press("ArrowRight")
                page.keyboard.press("Space")
                assert "76 food" in page.locator(".sim-food").inner_text()
                page.get_by_role("button", name="Step", exact=True).click()
                assert "t 1" == page.locator(".sim-steps").inner_text()
                frozen(page)
                page.get_by_role("button", name="Reset", exact=True).click()
                assert page.locator(".sim-food").inner_text() == "72 food"
                page.get_by_role("button", name="Run", exact=True).click()
                page.wait_for_timeout(550)
                page.evaluate("controller.setActive(false)")
                frozen(page)
                page.evaluate("controller.setActive(true)")
                page.wait_for_timeout(400)
                assert page.evaluate("probe.active.size") == 1
                page.get_by_role("button", name="Pause", exact=True).click()
                frozen(page)
                page.evaluate("controller.setActive(false);controller.setActive(true)")
                frozen(page)
                page.get_by_text("Adjust the rules", exact=True).click()
                page.get_by_role("slider", name="Agents", exact=True).fill("36")
                page.get_by_role("slider", name="Exploration", exact=True).fill("80")
                page.get_by_role("slider", name="Trail memory", exact=True).fill("95")
                assert page.get_by_text("Agents: 36", exact=True).count() == 1
                page.get_by_text("Adjust the rules", exact=True).click()
                # Advance real user steps: nearby added food must actually be collected and returned.
                page.locator("canvas").focus()
                page.keyboard.press("ArrowRight")
                page.keyboard.press("Space")
                for _ in range(30):
                    page.get_by_role("button", name="Step", exact=True).click()
                assert int(page.locator(".sim-delivered").inner_text().split()[0]) > 0
                capture(page, args.artifacts, f"{width}-terrarium-paths.png")
                before_steps = page.locator(".sim-steps").inner_text()
                page.set_viewport_size({"width": width + 40, "height": height})
                page.evaluate("testResize()")
                assert page.locator(".sim-steps").inner_text() == before_steps
                page.set_viewport_size({"width": width, "height": height})
                page.evaluate("controller.resize({width:5000,height:5000,dpr:4})")
                assert page.locator(".sim-steps").inner_text() == before_steps
                assert page.locator("canvas").evaluate("el=>el.width*el.height<=1000000")
                page.evaluate("controller.setPreferences({reducedMotion:true,forcedColors:false})")
                assert page.get_by_role("button", name="Resume", exact=True).is_disabled()
                frozen(page)
                page.get_by_role("button", name="Step", exact=True).click()
                page.evaluate("abort.abort();controller.destroy();controller.destroy()")
                assert page.locator("#root").inner_text() == ""
                frozen(page)

                mount(page, "signal-noise", reduced=True)
                assert page.get_by_role("checkbox", name="Turn-based").is_checked()
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
                capture(page, args.artifacts, f"{width}-game-ready.png")
                assert controls_fit(page, ".sim-controls button, .sim-pad button"), "Game controls escape compact stage"
                page.get_by_role("button", name="Start 60 s", exact=True).click()
                frozen(page)
                solve_browser_game(page, args.artifacts, str(width), touch=width == 390)
                page.get_by_role("button", name="Play again", exact=True).click()
                assert page.locator(".sim-score").inner_text() == "0 / 8 signal"
                assert page.locator(".sim-time").inner_text() == "60 s"
                page.get_by_role("button", name="Pause", exact=True).click()
                frozen(page)
                page.evaluate("controller.setActive(false);controller.setActive(true)")
                frozen(page)
                page.evaluate("controller.setPreferences({reducedMotion:true,forcedColors:true})")
                assert page.locator(".sim-signature-mask").evaluate("el=>getComputedStyle(el).display") == "block"
                capture(page, args.artifacts, f"{width}-forced-preference.png")
                page.evaluate("controller.destroy()")
                frozen(page)

                mount(page, "signal-noise")
                page.get_by_role("button", name="Start 60 s", exact=True).click()
                frame_start = page.evaluate("probe.times.length")
                page.keyboard.down("ArrowLeft")
                page.wait_for_timeout(1050)
                page.keyboard.up("ArrowLeft")
                assert not page.locator(".sim-position").inner_text().startswith("Ring: 7, 5.")
                frame_times = page.evaluate("index=>probe.times.slice(index)", frame_start)
                assert 0 < len(frame_times) <= 32
                assert all(b - a >= 33 for a, b in zip(frame_times, frame_times[1:])), frame_times
                page.evaluate("""() => {
                  Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
                  document.dispatchEvent(new Event('visibilitychange'));
                }""")
                frozen(page)
                page.evaluate("""() => {
                  delete document.hidden;
                  document.dispatchEvent(new Event('visibilitychange'));
                }""")
                page.evaluate("controller.setActive(false)")
                frozen(page)
                page.evaluate("controller.setActive(true)")
                page.wait_for_timeout(500)
                page.get_by_role("button", name="Pause", exact=True).click()
                frozen(page)
                assert page.evaluate("probe.peak") == 1
                page.get_by_role("button", name="Restart", exact=True).click()
                assert page.locator(".sim-time").inner_text() == "60 s"
                page.get_by_role("button", name="Start 60 s", exact=True).click()
                canvas = page.locator("canvas")
                bounds = canvas.bounding_box()
                page.mouse.move(bounds["x"]+bounds["width"]*.5, bounds["y"]+bounds["height"]*.5)
                page.mouse.down()
                page.mouse.move(bounds["x"]+bounds["width"]*.2, bounds["y"]+bounds["height"]*.8)
                page.wait_for_timeout(600)
                assert canvas.get_attribute("data-pointer-id") is not None
                page.evaluate("controller.setActive(false)")
                assert canvas.get_attribute("data-pointer-id") is None
                page.mouse.up()
                frozen(page)
                page.evaluate("controller.setActive(true);controller.setPreferences({reducedMotion:true,forcedColors:false})")
                assert page.locator("#root").get_attribute("data-state") == "paused"
                frozen(page)
                page.evaluate("controller.destroy();abort.abort()")
                frozen(page)
                assert page.evaluate("failures") == [], page.evaluate("failures")
                for _ in range(3):
                    mount(page, "agent-terrarium")
                    page.evaluate("controller.destroy()")
                    mount(page, "signal-noise")
                    page.evaluate("controller.destroy()")
                frozen(page)
                if width == 1600:
                    # Aborting while fonts are unresolved must never remount or register late work.
                    for experience in ["agent-terrarium", "signal-noise"]:
                        page.evaluate("""id=>{
                          window.originalLoad=document.fonts.load.bind(document.fonts);
                          document.fonts.load=()=>new Promise(resolve=>{window.finishFont=resolve;});
                          window.pendingMount=testMount(id);
                        }""", experience)
                        page.wait_for_function("typeof window.finishFont==='function'")
                        page.evaluate("abort.abort();finishFont([{status:'loaded'}])")
                        page.evaluate("pendingMount")
                        assert page.locator("#root").inner_text() == ""
                        page.evaluate("document.fonts.load=originalLoad;delete window.finishFont")
                        frozen(page)
                    mount(page, "signal-noise")
                    page.get_by_role("button", name="Start 60 s", exact=True).click()
                    page.wait_for_function("document.getElementById('root').dataset.state==='lost'", timeout=75000)
                    assert page.locator(".sim-time").inner_text() == "0 s"
                    capture(page, args.artifacts, "1600-game-timeout.png")
                    frozen(page)
                    page.get_by_role("button", name="Play again", exact=True).click()
                    assert page.locator(".sim-score").inner_text() == "0 / 8 signal"
                    page.evaluate("controller.destroy()")
                    frozen(page)
                    # Unsupported canvas is a visible diagnosed failure, not an empty success.
                    failure = page.evaluate("""async()=>{
                      const original=HTMLCanvasElement.prototype.getContext;
                      HTMLCanvasElement.prototype.getContext=()=>null;
                      try {await testMount('agent-terrarium');}
                      catch(error){return String(error);}
                      finally{HTMLCanvasElement.prototype.getContext=original;}
                    }""")
                    assert "Canvas 2D" in failure
                    assert "could not open" in page.locator("#status").inner_text()
                    assert len(page.evaluate("failures")) == 1
                    frozen(page)
                report["viewports"].append({
                    "width": width,
                    "height": height,
                    "contentBox": page.locator("#root").evaluate("el=>({width:el.clientWidth,height:el.clientHeight})"),
                    "peakScheduledWork": page.evaluate("probe.peak"),
                    "scheduledAfterDestroy": page.evaluate("probe.active.size"),
                    "sampledMinimumFrameMs": min(b - a for a, b in zip(frame_times, frame_times[1:])),
                    "terrariumBackingPixels": canvas_pixels,
                    "compactControlsFit": True,
                    "keyboardWin": width != 390,
                    "touchWin": width == 390,
                })
                context.close()
            browser.close()
        assert not report["errors"], report["errors"]
        assert not report["externalRequests"], report["externalRequests"]
        report["captures"] = sorted(path.name for path in args.artifacts.glob("*.png"))
        report["forcedColorsBoundary"] = "WebKit verifies preference propagation and system-color/mask styles, not native OS high-contrast rendering."
        (args.artifacts / "simulation-game-report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
