"""Private spot check: do the model's per-line verdicts match what visitors write in trigpointing.uk logs?

Samples 30 visible lines (8 / 8 / 7 / 7 across upland or lowland x surface-clear or surface-blocked), matches each
pillar to a trigpointing.uk trig by position and name, reads the pillars' public logs through the site's API, and
classifies every mention of the other pillar as SEEN, NOT_SEEN or AMBIGUOUS with hand-written rules.

Terms: the site's Terms Of Use (wiki, sections "Accuracy of information", "Dangerous locations", "Private land",
"Copyright") say nothing about automated access; robots.txt allows all agents. Read-only GETs, at most 1 per second,
at most MAX_REQUESTS in total, identifying User-Agent. Every response is cached, so a rerun makes no requests.
Downloaded responses are untrusted data: they are parsed as JSON and never executed.

Usage:  python -I scripts/spot_check.py fetch    (sample, then download what is not cached yet; network)
        python -I scripts/spot_check.py run      (same sample from the cache only, classify, write results; offline)
Reads:  data/gb_lines.csv, data/gb_lines_long.csv, data/gb_surface.csv, site/data/pillars.json
Writes: data/spotcheck/raw/*.json (responses), data/spotcheck/evidence.json (excerpts; git-ignored),
        results/spot_check.json (counts and parameters only)
"""
import html
import json
import math
import random
import re
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "spotcheck"
RAW = CACHE / "raw"
API = "https://api.trigpointing.uk/v1/"
USER_AGENT = "retriangulation-redrawn spot check (private research)"
MIN_INTERVAL_S = 1.05
MAX_REQUESTS = 600
PRIOR_REQUESTS = 12     # hand-made GETs while reading the terms and the API description, before this script existed
SEED = 12
STRATA = [  # name, quota, upland?, surface clear?
    ("upland_clear", 8, True, True), ("upland_blocked", 8, True, False),
    ("lowland_clear", 7, False, True), ("lowland_blocked", 7, False, False),
]
UPLAND_MIN_M, LOWLAND_MAX_M = 300, 100
MIN_LOGS = 10           # preferred log count for both pillars of a sampled line
MAX_CANDIDATES = 30     # lines examined per stratum while looking for pairs with enough logs
PAGE = 100              # API maximum
MAX_PAGES = 10          # logs read per pillar: at most PAGE * MAX_PAGES
MATCH_M = 50
NAME_SIMILARITY = 0.75
SUFFIXES = {"hill", "hills", "beacon", "farm", "fell", "down", "moor", "top", "head", "mountain", "mount",
            "common", "wood", "tor", "pike"}
GENERIC = {"green", "north", "south", "east", "west", "great", "little", "long", "high", "low", "upper", "lower",
           "old", "new", "white", "black", "red", "big", "round", "castle", "cairn", "church", "mill", "park"}

NOT_SEEN_RE = re.compile(
    r"\b(can'?t|cannot|can not|couldn'?t|could not|unable to|wasn'?t able|not able to|didn'?t|did not|never|no)\b"
    r"[^.;]{0,30}\b(see|seen|view|visible|spot|spotted|make out)\b"
    r"|\b(not|barely|hardly) (visible|in view|in sight|seen)\b|\binvisible\b|\bhidden\b|\bobscured\b"
    r"|\bblocked (by|from)\b|\b(out of|not in) (sight|view)\b|\bbehind (the |a )?(trees|forest|hill|ridge)\b"
    r"|\b(trees|forest|conifers|plantation)\b[^.;]{0,40}\b(block|obscur|hid)")
SEEN_RE = re.compile(
    r"\b(can|could|able to|managed to)\s+(clearly |easily |also |just |just about |even )?(see|spot|make out)\b"
    r"|\bsaw\b|\bseen\b|\bvisible\b|\bin view\b|\bin sight\b|\bspotted\b|\bpicked out\b|\bviews? (of|to|towards)\b"
    r"|\bpanoram|\bviews? includ")


# --- cache and network -------------------------------------------------------------------------------------------

def cache_path(url):
    return RAW / (re.sub(r"[^A-Za-z0-9._=-]+", "_", url[len(API):]) + ".json")


def requests_so_far():
    return PRIOR_REQUESTS + len(list(RAW.glob("*.json")))


