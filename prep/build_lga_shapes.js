/*
 * build_lga_shapes.js
 * -------------------
 * Builds council (LGA) boundaries for the maps by merging Victorian suburb
 * (locality) polygons, using the suburb -> council pairs listed in the
 * Crime Statistics Agency suburb table (prep/suburb_lga.csv).
 *
 * Input : prep/raw/vic_localities.topojson  (Vic locality polygons, from the
 *         public FIT3179/Vega-Lite teaching repository on GitHub)
 * Output: data/vic_lga.topojson  (object "lga", property "lga")
 *         data/vic_lga_centroids.csv  (lga, lon, lat) for the symbol map
 *
 * Suburbs with no recorded crime, or whose name exists in two councils,
 * take the council most common among their neighbouring suburbs.
 *
 * Run: node build_lga_shapes.js   (needs topojson-client, -server, -simplify)
 */
const fs = require("fs");
const path = require("path");
const topo = require("topojson-client");
const simp = require("topojson-simplify");
const server = require("topojson-server");

const here = __dirname;
const topology = JSON.parse(fs.readFileSync(path.join(here, "raw", "vic_localities.topojson")));
const objName = Object.keys(topology.objects)[0];
const geoms = topology.objects[objName].geometries;

// ---- 1. Candidate councils for each suburb name (most incidents first) ----
const rows = fs.readFileSync(path.join(here, "suburb_lga.csv"), "utf8").trim().split("\n").slice(1);
const candidates = {};                       // "NAME" -> [{lga, n}]
for (const line of rows) {
  const m = line.match(/^(.*),(.*),(\d+)$/); // suburb names can contain commas? (they don't, but be safe)
  const suburb = m[1].replace(/"/g, "").trim().toUpperCase();
  const lga = m[2].replace(/"/g, "").trim();
  (candidates[suburb] = candidates[suburb] || []).push({ lga, n: +m[3] });
}
Object.values(candidates).forEach(c => c.sort((a, b) => b.n - a.n));

const nameCount = {};
geoms.forEach(g => { const n = g.properties.NAME.toUpperCase(); nameCount[n] = (nameCount[n] || 0) + 1; });

// ---- 2. First pass: unambiguous suburbs ----
const lgaOf = geoms.map(g => {
  const n = g.properties.NAME.toUpperCase();
  const c = candidates[n];
  if (c && c.length === 1 && nameCount[n] === 1) return c[0].lga;
  if (c && nameCount[n] === 1 && c[0].n >= 3 * (c[1] ? c[1].n : 0)) return c[0].lga;
  return null;
});

// ---- 3. Fill the rest from neighbours (repeat until stable) ----
const neighbours = topo.neighbors(geoms);
for (let pass = 0; pass < 50; pass++) {
  let changed = 0;
  geoms.forEach((g, i) => {
    if (lgaOf[i]) return;
    const votes = {};
    neighbours[i].forEach(j => { if (lgaOf[j]) votes[lgaOf[j]] = (votes[lgaOf[j]] || 0) + 1; });
    const allowed = (candidates[g.properties.NAME.toUpperCase()] || []).map(c => c.lga);
    let best = null, bestV = 0;
    for (const [lga, v] of Object.entries(votes)) {
      const bonus = allowed.includes(lga) ? 100 : 0;  // prefer a council the CSA lists for this name
      if (v + bonus > bestV) { best = lga; bestV = v + bonus; }
    }
    if (best) { lgaOf[i] = best; changed++; }
  });
  if (!changed) break;
}
const missing = lgaOf.filter(x => !x).length;
console.log("suburbs:", geoms.length, "unassigned:", missing);

// ---- 4. Merge suburbs into councils, keep topology, simplify ----
const byLga = {};
geoms.forEach((g, i) => { if (lgaOf[i]) (byLga[lgaOf[i]] = byLga[lgaOf[i]] || []).push(g); });

const merged = Object.entries(byLga).map(([lga, gs]) => {
  const m = topo.mergeArcs(topology, gs);
  m.properties = { lga };
  return m;
});
// Rebuild a clean topology from the merged council shapes, then simplify.
const mergedGeo = { type: "FeatureCollection",
  features: merged.map(m => ({ type: "Feature", properties: m.properties,
                                geometry: topo.feature(topology, m).geometry })) };
let out = server.topology({ lga: mergedGeo }, 2e4);
out = simp.presimplify(out);
out = simp.simplify(out, simp.quantile(out, 0.95));     // drop ~92% of points
out = simp.filter(out, simp.filterWeight(out, simp.quantile(out, 0.5)));
out = topo.quantize(out, 1e4);                         // integer coordinates = small file

fs.writeFileSync(path.join(here, "..", "data", "vic_lga.topojson"), JSON.stringify(out));

// ---- 5. Centroids for the proportional symbol map ----
const fc = topo.feature(out, out.objects.lga);
const d3c = (f) => {            // area-weighted centroid of the largest ring set (planar approx.)
  let A = 0, X = 0, Y = 0;
  const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
  polys.forEach(p => {
    const r = p[0];
    for (let k = 0; k < r.length - 1; k++) {
      const [x0, y0] = r[k], [x1, y1] = r[k + 1];
      const c = x0 * y1 - x1 * y0; A += c; X += (x0 + x1) * c; Y += (y0 + y1) * c;
    }
  });
  return [X / (3 * A), Y / (3 * A)];
};
const csv = ["lga,lon,lat"].concat(fc.features.map(f => {
  const [x, y] = d3c(f); return `${f.properties.lga},${x.toFixed(4)},${y.toFixed(4)}`;
}));
fs.writeFileSync(path.join(here, "..", "data", "vic_lga_centroids.csv"), csv.join("\n") + "\n");
console.log("councils:", merged.length);
