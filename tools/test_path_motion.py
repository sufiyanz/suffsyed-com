"""Native SVG followers: rendered-path alignment, topology, clocks and lifecycle."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from foundation_art import ribbon

WIDTHS = (320, 390, 820, 1024, 1280, 1440, 1600)
ARTICLE = "/futurememo/qubit-teams-the-future-built-by-two-people-using-ai/"
PROBE = """window.pathFrames = 0;
const request = window.requestAnimationFrame;
window.requestAnimationFrame = callback => {window.pathFrames++; return request(callback);};"""


def wireform_fixture():
    return f'''<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Retained wireform test fixture</title>
<link rel="stylesheet" href="/assets/foundation.css"><link rel="stylesheet" href="/assets/frame.css">
<script type="module" src="/assets/motion.js"></script></head><body class="foundation"><main>
<section class="cover"><div class="hero-field motion-field" data-motion-scene>{ribbon("fixture-ribbon")}</div></section>
<div class="writing-plane--2" style="height:100vh;margin-top:100vh"></div>
</main></body></html>'''

GEOMETRY = """({cycle}) => {
  const svg = document.querySelector('.hero-geometry');
  const carrier = svg.querySelector('[data-motion-track]');
  const animation = carrier.getAnimations()[0];
  const center = el => {const r=el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};};
  const transform = (p,m) => ({x:m.a*p.x+m.c*p.y+m.e,y:m.b*p.x+m.d*p.y+m.f});
  const distance = (a,b) => Math.hypot(a.x-b.x,a.y-b.y);
  const results = [];
  for (const marker of svg.querySelectorAll('[data-motion-follower]')) {
    const route = document.getElementById(marker.dataset.motionFollower);
    const circle = marker.querySelector('circle');
    const motion = marker.querySelector('animateMotion');
    if (motion.querySelector('mpath').getAttribute('href') !== '#'+route.id ||
        route.parentElement !== marker.parentElement || !route.matches('path[data-motion-route="closed"]'))
      throw new Error('Follower is not bound to its visible carrier route');
    const style = getComputedStyle(route);
    if (style.display === 'none' || style.visibility !== 'visible' || style.stroke === 'none' ||
        Number(style.opacity) === 0 || parseFloat(style.strokeWidth) <= 0)
      throw new Error('Follower route must actually be drawn');
    const numbers = route.getAttribute('d').match(/-?\\d+(?:\\.\\d+)?/g).map(Number);
    const vertices = [];
    for (let i=0;i<numbers.length;i+=2) vertices.push({x:numbers[i],y:numbers[i+1]});
    const length = route.getTotalLength(), duration = motion.getSimpleDuration();
    const sample = (time, pose) => {
      if (cycle) {
        svg.setCurrentTime(time);
        animation.currentTime = pose;
      }
      const matrix = route.getScreenCTM(), point = center(circle);
      const points = vertices.map(p=>transform(p,matrix));
      let nearest = Infinity;
      for (let i=0;i<points.length;i++) {
        const a=points[i],b=points[(i+1)%points.length],dx=b.x-a.x,dy=b.y-a.y;
        const u=Math.max(0,Math.min(1,((point.x-a.x)*dx+(point.y-a.y)*dy)/(dx*dx+dy*dy)));
        nearest=Math.min(nearest,distance(point,{x:a.x+u*dx,y:a.y+u*dy}));
      }
      const local=transform(point,matrix.inverse());
      const expected=cycle ? route.getPointAtLength((time%duration)/duration*length) : vertices[0];
      return {time,pose,pathError:nearest,phaseError:distance(point,transform(expected,matrix)),local};
    };
    const samples = cycle ? Array.from({length:97},(_,i)=>sample(duration*i/96,(i*1873)%24000)) : [sample(0,0)];
    let travel=0;
    for (let i=1;i<samples.length;i++) travel+=distance(samples[i-1].local,samples[i].local);
    const seam = cycle ? [duration-.03,duration,duration+.03].map(t=>sample(t,12000)) : [];
    const tinySeam = cycle ? [sample(duration-.001,12000),sample(duration+.001,12000)] : [];
    let tangent=1;
    if (cycle) {
      const a=seam[0].local,b=seam[1].local,c=seam[2].local;
      tangent=((b.x-a.x)*(c.x-b.x)+(b.y-a.y)*(c.y-b.y))/(distance(a,b)*distance(b,c));
    }
    results.push({route:route.id,duration,length,samples,travel,closure:distance(samples[0].local,samples.at(-1).local),
      maxEdge:Math.max(...vertices.map((v,i)=>distance(v,vertices[(i+1)%vertices.length]))),
      tangent,seamStep:cycle ? distance(tinySeam[0].local,tinySeam[1].local) : 0});
  }
  return results;
}"""

ANCHORS = """() => [...document.querySelectorAll('[data-motion-anchor]')].map(marker => {
  const route=document.getElementById(marker.dataset.motionAnchor);
  const [x,y]=marker.dataset.anchorPoint.split(' ').map(Number);
  if (route.parentElement !== marker.parentElement) throw new Error('Anchor and axes have different carriers');
  const p=new DOMPoint(x,y).matrixTransform(route.getScreenCTM()),r=marker.getBoundingClientRect();
  return {anchor:route.id,error:Math.hypot(r.x+r.width/2-p.x,r.y+r.height/2-p.y)};
})"""

CLOCKS = """() => ({
  waapi:document.getAnimations().map(a=>({time:a.currentTime,state:a.playState})),
  native:[...document.querySelectorAll('[data-motion-scene] svg')].map(svg=>({
    time:svg.getCurrentTime(),paused:svg.animationsPaused(),
    followers:svg.querySelectorAll('[data-motion-follower]').length,
    started:[...svg.querySelectorAll('[data-motion-follower]')].some(g=>!g.hasAttribute('transform'))
  })),
  active:document.querySelectorAll('[data-motion-state="running"]').length,
  raf:window.pathFrames
})"""


def freeze(page):
    page.wait_for_function("document.getAnimations().every(a=>!a.pending)", polling=50)
    before = page.evaluate(CLOCKS)
    page.wait_for_timeout(250)
    after = page.evaluate(CLOCKS)
    assert before == after, (before, after)
    assert all(clock["paused"] for clock in after["native"]), after
    assert all(clock["state"] != "running" for clock in after["waapi"]), after
    return after


def hold_geometry(page):
    # Test-only clock control for deterministic samples, not a product pause UI.
    page.evaluate("""document.getAnimations().forEach(a=>a.pause());
      document.querySelectorAll('[data-motion-scene] svg').forEach(svg=>svg.pauseAnimations());""")
    return freeze(page)


def aligned(results, cycle):
    assert len(results) == 3
    for result in results:
        assert max(s["pathError"] for s in result["samples"]) <= 1, result
        assert max(s["phaseError"] for s in result["samples"]) <= 1, result
        assert result["maxEdge"] < 24, "A route must not bridge the open half with a chord"
        if cycle:
            assert result["travel"] >= result["length"] * .97, result
            assert result["closure"] <= .01 and result["seamStep"] < .25, result
            assert result["tangent"] > .98, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8774")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    evidence = {"widths": {}, "hiddenCoverage": "Synthetic visibility event; headless WebKit has no native hidden tab."}
    fixture_url = args.url + "/__test_wireform__/"
    fixture = wireform_fixture()
    evidence["wireformCoverage"] = "In-memory intercepted fixture; not a published route or homepage element."
    with sync_playwright() as p:
        browser = p.webkit.launch()
        for width in WIDTHS:
            context = browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="no-preference")
            context.add_init_script(PROBE)
            context.route(fixture_url, lambda route: route.fulfill(status=200, content_type="text/html", body=fixture))
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(fixture_url, wait_until="networkidle")
            page.wait_for_timeout(100)
            assert page.locator("[data-motion-toggle], .motion-toggle").count() == 0
            assert page.locator("html").get_attribute("data-motion-initialized") == "true"
            hold_geometry(page)
            results = page.evaluate(GEOMETRY, {"cycle": True})
            aligned(results, cycle=True)
            evidence["widths"][width] = {"followers": results, "anchors": []}
            if width in (390, 1440):
                for time in (0, 6, 12):
                    page.evaluate("""t=>{document.querySelector('.hero-geometry').setCurrentTime(t);
                      document.querySelector('.hero-geometry [data-motion-track]').getAnimations()[0].currentTime=12000;}""", time)
                    page.screenshot(path=str(args.output / f"paths-{width}-{time}.png"))
            # Three different native route durations, one SVG clock, <=2 WAAPI carriers.
            assert page.locator("animateMotion").count() == 3
            assert page.evaluate("document.getAnimations().length") <= 2
            page.reload(wait_until="networkidle")
            start = page.evaluate(CLOCKS)
            page.wait_for_timeout(200)
            running = page.evaluate(CLOCKS)
            assert running["active"] <= 2 and any(not c["paused"] for c in running["native"])
            assert running["native"][0]["time"] > start["native"][0]["time"]
            assert running["native"][0]["started"]
            assert running["raf"] == 0
            page.locator(".writing-plane--2").evaluate("el=>el.scrollIntoView({block:'center'})")
            page.wait_for_timeout(150)
            freeze(page)
            page.evaluate("scrollTo(0,0)")
            page.wait_for_timeout(150)
            assert not page.evaluate(CLOCKS)["native"][0]["paused"]
            page.evaluate("""Object.defineProperty(document,'hidden',{configurable:true,value:true});
              document.dispatchEvent(new Event('visibilitychange'));""")
            freeze(page)
            page.evaluate("delete document.hidden; document.dispatchEvent(new Event('visibilitychange'))")
            page.wait_for_timeout(100)
            assert not page.evaluate(CLOCKS)["native"][0]["paused"]
            for media in ({"reduced_motion": "reduce"},
                          {"reduced_motion": "no-preference", "forced_colors": "active"},
                          {"forced_colors": "none", "media": "print"}):
                page.emulate_media(**media)
                page.wait_for_timeout(100)
                assert page.locator("[data-motion-toggle]").count() == 0
                state = freeze(page)
                assert not state["waapi"] and not any(c["started"] for c in state["native"])
                if media.get("media") != "print":
                    aligned(page.evaluate(GEOMETRY, {"cycle": False}), cycle=False)
            page.emulate_media(media="screen", reduced_motion="no-preference", forced_colors="none")
            page.wait_for_timeout(150)
            assert page.evaluate(CLOCKS)["native"][0]["started"]
            assert page.evaluate(CLOCKS)["native"][0]["time"] > .1
            hold_geometry(page)
            aligned(page.evaluate(GEOMETRY, {"cycle": True}), cycle=True)
            page.reload(wait_until="networkidle")
            page.evaluate("document.documentElement.dataset.pathRestore='yes'")
            page.goto(args.url + "/futurememo/", wait_until="networkidle")
            page.go_back(wait_until="networkidle")
            assert page.locator("[data-motion-toggle]").count() == 0
            assert page.locator("html").get_attribute("data-motion-initialized") == "true"
            assert page.locator("animateMotion").count() == 3
            page.evaluate("import('/assets/motion.js?initialization-check')")
            assert page.evaluate("document.getAnimations().length") <= 2
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))")
            freeze(page)
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
            page.wait_for_timeout(100)
            assert any(not clock["paused"] for clock in page.evaluate(CLOCKS)["native"])
            # Reading pages deliberately omit decorative motion; retained origins stay bound.
            page.goto(args.url + ARTICLE, wait_until="networkidle")
            assert page.locator("[data-motion-scene], [data-motion-toggle]").count() == 0
            for route, selector in (("/futurememo/", ".arrival-field"),):
                page.goto(args.url + route, wait_until="networkidle")
                assert page.locator(".hero-field, .hero-geometry, [data-motion-follower]").count() == 0
                assert page.locator("[data-motion-scene]").count() == 1
                page.locator(selector).evaluate("el=>el.scrollIntoView({block:'center'})")
                page.wait_for_function("selector=>document.querySelector(selector).dataset.motionState==='running'", arg=selector, polling=50)
                hold_geometry(page)
                anchors = page.evaluate("""() => {
                  const nodes=[...document.querySelectorAll('[data-motion-anchor]')],results=[];
                  for(const node of nodes) {
                    const animation=node.closest('[data-motion-track]').getAnimations()[0];
                    for(const time of [0,3000,6000,12000,18000,23999,24000]) {
                      animation.currentTime=time;
                      const path=document.getElementById(node.dataset.motionAnchor);
                      const [x,y]=node.dataset.anchorPoint.split(' ').map(Number);
                      const p=new DOMPoint(x,y).matrixTransform(path.getScreenCTM()),r=node.getBoundingClientRect();
                      results.push({anchor:path.id,time,error:Math.hypot(r.x+r.width/2-p.x,r.y+r.height/2-p.y)});
                    }
                  } return results;
                }""")
                assert anchors and max(a["error"] for a in anchors) <= 1
                evidence["widths"][width]["anchors"].extend(anchors)
            assert not errors, errors
            context.close()
            context = browser.new_context(viewport={"width": width, "height": 900}, java_script_enabled=False)
            context.route(fixture_url, lambda route: route.fulfill(status=200, content_type="text/html", body=fixture))
            page = context.new_page()
            page.goto(fixture_url, wait_until="networkidle")
            assert page.locator("[data-motion-toggle]").count() == 0
            assert page.locator("html").get_attribute("data-motion-initialized") is None
            before = page.evaluate(GEOMETRY, {"cycle": False})
            aligned(before, cycle=False)
            page.wait_for_timeout(250)
            assert page.evaluate(GEOMETRY, {"cycle": False}) == before
            page.goto(args.url + "/futurememo/", wait_until="networkidle")
            assert page.locator(".hero-geometry, [data-motion-follower]").count() == 0
            anchors = page.evaluate(ANCHORS)
            assert anchors and max(a["error"] for a in anchors) <= 1
            context.close()
        browser.close()
    (args.output / "after-alignment.json").write_text(json.dumps(evidence, indent=2) + "\n")
    maximum = max(s["pathError"] for width in evidence["widths"].values()
                  for route in width["followers"] for s in route["samples"])
    print(f"PASS: {len(WIDTHS) * 3 * 97} full-cycle rendered-path samples at {len(WIDTHS)} widths; max {maximum:.6f}px error; "
          "forward traversal, closed seams, fixed origins, both clocks, media/hidden/offscreen/Back/no-JS, zero JS frames.")


if __name__ == "__main__":
    main()
