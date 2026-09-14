"""Contract-v1 host tests. Route-only fixtures are not registered or shipped experiences."""
import argparse
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDS = ["scratch-terminal", "ink-studio", "pocket-darkroom", "type-garden", "blackout-poetry",
       "agent-terrarium", "assumption-lab", "sound-loom", "generative-postcard", "signal-noise"]

FIXTURE = """
export async function mount(root, context) {
  const item = {id:root.dataset.experience, seed:context.seed, calls:[], destroyed:0, aborted:false};
  (window.pgFixtures ||= []).push(item);
  if (!Object.isFrozen(context.data) || !Object.isFrozen(context.data.photos[0]))
    throw new Error('Context material must be immutable');
  if (!context.data.passages[0].href.includes('#')) throw new Error('Original anchor required');
  context.signal.addEventListener('abort', () => {item.aborted=true;}, {once:true});
  if (window.pgFixtureMode === 'late') await new Promise(resolve => {window.finishPgMount=resolve;});
  if (window.pgFixtureMode === 'throw') throw new Error('Intentional fixture mount failure');
  const input = document.createElement('input'); input.setAttribute('aria-label','Test input');
  const action = document.createElement('button'); action.textContent='Test action';
  action.addEventListener('click', () => context.setStatus('A real fixture action.'));
  const failure = document.createElement('button'); failure.textContent='Recoverable error';
  failure.addEventListener('click', () => context.reportError('Keep this work and correct the input.', new Error('Test input')));
  root.append(input,action,failure);
  return {
    setActive(value) { item.calls.push(['active',value]); },
    resize(value) { item.calls.push(['resize',value]); },
    setPreferences(value) { item.calls.push(['preferences',value]); },
    destroy() { item.destroyed++; }
  };
}
"""


def static_checks(require_all=False):
    from bs4 import BeautifulSoup
    from corpus import flat_text
    data = json.loads((ROOT / "docs/assets/playground-data.json").read_text())
    assert len(data["photos"]) == 22 and len(data["passages"]) == 20
    from PIL import Image
    for photo in data["photos"]:
        with Image.open(ROOT / "docs" / photo["src"].lstrip("/")) as image:
            assert [image.width, image.height] == [photo["width"], photo["height"]]
            assert image.width <= 960
    for passage in data["passages"]:
        route, anchor = passage["href"].split("#")
        page = BeautifulSoup((ROOT / "docs" / route.lstrip("/") / "index.html").read_text(), "html.parser")
        original = page.find(id=anchor).select_one(".passage-text")
        assert flat_text(original) == passage["text"], passage["href"]
    assert data["signature"] == {"src": "/assets/suff-syed-signature.svg", "viewBox": [0, 0, 350, 148]}
    budget = sum(len(gzip.compress((ROOT / path).read_bytes())) for path in ["site/playground.js", "site/playground.css"])
    assert budget <= 12 * 1024, budget
    print(f"PASS: exact original materials/anchors/dimensions; initial host gzip {budget} bytes.")
    if require_all:
        folder = ROOT / "site/playground"
        for identifier in IDS:
            pending = [folder / f"{identifier}.js", folder / f"{identifier}.css"]
            files = set()
            while pending:
                path = pending.pop()
                if path in files:
                    continue
                assert path.is_file(), path
                files.add(path)
                assert path.read_bytes() == (ROOT / "docs/assets/playground" / path.name).read_bytes()
                for dependency in re.findall(r"""["']\./([\w.-]+\.(?:js|css))["']""", path.read_text()):
                    pending.append(folder / dependency)
            total = sum(len(gzip.compress(path.read_bytes())) for path in files)
            assert total <= 60 * 1024, (identifier, total)
            print(f"PASS: {identifier} and local dependencies {total} bytes gzip.")


