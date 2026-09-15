"""One reviewed lead promotion, supporting figures and affected reader behavior."""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "how-future-designers-will-win-in-the-age-of-ai"
WIDE = "/assets/img/9fe1e028baa0.webp"
PORTRAIT = "/assets/img/717a44366c7b.webp"
COWORK = "how-i-invented-claude-cowork-before-anthropic"


def static_checks():
    from unittest.mock import patch
    from bs4 import BeautifulSoup
    from PIL import Image
    from article_art import article_artwork
    from corpus import flat_text, measure

    rows = [measure(row, ROOT) for row in json.loads((ROOT / "content/corpus.json").read_text())["essays"]]
    target = next(row for row in rows if row["slug"] == SLUG)
    original = copy.deepcopy(target)
    lead, body = article_artwork(target, ROOT)
    assert lead == WIDE and target == original
    assert not body.select("img")
    assert body.find("p")["id"] == "p-93486e8954"
    assert flat_text(body) == flat_text(BeautifulSoup(target["body"], "html.parser"))

    changes = [
        lambda r: r.update(cover=WIDE),
        lambda r: r.update(body=r["body"].replace("<figure>", '<figure id="authored-anchor">', 1)),
        lambda r: r.update(body=r["body"].replace("</figure>", "<figcaption>Authored caption</figcaption></figure>", 1)),
        lambda r: r.update(body=r["body"].replace('alt=""', 'alt="New authored description"', 1)),
        lambda r: r.update(body=r["body"].replace(WIDE, PORTRAIT, 1)),
        lambda r: r.update(body=r["body"].split("</figure>", 1)[1]),
        lambda r: r.update(body="<p>New introduction</p>" + r["body"]),
        lambda r: r.update(body="New leading text" + r["body"]),
        lambda r: r.update(body=r["body"].replace("p-93486e8954", "p-changed")),
        lambda r: r.update(body=r["body"] + f'<figure><img src="{WIDE}"></figure>'),
    ]
    for change in changes:
        row = copy.deepcopy(target)
        change(row)
        try:
            article_artwork(row, ROOT)
        except ValueError as error:
            assert "Article artwork:" in str(error)
        else:
            raise AssertionError("Changed reviewed source shape/metadata was accepted")
    original_read = Path.read_bytes
    for changed in (ROOT / f"content/essays/{SLUG}.html", ROOT / "docs" / WIDE.lstrip("/"), ROOT / "docs" / PORTRAIT.lstrip("/")):
        def read(path):
            data = original_read(path)
            return data + b"changed" if path == changed else data
        with patch.object(Path, "read_bytes", read):
            try:
                article_artwork(target, ROOT)
            except ValueError as error:
                assert "Article artwork:" in str(error)
            else:
                raise AssertionError(f"Changed source/image identity was accepted: {changed}")
    unreviewed = {**target, "slug": "unreviewed-fixture"}
    untouched_lead, untouched_body = article_artwork(unreviewed, ROOT)
    assert untouched_lead == PORTRAIT and len(untouched_body.select("figure img")) == 1

    lead_count = supporting = 0
    for row in rows:
        source = BeautifulSoup((ROOT / f'content/essays/{row["slug"]}.html').read_bytes(), "html.parser")
        page = BeautifulSoup((ROOT / "docs" / row["url"].strip("/") / "index.html").read_bytes(), "html.parser")
        art = page.select(".essay-artwork img")
        assert len(art) == 1
        lead_count += len(art)
        expected = WIDE if row["slug"] == SLUG else row["cover"]
        assert art[0]["src"] == expected
        with Image.open(ROOT / "docs" / expected.lstrip("/")) as image:
            assert (int(art[0]["width"]), int(art[0]["height"])) == image.size
        assert [a["href"] for a in page.select(".essay-artwork [data-artwork]")] == [expected, expected]
        assert page.select_one('meta[property="og:image"]')["content"] == "https://suffsyed.com" + row["cover"]
        assert json.loads(page.select_one("#essay-data").string)["cover"] == row["cover"]
        figures = source.select("figure")
        if row["slug"] == SLUG:
            assert len(figures) == 1 and figures[0].img["src"] == WIDE
            assert not figures[0].select("[id], figcaption")
            figures = []
        rendered = page.select("#essay-body figure")
        assert len(rendered) == len(figures)
        for actual, authored in zip(rendered, figures):
            assert actual.img["src"] == authored.img["src"]
            clean = BeautifulSoup(str(actual), "html.parser").figure
            for tool in clean.select(".passage-tools"):
                tool.decompose()
            for span in clean.select(".passage-text"):
                span.unwrap()
            for passage in clean.select("[data-passage]"):
                del passage["data-passage"]
                del passage["tabindex"]
            del clean.img["width"]
            del clean.img["height"]
            assert str(clean) == str(authored), row["slug"]
        supporting += len(page.select("#essay-body img"))
        if row["slug"] == COWORK:
            assert len(rendered) == 7 and all(fig.figcaption for fig in rendered)
    assert (lead_count, supporting) == (20, 7)
    print("PASS: 20 opening images + seven unchanged captioned figures; one explicit promotion; source/metadata/image/shape guard failures; no automatic first-image removal.")


