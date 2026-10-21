"""Build the data files the static map page in site/ reads, from the full GB run (data/gb_lines.csv).

Usage:  TIPPECANOE=/path/to/tippecanoe python -I scripts/build_site.py data/trig/x/CompleteTrigArchive.csv
Writes (gitignored): site/data/pillars.geojson   standing pillars with id, name, height, visible-partner count
                     site/data/partners/<id>.json  [[partner id, km], ...] nearest first, one file per pillar
                     site/data/lines.pmtiles     every visible line <=150 km at k = 0.13 (property: km)
Pillar id = OS station name with "/" replaced by "-" (e.g. SW63-T16), unique and stable across rebuilds.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from region_prototype import pillars  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "data"


def pid(station):
    return station.replace("/", "-")


def main(trig_csv):
    p = pillars(trig_csv)
    p["id"] = p["STATION NAME"].map(pid)
    assert p.id.is_unique and not p["STATION NAME"].str.contains("-").any()
    lines = pd.read_csv(ROOT / "data" / "gb_lines.csv")
    lines["ia"], lines["ib"] = lines.a.map(pid), lines.b.map(pid)

    tr = Transformer.from_crs(27700, 4326, always_xy=True)
    lon, lat = tr.transform(p.EASTING.values, p.NORTHING.values)
    both = pd.concat([lines[["ia", "ib", "dist_km"]].set_axis(["id", "other", "km"], axis=1),
                      lines[["ib", "ia", "dist_km"]].set_axis(["id", "other", "km"], axis=1)])
    counts = both.id.value_counts()

    (OUT / "partners").mkdir(parents=True, exist_ok=True)
    feats = []
    for r, x, y in zip(p.itertuples(), lon, lat):
        feats.append({"type": "Feature", "id": len(feats),
                      "geometry": {"type": "Point", "coordinates": [round(x, 5), round(y, 5)]},
                      "properties": {"id": r.id, "name": r._1, "h": round(float(r.HEIGHT), 1),
                                     "n": int(counts.get(r.id, 0))}})
    (OUT / "pillars.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                    separators=(",", ":")))
    for i, g in both.sort_values(["id", "km"]).groupby("id"):
        (OUT / "partners" / f"{i}.json").write_text(json.dumps(list(zip(g.other, g.km.round(1))),
                                                               separators=(",", ":")))

    # lines GeoJSON for tiling: km only, the page draws a selected pillar's lines from its partners file
    pos = dict(zip(p.id, zip(lon, lat)))
    src = ROOT / "data" / "site_lines.geojson"
    with open(src, "w") as f:
        for a, b, km in zip(lines.ia, lines.ib, lines.dist_km):
            (xa, ya), (xb, yb) = pos[a], pos[b]
            f.write(json.dumps({"type": "Feature", "properties": {"km": km}, "geometry": {
                "type": "LineString", "coordinates": [[round(xa, 5), round(ya, 5)], [round(xb, 5), round(yb, 5)]]}},
                separators=(",", ":")) + "\n")
    subprocess.run([os.environ.get("TIPPECANOE", "tippecanoe"), "-o", str(OUT / "lines.pmtiles"), "--force",
                    "-l", "sightlines", "-Z4", "-z12", "--drop-densest-as-needed",
                    "--extend-zooms-if-still-dropping", "-q", str(src)], check=True)
    print(f"{len(p)} pillars, {len(lines)} lines, {counts.size} pillars with partners")


if __name__ == "__main__":
    main(sys.argv[1])
