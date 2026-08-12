#!/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT


pyuic5 mainwindow.ui -o mainwindow.py
pyuic5 bluetoothplayer.ui -o bluetoothplayer.py
#pyrcc5 radioresource.qrc -o radioresource_rc.py
