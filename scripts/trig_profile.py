"""Profile the OS Complete Trig Archive: counts by type, order and condition, height coverage and datum.

Usage:  python -I scripts/trig_profile.py data/trig/x/CompleteTrigArchive.csv
Writes: results/trig_profile.json, results/trig_profile.md
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def vc(s, n=30):
    return {str(k): int(v) for k, v in s.value_counts(dropna=False).head(n).items()}


def main(path):
    d = pd.read_csv(path, encoding="latin-1")
    pil = d[d["TYPE OF MARK"].eq("PILLAR")]
    live = pil[pil["DESTROYED MARK INDICATOR"].eq(0)]
    # one physical pillar can appear more than once (recomputed or refixed records share a station name)
    uniq_live = live.drop_duplicates("STATION NAME")
    comments = pil["COMMENTS"].fillna("").str.upper()
    out = {
        "source": "https://www.ordnancesurvey.co.uk/documents/gps/CompleteTrigArchive.zip",
        "records": len(d),
        "columns": list(d.columns),
        "type_of_mark": vc(d["TYPE OF MARK"], 40),
        "order": vc(d["ORDER"]),
        "destroyed_indicator_all": vc(d["DESTROYED MARK INDICATOR"]),
        "pillars": {
            "records": len(pil),
            "destroyed_indicator": vc(pil["DESTROYED MARK INDICATOR"]),
            "not_destroyed_records": len(live),
            "not_destroyed_unique_station_names": len(uniq_live),
            "order": vc(pil["ORDER"]),
            "height_gt_0": int((pil["HEIGHT"] > 0).sum()),
            "height_eq_0": int((pil["HEIGHT"] == 0).sum()),
            "levelling_datum": vc(pil["LEVELLING DATUM"]),
            "class_of_levelling": vc(pil["CLASS OF LEVELLING"]),
            "comment_height_to_top_of_pillar": int(comments.str.contains("TOP OF PILLAR").sum()),
            "comment_gps_height": int(comments.str.contains("GPS H").sum()),
        },
    }
    (ROOT / "results" / "trig_profile.json").write_text(json.dumps(out, indent=2))
    p = out["pillars"]
    md = [
        "# OS Complete Trig Archive profile", "",
        f"Source: {out['source']} (downloaded 2026-10-20). Script: `scripts/trig_profile.py`.", "",
        f"- Records: {out['records']:,}",
        f"- PILLAR records: {p['records']:,}; not destroyed (indicator 0): {p['not_destroyed_records']:,} "
        f"({p['not_destroyed_unique_station_names']:,} unique station names)",
        f"- Pillars with HEIGHT > 0: {p['height_gt_0']:,}; HEIGHT = 0 (no height): {p['height_eq_0']:,}",
        f"- Pillar comments saying the height is to the top of the pillar: {p['comment_height_to_top_of_pillar']}",
        "", "## Pillars by levelling datum", "",
        "| Datum code | Pillars |", "|---|---|",
        *[f"| {k} | {v:,} |" for k, v in p["levelling_datum"].items()],
        "", "## Pillars by order", "", "| Order | Pillars |", "|---|---|",
        *[f"| {k} | {v:,} |" for k, v in p["order"].items()],
        "", "## Pillars by destroyed-mark indicator", "", "| Indicator | Pillars |", "|---|---|",
        *[f"| {k} | {v:,} |" for k, v in p["destroyed_indicator"].items()],
        "", "## All records by type of mark (top 40)", "", "| Type | Records |", "|---|---|",
        *[f"| {k} | {v:,} |" for k, v in out["type_of_mark"].items()],
        "", "## All records by order", "", "| Order | Records |", "|---|---|",
        *[f"| {k} | {v:,} |" for k, v in out["order"].items()], "",
    ]
    (ROOT / "results" / "trig_profile.md").write_text("\n".join(md))
    print("\n".join(md[:12]))


if __name__ == "__main__":
    main(sys.argv[1])
