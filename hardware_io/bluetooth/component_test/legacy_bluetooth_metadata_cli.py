# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import sys

sys.path.append("../bluetooth")

from time import sleep

from BluetoothMetadata import BluetoothMetadata

btmd = BluetoothMetadata()
btmd.initialize()

while 1:
    btmd.tick()
    print("Artist = " + btmd.getTrackArtist())
    print("Title = " + btmd.getTrackTitle())
    print("Album = " + btmd.getTrackAlbum())
    print("Elapsed time = " + str(btmd.getTrackElapsedSeconds()))
    print("Percentage complete = " + str(btmd.getTrackPercentageComplete()))
    sleep(1)
