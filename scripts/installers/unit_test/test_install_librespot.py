# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from pathlib import Path
import os
import subprocess


PROJECT_ROOT=Path(__file__).resolve().parents[3]
INSTALLER=PROJECT_ROOT/"scripts"/"installers"/"install_librespot.sh"


def test_dry_run_reports_pipewire_visible_install(tmp_path:Path) -> None:
    environment=os.environ.copy()
    environment.update({"HOME":str(tmp_path),"LIBRESPOT_INSTALL_ROOT":str(tmp_path/"local"),"LIBRESPOT_CACHE_DIR":str(tmp_path/"cache"),"LIBRESPOT_SERVICE_DIR":str(tmp_path/"services")})

    result=subprocess.run([str(INSTALLER),"--device-name","CarUI Test","--dry-run"],cwd=PROJECT_ROOT,env=environment,capture_output=True,text=True,check=False)

    assert result.returncode == 0,result.stderr
    assert "Connect name:      CarUI Test" in result.stdout
    assert "Audio backend:    pulseaudio" in result.stdout
    assert "no changes were made" in result.stdout
    assert not (tmp_path/"services").exists()


def test_rejects_unsafe_device_name(tmp_path:Path) -> None:
    environment=os.environ.copy();environment["HOME"]=str(tmp_path)
    result=subprocess.run([str(INSTALLER),"--device-name","bad\nname","--dry-run"],cwd=PROJECT_ROOT,env=environment,capture_output=True,text=True,check=False)
    assert result.returncode != 0
    assert "unsupported characters" in result.stderr
