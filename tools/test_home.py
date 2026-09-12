"""Verify home selection is connected to real corpus measurements and routes."""
import argparse
import json
import math
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    args = parser.parse_args()
    data = json.loads((ROOT / "content/corpus.json").read_text())
    # Built per-essay models are the exact same measured source as the home.
    rows = []
    for row in data["essays"]:
        source = (ROOT / "docs/futurememo" / row["slug"] / "index.html").read_text()
        rows.append(json.loads(re.search(r'<script id="essay-data" type="application/json">(.*?)</script>', source, re.S).group(1)))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1120})
        page.goto(args.url, wait_until="networkidle")
        theme_buttons = page.locator("[data-home-theme]")
        assert theme_buttons.count() == 5
        visited = set()
        for i, theme in enumerate(data["themes"]):
            theme_buttons.nth(i).focus()
            page.keyboard.press("Enter")
            group = [row for row in rows if row["theme"] == theme["name"]]
            for _ in group:
                title = page.locator(".featured h2").inner_text()
                row = next(row for row in group if row["title"] == title)
                visited.add(row["slug"])
                assert page.locator(".engraving .word-bar").count() == math.ceil(row["words"] / 100)
                links = page.locator(".featured a").evaluate_all("els => els.map(el=>el.getAttribute('href'))")
                assert row["url"] in links, (title, links)
                image = page.locator(".featured img")
                assert image.get_attribute("src") == row["cover"]
                assert image.get_attribute("alt")
                page.get_by_role("button", name="Next essay in this theme").click()
        assert len(visited) == 20
        page.evaluate("scrollTo({top:0,behavior:'instant'})")
        motion = page.locator(".instrument-top button")
        assert motion.is_visible()
        motion.click()
        assert "Resume" in motion.inner_text()
        assert page.locator(".running-ring").count() > 0
        assert page.locator(".running-ring").evaluate("el=>getComputedStyle(el).animationPlayState") == "paused"
        motion.click()
        page.locator("footer.foot").scroll_into_view_if_needed()
        page.wait_for_timeout(200)
        assert page.locator(".running-ring").evaluate("el=>getComputedStyle(el).animationPlayState") == "paused"
        page.reload(wait_until="networkidle")
        assert page.locator(".featured h2").inner_text()
        touch = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mobile = touch.new_page()
        mobile.goto(args.url, wait_until="networkidle")
        mobile.locator("[data-home-theme]").nth(2).tap()
        assert mobile.locator("[data-home-theme]").nth(2).get_attribute("aria-pressed") == "true"
        title = mobile.locator(".featured h2").inner_text()
        mobile.get_by_role("button", name="Next essay in this theme").tap()
        assert mobile.locator(".featured h2").inner_text() != title
        touch.close()
        browser.close()
    print("PASS: all 20 home selections, exact tally counts, covers, real links, theme deep links, pause and offscreen motion.")


if __name__ == "__main__":
    main()
