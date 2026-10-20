"""Terrain line-of-sight between station pairs on the OS Terrain 50 mosaic.

Model, for a pair A-B at distance D:
    sight line z(x) = zA + (zB - zA) * x / D
    effective terrain t(x) = h(x) + x * (D - x) / (2 * R / (1 - k))   (Earth curvature with refraction coefficient k)
    blocked if t(x) > z(x) anywhere on the profile, ignoring `skip` metres next to each end
Station sight heights zA, zB are passed in (see station_heights()). h(x) is bilinear on the 50 m grid.
"""
import json
from pathlib import Path

import numpy as np

R_EARTH = 6_371_000.0
ROOT = Path(__file__).resolve().parent.parent

# Pillar geometry from Fig. 2.2 of the History (book p. 15): the pillar rises 4 ft (1.219 m) above ground, and the
# published height is the flush-bracket arrow, which the scaled figure puts about 0.40 m above ground. The theodolite
# axis or beacon sits about 0.25 m above the pillar top (assumption, stated in the report).
PILLAR_TOP_ABOVE_GROUND = 1.219
FB_ABOVE_GROUND = 0.40
INSTRUMENT_ABOVE_TOP = 0.25


class DEM:
    def __init__(self, folder=ROOT / "data" / "terrain50", factor=1):
        meta = json.loads((Path(folder) / "gb50.json").read_text())
        a = np.load(Path(folder) / "gb50.npy", mmap_mode="r")
        if factor > 1:  # coarsen by block mean, to test sensitivity to resolution
            ny, nx = (a.shape[0] // factor) * factor, (a.shape[1] // factor) * factor
            b = np.asarray(a[:ny, :nx], dtype=np.float32)
            b[b == meta["nodata"]] = np.nan
            b = np.nanmean(b.reshape(ny // factor, factor, nx // factor, factor), axis=(1, 3))
            self.z = np.nan_to_num(b / 10.0, nan=0.0).astype(np.float32)
        else:
            z = np.asarray(a, dtype=np.float32) / 10.0
            z[a == meta["nodata"]] = 0.0  # sea and off-grid
            self.z = z
        self.cell = meta["cell"] * factor
        self.x0, self.y1 = meta["x0"], meta["y1"]

    def sample(self, e, n):
        """Bilinear height at National Grid coordinates (arrays); cell values taken at cell centres."""
        c = (np.asarray(e) - self.x0) / self.cell - 0.5
        r = (self.y1 - np.asarray(n)) / self.cell - 0.5
        c0 = np.clip(np.floor(c).astype(np.int64), 0, self.z.shape[1] - 2)
        r0 = np.clip(np.floor(r).astype(np.int64), 0, self.z.shape[0] - 2)
        fc, fr = np.clip(c - c0, 0, 1), np.clip(r - r0, 0, 1)
        z = self.z
        return ((z[r0, c0] * (1 - fc) + z[r0, c0 + 1] * fc) * (1 - fr) +
                (z[r0 + 1, c0] * (1 - fc) + z[r0 + 1, c0 + 1] * fc) * fr)


def station_heights(height, comments, ground_dem, mode="fb"):
    """Sight height (m ODN) for each station.

    mode "fb":  archive HEIGHT is the flush bracket, so sight = HEIGHT - FB + top + instrument.
                Where HEIGHT is 0 or missing, fall back to DEM ground + top + instrument.
                Where the archive comment says the height is to the pillar top, sight = HEIGHT + instrument.
    mode "dem": ignore archive heights; sight = DEM ground + top + instrument.
    """
    height = np.asarray(height, dtype=float)
    comments = np.asarray(comments, dtype=object)
    top = PILLAR_TOP_ABOVE_GROUND + INSTRUMENT_ABOVE_TOP
    from_dem = ground_dem + top
    if mode == "dem":
        return from_dem, np.full(height.shape, "dem")
    fb = height - FB_ABOVE_GROUND + top
    to_top = np.array([isinstance(c, str) and "TOP OF PILLAR" in c.upper() for c in comments])
    fb = np.where(to_top, height + INSTRUMENT_ABOVE_TOP, fb)
    use_dem = ~(height > 0)
    src = np.where(use_dem, "dem", np.where(to_top, "top", "fb"))
    return np.where(use_dem, from_dem, fb), src


def clearance(dem, ea, na, za, eb, nb, zb, k=0.13, step=None, skip=100.0, chunk=2_000_000):
    """Minimum clearance (m) of the sight line over effective terrain, for each pair. Positive = visible."""
    ea, na, za, eb, nb, zb = (np.asarray(v, dtype=np.float64) for v in (ea, na, za, eb, nb, zb))
    step = step or dem.cell
    d = np.hypot(eb - ea, nb - na)
    nsamp = np.maximum(np.ceil(d / step).astype(np.int64), 1)
    out = np.full(d.shape, np.inf)
    reff = R_EARTH / (1.0 - k)
    # process pairs in batches whose total sample count is about `chunk`
    order = np.arange(len(d))
    csum = np.cumsum(nsamp)
    start = 0
    while start < len(d):
        stop = int(np.searchsorted(csum, (csum[start - 1] if start else 0) + chunk, side="right"))
        stop = max(stop, start + 1)
        idx = order[start:stop]
        ns = nsamp[idx]
        pair = np.repeat(np.arange(len(idx)), ns)
        j = np.arange(ns.sum()) - np.repeat(np.cumsum(ns) - ns, ns)
        f = (j + 0.5) / ns[pair]
        D = d[idx][pair]
        x = f * D
        keep = (x > skip) & (D - x > skip)
        e = ea[idx][pair] + (eb[idx][pair] - ea[idx][pair]) * f
        n = na[idx][pair] + (nb[idx][pair] - na[idx][pair]) * f
        h = dem.sample(e, n)
        sight = za[idx][pair] + (zb[idx][pair] - za[idx][pair]) * f
        c = sight - (h + x * (D - x) / (2.0 * reff))
        c = np.where(keep, c, np.inf)
        res = np.full(len(idx), np.inf)
        np.minimum.at(res, pair, c)
        out[idx] = res
        start = stop
    return out
