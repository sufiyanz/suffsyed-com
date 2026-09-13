"""Real-photo pixel, lifecycle and responsive tests using a temporary mount fixture.

Run with the existing Playwright environment:
  python tools/test_playground_photo_tools.py --artifacts /absolute/session/files/photo-tests

Serves this worktree only on an ephemeral 127.0.0.1 port; never builds or changes docs.
"""
import argparse
import base64
import hashlib
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import threading
import time
from urllib.parse import unquote, urlsplit

from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
IDS = ("pocket-darkroom", "generative-postcard")


class Gallery(HTMLParser):
    def __init__(self):
        super().__init__()
        self.photos = []
        self.plate = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "figure" and attrs.get("class") == "photograph":
            self.plate = attrs["id"]
        if tag == "img" and self.plate:
            src = attrs["srcset"].split(",")[0].strip().split()[0]
            with Image.open(ROOT / "docs" / src.lstrip("/")) as image:
                width, height = image.size
            self.photos.append(dict(id=self.plate, src=src, alt=attrs["alt"],
                                    title=f"{self.plate.replace('-', ' ').title()} / {attrs['alt']}",
                                    width=width, height=height))
            self.plate = None


def real_data():
    gallery = Gallery()
    gallery.feed((ROOT / "docs/lightworks/index.html").read_text())
    rows = json.loads((ROOT / "docs/assets/search-index.json").read_text())
    passages = []
    for row in rows:
        passage = next(p for p in row["passages"] if p["kind"] == "p" and 80 <= len(p["text"]) <= 320)
        passages.append(dict(id=f"{row['slug']}:{passage['id']}", text=passage["text"],
                             title=row["title"], href=f"{row['url']}#{passage['id']}"))
    assert len(gallery.photos) == 22 and len(passages) == 20
    return dict(photos=gallery.photos, passages=passages)


