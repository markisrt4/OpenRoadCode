// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#include "../src/vehicle_motion.hpp"
#include "../src/vehicle_marker.hpp"
#include "../src/vehicle_follow.hpp"
#include <cassert>
#include <fstream>
#include <iostream>

int main(int argc, char** argv) {
    orc::VehicleFollow follow;
    assert(!follow.enabled());
    follow.cameraUpdate(true);
    assert(follow.enabled());
    follow.suspend();
    follow.cameraUpdate(true); // Queued telemetry after a mouse gesture.
    assert(!follow.enabled());
    follow.setEnabled(true); // Follow/recenter is an explicit user request.
    assert(follow.enabled());
    follow.cameraUpdate(false); // An ordinary camera command stays manual.
    follow.cameraUpdate(true);
    assert(!follow.enabled());

    orc::VehicleMotion moving;
    assert(!moving.sample(0));
    moving.update(0, 0, 90, 90, 10, true, 0);
    double previous = 0;
    for (int frame = 1; frame <= 60; ++frame) {
        auto position = *moving.sample(frame / 60.0);
        assert(position.longitude > previous); // No one-second plateau.
        previous = position.longitude;
    }
    const auto beforeFix = *moving.sample(1);
    moving.update(0, 10.0 / 6378137.0 * 180 / orc::vehiclePi, 90, 90, 10, true, 1);
    assert(moving.sample(1)->longitude == beforeFix.longitude); // Retarget without jumping.
    auto afterFix = *moving.sample(1.1);
    assert(afterFix.longitude > beforeFix.longitude);
    const auto expired = *moving.sample(2.5);
    assert(moving.sample(100)->longitude == expired.longitude);

    moving.update(0, 0.01, 90, 90, 10, true, 101); // Teleport over 75 m.
    assert(moving.sample(101)->longitude == 0.01);
    moving.update(1, 2, std::nullopt, 90, 10, false, 102); // Cached state never predicts.
    assert(moving.sample(103)->latitude == 1);
    assert(moving.sample(103)->longitude == 2);
    assert(!moving.sample(103)->heading);

    orc::VehicleMotion stopped;
    stopped.update(0, 0, std::nullopt, std::nullopt, std::nullopt, true, 0);
    stopped.update(0, 0.00001, std::nullopt, std::nullopt, std::nullopt, true, 1);
    auto correcting = *stopped.sample(1.1);
    assert(correcting.longitude > 0 && correcting.longitude < 0.00001);
    assert(!correcting.heading);
    const auto held = *stopped.sample(2.5);
    assert(stopped.sample(10)->longitude == held.longitude);

    orc::VehicleMotion turning;
    turning.update(0, 0, 359, std::nullopt, std::nullopt, true, 0);
    turning.update(0, 0, 1, std::nullopt, std::nullopt, true, 1);
    assert(std::abs(orc::angleDelta(359, *turning.sample(1.1)->heading)) < 2);
    assert(*turning.sample(1.1)->heading > 359); // Short path across north.

    orc::VehicleMotion dateline;
    dateline.update(0, 179.9999, 90, 90, 30, true, 0);
    auto crossing = *dateline.sample(1);
    assert(crossing.longitude < -179.999);
    assert(std::abs(orc::angleDelta(179.9999, crossing.longitude)) < 0.001);

    const auto pixels = orc::vehicleIconPixels();
    const auto pixel = [&pixels](unsigned x, unsigned y, unsigned channel) {
        return pixels[(y * orc::vehicleIconSize + x) * 4 + channel];
    };
    assert(pixel(32, 20, 3) == 255); // Solid, forward-pointing tip.
    assert(pixel(32, 54, 3) == 0); // Split tail.
    assert(pixel(0, 0, 3) == 0);
    assert(pixel(32, 20, 0) == 22 && pixel(32, 20, 1) == 139 && pixel(32, 20, 2) == 209);
    for (unsigned i = 0; i < pixels.size(); i += 4) {
        assert(pixels[i] <= pixels[i + 3] && pixels[i + 1] <= pixels[i + 3] && pixels[i + 2] <= pixels[i + 3]);
    }
    if (argc == 2) {
        std::ofstream output(argv[1], std::ios::binary);
        output.write(reinterpret_cast<const char*>(pixels.data()), pixels.size());
    }
    std::cout << "Vehicle motion and chevron checks passed\n";
}
