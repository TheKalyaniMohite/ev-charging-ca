# src/transform/make_county_supply.py
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
EXTERNAL = ROOT / "data" / "external"

STATIONS_IN = PROCESSED / "stations_ca.csv"               # from earlier pipeline
ZIP_XWALK   = EXTERNAL / "zip_to_county_ca.csv"           # Step 2 (zip,county_fips)
EV_COUNTS   = EXTERNAL / "ev_counts_by_county_ca.csv"     # Step 1 (county,ev_count)

OUT_CSV     = PROCESSED / "ev_county_supply_vs_demand.csv"

# CA county FIPS -> county name (CEC naming)
FIPS_TO_NAME = {
    "06001":"Alameda","06003":"Alpine","06005":"Amador","06007":"Butte","06009":"Calaveras",
    "06011":"Colusa","06013":"Contra Costa","06015":"Del Norte","06017":"El Dorado","06019":"Fresno",
    "06021":"Glenn","06023":"Humboldt","06025":"Imperial","06027":"Inyo","06029":"Kern",
    "06031":"Kings","06033":"Lake","06035":"Lassen","06037":"Los Angeles","06039":"Madera",
    "06041":"Marin","06043":"Mariposa","06045":"Mendocino","06047":"Merced","06049":"Modoc",
    "06051":"Mono","06053":"Monterey","06055":"Napa","06057":"Nevada","06059":"Orange",
    "06061":"Placer","06063":"Plumas","06065":"Riverside","06067":"Sacramento","06069":"San Benito",
    "06071":"San Bernardino","06073":"San Diego","06075":"San Francisco","06077":"San Joaquin",
    "06079":"San Luis Obispo","06081":"San Mateo","06083":"Santa Barbara","06085":"Santa Clara",
    "06087":"Santa Cruz","06089":"Shasta","06091":"Sierra","06093":"Siskiyou","06095":"Solano",
    "06097":"Sonoma","06099":"Stanislaus","06101":"Sutter","06103":"Tehama","06105":"Trinity",
    "06107":"Tulare","06109":"Tuolumne","06111":"Ventura","06113":"Yolo","06115":"Yuba"
}

def load_data():
    df_st = pd.read_csv(STATIONS_IN, dtype={"zip":"string"})
    df_zip = pd.read_csv(ZIP_XWALK, dtype={"zip":"string","county_fips":"string"})
    df_ev  = pd.read_csv(EV_COUNTS)

    # normalize EV counts column names
    df_ev.columns = [c.strip().lower() for c in df_ev.columns]
    if "county" not in df_ev.columns or "ev_count" not in df_ev.columns:
        raise ValueError("ev_counts_by_county_ca.csv must have columns: county, ev_count")

    # keep only the 58 canonical CA counties
    canonical = {n.lower() for n in FIPS_TO_NAME.values()}
    df_ev = df_ev[df_ev["county"].str.strip().str.lower().isin(canonical)].copy()

    return df_st, df_zip, df_ev

def derive_county_supply(df_st, df_zip):
    """
    Expect stations columns:
      - 'zip'
      - 'ev_level2_evse_num'  (Level 2 ports)
      - 'ev_dc_fast_num'      (DCFC ports)
    Adjust here if your column names differ.
    """
    needed = ["zip", "ev_level2_evse_num", "ev_dc_fast_num"]
    missing = [c for c in needed if c not in df_st.columns]
    if missing:
        raise ValueError(f"Missing columns in stations_ca.csv: {missing}")

    df = df_st.merge(df_zip[["zip","county_fips"]], on="zip", how="left")
    df["county"] = df["county_fips"].map(FIPS_TO_NAME)
    df = df.dropna(subset=["county"]).copy()

    for c in ["ev_level2_evse_num","ev_dc_fast_num"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    grp = df.groupby("county", as_index=False).agg(
        level2_ports=("ev_level2_evse_num","sum"),
        dcfc_ports=("ev_dc_fast_num","sum")
    )
    grp["ports_total"] = grp["level2_ports"] + grp["dcfc_ports"]
    return grp

def join_ev_counts(county_supply, df_ev):
    # normalize names
    supply = county_supply.copy()
    supply["county_norm"] = supply["county"].str.strip().str.lower()

    ev = df_ev.copy()
    ev["county_norm"] = ev["county"].str.strip().str.lower()

    # start from EV counts (all counties), left-join supply
    merged = ev.merge(
        supply[["county_norm","level2_ports","dcfc_ports","ports_total"]],
        on="county_norm",
        how="left"
    )

    # prefer the EV table's county naming for output
    merged["county"] = merged["county"]  # already present from ev table

    # fill missing supply with zeros
    for c in ["level2_ports","dcfc_ports","ports_total"]:
        merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0)

    merged["ev_count"] = pd.to_numeric(merged["ev_count"], errors="coerce").fillna(0).astype(int)

    # keep nice columns
    keep = ["county","level2_ports","dcfc_ports","ports_total","ev_count"]
    return merged[keep]

def compute_metrics(df):
    out = df.copy()
    # existing KPIs
    out["dcfc_share"] = (out["dcfc_ports"] / out["ports_total"]).where(out["ports_total"] > 0, 0)
    out["ports_per_1000_evs"] = (out["ports_total"] / out["ev_count"] * 1000).where(out["ev_count"] > 0, 0)

    # --- Siting score ---
    # min-max normalize helper
    def minmax(series):
        s = pd.to_numeric(series, errors="coerce").fillna(0)
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 0 else pd.Series(0, index=s.index)

    norm_cov_gap = 1 - minmax(out["ports_per_1000_evs"])   # lower coverage -> higher gap
    norm_ev_dmd  = minmax(out["ev_count"])                  # more EVs -> higher demand

    out["siting_score"] = 0.6 * norm_cov_gap + 0.4 * norm_ev_dmd

    # nice ordering
    cols = [
        "county",
        "level2_ports","dcfc_ports","ports_total",
        "ev_count","ports_per_1000_evs","dcfc_share",
        "siting_score"
    ]
    return out[cols]

def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df_st, df_zip, df_ev = load_data()
    county_supply = derive_county_supply(df_st, df_zip)
    merged = join_ev_counts(county_supply, df_ev)
    final = compute_metrics(merged)
    final.to_csv(OUT_CSV, index=False)
    top10 = final.sort_values("siting_score", ascending=False).head(10)
    (PROCESSED / "siting_score_top10_counties.csv").write_text(top10.to_csv(index=False))
    print(f"Saved county file: {OUT_CSV} (rows={len(final)})")
    print("Saved Top 10 siting list: data/processed/siting_score_top10_counties.csv")

if __name__ == "__main__":
    main()