def browser_checks(args):
    from playwright.sync_api import sync_playwright
    from test_foundation import image_evidence
    from test_reader_detail import assert_anchor, body_position, click_native, open_details

    args.artifacts.mkdir(parents=True, exist_ok=True)
    rows = json.loads((ROOT / "content/corpus.json").read_text())["essays"]
    descriptions = json.loads((ROOT / "content/cover-descriptions.json").read_text())
    guide = json.loads((ROOT / f"content/reading-guides/{SLUG}.json").read_text())
    report, errors = {"images": [], "readers": [], "noJS": []}, []
    with sync_playwright() as p:
        browser = p.webkit.launch()
        context = browser.new_context(reduced_motion="reduce")
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        for width in (390, 1028, 1440):
            page.set_viewport_size({"width": width, "height": 844 if width == 390 else 1000})
            for row in rows:
                page.goto(args.url + f'/futurememo/{row["slug"]}/', wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                expected = WIDE if row["slug"] == SLUG else row["cover"]
                lead = page.locator(".essay-artwork img")
                assert lead.count() == 1 and lead.get_attribute("src") == expected
                assert lead.get_attribute("alt") == descriptions[row["slug"]]
                evidence = image_evidence(lead)
                assert evidence["width"] <= 640.1 and evidence["height"] <= 390.5
                assert page.locator("#essay-body img").count() == (7 if row["slug"] == COWORK else 0)
                opener = page.locator(".essay-artwork > a")
                click_native(page, opener)
                page.locator("#artwork-image").evaluate("e=>e.decode()")
                assert page.locator("#artwork-image").get_attribute("src") == args.url + expected
                assert page.locator("#artwork-original").get_attribute("href") == args.url + expected
                page.keyboard.press("Escape")
                assert page.locator("#artwork-dialog").is_hidden()
                assert opener.evaluate("e=>e===document.activeElement")
                if row["slug"] == COWORK:
                    evidence["supporting"] = []
                    for figure in page.locator("#essay-body figure").all():
                        metrics = image_evidence(figure.locator("img"))
                        style = figure.evaluate("e=>({top:getComputedStyle(e).marginTop,bottom:getComputedStyle(e).marginBottom})")
                        assert style == {"top": "32px", "bottom": "32px"}
                        image_box = figure.locator("img").bounding_box()
                        caption = figure.locator("figcaption")
                        assert caption.bounding_box()["y"] >= image_box["y"] + image_box["height"] - 1
                        assert caption.locator(".passage-text").text_content().strip()
                        metrics.update(caption=caption.locator(".passage-text").text_content(), margins=style)
                        evidence["supporting"].append(metrics)
                report["images"].append({"width": width, "slug": row["slug"], **evidence})

            page.goto(args.url + f"/futurememo/{SLUG}/", wait_until="networkidle")
            assert page.locator(".reading-position progress").evaluate("e=>e.value") == 0
            page.screenshot(path=str(args.artifacts / f"opening-{width}.png"))
            click_native(page, page.locator(".essay-artwork figcaption [data-artwork]"))
            assert page.locator("#artwork-image").get_attribute("src") == args.url + WIDE
            page.keyboard.press("Escape")
            for fraction in (0, .5, 1):
                body_position(page, fraction)
                assert abs(page.locator(".reading-position progress").evaluate("e=>e.value") - fraction * 100) <= 1
            for section in guide["sections"]:
                open_details(page, "#reader-tools")
                open_details(page, "#ai-reading-guide")
                click_native(page, page.locator(f'[data-guide-anchor="{section["anchor"]}"]'))
                assert_anchor(page, section["anchor"])
                assert page.locator(".guide-link[aria-current]").get_attribute("data-guide-anchor") == section["anchor"]
                open_details(page, "#reader-tools")
                open_details(page, "#ai-reading-guide")
                open_details(page, f'[data-guide-section="{section["id"]}"] .guide-points')
                source = page.locator(f'[data-guide-section="{section["id"]}"] .inline-sources a').first
                target = source.get_attribute("href")[1:]
                click_native(page, source)
                assert_anchor(page, target)
                expected_notes = [note for note in guide["notes"] if note["sectionId"] == section["id"]]
                assert page.locator("[data-note-section]:not([hidden])").count() == len(expected_notes)
            body_position(page, .5)
            y, url = page.evaluate("scrollY"), page.url
            page.screenshot(path=str(args.artifacts / f"reading-{width}.png"))
            body = page.locator("#essay-body").bounding_box()
            assert body["width"] == (326 if width == 390 else 640)
            assert abs(body["x"] + body["width"] / 2 - width / 2) < 1
            if width == 1440:
                assert page.locator(".reader-guide").bounding_box()["width"] == 188
                assert page.locator(".reader-notes").bounding_box()["width"] == 188
            page.goto(args.url + "/futurememo/", wait_until="networkidle")
            page.go_back(wait_until="networkidle")
            assert page.url == url and abs(page.evaluate("scrollY") - y) < 2
            report["readers"].append({"width": width, "progress": [0, 50, 100], "guideSections": len(guide["sections"]), "backError": abs(page.evaluate("scrollY") - y)})
        context.close()
        for width in (390, 1028, 1440):
            context = browser.new_context(java_script_enabled=False, viewport={"width": width, "height": 1000})
            page = context.new_page()
            page.goto(args.url + f"/futurememo/{SLUG}/", wait_until="networkidle")
            assert page.locator(".essay-artwork img").count() == 1 and page.locator("#essay-body img").count() == 0
            open_details(page, "#ai-reading-guide")
            link = page.locator("[data-guide-anchor]").nth(2)
            target = link.get_attribute("href")[1:]
            click_native(page, link)
            assert_anchor(page, target)
            page.locator(".essay-artwork > a").click()
            page.wait_for_url(args.url + WIDE)
            report["noJS"].append({"width": width, "sourceFocus": True, "originalImage": WIDE})
            context.close()
        browser.close()
    assert not errors, errors
    report["errors"] = errors
    (args.artifacts / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: all 20 leads/seven supporting images at three widths, decoded ratios/viewers; promoted-article guides/source/notes/progress/Back/no-JS.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8774")
    parser.add_argument("--artifacts", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--static-only", action="store_true")
    mode.add_argument("--browser-only", action="store_true")
    args = parser.parse_args()
    if not args.browser_only:
        static_checks()
    if not args.static_only:
        if not args.artifacts:
            parser.error("--artifacts is required for browser checks")
        browser_checks(args)
