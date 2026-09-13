"""Real font rendering, editorial roles, responsive controls and zoom-equivalent reflow."""
import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

QUBIT = "/futurememo/qubit-teams-the-future-built-by-two-people-using-ai/"
ROUTES = ["/", QUBIT, "/futurememo/", "/lightworks/", "/research/", "/about-me/"]


def no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def actual_font(page, selector, family):
    session = page.context.new_cdp_session(page)
    session.send("DOM.enable")
    session.send("CSS.enable")
    root = session.send("DOM.getDocument")["root"]["nodeId"]
    node = session.send("DOM.querySelector", {"nodeId": root, "selector": selector})["nodeId"]
    assert node, (page.url, selector)
    fonts = session.send("CSS.getPlatformFontsForNode", {"nodeId": node})["fonts"]
    session.detach()
    used = [font for font in fonts if font["glyphCount"]]
    assert used and all(font["isCustomFont"] and font["familyName"].startswith(family) for font in used), (selector, used)
    return used


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--private-fonts", action="store_true")
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    errors, missing, external, font_requests, report = [], [], [], set(), []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in [320, 390, 820, 1600, 1920]:
            context = browser.new_context(viewport={"width": width, "height": 844 if width == 390 else 900}, has_touch=width < 900, reduced_motion="reduce")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("response", lambda response: missing.append(response.url) if response.status >= 400 else None)
            page.on("request", lambda request: external.append(request.url) if not request.url.startswith(args.url) else None)
            page.on("request", lambda request: font_requests.add(request.url) if request.resource_type == "font" else None)
            for route in ROUTES:
                page.goto(args.url + route, wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                no_overflow(page)
                assert page.locator("h1").first.evaluate("el => getComputedStyle(el).fontStyle") == "normal"
                assert page.locator("body").evaluate("el => getComputedStyle(el).fontSynthesis") == "none"
                assert (page.locator("html").get_attribute("data-font-mode") == "private-evaluation") == args.private_fonts
                display_font = actual_font(page, "#home-essay-title" if route == "/" else "h1",
                                           "PP Kyoto" if args.private_fonts else "Newsreader")
                navigation_font = actual_font(page, ".mast nav a", "Newsreader")
                if page.locator(".label").count():
                    actual_font(page, ".label", "DM Mono")
                assert page.locator("body").evaluate("el => getComputedStyle(el).fontOpticalSizing") == "auto"
                too_small = page.locator("button, input, select, .mast nav a, .primary-link, label, .question-label").evaluate_all("""els => els
                  .filter(el => el.getBoundingClientRect().width && getComputedStyle(el).visibility !== 'hidden')
                  .filter(el => parseFloat(getComputedStyle(el).fontSize) < 14)
                  .map(el => [el.textContent, getComputedStyle(el).fontSize])""")
                assert not too_small, (width, route, too_small)
                if route == QUBIT:
                    actual_font(page, ".essay-body p", "Newsreader")
                    ids = page.locator(".contents a").evaluate_all("els => els.map(el => el.hash.slice(1))")
                    for target in [ids[-1], ids[0], ids[2]]:
                        page.locator(f"#{target}").evaluate("el => el.scrollIntoView({block:'start', behavior:'instant'})")
                        page.wait_for_function("(id) => document.querySelector('.contents a[aria-current]')?.hash === '#' + id", arg=target)
                    if width > 1000:
                        page.locator(".open-lens").click()
                        summary = page.locator(".contents summary").bounding_box()
                        count = page.locator(".contents summary .label").bounding_box()
                        assert count["y"] + count["height"] < summary["y"] + summary["height"]
                        page.locator("#close-lens").click()
                if route == "/":
                    assert page.locator(".chapter > header h2:visible").all_inner_texts() == [
                        "Follow a thought further.", "Step outside.", "What happens after the impressive first demo?"]
                    assert not page.locator(".perspective-disclosure").evaluate("el => el.open")
                    assert page.locator(".featured-meta .primary-link").count() == 1
                    assert page.locator("#home-essay-title").evaluate("el => parseFloat(getComputedStyle(el).fontSize)") > 1.8 * page.locator("#home-title").evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
                    for chapter in [".exploration", ".home-photography"]:
                        bounds = page.locator(chapter).bounding_box()
                        assert abs(bounds["x"]) < 1 and abs(bounds["width"] - width) < 1, (width, chapter, bounds)
                    if width in [320, 390]:
                        nav_rows = page.locator(".mast nav a").evaluate_all("els => els.map(el => Math.round(el.getBoundingClientRect().top))")
                        assert len(set(nav_rows)) == (2 if width == 320 else 1), nav_rows
                    if width == 390:
                        cta = page.locator(".featured-meta .primary-link").bounding_box()
                        art = page.locator("[data-home-cover]").bounding_box()
                        assert cta["y"] + cta["height"] <= 844, cta
                        assert min(844, art["y"] + art["height"]) - max(0, art["y"]) >= 150, art
                    report.append({"width": width, "renderedDisplay": display_font, "renderedNavigation": navigation_font,
                                   "fonts": page.evaluate("""() => [...document.fonts].map(font => ({
                      family: font.family, weight: font.weight, style: font.style,
                      status: font.status, display: font.display
                    }))""")})
            page.goto(args.url, wait_until="networkidle")
            # Every selected cover and complete title still fits the narrowest layout.
            data = page.locator("#home-data").evaluate("el => JSON.parse(el.textContent)")
            for index, theme in enumerate(data["themes"]):
                if width <= 580:
                    page.locator(".theme-selector summary").click()
                page.locator("[data-home-theme]").nth(index).focus()
                page.keyboard.press("Enter")
                group = [row for row in data["essays"] if row["theme"] == theme["name"]]
                for _ in group:
                    page.locator("[data-home-cover]").evaluate("el => el.decode()")
                    no_overflow(page)
                    assert page.locator("[data-home-cover]").evaluate("el => getComputedStyle(el).objectFit") == "contain"
                    assert page.locator("[data-home-selection-title]").inner_text() == page.locator("#home-essay-title").inner_text()
                    assert page.locator("[data-home-next]").bounding_box()["height"] >= 44
                    page.locator("[data-home-next]").click()
            if width == 390:
                page.locator(".reading-key > summary").focus()
                page.keyboard.press("Enter")
                assert page.locator(".reading-key").evaluate("el => el.open")
                page.keyboard.press("Tab")
                assert page.evaluate("document.activeElement.hasAttribute('data-home-selection-link')")
                assert page.evaluate("getComputedStyle(document.activeElement).outlineStyle") == "solid"
            context.close()

        # Same CSS viewport and physical text size as 200%/400% browser zoom on 1600x1120.
        for scale in [2, 4]:
            context = browser.new_context(viewport={"width": 1600 // scale, "height": 1120 // scale}, device_scale_factor=scale, reduced_motion="reduce")
            page = context.new_page()
            for route in ROUTES[:5]:
                page.goto(args.url + route, wait_until="networkidle")
                no_overflow(page)
                if route == "/":
                    page.screenshot(path=str(args.artifacts / f"reflow-{scale * 100}-home.png"))
                if route == QUBIT:
                    page.locator(".open-lens").click()
                    page.locator("#term-query").fill("systems")
                    page.locator("#term-form").evaluate("el => el.requestSubmit()")
                    no_overflow(page)
                    page.locator("#close-lens").click()
                    assert not page.locator("#reading-lens").is_visible()
            context.close()

        no_js = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
        page = no_js.new_page()
        page.goto(args.url, wait_until="networkidle")
        assert page.locator(".theme-selector").evaluate("el => el.open")
        assert page.locator("a[data-home-theme]:visible").count() == 5
        page.locator(".perspective-disclosure > summary").click()
        assert page.locator(".reader-margin").is_visible()
        no_js.close()
        browser.close()
    assert not errors and not missing and not external, (errors, missing, external)
    assert len(font_requests) == (7 if args.private_fonts else 4), font_requests
    assert not any(re.search(r"museum|bitter|alegreya|plex|inter", url, re.I) for url in font_requests)
    for record in report:
        assert len(record["fonts"]) == (7 if args.private_fonts else 4)
        assert {font["family"] for font in record["fonts"]} == (
            {"Newsreader", "DM Mono", "PP Kyoto"} if args.private_fonts else {"Newsreader", "DM Mono"})
        assert all(font["status"] != "error" and font["display"] == "swap" for font in record["fonts"])
    (args.artifacts / "font-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: actual Newsreader/DM Mono and optional Kyoto glyphs; all requested font assets, no retired/external requests; clear narrative, visible mobile CTA/art, 100 synchronized selections, reading orientation, focus and 200%/400% equivalent reflow.")


if __name__ == "__main__":
    main()
