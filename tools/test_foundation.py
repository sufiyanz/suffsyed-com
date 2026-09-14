"""Focused browser acceptance for the static homepage, not the parked experiments."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

from foundation_home import DESCRIPTION, IDENTITY

WIDTHS = (320, 390, 820, 1600)


def contact_sheet(output, frames):
    widths = (720, 320)
    images = []
    for name, width in zip(("1600", "390"), widths):
        source = Image.open(frames[name])
        images.append(source.resize((width, round(source.height * width / source.width))))
    sheet = Image.new("RGB", (sum(widths) + 72, max(im.height for im in images) + 64), "#f6f4eb")
    draw = ImageDraw.Draw(sheet)
    x = 24
    for name, image in zip(("Desktop / 1600px", "Phone / 390px"), images):
        draw.text((x, 12), name, fill="#213b2c")
        sheet.paste(image, (x, 40))
        x += image.width + 24
    path = output / "foundation-contact.png"
    sheet.save(path)
    sheet.thumbnail((1500, 1800))
    sheet.save(output / "foundation-contact-review.png")
    return str(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8773")
    parser.add_argument("--browser", choices=("chromium", "webkit", "firefox"), default="chromium")
    parser.add_argument("--output", type=Path, help="Optional directory for full-page screenshots and evidence.")
    args = parser.parse_args()
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
    evidence = {"browser": args.browser, "url": args.url, "widths": {}, "frames": {}}
    with sync_playwright() as p:
        browser = getattr(p, args.browser).launch()
        for width in WIDTHS:
            context = browser.new_context(viewport={"width": width, "height": 900 if width > 700 else 844},
                                          device_scale_factor=1, reduced_motion="reduce")
            page = context.new_page()
            requests, errors, failures = [], [], []
            page.on("request", lambda request: requests.append((request.url, request.resource_type)))
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("response", lambda response: failures.append(response.url) if response.status >= 400 else None)
            response = page.goto(args.url, wait_until="networkidle")
            assert response.status == 200
            assert page.get_by_role("heading", name="Suff Syed", exact=True).count() == 1
            assert page.locator(".cover-role").inner_text() == IDENTITY
            assert page.locator(".cover-description").inner_text() == DESCRIPTION
            assert page.locator("script, button, canvas, dialog, iframe").count() == 0
            assert page.locator('link[rel="stylesheet"]').count() == 1
            assert page.locator("h1 a, h1 button").count() == 0
            assert page.locator(".writing-list li").count() == 3
            assert page.locator(".photo-pair img").count() == 2
            assert page.locator(".site-header").evaluate("el => getComputedStyle(el).position") == "static"
            assert page.evaluate("document.getAnimations().length") == 0
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert page.evaluate("getComputedStyle(document.body).backgroundColor") in ("rgba(0, 0, 0, 0)", "rgb(232, 237, 223)")
            assert page.locator("html").evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(232, 237, 223)"
            assert page.locator("#writing-title").inner_text().replace("\n", " ").split() == ["Selected", "writing."]
            nav = page.locator(".site-header nav a")
            for link in nav.all():
                box = link.bounding_box()
                assert box["width"] >= 44 and box["height"] >= 44, box
            if width > 700:
                assert page.locator("#writing").bounding_box()["y"] < 900, "Cover must not bury the next section"
            page.keyboard.press("Alt+Tab" if args.browser == "webkit" else "Tab")
            assert page.locator(".skip").evaluate("el => el === document.activeElement")
            assert page.locator(".skip").bounding_box()["y"] >= 0
            assert page.locator(".skip").evaluate("el => getComputedStyle(el).outlineStyle") != "none"
            page.keyboard.press("Enter")
            assert page.locator("#main").evaluate("el => el === document.activeElement")
            for link in page.locator("a").all():
                link.focus()
                assert link.evaluate("el => getComputedStyle(el).outlineStyle") != "none"
            fonts = page.locator(".cover-role, .writing-list h3").evaluate_all(
                "els => els.map(el => ({family:getComputedStyle(el).fontFamily, weight:getComputedStyle(el).fontWeight}))")
            assert all("Helvetica" in font["family"] and font["weight"] == "400" for font in fonts)
            actual_fonts = []
            if args.browser == "chromium":
                client = context.new_cdp_session(page)
                client.send("DOM.enable")
                client.send("CSS.enable")
                document = client.send("DOM.getDocument")["root"]["nodeId"]
                for selector in (".cover-role", ".writing-list h3"):
                    node = client.send("DOM.querySelector", {"nodeId": document, "selector": selector})["nodeId"]
                    actual_fonts.append(client.send("CSS.getPlatformFontsForNode", {"nodeId": node})["fonts"])
                assert all(not font["isCustomFont"] for fonts_used in actual_fonts for font in fonts_used)
            for link in page.locator(".site-header nav a[href^='#']").all():
                href = link.get_attribute("href")
                link.click()
                assert page.url.endswith(href)
                assert abs(page.locator(href).bounding_box()["y"] - 32) < 2
            for image in page.locator(".photo-pair img").all():
                image.scroll_into_view_if_needed()
                image.evaluate("el => el.decode()")
                assert image.get_attribute("alt")
                assert image.get_attribute("srcset")
                dimensions = image.evaluate("""el => ({
                  painted: el.getBoundingClientRect().width / el.getBoundingClientRect().height,
                  expected: Number(el.getAttribute('width')) / Number(el.getAttribute('height')),
                  source: el.currentSrc, naturalWidth: el.naturalWidth
                })""")
                assert dimensions["naturalWidth"] > 0
                assert abs(dimensions["painted"] - dimensions["expected"]) < .01, dimensions
            page.get_by_role("link", name="Back to top").click()
            assert page.evaluate("scrollY") == 0
            if args.output:
                screenshot = args.output / f"foundation-{width}.png"
                page.screenshot(path=str(screenshot), full_page=True)
                evidence["frames"][str(width)] = str(screenshot)
            allowed_images = page.locator("img").evaluate_all(
                "els => els.flatMap(el => [el.src, ...el.srcset.split(',').filter(Boolean).map(s => new URL(s.trim().split(' ')[0], location.href).href)])")
            allowed = set(allowed_images) | {args.url.rstrip("/") + "/", args.url.rstrip("/") + "/assets/foundation.css",
                                             args.url.rstrip("/") + "/assets/favicon.svg"}
            assert all(url in allowed for url, _ in requests), requests
            assert not any(kind in ("script", "fetch", "xhr", "font") for _, kind in requests), requests
            assert not errors and not failures, (errors, failures)
            evidence["widths"][str(width)] = {"overflow": False, "computedFonts": fonts,
                                              "actualFonts": actual_fonts, "requests": requests,
                                              "height": page.evaluate("document.documentElement.scrollHeight")}
            context.close()
        # Native source navigation, at every required width, with scripting disabled.
        for width in WIDTHS:
            context = browser.new_context(java_script_enabled=False, viewport={"width": width, "height": 844})
            page = context.new_page()
            page.goto(args.url)
            assert page.get_by_role("heading", name="Suff Syed", exact=True).is_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.get_by_role("link", name="Writing", exact=True).first.click()
            assert page.url.endswith("#writing")
            essay = page.locator(".writing-list h3 a").first
            destination = essay.get_attribute("href")
            essay.click()
            page.wait_for_url("**" + destination)
            assert page.locator("#essay-body").is_visible()
            page.goto(args.url)
            photograph = page.locator(".photo-pair a").first
            destination = photograph.get_attribute("href")
            photograph.click()
            page.wait_for_url("**" + destination)
            assert page.locator("#plate-01 img").is_visible()
            context.close()
        context = browser.new_context(forced_colors="active", reduced_motion="reduce")
        page = context.new_page()
        for scheme in ("light", "dark"):
            page.emulate_media(forced_colors="active", color_scheme=scheme)
            page.goto(args.url)
            assert page.locator(".cover-signature").evaluate("el => getComputedStyle(el).visibility") == "hidden"
            mask = page.locator(".signature-ink").evaluate("""el => ({
              mask:getComputedStyle(el).maskImage, ink:getComputedStyle(el).backgroundColor,
              ground:getComputedStyle(document.documentElement).backgroundColor
            })""")
            assert "suff-syed-signature.svg" in mask["mask"] and mask["ink"] != mask["ground"], mask
            if args.output:
                page.screenshot(path=str(args.output / f"forced-colors-{scheme}.png"))
        context.close()
        browser.close()
    if args.output:
        evidence["contactSheet"] = contact_sheet(args.output, evidence["frames"])
        (args.output / "foundation-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("PASS: 320/390/820/1600, native navigation, authentic uncropped images, static signature, "
          "computed/public fonts, keyboard focus, no-JS, reduced motion, emulated forced colors; "
          "no deferred code, font, fetch or data requests.")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
