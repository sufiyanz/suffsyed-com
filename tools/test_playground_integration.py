"""Real cover-host actions; module algorithm/resource matrices live in the owned suites."""
import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

IDS = ["scratch-terminal", "assumption-lab", "pocket-darkroom", "generative-postcard",
       "ink-studio", "blackout-poetry", "type-garden", "sound-loom", "agent-terrarium", "signal-noise"]

AUDIO_PROBE = """(() => {
  window.pgAudio = []; window.pgOscillators = 0;
  const Native = window.AudioContext || window.webkitAudioContext;
  if (!Native) return;
  const Probe = new Proxy(Native, {construct(Target,args) {
    const audio = Reflect.construct(Target,args);
    pgAudio.push(audio);
    const oscillator = audio.createOscillator.bind(audio);
    audio.createOscillator = (...options) => { pgOscillators++; return oscillator(...options); };
    return audio;
  }});
  window.AudioContext = Probe;
  if (window.webkitAudioContext) window.webkitAudioContext = Probe;
})();"""


def pixels(root):
    return root.locator("canvas").first.evaluate("el => el.toDataURL()")

def choose_view(root, name):
    control = root.get_by_role("button", name=name, exact=True)
    if control.count() and control.is_visible():
        control.click()


def scratch(root, page, artifacts):
    root.get_by_role("button", name="Run", exact=True).click()
    page.wait_for_function("document.querySelector('.pg-status').textContent.includes('50')")
    before = pixels(root)
    choose_view(root, "Code")
    root.get_by_role("textbox", name="Drawing instructions").fill("circle nope")
    root.get_by_role("button", name="Run", exact=True).click()
    root.locator(".code-error:not([hidden])").wait_for()
    assert page.locator(".pg-shell").get_attribute("data-state") == "ready"
    assert pixels(root) == before
    root.get_by_role("button", name="Reset", exact=True).click()
    choose_view(root, "Code")
    root.get_by_role("combobox", name="Drawing example").select_option("1")
    root.get_by_role("button", name="Run", exact=True).click()
    page.wait_for_function("document.querySelector('.pg-status').textContent.includes('131')")
    assert pixels(root) != before
    return "Worker Run, syntax error preserves editor/art, Reset, second example"


def model(root, page, artifacts):
    choose_view(root, "Adjust")
    before = root.locator(".code-model-pocket").inner_text()
    root.get_by_role("combobox", name="Assumption example").select_option("3")
    assert root.locator(".code-model-pocket").inner_text() != before
    slider = root.get_by_role("slider", name="Human supervision")
    slider.focus()
    page.keyboard.press("Home")
    assert slider.input_value() == "0"
    root.get_by_role("button", name="Reset", exact=True).click()
    assert root.locator(".code-model-pocket").inner_text() == before
    choose_view(root, "Readout")
    return "Preset changes visible model, native keyboard slider, exact reset"


def png_download(root, page, artifacts, label="Download PNG"):
    with page.expect_download() as event:
        root.get_by_role("button", name=label, exact=True).click()
    download = event.value
    path = artifacts / download.suggested_filename
    download.save_as(path)
    assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def darkroom(root, page, artifacts):
    develop = root.locator("summary").filter(has_text="Develop print")
    opened = False
    if develop.count() and develop.is_visible() and not develop.evaluate("el=>el.parentElement.open"):
        develop.click()
        opened = True
        page.evaluate("new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))")
    before = pixels(root)
    slider = root.get_by_role("slider", name="Exposure", exact=False)
    slider.focus()
    page.keyboard.press("End")
    page.wait_for_function("before => document.querySelector('[data-experience=pocket-darkroom] canvas').toDataURL() !== before", arg=before)
    root.get_by_role("button", name="Show original", exact=True).click()
    page.wait_for_function("before => document.querySelector('[data-experience=pocket-darkroom] canvas').toDataURL() === before", arg=before)
    root.get_by_role("button", name="Show edited print", exact=True).click()
    png_download(root, page, artifacts)
    root.get_by_role("button", name="Reset to original", exact=True).click()
    page.wait_for_function("before => document.querySelector('[data-experience=pocket-darkroom] canvas').toDataURL() === before", arg=before)
    if opened:
        develop.click()
    return "Exposure changes pixels, original/edited comparison, real PNG, exact reset"


def postcard(root, page, artifacts):
    before = pixels(root)
    root.get_by_role("button", name="New variation", exact=True).click()
    page.wait_for_function("before => document.querySelector('[data-experience=generative-postcard] canvas').toDataURL() !== before", arg=before)
    assert root.locator("a[href*='#']").count() >= 1
    choose_view(root, "Edit postcard")
    png_download(root, page, artifacts)
    choose_view(root, "Edit postcard")
    return "New variation changes composition, original passage attribution, real PNG"


