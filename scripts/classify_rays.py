"""Then and now: classify every reciprocal primary ray observed in 1936-62 against today's models.

Rays: results/primary_rays.csv observed from both ends and at most 120 km long (the one longer reciprocal pair,
Shurland-Castle Ring at 241 km, is a parsing artefact; see score_primary.py). Non-pillar stations are included.
States, at k = 0.13 with a 100 m end skip:
    clear    clear over Terrain 50 and over the GLO-30 surface model (2010-15 radar)
    surface  clear over Terrain 50, blocked on GLO-30: probably trees or buildings
    terrain  blocked over Terrain 50 at station height: the surveyors needed a tower, or the ground has changed
    unknown  one end is not a pillar and has no recorded height; most are bolts on water towers, church towers and
             cathedrals observed from the top, so their sight height is not known and the ray is not classified
Sight height: pillars as in los.station_heights; other marks with a recorded height get an instrument 1.5 m above it.

Usage:  python -I scripts/classify_rays.py      (needs data/glo30/gb30.npy from scripts/glo30_gb.py)
Writes: results/rays_then_now.csv, results/rays_then_now.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glo30_gb import load_glo30  # noqa: E402
from los import DEM, clearance, station_heights  # noqa: E402
from score_primary import DEFAULT  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INSTRUMENT_ON_MARK = 1.5


def sight(r, end, dem):
    ground = dem.sample(r[f"{end}_e"], r[f"{end}_n"])
    pillar, _ = station_heights(r[f"{end}_height"], r[f"{end}_comments"], ground)
    h = r[f"{end}_height"].values
    mark = np.where(h > 0, h, ground) + INSTRUMENT_ON_MARK
    return np.where(r[f"{end}_type"].values == "PILLAR", pillar, mark)


def main():
    r = pd.read_csv(ROOT / "results" / "primary_rays.csv")
    r = r[(r.n_directions >= 2) & (r.dist_km <= 120)].reset_index(drop=True)
    args = lambda za, zb: (r.a_e, r.a_n, za, r.b_e, r.b_n, zb)  # noqa: E731
    t50 = DEM()
    za, zb = sight(r, "a", t50), sight(r, "b", t50)
    c_t50 = clearance(t50, *args(za, zb), k=DEFAULT["k"], skip=DEFAULT["skip"])
    del t50
    c_glo = clearance(load_glo30(), *args(za, zb), k=DEFAULT["k"], skip=DEFAULT["skip"])

    out = r[["a", "b", "a_name", "b_name", "a_type", "b_type", "a_destroyed", "b_destroyed", "figures",
             "dist_km", "a_e", "a_n", "b_e", "b_n", "both_pillars"]].copy()
    out["dist_km"] = out.dist_km.round(2)
    out["za"], out["zb"] = np.round(za, 2), np.round(zb, 2)
    out["clear_t50"], out["clear_glo30"] = np.round(c_t50, 2), np.round(c_glo, 2)
    known = ((r.a_type == "PILLAR") | (r.a_height > 0)) & ((r.b_type == "PILLAR") | (r.b_height > 0))
    out["state"] = np.where(~known, "unknown",
                            np.where(c_t50 <= 0, "terrain", np.where(c_glo <= 0, "surface", "clear")))
    out.to_csv(ROOT / "results" / "rays_then_now.csv", index=False)

    counts = lambda m: {s: int((out.state[m] == s).sum())  # noqa: E731
                        for s in ("clear", "surface", "terrain", "unknown")}
    pp = out.both_pillars
    fig5 = out.figures.str.contains("5")
    summary = {
        "rays": len(out), "k": DEFAULT["k"], "skip_m": DEFAULT["skip"],
        "instrument_on_non_pillar_mark_m": INSTRUMENT_ON_MARK,
        "states": counts(slice(None)),
        "pillar_to_pillar": {"rays": int(pp.sum()), "states": counts(pp),
                             # must equal the recall run (612 of 641, results/recall_sweep.csv)
                             "t50_visible": int((pp & (out.clear_t50 > 0)).sum())},
        "with_non_pillar_end": {"rays": int((~pp).sum()), "states": counts(~pp)},
        "figure_5_eastern_counties": {"rays": int(fig5.sum()), "states": counts(fig5)},
        "rays_with_a_destroyed_station": int(((out.a_destroyed == 1) | (out.b_destroyed == 1)).sum()),
    }
    (ROOT / "results" / "rays_then_now.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
