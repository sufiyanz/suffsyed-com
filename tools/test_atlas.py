"""Source integrity and real pointer/keyboard checks for the bounded question atlas."""
import argparse
import copy
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE = "/futurememo/#by-preoccupation"
PROBE = """(() => {
  const probe = window.atlasProbe = {frames: 0, pending: new Set(), storage: 0, reveals: 0};
  const scroll = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function(...args) {
    if (this.matches('.atlas-graph, .atlas-detail')) probe.reveals++;
    return scroll.apply(this, args);
  };
  const request = window.requestAnimationFrame, cancel = window.cancelAnimationFrame;
  window.requestAnimationFrame = function(callback) {
    if (callback.name !== 'drawLines') return request(callback);
    const id = request(time => {probe.pending.delete(id); probe.frames++; callback(time);});
    probe.pending.add(id);
    return id;
  };
  window.cancelAnimationFrame = function(id) {probe.pending.delete(id); return cancel(id);};
  const write = Storage.prototype.setItem;
  Storage.prototype.setItem = function(...args) {probe.storage++; return write.apply(this, args);};
})();"""


def static_checks():
    from bs4 import BeautifulSoup
    from corpus import measure
    from question_atlas import build_atlas, render_atlas

    data = json.loads((ROOT / "content/corpus.json").read_text())
    config = json.loads((ROOT / "content/question-atlas.json").read_text())
    rows = [measure(row, ROOT) for row in data["essays"]]
    atlas = build_atlas(rows, data["themes"], config)
    markup = render_atlas(atlas)
    assert markup == render_atlas(build_atlas(rows, data["themes"], config))
    page = BeautifulSoup((ROOT / "docs/futurememo/index.html").read_text(), "html.parser")
    groups = page.select("[data-atlas-question]")
    assert len(groups) == 5 and len(page.select("[data-atlas-entry]")) == 20
    for group, theme in zip(groups, data["themes"]):
        assert group.select_one("h3").get_text() == theme["question"]
        assert group["id"] == f"theme-{data['themes'].index(theme) + 1}"
        expected = [row for row in rows if row["theme"] == theme["name"]]
        assert [e["data-atlas-entry"] for e in group.select("[data-atlas-entry]")] == [r["slug"] for r in expected]
        for entry, row in zip(group.select("[data-atlas-entry]"), expected):
            source = next(p for p in row["passages"] if p["id"] == config["entries"][row["slug"]])
            assert entry.blockquote.get_text() == source["text"]
            assert entry.blockquote["cite"] == row["url"] + "#" + source["id"]
            assert entry.select_one(".atlas-context")["href"] == entry.blockquote["cite"]
            assert entry.select_one(".atlas-essay-title").get_text() == row["title"]
            assert f'{source["words"]} words, unabridged.' in entry.get_text()
    assert len(page.select("[data-atlas-bridge]")) == 4
    for rendered, bridge in zip(page.select("[data-atlas-bridge]"), atlas["bridges"]):
        assert rendered.select_one(".atlas-reason").get_text() == bridge["reason"]
        assert [a["href"] for a in rendered.select("[data-source-slug]")] == [s["href"] for s in bridge["sources"]]
    assert len(page.select('script[src="/assets/atlas.js"]')) == 1
    assert not page.select('script[src*="atlas-map"]')
    assert not page.select("#atlas-data"), "The map must reuse the HTML, not duplicate its prose in JSON"
    for path in (ROOT / "docs").rglob("*.html"):
        if path == ROOT / "docs/futurememo/index.html":
            continue
        other = path.read_text()
        assert 'src="/assets/atlas' not in other and 'href="/assets/atlas.css"' not in other
    assert len(markup.encode()) < 45 * 1024
    initial = sum(len(gzip.compress((ROOT / "site" / name).read_bytes())) for name in ("atlas.js", "atlas.css"))
    lazy = len(gzip.compress((ROOT / "site/atlas-map.js").read_bytes()))
    assert initial < 5 * 1024 and lazy < 6 * 1024, (initial, lazy)
    for name in ("atlas.js", "atlas-map.js", "atlas.css"):
        assert (ROOT / "site" / name).read_bytes() == (ROOT / "docs/assets" / name).read_bytes()
    for name in ("atlas.js", "atlas-map.js"):
        script = (ROOT / "site" / name).read_text()
        assert not any(token in script for token in ("setInterval", "setTimeout", "localStorage", "sessionStorage", "fetch(", "innerHTML", "scrollRestoration"))

    def rejected(change):
        invalid = copy.deepcopy(config)
        change(invalid)
        try:
            build_atlas(rows, data["themes"], invalid)
        except ValueError as error:
            assert "Question atlas:" in str(error)
        else:
            raise AssertionError("Invalid atlas was accepted")

    first = rows[0]["slug"]
    rejected(lambda c: c.update(version=2))
    rejected(lambda c: c["entries"].pop(first))
    rejected(lambda c: c["entries"].update(unknown="p-missing"))
    rejected(lambda c: c["entries"].update({first: "p-missing"}))
    rejected(lambda c: c["bridges"][0].update(reason=""))
    rejected(lambda c: c["bridges"][0].update(to="design"))
    rejected(lambda c: c["bridges"][1].update(id=c["bridges"][0]["id"]))
    rejected(lambda c: c["bridges"][0]["sources"][0].update(slug=first))
    rejected(lambda c: c["bridges"][0]["sources"][0].update(passage="p-missing"))
    rejected(lambda c: c["bridges"][0].update(sources=[]))
    hostile = copy.deepcopy(atlas)
    hostile["bridges"][0]["reason"] = '<img src=x onerror="alert(1)"> & </script>'
    escaped = BeautifulSoup(render_atlas(hostile), "html.parser")
    assert not escaped.select("img, script")
    assert escaped.select_one(".atlas-reason").get_text() == hostile["bridges"][0]["reason"]
    original = next(row for row in rows if row["theme"] == "Design")
    sixth = copy.deepcopy(original)
    sixth.update(slug="atlas-sixth-essay-fixture", no=21, title="Test fixture / sixth essay",
                 url="/futurememo/atlas-sixth-essay-fixture/")
    grown_config = copy.deepcopy(config)
    grown_config["entries"][sixth["slug"]] = config["entries"][original["slug"]]
    grown = build_atlas([*rows, sixth], data["themes"], grown_config)
    design = next(q for q in grown["questions"] if q["id"] == "design")
    assert len(design["entries"]) == 6
    rendered = BeautifulSoup(render_atlas(grown), "html.parser")
    assert len(rendered.select("[data-atlas-entry]")) == 21
    assert len(rendered.select('[data-atlas-question="design"] .atlas-context')) == 6
    extra = rendered.select_one('[data-atlas-entry="atlas-sixth-essay-fixture"]')
    assert extra.blockquote.get_text() == design["entries"][-1]["text"]
    assert extra.select_one(".atlas-context")["href"] == sixth["url"] + "#" + grown_config["entries"][sixth["slug"]]
    print(f"PASS: 20 exact source passages; five editorial questions; four source-pair bridges; invalid refs fail; {initial} B initial/{lazy} B lazy gzip.")
    print("PASS: valid 21-essay corpus with a six-member theme builds and retains every native source.")


