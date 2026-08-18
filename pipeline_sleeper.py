"""Scrape the Sleeper-format ranking and build data/unified_sleeper.csv.

Usage: python pipeline_sleeper.py
"""
import runpy
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def main() -> None:
    print("\n=== sleeper_scrape.py ===")
    try:
        runpy.run_path(str(SCRIPTS_DIR / "sleeper_scrape.py"), run_name="__main__")
    except Exception as exc:
        print(f"FAILED: sleeper_scrape.py: {exc}", file=sys.stderr)
        raise

    print("\n=== unify_sleeper.py ===")
    import unify_sleeper

    unify_sleeper.run()


if __name__ == "__main__":
    main()
