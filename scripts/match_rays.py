"""Match the OCR'd primary-ray station names to first-order stations in the OS Complete Trig Archive.

Inputs:  results/primary_rays_raw.csv (from extract_primary_rays.py), the OS CompleteTrigArchive.csv
Outputs: results/primary_rays_directions.csv  one row per observed direction, with match status
         results/primary_rays.csv             one row per unique undirected station pair (the ground truth)
         results/primary_rays_unmatched.csv   names that could not be matched

Usage: python -I scripts/match_rays.py data/trig/x/CompleteTrigArchive.csv
"""
import difflib
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ALIASES = {"twr": "tower", "wtr": "water", "ch": "church", "lighthse": "lighthouse", "lighthse": "lighthouse"}


def norm(s):
    s = s.lower().replace("’", "'").replace("*", "'")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\b\w{1,3}\)", " ", s)  # stray OCR'd station codes such as "CD)"
    s = re.sub(r"[^a-z ]", " ", s)
    s = s.replace("rn", "m")  # OCR reads "rn" as "m" (Carn -> Cam); fold both sides the same way
    words = [ALIASES.get(w, w) for w in s.split()]
    return " ".join(words)


def load_primary(csv_path):
    d = pd.read_csv(csv_path, encoding="latin-1")
    p = d[(d["ORDER"] == 1) & d["STATION NAME"].str.match(r"^/?PP\d+$", na=False)].copy()
    p["pp"] = p["STATION NAME"].str.lstrip("/")
    # prefer a surviving record per PP number, then the most recent one
    p["alive"] = p["DESTROYED MARK INDICATOR"].eq(0)
    p = p.sort_values(["pp", "alive"], ascending=[True, False]).drop_duplicates("pp")
    p["key"] = p["Trig Name"].map(norm)
    return p


def build_matcher(primary):
    keys = dict(zip(primary["key"], primary["pp"]))
    # also index by name with any "(...)" qualifier and trailing words removed, e.g. "Ben More (Mull)" -> "ben more"
    for name, pp in zip(primary["Trig Name"], primary["pp"]):
        keys.setdefault(norm(re.sub(r"\(.*?\)", "", name)), pp)

    def one(raw):
        k = norm(raw)
        if not k:
            return None
        if k in keys:
            return keys[k]
        m = difflib.get_close_matches(k, keys, n=1, cutoff=0.85)
        if m:
            return keys[m[0]]
        # names wrapped onto a second line keep only their first part, e.g. "Carn nan-tri-" or "Weeton Res'r"
        pre = {keys[x] for x in keys if len(k) >= 6 and (x.startswith(k) or k.startswith(x + " pillar"))}
        if len(pre) == 1:
            return pre.pop()
        pre = {keys[x] for x in keys if len(k) >= 6 and x.split()[0] == k.split()[0] and
               difflib.SequenceMatcher(None, k, x[:len(k)]).ratio() > 0.85}
        return pre.pop() if len(pre) == 1 else None

    def many(raw):
        """Return the list of stations in a cell; OCR sometimes merges two or three cells into one."""
        hit = one(raw)
        if hit:
            return [hit]
        words = raw.split()
        for i in range(1, len(words)):
            a = one(" ".join(words[:i]))
            if a:
                rest = many(" ".join(words[i:]))
                if rest:
                    return [a] + rest
        return []

    return one, many


def main(csv_path):
    primary = load_primary(csv_path)
    one, many = build_matcher(primary)
    raw = pd.read_csv(ROOT / "results" / "primary_rays_raw.csv")
    out, unmatched = [], []
    for r in raw.itertuples():
        f = many(str(r.from_name))
        t = many(str(r.to_name))
        if len(f) > 1:
            f = f[-1:]  # merged From cells: the last name is the station whose rows follow
        status = "ok" if (f and t) else "unmatched"
        if not f:
            unmatched.append(("from", r.from_name))
        if not t:
            unmatched.append(("to", r.to_name))
        for tt in t or [None]:
            out.append({"figure": r.figure, "pdf_page": r.pdf_page, "from_raw": r.from_name, "to_raw": r.to_name,
                        "from_pp": f[0] if f else None, "to_pp": tt, "status": status,
                        "split": len(t) > 1})
    dirs = pd.DataFrame(out)
    dirs.to_csv(ROOT / "results" / "primary_rays_directions.csv", index=False)
    pd.DataFrame(unmatched, columns=["column", "raw"]).value_counts().rename("n").reset_index().to_csv(
        ROOT / "results" / "primary_rays_unmatched.csv", index=False)

    ok = dirs[(dirs.status == "ok") & (dirs.from_pp != dirs.to_pp)].copy()
    ok["a"] = ok[["from_pp", "to_pp"]].min(axis=1)
    ok["b"] = ok[["from_pp", "to_pp"]].max(axis=1)
    g = ok.groupby(["a", "b"]).agg(n_directions=("figure", "size"), figures=("figure", lambda s: sorted(set(s))))
    g = g.reset_index()
    info = primary.set_index("pp")
    for end in "ab":
        for col, src in [("name", "Trig Name"), ("type", "TYPE OF MARK"), ("e", "EASTING"), ("n", "NORTHING"),
                         ("height", "HEIGHT"), ("destroyed", "DESTROYED MARK INDICATOR"), ("comments", "COMMENTS")]:
            g[f"{end}_{col}"] = g[end].map(info[src])
    g["dist_km"] = np.hypot(g.a_e - g.b_e, g.a_n - g.b_n) / 1000
    g["both_pillars"] = g.a_type.eq("PILLAR") & g.b_type.eq("PILLAR")
    g.to_csv(ROOT / "results" / "primary_rays.csv", index=False)

    n_dir = len(dirs)
    print(f"directions: {n_dir} rows; matched {int((dirs.status == 'ok').sum())}, "
          f"unmatched {int((dirs.status != 'ok').sum())}, from split cells {int(dirs.split.sum())}")
    print(f"unique undirected rays: {len(g)}; both ends PILLAR: {int(g.both_pillars.sum())}; "
          f"observed from both ends: {int((g.n_directions >= 2).sum())}")
    rec = g[g.both_pillars & (g.n_directions >= 2)]
    print(f"ground truth (both ends PILLAR, observed from both ends): {len(rec)} rays; "
          f"dist km min {rec.dist_km.min():.1f} median {rec.dist_km.median():.1f} max {rec.dist_km.max():.1f}")
    print(f"stations used: {len(set(g.a) | set(g.b))} of {len(primary)} first-order PP records")
    print(g.dist_km.describe().round(1).to_string())


if __name__ == "__main__":
    main(sys.argv[1])
