// Static map of trig-pillar sightlines, then and now. Data from scripts/build_site.py: data/pillars.geojson,
// data/partners/<id>.json, data/lines.pmtiles and data/rays.geojson. A selection is kept in the URL hash (#<id>).
const OS = "Contains OS data © Crown copyright and database right 2026";
const COP = "Contains modified Copernicus DEM data";
const LINE = "#c2410c";
const RAY = {clear: "#1d4ed8", surface: "#7c3aed", terrain: "#be123c", unknown: "#9ca3af"};
const RAY_TEXT = {clear: "still clear", surface: "blocked by trees or buildings",
                  terrain: "blocked by the terrain", unknown: "station height not recorded"};
// modern network opacity: full when alone, faint under the historical rays, nearly hidden behind a selection
const NET = {full: ["interpolate", ["linear"], ["zoom"], 4, 0.18, 9, 0.3],
             faint: ["interpolate", ["linear"], ["zoom"], 4, 0.07, 9, 0.14], selected: 0.04};

const protocol = new pmtiles.Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);
const base = new URL("data/", location.href).href;

const GB = [[-7.6, 49.9], [1.8, 58.7]];
const map = new maplibregl.Map({
  container: "map",
  style: "https://tiles.openfreemap.org/styles/positron",
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
  const [pillars, rayData] = await Promise.all(["pillars.geojson", "rays.geojson"].map(
    async (f) => (await fetch(base + f)).json()));
  for (const f of pillars.features) byId.set(f.properties.id, f);
  rays = rayData.features;
  fillSearch(pillars.features);
  fillLegend(pillars.features);

  map.addSource("lines", {type: "vector", url: "pmtiles://" + base + "lines.pmtiles", attribution: `${OS}. ${COP}`});
  map.addSource("pillars", {type: "geojson", data: pillars});
  map.addSource("rays", {type: "geojson", data: rayData});
  map.addSource("sel-lines", {type: "geojson", data: empty()});
  map.addSource("sel-pts", {type: "geojson", data: empty()});

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
  map.addLayer({id: "pillars", type: "circle", source: "pillars",
    paint: {"circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 0.8, 7, 1.6, 10, 4.5],
            "circle-color": "#1f2937", "circle-opacity": ["interpolate", ["linear"], ["zoom"], 4, 0.5, 8, 1], "circle-stroke-color": "#fff",
            "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 4, 0, 9, 1]}});
  map.addLayer({id: "sel-pts", type: "circle", source: "sel-pts",
    paint: {"circle-radius": ["case", ["get", "self"], 8, 5], "circle-color": ["case", ["get", "self"], "#fff", LINE],
            "circle-stroke-color": ["case", ["get", "self"], "#1f2937", "#fff"],
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
    const li = document.createElement("li");
    const name = document.createElement("span");
    const sw = document.createElement("span");
    sw.className = `sw ${s ? "net-clear" : "net-blocked"}`;
    sw.title = s ? "Clear on the surface model" : "Blocked by trees or buildings in the surface model";
    name.append(sw, g.properties.name);
    const d = document.createElement("span");
    d.className = "km";
    d.textContent = `${km} km`;
    li.append(name, d);
    li.addEventListener("click", () => select(g.properties.id, true));
    return li;
  }));
  list.scrollTop = 0;
  document.getElementById("detail").hidden = false;
  document.getElementById("panel").classList.add("has-detail");
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
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && selected) clear(); });