def browser_checks(args):
    from playwright.sync_api import sync_playwright
    args.artifacts.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = getattr(p, args.browser).launch()
        for width, height in [(320, 740), (390, 844), (1028, 900), (1600, 1000)]:
            print(f"Host contract: {width}px", flush=True)
            context = browser.new_context(viewport={"width": width, "height": height}, has_touch=width < 900)
            context.route("**/assets/playground/*.js", lambda route: route.fulfill(body=FIXTURE, content_type="text/javascript"))
            context.route("**/assets/playground/*.css", lambda route: route.fulfill(body="/* Test-only fixture */", content_type="text/css"))
            page = context.new_page()
            errors, requests = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.goto(args.url, wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            entry = page.get_by_role("button", name="Open cover experiments", exact=True)
            entry.wait_for(state="visible")
            assert not any("/assets/playground/" in url or "playground-data.json" in url for url in requests)
            assert page.get_by_role("heading", name="Suff Syed", exact=True).count() == 1
            geometry = page.locator(".home-cover").bounding_box()
            before_top = page.locator("#main").bounding_box()["y"]
            page.get_by_role("button", name="Pause signature animation").click()
            entry.focus()
            page.keyboard.press("Enter")
            page.wait_for_selector('.pg-shell[data-state="ready"]')
            assert page.locator(".home-cover").bounding_box() == geometry
            assert page.locator("#main").bounding_box()["y"] == before_top
            assert page.locator(".cover-identity").evaluate("el => el.inert")
            assert not page.locator("#main").evaluate("el => el.inert")
            assert page.evaluate("document.activeElement.id") == "pg-title"
            assert page.get_by_role("button", name="Choose experiment").count() == 0
            choose = page.get_by_role("combobox", name="Choose experiment")
            assert choose.bounding_box()["height"] >= 44
            assert choose.locator("option").count() == 10
            assert page.evaluate("pgFixtures[0].calls[0][0] === 'active' && pgFixtures[0].calls[0][1] === false")
            assert page.evaluate("pgFixtures[0].calls.some(([kind,value]) => kind==='active' && value)")
            assert page.locator(".home-cover").get_attribute("data-signature-state") == "paused"
            for label in ["Close experiment", "Another experiment"]:
                box = page.get_by_role("button", name=label).bounding_box()
                assert box["width"] >= 44 and box["height"] >= 44
            page.get_by_role("button", name="Test action").click()
            assert page.locator(".pg-status").inner_text() == "A real fixture action."
            assert page.locator(".pg-footer").evaluate("el => el.scrollWidth <= el.clientWidth")
            stage_size = page.locator(".pg-viewport").bounding_box()
            page.get_by_role("button", name="Recoverable error").click()
            assert page.locator(".pg-shell").get_attribute("data-state") == "ready"
            assert page.locator(".pg-status").inner_text() == "Keep this work and correct the input."
            assert page.locator(".pg-instance").count() == 1
            assert page.locator(".pg-viewport").bounding_box() == stage_size
            page.screenshot(path=str(args.artifacts / f"{width}-host-fixture.png"))
            page.evaluate("scrollTo(0, document.querySelector('.home-cover').offsetHeight + 5)")
            page.wait_for_function("pgFixtures[0].calls.filter(([k])=>k==='active').at(-1)[1] === false")
            assert page.locator(".mast").is_visible()
            page.evaluate("scrollTo(0,0)")
            page.wait_for_function("pgFixtures[0].calls.filter(([k])=>k==='active').at(-1)[1] === true")
            page.emulate_media(reduced_motion="reduce", forced_colors="active")
            page.wait_for_function("pgFixtures[0].calls.filter(([k])=>k==='preferences').at(-1)[1].forcedColors")
            page.emulate_media(reduced_motion="no-preference", forced_colors="none")
            original = page.evaluate("pgFixtures.length")
            visited = ["scratch-terminal"]
            for _ in range(9):
                page.get_by_role("button", name="Another experiment").click()
                page.wait_for_function("n => pgFixtures.length > n", arg=original)
                page.wait_for_selector('.pg-shell[data-state="ready"]')
                original += 1
                visited.append(choose.input_value())
            assert set(visited) == set(IDS), visited
            assert page.evaluate("pgFixtures.slice(0,-1).every(item => item.destroyed===1 && item.aborted)")
            page.get_by_role("textbox", name="Test input").focus()
            page.get_by_role("textbox", name="Test input").dispatch_event("keydown", {"key": "Escape", "isComposing": True})
            assert page.locator(".pg-shell").is_visible()
            page.keyboard.press("Escape")
            assert not page.locator(".pg-shell").is_visible()
            assert entry.evaluate("el => el === document.activeElement")
            assert page.get_by_role("button", name="Resume signature animation").is_visible()
            assert page.evaluate("pgFixtures.every(item => item.destroyed===1 && item.aborted)")
            assert page.locator(".home-cover").bounding_box() == geometry
            assert not errors, errors
            assert not [url for url in requests if not url.startswith(args.url)], requests
            context.close()

        context = browser.new_context(viewport={"width": 390, "height": 844})
        context.route("**/assets/playground/*.js", lambda route: route.fulfill(body=FIXTURE, content_type="text/javascript"))
        context.route("**/assets/playground/*.css", lambda route: route.fulfill(body="/* Test-only fixture */", content_type="text/css"))
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle")
        page.evaluate("window.pgFixtureMode='late'")
        entry = page.get_by_role("button", name="Open cover experiments")
        entry.click()
        page.wait_for_function("typeof finishPgMount === 'function'")
        page.get_by_role("button", name="Close experiment").click()
        page.evaluate("window.pgFixtureMode=''; finishPgMount()")
        page.wait_for_function("pgFixtures[0].destroyed === 1")
        assert page.evaluate("pgFixtures[0].aborted")
        assert not page.locator(".pg-instance").count()
        page.evaluate("window.pgFixtureMode='throw'")
        entry.click()
        page.wait_for_selector('.pg-shell[data-state="error"]')
        assert page.get_by_role("button", name="Retry", exact=True).is_visible()
        page.evaluate("window.pgFixtureMode=''")
        page.get_by_role("button", name="Retry", exact=True).click()
        page.wait_for_selector('.pg-shell[data-state="ready"]')
        page.get_by_role("button", name="Close experiment").click()
        assert entry.evaluate("el => el === document.activeElement")
        context.close()
        context = browser.new_context(viewport={"width": 390, "height": 844})
        attempts = []
        def import_route(route):
            attempts.append(route.request.url)
            if len(attempts) == 1:
                route.fulfill(status=503, body="Temporarily unavailable", content_type="text/plain")
            else:
                route.fulfill(body=FIXTURE, content_type="text/javascript")
        context.route("**/assets/playground/*.js*", import_route)
        context.route("**/assets/playground/*.css", lambda route: route.fulfill(body="/* Test-only fixture */", content_type="text/css"))
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle")
        page.get_by_role("button", name="Open cover experiments").click()
        page.wait_for_selector('.pg-shell[data-state="error"]')
        page.get_by_role("button", name="Retry", exact=True).click()
        page.wait_for_selector('.pg-shell[data-state="ready"]')
        assert len(attempts) == 2 and "retry=1" in attempts[-1], attempts
        page.get_by_role("button", name="Close experiment").click()
        context.close()
        context = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle")
        assert not page.locator(".signature-entry").is_visible()
        assert page.get_by_role("heading", name="Suff Syed", exact=True).count() == 1
        assert page.locator(".mast").is_visible()
        context.close()
        browser.close()
    print("PASS: cover-only footprint, all registry routes, entry/focus/close, cancellation/late disposal and no-JS.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--browser", default="webkit", choices=["webkit", "chromium"])
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument("--browser-only", action="store_true")
    parser.add_argument("--require-all", action="store_true")
    args = parser.parse_args()
    if not args.browser_only:
        static_checks(args.require_all)
    if not args.static_only:
        browser_checks(args)
