# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from __future__ import annotations
import shutil, subprocess, time
from pathlib import Path
from apps.launchers.app_launcher_if import AppLauncherIf, StatusCallback
from apps.launchers.external_window_manager import ExternalWindowManager, x11_environment
from apps.launchers.graphics_environment import graphics_environment
from apps.launchers.process_manager import close_matching_display_apps, is_process_running, terminate_process
from common.logging.logging_paths import logging_file_path

class BrowserKioskLauncher(AppLauncherIf):
    def __init__(self, *, url:str, process_pattern:str|None=None, log_file:str|Path|None=None, browser_candidates:tuple[str,...]=('chromium-browser','chromium','google-chrome'), kiosk:bool=True, app_mode:bool=False, profile_path:str|Path|None=None, window_position:tuple[int,int]|None=None, window_size:tuple[int,int]|None=None, startup_grace_seconds:float=0.0, extra_arguments:tuple[str,...]=(), window_class:str|None=None, exclusive_group:str|None=None, window_manager:ExternalWindowManager|None=None)->None:
        if kiosk and app_mode: raise ValueError('kiosk and app_mode cannot both be enabled')
        self.url=url; self.process_pattern=process_pattern or url; self.log_file=Path(log_file or logging_file_path('openroadcode','browser.log')); self.browser_candidates=browser_candidates; self.kiosk=kiosk; self.app_mode=app_mode; self.profile_path=Path(profile_path).expanduser() if profile_path else None; self.window_position=window_position; self.window_size=window_size; self.startup_grace_seconds=startup_grace_seconds; self.extra_arguments=extra_arguments; self.window_class=window_class; self.exclusive_group=exclusive_group; self.color_scheme:str|None=None; self.borderless=False; self.parent_window_id:int|None=None; self._window_manager=window_manager or ExternalWindowManager(); self._process=None; self._window_id=None; self._hidden=False
    def set_url(self,url:str)->None:
        if self.is_running(): raise RuntimeError('Cannot change browser URL while it is running')
        self.url=url
    def set_color_scheme(self,value:str|None)->None:
        if value not in (None,'dark','light'): raise ValueError("color_scheme must be 'dark', 'light', or None")
        if self.is_running(): raise RuntimeError('Cannot change browser color scheme while it is running')
        self.color_scheme=value
    def is_running(self)->bool:
        if self._process is not None and self._process.poll() is None: return True
        return is_process_running(self.process_pattern)
    def configure_app_window(self,*,position:tuple[int,int],size:tuple[int,int],borderless:bool=False,parent_window_id:int|None=None)->None:
        self.kiosk=False; self.app_mode=True; self.borderless=borderless; self.parent_window_id=parent_window_id; self.window_position=position; self.window_size=size; self.startup_grace_seconds=max(self.startup_grace_seconds,.2)
    def configure_kiosk_window(self,*,position:tuple[int,int],size:tuple[int,int])->None:
        self.kiosk=True; self.app_mode=False; self.parent_window_id=None; self.window_position=position; self.window_size=size; self.startup_grace_seconds=max(self.startup_grace_seconds,.2)
    def configure_embedded_kiosk_window(self,*,position:tuple[int,int],size:tuple[int,int],parent_window_id:int)->None:
        self.kiosk=True; self.app_mode=False; self.borderless=True; self.parent_window_id=parent_window_id; self.window_position=position; self.window_size=size; self.startup_grace_seconds=max(self.startup_grace_seconds,.2)
    def send_key(self,d:str,key:str)->bool:
        if not self.is_running(): return False
        self._ensure_window_id(d)
        return self._window_manager.send_key(display=d,window_id=self._window_id,key=key)
    def launch(self,remote_display:str,set_status:StatusCallback=None)->None:
        if self.is_running(): self.show(remote_display,set_status); return
        self._window_id=None; self._hidden=False; env=graphics_environment(x11_environment(remote_display)); browser=self._find_browser()
        if self.color_scheme=='dark': env['GTK_THEME']='Adwaita:dark'
        elif self.color_scheme=='light': env['GTK_THEME']='Adwaita'
        cmd=[browser,'--noerrdialogs','--disable-infobars','--disable-session-crashed-bubble','--disable-restore-session-state','--password-store=basic']
        if self.color_scheme=='dark': cmd.append('--force-dark-mode')
        if self.kiosk: cmd.append('--kiosk')
        if self.app_mode: cmd.append(f'--app={self.url}')
        if self.profile_path is not None: self.profile_path.mkdir(parents=True,exist_ok=True); cmd.append(f'--user-data-dir={self.profile_path}')
        if self.window_position: cmd.append(f'--window-position={self.window_position[0]},{self.window_position[1]}')
        if self.window_size: cmd.append(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        cmd.extend(self.extra_arguments)
        if self.window_class: cmd.append(f'--class={self.window_class}')
        if not self.app_mode: cmd.append(self.url)
        self.log_file.parent.mkdir(parents=True,exist_ok=True); log=self.log_file.open('a',encoding='utf-8')
        try: self._process=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,text=True)
        finally: log.close()
        if self.startup_grace_seconds: time.sleep(self.startup_grace_seconds)
        self._fit_app_window(remote_display); _status(set_status,f'Browser launched on {remote_display}')
    def show(self,d,set_status=None)->bool:
        if not self.is_running(): return False
        self._ensure_window_id(d); shown=self._window_manager.show(display=d,window_id=self._window_id); self._hidden=False; return shown
    def hide(self,d,set_status=None)->bool:
        if not self.is_running(): return False
        self._ensure_window_id(d); hidden=self._window_manager.hide(display=d,window_id=self._window_id); self._hidden=hidden; return hidden
    def stop(self,d,set_status=None)->None:
        self._ensure_window_id(d); self._window_manager.close(display=d,window_id=self._window_id)
        if self._process is not None: terminate_process(self._process)
        close_matching_display_apps(display=d,patterns=(self.process_pattern,)); self._process=None; self._window_id=None; self._hidden=False
    def toggle(self,d,set_status=None)->bool:
        if self.is_running() and not self._hidden: return False if self.hide(d,set_status) else False
        if self.is_running(): return self.show(d,set_status)
        self.launch(d,set_status); return True
    def _find_browser(self)->str:
        for c in self.browser_candidates:
            p=shutil.which(c)
            if p:return p
        raise RuntimeError('No supported browser found')
    def _fit_app_window(self,d:str)->None:
        if self.window_class and self.window_position and self.window_size: self._window_id=self._window_manager.fit(display=d,window_class=self.window_class,position=self.window_position,size=self.window_size,borderless=self.borderless,parent_window_id=self.parent_window_id)
    def _ensure_window_id(self,d:str)->None:
        if self._window_id is None and self.window_class: self._window_id=self._window_manager.wait_for_window_id(display=d,window_class=self.window_class)

def _status(callback,message):
    if callback: callback(message)
