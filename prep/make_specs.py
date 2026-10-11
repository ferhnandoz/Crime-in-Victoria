"""
make_specs.py
-------------
Writes every Vega-Lite chart specification in /js as a readable JSON file
(2-space indents). Each spec is a plain Python dict below, so shared settings
(fonts, colours, projection) only need to be defined once.

Run: python make_specs.py
"""

import json
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "js")
SCHEMA = "https://vega.github.io/schema/vega-lite/v5.json"

# ---------------------------------------------------------------- shared style
FONT = "Archivo"
INK, SOFT, RULE = "#1d2433", "#545c6b", "#ece8df"
RED, NAVY = "#b3261e", "#1f3a5f"

CONFIG = {
    "font": FONT,
    "view": {"stroke": None},
    "axis": {"labelFont": FONT, "titleFont": FONT, "labelFontSize": 12, "titleFontSize": 12,
             "titleFontWeight": 600, "labelColor": SOFT, "titleColor": SOFT,
             "domainColor": "#c9c4b8", "tickColor": "#c9c4b8", "gridColor": RULE},
    "axisQuantitative": {"format": ",.0f"},
    "legend": {"labelFont": FONT, "titleFont": FONT, "labelFontSize": 12, "titleFontSize": 12,
               "titleFontWeight": 600, "labelColor": SOFT, "titleColor": INK},
    "header": {"labelFont": FONT, "titleFont": FONT, "labelFontSize": 13,
               "labelFontWeight": 600, "labelColor": INK},
    "text": {"font": FONT, "fontSize": 12, "color": INK},
    "title": {"font": FONT, "fontSize": 14, "fontWeight": 700, "color": INK, "anchor": "start"},
}

# One colour per offence division, used in every chart that shows divisions.
DIV_DOMAIN = ["Crimes against the person", "Property and deception", "Justice procedures",
              "Drug offences", "Public order and security", "Other offences"]
DIV_RANGE = [RED, NAVY, "#c07a1d", "#3f7d5c", "#7a5c99", "#9aa0a6"]

# Choropleth classes for crime rate (incidents per 100,000 people)
RATE_STEPS = [4000, 5500, 7000, 8500, 10000]
RATE_COLOURS = ["#fdf0e1", "#f8cfa6", "#ee9f6e", "#d9663f", "#b3261e", "#6b100b"]

# Equal-area projection centred on Victoria (keeps council sizes honest)
PROJ = {"type": "conicEqualArea", "parallels": [-36, -38], "rotate": [-145, 0]}

GEO = {"url": "data/vic_lga.topojson", "format": {"type": "topojson", "feature": "lga"}}
LGA_FIELDS = ["lga", "region", "incidents", "rate", "rate_2017", "change_pct",
              "irsd_score", "disadvantage", "bivar", "metro", "unsolved_pct"]


def geo_with_lga_data():
    """Council shapes joined to lga.csv (the CSA + ABS figures for each council)."""
    return [
        {"calculate": "datum.properties.lga", "as": "lga"},
        {"lookup": "lga",
         "from": {"data": {"url": "data/lga.csv"}, "key": "lga",
                  "fields": [f for f in LGA_FIELDS if f != "lga"]}},
    ]


def write(name, spec):
    spec = {"$schema": SCHEMA, **spec, "config": CONFIG}
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(spec, f, indent=2)
    print("  wrote", name)


# ======================================================================
# 01  Ten-year trend (line chart, annotated)
# ======================================================================
write("01_trend.vl.json", {
    "description": "Criminal incidents recorded in Victoria, years ending June 2017-2026.",
    "data": {"url": "data/state_trend.csv"},
    "width": "container", "height": 300,
    "encoding": {
        "x": {"field": "year", "type": "ordinal", "title": "Year ending June",
              "axis": {"labelAngle": 0}},
        "y": {"field": "incidents", "type": "quantitative", "title": "Criminal incidents recorded",
              "scale": {"domain": [0, 520000]}, "axis": {"format": "~s", "tickCount": 5}},
    },
    "layer": [
        {"mark": {"type": "area", "color": NAVY, "opacity": 0.08}},
        {"mark": {"type": "line", "color": NAVY, "strokeWidth": 3}},
        {"mark": {"type": "point", "filled": True, "size": 60, "color": NAVY},
         "encoding": {
             "color": {"condition": {"test": "datum.year == 2022 || datum.year == 2025", "value": RED},
                       "value": NAVY},
             "size": {"condition": {"test": "datum.year == 2022 || datum.year == 2025", "value": 140},
                      "value": 60},
             "tooltip": [
                 {"field": "year", "title": "Year ending June"},
                 {"field": "incidents", "title": "Incidents", "format": ","},
                 {"field": "rate", "title": "Per 100,000 people", "format": ",.0f"}]}},
        {"transform": [{"filter": "datum.year == 2025"}],
         "mark": {"type": "text", "dy": -18, "fontWeight": 700, "color": RED, "align": "center"},
         "encoding": {"text": {"value": "Decade high: 482,134"}}},
        {"transform": [{"filter": "datum.year == 2022"}],
         "mark": {"type": "text", "dy": 30, "fontWeight": 700, "color": RED, "align": "center"},
         "encoding": {"text": {"value": ["Decade low: 340,067", "(year included the last lockdowns)"]}}},
    ],
})

