"""Build the data files the static map page in site/ reads, from the full GB run (data/gb_lines.csv).

Usage:  TIPPECANOE=/path/to/tippecanoe python -I scripts/build_site.py data/trig/x/CompleteTrigArchive.csv
Reads:  data/gb_lines.csv and data/gb_lines_long.csv (visible over Terrain 50, <=250 km),
        data/gb_surface.csv (GLO-30 clearance per line), results/rays_then_now.csv
Writes (gitignored): site/data/pillars.geojson   standing pillars with id, name, height, visible-partner counts
                                                 (n over the terrain, s also clear on the surface model)
                     site/data/partners/<id>.json  [[partner id, km, surface clear 0/1], ...] nearest first
                     site/data/lines.pmtiles     every visible line at k = 0.13 (properties: km, s)
                     site/data/rays.geojson      the reciprocal 1936-62 rays with their then-and-now state
                     site/data/longest.json      the 10 longest visible lines: [[id a, id b, km, surface clear], ...]
                     results/site_build.json     the counts above and file sizes (committed)
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
    lines = pd.concat([pd.read_csv(ROOT / "data" / f) for f in ("gb_lines.csv", "gb_lines_long.csv")],
                      ignore_index=True)
    surface = pd.read_csv(ROOT / "data" / "gb_surface.csv")
    lines = lines.merge(surface, on=["a", "b"], how="left", validate="one_to_one")
    assert lines.clear_glo30.notna().all(), "data/gb_surface.csv is missing lines; rerun glo30_gb.py run"
    lines["s"] = (lines.clear_glo30 > 0).astype(int)
    lines["ia"], lines["ib"] = lines.a.map(pid), lines.b.map(pid)

    tr = Transformer.from_crs(27700, 4326, always_xy=True)
    lon, lat = tr.transform(p.EASTING.values, p.NORTHING.values)
    both = pd.concat([lines[["ia", "ib", "dist_km", "s"]].set_axis(["id", "other", "km", "s"], axis=1),
                      lines[["ib", "ia", "dist_km", "s"]].set_axis(["id", "other", "km", "s"], axis=1)])
    counts = both.id.value_counts()
    clear = both[both.s == 1].id.value_counts()

    (OUT / "partners").mkdir(parents=True, exist_ok=True)
    feats = []
    for r, x, y in zip(p.itertuples(), lon, lat):
        feats.append({"type": "Feature", "id": len(feats),
                      "geometry": {"type": "Point", "coordinates": [round(x, 5), round(y, 5)]},
                      "properties": {"id": r.id, "name": r._1, "h": round(float(r.HEIGHT), 1),
                                     "n": int(counts.get(r.id, 0)), "s": int(clear.get(r.id, 0))}})
    (OUT / "pillars.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                    separators=(",", ":")))
    for i, g in both.sort_values(["id", "km"]).groupby("id"):
        (OUT / "partners" / f"{i}.json").write_text(json.dumps(list(zip(g.other, g.km.round(1), g.s.tolist())),
                                                               separators=(",", ":")))

    # lines GeoJSON for tiling: km and surface flag only; the page draws a selected pillar's lines from its
    # partners file
    pos = dict(zip(p.id, zip(lon, lat)))
    src = ROOT / "data" / "site_lines.geojson"
    with open(src, "w") as f:
        for a, b, km, s in zip(lines.ia, lines.ib, lines.dist_km, lines.s):
            (xa, ya), (xb, yb) = pos[a], pos[b]
            f.write(json.dumps({"type": "Feature", "properties": {"km": km, "s": int(s)}, "geometry": {
                "type": "LineString", "coordinates": [[round(xa, 5), round(ya, 5)], [round(xb, 5), round(yb, 5)]]}},
                separators=(",", ":")) + "\n")
    subprocess.run([os.environ.get("TIPPECANOE", "tippecanoe"), "-o", str(OUT / "lines.pmtiles"), "--force",
                    "-l", "sightlines", "-Z4", "-z12", "--drop-densest-as-needed",
                    "--extend-zooms-if-still-dropping", "-q", str(src)], check=True)

    top10 = lines.nlargest(10, "dist_km")
    (OUT / "longest.json").write_text(json.dumps(
        [[a, b, km, int(sc)] for a, b, km, sc in zip(top10.ia, top10.ib, top10.dist_km.round(1), top10.s)],
        separators=(",", ":")))

    # historical rays; their ends may be non-pillar marks, so each feature carries its own coordinates
    rays = pd.read_csv(ROOT / "results" / "rays_then_now.csv")
    ra = tr.transform(rays.a_e.values, rays.a_n.values)
    rb = tr.transform(rays.b_e.values, rays.b_n.values)
    feats = [{"type": "Feature", "properties": {
                  "a": pid(r.a), "b": pid(r.b), "an": r.a_name, "bn": r.b_name, "km": r.dist_km, "st": r.state},
              "geometry": {"type": "LineString", "coordinates": [[round(xa, 5), round(ya, 5)],
                                                                 [round(xb, 5), round(yb, 5)]]}}
             for r, xa, ya, xb, yb in zip(rays.itertuples(), *ra, *rb)]
    (OUT / "rays.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                 separators=(",", ":")))
    top = counts.idxmax()
    summary = {"pillars": len(p), "lines": len(lines), "surface_clear": int(lines.s.sum()),
               "pillars_with_partners": int(counts.size), "rays": len(rays),
               "longest": [{"a": a, "b": b, "km": km, "surface_clear": int(sc)} for a, b, km, sc in
                           zip(top10.a_name, top10.b_name, top10.dist_km, top10.s)],
               "most_partners": {"id": top, "name": p.set_index("id").loc[top, "Trig Name"],
                                 "partners": int(counts.max()), "surface_clear": int(clear.get(top, 0))},
               "bytes": {f.name: f.stat().st_size for f in (OUT / "lines.pmtiles", OUT / "pillars.geojson",
                                                             OUT / "rays.geojson")}}
    (ROOT / "results" / "site_build.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
