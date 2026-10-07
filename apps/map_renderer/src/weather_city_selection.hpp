// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once

#include <algorithm>
#include <cmath>
#include <string>
#include <tuple>
#include <vector>

struct WeatherCityCandidate {
    std::string name;
    double latitude;
    double longitude;
    double x;
    double y;
    double priority;
};

/** @brief Keep a stable, spaced selection of at most twelve visible cities. */
inline std::vector<WeatherCityCandidate> selectWeatherCities(std::vector<WeatherCityCandidate> candidates) {
    std::sort(candidates.begin(), candidates.end(), [](const auto& a, const auto& b) {
        return std::tie(a.priority, a.name, a.latitude, a.longitude) <
               std::tie(b.priority, b.name, b.latitude, b.longitude);
    });
    std::vector<WeatherCityCandidate> selected;
    for (const auto& candidate : candidates) {
        if (std::any_of(selected.begin(), selected.end(), [&candidate](const auto& other) {
                return (std::abs(candidate.x - other.x) < 150 && std::abs(candidate.y - other.y) < 70) ||
                       (candidate.name == other.name &&
                        std::abs(candidate.latitude - other.latitude) < 0.001 &&
                        std::abs(candidate.longitude - other.longitude) < 0.001);
            })) continue;
        selected.push_back(candidate);
        if (selected.size() == 12) break;
    }
    return selected;
}
