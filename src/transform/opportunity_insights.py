# src/transform/opportunity_insights.py
import pathlib
import pandas as pd

PROCESSED = pathlib.Path("data/processed")
STATIONS  = PROCESSED / "stations_ca.csv"
SUMMARY   = PROCESSED / "ev_summary_by_region.csv"  # region = county-or-city fallback
OUTDIR    = PROCESSED / "insights"
OUTDIR.mkdir(parents=True, exist_ok=True)


def main():
    # -------- Load inputs --------
    stations = pd.read_csv(STATIONS, low_memory=False)
    region   = pd.read_csv(SUMMARY, low_memory=False)

    # ensure numeric types we rely on
    for c in ["ev_level2_evse_num", "ev_dc_fast_num", "latitude", "longitude"]:
        if c in stations.columns:
            stations[c] = pd.to_numeric(stations[c], errors="coerce").fillna(0)

    # -------- Opportunities --------
    # 1) Regions with 0 DCFC but lots of Level-2 (upgrade to DCFC first)
    if {"dcfc_ports", "level2_ports"}.issubset(region.columns):
        zero_dcfc_regions = (
            region.loc[region["dcfc_ports"] == 0]
                  .sort_values("level2_ports", ascending=False)
        )
        zero_dcfc_regions.to_csv(
            OUTDIR / "opportunity_regions_zero_dcfc_sorted_by_level2.csv",
            index=False
        )

    # 2) Stations with many Level-2 ports and 0 DCFC (site-level upgrade candidates)
    lvl2_heavy = stations[
        (stations.get("ev_dc_fast_num", 0) == 0) &
        (stations.get("ev_level2_evse_num", 0) >= 8)
    ].copy()

    keep_cols = [
        "id", "station_name", "city", "county", "state",
        "latitude", "longitude",
        "ev_level2_evse_num", "ev_dc_fast_num", "ev_network"
    ]
    for c in keep_cols:
        if c not in lvl2_heavy.columns:
            lvl2_heavy[c] = pd.NA

    lvl2_heavy = lvl2_heavy[keep_cols].sort_values("ev_level2_evse_num", ascending=False)
    lvl2_heavy.to_csv(
        OUTDIR / "opportunity_stations_level2_no_dcfc_8plus.csv",
        index=False
    )

    # 3) Regions with high ports_total but low dcfc_share (fast-charging lags)
    # 3) Regions with high ports_total (>=50) but low (0 < dcfc_share <= 0.20)
    if {"ports_total", "dcfc_share"}.issubset(region.columns):
        rich = region.loc[region["ports_total"] >= 50].copy()
        if not rich.empty:
            laggers = rich.loc[(rich["dcfc_share"] > 0) & (rich["dcfc_share"] <= 0.20)].copy()
            laggers = laggers.sort_values(by=["dcfc_share", "ports_total"], ascending=[True, False])
            laggers.to_csv(OUTDIR / "opportunity_regions_low_dcfc_share_high_ports.csv", index=False)

    # -------- Likely busy hubs (capacity proxy) --------s
    # 4) Top stations by DCFC ports
    if "ev_dc_fast_num" in stations.columns:
        top_dcfc_sites = (
            stations.loc[stations["ev_dc_fast_num"] > 0]
                    .sort_values("ev_dc_fast_num", ascending=False)
        )
        top_dcfc_sites[keep_cols].head(200).to_csv(
            OUTDIR / "likely_busy_top_stations_by_dcfc_ports.csv",
            index=False
        )

    # 5) Top stations by total ports (L2 + DCFC)
    stations["total_ports"] = stations.get("ev_level2_evse_num", 0) + stations.get("ev_dc_fast_num", 0)
    stations.sort_values("total_ports", ascending=False)[keep_cols + ["total_ports"]].head(200).to_csv(
        OUTDIR / "likely_busy_top_stations_by_total_ports.csv",
        index=False
    )

    # -------- Done --------
    print("Saved insight tables in:", OUTDIR.resolve())
    for p in OUTDIR.glob("*.csv"):
        print("-", p.name)


if __name__ == "__main__":
    main()
