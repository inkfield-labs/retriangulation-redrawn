"""Full GB run: LOS for every pair of standing pillars within 150 km, at k = 0.13.

Runs in shards so each piece fits in a short process and the run can resume:
    python -I scripts/gb_full_run.py data/trig/x/CompleteTrigArchive.csv shard <i> <n>   # repeat for i = 0..n-1
    python -I scripts/gb_full_run.py data/trig/x/CompleteTrigArchive.csv finalize <n>
Writes: data/gb_shards/ (per-shard clearance and timing), data/gb_lines.csv (visible lines, gitignored),
        data/gb_lines.geojson (WGS84, for tiling), results/gb_full_run.json (timings and counts)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from los import DEM, clearance, station_heights  # noqa: E402
from region_prototype import pillars  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


SHARDS = ROOT / "data" / "gb_shards"


def setup(trig_csv):
    p = pillars(trig_csv)
    e, n = p.EASTING.values, p.NORTHING.values
    dem = DEM()
    z, _ = station_heights(p.HEIGHT.values, p.COMMENTS.values, dem.sample(e, n))
    pairs = cKDTree(np.c_[e, n]).query_pairs(150_000, output_type="ndarray")
    pairs = pairs[np.lexsort((pairs[:, 1], pairs[:, 0]))]  # deterministic order across processes
    return p, e, n, z, dem, pairs


def shard(trig_csv, i, nshards):
    p, e, n, z, dem, pairs = setup(trig_csv)
    part = np.array_split(np.arange(len(pairs)), nshards)[i]
    a, b = pairs[part, 0], pairs[part, 1]
    t0 = time.time()
    c = clearance(dem, e[a], n[a], z[a], e[b], n[b], z[b], k=0.13, skip=100.0)
    SHARDS.mkdir(exist_ok=True)
    np.save(SHARDS / f"clear_{i}_of_{nshards}.npy", c.astype(np.float32))
    (SHARDS / f"time_{i}_of_{nshards}.json").write_text(json.dumps({"pairs": len(part), "seconds": time.time() - t0}))
    print(f"shard {i}/{nshards}: {len(part)} pairs in {time.time() - t0:.0f} s")


def finalize(trig_csv, nshards):
    t_all = time.time()
    p, e, n, z, dem, pairs = setup(trig_csv)
    a, b = pairs[:, 0], pairs[:, 1]
    c = np.concatenate([np.load(SHARDS / f"clear_{i}_of_{nshards}.npy") for i in range(nshards)])
    t_los = sum(json.loads((SHARDS / f"time_{i}_of_{nshards}.json").read_text())["seconds"] for i in range(nshards))
    d = np.hypot(e[a] - e[b], n[a] - n[b]) / 1000
    vis = c > 0
    lines = pd.DataFrame({"a": p["STATION NAME"].values[a[vis]], "b": p["STATION NAME"].values[b[vis]],
                          "a_name": p["Trig Name"].values[a[vis]], "b_name": p["Trig Name"].values[b[vis]],
                          "dist_km": np.round(d[vis], 2), "clearance_m": np.round(c[vis], 1),
                          "a_e": e[a[vis]], "a_n": n[a[vis]], "b_e": e[b[vis]], "b_n": n[b[vis]]})
    lines.to_csv(ROOT / "data" / "gb_lines.csv", index=False)

    tr = Transformer.from_crs(27700, 4326, always_xy=True)
    lon_a, lat_a = tr.transform(lines.a_e.values, lines.a_n.values)
    lon_b, lat_b = tr.transform(lines.b_e.values, lines.b_n.values)
    with open(ROOT / "data" / "gb_lines.geojson", "w") as f:
        f.write('{"type":"FeatureCollection","features":[\n')
        for i in range(len(lines)):
            feat = {"type": "Feature", "properties": {"a": lines.a.iat[i], "b": lines.b.iat[i],
                                                      "km": float(lines.dist_km.iat[i])},
                    "geometry": {"type": "LineString", "coordinates": [[round(lon_a[i], 5), round(lat_a[i], 5)],
                                                                       [round(lon_b[i], 5), round(lat_b[i], 5)]]}}
            f.write(("," if i else "") + json.dumps(feat, separators=(",", ":")) + "\n")
        f.write("]}\n")

    longest = lines.sort_values("dist_km", ascending=False).head(10)
    deg = pd.concat([lines.a, lines.b]).value_counts()
    out = {
        "pillars": len(p), "pairs_le_150km": len(pairs), "los_seconds_sum_of_shards": round(t_los, 1),
        "finalize_seconds": round(time.time() - t_all, 1), "shards": nshards,
        "visible": {str(r): int((lines.dist_km <= r).sum()) for r in (50, 100, 150)},
        "pillars_with_no_visible_partner": int(len(p) - deg.size),
        "median_visible_partners": float(deg.reindex(p["STATION NAME"], fill_value=0).median()),
        "longest": longest[["a_name", "b_name", "dist_km", "clearance_m"]].to_dict("records"),
        "geojson_bytes": (ROOT / "data" / "gb_lines.geojson").stat().st_size,
    }
    (ROOT / "results" / "gb_full_run.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    if sys.argv[2] == "shard":
        shard(sys.argv[1], int(sys.argv[3]), int(sys.argv[4]))
    else:
        finalize(sys.argv[1], int(sys.argv[3]))