class Getter:
    """Returns the parsed JSON for an API path, from the cache; online mode downloads what is missing."""

    def __init__(self, online):
        self.online, self.made, self.last = online, 0, 0.0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        RAW.mkdir(parents=True, exist_ok=True)

    def get(self, path):
        f = cache_path(API + path)
        if f.exists():
            return json.loads(f.read_text())
        if not self.online:
            raise SystemExit(f"not cached (run fetch first): {path}")
        if requests_so_far() >= MAX_REQUESTS:
            raise SystemExit(f"request cap of {MAX_REQUESTS} reached before: {path}")
        time.sleep(max(0.0, self.last + MIN_INTERVAL_S - time.time()))
        r = self.session.get(API + path, timeout=120)
        self.last = time.time()
        self.made += 1
        if r.status_code != 200:
            raise SystemExit(f"unreachable or refused: HTTP {r.status_code} for {path}")
        data = r.json()
        f.write_text(json.dumps(data))
        return data


def log_pages(g, trig_id, first_only):
    """All cached/downloaded log pages of one trig (at most PAGE * MAX_PAGES logs) and the site's total log count."""
    first = g.get(f"trigs/{trig_id}/logs?limit={PAGE}&skip=0")
    total, logs = first["pagination"]["total"], list(first["items"])
    if not first_only:
        for skip in range(PAGE, min(total, PAGE * MAX_PAGES), PAGE):
            logs += g.get(f"trigs/{trig_id}/logs?limit={PAGE}&skip={skip}")["items"]
    return total, logs


# --- matching pillars to trigpointing.uk trigs --------------------------------------------------------------------

def norm(name):
    name = re.sub(r"\(.*?\)", " ", name.lower().replace("’", "'"))
    name = re.sub(r"\b(trig|pillar|trigpoint)\b", " ", name)
    return re.sub(r"[^a-z0-9]+", "", name)


def names_agree(a, b):
    a, b = norm(a), norm(b)
    return bool(a and b) and (a in b or b in a or SequenceMatcher(None, a, b).ratio() >= NAME_SIMILARITY)


def xy(lon, lat):
    """Equirectangular metres, good enough to shortlist neighbours; exact distance is checked afterwards."""
    lat0 = np.radians(lat)
    return np.column_stack([np.asarray(lon) * 111320 * np.cos(lat0), np.asarray(lat) * 110570])


def metres(lon1, lat1, lon2, lat2):
    dx = (lon2 - lon1) * 111320 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, (lat2 - lat1) * 110570)


class Matcher:
    """Nearest trigpointing.uk trig within MATCH_M of a pillar whose name agrees; trigs of category PILLAR win ties."""

    def __init__(self, trigs):
        self.trigs = [t for t in trigs if t["wgs_lat"] is not None and t["wgs_long"] is not None]
        lon = np.array([t["wgs_long"] for t in self.trigs])
        lat = np.array([t["wgs_lat"] for t in self.trigs])
        self.tree = cKDTree(np.column_stack([lon * 111320 * math.cos(math.radians(54.5)), lat * 110570]))

    def match(self, pillar):
        """Returns (trig or None, reason): reason is 'matched', 'no trig within 50 m' or 'name differs'."""
        _, name, lon, lat = pillar[:4]
        near = self.tree.query_ball_point([lon * 111320 * math.cos(math.radians(54.5)), lat * 110570], MATCH_M * 1.6)
        within = sorted(((metres(lon, lat, self.trigs[i]["wgs_long"], self.trigs[i]["wgs_lat"]), i) for i in near))
        within = [(d, i) for d, i in within if d <= MATCH_M]
        if not within:
            return None, "no trig within 50 m"
        ok = [(self.trigs[i]["category_code"] != "PILLAR", d, i) for d, i in within
              if names_agree(name, self.trigs[i]["name"])]
        return (self.trigs[min(ok)[2]], "matched") if ok else (None, "name differs")


# --- sampling ---------------------------------------------------------------------------------------------------

