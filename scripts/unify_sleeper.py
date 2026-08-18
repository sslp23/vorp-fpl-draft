"""Turn data/sleeper.csv into data/unified_sleeper.csv.

Currently just one source (Rotowire's Fantrax & Sleeper rankings), so there's
no cross-source matching to do -- this just reshapes it into the same column
layout unified.csv uses (unified_rank, sources_count, etc.) so vorp_engine.py
and app.py work against either ranking model unmodified. Structured this way
so a second Sleeper-format source could be folded in later the same way
unify.py combines OFPL sources.
"""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
IN_PATH = DATA_DIR / "sleeper.csv"
OUT_PATH = DATA_DIR / "unified_sleeper.csv"


def run() -> pd.DataFrame:
    if not IN_PATH.exists():
        raise FileNotFoundError(f"Missing {IN_PATH}. Run scripts/sleeper_scrape.py first.")

    df = pd.read_csv(IN_PATH).sort_values("rank").reset_index(drop=True)
    max_rank = df["rank"].max()

    unified = pd.DataFrame(
        {
            "unified_rank": df["rank"],
            "player": df["player"],
            "team": df["team"].astype(str).str.upper().str.strip(),
            "position": df["position"],
            "sleeper_rank": df["rank"],
            "sources_count": 1,
            "unified_score": df["rank"] / max_rank,
            "sleeper_pts": df["pts"],
            "sleeper_floor": df["floor"],
            "sleeper_pp90": df["pp90"],
        }
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    unified.to_csv(OUT_PATH, index=False)
    print(f"Unified (sleeper): {len(unified)} players -> {OUT_PATH}")
    return unified


if __name__ == "__main__":
    run()
