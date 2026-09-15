"""Public atlas retirement and preserved native writing journeys."""
import argparse
import builtins
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
RETIRED = ("atlas.css", "atlas.js", "atlas-map.js")


def static_checks(artifacts):
    from unittest.mock import patch
    from bs4 import BeautifulSoup
    import build_site

    def audit(output):
        pages = sorted(output.rglob("*.html"))
        assert pages
        for path in pages:
            page = BeautifulSoup(path.read_bytes(), "html.parser")
            assert not page.select("[data-question-atlas], [data-atlas-map], [id^='atlas-'], #by-preoccupation, #question-atlas, .ideas"), path
            for node in page.select("a[href], link[href], script[src]"):
                url = urlsplit(node.get("href", node.get("src", "")))
                assert url.path not in {"/assets/" + name for name in RETIRED}, (path, url)
                if not url.netloc or url.netloc == "suffsyed.com":
                    assert url.fragment not in {"by-preoccupation", "question-atlas"}, (path, url)
                    assert not url.fragment.startswith("atlas-"), (path, url)
                    assert not re.fullmatch(r"theme-\d+", url.fragment), (path, url)
            # Published references to products called Atlas are not this retired feature.
            for original in page.select("#essay-body, #essay-data"):
                original.decompose()
            assert not re.search(r"question atlas|(?:question|theme) index", page.get_text(" ", strip=True), re.I), path
        for name in RETIRED:
            assert not (output / "assets" / name).exists()
        return len(pages)

    count = audit(ROOT / "docs")
    assert all((ROOT / "site" / name).is_file() for name in RETIRED)
    assert (ROOT / "content/question-atlas.json").is_file()
    assert (ROOT / "tools/question_atlas.py").is_file()
    assert (ROOT / "tools/retired_atlas_checks.py").is_file()
    assert not (ROOT / "tools/test_atlas.py").exists()
    source = (ROOT / "tools/build_site.py").read_text()
    assert not any(token in source for token in ("build_atlas", "render_atlas", "question-atlas.json"))

    original_read, original_open, original_import = Path.read_text, builtins.open, builtins.__import__
    def read(path, *args, **kwargs):
        if path.name == "question-atlas.json":
            raise FileNotFoundError("Retired atlas configuration is unavailable")
        return original_read(path, *args, **kwargs)
    def open_file(file, *args, **kwargs):
        if isinstance(file, (str, Path)) and Path(file).name == "question-atlas.json":
            raise FileNotFoundError("Retired atlas configuration is unavailable")
        return original_open(file, *args, **kwargs)
    def import_module(name, *args, **kwargs):
        if name.rsplit(".", 1)[-1] == "question_atlas":
            raise ModuleNotFoundError("Retired atlas implementation is unavailable")
        return original_import(name, *args, **kwargs)

    with tempfile.TemporaryDirectory(prefix="atlas-retirement-") as directory:
        output = Path(directory) / "docs"
        shutil.copytree(ROOT / "docs/assets/img", output / "assets/img")
        shutil.copyfile(ROOT / "docs/CNAME", output / "CNAME")
        for name in RETIRED:
            shutil.copyfile(ROOT / "site" / name, output / "assets" / name)
        with patch.object(build_site, "OUT", output), patch.object(sys, "argv", ["build_site.py"]), \
                patch.object(Path, "read_text", read), patch.object(builtins, "open", open_file), \
                patch.object(builtins, "__import__", import_module):
            build_site.main()
        assert audit(output) == count
        for original in (ROOT / "docs/assets/img").iterdir():
            if original.is_file():
                assert original.read_bytes() == (output / "assets/img" / original.name).read_bytes()
        isolated_count = sum(path.is_file() for path in output.rglob("*"))
    report = {"publicPages": count, "retiredAssetsAbsent": list(RETIRED),
              "isolatedBuild": True, "configReadsAndImportsBlocked": True,
              "threeSeededAssetsRemoved": True, "originalImagesPreserved": True,
              "isolatedOutputFiles": isolated_count}
    if artifacts:
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / "static.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {count} public pages without atlas UI/links/assets; isolated build with retired config/imports blocked; three seeded stale assets removed; source images intact.")