# ======================================================================
# 02  Slope chart: rate by offence division, 2017 vs 2026 (log scale)
# ======================================================================
write("02_slope.vl.json", {
    "description": "Crime rate per 100,000 people by offence division, 2017 compared with 2026.",
    "data": {"url": "data/division_year.csv"},
    "transform": [
        {"filter": "(datum.year == 2017 || datum.year == 2026) && datum.division != 'Other offences'"},
        {"window": [{"op": "first_value", "field": "rate", "as": "rate_2017"}],
         "groupby": ["division"], "sort": [{"field": "year"}]},
        {"calculate": "100 * (datum.rate / datum.rate_2017 - 1)", "as": "change"},
        {"calculate": "datum.division + '  ' + (datum.change >= 0 ? '+' : '') + format(datum.change, '.0f') + '%'",
         "as": "label"},
        # nudge the two labels that would otherwise overlap
        {"calculate": "datum.division == 'Public order and security' ? datum.rate * 1.13 : "
                      "datum.division == 'Drug offences' ? datum.rate * 0.88 : datum.rate",
         "as": "label_y"},
    ],
    "width": 240, "height": 340,
    "encoding": {
        "x": {"field": "year", "type": "ordinal", "title": None,
              "scale": {"padding": 0.2},
              "axis": {"labelAngle": 0, "labelFontSize": 14, "labelFontWeight": 700,
                       "labelColor": INK, "domain": False, "ticks": False, "orient": "top"}},
        "y": {"field": "rate", "type": "quantitative", "title": "Incidents per 100,000 people",
              "scale": {"type": "log", "domain": [150, 6000]},
              "axis": {"values": [200, 500, 1000, 2000, 5000], "format": ","}},
        "color": {"field": "division", "type": "nominal", "legend": None,
                  "scale": {"domain": DIV_DOMAIN, "range": DIV_RANGE}},
    },
    "layer": [
        {"mark": {"type": "line", "strokeWidth": 3}},
        {"mark": {"type": "circle", "size": 90, "opacity": 1},
         "encoding": {"tooltip": [
             {"field": "division", "title": "Offence type"},
             {"field": "year", "title": "Year ending June"},
             {"field": "rate", "title": "Per 100,000 people", "format": ",.0f"}]}},
        {"transform": [{"filter": "datum.year == 2026"}],
         "mark": {"type": "text", "align": "left", "dx": 10, "fontWeight": 600, "fontSize": 13},
         "encoding": {"y": {"field": "label_y", "type": "quantitative"}, "text": {"field": "label"}}},
        {"transform": [{"filter": "datum.year == 2017"}],
         "mark": {"type": "text", "align": "right", "dx": -10, "fontSize": 12},
         "encoding": {"text": {"field": "rate", "format": ",.0f"}, "color": {"value": SOFT},
                      "y": {"field": "label_y", "type": "quantitative"}}},
    ],
})

# ======================================================================
# 03  Heatmap: offence subdivision x year, coloured by change since 2017
# ======================================================================
write("03_heatmap.vl.json", {
    "description": "Each offence subdivision's crime rate compared with 2017 (2017 = 100).",
    "data": {"url": "data/subdivision_year.csv"},
    "transform": [
        {"calculate": "datum.year == 2026 ? datum.incidents : 0", "as": "inc26"},
        {"calculate": "datum.year == 2026 ? datum.index : 0", "as": "idx26"},
        {"joinaggregate": [{"op": "sum", "field": "inc26", "as": "incidents_2026"},
                           {"op": "sum", "field": "idx26", "as": "index_2026"}],
         "groupby": ["subdivision"]},
        {"filter": "datum.incidents_2026 >= 1000"},
    ],
    "width": "container",
    "height": {"step": 24},
    "encoding": {
        "x": {"field": "year", "type": "ordinal", "title": "Year ending June",
              "axis": {"labelAngle": 0, "orient": "top", "domain": False, "ticks": False}},
        "y": {"field": "subdivision", "type": "nominal", "title": None,
              "sort": {"field": "index_2026", "order": "descending"},
              "axis": {"domain": False, "ticks": False, "labelLimit": 300, "labelFontSize": 12.5}},
    },
    "layer": [
        {"mark": {"type": "rect", "stroke": "#ffffff", "strokeWidth": 2, "cornerRadius": 2},
         "encoding": {
             "color": {"field": "index", "type": "quantitative",
                       "title": ["Compared with 2017", "(2017 = 100)"],
                       "scale": {"domain": [50, 100, 160], "range": ["#2c5a8c", "#f4f1ea", RED],
                                 "clamp": True},
                       "legend": {"orient": "bottom", "gradientLength": 260, "direction": "horizontal",
                                  "values": [50, 75, 100, 130, 160]}},
             "tooltip": [
                 {"field": "subdivision", "title": "Offence"},
                 {"field": "year", "title": "Year ending June"},
                 {"field": "incidents", "title": "Incidents", "format": ","},
                 {"field": "index", "title": "Compared with 2017 (=100)", "format": ".0f"}]}},
        {"transform": [{"filter": "datum.year == 2026"}],
         "mark": {"type": "text", "fontSize": 11, "fontWeight": 700},
         "encoding": {
             "text": {"field": "index", "format": ".0f"},
             "color": {"condition": {"test": "datum.index > 135 || datum.index < 65", "value": "#ffffff"},
                       "value": INK}}},
    ],
})

