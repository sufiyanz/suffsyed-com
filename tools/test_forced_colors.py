"""Verify painted signature identity in normal and forced-color browser screenshots."""
import argparse
import base64
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def raster(page, screenshot, dark_ink):
    return page.evaluate("""async ({png, darkInk}) => {
      const bytes = Uint8Array.from(atob(png), value => value.charCodeAt(0));
      const bitmap = await createImageBitmap(new Blob([bytes], {type: 'image/png'}));
      const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
      const context = canvas.getContext('2d');
      context.drawImage(bitmap, 0, 0);
      const pixels = context.getImageData(0, 0, bitmap.width, bitmap.height).data;
      const ink = [], values = [];
      let darkest = 255, lightest = 0;
      for (let i = 0; i < pixels.length; i += 4) {
        const value = (pixels[i] + pixels[i + 1] + pixels[i + 2]) / 3;
        darkest = Math.min(darkest, value);
        lightest = Math.max(lightest, value);
        values.push(value);
      }
      const threshold = (darkest + lightest) / 2;
      values.forEach((value, index) => {
        if (darkInk ? value < threshold : value > threshold) ink.push(index);
      });
      bitmap.close();
      return {width: canvas.width, height: canvas.height, ink, darkest, lightest};
    }""", {"png": base64.b64encode(screenshot).decode(), "darkInk": dark_ink})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    report, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height, expected_width in [(320, 740, 260), (390, 844, 300), (1028, 900, 431.75), (1600, 1000, 560)]:
            baseline, geometry = None, None
            for mode in ["normal", "light", "dark"]:
                context = browser.new_context(viewport={"width": width, "height": height},
                                              forced_colors="none" if mode == "normal" else "active",
                                              color_scheme="dark" if mode == "dark" else "light",
                                              reduced_motion="reduce")
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(args.url, wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                page.locator(".cover-signature").evaluate("el => el.decode()")
                assert page.get_by_role("heading", name="Suff Syed", exact=True).count() == 1
                assert page.locator(".cover-signature").count() == 1
                assert not page.locator(".cover-kicker").count()
                bounds = page.locator(".cover-signature").evaluate("""el => {
                  const r = el.getBoundingClientRect();
                  return {x: r.x, y: r.y, width: r.width, height: r.height};
                }""")
                assert abs(bounds["width"] - expected_width) < .1
                assert abs(bounds["width"] / bounds["height"] - 350 / 148) < .01
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                colors = page.locator("#cover-title").evaluate("""el => ({
                  heading: getComputedStyle(el).color,
                  paint: getComputedStyle(el, '::after').backgroundColor,
                  canvas: getComputedStyle(el.closest('.home-cover')).backgroundColor,
                  bodyAdjustment: getComputedStyle(document.body).forcedColorAdjust,
                  coverAdjustment: getComputedStyle(el.closest('.home-cover')).forcedColorAdjust
                })""")
                page.screenshot(path=str(args.artifacts / f"{width}-{mode}-cover.png"))
                image = page.screenshot(path=str(args.artifacts / f"{width}-{mode}-signature.png"), clip=bounds)
                sample = raster(page, image, dark_ink=mode == "light")
                painted = set(sample.pop("ink"))
                if mode == "normal":
                    baseline, geometry = painted, bounds
                    assert len(painted) > sample["width"] * sample["height"] * .05
                else:
                    assert bounds == geometry
                    assert colors["bodyAdjustment"] == colors["coverAdjustment"] == "auto"
                    assert colors["paint"] == colors["heading"] != colors["canvas"], colors
                    assert sample["darkest"] <= 5 and sample["lightest"] >= 250, sample
                    overlap = len(painted & baseline) / len(painted | baseline)
                    assert overlap >= .97, (width, mode, overlap)
                    report.append({"width": width, "scheme": mode, "paintedShapeOverlap": overlap,
                                   "colors": colors, "pixels": sample})
                context.close()
        browser.close()
    assert not errors, errors
    (args.artifacts / "forced-colors-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: both forced-color schemes paint the same identifiable signature with black/white contrast; four normal sizes/layouts and accessible name preserved.")


if __name__ == "__main__":
    main()
