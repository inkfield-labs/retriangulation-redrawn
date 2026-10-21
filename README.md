# Retriangulation Redrawn: feasibility investigation

Which Ordnance Survey trig pillars in Great Britain can see each other over the terrain? This repo holds the evidence
for deciding whether a static map of that sightline network is original and viable. It is an investigation, not a
product.

- `docs/investigation-plan.md`: questions, methods and pass/fail thresholds, written before any analysis
- `results/prior-art-log.md`: every prior-art query and result
- `scripts/`: analysis scripts (Python), run with `.venv/bin/python scripts/<name>.py`
- `results/`: saved outputs (CSV, JSON, PNG) that the report cites
- `INVESTIGATION.md`: the verdict and report
- `data/` (gitignored): downloaded trig and terrain data
- `site/`: the static map page (MVP build, not published). `site/data/` is built by `scripts/build_site.py`
  from `data/gb_lines.csv` (from `scripts/gb_full_run.py`) and needs [tippecanoe](https://github.com/felt/tippecanoe)
  (set `TIPPECANOE` if it is not on `PATH`). Serve `site/` with a server that supports Range requests, e.g.
  `npx http-server@14.1.1 site -c-1`

Setup: `uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt`
