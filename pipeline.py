"""Run scrapers for the selected sources, then unify them into data/unified.csv.

Usage:
  python pipeline.py                                   # all sources
  python pipeline.py --sources waiverkings              # just one
  python pipeline.py --sources waiverkings draftfantasy  # a subset
"""
import argparse
import runpy
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

SCRAPER_SCRIPTS = {
    "waiverkings": "waiverkings_scrape.py",
    "draftfantasy": "draftfantasy_scrape.py",
    "thedraftsociety": "thedraftsociety_scrape.py",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FPL ranking scrape + unify pipeline.")
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=list(SCRAPER_SCRIPTS),
        default=list(SCRAPER_SCRIPTS),
        help="Which sources to scrape and unify (default: all).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sources = args.sources

    for src in sources:
        script = SCRAPER_SCRIPTS[src]
        print(f"\n=== {script} ===")
        try:
            runpy.run_path(str(SCRIPTS_DIR / script), run_name="__main__")
        except Exception as exc:
            print(f"FAILED: {script}: {exc}", file=sys.stderr)
            raise

    print(f"\n=== unify.py (sources: {', '.join(sources)}) ===")
    import unify

    unify.run(sources)


if __name__ == "__main__":
    main()