# ======================================================================
# 04  Waffle charts: how much crime is family-violence related
# ======================================================================
write("04_waffle.vl.json", {
    "description": "Share of 2026 incidents flagged as family-violence related, for three offence types.",
    "data": {"url": "data/family_flag.csv"},
    "transform": [
        {"filter": "datum.year == 2026"},
        {"joinaggregate": [{"op": "sum", "field": "incidents", "as": "total"}], "groupby": ["division"]},
        {"filter": "datum.flag == 'Family incident related'"},
        {"filter": {"field": "division", "oneOf": ["Justice procedures", "Crimes against the person",
                                                   "Property and deception"]}},
        {"calculate": "round(100 * datum.incidents / datum.total)", "as": "pct"},
        {"calculate": "datum.division + ': ' + datum.pct + '%'", "as": "panel"},
        {"calculate": "sequence(0, 100)", "as": "cell"},
        {"flatten": ["cell"]},
        {"calculate": "datum.cell % 10", "as": "col"},
        {"calculate": "floor(datum.cell / 10)", "as": "row"},
        {"calculate": "datum.cell < datum.pct ? 'Family-violence related' : 'Other incidents'",
         "as": "type"},
    ],
    "facet": {"column": {"field": "panel", "type": "nominal", "title": None,
                         "sort": {"field": "pct", "order": "descending"},
                         "header": {"labelFontSize": 13, "labelLimit": 260}}},
    "spacing": 36,
    "spec": {
        "width": {"step": 17}, "height": {"step": 17},
        "mark": {"type": "square", "size": 210, "opacity": 1},
        "encoding": {
            "x": {"field": "col", "type": "ordinal", "axis": None},
            "y": {"field": "row", "type": "ordinal", "axis": None, "sort": "descending"},
            "color": {"field": "type", "type": "nominal", "title": None,
                      "scale": {"domain": ["Family-violence related", "Other incidents"],
                                "range": [RED, "#e3ddd0"]},
                      "legend": {"orient": "bottom", "direction": "horizontal", "symbolType": "square"}},
            "tooltip": [{"field": "division", "title": "Offence type"},
                        {"field": "incidents", "title": "Family-violence incidents", "format": ","},
                        {"field": "total", "title": "All incidents", "format": ","},
                        {"field": "pct", "title": "Share (%)"}],
        },
    },
})

# ======================================================================
# 05  Bump chart: ranking of the ten most common offences
# ======================================================================
HIGHLIGHT = {"Steal from a retail store": RED, "Motor vehicle theft": "#c07a1d",
             "Residential non-aggravated burglary": NAVY}
