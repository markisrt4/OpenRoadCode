# SPDX-License-Identifier: MIT
"""Test readsb's positive and negative USB ownership evidence."""

from pathlib import Path
from unittest.mock import Mock

from hardware_io.rf.readsb_systemd_service import ReadsbSystemdService


def test_readsb_verifies_the_open_usb_device(tmp_path: Path) -> None:
    usb = tmp_path / "usb"
    proc = tmp_path / "proc"
    device = usb / "1-1"
    device.mkdir(parents=True)
    for key, value in {
        "serial": "orbital",
        "idVendor": "0bda",
        "idProduct": "2838",
        "busnum": "1",
        "devnum": "5",
    }.items():
        (device / key).write_text(value)
    descriptors = proc / "42" / "fd"
    descriptors.mkdir(parents=True)
    fd = descriptors / "4"
    fd.symlink_to("/dev/bus/usb/001/006")
    service = ReadsbSystemdService("orbital", usb_root=usb, proc_root=proc)
    service._state = Mock(return_value={"ActiveState": "active", "MainPID": "42"})
    assert not service.active()
    fd.unlink()
    fd.symlink_to("/dev/bus/usb/001/005")
    assert service.active()

    (device / "devnum").unlink()
    assert not service.active()


def test_readsb_retains_ownership_while_control_group_exists() -> None:
    service = ReadsbSystemdService("orbital")
    service._run = Mock(return_value=Mock(returncode=0))
    state = {
        "ActiveState": "inactive",
        "SubState": "dead",
        "MainPID": "0",
        "ControlPID": "0",
        "ControlGroup": "/user.slice/readsb.service",
    }
    service._state = Mock(return_value=state)
    assert not service.stop()
    state["ControlGroup"] = ""
    assert service.stop()
