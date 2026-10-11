"""
prep_data.py
------------
Turns the three raw source workbooks into the small CSV files used by the
Vega-Lite charts in /js. No values are changed: the script only filters,
renames, sums and joins.

Sources (download and place in prep/raw/):
  lga.xlsx    Crime Statistics Agency (CSA), Data Tables LGA Criminal Incidents,
              Year Ending June 2026
  state.xlsx  CSA, Data Tables Criminal Incidents Visualisation,
              Year Ending June 2026
  seifa.xlsx  Australian Bureau of Statistics (ABS), SEIFA 2021,
              Local Government Area Indexes

Run:  python prep_data.py   (needs pandas + openpyxl)
"""

import os
import re
import pandas as pd

RAW = os.path.join(os.path.dirname(__file__), "raw")
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
FIRST, LAST = 2017, 2026          # ten years in the CSA release

# CSA uses current council names; ABS 2021 still uses older ones.
SEIFA_RENAME = {"Colac Otway": "Colac-Otway", "Moreland": "Merri-bek"}

# Short, plain-English labels for the six offence divisions.
DIVISION_LABEL = {
    "A Crimes against the person": "Crimes against the person",
    "B Property and deception offences": "Property and deception",
    "C Drug offences": "Drug offences",
    "D Public order and security offences": "Public order and security",
    "E Justice procedures offences": "Justice procedures",
    "F Other offences": "Other offences",
}

# The 31 councils of metropolitan Melbourne (used for the zoomed-in maps).
METRO = {
    "Banyule", "Bayside", "Boroondara", "Brimbank", "Cardinia", "Casey", "Darebin",
    "Frankston", "Glen Eira", "Greater Dandenong", "Hobsons Bay", "Hume", "Kingston",
    "Knox", "Manningham", "Maribyrnong", "Maroondah", "Melbourne", "Melton",
    "Merri-bek", "Monash", "Moonee Valley", "Mornington Peninsula", "Nillumbik",
    "Port Phillip", "Stonnington", "Whitehorse", "Whittlesea", "Wyndham", "Yarra",
    "Yarra Ranges",
}

NOT_COUNCILS = {"Total", "Justice Institutions and Immigration Facilities",
                "Unincorporated Vic"}


def strip_code(text):
    """'A20 Assault and related offences' -> 'Assault and related offences'."""
    return re.sub(r"^[A-Z]\d+\s+", "", str(text)).strip()


def save(df, name):
    df.to_csv(os.path.join(OUT, name), index=False)
    print(f"  {name:28s} {len(df):6d} rows")


