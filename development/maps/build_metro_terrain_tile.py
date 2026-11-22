"""Build one resumable tile of the Metro Detroit terrain package."""

import argparse
from pathlib import Path

from development.maps.regional_terrain import build_metro_tile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tile", required=True, type=int, choices=range(21))
    parser.add_argument("--cache", required=True, type=Path)
    args = parser.parse_args()
    build_metro_tile(args.cache, tile=args.tile)
    print(f"Validated Metro Detroit terrain tile {args.tile}/20")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

