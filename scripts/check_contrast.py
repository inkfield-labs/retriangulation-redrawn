"""Basemap contrast: WCAG 2.2 contrast ratios of the basemap colours the page uses, light and dark.

Reads OpenFreeMap's positron (light) and dark styles and applies the dark-mode colours that site/app.js sets
(DARK_PAINT, mirrored below). Text should reach 4.5:1 (WCAG 1.4.3, AA). Land against sea has no WCAG threshold, as the
basemap is context rather than content; the target is the light map's own separation.

Usage:  python -I scripts/check_contrast.py
Writes: results/basemap_contrast.json
"""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLES = "https://tiles.openfreemap.org/styles/"
# mirrors DARK_PAINT and the place_* label colour in site/app.js
DARK = {"sea": "rgb(28,52,90)", "water_label": "rgb(150,180,220)", "road_label": "rgb(150,150,150)",
        "place_label": "rgb(176,176,176)"}


def rgb(css):
    if css.startswith("#"):
        h = css[1:] if len(css) == 7 else "".join(c * 2 for c in css[1:4])
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(v) for v in re.findall(r"\d+", css)[:3])


def luminance(c):
    f = lambda v: v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(v / 255) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    hi, lo = sorted((luminance(rgb(a)), luminance(rgb(b))), reverse=True)
    return round((hi + 0.05) / (lo + 0.05), 2)


def paint(style, layer, prop):
    return next(l["paint"][prop] for l in style["layers"] if l["id"] == layer)


def main():
    get = lambda name: json.load(urllib.request.urlopen(urllib.request.Request(
        STYLES + name, headers={"User-Agent": "retriangulation-redrawn contrast check"}), timeout=30))
    light, dark = get("positron"), get("dark")
    land_l, land_d = paint(light, "background", "background-color"), paint(dark, "background", "background-color")
    out = {
        "light": {"land": land_l, "sea": paint(light, "water", "fill-color"),
                  "land_vs_sea": ratio(land_l, paint(light, "water", "fill-color")),
                  "town_label": ratio(paint(light, "label_town", "text-color"), land_l),
                  "road_label": ratio(paint(light, "highway-name-major", "text-color"), land_l)},
        "dark_as_published": {"land": land_d, "sea": paint(dark, "water", "fill-color"),
                              "land_vs_sea": ratio(land_d, paint(dark, "water", "fill-color")),
                              "place_label": ratio(paint(dark, "place_town", "text-color"), land_d),
                              "road_label": ratio(paint(dark, "highway_name_other", "text-color"), land_d)},
        "dark_as_used": {"land": land_d, **DARK, "land_vs_sea": ratio(land_d, DARK["sea"]),
                         "place_label": ratio(DARK["place_label"], land_d),
                         "place_label_over_sea": ratio(DARK["place_label"], DARK["sea"]),
                         "water_label_over_sea": ratio(DARK["water_label"], DARK["sea"]),
                         "road_label": ratio(DARK["road_label"], land_d)},
        "targets": {"text": 4.5, "land_vs_sea": "at least the light map's"},
    }
    used = out["dark_as_used"]
    out["dark_passes"] = (min(used[k] for k in ("place_label", "place_label_over_sea", "water_label_over_sea",
                                                 "road_label")) >= 4.5
                          and used["land_vs_sea"] >= out["light"]["land_vs_sea"])
    (ROOT / "results" / "basemap_contrast.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
