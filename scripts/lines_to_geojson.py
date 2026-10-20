"""Write visible lines from results/region_lines.csv as WGS84 GeoJSON for tiling.

Usage:  python -I scripts/lines_to_geojson.py data/trig/x/CompleteTrigArchive.csv out.geojson [max_km]
"""
import json
import sys
from pathlib import Path

import pandas as pd
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))

from region_prototype import ROOT, pillars  # noqa: E402


def main(trig_csv, out, max_km=100):
    p = pillars(trig_csv).set_index("STATION NAME")
    lines = pd.read_csv(ROOT / "results" / "region_lines.csv")
    lines = lines[(lines.clear_k013 > 0) & (lines.dist_km <= float(max_km))]
    tr = Transformer.from_crs(27700, 4326, always_xy=True)
    lon_a, lat_a = tr.transform(p.loc[lines.a, "EASTING"].values, p.loc[lines.a, "NORTHING"].values)
    lon_b, lat_b = tr.transform(p.loc[lines.b, "EASTING"].values, p.loc[lines.b, "NORTHING"].values)
    feats = [{"type": "Feature", "properties": {"a": a, "b": b, "km": float(km)},
              "geometry": {"type": "LineString", "coordinates": [[round(x1, 5), round(y1, 5)],
                                                                 [round(x2, 5), round(y2, 5)]]}}
             for a, b, km, x1, y1, x2, y2 in zip(lines.a, lines.b, lines.dist_km, lon_a, lat_a, lon_b, lat_b)]
    with open(out, "w") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f, separators=(",", ":"))
    print(f"{len(feats)} lines -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:])
