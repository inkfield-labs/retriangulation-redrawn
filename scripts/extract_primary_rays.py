"""Extract observed primary rays (From -> To) from the OCR text layer of the 1967 History of the Retriangulation.

Appendices 1 to 7 tabulate the mean observed directions for each primary figure (book pp. 241-319, PDF pages
286-364). Each From station is followed by the stations it observed. This script reads only the direction tables
(sections n.1), rebuilds the From and To columns from text-line positions, and writes one row per observed direction.

Usage: python -I scripts/extract_primary_rays.py data/book/history.pdf
Writes results/primary_rays_raw.csv
"""
import csv
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
FIRST, LAST = 286, 364  # 1-based PDF pages holding Appendices 1-7
CODE = re.compile(r"\(\s*[A-Za-z0-9 ]{1,7}\s*\)")
HEADER_WORDS = re.compile(r"^(From|To|Mean|Direction|Plane|Adjust|Correc|Observed|ment|tion|Appendix|APPENDIX|"
                          r"FIGURE|F I G|Adjusted|Zeros|History)")


def page_lines(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            t = " ".join(s["text"] for s in ln["spans"]).strip()
            if t:
                out.append((ln["bbox"][0], ln["bbox"][1], " ".join(t.split())))
    return sorted(out, key=lambda r: (r[1], r[0]))


def is_name(t):
    return bool(re.match(r"^[A-Z][A-Za-z'’.\-]", t)) and not HEADER_WORDS.match(t)


def is_direction_page(text):
    return bool(re.search(r"\d\.1\s+(continued|Mean observed)", text[:600]))


def main(pdf):
    doc = pymupdf.open(pdf)
    rows, frm, figure = [], None, None
    for pno in range(FIRST - 1, LAST):
        text = doc[pno].get_text()
        m = re.search(r"F\s*I\s*G\s*U\s*R\s*E\s*(\d)", text[:300])
        if m and "APPENDIX" in text[:80].replace(" ", ""):
            figure = int(m.group(1))
        if not is_direction_page(text):
            continue
        sec = re.search(r"(\d)\.1\s+(continued|Mean observed)", text[:600])
        figure = int(sec.group(1))
        lines = [ln for ln in page_lines(doc[pno]) if ln[1] > 100]
        names = [ln for ln in lines if is_name(ln[2])]
        if not names:
            continue
        from_x = min(x for x, y, t in names)
        to_xs = [x for x, y, t in names if x > from_x + 40]
        to_x = min(to_xs) if to_xs else from_x + 90
        codes = [(x, y) for x, y, t in lines if t.startswith("(") or CODE.search(t)]
        pending_to = []
        pending_from = []
        for x, y, t in lines:
            if not is_name(t):
                continue
            col = "from" if x < to_x - 25 else ("to" if x < to_x + 45 else None)
            if col == "from":
                # a From name may wrap; a wrapped part has no code in the From column between
                if pending_from and y - pending_from[-1][0] < 12:
                    pending_from.append((y, t))
                else:
                    pending_from = [(y, t)]
                frm = CODE.sub("", " ".join(p[1] for p in pending_from)).strip()
                continue
            if col != "to":
                continue
            pending_to.append(t)
            # entry is complete when a code sits on the same row (inline, or a separate code line to the right)
            inline = CODE.search(t)
            sep = any(abs(cy - y) < 4 and cx > x + 30 for cx, cy in codes)
            if inline or sep or re.search(r"\d", t):
                name = CODE.sub("", " ".join(pending_to))
                name = re.sub(r"\s+[\d°'\-+—.,*^ ]+$", "", name).strip()
                rows.append((figure, pno + 1, frm, name))
                pending_to = []
    out = ROOT / "results" / "primary_rays_raw.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["figure", "pdf_page", "from_name", "to_name"])
        w.writerows(rows)
    print(f"{len(rows)} observed directions written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1])
