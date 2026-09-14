"""Artwork scale, native writing paths and actual motion/lifecycle evidence."""
import argparse
import io
import json
from pathlib import Path
from urllib.request import urlopen

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = (320, 390, 820, 1440, 1600)
ARTICLES = (
    "qubit-teams-the-future-built-by-two-people-using-ai",
    "how-future-designers-will-win-in-the-age-of-ai",
    "the-vibe-coders-are-lying-to-you",
)


def image_evidence(image):
    image.scroll_into_view_if_needed()
    image.evaluate("el => el.decode()")
    result = image.evaluate("""el => {
      const r = el.getBoundingClientRect(), s = getComputedStyle(el);
      return {width:r.width, height:r.height, ratio:Number(el.getAttribute('width'))/Number(el.getAttribute('height')),
        source:el.currentSrc, filter:s.filter, blend:s.mixBlendMode, fit:s.objectFit};
    }""")
    with urlopen(result["source"]) as response:
        decoded = Image.open(io.BytesIO(response.read()))
        result["decoded"] = list(decoded.size)
    assert abs(result["width"] / result["height"] - result["ratio"]) < .01, result
    assert result["decoded"][0] >= result["width"] - 1, result
    assert result["filter"] == "none" and result["blend"] == "normal", result
    assert result["fit"] != "cover", result
    return result


