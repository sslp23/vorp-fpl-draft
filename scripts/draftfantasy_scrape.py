"""Scrape FPL rankings from DraftFantasy's draft cheat sheet into data/draftfantasy.csv."""
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://www.draftfantasy.com/fpl/draft-cheat-sheet"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "draftfantasy.csv"

POS_MAP = {"GKP": "GK", "GK": "GK", "DEF": "DEF", "MID": "MID", "FWD": "FWD"}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _parse_player_cell(cell) -> tuple[str, str, str, str]:
    """Player cell holds a name span plus a muted "TEAM · POS POSRANK" line.

    The site renders these as separate text fragments split by empty React
    hydration comments (`<!-- -->`), so pulling text node-by-node with a
    separator (e.g. "\n") splits "MCI · FWD" into "MCI", "·", "FWD" and loses
    the spacing. Reading each element's full text with the default (empty)
    separator reconstructs it correctly since comments are excluded.
    """
    name_span = cell.select_one("span.font-bold")
    player = name_span.get_text().strip()

    meta_div = cell.find(attrs={"class": "mt-0.5"})
    meta_text = meta_div.get_text().strip()
    team, pos_rank_part = meta_text.split(" · ", 1)
    pos, pos_rank = pos_rank_part.rsplit(" ", 1)
    return player.strip(), team.strip(), pos.strip(), pos_rank.strip()


def scrape() -> pd.DataFrame:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    table = soup.find("table")
    if table is None:
        raise RuntimeError("Could not find rankings table on DraftFantasy page")

    rows = []
    for tr in table.find_all("tr")[1:]:  # skip header
        cells = tr.find_all("td")
        if len(cells) < 7:
            continue
        overall_rank = cells[0].get_text(strip=True)
        if not overall_rank.isdigit():
            continue
        round_ = cells[1].get_text(strip=True)
        player, team, pos, pos_rank = _parse_player_cell(cells[2])
        tier = cells[3].get_text(strip=True)
        xp = cells[4].get_text(strip=True)
        edge = cells[5].get_text(strip=True)

        rows.append(
            {
                "rank": int(overall_rank),
                "player": player,
                "team": team,
                "position": POS_MAP.get(pos, pos),
                "pos_rank": int(pos_rank) if pos_rank.isdigit() else None,
                "round": int(round_) if round_.isdigit() else None,
                "tier": int(tier) if tier.isdigit() else None,
                "xp": float(xp) if xp else None,
                "edge": float(edge.replace("+", "")) if edge else None,
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
