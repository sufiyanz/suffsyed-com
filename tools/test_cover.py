"""Compact identity cover, visibility-driven navigation and readable review captures."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROLE = "Suff Syed is a Member of Technical Staff building across AI frontiers at Microsoft."
DESCRIPTION = "Essays on intelligence, creative work, and what remains human."
DESTINATIONS = ["featured-story", "connections", "lightworks", "unfinished"]


def settle(page):
    page.evaluate("document.fonts.ready")
    page.locator("[data-home-cover]").evaluate("el => el.decode()")
    page.locator(".cover-signature").evaluate("el => el.decode()")
    page.wait_for_timeout(100)


def wait_for(page, expression, arg=None):
    for _ in range(100):
        if page.evaluate(expression, arg):
            return
        page.wait_for_timeout(50)
    raise AssertionError((page.url, expression, page.evaluate("scrollY")))


def no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def cover_state(page, height):
    assert page.locator("#cover-title").inner_text() == "Suff Syed"
    assert page.get_by_role("heading", name="Suff Syed", exact=True).count() == 1
    assert page.locator(".cover-signature").count() == 1
    assert page.locator("#cover-title > .cover-signature").count() == 1
    assert not page.locator(".cover-kicker").count()
    assert page.locator("#cover-title > .sr-only").evaluate("""el => {
      const rect = el.getBoundingClientRect();
      return rect.width <= 1 && rect.height <= 1 && getComputedStyle(el).clipPath === 'inset(50%)';
    }""")
    assert page.locator(".cover-role").inner_text() == ROLE
    assert page.locator(".cover-description").inner_text() == DESCRIPTION
    assert page.locator(".mast").count() == 1
    assert page.locator(".mast nav a").count() == 4
    cover = page.locator(".home-cover").bounding_box()
    assert abs(cover["y"]) < 1
    assert abs(cover["x"]) < 1 and abs(cover["width"] - page.evaluate("innerWidth")) < 1
    assert page.locator(".home-cover").evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(27, 41, 21)"
    assert page.locator("body").evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(239, 237, 230)"
    assert page.locator("#cover-title").evaluate("el => getComputedStyle(el).color") == "rgb(255, 255, 255)"
    assert page.locator(".cover-role").evaluate("el => getComputedStyle(el).color") == "rgb(239, 237, 230)"
    assert page.locator(".cover-path a").first.evaluate("el => getComputedStyle(el).color") in ["rgb(255, 255, 255)", "rgb(215, 205, 184)"]
    assert height * .59 <= cover["height"] <= height * .70, (cover, height)
    enhanced = page.locator("html").evaluate("el => el.classList.contains('cover-navigation')")
    if enhanced:
        wait_for(page, "!document.documentElement.classList.contains('past-cover') && document.querySelector('.mast').inert")
        assert not page.locator(".mast").is_visible()
        assert abs(page.locator("#main").bounding_box()["y"] - cover["height"]) < 1
        story = page.locator("#home-essay-title").bounding_box()
        assert min(height, story["y"] + story["height"]) - story["y"] >= 60, story
    else:
        assert page.locator(".mast").is_visible()
        assert abs(page.locator(".mast").bounding_box()["y"] - cover["height"]) < 1
    for selector in ["#cover-title", ".cover-role", ".cover-invitation", ".cover-continue"]:
        bounds = page.locator(selector).bounding_box()
        assert bounds["y"] >= 0 and bounds["y"] + bounds["height"] <= cover["height"] + 1, (selector, bounds, height)
    signature = page.locator(".cover-signature").bounding_box()
    width = page.evaluate("innerWidth")
    assert signature["width"] >= (250 if width <= 760 else 330)
    assert signature["y"] <= (20 if width <= 760 else 28) + 1
    assert abs(signature["width"] / signature["height"] - 350 / 148) < .01
    assert signature["y"] + signature["height"] <= cover["height"]
    no_overflow(page)


def body_state(page, target):
    wait_for(page, """target => {
      const header = document.querySelector('.mast').getBoundingClientRect();
      const section = document.getElementById(target).getBoundingClientRect();
      const enhanced = document.documentElement.classList.contains('cover-navigation');
      const pastCover = document.querySelector('.home-cover').getBoundingClientRect().bottom <= 1;
      const visible = getComputedStyle(document.querySelector('.mast')).visibility !== 'hidden';
      const atEnd = Math.abs(scrollY + innerHeight - document.documentElement.scrollHeight) < 2;
      return (!enhanced || (visible === pastCover && document.querySelector('.mast').inert !== pastCover))
        && (!visible || Math.abs(header.top) < 1) && section.top >= (visible ? header.bottom - 1 : 0)
        && (section.top <= header.bottom + 22 || (atEnd && section.top < innerHeight - 160));
    }""", arg=target)
    no_overflow(page)


def focused_is_visible(page):
    assert page.evaluate("""() => {
      const el = document.activeElement;
      return getComputedStyle(el).outlineStyle === 'solid' && [...el.getClientRects()].some(rect => {
        const x = rect.left + rect.width / 2, y = rect.top + rect.height / 2;
        return rect.width > 0 && y >= 0 && y < innerHeight
          && el.contains(document.elementFromPoint(x, y));
      });
    }""")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--browser-channel", default=None)
    parser.add_argument("--browser", choices=["chromium", "webkit"], default="chromium")
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    errors, external, missing, states = [], [], [], []
    with sync_playwright() as p:
        browser = getattr(p, args.browser).launch(**({"channel": args.browser_channel} if args.browser_channel else {}))
        for width, height in [(320, 740), (390, 844), (820, 1180), (1028, 900), (1600, 1000), (1920, 1120)]:
            for javascript in [True, False]:
                print(f"Cover: {width}px / JavaScript {javascript}", flush=True)
                context = browser.new_context(viewport={"width": width, "height": height},
                                              has_touch=width < 900, is_mobile=width < 900,
                                              java_script_enabled=javascript, reduced_motion="reduce")
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda request: external.append(request.url) if not request.url.startswith(args.url) else None)
                page.on("response", lambda response: missing.append(response.url) if response.status >= 400 else None)
                page.goto(args.url, wait_until="networkidle")
                settle(page)
                cover_state(page, height)
                page.locator(".cover-path a").first.focus()
                assert page.locator(".cover-path a").first.evaluate("el => getComputedStyle(el).outlineColor") == "rgb(255, 255, 255)"
                page.locator(".cover-path a").first.hover()
                assert page.locator(".cover-path a").first.evaluate("el => getComputedStyle(el).color") == "rgb(215, 205, 184)"
                page.locator(".cover-path a").first.evaluate("el => el.blur()")
                page.mouse.move(0, 0)
                device = {320: "small-phone", 390: "phone", 1028: "midwidth", 1600: "desktop"}.get(width, str(width))
                capture = javascript and width in [320, 390, 1028, 1600]
                if capture:
                    page.screenshot(path=str(args.artifacts / f"{device}-cover-opening.png"))
                    page.evaluate("scrollTo({top: document.querySelector('.home-cover').offsetHeight - 24, behavior:'instant'})")
                    settle(page)
                    page.screenshot(path=str(args.artifacts / f"{device}-cover-boundary.png"))
                if javascript:
                    original_top = page.locator("#main").evaluate("el => el.offsetTop")
                    page.evaluate("scrollTo({top: document.querySelector('.home-cover').offsetHeight + 2, behavior:'instant'})")
                    wait_for(page, "document.documentElement.classList.contains('past-cover') && !document.querySelector('.mast').inert")
                    assert page.locator(".mast").is_visible()
                    assert page.locator(".mast").bounding_box()["y"] == 0
                    assert page.locator("#main").evaluate("el => el.offsetTop") == original_top
                    if capture:
                        settle(page)
                        page.screenshot(path=str(args.artifacts / f"{device}-header-after-cover.png"))
                    page.locator(".mast nav a").first.focus()
                    focused_is_visible(page)
                page.evaluate("scrollTo({top:0, behavior:'instant'})")
                cover_state(page, height)
                if javascript:
                    assert not page.evaluate("document.querySelector('.mast').contains(document.activeElement)")
                    page.locator(".cover-continue").focus()
                    page.keyboard.press("Tab")
                    assert page.evaluate("document.activeElement.matches('[data-home-title]')")
                    focused_is_visible(page)
                    page.evaluate("scrollTo({top:0, behavior:'instant'})")

                for index, target in enumerate(DESTINATIONS):
                    link = page.locator(".cover-path a").nth(index)
                    if width < 900:
                        link.tap()
                    else:
                        link.focus()
                        page.keyboard.press("Enter")
                    body_state(page, target)
                    settle(page)
                    if capture and target in ["featured-story", "connections"]:
                        label = "story-from-invitation" if target == "featured-story" else "header-over-reading-plate"
                        page.screenshot(path=str(args.artifacts / f"{device}-{label}.png"))
                    page.go_back(wait_until="load")
                    wait_for(page, "scrollY === 0")
                    cover_state(page, height)

                page.locator(".cover-continue").focus()
                page.keyboard.press("Enter")
                body_state(page, "featured-story")
                page.locator("#connections").evaluate("el => el.scrollIntoView({behavior:'instant'})")
                body_state(page, "connections")
                page.locator(".mast nav a").first.focus()
                focused_is_visible(page)
                restored_y = page.evaluate("scrollY")
                page.keyboard.press("Enter")
                page.wait_for_url("**/futurememo/")
                assert page.locator(".mast").evaluate("el => getComputedStyle(el).position") == "static"
                assert not page.locator(".home-cover").count()
                page.go_back(wait_until="networkidle")
                settle(page)
                if javascript:
                    wait_for(page, "y => Math.abs(scrollY - y) < 2", arg=restored_y)
                    body_state(page, "connections")
                else:
                    # Without page scripts, history may restore the URL's native fragment.
                    restored = page.evaluate("y => Math.abs(scrollY - y) < 2", restored_y)
                    body_state(page, "connections" if restored else "featured-story")
                page.locator('.foot a[href="#top"]').click()
                wait_for(page, "scrollY === 0")
                cover_state(page, height)
                if capture:
                    page.screenshot(path=str(args.artifacts / f"{device}-return-to-top.png"))
                for target in DESTINATIONS:
                    page.goto(args.url + "/#" + target, wait_until="networkidle")
                    settle(page)
                    body_state(page, target)
                states.append({"width": width, "javascript": javascript, "coverHeight": page.locator(".home-cover").bounding_box()["height"],
                               "header": "visibility-driven" if javascript else "native-sticky"})
                context.close()

        context = browser.new_context(viewport={"width": 1600, "height": 1120})
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle")
        settle(page)
        page.locator(".cover-continue").click()
        body_state(page, "featured-story")
        for width, height in [(390, 844), (820, 1180), (320, 900), (1920, 1120)]:
            page.set_viewport_size({"width": width, "height": height})
            settle(page)
            wait_for(page, """() => Math.abs(parseFloat(getComputedStyle(document.documentElement)
              .getPropertyValue('--home-header-height')) - document.querySelector('.mast').getBoundingClientRect().height) < 1""")
            page.locator("#connections").evaluate("el => el.scrollIntoView({behavior:'instant'})")
            body_state(page, "connections")
            page.locator('.foot a[href="#top"]').click()
            wait_for(page, "scrollY === 0")
            cover_state(page, height)
        page.keyboard.press("Tab")
        # Focused navigation remains ordinary document navigation, never a hidden clone.
        page.locator(".skip").focus()
        page.keyboard.press("Enter")
        body_state(page, "main")
        page.keyboard.press("Tab")
        focused_is_visible(page)
        context.close()
        for scale in [2, 4]:
            context = browser.new_context(viewport={"width": 1600 // scale, "height": 1120 // scale},
                                          device_scale_factor=scale, reduced_motion="reduce")
            page = context.new_page()
            page.goto(args.url, wait_until="networkidle")
            settle(page)
            no_overflow(page)
            assert page.get_by_role("heading", name="Suff Syed", exact=True).count() == 1
            assert page.locator(".cover-role").inner_text() == ROLE
            page.locator(".cover-continue").click()
            body_state(page, "featured-story")
            page.screenshot(path=str(args.artifacts / f"reflow-{scale * 100}.png"))
            context.close()
        browser.close()
    assert not errors and not missing and not external, (errors, missing, external)
    (args.artifacts / "cover-verification.json").write_text(json.dumps(states, indent=2) + "\n")
    print("PASS: one accessible signature masthead, six widths with/without JS, compact cover/visible story, gap-free header reveal, inert/tab states, keyboard/touch, back/anchors/resize/reflow and no external assets/errors.")


if __name__ == "__main__":
    main()
