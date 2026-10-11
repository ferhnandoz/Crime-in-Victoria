// Embeds each Vega-Lite chart (JSON spec in /js) into its placeholder <div>.
// The specs load their data from /data, relative to index.html.

const charts = [
  ["#vis1", "js/01_trend.vl.json"],
  ["#vis2", "js/02_slope.vl.json"],
  ["#vis3", "js/03_heatmap.vl.json"],
  ["#vis4", "js/05_bump.vl.json"],
  ["#vis5", "js/04_waffle.vl.json"],
  ["#vis6", "js/06_choropleth.vl.json"],
  ["#vis7", "js/07_symbols.vl.json"],
  ["#vis8", "js/09_small_multiples.vl.json"],
  ["#vis9", "js/08_bivariate.vl.json"],
  ["#vis10", "js/10_scatter.vl.json"],
  ["#vis11", "js/11_boxplot.vl.json"],
  ["#vis12", "js/12_dumbbell.vl.json"],
];

// Wait for web fonts so chart labels are measured in the right typeface.
document.fonts.ready.then(() => {
  for (const [target, spec] of charts) {
    vegaEmbed(target, spec, { actions: false, renderer: "svg" })
      .catch(err => console.error(spec, err));
  }
});
