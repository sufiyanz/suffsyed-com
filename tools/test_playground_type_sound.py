"""Exercise the v2 Type garden / Sound loom worlds through the preserved v1 mount contract.

Pass --harness /absolute/path/to/the/session-artifact-contract-fixture.html.
The fixture loads /assets/playground/<id>.js and exposes window.harness containing
root, controller, context, abort, errors. It must support ?id=<id>&inactive.
No generated site files or committed application shell are needed.
"""
import argparse
import gzip
import json
import math
import mimetypes
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROBE = r"""(() => {
  const probe = window.probe = {
    frames: 0, positions: [], times: [], reads: 0, rafts: new Set(), timers: new Set(),
    peakRaf: 0, peakTimers: 0, contexts: [], notes: [], nodes: new Set(), peakNodes: 0,
    gesture: false, resumes: [], connections: new Set(), gains: [], pulses: [],
    sceneFrames: 0, sceneTimes: [],
  };
  document.addEventListener('click', () => {
    probe.gesture = true;
  }, true);
  document.addEventListener('click', () => { probe.gesture = false; });
  const clear = CanvasRenderingContext2D.prototype.clearRect;
  const text = CanvasRenderingContext2D.prototype.fillText;
  const read = CanvasRenderingContext2D.prototype.getImageData;
  CanvasRenderingContext2D.prototype.clearRect = function(...args) {
    if (this.canvas.classList.contains('type-canvas')) {
      probe.frames++; probe.positions = []; probe.times.push(performance.now());
    }
    if (this.canvas.closest('[data-world-signature="sound-loom"]')) {
      probe.sceneFrames++; probe.sceneTimes.push(performance.now());
    }
    return clear.apply(this, args);
  };
  CanvasRenderingContext2D.prototype.fillText = function(glyph, x, y, ...args) {
    if (this.canvas.classList.contains('type-canvas')) {
      probe.positions.push({ glyph, x, y }); probe.glyphFont = this.font; probe.glyphColor = this.fillStyle;
    }
    return text.call(this, glyph, x, y, ...args);
  };
  CanvasRenderingContext2D.prototype.getImageData = function(...args) {
    probe.reads++;
    return read.apply(this, args);
  };
  const request = requestAnimationFrame, cancel = cancelAnimationFrame;
  window.requestAnimationFrame = fn => {
    if (fn.name !== 'gardenFrame') return request(fn);
    const id = request(time => { probe.rafts.delete(id); fn(time); });
    probe.rafts.add(id); probe.peakRaf = Math.max(probe.peakRaf, probe.rafts.size);
    return id;
  };
  window.cancelAnimationFrame = id => { probe.rafts.delete(id); return cancel(id); };
  const schedule = setTimeout, cancelTimer = clearTimeout;
  window.setTimeout = (fn, delay, ...args) => {
    if (fn.name !== 'loomTick') return schedule(fn, delay, ...args);
    const id = schedule(() => { probe.timers.delete(id); fn(...args); }, delay);
    probe.timers.add(id); probe.peakTimers = Math.max(probe.peakTimers, probe.timers.size);
    return id;
  };
  window.clearTimeout = id => { probe.timers.delete(id); return cancelTimer(id); };
  const NativeAudio = window.AudioContext || window.webkitAudioContext;
  if (NativeAudio) {
    function ObservedAudio(...args) {
      const audio = new NativeAudio(...args);
      const entry = { audio, gesture: probe.gesture, analyser: null };
      probe.contexts.push(entry);
      const resume = audio.resume.bind(audio);
      audio.resume = () => { probe.resumes.push(probe.gesture); return resume(); };
      const makeGain = audio.createGain.bind(audio);
      audio.createGain = () => {
        const gain = makeGain();
        probe.gains.push(gain);
        const connect = gain.connect.bind(gain), disconnect = gain.disconnect.bind(gain);
        gain.connect = target => {
          probe.connections.add(gain);
          if (target === audio.destination) {
            entry.analyser = audio.createAnalyser();
            connect(entry.analyser);
          }
          return connect(target);
        };
        gain.disconnect = (...values) => { probe.connections.delete(gain); return disconnect(...values); };
        return gain;
      };
      const makeOscillator = audio.createOscillator.bind(audio);
      audio.createOscillator = () => {
        const osc = makeOscillator();
        probe.nodes.add(osc); probe.peakNodes = Math.max(probe.peakNodes, probe.nodes.size);
        osc.addEventListener('ended', () => probe.nodes.delete(osc));
        const start = osc.start.bind(osc), disconnect = osc.disconnect.bind(osc);
        const setFrequency = osc.frequency.setValueAtTime.bind(osc.frequency);
        let frequency = 0;
        osc.frequency.setValueAtTime = (value, time) => { frequency = value; return setFrequency(value, time); };
        osc.start = time => {
          probe.notes.push({ frequency, time, type: osc.type, context: probe.contexts.length - 1 });
          return start(time);
        };
        osc.disconnect = (...values) => { probe.nodes.delete(osc); return disconnect(...values); };
        return osc;
      };
      return audio;
    }
    ObservedAudio.prototype = NativeAudio.prototype;
    Object.setPrototypeOf(ObservedAudio, NativeAudio);
    window.AudioContext = ObservedAudio;
  }
})();"""


