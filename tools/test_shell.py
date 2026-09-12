"""Check the edge-to-edge paper shell without changing internal reading measures."""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

QUBIT = "/futurememo/qubit-teams-the-future-built-by-two-people-using-ai/"
ROUTES = ["/", QUBIT, "/futurememo/", "/lightworks/", "/research/",
          "/about-me/", "/about-the-memo/", "/faqs/",
          "/the-end-of-design-report/", "/store/", "/404.html", "/methods/"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        errors = []
        for width in [1920, 1600, 820, 390, 320]:
            page = browser.new_page(viewport={"width": width, "height": 1120 if width > 820 else 844}, reduced_motion="reduce")
            page.on("pageerror", lambda error: errors.append(str(error)))
            for route in ROUTES:
                page.goto(args.url + route, wait_until="networkidle")
                state = page.evaluate("""() => {
                    const sheet = document.querySelector('.sheet');
                    const rect = sheet.getBoundingClientRect();
                    const css = getComputedStyle(sheet);
                    const caption = getComputedStyle(document.querySelector('.outside-caption'));
                    return {
                        left: rect.left, right: rect.right, top: rect.top,
                        viewport: document.documentElement.clientWidth,
                        overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
                        background: getComputedStyle(document.body).backgroundColor,
                        paper: css.backgroundColor, maxWidth: css.maxWidth,
                        margins: ['Top','Right','Bottom','Left'].map(side => css['margin' + side]),
                        borders: ['Top','Right','Bottom','Left'].map(side => css['border' + side + 'Width']),
                        shadow: css.boxShadow, padding: parseFloat(css.paddingLeft),
                        captionMaxWidth: caption.maxWidth,
                        measure: document.querySelector('.essay-body')?.getBoundingClientRect().width
                    };
                }""")
                assert state["left"] == 0 and state["top"] == 0, (width, route, state)
                assert abs(state["right"] - state["viewport"]) < 1, (width, route, state)
                assert not state["overflow"], (width, route)
                assert state["background"] == state["paper"] == "rgb(255, 250, 243)"
                assert state["maxWidth"] == state["captionMaxWidth"] == "none"
                assert state["margins"] == state["borders"] == ["0px"] * 4
                assert state["shadow"] == "none" and state["padding"] >= 20
                if state["measure"]:
                    assert state["measure"] <= 710
                if width in [1600, 390] and route in ["/", QUBIT]:
                    name = "home" if route == "/" else "essay"
                    device = "desktop" if width == 1600 else "phone"
                    page.screenshot(path=str(args.artifacts / f"{name}-{device}.png"))
                    if route == QUBIT:
                        height = page.locator("#reading").bounding_box()["y"]
                        page.screenshot(path=str(args.artifacts / f"essay-{device}-with-cover.png"), full_page=True,
                                        clip={"x": 0, "y": 0, "width": width, "height": height})
                if route == QUBIT:
                    page.locator(".open-lens").click()
                    page.locator("#term-query").fill("systems")
                    page.locator("#term-form").evaluate("form => form.requestSubmit()")
                    assert page.locator("#term-status").inner_text().startswith("10 occurrences")
                    assert not page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
                    page.locator("#close-lens").click()
                    assert not page.locator("#reading-lens").is_visible()
            page.close()
        browser.close()
    assert not errors, errors
    print("PASS: 12 routes at 1920/1600/820/390/320px; edge-to-edge ivory, no frame or overflow, preserved reading measure.")


if __name__ == "__main__":
    main()
