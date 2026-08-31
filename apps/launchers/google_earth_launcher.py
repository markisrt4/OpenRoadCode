# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from __future__ import annotations
from apps.launchers.app_launcher_if import StatusCallback
from apps.launchers.browser_launcher import BrowserKioskLauncher

class GoogleEarthLauncher:
    BASE_URL="https://earth.google.com/web/search"
    def __init__(self,*,browser:BrowserKioskLauncher|None=None)->None:
        self._browser=browser or BrowserKioskLauncher(url=self._location_url(42.3314,-83.0458),process_pattern="earth.google.com",window_class="openroadcode-google-earth")
    def configure_app_window(self,*,position:tuple[int,int],size:tuple[int,int],parent_window_id:int|None=None)->None:
        self._browser.configure_app_window(position=position,size=size,borderless=True,parent_window_id=parent_window_id)
    def configure_kiosk_window(self,*,position:tuple[int,int],size:tuple[int,int])->None:self._browser.configure_kiosk_window(position=position,size=size)
    def set_color_scheme(self,value:str|None)->None:self._browser.set_color_scheme(value)
    def set_location(self,latitude:float,longitude:float)->None:self._browser.set_url(self._location_url(latitude,longitude))
    def launch(self,d:str,set_status:StatusCallback=None)->None:self._browser.launch(d,set_status)
    def show(self,d:str,set_status:StatusCallback=None)->bool:return self._browser.show(d,set_status)
    def hide(self,d:str,set_status:StatusCallback=None)->bool:return self._browser.hide(d,set_status)
    def stop(self,d:str,set_status:StatusCallback=None)->None:self._browser.stop(d,set_status)
    def toggle(self,d:str,set_status:StatusCallback=None)->bool:return self._browser.toggle(d,set_status)
    def is_running(self)->bool:return self._browser.is_running()
    @classmethod
    def _location_url(cls,latitude:float,longitude:float,*,tilt:float=60.0)->str:return f"{cls.BASE_URL}/{latitude},{longitude}/@{latitude},{longitude},182a,605d,35y,0h,{tilt}t,0r"
