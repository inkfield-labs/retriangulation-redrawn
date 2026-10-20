"""GB-scale compute and output estimate.

Counts every pair of standing pillars within 50, 100 and 150 km, the profile samples those pairs need on the 50 m
grid, and the wall-clock time at the measured throughput. Runs LOS on a random sample of pairs at each range to
estimate how many lines are visible across GB.

Usage:  python -I scripts/gb_extrapolate.py data/trig/x/CompleteTrigArchive.csv [sample_pairs]
Writes: results/gb_extrapolation.json
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from los import DEM, clearance, station_heights  # noqa: E402
from region_prototype import pillars  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main(trig_csv, n_sample=200_000):
    p = pillars(trig_csv)
    e, n = p.EASTING.values, p.NORTHING.values
    dem = DEM()
    z, _ = station_heights(p.HEIGHT.values, p.COMMENTS.values, dem.sample(e, n))
    tree = cKDTree(np.c_[e, n])
    pairs = tree.query_pairs(150_000, output_type="ndarray")
    d = np.hypot(e[pairs[:, 0]] - e[pairs[:, 1]], n[pairs[:, 0]] - n[pairs[:, 1]])
    rng = np.random.default_rng(1)
    out = {"pillars": len(p), "dem_cell_m": dem.cell, "by_range": {}}
    for r in (50, 100, 150):
        m = d <= r * 1000
        samples = int(np.ceil(d[m] / dem.cell).sum())
        idx = rng.choice(np.flatnonzero(m), size=min(n_sample, int(m.sum())), replace=False)
        a, b = pairs[idx, 0], pairs[idx, 1]
        s = int(np.ceil(d[idx] / dem.cell).sum())
        t0 = time.time()
        c = clearance(dem, e[a], n[a], z[a], e[b], n[b], z[b], k=0.13, skip=100.0)
        dt = time.time() - t0
        frac = float((c > 0).mean())
        rate = s / dt
        out["by_range"][str(r)] = {
            "pairs": int(m.sum()), "profile_samples": samples, "mean_pair_km": round(float(d[m].mean()) / 1000, 1),
            "sampled_pairs": len(idx), "sample_seconds": round(dt, 1), "samples_per_second": round(rate),
            "estimated_full_run_hours": round(samples / rate / 3600, 2),
            "visible_fraction_in_sample": round(frac, 4),
            "estimated_visible_lines": round(frac * int(m.sum())),
        }
        print(r, out["by_range"][str(r)], flush=True)
    (ROOT / "results" / "gb_extrapolation.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(sys.argv[1], *(int(x) for x in sys.argv[2:]))
