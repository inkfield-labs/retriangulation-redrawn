// Static map of trig-pillar sightlines, then and now. Data from scripts/build_site.py: data/pillars.json,
// data/partners/<id>.json, data/lines.pmtiles and data/rays.geojson. A selection is kept in the URL hash (#<id>).
const OS = "Contains OS data © Crown copyright and database right 2026";
const COP = "Contains modified Copernicus DEM data";
const dark = matchMedia("(prefers-color-scheme: dark)").matches;
document.documentElement.dataset.scheme = dark ? "dark" : "light";
const palette = getComputedStyle(document.documentElement);
const color = (name) => palette.getPropertyValue(`--${name}`).trim();
const INK = color("ink"), PAPER = color("paper"), LINE = color("line");
const RAY = {clear: color("ray-clear"), surface: color("ray-surface"),
             terrain: color("ray-terrain"), unknown: color("ray-unknown")};
const RAY_TEXT = {clear: "clear in the 2010–15 surface model",
                  surface: "blocked by trees or buildings in the 2010–15 surface model",
                  terrain: "blocked by the terrain", unknown: "station height not recorded"};
// Five fixed stories. Every number traces to a script output; see the number audit (issue #13).
const STORIES = [
  {title: "Hensbarrow: lost to the clay tips?", at: [-4.819, 50.384], go: () => select("PP174", true),
   text: "Four of the six rays the surveyors observed from Hensbarrow, near St Austell, fail over the terrain " +
         "model: ground up to 45 m above the sight line, 0.2 to 2 km from the pillar, blocks them. The pillar stands " +
         "in the china-clay country around Hensbarrow Beacon, so spoil tips may have risen across those lines since. " +
         "That is inferred from location, not confirmed."},
  {title: "East Anglia: surveying from towers", at: [0.948, 52.109], go: () => select("PP240", true),
   text: "On the low ground of eastern England, sight lines from pillar height graze the fields. The 1967 history " +
         "records that this chain needed steel towers at no fewer than 34 of its primary stations, and many of its " +
         "other stations were bolts on church towers, water towers and cathedrals. Of its 226 observed rays, 63 are " +
         "still clear in the 2010–15 surface model, 32 are blocked by trees or buildings, 29 by the terrain, and 102 end " +
         "on a station whose height was not recorded, mostly a tower. Nedging Tye, shown here, has all four."},
  {title: "Deerness to Fair Isle: 92 km of sea", at: [-2.19, 59.25], go: () => showPair("PP457", "PP458"),
   text: "The surveyors observed between Deerness in Orkney and Fair Isle, 92 km apart across open sea. With the " +
         "standard refraction used here (k = 0.13) the model says the line misses by 1.7 m, yet they observed it. On " +
         "the day the light may have bent more than the model allows, or the sea stood below the 0 m the model " +
         "assumes; a miss this small is within the model's error."},
  {title: "The longest line: Merrick to Snowdon", at: [-4.468, 55.139], go: () => showPair("PP301", "SH62-T66"),
   text: "The longest sightline the model finds runs 231.9 km from Merrick in Galloway to Snowdon Summit, clearing " +
         "the terrain by 7.7 m and clear on the 2010–15 surface model too. It was not one of the observed rays, and " +
         "it has not been checked against reported sightings."},
  {title: "Sca Fell: 448 pillars in view", at: [-3.212, 54.454], go: () => select("PP92", true),
   text: "From the pillar on Sca Fell the model finds 448 other pillars in view over the terrain, more than from any " +
         "other pillar, and 435 of them are also clear on the 2010–15 surface model. The farthest is Cader Idris, " +
         "200.6 km away."},
];

// modern network opacity: full when alone, faint under the historical rays, nearly hidden behind a selection
const NET = {full: ["interpolate", ["linear"], ["zoom"], 4, 0.18, 9, 0.3],
             faint: ["interpolate", ["linear"], ["zoom"], 4, 0.07, 9, 0.14], selected: 0.04};

