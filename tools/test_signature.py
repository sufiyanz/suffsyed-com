"""Painted glyph substitutions, bounded scheduling, static fallbacks and cover geometry."""
import argparse
import base64
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

PROBE = """(() => {
  const probe = window.signatureProbe = {frames: 0, ticks: 0, cells: {}, times: [], active: new Set(), peak: 0};
  const clear = CanvasRenderingContext2D.prototype.clearRect;
  const text = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.clearRect = function(...args) {
    if (this.canvas.classList.contains('signature-field')) {
      probe.frames++; probe.cells = {}; probe.times.push(performance.now());
    }
    return clear.apply(this, args);
  };
  CanvasRenderingContext2D.prototype.fillText = function(value, x, y, ...args) {
    if (this.canvas.classList.contains('signature-field')) {
      probe.cells[x + ':' + y] = value; probe.font = this.font;
    }
    return text.call(this, value, x, y, ...args);
  };
  const schedule = window.setTimeout, cancel = window.clearTimeout;
  window.setTimeout = function(fn, delay, ...args) {
    if (typeof fn !== 'function' || fn.name !== 'tick') return schedule(fn, delay, ...args);
    const id = schedule(() => { probe.active.delete(id); probe.ticks++; fn(...args); }, delay);
    probe.active.add(id); probe.peak = Math.max(probe.peak, probe.active.size);
    return id;
  };
  window.clearTimeout = function(id) { probe.active.delete(id); return cancel(id); };
})();"""


def state(page, value):
    page.wait_for_function("value => document.querySelector('.home-cover').dataset.signatureState === value", arg=value)


def snapshot(page):
    return page.evaluate("""() => ({
      frames: signatureProbe.frames, ticks: signatureProbe.ticks, cells: signatureProbe.cells,
      timers: signatureProbe.active.size, peak: signatureProbe.peak, font: signatureProbe.font,
      bitmap: document.querySelector('.signature-field')?.toDataURL(),
      times: signatureProbe.times
    })""")


def frozen(page):
    before = snapshot(page)
    page.wait_for_timeout(720)
    after = snapshot(page)
    assert before == after, "A suspended/paused field changed or scheduled work."
    assert after["timers"] == 0


def geometry(page):
    return page.evaluate("""() => Object.fromEntries(
      ['.home-cover', '.cover-signature', '.cover-role', '.cover-invitation', '.cover-continue', '#main']
      .map(selector => { const r = document.querySelector(selector).getBoundingClientRect();
        return [selector, {x:r.x, y:r.y, width:r.width, height:selector === '#main' ? null : r.height}]; }))""")


def identity(page):
    assert page.get_by_role("heading", name="Suff Syed", exact=True).count() == 1
    assert page.locator("#cover-title > .cover-signature").count() == 1
    assert page.locator("#cover-title canvas[aria-hidden=true]").count() <= 1
    assert not page.locator(".cover-kicker, #cover-title button").count()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def capture(page, folder, name):
    page.screenshot(path=str(folder / f"{name}-opening.png"))
    bounds = page.locator(".cover-signature").bounding_box()
    page.screenshot(path=str(folder / f"{name}-mark.png"), clip=bounds)


