# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Compact, selectable network and USB diagnostics for small ORC displays."""

import ipaddress
import tkinter as tk

from ui.theme import ThemeBundle


def primary_ip(addresses):
    for value in addresses or []:
        try:
            addr = ipaddress.ip_interface(str(value)).ip
            if addr.version == 4:
                return str(addr)
        except ValueError:
            continue
    return "No IPv4"


class NetworkUsbPanel(tk.Frame):
    def __init__(self, parent, *, theme: ThemeBundle):
        ui = theme.ui
        super().__init__(parent, bg=ui.background)
        self._ui = ui
        self._networks = []
        self._devices = []
        self._selected = None
        self._header = tk.Label(self, text="Waiting for diagnostics", anchor="w",
                                bg=ui.background, fg=ui.text, font=("Sans", 11, "bold"))
        self._header.pack(fill=tk.X, padx=8, pady=(6, 2))
        self._source = tk.Label(self, text="", anchor="w", bg=ui.background,
                                fg=ui.text_muted, font=("Sans", 9))
        self._source.pack(fill=tk.X, padx=8)
        self._list = tk.Listbox(self, bg=ui.surface, fg=ui.text,
                                selectbackground=ui.control_active, selectforeground="#ffffff",
                                font=("Sans", 11), height=6, relief=tk.FLAT,
                                highlightthickness=1, highlightbackground=ui.border,
                                activestyle="none", exportselection=False)
        self._list.pack(fill=tk.BOTH, expand=True, padx=8, pady=(5, 4))
        self._list.bind("<<ListboxSelect>>", self._selection_changed)
        self._detail = tk.Label(self, text="Select an interface for details",
                                anchor="nw", justify=tk.LEFT, bg=ui.surface, fg=ui.text,
                                font=("Sans", 10), padx=8, pady=6)
        self._detail.pack(fill=tk.X, padx=8, pady=(0, 6))

    def render(self, report):
        networks = report.get("networks") or []
        usb = report.get("usb_sysfs") or {}
        host_devices = report.get("usb_devices") or []
        sysfs_devices = usb.get("devices") or []
        source = report.get("source", "Unknown")
        label = "Android Companion" if source == "android_companion_via_termux" else (
            "Termux (restricted)" if source == "termux_restricted" else "ORC runtime")
        self._header.configure(text=f"NETWORK  {len(networks)} interfaces     USB  {len(host_devices) + len(sysfs_devices)} devices")
        self._source.configure(text=f"Source: {label}  •  Network: {report.get('networks_status', 'unknown')}")
        previous = self._selected
        self._networks = networks
        self._devices = host_devices + sysfs_devices
        entries = []
        for index, network in enumerate(networks):
            name = network.get("interface") or f"Network {index + 1}"
            transport = ", ".join(network.get("transports") or []) or network.get("state") or "unknown"
            state = "●" if network.get("active") or network.get("state") == "up" else "○"
            entries.append((f"net:{name}", f"{state}  {name:<14} {transport:<12} {primary_ip(network.get('addresses'))}"))
        for index, device in enumerate(self._devices):
            vid = device.get("vendor_id_hex")
            pid = device.get("product_id_hex")
            if vid is None:
                vid, pid = f"{int(device.get('vendor_id', 0)):04x}", f"{int(device.get('product_id', 0)):04x}"
            name = device.get("product") or device.get("device_name") or "USB device"
            entries.append((f"usb:{index}", f"USB  {vid}:{pid}  {name}"))
        if not entries:
            entries = [("empty", "No interfaces or USB devices visible")]
        keys = [key for key, _ in entries]
        self._list.delete(0, tk.END)
        for _, label in entries:
            self._list.insert(tk.END, label)
        if previous in keys:
            selection = keys.index(previous)
        else:
            selection = 0
        self._keys = keys
        self._list.selection_set(selection)
        self._selected = keys[selection]
        self._show_detail()

    def _selection_changed(self, _event=None):
        selection = self._list.curselection()
        if selection:
            self._selected = self._keys[selection[0]]
            self._show_detail()

    def _show_detail(self):
        selected = self._selected or ""
        if selected.startswith("net:"):
            name = selected[4:]
            network = next((net for net in self._networks
                            if net.get("interface") == name), None)
            if network is None:
                text = "Interface unavailable"
            else:
                addresses = network.get("addresses") or []
                ipv6 = [str(value) for value in addresses if ":" in str(value)]
                dns = network.get("dns") or []
                text = (f"{name}  •  IPv4: {primary_ip(addresses)}\n"
                        f"IPv6: {ipv6[0] if ipv6 else 'Unavailable'}\n"
                        f"DNS: {', '.join(dns[:2]) if dns else 'Unavailable'}")
        elif selected.startswith("usb:"):
            device = self._devices[int(selected[4:])]
            text = (f"USB: {device.get('product') or device.get('device_name') or 'Device'}\n"
                    f"Speed: {device.get('speed') or 'Unknown'} Mb/s  •  "
                    f"Permission: {device.get('permission_granted', 'Unknown')}\n"
                    f"Detection: {device.get('detection', 'unknown')}")
        else:
            text = "No visible hardware. Android permissions may restrict enumeration."
        self._detail.configure(text=text)
