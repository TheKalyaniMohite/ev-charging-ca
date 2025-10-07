# EV Charging: Utilization & Reliability in California

**One-sentence overview:**
This is a comprehensive analysis of where EV chargers exist in California relative to demand—pinpointing coverage gaps, high-demand counties, and priority sites for adding DC fast charging (DCFC).

**What you get**

* Reproducible **data pipeline** (AFDC stations → clean stations/ports → county rollups)
* Clear **KPIs**: Total Ports, DCFC Ports, **DCFC Share**, and **Coverage = ports per 1,000 EVs**
* **Siting Score** (where to add DCFC next) and **Likely Busy** (ops watchlist)
* **Tableau dashboards** published to Tableau Public
* A polished **Next.js web app** (Vercel-ready) that embeds the dashboards with context

---

## Contents

* [Quick Start (Windows/PowerShell)](#quick-start-windowspowershell)
* [Project Structure](#project-structure)
* [Data Sources](#data-sources)
* [Environment Setup](#environment-setup)
* [Data Pipeline: Run End-to-End](#data-pipeline-run-end-to-end)
* [Generated Outputs](#generated-outputs)
* [KPIs & Scoring](#kpis--scoring)
* [Dashboards (Tableau) — Build & Publish](#dashboards-tableau--build--publish)
* [Web App (Next.js on Vercel)](#web-app-nextjs-on-vercel)
* [Refresh Workflow](#refresh-workflow)
* [Data Dictionary (selected)](#data-dictionary-selected)
* [Assumptions & Limits](#assumptions--limits)
* [Troubleshooting (Windows)](#troubleshooting-windows)
* [License](#license)
* [Changelog](#changelog)

---

## Quick Start (Windows/PowerShell)

```powershell
# 1) Clone and enter
git clone <your-repo-url> ev-charging-ca
cd ev-charging-ca

# 2) Create & activate venv
py -3 -m venv .venv
. .\.venv\Scripts\Activate.ps1

# 3) Install deps
pip install -r requirements.txt
# (or minimal) pip install python-dotenv pandas requests pyproj openpyxl

# 4) (If needed) set AFDC API key
#    Create .env with: AFDC_API_KEY=your_key_here

# 5) Run pipeline
python src\extract\afdc_fetch.py
python src\transform\make_kpis.py
python src\transform\opportunity_insights.py
python src\transform\make_county_supply.py
python src\transform\make_station_busy.py

# 6) Open Tableau → connect to data/processed/*.csv → open/refresh dashboards
```

---

## Project Structure

```
ev-charging-ca/
├─ data/
│  ├─ raw/                       # raw AFDC pulls / inputs
│  └─ processed/                 # clean outputs for BI
│     ├─ stations_ca.csv
│     ├─ ports_ca.csv
│     ├─ ev_summary_by_county.csv
│     ├─ ev_summary_by_region.csv
│     ├─ ev_county_supply_vs_demand.csv
│     ├─ siting_score_top10_counties.csv
│     ├─ station_busy_candidates.csv
│     ├─ station_busy_top25.csv
│     └─ insights/
│        ├─ top10_ports_total.csv
│        ├─ top10_dcfc_share.csv
│        ├─ opportunity_regions_zero_dcfc_sorted_by_level2.csv
│        ├─ opportunity_regions_low_dcfc_share_high_ports.csv
│        └─ opportunity_stations_level2_no_dcfc_8plus.csv
├─ src/
│  ├─ extract/
│  │  └─ afdc_fetch.py
│  └─ transform/
│     ├─ make_kpis.py
│     ├─ opportunity_insights.py
│     ├─ make_county_supply.py
│     └─ make_station_busy.py
├─ dashboards/                   # .twbx and exported PNGs (small)
├─ docs/                         # screenshots, one-pagers
├─ sql/
├─ .env
├─ .gitignore
├─ requirements.txt
└─ README.md
```

---

## Data Sources

* **AFDC (Alternative Fuels Data Center)** — Public EV charging station inventory (filtered to **California**, **status: open**).
* **California EV population (DMV/CEC)** — County-level EV registrations; used to compute **coverage** (ports per 1,000 EVs).
* **HUD USPS ZIP↔County Crosswalk** — Used to derive county when AFDC lacks county values (ZIP → county roll-up).

*Note:* AFDC inventory changes frequently; EV counts update on their publisher cadence (annual/quarterly). Crosswalks are quarterly.

---

## Environment Setup

```powershell
py -3 -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**`.env`**

```
AFDC_API_KEY=your_key_here
```

---

## Data Pipeline: Run End-to-End

### 1) Extract — `src/extract/afdc_fetch.py`

* Pulls AFDC Alternative Fueling Stations for **California**, **status = E (existing/open)**.
* Saves raw JSON/CSV to `data/raw/afdc_<timestamp>.*`.

```powershell
python src\extract\afdc_fetch.py
```

### 2) Transform & KPIs — `src/transform/make_kpis.py`

* Cleans to a **stations** table (normalize types/fields; handles missing county with city fallback for “region”).
* Builds **ports** table and **county/region summaries** (ports_total, dcfc_ports, dcfc_share).

```powershell
python src\transform\make_kpis.py
```

### 3) Opportunity/Proxy Lists — `src/transform/opportunity_insights.py`

* Generates fast triage lists (e.g., **0 DCFC** cities with lots of L2; **low %DCFC + high ports**).

```powershell
python src\transform\opportunity_insights.py
```

### 4) County Supply vs Demand + Siting — `src/transform/make_county_supply.py`

* Joins **county EV counts**; computes **Coverage = ports per 1,000 EVs**; ranks **Siting Score** (where to add DCFC).

```powershell
python src\transform\make_county_supply.py
```

### 5) Likely Busy (station) — `src/transform/make_station_busy.py`

* Aggregates to **one row per station**; computes Likely Busy score; saves **candidates** + **Top 25**.

```powershell
python src\transform\make_station_busy.py
```

---

## Generated Outputs

* `stations_ca.csv` — Cleaned station-level records (CA, open)
* `ports_ca.csv` — L2/DCFC/Total port counts per station
* `ev_summary_by_county.csv`, `ev_summary_by_region.csv` — Summaries
* `ev_county_supply_vs_demand.csv` — Adds EV counts & **coverage**
* `siting_score_top10_counties.csv` — Ranked siting targets (counties)
* `station_busy_candidates.csv`, `station_busy_top25.csv` — Ops watchlist (station)
* `insights/*.csv` — Proxy shortlists for the Opportunities dashboard

---

## KPIs & Scoring

**KPIs**

* **Total Ports** = Level 2 + DCFC public ports
* **DCFC Ports** = count of DC fast ports
* **DCFC Share (%)** = `DCFC Ports / Total Ports`
* **Coverage** = `Total Ports / EV Count * 1,000`  *(ports per 1,000 EVs)*

**Siting Score (county)** *(transparent)*

* Purpose: **Where should new DCFC go next?**
* Inputs (min-max normalized):

  * **Low coverage** (inverse of ports per 1,000 EVs) — higher weight
  * **EV count** — medium weight
* Higher score ⇒ **bigger coverage gap + bigger EV base** ⇒ better DCFC impact.

**Likely Busy (station)** *(proxy)*

* Purpose: **Which stations may queue / need ops attention?**
* Inputs: **DCFC ports** (high weight) + **Total ports** (small weight)
* Higher score ⇒ stronger candidate for **reliability / capacity add**.

> Weights live in code so they’re explainable and tunable (no black box).

---

## Dashboards (Tableau) — Build & Publish

**Dashboards**

1. **Overview** — KPIs (Total Ports, DCFC Share), CA-only map, Top-10 bars
2. **County – Supply vs Demand (2024)** — Coverage (ports/1k EVs), EV counts, choropleth & bars
3. **Planning – Siting & Busy** — Siting Score (Top-N) + Likely Busy stations (Top-N)
4. **Opportunities & Busy (Proxies)** — 0 DCFC cities/sites, low %DCFC + high ports, likely busy

**Tips**

* Create a **Top-N** integer parameter (e.g., 10/25/50) and apply to siting + busy lists.
* **Map (CA only)**: Use Latitude/Longitude **range filters**; disable pan/zoom; **Fix** the view.
* **Tooltips**: Region, Total, L2, DCFC, **%DCFC**.

**Publish to Tableau Public**

* File → **Save to Tableau Public As…**
* **Show sheets as tabs**: ON
* Hide raw worksheets; publish the dashboards.

**Export for repo**

* Save **.twbx** to `dashboards/`
* Export PNGs to `dashboards/`

---

## Web App (Next.js on Vercel)

* Separate repo/folder: embeds your Tableau Public workbook with context (Overview, Data Sources, Methodology, Findings).
* Dev:

  ```powershell
  npm install
  npm run dev
  # http://localhost:3000
  ```
* Deploy: connect repo to **Vercel** and **Deploy** (no server env needed).

---

## Refresh Workflow

When AFDC/EV counts update:

```powershell
. .\.venv\Scripts\Activate.ps1
git pull

python src\extract\afdc_fetch.py
python src\transform\make_kpis.py
python src\transform\opportunity_insights.py
python src\transform\make_county_supply.py
python src\transform\make_station_busy.py

# Update Tableau data sources → Refresh → republish
# Update “Last refreshed” in web app tiles (if applicable)

git add -A
git commit -m "data: refresh AFDC/EV counts <YYYY-MM-DD>"
git push
```

---

## Data Dictionary (selected)

| Column                                      | Where                          | Meaning                            |
| ------------------------------------------- | ------------------------------ | ---------------------------------- |
| `station_name`                              | stations_ca.csv                | Station/site label (AFDC)          |
| `city`, `county`, `zip`                     | stations_ca.csv                | Location metadata                  |
| `level2_ports`, `dcfc_ports`, `ports_total` | ports_ca.csv                   | Port counts by type and total      |
| `ev_count`                                  | ev_county_supply_vs_demand.csv | Registered EVs (county)            |
| `ports_per_1000_evs`                        | ev_county_supply_vs_demand.csv | **Coverage** KPI                   |
| `dcfc_share`                                | *various summaries*            | `dcfc_ports / ports_total`         |
| `siting_score`                              | ev_county_supply_vs_demand.csv | Ranked DCFC siting priority        |
| `likely_busy_score`                         | station_busy_*                 | Proxy for high throughput / queues |

---

## Assumptions & Limits

* **Snapshot**: AFDC inventory and EV counts evolve; treat outputs as time-bound.
* **Proxies, not telemetry**: “Likely busy” & “Siting” are explainable heuristics; validate with **traffic (AADT)**, grid capacity, and session/uptime before committing capital.
* **County roll-ups**: Crosswalk used where county is missing; minor boundary mismatch is possible.

---

## Troubleshooting (Windows)

* **Permission denied when writing CSV**
  Close the file in Excel/Tableau and rerun the script.

* **Tableau map shows “Unknown”**
  Map → **Edit Locations** → Country: **United States**.
  Restrict to CA via filters or fixed view (lat 32–42, lon −125 to −114).

* **Git tracked venv/raw**
  Ensure `.gitignore` has:

  ```
  .venv/
  __pycache__/
  .ipynb_checkpoints/
  data/raw/
  ```

  Then:

  ```powershell
  git rm -r --cached .venv data\raw
  git add .gitignore
  git commit -m "chore: ignore venv/raw"
  ```

---

## License

**Code:** MIT License — permissive reuse with attribution; no warranty.
**Data:** Subject to original source terms (AFDC, DMV/CEC, HUD).
See `LICENSE` for details.

---

## Changelog

* **Step 1** — Project scaffolding, venv, `.gitignore`, initial README
* **Step 2** — AFDC fetch; cleaning; `stations_ca.csv`, `ports_ca.csv`, summaries
* **Step 2.6** — **Overview** dashboard (KPIs, CA map, Top-10 bars)
* **Step 2.7** — **Opportunities & Busy (Proxies)** lists + dashboard
* **Step 3** — County EV counts join; **Coverage**; **Siting Score**; **Planning** dashboard
* **Step 4** — **Likely Busy** station aggregation & Top-25
* **Current** — Web app (Next.js), Tableau Public publish, README polish
