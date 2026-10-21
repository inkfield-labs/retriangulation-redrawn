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
- `site/`: the static map page (MVP build, not published). Serve it with a server that supports Range requests, e.g.
  `npx http-server@14.1.1 site -c-1`. `site/data/` is gitignored and built in this order (`TRIG` is the
  `CompleteTrigArchive.csv` under `data/trig/`; each script's docstring has its full usage):

      scripts/gb_full_run.py TRIG shard <i> <n>, then finalize <n>   # pairs up to 150 km
      scripts/gb_long_run.py TRIG                                    # pairs 150-250 km
      scripts/glo30_gb.py fetch, mosaic, run TRIG                    # surface flag; fetch needs CDSE S3 credentials
                                                                     # in AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
      scripts/classify_rays.py                                       # 1936-62 rays, then and now
      scripts/build_site.py TRIG                                     # needs tippecanoe: set TIPPECANOE if not on PATH
      scripts/audit_numbers.py                                       # every number on the page against results/

  Run each as `.venv/bin/python -I scripts/<name>.py ...`.

Setup: `uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt`