def ink(root, page, artifacts):
    canvas = root.locator(".ink-paper")
    def has_ink():
        return canvas.evaluate("""el => {
          const data = el.getContext('2d').getImageData(0,0,el.width,el.height).data;
          return data.some((value,index) => index % 4 === 3 && value > 0);
        }""")
    assert not has_ink()
    canvas.focus()
    page.keyboard.press("Space")
    for _ in range(7):
        page.keyboard.press("Shift+ArrowRight")
    page.keyboard.press("Space")
    assert has_ink()
    root.get_by_role("button", name="Undo", exact=True).click()
    assert not has_ink()
    box = canvas.bounding_box()
    page.mouse.move(box["x"] + box["width"] * .3, box["y"] + box["height"] * .35)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * .7, box["y"] + box["height"] * .65, steps=15)
    page.mouse.up()
    assert has_ink()
    png_download(root, page, artifacts, "Save PNG")
    choose_view(root, "Tools")
    root.get_by_role("button", name="Clear", exact=True).click()
    assert not has_ink()
    choose_view(root, "Done")
    return "Keyboard and pointer ink, exact Undo/Clear restoration, real PNG"


def poetry(root, page, artifacts):
    before = root.locator(".poetry-poem").inner_text()
    assert before == root.locator(".poetry-passage").inner_text()
    first = root.locator(".poetry-word").first
    first.click()
    assert first.get_attribute("aria-pressed") == "false"
    assert root.locator(".poetry-poem").inner_text() != before
    first.focus()
    page.keyboard.press("Space")
    assert root.locator(".poetry-poem").inner_text() == before
    choose_view(root, "Tools")
    root.get_by_role("button", name="Clear", exact=True).click()
    assert root.locator(".poetry-poem").inner_text() == ""
    root.get_by_role("button", name="Reset", exact=True).click()
    assert root.locator(".poetry-poem").inner_text() == before
    choose_view(root, "Done")
    root.get_by_role("button", name="New passage", exact=True).click()
    assert root.locator(".poetry-poem").inner_text() != before
    source = urlsplit(root.locator(".poetry-source-link").get_attribute("href"))
    assert source.path.startswith("/futurememo/") and source.fragment
    return "Exact source text, pointer/keyboard word toggles, Clear/Reset/new original passage"


def terrarium(root, page, artifacts):
    before = root.locator(".sim-steps").inner_text()
    root.get_by_role("button", name="Step", exact=True).click()
    assert root.locator(".sim-steps").inner_text() != before
    root.get_by_role("button", name="Resume", exact=True).click()
    page.wait_for_function("Number(document.querySelector('[data-experience=agent-terrarium] .sim-steps').textContent.match(/\\d+/)[0]) > 2")
    root.get_by_role("button", name="Pause", exact=True).click()
    paused = pixels(root)
    page.wait_for_timeout(180)
    assert pixels(root) == paused
    root.get_by_role("button", name="Reset", exact=True).click()
    assert root.locator(".sim-steps").inner_text() == before
    root.get_by_role("button", name="# Wall", exact=True).click()
    canvas = root.locator("canvas")
    canvas.focus()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    before_wall = pixels(root)
    page.keyboard.press("Space")
    assert pixels(root) != before_wall
    return "Real Step/run progression, stable Pause, seeded Reset, keyboard wall placement"


def signal_game(root, page, artifacts):
    root.get_by_role("checkbox", name="Turn-based", exact=True).check()
    root.get_by_role("button", name="Start 60 s", exact=True).click()
    before = root.locator(".sim-time").inner_text()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowDown")
    assert root.locator(".sim-time").inner_text() != before
    root.get_by_role("button", name="Pause", exact=True).click()
    paused = pixels(root)
    page.wait_for_timeout(180)
    assert pixels(root) == paused
    root.get_by_role("button", name="Restart", exact=True).click()
    assert root.get_by_role("button", name="Start 60 s", exact=True).is_visible()
    return "Turn-based start, real keyboard moves consume clock, stable Pause and Restart"


