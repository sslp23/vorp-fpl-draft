"""Pull FPL rankings from The Draft Society into data/thedraftsociety.csv.

The rankings table on the page itself is client-rendered (Wix/React), but the
site links out to the underlying Google Sheet, which we export as CSV directly.
"""
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

SHEET_ID = "1xeZKNo9Z9WdcW1PlJiePTnGKM5ZCTxIRSCDUsHNnPDI"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "thedraftsociety.csv"

POS_MAP = {"GKP": "GK", "GK": "GK", "DEF": "DEF", "MID": "MID", "FWD": "FWD"}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def scrape() -> pd.DataFrame:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    raw = pd.read_csv(StringIO(resp.text))

    df = pd.DataFrame(
        {
            "rank": raw["Rank"].astype(int),
            "player": raw["Player"],
            "team": raw["Team"],
            "position": raw["Position"].map(lambda p: POS_MAP.get(p, p)),
            "pos_rank": raw["Pos Rank"],
            "price": raw["FPL Price"],
            "ros_pct": raw["FPL Ros %"],
        }
    ).sort_values("rank").reset_index(drop=True)
    return df


def main() -> None:
    df = scrape()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df)} players to {OUT_PATH}")


if __name__ == "__main__":
    main()
