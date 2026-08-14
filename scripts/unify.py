"""Merge per-source ranking CSVs in data/ into a single data/unified.csv.

Matching strategy (progressively looser passes, run across all sources at
once via union-find so transitive matches connect correctly):
  1. exact match on (normalized name, team)
  2. exact match on (surname, team)
  3. fuzzy name match (same team)
  4. fuzzy name match (any team, higher threshold -- covers transfers/typos)

Ranking strategy: sources rank different pool sizes (400/240/199), so a
raw rank average would unfairly punish players missing from the smaller
lists. Instead each source's rank is converted to a percentile (rank / pool
size) before averaging, and the average percentile determines unified_rank.
Players found in fewer sources are not penalized beyond what their available
percentiles say -- `sources_count` is carried through as a confidence signal.
"""
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SOURCES = ["waiverkings", "draftfantasy", "thedraftsociety"]
OUT_PATH = DATA_DIR / "unified.csv"

FUZZY_SAME_TEAM_THRESHOLD = 0.82
FUZZY_ANY_TEAM_THRESHOLD = 0.90

EXTRA_COLS = ("pts", "price", "xp", "edge", "tsb_pct", "pp90", "ros_pct")

# Letters that aren't accent+base composites, so NFKD decomposition below
# leaves them untouched (e.g. "ß" has no canonical "ss" decomposition).
EXTRA_TRANSLITERATIONS = {
    "ß": "ss",
    "æ": "ae",
    "œ": "oe",
    "ø": "o",
    "đ": "d",
    "ł": "l",
    "þ": "th",
    "ð": "d",
}


def normalize_name(name: str) -> str:
    name = str(name).lower()
    for char, repl in EXTRA_TRANSLITERATIONS.items():
        name = name.replace(char, repl)
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r"[.'’]", "", name)
    name = re.sub(r"[^a-z0-9\s-]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def surname(normalized_name: str) -> str:
    return normalized_name.split(" ")[-1] if normalized_name else ""


def load_sources() -> dict[str, pd.DataFrame]:
    frames = {}
    for src in SOURCES:
        path = DATA_DIR / f"{src}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}. Run scripts/{src}_scrape.py first.")
        df = pd.read_csv(path)
        df["norm_name"] = df["player"].map(normalize_name)
        df["surname"] = df["norm_name"].map(surname)
        df["team"] = df["team"].astype(str).str.upper().str.strip()
        frames[src] = df
    return frames


class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _union_cross_source(records_df: pd.DataFrame, uf: UnionFind, key_fn) -> None:
    """Union records that share a key, but only across different sources."""
    by_key: dict = {}
    for i, rec in records_df.iterrows():
        key = key_fn(rec)
        if key is None or key == "":
            continue
        by_key.setdefault(key, []).append(i)

    for idxs in by_key.values():
        by_source: dict = {}
        for i in idxs:
            by_source.setdefault(records_df.at[i, "source"], []).append(i)
        sources_present = list(by_source.keys())
        for si in range(len(sources_present)):
            for sj in range(si + 1, len(sources_present)):
                for i in by_source[sources_present[si]]:
                    for j in by_source[sources_present[sj]]:
                        uf.union(i, j)


def _fuzzy_pass(records_df: pd.DataFrame, uf: UnionFind, same_team_only: bool, threshold: float) -> None:
    clusters: dict = {}
    for i in range(len(records_df)):
        clusters.setdefault(uf.find(i), []).append(i)
    cluster_ids = list(clusters.keys())

    for a in range(len(cluster_ids)):
        ca = clusters[cluster_ids[a]]
        sources_a = {records_df.at[i, "source"] for i in ca}
        for b in range(a + 1, len(cluster_ids)):
            cb = clusters[cluster_ids[b]]
            sources_b = {records_df.at[i, "source"] for i in cb}
            if sources_a & sources_b:
                continue  # would merge two records from the same source

            best_score = 0.0
            best_same_team = False
            for i in ca:
                for j in cb:
                    if uf.find(i) == uf.find(j):
                        continue
                    same_team = records_df.at[i, "team"] == records_df.at[j, "team"]
                    if same_team_only and not same_team:
                        continue
                    score = SequenceMatcher(
                        None, records_df.at[i, "norm_name"], records_df.at[j, "norm_name"]
                    ).ratio()
                    if score > best_score:
                        best_score = score
                        best_same_team = same_team

            if best_score >= threshold and (same_team_only is False or best_same_team):
                uf.union(ca[0], cb[0])


def match_players(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    records = [
        {"source": src, **row.to_dict()}
        for src, df in frames.items()
        for _, row in df.iterrows()
    ]
    records_df = pd.DataFrame(records).reset_index(drop=True)
    uf = UnionFind(len(records_df))

    _union_cross_source(records_df, uf, lambda r: (r["norm_name"], r["team"]))
    _union_cross_source(records_df, uf, lambda r: (r["surname"], r["team"]))
    _fuzzy_pass(records_df, uf, same_team_only=True, threshold=FUZZY_SAME_TEAM_THRESHOLD)
    _fuzzy_pass(records_df, uf, same_team_only=False, threshold=FUZZY_ANY_TEAM_THRESHOLD)

    records_df["cluster"] = [uf.find(i) for i in range(len(records_df))]
    return records_df


def build_unified(records_df: pd.DataFrame, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    max_rank = {src: frames[src]["rank"].max() for src in SOURCES}

    rows = []
    for _, group in records_df.groupby("cluster"):
        by_source = {rec["source"]: rec for _, rec in group.iterrows()}

        canon = next(by_source[src] for src in SOURCES if src in by_source)
        row = {"player": canon["player"], "team": canon["team"], "position": canon["position"]}

        percentiles = []
        for src in SOURCES:
            if src in by_source:
                r = int(by_source[src]["rank"])
                row[f"{src}_rank"] = r
                percentiles.append(r / max_rank[src])
            else:
                row[f"{src}_rank"] = pd.NA

        row["sources_count"] = len(by_source)
        row["unified_score"] = sum(percentiles) / len(percentiles)

        for src, rec in by_source.items():
            for col in EXTRA_COLS:
                if col in rec and pd.notna(rec[col]):
                    row[f"{src}_{col}"] = rec[col]

        rows.append(row)

    unified = (
        pd.DataFrame(rows)
        .sort_values(["unified_score", "sources_count"], ascending=[True, False])
        .reset_index(drop=True)
    )
    unified.insert(0, "unified_rank", range(1, len(unified) + 1))
    return unified


def main() -> None:
    frames = load_sources()
    for src, df in frames.items():
        print(f"{src}: {len(df)} players")

    records_df = match_players(frames)
    unified = build_unified(records_df, frames)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    unified.to_csv(OUT_PATH, index=False)

    print(f"\nUnified: {len(unified)} unique players -> {OUT_PATH}")
    print(unified["sources_count"].value_counts().sort_index(ascending=False).rename("players per source-count"))


if __name__ == "__main__":
    main()
