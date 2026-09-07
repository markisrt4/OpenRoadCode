# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ORC-owned HPR-aware vehicle marker rendered above Google Earth."""

from __future__ import annotations

import math

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient


class EarthVehicleOverlay:
    """Render a small CSS-3D vehicle marker over Earth's tracked position.

    Google Earth Web does not expose a supported API for replacing its native
    blue location marker.  This keeps the marker entirely ORC-owned by placing
    a lightweight 3-D model above the Earth canvas through CDP.  The model can
    later be replaced by a real mesh without changing navigation telemetry.
    """

    _ROOT_ID = "orc-earth-vehicle-overlay"

    def __init__(
        self,
        client: ChromiumDevToolsClient | None = None,
        *,
        x_fraction: float = 0.50,
        y_fraction: float = 0.63,
    ) -> None:
        self._client = client or ChromiumDevToolsClient(port=9223)
        self._x_fraction = max(0.05, min(0.95, float(x_fraction)))
        self._y_fraction = max(0.05, min(0.95, float(y_fraction)))

    def install(self) -> bool:
        x_pct = self._x_fraction * 100.0
        y_pct = self._y_fraction * 100.0
        expression = f"""(() => {{
            const existing = document.getElementById('{self._ROOT_ID}');
            if (existing) return true;

            const root = document.createElement('div');
            root.id = '{self._ROOT_ID}';
            root.style.cssText = `
                position: fixed;
                left: {x_pct:.3f}%;
                top: {y_pct:.3f}%;
                width: 58px;
                height: 58px;
                transform: translate(-50%, -50%);
                transform-style: preserve-3d;
                perspective: 180px;
                pointer-events: none;
                z-index: 2147483646;
                filter: drop-shadow(0 3px 3px rgba(0,0,0,.75));
            `;

            const attitude = document.createElement('div');
            attitude.dataset.role = 'attitude';
            attitude.style.cssText = `
                position: absolute;
                left: 50%;
                top: 50%;
                width: 42px;
                height: 22px;
                transform-style: preserve-3d;
                transform-origin: 50% 50%;
            `;

            const body = document.createElement('div');
            body.style.cssText = `
                position: absolute;
                left: -21px;
                top: -11px;
                width: 42px;
                height: 22px;
                border-radius: 10px 10px 7px 7px;
                background: linear-gradient(90deg,#20282f 0%,#46535d 42%,#20282f 100%);
                border: 1px solid rgba(255,255,255,.9);
                box-sizing: border-box;
                transform: translateZ(5px);
            `;

            const nose = document.createElement('div');
            nose.style.cssText = `
                position: absolute;
                left: -7px;
                top: -5px;
                width: 14px;
                height: 10px;
                border-radius: 6px 2px 2px 6px;
                background: #84ce1f;
                transform: translate3d(16px,0,8px);
            `;

            const cabin = document.createElement('div');
            cabin.style.cssText = `
                position: absolute;
                left: -10px;
                top: -7px;
                width: 20px;
                height: 14px;
                border-radius: 7px;
                background: rgba(115,190,230,.85);
                border: 1px solid rgba(255,255,255,.65);
                box-sizing: border-box;
                transform: translate3d(-3px,0,11px);
            `;

            for (const y of [-12, 12]) {{
                for (const x of [-12, 12]) {{
                    const wheel = document.createElement('div');
                    wheel.style.cssText = `
                        position:absolute;
                        width:8px;
                        height:4px;
                        margin-left:-4px;
                        margin-top:-2px;
                        border-radius:3px;
                        background:#050505;
                        transform: translate3d(${{x}}px,${{y}}px,2px);
                    `;
                    attitude.appendChild(wheel);
                }}
            }}

            attitude.appendChild(body);
            attitude.appendChild(cabin);
            attitude.appendChild(nose);
            root.appendChild(attitude);
            document.documentElement.appendChild(root);
            return true;
        }})()"""
        try:
            return self._client.evaluate_earth(expression) is True
        except (OSError, RuntimeError, ValueError):
            return False

    def remove(self) -> bool:
        try:
            self._client.evaluate_earth(
                f"document.getElementById('{self._ROOT_ID}')?.remove(); true"
            )
            return True
        except (OSError, RuntimeError, ValueError):
            return False

    def update_attitude(
        self,
        *,
        heading_rad: float | None,
        pitch_rad: float | None,
        roll_rad: float | None,
    ) -> bool:
        """Apply heading, pitch, and roll from ORC navigation telemetry."""
        heading_deg = 0.0 if heading_rad is None else math.degrees(heading_rad) % 360.0
        pitch_deg = 0.0 if pitch_rad is None else math.degrees(pitch_rad)
        roll_deg = 0.0 if roll_rad is None else math.degrees(roll_rad)

        # Vehicle-space axes: heading around screen Z, pitch around Y, roll around X.
        expression = f"""(() => {{
            const root = document.getElementById('{self._ROOT_ID}');
            const node = root?.querySelector('[data-role="attitude"]');
            if (!node) return false;
            node.style.transform =
                'translate(-50%, -50%) ' +
                'rotateZ({heading_deg:.3f}deg) ' +
                'rotateY({-pitch_deg:.3f}deg) ' +
                'rotateX({roll_deg:.3f}deg)';
            return true;
        }})()"""
        try:
            return self._client.evaluate_earth(expression) is True
        except (OSError, RuntimeError, ValueError):
            return False
