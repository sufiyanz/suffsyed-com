"""Structured archive rows, retained search and an unpublished growth fixture."""
import argparse
import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SLUG = "archive-growth-fixture-not-published"
FIXTURE_TITLE = "Growth-only-title / Unpublished renderer fixture"


def static_checks(fixtures):
    from unittest.mock import patch
    from bs4 import BeautifulSoup
    from build_site import archive_page
    from corpus import measure

    data = json.loads((ROOT / "content/corpus.json").read_text())
    descriptions = json.loads((ROOT / "content/cover-descriptions.json").read_text())
    rows = [{**measure(row, ROOT), "coverAlt": descriptions[row["slug"]]} for row in data["essays"]]

    def render(items):
        with patch("build_site.write") as write:
            archive_page(items, data)
        write.assert_called_once()
        assert write.call_args.args[0] == "/futurememo/index.html"
        return write.call_args.args[1]

    def verify(markup, items):
        page = BeautifulSoup(markup, "html.parser")
        assert page.select_one(".archive-brand").get_text() == "Future (Memo)"
        assert page.title.get_text().startswith("Future (Memo)")
        assert page.select_one("#archive-theme option").get_text() == "All themes"
        assert not page.select(".entry-number, .archive-entry > .entry-read, [data-number]")
        assert page.select_one("#archive-status").get_text() == f'{len(items)} essays · {sum(r["words"] for r in items):,} words'
        for node in page.select(".page-opening, .archive-native-note"):
            assert not re.search(r"\b(twenty|five|four)\b", node.get_text(), re.I)
        entries = page.select(".archive-entry")
        assert len(entries) == len(items)
        for entry, row in zip(entries, items):
            assert entry["data-slug"] == row["slug"]
            assert entry["data-theme"] == row["theme"]
            assert entry.h2.get_text() == row["title"]
            assert entry.img["src"] == row["cover"] and entry.img["alt"] == row["coverAlt"]
            assert [entry.select_one(s)["href"] for s in (".archive-art", "h2 a", ".entry-read")] == [row["url"]] * 3
            assert "Read essay" in entry.select_one(".reading-action").get_text()
            assert entry.select_one(".entry-thread a")["href"].startswith(row["url"] + "?term=")
        assert not page.select("[data-question-atlas], [data-atlas-entry], #by-preoccupation")
        assert len(page.select("#archive-theme option")) == len(data["themes"]) + 1
        return page

    actual = render(rows)
    verify(actual, rows)
    assert actual == (ROOT / "docs/futurememo/index.html").read_text()
    original = next(row for row in rows if row["theme"] == "Design")
    extra = copy.deepcopy(original)
    extra.update(slug=FIXTURE_SLUG, no=21, title=FIXTURE_TITLE, url=f"/futurememo/{FIXTURE_SLUG}/")
    grown_rows = [*rows, extra]
    grown = render(grown_rows)
    page = verify(grown, grown_rows)
    assert len(page.select(".archive-entry")) == 21
    assert len(page.select('.archive-entry[data-theme="Design"]')) == 6
    assert not (ROOT / "docs/futurememo" / FIXTURE_SLUG).exists()
    assert FIXTURE_SLUG not in [row["slug"] for row in data["essays"]]
    if fixtures:
        fixtures.mkdir(parents=True, exist_ok=True)
        (fixtures / "growth.html").write_text(grown)
        index = json.loads((ROOT / "docs/assets/search-index.json").read_text())
        search_extra = copy.deepcopy(next(row for row in index if row["slug"] == original["slug"]))
        search_extra.update(slug=extra["slug"], title=extra["title"], url=extra["url"])
        (fixtures / "search-index.json").write_text(json.dumps([*index, search_extra]))
    print("PASS: exact titles/art/URLs, size-neutral branding, data-derived counts, no atlas dependency; unpublished 21-row renderer and six-member theme.")


