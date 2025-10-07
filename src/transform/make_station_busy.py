# src/transform/make_station_busy.py
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
EXTERNAL = ROOT / "data" / "external"

STATIONS_IN = PROCESSED / "stations_ca.csv"            # cleaned stations you already generated
ZIP_XWALK   = EXTERNAL / "zip_to_county_ca.csv"        # (zip, county_fips) you built earlier

# CA county FIPS -> county name
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

OUT_ALL = PROCESSED / "station_busy_candidates.csv"
OUT_TOP = PROCESSED / "station_busy_top25.csv"

def main():
    df = pd.read_csv(STATIONS_IN, dtype={"zip":"string"}, low_memory=False)

    # Expected column names – adjust here if yours differ
    # station name/city/zip
    name_col = "station_name" if "station_name" in df.columns else "station_name"
    city_col = "city" if "city" in df.columns else "city"
    zip_col  = "zip" if "zip" in df.columns else "zip"

    # port counts
    l2_col = "ev_level2_evse_num"
    dc_col = "ev_dc_fast_num"
    missing = [c for c in [name_col, city_col, zip_col, l2_col, dc_col] if c not in df.columns]
    if missing:
        raise ValueError(f"stations_ca.csv is missing needed columns: {missing}")

    # keep only needed fields
    keep = [name_col, city_col, zip_col, l2_col, dc_col]
    df = df[keep].copy()

    # numeric ports
    df[l2_col] = pd.to_numeric(df[l2_col], errors="coerce").fillna(0)
    df[dc_col] = pd.to_numeric(df[dc_col], errors="coerce").fillna(0)

    # add county via ZIP crosswalk
    xw = pd.read_csv(ZIP_XWALK, dtype={"zip":"string","county_fips":"string"})
    df = df.merge(xw[["zip","county_fips"]], on="zip", how="left")
    df["county"] = df["county_fips"].map(FIPS_TO_NAME)

    # compute totals + busy score
    df["total_ports"] = df[l2_col] + df[dc_col]
    df["likely_busy_score"] = 1.5 * df[dc_col] + 0.25 * df[l2_col]

    # order & rename for clarity
    out = df.rename(columns={
        name_col: "station_name",
        city_col: "city",
        zip_col: "zip",
        l2_col: "level2_ports",
        dc_col: "dcfc_ports",
    })[["station_name","city","zip","county","level2_ports","dcfc_ports","total_ports","likely_busy_score"]]

    # sort & save
    out_sorted = out.sort_values(["likely_busy_score","dcfc_ports","total_ports"], ascending=False)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out_sorted.to_csv(OUT_ALL, index=False)
    out_sorted.head(25).to_csv(OUT_TOP, index=False)

    print(f"Saved: {OUT_ALL} (rows={len(out_sorted)})")
    print(f"Saved: {OUT_TOP}")

if __name__ == "__main__":
    main()
