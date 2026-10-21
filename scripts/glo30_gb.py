"""GB-wide surface flag: re-test every visible Terrain 50 line on Copernicus GLO-30 (release 2024_1).

A line clear on Terrain 50 but blocked on GLO-30 is probably blocked by trees or buildings as the radar saw them in
2010-15. Same model as scripts/glo30_precision.py: k = 0.13, 100 m end skip, GLO-30 heights used as published
(EGM2008, about 0.4-0.8 m above ODN in the precision boxes; no offset applied).

Steps:
    python -I scripts/glo30_gb.py fetch [lines.csv ...]   # tiles crossed by the lines (default data/gb_lines.csv);
                                                          # needs the CDSE S3 key in AWS_ACCESS_KEY_ID / _SECRET_
    python -I scripts/glo30_gb.py mosaic                  # data/glo30/gb30.npy, int16 decimetres on a 30 m BNG grid
    python -I scripts/glo30_gb.py landgaps                # Terrain 50 land with no GLO-30 data; run calls it first
    python -I scripts/glo30_gb.py run data/trig/x/CompleteTrigArchive.csv [lines.csv ...]
Writes: data/glo30/*.tif and gb30.npy (gitignored), data/gb_surface.csv (a, b, clear_glo30, gitignored),
        results/glo30_gb_tiles.json, results/glo30_gb_landgaps.json, results/glo30_gb.json
Horizontal transform WGS84 -> OSGB36 is PROJ's default (no OSTN15 grid installed; metre-level error).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glo30_precision import BOXES, CATALOGUE, DATASET, TILES, GridDEM, bounds  # noqa: E402
from los import DEM, clearance, station_heights  # noqa: E402
from region_prototype import pillars  # noqa: E402
from score_primary import DEFAULT  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CELL = 30
X0, X1, Y0, Y1 = 0, 700_020, 0, 1_250_010  # National Grid extent of Terrain 50, rounded up to whole 30 m cells
NODATA = -32768
BLOCK = 100_000
K = DEFAULT["k"]


def line_files(args):
    return [Path(a) for a in args] or [ROOT / "data" / "gb_lines.csv"]


def needed_tiles(files):
    """1-degree cells (lat, lon of the south-west corner) crossed by any line, sampled every 2 km."""
    from pyproj import Transformer

    tr = Transformer.from_crs(27700, 4326, always_xy=True)
    cells = set()
    for f in files:
        ln = pd.read_csv(f, usecols=["a_e", "a_n", "b_e", "b_n", "dist_km"])
        ns = np.maximum(np.ceil(ln.dist_km.values / 2).astype(int), 1) + 1
        pair = np.repeat(np.arange(len(ln)), ns)
        t = (np.arange(ns.sum()) - np.repeat(np.cumsum(ns) - ns, ns)) / (ns[pair] - 1)
        e = ln.a_e.values[pair] + (ln.b_e.values - ln.a_e.values)[pair] * t
        n = ln.a_n.values[pair] + (ln.b_n.values - ln.a_n.values)[pair] * t
        lon, lat = tr.transform(e, n)
        cells |= set(zip(np.floor(lat).astype(int).tolist(), np.floor(lon).astype(int).tolist()))
    return cells


def grid_name(lat, lon):
    return (f"Copernicus_DSM_10_{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00_"
            f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}_00")


def fetch(args):
    import boto3
    import requests

    cells = needed_tiles(line_files(args))
    lats, lons = [c[0] for c in cells], [c[1] for c in cells]
    w, s, e, n = min(lons) + 0.5, min(lats) + 0.5, max(lons) + 0.5, max(lats) + 0.5
    poly = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
    f = (f"contains(Name,'DEM1_SAR_DGE_30') and Attributes/OData.CSC.StringAttribute/any("
         f"a:a/Name eq 'dataset' and a/OData.CSC.StringAttribute/Value eq '{DATASET}') and "
         f"OData.CSC.Intersects(area=geography'SRID=4326;{poly}')")
    found, url, params = {}, CATALOGUE, {"$filter": f, "$top": 200, "$expand": "Attributes"}
    while url:
        page = requests.get(url, params=params, timeout=120).json()
        for p in page["value"]:
            a = {x["Name"]: x["Value"] for x in p["Attributes"]}
            grid = a["eopIdentifier"].split(":")[4]
            found.setdefault(grid, {"product": p["Name"],
                                    "key": f"{p['S3Path'].removeprefix('/eodata/')}/{grid}/DEM/{grid}_DEM.tif",
                                    "file": f"{grid}_DEM.tif"})
        url, params = page.get("@odata.nextLink"), None
    want = {grid_name(*c) for c in cells}
    tiles = {g: found[g] for g in sorted(want & found.keys())}
    s3 = boto3.client("s3", endpoint_url="https://eodata.dataspace.copernicus.eu", region_name="default")
    TILES.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(tiles.values()):
        dest = TILES / t["file"]
        if not dest.exists():
            s3.download_file("eodata", t["key"], str(dest))
        t["bytes"] = dest.stat().st_size
        print(f"{i + 1}/{len(tiles)} {t['file']}", flush=True)
    out = {"dataset": DATASET, "cells_crossed": len(cells), "tiles": len(tiles),
           "cells_without_tile": sorted(want - found.keys()),  # all-sea cells have no GLO-30 tile
           "bytes": sum(t["bytes"] for t in tiles.values()), "tile_list": tiles}
    (ROOT / "results" / "glo30_gb_tiles.json").write_text(json.dumps(out, indent=2))
    print(len(tiles), "tiles,", round(out["bytes"] / 1e9, 2), "GB;", len(out["cells_without_tile"]), "sea cells")


def mosaic():
    import rasterio
    from rasterio.merge import merge
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject, transform_bounds

    tiles = json.loads((ROOT / "results" / "glo30_gb_tiles.json").read_text())["tile_list"]
    srcs = [rasterio.open(TILES / t["file"]) for t in tiles.values()]
    nx, ny = (X1 - X0) // CELL, (Y1 - Y0) // CELL
    out = np.lib.format.open_memmap(TILES / "gb30.npy", mode="w+", dtype=np.int16, shape=(ny, nx))
    out[:] = NODATA
    t0, filled = time.time(), 0
    for by in range(Y0, Y1, BLOCK):
        for bx in range(X0, X1, BLOCK):
            bx1, by1 = min(bx + BLOCK, X1), min(by + BLOCK, Y1)
            w, s, e, n = transform_bounds("EPSG:27700", "EPSG:4326", bx, by, bx1, by1)
            m = 0.01  # margin so bilinear sampling at the block edge has neighbours
            hit = [r for r in srcs if r.bounds.left < e + m and r.bounds.right > w - m and
                   r.bounds.bottom < n + m and r.bounds.top > s - m]
            if not hit:
                continue
            # snap the merge window to the source pixel lattice, or merge resamples every block by nearest
            # neighbour; tiles are finer south of 60 N, so use the finest and bilinear where they mix (Shetland)
            ref = min(hit, key=lambda r: r.res[0])
            (rx, ry), x0, y1 = ref.res, ref.bounds.left, ref.bounds.top
            snap = (x0 + np.floor((w - m - x0) / rx) * rx, y1 - np.ceil((y1 - s + m) / ry) * ry,
                    x0 + np.ceil((e + m - x0) / rx) * rx, y1 - np.floor((y1 - n - m) / ry) * ry)
            src, tf = merge(hit, bounds=snap, res=(rx, ry), nodata=np.nan, dtype="float32",
                            resampling=Resampling.bilinear)
            c0, r0 = (bx - X0) // CELL, (Y1 - by1) // CELL
            z = np.full(((by1 - by) // CELL, (bx1 - bx) // CELL), np.nan, dtype=np.float32)
            reproject(src[0], z, src_transform=tf, src_crs=hit[0].crs, src_nodata=np.nan,
                      dst_transform=from_origin(bx, by1, CELL, CELL), dst_crs="EPSG:27700", dst_nodata=np.nan,
                      resampling=Resampling.bilinear)
            ok = ~np.isnan(z)
            win = out[r0:r0 + z.shape[0], c0:c0 + z.shape[1]]
            win[ok] = np.round(z[ok] * 10).astype(np.int16)
            filled += int(ok.sum())
        print(f"row {by // 1000} km done, {time.time() - t0:.0f} s", flush=True)
    out.flush()
    meta = {"x0": X0, "y1": Y1, "cell": CELL, "nx": nx, "ny": ny, "units": "decimetres", "nodata": NODATA,
            "dataset": DATASET, "tiles": len(srcs), "filled_cells": filled}
    (TILES / "gb30.json").write_text(json.dumps(meta))
    print(json.dumps(meta))


def landgaps():
    """Count Terrain 50 land cells (> 0 m) whose 30 m GLO-30 cell has no data. load_glo30 reads no data as sea (0 m), so a
    land gap (a tile that was not fetched) would put the surface below the terrain and turn lines surface-clear."""
    meta = json.loads((TILES / "gb30.json").read_text())
    t50 = np.load(ROOT / "data" / "terrain50" / "gb50.npy", mmap_mode="r")
    t50_meta = json.loads((ROOT / "data" / "terrain50" / "gb50.json").read_text())
    glo = np.load(TILES / "gb30.npy", mmap_mode="r")
    land = gaps = 0
    for r0 in range(0, t50.shape[0], 500):
        rows, cols = np.nonzero(np.asarray(t50[r0:r0 + 500]) > 0)  # nodata is -32768, so > 0 is land
        e = (cols + 0.5) * t50_meta["cell"] + t50_meta["x0"]
        n = t50_meta["y1"] - (rows + r0 + 0.5) * t50_meta["cell"]
        gr = ((meta["y1"] - n) // meta["cell"]).astype(int)
        gc = ((e - meta["x0"]) // meta["cell"]).astype(int)
        land += rows.size
        gaps += int((glo[gr, gc] == meta["nodata"]).sum())
    out = {"terrain50_land_cells": land, "land_cells_without_glo30": gaps, "glo30_nodata": meta["nodata"],
           "cells_without_tile": json.loads((ROOT / "results" / "glo30_gb_tiles.json").read_text())["cells_without_tile"]}
    (ROOT / "results" / "glo30_gb_landgaps.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out))
    return gaps


def load_glo30():
    meta = json.loads((TILES / "gb30.json").read_text())
    z = np.load(TILES / "gb30.npy")
    z[z == meta["nodata"]] = 0  # no tile: sea
    g = GridDEM(z, meta["x0"], meta["y1"], meta["cell"])
    g.scale = 0.1
    return g


def run(trig_csv, args):
    if landgaps():
        sys.exit("GLO-30 has no data under Terrain 50 land: fetch the missing tiles and rerun mosaic")
    p = pillars(trig_csv)
    t50 = DEM()
    z = dict(zip(p["STATION NAME"], station_heights(p.HEIGHT.values, p.COMMENTS.values,
                                                    t50.sample(p.EASTING.values, p.NORTHING.values))[0]))
    del t50
    lines = pd.concat([pd.read_csv(f) for f in line_files(args)], ignore_index=True)
    g = load_glo30()
    t0 = time.time()
    c = clearance(g, lines.a_e, lines.a_n, lines.a.map(z), lines.b_e, lines.b_n, lines.b.map(z),
                  k=K, skip=DEFAULT["skip"])
    secs = time.time() - t0
    lines["clear_glo30"] = np.round(c, 2)
    lines[["a", "b", "clear_glo30"]].to_csv(ROOT / "data" / "gb_surface.csv", index=False)

    clear = lines.clear_glo30 > 0
    bands = {}
    for lo, hi in ((0, 20), (20, 50), (50, 100), (100, 150), (150, 250)):
        m = (lines.dist_km > lo) & (lines.dist_km <= hi)
        if m.any():
            bands[f"{lo}-{hi}km"] = {"lines": int(m.sum()), "surface_clear_share": round(float(clear[m].mean()), 4)}
    # 100 km squares by line midpoint, keyed by the south-west corner in km ("easting_northing")
    sq = ((lines.a_e + lines.b_e) // 2 // 100_000 * 100).astype(int).astype(str) + "_" + \
         ((lines.a_n + lines.b_n) // 2 // 100_000 * 100).astype(int).astype(str)
    by_sq = {k: {"lines": int(v.size), "surface_clear_share": round(float(v.mean()), 4)}
             for k, v in clear.groupby(sq)}
    # sanity: the precision-check boxes (both ends inside the box, <= 100 km), same rule as glo30_precision.py
    boxes = {}
    for name in BOXES:
        x0, x1, y0, y1 = bounds(name)
        inb = lambda e, n: (e >= x0) & (e <= x1) & (n >= y0) & (n <= y1)  # noqa: E731
        m = inb(lines.a_e, lines.a_n) & inb(lines.b_e, lines.b_n) & (lines.dist_km <= 100)
        boxes[name] = {"t50_visible": int(m.sum()), "surface_clear": int((m & clear).sum()),
                       "survival_share": round(float(clear[m].mean()), 4)}
        # the same lines on the precision check's own grid (30 m, different lattice): how many flags flip
        old = pd.read_csv(ROOT / "results" / "glo30_lines.csv")
        old = old[(old.box == name) & (old.dist_km <= 100) & (old.clear_t50 > 0)]
        j = old.merge(lines[["a", "b", "clear_glo30"]], on=["a", "b"], suffixes=("_box", ""))
        flip = (j.clear_glo30_box > 0) != (j.clear_glo30 > 0)
        boxes[name]["vs_precision_grid"] = {
            "lines": len(j), "flag_flips": int(flip.sum()),
            "clearance_diff_median_m": round(float((j.clear_glo30 - j.clear_glo30_box).median()), 2),
            "flipped_abs_clearance_p90_m": round(float(j.clear_glo30_box[flip].abs().quantile(0.9)), 2)}
    out = {"dataset": DATASET, "k": K, "skip_m": DEFAULT["skip"], "grid_cell_m": CELL,
           "line_files": [str(Path(f).relative_to(ROOT)) if Path(f).is_absolute() else str(f)
                          for f in line_files(args)],
           "lines": len(lines), "surface_clear": int(clear.sum()),
           "surface_clear_share": round(float(clear.mean()), 4), "los_seconds": round(secs, 1),
           "by_distance": bands, "precision_boxes_rerun": boxes, "by_100km_square_of_midpoint": by_sq}
    (ROOT / "results" / "glo30_gb.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "by_100km_square_of_midpoint"}, indent=2))


if __name__ == "__main__":
    step = sys.argv[1]
    if step == "fetch":
        fetch(sys.argv[2:])
    elif step == "mosaic":
        mosaic()
    elif step == "landgaps":
        sys.exit(1 if landgaps() else 0)
    else:
        run(sys.argv[2], sys.argv[3:])
