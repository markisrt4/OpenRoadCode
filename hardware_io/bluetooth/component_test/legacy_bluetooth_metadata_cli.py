import sys
sys.path.append('../bluetooth')

from BluetoothMetadata import BluetoothMetadata

from threading import Thread
from time import sleep

btmd = BluetoothMetadata()
btmd.initialize()

while 1:
	btmd.tick()
	print ("Artist = "+btmd.getTrackArtist())
	print ("Title = "+btmd.getTrackTitle())
	print ("Album = "+btmd.getTrackAlbum())
	print ("Elapsed time = "+str(btmd.getTrackElapsedSeconds()))
	print ("Percentage complete = " + str(btmd.getTrackPercentageComplete()))
	sleep (1)