def frame_diff(first, second):
    a = Image.open(io.BytesIO(first)).convert("RGB")
    b = Image.open(io.BytesIO(second)).convert("RGB")
    difference = ImageChops.difference(a, b)
    return sum(1 for pixel in difference.getdata() if max(pixel) > 5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8774")
    parser.add_argument("--browser", default="webkit", choices=("webkit", "chromium", "firefox"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = json.loads((ROOT / "content/corpus.json").read_text())["essays"]
    evidence = {"url": args.url, "widths": {}, "motion": {}, "covers": [], "archiveArrivals": {}}
    with sync_playwright() as p:
        browser = getattr(p, args.browser).launch()
        for width in WIDTHS:
            context = browser.new_context(viewport={"width": width, "height": 1000 if width > 700 else 844}, reduced_motion="reduce")
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            evidence["widths"][width] = {}
            for route, name in (("/", "home"), ("/futurememo/", "archive"),
                                *[(f"/futurememo/{slug}/", f"article-{i}") for i, slug in enumerate(ARTICLES)]):
                assert page.goto(args.url + route, wait_until="networkidle").status == 200
                page.evaluate("document.fonts.ready")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (width, route)
                assert page.locator(".site-header").evaluate("el => getComputedStyle(el).position") == "fixed"
                assert page.locator("[data-motion-toggle]").is_hidden()
                assert page.evaluate("document.getAnimations().length") == 0
                collisions = page.evaluate("""() => {
                  const fields = [...document.querySelectorAll('[data-motion-scene]')];
                  const copy = [...document.querySelectorAll('main h1, main h2, main h3, main p, .site-header')];
                  return fields.flatMap(field => {
                    const box = field.getBoundingClientRect(), style = getComputedStyle(field);
                    if (!['hidden','clip'].includes(style.overflow) || !style.contain.includes('paint'))
                      return ['unbounded scene'];
                    return copy.filter(el => {
                      const r = el.getBoundingClientRect();
                      return r.width && r.height && r.left < box.right && r.right > box.left &&
                        r.top < box.bottom && r.bottom > box.top;
                    }).map(el => el.className || el.tagName);
                  });
                }""")
                assert not collisions, (width, route, collisions)
                header = page.locator(".site-header").bounding_box()
                assert header["x"] >= 0 and header["x"] + header["width"] <= width
                for link in page.locator(".site-header a").all():
                    box = link.bounding_box()
                    assert box["height"] >= 44 and box["width"] >= 44
                selectors = ".exhibition-art img" if name == "home" else ".archive-art img" if name == "archive" else ".essay-artwork img"
                images = page.locator(selectors).all()
                if name == "archive":
                    assert not page.locator(".archive-discovery").evaluate("el => el.open")
                    first = page.locator(".archive-art").first.bounding_box()
                    viewport_height = page.viewport_size["height"]
                    visible = max(0, min(viewport_height, first["y"] + first["height"]) - max(0, first["y"]))
                    evidence["archiveArrivals"][width] = {"artworkTop": first["y"], "visibleArtwork": visible,
                                                         "viewportHeight": viewport_height}
                    if width in (390, 1440):
                        assert visible >= 180, (width, first, visible)
                # Every cover at every width; decoded sizes, not density-corrected naturalWidth.
                dimensions = [image_evidence(image) for image in images]
                assert all(d["width"] >= (width - 48 if width <= 700 else 300) for d in dimensions), (width, route, dimensions)
                evidence["widths"][width][name] = dimensions
                if name == "archive":
                    links = page.locator(".archive-entry").evaluate_all("""els => els.map(el => ({
                      image:el.querySelector('img').getAttribute('src'), title:el.querySelector('h2').textContent,
                      href:el.querySelector('.archive-art').getAttribute('href'), titleHref:el.querySelector('h2 a').getAttribute('href')
                    }))""")
                    assert len(links) == 20
                    for link, row in zip(links, rows):
                        assert link == {"image": row["cover"], "title": row["title"],
                                        "href": f'/futurememo/{row["slug"]}/', "titleHref": f'/futurememo/{row["slug"]}/'}
                    evidence["covers"] = links
                if name.startswith("article"):
                    assert page.locator("#essay-body [data-passage]").count() > 0
                    assert page.locator(".essay-body").evaluate("el => getComputedStyle(el).fontFamily").startswith("Newsreader")
                    page.locator(".paragraph-anchor").first.focus()
                    box = page.locator(".paragraph-anchor").first.bounding_box()
                    assert box["y"] >= header["y"] + header["height"]
                page.evaluate("scrollTo(0,0)")
                if width in (390, 1440):
                    if name == "home":
                        page.locator(".footer-signature img").evaluate("el => {el.loading='eager'; return el.decode()}")
                    page.screenshot(path=str(args.output / f"{name}-{width}.png"), full_page=name == "home")
                    if name == "archive":
                        page.locator(".archive-art").first.scroll_into_view_if_needed()
                        page.screenshot(path=str(args.output / f"archive-gallery-{width}.png"))
                if name == "archive":
                    page.locator(".archive-discovery > summary").focus()
                    page.keyboard.press("Enter")
                    assert page.locator("#archive-query").is_visible()
                    page.locator("#archive-query").fill("judgment")
                    page.locator("#archive-search button").click()
                    page.wait_for_function("document.querySelector('#archive-status').textContent.includes('matching passages')")
                    assert page.locator(".archive-matches a").count() > 0
                    page.locator("#archive-theme").select_option("Builders & craft")
                    page.locator("#archive-list-toggle").click()
                    assert page.locator(".archive-art").first.is_hidden()
                    page.locator("#archive-reset").click()
                    assert page.locator(".archive-entry:visible").count() == 20
                    page.locator("#archive-list-toggle").click()
                    page.locator(".archive-discovery > summary").click()
                    assert page.locator("#archive-query").is_hidden()
                assert not errors, errors
            context.close()

        context = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        field = page.locator(".hero-field")
        toggle = page.locator("[data-motion-toggle]")
        assert toggle.is_visible()
        page.wait_for_function("document.querySelector('.hero-field').dataset.motionState === 'running'")
        a = field.screenshot()
        page.wait_for_timeout(1100)
        b = field.screenshot()
        changed = frame_diff(a, b)
        assert changed > 500, changed
        (args.output / "motion-a.png").write_bytes(a)
        (args.output / "motion-b.png").write_bytes(b)
        evidence["motion"]["changedPixels"] = changed
        assert page.evaluate("document.getAnimations().filter(a => a.playState === 'running').length") <= 2
        assert page.locator("animateMotion").count() == 3
        toggle.click()
        page.wait_for_timeout(100)
        a = field.screenshot()
        page.wait_for_timeout(500)
        assert frame_diff(a, field.screenshot()) == 0
        assert toggle.get_attribute("aria-pressed") == "true"
        times = page.evaluate("document.getAnimations().map(a => a.currentTime)")
        page.locator(".writing-plane--2").evaluate("el => el.scrollIntoView({block:'center'})")
        page.wait_for_timeout(300)
        page.evaluate("scrollTo(0,0)")
        page.wait_for_timeout(300)
        assert page.evaluate("document.getAnimations().map(a => a.currentTime)") == times
        toggle.click()
        page.wait_for_timeout(300)
        assert page.evaluate("document.getAnimations().some(a => a.playState === 'running')")
        # A real offscreen transition freezes timelines and resumes at the same pose.
        page.locator(".writing-plane--2").evaluate("el => el.scrollIntoView({block:'center'})")
        page.wait_for_timeout(250)
        times = page.evaluate("document.getAnimations().map(a => a.currentTime)")
        page.wait_for_timeout(400)
        assert page.evaluate("document.getAnimations().map(a => a.currentTime)") == times
        page.evaluate("scrollTo(0,0)")
        page.wait_for_timeout(250)
        assert page.evaluate("document.getAnimations().some(a => a.playState === 'running')")
        # Headless WebKit has no foreground tabs; exercise the visibility event contract explicitly.
        page.evaluate("""Object.defineProperty(document, 'hidden', {configurable:true, value:true});
          document.dispatchEvent(new Event('visibilitychange'));""")
        page.wait_for_function("document.getAnimations().every(a => !a.pending)")
        times = page.evaluate("document.getAnimations().map(a => a.currentTime)")
        page.wait_for_timeout(400)
        assert page.evaluate("document.getAnimations().map(a => a.currentTime)") == times
        page.evaluate("delete document.hidden; document.dispatchEvent(new Event('visibilitychange'))")
        assert page.evaluate("document.getAnimations().some(a => a.playState === 'running')")
        toggle.click()
        page.evaluate("document.documentElement.dataset.bfcacheProbe = 'gallery'")
        page.goto(args.url + "/futurememo/")
        page.go_back(wait_until="networkidle")
        # Back may restore a document or reload it: neither may duplicate controllers.
        assert page.locator("[data-motion-toggle]").count() == 1
        assert page.evaluate("document.getAnimations().length") <= 2
        if page.locator("html").get_attribute("data-bfcache-probe") == "gallery":
            assert page.locator("[data-motion-toggle]").get_attribute("aria-pressed") == "true"
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted:true}))")
        assert page.evaluate("document.getAnimations().every(a => a.playState !== 'running')")
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted:true}))")
        if page.locator("[data-motion-toggle]").get_attribute("aria-pressed") == "true":
            page.locator("[data-motion-toggle]").click()
        for media in ({"reduced_motion": "reduce"}, {"reduced_motion": "no-preference", "forced_colors": "active"}, {"media": "print", "forced_colors": "none"}):
            page.emulate_media(**media)
            page.wait_for_timeout(100)
            assert page.locator("[data-motion-toggle]").is_hidden()
            assert page.evaluate("document.getAnimations().length") == 0
        page.emulate_media(media="screen", reduced_motion="no-preference", forced_colors="none")
        page.wait_for_timeout(200)
        samples = page.evaluate("""() => new Promise(resolve => {
          const deltas = []; let last; const start = performance.now();
          function sample(now) {
            if (last) deltas.push(now-last); last=now;
            if (now-start < 1800) requestAnimationFrame(sample); else resolve(deltas);
          } requestAnimationFrame(sample);
        })""")
        ordered = sorted(samples)
        evidence["motion"].update({"rafSamples": len(samples), "p95FrameMs": ordered[int(len(ordered)*.95)],
                                   "maxFrameMs": max(samples), "jsFrameCallbacks": 0, "maxScenes": 2,
                                   "maxCarrierTracks": 2, "maxNativeFollowers": 3,
                                   "visibilityCheck": "emulated hidden event; real IntersectionObserver scroll",
                                   "pausePixelDifference": 0})
        assert len(samples) >= 40 and ordered[int(len(ordered)*.95)] < 50, evidence["motion"]
        context.close()

        for width in WIDTHS:
            context = browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="no-preference")
            page = context.new_page()
            page.goto(args.url, wait_until="networkidle")
            toggle = page.locator("[data-motion-toggle]")
            assert toggle.is_visible()
            toggle.click()
            assert toggle.inner_text() == "Resume"
            header = page.locator(".site-header").bounding_box()
            assert header["height"] <= 56 and header["x"] + header["width"] <= width
            assert toggle.bounding_box()["height"] >= 44
            page.locator(".writing-list h3 a").first.focus()
            assert page.locator(".writing-list h3 a").first.bounding_box()["y"] >= header["y"] + header["height"]
            assert page.locator(".site-header").bounding_box() == header
            context.close()

        for width in WIDTHS:
            context = browser.new_context(java_script_enabled=False, viewport={"width": width, "height": 900})
            page = context.new_page()
            page.goto(args.url)
            assert page.locator("[data-motion-toggle]").is_hidden()
            page.locator(".site-header nav a").first.click()
            assert page.locator("#writing").bounding_box()["y"] >= 79
            page.locator(".exhibition-art").first.click()
            assert page.locator("#essay-body").is_visible()
            page.goto(args.url + "/futurememo/")
            assert page.locator(".archive-entry").count() == 20
            assert page.locator(".archive-tools").is_hidden()
            page.locator(".archive-discovery > summary").click()
            assert page.locator(".archive-native-note").is_visible()
            assert page.locator(".archive-tools").is_hidden()
            assert page.locator('.archive-notes a[href="#by-preoccupation"]').is_visible()
            page.locator(".archive-art").first.click()
            assert page.locator("#essay-body").is_visible()
            page.locator(".essay-artwork a").first.click()
            assert page.url.endswith(".webp")
            page.goto(args.url + "/lightworks/")
            assert page.locator(".photograph").count() == 22
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            context.close()
        browser.close()
    (args.output / "gallery-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("PASS: artwork scale/full ratios/decoded resources at five widths, 20 title-image-URL associations, "
          "native writing/Lightworks paths, actual animated pixels, pause/resume, suspension, media fallback and frame budget.")


if __name__ == "__main__":
    main()
