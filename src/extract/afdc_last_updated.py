import os
import json
import pathlib
import requests

LAST_UPDATED_ENDPOINT = "https://developer.nrel.gov/api/alt-fuel-stations/v1/last-updated.json"

def main():
    api_key = os.getenv("NREL_API_KEY")
    if not api_key:
        raise SystemExit('ERROR: NREL_API_KEY not set. In PowerShell: $env:NREL_API_KEY = "YOUR_KEY"')

    pathlib.Path("data/raw").mkdir(parents=True, exist_ok=True)
    r = requests.get(LAST_UPDATED_ENDPOINT, params={"api_key": api_key}, timeout=30)
    r.raise_for_status()
    payload = r.json()

    out_path = "data/raw/afdc_last_updated.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    ts = payload.get("last_updated")
    print(f"AFDC last_updated: {ts}")
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    main()
