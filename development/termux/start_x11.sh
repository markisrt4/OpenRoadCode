#!/usr/bin/env bash

echo "Starting X11 on DISPLAY=:1"

termux-x11 :1 -xstartup "dbus-launch --exit-with-session xfce4-session"