write("05_bump.vl.json", {
    "description": "Rank of the ten most common offence subgroups in 2026, by year.",
    "data": {"url": "data/subgroup_rank.csv"},
    "transform": [
        {"calculate": "indexof(" + json.dumps(list(HIGHLIGHT)) + ", datum.subgroup) >= 0 ? datum.subgroup : 'Other'",
         "as": "group"},
        {"calculate": "datum.subgroup == 'Residential non-aggravated burglary' ? 'Home burglary (no violence)' : "
                      "datum.subgroup == 'Non-residential non-aggravated burglary' ? 'Business burglary (no violence)' : "
                      "datum.subgroup == 'Obtain benefit by deception' ? 'Fraud (obtain benefit by deception)' : "
                      "datum.subgroup", "as": "name"},
    ],
    "width": 420, "height": 380,
    "encoding": {
        "x": {"field": "year", "type": "ordinal", "title": "Year ending June",
              "axis": {"labelAngle": 0, "domain": False, "ticks": False}},
        "y": {"field": "rank", "type": "quantitative", "title": "Rank (1 = most common)",
              "scale": {"reverse": True, "domain": [1, 14], "nice": False},
              "axis": {"values": list(range(1, 15)), "grid": False}},
        "detail": {"field": "subgroup"},
        "color": {"field": "group", "type": "nominal", "legend": None,
                  "scale": {"domain": list(HIGHLIGHT) + ["Other"],
                            "range": list(HIGHLIGHT.values()) + ["#c9c4b8"]}},
        "tooltip": [{"field": "name", "title": "Offence"}, {"field": "year", "title": "Year ending June"},
                    {"field": "rank", "title": "Rank"},
                    {"field": "incidents", "title": "Incidents", "format": ","}],
    },
    "layer": [
        {"mark": {"type": "line", "interpolate": "monotone"},
         "encoding": {"strokeWidth": {"condition": {"test": "datum.group != 'Other'", "value": 3.5},
                                      "value": 2}}},
        {"mark": {"type": "circle", "size": 70, "opacity": 1}},
        {"transform": [{"filter": "datum.year == 2026 && datum.group == 'Other'"}],
         "mark": {"type": "text", "align": "left", "dx": 10, "fontSize": 12.5, "color": SOFT},
         "encoding": {"text": {"field": "name"}, "color": {"value": SOFT}}},
        {"transform": [{"filter": "datum.year == 2026 && datum.group != 'Other'"}],
         "mark": {"type": "text", "align": "left", "dx": 10, "fontSize": 12.5, "fontWeight": 700},
         "encoding": {"text": {"field": "name"}}},
        {"transform": [{"filter": "datum.year == 2021 && datum.subgroup == 'Steal from a retail store'"}],
         "mark": {"type": "text", "dy": 22, "align": "center", "fontWeight": 700, "color": RED,
                  "fontSize": 11.5},
         "encoding": {"text": {"value": ["Shops closed in", "lockdown: down to #10"]}}},
    ],
})

# ======================================================================
# 06  Choropleth (state + Melbourne zoom) linked to a council trend line
# ======================================================================
def rate_map(name, metro_only, w, h, title):
    tr = geo_with_lga_data()
    if metro_only:
        tr.append({"filter": "datum.metro == 'True' || datum.metro == true"})
    return {
        "name": name, "title": title,
        "width": w, "height": h,
        "data": GEO, "transform": tr,
        "projection": PROJ,
        "mark": {"type": "geoshape", "stroke": "#ffffff", "strokeWidth": 0.6, "cursor": "pointer"},
        "encoding": {
            "color": {"field": "rate", "type": "quantitative",
                      "title": "Incidents per 100,000 people",
                      "scale": {"type": "threshold", "domain": RATE_STEPS, "range": RATE_COLOURS},
                      "legend": {"orient": "top", "direction": "horizontal", "labelOverlap": False,
                                 "labelExpr": "isFinite(datum.value) ? format(datum.value / 1000, '.1~f') + 'k' : ''"}},
            "stroke": {"condition": {"param": "pick", "empty": False, "value": INK}, "value": "#ffffff"},
            "strokeWidth": {"condition": {"param": "pick", "empty": False, "value": 2.5}, "value": 0.6},
            "order": {"condition": {"param": "pick", "empty": False, "value": 1}, "value": 0},
            "tooltip": [
                {"field": "lga", "title": "Council"},
                {"field": "rate", "title": "Per 100,000 people", "format": ",.0f"},
                {"field": "incidents", "title": "Incidents (year to June 2026)", "format": ","},
                {"field": "change_pct", "title": "Change in rate since 2017 (%)", "format": "+.0f"}],
        },
    }


