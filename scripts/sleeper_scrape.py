"""Scrape Sleeper-format FPL rankings from Rotowire into data/sleeper.csv.

Rotowire publishes a separate "Fantrax & Sleeper" rankings article from
their standard FPL one -- different scoring (Pts/Floor here vs Price/TSB%
on the classic FPL page) since Sleeper/Fantrax leagues don't score like
official FPL Draft.
"""
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://www.rotowire.com/soccer/article/fantrax-sleeper-premier-league-rankings-top-400-for-the-202627-season-123920"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "sleeper.csv"

POS_MAP = {"G": "GK", "D": "DEF", "M": "MID", "F": "FWD"}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def scrape() -> pd.DataFrame:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    table = soup.find("table", class_="ck-table-resized")
    if table is None:
        raise RuntimeError("Could not find rankings table on Rotowire Sleeper page")

    rows = []
    for tr in table.find_all("tr")[1:]:  # skip header
        cells = tr.find_all("td")
        if len(cells) < 10:
            continue

        overall_rank = cells[0].get_text(strip=True)
        if not overall_rank.isdigit():
            continue

        pos_rank = cells[1].get_text(strip=True)
        player = cells[4].get_text(strip=True)
        team = cells[5].get_text(strip=True)
        pos = cells[6].get_text(strip=True)
        pts = cells[7].get_text(strip=True)
        floor = cells[8].get_text(strip=True)
        pp90 = cells[9].get_text(strip=True)

        rows.append(
            {
                "rank": int(overall_rank),
                "player": player,
                "team": team,
                "position": POS_MAP.get(pos, pos),
                "pos_rank": int(pos_rank) if pos_rank.isdigit() else None,
                "pts": float(pts) if pts else None,
                "floor": float(floor) if floor else None,
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
