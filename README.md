# vor_fpl_draft

Pulls FPL (Fantasy Premier League) draft rankings from multiple public sources,
merges them into one unified ranking, and (next step) uses that to power a
live VORP draft-board dashboard.

## Sources

| Source | How it's fetched | Pool size |
|---|---|---|
| [Waiver Kings](https://waiver-kings.com/board) | Manual: page is client-rendered (Vue), so its table HTML is copy-pasted into `data/raw/waiverkings_board.html` and parsed from there | ~160 |
| [DraftFantasy](https://www.draftfantasy.com/fpl/draft-cheat-sheet) | Scraped directly (static HTML table) | 240 |
| [The Draft Society](https://www.thedraftsociety.com/fpl-draft-rankings) | Fetched via the linked public Google Sheet export | 200 |

Rotowire was originally included but has been dropped from the pipeline
(`scripts/rotowire_scrape.py` is still on disk if it's ever needed again).

## Project layout

```
data/
  raw/waiverkings_board.html   manually saved HTML snapshot (see below)
  waiverkings.csv               per-source ranking, normalized columns
  draftfantasy.csv
  thedraftsociety.csv
  unified.csv                   merged ranking across all sources
scripts/
  waiverkings_scrape.py         parses data/raw/waiverkings_board.html
  draftfantasy_scrape.py        scrapes DraftFantasy live
  thedraftsociety_scrape.py     fetches the Google Sheet export live
  unify.py                      matches players across sources and merges rankings
pipeline.py                     runs every scraper, then unify.py
```

## Running it

Requires `pandas`, `requests`, `beautifulsoup4`, `streamlit` (see
`requirements.txt`).

Before running, refresh the Waiver Kings snapshot since it can't be fetched
automatically:

1. Open https://waiver-kings.com/board, right-click the table -> Inspect
2. Right-click the `<table>` element -> Copy -> Copy outerHTML
3. Paste it into `data/raw/waiverkings_board.html`, replacing the old contents

Then:

```
python pipeline.py
```

This regenerates every per-source CSV in `data/` and merges them into
`data/unified.csv`.

## How unification works

Sources rank different pool sizes, so `unify.py` merges on **rank**, not
points (not every source publishes projected points):

1. Players are matched across sources through progressively looser passes:
   exact (normalized name, team) -> exact (surname, team) -> fuzzy name
   match (same team) -> fuzzy name match (any team, for transfers/typos).
2. Each source's rank is converted to a percentile (`rank / pool size`)
   before averaging, so a player missing from a smaller list isn't unfairly
   penalized relative to one missing from a larger list.
3. The average percentile determines `unified_rank`. `sources_count` is kept
   per player as a confidence signal (e.g. ranked by all three sources vs.
   just one).