write("06_choropleth.vl.json", {
    "description": "Crime rate by council, year ending June 2026. Click a council to see its ten-year trend.",
    "params": [{"name": "pick", "views": ["state_map", "metro_map"],
                "select": {"type": "point", "fields": ["lga"], "on": "click", "clear": False},
                "value": [{"lga": "Latrobe"}]}],
    "vconcat": [
        {"hconcat": [
            rate_map("state_map", False, 470, 330, "All of Victoria"),
            rate_map("metro_map", True, 340, 330, "Zoom: metropolitan Melbourne"),
        ], "spacing": 30, "resolve": {"legend": {"color": "shared"}}},
        {
            "title": {"text": {"expr": "'Ten-year trend: ' + (pick.lga ? pick.lga[0] : 'click a council')"},
                      "fontSize": 14},
            "width": 840, "height": 200,
            "layer": [
                {"data": {"url": "data/lga_trend.csv"},
                 "mark": {"type": "line", "color": "#ddd7ca", "strokeWidth": 1},
                 "encoding": {"x": {"field": "year", "type": "ordinal", "title": "Year ending June",
                                    "axis": {"labelAngle": 0}},
                              "y": {"field": "rate", "type": "quantitative",
                                    "title": "Per 100,000 people", "scale": {"type": "log", "domain": [1000, 20000], "nice": False},
                                    "axis": {"values": [1000, 2000, 5000, 10000, 20000], "format": ","}},
                              "detail": {"field": "lga"}}},
                {"data": {"url": "data/state_trend.csv"},
                 "layer": [
                     {"mark": {"type": "line", "color": NAVY, "strokeDash": [5, 4], "strokeWidth": 2},
                      "encoding": {"x": {"field": "year", "type": "ordinal"},
                                   "y": {"field": "rate", "type": "quantitative"}}},
                     {"transform": [{"filter": "datum.year == 2026"}],
                      "mark": {"type": "text", "align": "left", "dx": 8, "color": NAVY, "fontWeight": 700},
                      "encoding": {"x": {"field": "year", "type": "ordinal"},
                                   "y": {"field": "rate", "type": "quantitative"},
                                   "text": {"value": "Victoria"}}}]},
                {"data": {"url": "data/lga_trend.csv"},
                 "transform": [{"filter": {"param": "pick"}}],
                 "layer": [
                     {"mark": {"type": "line", "color": RED, "strokeWidth": 3.5}},
                     {"mark": {"type": "circle", "color": RED, "size": 50, "opacity": 1},
                      "encoding": {"tooltip": [
                          {"field": "lga", "title": "Council"}, {"field": "year", "title": "Year"},
                          {"field": "rate", "title": "Per 100,000 people", "format": ",.0f"},
                          {"field": "incidents", "title": "Incidents", "format": ","}]}},
                     {"transform": [{"filter": "datum.year == 2026"}],
                      "mark": {"type": "text", "align": "left", "dx": 8, "color": RED, "fontWeight": 700},
                      "encoding": {"text": {"field": "lga"}}}],
                 "encoding": {"x": {"field": "year", "type": "ordinal"},
                              "y": {"field": "rate", "type": "quantitative"}}},
            ],
        },
    ],
    "spacing": 28,
})

# ======================================================================
# 07  Proportional symbol map: number of incidents + change since 2017
# ======================================================================
def symbol_map(name, metro_only, w, h, title, labels):
    is_metro = "(datum.metro == 'True' || datum.metro == true)"
    filt = [{"filter": is_metro}] if metro_only else []
    base_tr = geo_with_lga_data() + filt
    pts = {"url": "data/lga.csv"}
    # State view shows regional councils only; Melbourne's councils are in the zoom.
    pt_filt = filt if metro_only else [{"filter": "!" + is_metro}]
    pt_tr = [{"lookup": "lga", "from": {"data": {"url": "data/vic_lga_centroids.csv"},
                                       "key": "lga", "fields": ["lon", "lat"]}}] + pt_filt
    return {
        "title": title, "width": w, "height": h, "projection": PROJ,
        "layer": [
            {"data": GEO, "transform": base_tr + [{"calculate": is_metro + " ? 1 : 0", "as": "m"}],
             "mark": {"type": "geoshape", "stroke": "#ffffff", "strokeWidth": 0.7},
             "encoding": {"fill": {"condition": {"test": "datum.m == 1 && " + str(not metro_only).lower(),
                                                 "value": "#d5cfc2"}, "value": "#ebe6db"}}},
            {"data": pts, "transform": pt_tr,
             "mark": {"type": "circle", "stroke": "#ffffff", "strokeWidth": 0.8, "opacity": 0.88},
             "encoding": {
                 "longitude": {"field": "lon", "type": "quantitative"},
                 "latitude": {"field": "lat", "type": "quantitative"},
                 "size": {"field": "incidents", "type": "quantitative", "title": "Incidents recorded",
                          "scale": {"range": [8, 1600], "domain": [0, 33128]},
                          "legend": {"values": [1000, 10000, 30000], "labelExpr": "format(datum.value, ',')", "orient": "top",
                                     "symbolFillColor": "#bbb5a8", "symbolStrokeColor": "#ffffff"}},
                 "color": {"field": "change_pct", "type": "quantitative",
                           "title": "Change in rate since 2017 (%)",
                           "scale": {"domain": [-30, 0, 30], "range": ["#2c5a8c", "#d8d3c8", RED],
                                     "clamp": True, "interpolate": "rgb"},
                           "legend": {"orient": "top", "direction": "horizontal", "gradientLength": 140,
                                      "values": [-30, -15, 0, 15, 30], "format": "+d"}},
                 "order": {"field": "incidents", "sort": "descending"},
                 "tooltip": [{"field": "lga", "title": "Council"},
                             {"field": "incidents", "title": "Incidents", "format": ","},
                             {"field": "rate", "title": "Per 100,000 people", "format": ",.0f"},
                             {"field": "change_pct", "title": "Rate change since 2017 (%)", "format": "+.0f"}]}},
            {"data": pts, "transform": pt_tr + [{"filter": {"field": "lga", "oneOf": labels}}],
             "mark": {"type": "text", "fontWeight": 700, "fontSize": 11.5, "dy": -2, "color": INK,
                      "stroke": "#ffffff", "strokeWidth": 3, "strokeOpacity": 0.8},
             "encoding": {"longitude": {"field": "lon", "type": "quantitative"},
                          "latitude": {"field": "lat", "type": "quantitative"},
                          "text": {"field": "lga"}}},
            {"data": pts, "transform": pt_tr + [{"filter": {"field": "lga", "oneOf": labels}}],
             "mark": {"type": "text", "fontWeight": 700, "fontSize": 11.5, "dy": -2, "color": INK},
             "encoding": {"longitude": {"field": "lon", "type": "quantitative"},
                          "latitude": {"field": "lat", "type": "quantitative"},
                          "text": {"field": "lga"}}},
        ],
    }


