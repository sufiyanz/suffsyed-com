"""Readable viewport studies plus fully loaded, full-page review artifacts."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

QUBIT = "/futurememo/qubit-teams-the-future-built-by-two-people-using-ai/"


def load_images(page):
    page.evaluate("""async () => {
      const oldY = scrollY;
      for (let y = 0; y < document.documentElement.scrollHeight; y += innerHeight) {
        scrollTo({top: y, behavior: 'instant'});
        await new Promise(resolve => setTimeout(resolve, 75));
      }
      await Promise.all([...document.images].filter(image => image.getAttribute('src')).map(image => image.decode()));
      scrollTo({top: oldY, behavior: 'instant'});
    }""")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--devices", nargs="+", choices=["desktop", "tablet", "phone"], default=["desktop", "tablet", "phone"])
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height, name in [(1600, 1120, "desktop"), (820, 1180, "tablet"), (390, 844, "phone")]:
            if name not in args.devices:
                continue
            context = browser.new_context(viewport={"width": width, "height": height}, has_touch=name != "desktop", is_mobile=name != "desktop", reduced_motion="reduce")
            page = context.new_page()
            for path, surface in [("/", "home"), (QUBIT, "essay"), ("/lightworks/", "photography"), ("/futurememo/", "archive"), ("/research/", "research")]:
                page.goto(args.url + path, wait_until="networkidle")
                load_images(page)
                page.screenshot(path=str(args.artifacts / f"{surface}-{name}-full.png"), full_page=True)
                page.screenshot(path=str(args.artifacts / f"{surface}-{name}-opening.png"))
                if surface == "home":
                    cover_end = page.locator("[data-home-cover]").bounding_box()
                    page.screenshot(path=str(args.artifacts / f"home-{name}-opening-with-cover.png"), full_page=True,
                                    clip={"x": 0, "y": 0, "width": width, "height": cover_end["y"] + cover_end["height"] + 20})
                    for selector, label in [
                        (".exploration", "collection-instrument"),
                        (".home-photography", "photography-chapter"),
                        (".research-teaser", "unfinished-chapter"),
                    ]:
                        page.locator(selector).screenshot(path=str(args.artifacts / f"home-{name}-{label}.png"))
                    page.locator(".perspective-disclosure > summary").click()
                    page.locator(".reader-margin").screenshot(path=str(args.artifacts / f"home-{name}-reader-participation.png"))
                    if name == "phone":
                        for selector, label in [
                            (".reader-margin", "participation-entry"),
                            (".margin-axis", "participation-axis"),
                            (".margin-foot", "participation-status"),
                        ]:
                            page.locator(selector).first.evaluate("el => el.scrollIntoView({block:'start',behavior:'instant'})")
                            page.screenshot(path=str(args.artifacts / f"home-{name}-{label}.png"))
                if surface == "essay":
                    opening_height = page.locator("#reading").bounding_box()["y"]
                    page.screenshot(path=str(args.artifacts / f"essay-{name}-opening-with-cover.png"), full_page=True, clip={"x": 0, "y": 0, "width": width, "height": opening_height})
                    page.locator("#essay-body").evaluate("el => el.scrollIntoView({block:'start',behavior:'instant'})")
                    page.screenshot(path=str(args.artifacts / f"essay-{name}-reading.png"))
                    page.locator(".open-lens").click()
                    page.locator("#term-query").fill("systems")
                    page.locator("#term-form").evaluate("form => form.requestSubmit()")
                    page.screenshot(path=str(args.artifacts / f"essay-{name}-term.png"))
                    model = page.locator("#essay-data").evaluate("el=>JSON.parse(el.textContent)")
                    passage = next(p for p in model["passages"] if p["terms"].get("systems") and p["related"])
                    page.locator(f'button[data-inspect="{passage["id"]}"]').evaluate("el => el.click()")
                    page.locator("#inspected-link").click()
                    page.wait_for_timeout(100)
                    page.screenshot(path=str(args.artifacts / f"essay-{name}-connections.png"))
                    page.locator("#reading-lens").evaluate("""el => {
                      const related = document.getElementById('related-passages');
                      el.scrollTop += related.getBoundingClientRect().top - el.getBoundingClientRect().top
                        - el.querySelector('.lens-heading').getBoundingClientRect().height - 24;
                    }""")
                    page.screenshot(path=str(args.artifacts / f"essay-{name}-neighbors.png"))
                    page.locator("#close-lens").click()
                    page.screenshot(path=str(args.artifacts / f"essay-{name}-returned.png"))
            page.goto(args.url + "/futurememo/are-you-an-ai-illiterate/#p-960587f273", wait_until="networkidle")
            page.screenshot(path=str(args.artifacts / f"restored-table-{name}.png"))
            context.close()
        browser.close()
    print(f"Review artifacts: {args.artifacts}")


if __name__ == "__main__":
    main()
