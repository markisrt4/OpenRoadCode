import sys
sys.path.append("../config")

from RadioConfig import RadioConfig

import curses


# Create Radio Config object
radioConfig = RadioConfig()

datastore = radioConfig.load("../config/RadioConfig.json")

for n in datastore["radio_config"]["stations"]:
    print ("Name = " + n["name"])
    print ("Demod = "+n["demod"])
    print ("Start = " +str(n["freq_start"]))
    print ("End = " +str(n["freq_end"]))
    print ("Jump = " +str(n["freq_jump"]) + "\n\n")
