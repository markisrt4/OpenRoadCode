// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once

#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace orc {
constexpr unsigned vehicleIconSize = 64;
/** Rasterize the ORC split-tail chevron at 2x resolution, without external sprites. */
inline std::array<uint8_t, vehicleIconSize * vehicleIconSize * 4> vehicleIconPixels() {
    std::array<uint8_t, vehicleIconSize * vehicleIconSize * 4> pixels{};
    constexpr std::array<std::array<double, 2>, 4> polygon{{
        {{32, 8}}, {{51, 52}}, {{32, 42}}, {{13, 52}}
    }};
    for (unsigned y = 0; y < vehicleIconSize; ++y) {
        for (unsigned x = 0; x < vehicleIconSize; ++x) {
            double r = 0, g = 0, b = 0, alpha = 0;
            // Supersampling gives clean outlines on both light and dark tiles.
            for (unsigned sy = 0; sy < 4; ++sy) for (unsigned sx = 0; sx < 4; ++sx) {
                const double px = x + (sx + 0.5) / 4, py = y + (sy + 0.5) / 4;
                bool inside = false;
                double edgeDistance = 100;
                for (unsigned i = 0, j = 3; i < polygon.size(); j = i++) {
                    const auto& a = polygon[j]; const auto& c = polygon[i];
                    if ((a[1] > py) != (c[1] > py) &&
                        px < (c[0] - a[0]) * (py - a[1]) / (c[1] - a[1]) + a[0]) inside = !inside;
                    const double dx = c[0] - a[0], dy = c[1] - a[1];
                    const double t = std::clamp(((px - a[0]) * dx + (py - a[1]) * dy) /
                        (dx * dx + dy * dy), 0.0, 1.0);
                    edgeDistance = std::min(edgeDistance, std::hypot(px - a[0] - t * dx, py - a[1] - t * dy));
                }
                if (!inside && edgeDistance > 4) continue;
                alpha += 255;
                if (!inside && edgeDistance > 2.5) { r += 20; g += 29; b += 38; }
                else if (!inside || edgeDistance < 2.5) { r += 255; g += 255; b += 255; }
                else { r += 22; g += 139; b += 209; } // ORC --accent-primary
            }
            const auto offset = (y * vehicleIconSize + x) * 4;
            pixels[offset] = static_cast<uint8_t>(r / 16);
            pixels[offset + 1] = static_cast<uint8_t>(g / 16);
            pixels[offset + 2] = static_cast<uint8_t>(b / 16);
            pixels[offset + 3] = static_cast<uint8_t>(alpha / 16);
        }
    }
    return pixels;
}
} // namespace orc