class FixtureServer(BaseHTTPRequestHandler):
    def __init__(self, *args, harness, shared_css, **kwargs):
        self.harness = harness
        self.shared_css = shared_css
        super().__init__(*args, **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            target = self.harness
        elif path == "/fixture-shared.css":
            if not self.shared_css:
                self.send_response(200)
                self.send_header("Content-Type", "text/css")
                self.end_headers()
                return
            target = self.shared_css
        elif path.startswith("/assets/"):
            target = (ROOT / "site" / path.removeprefix("/assets/")).resolve()
            if ROOT / "site" not in target.parents:
                self.send_error(403)
                return
        else:
            self.send_error(404)
            return
        if not target.is_file():
            self.send_error(404)
            return
        payload = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def state(page, value):
    page.wait_for_function("value => window.harness?.root.dataset.state === value", arg=value)


def snapshot(page):
    return page.evaluate("""() => ({
      frames: probe.frames, positions: probe.positions, times: probe.times, reads: probe.reads,
      raf: probe.rafts.size, timers: probe.timers.size, nodes: probe.nodes.size,
      peakRaf: probe.peakRaf, peakTimers: probe.peakTimers, peakNodes: probe.peakNodes,
      notes: probe.notes, audioStates: probe.contexts.map(c => c.audio.state),
      gestures: probe.contexts.map(c => c.gesture), resumes: probe.resumes,
      connections: probe.connections.size, state: harness.root.dataset.state,
      pulses: probe.pulses, glyphFont: probe.glyphFont, glyphColor: probe.glyphColor,
    })""")


def displacement(before, after):
    assert len(before) == len(after)
    return max(math.hypot(a["x"] - b["x"], a["y"] - b["y"]) for a, b in zip(before, after))


def frozen(page, audio=False):
    first = snapshot(page)
    page.wait_for_timeout(250)
    second = snapshot(page)
    assert first["frames"] == second["frames"], "Inactive or resting canvas repainted."
    assert first["positions"] == second["positions"], "Inactive or resting particles moved."
    assert second["raf"] == second["timers"] == 0, "Idle work is still scheduled."
    assert first["pulses"] == second["pulses"], "Idle scene pulse was requested."
    if audio:
        assert not second["nodes"] and not second["connections"]
        page.wait_for_function("probe.contexts.every(c => c.audio.state === 'closed')", timeout=5000)
        second = snapshot(page)
        assert all(value == "closed" for value in second["audioStates"]), second
        assert first["notes"] == second["notes"], "Stopped loom scheduled new notes."


def capture(page, folder, name):
    page.locator("#fixture").screenshot(path=str(folder / f"{name}.png"))


def layout(page, kind):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Document overflowed."
    assert page.locator("#fixture").evaluate("el => el.getBoundingClientRect().height") == 400
    controls = page.locator(f'[data-experience="{kind}"] button:visible, [data-experience="{kind}"] select:visible')
    for control in controls.all():
        box = control.bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44, box
    if kind == "sound-loom":
        scroll = page.locator(".loom-scroll")
        assert scroll.evaluate("el => el.scrollHeight <= el.clientHeight + 2"), scroll.evaluate(
            "el => [el.scrollHeight, el.clientHeight]")


def world_checks(page, kind):
    result = page.evaluate("""kind => {
      const root = document.querySelector(`[data-experience="${kind}"]`);
      const style = getComputedStyle(root);
      const rgb = value => {
        if (value.startsWith('#')) return value.slice(1).match(/../g).map(x => parseInt(x, 16) / 255);
        return value.match(/[\\d.]+/g).slice(0,3).map(x => Number(x) / 255);
      };
      const luminance = value => rgb(value).map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4)
        .reduce((sum, x, i) => sum + x * [.2126, .7152, .0722][i], 0);
      const contrast = (a,b) => {
        const x = luminance(a), y = luminance(b);
        return (Math.max(x,y) + .05) / (Math.min(x,y) + .05);
      };
      const tokens = Object.fromEntries(['bg','surface','ink','muted','accent','line','signature'].map(name =>
        [name, style.getPropertyValue('--pg-world-' + name).trim()]));
      const colors = {
        ink: contrast(tokens.ink, tokens.bg), muted: contrast(tokens.muted, tokens.bg),
        signature: contrast(tokens.signature, tokens.bg),
        action: kind === 'sound-loom' ? contrast(tokens.surface, tokens.accent) : contrast(tokens.bg, tokens.ink),
        buttonBorder: contrast(kind === 'sound-loom' ? tokens.muted : tokens.ink, tokens.surface),
      };
      const box = element => {
        const r = element.getBoundingClientRect();
        return {x:r.x, y:r.y, width:r.width, height:r.height,
          scrollWidth:element.scrollWidth, scrollHeight:element.scrollHeight,
          clientWidth:element.clientWidth, clientHeight:element.clientHeight};
      };
      const stage = root.querySelector('.type-stage, .loom-scroll');
      const allowed = new Set(['color-scheme', '--pg-world-bg', '--pg-world-surface',
        '--pg-world-ink', '--pg-world-muted', '--pg-world-accent', '--pg-world-line',
        '--pg-world-signature', '--pg-world-signature-opacity']);
      const violations = [];
      const walk = rules => {
        for (const rule of rules) {
          if (rule.cssRules) walk(rule.cssRules);
          else if (rule.selectorText?.includes('#cover-playground')) {
            for (const property of rule.style) if (!allowed.has(property)) violations.push(property);
          } else if (rule.selectorText && !rule.selectorText.startsWith(`[data-experience="${kind}"]`)) {
            violations.push(rule.selectorText);
          }
        }
      };
      for (const sheet of document.styleSheets) {
        if (sheet.href?.includes('/playground/' + kind + '.css')) walk(sheet.cssRules);
      }
      return {tokens, contrast:colors, root:box(root), stage:box(stage), violations,
        signatureMarkers:root.querySelectorAll('[data-world-signature]').length};
    }""", kind)
    assert not result["violations"], result["violations"]
    assert result["contrast"]["ink"] >= 4.5
    assert result["contrast"]["muted"] >= 4.5
    assert result["contrast"]["action"] >= 4.5
    assert result["contrast"]["buttonBorder"] >= 3
    if kind == "type-garden":
        assert result["contrast"]["signature"] >= 4.5
        assert result["signatureMarkers"] == 1
        assert page.locator('canvas[data-world-signature="type-garden"]').get_attribute("aria-hidden") != "true"
    return result


def preferences(page, reduced=False, forced=False):
    page.evaluate("""value => {
      harness.context.preferences = value;
      harness.controller.setPreferences(value);
    }""", {"reducedMotion": reduced, "forcedColors": forced})


def inactive(page):
    page.evaluate("harness.controller.setActive(false)")


def active(page):
    page.evaluate("harness.controller.setActive(true)")


def hidden(page, value):
    page.evaluate("""hidden => {
      if (hidden) Object.defineProperty(document, 'hidden', {configurable:true, get: () => true});
      else delete document.hidden;
      document.dispatchEvent(new Event('visibilitychange'));
    }""", value)


def run_garden(page, url, folder, width):
    page.goto(f"{url}/?id=type-garden&inactive", wait_until="load")
    state(page, "inactive")
    initial = snapshot(page)
    assert 100 <= len(initial["positions"]) <= (250 if width < 500 else 500), len(initial["positions"])
    frozen(page)
    active(page)
    state(page, "resting")
    frozen(page)
    layout(page, "type-garden")
    capture(page, folder, f"type-garden-{width}-resting")
    assert "900" in initial["glyphFont"] and "Impact" in initial["glyphFont"], initial["glyphFont"]
    assert initial["glyphColor"] == "#252912", initial["glyphColor"]
    home = snapshot(page)["positions"]
    field = page.locator(".type-canvas")
    box = field.bounding_box()
    assert field.evaluate("el => el.width * el.height <= 1000000")
    assert field.evaluate("el => el.width / el.clientWidth <= 2.01")
    aim = home[len(home) // 2]
    page.mouse.move(box["x"] + aim["x"], box["y"] + aim["y"])
    page.mouse.down()
    page.wait_for_timeout(550)
    moving = snapshot(page)
    moved = displacement(home, moving["positions"])
    assert moved > 6, moved
    assert moving["reads"] == initial["reads"], "Interaction re-sampled the signature."
    assert [p["glyph"] for p in home] == [p["glyph"] for p in moving["positions"]]
    assert moving["peakRaf"] == moving["raf"] == 1
    frame_times = moving["times"][-8:]
    assert min(b - a for a, b in zip(frame_times, frame_times[1:])) >= 32
    capture(page, folder, f"type-garden-{width}-attract")
    page.mouse.up()
    state(page, "resting")
    assert displacement(home, snapshot(page)["positions"]) < .001
    frozen(page)
    for mode in ["repel", "flow"]:
        page.get_by_label("Garden force").select_option(mode)
        field.focus()
        page.keyboard.press("ArrowRight")
        page.keyboard.down("Space")
        page.wait_for_timeout(350)
        assert displacement(home, snapshot(page)["positions"]) > 3
        page.keyboard.up("Space")
        page.get_by_role("button", name="Re-form", exact=True).click()
        state(page, "resting")
        assert displacement(home, snapshot(page)["positions"]) < .001
    field.focus()
    page.keyboard.down("Space")
    page.wait_for_timeout(250)
    page.keyboard.up("Space")
    page.get_by_role("button", name="Pause garden motion").click()
    state(page, "paused")
    frozen(page)
    inactive(page)
    active(page)
    state(page, "paused")
    frozen(page)
    preferences(page, reduced=True)
    state(page, "paused")
    page.get_by_role("button", name="Resume garden motion").click()
    state(page, "manual")
    field.focus()
    page.keyboard.press("ArrowLeft")
    home_manual = snapshot(page)["positions"]
    page.get_by_role("button", name="Step", exact=True).click()
    assert displacement(home_manual, snapshot(page)["positions"]) > 2
    frozen(page)
    page.get_by_role("button", name="Re-form", exact=True).click()
    assert displacement(home_manual, snapshot(page)["positions"]) < .001
    capture(page, folder, f"type-garden-{width}-reduced")
    preferences(page, forced=True)
    state(page, "resting")
    frozen(page)
    capture(page, folder, f"type-garden-{width}-forced-controller")
    preferences(page)
    before_resize = snapshot(page)
    page.set_viewport_size({"width": width + 37 if width < 1000 else width - 137, "height": 740})
    page.wait_for_timeout(100)
    after_resize = snapshot(page)
    assert after_resize["reads"] == before_resize["reads"] + 1, (before_resize["reads"], after_resize["reads"])
    assert after_resize["positions"] != before_resize["positions"]
    assert len(after_resize["positions"]) <= 500
    frozen(page)
    page.evaluate("""() => {
      const r = harness.root.getBoundingClientRect();
      harness.controller.resize({width:r.width, height:r.height, dpr:devicePixelRatio});
    }""")
    assert snapshot(page)["reads"] == after_resize["reads"], "Same resolution re-sampled mask."
    field.focus()
    page.keyboard.down("Space")
    page.wait_for_timeout(180)
    hidden(page, True)
    frozen(page)
    inactive(page)
    hidden(page, False)
    page.keyboard.up("Space")
    frozen(page)
    active(page)
    state(page, "resting")
    box = field.bounding_box()
    page.mouse.move(box["x"] + 120, box["y"] + 70)
    page.mouse.down()
    assert field.evaluate("el => el.hasPointerCapture(1)"), "Pointer was not captured."
    inactive(page)
    assert not field.evaluate("el => el.hasPointerCapture(1)"), "Inactive tool retained capture."
    page.mouse.up()
    frozen(page)
    active(page)
    state(page, "resting")
    field.focus()
    page.keyboard.down("Space")
    page.wait_for_timeout(180)
    page.evaluate("harness.abort.abort(); harness.controller.destroy(); harness.controller.destroy()")
    page.keyboard.up("Space")
    frozen(page)
    assert page.locator(".type-canvas").count() == 0
    assert not page.evaluate("harness.errors")
    return {"width": width, "particles": len(home), "attract_displacement_px": round(moved, 2),
            "peak_raf": moving["peakRaf"], "idle_raf": 0, "mask_reads_initial": initial["reads"]}


def rms(page):
    return page.evaluate("""() => {
      const analyser = probe.contexts.at(-1)?.analyser;
      if (!analyser) return 0;
      const samples = new Float32Array(analyser.fftSize);
      analyser.getFloatTimeDomainData(samples);
      return Math.sqrt(samples.reduce((sum, x) => sum + x*x, 0) / samples.length);
    }""")


def run_loom(page, url, folder, width):
    page.set_viewport_size({"width": width, "height": 740})
    page.goto(f"{url}/?id=sound-loom&inactive", wait_until="load")
    state(page, "inactive")
    page.evaluate("""() => {
      harness.context.pulseSignature = () => probe.pulses.push({
        state: harness.root.dataset.state, step: document.querySelector('.loom-beat').textContent,
        time: performance.now(),
      });
    }""")
    assert not snapshot(page)["audioStates"], "AudioContext was created on mount."
    active(page)
    state(page, "ready")
    frozen(page)
    assert not snapshot(page)["audioStates"], "AudioContext was created on activation."
    layout(page, "sound-loom")
    assert page.locator(".loom-note[aria-pressed=true]").count() == 9
    capture(page, folder, f"sound-loom-{width}-ready")
    page.get_by_role("button", name="Clear", exact=True).click()
    assert page.locator(".loom-note[aria-pressed=true]").count() == 0
    page.get_by_role("button", name="Play loom").click()
    assert not snapshot(page)["audioStates"], "Empty pattern started audio."
    first = page.get_by_role("button", name="A4, step 1", exact=True)
    first.focus()
    page.keyboard.press("ArrowRight")
    assert page.get_by_role("button", name="A4, step 2", exact=True).evaluate("el => el === document.activeElement")
    page.keyboard.press("Space")
    assert page.get_by_role("button", name="A4, step 2", exact=True).get_attribute("aria-pressed") == "true"
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Space")
    assert page.get_by_role("button", name="G4, step 2", exact=True).get_attribute("aria-pressed") == "true"
    page.keyboard.press("End")
    assert page.get_by_role("button", name="G4, step 8", exact=True).evaluate("el => el === document.activeElement")
    assert page.locator(".loom-note[tabindex='0']").count() == 1
    page.get_by_role("button", name="Reset", exact=True).click()
    before_resize = page.locator(".loom-note[aria-pressed=true]").count()
    page.set_viewport_size({"width": width + 37, "height": 740})
    page.wait_for_timeout(70)
    page.evaluate("harness.controller.resize({width:300,height:400,dpr:2})")
    assert page.locator(".loom-note[aria-pressed=true]").count() == before_resize
    page.set_viewport_size({"width": width, "height": 740})
    page.get_by_role("button", name="Play loom").click()
    state(page, "playing")
    peak_rms = 0
    for _ in range(24):
        page.wait_for_timeout(100)
        peak_rms = max(peak_rms, rms(page))
    sound = snapshot(page)
    assert sound["gestures"] == [True] and sound["resumes"] == [True], sound
    assert sound["audioStates"] == ["running"]
    assert 9 <= len(sound["notes"]) <= 16, sound["notes"]
    assert 0 < peak_rms < .2, f"No real audio samples or excessive gain: {peak_rms}"
    assert sound["timers"] == sound["peakTimers"] == 1
    assert sound["peakNodes"] <= 6
    assert len(sound["pulses"]) >= 7
    assert all(pulse["state"] == "playing" and pulse["step"] != "--" for pulse in sound["pulses"])
    assert page.locator(".loom-beat").inner_text() != "--"
    assert page.locator(".loom-step[aria-current='step']").count() == 1
    expected = [{261.626, 329.628}, {329.628}, {293.665}, {391.995},
                {261.626}, {329.628}, {440}, {391.995}]
    epoch = sound["notes"][0]["time"]
    for note in sound["notes"]:
        step = round((note["time"] - epoch) / (60 / 96 / 2)) % 8
        assert note["frequency"] in expected[step], note
        assert note["type"] == "sine"
    capture(page, folder, f"sound-loom-{width}-playing")
    page.get_by_role("button", name="Stop loom").click()
    state(page, "ready")
    frozen(page, audio=True)
    page.get_by_role("button", name="Play loom").click()
    state(page, "playing")
    inactive(page)
    frozen(page, audio=True)
    active(page)
    state(page, "ready")
    frozen(page, audio=True)
    contexts = len(snapshot(page)["audioStates"])
    page.wait_for_timeout(150)
    assert len(snapshot(page)["audioStates"]) == contexts, "Loom auto-resumed."
    page.get_by_role("button", name="Play loom").click()
    state(page, "playing")
    hidden(page, True)
    frozen(page, audio=True)
    hidden(page, False)
    frozen(page, audio=True)
    page.get_by_role("button", name="Clear", exact=True).click()
    for pitch in ["A4", "G4", "E4", "D4"]:
        page.get_by_role("button", name=f"{pitch}, step 1", exact=True).click()
    assert page.locator(".loom-note[data-step='0'][aria-pressed=true]").count() == 3
    assert "already has three notes" in page.locator(".loom-summary").inner_text()
    page.locator(".loom-tuning > summary").click()
    page.wait_for_function("harness.root.dataset.view === 'tune'")
    assert not page.locator(".loom-scroll").is_visible()
    page.get_by_label("Timbre", exact=True).select_option("triangle")
    page.get_by_label("Tempo", exact=True).fill("144")
    capture(page, folder, f"sound-loom-{width}-tune")
    page.locator(".loom-tuning > summary").click()
    page.wait_for_function("harness.root.dataset.view === 'keys'")
    assert page.locator(".loom-scroll").is_visible()
    page.evaluate("""() => document.querySelectorAll('.loom-note').forEach(cell => {
      if (Number(cell.dataset.row) < 3 && cell.getAttribute('aria-pressed') === 'false') cell.click();
    })""")
    assert page.locator(".loom-note[aria-pressed=true]").count() == 24
    page.get_by_role("button", name="Play loom").click()
    state(page, "playing")
    page.wait_for_timeout(800)
    stress = snapshot(page)
    assert stress["notes"][-1]["type"] == "triangle"
    assert 3 <= stress["peakNodes"] <= 6
    stress_notes = [note for note in stress["notes"] if note["context"] == len(stress["audioStates"]) - 1]
    assert len(stress_notes) >= 9
    assert all(note["frequency"] in {440, 391.995, 329.628} for note in stress_notes)
    step_times = sorted({note["time"] for note in stress_notes})
    assert all(abs(second - first - 60 / 144 / 2) < .00001 for first, second in zip(step_times, step_times[1:]))
    preferences(page, reduced=True, forced=True)
    assert page.locator(".loom-note").first.evaluate(
        "el => getComputedStyle(el).animationName === 'none' && getComputedStyle(el).transitionDuration === '0s'")
    capture(page, folder, f"sound-loom-{width}-forced-controller")
    assert page.locator(".loom-note[aria-pressed=true]").first.evaluate(
        "el => getComputedStyle(el).borderTopStyle") == "double"
    page.evaluate("harness.abort.abort(); harness.controller.destroy(); harness.controller.destroy()")
    frozen(page, audio=True)
    assert not page.locator(".loom-note").count()
    assert not page.evaluate("harness.errors")
    return {"width": width, "peak_audio_rms": round(peak_rms, 6), "scheduled_notes": len(sound["notes"]),
            "peak_nodes": stress["peakNodes"], "peak_scheduling_timers": sound["peakTimers"],
            "audio_creation_and_resume_in_gesture": True, "stopped_scheduling": 0,
            "actual_step_pulses": len(sound["pulses"])}


def failures(browser, url):
    print("Testing explicit failure and in-flight cancellation paths", flush=True)
    context = browser.new_context()
    context.add_init_script(PROBE)
    page = context.new_page()
    page.route("**/suff-syed-signature.svg", lambda route: route.abort())
    page.goto(f"{url}/?id=type-garden")
    state(page, "failed")
    assert page.locator(".type-error").is_visible()
    assert page.evaluate("harness.errors.length") == 1
    frozen(page)
    context.close()

    context = browser.new_context()
    context.add_init_script(PROBE)
    page = context.new_page()
    page.goto(f"{url}/?id=sound-loom")
    state(page, "ready")
    page.evaluate("() => { window.AudioContext = function() { throw new Error('Deliberate audio failure'); }; }")
    page.get_by_role("button", name="Play loom").click()
    state(page, "error")
    assert page.locator(".loom-error").is_visible()
    assert page.get_by_role("button", name="Play loom").get_attribute("aria-pressed") == "false"
    assert page.evaluate("harness.errors.length") == 1
    frozen(page)
    context.close()

    context = browser.new_context()
    context.add_init_script(PROBE)
    page = context.new_page()
    page.goto(f"{url}/?id=type-garden&inactive")
    state(page, "inactive")
    # Font readiness is held to test aborting an actual in-flight mount, not only a mounted controller.
    page.evaluate("""async () => {
      const module = await import('/assets/playground/type-garden.js');
      const original = document.fonts.load.bind(document.fonts);
      let releaseFont;
      document.fonts.load = (...args) => new Promise(resolve => {
        releaseFont = () => original(...args).then(resolve);
      });
      harness.controller.destroy();
      const abort = new AbortController();
      const pending = module.mount(harness.root, { ...harness.context, signal: abort.signal });
      abort.abort();
      releaseFont();
      const controller = await Promise.race([pending, new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Aborted mount did not settle')), 2000))]);
      controller.setActive(true);
      controller.destroy();
      document.fonts.load = original;
    }""")
    frozen(page)
    assert not page.locator(".type-canvas").count()
    context.close()

    context = browser.new_context()
    context.add_init_script(PROBE)
    page = context.new_page()
    page.goto(f"{url}/?id=sound-loom")
    state(page, "ready")
    page.evaluate("""(() => {
      const Observed = window.AudioContext;
      window.AudioContext = function() {
        const audio = new Observed(), resume = audio.resume.bind(audio);
        audio.resume = () => {
          const resumed = resume();
          return new Promise(resolve => { window.finishAudioResume = () => resumed.then(resolve); });
        };
        return audio;
      };
    })();""")
    page.get_by_role("button", name="Play loom").click()
    state(page, "starting")
    assert len(snapshot(page)["audioStates"]) == 1
    page.evaluate("harness.abort.abort(); window.finishAudioResume()")
    frozen(page, audio=True)
    assert not snapshot(page)["notes"], "Cancelled resume scheduled notes."
    assert not page.locator(".loom-note").count()
    context.close()


def compact(browser, url, folder):
    results = []
    for viewport, root_width, height in [(320, 280, 320), (390, 350, 310)]:
        context = browser.new_context(viewport={"width": viewport, "height": 740}, device_scale_factor=2, has_touch=True)
        context.add_init_script(PROBE)
        page = context.new_page()
        for kind in ["type-garden", "sound-loom"]:
            page.goto(f"{url}/?id={kind}&width={root_width}&height={height}", wait_until="load")
            state(page, "resting" if kind == "type-garden" else "ready")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            bounds = page.locator("#fixture").bounding_box()
            assert bounds["width"] == root_width and bounds["height"] == height
            geometry = world_checks(page, kind)
            assert geometry["root"]["scrollHeight"] <= geometry["root"]["clientHeight"] + 2
            if kind == "sound-loom":
                scroll = page.locator(".loom-scroll")
                assert scroll.evaluate("el => el.scrollWidth > el.clientWidth")
                assert scroll.evaluate("el => el.scrollHeight <= el.clientHeight + 2"), (
                    scroll.evaluate("el => [el.scrollHeight, el.clientHeight]"))
                note = page.get_by_role("button", name="A4, step 1", exact=True)
                note.tap()
                assert note.get_attribute("aria-pressed") == "true"
                assert not snapshot(page)["audioStates"], "Tap editing started audio."
                page.get_by_role("button", name="Play loom").tap()
                state(page, "playing")
                page.get_by_role("button", name="Stop loom").tap()
                frozen(page, audio=True)
            else:
                page.get_by_role("button", name="Pause garden motion").tap()
                state(page, "paused")
                preferences(page, reduced=True)
                frozen(page)
            capture(page, folder, f"{kind}-{viewport}-compact-{root_width}x{height}")
            if kind == "sound-loom":
                page.locator(".loom-tuning > summary").tap()
                page.wait_for_function("harness.root.dataset.view === 'tune'")
                capture(page, folder, f"{kind}-{viewport}-compact-tune")
                page.locator(".loom-tuning > summary").tap()
            assert not page.evaluate("harness.errors")
            page.evaluate("harness.abort.abort()")
            frozen(page, audio=True)
            results.append({"id": kind, "width": root_width, "height": height, "touch": True, **geometry})
        context.close()
    return results


def world_frames(browser, url, folder):
    results = []
    for viewport, root_width, height in [(320, 280, 397.5), (390, 350, 386.390625),
                                         (1028, 962.21875, 410), (1600, 1500, 470)]:
        context = browser.new_context(viewport={"width": viewport, "height": 1000}, device_scale_factor=2)
        context.add_init_script(PROBE)
        page = context.new_page()
        for kind in ["type-garden", "sound-loom"]:
            page.goto(f"{url}/?id={kind}&width={root_width}&height={height}", wait_until="load")
            state(page, "resting" if kind == "type-garden" else "ready")
            result = world_checks(page, kind)
            assert result["root"]["scrollHeight"] <= result["root"]["clientHeight"] + 2
            if kind == "sound-loom":
                assert result["stage"]["scrollHeight"] <= result["stage"]["clientHeight"] + 2, result
            capture(page, folder, f"{kind}-{viewport}-host-sized")
            results.append({"id": kind, "viewport": viewport, **result})
            page.evaluate("harness.abort.abort()")
            frozen(page, audio=True)
        context.close()
    return results


def host_frames(browser, url, folder):
    """Inspect the owner's running host; route only owned module assets in this browser."""
    results = []
    for width, height in [(320, 740), (390, 844), (1028, 900), (1600, 1000)]:
        context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=2)
        context.add_init_script(PROBE)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def owned_asset(route):
            filename = Path(urlparse(route.request.url).path).name
            target = ROOT / "site" / "playground" / filename
            route.fulfill(path=str(target), content_type=mimetypes.guess_type(str(target))[0])

        for kind in ["type-garden", "sound-loom"]:
            for extension in ["js", "css"]:
                page.route(f"**/assets/playground/{kind}.{extension}*", owned_asset)
        page.goto(url, wait_until="load")
        cover = page.locator(".home-cover")
        original_height = cover.bounding_box()["height"]
        page.locator(".signature-entry").click()
        for kind in ["type-garden", "sound-loom"]:
            page.get_by_label("Choose experiment", exact=True).select_option(kind)
            page.wait_for_function("""kind => document.querySelector(`[data-experience="${kind}"]`)?.dataset.state
              === (kind === 'type-garden' ? 'resting' : 'ready')""", arg=kind)
            page.wait_for_timeout(400)
            assert abs(cover.bounding_box()["height"] - original_height) < .1
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            result = world_checks(page, kind)
            assert result["root"]["scrollHeight"] <= result["root"]["clientHeight"] + 2, result
            if kind == "sound-loom":
                assert result["stage"]["scrollHeight"] <= result["stage"]["clientHeight"] + 2, result
                assert not page.evaluate("probe.contexts.length"), "Host selection started audio."
            cover.screenshot(path=str(folder / f"{kind}-{width}-real-host.png"))
            result["shared_scene_markers"] = page.locator(f'[data-world-signature="{kind}"]').count()
            if kind == "sound-loom":
                assert result["shared_scene_markers"] == 1, "Sound should have exactly one decorative scene."
                assert page.locator('[data-world-signature="sound-loom"]').get_attribute("aria-hidden") == "true"
                page.wait_for_timeout(1400)
                settled = page.evaluate("probe.sceneFrames")
                page.wait_for_timeout(250)
                assert page.evaluate("probe.sceneFrames") == settled, "Shared arrival did not settle."
                page.get_by_role("button", name="Play loom").click()
                page.wait_for_function("document.querySelector('[data-experience=\"sound-loom\"]').dataset.state === 'playing'")
                peak = 0
                for _ in range(18):
                    page.wait_for_timeout(100)
                    peak = max(peak, rms(page))
                assert peak > 0, "The actual host produced no audio samples."
                assert page.evaluate("probe.sceneFrames") > settled, "Actual sequencer steps did not pulse the shared signature."
                cover.screenshot(path=str(folder / f"{kind}-{width}-real-host-playing.png"))
                page.get_by_role("button", name="Stop loom").click()
                page.wait_for_function("probe.contexts.every(c => c.audio.state === 'closed')")
                assert page.evaluate("probe.nodes.size === 0 && probe.timers.size === 0 && probe.connections.size === 0")
                page.wait_for_timeout(1400)
                after_stop = page.evaluate("probe.sceneFrames")
                page.wait_for_timeout(300)
                assert page.evaluate("probe.sceneFrames") == after_stop, "Stopped loom kept requesting scene work."
                result["actual_host_audio_rms"] = peak
                result["actual_host_playing_scene_frames"] = after_stop - settled
            results.append({"id": kind, "width": width, "cover_height": original_height, **result})
        page.get_by_role("button", name="Play loom").click()
        page.wait_for_function("document.querySelector('[data-experience=\"sound-loom\"]').dataset.state === 'playing'")
        page.get_by_role("button", name="Close experiment", exact=True).click()
        page.wait_for_function("probe.contexts.every(c => c.audio.state === 'closed')")
        closed_frames = page.evaluate("probe.sceneFrames")
        page.wait_for_timeout(100)
        assert not page.locator(".pg-instance").count()
        assert page.evaluate("probe.rafts.size === 0 && probe.timers.size === 0 && probe.nodes.size === 0 && probe.connections.size === 0")
        assert page.evaluate("probe.sceneFrames") == closed_frames
        assert not errors, errors
        context.close()
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--shared-css", type=Path, help="Optional read-only integration-owner playground.css")
    parser.add_argument("--host-url", help="Optional live integration host; only owned assets are browser-routed.")
    parser.add_argument("--frames-only", action="store_true", help="Only palette/geometry/real-frame checks; not a substitute for the full suite.")
    parser.add_argument("--widths", nargs="+", type=int, default=[320, 390, 1028, 1600])
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    assert args.harness.is_file(), "Supply the session-artifact v1 mount fixture."
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(
        FixtureServer, harness=args.harness.resolve(), shared_css=args.shared_css))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    assert server.server_port != 8766
    with urlopen(url) as response:
        assert response.status == 200
    report = {"url": url, "garden": [], "loom": [], "gzip_bytes": {}, "limitations": [
        "WebKit forced-color controller and CSS checks are not native OS forced-palette emulation.",
        "Standalone v1 contract fixture; final shared-host integration is verified by the integration owner.",
    ]}
    report["validation_mode"] = "frames-only" if args.frames_only else "full"
    errors, external = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.webkit.launch(timeout=20000)
            for width in [] if args.frames_only else args.widths:
                print(f"Testing Type garden and Sound loom at {width}px", flush=True)
                context = browser.new_context(viewport={"width": width, "height": 740}, device_scale_factor=2)
                context.add_init_script(PROBE)
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda request: external.append(request.url) if not request.url.startswith(url) else None)
                try:
                    report["garden"].append(run_garden(page, url, args.artifacts, width))
                    report["loom"].append(run_loom(page, url, args.artifacts, width))
                except Exception:
                    page.screenshot(path=str(args.artifacts / f"failure-{width}.png"))
                    (args.artifacts / f"failure-{width}.json").write_text(json.dumps(snapshot(page), indent=2))
                    raise
                context.close()
            if not args.frames_only:
                failures(browser, url)
            print("Testing exact compact host roots and touch controls", flush=True)
            report["compact"] = compact(browser, url, args.artifacts)
            report["world_frames"] = world_frames(browser, url, args.artifacts)
            if args.host_url:
                report["real_host"] = host_frames(browser, args.host_url, args.artifacts)
            browser.close()
        assert not errors, errors
        assert not external, external
        for name in ["type-garden", "sound-loom"]:
            parts = [(ROOT / "site" / "playground" / f"{name}.{ext}").read_bytes() for ext in ["js", "css"]]
            payload = b"".join(parts)
            compressed = len(gzip.compress(payload, mtime=0))
            assert compressed < 60 * 1024
            separate = [len(gzip.compress(part, mtime=0)) for part in parts]
            report["gzip_bytes"][name] = {
                "concatenated": compressed, "js": separate[0], "css": separate[1],
                "separately_served": sum(separate),
            }
        (args.artifacts / "type-sound-results.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({key: report[key] for key in ["validation_mode", "garden", "loom", "gzip_bytes", "limitations"]}, indent=2))
        print(f"Detailed frames, contrast and geometry: {args.artifacts / 'type-sound-results.json'}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
