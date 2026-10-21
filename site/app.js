// Static map of trig-pillar sightlines. Data from scripts/build_site.py: data/pillars.geojson,
// data/partners/<id>.json and data/lines.pmtiles. A selection is kept in the URL hash (#<pillar id>).
const OS = "Contains OS data © Crown copyright and database right 2026";
const LINE = "#c2410c";

const protocol = new pmtiles.Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);
const base = new URL("data/", location.href).href;

const map = new maplibregl.Map({
  container: "map",
  style: "https://tiles.openfreemap.org/styles/positron",
  bounds: [[-7.6, 49.9], [1.8, 58.7]],
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

map.on("load", async () => {
  const pillars = await (await fetch(base + "pillars.geojson")).json();
  for (const f of pillars.features) byId.set(f.properties.id, f);
  fillSearch(pillars.features);

  map.addSource("lines", {type: "vector", url: "pmtiles://" + base + "lines.pmtiles", attribution: OS});
  map.addSource("pillars", {type: "geojson", data: pillars});
  map.addSource("sel-lines", {type: "geojson", data: empty()});
  map.addSource("sel-pts", {type: "geojson", data: empty()});

  map.addLayer({id: "lines", type: "line", source: "lines", "source-layer": "sightlines",
    paint: {"line-color": LINE, "line-width": ["interpolate", ["linear"], ["zoom"], 4, 0.3, 10, 0.8],
            "line-opacity": ["interpolate", ["linear"], ["zoom"], 4, 0.18, 9, 0.3]}});
  map.addLayer({id: "sel-lines", type: "line", source: "sel-lines",
    paint: {"line-color": LINE, "line-width": 1.8, "line-opacity": 0.85}});
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
  const others = partners.map(([pid, km]) => [byId.get(pid), km]).filter(([g]) => g);
  map.getSource("sel-lines").setData({type: "FeatureCollection", features: others.map(([g]) => ({
    type: "Feature", properties: {}, geometry: {type: "LineString", coordinates: [from, g.geometry.coordinates]}}))});
  map.getSource("sel-pts").setData({type: "FeatureCollection", features: [
    ...others.map(([g]) => ({...g, properties: {...g.properties, self: false}})),
    {...f, properties: {...f.properties, self: true}}]});
  map.setPaintProperty("lines", "line-opacity", 0.04);
  showDetail(f, others);
  if (fly) {
    const b = new maplibregl.LngLatBounds(from, from);
    for (const [g] of others) b.extend(g.geometry.coordinates);
    map.fitBounds(b, {padding: framePadding(), maxZoom: 11, duration: 800});
  }
}

function clear() {
  selected = null;
  history.replaceState(null, "", location.pathname + location.search);
  map.getSource("sel-lines").setData(empty());
  map.getSource("sel-pts").setData(empty());
  map.setPaintProperty("lines", "line-opacity", ["interpolate", ["linear"], ["zoom"], 4, 0.18, 9, 0.3]);
  document.getElementById("detail").hidden = true;
}

function showDetail(f, others) {
  const p = f.properties;
  document.getElementById("d-name").textContent = p.name;
  const far = others.length ? others[others.length - 1] : null;
  document.getElementById("d-meta").textContent =
    `${p.id} · ${p.h > 0 ? p.h + " m" : "height not recorded"} · ` +
    (others.length ? `${others.length} pillars in view, farthest ${far[0].properties.name} at ${far[1]} km`
                   : "no other pillar in view over the terrain");
  const list = document.getElementById("d-list");
  list.replaceChildren(...others.map(([g, km]) => {
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = g.properties.name;
    const d = document.createElement("span");
    d.className = "km";
    d.textContent = `${km} km`;
    li.append(name, d);
    li.addEventListener("click", () => select(g.properties.id, true));
    return li;
  }));
  list.scrollTop = 0;
  document.getElementById("detail").hidden = false;
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
