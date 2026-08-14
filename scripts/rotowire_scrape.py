"""Scrape FPL rankings from Rotowire's top-400 article into data/rotowire.csv."""
import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://www.rotowire.com/soccer/article/fantasy-premier-league-fpl-rankings-top-400-for-2026-27-season-124261"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "rotowire.csv"

POS_MAP = {"G": "GK", "D": "DEF", "M": "MID", "F": "FWD"}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def scrape() -> pd.DataFrame:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    table = soup.find("table", class_="ck-table-resized")
    if table is None:
        raise RuntimeError("Could not find rankings table on Rotowire page")

    rows = []
    for tr in table.find_all("tr")[1:]:  # skip header
        cells = tr.find_all("td")
        if len(cells) < 12:
            continue
        overall_rank = cells[0].get_text(strip=True)
        player = cells[5].get_text(strip=True)
        team = cells[6].get_text(strip=True)
        pos = cells[7].get_text(strip=True)
        price = cells[8].get_text(strip=True)
        tsb_pct = cells[9].get_text(strip=True)
        pts = cells[10].get_text(strip=True)
        pp90 = cells[11].get_text(strip=True)

        if not overall_rank.isdigit():
            continue

        rows.append(
            {
                "rank": int(overall_rank),
                "player": player,
                "team": team,
                "position": POS_MAP.get(pos, pos),
                "price": float(price) if price else None,
                "tsb_pct": float(tsb_pct) if tsb_pct else None,
                "pts": float(pts) if pts else None,
                "pp90": float(pp90) if pp90 else None,
            }
        )

    df = pd.DataFrame(rows).sort_values("rank").reset_index(drop=True)
    return df


def main() -> None:
    df = scrape()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df)} players to {OUT_PATH}")


if __name__ == "__main__":
    main()
