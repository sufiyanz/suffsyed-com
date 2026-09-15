"""The real archive lead on one document-scrolling gallery entrance surface."""
import argparse
import io
import json
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

from foundation_home import DESCRIPTION, IDENTITY
from test_foundation import image_evidence
from test_navigation import header_bounds

WIDTHS = (320, 390, 820, 1028, 1280, 1440, 1600)
SERIES_SLUGS = [part["slug"] for part in json.loads(
    (Path(__file__).resolve().parents[1] / "content/series.json").read_text())["parts"]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8774")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report, errors = {"viewports": [], "scroll": [], "series": []}, []
    with sync_playwright() as p:
        browser = p.webkit.launch()
        context = browser.new_context()
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url + "/futurememo/", wait_until="networkidle")
        archive_lead = page.locator(".archive-entry").first.evaluate("""el=>({
          slug:el.dataset.slug,href:el.querySelector('.archive-art').getAttribute('href'),
          title:el.querySelector('h2').textContent,src:el.querySelector('img').getAttribute('src'),
          alt:el.querySelector('img').alt})""")
        assert page.locator(".archive-entry").count() == 20
        for width in WIDTHS:
            height = 844 if width <= 700 else 1000
            page.set_viewport_size({"width": width, "height": height})
            page.goto(args.url, wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.locator(".featured-art img").evaluate("el=>el.decode()")
            header = header_bounds(page)
            assert header["y"] == 0 and header["height"] == (120 if width <= 700 else 88)
            assert page.locator(".gallery-masthead").evaluate(
                "el=>el.parentElement===document.body && getComputedStyle(el).position==='absolute'")
            assert page.locator(".gallery-masthead").evaluate(
                "el=>getComputedStyle(el).backgroundImage==='none' && getComputedStyle(el).backgroundColor==='rgba(0, 0, 0, 0)'")
            assert page.locator(".gallery-cover").bounding_box()["y"] == 0
            assert page.locator(".cover-introduction").evaluate(
                "el=>getComputedStyle(el).backgroundColor==='rgba(0, 0, 0, 0)'")
            assert page.locator(".cover-description").inner_text() == DESCRIPTION
            assert page.locator(".cover-role").inner_text() == IDENTITY
            assert page.locator(".site-name,.editorial-plane,.hero-field,.hero-geometry").count() == 0
            assert page.locator(".gallery-masthead .cover-signature").count() == 1
            assert page.locator(".gallery-cover .cover-signature").count() == 0
            feature = page.locator(".featured-essay")
            assert feature.get_attribute("data-featured-slug") == archive_lead["slug"]
            assert feature.locator("h2").inner_text() == archive_lead["title"]
            assert feature.locator(".exhibition-label").text_content() == "Featured essay"
            assert feature.locator("a").evaluate_all("es=>es.map(e=>e.getAttribute('href'))") == [archive_lead["href"]] * 3
            assert feature.locator("img").get_attribute("src") == archive_lead["src"]
            assert feature.locator("img").get_attribute("alt") == archive_lead["alt"]
            assert archive_lead["href"] not in page.locator(".writing-list .exhibition-art").evaluate_all(
                "es=>es.map(e=>e.getAttribute('href'))")
            intro = page.locator(".cover-description").bounding_box()
            role = page.locator(".cover-role").bounding_box()
            art = page.locator(".featured-art").bounding_box()
            caption = feature.locator("figcaption").bounding_box()
            assert intro["y"] >= header["height"] + 20
            assert role["y"] >= intro["y"] + intro["height"]
            assert art["y"] >= role["y"] + role["height"] + 20
            if width <= 700:
                assert art["width"] == width - 48
                assert caption["y"] >= art["y"] + art["height"] + 19
            else:
                assert caption["x"] >= art["x"] + art["width"] + 47
            page.screenshot(path=str(args.output / f"opening-{width}.png"))
            if width in (390, 1028):
                first = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
                for y in (40, 100, 240):
                    page.evaluate("y=>scrollTo(0,y)", y)
                    page.wait_for_timeout(80)
                    moved = page.locator(".gallery-masthead").bounding_box()
                    assert moved["y"] == -y
                    if y == 240:
                        assert moved["y"] + moved["height"] < 0
                    current = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
                    difference = ImageChops.difference(
                        first.crop((8, y, width - 8, height)),
                        current.crop((8, 0, width - 8, height - y)))
                    maximum = max(high for low, high in difference.getextrema())
                    # WebKit's gradient rasterization can round a channel by one level.
                    assert maximum <= 1, (width, y, maximum, "background/content did not scroll as one surface")
                    report["scroll"].append({"width": width, "scrollY": y, "headerY": moved["y"],
                                              "maximumChannelDifference": maximum, "pixelsOverOneLevel": 0})
                    current.save(args.output / f"scroll-{width}-{y}.png")
            dimensions = image_evidence(feature.locator("img"))
            heading = page.locator("#writing .chapter-heading h2")
            assert heading.inner_text() == "The Future of Design"
            assert heading.evaluate("el=>parseFloat(getComputedStyle(el).fontSize)") >= 36
            assert page.locator(".writing-list > li").evaluate_all(
                "es=>es.map(e=>e.dataset.seriesSlug)") == list(SERIES_SLUGS)
            actions = []
            for link in page.locator(".text-link").all():
                action = link.evaluate("""el=>{
                  const r=el.getBoundingClientRect(),s=getComputedStyle(el);
                  return {label:el.textContent.trim(),fontSize:parseFloat(s.fontSize),
                    height:r.height,transform:s.textTransform,primary:el.classList.contains('reading-action')};
                }""")
                assert action["fontSize"] >= (18 if action["primary"] else 16), action
                assert action["height"] >= 44 and action["transform"] == "none", action
                if action["primary"]:
                    icon = link.locator("[aria-hidden]").bounding_box()
                    assert icon["width"] >= 44 and icon["height"] >= 44
                actions.append(action)
            series_art = [image_evidence(image) for image in page.locator(".writing-list img").all()]
            report["series"].append({"width": width, "artworks": series_art, "actions": actions})
            if width in (390, 1440, 1600):
                page.locator("#writing").evaluate("el=>el.scrollIntoView()")
                page.screenshot(path=str(args.output / f"series-{width}.png"))
            for selector in (".featured-essay h2 a", ".writing-list h3 a", ".site-footer > nav a"):
                link = page.locator(selector).first
                link.focus()
                assert page.locator(".gallery-masthead").bounding_box()["y"] == -page.evaluate("scrollY")
                bounds = link.bounding_box()
                assert bounds["y"] >= 0 and bounds["y"] + bounds["height"] <= height
            report["viewports"].append({"width": width, "header": header, "intro": intro, "role": role,
                                        "art": art, "caption": caption, "image": dimensions})
        page.goto(args.url, wait_until="networkidle")
        page.locator(".featured-art").click()
        page.wait_for_url(args.url + archive_lead["href"], wait_until="networkidle")
        assert json.loads(page.locator("#essay-data").text_content())["slug"] == archive_lead["slug"]
        assert page.locator("#essay-body [data-passage]").count() > 0
        context.close()
        for width in (390, 1440):
            context = browser.new_context(java_script_enabled=False, viewport={"width": width, "height": 1000})
            page = context.new_page()
            page.goto(args.url, wait_until="networkidle")
            header_bounds(page)
            page.evaluate("scrollTo(0,240)")
            page.wait_for_timeout(80)
            header = page.locator(".gallery-masthead").bounding_box()
            assert header["y"] == -240 and header["y"] + header["height"] < 0
            assert page.locator(".cover-role").inner_text() == IDENTITY
            page.locator(".featured-essay h2 a").click()
            page.wait_for_url(args.url + archive_lead["href"], wait_until="networkidle")
            assert page.locator("#essay-body").is_visible()
            context.close()
        browser.close()
    assert not errors, errors
    report["archiveLead"] = archive_lead
    (args.output / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: real archive lead/credit, four ordered full-ratio series artworks, readable 44px+ actions, seven widths, natural masthead, focus and no-JS.")


if __name__ == "__main__":
    main()
