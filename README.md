# Retriangulation Redrawn

Between 1936 and 1962 the Ordnance Survey remeasured Great Britain by sighting angles between concrete trig pillars.
This project redraws those sightlines over a terrain model and a 2010–15 model of trees and buildings: which views
still clear, and which are now blocked? The map is at <https://retriangulation-redrawn.pages.dev/>.

It shows the 829 rays the surveyors observed from both ends, each re-tested, over the 230,499 pairs of standing
pillars that the model finds in view over the terrain. Every number on the page traces to a script and a saved output
in `results/` (`scripts/audit_numbers.py` checks them). These are models, not observations; the map's "How this was
made" panel gives the method and its limits.

Built with AI assistance (Claude, credited in the commits).

## Layout

- `INVESTIGATION.md`: the feasibility investigation and its verdict; `docs/investigation-plan.md` was written first
- `scripts/`: analysis and build scripts (Python); each docstring gives its usage, inputs and outputs
- `results/`: saved outputs (CSV, JSON, PNG) that the report and the page cite
- `site/`: the static map page (MapLibre GL); `site/data/` is built, not committed
- `data/` (not committed): downloaded trig and elevation data

## Building

Setup: `uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt`. Run each script as
`.venv/bin/python -I scripts/<name>.py ...`. `TRIG` is the OS `CompleteTrigArchive.csv` under `data/trig/`.

    scripts/gb_full_run.py TRIG shard <i> <n>, then finalize <n>   # pairs up to 150 km
    scripts/gb_long_run.py TRIG                                    # pairs 150-250 km
    scripts/glo30_gb.py fetch, mosaic, run TRIG                    # surface flag; fetch needs Copernicus (CDSE) S3
                                                                   # credentials in AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
    scripts/classify_rays.py                                       # 1936-62 rays, then and now
    scripts/build_site.py TRIG                                     # needs tippecanoe: set TIPPECANOE if not on PATH
    scripts/audit_numbers.py                                       # every number on the page against results/

Serve `site/` with any static server, e.g. `npx http-server@14.1.1 site -c-1`. `scripts/deploy_preview.sh` deploys it
to Cloudflare Pages.

## Licence and data

The code is under the MIT licence (`LICENSE`). The data keep their own terms:

- Contains OS data © Crown copyright and database right 2026, licensed under the
  [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
- Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided
  under COPERNICUS by the European Union and ESA; all rights reserved.
- Historical rays from *History of the Retriangulation of Great Britain 1935–1962* (Ordnance Survey, 1967).
- Basemap © [OpenFreeMap](https://openfreemap.org), © [OpenMapTiles](https://www.openmaptiles.org/), data from
  [OpenStreetMap](https://www.openstreetmap.org/copyright).
