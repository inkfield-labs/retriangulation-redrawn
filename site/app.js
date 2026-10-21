// Static map of trig-pillar sightlines, then and now. Data from scripts/build_site.py: data/pillars.geojson,
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
const RAY_TEXT = {clear: "still clear", surface: "blocked by trees or buildings",
                  terrain: "blocked by the terrain", unknown: "station height not recorded"};
// Five fixed stories. Every number traces to a script output; see the number audit (issue #13).
const STORIES = [
  {title: "Hensbarrow: lost to the clay tips?", at: [-4.819, 50.384], go: () => select("PP174", true),
   text: "Four of the six rays the surveyors observed from Hensbarrow, near St Austell, now fail over the terrain " +
         "model: ground up to 45 m above the sight line, 0.2 to 2 km from the pillar, blocks them. The pillar stands " +
         "in the china-clay country around Hensbarrow Beacon, so spoil tips may have risen across those lines since. " +
         "That is inferred from location, not confirmed."},
  {title: "East Anglia: surveying from towers", at: [0.948, 52.109], go: () => select("PP240", true),
   text: "On the low ground of eastern England, sight lines from pillar height graze the fields. The 1967 history " +
         "records that this chain needed steel towers at no fewer than 34 of its primary stations, and most of its " +
         "other stations were bolts on church towers, water towers and cathedrals. Of its 226 observed rays, 63 are " +
         "still clear, 32 are blocked by trees or buildings, 29 by the terrain, and 102 end on a tower whose height " +
         "was not recorded. Nedging Tye, shown here, has all four."},
  {title: "Deerness to Fair Isle: 92 km of sea", at: [-2.19, 59.25], go: () => showPair("PP457", "PP458"),
   text: "The surveyors observed between Deerness in Orkney and Fair Isle, 92 km apart across open sea. With the " +
         "standard refraction used here (k = 0.13) the model says the line misses by 1.7 m, so when they observed it " +
         "the air over the sea must have bent the light more than the model allows."},
  {title: "The longest line: Merrick to Snowdon", at: [-4.468, 55.139], go: () => showPair("PP301", "SH62-T66"),
   text: "The longest sightline the model finds runs 231.9 km from Merrick in Galloway to Snowdon Summit, clearing " +
         "the terrain by 7.7 m and clear on the surface model too. It was not one of the observed rays, and it has " +
         "not been checked against reported sightings."},
  {title: "Sca Fell: 448 pillars in view", at: [-3.212, 54.454], go: () => select("PP92", true),
   text: "From the pillar on Sca Fell the model finds 448 other pillars in view over the terrain, more than from any " +
         "other pillar, and 433 of them are also clear on the surface model. The farthest is Cader Idris, 200.6 km " +
         "away."},
];

// modern network opacity: full when alone, faint under the historical rays, nearly hidden behind a selection
const NET = {full: ["interpolate", ["linear"], ["zoom"], 4, 0.18, 9, 0.3],
             faint: ["interpolate", ["linear"], ["zoom"], 4, 0.07, 9, 0.14], selected: 0.04};

const protocol = new pmtiles.Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);
const base = new URL("data/", location.href).href;