def browser_checks(args):
    from playwright.sync_api import sync_playwright
    from test_foundation import image_evidence
    from test_reader_detail import assert_anchor

    args.artifacts.mkdir(parents=True, exist_ok=True)
    rows = json.loads((ROOT / "content/corpus.json").read_text())["essays"]
    report, errors = {"layouts": [], "images": [], "search": [], "growth": {}}, []

    def search(page, phrase):
        page.locator("#archive-query").fill(phrase)
        page.locator("#archive-search").evaluate("form=>form.requestSubmit()")
        page.wait_for_function("!document.querySelector('#archive-status').textContent.includes('Opening')")

    with sync_playwright() as p:
        browser = p.webkit.launch()
        context = browser.new_context(reduced_motion="reduce")
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        for width in (320, 390, 700, 701, 820, 1028, 1280, 1440, 1600):
            page.set_viewport_size({"width": width, "height": 844 if width <= 700 else 1000})
            page.goto(args.url + "/futurememo/", wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            assert page.locator(".archive-entry").count() == len(rows)
            assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
            for entry, row in zip(page.locator(".archive-entry").all(), rows):
                assert entry.locator("h2").inner_text() == row["title"]
                assert entry.locator(".archive-art").get_attribute("href") == f'/futurememo/{row["slug"]}/'
            for compact in (False, True):
                if compact:
                    page.locator(".archive-discovery > summary").click()
                    page.locator("#archive-list-toggle").click()
                boxes = page.locator(".archive-entry").evaluate_all("""es=>es.map(e=>{
                  const box=n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};};
                  const a=e.querySelector('.archive-art'),c=e.querySelector('.entry-copy'),r=e.querySelector('.entry-read');
                  return {row:box(e),art:box(a),copy:box(c),action:box(r),
                    border:parseFloat(getComputedStyle(e).borderTopWidth),
                    actionFont:parseFloat(getComputedStyle(r).fontSize),
                    thread:getComputedStyle(e.querySelector('.entry-thread')).display,
                    columns:getComputedStyle(e).gridTemplateColumns};
                })""")
                for index, box in enumerate(boxes):
                    assert box["border"] >= 1 and box["action"]["h"] >= 44 and box["actionFont"] >= 18
                    assert box["thread"] != "none"
                    if index:
                        previous = boxes[index - 1]["row"]
                        assert abs(box["row"]["y"] - previous["y"] - previous["h"]) < 1
                    assert abs(box["row"]["w"] - boxes[0]["row"]["w"]) < 1
                    if compact:
                        assert box["art"]["w"] == 0
                        assert abs(box["copy"]["x"] - box["row"]["x"]) < 1
                        assert abs(box["copy"]["w"] - box["row"]["w"]) < 1
                    elif width <= 700:
                        assert abs(box["art"]["w"] - (width - 48)) < 1
                        assert box["copy"]["y"] >= box["art"]["y"] + box["art"]["h"] + 23
                    else:
                        assert abs(box["art"]["y"] - box["copy"]["y"]) < 1
                        assert box["copy"]["x"] >= box["art"]["x"] + box["art"]["w"] + 31
                report["layouts"].append({"width": width, "compact": compact, "first": boxes[0]})
                if width in (390, 1028, 1600):
                    page.locator(".archive-entry").first.evaluate("e=>e.scrollIntoView()")
                    page.screenshot(path=str(args.artifacts / f'rows-{width}-{"compact" if compact else "art"}.png'))
                if not compact and width in (390, 1028, 1600):
                    report["images"].append({"width": width, "images": [image_evidence(img) for img in page.locator(".archive-art img").all()]})
            page.locator("#archive-list-toggle").click()
            assert page.locator(".archive-art:visible").count() == len(rows)

        page.goto(args.url + "/futurememo/", wait_until="networkidle")
        page.locator(".archive-discovery > summary").click()
        index = json.loads((ROOT / "docs/assets/search-index.json").read_text())
        for phrase in ("judgment", "Claude Cowork", "no-such-phrase-archive-fixture"):
            search(page, phrase)
            expected = [row["slug"] for row in index if phrase.lower() in row["title"].lower()
                        or any(phrase.lower() in passage["text"].lower() for passage in row["passages"])]
            actual = page.locator(".archive-entry:visible").evaluate_all("es=>es.map(e=>e.dataset.slug)")
            assert actual == expected, (phrase, actual, expected)
            report["search"].append({"phrase": phrase, "matches": len(actual)})
        page.locator("#archive-reset").click()
        assert page.locator(".archive-entry:visible").count() == len(rows)
        page.locator("#archive-theme").select_option("Design")
        assert page.locator(".archive-entry:visible").count() == sum(row["theme"] == "Design" for row in rows)
        page.goto(args.url + "/futurememo/?q=judgment&theme=Builders+%26+craft", wait_until="networkidle")
        assert page.locator(".archive-discovery").evaluate("e=>e.open")
        assert page.locator("#archive-query").input_value() == "judgment"
        assert page.locator("#archive-theme").input_value() == "Builders & craft"
        target = page.locator(".archive-matches a").first.get_attribute("href")
        page.locator(".archive-matches a").first.click()
        page.wait_for_url(args.url + target, wait_until="networkidle")
        assert_anchor(page, target.split("#")[1])

        failure = browser.new_context()
        failure.route("**/search-index.json", lambda route: route.fulfill(status=503, body="Unavailable"))
        failed = failure.new_page()
        failed.goto(args.url + "/futurememo/", wait_until="networkidle")
        failed.locator(".archive-discovery > summary").click()
        search(failed, "judgment")
        assert "could not be loaded" in failed.locator("#archive-status").inner_text()
        assert failed.locator(".archive-entry:visible").count() == len(rows)
        failure.unroute("**/search-index.json")
        search(failed, "judgment")
        assert "matching passages" in failed.locator("#archive-status").inner_text()
        failure.close()

        growth = browser.new_context(viewport={"width": 1028, "height": 1000}, reduced_motion="reduce")
        growth.route("**/__test_archive_growth__/**", lambda route: route.fulfill(
            body=(args.fixtures / "growth.html").read_text(), content_type="text/html"))
        growth.route("**/search-index.json", lambda route: route.fulfill(
            body=(args.fixtures / "search-index.json").read_text(), content_type="application/json"))
        grown = growth.new_page()
        grown.on("pageerror", lambda error: errors.append(str(error)))
        grown.goto(args.url + "/__test_archive_growth__/", wait_until="networkidle")
        assert grown.locator(".archive-entry").count() == 21
        assert grown.locator("#archive-status").inner_text().startswith("21 essays")
        grown.locator(".archive-discovery > summary").click()
        search(grown, "Growth-only-title")
        assert grown.locator(".archive-entry:visible").count() == 1
        assert grown.locator(".archive-entry:visible h2").inner_text() == FIXTURE_TITLE
        assert "0 matching passages" in grown.locator("#archive-status").inner_text()
        grown.locator("#archive-reset").click()
        assert grown.locator(".archive-entry:visible").count() == 21
        grown.locator("#archive-list-toggle").click()
        assert grown.locator(".entry-read:visible").count() == 21
        grown.locator("#archive-theme").select_option("Design")
        assert grown.locator(".archive-entry:visible").count() == 6
        report["growth"] = {"rendered": 21, "reset": 21, "compactActions": 21, "themeMatches": 6, "titleOnlyMatches": 1, "published": False}
        growth.close()
        for width in (390, 1028):
            static = browser.new_context(java_script_enabled=False, viewport={"width": width, "height": 1000})
            native = static.new_page()
            native.goto(args.url + "/futurememo/", wait_until="networkidle")
            assert native.locator(".archive-entry").count() == len(rows)
            native.locator(".archive-discovery > summary").click()
            assert "All essays" in native.locator(".archive-native-note").inner_text()
            native.locator(".entry-read").first.click()
            assert native.locator("#essay-body").is_visible()
            static.close()
        context.close()
        browser.close()
    assert not errors, errors
    report.update(errors=errors, errorRecovery=True, nativeSource=True, noJS=True)
    (args.artifacts / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: normal/compact row geometry at nine widths; all original art/links; search/source/error/reset/no-JS; unpublished 21-row search/theme/compact growth.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8774")
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--artifacts", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--static-only", action="store_true")
    mode.add_argument("--browser-only", action="store_true")
    args = parser.parse_args()
    if not args.browser_only:
        static_checks(args.fixtures)
    if not args.static_only:
        if not args.fixtures or not args.artifacts:
            parser.error("--fixtures and --artifacts are required for browser checks")
        browser_checks(args)
