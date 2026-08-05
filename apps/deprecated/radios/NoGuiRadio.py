import sys
import threading

sys.path.append("../radioFreq")
sys.path.append("../config")
sys.path.append("../hardwareDevices")
sys.path.append("../network")

from time import sleep

from GqrxCtrl import GqrxCtrl
from RadioConfig import RadioConfig
from RadioCtrl import RadioCtrl
from MultiTurnPot import MultiTurnPot
from RotaryEncoder import RotaryEncoder
from VolumeKnob import VolumeKnob

# Constants
ENCODER_PIN_A = 16
ENCODER_PIN_B = 20
ENCODER_GPIO_PRESS_BTN = 12


# Create Radio Config object
radioConfig = RadioConfig()

# Create new radio controller object
radio_ctrl = RadioCtrl(radioConfig)

initial_counter = 0

def MultiTurnPotHandler(deltaVal):
	global radio_ctrl, initial_counter
	if initial_counter < 1:
		initial_counter = 1
		print ("Ignoring first multi-turn read")
                return
	deltaFreq = (deltaVal % 10) * 1000
	print ("deltaFreq=" + str(deltaFreq))
	if deltaVal > 0:
		print ("Increasing frequency by: " + str(deltaFreq))
		radio_ctrl.increaseFrequency(radio_ctrl, deltaFreq)
		
	elif deltaVal < 0:
		print ("Decreasing frequency by: " + str(deltaFreq))
		radio_ctrl.decreaseFrequency(deltaFreq)


def RotaryBtnHandler(self):
    radio_ctrl.setNextBand()
    demod = radio_ctrl.getCurrDemod
    freq = radio_ctrl.getCurrFreqency
    print ("Demod=" + demod)
    #gqrx.gqrxSetDemodMode(demod)
    #gqrx.gqrxTuneFreq(freq)


def RotaryRotateHandler(num):
    if num > 1 or num < -1:
        print ("Bogus number: " + str(num))
    else:
        if num == 1:
            freq = radio_ctrl.getNextFrequency
        elif num == -1:
            freq = radio_ctrl.getPrevFrequency
        print ("New freq=" + str(freq))
        #gqrx.gqrxTuneFreq(freq)


def VolumeOffHandler(self):
    print ("Volume is at 0!")



# Create new multi turn pot handler
mtpot = MultiTurnPot(1, 10)
mtpot.registerCallback(MultiTurnPotHandler)


def mtpotThread():
    while True:
    	mtpot.tick()
    	sleep(.25)


# Create rotary encoder handler
rotenc = RotaryEncoder(ENCODER_PIN_A, ENCODER_PIN_B, ENCODER_GPIO_PRESS_BTN)
rotenc.registerPressCallback(RotaryBtnHandler)
rotenc.registerRotateCallback(RotaryRotateHandler)


def rotencThread():
    while True:
    	rotenc.tick()
    	sleep(.05)


# Create volume knob handler
volknob = VolumeKnob(0, VolumeOffHandler, True)


def volknobThread():
    while True:
    	volknob.tick()
    	sleep(.25)


# Setup GQRX
#gqrx = GqrxCtrl(sys.argv[1], True)

thread1 = threading.Thread(target=mtpotThread)
thread2 = threading.Thread(target=rotencThread)
thread3 = threading.Thread(target=volknobThread)

# Start all threads
thread1.start()
thread2.start()
thread3.start()

thread3.join()
thread2.join()
thread1.join()
