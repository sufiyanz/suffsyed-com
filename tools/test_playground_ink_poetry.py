"""WebKit interaction checks for the v1 ink/poetry modules.

Runs an artifact-only mount harness on an OS-assigned loopback port. Pass the
host's --data-url to exercise its exact published passage payload.
"""
import argparse
import gzip
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import urlopen
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PALETTE = {
    "forest": "#1B2915", "green": "#305831", "stone": "#D7CDB8",
    "paper": "#EFEDE6", "white": "#FFFFFF", "ink": "#191919",
}

HARNESS = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ink and poetry contract checks</title>
<link rel="stylesheet" href="/site/journal.css">
<link rel="stylesheet" href="/__shared-playground__.css">
<link rel="stylesheet" href="/site/playground/ink-studio.css">
<link rel="stylesheet" href="/site/playground/blackout-poetry.css">
<style>
body { margin: 0; padding: 12px; }
#frame { position: static; display: block; padding: 0; width: calc(100% - 16px); max-width: 1100px; overflow: visible; }
#experience { position: relative; inset: auto; height: 520px; }
#status, #errors { font: 12px/1.3 var(--font-technical); margin-top: 8px; }
</style></head><body><button id="close">Close experiment</button>
<div id="frame" class="pg-shell"><div id="experience" class="pg-instance"></div></div>
<p id="status" role="status"></p><p id="errors" role="alert"></p>
<script type="module">
import { mount as ink } from '/site/playground/ink-studio.js';
import { mount as poetry } from '/site/playground/blackout-poetry.js';
window.fixture = __DATA__;
window.palette = __PALETTE__;
window.events = []; window.statuses = []; window.failures = [];
window.scheduled = 0; window.urlsCreated = 0; window.urlsRevoked = 0;
const raf = window.requestAnimationFrame, timeout = window.setTimeout, interval = window.setInterval;
window.requestAnimationFrame = (...args) => { window.scheduled++; return raf(...args); };
window.setTimeout = (...args) => { window.scheduled++; return timeout(...args); };
window.setInterval = (...args) => { window.scheduled++; return interval(...args); };
const create = URL.createObjectURL, revoke = URL.revokeObjectURL;
URL.createObjectURL = (...args) => { window.urlsCreated++; return create(...args); };
URL.revokeObjectURL = (...args) => { window.urlsRevoked++; return revoke(...args); };
for (const name of ['pointerdown', 'gotpointercapture', 'lostpointercapture']) {
  document.addEventListener(name, event => {
    window.events.push({name, id:event.pointerId, target:event.target.className});
  }, true);
}
const root = document.getElementById('experience');
window.root = root;
window.size = (height = 520, dpr = 2) => {
  root.style.height = height + 'px';
  const box = root.getBoundingClientRect();
  window.controller?.resize({width:box.width, height:box.height, dpr});
};
window.openExperience = async (id, passages = window.fixture.passages, activate = true, preAbort = false) => {
  window.abort?.abort(); await window.controller?.destroy();
  window.abort = new AbortController();
  if (preAbort) window.abort.abort();
  root.dataset.experience = id;
  document.getElementById('errors').textContent = '';
  window.statuses = []; window.failures = [];
  window.controller = await (id === 'ink-studio' ? ink : poetry)(root, {
    signal:window.abort.signal, seed:12345, random:() => 0,
    preferences:{reducedMotion:true, forcedColors:false}, palette:window.palette,
    data:{...window.fixture, passages},
    setStatus:message => {
      window.statuses.push(message);
      document.getElementById('status').textContent = message;
    },
    reportError:(message,error) => {
      window.failures.push({message, error:String(error)});
      document.getElementById('errors').textContent = message;
    },
  });
  window.size(innerWidth <= 320 ? 320 : innerWidth < 600 ? 310 : 560, 2);
  if (activate) window.controller.setActive(true);
};
document.getElementById('close').onclick = () => window.abort.abort();
window.ready = true;
</script></body></html>"""

INK_STATS = """canvas => {
  const context = canvas.getContext('2d');
  const data = context.getImageData(0,0,canvas.width,canvas.height).data;
  let count = 0, sumX = 0, sumY = 0;
  for (let y=0; y<canvas.height; y++) for (let x=0; x<canvas.width; x++) {
    if (data[(y*canvas.width+x)*4+3] > 30) { count++; sumX+=x; sumY+=y; }
  }
  return {count, x:count ? sumX/count/canvas.width:0, y:count ? sumY/count/canvas.height:0,
    width:canvas.width, height:canvas.height};
}"""


def fixture():
    """Use complete existing paragraphs, never synthetic prose, when host is absent."""
    from bs4 import BeautifulSoup

    corpus = json.loads((ROOT / "content/corpus.json").read_text())
    rows = corpus if isinstance(corpus, list) else corpus["essays"]
    passages = []
    for row in rows[:3]:
        soup = BeautifulSoup((ROOT / "content/essays" / (row["slug"] + ".html")).read_text(), "html.parser")
        paragraph = next(p for p in soup.find_all("p", id=True) if len(p.get_text().split()) >= 25)
        passages.append({
            "id": paragraph["id"], "text": paragraph.get_text(), "title": row["title"],
            "href": f"/futurememo/{row['slug']}/#{paragraph['id']}",
        })
    return {"passages": passages, "photos": [], "signature": {"src": "/site/suff-syed-signature.svg", "viewBox": [0, 0, 350, 148]}}


def open_experience(page, name, passages=None, activate=True, pre_abort=False):
    page.evaluate("args => window.openExperience(...args)", [name, passages if passages is not None else page.evaluate("fixture.passages"), activate, pre_abort])
    page.evaluate("document.fonts.ready")


def stats(page):
    return page.locator(".ink-paper").evaluate(INK_STATS)


def line(page, start=(.16, .35), end=(.8, .55), steps=30):
    box = page.locator(".ink-paper").bounding_box()
    page.mouse.move(box["x"] + box["width"] * start[0], box["y"] + box["height"] * start[1])
    page.mouse.down()
    assert page.evaluate("""() => {
      const id = events.filter(e=>e.name==='pointerdown').at(-1).id;
      return document.querySelector('.ink-paper').hasPointerCapture(id);
    }""")
    page.mouse.move(box["x"] + box["width"] * end[0], box["y"] + box["height"] * end[1], steps=steps)
    page.mouse.up()
    assert page.evaluate("events.filter(e => e.name === 'lostpointercapture').length > 0")


def assert_layout(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "page overflow"
    assert page.locator("#experience").evaluate("el => el.scrollWidth <= el.clientWidth + 1"), "root overflow"
    small = page.locator("#experience").evaluate("""el => [...el.querySelectorAll('button,select')].map(node => {
      const r=node.getBoundingClientRect(); return {text:node.textContent, width:r.width, height:r.height};
    }).filter(r=>r.width<43.9 || r.height<43.9)""")
    assert not small, small
    assert page.locator("#experience").evaluate("""el=>[...el.querySelectorAll('button')].every(
      button=>button.scrollWidth<=button.clientWidth+1)"""), "clipped button label"
    assert page.locator("#close").is_visible()


def ink_checks(page, artifacts, width):
    open_experience(page, "ink-studio", activate=False)
    assert page.locator("#experience").evaluate("el => el.inert")
    assert stats(page)["count"] == 0
    page.evaluate("controller.setActive(true)")
    assert_layout(page)
    root_box = page.locator("#experience").bounding_box()
    if width < 600:
        assert root_box["width"] == width - 40
        assert root_box["height"] == (320 if width == 320 else 310)
        assert page.locator(".ink-paper").bounding_box()["height"] >= 76
        assert page.locator("#experience").evaluate("el=>el.scrollHeight<=el.clientHeight+1")
    canvas = page.locator(".ink-paper")
    page.get_by_label("Size", exact=True).select_option("10")
    page.get_by_label("Nib", exact=True).select_option("round")
    line(page)
    drawn = stats(page)
    assert drawn["count"] > 250
    assert drawn["width"] * drawn["height"] <= 1000000
    assert canvas.evaluate("el => el.width / el.getBoundingClientRect().width <= 2.01")
    assert not page.evaluate("failures")
    page.get_by_role("button", name="Undo", exact=True).click()
    assert stats(page)["count"] == 0
    assert page.get_by_role("button", name="Clear", exact=True).is_disabled()

    # Pen pressure is supplied through PointerEvents; pixel widths prove pressure use.
    box = canvas.bounding_box()
    page.mouse.move(box["x"] + 12, box["y"] + box["height"] * .4)
    page.mouse.down()
    page.evaluate("""() => {
      const canvas = root.querySelector('canvas'), rect = canvas.getBoundingClientRect();
      const id = events.filter(e=>e.name==='pointerdown').at(-1).id;
      for (let i=1; i<=80; i++) canvas.dispatchEvent(new PointerEvent('pointermove', {
        pointerId:id, pointerType:'pen', isPrimary:true, buttons:1,
        pressure:i<40 ? .12 : .95,
        clientX:rect.left+12+(rect.width-24)*i/80, clientY:rect.top+rect.height*.4,
      }));
      canvas.dispatchEvent(new PointerEvent('pointerup', {
        pointerId:id, pointerType:'pen', pressure:.95,
        clientX:rect.right-12, clientY:rect.top+rect.height*.4,
      }));
    }""")
    page.mouse.up()
    pressure = canvas.evaluate("""canvas => {
      const data=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
      return [.25,.72].map(pos => {
        const x=Math.round(canvas.width*pos); let n=0;
        for(let y=0;y<canvas.height;y++) if(data[(y*canvas.width+x)*4+3]>30)n++;
        return n;
      });
    }""")
    assert pressure[1] > pressure[0] * 1.6, pressure
    before_erase = stats(page)["count"]
    page.get_by_role("button", name="Eraser", exact=True).click()
    line(page, (.5, .25), (.5, .55))
    assert stats(page)["count"] < before_erase
    page.get_by_role("button", name="Undo", exact=True).click()
    assert stats(page)["count"] == before_erase
    page.get_by_role("button", name="Eraser", exact=True).click()

    before_resize = stats(page)
    page.evaluate("size(620, 3)")
    after_resize = stats(page)
    assert after_resize["count"] > 0
    assert abs(before_resize["x"] - after_resize["x"]) < .015
    assert abs(before_resize["y"] - after_resize["y"]) < .015
    assert after_resize["width"] * after_resize["height"] <= 1000000
    page.evaluate("size(innerWidth <= 320 ? 320 : innerWidth < 600 ? 310 : 560, 2)")
    with page.expect_download() as saved:
        page.get_by_role("button", name="Save PNG", exact=True).click()
    saved.value.save_as(artifacts / f"ink-export-{width}.png")
    assert (artifacts / f"ink-export-{width}.png").read_bytes().startswith(b"\x89PNG")
    assert page.evaluate("urlsCreated === urlsRevoked && urlsCreated > 0")

    page.get_by_role("button", name="Clear", exact=True).click()
    assert stats(page)["count"] == 0
    if width < 600:
        canvas.tap()
        assert stats(page)["count"] > 0
        page.get_by_role("button", name="Undo", exact=True).click()
        assert stats(page)["count"] == 0
    canvas.focus()
    page.keyboard.press("Enter")
    for _ in range(12):
        page.keyboard.press("Shift+ArrowRight")
    page.keyboard.press("Space")
    keyboard_ink = stats(page)["count"]
    assert keyboard_ink > 0
    for _ in range(4):
        page.keyboard.press("ArrowDown")
    assert stats(page)["count"] == keyboard_ink, "pen should be up"
    page.get_by_label("Nib", exact=True).select_option("fountain")
    page.get_by_label("Ink", exact=True).select_option("green")
    line(page, (.12, .7), (.85, .25), 60)
    line(page, (.25, .25), (.45, .8), 35)
    page.mouse.move(0, 0)
    page.screenshot(path=str(artifacts / f"ink-art-{width}.png"))
    page.evaluate("controller.setPreferences({reducedMotion:true, forcedColors:true})")
    assert stats(page)["count"] > 0
    assert page.locator("#experience").get_attribute("data-ink-forced") == "true"
    page.evaluate("controller.setPreferences({reducedMotion:false, forcedColors:false})")
    assert page.evaluate("scheduled === 0"), "idle loops or timers"

    box = canvas.bounding_box()
    page.mouse.move(box["x"] + 40, box["y"] + 40)
    page.mouse.down()
    page.evaluate("controller.setActive(false)")
    assert page.evaluate("""() => !root.querySelector('canvas').hasPointerCapture(
      events.filter(e=>e.name==='pointerdown').at(-1).id)""")
    inactive_ink = stats(page)["count"]
    page.mouse.move(box["x"] + 80, box["y"] + 80)
    page.mouse.up()
    assert stats(page)["count"] == inactive_ink
    page.evaluate("controller.setActive(false); controller.setActive(true)")
    page.locator("#close").click()
    assert page.locator("#experience").evaluate("el => el.childElementCount === 0")
    page.evaluate("controller.destroy(); controller.resize({width:400,height:400,dpr:2}); controller.setActive(true)")
    open_experience(page, "ink-studio")
    assert stats(page)["count"] == 0
    open_experience(page, "ink-studio", pre_abort=True)
    assert page.locator("#experience").evaluate("el => !el.childElementCount")
    return {"width": width, "pressure_pixels": pressure, "drawn_pixels": drawn["count"]}


def poetry_checks(page, artifacts, width):
    open_experience(page, "blackout-poetry", activate=False)
    assert page.locator("#experience").evaluate("el => el.inert")
    page.evaluate("controller.setActive(true)")
    original = page.evaluate("fixture.passages[0]")
    assert page.locator(".poetry-passage").text_content() == original["text"]
    assert page.locator(".poetry-poem").text_content() == original["text"]
    assert page.locator(".poetry-source-link").text_content() == original["title"]
    assert page.locator(".poetry-source-link").evaluate("el => new URL(el.href).hash") != ""
    page.locator(".poetry-source summary").click()
    assert page.locator(".poetry-source-link").is_visible()
    page.locator(".poetry-source summary").click()
    assert_layout(page)
    words = page.locator(".poetry-word")
    total = words.count()
    assert total == len(original["text"].split())
    if width < 600:
        words.first.tap()
        assert words.first.get_attribute("aria-pressed") == "false"
        words.first.tap()
        assert words.first.get_attribute("aria-pressed") == "true"
    first = words.first.text_content()
    words.first.focus()
    page.keyboard.press("Space")
    assert words.first.get_attribute("aria-pressed") == "false"
    assert not page.locator(".poetry-poem").text_content().startswith(first + " ")
    page.keyboard.press("ArrowRight")
    assert words.nth(1).evaluate("el => el === document.activeElement")
    page.keyboard.press("Enter")
    assert words.nth(1).get_attribute("aria-pressed") == "false"
    page.keyboard.press("End")
    assert words.last.evaluate("el => el === document.activeElement")
    page.keyboard.press("Home")
    assert words.first.evaluate("el => el === document.activeElement")
    page.get_by_role("button", name="Reset", exact=True).click()
    assert page.locator(".poetry-poem").text_content() == original["text"]
    page.get_by_role("button", name="Clear", exact=True).click()
    assert page.locator(".poetry-empty").is_visible()
    assert page.locator(".poetry-poem").text_content() == ""
    assert page.get_by_role("button", name="Copy poem", exact=True).is_disabled()
    for index in range(min(total, 9)):
        words.nth(index).click()
    expected = page.evaluate("""() => {
      let n=0; return fixture.passages[0].text.match(/\\s+|\\S+/gu)
        .filter(t => /^\\s+$/u.test(t) ? n>0 && n<9 : n++<9).join('');
    }""")
    assert page.locator(".poetry-poem").text_content() == expected

    page.get_by_label("Poetry brush", exact=True).select_option("remove")
    page.locator(".poetry-reading").evaluate("el => el.scrollTop=0")
    first_box = words.first.bounding_box()
    third_box = words.nth(2).bounding_box()
    page.mouse.move(first_box["x"] + 10, first_box["y"] + 18)
    page.mouse.down()
    assert page.evaluate("""() => root.querySelector('.poetry-passage').hasPointerCapture(
      events.filter(e=>e.name==='pointerdown').at(-1).id)""")
    page.mouse.move(third_box["x"] + 10, third_box["y"] + 18, steps=12)
    page.mouse.up()
    assert words.first.get_attribute("aria-pressed") == "false"
    assert words.nth(2).get_attribute("aria-pressed") == "false"
    page.get_by_label("Poetry brush", exact=True).select_option("restore")
    words.first.click()
    assert words.first.get_attribute("aria-pressed") == "true"
    page.get_by_label("Poetry brush", exact=True).select_option("tap")
    assert page.locator(".poetry-passage").evaluate("el=>getComputedStyle(el).touchAction") == "auto"
    assert page.locator(".poetry-word").first.evaluate("el=>getComputedStyle(el).textDecorationLine") == "underline"
    page.locator(".poetry-reading").evaluate("el => el.scrollTop=0")
    page.screenshot(path=str(artifacts / f"poetry-selection-{width}.png"))
    page.locator(".poetry-remix").scroll_into_view_if_needed()
    page.screenshot(path=str(artifacts / f"poetry-remix-{width}.png"))
    assert page.locator("#experience").evaluate("el => el.scrollHeight <= el.clientHeight + 1")
    assert not page.evaluate("failures")
    page.evaluate("Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText:async text=>window.copied=text}})")
    page.get_by_role("button", name="Copy poem", exact=True).click()
    assert page.evaluate("copied.startsWith('Visitor remix (not an original quotation)') && copied.includes(fixture.passages[0].title)")
    page.evaluate("() => { navigator.clipboard.writeText=async()=>{throw new Error('denied for test')}; }")
    page.get_by_role("button", name="Copy poem", exact=True).click()
    assert page.locator(".poetry-error").is_visible()
    assert page.evaluate("failures.length") == 1
    page.get_by_role("button", name="New passage", exact=True).click()
    assert page.locator(".poetry-passage").text_content() == page.evaluate("fixture.passages[1].text")
    page.get_by_role("button", name="Reset", exact=True).click()
    assert page.locator(".poetry-poem").text_content() == page.locator(".poetry-passage").text_content()
    page.evaluate("controller.setPreferences({reducedMotion:true, forcedColors:true})")
    assert page.locator("#experience").get_attribute("data-poetry-forced") == "true"
    page.evaluate("controller.setActive(false); controller.resize({width:300,height:420,dpr:2}); controller.setActive(true)")
    assert page.evaluate("scheduled === 0")
    page.locator("#close").click()
    assert page.locator("#experience").evaluate("el => !el.childElementCount")
    page.evaluate("controller.destroy(); controller.destroy()")
    open_experience(page, "blackout-poetry")
    assert page.locator(".poetry-poem").text_content() == original["text"]
    open_experience(page, "blackout-poetry", pre_abort=True)
    assert page.locator("#experience").evaluate("el => !el.childElementCount")
    return {"width": width, "source_words": total, "exact_source": True, "touch_tap": width < 600}


def edge_checks(page):
    source = page.evaluate("fixture.passages[0]")
    # Exact separators/punctuation and markup-like tokens remain inert text.
    unusual = {**source, "text": " \t" + source["text"] + "\n\t"}
    open_experience(page, "blackout-poetry", [unusual])
    assert page.locator(".poetry-passage").text_content() == unusual["text"]
    assert page.locator(".poetry-poem").text_content() == unusual["text"]
    markup = {**source, "text": source["text"] + ' <img src="missing" onerror="alert(1)">'}
    open_experience(page, "blackout-poetry", [markup])
    assert page.locator(".poetry-passage").text_content() == markup["text"]
    assert page.locator("#experience img").count() == 0
    long_word = {**source, "text": source["text"].replace(" ", "")}
    open_experience(page, "blackout-poetry", [long_word])
    assert_layout(page)
    assert page.locator(".poetry-passage").text_content() == long_word["text"]
    long_paragraph = {**source, "text": (source["text"] + " ") * 12}
    open_experience(page, "blackout-poetry", [long_paragraph])
    assert_layout(page)
    assert page.locator(".poetry-reading").evaluate("el=>el.scrollHeight > el.clientHeight")
    assert page.locator("#experience").evaluate("el=>el.scrollHeight <= el.clientHeight + 1")
    assert page.locator(".poetry-passage").text_content() == long_paragraph["text"]
    for broken in [[], [{**source, "href": "javascript:alert(1)"}], [{**source, "text": "x" * 60001}]]:
        open_experience(page, "blackout-poetry", broken)
        assert page.locator(".poetry-error").is_visible()
        assert page.locator("#close").is_visible()
        assert page.evaluate("failures.length") == 1
        page.locator("#close").click()
        assert page.locator("#experience").evaluate("el=>!el.childElementCount")


def ink_edge_checks(page):
    open_experience(page, "ink-studio")
    page.get_by_label("Size", exact=True).select_option("10")
    page.get_by_label("Nib", exact=True).select_option("round")
    canvas = page.locator(".ink-paper")
    box = canvas.bounding_box()
    page.mouse.move(box["x"] + 12, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.evaluate("""() => {
      const c=root.querySelector('canvas'), r=c.getBoundingClientRect();
      const id=events.filter(e=>e.name==='pointerdown').at(-1).id;
      let time=performance.now();
      for(let i=1; i<=80; i++) {
        time+=i<40 ? 90 : 1;
        const event=new PointerEvent('pointermove', {pointerId:id, pointerType:'mouse', buttons:1,
          clientX:r.left+12+(r.width-24)*i/80, clientY:r.top+r.height/2, pressure:.5});
        Object.defineProperty(event,'timeStamp',{value:time});
        c.dispatchEvent(event);
      }
      c.dispatchEvent(new PointerEvent('pointercancel', {pointerId:id}));
      window.cancelledCapture=!c.hasPointerCapture(id);
    }""")
    page.mouse.up()
    widths = canvas.evaluate("""canvas => {
      const data=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
      return [.25,.72].map(pos => {
        const x=Math.round(canvas.width*pos); let n=0;
        for(let y=0;y<canvas.height;y++) if(data[(y*canvas.width+x)*4+3]>30)n++;
        return n;
      });
    }""")
    assert widths[0] > widths[1] * 1.3, widths
    assert page.evaluate("cancelledCapture")
    page.get_by_role("button", name="Clear", exact=True).click()
    # Keep at most 900 points in a stroke, report the cap, and release capture.
    box = canvas.bounding_box()
    page.mouse.move(box["x"] + 20, box["y"] + 20)
    page.mouse.down()
    page.evaluate("""() => {
      const c=root.querySelector('canvas'), r=c.getBoundingClientRect();
      const id=events.filter(e=>e.name==='pointerdown').at(-1).id;
      for(let i=0; i<940; i++) c.dispatchEvent(new PointerEvent('pointermove', {
        pointerId:id, pointerType:'pen', buttons:1, pressure:.4,
        clientX:r.left+20+(i%2)*20, clientY:r.top+25+(i%3)*5,
      }));
      window.limitReleased=!c.hasPointerCapture(id);
    }""")
    page.mouse.up()
    assert page.locator(".ink-notice").is_visible()
    assert "900 points" in page.locator(".ink-notice").text_content()
    assert page.locator(".ink-budget").text_content().startswith("1/96 strokes · 900/")
    assert page.evaluate("limitReleased")
    before_budget_resize = stats(page)
    page.evaluate("size(720, 2)")
    after_budget_resize = stats(page)
    assert abs(before_budget_resize["x"] - after_budget_resize["x"]) < .02
    assert abs(before_budget_resize["y"] - after_budget_resize["y"]) < .02
    # 96 independent taps reach the separate stroke cap without dropping old art.
    page.get_by_role("button", name="Clear", exact=True).click()
    canvas.focus()
    page.evaluate("""() => {
      const c=root.querySelector('canvas');
      for(let i=0; i<194; i++) c.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', bubbles:true}));
    }""")
    assert page.locator(".ink-budget").text_content().startswith("96/96 strokes · 96/")
    assert "sheet is full" in page.locator(".ink-notice").text_content()
    preserved = stats(page)["count"]
    assert preserved > 0
    page.get_by_role("button", name="Undo", exact=True).click()
    assert page.locator(".ink-budget").text_content().startswith("95/96")
    # Native page keys remain untouched outside the surface.
    assert page.locator("#close").evaluate("""el => {
      const e=new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true});
      el.dispatchEvent(e); return !e.defaultPrevented;
    }""")
    assert page.locator(".ink-stage").evaluate("el=>getComputedStyle(el).touchAction") == "auto"
    assert page.locator(".ink-paper").evaluate("el=>getComputedStyle(el).touchAction") == "none"
    page.get_by_role("button", name="Clear", exact=True).click()
    for _ in range(14):
        box = canvas.bounding_box()
        page.mouse.move(box["x"] + 20, box["y"] + 20)
        page.mouse.down()
        page.evaluate("""() => {
          const c=root.querySelector('canvas'), r=c.getBoundingClientRect();
          const id=events.filter(e=>e.name==='pointerdown').at(-1).id;
          for(let i=0; i<905; i++) c.dispatchEvent(new PointerEvent('pointermove', {
            pointerId:id, pointerType:'pen', buttons:1, pressure:.4,
            clientX:r.left+20+(i%2)*20, clientY:r.top+25+(i%3)*5,
          }));
        }""")
        page.mouse.up()
    assert page.locator(".ink-budget").text_content().startswith("14/96 strokes · 12,000/")
    assert "12,000 points" in page.locator(".ink-notice").text_content()
    assert stats(page)["count"] > 0
    page.locator("#close").click()
    # DOM references retained by callers must not retain the visitor's remix.
    open_experience(page, "blackout-poetry")
    page.evaluate("window.removedPoem=root.querySelector('.poetry-poem'); window.removedWords=root.querySelector('.poetry-passage')")
    page.locator("#close").click()
    assert page.evaluate("removedPoem.textContent === '' && removedWords.childElementCount === 0")
    return {"velocity_pixels": widths, "stroke_point_cap": 900, "stroke_count_cap": 96, "total_point_cap": 12000}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--data-url")
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    if args.data_url:
        with urlopen(args.data_url, timeout=10) as response:
            data = json.load(response)
        with urlopen(urljoin(args.data_url, "playground.css"), timeout=10) as response:
            shared_css = response.read()
    else:
        data = fixture()
        shared = ROOT / "site/playground.css"
        shared_css = shared.read_bytes() if shared.exists() else b""
    harness = args.artifacts / "ink-poetry-harness.html"
    harness.write_text(HARNESS.replace("__DATA__", json.dumps(data).replace("<", "\\u003c")).replace("__PALETTE__", json.dumps(PALETTE)))
    (args.artifacts / "ink-poetry-host.css").write_bytes(shared_css)

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path in ["/__ink-poetry-harness__.html", "/__shared-playground__.css"]:
                body = shared_css if self.path.endswith(".css") else harness.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/css" if self.path.endswith(".css") else "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                super().do_GET()

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results, errors, external = [], [], []
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.webkit.launch(timeout=20000)
            for width, height in [(320, 740), (390, 844), (1280, 900)]:
                print(f"Ink/poetry: {width}px", flush=True)
                context = browser.new_context(viewport={"width": width, "height": height},
                                              device_scale_factor=2, reduced_motion="reduce",
                                              has_touch=width < 600, accept_downloads=True)
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda request: external.append(request.url) if not request.url.startswith(base) else None)
                page.goto(base + "/__ink-poetry-harness__.html")
                page.wait_for_function("window.ready")
                results.append({"ink": ink_checks(page, args.artifacts, width),
                                "poetry": poetry_checks(page, args.artifacts, width)})
                if width == 320:
                    edge_checks(page)
                    results[-1]["ink_edges"] = ink_edge_checks(page)
                context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    assert not errors, errors
    assert not external, external
    costs = {}
    for name in ["ink-studio", "blackout-poetry"]:
        costs[name] = sum(len(gzip.compress((ROOT / f"site/playground/{name}.{extension}").read_bytes(), mtime=0))
                          for extension in ["js", "css"])
        assert costs[name] < 60 * 1024
    summary = {"results": results, "gzip_bytes": costs, "page_errors": errors, "external_requests": external,
               "forced_colors_scope": "Runtime preference styles checked; WebKit is not a native Windows high-contrast palette test."}
    (args.artifacts / "ink-poetry-results.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