write("07_symbols.vl.json", {
    "description": "Number of criminal incidents by council (circle size) and change in rate since 2017 (colour).",
    "hconcat": [
        symbol_map("sym_state", False, 470, 330, "Regional Victoria (Melbourne shaded, see zoom)",
                   ["Greater Geelong", "Ballarat", "Greater Bendigo", "Latrobe", "Mildura", "Greater Shepparton"]),
        symbol_map("sym_metro", True, 340, 330, "Zoom: metropolitan Melbourne",
                   ["Melbourne", "Casey", "Hume", "Wyndham", "Greater Dandenong", "Frankston"]),
    ],
    "spacing": 30,
    "resolve": {"legend": {"size": "shared", "color": "shared"}},
})

# ======================================================================
# 08  Bivariate choropleth: crime rate x socio-economic disadvantage
# ======================================================================
BIVAR = ["1-1", "2-1", "3-1", "1-2", "2-2", "3-2", "1-3", "2-3", "3-3"]
BIVAR_COLOURS = ["#e8e8e8", "#e4acac", "#c85a5a",
                 "#b0d5df", "#ad9ea5", "#985356",
                 "#64acbe", "#627f8c", "#574249"]
BIVAR_SCALE = {"domain": BIVAR, "range": BIVAR_COLOURS}
BIVAR_TIP = [{"field": "lga", "title": "Council"},
             {"field": "rate", "title": "Crime per 100,000", "format": ",.0f"},
             {"field": "disadvantage", "title": "Disadvantage (ABS)"}]


def bivar_map(metro_only, w, h, title):
    tr = geo_with_lga_data()
    if metro_only:
        tr.append({"filter": "datum.metro == 'True' || datum.metro == true"})
    return {"title": title, "width": w, "height": h, "data": GEO, "transform": tr, "projection": PROJ,
            "mark": {"type": "geoshape", "stroke": "#ffffff", "strokeWidth": 0.6},
            "encoding": {"color": {"field": "bivar", "type": "nominal", "legend": None, "scale": BIVAR_SCALE},
                         "tooltip": BIVAR_TIP}}


write("08_bivariate.vl.json", {
    "description": "Councils grouped by crime rate (thirds) and ABS disadvantage score (thirds).",
    "hconcat": [
        bivar_map(False, 430, 320, "All of Victoria"),
        bivar_map(True, 300, 320, "Zoom: metropolitan Melbourne"),
        {
            "title": {"text": "How to read the colours", "fontSize": 13},
            "data": {"url": "data/lga.csv"},
            "transform": [{"aggregate": [{"op": "count", "as": "councils"}],
                           "groupby": ["bivar", "crime_t", "disadv_t"]}],
            "width": 150, "height": 150,
            "encoding": {
                "x": {"field": "disadv_t", "type": "ordinal", "title": "More disadvantage →",
                      "axis": {"labelExpr": "['', 'Low', 'Mid', 'High'][datum.value]", "labelAngle": 0,
                               "domain": False, "ticks": False}},
                "y": {"field": "crime_t", "type": "ordinal", "title": "More crime →", "sort": "descending",
                      "axis": {"labelExpr": "['', 'Low', 'Mid', 'High'][datum.value]",
                               "domain": False, "ticks": False}},
            },
            "layer": [
                {"mark": {"type": "rect", "stroke": "#ffffff", "strokeWidth": 2},
                 "encoding": {"color": {"field": "bivar", "type": "nominal", "legend": None,
                                        "scale": BIVAR_SCALE}}},
                {"mark": {"type": "text", "fontSize": 12, "fontWeight": 700},
                 "encoding": {"text": {"field": "councils"},
                              "color": {"condition": {"test": "datum.bivar == '3-3' || datum.bivar == '2-3' || datum.bivar == '3-2'",
                                                      "value": "#ffffff"}, "value": INK},
                              "tooltip": [{"field": "councils", "title": "Number of councils"}]}},
            ],
        },
    ],
    "spacing": 24,
})

