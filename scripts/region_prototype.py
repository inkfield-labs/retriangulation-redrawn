"""Regional prototype: every pillar pair inside a 100 km x 100 km box around Ben Wyvis.

Pillars: TYPE OF MARK = PILLAR and not destroyed in the OS archive (one record per station name).
Computes clearance for all pairs up to 150 km at k = 0.13 (default) and k = 0 and 0.20, times the run,
compares with the observed primary rays, and renders a PNG map.

Usage:  python -I scripts/region_prototype.py data/trig/x/CompleteTrigArchive.csv
Writes: results/region_lines.csv, results/region_summary.json, results/region_network.png
"""
import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from los import DEM, clearance, station_heights  # noqa: E402
from score_primary import BOX, DEFAULT, ground_truth, in_box  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RANGES = (50, 100, 150)


def pillars(trig_csv):
    d = pd.read_csv(trig_csv, encoding="latin-1")
    p = d[d["TYPE OF MARK"].eq("PILLAR") & d["DESTROYED MARK INDICATOR"].eq(0)]
    return p.drop_duplicates("STATION NAME").reset_index(drop=True)


def main(trig_csv):
    dem = DEM()
    p = pillars(trig_csv)
    p = p[in_box(p.EASTING, p.NORTHING)].reset_index(drop=True)
    e, n = p.EASTING.values, p.NORTHING.values
    z, src = station_heights(p.HEIGHT.values, p.COMMENTS.values, dem.sample(e, n))
    i, j = np.triu_indices(len(p), 1)
    dist = np.hypot(e[i] - e[j], n[i] - n[j])
    keep = dist <= max(RANGES) * 1000
    i, j, dist = i[keep], j[keep], dist[keep]
    samples = int(np.ceil(dist / dem.cell).sum())

    res, timing = {}, {}
    for k in (0.13, 0.0, 0.20):
        t0 = time.time()
        res[k] = clearance(dem, e[i], n[i], z[i], e[j], n[j], z[j], k=k, skip=DEFAULT["skip"])
        timing[k] = time.time() - t0
    lines = pd.DataFrame({"a": p["STATION NAME"].values[i], "b": p["STATION NAME"].values[j],
                          "a_name": p["Trig Name"].values[i], "b_name": p["Trig Name"].values[j],
                          "dist_km": np.round(dist / 1000, 3), "clear_k013": np.round(res[0.13], 2),
                          "clear_k0": np.round(res[0.0], 2), "clear_k020": np.round(res[0.20], 2)})
    lines.to_csv(ROOT / "results" / "region_lines.csv", index=False)

    gt = ground_truth()
    gtbox = gt[in_box(gt.a_e, gt.a_n) & in_box(gt.b_e, gt.b_n)]
    obs = {frozenset(x) for x in zip(gtbox.a, gtbox.b)}
    prim = set(gtbox.a) | set(gtbox.b) | set(p.loc[p.ORDER.eq(1), "STATION NAME"])
    summary = {
        "box_national_grid": BOX, "pillars": len(p), "pillar_height_source": pd.Series(src).value_counts().to_dict(),
        "pairs_le_150km": int(len(lines)), "profile_samples_le_150km": samples,
        "seconds_per_k": {str(k): round(v, 2) for k, v in timing.items()},
        "samples_per_second": round(samples / timing[0.13]),
        "by_range": {},
    }
    for r in RANGES:
        m = lines.dist_km <= r
        pm = m & lines.a.isin(prim) & lines.b.isin(prim)
        summary["by_range"][str(r)] = {
            "pairs": int(m.sum()),
            "visible_k0": int((m & (lines.clear_k0 > 0)).sum()),
            "visible_k013": int((m & (lines.clear_k013 > 0)).sum()),
            "visible_k020": int((m & (lines.clear_k020 > 0)).sum()),
            "primary_pairs": int(pm.sum()),
            "primary_visible_k013": int((pm & (lines.clear_k013 > 0)).sum()),
            "primary_observed_in_box": len(obs),
        }
    (ROOT / "results" / "region_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    render(dem, p, lines, gtbox)


def render(dem, p, lines, gtbox):
    x0, x1, y0, y1 = BOX
    c0, c1 = int((x0 - dem.x0) / dem.cell), int((x1 - dem.x0) / dem.cell)
    r0, r1 = int((dem.y1 - y1) / dem.cell), int((dem.y1 - y0) / dem.cell)
    z = dem.z[r0:r1, c0:c1]
    gy, gx = np.gradient(z, dem.cell)
    shade = np.clip(0.7 + 1.5 * (gx - gy), 0, 1)  # light from the north-west
    sea = z <= 0
    fig, ax = plt.subplots(figsize=(11, 11), dpi=130)
    ax.imshow(np.where(sea, np.nan, shade), extent=(x0, x1, y0, y1), cmap="Greys_r", vmin=0.0, vmax=1.3, alpha=0.35)
    ax.imshow(np.where(sea, 1, np.nan), extent=(x0, x1, y0, y1), cmap="Blues", vmin=0, vmax=4, alpha=0.6)
    idx = p.set_index("STATION NAME")
    vis = lines[(lines.clear_k013 > 0) & (lines.dist_km <= 100)]
    for r in vis.itertuples():
        a, b = idx.loc[r.a], idx.loc[r.b]
        ax.plot([a.EASTING, b.EASTING], [a.NORTHING, b.NORTHING], color="#c2410c", lw=0.3, alpha=0.45)
    for r in gtbox.itertuples():
        ax.plot([r.a_e, r.b_e], [r.a_n, r.b_n], color="#1d4ed8", lw=1.6)
    ax.scatter(p.EASTING, p.NORTHING, s=5, color="black", zorder=3)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"Ben Wyvis 100 km box: {len(p)} standing pillars, {len(vis):,} modelled sightlines "
                 f"(≤100 km, k=0.13, orange)\nObserved primary rays from the 1967 History in blue. "
                 f"Contains OS data © Crown copyright and database right 2026", fontsize=9)
    fig.tight_layout()
    fig.savefig(ROOT / "results" / "region_network.png")
    print("wrote results/region_network.png")


if __name__ == "__main__":
    main(sys.argv[1])
