"""Parse FPL rankings from a saved Waiver Kings board snapshot into data/waiverkings.csv.

The /board page renders its table client-side (Vue) from data that doesn't
match the site's own /board.json feed (that feed lags behind what's shown on
the live page), so there's no clean URL to fetch. Instead, save the rendered
table's HTML to data/raw/waiverkings_board.html (e.g. right-click the table
on https://waiver-kings.com/board -> Inspect -> copy the outerHTML of the
<table> element, or the whole page) and this script parses that snapshot.
"""
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "waiverkings_board.html"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "waiverkings.csv"

POS_MAP = {"GKP": "GK", "GK": "GK", "DEF": "DEF", "MID": "MID", "FWD": "FWD"}


def _cell_value(text: str):
    text = text.strip()
    if text in ("", "-"):
        return None
    return text


def scrape() -> pd.DataFrame:
    if not RAW_PATH.exists():
        raise FileNotFoundError(
            f"Missing {RAW_PATH}. Save the rendered board table's HTML there first "
            "(the /board page is client-rendered, so it can't be fetched directly)."
        )

    html = RAW_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    if table is None:
        raise RuntimeError(f"Could not find a <table> in {RAW_PATH}")

    rows = []
    for tr in table.select("tbody tr"):
        cells = tr.find_all("td")
        if len(cells) < 8:
            continue

        rank = _cell_value(cells[0].get_text())
        if rank is None or not rank.isdigit():
            continue

        player = cells[1].get_text(strip=True)
        team = cells[2].get_text(strip=True)

        pos_badge = cells[3].select_one("[data-pos]")
        pos = pos_badge["data-pos"] if pos_badge else cells[3].get_text(strip=True)

        pts = _cell_value(cells[4].get_text())
        minpct = _cell_value(cells[5].get_text().replace("%", ""))
        goals = _cell_value(cells[6].get_text())
        assists = _cell_value(cells[7].get_text())

        rows.append(
            {
                "rank": int(rank),
                "player": player,
                "team": team,
                "position": POS_MAP.get(pos, pos),
                "pts": float(pts) if pts is not None else None,
                "minpct": float(minpct) if minpct is not None else None,
                "goals": float(goals) if goals is not None else None,
                "assists": float(assists) if assists is not None else None,
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