const GB = [[-7.6, 49.9], [1.8, 58.7]];
const map = new maplibregl.Map({
  container: "map",
  style: "https://tiles.openfreemap.org/styles/" + (dark ? "dark" : "positron"),
  bounds: GB,
  fitBoundsOptions: {padding: 20},
  attributionControl: false,
});
map.addControl(new maplibregl.NavigationControl({showCompass: false}), "top-right");
const narrow = innerWidth <= 640;
const attribution = new maplibregl.AttributionControl({compact: narrow});
map.addControl(attribution, "bottom-right");
// on phones start collapsed to the (i) button; the full credits are also in the About dialog
if (narrow) map.once("load", () =>
  document.querySelector(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show"));

const byId = new Map();
let selected = null;
let rays = [];
const historyBox = document.getElementById("history");

map.on("load", async () => {
  const [pillars, rayData, longest] = await Promise.all(["pillars.geojson", "rays.geojson", "longest.json"].map(
    async (f) => (await fetch(base + f)).json()));
  for (const f of pillars.features) byId.set(f.properties.id, f);
  rays = rayData.features;
  fillSearch(pillars.features);
  fillLegend(pillars.features);
  fillLongest(longest);
  fillStories();

  map.addSource("lines", {type: "vector", url: "pmtiles://" + base + "lines.pmtiles", attribution: `${OS}. ${COP}`});
  map.addSource("pillars", {type: "geojson", data: pillars});
  map.addSource("rays", {type: "geojson", data: rayData});
  map.addSource("sel-lines", {type: "geojson", data: empty()});
  map.addSource("sel-pts", {type: "geojson", data: empty()});
  map.addSource("pair", {type: "geojson", data: empty()});

  // surface-blocked lines (s = 0) get their own dashed layer: line-dasharray cannot be data-driven
  const width = ["interpolate", ["linear"], ["zoom"], 4, 0.3, 10, 0.8];
  map.addLayer({id: "lines", type: "line", source: "lines", "source-layer": "sightlines", filter: ["==", ["get", "s"], 1],
    paint: {"line-color": LINE, "line-width": width}});
  map.addLayer({id: "lines-blocked", type: "line", source: "lines", "source-layer": "sightlines",
    filter: ["==", ["get", "s"], 0], paint: {"line-color": LINE, "line-width": width, "line-dasharray": [2, 2]}});
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

async function select(id, fly) {
  const f = byId.get(id);
  if (!f) return;
  selected = id;
  map.getSource("pair").setData(empty());
  for (const d of document.querySelectorAll("#explore details")) d.open = false;
  document.getElementById("d-story").hidden = true;
  if (location.hash.slice(1) !== id) history.replaceState(null, "", "#" + encodeURIComponent(id));
  const partners = f.properties.n ? await (await fetch(`${base}partners/${encodeURIComponent(id)}.json`)).json() : [];
  if (selected !== id) return;  // a newer selection won the race
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
}

function clear() {
  selected = null;
  history.replaceState(null, "", location.pathname + location.search);
  map.getSource("sel-lines").setData(empty());
  map.getSource("sel-pts").setData(empty());
  map.getSource("pair").setData(empty());
  restyle();
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
    (others.length ? `${others.length} pillars in view over the terrain, ${clearN} also clear on the surface model; ` +
                     `farthest ${far[0].properties.name} at ${far[1]} km`
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
    sw.title = s ? "Clear on the surface model" : "Blocked by trees or buildings in the surface model";
    name.append(sw, g.properties.name);
    return pick(name, `${km} km`, () => select(g.properties.id, true));
  }));
  document.getElementById("detail").hidden = false;
  document.getElementById("detail").scrollTop = 0;
  document.getElementById("panel").classList.add("has-detail");
}

// Select one end of a line and frame the whole line.
async function showPair(a, b) {
  await select(a, false);
  const A = byId.get(a).geometry.coordinates, B = byId.get(b).geometry.coordinates;
  map.getSource("pair").setData({type: "Feature", properties: {}, geometry: {type: "LineString", coordinates: [A, B]}});
  map.fitBounds(new maplibregl.LngLatBounds(A, A).extend(B), {padding: framePadding(), maxZoom: 10, duration: 800});
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
  btn.addEventListener("click", onClick);
  li.append(btn);
  return li;
}

async function story(i) {
  const s = STORIES[i];
  await s.go();
  const box = document.getElementById("d-story");
  box.querySelector("h3").textContent = `${i + 1}. ${s.title}`;
  box.querySelector("p").textContent = s.text;
  box.hidden = false;
}

function fillStories() {
  document.getElementById("story-list").replaceChildren(...STORIES.map((s, i) => pick(s.title, "", () => story(i))));
  STORIES.forEach((s, i) => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "story-marker";
    el.textContent = i + 1;
    el.addEventListener("click", (e) => { e.stopPropagation(); story(i); });  // not also a map click
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
  return innerWidth <= 640 ? {top: 40, left: 30, right: 30, bottom: panel.height + 20}
                           : {top: 40, right: 60, bottom: 40, left: panel.right + 30};
}

function fillSearch(features) {
  const list = document.getElementById("names");
  const labels = new Map();
  for (const f of features) labels.set(`${f.properties.name} (${f.properties.id})`, f.properties.id);
  list.replaceChildren(...[...labels.keys()].sort().map((l) => Object.assign(document.createElement("option"), {value: l})));
  const input = document.getElementById("search");
  input.addEventListener("change", () => {
    const id = labels.get(input.value);
    if (id) { select(id, true); input.value = ""; input.blur(); }
  });
}

document.getElementById("clear").addEventListener("click", clear);
document.getElementById("about-open").addEventListener("click", () => document.getElementById("about").showModal());
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !document.getElementById("about").open && selected) clear();
});
