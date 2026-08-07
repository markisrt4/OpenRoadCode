from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

import sys
import subprocess

sys.path.append("../bluetooth")
sys.path.append("../hardwareDevices")
sys.path.append("../qtUi")

import mainwindow  # This file holds our MainWindow and all design related things
import bluetoothplayer

from BluetoothMetadata import BluetoothMetadata

from threading import Thread
from time import sleep


class RadioApp(QtWidgets.QMainWindow, mainwindow.Ui_MainWindow):
    def __init__(self):
        super(self.__class__, self).__init__()
        # self.showFullScreen()
        self.setupUi(self)  # This is defined in design.py file automatically
        self.bluetoothBtn.clicked.connect(self.enableBluetooth)
        self.radioBtn.clicked.connect(self.enableRadio)

    def enableBluetooth(self):
        print ("Bluetooth mode")
        # subprocess.call(["sudo", "systemctl", "stop", "radiostream"])
        # subprocess.call(["sudo", "systemctl", "stop", "radioctrl"])
        # subprocess.call(["sudo", "rfkill", "block",  "wifi"])
        # subprocess.call(["sudo", "rfkill", "unblock", "bluetooth"])
        self.hide()
        self.bluetoothmusic = BluetoothMusic(self)
        self.bluetoothmusic.show()
        self.bluetoothmusic.raise_()

    def enableRadio(self):
        print ("Radio mode")
        # subprocess.call(["sudo", "rfkill", "unblock", "wifi"])
        # subprocess.call(["sudo", "rfkill", "block", "bluetooth"])
        # subprocess.call(["sudo", "systemctl", "start", "radiostream"])
        # subprocess.call(["sudo", "systemctl", "start", "radioctrl"])
        subprocess.call(["/opt/script/startvnc.sh"])


class BluetoothMusic(QtWidgets.QMainWindow, bluetoothplayer.Ui_bluetoothplayer):
    def __init__(self, parent):
        super(self.__class__, self).__init__(parent)
        # self.showFullScreen()
        self.setupUi(self)
        self.backBtn.clicked.connect(self.closeAndReturn)
        self.btmd = BluetoothMetadata()
        self.btThread = BluetoothThread(self.btmd)
        # self.btconnected = self.btmd.initialize()
        # if self.btconnected != True:
        #    print "Error connecting!!"
        # else:
        self.btThread.start()
        self.btThread.updateArtistText.connect(self.updateArtistText)
        self.btThread.updateTitleText.connect(self.updateTitleText)
        self.btThread.updateAlbumText.connect(self.updateAlbumText)
        self.btThread.updateTrackProgress.connect(self.updateTrackProgress)
        self.btThread.updateTrackTime.connect(self.updateTrackTime)

    def closeAndReturn(self):
        self.isRunning = False
        self.btThread.quit()
        self.close()
        self.parent().show()

    def updateAlbumText(self, text):
        self.albumLabel.setText(text)

    def updateArtistText(self, text):
        self.artistLabel.setText(text)

    def updateTitleText(self, text):
        self.songLabel.setText(text)

    def updateTrackProgress(self, percent):
        self.progressBar.setProperty("value", percent)

    def updateTrackTime(self, timeNow, totalTime):
        timeNowMins = timeNow / 60
        timeSecsNow = timeNow % 60
        timeStr = '%02.0f' % (timeNowMins) + ':' + '%02.0f' % (timeSecsNow)
        totalTimeMins = totalTime / 60
        totalTimeSecs = totalTime % 60
        totalStr = '%02.0f' % (totalTimeMins) + ':' + '%02.0f' % (totalTimeSecs)
        self.trackElapsed.setText(timeStr)
        self.trackTotal.setText(totalStr)


class BluetoothThread(QThread):
    updateArtistText = pyqtSignal(str)
    updateAlbumText = pyqtSignal(str)
    updateTitleText = pyqtSignal(str)
    updateTrackTime = pyqtSignal(int, int)
    updateTrackProgress = pyqtSignal(float)

    def __init__(self, BluetoothMetadata):
        QThread.__init__(self)
        self.btmd = BluetoothMetadata
        self.isRunning = True
        self.currArtist = ""
        self.currAlbum = ""
        self.currTitle = ""

    def __del__(self):
        self.wait()

    def run(self):
        while not self.btmd.initialize():
            print ("Error connecting!!")
            sleep(1)

        self.running = True

        while self.isRunning:
            try:
                self.btmd.tick()
            except Exception as e:
                print(e)

            artist = self.btmd.getTrackArtist()
            title = self.btmd.getTrackTitle()
            album = self.btmd.getTrackAlbum()
            elapsedTime = self.btmd.getTrackElapsedSeconds()
            totalTime = self.btmd.getTrackTotalSeconds()
            percComplete = self.btmd.getTrackPercentageComplete() * 100
            # print ("Artist = "+artist)
            # print ("Title = "+title)
            # print ("Album = "+album)
            # print ("Elapsed time = "+ str(elapsedTime))
            # print ("Percentage complete = " + str(percComplete))
            if artist != self.currArtist:
                self.updateArtistText.emit(artist)
                self.currArtist = artist

            if album != self.currAlbum:
                self.updateAlbumText.emit(album)
                self.currAlbum = album

            if title != self.currTitle:
                self.updateTitleText.emit(title)
                self.currTitle = title

            self.updateTrackProgress.emit(percComplete)
            self.updateTrackTime.emit(elapsedTime, totalTime)
            sleep(.5)


def main():
    app = QtWidgets.QApplication(sys.argv)  # A new instance of QApplication
    form = RadioApp()  # We set the form to be our ExampleApp (design)
    form.show()  # Show the form
    app.exec_()  # and execute the app


if __name__ == '__main__':  # if we're running file directly and not importing it
    main()  # run the main function

