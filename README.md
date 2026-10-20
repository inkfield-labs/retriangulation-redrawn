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

Setup: `uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt`
