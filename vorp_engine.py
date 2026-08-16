"""Valuation and VORP calculation on top of data/unified.csv.

Value is derived purely from the unified ranking -- unified_score, the
average percentile across sources computed in unify.py -- rather than any
single source's points. Waiver Kings' "pts" is last season's actual output
(not a projection) and The Draft Society doesn't publish points at all, so
points aren't a reliable, consistent value basis across sources; rank is.

Kept separate from app.py so the math can be tested/reused without Streamlit.
"""
import pandas as pd

POSITIONS = ["GK", "DEF", "MID", "FWD"]


def rank_value(df: pd.DataFrame) -> pd.Series:
    """Turn unified_score (avg percentile across sources, 0=best) into a
    0-100 scale where higher is better, so it behaves like a "value" a VORP
    calculation can subtract."""
    if "unified_score" not in df:
        raise KeyError("unified_score column missing from unified.csv")
    return ((1 - df["unified_score"]) * 100).rename("value")


def replacement_levels(df: pd.DataFrame, num_teams: int, starters: dict) -> dict:
    """Value of the Nth-best player at each position (N = num_teams * starters
    at that position) -- the baseline for VORP: the last player you'd expect
    to still be a league-wide starter at that position.
    """
    levels = {}
    for pos in POSITIONS:
        pool = df.loc[df["position"] == pos, "value"].sort_values(ascending=False).reset_index(drop=True)
        n = num_teams * starters.get(pos, 0)
        if len(pool) == 0:
            levels[pos] = 0.0
        else:
            idx = min(max(n - 1, 0), len(pool) - 1)
            levels[pos] = float(pool.iloc[idx])
    return levels


def compute_vorp(df: pd.DataFrame, num_teams: int, starters: dict) -> pd.DataFrame:
    df = df.copy()
    df["value"] = rank_value(df)
    levels = replacement_levels(df, num_teams, starters)
    df["replacement_value"] = df["position"].map(levels)
    df["vorp"] = df["value"] - df["replacement_value"]
    return df
