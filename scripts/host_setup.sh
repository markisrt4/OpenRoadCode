#!/bin/bash

sudo apt update
sudo apt install -y git curl lighttpd python3.10-venv python3-tk python3-pip
sudo apt install -y tigervnc-standalone-server tigervnc-common xfce4 xfce4-goodies
sudo apt install -y xfce4 xfce4-goodies dbus-x11 xterm
sudo apt install -y openbox xterm x11-apps
sudo apt install -y curl wget ca-certificates rtl-sdr lighttpd
sudo apt install -y gpsd gpsd-clients python3-gps chromium-browser
sudo apt install -y sdrpp wmctrl

python3 -m venv venv
source venv/bin/activate
pip install streamlit requests geocoder streamlit-autorefresh gpsd-py3 tk