HARNESS = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Photo experience test fixture</title>
<link rel="stylesheet" href="/assets/journal.css">
__SHARED__
<style>
body{padding:12px;background:var(--cp-bg);color:var(--cp-text)}
#fixture-shell{position:static;display:block;padding:0;overflow:visible}
#fixture{width:100%;max-width:1000px;height:400px;min-height:0;margin:auto}
#status{font:14px var(--font-technical);padding:12px}
</style></head><body><div id="fixture-shell" class="pg-shell"><div id="fixture"></div></div><p id="status" role="status"></p>
<script type="module">
window.fixtureData = __DATA__;
window.mountPhoto = async (id, options = {}) => {
  window.abortPhoto?.abort();
  const root = document.querySelector('#fixture');
  root.replaceChildren(); root.scrollTop = 0; root.dataset.experience = id;
  document.querySelector('#experience-style')?.remove();
  const css = document.createElement('link'); css.id = 'experience-style'; css.rel = 'stylesheet';
  css.href = '/site/playground/' + id + '.css'; document.head.append(css);
  await new Promise((resolve, reject) => {css.onload = resolve; css.onerror = reject;});
  const mod = await import('/site/playground/' + id + '.js');
  window.abortPhoto = new AbortController();
  window.failures = []; window.statuses = []; window.mounted = false;
  const data = structuredClone(fixtureData);
  if (options.empty) data[options.empty] = [];
  if (options.bad) data.photos[0].src = '/missing-photo.webp';
  if (options.slow) data.photos[0].src += '?slow=1';
  if (options.crossOrigin) data.photos[0].src = 'https://invalid.example/forbidden.webp';
  window.pending = mod.mount(root, {
    signal: abortPhoto.signal, seed: options.seed ?? 12871, random: () => .5,
    preferences: {reducedMotion:false,forcedColors:false},
    palette: {forest:'#1B2915',green:'#305831',stone:'#D7CDB8',paper:'#EFEDE6',white:'#FFFFFF',ink:'#191919'},
    data, setStatus: message => {statuses.push(message); document.querySelector('#status').textContent = message;},
    reportError: message => {failures.push(message); document.querySelector('#status').textContent = message;}
  });
  if (options.abort) abortPhoto.abort();
  window.controller = await pending;
  if (options.active !== false) controller.setActive(true);
  window.mounted = true;
};
window.resizePhoto = () => controller.resize({width:fixture.clientWidth,height:fixture.clientHeight,dpr:devicePixelRatio});
window.ready = true;
</script></body></html>"""

PROBE = """(() => {
  const probe = window.photoProbe = {paints:0, timers:new Set(), urls:new Set(), texts:[], clips:[]};
  for (const name of ['putImageData','drawImage','fillText','fillRect']) {
    const original = CanvasRenderingContext2D.prototype[name];
    CanvasRenderingContext2D.prototype[name] = function(...args) {
      if(this.canvas.closest('[data-experience]')) {
        probe.paints++;
        if(name === 'fillText') {
          probe.texts.push({text:args[0],font:this.font});
          const m=this.measureText(args[0]), t=this.getTransform();
          if ((args[1]+m.width)*t.a>this.canvas.width+.5
              || (args[2]+m.actualBoundingBoxDescent)*t.d>this.canvas.height+.5
              || (args[2]-m.actualBoundingBoxAscent)*t.d<-.5) probe.clips.push(args[0]);
        }
      }
      return original.apply(this,args);
    };
  }
  const timeout = window.setTimeout, clear = window.clearTimeout;
  window.setTimeout = function(fn, ms, ...args) {
    if (!new Error().stack.includes('photo-tools.js')) return timeout(fn,ms,...args);
    const id = timeout(() => {probe.timers.delete(id); fn(...args);},ms);
    probe.timers.add(id); return id;
  };
  window.clearTimeout = id => {probe.timers.delete(id);clear(id);};
  const create = URL.createObjectURL, revoke = URL.revokeObjectURL;
  URL.createObjectURL = blob => {const url=create(blob);probe.urls.add(url);return url;};
  URL.revokeObjectURL = url => {probe.urls.delete(url);revoke(url);};
  for (const method of ['setItem','getItem','removeItem']) {
    Storage.prototype[method] = () => {throw new Error('Storage is forbidden in photo tools');};
  }
})();"""


def source_hashes():
    paths = [*ROOT.glob("content/**/*"), *ROOT.glob("docs/assets/img/*"),
             *ROOT.glob("docs/assets/responsive/*"), *ROOT.glob("site/fonts/*"),
             ROOT / "site/suff-syed-signature.svg"]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file()}


def mount(page, identifier, **options):
    page.evaluate("([id,options]) => mountPhoto(id,options)", [identifier, options])
    page.wait_for_function("window.mounted")
    page.wait_for_timeout(100)


def bitmap(page):
    data = page.locator("#fixture canvas").evaluate("c=>c.toDataURL('image/png').split(',')[1]")
    return Image.open(io.BytesIO(base64.b64decode(data))).convert("RGB")


def changed(first, second):
    assert first.size == second.size
    return sum(ImageStat.Stat(ImageChops.difference(first, second)).mean) / 3


def slider(page, name, value):
    page.get_by_role("slider", name=name, exact=True).evaluate("""(el, value) => {
      el.value=value; el.dispatchEvent(new Event('input',{bubbles:true}));
    }""", value)
    page.wait_for_timeout(100)


def frozen(page):
    before = page.evaluate("({paints:photoProbe.paints,timers:photoProbe.timers.size,urls:photoProbe.urls.size})")
    page.wait_for_timeout(220)
    after = page.evaluate("({paints:photoProbe.paints,timers:photoProbe.timers.size,urls:photoProbe.urls.size})")
    assert before == after and after["timers"] == after["urls"] == 0, after


def geometry(page):
    info = page.evaluate("""() => {
      const root=document.querySelector('#fixture'), canvas=root.querySelector('canvas');
      const r=root.getBoundingClientRect(), c=canvas.getBoundingClientRect();
      return {height:r.height, overflow:document.documentElement.scrollWidth>innerWidth,
        rootOverflow:root.scrollWidth>root.clientWidth, scrollWidth:root.scrollWidth, clientWidth:root.clientWidth,
        aspect:Math.abs(c.width/c.height-canvas.width/canvas.height),
        pixels:canvas.width*canvas.height, previewVisible:c.top>=r.top && c.bottom<=r.bottom,
        small:[...root.querySelectorAll('button,input,select,a')].filter(el=>{
          const b=el.getBoundingClientRect();return b.width<44 || b.height<44;
        }).map(el=>({tag:el.tagName,label:el.getAttribute('aria-label'),width:el.getBoundingClientRect().width,height:el.getBoundingClientRect().height})),
        outside:[...root.querySelectorAll('*')].filter(el=>el.getBoundingClientRect().right>r.right+1 || el.scrollWidth>el.clientWidth+1).map(el=>({tag:el.tagName,cls:el.className,width:el.getBoundingClientRect().width,scroll:el.scrollWidth,client:el.clientWidth}))};
    }""")
    assert info["height"] in [310,320,400] and not info["overflow"] and not info["rootOverflow"], info
    assert info["pixels"] <= 1000000 and not info["small"], info
    assert info["aspect"] < .03, info
    if info["clientWidth"] >= 620:
        assert info["previewVisible"], info
    return info


def export(page, folder, identifier):
    expected_size = bitmap(page).size
    with page.expect_download() as event:
        page.get_by_role("button", name="Download PNG", exact=True).click()
    download = event.value
    assert download.suggested_filename == f"{identifier}.png"
    target = folder / download.suggested_filename
    download.save_as(target)
    with Image.open(target) as image:
        assert image.format == "PNG" and image.size == expected_size
    assert page.evaluate("photoProbe.urls.size") == 0


def test_darkroom(page, folder):
    mount(page, IDS[0], active=False)
    initial = bitmap(page)
    frozen(page)
    page.evaluate("controller.setActive(true)")
    slider(page, "Exposure", 1)
    exposed = bitmap(page)
    assert changed(initial, exposed) > 8
    assert sum(ImageStat.Stat(exposed).mean) > sum(ImageStat.Stat(initial).mean)
    slider(page, "Grain", 32)
    grain = bitmap(page)
    assert changed(exposed, grain) > 3
    frozen(page)
    slider(page, "Contrast", 20)
    assert changed(grain, bitmap(page)) > 2
    slider(page, "Contrast", 0)
    assert changed(grain, bitmap(page)) == 0, "Grain shifted when another slider returned to its original value."
    slider(page, "Forest duotone", 100)
    assert changed(grain, bitmap(page)) > 10
    page.get_by_role("button", name="Show original", exact=True).click()
    page.wait_for_timeout(100)
    assert changed(initial, bitmap(page)) == 0
    page.get_by_role("button", name="Reset to original", exact=True).click()
    page.wait_for_timeout(100)
    assert changed(initial, bitmap(page)) == 0
    assert page.get_by_role("slider", name="Exposure", exact=True).input_value() == "0"
    page.get_by_role("slider", name="Exposure", exact=True).focus()
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(100)
    assert page.get_by_role("slider", name="Exposure", exact=True).input_value() == "0.1"
    page.evaluate("controller.setActive(false)")
    slider(page, "Exposure", 1.5)
    frozen(page)
    page.evaluate("controller.resize({width:390,height:400,dpr:4})")
    frozen(page)
    page.evaluate("controller.setActive(true)")
    page.wait_for_timeout(100)
    assert page.locator("canvas").evaluate("c=>c.width*c.height<=1000000")
    page.evaluate("resizePhoto()")
    page.wait_for_timeout(100)
    assert changed(initial, bitmap(page)) > 8
    before = page.evaluate("photoProbe.paints")
    page.get_by_role("slider", name="Exposure", exact=True).evaluate("""el=>{
      for(let i=0;i<100;i++){el.value=(i%20)/10;el.dispatchEvent(new Event('input'));}
    }""")
    page.wait_for_timeout(100)
    assert page.evaluate("photoProbe.paints") - before == 1, "Rapid input was not coalesced."
    export(page, folder, IDS[0])
    assert not page.evaluate("failures"), page.evaluate("failures")


def test_postcard(page, folder):
    mount(page, IDS[1])
    initial = bitmap(page)
    frozen(page)
    assert page.evaluate("""() => {
      const selected=fixtureData.passages.find(p=>p.id===document.querySelector('[aria-label=Passage]').value);
      return selected.text.includes(document.querySelector('.photo-quote').textContent)
        && document.querySelector('.photo-source').href===new URL(selected.href,location.href).href;
    }""")
    assert page.evaluate("photoProbe.texts.some(row=>row.font.includes('Newsreader'))")
    assert page.evaluate("photoProbe.texts.some(row=>row.font.includes('DM Mono'))")
    mount(page, IDS[1])
    assert changed(initial, bitmap(page)) == 0, "Same seed did not reproduce the same card."
    page.get_by_role("button", name="New variation", exact=True).click()
    page.wait_for_timeout(100)
    variation = bitmap(page)
    assert initial.size != variation.size or changed(initial, variation) > .2
    frozen(page)
    slider(page, "Crop position", 0)
    assert changed(variation, bitmap(page)) > 1
    page.get_by_role("combobox", name="Accent", exact=True).select_option("ink")
    page.wait_for_timeout(100)
    slider(page, "Photo balance", 65)
    assert bitmap(page).height > variation.height
    page.get_by_role("combobox", name="Passage", exact=True).select_option(index=1)
    page.wait_for_timeout(100)
    assert not page.evaluate("failures"), page.evaluate("failures")
    export(page, folder, IDS[1])


def test_lifecycle(page, url):
    for identifier in IDS:
        mount(page, identifier, bad=True)
        assert page.locator(".photo-error").is_visible()
        page.get_by_role("combobox", name="Photograph", exact=True).select_option(index=1)
        page.wait_for_function("document.querySelector('canvas').width>1 && document.querySelector('.photo-error').hidden")
        page.wait_for_timeout(120)
        assert page.get_by_role("button", name="Download PNG", exact=True).is_enabled()
        mount(page, identifier, crossOrigin=True)
        assert page.locator(".photo-error").is_visible()
        mount(page, identifier, empty="photos")
        assert page.locator(".photo-error").is_visible()
        mount(page, identifier, abort=True)
        assert page.locator("#fixture").inner_html() == ""
        page.evaluate("controller.destroy();controller.destroy();controller.resize({width:100,height:200,dpr:1})")
        frozen(page)
        page.evaluate("id=>{void mountPhoto(id,{slow:true});}", identifier)
        page.wait_for_function("document.querySelector('#fixture canvas')")
        page.evaluate("abortPhoto.abort()")
        page.wait_for_function("window.mounted")
        assert page.locator("#fixture").inner_html() == ""
        frozen(page)
        mount(page, identifier)
        page.evaluate("""() => {
          const select=document.querySelector('[aria-label=Photograph]');
          select.selectedIndex=1;select.dispatchEvent(new Event('change'));
          select.selectedIndex=2;select.dispatchEvent(new Event('change'));
          controller.resize({width:390,height:400,dpr:2});
        }""")
        page.wait_for_function("document.querySelector('canvas').getAttribute('aria-label')?.includes(fixtureData.photos[2].alt)")
        page.evaluate("""() => {
          const select=document.querySelector('[aria-label=Photograph]');
          select.selectedIndex=3;select.dispatchEvent(new Event('change'));
          controller.setActive(false);
        }""")
        frozen(page)
        page.evaluate("controller.setActive(true)")
        page.wait_for_function("document.querySelector('canvas').getAttribute('aria-label')?.includes(fixtureData.photos[3].alt)")
        page.evaluate("abortPhoto.abort();controller.destroy();controller.destroy()")
        frozen(page)
        assert page.locator("#fixture").inner_html() == ""
    mount(page, IDS[1], empty="passages")
    assert page.locator(".photo-error").is_visible()
    for identifier in IDS:
        page.evaluate("""() => {
          window.readback=CanvasRenderingContext2D.prototype.getImageData;
          CanvasRenderingContext2D.prototype.getImageData = () => {throw new DOMException('Canvas read blocked','SecurityError');};
        }""")
        mount(page, identifier)
        assert page.locator(".photo-error").is_visible()
        assert page.get_by_role("button", name="Download PNG", exact=True).is_disabled()
        page.evaluate("() => {CanvasRenderingContext2D.prototype.getImageData=window.readback;}")
        page.get_by_role("button", name="Reload", exact=False).click()
        page.wait_for_function("document.querySelector('.photo-error').hidden")
        page.wait_for_timeout(100)
        assert page.get_by_role("button", name="Download PNG", exact=True).is_enabled()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--data", type=Path, help="Optional authoritative v1 host data, using this worktree's existing assets.")
    parser.add_argument("--shared-css", type=Path, help="Optional read-only shared host stylesheet.")
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    sources = source_hashes()
    authoritative = args.data or ROOT / "docs/assets/playground-data.json"
    data = json.loads(authoritative.read_text()) if authoritative.exists() else real_data()
    harness = HARNESS.replace("__DATA__", json.dumps(data).replace("<", "\\u003c"))
    shared_css = args.shared_css or ROOT / "site/playground.css"
    harness = harness.replace("__SHARED__", '<link rel="stylesheet" href="/__photo_shared.css">' if shared_css.exists() else "")
    fixture_path = args.artifacts / "photo-mount-harness.html"
    fixture_path.write_text(harness)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, *args):
            pass

        def do_GET(self):
            if urlsplit(self.path).query == "slow=1":
                time.sleep(.3)
            try:
                super().do_GET()
            except (BrokenPipeError, ConnectionResetError):
                # Abort tests deliberately close requests before their responses arrive.
                pass

        def translate_path(self, path):
            route = unquote(urlsplit(path).path)
            if route == "/__photo_harness":
                return str(fixture_path)
            if route == "/__photo_shared.css":
                return str(shared_css)
            if route.startswith("/assets/"):
                return super().translate_path("/docs" + route)
            return super().translate_path(path)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    errors, external, report = [], [], []
    try:
        with sync_playwright() as p:
            browser = p.webkit.launch(timeout=20000)
            context = browser.new_context(viewport={"width":980,"height":760}, device_scale_factor=2)
            context.add_init_script(PROBE)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: external.append(request.url)
                    if not request.url.startswith((url, "blob:")) else None)
            page.goto(url + "/__photo_harness")
            page.wait_for_function("window.ready")
            test_darkroom(page, args.artifacts)
            print("PASS darkroom pixels, stable grain, keyboard, reset, inactive resize and PNG", flush=True)
            test_postcard(page, args.artifacts)
            print("PASS postcard source attribution, deterministic layout, controls and PNG", flush=True)
            test_lifecycle(page, url)
            print("PASS empty/failed sources, switch/resize races, inactive and abort cleanup", flush=True)
            mount(page, IDS[0])
            for index, photo in enumerate(data["photos"]):
                page.get_by_role("combobox", name="Photograph", exact=True).select_option(index=index)
                page.wait_for_function("alt=>document.querySelector('canvas').getAttribute('aria-label')?.includes(alt)", arg=photo["alt"])
                assert page.locator("canvas").evaluate("c=>c.width*c.height<=1000000")
            assert not page.evaluate("failures"), page.evaluate("failures")
            mount(page, IDS[1])
            for index in range(len(data["passages"])):
                page.get_by_role("combobox", name="Passage", exact=True).select_option(index=index)
                page.wait_for_timeout(60)
                assert page.locator("canvas").evaluate("c=>c.width*c.height<=1000000")
                actual = page.locator(".photo-quote").inner_text()
                assert actual and actual in data["passages"][index]["text"]
                assert page.get_by_role("button", name="Download PNG", exact=True).is_enabled()
            assert not page.evaluate("failures"), page.evaluate("failures")
            for width in [320,390,980]:
                page.set_viewport_size({"width":width,"height":760})
                for identifier in IDS:
                    mount(page, identifier)
                    page.evaluate("resizePhoto()")
                    page.wait_for_timeout(120)
                    page.locator("#fixture").screenshot(path=str(args.artifacts / f"{identifier}-{width}-preview.png"))
                    info = geometry(page)
                    page.locator("#fixture").evaluate("""el=>{
                      const scroll=el.dataset.photoLayout==='wide'?el.querySelector('.photo-controls'):el;
                      scroll.scrollTop=scroll.scrollHeight;
                    }""")
                    page.locator("#fixture").screenshot(path=str(args.artifacts / f"{identifier}-{width}-controls.png"))
                    page.evaluate("controller.setPreferences({reducedMotion:true,forcedColors:true})")
                    assert page.locator("#fixture").get_attribute("data-photo-contrast") == "forced"
                    frozen(page)
                    page.evaluate("controller.setPreferences({reducedMotion:false,forcedColors:false})")
                    report.append(dict(id=identifier,width=width,**info))
            for width, height in [(304,320),(374,310)]:
                page.set_viewport_size({"width":width,"height":700})
                page.locator("#fixture").evaluate("(el,height)=>el.style.height=height+'px'", height)
                for identifier in IDS:
                    mount(page, identifier)
                    page.evaluate("resizePhoto()")
                    page.wait_for_timeout(100)
                    report.append(dict(id=identifier,width=width,**geometry(page)))
                    page.locator("#fixture").screenshot(path=str(args.artifacts / f"{identifier}-compact-{width-24}x{height}.png"))
            assert not errors, errors
            assert not external, external
            assert not page.evaluate("photoProbe.clips"), page.evaluate("photoProbe.clips")
            context.close()
            # A fresh context proves explicit, recoverable local-font failure.
            context = browser.new_context()
            page = context.new_page()
            page.route("**/*.woff2", lambda route: route.abort())
            page.goto(url + "/__photo_harness")
            page.wait_for_function("window.ready")
            mount(page, IDS[1])
            assert page.locator(".photo-error").is_visible()
            assert page.get_by_role("button", name="Download PNG", exact=True).is_enabled()
            page.unroute("**/*.woff2")
            page.get_by_role("button", name="Reload image & fonts", exact=True).click()
            page.wait_for_timeout(500)
            browser.close()
        assert sources == source_hashes(), "Original source assets changed."
        (args.artifacts / "photo-results.json").write_text(json.dumps(
            dict(geometry=report,sourceHashes=sources,errors=errors,externalRequests=external), indent=2))
        print(f"PASS 320/390/980 plus compact 280x320/350x310 roots, 44px controls, fonts, <=1Mpx, no external requests; {len(sources)} source hashes unchanged.")
        print(f"Artifacts: {args.artifacts}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
