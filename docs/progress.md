# Progress (paused 2026-10-20, usage limit)

## Done
- Plan committed (`docs/investigation-plan.md`).
- Portfolio repo: stage moved to FEASIBILITY.
- Phase 1 gate passed: no DIRECT equivalent (`results/prior-art-log.md`). Reddit and Bluesky were unreachable (403).
  Mastodon search was inconclusive.
- Audience: trigpointing.uk has 7,479 members and 504,604 logs, with 742 logs in the last 7 days and 203 users active
  in the last 30 days (`results/audience_trigpointing_stats.json`). YouTube engagement is in `results/audience_youtube.csv`.
- Pillar data: `results/trig_profile.md`. 7,111 PILLAR records, 6,079 not destroyed, 6,816 with a height. Licence is
  OGL per the OS trig-search page.
- Height reference: the flush-bracket arrow (History p. 16). The pillar is 4 ft above ground (Fig. 2.2, p. 15).
- Book: OS hosts the PDF and diagrams. The book is © Crown copyright 1967. **To do:** cite CDPA 1988 s.163 (50 years
  from publication), which means the copyright expired at the end of 2017.
- Ground truth: `scripts/extract_primary_rays.py` and `scripts/match_rays.py` found 1,207 unique primary rays, 642 of
  them pillar-to-pillar and observed from both ends. One known artefact is Shurland–Castle Ring at 241 km, so cap
  rays at 120 km. `results/hand_rays_diagram10.csv` holds 67 rays read by hand around Ben Wyvis.
- Terrain 50: downloaded with md5 verified (154 MB zip). The mosaic is `data/terrain50/gb50.npy` (built by
  `scripts/build_dem.py`, 48 s).
- LOS model: `scripts/los.py`, written but **not yet run or tested**.

## Next
1. Check trigpointing.uk reuse terms (wiki is CC BY-SA 4.0; the bulk download needs login). Define OS datum codes S, L, D.
2. Write `scripts/score_primary.py`. Measure recall on the reciprocal pillar rays (GB, and the Ben Wyvis 100 km box),
   sweeping k from 0 to 0.2, `skip`, height mode (fb or dem) and DEM factor 1, 2 and 4. Also score the hand set.
   Render the PNG.
3. Time it, then extrapolate pillar pairs and samples at 50, 100 and 150 km.
4. Estimate PMTiles size (tippecanoe is not installed), do a MapLibre test, cost R2.
5. Assess higher-resolution DEMs (Scottish LiDAR, EA, Wales, GLO-30). spacedata.copernicus.eu was unreachable.
6. Write `INVESTIGATION.md`, then the portfolio sources file, history event, render and check.
