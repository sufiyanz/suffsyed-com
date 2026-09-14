"""Real browser interaction checks; requires Playwright and a running preview."""
import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "content/corpus.json").read_text())
QUBIT = "/futurememo/qubit-teams-the-future-built-by-two-people-using-ai/"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--browser", choices=["chromium", "webkit"], default="chromium")
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    errors, missing, external = [], [], []
    with sync_playwright() as p:
        browser = getattr(p, args.browser).launch()
        context = browser.new_context(viewport={"width": 1600, "height": 1120}, device_scale_factor=1)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("response", lambda response: missing.append(f"{response.status} {response.url}") if response.status >= 400 else None)
        page.on("request", lambda request: external.append(request.url) if not request.url.startswith(args.url) and not request.url.startswith("data:") else None)
        page.goto(args.url, wait_until="networkidle")
        page.screenshot(path=str(args.artifacts / "home-desktop.png"), full_page=True)
        assert page.locator("h1").count() == 1
        page.locator(".exhibition-art").first.click()
        page.locator(".essay-artwork [data-artwork]").first.click()
        assert page.locator("#artwork-dialog").is_visible()
        page.wait_for_function("document.getElementById('artwork-image').naturalWidth > 0")
        page.keyboard.press("Escape")
        assert not page.locator("#artwork-dialog").is_visible()

        # Every essay loads its entire addressable body; measured counts are checked
        # against text nodes by the reader itself, not a screenshot proxy.
        for row in DATA["essays"]:
            page.goto(args.url + f'/futurememo/{row["slug"]}/', wait_until="networkidle")
            model = json.loads(page.locator("#essay-data").text_content())
            assert page.locator("#essay-body [data-passage]").count() == len(model["passages"])
            page.locator(".open-lens").click()
            for term in [model["terms"][0]["term"], "ai", "judgment", "design", "team", "teams", "it's"]:
                query = page.locator("#term-query")
                query.fill(term)
                page.locator("#term-form").evaluate("form => form.requestSubmit()")
                count = sum(passage["terms"].get(term, 0) for passage in model["passages"])
                assert page.locator("#term-status").inner_text().startswith(f"{count} occurrence"), (row["slug"], term)
                assert "does not match" not in page.locator("#term-status").inner_text()
            page.locator("#close-lens").click()
            assert page.locator("#essay-body mark").count() == 0
            assert not page.locator("#reading-lens").is_visible()
            for table in page.locator(".table-passage > .passage-text").all():
                assert table.locator("table thead").count() == 1
                table.focus()
                assert table.evaluate("el=>el.contains(document.activeElement)")

        page.goto(args.url + QUBIT, wait_until="networkidle")
        page.screenshot(path=str(args.artifacts / "essay-desktop.png"), full_page=True)
        model = json.loads(page.locator("#essay-data").text_content())
        page.locator(".open-lens").click()
        query = page.locator("#term-query")
        query.fill("systems")
        page.locator("#term-form").evaluate("form => form.requestSubmit()")
        section = model["sections"][1]
        page.locator("#term-scope").select_option(section["id"])
        expected = sum(passage["terms"].get("systems", 0) for passage in model["passages"] if passage["section"] == section["id"])
        assert page.locator("#term-status").inner_text().startswith(f"{expected} occurrence")
        page.locator("#term-scope").select_option("")
        page.screenshot(path=str(args.artifacts / "essay-reading-lens.png"), full_page=True)
        first_result = page.locator("#term-results > li a").first
        if first_result.count():
            target = first_result.get_attribute("href")[1:]
            first_result.click()
            assert page.evaluate("document.activeElement.id") == target
        for invalid in ["system", ".*", "<img src=x onerror=alert(1)>", "systems <script>"]:
            query.fill(invalid)
            page.locator("#term-form").evaluate("form => form.requestSubmit()")
            assert not page.locator("#reading-lens img").count()
            assert not page.locator("#essay-body mark").filter(has_text="systems").count()
        passage = next(p for p in model["passages"] if p["related"])
        page.locator(f'button[data-inspect="{passage["id"]}"]').evaluate("button => button.click()")
        assert page.locator("#passage-inspector").is_visible()
        assert "Shared words:" in page.locator("#related-passages").inner_text()
        destination = page.locator("#related-passages a").first
        href = destination.get_attribute("href")
        destination.click()
        assert page.url.endswith(href)
        assert page.locator(f'#{href.split("#")[1]}').count() == 1
        page.go_back(wait_until="networkidle")
        assert QUBIT in page.url
        page.locator(".open-lens").click()
        page.locator(f'button[data-inspect="{passage["id"]}"]').evaluate("button => button.click()")
        page.locator("#inspected-link").click()
        assert page.evaluate("document.activeElement.id") == passage["id"]
        before = page.locator(f'#{passage["id"]}').bounding_box()["y"]
        page.locator("#close-lens").click()
        page.wait_for_timeout(200)
        after = page.locator(f'#{passage["id"]}').bounding_box()["y"]
        assert abs(before - after) < 3, (before, after)
        page.goto(args.url + QUBIT + "?term=systems#reading-lens", wait_until="networkidle")
        assert page.locator("#reading-lens").is_visible()
        assert "systems" in page.locator("#term-status").inner_text()
        assert page.locator("#essay-body mark").count() > 0

        page.goto(args.url + "/futurememo/", wait_until="networkidle")
        page.locator(".archive-discovery > summary").click()
        page.locator("#archive-query").fill("judgment")
        page.locator("#archive-search").evaluate("form => form.requestSubmit()")
        page.wait_for_function("!document.getElementById('archive-status').textContent.includes('Opening')")
        assert "matching passages" in page.locator("#archive-status").inner_text()
        assert page.locator(".archive-matches a").count() > 0
        page.locator("#archive-theme").select_option("Builders & craft")
        assert page.locator(".archive-entry:visible").count() <= 5
        page.locator("#archive-list-toggle").click()
        assert page.locator("#archive-entries").evaluate("el => el.classList.contains('compact')")
        page.locator("#archive-reset").click()
        assert page.locator(".archive-entry:visible").count() == 20
        page.locator("#archive-list-toggle").click()
        page.screenshot(path=str(args.artifacts / "archive-desktop.png"), full_page=True)
        page.locator("#archive-query").fill('<img src=x onerror="alert(1)">')
        page.locator("#archive-search").evaluate("form => form.requestSubmit()")
        assert page.locator(".archive-entry:visible").count() == 0
        assert "0 essays" in page.locator("#archive-status").inner_text()

        page.goto(args.url + "/lightworks/", wait_until="networkidle")
        assert page.locator("[data-gallery]").count() == 22
        page.locator("[data-gallery]").first.click()
        assert page.locator("#artwork-prev").is_disabled()
        page.locator("#artwork-next").click()
        assert "02" in page.locator("#artwork-title").inner_text()
        page.keyboard.press("ArrowRight")
        assert "03" in page.locator("#artwork-title").inner_text()
        page.keyboard.press("Escape")
        page.screenshot(path=str(args.artifacts / "photography-desktop.png"), full_page=True)

        for route in ["about-me", "about-the-memo", "faqs", "the-end-of-design-report", "store", "methods", "research"]:
            page.goto(args.url + f"/{route}/", wait_until="networkidle")
            assert page.locator("h1").count() == 1, route
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"), route
        for route, target in [("home", "/"), ("member-site-homepage-1", "/"), ("futurememo/tag/June+2024+Edition", "/futurememo/"), ("store/p/chemex", "/store/")]:
            page.goto(args.url + f"/{route}/")
            page.wait_for_url(args.url + target)

        # The loaded essay's complete text and analytic index need no network.
        offline = browser.new_context()
        offline_page = offline.new_page()
        offline_page.goto(args.url + QUBIT, wait_until="networkidle")
        offline.set_offline(True)
        offline_page.locator(".open-lens").click()
        offline_page.locator("#term-query").fill("systems")
        offline_page.locator("#term-form").evaluate("form => form.requestSubmit()")
        assert offline_page.locator("#term-status").inner_text().startswith("10 occurrences")
        assert "It’s how precisely two people can decide." in offline_page.locator("#essay-body").inner_text()
        offline.close()

        unavailable = browser.new_context()
        failed_search = unavailable.new_page()
        failed_search.goto(args.url + "/futurememo/", wait_until="networkidle")
        failed_search.locator(".archive-discovery > summary").click()
        unavailable.set_offline(True)
        failed_search.locator("#archive-query").fill("systems")
        failed_search.locator("#archive-search").evaluate("form => form.requestSubmit()")
        failed_search.wait_for_function("document.getElementById('archive-status').textContent.includes('could not be loaded')")
        assert failed_search.locator(".archive-entry:visible").count() == 20
        unavailable.set_offline(False)
        failed_search.locator("#archive-search").evaluate("form => form.requestSubmit()")
        failed_search.wait_for_function("document.getElementById('archive-status').textContent.includes('matching passages')")
        unavailable.close()

        for width, height, name in [(820, 1180, "tablet"), (390, 844, "phone"), (320, 700, "small-phone")]:
            mobile = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True, reduced_motion="reduce")
            view = mobile.new_page()
            view.on("pageerror", lambda error: errors.append(str(error)))
            for route, label in [("/", "home"), (QUBIT, "essay"), ("/futurememo/", "archive"), ("/lightworks/", "photography"), ("/research/", "research")]:
                view.goto(args.url + route, wait_until="networkidle")
                assert not view.evaluate("document.documentElement.scrollWidth > innerWidth + 1"), (name, route)
                if name != "small-phone":
                    view.screenshot(path=str(args.artifacts / f"{label}-{name}.png"), full_page=True)
            view.goto(args.url + QUBIT)
            view.locator(".open-lens").tap()
            view.locator("#term-query").fill("judgment")
            view.locator("#term-form button[type=submit]").tap()
            assert "judgment" in view.locator("#term-status").inner_text()
            view.locator("#close-lens").tap()
            assert not view.locator("#reading-lens").is_visible()
            view.goto(args.url + "/futurememo/are-you-an-ai-illiterate/", wait_until="networkidle")
            table = view.locator(".table-passage > .passage-text").first
            table.scroll_into_view_if_needed()
            assert table.evaluate("el=>el.scrollWidth > el.clientWidth")
            table.evaluate("el=>el.scrollLeft=100")
            assert table.evaluate("el=>el.scrollLeft") == 100
            assert not view.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
            view.goto(args.url + QUBIT, wait_until="networkidle")
            view.locator(".open-lens").tap()
            model = json.loads(view.locator("#essay-data").text_content())
            selected = next(p for p in model["passages"] if p["related"])
            view.locator(f'button[data-inspect="{selected["id"]}"]').evaluate("el=>el.click()")
            view.locator("#reading-lens").evaluate("el=>el.scrollTop=el.scrollHeight")
            box = view.locator("#close-lens").bounding_box()
            lens_box = view.locator("#reading-lens").bounding_box()
            assert box["y"] >= lens_box["y"] - 1
            assert box["y"] + box["height"] <= lens_box["y"] + lens_box["height"]
            view.locator("#inspected-link").click()
            target = view.locator(f'#{selected["id"]}')
            before = target.bounding_box()["y"]
            view.locator("#close-lens").tap()
            view.wait_for_timeout(150)
            assert abs(target.bounding_box()["y"] - before) < 3, (width, before, target.bounding_box()["y"])
            assert view.evaluate("document.activeElement.id") == selected["id"]
            view.locator(".contents summary").tap()
            if width < 760:
                view.locator(".contents a").nth(1).tap()
                assert "#" in view.url
            mobile.close()

        no_js = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
        view = no_js.new_page()
        for row in DATA["essays"]:
            view.goto(args.url + f'/futurememo/{row["slug"]}/')
            assert view.locator("#essay-body .passage-text").count() > 10
            assert not view.locator(".reading-lens").is_visible()
            assert view.locator(".contents a").count() > 0
        view.goto(args.url)
        assert view.locator(".writing-list h3").first.inner_text()
        assert view.locator('a[href^="/futurememo/"]').count() > 5
        no_js.close()
        browser.close()
    assert not errors, errors
    assert not missing, missing
    assert not external, external
    print("PASS: complete essays, exact counts, full-word safety, passage destinations, archive, gallery, routes, desktop/tablet/touch, no-JS, no browser errors or external requests.")


if __name__ == "__main__":
    main()