def painted_shape(page):
    image = page.screenshot(clip=page.locator(".cover-signature").bounding_box())
    return page.evaluate("""async png => {
      const bitmap = await createImageBitmap(new Blob([
        Uint8Array.from(atob(png), c => c.charCodeAt(0))], {type:'image/png'}));
      const surface = document.createElement('canvas');
      surface.width = bitmap.width; surface.height = bitmap.height;
      const ctx = surface.getContext('2d');
      ctx.drawImage(bitmap, 0, 0);
      const actual = ctx.getImageData(0, 0, surface.width, surface.height).data;
      ctx.clearRect(0, 0, surface.width, surface.height);
      const source = document.querySelector('.cover-signature');
      const bounds = source.getBoundingClientRect();
      // Screenshot crops can truncate fractional CSS heights; don't rescale the reference to the crop.
      ctx.drawImage(source, 0, 0, bounds.width * devicePixelRatio, bounds.height * devicePixelRatio);
      const reference = ctx.getImageData(0, 0, surface.width, surface.height).data;
      const bg = getComputedStyle(document.querySelector('.home-cover')).backgroundColor.match(/[0-9.]+/g).map(Number);
      const radius = Math.round(surface.width / document.querySelector('.cover-signature').width * 1.5);
      const alpha = (x,y) => x < 0 || y < 0 || x >= surface.width || y >= surface.height
        ? 0 : reference[(y * surface.width + x) * 4 + 3];
      let core = 0, visible = 0, thin = 0, thinVisible = 0, bright = 0, quiet = 0;
      for (let y = 0; y < surface.height; y++) for (let x = 0; x < surface.width; x++) {
        if (alpha(x,y) < 192) continue;
        const i = (y * surface.width + x) * 4;
        const strength = (actual[i] + actual[i+1] + actual[i+2] - bg[0] - bg[1] - bg[2])
          / (765 - bg[0] - bg[1] - bg[2]);
        core++; if (strength > .1) visible++;
        if (strength > .6) bright++;
        if (strength < .45) quiet++;
        if ([[radius,0],[0,radius],[radius,radius],[radius,-radius]].some(([dx,dy]) =>
          alpha(x-dx,y-dy) < 32 && alpha(x+dx,y+dy) < 32)) {
          thin++; if (strength > .1) thinVisible++;
        }
      }
      bitmap.close();
      return {core, coverage:visible/core, thin, thinCoverage:thinVisible/thin,
        bright:bright/core, quiet:quiet/core};
    }""", base64.b64encode(image).decode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--capture-only", action="store_true")
    parser.add_argument("--no-captures", action="store_true")
    parser.add_argument("--fallbacks-only", action="store_true")
    parser.add_argument("--browser-channel", default=None)
    parser.add_argument("--browser", choices=["chromium", "webkit"], default="chromium")
    parser.add_argument("--widths", type=int, nargs="+", choices=[320,390,820,1028,1600,1920])
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    errors, external, report = [], [], []
    with sync_playwright() as p:
        browser = getattr(p, args.browser).launch(**({"channel": args.browser_channel} if args.browser_channel else {}))
        sizes = [(320, 740), (390, 844), (820, 1180), (1028, 900), (1600, 1000), (1920, 1120)]
        if args.widths:
            sizes = [size for size in sizes if size[0] in args.widths]
        if args.fallbacks_only:
            sizes = []
        for width, height in sizes:
            print(f"Character field: {width}px", flush=True)
            context = browser.new_context(viewport={"width": width, "height": height},
                                          device_scale_factor=2, has_touch=width < 900, is_mobile=width < 900)
            context.add_init_script(PROBE)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: external.append(request.url) if not request.url.startswith(args.url) else None)
            page.goto(args.url, wait_until="load")
            state(page, "running")
            page.evaluate("document.fonts.ready")
            before = geometry(page)
            identity(page)
            expected = {320:260, 390:300, 820:344.4, 1028:431.75, 1600:560, 1920:560}
            assert abs(before[".cover-signature"]["width"] - expected[width]) < .1
            assert abs(before[".cover-signature"]["width"] / before[".cover-signature"]["height"] - 350/148) < .01
            if not args.no_captures:
                capture(page, args.artifacts, f"{width}-initial")
            page.wait_for_timeout(550)
            if not args.no_captures:
                capture(page, args.artifacts, f"{width}-resolve")
            page.wait_for_timeout(1200)
            if not args.no_captures:
                capture(page, args.artifacts, f"{width}-settled")
            shape = painted_shape(page)
            assert shape["coverage"] > .97 and shape["thinCoverage"] > .95, shape
            assert shape["thin"] > 0 and shape["bright"] > .01 and shape["quiet"] > .2, shape
            first = snapshot(page)
            page.wait_for_timeout(700)
            second = snapshot(page)
            assert first["bitmap"] != second["bitmap"], "Paint did not change."
            changed = [key for key in first["cells"] if first["cells"][key] != second["cells"][key]]
            assert 1 <= len(changed) <= 6, changed
            assert first["cells"].keys() == second["cells"].keys(), "Grid positions moved."
            assert second["peak"] == second["timers"] == 1
            assert 0 < len(second["cells"]) <= 3000
            assert "DM Mono" in second["font"]
            assert page.locator(".signature-field").evaluate("el => el.width * el.height <= 600000")
            # Only the bounded scheduler paints after the one-time layout/initialization draws.
            assert min(b - a for a, b in zip(second["times"][-5:], second["times"][-4:])) >= 145
            button = page.get_by_role("button", name="Pause signature animation", exact=True)
            box = button.bounding_box()
            assert box["width"] >= 44 and box["height"] >= 44
            assert box["y"] >= before[".cover-signature"]["y"] + before[".cover-signature"]["height"]
            if width < 900:
                button.tap()
            else:
                button.focus()
                page.keyboard.press("Space")
            state(page, "paused")
            if width >= 900:
                assert page.get_by_role("button", name="Resume signature animation").evaluate(
                    "el => getComputedStyle(el).outlineColor") == "rgb(255, 255, 255)"
            frozen(page)
            assert page.get_by_role("button", name="Resume signature animation", exact=True).is_visible()
            assert geometry(page) == before
            page.emulate_media(reduced_motion="reduce")
            state(page, "static")
            frozen(page)
            assert not page.locator(".signature-field").is_visible()
            assert not page.locator(".signature-motion").is_visible()
            assert page.locator(".cover-signature").evaluate("el => getComputedStyle(el).opacity") == "1"
            assert geometry(page) == before, "Enhancement changed the static cover footprint."
            page.emulate_media(reduced_motion="no-preference")
            state(page, "paused")
            frozen(page)
            page.get_by_role("button", name="Resume signature animation").click()
            state(page, "running")
            if not args.capture_only:
                page.evaluate("scrollTo(0, document.querySelector('.home-cover').offsetHeight + 5)")
                state(page, "suspended")
                frozen(page)
                assert page.locator(".mast").is_visible()
                page.evaluate("scrollTo(0, 0)")
                state(page, "running")
                assert not page.locator(".mast").is_visible()
                # Exercise the real lifecycle listener with controlled visibility on headless Chromium.
                page.evaluate("""() => {
                  Object.defineProperty(document, 'hidden', {configurable:true, get: () => true});
                  document.dispatchEvent(new Event('visibilitychange'));
                }""")
                state(page, "suspended")
                frozen(page)
                page.evaluate("""() => {
                  delete document.hidden;
                  document.dispatchEvent(new Event('visibilitychange'));
                }""")
                state(page, "running")
                for scheme in ["light", "dark"]:
                    page.emulate_media(forced_colors="active", color_scheme=scheme)
                    state(page, "static")
                    frozen(page)
                    identity(page)
                    assert not page.locator(".signature-motion").is_visible()
                    if page.evaluate("CSS.supports('forced-color-adjust', 'auto')"):
                        assert page.locator("body").evaluate("el => getComputedStyle(el).forcedColorAdjust") == "auto"
                    else:
                        print(f"NOTE: {args.browser} lacks native forced-palette rendering; {scheme} controller/static checks only.", flush=True)
                page.emulate_media(forced_colors="none")
                state(page, "running")
                context.set_offline(True)
                offline = snapshot(page)
                page.wait_for_timeout(700)
                assert snapshot(page)["bitmap"] != offline["bitmap"]
                context.set_offline(False)
                if width == 1600:
                    page.get_by_role("button", name="Pause signature animation").click()
                    for size in [{"width":390, "height":844}, {"width":1600, "height":1000}]:
                        page.set_viewport_size(size)
                        page.wait_for_timeout(300)
                        state(page, "paused")
                        assert len(snapshot(page)["cells"]) < 1000, "Resize restarted the ambient resolve."
                        assert snapshot(page)["peak"] == 1
                        frozen(page)
                        identity(page)
            report.append({"width": width, "geometry": before, "drawnCells": len(second["cells"]),
                           "changedGlyphs": len(changed), "peakTimers": second["peak"], "font": second["font"],
                           "paintedShape": shape,
                           "nativeForcedPaletteSupported": page.evaluate("CSS.supports('forced-color-adjust','auto')")})
            context.close()

        if not args.capture_only:
            for mode in ["no-js", "font-failure", "no-canvas", "no-resize", "reduced", "forced", "offscreen"]:
                print(f"Fallback: {mode}", flush=True)
                context = browser.new_context(viewport={"width": 390, "height": 844},
                                              java_script_enabled=mode != "no-js",
                                              reduced_motion="reduce" if mode == "reduced" else "no-preference",
                                              forced_colors="active" if mode == "forced" else "none")
                warnings = []
                if mode != "no-js":
                    context.add_init_script(PROBE)
                if mode == "font-failure":
                    context.route("**/dm-mono-regular.woff2", lambda route: route.abort())
                if mode == "no-canvas":
                    context.add_init_script("HTMLCanvasElement.prototype.getContext = () => null;")
                if mode == "no-resize":
                    context.add_init_script("delete window.ResizeObserver;")
                page = context.new_page()
                page.on("console", lambda message: warnings.append(message.text) if message.type == "warning" else None)
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(args.url + ("/#connections" if mode == "offscreen" else "/"), wait_until="networkidle")
                identity(page)
                if mode == "offscreen":
                    # Native fragment restoration may follow a brief initial intersection.
                    state(page, "suspended")
                    assert page.locator(".cover-signature").bounding_box()["y"] < 0
                    frozen(page)
                    context.close()
                    continue
                assert not page.locator(".signature-motion").is_visible()
                assert page.locator(".cover-signature").evaluate("el => getComputedStyle(el).opacity") == "1"
                if mode in ["font-failure", "no-canvas", "no-resize"]:
                    state(page, "failed")
                    assert any("Signature animation unavailable" in message for message in warnings), (mode, warnings)
                if mode != "no-js":
                    frozen(page)
                    assert snapshot(page)["frames"] == 0, mode
                page.screenshot(path=str(args.artifacts / f"fallback-{mode}.png"))
                context.close()
        browser.close()
    assert not errors, errors
    assert not external, external
    (args.artifacts / "signature-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    if not args.fallbacks_only:
        print("PASS: actual sparse glyph changes, frozen pause/preferences and unchanged geometry.")
    print("Full lifecycle/failure matrix not run (--capture-only)." if args.capture_only else
          "PASS: static initialization fallbacks and deep-link suspension.")
    print("Native palette contrast requires the separate capable-engine check.")


if __name__ == "__main__":
    main()
