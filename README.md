# EV Charging in California — Utilization, Reliability (Proxy), and Siting Score

**Goal:** Give planners/ops a clear view of charger coverage (Level 2 vs DC Fast), pressure vs EV adoption, and a transparent **SitingScore** to prioritize where to add more stations.

## Key Questions
1) Where are chargers today (by county/network/connector), and what’s the DC Fast mix?
2) Which regions look **underserved** given EV counts and traffic?
3) Where should California **add more** chargers first (transparent, reproducible scoring)?

## Deliverables
- Clean tables in `data/processed/`:
  - `stations_ca.csv` (one row per site)
  - `ports_ca.csv` (one row per port)
  - `county_ev_counts.csv`
  - `aadt_points.csv` (optional at v1)
  - `ev_summary.csv` (KPIs) and `siting_scores.csv`
- **Dashboard**: `dashboards/EV_CA_Reliability_Utilization.twbx`
- **SQL**: `sql/kpis.sql` (joins, window functions for interview-readiness)
- **Docs**: `docs/one-pager.md` (insights, actions, limitations)

## Data Sources (public)
- AFDC (NREL) Alternative Fuel Stations — CA subset
- CEC/DMV Zero-Emission Vehicle counts by county
- Caltrans AADT (traffic), optional in v1

## KPIs
- Ports total; **DCFC ports**; **DCFC share**
- **Ports per 100k residents** (coverage)
- **Ports per 1,000 EVs** (supply pressure)
- 24/7 access share; network & connector mix

## Reliability (Proxy) Note
We **do not** claim “true uptime %” (requires time-series telemetry). We label availability as **proxy**; v2 would compute true uptime from per-port status logs.

## SitingScore (v1, transparent)
We compute 4 normalized components and combine:
- `EV_pressure` (more EVs → higher)
- `Traffic_pressure` (more traffic → higher)
- `Low_ports_per_1000_EVs` (scarcity vs EVs)
- `Low_ports_per_100k` (scarcity vs population)

Default weights:
SitingScore = 0.35EV_pressure
+ 0.25Traffic_pressure
+ 0.25Low_ports_per_1000_EVs
+ 0.15Low_ports_per_100k


## How to Run
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
# Then open notebooks/01_extract_clean.ipynb and run cells step by step


---

## Changelog
- Step 1 (Project setup): Created folder structure; set up virtual environment; added requirements.txt; created placeholders (extract/transform/utils/notebook); added README with KPIs/SitingScore and running instructions; created docs/one-pager and sql/kpis.sql.

**Do this:**
```bash
@(
  'src\extract\afdc_fetch.py',
  'src\transform\make_kpis.py',
  'src\utils.py',
  'notebooks\01_extract_clean.ipynb',
  'docs\one-pager.md',
  'sql\kpis.sql'
) | ForEach-Object { New-Item $_ -ItemType File -Force }