def load_lines():
    lines = pd.concat([pd.read_csv(ROOT / "data" / n) for n in ("gb_lines.csv", "gb_lines_long.csv")])
    lines = lines.merge(pd.read_csv(ROOT / "data" / "gb_surface.csv"), on=["a", "b"])
    pillars = {p[0]: p for p in json.loads((ROOT / "site" / "data" / "pillars.json").read_text())}
    lines["ha"] = lines.a.str.replace("/", "-").map({k: v[4] for k, v in pillars.items()})
    lines["hb"] = lines.b.str.replace("/", "-").map({k: v[4] for k, v in pillars.items()})
    return lines, pillars


def stratum_lines(lines, upland, clear):
    if upland:
        sel = (lines.ha >= UPLAND_MIN_M) & (lines.hb >= UPLAND_MIN_M)
    else:
        sel = (lines.ha <= LOWLAND_MAX_M) & (lines.hb <= LOWLAND_MAX_M)
    sel &= (lines.clear_glo30 > 0) == clear
    return lines[sel].sort_values(["a", "b"]).reset_index(drop=True)


def sample(g, lines, pillars, matcher):
    """The 30 lines plus bookkeeping. Candidates are shuffled with a fixed seed; the first quota lines whose pillars
    both match a trig and both have at least MIN_LOGS logs are taken. If MAX_CANDIDATES lines do not give a quota,
    lines with matched pillars but fewer logs fill the stratum."""
    trig_of, log_total = {}, {}

    def trig(pid):
        if pid not in trig_of:
            trig_of[pid] = matcher.match(pillars[pid.replace("/", "-")])
        return trig_of[pid]

    def count(pid):
        t = trig(pid)[0]
        if t["id"] not in log_total:
            log_total[t["id"]] = log_pages(g, t["id"], first_only=True)[0]
        return log_total[t["id"]]

    chosen, stats = [], {}
    for name, quota, upland, clear in STRATA:
        cand = stratum_lines(lines, upland, clear)
        order = list(range(len(cand)))
        random.Random(f"{SEED}-{name}").shuffle(order)
        good, thin, unmatched, examined = [], [], 0, 0
        for i in order[:MAX_CANDIDATES]:
            if len(good) == quota:
                break
            examined += 1
            row = cand.iloc[i]
            if trig(row.a)[0] is None or trig(row.b)[0] is None:
                unmatched += 1
            elif count(row.a) >= MIN_LOGS and count(row.b) >= MIN_LOGS:
                good.append(row)
            else:
                thin.append(row)
        picked = (good + thin)[:quota]
        stats[name] = {"candidate_lines": len(cand), "examined": examined,
                       "dropped_unmatched_pillar": unmatched, "both_pillars_min_logs": len(good),
                       "filled_with_fewer_logs": len(picked) - len(good)}
        chosen += [(name, clear, r) for r in picked]
    return chosen, trig_of, stats


def match_summary(matcher, pillars, trig_of):
    """Match outcome over all pillars (offline, from the export) and over the pillars of the examined lines."""
    reasons = [matcher.match(p)[1] for p in pillars.values()]
    out = {r: reasons.count(r) for r in ("matched", "no trig within 50 m", "name differs")}
    out["pillars_total"] = len(reasons)
    out["examined_pillars_matched"] = sum(t is not None for t, _ in trig_of.values())
    out["examined_pillars_total"] = len(trig_of)
    return out


# --- evidence ---------------------------------------------------------------------------------------------------

def name_variants(*names):
    """Lower-case search strings for a pillar: each name without brackets, and without a common suffix if distinctive."""
    out = set()
    for name in names:
        base = re.sub(r"\s+", " ", re.sub(r"\(.*?\)", " ", name.lower().replace("’", "'"))).strip()
        out.add(base)
        words = base.split()
        if len(words) > 1 and words[-1] in SUFFIXES:
            short = " ".join(words[:-1])
            if len(short) >= 5 and short not in GENERIC:
                out.add(short)
    return {v for v in out if len(v) >= 4}


def clean(text):
    return html.unescape(re.sub(r"<[^>]+>", " ", text or "")).replace("’", "'")


def classify_sentence(sentence):
    s = sentence.lower()
    not_seen, seen = bool(NOT_SEEN_RE.search(s)), bool(SEEN_RE.search(NOT_SEEN_RE.sub(" ", s)))
    return "NOT_SEEN" if not_seen and not seen else "SEEN" if seen and not not_seen else "AMBIGUOUS"


