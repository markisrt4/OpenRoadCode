"""Build one resumable row of a state terrain package."""

import argparse
from pathlib import Path

from development.maps.regional_terrain import build_michigan_row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", required=True)
    parser.add_argument("--row", required=True, type=int, choices=range(8))
    parser.add_argument("--cache", required=True, type=Path)
    args = parser.parse_args()
    build_michigan_row(args.cache, coverage=args.coverage, row=args.row)
    print(f"Validated terrain row {args.row}/7 for {args.coverage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
