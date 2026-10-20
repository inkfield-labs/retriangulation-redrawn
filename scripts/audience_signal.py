"""Passive audience signal: trigpointing.uk site stats and YouTube engagement on trig videos.

Writes results/audience_trigpointing_stats.json and results/audience_youtube.csv.
Read-only requests; nothing is posted anywhere.
"""
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results"
UA = {"User-Agent": "Mozilla/5.0 (retriangulation-redrawn investigation)"}
QUERIES = ["trig pillar", "trig points", "triangulation pillar ordnance survey", "retriangulation of great britain",
           "trig pillar line of sight"]


def trigpointing_stats():
    url = "https://api.trigpointing.uk/v1/stats/site"
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    out = {"url": url, "fetched": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), "stats": r.json()}
    (OUT / "audience_trigpointing_stats.json").write_text(json.dumps(out, indent=2))
    return out


def youtube(query):
    url = "https://www.youtube.com/results"
    r = requests.get(url, params={"search_query": query}, headers=UA, timeout=30)
    r.raise_for_status()
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", r.text)
    if not m:
        return []
    rows = []

    def walk(o):
        if isinstance(o, dict):
            if "videoRenderer" in o:
                v = o["videoRenderer"]
                views = v.get("viewCountText", {}).get("simpleText", "")
                rows.append({
                    "query": query,
                    "video_id": v.get("videoId"),
                    "title": "".join(x["text"] for x in v.get("title", {}).get("runs", [])),
                    "channel": "".join(x["text"] for x in v.get("ownerText", {}).get("runs", [])),
                    "views": int(re.sub(r"\D", "", views) or 0),
                    "published": v.get("publishedTimeText", {}).get("simpleText", ""),
                })
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(json.loads(m.group(1)))
    return rows


def main():
    s = trigpointing_stats()
    print("trigpointing.uk:", s["stats"])
    seen, rows = set(), []
    for q in QUERIES:
        for row in youtube(q):
            if row["video_id"] not in seen:
                seen.add(row["video_id"])
                rows.append(row)
    rows.sort(key=lambda r: -r["views"])
    with open(OUT / "audience_youtube.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"youtube: {len(rows)} unique videos across {len(QUERIES)} queries; fetched {dt.date.today()}")
    for r in rows[:15]:
        print(f"{r['views']:>10,}  {r['channel'][:28]:28}  {r['title'][:80]}")


if __name__ == "__main__":
    sys.exit(main())
