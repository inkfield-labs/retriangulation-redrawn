# Investigation plan: Retriangulation Redrawn

Written on 2026-10-20, before any search or analysis. Its authority is the owner's decision
to investigate (a private record).

**Question.** Is a static, explorable map of every pair of Ordnance Survey trig pillars in Great Britain that have
terrain line of sight to each other (a) original and (b) viable for one solo developer?

**Owner constraints.** MVP in 1 to 3 weekends (taken as at most 48 working hours). Opex of £0 to £20 a month. Upkeep
under 2 to 4 hours a week. No ads, no accounts, no content production.

**Out of scope.** Ireland and other networks, a polished UI, apps, publishing, posting to communities, monetisation.

## Rules

- Every claim in `INVESTIGATION.md` links to a source URL, or to a script in `scripts/` plus a saved output in
  `results/`. Numbers are only reported if computed or read.
- Spatial results are shown as PNG maps in `results/`.
- Unreachable sources are logged as unreachable, with what was intended. No mirrors, caches or other workarounds.
- One commit per step.
- Downloaded data lives in `data/` (gitignored). Scripts record the URL and date they fetched.

## Phase 1. Competition gate

**Method.** Search the places listed in the handover (trigpointing.uk, bagging sites and apps, code hosts, GIS
literature and talks, academic papers, social media, digitised historical networks). Log every query and its result in
`results/prior-art-log.md`.

**Classes.**
- DIRECT: a public tool, dataset or map that computes or shows pillar-to-pillar visibility across GB.
- PARTIAL: covers part of the idea (per-point viewshed, historical ray diagram, one region).
- ADJACENT: a related but different question (longest lines of sight, panoramas).

**Gate.** A maintained, public DIRECT equivalent means stop and report NO-GO. An unmaintained or private DIRECT
equivalent is reported and weighed, but does not stop the investigation automatically. Otherwise, list every PARTIAL
and ADJACENT item with one sentence of differentiation and continue.

## Phase 2. Viability

| # | Question | Method | Pass | Fail |
|---|---|---|---|---|
| 1 | Pillar data | Download the OS legacy trig CSV. Count records by type and condition. Find the height datum, what the height refers to, the licence and attribution. Check trigpointing.uk reuse terms. | At least 4,000 pillars with coordinates and heights, under a licence that allows redistribution with attribution | No redistributable licence, or heights missing for most pillars |
| 2 | Terrain data | Confirm the OS Terrain 50 licence, format and size. Assess Scottish, English and Welsh LiDAR and Copernicus GLO-30 for a validation region. | OS Terrain 50 open and downloadable | No open GB-wide DTM |
| 3 | Ground truth | Find the primary-observation diagrams. Check the 1967 book's copyright. Estimate the hours to digitise the primary network. Hand-extract 30 to 50 observed rays, long and short. | At least 30 rays extracted with a documented source | No access to any observed-ray source (then BLOCKED on accuracy, not NO-GO) |
| 4 | LOS accuracy | About 100 km × 100 km region, Ben Wyvis area by default. LOS with Earth curvature, refraction k in {0, 0.05, 0.10, 0.13, 0.20} (default 0.13), surveyed height plus pillar height at both ends, maximum range 50, 100 and 150 km. Score recall on observed rays. Count extra lines. Test DEM sensitivity where a finer DEM is available. Render a PNG. | Recall at least 95% at default settings | Recall below 95% after diagnosing heights, datum and DEM |
| 5 | GB-scale compute | Time the prototype. Extrapolate pairs, samples and wall-clock time to all pillars at each range. | Full run under 12 hours on one laptop at some range of at least 100 km | Over 12 hours at every range, with no simple fix |
| 6 | Output and hosting | Estimate the line count and PMTiles size. Render a regional tileset in MapLibre. Cost static hosting on Cloudflare R2 or Pages. | Tiles render. Hosting at most £20 a month. | Not renderable, or hosting over £20 a month |
| 7 | Audience | Passive only. trigpointing.uk member and log counts. Engagement on past trig posts. Wishes found in Phase 1. | Descriptive, no threshold | Descriptive, no threshold |
| 8 | Hooks | List features the data makes cheap, without building them. | Descriptive | Descriptive |

**Recall definition.** An observed ray counts as recovered if the model says the two pillars are intervisible at the
stated settings. Recall is recovered rays divided by observed rays whose two end stations both exist in the pillar
data. Rays whose stations cannot be matched are reported separately, not dropped silently.

**Extra lines.** Modelled intervisible pairs that are not observed rays. These are not errors. The historical network
observed only a subset of visible lines. The count is reported for context.

## Verdict rules

- NO-GO: the gate fails, or a hard data or licence blocker has no workaround.
- BLOCKED: a question that decides the verdict cannot be answered with accessible sources.
- CONDITIONAL GO: no blocker, but one or more pass thresholds are unmet or unknown, with a cheap way to close them.
- GO: the gate passes and questions 1 to 6 pass.

## Constraint arithmetic

The report states hours to MVP, monthly opex and weekly upkeep as sums of named items, and compares each with the
owner's limits.

## Deliverables

- `results/prior-art-log.md`, scripts in `scripts/`, outputs and PNGs in `results/`.
- `INVESTIGATION.md` with the seven sections the handover lists.
- In the portfolio repo: a FEASIBILITY history event at the start, and at the end a
  `sources/2026-10-20-retriangulation-investigation.md` summary and a closing history event. The disposition is not
  changed. A proposed disposition goes in the report as an agent recommendation.
