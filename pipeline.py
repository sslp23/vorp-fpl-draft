"""Run every source scraper, then unify them into data/unified.csv.

Usage: python pipeline.py
"""
import runpy
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"

SCRAPERS = [
    "waiverkings_scrape.py",
    "draftfantasy_scrape.py",
    "thedraftsociety_scrape.py",
]


def main() -> None:
    for script in SCRAPERS:
        path = SCRIPTS_DIR / script
        print(f"\n=== {script} ===")
        try:
            runpy.run_path(str(path), run_name="__main__")
        except Exception as exc:
            print(f"FAILED: {script}: {exc}", file=sys.stderr)
            raise

    print("\n=== unify.py ===")
    runpy.run_path(str(SCRIPTS_DIR / "unify.py"), run_name="__main__")


if __name__ == "__main__":
    main()