def browser_checks(args):
    from playwright.sync_api import sync_playwright
    args.artifacts.mkdir(parents=True, exist_ok=True)
    config = json.loads((ROOT / "content/question-atlas.json").read_text())
    errors = []

    def state(page):
        return page.evaluate("({frames:atlasProbe.frames,pending:atlasProbe.pending.size,storage:atlasProbe.storage,reveals:atlasProbe.reveals})")

    def in_view(page, locator, lines=3):
        metrics = locator.evaluate("""el => {
          const rect=el.getBoundingClientRect();
          return {top:rect.top,bottom:rect.bottom,height:rect.height,viewport:innerHeight,
            clearance:parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0,
            lineHeight:parseFloat(getComputedStyle(el).lineHeight)};
        }""")
        assert metrics["top"] >= metrics["clearance"] - 1, metrics
        visible = min(metrics["bottom"], metrics["viewport"]) - metrics["top"]
        required = metrics["height"] if lines is None else min(metrics["height"], metrics["lineHeight"] * lines)
        assert visible >= required - 1, metrics
        return metrics

    def inspected_detail(page, bridge=False):
        assert page.evaluate("document.activeElement.id") == "atlas-detail-title"
        section = page.locator(".atlas-detail").bounding_box()
        clearance = page.evaluate("parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop)")
        assert abs(section["y"] - clearance) <= 1, (section, clearance)
        in_view(page, page.locator("#atlas-detail-title"), lines=None)
        return in_view(page, page.locator(".atlas-detail-intro" if bridge else ".atlas-detail blockquote"))

    def neighborhood(page):
        assert page.locator(".atlas-node-selected").evaluate("el=>el===document.activeElement")
        in_view(page, page.locator(".atlas-node-selected"), lines=None)
        in_view(page, page.locator(".atlas-node-essay").first, lines=None)

    def frozen(page):
        page.wait_for_timeout(120)
        before = state(page)
        page.wait_for_timeout(500)
        assert state(page) == before, (before, state(page))
        assert before["pending"] == 0 and before["storage"] == 0

    def layout(page):
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
        boxes = page.locator(".atlas-node").evaluate_all("""nodes => nodes.map(n => {
          const r=n.getBoundingClientRect();
          return {id:n.dataset.atlasNode,x:r.x,y:r.y,right:r.right,bottom:r.bottom,
            width:r.width,height:r.height,overflow:n.scrollWidth > n.clientWidth + 1};
        })""")
        assert len(boxes) <= 8
        for i, box in enumerate(boxes):
            assert box["width"] >= 44 and box["height"] >= 44 and not box["overflow"], box
            for other in boxes[i + 1:]:
                assert (box["right"] <= other["x"] or other["right"] <= box["x"]
                        or box["bottom"] <= other["y"] or other["bottom"] <= box["y"]), (box, other)
        assert page.locator(".atlas-node").evaluate_all("""nodes => nodes.every(n =>
          getComputedStyle(n.querySelector('.atlas-node-title')).fontSize.replace('px','') >= 19)""")

    def ready(page, first_open_width=None):
        summary = page.locator("[data-atlas-map] > summary")
        summary.tap() if first_open_width and first_open_width < 700 else summary.click()
        page.wait_for_selector('[data-atlas-state="ready"]')
        if first_open_width:
            assert state(page)["reveals"] == 0, "Opening the map must not programmatically scroll it."
            page.evaluate("document.fonts.ready.then(() => true)")
            first = page.locator(".atlas-node").first.bounding_box()
            viewport = page.viewport_size
            assert 0 <= first["y"] and first["y"] + first["height"] <= viewport["height"], (viewport, first)
            page.screenshot(path=str(args.artifacts / f"atlas-{first_open_width}-first-open.png"))
        page.locator(".atlas-graph").scroll_into_view_if_needed()
        page.wait_for_function("document.querySelectorAll('.atlas-lines path').length === 4")

    with sync_playwright() as p:
        browser = getattr(p, args.browser).launch()
        for width in args.widths:
            context = browser.new_context(viewport={"width": width, "height": 700 if width == 320 else (844 if width < 700 else 1000)},
                                          has_touch=width < 700, reduced_motion="reduce")
            context.add_init_script(PROBE)
            page = context.new_page()
            requests = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.goto(args.url + ROUTE, wait_until="networkidle")
            assert not any("atlas-map.js" in url or "search-index.json" in url for url in requests)
            assert page.locator("#theme-1").count() == 1
            ready(page, first_open_width=width)
            layout(page)
            page.locator(".atlas-graph").screenshot(path=str(args.artifacts / f"atlas-{width}-overview.png"))
            frozen(page)
            for qid in ["design", "builders-craft", "work-careers", "industry-markets", "culture-hype"]:
                page.locator(".atlas-overview").click() if page.locator(".atlas-overview").is_enabled() else None
                page.locator(f'[data-atlas-node="{qid}"]').focus()
                page.keyboard.press("Enter")
                assert page.locator(".atlas-node-selected").get_attribute("data-atlas-node") == qid
                neighborhood(page)
                expected_count = page.locator(f'[data-atlas-question="{qid}"] [data-atlas-entry]').count()
                assert page.locator(".atlas-node-essay").count() == expected_count
                assert page.locator(".atlas-detail-intro").text_content().startswith(f"All {expected_count} essays")
                layout(page)
                if qid == "design":
                    page.locator(".atlas-graph").screenshot(path=str(args.artifacts / f"atlas-{width}-neighborhood.png"))
                sources = page.locator(f'[data-atlas-question="{qid}"] [data-atlas-entry]').evaluate_all("""entries =>
                  entries.map(e=>({id:e.dataset.atlasEntry,text:e.querySelector('blockquote').textContent,
                    href:e.querySelector('.atlas-context').getAttribute('href')}))""")
                for index, source in enumerate(sources if width in (320, 1600) else sources[:1]):
                    node = page.locator(f'[data-atlas-node="{source["id"]}"]')
                    node.tap() if width < 700 else node.click()
                    assert page.locator(".atlas-detail blockquote").text_content() == source["text"]
                    assert page.locator(".atlas-detail .atlas-context").get_attribute("href") == source["href"]
                    assert page.evaluate("document.activeElement.id") == "atlas-detail-title"
                    assert page.locator(f'[data-atlas-node="{source["id"]}"]').get_attribute("aria-pressed") == "true"
                    metrics = inspected_detail(page)
                    if qid == "design" and index == 0:
                        page.screenshot(path=str(args.artifacts / f"atlas-{width}-first-essay-viewport.png"))
                        (args.artifacts / f"atlas-{width}-first-essay-viewport.json").write_text(json.dumps(metrics, indent=2))
                if qid == "design":
                    page.locator(".atlas-detail").screenshot(path=str(args.artifacts / f"atlas-{width}-source.png"))
            for bridge in config["bridges"]:
                page.locator(".atlas-overview").click()
                page.locator(f'[data-atlas-node="{bridge["from"]}"]').click()
                page.locator(f'[data-atlas-node="{bridge["to"]}"]').click()
                assert page.locator("#atlas-detail-title").text_content() == bridge["label"]
                assert page.locator(".atlas-detail-intro").text_content() == bridge["reason"]
                inspected_detail(page, bridge=True)
                for quote, source in zip(page.locator(".atlas-source-pair blockquote").all(), bridge["sources"]):
                    original = page.locator(f'[data-atlas-entry="{source["slug"]}"] blockquote')
                    assert quote.text_content() == original.text_content()
                    assert quote.get_attribute("cite").endswith("#" + source["passage"])
                if bridge["id"] == "depth-and-direction":
                    page.screenshot(path=str(args.artifacts / f"atlas-{width}-bridge-viewport.png"))
                    page.locator(".atlas-detail").screenshot(path=str(args.artifacts / f"atlas-{width}-bridge.png"))
                page.locator("[data-atlas-follow]").click()
                assert page.locator(".atlas-node-selected").get_attribute("data-atlas-node") == bridge["to"]
                neighborhood(page)
                if bridge["id"] == "depth-and-direction":
                    page.screenshot(path=str(args.artifacts / f"atlas-{width}-follow-viewport.png"))
            reveals = state(page)["reveals"]
            page.evaluate("window.dispatchEvent(new Event('resize')); window.dispatchEvent(new PageTransitionEvent('pageshow'))")
            page.wait_for_timeout(120)
            assert state(page)["reveals"] == reveals, "Passive lifecycle events must not reveal or refocus a view."
            page.locator(".atlas-graph").scroll_into_view_if_needed()
            page.wait_for_timeout(120)
            frozen(page)
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(120)
            frozen(page)
            page.locator("[data-atlas-map] > summary").click()
            assert not page.locator(".atlas-graph").is_visible()
            frozen(page)
            page.locator("[data-atlas-map] > summary").click()
            page.locator(".atlas-graph").scroll_into_view_if_needed()
            page.wait_for_timeout(120)
            page.evaluate("""Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
              document.dispatchEvent(new Event('visibilitychange'));""")
            frozen(page)
            page.evaluate("delete document.hidden; document.dispatchEvent(new Event('visibilitychange'))")
            page.emulate_media(reduced_motion="no-preference")
            page.wait_for_timeout(120)
            frozen(page)
            page.emulate_media(forced_colors="active")
            page.locator(".atlas-graph").screenshot(path=str(args.artifacts / f"atlas-{width}-forced-media.png"))
            layout(page)
            frozen(page)
            page.emulate_media(forced_colors="none")
            page.locator(".atlas-overview").click()
            page.locator('[data-atlas-node="builders-craft"]').click()
            slug = "qubit-teams-the-future-built-by-two-people-using-ai"
            page.locator(f'[data-atlas-node="{slug}"]').click()
            inspected_detail(page)
            before_navigation = state(page)["reveals"]
            destination = page.locator(".atlas-detail .atlas-context").get_attribute("href")
            page.locator(".atlas-detail .atlas-context").click()
            page.wait_for_url(args.url + destination)
            assert page.locator("#" + destination.split("#")[1] + " .passage-text").count() == 1
            page.go_back(wait_until="networkidle")
            assert page.locator("#by-preoccupation").is_visible()
            assert state(page)["reveals"] in (0, before_navigation), "Back restoration must not explicitly realign a view."
            if not page.locator("[data-atlas-map]").evaluate("el=>el.open"):
                ready(page)
            else:
                page.wait_for_selector('[data-atlas-state="ready"]')
            if page.locator(".atlas-overview").is_enabled():
                page.locator(".atlas-overview").click()
            page.locator('[data-atlas-node="work-careers"]').click()
            page.locator('[data-atlas-node="ai-is-making-you-faster-and-dumber"]').click()
            expected = page.locator('[data-atlas-entry="ai-is-making-you-faster-and-dumber"] blockquote').text_content()
            assert page.locator(".atlas-detail blockquote").text_content() == expected
            page.locator(".atlas-graph").scroll_into_view_if_needed()
            page.wait_for_function("document.querySelectorAll('.atlas-lines path').length === 6")
            frozen(page)
            assert not any("search-index.json" in url for url in requests), "Atlas must never fetch the lexical index."
            assert not [url for url in requests if not url.startswith(args.url)]
            assert state(page)["storage"] == 0
            context.close()
            print(f"PASS: {width}px real question/essay/bridge exploration, exact quotes, keyboard/touch, stable nodes, lifecycle and source return.", flush=True)

        context = browser.new_context(viewport={"width": 1028, "height": 900})
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url + "/futurememo/?q=judgment&theme=Builders+%26+craft#by-preoccupation", wait_until="networkidle")
        ready(page)
        page.locator('[data-atlas-node="design"]').click()
        assert page.locator("#archive-query").input_value() == "judgment"
        assert page.locator("#archive-theme").input_value() == "Builders & craft"
        assert "q=judgment" in page.url
        page.locator("#archive-reset").click()
        assert page.locator("[data-atlas-question]").count() == 5
        assert page.locator(".archive-entry:visible").count() == 20
        context.close()

        for width in (320, 1600):
            context = browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="reduce")
            context.add_init_script(PROBE)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(args.url + ROUTE, wait_until="networkidle")
            source = page.evaluate("""() => {
              const list = document.querySelector('[data-atlas-question="design"] > ol');
              const entry = list.firstElementChild.cloneNode(true);
              entry.dataset.atlasEntry = 'atlas-sixth-essay-fixture';
              entry.querySelector('.atlas-source').id = 'atlas-source-sixth-fixture';
              entry.querySelector('.atlas-essay-title').textContent = 'Test fixture / sixth essay';
              list.append(entry);
              return {text:entry.querySelector('blockquote').textContent,
                href:entry.querySelector('.atlas-context').getAttribute('href')};
            }""")
            ready(page)
            assert "6 essays" in page.locator('[data-atlas-node="design"]').text_content()
            page.locator('[data-atlas-node="design"]').click()
            assert page.locator(".atlas-coverage").is_visible()
            assert page.locator(".atlas-coverage").inner_text() == "5 of 6 essays mapped; all 6 in the index and detail list below."
            assert page.locator(".atlas-node").count() == 8
            assert page.locator(".atlas-node-essay").count() == 5
            assert page.locator('[data-atlas-question="design"] .atlas-context').count() == 6
            assert page.locator(".atlas-detail-essay").count() == 6
            page.locator('[data-atlas-detail-entry="atlas-sixth-essay-fixture"]').click()
            assert page.locator(".atlas-node").count() == 8
            assert page.locator('[data-atlas-node="atlas-sixth-essay-fixture"]').count() == 0
            assert page.locator(".atlas-detail blockquote").text_content() == source["text"]
            assert page.locator(".atlas-detail .atlas-context").get_attribute("href") == source["href"]
            assert "outside the bounded map preview" in page.locator(".atlas-detail-intro").inner_text()
            assert page.locator('.atlas-node[aria-pressed="true"]').count() == 0
            page.locator(".atlas-detail").screenshot(path=str(args.artifacts / f"atlas-{width}-sixth-source.png"))
            page.get_by_role("button", name="Back to this question", exact=True).click()
            assert page.locator(".atlas-detail-essay").count() == 6
            page.locator(".atlas-coverage").scroll_into_view_if_needed()
            page.screenshot(path=str(args.artifacts / f"atlas-{width}-six-member.png"))
            page.locator(".atlas-graph").scroll_into_view_if_needed()
            page.wait_for_function("document.querySelectorAll('.atlas-lines path').length === 7")
            layout(page)
            frozen(page)
            context.close()
        print("PASS: six-member themes retain six source choices while mapping only five essays/eight total nodes.")

        context = browser.new_context()
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        module_responses = []
        page.on("response", lambda response: module_responses.append((response.url, response.status))
                if "atlas-map.js" in response.url else None)
        page.route("**/atlas-map.js*", lambda route: route.fulfill(status=503, body="Unavailable", content_type="text/javascript"))
        page.goto(args.url + ROUTE, wait_until="networkidle")
        page.locator("[data-atlas-map] > summary").click()
        page.wait_for_selector('[data-atlas-state="failed"]')
        assert page.locator("[data-atlas-notice]").inner_text().startswith("The map could not be opened")
        assert page.locator("[data-atlas-entry]").count() == 20
        page.unroute("**/atlas-map.js*")
        page.locator("[data-atlas-retry]").click()
        page.wait_for_selector('[data-atlas-state="ready"]')
        assert [status for _, status in module_responses] == [503, 200], module_responses
        assert module_responses[1][0].endswith("atlas-map.js?attempt=2")
        context.close()

        context = browser.new_context()
        page = context.new_page()
        failed_requests = []
        page.route("**/atlas-map.js*", lambda route: (
            failed_requests.append(route.request.url),
            route.fulfill(status=503, body="Unavailable", content_type="text/javascript")))
        page.goto(args.url + ROUTE, wait_until="networkidle")
        page.locator("[data-atlas-map] > summary").click()
        for attempt in range(3):
            page.wait_for_selector('[data-atlas-state="failed"]')
            if attempt < 2:
                page.locator("[data-atlas-retry]").click()
        assert len(set(failed_requests)) == 3
        assert page.locator("[data-atlas-retry]").is_hidden()
        assert "Reload this page" in page.locator("[data-atlas-notice]").inner_text()
        page.locator("#theme-1 .atlas-source > summary").first.click()
        assert page.locator("#theme-1 blockquote").first.is_visible()
        context.close()

        context = browser.new_context()
        page = context.new_page()
        page.route("**/atlas.js", lambda route: route.abort())
        page.goto(args.url + ROUTE, wait_until="networkidle")
        page.locator("[data-atlas-map] > summary").click()
        assert "needs JavaScript" in page.locator("[data-atlas-notice]").inner_text()
        page.locator("#theme-1 .atlas-source > summary").first.click()
        assert page.locator("#theme-1 blockquote").first.is_visible()
        context.close()

        context = browser.new_context()
        page = context.new_page()
        pending = []
        page.route("**/atlas-map.js", lambda route: pending.append(route))
        page.goto(args.url + ROUTE, wait_until="networkidle")
        page.locator("[data-atlas-map] > summary").click()
        page.wait_for_selector('[data-atlas-state="loading"]')
        page.locator("[data-atlas-map] > summary").click()
        assert not page.locator("[data-atlas-map]").evaluate("el=>el.open")
        assert pending
        pending[0].continue_()
        page.wait_for_selector('[data-atlas-state="ready"]')
        assert not page.locator(".atlas-graph").is_visible()
        context.close()

        for width in (320, 1600):
            context = browser.new_context(java_script_enabled=False, viewport={"width": width, "height": 900})
            page = context.new_page()
            page.goto(args.url + ROUTE, wait_until="networkidle")
            page.evaluate("document.fonts.ready.then(() => true)")
            assert page.locator("[data-atlas-entry]").count() == 20
            assert page.locator("[data-atlas-bridge]").count() == 4
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
            for source in page.locator(".atlas-source").all():
                source.locator("summary").click()
                assert source.locator("blockquote").is_visible()
                assert source.locator(".atlas-context").get_attribute("href").startswith("/futurememo/")
                source.locator("summary").click()
            page.locator(".atlas-bridges > summary").click()
            assert page.locator(".atlas-bridge:visible").count() == 4
            page.locator("#theme-1 .atlas-source > summary").first.click()
            page.locator("#theme-1").screenshot(path=str(args.artifacts / f"atlas-{width}-no-js.png"))
            page.goto(args.url + "/futurememo/#theme-2")
            assert page.locator("#theme-2").is_visible()
            context.close()
        browser.close()
    assert not errors, errors
    print("PASS: no-JS full index, native anchors, search independence, lazy/error/retry/late-close behavior. Forced-media checks do not establish native OS palette contrast.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8772")
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--widths", type=int, nargs="+", default=[320, 390, 1028, 1600])
    parser.add_argument("--browser", choices=["webkit", "chromium"], default="webkit")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--static-only", action="store_true")
    mode.add_argument("--browser-only", action="store_true")
    args = parser.parse_args()
    if not args.browser_only:
        static_checks()
    if not args.static_only:
        if args.artifacts is None:
            parser.error("--artifacts is required for browser checks")
        browser_checks(args)
