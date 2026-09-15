"""Canonical navigation, real responsive bounds and article toolbar clearance."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from test_reader_detail import SEED, assert_anchor, body_position, click_native, open_details

WIDTHS = (320, 390, 820, 1024, 1280, 1440, 1600)
LABELS = ["Future (Memo)", "About (Me)"]
DESTINATIONS = ["/futurememo/", "/about-me/"]
ARTICLE = f"/futurememo/{SEED}/"


def header_bounds(page):
    header = page.locator(".site-header")
    box = header.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= page.viewport_size["width"]
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    assert header.locator("button").count() == 0
    assert page.locator("[data-motion-toggle], .motion-toggle").count() == 0
    links = header.locator("nav a")
    assert links.all_text_contents() == LABELS
    assert links.evaluate_all("es=>es.map(e=>e.getAttribute('href'))") == DESTINATIONS
    rectangles = []
    for link in header.locator("a").all():
        rect = link.bounding_box()
        assert rect["width"] >= 44 and rect["height"] >= 44
        assert rect["x"] >= box["x"] and rect["x"] + rect["width"] <= box["x"] + box["width"] + .1
        assert rect["y"] >= box["y"] and rect["y"] + rect["height"] <= box["y"] + box["height"] + .1
        assert link.evaluate("el=>parseFloat(getComputedStyle(el).fontSize)") >= 12
        assert link.evaluate("el=>getComputedStyle(el).textTransform") == "none"
        for other in rectangles:
            assert (rect["x"] >= other["x"] + other["width"] - .1
                    or other["x"] >= rect["x"] + rect["width"] - .1
                    or rect["y"] >= other["y"] + other["height"] - .1
                    or other["y"] >= rect["y"] + rect["height"] - .1)
        rectangles.append(rect)
    return box


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8774")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--home-only", action="store_true", help="Focus homepage navigation without rerunning the article reader.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report, errors = {"headers": [], "readers": []}, []
    with sync_playwright() as p:
        browser = p.webkit.launch()
        context = browser.new_context()
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        routes = [("/", "home", None), ("/futurememo/", "archive", DESTINATIONS[0]),
                  (ARTICLE, "article", DESTINATIONS[0]), ("/lightworks/", "photography", None),
                  ("/about-me/", "about", DESTINATIONS[1]), ("/methods/", "methods", None)]
        if args.home_only:
            routes = routes[:1]
        for width in WIDTHS:
            page.set_viewport_size({"width": width, "height": 844 if width < 700 else 1000})
            for route, name, active in routes:
                response = page.goto(args.url + route, wait_until="networkidle")
                assert response.status in (200, 304), (width, route, response.status, page.url)
                assert page.locator('link[rel="canonical"]').get_attribute("href") == "https://suffsyed.com" + route
                page.evaluate("document.fonts.ready")
                box = header_bounds(page)
                current = page.locator(".site-header nav [aria-current]")
                if active:
                    assert current.count() == 1 and current.get_attribute("href") == active
                else:
                    assert current.count() == 0
                assert page.locator(".site-footer > nav a").all_text_contents()[:2] == LABELS
                for link in page.locator(".site-footer > nav a").all():
                    assert link.bounding_box()["height"] >= 44
                    assert link.evaluate("e=>parseFloat(getComputedStyle(e).fontSize)") >= 16
                assert page.locator('.site-footer a[href="/lightworks/"]').count() == 0
                assert page.locator(".site-header .site-signature").count() == 1
                assert page.locator(".site-header").evaluate("e=>getComputedStyle(e).backgroundColor") == "rgba(0, 0, 0, 0)"
                first_title = page.locator("main h1").first.bounding_box()
                assert first_title["y"] >= box["y"] + box["height"]
                collisions = page.locator("[data-motion-scene]").evaluate_all("""es=>es.filter(e=>{
                  const r=e.getBoundingClientRect(),h=document.querySelector('.site-header').getBoundingClientRect();
                  return r.left<h.right && r.right>h.left && r.top<h.bottom && r.bottom>h.top;
                }).length""")
                assert collisions == 0, (width, route)
                report["headers"].append({"width": width, "route": route, "bounds": box, "active": active})
                if width in (320, 390, 1280, 1440, 1600):
                    page.screenshot(path=str(args.output / f"{name}-opening-{width}.png"))
                if route != ARTICLE:
                    page.evaluate("scrollTo(0, 240)")
                    moved = header_bounds(page)
                    assert abs(moved["y"] + page.evaluate("scrollY")) < 1
                    assert page.locator(".site-header").evaluate("e=>getComputedStyle(e).position") == "absolute"
                    continue
                body_position(page, .5)
                moved = header_bounds(page)
                assert abs(moved["y"] + page.evaluate("scrollY")) < 1
                assert moved["y"] + moved["height"] <= 0
                assert box["x"] == box["y"] == 0 and box["width"] == width
                assert page.locator(".sheet").evaluate("e=>getComputedStyle(e).backgroundColor") == "rgba(0, 0, 0, 0)"
                clearance = page.evaluate("parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop)")
                body = page.locator("#essay-body").bounding_box()
                assert abs(body["x"] + body["width"] / 2 - width / 2) < .1
                assert body["width"] == (640 if width >= 820 else width - (48 if width == 320 else 64))
                toolbar = None
                if width < 1280:
                    toolbar = page.locator("#reader-tools > summary").bounding_box()
                    assert abs(toolbar["y"]) < 1
                    assert toolbar["y"] + toolbar["height"] <= clearance
                if width in (320, 390, 1280, 1440, 1600):
                    page.screenshot(path=str(args.output / f"article-reading-{width}.png"))
                open_details(page, "#reader-tools")
                open_details(page, "#ai-reading-guide")
                link = page.locator("[data-guide-anchor]").nth(2)
                target = link.get_attribute("href")[1:]
                click_native(page, link)
                assert_anchor(page, target)
                open_details(page, "#reader-tools")
                open_details(page, "#ai-reading-guide")
                points = page.locator("[data-guide-section]").nth(2)
                open_details(page, f'[data-guide-section="{points.get_attribute("data-guide-section")}"] .guide-points')
                source = points.locator(".inline-sources a").first
                target = source.get_attribute("href")[1:]
                click_native(page, source)
                assert_anchor(page, target)
                body_position(page, .5)
                y, url = page.evaluate("scrollY"), page.url
                # Navigate from the reading position, without auto-scrolling to the departed masthead.
                page.goto(args.url + "/futurememo/", wait_until="networkidle")
                assert page.locator(".archive-entry").count() == 20
                page.go_back(wait_until="networkidle")
                assert page.url == url and abs(page.evaluate("scrollY") - y) < 2
                report["readers"].append({"width": width, "bodyWidth": body["width"], "header": box,
                                          "toolbar": toolbar, "clearance": clearance,
                                          "backError": abs(page.evaluate("scrollY") - y)})
        page.goto(args.url + "/lightworks/", wait_until="networkidle")
        assert page.locator(".photograph").count() == 22
        page.locator("[data-gallery]").first.click()
        assert page.locator("#artwork-dialog").is_visible()
        page.keyboard.press("Escape")
        assert page.locator("#artwork-dialog").is_hidden()
        context.close()
        for width in (320, 390, 1440):
            context = browser.new_context(java_script_enabled=False, viewport={"width": width, "height": 1000})
            page = context.new_page()
            page.goto(args.url, wait_until="networkidle")
            header_bounds(page)
            page.locator(".site-header nav a").first.click()
            page.wait_for_url(args.url + "/futurememo/", wait_until="networkidle")
            assert page.locator(".archive-entry").count() == 20
            static_routes = ("/lightworks/", "/about-me/") if args.home_only else ("/lightworks/", "/about-me/", ARTICLE)
            for route in static_routes:
                page.goto(args.url + route, wait_until="networkidle")
                header_bounds(page)
            if not args.home_only:
                assert page.locator("#reader-tools").is_hidden()
                open_details(page, "#ai-reading-guide")
                link = page.locator("[data-guide-anchor]").nth(2)
                target = link.get_attribute("href")[1:]
                click_native(page, link)
                assert_anchor(page, target)
            context.close()
        browser.close()
    assert not errors, errors
    (args.output / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
    scope = "homepage, canonical destinations, parked photography and no-JS" if args.home_only else "natural mastheads, toolbar/source clearance, Back, parked photography and no-JS"
    print(f"PASS: exact canonical navigation/active states; seven widths; {scope}.")


if __name__ == "__main__":
    main()
