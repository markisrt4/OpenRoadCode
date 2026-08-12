# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

# Import the ADS1x15 module.
import Adafruit_ADS1x15

class MultiTurnPot(object):
    # Reads the multi turn pot and sends an event after a turn has been made.

    def __init__(self, AtoDPin, thresh):
        self.AtoDPin = AtoDPin
        self.thresh = thresh

        self.gain = 1
        self.thresh = 10
        self.val0 = 0
	self.deltaFilter = 100

	self.potTurnedCallback = None

        # Create an ADS1015 ADC (12-bit) instance.
        self.adc = Adafruit_ADS1x15.ADS1015()

    def registerCallback(self, callbackFunc):
        self.potTurnedCallback = callbackFunc

    def tick(self):
        # Should be called a 4 Hz
        # Read ADC channel AtoAPin for volume.
        val1 = self.adc.read_adc(self.AtoDPin, gain=self.gain)
        deltaVal = val1 - self.val0

        if deltaVal > self.thresh or deltaVal < -self.thresh:
            self.val0 = val1
            self.potTurnedCallback(deltaVal)
