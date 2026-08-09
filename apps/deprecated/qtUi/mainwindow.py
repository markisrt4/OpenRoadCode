# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(480, 320)
        self.centralWidget = QtWidgets.QWidget(MainWindow)
        self.centralWidget.setObjectName("centralWidget")
        self.bluetoothBtn = QtWidgets.QPushButton(self.centralWidget)
        self.bluetoothBtn.setGeometry(QtCore.QRect(0, 0, 240, 320))
        self.bluetoothBtn.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("../qtUi/resources/bluetooth.jpg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.bluetoothBtn.setIcon(icon)
        self.bluetoothBtn.setIconSize(QtCore.QSize(280, 320))
        self.bluetoothBtn.setObjectName("bluetoothBtn")
        self.radioBtn = QtWidgets.QPushButton(self.centralWidget)
        self.radioBtn.setGeometry(QtCore.QRect(240, 0, 240, 320))
        self.radioBtn.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("../qtUi/resources/Antena-Wireless.jpg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.radioBtn.setIcon(icon1)
        self.radioBtn.setIconSize(QtCore.QSize(280, 330))
        self.radioBtn.setObjectName("radioBtn")
        MainWindow.setCentralWidget(self.centralWidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))

