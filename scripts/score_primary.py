"""Score the LOS model against observed primary rays.

Ground truth: rays in results/primary_rays.csv with both ends PILLAR, observed from both ends, and at most 120 km
long (one longer reciprocal pair, Shurland-Castle Ring at 241 km, is a parsing artefact). Also scores the hand-read
Diagram 10 set.

Usage:  python -I scripts/score_primary.py data/trig/x/CompleteTrigArchive.csv
Writes: results/recall_sweep.csv, results/primary_clearance_default.csv, results/hand_rays_scored.csv,
        results/station_height_vs_dem.csv
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from los import DEM, FB_ABOVE_GROUND, clearance, station_heights  # noqa: E402
from match_rays import build_matcher, load_primary  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WYVIS = (246296, 868378)
BOX = (WYVIS[0] - 50_000, WYVIS[0] + 50_000, WYVIS[1] - 50_000, WYVIS[1] + 50_000)
DEFAULT = dict(k=0.13, skip=100.0, mode="fb", factor=1)


def in_box(e, n):
    return (e >= BOX[0]) & (e <= BOX[1]) & (n >= BOX[2]) & (n <= BOX[3])


def ground_truth():
    g = pd.read_csv(ROOT / "results" / "primary_rays.csv")
    return g[g.both_pillars & (g.n_directions >= 2) & (g.dist_km <= 120)].reset_index(drop=True)


def run(dem, rays, k, skip, mode):
    ga, gb = dem.sample(rays.a_e, rays.a_n), dem.sample(rays.b_e, rays.b_n)
    za, _ = station_heights(rays.a_height, rays.a_comments, ga, mode)
    zb, _ = station_heights(rays.b_height, rays.b_comments, gb, mode)
    return clearance(dem, rays.a_e, rays.a_n, za, rays.b_e, rays.b_n, zb, k=k, skip=skip)


def main(trig_csv):
    gt = ground_truth()
    box = in_box(gt.a_e, gt.a_n) & in_box(gt.b_e, gt.b_n)
    print(f"ground truth: {len(gt)} rays GB-wide; {int(box.sum())} with both ends in the Ben Wyvis 100 km box")

    rows, dems = [], {}
    configs = ([dict(DEFAULT, k=k) for k in (0.0, 0.05, 0.10, 0.13, 0.20)] +
               [dict(DEFAULT, skip=s) for s in (0.0, 50.0, 200.0)] +
               [dict(DEFAULT, mode="dem")] +
               [dict(DEFAULT, factor=f) for f in (2, 4)])
    for cfg in configs:
        if cfg["factor"] not in dems:
            dems[cfg["factor"]] = DEM(factor=cfg["factor"])
        t0 = time.time()
        c = run(dems[cfg["factor"]], gt, cfg["k"], cfg["skip"], cfg["mode"])
        dt = time.time() - t0
        vis = c > 0
        rows.append({**cfg, "dem_cell_m": dems[cfg["factor"]].cell, "n_gb": len(gt),
                     "recall_gb": vis.mean(), "n_box": int(box.sum()), "recall_box": vis[box].mean(),
                     "seconds": round(dt, 2)})
        print(f"{cfg} cell={dems[cfg['factor']].cell} recall GB {vis.mean():.3f} box {vis[box].mean():.3f} "
              f"({dt:.1f}s)")
        if cfg == DEFAULT:
            out = gt[["a", "b", "a_name", "b_name", "dist_km", "a_e", "a_n", "b_e", "b_n"]].copy()
            out["clearance_m"] = np.round(c, 2)
            out["visible"] = vis
            out["in_box"] = box
            out.to_csv(ROOT / "results" / "primary_clearance_default.csv", index=False)
    pd.DataFrame(rows).to_csv(ROOT / "results" / "recall_sweep.csv", index=False)

    # station heights against the DEM: archive ground (HEIGHT - FB offset) minus DEM at the pillar
    dem = dems[1]
    st = pd.concat([gt[[f"{e}_{c}" for c in ("name", "e", "n", "height")]].set_axis(
        ["name", "e", "n", "height"], axis=1) for e in "ab"]).drop_duplicates("name")
    st["dem"] = dem.sample(st.e, st.n)
    st["ground_minus_dem"] = st.height - FB_ABOVE_GROUND - st.dem
    st.to_csv(ROOT / "results" / "station_height_vs_dem.csv", index=False)
    q = st.ground_minus_dem[st.height > 0]
    print(f"archive ground minus DEM at {len(q)} primary pillars: median {q.median():.1f} m, "
          f"p10 {q.quantile(.1):.1f}, p90 {q.quantile(.9):.1f}")

    # hand-read Diagram 10 rays
    primary = load_primary(trig_csv)
    one, _ = build_matcher(primary)
    hand = pd.read_csv(ROOT / "results" / "hand_rays_diagram10.csv")
    hand["a_pp"], hand["b_pp"] = hand.a.map(one), hand.b.map(one)
    info = primary.set_index("pp")
    for e in "ab":
        for col, src in [("e", "EASTING"), ("n", "NORTHING"), ("height", "HEIGHT"), ("comments", "COMMENTS"),
                         ("type", "TYPE OF MARK")]:
            hand[f"{e}_{col}"] = hand[f"{e}_pp"].map(info[src])
    hand["dist_km"] = np.hypot(hand.a_e - hand.b_e, hand.a_n - hand.b_n) / 1000
    hand["clearance_m"] = np.round(run(dem, hand, **{k: DEFAULT[k] for k in ("k", "skip", "mode")}), 2)
    hand["visible"] = hand.clearance_m > 0
    pairs = set(zip(gt.a, gt.b)) | set(zip(gt.b, gt.a))
    allg = pd.read_csv(ROOT / "results" / "primary_rays.csv")
    parsed = set(zip(allg.a, allg.b)) | set(zip(allg.b, allg.a))
    hand["in_parsed_rays"] = [(a, b) in parsed for a, b in zip(hand.a_pp, hand.b_pp)]
    hand["in_ground_truth"] = [(a, b) in pairs for a, b in zip(hand.a_pp, hand.b_pp)]
    hand.to_csv(ROOT / "results" / "hand_rays_scored.csv", index=False)
    print(f"hand rays: {len(hand)}; unmatched names {int(hand.a_pp.isna().sum() + hand.b_pp.isna().sum())}; "
          f"found by parser {int(hand.in_parsed_rays.sum())}; recall {hand.visible.mean():.3f}; "
          f"dist km {hand.dist_km.min():.1f}-{hand.dist_km.max():.1f}")


if __name__ == "__main__":
    main(sys.argv[1])
