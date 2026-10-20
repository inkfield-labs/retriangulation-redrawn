# Prior-art log

Phase 1 competition gate, run on 2026-10-20. Web searches used a general web-search tool. Pages were read by direct
fetch. GitHub was searched with `gh search`. Each entry records the query or URL, what came back, and how the finding
is classified.

Classes, from `docs/investigation-plan.md`:
- **DIRECT** means a public tool, dataset or map that computes or shows pillar-to-pillar visibility across GB.
- **PARTIAL** means it covers part of the idea.
- **ADJACENT** means a related but different question.

## Gate result

**No DIRECT equivalent was found.** The closest items are the following.
- The 1967 OS *History of the Retriangulation*. Its diagrams and Appendix 6 tables record the primary rays actually
  observed. They are historical and static, and cover only the primary order.
- Barry Hunter's 2004 static image of the same rays, which is research-only and not redistributable.
- An abandoned 2023 GitHub stub with the same aim. It stopped at a horizon-distance formula, uses no terrain and has
  no output.

Nothing computes terrain intervisibility between pillars, and nothing covers the full set of pillars.
The gate passes.

## Searches and results

| # | Where | Query or URL | Result | Class |
|---|---|---|---|---|
| 1 | Web | `trig pillar intervisibility map Great Britain which trig points can see each other` (extended) | Pillar location maps only (OS GeoDataViz, trigbagging.co.uk, jdconey trigmap). No intervisibility map. | none |
| 2 | Web | `trigpointing.uk intervisibility "visible from" trig pillars line of sight` | forum thread t=372 "Trig point visibility", a geocache page and encyclopaedia definitions. No tool. | none |
| 3 | trigpointing.uk forum | https://forum.trigpointing.uk/viewtopic.php?t=372 (read in full) | Thread from 2021 to 2022. A student asks which trigs see which. Replies explain that each station observed at least two others. User "Teasel" links a commissioned searchable scan of the 1967 *History* book and a zip of its 20 diagrams, saying the scan was made "shortly before its Crown Copyright expired" and that the appendix diagrams "show the complete set of primary observations". No tool mentioned. | PARTIAL (source) |
| 4 | Book | https://storage.googleapis.com/retriangulation/ (PDF, 441 pp, plus `Diagrams.zip`, 20 PDFs) | Downloaded. The Diagrams list (p. xiv) includes "2. Retriangulation Primary Observations" and "5 to 11. Primary Figures 1 to 7". **Appendix 6** tabulates every mean observed direction From→To for each primary figure. | PARTIAL |
| 5 | Web | `retriangulation of Great Britain primary triangulation network shapefile digitised observations` | Wikipedia article and TNA catalogue. OS 51/16, "Diagram showing the Primary Observations", is not available online. OS 69 station files. No shapefile. | PARTIAL (archive, not online) |
| 6 | Wikipedia | https://en.wikipedia.org/wiki/Retriangulation_of_Great_Britain | No network map. About 6,500 pillars. Cites Edge (1967), HMSO. | none |
| 7 | Web | `retriangulation primary observations map digitised GIS "primary triangulation" Great Britain lines` | **Trig Tools** (deformedweb.co.uk, Barry Hunter, 2004). Static PNG "primary-rays-observed" from Harley (1974) fig. 3, combining the Retriangulation with the 1962 to 1967 Readjustment. "made available here purely for research purposes, and should not be duplicated or redistributed." No terrain computation. | PARTIAL |
| 8 | Web | `"retriangulation" Great Britain primary network map wikimedia commons diagram primary stations rays` | No Commons file. Cambridge UL holds the OS sheet "Retriangulation of Great Britain: primary observations: 1936-1957" (1:625,000, 1957). Its catalogue page returned **403 unreachable**. OS docs say the OSGB36 TRF has 326 primary stations. | PARTIAL (archive) |
| 9 | GitHub | `gh search repos`: "trig intervisibility", "trig pillar", "trigpoint line of sight", "triangulation pillar viewshed", "trig points viewshed", "ordnance survey trig", "retriangulation", "intervisibility network", "trigpointing", "trig point visibility", "trig viewshed", "trigpoint intervisible", "line of sight trig", "ordnance survey viewshed", "terrain50 viewshed", "OS Terrain 50 line of sight" | Hits: **ArachnaDude/trig-pillar-project**, crochan/Trig-Pillars, grahamwhaley/OSM_UK_trigpoints, cran/trigpoints, mdales/Trigpoints. Others unrelated. | see below |
| 10 | GitHub | `gh search code`: "intervisib trig", "trigpoint viewshed", "TrigUser intervisible" | No results. | none |
| 11 | GitHub | ArachnaDude/trig-pillar-project (README and code read) | README: "calculate lines of sight between Ordinance Survey trig pillars to gain an understanding of the network involved in the retriangulation". Eight commits from 2023-09-04 to 2023-10-04, 0 stars. The only logic is a horizon-distance formula `sqrt(h*13)`. No terrain and no output. Abandoned. | PARTIAL (same aim, no output) |
| 12 | GitHub | crochan/Trig-Pillars | Static web map of pillars in the Bannau Brycheiniog National Park. No sightlines. | ADJACENT |
| 13 | GitHub | grahamwhaley/OSM_UK_trigpoints | Processes the OS CompleteTrigArchive for an OSM import. Slippy map of import status. No sightlines. | ADJACENT |
| 14 | Web | `github trig pillar line of sight viewshed Ordnance Survey Terrain 50 intervisibility` | Only GIS body-of-knowledge definitions. | none |
| 15 | Web | `"trig points" "line of sight" network map visualisation QGIS viewshed all trig pillars` | QGIS **Viewshed Analysis** plugin (landscapearchaeology.org), which can generate "intervisibility networks between groups of points". QGIS LoS Tools. Tutorials only, no trig output. | ADJACENT (enabling tool) |
| 16 | OS docs | https://docs.os.uk/.../trig-pillars-today | OS GeoDataViz hex cartogram of standing-pillar count and mean elevation. "No line of sight." | ADJACENT |
| 17 | Web | jdconey.github.io/run/trigmap, trigbagging.co.uk/trig-pillar-map | Pillar location maps by condition. No sightlines. | ADJACENT |
| 18 | trigpointing.uk | Site, wiki, and API docs at https://api.trigpointing.uk/v1/openapi.json (read in full) | The API has trigs, logs, photos, lists, stats and downloads. The only "visibility" field is list privacy. **No intervisibility or "visible from" feature.** The wiki page "User generated maps" returned 404. | none |
| 19 | Web | `"intervisibility" "trig points" OR "triangulation pillars" analysis DEM Britain paper` | R package `trigpoints` (coordinates only), a Tom Scott write-up and an FOI response. No paper. | none |
| 20 | Web | `longest line of sight between trig points UK computed` | Walkhighlands photographed long views (134 km from Braid Hills). livefortheoutdoors "Britain's longest view", 232 km from the Merrick to Snowdon, hypothetical. No trig-to-trig computation. | ADJACENT |
| 21 | Web | `hill bagging "intervisible" OR "visible from" summits app Britain DoBIH line of sight tool` | DoBIH / Hill Bagging (data, CC BY 4.0), an unofficial DoBIH MCP server, and Mountain Weather UK. No line-of-sight tool. | none |
| 22 | Web | `PeakVisor OR PeakFinder "trig point" OR "trig pillar" visible line of sight feature` | PeakFinder and PeakVisor identify the summits on a horizon from one point. No trig feature found. | ADJACENT |
| 23 | Web | `Viewfinder Panoramas de Ferranti "line of sight" Britain longest view list summits visible` | Per-point panoramas. De Ferranti disputes visibility claims (Wrekin to Snowdon). | ADJACENT |
| 24 | Web | `Ulrich Deuschle panorama generator trig point Britain udeuschle` | Per-point panoramas with DoBIH, OSM and GeoNames summit labels. Trig points are not confirmed as a layer. | ADJACENT |
| 25 | HeyWhatsThat | https://www.heywhatsthat.com/faq.html | Per-viewer panorama and "visibility cloak" (viewshed), with curvature and refraction modelled. SRTM about 90 m. Peak list from GNIS and GeoNames. No point-set intervisibility. | PARTIAL (per-point viewshed) |
| 26 | alltheviews.world | Home page and https://alltheviews.world/faq | Global longest lines of sight (CacheTVS). SRTM about 100 m (viewfinderpanoramas cleaned), k = 0.13, observer at 1.65 m. GB coverage is not stated. No point-pair queries. | ADJACENT |
| 27 | Web | `"triangulation" network "intervisibility" historical survey reconstruction viewshed GIS paper Ordnance Survey OR "principal triangulation"` | Archaeology "viewnets" (Wheatley 1995 cumulative viewshed, Chacoan viewnet supplement). Nothing on the OS network. | ADJACENT |
| 28 | Web | `intervisibility triangulation stations reconstruct historical geodetic network DEM line-of-sight analysis journal` (extended) | Textbook material only. No paper reconstructing a geodetic network's intervisibility from a DEM. | none |
| 29 | Web | `FOSS4G UK OR GISRUK OR "British Cartographic Society" trig pillars talk visibility network map` | OSM import and talk-gb threads, OS blogs. No talk found. | none |
| 30 | Web | `observablehq trig points Great Britain OR "trig pillars" visualisation` | No Observable notebook. OSM wiki on the OS station database (OGL v3). | none |
| 31 | Web | `gitlab trig pillar OR trigpoint "line of sight" OR viewshed OR intervisibility` | No GitLab project. | none |
| 32 | Web | `"which trig points can I see" OR "trig points visible from" OR "visible trig pillars" tool map` | No tool. Mentions France's "géodésie de poche" map of geodetic points (no sightlines). | none |
| 33 | Web | `youtube trig pillars "line of sight" "can see" other trig point visible Britain` | Tom Scott video write-up and general explainers. No tool. | none |
| 34 | YouTube | Direct search pages, via `scripts/audience_signal.py` | 52 videos (`results/audience_youtube.csv`). Explainers only. None shows a computed sightline network. | none |
| 35 | Web | `reddit trig pillars map line of sight network dataisbeautiful MapPorn` | No Reddit result surfaced. | none |
| 36 | Reddit | https://www.reddit.com/r/MapPorn/search.json?q=trig+pillars and old.reddit.com r/UKhiking search | **Unreachable (HTTP 403 "Blocked")**. The intent was to search r/MapPorn, r/dataisbeautiful and r/UKhiking for trig sightline maps and engagement. Not routed around. | n/a |
| 37 | Bluesky | public.api.bsky.app `searchPosts?q=trig pillars line of sight` | **Unreachable (HTTP 403)**. | n/a |
| 38 | Mastodon | mastodon.social `/api/v2/search?q=trig pillars&type=statuses` | 200, but empty. Unauthenticated status search returns nothing, so this is **inconclusive** rather than a negative. | n/a |
| 39 | Web | `"trig" "intervisible" pillars mastodon OR bluesky OR "bsky.app" map` | No social post found. trigpointing.uk wiki pages on ghost and unusual trigs. | none |

