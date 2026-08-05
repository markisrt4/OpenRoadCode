import sys

sys.path.append("../hardwareDevices")

from MultiTurnPot import MultiTurnPot
from time import sleep

def TurnNotifier(deltaVal):
    if deltaVal > 50 or deltaVal < -50:
        print ("Bogus delta value of " + str(deltaVal) + ", disregarding")
    else:
        print ("Delta Turn=" + str(deltaVal))

mtpot = MultiTurnPot(1,10)
mtpot.registerCallback(TurnNotifier)


while True:
    mtpot.tick()
    sleep(.25)
