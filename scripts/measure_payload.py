"""Payload budget: bytes a first visit downloads before the first tap, on throttled 4G with a cold cache.

Loads the page in headless Chromium at phone and desktop sizes, waits for the page's data (window.mapReady) and then
for the map to go idle, and sums the bytes received per request. Throttling is Lighthouse's mobile profile: 150 ms
round trip, 1.6 Mbit/s down, 750 kbit/s up. The local server (http-server) sends files uncompressed, so for this
site's own text files the gzip size is also reported: that is what a host such as Cloudflare Pages would send.
That adjustment is skipped for any other host, which already compresses.

Usage:  python -I scripts/measure_payload.py [url [out.json]]
        defaults: http://localhost:8766/ (serve site/ first) and results/payload.json
Needs:  pip install playwright && python -m playwright install --only-shell chromium
Writes: results/payload.json, or the given out.json (e.g. results/payload_preview.json for the preview)
"""
import gzip
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
THROTTLE = {"offline": False, "latency": 150, "downloadThroughput": 1_638_400 / 8, "uploadThroughput": 750_000 / 8}
VIEWPORTS = {"phone": (390, 844), "desktop": (1280, 800)}
TEXT = (".html", ".css", ".js", ".json", ".geojson")


def kind(url, site):
    u = urlparse(url)
    if u.netloc == site:
        return "data" if u.path.startswith("/data/") else "page"
    if "unpkg.com" in u.netloc:
        return "libraries"
    if u.netloc.endswith(".r2.dev"):
        return "tiles"
    if "openfreemap" in u.netloc:
        return "basemap"
    return "other"


def local_gzip(url):
    """gzip size of a site/ text file, as a compressing host would send it; None if not a local text file."""
    u = urlparse(url)
    if u.hostname not in ("localhost", "127.0.0.1"):
        return None
    path = u.path
    path = "/index.html" if path == "/" else path
    f = ROOT / "site" / path.lstrip("/")
    if not path.endswith(TEXT) or not f.is_file():
        return None
    return len(gzip.compress(f.read_bytes(), 6))


def measure(browser, url, size):
    ctx = browser.new_context(viewport=dict(zip(("width", "height"), size)))
    page = ctx.new_page()
    cdp = ctx.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
    cdp.send("Network.emulateNetworkConditions", THROTTLE)
    urls, done = {}, {}
    cdp.on("Network.requestWillBeSent", lambda e: urls.__setitem__(e["requestId"], e["request"]["url"]))
    cdp.on("Network.loadingFinished", lambda e: done.__setitem__(e["requestId"], e["encodedDataLength"]))
    t0 = time.time()
    page.goto(url)
    page.wait_for_function("window.mapReady === true", timeout=120_000)
    t_ready = time.time() - t0
    # idle = style, sources and tiles loaded and rendered; a repaint makes sure the event fires
    page.evaluate("new Promise((r) => { map.once('idle', r); map.triggerRepaint(); })")
    t_idle = time.time() - t0
    site = urlparse(url).netloc
    rows = [(urls.get(i, "?"), n) for i, n in done.items()]
    by_kind, gz_saving = {}, 0
    for u, n in rows:
        k = kind(u, site)
        by_kind[k] = by_kind.get(k, 0) + n
        g = local_gzip(u)
        if g is not None and g < n:
            gz_saving += n - g
    total = sum(n for _, n in rows)
    ctx.close()
    return {"viewport": list(size), "requests": len(rows), "tile_requests": sum(kind(u, site) == "tiles" for u, _ in rows),
            "bytes": total, "bytes_by_kind": by_kind,
            "bytes_if_site_text_gzipped": total - gz_saving, "seconds_to_data_ready": round(t_ready, 1),
            "seconds_to_map_idle": round(t_idle, 1),
            "largest": [{"url": urlparse(u)._replace(query="").geturl(), "bytes": n}
                        for u, n in sorted(rows, key=lambda r: -r[1])[:8]]}


def main(url, out_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        out = {"url": url, "throttle": {"rtt_ms": 150, "down_mbit_s": 1.6, "up_mbit_s": 0.75}, "cache": "cold",
               "budget_bytes": 3_000_000, "chromium": browser.version}
        for name, size in VIEWPORTS.items():
            out[name] = measure(browser, url, size)
        browser.close()
    Path(out_path).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8766/",
         sys.argv[2] if len(sys.argv) > 2 else ROOT / "results" / "payload.json")