const protocol = new pmtiles.Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);
const base = new URL("data/", location.href).href;
// tiles URL: scripts/deploy_preview.sh rewrites this one line to point at R2 (Pages caps files at 25 MiB)
const TILES = base + "lines.pmtiles";

const GB = [[-7.6, 49.9], [1.8, 58.7]];
const map = new maplibregl.Map({container: "map", bounds: GB, fitBoundsOptions: {padding: 20}, attributionControl: false});
// basemap labels in Latin script only: the bilingual labels fetch font ranges for other scripts (about 1 MB on a phone)
const latin = ["coalesce", ["get", "name:latin"], ["get", "name_en"], ["get", "name"]];
// dark basemap: OpenFreeMap's dark style draws sea almost as land (1.14:1) and labels below WCAG AA (3.4:1). A navy sea
// separates as much as the light map's (1.57:1 vs 1.52:1); labels reach 4.5:1 or more. Ratios: scripts/check_contrast.py
const SEA = "rgb(28,52,90)";
const DARK_PAINT = {water: {"fill-color": SEA}, waterway: {"line-color": SEA},
  water_name: {"text-color": "rgb(150,180,220)", "text-halo-color": "rgb(12,12,12)"},
  highway_name_other: {"text-color": "rgb(150,150,150)"}, highway_name_motorway: {"text-color": "rgb(150,150,150)"}};
const darkPaint = (l) => DARK_PAINT[l.id] ?? (l.id.startsWith("place_")
  ? {"text-color": "rgb(176,176,176)", "text-halo-color": "rgba(0,0,0,0.85)", "text-halo-width": 1.5} : null);
map.setStyle("https://tiles.openfreemap.org/styles/" + (dark ? "dark" : "positron"), {transformStyle: (_, style) => ({
  ...style, layers: style.layers.map((l) => (JSON.stringify(l.layout?.["text-field"] ?? "").includes("name:nonlatin")
    ? {...l, layout: {...l.layout, "text-field": latin}} : l)).map((l) => (dark && darkPaint(l)
    ? {...l, paint: {...l.paint, ...darkPaint(l)}} : l))})});
map.addControl(new maplibregl.NavigationControl({showCompass: false}), "top-right");
const narrow = innerWidth <= 640;
// the tile credits are also given up front, so the credits are full when the opening view is framed below them
const attribution = new maplibregl.AttributionControl({compact: narrow, customAttribution: `${OS}. ${COP}`});
// on phones the bottom sheet is below and the zoom buttons top-right, so the credits go top-left
map.addControl(attribution, narrow ? "top-left" : "bottom-right");

const byId = new Map();
let selected = null;
let rays = [];
const historyBox = document.getElementById("history");