# ======================================================================
# 09  Small-multiple choropleths: four kinds of crime
# ======================================================================
write("09_small_multiples.vl.json", {
    "description": "Rate per 100,000 people for four offence divisions, by council, year ending June 2026.",
    "data": {"url": "data/lga_division.csv"},
    "transform": [
        {"lookup": "lga", "from": {"data": GEO, "key": "properties.lga"}, "as": "geo"},
        {"window": [{"op": "percent_rank", "as": "pr"}], "groupby": ["division"],
         "sort": [{"field": "rate"}]},
        {"calculate": "datum.pr < 0.2 ? 'Lowest fifth' : datum.pr < 0.4 ? 'Low' : datum.pr < 0.6 ? 'Middle' : "
                      "datum.pr < 0.8 ? 'High' : 'Highest fifth'", "as": "band"},
    ],
    "columns": 2,
    "facet": {"field": "division", "type": "nominal", "title": None,
              "sort": ["Property and deception", "Crimes against the person",
                       "Drug offences", "Public order and security"],
              "header": {"labelFontSize": 14, "labelAnchor": "start"}},
    "spec": {
        "width": 380, "height": 230,
        "projection": PROJ,
        "mark": {"type": "geoshape", "stroke": "#ffffff", "strokeWidth": 0.4},
        "encoding": {
            "shape": {"field": "geo", "type": "geojson"},
            "color": {"field": "band", "type": "ordinal",
                      "title": "Council's rate compared with other councils (for that crime type)",
                      "scale": {"domain": ["Lowest fifth", "Low", "Middle", "High", "Highest fifth"],
                                "range": ["#f6efe4", "#e9c9a4", "#d48f63", "#b3261e", "#6b100b"]},
                      "legend": {"orient": "top", "direction": "horizontal", "titleLimit": 500}},
            "tooltip": [{"field": "lga", "title": "Council"}, {"field": "division", "title": "Offence type"},
                        {"field": "rate", "title": "Per 100,000 people", "format": ",.0f"}],
        },
    },
    "spacing": {"column": 30, "row": 24},
})

# ======================================================================
# 10  Scatterplot: disadvantage score vs crime rate
# ======================================================================
LABEL_COUNCILS = ["Melbourne", "Latrobe", "Greater Dandenong", "Mildura", "Brimbank",
                  "Nillumbik", "Boroondara", "Queenscliffe", "Yarra"]
write("10_scatter.vl.json", {
    "description": "ABS disadvantage score (2021) against crime rate (2026) for every Victorian council.",
    "data": {"url": "data/lga.csv",
             "format": {"type": "csv", "parse": {"irsd_score": "number", "rate": "number",
                                                 "population": "number"}}},
    "transform": [{"calculate": "datum.metro == 'True' || datum.metro == true ? 'Metropolitan Melbourne' : 'Regional Victoria'",
                   "as": "area"}],
    "width": "container", "height": 380,
    "encoding": {
        "x": {"field": "irsd_score", "type": "quantitative", "scale": {"reverse": True, "domain": [880, 1100]},
              "title": "ABS disadvantage score (2021)   ← less disadvantaged · more disadvantaged →"},
        "y": {"field": "rate", "type": "quantitative", "title": "Incidents per 100,000 people (2026)",
              "axis": {"format": ",.0f"}},
    },
    "layer": [
        {"transform": [{"regression": "rate", "on": "irsd_score"}],
         "mark": {"type": "line", "color": SOFT, "strokeDash": [6, 4], "strokeWidth": 1.5}},
        {"mark": {"type": "circle", "stroke": "#ffffff", "strokeWidth": 0.8},
         "params": [{"name": "hover", "select": {"type": "point", "on": "mouseover", "fields": ["lga"],
                                                  "clear": "mouseout"}}],
         "encoding": {
             "size": {"field": "population", "type": "quantitative", "title": "Population",
                      "scale": {"range": [25, 600]}, "legend": {"labelExpr": "format(datum.value, ',')", "values": [10000, 100000, 300000]}},
             "color": {"field": "area", "type": "nominal", "title": None,
                       "scale": {"domain": ["Metropolitan Melbourne", "Regional Victoria"], "range": [NAVY, "#c07a1d"]}},
             "opacity": {"condition": {"param": "hover", "empty": True, "value": 0.85}, "value": 0.25},
             "tooltip": [{"field": "lga", "title": "Council"},
                         {"field": "rate", "title": "Per 100,000 people", "format": ",.0f"},
                         {"field": "irsd_score", "title": "Disadvantage score", "format": ".0f"},
                         {"field": "disadvantage", "title": "Group"}]}},
        {"transform": [{"filter": {"field": "lga", "oneOf": LABEL_COUNCILS}}],
         "mark": {"type": "text", "align": "left", "dx": 9, "fontSize": 11.5, "fontWeight": 600},
         "encoding": {"text": {"field": "lga"}}},
        {"transform": [{"filter": "datum.lga == 'Melbourne'"}],
         "mark": {"type": "text", "align": "left", "dx": 12, "dy": 26, "fontSize": 11.5, "color": SOFT,
                  "fontStyle": "italic"},
         "encoding": {"text": {"value": ["The city's rate looks high because millions of workers",
                                         "and visitors pass through, but only residents are counted."]}}},
    ],
})

