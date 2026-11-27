"""Hardware-independent receiver assignment tests."""

from pathlib import Path

from controllers.radio.receiver_assignments import (
    ReceiverAssignmentController,
    ReceiverAssignments,
    ReceiverAssignmentStore,
)
from hardware_io.rf.linux_usb_receiver_adapter import LinuxUsbReceiverAdapter


def add_device(root: Path, name: str, serial: str, product: str = "2838") -> None:
    device = root / name
    device.mkdir()
    (device / "idVendor").write_text("0bda")
    (device / "idProduct").write_text(product)
    (device / "serial").write_text(serial)


def test_discovery_filters_unrelated_devices(tmp_path: Path) -> None:
    add_device(tmp_path, "1-1", "radio")
    add_device(tmp_path, "1-2", "other", "9999")
    devices = LinuxUsbReceiverAdapter(tmp_path).discover()
    assert len(devices) == 1
    assert devices[0].identity == "0bda:2838:radio"


def test_missing_hardware(tmp_path: Path) -> None:
    assert LinuxUsbReceiverAdapter(tmp_path / "missing").discover() == ()


def test_assignment_persistence(tmp_path: Path) -> None:
    store = ReceiverAssignmentStore(tmp_path / "config" / "rf.json")
    assert store.load() == ReceiverAssignments()
    assignments = ReceiverAssignments(radio="0bda:2838:radio", weather="0bda:2838:radio")
    store.save(assignments)
    assert store.load() == assignments


def test_duplicate_serial_is_not_resolved(tmp_path: Path) -> None:
    add_device(tmp_path, "1-1", "duplicate")
    add_device(tmp_path, "1-2", "duplicate")
    controller = ReceiverAssignmentController(LinuxUsbReceiverAdapter(tmp_path))
    assert controller.resolve(ReceiverAssignments(radio="0bda:2838:duplicate"))["radio"] is None


def test_assignment_survives_usb_path_change(tmp_path: Path) -> None:
    add_device(tmp_path, "1-1", "radio")
    controller = ReceiverAssignmentController(LinuxUsbReceiverAdapter(tmp_path))
    assignments = ReceiverAssignments(radio="0bda:2838:radio")
    (tmp_path / "1-1").rename(tmp_path / "2-3")
    device = controller.resolve(assignments)["radio"]
    assert device is not None
    assert device.usb_path == "2-3"
