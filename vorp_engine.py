"""Valuation and VORP calculation on top of data/unified.csv.

Value is derived purely from the unified ranking -- unified_rank, computed
in unify.py by combining sources -- rather than any single source's points.
Waiver Kings' "pts" is last season's actual output (not a projection) and
The Draft Society doesn't publish points at all, so points aren't a
reliable, consistent value basis across sources; rank is.

Kept separate from app.py so the math can be tested/reused without Streamlit.
"""
import numpy as np
import pandas as pd

POSITIONS = ["GK", "DEF", "MID", "FWD"]

# Rank e-folding scale for rank_value's decay curve: bigger = flatter (ranks
# matter less relative to each other), smaller = steeper (top picks worth
# much more than everyone else).
DEFAULT_DECAY = 45.0


def rank_value(df: pd.DataFrame, decay: float = DEFAULT_DECAY) -> pd.Series:
    """Turn unified_rank into a 0-100 value via exponential decay rather than
    a linear percentile.

    A linear rank-to-value mapping badly understates how much better elite
    players are than merely-very-good ones -- e.g. the #1 overall player
    and the #12 overall player end up just a few points apart on a 0-100
    scale, a gap easily swamped by differences in positional replacement
    level. Real fantasy value isn't linear in rank: the gap between #1 and
    #12 is normally much bigger than the gap between #50 and #61.
    Exponential decay keeps the top of the board sharply differentiated
    while flattening out near replacement level, which matches that shape.
    """
    if "unified_rank" not in df:
        raise KeyError("unified_rank column missing from unified.csv")
    return (100 * np.exp(-(df["unified_rank"] - 1) / decay)).rename("value")


def replacement_levels(df: pd.DataFrame, num_teams: int, roster_spots: dict) -> dict:
    """Value of the Nth-best player at each position (N = num_teams *
    roster_spots at that position) -- the baseline for VORP: the value of the
    last player who'll actually get drafted onto a squad at that position,
    across the whole league.

    roster_spots is squad composition (e.g. classic FPL: 2 GK / 5 DEF / 5 MID
    / 3 FWD), not weekly starting-lineup counts -- draft leagues roster the
    full squad, not just a starting XI.
    """
    levels = {}
    for pos in POSITIONS:
        pool = df.loc[df["position"] == pos, "value"].sort_values(ascending=False).reset_index(drop=True)
        n = num_teams * roster_spots.get(pos, 0)
        if len(pool) == 0:
            levels[pos] = 0.0
        else:
            idx = min(max(n - 1, 0), len(pool) - 1)
            levels[pos] = float(pool.iloc[idx])
    return levels


def compute_vorp(df: pd.DataFrame, num_teams: int, roster_spots: dict, decay: float = DEFAULT_DECAY) -> pd.DataFrame:
    df = df.copy()
    df["value"] = rank_value(df, decay)
    levels = replacement_levels(df, num_teams, roster_spots)
    df["replacement_value"] = df["position"].map(levels)
    df["vorp"] = df["value"] - df["replacement_value"]
    return df