# ======================================================================
# 11  Box plot: crime rate by disadvantage group
# ======================================================================
GROUPS = ["Least disadvantaged", "Less disadvantaged", "Middle", "More disadvantaged", "Most disadvantaged"]
write("11_boxplot.vl.json", {
    "description": "Distribution of council crime rates within each ABS disadvantage group (Victorian deciles).",
    "data": {"url": "data/lga.csv"},
    "transform": [{"calculate": "(random() - 0.5) * 0.6", "as": "jitter"}],
    "width": "container", "height": 340,
    "encoding": {
        "x": {"field": "disadvantage", "type": "ordinal", "sort": GROUPS, "title": None,
              "axis": {"labelAngle": 0, "labelFontSize": 12.5, "labelFontWeight": 600}},
    },
    "layer": [
        {"mark": {"type": "boxplot", "extent": "min-max", "size": 46, "opacity": 0.9,
                  "median": {"color": INK, "strokeWidth": 2.5},
                  "rule": {"color": SOFT}},
         "encoding": {
             "y": {"field": "rate", "type": "quantitative", "title": "Incidents per 100,000 people",
                   "axis": {"format": ",.0f"}},
             "color": {"field": "disadvantage", "type": "ordinal", "legend": None,
                       "scale": {"domain": GROUPS, "range": ["#f3dccb", "#eab598", "#d98a6a", "#c55a43", RED]}}}},
        {"mark": {"type": "circle", "size": 26, "color": INK, "opacity": 0.55},
         "encoding": {"y": {"field": "rate", "type": "quantitative"},
                      "xOffset": {"field": "jitter", "type": "quantitative", "scale": {"domain": [-1, 1]}},
                      "tooltip": [{"field": "lga", "title": "Council"},
                                  {"field": "rate", "title": "Per 100,000 people", "format": ",.0f"}]}},
        {"transform": [{"aggregate": [{"op": "median", "field": "rate", "as": "median"}],
                        "groupby": ["disadvantage"]}],
         "mark": {"type": "text", "dx": 34, "align": "left", "fontWeight": 700, "fontSize": 12.5},
         "encoding": {"y": {"field": "median", "type": "quantitative"},
                      "text": {"field": "median", "format": ",.0f"}}},
    ],
})

# ======================================================================
# 12  Dumbbell chart: share of incidents unsolved, 2017 vs 2026
# ======================================================================
write("12_dumbbell.vl.json", {
    "description": "Share of incidents with no offender identified ('unsolved'), 2017 vs 2026, by offence type.",
    "data": {"url": "data/charge_status.csv"},
    "transform": [
        {"filter": "datum.status == 'Unsolved' && (datum.year == 2017 || datum.year == 2026) && datum.division != 'Other offences'"},
        {"calculate": "'' + datum.year", "as": "Year"},
        {"calculate": "datum.year == 2026 ? datum.share : 0", "as": "s26"},
        {"joinaggregate": [{"op": "sum", "field": "s26", "as": "share_2026"}], "groupby": ["division"]},
    ],
    "width": "container", "height": {"step": 52},
    "encoding": {
        "y": {"field": "division", "type": "nominal", "title": None,
              "sort": {"field": "share_2026", "order": "descending"},
              "axis": {"domain": False, "ticks": False, "labelFontSize": 13, "labelFontWeight": 600,
                       "labelPadding": 10}},
        "x": {"field": "share", "type": "quantitative", "title": "Share of incidents left unsolved",
              "axis": {"format": ".0%", "values": [0, 0.2, 0.4, 0.6, 0.8]}, "scale": {"domain": [0, 0.85]}},
    },
    "layer": [
        {"mark": {"type": "line", "color": "#c9c4b8", "strokeWidth": 5},
         "encoding": {"detail": {"field": "division"}}},
        {"mark": {"type": "circle", "size": 220, "opacity": 1, "stroke": "#ffffff", "strokeWidth": 1.5},
         "encoding": {"color": {"field": "Year", "type": "nominal", "title": "Year ending June",
                                "scale": {"domain": ["2017", "2026"], "range": ["#a9a397", RED]},
                                "legend": {"orient": "top", "direction": "horizontal"}},
                      "tooltip": [{"field": "division", "title": "Offence type"},
                                  {"field": "year", "title": "Year ending June"},
                                  {"field": "incidents", "title": "Unsolved incidents", "format": ","},
                                  {"field": "share", "title": "Share unsolved", "format": ".0%"}]}},
        {"transform": [{"filter": "datum.year == 2026"}],
         "mark": {"type": "text", "dy": -17, "fontWeight": 700, "color": RED, "fontSize": 12},
         "encoding": {"text": {"field": "share", "format": ".0%"}}},
        {"transform": [{"filter": "datum.year == 2017"}],
         "mark": {"type": "text", "dy": -17, "color": SOFT, "fontSize": 12},
         "encoding": {"text": {"field": "share", "format": ".0%"}}},
    ],
})