def garden(root, page, artifacts):
    before = pixels(root)
    canvas = root.locator("canvas")
    canvas.focus()
    page.keyboard.press("ArrowRight")
    page.keyboard.down("Space")
    page.wait_for_timeout(350)
    assert pixels(root) != before
    page.keyboard.up("Space")
    root.get_by_role("button", name="Pause garden motion", exact=True).click()
    paused = pixels(root)
    page.wait_for_timeout(180)
    assert pixels(root) == paused
    root.get_by_role("button", name="Resume garden motion", exact=True).click()
    root.get_by_role("button", name="Re-form", exact=True).click()
    page.emulate_media(reduced_motion="reduce")
    root.get_by_role("button", name="Step", exact=True).wait_for(state="visible")
    root.get_by_role("button", name="Step", exact=True).click()
    page.emulate_media(reduced_motion="no-preference")
    return "Keyboard force changes glyph positions, Pause freezes pixels, Re-form, reduced-motion Step"


def loom(root, page, artifacts):
    assert page.evaluate("pgAudio.length") == 0
    cell = root.get_by_role("button", name="A4, step 1", exact=True)
    before = cell.get_attribute("aria-pressed")
    cell.click()
    assert cell.get_attribute("aria-pressed") != before
    root.get_by_role("button", name="Reset", exact=True).click()
    root.get_by_role("button", name="Play loom", exact=True).click()
    page.wait_for_function("pgOscillators > 0")
    assert page.evaluate("pgAudio.length") == 1
    root.get_by_role("button", name="Stop loom", exact=True).click()
    page.wait_for_function("pgAudio.every(audio => audio.state === 'closed')")
    root.get_by_role("button", name="Clear", exact=True).click()
    assert root.locator("button[aria-pressed=true]").count() == 0
    root.get_by_role("button", name="Reset", exact=True).click()
    assert root.locator("button[aria-pressed=true]").count() == 9
    return "Real note toggle, user-gesture native audio/oscillators, Stop closes context, Clear/Reset"


ACTIONS = {"scratch-terminal": scratch, "assumption-lab": model,
           "pocket-darkroom": darkroom, "generative-postcard": postcard,
           "ink-studio": ink, "blackout-poetry": poetry,
           "agent-terrarium": terrarium, "signal-noise": signal_game,
           "type-garden": garden, "sound-loom": loom}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--ids", nargs="+", choices=IDS, default=IDS)
    parser.add_argument("--widths", nargs="+", type=int, default=[390, 1600])
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--late-palette", action="store_true",
                        help="Delay the real journal stylesheet response by two seconds.")
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    report = []
    with sync_playwright() as p:
        browser = p.webkit.launch()
        for width in args.widths:
            context = browser.new_context(viewport={"width": width, "height": 844 if width < 900 else 1000},
                                          has_touch=width < 900, accept_downloads=True)
            context.add_init_script(AUDIO_PROBE)
            if args.late_palette:
                def delay_stylesheet(route):
                    response = route.fetch()
                    time.sleep(2)
                    route.fulfill(response=response)
                context.route("**/assets/journal.css", delay_stylesheet)
            page = context.new_page()
            errors, requests = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.goto(args.url, wait_until="networkidle")
            assert not [url for url in requests if "/assets/playground/" in url or "playground-data.json" in url]
            cover = page.locator(".home-cover").bounding_box()
            page.get_by_role("button", name="Open cover experiments").click()
            for identifier in args.ids:
                print(f"Live {identifier}: {width}px", flush=True)
                page.get_by_role("combobox", name="Choose experiment").select_option(identifier)
                page.wait_for_function("['ready','error'].includes(document.querySelector('.pg-shell').dataset.state)")
                assert page.locator(".pg-shell").get_attribute("data-state") == "ready", page.locator(".pg-feedback").inner_text()
                page.evaluate("new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                root = page.locator(f'[data-experience="{identifier}"]')
                assert identifier in ACTIONS, f"No real action test yet for {identifier}"
                action = ACTIONS[identifier](root, page, args.artifacts)
                if identifier != "type-garden":
                    page.wait_for_selector(f'[data-world-signature="{identifier}"][data-scene-status="ready"]')
                    page.wait_for_timeout(650)
                page.screenshot(path=str(args.artifacts / f"{width}-{identifier}.png"))
                assert page.locator(".home-cover").bounding_box()["height"] == cover["height"]
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                report.append({"id": identifier, "width": width, "actions": action})
            page.get_by_role("button", name="Close experiment").click()
            assert page.get_by_role("button", name="Open cover experiments").evaluate("el => el === document.activeElement")
            assert not page.locator(".pg-instance").count()
            assert not errors, errors
            assert not [url for url in requests if not url.startswith((args.url, f"blob:{args.url}/"))], requests
            context.close()
        browser.close()
    (args.artifacts / "integration.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {len(report)} actual module/viewport action checks in the real cover host.")


if __name__ == "__main__":
    main()
