"""Diagnose observed primary rays the LOS model calls blocked at default settings.

For each missed ray: where along the profile the worst obstruction is, and the terrain height there.
Also recall by primary figure, since Figure 5 (Eastern Counties) used steel towers at 34 primary stations
(History p. 51, section 2.130), so its rays were observed from tower height, not pillar height.

Usage:  python -I scripts/diagnose_misses.py
Writes: results/misses_diagnosis.csv, results/recall_by_figure.csv
"""
import ast
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from los import DEM, R_EARTH, station_heights  # noqa: E402
from score_primary import DEFAULT, ground_truth  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def worst_point(dem, r, k, skip):
    d = np.hypot(r.b_e - r.a_e, r.b_n - r.a_n)
    n = int(np.ceil(d / dem.cell))
    f = (np.arange(n) + 0.5) / n
    x = f * d
    e, nn = r.a_e + (r.b_e - r.a_e) * f, r.a_n + (r.b_n - r.a_n) * f
    h = dem.sample(e, nn)
    za, _ = station_heights([r.a_height], [r.a_comments], dem.sample([r.a_e], [r.a_n]))
    zb, _ = station_heights([r.b_height], [r.b_comments], dem.sample([r.b_e], [r.b_n]))
    sight = za[0] + (zb[0] - za[0]) * f
    c = sight - (h + x * (d - x) / (2 * R_EARTH / (1 - k)))
    c[(x <= skip) | (d - x <= skip)] = np.inf
    i = int(np.argmin(c))
    return dict(clearance_m=round(float(c[i]), 2), obstruction_km_from_a=round(x[i] / 1000, 2),
                obstruction_e=round(e[i]), obstruction_n=round(nn[i]), terrain_m=round(float(h[i]), 1),
                sight_line_m=round(float(sight[i]), 1))


def main():
    gt = ground_truth()
    cl = pd.read_csv(ROOT / "results" / "primary_clearance_default.csv")
    gt["visible"] = cl.visible.values
    gt["figs"] = gt.figures.map(ast.literal_eval)
    gt["fig5_only"] = gt.figs.map(lambda f: f == [5])
    rows = []
    for fig in range(1, 8):
        m = gt.figs.map(lambda f: fig in f)
        rows.append({"figure": fig, "rays": int(m.sum()), "recall": round(gt.visible[m].mean(), 4)})
    nf5 = ~gt.fig5_only
    rows.append({"figure": "all", "rays": len(gt), "recall": round(gt.visible.mean(), 4)})
    rows.append({"figure": "all except Figure 5 only", "rays": int(nf5.sum()), "recall": round(gt.visible[nf5].mean(), 4)})
    rec = pd.DataFrame(rows)
    rec.to_csv(ROOT / "results" / "recall_by_figure.csv", index=False)
    print(rec.to_string(index=False))

    dem = DEM()
    miss = gt[~gt.visible]
    out = []
    for r in miss.itertuples():
        out.append({"a_name": r.a_name, "b_name": r.b_name, "figures": r.figures, "dist_km": round(r.dist_km, 1),
                    **worst_point(dem, r, DEFAULT["k"], DEFAULT["skip"])})
    out = pd.DataFrame(out).sort_values("clearance_m")
    out.to_csv(ROOT / "results" / "misses_diagnosis.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
