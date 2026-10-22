"""Device check: the page on emulated phones, Chromium for Android and WebKit (Safari's engine) for iPhone, light and dark.

For each device profile and colour scheme: load the page, wait for window.mapReady and the map's idle event, then
check there is no sideways scroll, the search field is at least 16px on phones (below that iOS Safari zooms in on
focus), tapping story marker 1 opens Hensbarrow, and searching "Snowdon" + Enter selects Snowdon Summit. Console
errors are recorded. Emulation is not a real device: WebKit here is Playwright's Linux build, which shares Safari's
engine but not iOS itself (no on-screen keyboard, toolbars or the focus zoom), so this narrows what a device test must
cover rather than replacing it.

Rendering uses SwiftShader: on this machine the default headless GPU path leaves a 412px-wide map canvas mostly blank,
which is a headless fault, not the page. Pixel density is 1 to keep software rendering quick; layout and behaviour do
not depend on it. Screenshots of the map go to data/devicecheck/ (gitignored).

Usage:  python -I scripts/check_devices.py [url]       default http://localhost:8766/ (serve site/ first)
Needs:  pip install playwright && python -m playwright install chromium webkit
Writes: results/device_check.json
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import TimeoutError, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "data" / "devicecheck"
DEVICES = {"chromium": ["Pixel 7"], "webkit": ["iPhone 15", "iPhone SE"]}
LAUNCH = {"chromium": {"args": ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"]}, "webkit": {}}
GPU_STALL = "GPU stall due to ReadPixels"
IDLE = "new Promise((r) => { map.once('idle', r); map.triggerRepaint(); })"


def check(browser, profile, scheme, url, name):
    ctx = browser.new_context(**{**profile, "device_scale_factor": 1}, color_scheme=scheme)
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: m.type == "error" and GPU_STALL not in m.text and errors.append(m.text[:200]))
    page.on("pageerror", lambda e: errors.append(str(e)[:200]))
    page.goto(url)
    page.wait_for_function("window.mapReady === true", timeout=120_000)
    page.evaluate(IDLE)
    page.screenshot(path=SHOTS / f"{name}-{scheme}-start.png")
    out = {"viewport": page.viewport_size,
           "sideways_scroll": page.evaluate("document.documentElement.scrollWidth > innerWidth"),
           "search_font_px": page.evaluate("parseFloat(getComputedStyle(document.getElementById('search')).fontSize)")}
    page.locator(".story-marker").first.tap()
    page.wait_for_function("document.getElementById('d-name').textContent.startsWith('Hensbarrow')", timeout=10_000)
    out["story_tap_opens"] = page.locator("#d-name").inner_text()
    page.evaluate(IDLE)
    page.screenshot(path=SHOTS / f"{name}-{scheme}-story.png")
    page.locator("#clear").tap()
    page.wait_for_function("location.hash === ''", timeout=10_000)
    page.locator("#search").fill("Snowdon")
    page.locator("#search").press("Enter")
    try:
        page.wait_for_function("document.getElementById('d-name').textContent.startsWith('Snowdon')", timeout=10_000)
        out["search_snowdon_selects"] = page.locator("#d-name").inner_text()
    except TimeoutError:
        out["search_snowdon_selects"] = "nothing selected"
    out["console_errors"] = errors
    ctx.close()
    return out


def main(url):
    SHOTS.mkdir(parents=True, exist_ok=True)
    results = {"url": url, "note": "emulation, not real devices; pixel density 1; SwiftShader rendering in Chromium"}
    with sync_playwright() as p:
        for engine, names in DEVICES.items():
            browser = getattr(p, engine).launch(**LAUNCH[engine])
            for name in names:
                for scheme in ("light", "dark"):
                    key = f"{engine} / {name} / {scheme}"
                    results[key] = check(browser, p.devices[name], scheme, url, name.replace(" ", "-"))
                    print(key, results[key], flush=True)
            browser.close()
    rows = [v for k, v in results.items() if " / " in k]
    results["all_pass"] = all(not r["sideways_scroll"] and r["search_font_px"] >= 16 and not r["console_errors"]
                              and r["story_tap_opens"].startswith("Hensbarrow")
                              and r["search_snowdon_selects"].startswith("Snowdon") for r in rows)
    (ROOT / "results" / "device_check.json").write_text(json.dumps(results, indent=2) + "\n")
    print("all_pass:", results["all_pass"])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8766/")
