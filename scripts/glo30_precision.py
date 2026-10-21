"""Precision check: how many Terrain 50 (bare-earth) sightlines survive on Copernicus GLO-30, a surface model.

GLO-30 (release 2024_1) includes canopy and buildings as the radar saw them, so a line that is clear on Terrain 50
but blocked on GLO-30 is probably blocked today by trees or buildings. Two 100 km boxes: Ben Wyvis (upland, the
regional prototype) and Suffolk (lowland, the steel-tower Figure 5 area).

Steps:
    python -I scripts/glo30_precision.py fetch     # catalogue lookup + S3 download of the DEM tiles (needs the
                                                   # CDSE S3 key with CCM access in AWS_ACCESS_KEY_ID / _SECRET_)
    python -I scripts/glo30_precision.py run data/trig/x/CompleteTrigArchive.csv
Writes: data/glo30/*.tif (gitignored), results/glo30_tiles.json, results/glo30_lines.csv,
        results/glo30_precision.json, results/glo30_precision.png

Horizontal transform WGS84 -> OSGB36 is PROJ's default (no OSTN15 grid installed; metre-level error).
GLO-30 heights are EGM2008; Terrain 50 and the archive are ODN. The offset is measured and a corrected run reported.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from los import DEM, clearance, station_heights  # noqa: E402
from region_prototype import pillars  # noqa: E402
from score_primary import DEFAULT, ground_truth  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TILES = ROOT / "data" / "glo30"
CELL = 30.0
K = DEFAULT["k"]
MAX_KM = 100
BOXES = {  # name: (centre easting, centre northing), each +-50 km
    "ben_wyvis": (246296, 868378),
    "suffolk": (590000, 270000),
}
CATALOGUE = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
DATASET = "COP-DEM_GLO-30-DGED/2024_1"


def bounds(name):
    e, n = BOXES[name]
    return e - 50_000, e + 50_000, n - 50_000, n + 50_000


def fetch():
    import boto3
    import requests
    from pyproj import Transformer

    tr = Transformer.from_crs(27700, 4326, always_xy=True)
    s3 = boto3.client("s3", endpoint_url="https://eodata.dataspace.copernicus.eu", region_name="default")
    TILES.mkdir(parents=True, exist_ok=True)
    out = {}
    for name in BOXES:
        x0, x1, y0, y1 = bounds(name)
        xs, ys = tr.transform([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0])
        poly = "POLYGON((" + ",".join(f"{x:.4f} {y:.4f}" for x, y in zip(xs, ys)) + "))"
        f = (f"contains(Name,'DEM1_SAR_DGE_30') and Attributes/OData.CSC.StringAttribute/any("
             f"a:a/Name eq 'dataset' and a/OData.CSC.StringAttribute/Value eq '{DATASET}') and "
             f"OData.CSC.Intersects(area=geography'SRID=4326;{poly}')")
        prods = requests.get(CATALOGUE, params={"$filter": f, "$top": 100, "$expand": "Attributes"},
                             timeout=60).json()["value"]
        tiles = {}
        for p in prods:
            a = {x["Name"]: x["Value"] for x in p["Attributes"]}
            grid = a["eopIdentifier"].split(":")[4]  # e.g. Copernicus_DSM_10_N57_00_W005_00
            key = f"{p['S3Path'].removeprefix('/eodata/')}/{grid}/DEM/{grid}_DEM.tif"
            tiles.setdefault(a["gridId"], {"product": p["Name"], "key": key, "file": f"{grid}_DEM.tif"})
        for t in tiles.values():
            dest = TILES / t["file"]
            if not dest.exists():
                s3.download_file("eodata", t["key"], str(dest))
            t["bytes"] = dest.stat().st_size
        out[name] = dict(sorted(tiles.items()))
        print(name, len(tiles), "tiles")
    (ROOT / "results" / "glo30_tiles.json").write_text(json.dumps({"dataset": DATASET, "boxes": out}, indent=2))


class GridDEM(DEM):
    """A National Grid raster held in memory, sampled with DEM.sample()."""

    def __init__(self, z, x0, y1, cell):
        self.z, self.x0, self.y1, self.cell, self.scale = z, x0, y1, cell, 1.0


def glo30_grid(name):
    import rasterio
    from rasterio.merge import merge
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject

    tiles = json.loads((ROOT / "results" / "glo30_tiles.json").read_text())["boxes"][name]
    srcs = [rasterio.open(TILES / t["file"]) for t in tiles.values()]
    mosaic, transform = merge(srcs)
    crs, src_nodata = srcs[0].crs, srcs[0].nodata
    for s in srcs:
        s.close()
    x0, x1, y0, y1 = bounds(name)
    x0, y1 = x0 - 1000, y1 + 1000
    w, h = int((x1 + 1000 - x0) / CELL), int((y1 - (y0 - 1000)) / CELL)
    z = np.full((h, w), np.nan, dtype=np.float32)
    reproject(mosaic[0].astype(np.float32), z, src_transform=transform, src_crs=crs, src_nodata=src_nodata,
              dst_transform=from_origin(x0, y1, CELL, CELL), dst_crs="EPSG:27700", dst_nodata=np.nan,
              resampling=Resampling.bilinear)
    nodata = int(np.isnan(z).sum())
    return GridDEM(np.nan_to_num(z, nan=0.0), x0, y1, CELL), nodata


def run(trig_csv):
    t50 = DEM()
    gt = ground_truth()
    allp = pillars(trig_csv)
    rows, summary = [], {"dataset": DATASET, "k": K, "skip_m": DEFAULT["skip"], "max_km": MAX_KM, "boxes": {}}
    grids = {}
    for name in BOXES:
        x0, x1, y0, y1 = bounds(name)
        inb = lambda e, n: (e >= x0) & (e <= x1) & (n >= y0) & (n <= y1)  # noqa: E731
        p = allp[inb(allp.EASTING, allp.NORTHING)].reset_index(drop=True)
        e, n = p.EASTING.values, p.NORTHING.values
        z, _ = station_heights(p.HEIGHT.values, p.COMMENTS.values, t50.sample(e, n))
        g, nodata = glo30_grid(name)
        grids[name] = g

        # vertical offset GLO-30 minus Terrain 50 on land, on a 300 m lattice across the box
        ge, gn = np.meshgrid(np.arange(x0, x1, 300.0), np.arange(y0, y1, 300.0))
        a, b = g.sample(ge.ravel(), gn.ravel()), t50.sample(ge.ravel(), gn.ravel())
        land = b > 0
        diff = a[land] - b[land]
        offset = float(np.median(diff))

        i, j = np.triu_indices(len(p), 1)
        d = np.hypot(e[i] - e[j], n[i] - n[j])
        keep = d <= 150_000
        i, j, d = i[keep], j[keep], d[keep]
        args = (e[i], n[i], z[i], e[j], n[j], z[j])
        c_t50 = clearance(t50, *args, k=K, skip=DEFAULT["skip"])
        c_g = clearance(g, *args, k=K, skip=DEFAULT["skip"])
        c_gc = c_g + offset  # equivalent to lowering the whole surface by the offset
        lines = pd.DataFrame({"box": name, "a": p["STATION NAME"].values[i], "b": p["STATION NAME"].values[j],
                              "a_name": p["Trig Name"].values[i], "b_name": p["Trig Name"].values[j],
                              "a_e": e[i], "a_n": n[i], "b_e": e[j], "b_n": n[j],
                              "za": np.round(z[i], 2), "zb": np.round(z[j], 2),
                              "dist_km": np.round(d / 1000, 3), "clear_t50": np.round(c_t50, 2),
                              "clear_glo30": np.round(c_g, 2), "clear_glo30_offset": np.round(c_gc, 2)})
        lost = (lines.clear_t50 > 0) & (lines.clear_glo30 <= 0)
        lines["glo30_block_km_from_nearer_end"] = np.nan
        lines.loc[lost, "glo30_block_km_from_nearer_end"] = block_km(g, lines[lost])
        rows.append(lines)

        m = lines.dist_km <= MAX_KM
        vt = m & (lines.clear_t50 > 0)
        vg, vgc = m & (lines.clear_glo30 > 0), m & (lines.clear_glo30_offset > 0)
        obs = gt[inb(gt.a_e, gt.a_n) & inb(gt.b_e, gt.b_n)]
        pair = {frozenset(x): r for x, r in zip(zip(lines.a, lines.b), lines.itertuples())}
        o = [pair[frozenset(x)] for x in zip(obs.a, obs.b) if frozenset(x) in pair]
        by_band = {}
        for lo, hi in ((0, 20), (20, 50), (50, MAX_KM)):
            bm = vt & (lines.dist_km > lo) & (lines.dist_km <= hi)
            by_band[f"{lo}-{hi}km"] = {"t50_visible": int(bm.sum()),
                                       "survive_glo30": round(float((bm & vg).sum() / max(bm.sum(), 1)), 4)}
        bk = lines.loc[lost & m, "glo30_block_km_from_nearer_end"]
        summary["boxes"][name] = {
            "national_grid_bounds": [x0, x1, y0, y1], "pillars": len(p),
            "pairs_le_max_km": int(m.sum()),
            "glo30_nodata_cells": nodata,
            "glo30_minus_t50_land_m": {"median": round(offset, 2),
                                       "p10": round(float(np.percentile(diff, 10)), 2),
                                       "p90": round(float(np.percentile(diff, 90)), 2), "cells": int(land.sum())},
            "t50_visible": int(vt.sum()),
            "glo30_visible": int(vg.sum()),
            "t50_visible_also_glo30": int((vt & vg).sum()),
            "survival_share": round(float((vt & vg).sum() / vt.sum()), 4),
            "survival_share_offset_corrected": round(float((vt & vgc).sum() / vt.sum()), 4),
            "glo30_only_visible": int((vg & ~vt).sum()),
            "survival_by_distance": by_band,
            "lost_lines_block_km_from_nearer_end": {"median": round(float(bk.median()), 2),
                                                    "share_within_0_5km": round(float((bk <= 0.5).mean()), 4),
                                                    "share_within_2km": round(float((bk <= 2).mean()), 4)},
            "observed_primary_rays_in_box": len(obs),
            "observed_rays_visible_t50": int(sum(r.clear_t50 > 0 for r in o)),
            "observed_rays_visible_glo30": int(sum(r.clear_glo30 > 0 for r in o)),
        }
    lines = pd.concat(rows, ignore_index=True)
    lines.to_csv(ROOT / "results" / "glo30_lines.csv", index=False)
    (ROOT / "results" / "glo30_precision.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    render(lines, grids)


def block_km(g, lines):
    """Distance (km) from the nearer end to the lowest-clearance point on GLO-30, for each line."""
    reff = 6_371_000.0 / (1.0 - K)
    out = []
    for r in lines.itertuples():
        D = r.dist_km * 1000
        x = np.arange(DEFAULT["skip"], D - DEFAULT["skip"], CELL / 2)
        f = x / D
        h = g.sample(r.a_e + (r.b_e - r.a_e) * f, r.a_n + (r.b_n - r.a_n) * f)
        terrain = h + x * (D - x) / (2 * reff)
        sight = r.za + (r.zb - r.za) * f
        i = int(np.argmin(sight - terrain))
        out.append(min(x[i], D - x[i]) / 1000)
    return out


def render(lines, grids):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(16, 8.6), dpi=120)
    for ax, name in zip(axes, BOXES):
        x0, x1, y0, y1 = bounds(name)
        g = grids[name]
        c0, r0 = int((x0 - g.x0) / CELL), int((g.y1 - y1) / CELL)
        z = g.z[r0:r0 + int(100_000 / CELL), c0:c0 + int(100_000 / CELL)]
        gy, gx = np.gradient(z, CELL)
        shade = np.clip(0.7 + 1.5 * (gx - gy), 0, 1)
        ax.imshow(shade, extent=(x0, x1, y0, y1), cmap="Greys_r", vmin=0, vmax=1.3,
                  alpha=0.35)
        ln = lines[(lines.box == name) & (lines.dist_km <= MAX_KM) & (lines.clear_t50 > 0)]
        kept, lost = ln[ln.clear_glo30 > 0], ln[ln.clear_glo30 <= 0]
        for sub, colour, lw in ((kept, "#c2410c", 0.35), (lost, "#7c3aed", 0.35)):
            xs = np.c_[sub.a_e, sub.b_e, np.full(len(sub), np.nan)].ravel()
            ys = np.c_[sub.a_n, sub.b_n, np.full(len(sub), np.nan)].ravel()
            ax.plot(xs, ys, color=colour, lw=lw, alpha=0.45)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"{name.replace('_', ' ').title()}: {len(ln):,} bare-earth lines ≤{MAX_KM} km; "
                     f"{len(kept):,} survive on GLO-30 (orange), {len(lost):,} blocked (purple)", fontsize=9)
    fig.suptitle("Terrain 50 sightlines re-tested on the Copernicus GLO-30 surface model (k = 0.13)\n"
                 "Contains OS data © Crown copyright and database right 2026.\n"
                 "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH\n"
                 "2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(ROOT / "results" / "glo30_precision.png")
    print("wrote results/glo30_precision.png")


if __name__ == "__main__":
    fetch() if sys.argv[1] == "fetch" else run(sys.argv[2])
