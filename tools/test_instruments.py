"""Integration checks for optional, local-only question instruments."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

KEY = "suff-journal-reader-marks-v1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1080})
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle")
        assert page.locator("[data-margin-axis]").count() == 3
        assert not page.locator(".perspective-disclosure").evaluate("el => el.open")
        page.locator(".perspective-disclosure > summary").focus()
        page.keyboard.press("Enter")
        assert page.evaluate(f"localStorage.getItem({json.dumps(KEY)})") is None
        axis = page.locator("[data-margin-axis] input[type=range]").first
        axis.focus()
        page.keyboard.press("End")
        assert page.evaluate(f"localStorage.getItem({json.dumps(KEY)})") is not None
        saved = page.evaluate(f"localStorage.getItem({json.dumps(KEY)})")
        page.reload(wait_until="networkidle")
        page.locator(".perspective-disclosure > summary").click()
        assert page.evaluate(f"localStorage.getItem({json.dumps(KEY)})") == saved
        page.locator("[data-margin-reset]").click()
        page.reload(wait_until="networkidle")
        page.locator(".perspective-disclosure > summary").click()
        assert "No mark" in page.locator("[data-margin-output]").first.inner_text()

        for corrupt in ["not-json", '{"x":2}', "[null]", "[101,null,null]", '["50",null,null]', "[0.5,null,null]"]:
            page.evaluate("([key,value]) => localStorage.setItem(key,value)", [KEY, corrupt])
            page.reload(wait_until="networkidle")
            page.locator(".perspective-disclosure > summary").click()
            notice = page.locator("[data-margin-notice]").inner_text()
            assert notice, corrupt
            assert page.locator("[data-storage-problem]").count(), corrupt
            page.locator("[data-margin-reset]").click()
            assert page.evaluate(f"localStorage.getItem({json.dumps(KEY)})") is None

        denied = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True)
        denied.add_init_script("""Object.defineProperty(window, 'localStorage', {get() { throw new DOMException('Denied for test', 'SecurityError'); }});""")
        view = denied.new_page()
        view.goto(args.url, wait_until="networkidle")
        view.locator(".perspective-disclosure > summary").tap()
        assert view.locator("[data-storage-problem]").count()
        view.locator("[data-margin-middle]").first.tap()
        assert view.locator("[data-margin-notice]").inner_text()
        view.locator("[data-margin-reset]").tap()
        denied.close()

        page.goto(args.url + "/research/", wait_until="networkidle")
        page.locator("[data-research-start]").click()
        page.locator("[data-research-pause]").click()
        paused = page.locator("[data-research-log]:visible").all_inner_texts()
        page.wait_for_timeout(2300)
        assert page.locator("[data-research-log]:visible").all_inner_texts() == paused
        page.locator("[data-research-resume]").click()
        page.wait_for_timeout(120)
        page.locator("[data-research-pause]").click()
        # Deterministic manual stepping exposes the same authored artifact.
        for _ in range(8):
            if page.locator("[data-research-artifact]").is_visible():
                break
            step = page.locator("[data-research-step]")
            if not step.is_enabled():
                break
            step.click()
        assert page.locator("[data-research-artifact]").is_visible()
        assert page.locator("#research-sample").inner_text()
        page.screenshot(path=str(args.artifacts / "research-result-desktop.png"), full_page=True)
        page.locator("[data-research-reset]").click()
        assert not page.locator("[data-research-artifact]").is_visible()
        assert page.locator("[data-research-start]").is_visible()
        page.locator("[data-research-start]").click()
        page.locator("[data-research-artifact]").wait_for(state="visible", timeout=20000)
        page.locator("[data-research-reset]").click()

        reduced = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, reduced_motion="reduce")
        view = reduced.new_page()
        view.goto(args.url, wait_until="networkidle")
        assert view.locator(".running-ring").evaluate_all("els => els.every(el => getComputedStyle(el).animationName === 'none' || getComputedStyle(el).animationPlayState === 'paused')")
        view.goto(args.url + "/research/", wait_until="networkidle")
        view.locator("[data-research-start]").tap()
        for _ in range(8):
            if view.locator("[data-research-artifact]").is_visible():
                break
            view.locator("[data-research-step]").tap()
        assert view.locator("[data-research-artifact]").is_visible()
        view.screenshot(path=str(args.artifacts / "research-result-phone.png"), full_page=True)
        reduced.close()
        browser.close()
    print("PASS: browser-only opt-in marks, keyboard/touch, corrupt/denied storage, reset, research pause/resume/steps/result/reset, reduced motion.")


if __name__ == "__main__":
    import re
    main()
