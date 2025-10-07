import os
import json
import time
import pathlib
import requests
import pandas as pd

AFDC_ENDPOINT = "https://developer.nrel.gov/api/alt-fuel-stations/v1.json"

CSV_COLUMNS = [
    "id", "station_name", "status_code", "ev_network", "ev_network_web",
    "city", "county", "state", "zip", "latitude", "longitude",
    "ev_dc_fast_num", "ev_level2_evse_num", "ev_connector_types",
    "access_days_time", "facility_type", "station_phone"
]

def ensure_dirs():
    pathlib.Path("data/raw").mkdir(parents=True, exist_ok=True)

def fetch_all_stations(api_key: str) -> list:
    stations = []
    limit = 200
    offset = 0
    session = requests.Session()
    params = {
        "api_key": api_key,
        "fuel_type": "ELEC",
        "state": "CA",
        "status": "E",
        "limit": limit,
        "offset": offset
    }
    while True:
        params["offset"] = offset
        r = session.get(AFDC_ENDPOINT, params=params, timeout=60)
        r.raise_for_status()
        payload = r.json()
        batch = payload.get("fuel_stations", [])
        total = payload.get("total_results", 0)
        stations.extend(batch)
        print(f"Fetched {len(stations)} / {total} (offset={offset})")
        if len(stations) >= total or not batch:
            break
        offset += limit
        time.sleep(0.2)
    return stations

def to_flat_csv(stations: list, out_csv: str):
    def row_map(s):
        return {
            "id": s.get("id"),
            "station_name": s.get("station_name"),
            "status_code": s.get("status_code"),
            "ev_network": s.get("ev_network"),
            "ev_network_web": s.get("ev_network_web"),
            "city": s.get("city"),
            "county": s.get("county"),
            "state": s.get("state"),
            "zip": s.get("zip"),
            "latitude": s.get("latitude"),
            "longitude": s.get("longitude"),
            "ev_dc_fast_num": s.get("ev_dc_fast_num"),
            "ev_level2_evse_num": s.get("ev_level2_evse_num"),
            "ev_connector_types": ",".join(s.get("ev_connector_types") or []) if isinstance(s.get("ev_connector_types"), list) else s.get("ev_connector_types"),
            "access_days_time": s.get("access_days_time"),
            "facility_type": s.get("facility_type"),
            "station_phone": s.get("station_phone"),
        }
    rows = [row_map(s) for s in stations]
    df = pd.DataFrame(rows, columns=CSV_COLUMNS)
    df.to_csv(out_csv, index=False)

def main():
    api_key = os.getenv("NREL_API_KEY")
    if not api_key:
        raise SystemExit('ERROR: NREL_API_KEY not set. In PowerShell: $env:NREL_API_KEY = "YOUR_KEY"')
    ensure_dirs()
    out_json = "data/raw/afdc_stations_ca.json"
    out_csv = "data/raw/afdc_stations_ca.csv"
    stations = fetch_all_stations(api_key=api_key)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"fuel_stations": stations}, f, ensure_ascii=False, indent=2)
    to_flat_csv(stations, out_csv)
    print(f"\nSaved {len(stations)} stations")
    print(f"- JSON: {out_json}")
    print(f"- CSV : {out_csv}")

if __name__ == "__main__":
    main()