def browser_checks(args):
    from playwright.sync_api import sync_playwright
    from test_reader_detail import open_details, click_native, assert_anchor, body_position

    args.artifacts.mkdir(parents=True, exist_ok=True)
    report, errors, requests = {"pages": [], "writing": []}, [], []
    with sync_playwright() as p:
        browser = p.webkit.launch()
        context = browser.new_context(viewport={"width": 1028, "height": 1000}, reduced_motion="reduce")
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        for path in sorted((ROOT / "docs").rglob("*.html")):
            route = "/" + path.relative_to(ROOT / "docs").as_posix()
            page.goto(args.url + route, wait_until="networkidle")
            assert page.locator("[data-question-atlas], [data-atlas-map], #by-preoccupation, #question-atlas").count() == 0
            report["pages"].append(route)
        page.goto(args.url + "/the-end-of-design-report/", wait_until="networkidle")
        page.locator('a[href="/futurememo/?theme=Design"]').click()
        page.wait_for_url("**/futurememo/?theme=Design", wait_until="networkidle")
        assert page.locator("#archive-theme").input_value() == "Design"
        rows = json.loads((ROOT / "content/corpus.json").read_text())["essays"]
        assert page.locator(".archive-entry:visible").count() == sum(row["theme"] == "Design" for row in rows)
        report["reportDesignFilter"] = True
        for width in (390, 1028):
            page.set_viewport_size({"width": width, "height": 844 if width == 390 else 1000})
            page.goto(args.url, wait_until="networkidle")
            assert page.locator(".ideas, .idea-field, [data-motion-scene], script").count() == 0
            assert page.locator("main > section").count() == 2
            assert page.locator(".writing-list > li").count() == 4
            assert page.locator("main").evaluate("e=>e.nextElementSibling.classList.contains('site-footer')")
            page.locator(".writing-plane").last.scroll_into_view_if_needed()
            last = page.locator(".writing-plane").last.bounding_box()
            footer = page.locator(".site-footer").bounding_box()
            assert 0 <= footer["y"] - last["y"] - last["height"] <= 256
            assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
            link = page.locator(".writing-plane").last.locator(".reading-action")
            click_native(page, link)
            page.wait_for_url("**/futurememo/how-future-designers-will-win-in-the-age-of-ai/", wait_until="networkidle")
            assert page.locator(".essay-artwork img").get_attribute("src") == "/assets/img/9fe1e028baa0.webp"
            assert page.locator("#essay-body img").count() == 0
            assert page.locator(".series-context").get_attribute("data-series-part") == "4"
            open_details(page, "#reader-tools")
            open_details(page, "#ai-reading-guide")
            link = page.locator("[data-guide-anchor]").nth(2)
            identifier = link.get_attribute("href")[1:]
            click_native(page, link)
            assert_anchor(page, identifier)
            for fraction in (0, .5, 1):
                body_position(page, fraction)
                assert abs(page.locator(".reading-position progress").evaluate("e=>e.value") - fraction * 100) <= 1
            body_position(page, .5)
            y, url = page.evaluate("scrollY"), page.url
            page.goto(args.url + "/futurememo/#by-preoccupation", wait_until="networkidle")
            assert page.locator(".archive-entry").count() == 20
            assert page.locator("#by-preoccupation").count() == 0
            page.go_back(wait_until="networkidle")
            assert page.url == url and abs(page.evaluate("scrollY") - y) < 2
            report["writing"].append({"width": width, "series": True, "reader": True, "bodyProgress": [0, 50, 100], "backError": abs(page.evaluate("scrollY") - y)})
        context.close()
        static = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
        page = static.new_page()
        page.goto(args.url, wait_until="networkidle")
        page.locator(".writing-list .reading-action").first.click()
        assert page.locator("#essay-body").is_visible()
        assert page.locator(".series-context").get_attribute("data-series-part") == "1"
        page.goto(args.url + "/futurememo/#by-preoccupation", wait_until="networkidle")
        page.locator(".archive-discovery > summary").click()
        assert page.locator(".archive-native-note").inner_text() == "Search and filters need JavaScript. All essays remain available below."
        assert page.locator(".archive-entry").count() == 20
        page.locator(".entry-read").first.click()
        assert page.locator("#essay-body").is_visible()
        static.close()
        browser.close()
    assert not errors, errors
    retired_requests = [url for url in requests if urlsplit(url).path in {"/assets/" + name for name in RETIRED}]
    assert not retired_requests
    for name in RETIRED:
        try:
            urlopen(args.url + "/assets/" + name)
        except HTTPError as error:
            assert error.code == 404
        else:
            raise AssertionError(f"Retired asset still publicly served: {name}")
    report.update(errors=errors, atlasRequests=retired_requests, retiredAssetsHttp404=True, noJS=True)
    (args.artifacts / "browser.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: all public-page requests atlas-free; three assets404; natural home ending, series/reader/source/progress/Back and no-JS preserved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8774")
    parser.add_argument("--artifacts", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--static-only", action="store_true")
    mode.add_argument("--browser-only", action="store_true")
    args = parser.parse_args()
    if not args.browser_only:
        static_checks(args.artifacts)
    if not args.static_only:
        if not args.artifacts:
            parser.error("--artifacts is required for browser checks")
        browser_checks(args)
