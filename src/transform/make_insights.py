import pathlib
import pandas as pd

PROCESSED_DIR = pathlib.Path("data/processed")
INSIGHTS_DIR = PROCESSED_DIR / "insights"
COUNTY_SUMMARY = PROCESSED_DIR / "ev_summary_by_county.csv"

def main():
    INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(COUNTY_SUMMARY)

    # Top/Bottom by total ports
    top_ports = df.sort_values("ports_total", ascending=False).head(10)
    bot_ports = df.sort_values("ports_total", ascending=True).head(10)

    # Top/Bottom by DCFC share (filter counties with at least some ports to avoid divide-by-zero noise)
    df_nonzero = df[df["ports_total"] > 0].copy()
    top_dcfc_share = df_nonzero.sort_values("dcfc_share", ascending=False).head(10)
    bot_dcfc_share = df_nonzero.sort_values("dcfc_share", ascending=True).head(10)

    top_ports.to_csv(INSIGHTS_DIR / "top10_ports_total.csv", index=False)
    bot_ports.to_csv(INSIGHTS_DIR / "bottom10_ports_total.csv", index=False)
    top_dcfc_share.to_csv(INSIGHTS_DIR / "top10_dcfc_share.csv", index=False)
    bot_dcfc_share.to_csv(INSIGHTS_DIR / "bottom10_dcfc_share.csv", index=False)

    print("Saved insight tables:")
    print(f"- {INSIGHTS_DIR/'top10_ports_total.csv'}")
    print(f"- {INSIGHTS_DIR/'bottom10_ports_total.csv'}")
    print(f"- {INSIGHTS_DIR/'top10_dcfc_share.csv'}")
    print(f"- {INSIGHTS_DIR/'bottom10_dcfc_share.csv'}")

if __name__ == "__main__":
    main()
