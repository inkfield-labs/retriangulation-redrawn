"""Long lines: LOS for every pair of standing pillars more than 150 km and up to 250 km apart, at k = 0.13.

Same model as scripts/gb_full_run.py. Most long pairs cannot be visible, so they are pruned first with a bound that
cannot reject a visible pair: every terrain sample is at least hmin (the grid minimum, less 1 m), so the clearance at
each of los.clearance's sample points is at most
    f(x) = za + (zb - za) x / D - hmin - x (D - x) / (2 Reff).
f is convex in x, so its smallest value over the samples is at the sample nearest the continuous minimum or a
neighbour. A pair is pruned when that value is below zero. A random 20,000 pruned pairs are re-run in full as a check.

Usage:  python -I scripts/gb_long_run.py data/trig/x/CompleteTrigArchive.csv
Writes: data/gb_lines_long.csv (visible lines, gb_lines.csv columns, gitignored), results/gb_long_run.json
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from los import DEM, R_EARTH, clearance, station_heights  # noqa: E402
from region_prototype import pillars  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
K, SKIP, LO, HI = 0.13, 100.0, 150_000, 250_000


def bound(dem, hmin, ea, na, za, eb, nb, zb):
    """Upper bound on clearance at the worst sample of los.clearance, per pair (vectorised)."""
    D = np.hypot(eb - ea, nb - na)
    n = np.maximum(np.ceil(D / dem.cell).astype(np.int64), 1)
    reff = R_EARTH / (1.0 - K)
    # kept samples are j in [jlo, jhi]: x = (j + 0.5) / n * D with x > SKIP and D - x > SKIP
    jlo = np.floor(SKIP * n / D - 0.5).astype(np.int64) + 1
    jhi = np.ceil((D - SKIP) * n / D - 0.5).astype(np.int64) - 1
    xstar = D / 2 - reff * (zb - za) / D
    jstar = np.clip(np.round(xstar * n / D - 0.5).astype(np.int64), jlo, jhi)
    best = np.full(D.shape, np.inf)
    for dj in (-1, 0, 1):
        j = np.clip(jstar + dj, jlo, jhi)
        x = (j + 0.5) / n * D
        best = np.minimum(best, za + (zb - za) * x / D - hmin - x * (D - x) / (2 * reff))
    return best


def main(trig_csv):
    t0 = time.time()
    p = pillars(trig_csv)
    e, n = p.EASTING.values, p.NORTHING.values
    dem = DEM()
    hmin = float(dem.z.min()) * dem.scale - 1.0
    z, _ = station_heights(p.HEIGHT.values, p.COMMENTS.values, dem.sample(e, n))
    pairs = cKDTree(np.c_[e, n]).query_pairs(HI, output_type="ndarray")
    a, b = pairs[:, 0], pairs[:, 1]
    d = np.hypot(e[a] - e[b], n[a] - n[b])
    long_ = d > LO
    a, b, d = a[long_], b[long_], d[long_]
    order = np.lexsort((b, a))  # deterministic
    a, b, d = a[order], b[order], d[order]

    ub = bound(dem, hmin, e[a], n[a], z[a], e[b], n[b], z[b])
    keep = ub >= 0
    t_los = time.time()
    c = clearance(dem, e[a[keep]], n[a[keep]], z[a[keep]], e[b[keep]], n[b[keep]], z[b[keep]], k=K, skip=SKIP)
    t_los = time.time() - t_los

    pruned = np.flatnonzero(~keep)
    check = np.random.default_rng(0).choice(pruned, size=min(20_000, pruned.size), replace=False)
    cc = clearance(dem, e[a[check]], n[a[check]], z[a[check]], e[b[check]], n[b[check]], z[b[check]], k=K, skip=SKIP)
    assert (cc <= 0).all(), "pruning rejected a visible pair"

    ka, kb, kd = a[keep], b[keep], d[keep] / 1000
    vis = c > 0
    lines = pd.DataFrame({"a": p["STATION NAME"].values[ka[vis]], "b": p["STATION NAME"].values[kb[vis]],
                          "a_name": p["Trig Name"].values[ka[vis]], "b_name": p["Trig Name"].values[kb[vis]],
                          "dist_km": np.round(kd[vis], 2), "clearance_m": np.round(c[vis], 1),
                          "a_e": e[ka[vis]], "a_n": n[ka[vis]], "b_e": e[kb[vis]], "b_n": n[kb[vis]]})
    lines.to_csv(ROOT / "data" / "gb_lines_long.csv", index=False)

    both = pd.concat([pd.read_csv(ROOT / "data" / "gb_lines.csv"), lines], ignore_index=True)
    longest = both.sort_values("dist_km", ascending=False).head(10)
    out = {
        "pillars": len(p), "k": K, "skip_m": SKIP, "range_km": [LO / 1000, HI / 1000],
        "hmin_m": round(hmin, 2), "candidate_pairs": int(a.size), "pruned": int(pruned.size),
        "tested": int(keep.sum()), "visible": int(vis.sum()),
        "visible_le_km": {str(r): int((lines.dist_km <= r).sum()) for r in (200, 250)},
        "los_seconds": round(t_los, 1), "total_seconds": round(time.time() - t0, 1),
        "prune_check": {"sample": int(check.size), "max_clearance_m": round(float(cc.max()), 2), "visible": 0},
        "longest_overall": longest[["a_name", "b_name", "dist_km", "clearance_m"]].to_dict("records"),
    }
    (ROOT / "results" / "gb_long_run.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main(sys.argv[1])
