"""Number audit: every number the map page (and the README) states, checked against the script output it comes from.

Each claim is a snippet that must appear in the page (whitespace collapsed) and a recomputation from results/ (or
from site/data/, built by scripts/build_site.py). Dates and figures taken from documents are listed as citations.
The page's legend and panel counts are computed in the browser from site/data/, so the audit checks pillars.json and
rays.geojson against results/, and the longest-lines list (longest.json) against results/gb_long_run.json (ids,
distances and order). It checks only the listed snippets: a new number added to the copy is not found by it.

Usage:  python -I scripts/audit_numbers.py      (after build_site.py; exits non-zero if any claim fails)
Writes: results/number_audit.md
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify_rays import INSTRUMENT_ON_MARK  # noqa: E402
from los import INSTRUMENT_ABOVE_TOP, PILLAR_TOP_ABOVE_GROUND  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
HANDBOOK = ("Copernicus DEM Product Handbook issue 5.0, p. 30: TanDEM-X/WorldDEM acquired December 2010 - January "
            "2015 (dataspace.copernicus.eu)")
BOOK = "History of the Retriangulation of Great Britain 1935-1962 (OS 1967)"


def page_text():
    """Page files with whitespace collapsed and JS string joins ("..." + "...") removed."""
    text = {f: " ".join((ROOT / "site" / f).read_text().split()) for f in ("index.html", "app.js")}
    text["README.md"] = " ".join((ROOT / "README.md").read_text().split())
    text["app.js"] = re.sub(r'"\s*\+\s*"', "", text["app.js"])
    return text


def load():
    j = lambda f: json.loads((R / f).read_text())  # noqa: E731
    rays = pd.read_csv(R / "rays_then_now.csv")
    return {"rays": j("rays_then_now.json"), "build": j("site_build.json"), "glo": j("glo30_gb.json"),
            "long": j("gb_long_run.json"), "ray_rows": rays, "misses": pd.read_csv(R / "misses_diagnosis.csv"),
            "primary": pd.read_csv(R / "primary_rays.csv"),
            "t50": json.loads((ROOT / "data" / "terrain50" / "gb50.json").read_text()),
            "site": ROOT / "site" / "data"}


def fmt(n):
    return f"{n:,}"


def rays_in_fig5(rows):
    return int(rows.figures.str.contains("5").sum())


def claims(d):
    """(file, snippet, recomputed text, ok, source) for every number on the page."""
    st, pp, f5 = d["rays"]["states"], d["rays"]["pillar_to_pillar"], d["rays"]["figure_5_eastern_counties"]
    b, rr = d["build"], d["ray_rows"]
    hens = rr[(rr.a_name == "Hensbarrow") | (rr.b_name == "Hensbarrow")]
    hm = d["misses"][(d["misses"].a_name == "Hensbarrow") | (d["misses"].b_name == "Hensbarrow")]
    # distance from the Hensbarrow end to each obstruction
    hkm = [r.obstruction_km_from_a if r.a_name == "Hensbarrow" else r.dist_km - r.obstruction_km_from_a
           for r in hm.itertuples()]
    df = rr[(rr.a_name == "Deerness") & (rr.b_name == "Fair Isle")].iloc[0]
    ned = rr[(rr.a == "PP240") | (rr.b == "PP240")].state.nunique()
    top, flips = d["long"]["longest_overall"][0], d["glo"]["precision_boxes_rerun"]["ben_wyvis"]["vs_precision_grid"]
    fig5 = rr.figures.str.contains("5")
    pp_miss = rr[rr.both_pillars & (rr.state == "terrain")]
    unk5 = rr[fig5 & (rr.state == "unknown")]
    tower = unk5.apply(lambda r: any(re.search(r"\b(twr|tower)\b", str(n), re.I) for n, t in
                                     ((r.a_name, r.a_type), (r.b_name, r.b_type)) if t != "PILLAR"), axis=1)
    ids = [r[0] for r in json.loads((d["site"] / "pillars.json").read_text())]
    sca = json.loads((d["site"] / "partners" / f"{ids.index('PP92') // 6}.json").read_text())["PP92"]
    pairs = set(zip(d["primary"].a, d["primary"].b)) | set(zip(d["primary"].b, d["primary"].a))
    i, a = "index.html", "app.js"
    yield i, "the 829 rays observed from both ends", d["rays"]["rays"], d["rays"]["rays"] == 829, "rays_then_now.json"
    yield i, "Bold coloured lines are 829 views", d["rays"]["rays"], d["rays"]["rays"] == 829, "rays_then_now.json"
    yield i, "Still clear</strong> (608)", st["clear"], st["clear"] == 608, "rays_then_now.json"
    yield i, "(50): clear over the terrain", st["surface"], st["surface"] == 50, "rays_then_now.json"
    yield i, "(35): not clear even over bare ground", st["terrain"], st["terrain"] == 35, "rays_then_now.json"
    yield i, "(136): one end is usually a bolt", st["unknown"], st["unknown"] == 136, "rays_then_now.json"
    yield (i, "Most are in the eastern lowlands", f"{f5['states']['terrain']} of {st['terrain']} are Figure 5",
           f5["states"]["terrain"] > st["terrain"] / 2, "rays_then_now.json")
    yield i, "the 6,079 standing pillars", fmt(b["pillars"]), b["pillars"] == 6079, "site_build.json"
    yield (i, "(1.22 m above ground) plus 0.25 m", f"{PILLAR_TOP_ABOVE_GROUND}, {INSTRUMENT_ABOVE_TOP}",
           round(PILLAR_TOP_ABOVE_GROUND, 2) == 1.22 and INSTRUMENT_ABOVE_TOP == 0.25, "scripts/los.py")
    yield i, "other marks get 1.5 m", INSTRUMENT_ON_MARK, INSTRUMENT_ON_MARK == 1.5, "scripts/classify_rays.py"
    yield i, "Every pair up to 250 km apart", d["long"]["range_km"][1], d["long"]["range_km"][1] == 250, \
        "gb_long_run.json"
    yield i, "a 50 m bare-earth model", d["t50"]["cell"], d["t50"]["cell"] == 50, "data/terrain50/gb50.json"
    yield (i, "refraction coefficient of 0.13 and ignoring 100 m at each end", f"{d['long']['k']}, {d['long']['skip_m']}",
           d["long"]["k"] == 0.13 and d["long"]["skip_m"] == 100, "gb_long_run.json, gb_full_run.py")
    yield i, "230,499 pairs are clear", fmt(b["lines"]), b["lines"] == 230_499, "site_build.json"
    yield "README.md", "It shows the 829 rays", d["rays"]["rays"], d["rays"]["rays"] == 829, "rays_then_now.json"
    yield "README.md", "over the 230,499 pairs", fmt(b["lines"]), b["lines"] == 230_499, "site_build.json"
    yield i, "a 30 m model", d["glo"]["grid_cell_m"], d["glo"]["grid_cell_m"] == 30, "glo30_gb.json"
    yield i, "them in 2010–15: 201,232 are still clear", fmt(b["surface_clear"]), b["surface_clear"] == 201_232, \
        "site_build.json; dates: " + HANDBOOK
    yield (i, "finds 612 of the 641 rays", f"{pp['t50_visible']} of {pp['rays']}",
           (pp["t50_visible"], pp["rays"]) == (612, 641), "rays_then_now.json, recall_sweep.csv")
    yield i, "(95.5%)", f"{pp['t50_visible'] / pp['rays']:.1%}", f"{pp['t50_visible'] / pp['rays']:.1%}" == "95.5%", \
        "rays_then_now.json"
    boxes = [v["vs_precision_grid"] for v in d["glo"]["precision_boxes_rerun"].values()]
    pct = [round(100 * v["flag_flips"] / v["lines"], 1) for v in boxes]
    yield (i, "changed the verdict on 0.2–1.4% of lines", "; ".join(f"{v['flag_flips']} of {v['lines']}" for v in boxes),
           sorted(pct) == [0.2, 1.4] and len(boxes) == 2, "glo30_gb.json (Ben Wyvis and Suffolk boxes)")
    yield (i, "mostly ones clearing by less than 1 m", f"p90 {[v['flipped_abs_clearance_p90_m'] for v in boxes]} m",
           all(v["flipped_abs_clearance_p90_m"] < 1 for v in boxes), "glo30_gb.json")
    yield (i, "Most of the misses are lowland rays in the eastern counties",
           f"{rays_in_fig5(pp_miss)} of {len(pp_miss)} pillar-to-pillar terrain misses are Figure 5",
           len(pp_miss) == pp["states"]["terrain"] and 2 * rays_in_fig5(pp_miss) > len(pp_miss), "rays_then_now.csv")
    yield i, "says it misses by 1.7 m", df.clear_t50, round(-df.clear_t50, 1) == 1.7, "rays_then_now.csv"
    for f, snip in ((i, "in 1936–62"), (i, "Between 1936 and 1962"), (i, "Great Britain 1935–1962</i>"),
                      ("README.md", "Between 1936 and 1962")):
        yield f, snip, "cited", True, BOOK
    for f, snip in ((i, "in the 2010–15 Copernicus surface model"), (i, "from 2010–15 for trees"),
                    (i, "a 2010–15 model of trees and buildings"),
                    ("README.md", "a 2010–15 model of trees and buildings"),
                    (i, "The surface model is 2010–15 radar"), (i, "but not over the 2010–15 surface model"),
                    (a, "also clear on the 2010–15 surface model; farthest"), (a, "Clear on the 2010–15 surface model"),
                    (a, "blocked by trees or buildings in the 2010–15 surface model")):
        yield f, snip, "cited", True, HANDBOOK
    # stories
    yield (a, "Four of the six rays the surveyors observed from Hensbarrow",
           f"{(hens.state == 'terrain').sum()} of {len(hens)}", (len(hens), (hens.state == "terrain").sum()) == (6, 4),
           "rays_then_now.csv")
    yield a, "ground up to 45 m above the sight line", -hm.clearance_m.min(), round(-hm.clearance_m.min()) == 45, \
        "misses_diagnosis.csv"
    yield (a, "0.2 to 2 km from the pillar", f"{min(hkm):.2f}-{max(hkm):.2f} km",
           round(min(hkm), 1) == 0.2 and round(max(hkm)) == 2, "misses_diagnosis.csv")
    yield a, "steel towers at no fewer than 34 of its primary stations", "cited", True, BOOK + ", p. 51, §2.130"
    s5 = f5["states"]
    yield (a, "Of its 226 observed rays, 63 are still clear in the 2010–15 surface model, 32 are blocked by trees or "
              "buildings, 29 by the terrain, and 102", f"{f5['rays']}: {s5['clear']}/{s5['surface']}/{s5['terrain']}/{s5['unknown']}",
           (f5["rays"], s5["clear"], s5["surface"], s5["terrain"], s5["unknown"]) == (226, 63, 32, 29, 102),
           "rays_then_now.json")
    yield (a, "on a station whose height was not recorded, mostly a tower", f"{tower.sum()} of {len(unk5)} on a tower",
           2 * tower.sum() > len(unk5) and len(unk5) == s5["unknown"], "rays_then_now.csv (station names)")
    yield a, "Nedging Tye, shown here, has all four", f"{ned} states", ned == 4, "rays_then_now.csv"
    yield a, "Deerness to Fair Isle: 92 km of sea", df.dist_km, round(df.dist_km) == 92, "rays_then_now.csv"
    yield a, "92 km apart across open sea", df.dist_km, round(df.dist_km) == 92, "rays_then_now.csv"
    yield a, "the model says the line misses by 1.7 m", df.clear_t50, round(-df.clear_t50, 1) == 1.7, \
        "rays_then_now.csv"
    yield (a, "runs 231.9 km from Merrick", f"{top['a_name']} - {top['b_name']} {top['dist_km']}",
           (top["a_name"], top["b_name"], round(top["dist_km"], 1)) == ("Merrick", "Snowdon Summit", 231.9),
           "gb_long_run.json")
    yield a, "clearing the terrain by 7.7 m", top["clearance_m"], top["clearance_m"] == 7.7, "gb_long_run.json"
    yield (a, "clear on the 2010–15 surface model too", b["longest"][0]["surface_clear"], b["longest"][0]["surface_clear"] == 1,
           "site_build.json")
    yield (a, "It was not one of the observed rays", "pair absent", ("PP301", "SH62/T66") not in pairs,
           "primary_rays.csv")
    m = b["most_partners"]
    yield a, "Sca Fell: 448 pillars in view", m["partners"], (m["id"], m["partners"]) == ("PP92", 448), \
        "site_build.json"
    yield (a, "finds 448 other pillars in view over the terrain, more than from any other pillar, and 435 of them are "
              "also clear on the 2010–15 surface model", f"{m['partners']}, {m['surface_clear']}",
           (m["partners"], m["surface_clear"]) == (448, 435), "site_build.json")
    yield a, "The farthest is Cader Idris, 200.6 km", sca[-1][1], sca[-1][1] == 200.6, "site/data/partners/ (PP92)"


def data_checks(d):
    """The browser computes the legend and panel numbers from site/data/; check those files match results/."""
    rays = json.loads((d["site"] / "rays.geojson").read_text())["features"]
    rows = json.loads((d["site"] / "pillars.json").read_text())
    st = pd.Series([f["properties"]["st"] for f in rays]).value_counts().to_dict()
    n, s = sum(r[5] for r in rows) / 2, sum(r[6] for r in rows) / 2
    yield "legend: ray states", st, st == {k: v for k, v in d["rays"]["states"].items() if v}, "rays_then_now.json"
    yield "legend: lines, surface-clear", (n, s), (n, s) == (d["build"]["lines"], d["build"]["surface_clear"]), \
        "site_build.json"
    yield "legend: surface-blocked", n - s, n - s == d["glo"]["lines"] - d["glo"]["surface_clear"], "glo30_gb.json"
    names = {r[0]: r[1] for r in rows}
    page = [(names[a], names[b], km) for a, b, km, _ in json.loads((d["site"] / "longest.json").read_text())]
    run = [(x["a_name"], x["b_name"], round(x["dist_km"], 1)) for x in d["long"]["longest_overall"]]
    yield "longest.json: ids (as names), km, order", f"{len(page)} lines, first {page[0]}", page == run, "gb_long_run.json"


def main():
    text, d = page_text(), load()
    out = ["# Number audit", "", "Generated by `scripts/audit_numbers.py`. Each row is a number the map page states,",
           "found by its exact wording in `site/` and recomputed from the named output.", "",
           "| File | Wording on the page | Recomputed | OK | Source |", "|---|---|---|---|---|"]
    bad = 0
    for f, snip, val, ok, src in claims(d):
        found = snip in text[f]
        bad += not (ok and found)
        mark = "yes" if ok and found else ("WORDING NOT FOUND" if not found else "MISMATCH")
        out.append(f"| {f} | {snip.replace('|', '/')} | {val} | {mark} | {src} |")
    out += ["", "## Numbers the page computes from `site/data/`", "", "| Check | Value | OK | Source |", "|---|---|---|---|"]
    for name, val, ok, src in data_checks(d):
        bad += not ok
        out.append(f"| {name} | {val} | {'yes' if ok else 'MISMATCH'} | {src} |")
    (R / "number_audit.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))
    if bad:
        sys.exit(f"{bad} claim(s) failed")


if __name__ == "__main__":
    main()
