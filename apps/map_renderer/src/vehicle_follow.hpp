// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once

namespace orc {
/** Explicit follow requests own resumption; queued telemetry cannot undo a pan. */
class VehicleFollow {
public:
    void setEnabled(bool value) { suspended = !value; following = value; }
    void suspend() { setEnabled(false); }
    void cameraUpdate(bool followPosition) {
        if (!followPosition) suspend();
        else if (!suspended) following = true;
    }
    bool enabled() const { return following; }
private:
    bool suspended = false;
    bool following = false;
};
} // namespace orc
