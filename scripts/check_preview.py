"""Preview check: one cold load of each URL in headless Chromium, recording what the tile server and page did.

Waits for window.mapReady and the map's idle event, then counts the tile (.pmtiles) requests with their statuses and
whether each carried Content-Range, the line features rendered, the console errors and the X-Robots-Tag of the page.
Headless Chromium's "GPU stall due to ReadPixels" driver warnings (caused by the feature query below) are not counted
as errors; their number is recorded separately as gpu_stall_warnings_filtered.

Usage:  python -I scripts/check_preview.py URL [URL ...]      (e.g. the pages.dev URL and http://localhost:8766/)
Needs:  pip install playwright && python -m playwright install --only-shell chromium
Writes: results/preview_check.json (one entry per URL)
"""
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
GPU_STALL = "GPU stall due to ReadPixels"


def check(browser, url):
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    tiles, errors, filtered, robots = [], [], 0, {}

    def on_console(m):
        nonlocal filtered
        if GPU_STALL in m.text:
            filtered += 1
        elif m.type in ("error", "warning"):
            errors.append(m.text)

    def on_response(r):
        if urlparse(r.url).path.endswith(".pmtiles"):
            tiles.append({"status": r.status, "content_range": r.headers.get("content-range") is not None})
        if r.url == url:
            robots["x_robots_tag"] = r.headers.get("x-robots-tag")

    page.on("console", on_console)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("requestfailed", lambda r: errors.append(f"requestfailed: {r.url}"))
    page.on("response", on_response)
    page.goto(url)
    page.wait_for_function("window.mapReady === true", timeout=120_000)
    page.evaluate("new Promise((r) => { map.once('idle', r); map.triggerRepaint(); })")
    lines = page.evaluate("map.queryRenderedFeatures({layers: ['lines']}).length")
    page.close()
    statuses = {}
    for t in tiles:
        statuses[str(t["status"])] = statuses.get(str(t["status"]), 0) + 1
    return {"tile_requests": len(tiles), "tile_statuses": statuses,
            "tile_requests_with_content_range": sum(t["content_range"] for t in tiles),
            "rendered_line_features": lines, "console_errors": len(errors), "console_error_messages": errors,
            "gpu_stall_warnings_filtered": filtered, "gpu_stall_filter": GPU_STALL,
            "x_robots_tag": robots.get("x_robots_tag")}


def main(urls):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        out = {url: check(browser, url) for url in urls}
        browser.close()
    (ROOT / "results" / "preview_check.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:] or sys.exit(__doc__))