## PARTIAL and ADJACENT items with differentiation

| Finding | Class | Differentiation (one sentence) |
|---|---|---|
| *History of the Retriangulation* (OS 1967), Diagrams 2 and 5 to 11 and Appendix 6 | PARTIAL | It records only the primary stations' observed rays (OS docs: 326 primary stations in the OSGB36 TRF) from 1936 to 1962 as static paper figures, while the idea computes present-day terrain visibility among all pillars and makes it explorable. These rays are its best validation set, not a competitor. |
| Trig Tools primary-rays image (deformedweb.co.uk, 2004) | PARTIAL | A single research-only static image of the historical primary rays, with no computation, no lower-order pillars and no reuse permitted. |
| ArachnaDude/trig-pillar-project (GitHub, 2023) | PARTIAL | Same aim, but abandoned after one month at a horizon-distance formula, with no terrain model and no output. It shows the idea occurs to people but has not been delivered. |
| TNA OS 51/16 and Cambridge UL 1957 primary-observations sheet | PARTIAL | Archive paper copies of the historical primary diagram. Not online, and the same scope as the book. |
| HeyWhatsThat | PARTIAL | Per-viewer viewshed and peak list on SRTM. It does not know about trig pillars or compute a network between a fixed point set. |
| alltheviews.world | ADJACENT | It answers "what is the longest view from anywhere" on SRTM, not "which survey pillars see which". |
| PeakFinder, PeakVisor, Ulrich Deuschle, Viewfinder Panoramas | ADJACENT | Per-point panoramas labelling summits, not a pillar-to-pillar network. |
| QGIS Viewshed Analysis plugin, LoS Tools | ADJACENT | Desktop tools that could compute such a network, but no published trig output exists. |
| OS "Trig pillars today" cartogram, trigbagging.co.uk, jdconey trigmap, OSM_UK_trigpoints, crochan/Trig-Pillars, trigpointing.uk | ADJACENT | Pillar location or condition maps with no sightlines. |
| Britain's-longest-view articles and Walkhighlands threads | ADJACENT | Single longest views between summits, not a pillar network. |

## Expressed wishes

The forum thread t=372 (2021) is someone asking which trigs see which. ArachnaDude/trig-pillar-project (2023) is
someone starting to build it. Both are weak signals of interest. No explicit request for a tool was found.
