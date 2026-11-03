"""Assemble a regional terrain pack from previously validated tile directories."""

import argparse
from pathlib import Path

from development.maps.regional_terrain import assemble


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", required=True, choices=("metro-detroit",))
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    assemble(args.output, coverage=args.coverage, cache=args.cache)
    print(f"Assembled validated terrain pack: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
