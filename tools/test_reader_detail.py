"""Actual reader hierarchy, source navigation, progress and event-driven lifecycle."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SEED = "ai-doesnt-create-slop-humans-do"
PROBE = """(() => {
  window.readerProbe = {frames: 0, durations: [], storage: 0};
  const raf = window.requestAnimationFrame;
  window.requestAnimationFrame = callback => {
    readerProbe.frames++;
    return raf.call(window, time => {
      const start = performance.now();
      callback(time);
      readerProbe.durations.push(performance.now() - start);
    });
  };
  const store = Storage.prototype.setItem;
  Storage.prototype.setItem = function(...args) {
    readerProbe.storage++;
    return store.apply(this, args);
  };
})();"""


def click_native(page, locator):
    # Locator auto-scroll moves the document for WebKit sticky descendants.
    # Scroll only the actual rail/panel, then exercise a hit-tested native click.
    locator.evaluate("""el => {
      for (let node = el.parentElement; node; node = node.parentElement) {
        if (!['auto', 'scroll'].includes(getComputedStyle(node).overflowY)) continue;
        const target = el.getBoundingClientRect(), bounds = node.getBoundingClientRect();
        if (target.top < bounds.top + 8) node.scrollTop += target.top - bounds.top - 8;
        else if (target.bottom > bounds.bottom - 8) node.scrollTop += target.bottom - bounds.bottom + 8;
      }
    }""")
    box = locator.bounding_box()
    if box["y"] < 0 or box["y"] + box["height"] > page.viewport_size["height"]:
        locator.scroll_into_view_if_needed()
        box = locator.bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    assert locator.evaluate("(el, point) => el.contains(document.elementFromPoint(...point))", [x, y])
    page.mouse.click(x, y)


def open_details(page, selector):
    details = page.locator(selector).first
    if selector == "#reader-tools" and details.is_hidden():
        return
    if not details.evaluate("node => node.open"):
        click_native(page, details.locator(":scope > summary"))


def body_position(page, fraction):
    page.evaluate("""fraction => {
      const body = document.querySelector('#essay-body').getBoundingClientRect();
      const clearance = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop);
      scrollTo(0, scrollY + body.top - clearance + fraction * (body.height - innerHeight + clearance));
    }""", fraction)
    page.wait_for_timeout(100)


def assert_anchor(page, identifier):
    assert page.evaluate("document.activeElement.id") == identifier
    bounds = page.locator("#" + identifier).bounding_box()
    clearance = page.evaluate("parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop)")
    assert bounds["y"] >= clearance - 1, (identifier, bounds, clearance)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8774")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    companions = [json.loads(path.read_text()) for path in sorted((ROOT / "content/reading-guides").glob("*.json"))]
    assert len(companions) == 20
    report = {"articles": [], "viewports": [], "hiddenProof": "synthetic visibility event, not native tab hiding"}
    errors, external, corpus_fetches = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.webkit.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        context.add_init_script(PROBE)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: external.append(request.url) if not request.url.startswith(args.url) else None)
        page.on("request", lambda request: corpus_fetches.append(request.url) if request.url.endswith("/corpus.json") else None)
        models = []
        for guide in companions:
            page.goto(f'{args.url}/futurememo/{guide["slug"]}/', wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            model = json.loads(page.locator("#essay-data").text_content())
            models.append(model)
            assert page.locator("#essay-body [data-passage]").count() == len(model["passages"])
            for section in guide["sections"]:
                click_native(page, page.locator(f'[data-guide-anchor="{section["anchor"]}"]'))
                page.wait_for_timeout(80)
                assert_anchor(page, section["anchor"])
                assert page.locator(".guide-link[aria-current]").get_attribute("data-guide-anchor") == section["anchor"], (guide["slug"], section["anchor"])
                active = page.locator(f'[data-guide-section="{section["id"]}"]')
                assert active.locator(".guide-points").evaluate("el => el.open")
                assert active.locator("ul").evaluate("el => getComputedStyle(el).listStyleType") == "disc"
                citations = active.locator(".inline-sources a")
                target = citations.first.get_attribute("href")[1:]
                click_native(page, citations.first)
                assert_anchor(page, target)
                expected_notes = [note for note in guide["notes"] if note["sectionId"] == section["id"]]
                visible = page.locator("[data-note-section]:not([hidden])")
                assert visible.count() == len(expected_notes)
                if expected_notes:
                    assert visible.get_attribute("data-note-section") == section["id"]
                    assert expected_notes[0]["text"] in visible.inner_text()
                    assert visible.locator(".reader-note-section").is_hidden()
                    target = visible.locator(".guide-sources a").first.get_attribute("href")[1:]
                    click_native(page, visible.locator(".guide-sources a").first)
                    assert_anchor(page, target)
            click_native(page, page.locator("[data-all-notes]"))
            assert page.locator("[data-note-section]:not([hidden])").count() == len(guide["notes"])
            click_native(page, page.locator("[data-all-notes]"))
            report["articles"].append({"slug": guide["slug"], "sections": len(guide["sections"]), "notes": len(guide["notes"]), "passages": len(model["passages"])})
        shortest = min(models, key=lambda model: model["words"])["slug"]
        longest = max(models, key=lambda model: model["words"])["slug"]
        for width, height in [(320, 700), (390, 844), (820, 1180), (1024, 900), (1440, 1000), (1600, 1000)]:
            page.set_viewport_size({"width": width, "height": height})
            for slug in [SEED, shortest, longest]:
                page.goto(f"{args.url}/futurememo/{slug}/", wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                assert page.locator("[data-motion-scene], [data-motion-toggle]").count() == 0
                body = page.locator("#essay-body").bounding_box()
                assert abs(body["x"] + body["width"] / 2 - width / 2) < 1
                assert body["width"] == (640 if width >= 820 else width - (48 if width == 320 else 64))
                assert page.locator(".reading-position progress").evaluate("el => el.value") == 0
                if slug == SEED:
                    page.screenshot(path=str(args.output / f"opening-{width}.png"))
                for fraction in [0, .5, 1]:
                    body_position(page, fraction)
                    actual = page.locator(".reading-position progress").evaluate("el => el.value")
                    assert abs(actual - fraction * 100) <= 1, (width, slug, fraction, actual)
                body_position(page, .5)
                if width < 1280:
                    toolbar = page.locator("#reader-tools")
                    assert not toolbar.evaluate("el => el.open")
                    header = page.locator(".site-header").bounding_box()
                    control = toolbar.locator(":scope > summary").bounding_box()
                    assert header["y"] == 0 and header["x"] == 0 and header["width"] == width
                    assert control["y"] >= header["y"] + header["height"] - 1
                    assert control["y"] + control["height"] <= 112
                    assert page.locator("[data-compact-progress]").inner_text() == "50%"
                    toolbar.locator(":scope > summary").focus()
                    page.keyboard.press("Enter")
                    open_details(page, "#ai-reading-notes")
                    panel = page.locator(".reader-tools-content").bounding_box()
                    assert panel["y"] >= control["y"] + control["height"]
                    assert panel["y"] + panel["height"] <= height
                    if slug == SEED:
                        page.screenshot(path=str(args.output / f"notes-{width}.png"))
                    page.keyboard.press("Escape")
                    assert not toolbar.evaluate("el => el.open")
                    open_details(page, "#reader-tools")
                    open_details(page, "#ai-reading-guide")
                    link = page.locator("[data-guide-anchor]").nth(2)
                    target = link.get_attribute("href")[1:]
                    click_native(page, link)
                    assert not toolbar.evaluate("el => el.open")
                    assert_anchor(page, target)
                else:
                    for selector in [".reader-guide", ".reader-notes"]:
                        rail = page.locator(selector).bounding_box()
                        assert rail["y"] >= page.locator(".site-header").bounding_box()["y"] + 48
                        assert rail["y"] + rail["height"] <= height
                        if selector == ".reader-guide":
                            assert rail["x"] + rail["width"] <= body["x"]
                        else:
                            assert rail["x"] >= body["x"] + body["width"]
                    click_native(page, page.locator("[data-guide-anchor]").nth(2))
                    page.wait_for_function("""() => document.querySelector('.guide-link[aria-current]')?.dataset.guideAnchor
                      === document.querySelectorAll('[data-guide-anchor]')[2].dataset.guideAnchor""")
                    source = page.locator('[data-guide-section][data-active="true"] .inline-sources a').first
                    click_native(page, source)
                assert page.evaluate("Boolean(location.hash)")
                body_position(page, .5)
                if slug == SEED:
                    page.screenshot(path=str(args.output / f"prose-{width}.png"))
                y = page.evaluate("scrollY")
                returning_url = page.url
                page.evaluate("history.replaceState({...history.state, unrelated: {value: 'preserved'}}, '')")
                page.locator(".site-header a[href='/futurememo/']").click()
                page.wait_for_url(args.url + "/futurememo/", wait_until="networkidle")
                page.go_back(wait_until="networkidle")
                assert page.url == returning_url
                assert abs(page.evaluate("scrollY") - y) < 2, (width, y, page.evaluate("scrollY"))
                assert page.locator("#reader-tools").count() == 1
                assert page.evaluate("history.state.unrelated.value") == "preserved"
                report["viewports"].append({"width": width, "slug": slug, "bodyWidth": body["width"], "progress": [0, 50, 100], "backError": abs(page.evaluate("scrollY") - y)})
        # Real native fragment history, reduced media, and no idle/persistent work.
        page.set_viewport_size({"width": 1440, "height": 1000})
        fresh_anchor = next(guide for guide in companions if guide["slug"] == SEED)["sections"][2]["anchor"]
        page.goto(f"{args.url}/futurememo/{SEED}/#{fresh_anchor}", wait_until="networkidle")
        assert_anchor(page, fresh_anchor)
        click_native(page, page.locator("[data-guide-anchor]").nth(1))
        old_hash, y = page.evaluate("location.hash"), page.evaluate("scrollY")
        click_native(page, page.locator("[data-guide-anchor]").nth(3))
        page.go_back(wait_until="networkidle")
        assert page.evaluate("location.hash") == old_hash
        assert abs(page.evaluate("scrollY") - y) < 2
        page.emulate_media(reduced_motion="reduce")
        body_position(page, .5)
        assert page.locator(".reading-position progress").evaluate("el => el.value") == 50
        page.wait_for_timeout(300)
        frames = page.evaluate("readerProbe.frames")
        page.wait_for_timeout(400)
        assert page.evaluate("readerProbe.frames") == frames
        page.evaluate("""Object.defineProperty(document, 'hidden', {configurable:true, get:()=>true});
          document.dispatchEvent(new Event('visibilitychange'));
          window.dispatchEvent(new Event('scroll'));""")
        page.wait_for_timeout(150)
        assert page.evaluate("readerProbe.frames") == frames
        page.evaluate("delete document.hidden; document.dispatchEvent(new Event('visibilitychange'))")
        page.wait_for_timeout(100)
        assert page.evaluate("readerProbe.frames") > frames
        assert page.evaluate("readerProbe.storage") == 0
        # A user gesture cancels a pending return restoration, even from bfcache.
        y = page.evaluate("scrollY")
        page.evaluate("""history.replaceState({...history.state, readerPosition: {url:location.href, y:scrollY+1000}}, '');
          window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted:true}));
          window.dispatchEvent(new WheelEvent('wheel'));""")
        page.wait_for_timeout(100)
        assert page.evaluate("scrollY") == y
        click_native(page, page.locator("[data-all-notes]"))
        assert page.locator("[data-all-notes]").get_attribute("aria-pressed") == "true"
        click_native(page, page.locator("[data-all-notes]"))
        assert page.locator("[data-all-notes]").get_attribute("aria-pressed") == "false"
        samples = sorted(page.evaluate("readerProbe.durations"))
        p95 = samples[min(len(samples) - 1, int(len(samples) * .95))]
        assert p95 < 16, p95
        report["lifecycle"] = {"idleFrames": 0, "hiddenFrames": 0, "storageWrites": 0, "callbackP95Milliseconds": p95,
                               "nativeFragmentBack": True, "freshFragment": True, "unrelatedHistoryState": "preserved",
                               "returnGestureCancellation": "synthetic persisted pageshow and wheel", "singleToggleAfterReturn": True}
        page.emulate_media(media="print")
        assert page.locator("#reader-tools").is_hidden()
        assert page.locator("#essay-body").is_visible()
        context.close()
        for width in [390, 1440]:
            static = browser.new_context(java_script_enabled=False, viewport={"width": width, "height": 1000})
            page = static.new_page()
            page.goto(f"{args.url}/futurememo/{SEED}/", wait_until="networkidle")
            assert page.locator(".reading-position").is_hidden()
            assert page.locator("[data-compact-progress]").is_hidden()
            open_details(page, "#reader-tools")
            open_details(page, "#ai-reading-guide")
            open_details(page, ".guide-points")
            target = page.locator(".inline-sources a").first.get_attribute("href")[1:]
            click_native(page, page.locator(".inline-sources a").first)
            assert page.locator("#" + target).bounding_box()["y"] >= (100 if width == 390 else 80)
            open_details(page, "#ai-reading-notes")
            assert page.locator(".reader-note:visible").count() == 5
            assert page.locator("[data-all-notes]").is_hidden()
            if width == 1440:
                body_position(page, .5)
                body = page.locator("#essay-body").bounding_box()
                left = page.locator(".reader-guide").bounding_box()
                right = page.locator(".reader-notes").bounding_box()
                assert left["x"] + left["width"] <= body["x"]
                assert right["x"] >= body["x"] + body["width"]
                assert right["y"] < 200
            static.close()
        browser.close()
    assert not errors, errors
    assert not external, external
    assert not corpus_fetches, corpus_fetches
    report["noJS"] = True
    report["errors"] = errors
    report["externalRequests"] = external
    report["extraCorpusFetches"] = corpus_fetches
    (args.output / "acceptance.json").write_text(json.dumps(report, indent=2))
    print(f"PASS: 20 source-bound readers; six widths; native targets, notes, body progress, Back, media and no-JS; idle frames=0; callback p95={p95:.2f}ms.")


if __name__ == "__main__":
    main()