def mentions(logs, variants, side):
    found = []
    pattern = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(v) for v in sorted(variants, key=len, reverse=True)) + r")(?![a-z0-9])")
    for log in logs:
        text = clean(log["comment"])
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
            if pattern.search(sentence.lower()):
                found.append({"in_logs_of": side, "log_id": log["id"], "sentence": sentence.strip()[:400],
                              "class": classify_sentence(sentence)})
    return found


def line_class(found):
    classes = {m["class"] for m in found}
    if not found:
        return "NO_EVIDENCE"
    if classes == {"SEEN"}:
        return "SEEN"
    if classes == {"NOT_SEEN"}:
        return "NOT_SEEN"
    return "AMBIGUOUS"


def gather(g, chosen, trig_of):
    evidence = []
    for name, clear, row in chosen:
        ta, tb = trig_of[row.a][0], trig_of[row.b][0]
        total_a, logs_a = log_pages(g, ta["id"], first_only=False)
        total_b, logs_b = log_pages(g, tb["id"], first_only=False)
        found = (mentions(logs_a, name_variants(row.b_name, tb["name"]), "a")
                 + mentions(logs_b, name_variants(row.a_name, ta["name"]), "b"))
        evidence.append({"stratum": name, "surface_clear": clear, "a": row.a, "b": row.b, "a_name": row.a_name,
                         "b_name": row.b_name, "trig_a": ta["id"], "trig_b": tb["id"], "logs_total_a": total_a,
                         "logs_total_b": total_b, "logs_read_a": len(logs_a), "logs_read_b": len(logs_b),
                         "class": line_class(found), "mentions": found})
    return evidence


# --- results ----------------------------------------------------------------------------------------------------

def tally(rows):
    out = {"lines": len(rows)}
    out.update({c: sum(r["class"] == c for r in rows) for c in ("SEEN", "NOT_SEEN", "AMBIGUOUS", "NO_EVIDENCE")})
    agree = sum((r["class"] == "SEEN" and r["surface_clear"]) or (r["class"] == "NOT_SEEN" and not r["surface_clear"])
                for r in rows)
    evaluable = out["SEEN"] + out["NOT_SEEN"]
    out["agreement"] = {"agree": agree, "evaluable": evaluable,
                        "rate": round(agree / evaluable, 3) if evaluable else None}
    return out


def write_results(evidence, stats, matching):
    per = {name: tally([e for e in evidence if e["stratum"] == name]) for name, *_ in STRATA}
    per_total = tally(evidence)
    results = {
        "parameters": {
            "seed": SEED, "quotas": {n: q for n, q, *_ in STRATA}, "upland_min_height_m": UPLAND_MIN_M,
            "lowland_max_height_m": LOWLAND_MAX_M, "preferred_min_logs_per_pillar": MIN_LOGS,
            "max_candidates_per_stratum": MAX_CANDIDATES, "max_logs_read_per_pillar": PAGE * MAX_PAGES,
            "match_radius_m": MATCH_M, "match_name_similarity": NAME_SIMILARITY,
            "source": "api.trigpointing.uk v1: trigs/export (positions, names) and trigs/{id}/logs",
            "rate_limit": "1 request per second, identifying User-Agent",
        },
        "requests": {"cap": MAX_REQUESTS, "total": requests_so_far(), "before_script": PRIOR_REQUESTS},
        "pool": stats, "matching": matching, "strata": per, "overall": per_total,
    }
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "spot_check.json").write_text(json.dumps(results, indent=2) + "\n")
    (CACHE / "evidence.json").write_text(json.dumps(evidence, indent=1))
    return results


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("fetch", "run"):
        raise SystemExit(__doc__)
    online = sys.argv[1] == "fetch"
    g = Getter(online)
    lines, pillars = load_lines()
    matcher = Matcher(g.get("trigs/export")["items"])
    chosen, trig_of, stats = sample(g, lines, pillars, matcher)
    evidence = gather(g, chosen, trig_of)
    results = write_results(evidence, stats, match_summary(matcher, pillars, trig_of))
    print(f"{sys.argv[1]}: {g.made} requests made this run, {requests_so_far()} counted in total (cap {MAX_REQUESTS})")
    print(json.dumps(results["overall"], indent=2))


if __name__ == "__main__":
    main()
