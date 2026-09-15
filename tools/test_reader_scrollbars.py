"""Scoped scrollbar chrome without changing native reader scrolling."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from test_reader_detail import SEED, assert_anchor, body_position, click_native, open_details


def check_scroller(page, selector):
    scroller = page.locator(selector)
    styles = scroller.evaluate("""e => ({
      scrollbarWidth: getComputedStyle(e).scrollbarWidth,
      webkitScrollbar: getComputedStyle(e, '::-webkit-scrollbar').display,
      overflowY: getComputedStyle(e).overflowY,
      clientHeight: e.clientHeight, scrollHeight: e.scrollHeight,
      horizontalOverflow: e.scrollWidth - e.clientWidth
    })""")
    assert styles["scrollbarWidth"] == "none", (selector, styles)
    assert styles["webkitScrollbar"] == "none", (selector, styles)
    assert styles["overflowY"] == "auto"
    assert styles["scrollHeight"] > styles["clientHeight"] + 200
    assert styles["horizontalOverflow"] <= 1
    scroller.evaluate("e => e.scrollTop = 0")
    box = scroller.bounding_box()
    y = page.evaluate("scrollY")
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.wheel(0, 180)
    page.wait_for_function("s => document.querySelector(s).scrollTop > 0", arg=selector)
    page.wait_for_timeout(250)
    styles["wheelPageShift"] = abs(page.evaluate("scrollY") - y)
    assert styles["wheelPageShift"] < 1
    styles["wheelScrollTop"] = scroller.evaluate("e => e.scrollTop")
    assert styles["wheelScrollTop"] > 0

    last = scroller.locator(".guide-sources a").last
    last.focus()
    assert last.evaluate("e => e === document.activeElement"), selector
    # WebKit follows macOS's Option-Tab convention for including links.
    page.keyboard.press("Alt+Shift+Tab")
    page.keyboard.press("Alt+Tab")
    assert last.evaluate("e => e === document.activeElement"), (selector, page.evaluate("document.activeElement.outerHTML"))
    link = last.bounding_box()
    box = scroller.bounding_box()
    assert box["y"] <= link["y"] and link["y"] + link["height"] <= box["y"] + box["height"] + 1
    assert scroller.evaluate("e => e.scrollTop") > styles["wheelScrollTop"]
    styles["endLinkScrollTop"] = scroller.evaluate("e => e.scrollTop")
    target = last.get_attribute("href")[1:]
    page.keyboard.press("Enter")
    assert_anchor(page, target)
    styles.update(keyboardEndLink=True, sourceTarget=target)
    return styles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8774")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results, errors = [], []
    with sync_playwright() as p:
        browser = p.webkit.launch()
        for width in (1440, 390, 1028):
            context = browser.new_context(viewport={"width": width, "height": 600}, reduced_motion="reduce")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"{args.url}/futurememo/{SEED}/", wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            body_position(page, .5)
            open_details(page, "#reader-tools")
            open_details(page, "#ai-reading-guide")
            for points in page.locator(".guide-points").all():
                if not points.evaluate("e => e.open"):
                    click_native(page, points.locator(":scope > summary"))
            open_details(page, "#ai-reading-notes")
            click_native(page, page.locator("[data-all-notes]"))
            assert page.locator("[data-all-notes]").get_attribute("aria-pressed") == "true"
            assert page.locator(".reader-note:visible").count() == 5
            body = page.locator("#essay-body").bounding_box()
            assert body["width"] == (326 if width == 390 else 640)
            assert abs(body["x"] + body["width"] / 2 - width / 2) < 1
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            for selector in ("html", "body"):
                assert page.locator(selector).evaluate("e => getComputedStyle(e).scrollbarWidth") != "none"
                assert page.locator(selector).evaluate("e => getComputedStyle(e, '::-webkit-scrollbar').display") != "none"
            selectors = (".reader-guide", ".reader-notes") if width >= 1280 else (".reader-tools-content",)
            record = {"width": width, "height": 600, "scrollers": {}}
            for selector in selectors:
                if width >= 1280:
                    body_position(page, .5)
                    rail = page.locator(selector).bounding_box()
                    assert rail["width"] == 188 and abs(rail["y"] - 32) < 1
                    gap = body["x"] - rail["x"] - rail["width"] if selector == ".reader-guide" else rail["x"] - body["x"] - body["width"]
                    assert abs(gap - 80) < 1
                record["scrollers"][selector] = check_scroller(page, selector)
            for fraction in (0, .5, 1):
                body_position(page, fraction)
                assert abs(page.locator(".reading-position progress").evaluate("e => e.value") - fraction * 100) <= 1
                if width < 1280:
                    assert page.locator("[data-compact-progress]").inner_text() == f"{round(fraction * 100)}%"
            body_position(page, .5)
            if width >= 1280:
                progress = page.locator(".reading-position progress")
                assert progress.is_visible() and progress.bounding_box()["height"] == 3
                for selector in selectors:
                    page.locator(selector).evaluate("e => e.scrollTop = 0")
            else:
                open_details(page, "#reader-tools")
                page.locator(".reader-tools-content").evaluate("e => e.scrollTop = 0")
            page.screenshot(path=str(args.output / f"reader-{width}.png"))
            results.append(record)
            context.close()
        browser.close()
    assert not errors, errors
    (args.output / "acceptance.json").write_text(json.dumps({"viewports": results, "bodyProgress": [0, 50, 100], "errors": errors}, indent=2) + "\n")
    print("PASS: hidden scoped scrollbar styles; native wheel isolation and keyboard end-source access; 640px prose/188px rails; compact tools; 0/50/100 progress.")


if __name__ == "__main__":
    main()
