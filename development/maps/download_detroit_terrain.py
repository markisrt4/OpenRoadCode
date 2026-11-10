"""Download the legacy downtown prototype using the shared terrain builder."""

import argparse
from pathlib import Path

from apps.launchers.local_terrain_pack import detroit_terrain_directory
from tools.map_builder.builder.terrain import download as build_terrain

SIZE = 33


def download(destination):
    build_terrain(destination, 'detroit-downtown', size=SIZE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=detroit_terrain_directory())
    args = parser.parse_args()
    try:
        download(args.output)
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as error:
        parser.exit(1,f"Detroit terrain download: {error}\n")


if __name__ == "__main__":
    main()
