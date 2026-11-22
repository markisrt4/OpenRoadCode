"""Activate a finished offline imagery pyramid without build tools on the device."""

import argparse
from pathlib import Path
import sqlite3
import uuid

from apps.launchers.local_imagery_pyramid import LocalImageryPyramidPack, PILOT_BOUNDS, MAX_DATABASE_BYTES
from common.xdg_paths import openroadcode_data_dir
from development.maps.prebuilt_imagery import read_local_archive, unpack

MAX_ARCHIVE_BYTES = 512*1024*1024


def install(archive, coverage, *, destination=None):
    descriptor,archive = read_local_archive(archive,coverage,max_archive_bytes=MAX_ARCHIVE_BYTES)
    if descriptor.get('kind') != 'imagery-pyramid':
        raise ValueError('Descriptor is not an imagery pyramid')
    active = destination or openroadcode_data_dir('map-packs',coverage+'-imagery-detail-active')
    if active.exists() and not active.is_symlink():
        raise ValueError('Active detail imagery path must be a managed revision link')
    active.parent.mkdir(parents=True,exist_ok=True)
    revision = active.parent/('.imagery-detail-'+uuid.uuid4().hex)
    unpack(archive,revision,PILOT_BOUNDS[coverage],loader=LocalImageryPyramidPack.load,
           max_unpacked_bytes=MAX_DATABASE_BYTES+16*1024*1024)
    pending = active.parent/('.active-imagery-detail-'+uuid.uuid4().hex)
    try:
        pending.symlink_to(revision.name,target_is_directory=True)
        pending.replace(active)
    finally:
        pending.unlink(missing_ok=True)
    print('Ready: offline detail imagery installed. Reopen Terrain and zoom into '+coverage+'.')
    return active


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coverage',choices=tuple(PILOT_BOUNDS),required=True)
    parser.add_argument('--pack-file',type=Path,required=True)
    args = parser.parse_args()
    try:
        install(args.pack_file,args.coverage)
    except (OSError,ValueError,KeyError,RuntimeError,sqlite3.Error) as error:
        parser.exit(1,f'Detail imagery install failed: {error}\n')


if __name__ == '__main__':
    main()