def main():
    os.makedirs(OUT, exist_ok=True)
    lga_book = pd.read_excel(os.path.join(RAW, "lga.xlsx"), sheet_name=None)
    state_book = pd.read_excel(os.path.join(RAW, "state.xlsx"), sheet_name=None)

    t1 = lga_book["Table 01"].copy()
    t1["lga"] = t1["Local Government Area"].str.strip()

    # ---------- 1. Statewide trend (state Table 01, all offences summed) ----------
    s1 = state_book["Table 01"].iloc[:, :7]
    s1.columns = ["year", "ye", "division", "subdivision", "subgroup",
                  "incidents", "rate"]
    s1["division"] = s1["division"].map(DIVISION_LABEL)
    save(s1.groupby("year", as_index=False)[["incidents", "rate"]].sum(), "state_trend.csv")

    # ---------- 2. Offence division and subdivision by year ----------

    div = s1.groupby(["year", "division"], as_index=False)[["incidents", "rate"]].sum()
    save(div, "division_year.csv")

    sub = s1.groupby(["year", "division", "subdivision"], as_index=False)[["incidents", "rate"]].sum()
    sub["subdivision"] = sub["subdivision"].map(strip_code)
    base = sub[sub.year == FIRST].set_index("subdivision")["rate"]
    sub["index"] = sub.apply(lambda r: 100 * r["rate"] / base.get(r["subdivision"], float("nan")), axis=1)
    save(sub, "subdivision_year.csv")

    # Subgroup ranks for the bump chart (top 10 in the latest year)
    grp = s1.groupby(["year", "subgroup"], as_index=False)["incidents"].sum()
    grp["subgroup"] = grp["subgroup"].map(strip_code)
    top = grp[grp.year == LAST].nlargest(10, "incidents")["subgroup"]
    grp["rank"] = grp.groupby("year")["incidents"].rank(ascending=False, method="first")
    save(grp[grp.subgroup.isin(top)].sort_values(["year", "rank"]), "subgroup_rank.csv")

    # ---------- 3. Family-violence share (state Table 03) ----------
    s3 = state_book["Table 03"].iloc[:, :7]
    s3.columns = ["year", "ye", "division", "subdivision", "flag", "incidents", "rate"]
    s3["division"] = s3["division"].map(DIVISION_LABEL)
    fam = s3.groupby(["year", "division", "flag"], as_index=False)["incidents"].sum()
    save(fam, "family_flag.csv")

    # ---------- 4. Charge status by division (state Table 04) ----------
    s4 = state_book["Table 04"].iloc[:, :7]
    s4.columns = ["year", "ye", "division", "subdivision", "subgroup", "status", "incidents"]
    s4["division"] = s4["division"].map(DIVISION_LABEL)
    st = s4.groupby(["year", "division", "status"], as_index=False)["incidents"].sum()
    st["share"] = st["incidents"] / st.groupby(["year", "division"])["incidents"].transform("sum")
    save(st, "charge_status.csv")

    # ---------- 5. Council (LGA) level ----------
    councils = t1[~t1["lga"].isin(NOT_COUNCILS)].rename(columns={
        "Year": "year", "Incidents Recorded": "incidents",
        "Rate per 100,000 population": "rate"})
    councils["region"] = councils["Police Region"].str.replace(r"^\d\s+", "", regex=True)
    save(councils[["year", "lga", "region", "incidents", "rate"]], "lga_trend.csv")

    latest = councils[councils.year == LAST].set_index("lga")
    first = councils[councils.year == FIRST].set_index("lga")
    lga = latest[["region", "incidents", "rate"]].copy()
    lga["rate_2017"] = first["rate"]
    lga["change_pct"] = 100 * (lga["rate"] / lga["rate_2017"] - 1)

    # Share of incidents still unsolved (LGA Table 05)
    t5 = lga_book["Table 05"]
    t5 = t5[t5.Year == LAST].copy()
    t5["lga"] = t5["Local Government Area"].str.strip()
    piv = t5.pivot_table(index="lga", columns="Charge Status",
                         values="Incidents Recorded", aggfunc="sum")
    lga["unsolved_pct"] = 100 * piv["Unsolved"] / piv.sum(axis=1)

    # ---------- 6. Join ABS SEIFA (second source) ----------
    se = pd.read_excel(os.path.join(RAW, "seifa.xlsx"), sheet_name="Table 2", header=5)
    se = se.iloc[:, [0, 1, 2, 3, 10, 11]]
    se.columns = ["code", "name", "population", "irsd_score", "irsd_rank_vic", "irsd_decile_vic"]
    se = se[se["code"].astype(str).str.match(r"^2\d{4}$")]          # Victoria only
    se["name"] = se["name"].str.replace(r" \(Vic\.\)", "", regex=True).replace(SEIFA_RENAME)
    lga = lga.join(se.set_index("name")[["code", "population", "irsd_score", "irsd_decile_vic"]])

    # Plain-language disadvantage group from the Victorian decile (1 = most disadvantaged)
    lga["disadvantage"] = pd.cut(lga["irsd_decile_vic"], [0, 2, 4, 6, 8, 10],
                                 labels=["Most disadvantaged", "More disadvantaged", "Middle",
                                         "Less disadvantaged", "Least disadvantaged"])
    # Bivariate classes: crime rate tercile x disadvantage tercile (1 = low)
    lga["crime_t"] = pd.qcut(lga["rate"], 3, labels=[1, 2, 3]).astype(int)
    lga["disadv_t"] = pd.qcut(-lga["irsd_score"], 3, labels=[1, 2, 3]).astype(int)
    lga["bivar"] = lga["crime_t"].astype(str) + "-" + lga["disadv_t"].astype(str)
    lga["metro"] = lga.index.isin(METRO)
    lga = lga.reset_index().rename(columns={"index": "lga"})
    save(lga.round(2), "lga.csv")

    # ---------- 7. Council rate by offence division (LGA Table 02) ----------
    t2 = lga_book["Table 02"]
    t2 = t2[t2.Year == LAST]
    d2 = t2.groupby(["Local Government Area", "Offence Division"], as_index=False)[
        "LGA Rate per 100,000 population"].sum()
    d2.columns = ["lga", "division", "rate"]
    d2["lga"] = d2["lga"].str.strip()
    d2["division"] = d2["division"].map(DIVISION_LABEL)
    save(d2[d2.division.isin(["Crimes against the person", "Property and deception",
                              "Drug offences", "Public order and security"])].round(1),
         "lga_division.csv")

    # Suburb -> council lookup for building council shapes from suburb shapes
    t3 = lga_book["Table 03"]
    sub_lga = t3.groupby(["Suburb/Town Name", "Local Government Area"], as_index=False)[
        "Incidents Recorded"].sum()
    sub_lga.columns = ["suburb", "lga", "incidents"]
    sub_lga.to_csv(os.path.join(os.path.dirname(__file__), "suburb_lga.csv"), index=False)


if __name__ == "__main__":
    main()
