-- Total ports by county (Level 2 + DCFC)
SELECT
  county,
  SUM(ev_level2_evse_num) AS level2_ports,
  SUM(ev_dc_fast_num)     AS dcfc_ports,
  SUM(ev_level2_evse_num + ev_dc_fast_num) AS ports_total,
  CASE
    WHEN SUM(ev_level2_evse_num + ev_dc_fast_num) = 0 THEN 0
    ELSE CAST(SUM(ev_dc_fast_num) AS FLOAT) / SUM(ev_level2_evse_num + ev_dc_fast_num)
  END AS dcfc_share
FROM stations_ca   -- (Assume you’ve imported data/processed/stations_ca.csv into a table)
GROUP BY county
ORDER BY ports_total DESC;

-- Top 10 by DCFC share (filtering out tiny counties with 0 total)
WITH summary AS (
  SELECT
    county,
    SUM(ev_level2_evse_num) AS level2_ports,
    SUM(ev_dc_fast_num)     AS dcfc_ports,
    SUM(ev_level2_evse_num + ev_dc_fast_num) AS ports_total
  FROM stations_ca
  GROUP BY county
)
SELECT
  county,
  level2_ports,
  dcfc_ports,
  ports_total,
  CAST(dcfc_ports AS FLOAT) / NULLIF(ports_total, 0) AS dcfc_share
FROM summary
WHERE ports_total > 0
ORDER BY dcfc_share DESC
LIMIT 10;
