"""Mosaic OS Terrain 50 ASCII grid tiles into one GB array.

Input:  the unpacked terr50_gagg_gb.zip (folder holding data/<sq>/<tile>_OST50GRID_<date>.zip)
Output: data/terrain50/gb50.npy  int16 decimetres, row 0 = north edge; NODATA = -32768
        data/terrain50/gb50.json grid origin and size
Usage:  python -I scripts/build_dem.py data/terrain50
"""
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np

CELL = 50
X0, X1, Y0, Y1 = 0, 700_000, 0, 1_250_000  # National Grid extent covering GB including Shetland


def main(folder):
    folder = Path(folder)
    nx, ny = (X1 - X0) // CELL, (Y1 - Y0) // CELL
    dem = np.full((ny, nx), -32768, dtype=np.int16)
    t0, n = time.time(), 0
    for z in sorted(folder.glob("data/*/*_OST50GRID_*.zip")):
        with zipfile.ZipFile(z) as zf:
            asc = next(m for m in zf.namelist() if m.lower().endswith(".asc"))
            text = zf.read(asc).decode("ascii")
        head, body = text.split("\n", 5)[:5], text.split("\n", 5)[5]
        h = {k.lower(): float(v) for k, v in (ln.split() for ln in head)}
        a = np.loadtxt(io.StringIO(body), dtype=np.float32)
        nr, nc = int(h["nrows"]), int(h["ncols"])
        a = a.reshape(nr, nc)
        col = int((h["xllcorner"] - X0) // CELL)
        row = int((Y1 - (h["yllcorner"] + nr * CELL)) // CELL)
        dem[row:row + nr, col:col + nc] = np.round(a * 10).astype(np.int16)
        n += 1
    np.save(folder / "gb50.npy", dem)
    meta = {"x0": X0, "y1": Y1, "cell": CELL, "nx": nx, "ny": ny, "units": "decimetres", "nodata": -32768,
            "tiles": n}
    (folder / "gb50.json").write_text(json.dumps(meta))
    valid = dem[dem != -32768]
    print(f"{n} tiles in {time.time() - t0:.0f} s; grid {nx}x{ny}; max {valid.max() / 10} m; "
          f"valid cells {valid.size:,}")


if __name__ == "__main__":
    main(sys.argv[1])
