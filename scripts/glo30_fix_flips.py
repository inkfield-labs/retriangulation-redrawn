"""Before and after the GLO-30 mosaic fix (#16): what moved when the 100 km blocks were put on whole 30 m cells.

The mosaic before the fix placed each 100 km block 0, 10 or 20 m off the grid and left one-cell seams of no data
(read as 0 m), and four 1-degree tiles under Terrain 50 land were never fetched (results/glo30_gb_alignment.json,
results/glo30_gb_landgaps.json). This compares the outputs of the surface pipeline from before the fix, copied to
data/fix_before/ before the re-run, with the current ones.

Usage:  python -I scripts/glo30_fix_flips.py
Reads:  data/fix_before/{gb_surface.csv, rays_then_now.csv, glo30_gb.json, glo30_gb_landgaps.json, site_build.json}
        (gitignored copies of the old outputs) and the current data/gb_surface.csv and results/
Writes: results/glo30_gb_fix_flips.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OLD, R = ROOT / "data" / "fix_before", ROOT / "results"
BANDS = [(0, 1), (1, 3), (3, 10), (10, np.inf)]  # |clearance| on the old mosaic, m


def main():
    j = lambda p: json.loads(p.read_text())  # noqa: E731
    s = pd.read_csv(OLD / "gb_surface.csv").merge(pd.read_csv(ROOT / "data" / "gb_surface.csv"), on=["a", "b"],
                                                    suffixes=("_old", ""), validate="one_to_one")
    was, now = s.clear_glo30_old > 0, s.clear_glo30 > 0
    flip = was != now
    band = {}
    for lo, hi in BANDS:
        m = (s.clear_glo30_old.abs() >= lo) & (s.clear_glo30_old.abs() < hi)
        band[f"{lo}-{hi}m" if np.isfinite(hi) else f">={lo}m"] = {
            "lines": int(m.sum()), "clear_to_blocked": int((m & was & ~now).sum()),
            "blocked_to_clear": int((m & ~was & now).sum())}
    d = (s.clear_glo30 - s.clear_glo30_old).abs()
    lines = {"lines": len(s), "surface_clear_old": int(was.sum()), "surface_clear_new": int(now.sum()),
             "flag_flips": int(flip.sum()), "clear_to_blocked": int((was & ~now).sum()),
             "blocked_to_clear": int((~was & now).sum()), "by_old_abs_clearance": band,
             "abs_clearance_change_m": {"median": round(float(d.median()), 2),
                                        "p95": round(float(d.quantile(0.95)), 2), "max": round(float(d.max()), 2)}}

    ro, rn = pd.read_csv(OLD / "rays_then_now.csv"), pd.read_csv(R / "rays_then_now.csv")
    r = ro.merge(rn[["a", "b", "clear_glo30", "state"]], on=["a", "b"], suffixes=("_old", ""), validate="one_to_one")
    moved = r[r.state_old != r.state]
    states = ("clear", "surface", "terrain", "unknown")
    rays = {"rays": len(r), "states_old": {k: int((r.state_old == k).sum()) for k in states},
            "states_new": {k: int((r.state == k).sum()) for k in states}, "rays_changing_state": len(moved),
            "changes": [{"a": x.a_name, "b": x.b_name, "from": x.state_old, "to": x.state,
                         "clear_glo30_old_m": x.clear_glo30_old, "clear_glo30_m": x.clear_glo30}
                        for x in moved.itertuples()]}

    go, gn = j(OLD / "glo30_gb.json")["precision_boxes_rerun"], j(R / "glo30_gb.json")["precision_boxes_rerun"]
    boxes = {k: {"old": go[k], "new": gn[k]} for k in gn}
    bo, bn = j(OLD / "site_build.json"), j(R / "site_build.json")
    out = {"land_cells_without_glo30": {"old": j(OLD / "glo30_gb_landgaps.json")["land_cells_without_glo30"],
                                        "new": j(R / "glo30_gb_landgaps.json")["land_cells_without_glo30"]},
           "visible_lines": lines, "rays_then_now": rays, "precision_boxes_vs_precision_grid": boxes,
           "site": {"surface_clear": {"old": bo["surface_clear"], "new": bn["surface_clear"]},
                    "most_partners": {"old": bo["most_partners"], "new": bn["most_partners"]},
                    "longest_surface_clear": {"old": [x["surface_clear"] for x in bo["longest"]],
                                              "new": [x["surface_clear"] for x in bn["longest"]]}}}
    (R / "glo30_gb_fix_flips.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
