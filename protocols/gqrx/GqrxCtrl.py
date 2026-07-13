import socket
import sys


class GqrxCtrl():
    # Class to control qgrx via TCP

    def __init__(self, gqrxHostIp, debugOn):
        self.ip = gqrxHostIp
        self.port = 7356
        self.bufSize = 1024
	self.debugOn = debugOn

        # Establish TCP connection to GQRX
        self.qgrxClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.qgrxClient.connect((self.ip, self.port))

    def gqrxTuneFreq(self, freq):
        message = "F " + str(freq)
	if self.debugOn == True:
		print (message)
        #self.qgrxClient.send(message)

    def gqrxSetDemodMode(self, DemodMode):
        message = "M " + DemodMode
	if self.debugOn == True:
		print (message)
        #self.qgrxClient.send(message)

    def gqrxClose(self):
        self.gqrxClient.close()
