import pathlib
import pandas as pd

RAW_CSV = "data/raw/afdc_stations_ca.csv"

PROCESSED_DIR = pathlib.Path("data/processed")
STATIONS_OUT = PROCESSED_DIR / "stations_ca.csv"
PORTS_OUT = PROCESSED_DIR / "ports_ca.csv"
COUNTY_SUMMARY_OUT = PROCESSED_DIR / "ev_summary_by_county.csv"

KEEP_COLS = [
    "id", "station_name", "status_code", "ev_network", "ev_network_web",
    "city", "county", "state", "zip", "latitude", "longitude",
    "ev_dc_fast_num", "ev_level2_evse_num", "ev_connector_types",
    "access_days_time", "facility_type", "station_phone"
]

def load_raw():
    df = pd.read_csv(RAW_CSV, dtype=str, low_memory=False)
    # ensure columns exist even if AFDC omitted some
    for c in KEEP_COLS:
        if c not in df.columns:
            df[c] = pd.NA
    return df[KEEP_COLS].copy()

def clean_stations(df: pd.DataFrame) -> pd.DataFrame:
    # types
    num_cols = ["latitude", "longitude", "ev_dc_fast_num", "ev_level2_evse_num"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # normalize county names (title case, strip " County" if present)
    def norm_county(x):
        if pd.isna(x):
            return x
        x = str(x).strip()
        if x.lower().endswith(" county"):
            x = x[:-7]
        return x.title()
    df["county"] = df["county"].apply(norm_county)

    # drop rows missing lat/lon (can’t map)
    df = df.dropna(subset=["latitude", "longitude"])

    # fill NA port counts with 0
    df["ev_dc_fast_num"] = df["ev_dc_fast_num"].fillna(0).astype(int)
    df["ev_level2_evse_num"] = df["ev_level2_evse_num"].fillna(0).astype(int)

    # standardize connector types as comma-separated lower strings
    df["ev_connector_types"] = df["ev_connector_types"].fillna("").astype(str)

    def title_or_na(x):
        if pd.isna(x) or str(x).strip() == "":
            return pd.NA
        return str(x).strip().title()

    df["county"] = df["county"].apply(title_or_na)
    df["city"] = df["city"].apply(title_or_na)

    df["region"] = df["county"]
    df.loc[df["region"].isna(), "region"] = df["city"]  # fallback to city
    # status sanity: keep status_code if present; AFDC fetch already filters to status=E
    return df

def make_ports_table(df_stations: pd.DataFrame) -> pd.DataFrame:
    """
    Build one row per port for Level2 and DCFC to enable per-port mapping and counts.
    We replicate station rows according to the number of ports.
    """
    # Level 2
    lvl2 = df_stations.loc[df_stations["ev_level2_evse_num"] > 0, [
        "id","county","city","state","latitude","longitude","ev_network"
    ]].copy()
    lvl2 = lvl2.reindex(lvl2.index.repeat(df_stations.loc[lvl2.index, "ev_level2_evse_num"]))
    lvl2["level"] = "Level2"

    # DC Fast
    dcfc = df_stations.loc[df_stations["ev_dc_fast_num"] > 0, [
        "id","county","city","state","latitude","longitude","ev_network"
    ]].copy()
    dcfc = dcfc.reindex(dcfc.index.repeat(df_stations.loc[dcfc.index, "ev_dc_fast_num"]))
    dcfc["level"] = "DCFC"

    ports = pd.concat([lvl2, dcfc], ignore_index=True)
    ports.rename(columns={"id": "station_id"}, inplace=True)
    return ports[["station_id","level","ev_network","county","city","state","latitude","longitude"]]

def make_county_summary(df_stations: pd.DataFrame) -> pd.DataFrame:
    grp = df_stations.groupby("county", dropna=False).agg(
        level2_ports=("ev_level2_evse_num","sum"),
        dcfc_ports=("ev_dc_fast_num","sum")
    ).reset_index()
    grp["ports_total"] = grp["level2_ports"] + grp["dcfc_ports"]
    grp["dcfc_share"] = (grp["dcfc_ports"] / grp["ports_total"]).fillna(0).round(4)
    return grp.sort_values("ports_total", ascending=False)

def make_region_summary(df_stations: pd.DataFrame) -> pd.DataFrame:
    grp = df_stations.groupby("region", dropna=False).agg(
        level2_ports=("ev_level2_evse_num","sum"),
        dcfc_ports=("ev_dc_fast_num","sum")
    ).reset_index()
    grp["ports_total"] = grp["level2_ports"] + grp["dcfc_ports"]
    grp["dcfc_share"] = (grp["dcfc_ports"] / grp["ports_total"]).fillna(0).round(4)
    return grp.sort_values("ports_total", ascending=False)

def main():
    REGION_SUMMARY_OUT = PROCESSED_DIR / "ev_summary_by_region.csv"

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df_raw = load_raw()
    df_stations = clean_stations(df_raw)

    # Save cleaned stations
    df_stations.to_csv(STATIONS_OUT, index=False)

    # Ports table (may be large; OK)
    ports = make_ports_table(df_stations)
    ports.to_csv(PORTS_OUT, index=False)

    # County KPI summary
    county_summary = make_county_summary(df_stations)
    county_summary.to_csv(COUNTY_SUMMARY_OUT, index=False)

    region_summary = make_region_summary(df_stations)
    region_summary.to_csv(REGION_SUMMARY_OUT, index=False)

    print("Saved processed outputs:")
    print(f"- Stations: {STATIONS_OUT}")
    print(f"- Ports   : {PORTS_OUT} (rows={len(ports)})")
    print(f"- County summary: {COUNTY_SUMMARY_OUT}")
    print(f"- Region summary: {REGION_SUMMARY_OUT}")

if __name__ == "__main__":
    main()
