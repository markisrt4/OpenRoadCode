// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once

#include <algorithm>
#include <cmath>
#include <optional>

namespace orc {
constexpr double vehiclePi = 3.14159265358979323846;
inline double angleDelta(double from, double to) {
    return std::remainder(to - from, 360.0);
}
inline double wrapLongitude(double longitude) {
    return std::remainder(longitude, 360.0);
}

struct VehicleFrame {
    double latitude;
    double longitude;
    std::optional<double> heading;
};

/** Frame-driven visual motion; authoritative GPS fixes are never modified.
 * Inputs use degrees/metres/seconds at the native protocol boundary.
 * Prediction expires after 1.5 seconds; discontinuities over 75 m snap.
 */
class VehicleMotion {
public:
    void update(double latitude, double longitude, std::optional<double> heading,
                std::optional<double> course, std::optional<double> speed,
                bool smooth, double now) {
        sample(now);
        fix = VehicleFrame{latitude, longitude, heading};
        fixTime = now;
        lastFrameTime = now;
        predictionCourse = course;
        predictionSpeed = speed;
        smoothing = smooth;
        if (!display || !smooth || distance(*display, *fix) >= 75.0) {
            display = fix;
        }
        // A lost direction must not leave a north-pointing arrow on the map.
        if (!heading) display->heading.reset();
        else if (!display->heading) display->heading = heading;
    }

    std::optional<VehicleFrame> sample(double now) {
        if (!fix || !display) return std::nullopt;
        if (!smoothing) return display;
        const double age = std::clamp(now - fixTime, 0.0, 1.5);
        const double frameTime = fixTime + age;
        const double dt = std::max(0.0, frameTime - lastFrameTime);
        if (dt == 0.0) return display;
        auto target = *fix;
        if (predictionCourse && predictionSpeed && *predictionSpeed >= 1.5) {
            const double bearing = *predictionCourse * vehiclePi / 180.0;
            const double angularDistance = *predictionSpeed * age / 6378137.0;
            const double latitude = fix->latitude * vehiclePi / 180.0;
            const double nextLatitude = std::asin(std::clamp(
                std::sin(latitude) * std::cos(angularDistance) +
                std::cos(latitude) * std::sin(angularDistance) * std::cos(bearing), -1.0, 1.0));
            target.latitude = nextLatitude * 180.0 / vehiclePi;
            target.longitude = wrapLongitude(fix->longitude + std::atan2(
                std::sin(bearing) * std::sin(angularDistance) * std::cos(latitude),
                std::cos(angularDistance) - std::sin(latitude) * std::sin(nextLatitude))
                * 180.0 / vehiclePi);
        }
        const double alpha = 1.0 - std::exp(-dt / 0.25);
        display->latitude += alpha * (target.latitude - display->latitude);
        display->longitude = wrapLongitude(display->longitude +
            alpha * angleDelta(display->longitude, target.longitude));
        if (display->heading && target.heading) {
            display->heading = std::fmod(*display->heading +
                alpha * angleDelta(*display->heading, *target.heading) + 360.0, 360.0);
        }
        lastFrameTime = frameTime;
        return display;
    }

private:
    static double distance(const VehicleFrame& a, const VehicleFrame& b) {
        const double latitude = (b.latitude - a.latitude) * vehiclePi / 180.0;
        const double longitude = angleDelta(a.longitude, b.longitude) * vehiclePi / 180.0;
        const double haversine = std::pow(std::sin(latitude / 2.0), 2) +
            std::cos(a.latitude * vehiclePi / 180.0) * std::cos(b.latitude * vehiclePi / 180.0) *
            std::pow(std::sin(longitude / 2.0), 2);
        return 2.0 * 6378137.0 * std::asin(std::sqrt(std::clamp(haversine, 0.0, 1.0)));
    }
    std::optional<VehicleFrame> fix;
    std::optional<VehicleFrame> display;
    std::optional<double> predictionCourse;
    std::optional<double> predictionSpeed;
    double fixTime = 0.0;
    double lastFrameTime = 0.0;
    bool smoothing = false;
};
} // namespace orc