map.on("load", async () => {
  let rows, rayData, longest;
  try {
    [rows, rayData, longest] = await Promise.all(["pillars.json", "rays.geojson", "longest.json"].map(
      async (f) => (await fetch(base + f)).json()));
  } catch { return showError(); }
  const pillars = {type: "FeatureCollection", features: rows.map(([id, name, lon, lat, h, n, s], i) => ({
    type: "Feature", id: i, geometry: {type: "Point", coordinates: [lon, lat]}, properties: {id, name, h, n, s}}))};
  for (const f of pillars.features) byId.set(f.properties.id, f);
  rays = rayData.features;
  fillSearch(pillars.features);
  fillLegend(pillars.features);
  fillLongest(longest);
  fillStories();

  map.addSource("lines", {type: "vector", url: "pmtiles://" + TILES, attribution: `${OS}. ${COP}`});
  map.addSource("pillars", {type: "geojson", data: pillars});
  map.addSource("rays", {type: "geojson", data: rayData});
  map.addSource("sel-lines", {type: "geojson", data: empty()});
  map.addSource("sel-pts", {type: "geojson", data: empty()});
  map.addSource("pair", {type: "geojson", data: empty()});

  // surface-blocked lines (s = 0) get their own dashed layer: line-dasharray cannot be data-driven
  const width = ["interpolate", ["linear"], ["zoom"], 4, 0.3, 10, 0.8];
  // the dense network goes under the basemap's place labels (its closing run of symbol layers) so towns stay readable
  const styleLayers = map.getStyle().layers;
  let labels = styleLayers.length;
  while (labels > 0 && styleLayers[labels - 1].type === "symbol") labels--;
  map.addLayer({id: "lines", type: "line", source: "lines", "source-layer": "sightlines", filter: ["==", ["get", "s"], 1],
    paint: {"line-color": LINE, "line-width": width}}, styleLayers[labels]?.id);
  map.addLayer({id: "lines-blocked", type: "line", source: "lines", "source-layer": "sightlines",
    filter: ["==", ["get", "s"], 0], paint: {"line-color": LINE, "line-width": width, "line-dasharray": [2, 2]}},
    styleLayers[labels]?.id);
  const rayPaint = (dash) => ({"line-color": ["match", ["get", "st"], ...Object.entries(RAY).flat(), "#000"],
    "line-width": ["interpolate", ["linear"], ["zoom"], 4, ["match", ["get", "st"], "unknown", 0.8, 1.6],
                   9, ["match", ["get", "st"], "unknown", 1.5, 3]],
    "line-opacity": 0.9, ...(dash ? {"line-dasharray": [2, 1.5]} : {})});
  map.addLayer({id: "rays", type: "line", source: "rays", layout: {"line-cap": "round"}, paint: rayPaint(false)});
  map.addLayer({id: "rays-surface", type: "line", source: "rays", paint: rayPaint(true)});
  map.addLayer({id: "sel-lines", type: "line", source: "sel-lines", filter: ["==", ["get", "s"], 1],
    paint: {"line-color": LINE, "line-width": 1.8, "line-opacity": 0.85}});
  map.addLayer({id: "sel-lines-blocked", type: "line", source: "sel-lines", filter: ["==", ["get", "s"], 0],
    paint: {"line-color": LINE, "line-width": 1.4, "line-opacity": 0.6, "line-dasharray": [2, 2]}});
  map.addLayer({id: "pair", type: "line", source: "pair", layout: {"line-cap": "round"},
    paint: {"line-color": INK, "line-width": 4}});
  map.addLayer({id: "pillars", type: "circle", source: "pillars",
    paint: {"circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 0.8, 7, 1.6, 10, 4.5],
            "circle-color": INK, "circle-opacity": ["interpolate", ["linear"], ["zoom"], 4, 0.5, 8, 1], "circle-stroke-color": PAPER,
            "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 4, 0, 9, 1]}});
  map.addLayer({id: "sel-pts", type: "circle", source: "sel-pts",
    paint: {"circle-radius": ["case", ["get", "self"], 8, 5], "circle-color": ["case", ["get", "self"], PAPER, LINE],
            "circle-stroke-color": ["case", ["get", "self"], INK, PAPER],
            "circle-stroke-width": ["case", ["get", "self"], 3, 1.5]}});

  map.on("click", (e) => {
    const p = e.point, r = 8;  // generous hit area for touch
    const hit = map.queryRenderedFeatures([[p.x - r, p.y - r], [p.x + r, p.y + r]], {layers: ["sel-pts", "pillars"]});
    if (!hit.length) return;
    const dist = (f) => { const q = map.project(f.geometry.coordinates); return Math.hypot(q.x - p.x, q.y - p.y); };
    select(hit.reduce((a, b) => (dist(b) < dist(a) ? b : a)).properties.id, false);  // nearest, not topmost
  });
  map.on("mouseenter", "pillars", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "pillars", () => (map.getCanvas().style.cursor = ""));

  historyBox.addEventListener("change", restyle);
  restyle();
  if (narrow) map.fitBounds(GB, {padding: framePadding(), duration: 0});  // keep GB clear of the bottom sheet
  window.addEventListener("hashchange", fromHash);
  fromHash();
  window.mapReady = true;
});

function empty() { return {type: "FeatureCollection", features: []}; }

function fromHash() {
  const id = decodeURIComponent(location.hash.slice(1));
  if (id && byId.has(id)) { if (id !== selected) select(id, true); }
  else if (!id && selected) clear();
}

const LOAD_ERROR = "Could not load the data. Reload to try again.";

// One line in the detail panel, reusing the pillar heading; no pillar is selected afterwards.
function showError() {
  document.getElementById("d-name").textContent = LOAD_ERROR;
  for (const el of ["d-story", "d-then"]) document.getElementById(el).hidden = true;
  for (const el of ["d-meta", "d-list"]) document.getElementById(el).replaceChildren();
  document.getElementById("detail").hidden = false;
  document.getElementById("panel").classList.add("has-detail");
}

// Resolves to whether this selection is still the current one (a newer one may have won the race).
async function select(id, fly) {
  const f = byId.get(id);
  if (!f) return false;
  selected = id;
  map.getSource("pair").setData(empty());
  for (const d of document.querySelectorAll("#explore details")) d.open = false;
  document.getElementById("d-story").hidden = true;
  if (location.hash.slice(1) !== id) history.replaceState(null, "", "#" + encodeURIComponent(id));
  let partners = [];
  try {
    if (f.properties.n) partners = await (await fetch(`${base}partners/${encodeURIComponent(id)}.json`)).json();
  } catch {
    if (selected !== id) return false;
    clear();
    showError();
    return false;
  }
  if (selected !== id) return false;
  const from = f.geometry.coordinates;
  const others = partners.map(([pid, km, s]) => [byId.get(pid), km, s]).filter(([g]) => g);
  map.getSource("sel-lines").setData({type: "FeatureCollection", features: others.map(([g, , s]) => ({
    type: "Feature", properties: {s}, geometry: {type: "LineString", coordinates: [from, g.geometry.coordinates]}}))});
  map.getSource("sel-pts").setData({type: "FeatureCollection", features: [
    ...others.map(([g]) => ({...g, properties: {...g.properties, self: false}})),
    {...f, properties: {...f.properties, self: true}}]});
  restyle();
  showDetail(f, others);
  if (fly) {
    const b = new maplibregl.LngLatBounds(from, from);
    for (const [g] of others) b.extend(g.geometry.coordinates);
    if (historyBox.checked) for (const r of rays) {
      if (r.properties.a === id || r.properties.b === id) for (const c of r.geometry.coordinates) b.extend(c);
    }
    map.fitBounds(b, {padding: framePadding(), maxZoom: 11, duration: 800});
  }
  return true;
}

function clear() {
  selected = null;
  history.replaceState(null, "", location.pathname + location.search);
  if (map.getSource("sel-lines")) {  // absent after a failed first load, when × only dismisses the error
    map.getSource("sel-lines").setData(empty());
    map.getSource("sel-pts").setData(empty());
    map.getSource("pair").setData(empty());
    restyle();
  }
  document.getElementById("detail").hidden = true;
  document.getElementById("panel").classList.remove("has-detail");
}

// Layer visibility, opacity and filters for the current history switch and selection.
function restyle() {
  const history = historyBox.checked;
  const net = selected ? NET.selected : history ? NET.faint : NET.full;
  map.setPaintProperty("lines", "line-opacity", net);
  map.setPaintProperty("lines-blocked", "line-opacity", selected ? 0.02 : history ? 0.05 : 0.12);
  const own = selected ? [["any", ["==", ["get", "a"], selected], ["==", ["get", "b"], selected]]] : [];
  map.setFilter("rays", ["all", ["!=", ["get", "st"], "surface"], ...own]);
  map.setFilter("rays-surface", ["all", ["==", ["get", "st"], "surface"], ...own]);
  for (const id of ["rays", "rays-surface"]) map.setLayoutProperty(id, "visibility", history ? "visible" : "none");
}

function count(items, key) {
  const n = {};
  for (const x of items) n[key(x)] = (n[key(x)] || 0) + 1;
  return n;
}

function fillLegend(pillars) {
  const fmt = (n) => (n || 0).toLocaleString("en-GB");
  const st = count(rays, (r) => r.properties.st);
  document.getElementById("n-rays").textContent = `(${fmt(rays.length)})`;
  for (const el of document.querySelectorAll("#key-rays .n")) el.textContent = fmt(st[el.dataset.st]);
  // each line is counted at both its ends
  const n = pillars.reduce((t, f) => t + f.properties.n, 0) / 2, s = pillars.reduce((t, f) => t + f.properties.s, 0) / 2;
  document.getElementById("n-lines").textContent = `(${fmt(n)})`;
  document.getElementById("n-clear").textContent = fmt(s);
  document.getElementById("n-blocked").textContent = fmt(n - s);
}

function showDetail(f, others) {
  const p = f.properties;
  document.getElementById("d-name").textContent = p.name;
  const far = others.length ? others[others.length - 1] : null;
  const clearN = others.filter(([, , s]) => s).length;
  document.getElementById("d-meta").textContent =
    `${p.id} · ${p.h > 0 ? p.h + " m" : "height not recorded"} · ` +
    (others.length ? `${others.length} pillars in view over the terrain, ` +
                     `${clearN} also clear on the 2010–15 surface model; farthest ${far[0].properties.name} at ${far[1]} km`
                   : "no other pillar in view over the terrain");
  const mine = rays.filter((r) => r.properties.a === p.id || r.properties.b === p.id);
  const then = document.getElementById("d-then");
  then.hidden = !mine.length;
  if (mine.length) {
    const st = count(mine, (r) => r.properties.st);
    then.textContent = `Observed 1936–62: ${mine.length} ray${mine.length > 1 ? "s" : ""}, ` +
      Object.keys(RAY).filter((k) => st[k]).map((k) => `${st[k]} ${RAY_TEXT[k]}`).join(", ") + ".";
  }
  const list = document.getElementById("d-list");
  list.replaceChildren(...others.map(([g, km, s]) => {
    const name = document.createElement("span");
    const sw = document.createElement("span");
    sw.className = `sw ${s ? "net-clear" : "net-blocked"}`;
    sw.title = s ? "Clear on the 2010–15 surface model" : "Blocked by trees or buildings in the 2010–15 surface model";
    name.append(sw, g.properties.name);
    return pick(name, `${km} km`, () => select(g.properties.id, true));
  }));
  document.getElementById("detail").hidden = false;
  document.getElementById("detail").scrollTop = 0;
  document.getElementById("panel").classList.add("has-detail");
}

// Select one end of a line and frame the whole line.
async function showPair(a, b) {
  if (!(await select(a, false))) return false;
  const A = byId.get(a).geometry.coordinates, B = byId.get(b).geometry.coordinates;
  map.getSource("pair").setData({type: "Feature", properties: {}, geometry: {type: "LineString", coordinates: [A, B]}});
  map.fitBounds(new maplibregl.LngLatBounds(A, A).extend(B), {padding: framePadding(), maxZoom: 10, duration: 800});
  return true;
}

// After a pick, move focus to the pillar heading so the new panel is announced.
async function reveal(done) {
  if (await done) document.getElementById("d-name").focus();
}

function pick(text, km, onClick, swatch) {
  const li = document.createElement("li");
  const btn = document.createElement("button");
  btn.type = "button";
  const k = document.createElement("span");
  k.className = "km";
  k.textContent = km;
  if (swatch) {
    const sw = document.createElement("span");
    sw.className = `sw ${swatch}`;
    btn.append(sw);
  }
  btn.append(text, k);
  btn.addEventListener("click", () => reveal(onClick()));
  li.append(btn);
  return li;
}

async function story(i) {
  const s = STORIES[i];
  if (!(await s.go())) return false;
  const box = document.getElementById("d-story");
  box.querySelector("h3").textContent = `${i + 1}. ${s.title}`;
  box.querySelector("p").textContent = s.text;
  box.hidden = false;
  return true;
}

function fillStories() {
  document.getElementById("story-list").replaceChildren(...STORIES.map((s, i) => pick(s.title, "", () => story(i))));
  STORIES.forEach((s, i) => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "story-marker";
    el.textContent = i + 1;
    el.addEventListener("click", (e) => { e.stopPropagation(); reveal(story(i)); });  // not also a map click
    new maplibregl.Marker({element: el}).setLngLat(s.at).addTo(map);
    el.title = `Story ${i + 1}: ${s.title}`;
    el.setAttribute("aria-label", el.title);  // after Marker(), which sets its own generic label
  });
}

function fillLongest(longest) {
  document.getElementById("longest-list").replaceChildren(...longest.map(([a, b, km, s]) =>
    pick(`${byId.get(a).properties.name} – ${byId.get(b).properties.name}`, `${km} km`, () => showPair(a, b),
         s ? "net-clear" : "net-blocked")));
}

function framePadding() {
  const panel = document.getElementById("panel").getBoundingClientRect();
  // phones: frame below the credits (top-left, open until the map is dragged), which would hide story marker 3
  const credits = document.querySelector(".maplibregl-ctrl-top-left").getBoundingClientRect().bottom;
  return innerWidth <= 640 ? {top: credits + 40, left: 30, right: 30, bottom: panel.height + 20}
                           : {top: 40, right: 60, bottom: 40, left: panel.right + 30};
}

function fillSearch(features) {
  const list = document.getElementById("names");
  const labels = new Map();
  for (const f of features) labels.set(`${f.properties.name} (${f.properties.id})`, f.properties.id);
  list.replaceChildren(...[...labels.keys()].sort().map((l) => Object.assign(document.createElement("option"), {value: l})));
  const input = document.getElementById("search");
  // Enter on a name that is not a full label picks a pillar starting with the text, else containing it: an exact
  // name first, then the one with the most partners ("Snowdon" is Snowdon Summit)
  const rank = (f, t) => (f.properties.name.toLowerCase() === t ? 1e6 : 0) + f.properties.n;
  const guess = (t) => {
    for (const hit of [(name) => name.startsWith(t), (name) => name.includes(t)]) {
      const m = features.filter((f) => hit(f.properties.name.toLowerCase()));
      if (m.length) return m.reduce((a, f) => (rank(f, t) > rank(a, t) ? f : a)).properties.id;
    }
    return null;
  };
  let enter = false;
  input.addEventListener("keydown", (e) => {
    enter = e.key === "Enter";
    // WebKit (Safari, every iPhone browser) fires neither "change" nor "search" on Enter here, so Enter commits too;
    // deferred so a picked suggestion lands first, and a no-op once another event has used and cleared the value
    if (enter) setTimeout(() => commit(true));
  });
  // the value is cleared once used, so a "change" and a "search" from the same Enter select only once
  const commit = (fallback) => {
    const text = input.value.trim().toLowerCase();
    const id = labels.get(input.value) ?? (fallback && text ? guess(text) : null);
    enter = false;
    if (id) { select(id, true); input.value = ""; input.blur(); }
  };
  input.addEventListener("change", () => commit(enter));
  // a search box fires "search" on Enter, also where keydown reports "Unidentified" (Android keyboards)
  input.addEventListener("search", () => commit(true));
}

// a keyboard activation (no pointer click count) returns focus to the search box; a tap must not raise a phone keyboard
document.getElementById("clear").addEventListener("click", (e) => {
  clear();
  if (e.detail === 0) document.getElementById("search").focus();
});
document.getElementById("about-open").addEventListener("click", () => document.getElementById("about").showModal());
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !document.getElementById("about").open && selected) clear();
});
